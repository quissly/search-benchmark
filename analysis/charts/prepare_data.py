"""Data prep + reconciliation gate for the report figures.

Recomputes every charted value from primary sources (judged data, cells.json,
the three bootstrap CSVs, sector_grid.json, audit.json), asserts each against
the expected values embedded in the figure specs, and only then writes
chart_data.json for the renderer. ANY mismatch aborts (charts must never
disagree with the published report). nDCG is NEVER sourced from the website
bundle (stale normalization); it comes only from analysis/ndcg_pooled/.

Writes: analysis/charts/chart_data.json, analysis/charts/reconciliation.md
"""
import csv
import gzip
import json
import math
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
JUDGED_DIR = ROOT / "comparison_final_judged" / "judged"
OUT = Path(__file__).resolve().parent

SECTORS = ["auto", "cosmetics", "electronics", "fast_fashion",
           "furniture", "marketplace", "pharmacy"]
TIERS = ["simple", "medium", "complex"]
ENGINES = ["quissly", "doofinder", "clerk", "luigisbox", "algolia"]  # canonical
CHECKS = []


def check(name, got, want, tol=0.005):
    """A value matches if it rounds to the expected 2dp value OR truncates to
    it (the report's tables truncate: e.g. computed 2.1053 is printed 2.10).
    Chart labels are 1dp, identical under either convention."""
    trunc = math.floor(got * 100) / 100
    ok = abs(got - want) <= tol
    ok_trunc = (not ok) and abs(trunc - want) < 1e-9
    CHECKS.append((name + (" [matches under truncation-to-2dp]"
                           if ok_trunc else ""), got, want, ok or ok_trunc))
    if not (ok or ok_trunc):
        print(f"FAIL {name}: computed {got:.4f} vs expected {want:.4f}")
    return ok or ok_trunc


EXP = {
    "ezr_pooled": {"quissly": 7.39, "doofinder": 11.83, "clerk": 19.78,
                   "luigisbox": 24.46, "algolia": 37.89},
    "ezr_tier": {  # simple / medium / complex
        "quissly": [2.10, 8.53, 13.65], "doofinder": [5.68, 13.86, 18.10],
        "clerk": [5.26, 21.75, 38.73], "luigisbox": [6.52, 17.91, 61.27],
        "algolia": [5.89, 30.91, 96.50]},
    "zero_tier": {
        "quissly": [0.21, 1.71, 11.11], "doofinder": [0.21, 0.00, 0.00],
        "clerk": [0.63, 0.21, 0.63], "luigisbox": [1.47, 5.12, 45.08],
        "algolia": [1.47, 23.45, 95.87]},
    "alljunk_tier": {
        "quissly": [1.89, 6.82, 2.54], "doofinder": [5.47, 13.86, 18.10],
        "clerk": [4.63, 21.54, 38.10], "luigisbox": [5.05, 12.79, 16.19],
        "algolia": [4.42, 7.46, 0.63]},
    # ndcg_tier / recall_tier / ndcg_forest updated 2026-07-18 for the
    # normalized-pool marketplace correction (see analysis/id_overlap_check/
    # ID_OVERLAP_REPORT.md); raw-id predecessors preserved in
    # analysis/_superseded_rawid_pools/charts/chart_data.json
    "ndcg_tier": {
        "quissly": [91.02, 65.93, 58.65], "doofinder": [72.39, 55.78, 23.53],
        "luigisbox": [70.64, 55.90, 12.17], "clerk": [66.57, 51.01, 19.46],
        "algolia": [67.54, 48.17, 1.16]},
    "recall_tier": {
        "quissly": [56.03, 71.59, 73.29], "doofinder": [42.38, 53.94, 23.20],
        "clerk": [40.21, 50.53, 17.00], "luigisbox": [41.44, 54.02, 8.43],
        "algolia": [41.01, 48.23, 0.50]},
    "ndcg_tier_n": [466, 448, 298],
    "recall_tier_n": [443, 361, 255],
    "ezr_forest": {"doofinder": 4.45, "clerk": 12.39, "luigisbox": 17.08,
                   "algolia": 30.50},
    "ndcg_forest_doofinder": 19.55,
    "audit_classes": {"partial": 35, "inconclusive": 7, "catalog-gap": 5,
                      "engines-missed": 3},
}


def tier_stats():
    """From judged data: per engine per tier: EZR%, zero%, alljunk%, n; and
    recall@20 per tier over pool>0 queries; pooled EZR."""
    agg = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
    recall = defaultdict(lambda: defaultdict(list))
    for sector in SECTORS:
        judged = json.load(gzip.open(JUDGED_DIR / f"{sector}_judged.json.gz",
                                     "rt", encoding="utf-8"))
        for e in judged:
            t = e["complexity"]
            # pools keyed by _norm_id (lowercase, dashes stripped): Quissly's
            # marketplace hits carry dashed UUIDs where the other engines
            # carry undashed hex of the same ids — see
            # analysis/id_overlap_check/ID_OVERLAP_REPORT.md
            pool = {str(h["id"]).lower().replace("-", "")
                    for p in e["providers"].values()
                    for h in p.get("hits", []) if h["score"] == 1}
            for eng in ENGINES:
                hits = sorted(e["providers"][eng].get("hits", []),
                              key=lambda h: h["rank"])[:20]
                g = [h["score"] for h in hits]
                zero = not hits
                alljunk = bool(hits) and all(x == 0 for x in g)
                agg[eng][t]["zero"].append(1.0 if zero else 0.0)
                agg[eng][t]["alljunk"].append(1.0 if alljunk else 0.0)
                agg[eng][t]["ezr"].append(1.0 if (zero or alljunk) else 0.0)
                if pool:
                    ids = [str(h["id"]).lower().replace("-", "")
                           for h in hits]
                    recall[eng][t].append(
                        len({i for i in ids if i in pool}) / len(pool))
    return agg, recall


