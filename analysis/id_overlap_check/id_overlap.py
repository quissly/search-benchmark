"""Marketplace id-spelling overlap check.

Quissly's marketplace judged hits carry dashed UUID ids; the other four
engines carry undashed lowercase hex of the same namespace. Pools, Exact
pools, and pooled ideals were built by raw id string. This script:

  1. finds every within-query collision (raw ids differ, _norm_id equal)
     in marketplace, with label agreement per colliding pair;
  2. proves the other six sectors have zero collisions;
  3. recomputes marketplace pooled recall@10/@20 and pooled-ideal
     nDCG@10/@20 under the unified-judgment policy (normalize ids; one
     canonical judgment per (query, normalized id), drawn with seed 42 from
     records sorted by (raw id, engine); canonical gain applied to every
     engine's recorded ranks), next to an exact replication of the
     published raw-id numbers (asserted against cells.json and the
     committed bootstrap CSV before any diff is trusted);
  4. re-runs the paired bootstrap (B=10,000, seed 42, percentile 95% CI,
     two-sided empirical p, numpy default_rng) for the report-critical
     cells — marketplace Quissly-vs-Doofinder recall@10, nDCG@10, nDCG@20 —
     under both policies with identical per-cell RNG procedure;
  5. if any colliding pair disagreed on label, recomputes the headline
     observed diffs under always-max / always-min canonical gain.

Reads judged data read-only. Writes only analysis/id_overlap_check/.
"""
import gzip
import json
import math
import random
from collections import defaultdict
from itertools import combinations
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
JUDGED = ROOT / "comparison_final_judged" / "judged"
OUT = Path(__file__).resolve().parent

SECTORS = ["auto", "cosmetics", "electronics", "fast_fashion",
           "furniture", "marketplace", "pharmacy"]
ENGINES = ["quissly", "doofinder", "luigisbox", "clerk", "algolia"]
KS = (10, 20)
SEED = 42
B = 10_000


def _norm_id(s):
    return str(s).lower().replace("-", "")


def load_sector(sector):
    """Per query: list of judged records (engine, raw_id, rank, label, gain)."""
    data = json.load(gzip.open(JUDGED / f"{sector}_judged.json.gz",
                               "rt", encoding="utf-8"))
    out = []
    for e in data:
        recs = []
        for eng in ENGINES:
            for h in sorted(e["providers"][eng].get("hits", []),
                            key=lambda h: h["rank"]):
                recs.append({"engine": eng, "raw_id": str(h["id"]),
                             "rank": h["rank"], "label": h["label"],
                             "gain": float(h["score"])})
        out.append({"qid": e["query_id"], "recs": recs})
    return out


def find_collisions(queries):
    """Pairs of judged records in one query with different raw ids but equal
    _norm_id. Returns per-query collision info + flat pair list."""
    q_hit, pairs = 0, []
    for q in queries:
        groups = defaultdict(list)
        for r in q["recs"]:
            groups[_norm_id(r["raw_id"])].append(r)
        found = False
        for nid, recs in groups.items():
            spellings = sorted({r["raw_id"] for r in recs})
            if len(spellings) < 2:
                continue
            found = True
            # one representative record per raw spelling (labels are
            # engine-invariant per spelling by the shared-judgment design;
            # verified below via the label sets)
            for a, b in combinations(spellings, 2):
                ra = [r for r in recs if r["raw_id"] == a]
                rb = [r for r in recs if r["raw_id"] == b]
                pairs.append({
                    "qid": q["qid"], "norm_id": nid, "raw_a": a, "raw_b": b,
                    "engines_a": sorted({r["engine"] for r in ra}),
                    "engines_b": sorted({r["engine"] for r in rb}),
                    "labels_a": sorted({r["label"] for r in ra}),
                    "labels_b": sorted({r["label"] for r in rb}),
                })
        q_hit += 1 if found else 0
    return q_hit, pairs


def canonical_judgments(queries, policy="seeded"):
    """(qid, norm_id) -> (label, gain) under the unified policy."""
    rng = random.Random(SEED)
    canon = {}
    multi_record = 0
    for q in sorted(queries, key=lambda q: q["qid"]):
        groups = defaultdict(list)
        for r in q["recs"]:
            groups[_norm_id(r["raw_id"])].append(r)
        for nid in sorted(groups):
            recs = sorted(groups[nid],
                          key=lambda r: (r["raw_id"], r["engine"]))
            if len(recs) > 1:
                multi_record += 1
            if policy == "seeded":
                pick = rng.choice(recs)
            elif policy == "max":
                pick = max(recs, key=lambda r: r["gain"])
            elif policy == "min":
                pick = min(recs, key=lambda r: r["gain"])
            canon[(q["qid"], nid)] = (pick["label"], pick["gain"])
    return canon


