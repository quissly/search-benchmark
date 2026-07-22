"""Corrected nDCG under the standard pooled-IDCG definition, computed
alongside (not replacing) the shipped self-normalized metric.

Definition (per query):
  pool     = union of judged (product_id, gain) pairs across all 5 engines,
             deduplicated by product_id keeping the MAX gain; gains as judged
             (1 / 0.1 / 0.01 / 0).
  IDCG@k   = DCG of the pool's gains sorted descending, truncated at k.
  nDCG@k   = engine DCG@k (own returned order, top-k) / pooled IDCG@k.
  Queries with pooled IDCG@k == 0 are excluded (undefined). Note IDCG@10 == 0
  iff IDCG@20 == 0 iff the pool's max gain is 0, so the exclusion set is
  identical for both cutoffs.

Shipped, for side-by-side: the pipeline's self-normalized formula
(IDCG over the engine's OWN returned top-k; zero-IDCG scores 0.0; averaged
over ALL queries) — reconciled against analysis/ndcg_audit/treatment_cells.json,
which was itself reconciled bit-exactly against pipeline.compute_rich_metrics
and the committed bootstrap CSV.

Reads comparison_final_judged/judged/*.json.gz read-only. Writes only into
analysis/ndcg_pooled/ (report.md, cells.json). Touches nothing else.
"""
import gzip
import json
import math
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
JUDGED_DIR = ROOT / "comparison_final_judged" / "judged"
OUT_DIR = Path(__file__).resolve().parent
AUDIT_CELLS = ROOT / "analysis" / "ndcg_audit" / "treatment_cells.json"

SECTORS = ["auto", "cosmetics", "electronics", "fast_fashion",
           "furniture", "marketplace", "pharmacy"]
ENGINES = ["quissly", "doofinder", "luigisbox", "clerk", "algolia"]
KS = (10, 20)
TIERS = ("simple", "medium", "complex")


def _norm_id(s):
    """Pool join key: lowercase, dashes stripped. Quissly's marketplace hits
    carry dashed UUIDs where the other engines carry undashed hex of the
    same ids — see analysis/id_overlap_check/ID_OVERLAP_REPORT.md."""
    return str(s).lower().replace("-", "")


def _dcg(gains):
    return sum(g / math.log2(i + 2) for i, g in enumerate(gains))


def load():
    """One record per query with everything both definitions need."""
    queries = []
    exceptions = {"dup_ids_within_engine": [], "inconsistent_gains": [],
                  "hit_not_in_pool": []}
    for sector in SECTORS:
        judged = json.load(gzip.open(JUDGED_DIR / f"{sector}_judged.json.gz",
                                     "rt", encoding="utf-8"))
        for entry in judged:
            providers = entry["providers"]
            assert set(providers) == set(ENGINES), entry["query_id"]
            pool = {}          # id -> max gain
            gain_seen = defaultdict(set)   # id -> set of judged gains
            eng_hits = {}
            for eng in ENGINES:
                hits = sorted(providers[eng].get("hits", []),
                              key=lambda h: h["rank"])
                ids = [_norm_id(h["id"]) for h in hits]
                if len(ids) != len(set(ids)):
                    dups = sorted({i for i in ids if ids.count(i) > 1})
                    exceptions["dup_ids_within_engine"].append(
                        (sector, entry["query_id"], eng, dups))
                for h in hits:
                    hid = _norm_id(h["id"])
                    gain_seen[hid].add(h["score"])
                    pool[hid] = max(pool.get(hid, 0.0), h["score"])
                eng_hits[eng] = [(_norm_id(h["id"]), h["score"])
                                 for h in hits]
            for hid, gains in gain_seen.items():
                if len(gains) > 1:
                    exceptions["inconsistent_gains"].append(
                        (sector, entry["query_id"], hid, sorted(gains)))
            # sanity 1: every returned hit is in the judged pool
            for eng, hits in eng_hits.items():
                for hid, _ in hits:
                    if hid not in pool:
                        exceptions["hit_not_in_pool"].append(
                            (sector, entry["query_id"], eng, hid))
            queries.append({
                "sector": sector, "qid": entry["query_id"],
                "complexity": entry["complexity"], "text": entry["text_query"],
                "pool": pool, "eng_hits": eng_hits,
                "recall_pool_empty": not any(g == 1 for g in pool.values()),
            })
    return queries, exceptions


def shipped_ndcg(gains, k):
    ordered = gains[:k]
    idcg = _dcg(sorted(ordered, reverse=True))
    return _dcg(ordered) / idcg if idcg > 0 else 0.0