def main():
    data = {}
    # palette (recorded from the website source; see MANIFEST)
    data["palette"] = {"quissly": "#6366f1", "doofinder": "#ef4444",
                       "algolia": "#f59e0b", "luigisbox": "#10b981",
                       "clerk": "#ec4899"}
    data["palette_source"] = ("../website/client/src/pages/comparison/"
                              "data.ts lines 28-32 (ENGINE_META)")
    data["display"] = {"quissly": "Quissly", "doofinder": "Doofinder",
                       "clerk": "Clerk.io", "luigisbox": "Luigi's Box",
                       "algolia": "Algolia"}

    # ── C1 / C2 primitives from judged data ─────────────────────────────────
    agg, recall = tier_stats()
    ezr_pooled, ezr_tier, zero_tier, alljunk_tier = {}, {}, {}, {}
    tier_n = {}
    for eng in ENGINES:
        all_ezr = [v for t in TIERS for v in agg[eng][t]["ezr"]]
        ezr_pooled[eng] = sum(all_ezr) / len(all_ezr) * 100
        check(f"C1 pooled EZR {eng}", ezr_pooled[eng],
              EXP["ezr_pooled"][eng])
        ezr_tier[eng], zero_tier[eng], alljunk_tier[eng] = [], [], []
        for i, t in enumerate(TIERS):
            n = len(agg[eng][t]["ezr"])
            tier_n[t] = n
            for store, key, exp in ((ezr_tier, "ezr", "ezr_tier"),
                                    (zero_tier, "zero", "zero_tier"),
                                    (alljunk_tier, "alljunk", "alljunk_tier")):
                v = sum(agg[eng][t][key]) / n * 100
                store[eng].append(v)
                check(f"C1/C2 {key} {eng} {t}", v, EXP[exp][eng][i])
    assert tier_n == {"simple": 475, "medium": 469, "complex": 315}, tier_n
    data["ezr_pooled"] = ezr_pooled
    data["ezr_tier"] = ezr_tier
    data["zero_tier"] = zero_tier
    data["alljunk_tier"] = alljunk_tier
    data["tier_n"] = tier_n

    # ── C3 from cells.json (NEVER the website bundle) ───────────────────────
    cells = json.loads((ROOT / "analysis/ndcg_pooled/cells.json").read_text())
    ndcg_tier, ndcg_n = {}, []
    for i, t in enumerate(TIERS):
        c = cells["cells"][f"complexity:{t}"]
        ndcg_n.append(c["quissly@10"]["n_pooled"])
        for eng in ENGINES:
            v = c[f"{eng}@10"]["pooled"]
            ndcg_tier.setdefault(eng, []).append(v)
            check(f"C3 nDCG {eng} {t}", v, EXP["ndcg_tier"][eng][i])
    for i, t in enumerate(TIERS):
        check(f"C3 n {t}", ndcg_n[i], EXP["ndcg_tier_n"][i], tol=0)
    data["ndcg_tier"] = ndcg_tier
    data["ndcg_tier_n"] = ndcg_n

    # ── C4 recall by tier ────────────────────────────────────────────────────
    recall_tier, recall_n = {}, []
    for i, t in enumerate(TIERS):
        ns = {len(recall[eng][t]) for eng in ENGINES}
        assert len(ns) == 1
        recall_n.append(ns.pop())
        check(f"C4 n {t}", recall_n[i], EXP["recall_tier_n"][i], tol=0)
        for eng in ENGINES:
            v = sum(recall[eng][t]) / len(recall[eng][t]) * 100
            recall_tier.setdefault(eng, []).append(v)
            check(f"C4 recall {eng} {t}", v, EXP["recall_tier"][eng][i])
    data["recall_tier"] = recall_tier
    data["recall_tier_n"] = recall_n

    # ── C5 forest from the three CSVs ───────────────────────────────────────
    forest = {"ezr": {}, "ndcg": {}, "recall": {}}
    for r in csv.DictReader(open(ROOT / "analysis/ezr_bootstrap/"
                                 "ezr_results.csv")):
        if r["sector"] != "pooled":
            continue
        v = r["vendor_pair"].split("_vs_")[1]
        # EZR: advantage = rival minus Quissly = -(observed_diff)
        forest["ezr"][v] = {
            "adv": -float(r["observed_diff"]) * 100,
            "lo": -float(r["ci_high"]) * 100, "hi": -float(r["ci_low"]) * 100}
        check(f"C5 EZR adv {v}", forest["ezr"][v]["adv"],
              EXP["ezr_forest"][v])
    for r in csv.DictReader(open(ROOT / "analysis/ndcg_pooled/"
                                 "bootstrap_results.csv")):
        if r["sector"] != "pooled" or r["metric"] != "ndcg_at_10":
            continue
        v = r["vendor_pair"].split("_vs_")[1]
        forest["ndcg"][v] = {
            "adv": float(r["observed_diff"]) * 100,
            "lo": float(r["ci_low"]) * 100, "hi": float(r["ci_high"]) * 100}
    check("C5 nDCG adv doofinder", forest["ndcg"]["doofinder"]["adv"],
          EXP["ndcg_forest_doofinder"])
    # the 2026-07-18 normalized-pool run; the raw-id predecessor
    # (20260715_070827Z) is preserved in analysis/_superseded_rawid_pools/
    committed = ROOT / "analysis/bootstrap/20260718_112921Z/bootstrap_results.csv"
    for r in csv.DictReader(open(committed)):
        if r["sector"] != "pooled" or r["metric"] != "recall_at_20":
            continue
        v = r["vendor_pair"].split("_vs_")[1]
        forest["recall"][v] = {
            "adv": float(r["observed_diff"]) * 100,
            "lo": float(r["ci_low"]) * 100, "hi": float(r["ci_high"]) * 100}
    for metric, rows in forest.items():
        assert set(rows) == {"doofinder", "clerk", "luigisbox", "algolia"}
        for v, d in rows.items():
            ok = d["lo"] > 0
            CHECKS.append((f"C5 {metric} vs {v} CI clears zero "
                           f"[{d['lo']:.2f}, {d['hi']:.2f}]",
                           d["lo"], 0.0, ok))
            if not ok:
                print(f"FAIL C5 {metric} {v}: CI does not clear zero")
    data["forest"] = forest
    data["forest_recall_source"] = str(committed.relative_to(ROOT))

    # ── C6 heatmap from sector_grid.json, reconciled vs REPORT_INPUTS.md ────
    grid = json.loads((ROOT / "analysis/report_inputs/"
                       "sector_grid.json").read_text())
    md = (ROOT / "analysis/report_inputs/REPORT_INPUTS.md").read_text()
    heat = {"ezr": {}, "ndcg": {}}
    for s in SECTORS:
        heat["ezr"][s] = {e: grid[s]["engines"][e]["ezr_pct"]
                          for e in ENGINES}
        heat["ndcg"][s] = {e: grid[s]["engines"][e]["ndcg10"]
                           for e in ENGINES}
        # reconcile every cell against the ASK-1 markdown tables:
        # rows look like: | quissly | 0.00% (0/180) | ... | 80.06 | 82.74 |
        sec = re.search(rf"### {s} \(queries.*?\n\n(.*?)\n\n", md, re.DOTALL)
        assert sec, s
        for eng in ENGINES:
            row = re.search(rf"\| {eng} \| ([0-9.]+)% .*", sec.group(1))
            cols = [c.strip() for c in row.group(0).split("|")]
            md_ezr = float(cols[2].split("%")[0])
            md_ndcg = float(cols[9])
            check(f"C6 EZR {s}/{eng} vs REPORT_INPUTS", heat["ezr"][s][eng],
                  md_ezr, tol=0.005)
            check(f"C6 nDCG {s}/{eng} vs REPORT_INPUTS", heat["ndcg"][s][eng],
                  md_ndcg, tol=0.005)
    order = sorted(SECTORS, key=lambda s: heat["ezr"][s]["quissly"])
    assert order[0] == "auto" and order[-1] == "marketplace", order
    data["heat"] = heat
    data["heat_sector_order"] = order

    # ── C7 audit classes ────────────────────────────────────────────────────
    audit = json.loads((ROOT / "analysis/empty_pool_audit/"
                        "audit.json").read_text())
    from collections import Counter
    counts = Counter(r["class"] for r in audit["results"])
    for cls, want in EXP["audit_classes"].items():
        check(f"C7 {cls}", counts.get(cls, 0), want, tol=0)
    data["audit_classes"] = dict(counts)

    # ── write ────────────────────────────────────────────────────────────────
    n_fail = sum(1 for *_, ok in CHECKS if not ok)
    lines = ["# Chart data reconciliation\n",
             f"{len(CHECKS)} checks, {n_fail} failures\n"]
    for name, got, want, ok in CHECKS:
        lines.append(f"- {'PASS' if ok else '**FAIL**'} {name}: "
                     f"computed {got:.4f}, expected {want:.4f}")
    (OUT / "reconciliation.md").write_text("\n".join(lines))
    if n_fail:
        sys.exit(f"ABORT: {n_fail} reconciliation failures — see "
                 f"analysis/charts/reconciliation.md")
    (OUT / "chart_data.json").write_text(json.dumps(data, indent=1))
    print(f"ALL {len(CHECKS)} RECONCILIATION CHECKS PASS -> chart_data.json")


if __name__ == "__main__":
    main()
