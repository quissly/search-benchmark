"""Paired bootstrap significance testing for the search comparison.

Reads comparison_final_judged/judged/<sector>_judged.json.gz (read-only) and,
for each metric x (Quissly vs vendor) pairing x sector (plus all-sectors
pooled), runs a paired bootstrap over per-query score differences.

Metrics:
  - precision_at_10 / precision_at_20: persisted per-query scalars, used as-is.
  - recall_at_10 / recall_at_20: pooled recall derived per query from the
    persisted per-hit judgments. The relevance pool is the union of score==1
    ids across the 5 compared engines, matching the recall numbers this
    repo publishes (pipeline/metrics_dashboard.py::
    compute_recall_by_complexity, ks=(10, 20)). The script asserts that every
    judged entry contains only the 5 compared engines, so a judged file with
    extra engines (e.g. an older file that included a since-dropped
    engine) fails loudly instead of
    silently widening the pool. Queries with an empty pool are excluded
    (recall undefined), same as the pipeline.
  - ndcg_at_10 / ndcg_at_20: derived per query with the pipeline's exact
    formula (ideal ranking taken over the returned hits' top-k scores).
    Zero-hit queries score 0.0, same as the pipeline.

Sanity check: before any bootstrap runs, the per-query scores are aggregated
and asserted equal to (a) the aggregates CSVs (precision), (b) this repo's
pipeline (compute_rich_metrics), and (c) — when the website repo is checked
out alongside — the published /compare bundle per complexity band.

Bootstrap: resampling unit is the query. For each cell, draw N queries with
replacement from the N paired diffs (Quissly minus vendor), B=10,000
replicates, single numpy default_rng(SEED) consumed in a fixed deterministic
cell order. 95% CI = 2.5th/97.5th percentiles of the bootstrap means.
Two-sided empirical p = 2 * min(P(boot <= 0), P(boot >= 0)), capped at 1.0
(equals the spec's "proportion at or below zero, doubled" whenever the
observed diff is positive). p_raw == 0.0 means no replicate crossed zero,
i.e. p < 2/B = 0.0002.

Holm-Bonferroni is applied across the FULL family of all cells
(6 metrics x 4 pairings x 8 sector slots = 192 tests).

Usage: python analysis/bootstrap/paired_bootstrap.py
Writes analysis/bootstrap/<UTC timestamp>/bootstrap_results.csv and summary.md.
"""
import csv
import gzip
import json
import math
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
JUDGED_DIR = ROOT / "comparison_final_judged" / "judged"
AGGREGATES_DIR = ROOT / "comparison_final_judged" / "aggregates"
WEBSITE_JSON = ROOT.parent / "website" / "website" / "comparison-data" / "json"

SEED = 42
N_REPLICATES = 10_000
ALPHA = 0.05

QUISSLY = "quissly"
COMPARATORS = ["algolia", "clerk", "doofinder", "luigisbox"]
ENGINES = {QUISSLY, *COMPARATORS}
SECTORS = ["auto", "cosmetics", "electronics", "fast_fashion",
           "furniture", "marketplace", "pharmacy"]
METRICS = ["precision_at_10", "precision_at_20", "recall_at_10",
           "recall_at_20", "ndcg_at_10", "ndcg_at_20"]
DISPLAY = {"algolia": "Algolia", "clerk": "Clerk.io", "doofinder": "Doofinder",
           "luigisbox": "Luigi's Box", "quissly": "Quissly"}


def _dcg(scores):
    return sum(s / math.log2(i + 2) for i, s in enumerate(scores))


def _norm_id(s):
    """Pool join key: lowercase, dashes stripped. Quissly's marketplace hits
    carry dashed UUIDs where the other engines carry undashed hex of the
    same ids — see analysis/id_overlap_check/ID_OVERLAP_REPORT.md."""
    return str(s).lower().replace("-", "")


def _read_judged(sector):
    with gzip.open(JUDGED_DIR / f"{sector}_judged.json.gz", "rt",
                   encoding="utf-8") as f:
        return json.load(f)


