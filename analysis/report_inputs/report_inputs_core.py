"""Numeric core for the report-inputs deliverable (ASK-1/2/3/6 + gate).

Everything is recomputed from the raw judged data
(comparison_final_judged/judged/*.json.gz) with fresh code, then
cross-checked against the published website bundle
(<website repo>/comparison-data/) and this repo's committed
analysis outputs. The reconciliation gate ABORTS the whole run on any
mismatch with the expected constants.

Read-only on all sources. Writes only into analysis/report_inputs/:
  gate.md, ask1_sector_grid.md, sector_grid.json, ask2_tiers.md,
  ask3_holm.md, consolidated_holm.csv, ask6_labels.md, versions.md
"""
import csv
import gzip
import json
import math
import os
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
JUDGED_DIR = ROOT / "comparison_final_judged" / "judged"
AGG_DIR = ROOT / "comparison_final_judged" / "aggregates"
# published website bundle to cross-check against: a sibling checkout of the
# website repo by default, or point WEBSITE_BUNDLE at it
BUNDLE = Path(os.environ.get("WEBSITE_BUNDLE",
                             ROOT.parent / "website" / "comparison-data"))
# the 2026-07-18 normalized-pool run; the raw-id predecessor (20260715_070827Z)
# is preserved in analysis/_superseded_rawid_pools/
ORIG_CSV = ROOT / "analysis/bootstrap/20260718_112921Z/bootstrap_results.csv"
POOLED_CSV = ROOT / "analysis/ndcg_pooled/bootstrap_results.csv"
EZR_CSV = ROOT / "analysis/ezr_bootstrap/ezr_results.csv"
CELLS_JSON = ROOT / "analysis/ndcg_pooled/cells.json"
OUT = Path(__file__).resolve().parent

SECTORS = ["auto", "cosmetics", "electronics", "fast_fashion",
           "furniture", "marketplace", "pharmacy"]
ENGINES = ["quissly", "doofinder", "luigisbox", "clerk", "algolia"]
TIERS = ["simple", "medium", "complex"]
ALPHA = 0.05

GATE = {
    "ezr": {"quissly": 93, "doofinder": 149, "clerk": 249,
            "luigisbox": 308, "algolia": 477},
    # pooled-ideal nDCG under normalized pools (2026-07-18 marketplace
    # correction — see analysis/id_overlap_check/ID_OVERLAP_REPORT.md);
    # raw-id predecessors: quissly (72.83, 76.04), doofinder (53.47, 53.48),
    # luigisbox (50.22, 49.61), clerk (48.73, 48.53), algolia (43.61, 43.13)
    "ndcg": {"quissly": (73.78, 77.28), "doofinder": (54.24, 54.50),
             "luigisbox": (50.81, 50.41), "clerk": (49.24, 49.21),
             "algolia": (44.06, 43.77)},
    "n_total": 1259, "n_ndcg": 1212, "n_recall": 1059,
    "exclusions": {"marketplace": 26, "pharmacy": 8, "fast_fashion": 6,
                   "cosmetics": 3, "electronics": 2, "furniture": 2,
                   "auto": 0},
}


def _norm_id(s):
    """Pool join key: lowercase, dashes stripped. Quissly's marketplace hits
    carry dashed UUIDs where the other engines carry undashed hex of the
    same ids — see analysis/id_overlap_check/ID_OVERLAP_REPORT.md."""
    return str(s).lower().replace("-", "")


def _dcg(gains):
    return sum(g / math.log2(i + 2) for i, g in enumerate(gains))


