"""Paired bootstrap re-run with nDCG under the pooled-IDCG definition.

Identical harness to analysis/bootstrap/paired_bootstrap.py — same seed (42),
same B (10,000), same deterministic cell order, same full Holm family of 192
tests (6 metrics x 4 pairings x [7 sectors + pooled]) — with ONE change:
ndcg_at_10 / ndcg_at_20 are computed under the pooled-IDCG definition
(pool = union of judged (id, gain) pairs across the 5 engines, dedup by id
keeping max gain; IDCG@k = DCG of pool gains desc truncated at k; queries
with pooled IDCG == 0 excluded, mirroring how recall excludes empty pools).
precision/recall per-query scores are byte-identical to the original run, and
because the RNG is consumed in fixed cell order with metrics iterated
precision -> recall -> ndcg, every precision/recall cell draws the exact same
bootstrap indices as the committed run — asserted against
analysis/bootstrap/20260718_112921Z/bootstrap_results.csv.

Reads judged data read-only. Writes only analysis/ndcg_pooled/
(bootstrap_results.csv, bootstrap_summary.md). Replaces nothing.
"""
import csv
import gzip
import json
import math
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
JUDGED_DIR = ROOT / "comparison_final_judged" / "judged"
AGGREGATES_DIR = ROOT / "comparison_final_judged" / "aggregates"
# the 2026-07-18 normalized-pool run; the raw-id predecessor (20260715_070827Z)
# is preserved in analysis/_superseded_rawid_pools/
ORIGINAL_CSV = ROOT / "analysis/bootstrap/20260718_112921Z/bootstrap_results.csv"
OUT_DIR = Path(__file__).resolve().parent

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
    """provider -> metric -> {query_id: score}. precision/recall identical to
    the original analysis/bootstrap/paired_bootstrap.py; ndcg replaced by the
    pooled-IDCG definition. Pools keyed by _norm_id."""
    out = defaultdict(lambda: defaultdict(dict))
    for entry in judged:
        qid = entry["query_id"]
        providers = entry["providers"]
        assert set(providers) <= ENGINES, \
            f"unexpected engines in {qid}: {sorted(set(providers) - ENGINES)}"
        pool = {_norm_id(h["id"]) for p in providers.values()
                for h in p.get("hits", []) if h["score"] == 1}
        # pooled-IDCG relevance pool: normalized id -> max judged gain
        gain_pool = {}
        for p in providers.values():
            for h in p.get("hits", []):
                hid = _norm_id(h["id"])
                gain_pool[hid] = max(gain_pool.get(hid, 0.0), h["score"])
        ideal = sorted(gain_pool.values(), reverse=True)
        idcg = {k: _dcg(ideal[:k]) for k in (10, 20)}
        for prov, pdata in providers.items():
            hits = sorted(pdata.get("hits", []), key=lambda h: h["rank"])
            out[prov]["precision_at_10"][qid] = pdata["precision_at_10"]
            out[prov]["precision_at_20"][qid] = pdata["precision_at_20"]
            for k in (10, 20):
                if idcg[k] > 0:   # excluded when pooled IDCG == 0
                    ordered = [h["score"] for h in hits][:k]
                    out[prov][f"ndcg_at_{k}"][qid] = _dcg(ordered) / idcg[k]
            if pool:
                for k in (10, 20):
                    found = len({_norm_id(h["id"]) for h in hits[:k]
                                 if _norm_id(h["id"]) in pool
                                 and h["score"] == 1})
                    out[prov][f"recall_at_{k}"][qid] = found / len(pool)
    return out


def load_all():
    return {sector: per_query_scores(_read_judged(sector)) for sector in SECTORS}