def compute(queries):
    """Attach per-query per-engine shipped + pooled nDCG for both k."""
    for q in queries:
        pool_sorted = sorted(q["pool"].values(), reverse=True)
        q["idcg"] = {k: _dcg(pool_sorted[:k]) for k in KS}
        assert (q["idcg"][10] == 0) == (q["idcg"][20] == 0)
        q["excluded"] = q["idcg"][10] == 0
        q["scores"] = {}
        for eng in ENGINES:
            gains = [g for _, g in q["eng_hits"][eng]]
            s = {}
            for k in KS:
                s[f"shipped{k}"] = shipped_ndcg(gains, k)
                s[f"dcg{k}"] = _dcg(gains[:k])
                s[f"pooled{k}"] = (s[f"dcg{k}"] / q["idcg"][k]
                                   if not q["excluded"] else None)
            q["scores"][eng] = s


def mean(xs):
    return sum(xs) / len(xs) if xs else float("nan")


def cell_values(queries, pred):
    """{engine: {k: {shipped, pooled, n_shipped, n_pooled}}} for one cell."""
    out = {}
    qs = [q for q in queries if pred(q)]
    for eng in ENGINES:
        out[eng] = {}
        for k in KS:
            shipped = [q["scores"][eng][f"shipped{k}"] for q in qs]
            pooled = [q["scores"][eng][f"pooled{k}"] for q in qs
                      if not q["excluded"]]
            out[eng][k] = {
                "shipped": mean(shipped) * 100, "pooled": mean(pooled) * 100,
                "delta": (mean(pooled) - mean(shipped)) * 100,
                "n_shipped": len(shipped), "n_pooled": len(pooled),
            }
    return out


def order_of(cell, k, key):
    vals = {eng: cell[eng][k][key] for eng in ENGINES}
    return tuple(sorted(vals, key=vals.get, reverse=True))