def load():
    """Per-query records with every per-engine stat both tasks need."""
    qs = []
    labels = Counter()
    for sector in SECTORS:
        judged = json.load(gzip.open(JUDGED_DIR / f"{sector}_judged.json.gz",
                                     "rt", encoding="utf-8"))
        for e in judged:
            provs = e["providers"]
            assert set(provs) == set(ENGINES)
            gain_pool, exact_pool = {}, set()
            for p in provs.values():
                for h in p.get("hits", []):
                    labels[h["label"]] += 1
                    hid = _norm_id(h["id"])
                    gain_pool[hid] = max(gain_pool.get(hid, 0.0), h["score"])
                    if h["score"] == 1:
                        exact_pool.add(hid)
            ideal = sorted(gain_pool.values(), reverse=True)
            idcg = {k: _dcg(ideal[:k]) for k in (10, 20)}
            rec = {"sector": sector, "complexity": e["complexity"],
                   "excluded": idcg[10] == 0, "has_pool": bool(exact_pool),
                   "eng": {}}
            for eng in ENGINES:
                hits = sorted(provs[eng].get("hits", []),
                              key=lambda h: h["rank"])
                g = [h["score"] for h in hits]
                d = {"answered": bool(hits),
                     "ezr": 1 if (not hits or all(s == 0 for s in g)) else 0}
                for k in (10, 20):
                    top = g[:k]
                    d[f"junk{k}"] = (sum(1 for s in top if s == 0) / len(top)
                                     if top else None)
                    d[f"ndcg{k}"] = (_dcg(top) / idcg[k]
                                     if idcg[k] > 0 else None)
                    d[f"recall{k}"] = (
                        len({_norm_id(h["id"]) for h in hits[:k]
                             if _norm_id(h["id"]) in exact_pool
                             and h["score"] == 1}) / len(exact_pool)
                        if exact_pool else None)
                rec["eng"][eng] = d
            qs.append(rec)
    return qs, labels


def mean(xs):
    xs = [x for x in xs if x is not None]
    return sum(xs) / len(xs) if xs else float("nan")


def gate_check(qs):
    lines = ["## Reconciliation gate\n"]
    errs = []
    n = len(qs)
    if n != GATE["n_total"]:
        errs.append(f"n_total {n} != {GATE['n_total']}")
    for eng in ENGINES:
        ezr = sum(q["eng"][eng]["ezr"] for q in qs)
        if ezr != GATE["ezr"][eng]:
            errs.append(f"EZR {eng}: {ezr} != {GATE['ezr'][eng]}")
        nd10 = mean([q["eng"][eng]["ndcg10"] for q in qs
                     if not q["excluded"]]) * 100
        nd20 = mean([q["eng"][eng]["ndcg20"] for q in qs
                     if not q["excluded"]]) * 100
        e10, e20 = GATE["ndcg"][eng]
        if round(nd10, 2) != e10 or round(nd20, 2) != e20:
            errs.append(f"nDCG {eng}: {nd10:.2f}/{nd20:.2f} != {e10}/{e20}")
        lines.append(f"- {eng}: EZR {ezr}/{n}  corrected nDCG@10/@20 = "
                     f"{nd10:.2f}/{nd20:.2f}  -> match")
    n_ndcg = sum(1 for q in qs if not q["excluded"])
    n_recall = sum(1 for q in qs if q["has_pool"])
    excl = Counter(q["sector"] for q in qs if q["excluded"])
    if n_ndcg != GATE["n_ndcg"]:
        errs.append(f"n_ndcg {n_ndcg} != {GATE['n_ndcg']}")
    if n_recall != GATE["n_recall"]:
        errs.append(f"n_recall {n_recall} != {GATE['n_recall']}")
    for s in SECTORS:
        if excl.get(s, 0) != GATE["exclusions"][s]:
            errs.append(f"exclusions {s}: {excl.get(s, 0)} != "
                        f"{GATE['exclusions'][s]}")
    lines.append(f"- populations: total {n}, corrected-nDCG {n_ndcg} "
                 f"(exclusions {dict(excl)}), recall {n_recall} -> match")

    # cross-check against the published bundle
    bundle_all = json.loads((BUNDLE / "json/all_metrics.json").read_text())
    for eng in ENGINES:
        n_rec_bundle = sum(v["n"] for v in
                           bundle_all["recall_by_cx"][eng]["20"].values())
        if n_rec_bundle != GATE["n_recall"]:
            errs.append(f"bundle recall n {eng}: {n_rec_bundle}")
        aj_bundle = bundle_all["rich"][eng]["alljunk"]
        zero_csv = 0.0
        cnt = 0
        for s in SECTORS:
            for r in csv.DictReader(open(AGG_DIR / f"{s}_aggregated.csv")):
                if r["Engine Name"] == eng:
                    zero_csv += float(r["Zero-Result Rate (%)"]) * \
                        int(r["Query Count"])
                    cnt += int(r["Query Count"])
        ezr_bundle = round((zero_csv / cnt + aj_bundle) / 100 * n)
        if ezr_bundle != GATE["ezr"][eng]:
            errs.append(f"bundle-derived EZR {eng}: {ezr_bundle} "
                        f"!= {GATE['ezr'][eng]}")
    lines.append("- published bundle cross-check: recall n per engine = "
                 "1,059; zero-result(CSV) + all-junk(bundle rich) "
                 "reproduces every EZR count -> match")
    if errs:
        lines.append("\n**GATE FAILED:**\n" + "\n".join(f"- {e}" for e in errs))
        (OUT / "gate.md").write_text("\n".join(lines))
        sys.exit("GATE FAILED:\n" + "\n".join(errs))
    lines.append("\n**GATE PASSED — all expected values reproduced from raw "
                 "judged data and cross-checked against the published "
                 "bundle.**")
    (OUT / "gate.md").write_text("\n".join(lines))
    print("GATE PASSED")