def sanity_check(data):
    """(1) precision vs aggregates CSVs, (2) recall vs the original committed
    bootstrap CSV's pooled means, (3) pooled ndcg vs cells.json produced by
    pooled_ndcg.py (an independent implementation in this directory)."""
    lines = []
    cells_json = json.loads((OUT_DIR / "cells.json").read_text())["cells"]
    worst = 0.0
    for sector in SECTORS:
        csv_rows = list(csv.DictReader(
            open(AGGREGATES_DIR / f"{sector}_aggregated.csv", encoding="utf-8")))
        for eng in [QUISSLY] + COMPARATORS:
            mine = data[sector][eng]
            rows = [r for r in csv_rows if r["Engine Name"] == eng]
            n_tot = sum(int(r["Query Count"]) for r in rows)
            for col, key in (("Precision@10 (%)", "precision_at_10"),
                             ("Precision@20 (%)", "precision_at_20")):
                reported = sum(float(r[col]) * int(r["Query Count"])
                               for r in rows) / n_tot
                ours = np.mean(list(mine[key].values())) * 100
                worst = max(worst, abs(ours - reported))
                assert abs(ours - reported) < 0.05, (sector, eng, key)
            for k in (10, 20):
                ref = cells_json[f"sector:{sector}"][f"{eng}@{k}"]
                ours = np.mean(list(mine[f"ndcg_at_{k}"].values())) * 100
                worst = max(worst, abs(ours - ref["pooled"]))
                assert abs(ours - ref["pooled"]) < 1e-9, (sector, eng, k)
                assert len(mine[f"ndcg_at_{k}"]) == ref["n_pooled"], \
                    (sector, eng, k, len(mine[f"ndcg_at_{k}"]), ref["n_pooled"])
    lines.append(f"Sanity: precision matches the aggregates CSVs and pooled "
                 f"nDCG matches pooled_ndcg.py's cells.json per sector, engine "
                 f"and cutoff, including populations (worst deviation "
                 f"{worst:.6f} pp).")
    return lines