def per_query_scores(judged):
    """provider -> metric -> {query_id: score}. Mirrors the pipeline's math."""
    out = defaultdict(lambda: defaultdict(dict))
    for entry in judged:
        qid = entry["query_id"]
        providers = entry["providers"]
        # An entry with engines outside the compared set (e.g. from an older
        # file with a since-dropped engine) would silently widen the recall
        # pool — refuse it.
        assert set(providers) <= ENGINES, \
            f"unexpected engines in {qid}: {sorted(set(providers) - ENGINES)}"
        pool = {_norm_id(h["id"]) for p in providers.values()
                for h in p.get("hits", []) if h["score"] == 1}
        for prov, pdata in providers.items():
            hits = sorted(pdata.get("hits", []), key=lambda h: h["rank"])
            out[prov]["precision_at_10"][qid] = pdata["precision_at_10"]
            out[prov]["precision_at_20"][qid] = pdata["precision_at_20"]
            for k in (10, 20):
                ordered = [h["score"] for h in hits][:k]
                idcg = _dcg(sorted(ordered, reverse=True))
                out[prov][f"ndcg_at_{k}"][qid] = \
                    _dcg(ordered) / idcg if idcg > 0 else 0.0
            if pool:
                for k in (10, 20):
                    found = len({_norm_id(h["id"]) for h in hits[:k]
                                 if _norm_id(h["id"]) in pool
                                 and h["score"] == 1})
                    out[prov][f"recall_at_{k}"][qid] = found / len(pool)
    return out


def load_all():
    """sector -> provider -> metric -> {qid: score}"""
    return {sector: per_query_scores(_read_judged(sector)) for sector in SECTORS}


def sanity_check(data):
    """Reproduce the pipeline's reported aggregates from the per-query scores.
    Returns (lines, observed-means table rows). Fails loudly on mismatch."""
    sys.path.insert(0, str(ROOT))
    from pipeline.metrics_dashboard import compute_rich_metrics

    check_website = WEBSITE_JSON.is_dir()
    lines, mean_rows = [], []
    worst = 0.0
    for sector in SECTORS:
        judged = _read_judged(sector)
        ref = compute_rich_metrics(JUDGED_DIR / f"{sector}_judged.json.gz")
        cx_of = {q["query_id"]: q["complexity"] for q in judged}
        if check_website:
            with open(WEBSITE_JSON / f"{sector}_metrics.json", encoding="utf-8") as f:
                site_all = json.load(f)
                site = site_all["recall_by_cx"]
                site_rich = site_all["rich"]
        csv_rows = list(csv.DictReader(
            open(AGGREGATES_DIR / f"{sector}_aggregated.csv", encoding="utf-8")))
        for eng in [QUISSLY] + COMPARATORS:
            mine = data[sector][eng]
            # precision vs aggregated CSV (query-weighted mean over complexity rows)
            rows = [r for r in csv_rows if r["Engine Name"] == eng]
            n_tot = sum(int(r["Query Count"]) for r in rows)
            for col, key in (("Precision@10 (%)", "precision_at_10"),
                             ("Precision@20 (%)", "precision_at_20")):
                reported = sum(float(r[col]) * int(r["Query Count"]) for r in rows) / n_tot
                ours = np.mean(list(mine[key].values())) * 100
                worst = max(worst, abs(ours - reported))
                assert abs(ours - reported) < 0.05, \
                    f"{sector}/{eng}/{key}: ours {ours:.3f} vs CSV {reported:.3f}"
            # recall@20 vs this repo's pipeline (unrounded). The ndcg-vs-
            # pipeline check was retired when pipeline/metrics_dashboard.py
            # moved to pooled-ideal nDCG (release final pass): this script's
            # ndcg deliberately keeps the superseded self-normalized
            # definition and is still cross-checked against the website
            # bundle per complexity band below.
            for key, mval in (("recall", "recall_at_20"),):
                ours = np.mean(list(mine[mval].values())) * 100
                worst = max(worst, abs(ours - ref[eng][key]))
                assert abs(ours - ref[eng][key]) < 1e-6, \
                    f"{sector}/{eng}/{mval}: ours {ours:.6f} vs pipeline {ref[eng][key]:.6f}"
            if check_website:
                # ndcg@10/@20 vs the published website bundle, per complexity band
                for k in (10, 20):
                    per_cx = defaultdict(list)
                    for qid, v in mine[f"ndcg_at_{k}"].items():
                        per_cx[cx_of[qid]].append(v)
                    for cx, vals in per_cx.items():
                        ours = np.mean(vals) * 100
                        pub = site_rich[eng][f"ndcg{k}_by_cx"][cx]
                        worst = max(worst, abs(ours - pub["rate"]))
                        assert len(vals) == pub["n"] and abs(ours - pub["rate"]) < 1e-6, \
                            (f"{sector}/{eng}/ndcg_at_{k}/{cx}: ours {ours:.6f} "
                             f"(n={len(vals)}) vs website {pub['rate']:.6f} (n={pub['n']})")
                # recall@10/@20 vs the published website bundle, per complexity
                # band. marketplace + pharmacy recall changed under the
                # normalized-pool correction (see analysis/id_overlap_check/
                # ID_OVERLAP_REPORT.md), so for those sectors the pre-correction
                # bundle values only gate the population n, not the rate.
                for k in (10, 20):
                    per_cx = defaultdict(list)
                    for qid, v in mine[f"recall_at_{k}"].items():
                        per_cx[cx_of[qid]].append(v)
                    for cx, vals in per_cx.items():
                        ours = np.mean(vals) * 100
                        pub = site[eng][str(k)][cx]
                        assert len(vals) == pub["n"], \
                            (f"{sector}/{eng}/recall_at_{k}/{cx}: n={len(vals)} "
                             f"vs website n={pub['n']}")
                        if sector in ("marketplace", "pharmacy"):
                            continue
                        worst = max(worst, abs(ours - pub["rate"]))
                        assert abs(ours - pub["rate"]) < 1e-6, \
                            (f"{sector}/{eng}/recall_at_{k}/{cx}: ours {ours:.6f} "
                             f"(n={len(vals)}) vs website {pub['rate']:.6f} (n={pub['n']})")
            mean_rows.append([sector, DISPLAY[eng]] + [
                f"{np.mean(list(mine[m].values())) * 100:.2f}" for m in METRICS])
    site_note = ("recall@10/@20 + nDCG@10/@20 match the published website "
                 "bundle exactly per complexity band"
                 if check_website else
                 "website bundle not found next to this repo — website "
                 "validation skipped")
    lines.append(f"All per-query means reproduce the reported aggregates: P@10/P@20 "
                 f"match the aggregates CSVs, recall@20 matches this repo's "
                 f"pipeline exactly (normalized pools; the pipeline's nDCG is "
                 f"now pooled-ideal so the self-norm nDCG here is checked "
                 f"against the website bundle only), and {site_note} "
                 f"(worst deviation {worst:.4f} pp).")
    return lines, mean_rows