def main():
    queries, exceptions = load()
    compute(queries)
    r = []

    # ── Sanity checks ────────────────────────────────────────────────────────
    r.append("# Pooled-IDCG nDCG — corrected computation\n")
    r.append("## Sanity checks\n")
    n_bad = sum(len(v) for v in exceptions.values())
    r.append(f"1. **Returned hits ⊆ judged pool:** "
             f"{'PASS — no exceptions' if not exceptions['hit_not_in_pool'] else exceptions['hit_not_in_pool'][:10]}")
    r.append(f"   - duplicate ids within one engine's hit list: "
             f"{len(exceptions['dup_ids_within_engine'])} "
             f"{exceptions['dup_ids_within_engine'][:5] if exceptions['dup_ids_within_engine'] else ''}")
    r.append(f"   - same product judged with different gains on one query: "
             f"{len(exceptions['inconsistent_gains'])} "
             f"{exceptions['inconsistent_gains'][:5] if exceptions['inconsistent_gains'] else ''}")
    over1 = [(q["sector"], q["qid"], eng, k, q["scores"][eng][f"pooled{k}"])
             for q in queries if not q["excluded"]
             for eng in ENGINES for k in KS
             if q["scores"][eng][f"pooled{k}"] > 1.0 + 1e-12]
    r.append(f"2. **No nDCG > 1.0 anywhere:** "
             f"{'PASS — max per-query pooled nDCG is ' + format(max(q['scores'][eng][f'pooled{k}'] for q in queries if not q['excluded'] for eng in ENGINES for k in KS), '.6f') if not over1 else 'FAIL: ' + str(over1[:10])}")

    # 3 hand-picked queries, chosen deterministically
    def pick(cond):
        return next(q for q in queries if cond(q))
    q_mixed = pick(lambda q: {1.0, 0.1, 0.01, 0.0} <= set(q["pool"].values()))
    q_sub = pick(lambda q: q["pool"] and max(q["pool"].values()) == 0.1)
    q_zero = pick(lambda q: q["excluded"]
                  and any(q["eng_hits"][e] for e in ENGINES))
    r.append("\n3. **Worked examples** (eyeball the math):\n")
    for tag, q in (("mixed-gain pool", q_mixed),
                   ("substitute-only pool (recall excludes, pooled nDCG includes)", q_sub),
                   ("all-zero pool (excluded: IDCG=0)", q_zero)):
        r.append(f"### {tag}: {q['sector']} / {q['qid']} — “{q['text']}”\n")
        by_gain = sorted(q["pool"].items(), key=lambda x: -x[1])
        gains_desc = [g for _, g in by_gain]
        shown = ", ".join(f"{i}:{g}" for i, g in by_gain[:12])
        r.append(f"- pool ({len(by_gain)} products, id:gain, desc): {shown}"
                 f"{' …' if len(by_gain) > 12 else ''}")
        r.append(f"- pool gains@10 desc: {gains_desc[:10]}")
        r.append(f"- IDCG@10 = {q['idcg'][10]:.6f}, IDCG@20 = {q['idcg'][20]:.6f}")
        if q["excluded"]:
            r.append("- **excluded** (pooled IDCG = 0; nothing judged better "
                     "than Irrelevant anywhere)")
        for eng in ENGINES:
            s = q["scores"][eng]
            g10 = [g for _, g in q["eng_hits"][eng]][:10]
            nd = f"{s['pooled10']:.6f}" if s["pooled10"] is not None else "excluded"
            r.append(f"  - {eng}: top-10 gains {g10} → DCG@10 = "
                     f"{s['dcg10']:.6f}, pooled nDCG@10 = {nd} "
                     f"(shipped self-norm: {s['shipped10']:.6f})")
        r.append("")

    # ── Exclusions ───────────────────────────────────────────────────────────
    excl = [q for q in queries if q["excluded"]]
    recall_excl = [q for q in queries if q["recall_pool_empty"]]
    assert all(q["recall_pool_empty"] for q in excl), \
        "pooled-IDCG exclusion must be a subset of recall's exclusion"
    r.append("## Excluded queries (pooled IDCG@k = 0 — identical set for @10 and @20)\n")
    r.append(f"- overall: **{len(excl)}** of {len(queries)} excluded → "
             f"nDCG population n = {len(queries) - len(excl)}")
    r.append(f"- recall's Exact-only pool excludes {len(recall_excl)}; pooled "
             f"IDCG (any gain > 0) excludes {len(excl)}. The "
             f"**{len(recall_excl) - len(excl)}** queries in between have no "
             f"Exact anywhere but at least one Substitute/Complementary — "
             f"they enter corrected nDCG but not recall. (Pooled exclusion is "
             f"a strict subset of recall's: verified.)\n")
    r.append("| slice | queries | excluded | included n |")
    r.append("|---|---:|---:|---:|")
    for sector in SECTORS:
        qs = [q for q in queries if q["sector"] == sector]
        e = sum(1 for q in qs if q["excluded"])
        r.append(f"| {sector} | {len(qs)} | {e} | {len(qs) - e} |")
    for tier in TIERS:
        qs = [q for q in queries if q["complexity"] == tier]
        e = sum(1 for q in qs if q["excluded"])
        r.append(f"| tier: {tier} | {len(qs)} | {e} | {len(qs) - e} |")
    r.append(f"| **all** | **{len(queries)}** | **{len(excl)}** | "
             f"**{len(queries) - len(excl)}** |\n")

    # ── Cells: corrected vs shipped ──────────────────────────────────────────
    cells = {"overall": cell_values(queries, lambda q: True)}
    for sector in SECTORS:
        cells[f"sector:{sector}"] = cell_values(
            queries, lambda q, s=sector: q["sector"] == s)
    for tier in TIERS:
        cells[f"complexity:{tier}"] = cell_values(
            queries, lambda q, t=tier: q["complexity"] == t)

    r.append("## Corrected (pooled-IDCG) vs shipped (self-normalized) nDCG\n")
    r.append("Deltas ≥ 10pp in **bold**; negative delta = corrected number "
             "is lower than shipped.\n")
    for name, cell in cells.items():
        r.append(f"### {name}\n")
        r.append("| engine | k | shipped | corrected | delta | n (shipped → corrected) |")
        r.append("|---|---:|---:|---:|---:|---:|")
        for eng in ENGINES:
            for k in KS:
                c = cell[eng][k]
                d = f"{c['delta']:+.2f}"
                if abs(c["delta"]) >= 10:
                    d = f"**{d}**"
                r.append(f"| {eng} | {k} | {c['shipped']:.2f} | "
                         f"{c['pooled']:.2f} | {d} | "
                         f"{c['n_shipped']} → {c['n_pooled']} |")
        r.append("")

    # ── Ordering changes ─────────────────────────────────────────────────────
    r.append("## Engine-ordering changes (corrected vs shipped)\n")
    changes = []
    for name, cell in cells.items():
        for k in KS:
            o_s, o_p = order_of(cell, k, "shipped"), order_of(cell, k, "pooled")
            if o_s != o_p:
                changes.append((name, k, o_s, o_p, cell))
    if changes:
        for name, k, o_s, o_p, cell in changes:
            r.append(f"**{name}, nDCG@{k}:**")
            r.append(f"- shipped:   {' > '.join(o_s)}")
            r.append(f"- corrected: {' > '.join(o_p)}")
            for eng in ENGINES:
                c = cell[eng][k]
                r.append(f"  - {eng}: shipped {c['shipped']:.2f} → "
                         f"corrected {c['pooled']:.2f}")
            r.append("")
    else:
        r.append("None — every cell keeps the shipped ordering.\n")

    med = cells["complexity:medium"]
    q20, d20 = med["quissly"][20]["pooled"], med["doofinder"][20]["pooled"]
    r.append("### The audit's medium-tier @20 Quissly/Doofinder flip\n")
    r.append(f"- corrected medium@20: quissly {q20:.2f} vs doofinder {d20:.2f} → "
             f"{'**flip persists: doofinder ahead**' if d20 > q20 else '**flip does NOT persist: quissly ahead**'} "
             f"(margin {abs(q20 - d20):.2f}pp)")
    r.append(f"- shipped medium@20 was: quissly "
             f"{med['quissly'][20]['shipped']:.2f} vs doofinder "
             f"{med['doofinder'][20]['shipped']:.2f}\n")

    # ── Reconciliation of the shipped side against the audit ────────────────
    # The internal nDCG-audit record is not part of the public tree; when it
    # is absent this cross-check is skipped (the shipped column is still
    # verified against pipeline.compute_rich_metrics by verify_release.py).
    if AUDIT_CELLS.exists():
        audit = json.loads(AUDIT_CELLS.read_text())
        worst = 0.0
        for name in cells:
            for eng in ENGINES:
                for k in KS:
                    a = audit[name][f"{eng}@{k}"][0]   # treatment (a) shipped
                    ours = cells[name][eng][k]["shipped"]
                    worst = max(worst, abs(a - ours))
                    assert abs(a - ours) < 1e-9, (name, eng, k, a, ours)
        r.append(f"Reconciliation: the shipped column reproduces the audited "
                 f"pipeline values in every cell exactly "
                 f"(worst |diff| = {worst:.2e} pp).\n")
    else:
        r.append("Reconciliation vs the internal nDCG-audit record: skipped "
                 "(record not present in this tree; the shipped column is "
                 "cross-checked against the pipeline by verify_release.py).\n")

    # ── Machine-readable dump ────────────────────────────────────────────────
    (OUT_DIR / "cells.json").write_text(json.dumps({
        "definition": "pooled IDCG: pool = union of judged (id, gain) across "
                      "all 5 engines, dedup by id keeping max gain; IDCG@k = "
                      "DCG of pool gains desc truncated at k; nDCG@k = engine "
                      "DCG@k / pooled IDCG@k; queries with pooled IDCG == 0 "
                      "excluded",
        "exclusions": {
            "overall": {"total": len(queries), "excluded": len(excl)},
            "recall_exact_only_excluded": len(recall_excl),
            "per_sector": {s: sum(1 for q in queries
                                  if q["sector"] == s and q["excluded"])
                           for s in SECTORS},
            "per_tier": {t: sum(1 for q in queries
                                if q["complexity"] == t and q["excluded"])
                         for t in TIERS},
        },
        "cells": {name: {f"{eng}@{k}": cell[eng][k]
                         for eng in ENGINES for k in KS}
                  for name, cell in cells.items()},
        "ordering_changes": [
            {"cell": name, "k": k, "shipped": list(o_s), "corrected": list(o_p)}
            for name, k, o_s, o_p, _ in changes],
    }, indent=2))

    (OUT_DIR / "report.md").write_text("\n".join(r))
    print("\n".join(r))
    print(f"\nWrote {OUT_DIR / 'report.md'} and cells.json")
    # per-query pooled scores for the bootstrap script
    per_query = {
        q["sector"] + "/" + q["qid"]: {
            "excluded": q["excluded"],
            **{f"{eng}@{k}": q["scores"][eng][f"pooled{k}"]
               for eng in ENGINES for k in KS}}
        for q in queries}
    (OUT_DIR / "per_query_pooled.json").write_text(json.dumps(per_query))
    print(f"Wrote {OUT_DIR / 'per_query_pooled.json'} "
          f"({len(per_query)} queries)")


if __name__ == "__main__":
    main()