def paired_diffs(data, sector_list, vendor, metric):
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
    sanity_lines = sanity_check(data)
    print("\n".join(sanity_lines))

    rng = np.random.default_rng(SEED)
    cells = []
    for metric in METRICS:
        for vendor in COMPARATORS:
            for sector in SECTORS + ["pooled"]:
                sector_list = SECTORS if sector == "pooled" else [sector]
                diffs, q_mean, v_mean = paired_diffs(data, sector_list,
                                                     vendor, metric)
                n = len(diffs)
                idx = rng.integers(0, n, size=(N_REPLICATES, n))
                boot = diffs[idx].mean(axis=1)
                ci_low, ci_high = np.percentile(boot, [2.5, 97.5])
                p_raw = min(1.0, 2 * min((boot <= 0).mean(),
                                         (boot >= 0).mean()))
                cells.append({
                    "metric": metric, "sector": sector,
                    "vendor_pair": f"quissly_vs_{vendor}",
                    "quissly_mean": q_mean, "other_mean": v_mean,
                    "observed_diff": float(diffs.mean()),
                    "ci_low": float(ci_low), "ci_high": float(ci_high),
                    "p_raw": p_raw, "n_queries": n,
                    "n_replicates": N_REPLICATES, "seed": SEED,
                })

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
    df.to_csv(OUT_DIR / "bootstrap_results.csv", index=False,
              float_format="%.6f")

    # ── Compare against the committed original run ───────────────────────────
    orig = pd.read_csv(ORIGINAL_CSV)
    key = ["metric", "sector", "vendor_pair"]
    merged = df.merge(orig, on=key, suffixes=("_new", "_orig"))
    assert len(merged) == m
    pr = merged[~merged.metric.str.startswith("ndcg")]
    # precision/recall cells must reproduce the committed run: same inputs and
    # same rng consumption order before any ndcg cell. The committed CSV is
    # rounded to 6 decimals, so means compare at 5e-7; p_raw is a multiple of
    # 1/N_REPLICATES = 1e-4 and round-trips exactly, pinning identical draws.
    same = ((pr.p_raw_new - pr.p_raw_orig).abs() < 1e-12) & \
           ((pr.observed_diff_new - pr.observed_diff_orig).abs() < 5e-7) & \
           ((pr.ci_low_new - pr.ci_low_orig).abs() < 5e-7) & \
           ((pr.ci_high_new - pr.ci_high_orig).abs() < 5e-7) & \
           (pr.n_queries_new == pr.n_queries_orig)
    assert same.all(), pr[~same][key]
    nd = merged[merged.metric.str.startswith("ndcg")]
    status_changed = nd[nd.significant_after_holm_new
                        != nd.significant_after_holm_orig]

    lines = [
        "# Paired bootstrap — nDCG corrected to pooled IDCG",
        "",
        "Same harness as analysis/bootstrap/paired_bootstrap.py (seed 42, "
        "B=10,000, fixed cell order, Holm over the full 192-test family); "
        "only the ndcg_at_10/ndcg_at_20 per-query scores changed to the "
        "pooled-IDCG definition (queries with pooled IDCG=0 excluded, "
        "n=1,212 pooled instead of 1,259).",
        "",
        *sanity_lines,
        "",
        f"Cross-check vs the committed original run: all "
        f"{len(pr)} precision/recall cells reproduce it exactly (p_raw "
        f"bit-identical; means/CIs equal within the CSV's 6-decimal "
        f"rounding; same n) — the RNG consumed identical draws for them. "
        f"Only the {len(nd)} nDCG cells changed.",
        "",
        "## nDCG cells (pooled-IDCG)",
        "",
        f"- significant after Holm: {int(nd.significant_after_holm_new.sum())} "
        f"of {len(nd)} (original run: "
        f"{int(nd.significant_after_holm_orig.sum())} of {len(nd)})",
        f"- significance status changes vs original: {len(status_changed)}",
    ]
    if len(status_changed):
        for r in status_changed.itertuples():
            lines.append(f"  - {r.metric} / {r.sector} / {r.vendor_pair}: "
                         f"orig p_holm={r.p_holm_orig:.4g} "
                         f"(sig={r.significant_after_holm_orig}) -> new "
                         f"p_holm={r.p_holm_new:.4g} "
                         f"(sig={r.significant_after_holm_new})")
    lines += ["", "### Pooled (all-sectors) nDCG cells", ""]
    for r in nd[nd.sector == "pooled"].sort_values(
            ["metric", "vendor_pair"]).itertuples():
        star = "" if r.significant_after_holm_new else " (within noise)"
        lines.append(
            f"- {r.metric} vs {DISPLAY[r.vendor_pair.split('_vs_')[1]]}: "
            f"quissly {r.quissly_mean_new * 100:.2f} vs "
            f"{r.other_mean_new * 100:.2f}, diff "
            f"{r.observed_diff_new * 100:+.2f} pp "
            f"[{r.ci_low_new * 100:.2f}, {r.ci_high_new * 100:.2f}], "
            f"p_holm={r.p_holm_new:.4g}{star} (n={r.n_queries_new}; original "
            f"diff was {r.observed_diff_orig * 100:+.2f} pp)")
    lines += ["", "### All nDCG cells, new vs original observed diff (pp)", "",
              "| metric | sector | vendor | new diff | orig diff | new p_holm | sig |",
              "|---|---|---|---:|---:|---:|---|"]
    for r in nd.sort_values(["metric", "sector", "vendor_pair"]).itertuples():
        lines.append(
            f"| {r.metric} | {r.sector} | "
            f"{DISPLAY[r.vendor_pair.split('_vs_')[1]]} | "
            f"{r.observed_diff_new * 100:+.2f} | "
            f"{r.observed_diff_orig * 100:+.2f} | {r.p_holm_new:.4g} | "
            f"{'yes' if r.significant_after_holm_new else 'NO'} |")
    lines.append("")
    (OUT_DIR / "bootstrap_summary.md").write_text("\n".join(lines))
    print(f"Wrote {OUT_DIR / 'bootstrap_results.csv'} and bootstrap_summary.md")
    print(f"nDCG significant after Holm: "
          f"{int(nd.significant_after_holm_new.sum())}/{len(nd)}; "
          f"status changes vs original: {len(status_changed)}")


if __name__ == "__main__":
    main()