def paired_diffs(data, sector_list, vendor, metric):
    """Aligned per-query diff vector (Quissly minus vendor) and per-engine means."""
    d, q_vals, v_vals = [], [], []
    for sector in sector_list:
        sq = data[sector][QUISSLY][metric]
        sv = data[sector][vendor][metric]
        qids = sorted(set(sq) & set(sv))
        assert len(qids) == len(sq) == len(sv), \
            f"unpaired queries in {sector}/{vendor}/{metric}"
        for qid in qids:
            d.append(sq[qid] - sv[qid])
            q_vals.append(sq[qid])
            v_vals.append(sv[qid])
    return (np.array(d), float(np.mean(q_vals)), float(np.mean(v_vals)))


def main():
    data = load_all()
    sanity_lines, mean_rows = sanity_check(data)
    print("\n".join(sanity_lines))

    rng = np.random.default_rng(SEED)
    cells = []
    # Fixed deterministic order: metric -> pairing -> sectors then pooled.
    for metric in METRICS:
        for vendor in COMPARATORS:
            for sector in SECTORS + ["pooled"]:
                sector_list = SECTORS if sector == "pooled" else [sector]
                diffs, q_mean, v_mean = paired_diffs(data, sector_list, vendor, metric)
                n = len(diffs)
                idx = rng.integers(0, n, size=(N_REPLICATES, n))
                boot = diffs[idx].mean(axis=1)
                ci_low, ci_high = np.percentile(boot, [2.5, 97.5])
                p_raw = min(1.0, 2 * min((boot <= 0).mean(), (boot >= 0).mean()))
                cells.append({
                    "metric": metric, "sector": sector,
                    "vendor_pair": f"quissly_vs_{vendor}",
                    "quissly_mean": q_mean, "other_mean": v_mean,
                    "observed_diff": float(diffs.mean()),
                    "ci_low": float(ci_low), "ci_high": float(ci_high),
                    "p_raw": p_raw, "n_queries": n,
                    "n_replicates": N_REPLICATES, "seed": SEED,
                })

    # Holm-Bonferroni over the full family.
    m = len(cells)
    order = sorted(range(m), key=lambda i: cells[i]["p_raw"])
    running = 0.0
    for rank, i in enumerate(order):
        running = max(running, (m - rank) * cells[i]["p_raw"])
        cells[i]["p_holm"] = min(1.0, running)
    for c in cells:
        c["significant_after_holm"] = c["p_holm"] < ALPHA
        c["within_noise"] = (not c["significant_after_holm"]) or \
            (c["ci_low"] <= 0 <= c["ci_high"])

    df = pd.DataFrame(cells)[[
        "metric", "sector", "vendor_pair", "quissly_mean", "other_mean",
        "observed_diff", "ci_low", "ci_high", "p_raw", "p_holm",
        "significant_after_holm", "within_noise", "n_queries",
        "n_replicates", "seed"]]

    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%SZ")
    out_dir = Path(__file__).resolve().parent / ts
    out_dir.mkdir(parents=True, exist_ok=False)
    csv_path = out_dir / "bootstrap_results.csv"
    df.to_csv(csv_path, index=False, float_format="%.6f")

    md_path = out_dir / "summary.md"
    md_path.write_text(build_summary(df, sanity_lines, mean_rows, m, ts),
                       encoding="utf-8")
    print(f"CSV: {csv_path}")
    print(f"Summary: {md_path}")