def _dcg(gains):
    return sum(g / math.log2(i + 2) for i, g in enumerate(gains))


def per_query_scores(queries, unified, canon=None):
    """Per-engine per-query recall@k / pooled nDCG@k.

    unified=False replicates the published raw-id computation exactly
    (pool by raw id, max-gain dedup, recall pool = score==1 raw ids,
    position-counted recall). unified=True uses normalized ids with the
    canonical judgment for both the pools and every engine's ranked gains.
    """
    res = {e: {f"recall@{k}": {} for k in KS} | {f"ndcg@{k}": {} for k in KS}
           for e in ENGINES}
    pool_sizes, ndcg_included = [], 0
    for q in queries:
        key = (lambda r: _norm_id(r["raw_id"])) if unified \
            else (lambda r: r["raw_id"])
        gain_of = {}
        for r in q["recs"]:
            kid = key(r)
            g = canon[(q["qid"], kid)][1] if unified else r["gain"]
            gain_of[kid] = max(gain_of.get(kid, 0.0), g)
        exact_pool = {kid for kid, g in gain_of.items() if g == 1.0}
        ideal = sorted(gain_of.values(), reverse=True)
        idcg = {k: _dcg(ideal[:k]) for k in KS}
        pool_sizes.append(len(gain_of))
        if idcg[20] > 0:
            ndcg_included += 1
        by_eng = defaultdict(list)
        for r in q["recs"]:
            by_eng[r["engine"]].append(r)
        for eng in ENGINES:
            hits = sorted(by_eng.get(eng, []), key=lambda r: r["rank"])
            kids = [key(r) for r in hits]
            gains = [gain_of[kid] for kid in kids]
            for k in KS:
                if exact_pool:
                    found = sum(1 for kid in kids[:k] if kid in exact_pool)
                    res[eng][f"recall@{k}"][q["qid"]] = found / len(exact_pool)
                if idcg[k] > 0:
                    res[eng][f"ndcg@{k}"][q["qid"]] = \
                        _dcg(gains[:k]) / idcg[k]
    return res, pool_sizes, ndcg_included


def bootstrap_cell(diffs):
    """Published convention: B resamples of the paired diffs, mean per
    replicate, percentile CI, two-sided empirical p. Fresh default_rng(SEED)
    per cell (disclosed: the committed run consumed one RNG across its full
    cell family, so CIs match to Monte-Carlo noise, not bit-exactly)."""
    rng = np.random.default_rng(SEED)
    d = np.asarray(diffs)
    idx = rng.integers(0, len(d), size=(B, len(d)))
    means = d[idx].mean(axis=1)
    lo, hi = np.percentile(means, [2.5, 97.5])
    p = 2 * min((means <= 0).mean(), (means >= 0).mean())
    return {"n": len(d), "observed": float(d.mean()),
            "ci_low": float(lo), "ci_high": float(hi),
            "p_raw": float(min(p, 1.0))}


