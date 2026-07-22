"""Reconciliation spot-checks runnable from this repo alone (no network,
no keys). Verifies the shipped data still reproduces the report's headline
counts:

  1. Effective zero-result counts per engine over all 1,259 queries:
     Quissly 93, Doofinder 149, Clerk.io 249, Luigi's Box 308, Algolia 477.
  2. Judge label census: Exact 46,738 + Substitute 14,071 +
     Complementary 11,465 + Irrelevant 26,894 = 99,168.
  3. analysis/report_inputs/consolidated_holm.csv: 229 of 236 tests
     significant after Holm.
  4. Query generator: documented constants (225 slots, .30/.30/.20/.20,
     0.8 yield, grocery listed) and the three tier prompt templates at
     their externally verified whitespace-normalized lengths (217/258/331).
  5. Pipeline reproduces the published pooled-ideal nDCG cells
     (analysis/ndcg_pooled/cells.json) to 1e-9, overall and per tier.
  6. Zero cross-spelling collisions in constructed pools: marketplace
     recall is invariant to pre-normalizing every hit id (fails if the
     _norm_id pool keying is ever dropped).

Checks 5-6 import pipeline/metrics_dashboard.py (needs pandas installed,
as in requirements.txt); checks 1-4 are stdlib-only.

    python scripts/verify_release.py
"""
import ast
import csv
import gzip
import json
import re
import sys
import tempfile
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SECTORS = ["auto", "cosmetics", "electronics", "fast_fashion",
           "furniture", "marketplace", "pharmacy"]
EXPECT_EZR = {"quissly": 93, "doofinder": 149, "clerk": 249,
              "luigisbox": 308, "algolia": 477}
EXPECT_LABELS = {"Exact": 46738, "Substitute": 14071,
                 "Complementary": 11465, "Irrelevant": 26894}


def main():
    ezr = Counter()
    labels = Counter()
    n_q = 0
    for sector in SECTORS:
        judged = json.load(gzip.open(
            ROOT / "comparison_final_judged/judged" / f"{sector}_judged.json.gz",
            "rt", encoding="utf-8"))
        for e in judged:
            n_q += 1
            for eng, p in e["providers"].items():
                hits = p.get("hits", [])
                for h in hits:
                    labels[h["label"]] += 1
                if not hits or all(h["score"] == 0 for h in hits):
                    ezr[eng] += 1
    ok = True
    ok &= n_q == 1259
    print(f"{'PASS' if n_q == 1259 else 'FAIL'} queries: {n_q} (expect 1259)")
    for eng, want in EXPECT_EZR.items():
        good = ezr[eng] == want
        ok &= good
        print(f"{'PASS' if good else 'FAIL'} EZR {eng}: {ezr[eng]} "
              f"(expect {want})")
    for lbl, want in EXPECT_LABELS.items():
        good = labels[lbl] == want
        ok &= good
        print(f"{'PASS' if good else 'FAIL'} label {lbl}: {labels[lbl]:,} "
              f"(expect {want:,})")
    total = sum(labels.values())
    good = total == 99168 and set(labels) == set(EXPECT_LABELS)
    ok &= good
    print(f"{'PASS' if good else 'FAIL'} label total: {total:,} "
          f"(expect 99,168; only 4 canonical labels)")

    holm = list(csv.DictReader(open(
        ROOT / "analysis/report_inputs/consolidated_holm.csv")))
    sig = sum(1 for r in holm if r["significant_236"] == "True")
    good = len(holm) == 236 and sig == 229
    ok &= good
    print(f"{'PASS' if good else 'FAIL'} consolidated Holm: {sig} of "
          f"{len(holm)} significant (expect 229 of 236)")

    # 4. generator constants + Appendix-D template identity
    gen = (ROOT / "queries/query_generator.py").read_text()
    good = ("TARGET_TOTAL = 225" in gen and '"simple": 0.30' in gen
            and '"medium": 0.30' in gen and '"complex": 0.20' in gen
            and '"visual": 0.20' in gen and "n * 0.8" in gen
            and '"grocery"' in gen)
    ok &= good
    print(f"{'PASS' if good else 'FAIL'} generator constants "
          f"(225, .30/.30/.20/.20, 0.8, grocery)")
    tpl = None
    for node in ast.walk(ast.parse(gen)):
        if (isinstance(node, ast.Assign)
                and getattr(node.targets[0], "id", "") == "COMPLEXITY_PROMPTS"):
            tpl = ast.literal_eval(node.value)
    lens = ({k: len(re.sub(r"\s+", " ", tpl[k]).strip())
             for k in ("simple", "medium", "complex")} if tpl else {})
    good = lens == {"simple": 217, "medium": 258, "complex": 331}
    ok &= good
    print(f"{'PASS' if good else 'FAIL'} Appendix-D template lengths "
          f"{lens or '(COMPLEXITY_PROMPTS not found)'} "
          f"(expect 217/258/331 ws-normalized)")

    # 5-6 need the pipeline (pandas): pooled-nDCG reproduction + pool-keying
    sys.path.insert(0, str(ROOT))
    from pipeline.metrics_dashboard import (compute_rich_metrics,
                                            compute_recall_by_complexity,
                                            _norm_id)
    engines = list(EXPECT_EZR)
    paths = [ROOT / "comparison_final_judged/judged" / f"{s}_judged.json.gz"
             for s in SECTORS]
    cells = json.loads(
        (ROOT / "analysis/ndcg_pooled/cells.json").read_text())["cells"]
    rich = compute_rich_metrics(paths)
    worst = 0.0
    good = True
    for e in engines:
        worst = max(worst, abs(rich[e]["ndcg"]
                               - cells["overall"][f"{e}@10"]["pooled"]))
        for cx in ("simple", "medium", "complex"):
            got = rich[e]["ndcg10_by_cx"][cx]
            ref = cells[f"complexity:{cx}"][f"{e}@10"]
            worst = max(worst, abs(got["rate"] - ref["pooled"]))
            good &= got["n"] == ref["n_pooled"]
    good &= worst < 1e-9
    ok &= good
    print(f"{'PASS' if good else 'FAIL'} pipeline reproduces pooled-nDCG "
          f"cells.json (overall + tiers; worst dev {worst:.1e}, tol 1e-9)")

    mkt = ROOT / "comparison_final_judged/judged/marketplace_judged.json.gz"
    base = compute_recall_by_complexity(mkt)
    data = json.load(gzip.open(mkt, "rt", encoding="utf-8"))
    for entry in data:
        for prov in entry["providers"].values():
            for h in prov.get("hits", []):
                h["id"] = _norm_id(h["id"])
    with tempfile.NamedTemporaryFile("w", suffix=".json",
                                     delete=False) as f:
        json.dump(data, f)
        tmp = f.name
    norm = compute_recall_by_complexity(Path(tmp))
    Path(tmp).unlink(missing_ok=True)
    good = (json.dumps(base, sort_keys=True, default=dict)
            == json.dumps(norm, sort_keys=True, default=dict))
    ok &= good
    print(f"{'PASS' if good else 'FAIL'} pool keying: marketplace recall "
          f"invariant to id pre-normalization (_norm_id in effect)")

    if not ok:
        sys.exit("VERIFY FAILED")
    print("ALL RELEASE SPOT-CHECKS PASS")


if __name__ == "__main__":
    main()