def fmt_row(r):
    star = "" if r.significant_after_holm else " (within noise)"
    return (f"{r.metric}, {r.sector}, vs {DISPLAY[r.vendor_pair.split('_vs_')[1]]}: "
            f"+{r.observed_diff * 100:.2f} pp [{r.ci_low * 100:.2f}, "
            f"{r.ci_high * 100:.2f}], p_holm={r.p_holm:.4g}{star}")


def build_summary(df, sanity_lines, mean_rows, family_size, ts):
    sig = df[df.significant_after_holm]
    noise = df[~df.significant_after_holm | ((df.ci_low <= 0) & (df.ci_high >= 0))]
    lines = [
        f"# Paired bootstrap significance — Quissly vs competitors ({ts})",
        "",
        f"- Data: `comparison_final_judged/judged/<sector>_judged.json.gz` "
        f"(read-only), 7 sectors, 1,259 paired queries pooled (furniture has "
        f"179, not 180).",
        f"- Pairings: Quissly vs {', '.join(DISPLAY[v] for v in COMPARATORS)} "
        f"(the 5 compared engines; the recall pool is their union, matching "
        f"this repo's pipeline and the published /compare bundle).",
        f"- Metrics: precision@10/@20 (persisted per-query scalars), pooled "
        f"recall@10/@20 and nDCG@10/@20 (derived per query from persisted "
        f"per-hit judgments with the pipeline's exact formulas; both cutoffs "
        f"of recall and nDCG are published on the website's /compare page). "
        f"Recall excludes queries whose pool is empty (see n_queries per "
        f"cell), same as the pipeline.",
        f"- Method: paired bootstrap on per-query differences (Quissly minus "
        f"vendor), resampling whole queries with replacement, B={N_REPLICATES:,}, "
        f"seed={SEED} (numpy default_rng, fixed cell order). 95% CI = 2.5/97.5 "
        f"percentiles. Two-sided empirical p; p_raw=0 means no replicate crossed "
        f"zero (p < {2 / N_REPLICATES}).",
        f"- Multiple comparisons: Holm-Bonferroni across the full family of "
        f"**{family_size} tests** (6 metrics x 4 pairings x [7 sectors + pooled]). "
        f"Significance threshold alpha={ALPHA}.",
        f"- Environment: Python {sys.version.split()[0]}, numpy "
        f"{np.__version__}, pandas {pd.__version__}.",
        "",
        "## Sanity check",
        "",
        *sanity_lines,
        "",
        "## Headline",
        "",
        f"**{len(sig)} of {family_size} comparisons are significant after Holm "
        f"correction; {family_size - len(sig)} are not.** "
        f"{int((df.observed_diff > 0).sum())} of {family_size} observed "
        f"differences favor Quissly.",
        "",
        "### Pooled (all sectors) results",
        "",
    ]
    pooled = df[df.sector == "pooled"].sort_values(["metric", "vendor_pair"])
    lines += [f"- {fmt_row(r)}" for r in pooled.itertuples()]
    lines += ["", "## Narrowest significant margins (10 smallest observed diffs "
              "that survived Holm)", ""]
    lines += [f"- {fmt_row(r)}"
              for r in sig.nsmallest(10, "observed_diff").itertuples()]
    lines += ["", f"## Within noise ({len(noise)} cells: not significant after "
              "Holm, or CI crosses zero)", ""]
    if noise.empty:
        lines.append("None — every comparison survived correction.")
    else:
        lines += [f"- {fmt_row(r)}"
                  for r in noise.sort_values(["metric", "sector", "vendor_pair"])
                  .itertuples()]
    lines += ["", "## Observed per-engine means (sanity-check against reported "
              "aggregates, %)", "",
              "| Sector | Engine | P@10 | P@20 | R@10 | R@20 | nDCG@10 | nDCG@20 |",
              "|---|---|---|---|---|---|---|---|"]
    lines += ["| " + " | ".join(r) + " |" for r in mean_rows]
    lines.append("")
    return "\n".join(lines)


if __name__ == "__main__":
    main()
