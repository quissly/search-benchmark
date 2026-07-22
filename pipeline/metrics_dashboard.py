"""Metric computation for the benchmark data.

compute_rich_metrics / compute_recall_by_complexity are the single source
of the recall / pooled-ideal nDCG / junk / zero-result numbers, consumed by
the analysis scripts, scripts/verify_release.py and scripts/harness_dry_run.py.
(The Plotly panel builders that once lived here were retired with the local
dashboard; the interactive views are the website repo's TypeScript port.)
"""
import gzip
import json
import math
from pathlib import Path
from collections import defaultdict


ENGINES = ["quissly", "doofinder", "algolia", "luigisbox", "clerk"]


def _norm_id(s):
    """Pool join key: lowercase, dashes stripped. Quissly's marketplace hits
    carry dashed UUIDs where the other engines carry undashed hex of the
    same ids — see analysis/id_overlap_check/ID_OVERLAP_REPORT.md."""
    return str(s).lower().replace("-", "")


def _dcg(scores):
    return sum(s / math.log2(i + 2) for i, s in enumerate(scores))


def _read_json(path):
    """Load a JSON file, transparently decompressing .gz files."""
    path = Path(path)
    if path.suffix == ".gz":
        with gzip.open(path, "rt", encoding="utf-8") as f:
            return json.load(f)
    return json.loads(path.read_text())


def _judged_entries(judged_path):
    """judged_path is one Path or a list of Paths (the all-sectors view pools
    every sector's judged queries into one per-query set)."""
    paths = judged_path if isinstance(judged_path, (list, tuple)) else [judged_path]
    return [e for p in paths for e in _read_json(p)]


def compute_rich_metrics(judged_path, k_ndcg=10, k_recall=20):
    judged = _judged_entries(judged_path)
    agg = defaultdict(lambda: {"recall": [], "nrel": [], "ndcg": [], "junk10": [], "junk20": [],
                               "alljunk": []})
    aj_cx = defaultdict(lambda: defaultdict(list))  # engine -> complexity -> [0/1, ...]
    junk_cx = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))  # engine -> junk key -> cx -> [rates]
    # engine -> k -> complexity -> [ndcg, ...] for the card's @10/@20 toggle
    ndcg_cx = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
    for entry in judged:
        cx = entry.get("complexity", "")
        providers = entry.get("providers", {})
        pool = {_norm_id(h["id"]) for p in providers.values() for h in p.get("hits", []) if h["score"] == 1}
        # Pooled-ideal nDCG (matches analysis/ndcg_pooled/pooled_ndcg.py):
        # the normalizer is the ideal ranking of the UNION of judged items
        # across all engines (dedup by NORMALIZED product id keeping max
        # gain), not a reordering of the engine's own hits. Queries whose
        # pooled IDCG is zero (nothing judged above Irrelevant anywhere)
        # are excluded.
        gain_pool = {}
        for p in providers.values():
            for h in p.get("hits", []):
                hid = _norm_id(h["id"])
                gain_pool[hid] = max(gain_pool.get(hid, 0.0), h["score"])
        ideal = sorted(gain_pool.values(), reverse=True)
        for prov, pdata in providers.items():
            hits = pdata.get("hits", [])
            ranked = [h["score"] for h in sorted(hits, key=lambda h: h["rank"])]
            for k in (k_ndcg, k_recall):
                idcg = _dcg(ideal[:k])
                if idcg > 0:
                    ndcg = _dcg(ranked[:k]) / idcg
                    if k == k_ndcg:
                        agg[prov]["ndcg"].append(ndcg)
                    ndcg_cx[prov][k][cx].append(ndcg)
            agg[prov]["nrel"].append(sum(1 for h in hits if h["score"] == 1))
            # Junk@k (k=10, 20): share of the top-k *returned* hits judged Irrelevant
            # (score == 0). Zero-result queries are excluded, the zero-result panel
            # covers them.
            for k, key in ((10, "junk10"), (20, "junk20")):
                top = ranked[:k]
                if top:
                    rate = sum(1 for s in top if s == 0) / len(top)
                    agg[prov][key].append(rate)
                    junk_cx[prov][key][cx].append(rate)
            # All-junk: the engine returned results but every one was judged
            # Irrelevant. Rate over ALL queries (zero-result queries count 0 here
            # so the two failure modes stay disjoint and can be summed).
            aj = 1 if ranked and all(s == 0 for s in ranked) else 0
            agg[prov]["alljunk"].append(aj)
            aj_cx[prov][cx].append(aj)
            if pool:
                found = len({_norm_id(h["id"]) for h in hits[:k_recall]
                             if _norm_id(h["id"]) in pool and h["score"] == 1})
                agg[prov]["recall"].append(found / len(pool))
    out = {}
    for prov, a in agg.items():
        out[prov] = {
            "recall": (sum(a["recall"]) / len(a["recall"]) * 100) if a["recall"] else 0.0,
            "ndcg":   (sum(a["ndcg"]) / len(a["ndcg"]) * 100) if a["ndcg"] else 0.0,
            "nrel":   (sum(a["nrel"]) / len(a["nrel"])) if a["nrel"] else 0.0,
            "junk10": (sum(a["junk10"]) / len(a["junk10"]) * 100) if a["junk10"] else 0.0,
            "junk20": (sum(a["junk20"]) / len(a["junk20"]) * 100) if a["junk20"] else 0.0,
            "alljunk": (sum(a["alljunk"]) / len(a["alljunk"]) * 100) if a["alljunk"] else 0.0,
            "ndcg10_by_cx": {cx: {"rate": sum(v) / len(v) * 100, "n": len(v)}
                             for cx, v in ndcg_cx[prov][k_ndcg].items() if v},
            "ndcg20_by_cx": {cx: {"rate": sum(v) / len(v) * 100, "n": len(v)}
                             for cx, v in ndcg_cx[prov][k_recall].items() if v},
            "alljunk_by_cx": {cx: {"rate": sum(v) / len(v) * 100, "n": len(v)}
                              for cx, v in aj_cx[prov].items() if v},
            "junk10_by_cx": {cx: {"rate": sum(v) / len(v) * 100, "n": len(v)}
                             for cx, v in junk_cx[prov]["junk10"].items() if v},
            "junk20_by_cx": {cx: {"rate": sum(v) / len(v) * 100, "n": len(v)}
                             for cx, v in junk_cx[prov]["junk20"].items() if v},
        }
    return out


def compute_recall_by_complexity(judged_path, ks=(10, 20)):
    """engine -> k -> complexity -> {"rate": %, "n": #queries} for each cutoff
    in ks (n enables exact recombination of any band selection:
    sum(rate*n) / sum(n))."""
    judged = _judged_entries(judged_path)
    agg = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))  # engine -> k -> cx -> [recall, ...]
    for entry in judged:
        cx = entry.get("complexity", "")
        providers = entry.get("providers", {})
        pool = {_norm_id(h["id"]) for p in providers.values() for h in p.get("hits", []) if h["score"] == 1}
        if not pool:
            continue
        for prov, pdata in providers.items():
            hits = pdata.get("hits", [])
            for k in ks:
                found = len({_norm_id(h["id"]) for h in hits[:k]
                             if _norm_id(h["id"]) in pool and h["score"] == 1})
                agg[prov][k][cx].append(found / len(pool))
    out = defaultdict(lambda: defaultdict(dict))
    for prov, kmap in agg.items():
        for k, cxmap in kmap.items():
            for cx, vals in cxmap.items():
                out[prov][k][cx] = {"rate": sum(vals) / len(vals) * 100 if vals else 0.0,
                                    "n": len(vals)}
    return out