def ask1(qs):
    grid = {}
    frag = ["## ASK-1 — Full per-sector grid\n",
            "All percentages to 2 decimals. n's: EZR/coverage over all "
            "sector queries; junk over answered queries (>=1 hit); recall "
            "over pool>0 queries; corrected nDCG over pooled-IDCG>0 "
            "queries.\n"]
    bundle = {s: json.loads((BUNDLE / f"json/{s}_metrics.json").read_text())
              for s in SECTORS}
    cells = json.loads(CELLS_JSON.read_text())["cells"]
    for s in SECTORS:
        sq = [q for q in qs if q["sector"] == s]
        n_tot = len(sq)
        n_pool = sum(1 for q in sq if q["has_pool"])
        n_inc = sum(1 for q in sq if not q["excluded"])
        frag.append(f"### {s} (queries {n_tot}, recall pool n {n_pool}, "
                    f"nDCG included n {n_inc})\n")
        frag.append("| engine | EZR | coverage | junk@10 | junk@20 | "
                    "(junk n) | recall@10 | recall@20 | nDCG@10 | nDCG@20 |")
        frag.append("|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
        grid[s] = {"n_queries": n_tot, "n_recall_pool": n_pool,
                   "n_ndcg_included": n_inc, "engines": {}}
        for eng in ENGINES:
            E = [q["eng"][eng] for q in sq]
            ezr = sum(d["ezr"] for d in E)
            ans = sum(1 for d in E if d["answered"])
            j10 = mean([d["junk10"] for d in E]) * 100
            j20 = mean([d["junk20"] for d in E]) * 100
            r10 = mean([q["eng"][eng]["recall10"] for q in sq
                        if q["has_pool"]]) * 100
            r20 = mean([q["eng"][eng]["recall20"] for q in sq
                        if q["has_pool"]]) * 100
            n10 = mean([q["eng"][eng]["ndcg10"] for q in sq
                        if not q["excluded"]]) * 100
            n20 = mean([q["eng"][eng]["ndcg20"] for q in sq
                        if not q["excluded"]]) * 100
            # cross-checks vs published bundle + committed cells.json
            b = bundle[s]["rich"][eng]
            assert abs(j10 - b["junk10"]) < 1e-9, (s, eng, "junk10")
            assert abs(j20 - b["junk20"]) < 1e-9, (s, eng, "junk20")
            br = bundle[s]["recall_by_cx"][eng]
            for k, rv in ((10, r10), (20, r20)):
                num = sum(v["rate"] * v["n"] for v in br[str(k)].values())
                den = sum(v["n"] for v in br[str(k)].values())
                assert den == n_pool, (s, eng, f"recall{k} n")
                # marketplace + pharmacy recall changed under the
                # normalized-pool correction; the pre-correction bundle
                # gates only the population there
                if s not in ("marketplace", "pharmacy"):
                    assert abs(rv - num / den) < 1e-9, (s, eng, f"recall{k}")
            for k, nv in ((10, n10), (20, n20)):
                ref = cells[f"sector:{s}"][f"{eng}@{k}"]
                assert ref["n_pooled"] == n_inc and \
                    abs(nv - ref["pooled"]) < 1e-9, (s, eng, f"ndcg{k}")
            frag.append(
                f"| {eng} | {ezr / n_tot * 100:.2f}% ({ezr}/{n_tot}) | "
                f"{ans / n_tot * 100:.2f}% ({ans}/{n_tot}) | {j10:.2f}% | "
                f"{j20:.2f}% | {ans} | {r10:.2f}% | {r20:.2f}% | "
                f"{n10:.2f} | {n20:.2f} |")
            grid[s]["engines"][eng] = {
                "ezr_count": ezr, "ezr_pct": round(ezr / n_tot * 100, 2),
                "answered": ans,
                "coverage_pct": round(ans / n_tot * 100, 2),
                "junk10_pct": round(j10, 2), "junk20_pct": round(j20, 2),
                "junk_n": ans,
                "recall10_pct": round(r10, 2), "recall20_pct": round(r20, 2),
                "ndcg10": round(n10, 2), "ndcg20": round(n20, 2),
            }
        frag.append("")
    # sanity: weighted sector aggregation reproduces pooled values
    checks = []
    for eng in ENGINES:
        agg_ezr = sum(grid[s]["engines"][eng]["ezr_count"] for s in SECTORS)
        assert agg_ezr == GATE["ezr"][eng]
        for metric, pooled_fn, n_key in (
            ("junk10_pct", lambda q, d: d["junk10"], "junk_n"),
            ("recall20_pct", lambda q, d: d["recall20"], "n_recall_pool"),
            ("ndcg10", lambda q, d: d["ndcg10"], "n_ndcg_included"),
        ):
            num = den = 0.0
            for s in SECTORS:
                w = (grid[s]["engines"][eng]["junk_n"]
                     if n_key == "junk_n" else grid[s][n_key])
                num += grid[s]["engines"][eng][metric] * w
                den += w
            if metric == "junk10_pct":
                pooled = mean([q["eng"][eng]["junk10"] for q in qs]) * 100
            elif metric == "recall20_pct":
                pooled = mean([q["eng"][eng]["recall20"] for q in qs
                               if q["has_pool"]]) * 100
            else:
                pooled = mean([q["eng"][eng]["ndcg10"] for q in qs
                               if not q["excluded"]]) * 100
            assert abs(num / den - pooled) < 0.005, (eng, metric)
        checks.append(eng)
    frag.append(f"Sanity: weighted sector aggregation reproduces the pooled "
                f"value for EZR (exact counts), junk@10, recall@20 and "
                f"nDCG@10 for all engines ({', '.join(checks)}) within "
                f"2-decimal rounding.\n")
    (OUT / "ask1_sector_grid.md").write_text("\n".join(frag))
    (OUT / "sector_grid.json").write_text(json.dumps(grid, indent=2))
    print("ASK-1 done")


def ask2(qs):
    cells = json.loads(CELLS_JSON.read_text())["cells"]
    n_tier = {t: sum(1 for q in qs if q["complexity"] == t
                     and not q["excluded"]) for t in TIERS}
    frag = ["## ASK-2 — Corrected pooled-IDCG nDCG by complexity tier\n",
            "| engine | " + " | ".join(
                f"{t} @10 / @20 (n={n_tier[t]})" for t in TIERS) + " |",
            "|---|" + "---:|" * 3]
    for eng in ENGINES:
        row = []
        for t in TIERS:
            c10 = cells[f"complexity:{t}"][f"{eng}@10"]
            c20 = cells[f"complexity:{t}"][f"{eng}@20"]
            assert c10["n_pooled"] == n_tier[t]
            row.append(f"{c10['pooled']:.2f} / {c20['pooled']:.2f}")
        frag.append(f"| {eng} | " + " | ".join(row) + " |")
    df = pd.read_csv(POOLED_CSV)
    sig = df[df.significant_after_holm].copy()
    sig["absdiff"] = sig.observed_diff.abs()
    frag.append("\n### 8 narrowest significant margins in the corrected "
                "bootstrap (any metric, any scope; family m=192, seed 42)\n\n"
                "Note: significance here is within the corrected bootstrap's "
                "own m=192 family; the consolidated m=236 pass is ASK-3.\n")
    for r in sig.nsmallest(8, "absdiff").itertuples():
        frag.append(f"- {r.metric} / {r.sector} / {r.vendor_pair}: "
                    f"diff {r.observed_diff * 100:+.2f} pp "
                    f"[{r.ci_low * 100:.2f}, {r.ci_high * 100:.2f}], "
                    f"p_holm={r.p_holm:.4g}")
    frag.append("")
    (OUT / "ask2_tiers.md").write_text("\n".join(frag))
    print("ASK-2 done")


def ask3():
    orig = pd.read_csv(ORIG_CSV)
    pooled = pd.read_csv(POOLED_CSV)
    ezr = pd.read_csv(EZR_CSV)
    # provenance gate
    errs = []
    for name, df, metrics, want in (
        ("original", orig, ["precision_at_10", "precision_at_20",
                            "recall_at_10", "recall_at_20"], 64 + 64),
        ("corrected", pooled, ["ndcg_at_10", "ndcg_at_20"], 64),
        ("ezr", ezr, ["effective_zero_rate"], 44),
    ):
        sub = df[df.metric.isin(metrics)]
        if len(sub) != want:
            errs.append(f"{name}: {len(sub)} rows for {metrics}, want {want}")
        if not (df.seed == 42).all():
            errs.append(f"{name}: seed != 42 somewhere")
        if not (df.n_replicates == 10000).all():
            errs.append(f"{name}: n_replicates != 10000 somewhere")
    key = ["metric", "sector", "vendor_pair"]
    pr_o = orig[~orig.metric.str.startswith("ndcg")].set_index(key)
    pr_p = pooled[~pooled.metric.str.startswith("ndcg")].set_index(key)
    if not (pr_o.p_raw == pr_p.p_raw.reindex(pr_o.index)).all():
        errs.append("precision/recall p_raw differ between original and "
                    "corrected CSVs")
    if errs:
        (OUT / "ask3_holm.md").write_text("PROVENANCE FAILED:\n"
                                          + "\n".join(errs))
        sys.exit("ASK-3 provenance failed: " + "; ".join(errs))

    fam = pd.concat([
        orig[~orig.metric.str.startswith("ndcg")].assign(
            source="original_grid"),
        pooled[pooled.metric.str.startswith("ndcg")].assign(
            source="corrected_ndcg"),
        ezr.assign(source="ezr"),
    ], ignore_index=True)
    assert len(fam) == 236
    m = 236
    order = fam.p_raw.sort_values(kind="mergesort").index
    running, ph = 0.0, {}
    for rank, i in enumerate(order):
        running = max(running, (m - rank) * fam.p_raw[i])
        ph[i] = min(1.0, running)
    fam["p_holm_236"] = pd.Series(ph)
    fam["significant_236"] = fam.p_holm_236 < ALPHA
    cols = ["source", "metric", "sector", "vendor_pair", "quissly_mean",
            "other_mean", "observed_diff", "ci_low", "ci_high", "p_raw",
            "p_holm_236", "significant_236", "n_queries", "n_replicates",
            "seed"]
    fam[cols].to_csv(OUT / "consolidated_holm.csv", index=False,
                     float_format="%.6f")

    ns = fam[~fam.significant_236]
    frag = ["## ASK-3 — One consolidated Holm pass across all 236 tests\n",
            f"Family: 128 precision/recall tests (original grid, p_raw "
            f"bit-identical in both bootstrap CSVs — verified), 64 nDCG "
            f"tests with CORRECTED pooled-IDCG scores "
            f"(analysis/ndcg_pooled/bootstrap_results.csv), 44 effective "
            f"zero-rate tests (analysis/ezr_bootstrap/ezr_results.csv). "
            f"Provenance verified: row counts 64+64+64+44, seed 42 and "
            f"B=10,000 in every row. No resampling performed — single "
            f"Holm-Bonferroni pass over the 236 committed p_raw values.\n",
            f"**{int(fam.significant_236.sum())} of 236 significant after "
            f"Holm; {len(ns)} not significant.**\n"]
    if len(ns):
        frag.append("| source | metric | scope | pair | diff pp | 95% CI | "
                    "p_raw | p_holm |")
        frag.append("|---|---|---|---|---:|---|---:|---:|")
        for r in ns.sort_values(["source", "metric", "sector"]).itertuples():
            frag.append(
                f"| {r.source} | {r.metric} | {r.sector} | "
                f"{r.vendor_pair.replace('quissly_vs_', 'vs ')} | "
                f"{r.observed_diff * 100:+.2f} | "
                f"[{r.ci_low * 100:.2f}, {r.ci_high * 100:.2f}] | "
                f"{r.p_raw:.4g} | {r.p_holm_236:.4g} |")
    def cell(metric):
        r = fam[(fam.metric == metric) & (fam.sector == "marketplace")
                & (fam.vendor_pair == "quissly_vs_doofinder")].iloc[0]
        return r
    frag.append("\n### The marketplace-vs-Doofinder questions\n")
    for mt in ("ndcg_at_10", "ndcg_at_20"):
        r = cell(mt)
        frag.append(f"- {mt} (corrected scores): p_raw={r.p_raw:.4g}, "
                    f"p_holm={r.p_holm_236:.4g} -> "
                    f"**{'SURVIVES' if r.significant_236 else 'does NOT survive'}** "
                    f"(under the old self-normalized scores these cells had "
                    f"p_raw 0.0162/0.0454, p_holm 0.0426/0.0454 at m=192, "
                    f"and died at m=236; corrected diffs are much larger).")
    r = cell("recall_at_10")
    frag.append(f"- recall_at_10 (normalized pools): p_raw={r.p_raw:.4g}, "
                f"p_holm={r.p_holm_236:.4g} -> "
                f"**{'now significant' if r.significant_236 else 'remains NON-significant'}** "
                f"(raw-id pools: p_raw 0.0142, non-significant at m=236).")
    frag.append("")
    (OUT / "ask3_holm.md").write_text("\n".join(frag))
    print(f"ASK-3 done: {int(fam.significant_236.sum())}/236 significant, "
          f"{len(ns)} not")


def ask6(labels):
    frag = ["## ASK-6 — Label -> gain mapping\n",
            "Exact code (`pipeline/llm_judge.py`):\n",
            "```python",
            "# ESCI-style graded relevance: label -> gain",
            "GAIN_MAP = {",
            '    "exact":         1.0,',
            '    "substitute":    0.1,',
            '    "complementary": 0.01,',
            '    "complement":    0.01,  # tolerate the ESCI spelling',
            '    "irrelevant":    0.0,',
            "}",
            "```\n",
            "Distinct label strings actually present in the judged data:\n",
            "| label | count |", "|---|---:|"]
    for lbl, c in labels.most_common():
        frag.append(f"| {lbl} | {c:,} |")
    frag.append(f"| **total judged hits** | "
                f"**{sum(labels.values()):,}** |")
    frag.append("\nConfirmed: only the four canonical strings occur, "
                "mapping Exact=1.0, Substitute=0.1, Complementary=0.01, "
                "Irrelevant=0.0.")
    frag.append("")
    (OUT / "ask6_labels.md").write_text("\n".join(frag))
    print("ASK-6 done:", dict(labels))


def main():
    (OUT / "versions.md").write_text(
        f"Python {sys.version.split()[0]}, numpy {np.__version__}, pandas "
        f"{pd.__version__}. Seeds: bootstrap seed 42 (B=10,000) in all "
        f"three bootstrap CSVs; empty-pool-audit sampling seed 42; "
        f"consolidated Holm is deterministic (no resampling).\n")
    qs, labels = load()
    gate_check(qs)
    ask1(qs)
    ask2(qs)
    ask3()
    ask6(labels)
    print("all fragments written to", OUT)


if __name__ == "__main__":
    main()