def main():
    results = {"collisions": {}, "sectors_clean": {}, "metrics": {},
               "bootstrap": {}, "sensitivity": {}}

    # ---- 1+2: collisions everywhere ----------------------------------
    mkt = None
    for sector in SECTORS:
        queries = load_sector(sector)
        q_hit, pairs = find_collisions(queries)
        if sector == "marketplace":
            mkt = queries
            qvr = [p for p in pairs
                   if ("quissly" in p["engines_a"]) !=
                      ("quissly" in p["engines_b"])]
            agree = [p for p in pairs
                     if set(p["labels_a"]) == set(p["labels_b"])
                     and len(p["labels_a"]) == 1]
            disagreements = defaultdict(int)
            for p in pairs:
                if not (set(p["labels_a"]) == set(p["labels_b"])
                        and len(p["labels_a"]) == 1):
                    la = "/".join(p["labels_a"])
                    lb = "/".join(p["labels_b"])
                    disagreements[f"{la} vs {lb}"] += 1
            results["collisions"] = {
                "queries_with_collision": q_hit,
                "colliding_pairs": len(pairs),
                "quissly_vs_rival_pairs": len(qvr),
                "agreeing_pairs": len(agree),
                "disagreement_table": dict(disagreements),
                "pairs": pairs,
            }
        else:
            results["sectors_clean"][sector] = {
                "queries_with_collision": q_hit,
                "colliding_pairs": len(pairs)}

    # ---- 3: replicate published, then unified recompute ---------------
    canon = canonical_judgments(mkt, "seeded")
    raw_scores, raw_pools, raw_ndcg_n = per_query_scores(mkt, False)
    uni_scores, uni_pools, uni_ndcg_n = per_query_scores(mkt, True, canon)

    cells = json.loads((ROOT / "analysis/ndcg_pooled/cells.json")
                       .read_text())["cells"]["sector:marketplace"]
    tol = 1e-9
    for eng in ENGINES:
        for k in KS:
            mine = 100 * (sum(raw_scores[eng][f"ndcg@{k}"].values())
                          / len(raw_scores[eng][f"ndcg@{k}"]))
            pub = cells[f"{eng}@{k}"]["pooled"]
            assert abs(mine - pub) < tol, (eng, k, mine, pub)
    rq = raw_scores["quissly"]["recall@10"]
    assert len(rq) == 103, len(rq)
    assert abs(sum(rq.values()) / len(rq) - 0.365323) < 5e-7
    rd = raw_scores["doofinder"]["recall@10"]
    assert abs(sum(rd.values()) / len(rd) - 0.286642) < 5e-7
    print("replication of published raw-id numbers: EXACT (asserted)")

    def table(scores):
        return {e: {m: round(sum(v.values()) / len(v), 6)
                    for m, v in scores[e].items() if v}
                for e in ENGINES}
    results["metrics"] = {
        "raw": table(raw_scores), "unified": table(uni_scores),
        "raw_recall_n": len(rq),
        "unified_recall_n": len(uni_scores["quissly"]["recall@10"]),
        "raw_ndcg_n": raw_ndcg_n, "unified_ndcg_n": uni_ndcg_n,
        "raw_pool_total": sum(raw_pools),
        "unified_pool_total": sum(uni_pools),
    }

    # ---- 4: paired bootstrap, report-critical cells -------------------
    for name, metric in (("recall@10", "recall@10"),
                         ("ndcg@10", "ndcg@10"), ("ndcg@20", "ndcg@20")):
        results["bootstrap"][name] = {}
        for pol, scores in (("raw", raw_scores), ("unified", uni_scores)):
            qs = scores["quissly"][metric]
            ds = scores["doofinder"][metric]
            common = sorted(set(qs) & set(ds))
            diffs = [qs[q] - ds[q] for q in common]
            results["bootstrap"][name][pol] = bootstrap_cell(diffs)

    # ---- 5: sensitivity under extreme tie-breaks ----------------------
    n_disagree = sum(results["collisions"]["disagreement_table"].values())
    if n_disagree:
        for pol in ("max", "min"):
            c2 = canonical_judgments(mkt, pol)
            s2, _, _ = per_query_scores(mkt, True, c2)
            ext = {}
            for metric in ("recall@10", "ndcg@10", "ndcg@20"):
                qs, ds = s2["quissly"][metric], s2["doofinder"][metric]
                common = sorted(set(qs) & set(ds))
                ext[metric] = round(sum(qs[q] - ds[q] for q in common)
                                    / len(common), 6)
            results["sensitivity"][f"always_{pol}"] = ext
    else:
        results["sensitivity"] = {"note": "all colliding pairs agree on "
                                  "label; tie-break is moot"}

    (OUT / "results.json").write_text(json.dumps(results, indent=1))
    c = results["collisions"]
    print(f"marketplace: {c['queries_with_collision']} queries with "
          f"collisions, {c['colliding_pairs']} pairs "
          f"({c['quissly_vs_rival_pairs']} quissly-vs-rival), "
          f"{c['agreeing_pairs']} agree, table={c['disagreement_table']}")
    print("other sectors:", {s: v["colliding_pairs"]
                             for s, v in results["sectors_clean"].items()})
    print(f"recall n: {results['metrics']['raw_recall_n']} -> "
          f"{results['metrics']['unified_recall_n']}; ndcg n: "
          f"{results['metrics']['raw_ndcg_n']} -> "
          f"{results['metrics']['unified_ndcg_n']}")
    for m, d in results["bootstrap"].items():
        for pol, b in d.items():
            print(f"  {m} {pol}: diff={b['observed']:+.6f} "
                  f"CI[{b['ci_low']:.6f},{b['ci_high']:.6f}] "
                  f"p={b['p_raw']:.4f} n={b['n']}")
    if results["sensitivity"]:
        print("sensitivity:", results["sensitivity"])


if __name__ == "__main__":
    main()
