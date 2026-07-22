"""Empty-pool audit: for 50 of the 200 recall-excluded queries (no engine
returned anything judged Exact), determine whether relevant products existed
in the catalog (engines missed them) or the catalog simply doesn't contain
what was asked (catalog gap).

Pipeline per sampled query:
  1. Retrieve up to 30 candidates from the sector's FULL indexed catalog
     ($CATALOG_DIR/<sector>.parquet, defaulting to <repo>/data/normalized/ — the
     product data the engines indexed). Product ids are NORMALIZED
     (lowercase, dashes stripped) before any comparison: Quissly's
     marketplace hits carry dashed UUIDs while the catalog stores undashed
     hex. After normalization the id-join is 100% for every engine in every
     sector (verified). Candidates come from BM25 text matching over
     title/brand/category/description on the query's content terms.
  2. Judge every candidate with the SAME judge as the benchmark:
     pipeline.llm_judge.judge_products (gemini-3.5-flash, the same per-tier
     system prompts, same batched format, images included). GEMINI_API_KEY
     must be in the environment.
  3. Classify:
       engines-missed : >= 1 candidate judged Exact that NO engine returned
                        for this query.
       partial        : no Exact anywhere, but a Substitute/Complementary
                        exists (newly judged in-catalog, or already present
                        among the engines' originally-returned hits).
       catalog-gap    : nothing above Irrelevant in the new sweep or the
                        original returns, AND retrieval was confident
                        (>= 10 candidates, best candidate matches >= 50% of
                        the query's content terms, <= 30% judge failures).
       inconclusive   : catalog-gap conditions not met (weak retrieval /
                        judge failures), or the only Exact found was a
                        product an engine DID return but the original run
                        judged differently (judge inconsistency, not a miss).

Caveat baked into the summary: candidate retrieval is BM25 text matching and
therefore imperfect — "engines-missed" counts are a LOWER bound.

Read-only on all existing data. Writes only analysis/empty_pool_audit/
(audit.json, summary.md, audit_partial.json checkpoints).
Usage: python empty_pool_audit.py [--limit N] [--dry-run]
"""
import argparse
import gzip
import json
import math
import os
import random
import re
import sys
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
JUDGED_DIR = ROOT / "comparison_final_judged" / "judged"
# Normalized sector catalogs (see catalogs/README.md for how to rebuild).
CATALOG_DIR = Path(os.environ.get(
    "CATALOG_DIR", Path(__file__).resolve().parents[2] / "data" / "normalized"))
OUT_DIR = Path(__file__).resolve().parent

SEED = 42
N_CANDIDATES = 30
STRATA = {"marketplace": 19, "pharmacy": 10, "fast_fashion": 9,
          "furniture": 4, "electronics": 3, "cosmetics": 3, "auto": 2}
SECTORS = ["auto", "cosmetics", "electronics", "fast_fashion",
           "furniture", "marketplace", "pharmacy"]
ENGINES = ["quissly", "doofinder", "luigisbox", "clerk", "algolia"]

STOPWORDS = set("""a an and are as at be best but by can cheap do for from
good has have how i in is it me my need needs of on or that the this to
under what when where which will with without you your something anything
help helps looking want""".split())

_token_re = re.compile(r"[a-z0-9]+")


def tokens(text):
    return [t for t in _token_re.findall(str(text).lower())
            if len(t) > 2 and t not in STOPWORDS]


def _norm_id(s):
    """Join key for product ids across judged hits and the catalog: Quissly's
    marketplace ids are dashed UUIDs, the catalog stores them undashed."""
    return str(s).lower().replace("-", "")


def load_empty_pool_queries():
    out = []
    for sector in SECTORS:
        judged = json.load(gzip.open(JUDGED_DIR / f"{sector}_judged.json.gz",
                                     "rt", encoding="utf-8"))
        for entry in judged:
            providers = entry["providers"]
            pool = {str(h["id"]) for p in providers.values()
                    for h in p.get("hits", []) if h["score"] == 1}
            if pool:
                continue
            returned = {}
            for p in providers.values():
                for h in p.get("hits", []):
                    hid = _norm_id(h["id"])
                    if hid not in returned or h["score"] > returned[hid][0]:
                        returned[hid] = (h["score"], h["label"])
            out.append({"sector": sector, "qid": entry["query_id"],
                        "complexity": entry["complexity"],
                        "text": entry["text_query"], "returned": returned})
    return out


def sample_queries(pool):
    by_sector = defaultdict(list)
    for q in pool:
        by_sector[q["sector"]].append(q)
    rng = random.Random(SEED)
    sampled = []
    for sector in SECTORS:                      # fixed order for determinism
        qs = sorted(by_sector[sector], key=lambda q: q["qid"])
        n = STRATA[sector]
        assert len(qs) >= n, (sector, len(qs), n)
        sampled.extend(rng.sample(qs, n))
    return sampled


class BM25:
    def __init__(self, docs, k1=1.5, b=0.75):
        self.k1, self.b = k1, b
        self.doc_tf = []
        self.doc_len = []
        df = Counter()
        for d in docs:
            tf = Counter(d)
            self.doc_tf.append(tf)
            self.doc_len.append(len(d))
            df.update(tf.keys())
        self.n = len(docs)
        self.avgdl = sum(self.doc_len) / max(1, self.n)
        self.idf = {t: math.log(1 + (self.n - c + 0.5) / (c + 0.5))
                    for t, c in df.items()}
        self.postings = defaultdict(list)
        for i, tf in enumerate(self.doc_tf):
            for t in tf:
                self.postings[t].append(i)

    def search(self, query_tokens, top_n):
        scores = defaultdict(float)
        for t in set(query_tokens):
            idf = self.idf.get(t)
            if idf is None:
                continue
            for i in self.postings[t]:
                tf = self.doc_tf[i][t]
                dl = self.doc_len[i]
                scores[i] += idf * tf * (self.k1 + 1) / (
                    tf + self.k1 * (1 - self.b + self.b * dl / self.avgdl))
        ranked = sorted(scores.items(), key=lambda x: (-x[1], x[0]))
        return ranked[:top_n]


_catalogs = {}


def catalog(sector):
    if sector not in _catalogs:
        df = pd.read_parquet(CATALOG_DIR / f"{sector}.parquet")
        df = df.reset_index(drop=True)
        docs = [tokens(f"{r.title} {r.title} {r.title} {r.brand} "
                       f"{r.category} {r.description}")
                for r in df.itertuples()]
        _catalogs[sector] = (df, BM25(docs))
        print(f"  [{sector}] catalog loaded: {len(df):,} products")
    return _catalogs[sector]


def coverage(query_tokens, row):
    text = set(tokens(f"{row.title} {row.brand} {row.category} "
                      f"{row.description}"))
    qt = set(query_tokens)
    return len(qt & text) / len(qt) if qt else 0.0


def retrieve(q):
    df, bm25 = catalog(q["sector"])
    qtok = tokens(q["text"])
    hits = bm25.search(qtok, N_CANDIDATES)
    cands = []
    for i, score in hits:
        row = df.iloc[i]
        raw_id = row.product_id.split(":", 1)[1]
        cands.append({
            "id": raw_id, "title": row.title,
            "description": (row.description or "")[:1500],
            "price": None if pd.isna(row.price) else float(row.price),
            "discount_price": None, "image_url": row.image_url or None,
            "bm25": float(score),
            "coverage": coverage(qtok, row),
            "was_returned": _norm_id(raw_id) in q["returned"],
            "original_label": q["returned"].get(_norm_id(raw_id),
                                                (None, None))[1],
        })
    return cands


def classify(q, cands, judgments):
    ok = [(c, j) for c, j in zip(cands, judgments) if not j.get("failed")]
    n_failed = len(judgments) - len(ok)
    failed_frac = n_failed / len(judgments) if judgments else 1.0
    best_new = max((j["score"] for _, j in ok), default=0.0)
    best_orig = max((g for g, _ in q["returned"].values()), default=0.0)
    fresh_exact = [(c, j) for c, j in ok
                   if j["score"] == 1.0 and not c["was_returned"]]
    stale_exact = [(c, j) for c, j in ok
                   if j["score"] == 1.0 and c["was_returned"]]
    cov_best = max((c["coverage"] for c in cands), default=0.0)
    confident = (len(cands) >= 10 and cov_best >= 0.5
                 and failed_frac <= 0.3)
    if fresh_exact:
        cls, why = "engines-missed", \
            f"{len(fresh_exact)} in-catalog product(s) judged Exact that no engine returned"
    elif stale_exact:
        cls, why = "inconclusive", \
            ("only Exact(s) found were products an engine DID return but the "
             "benchmark run judged differently — judge inconsistency, not a miss")
    elif best_new in (0.1, 0.01) or best_orig in (0.1, 0.01):
        src = "new catalog sweep" if best_new >= best_orig else \
            "engines' original returns"
        cls, why = "partial", \
            f"best available is gain {max(best_new, best_orig)} ({src}); no Exact found"
    elif confident:
        cls, why = "catalog-gap", \
            (f"nothing above Irrelevant in {len(cands)} candidates "
             f"(best term coverage {cov_best:.2f}) nor in original returns")
    else:
        cls, why = "inconclusive", \
            (f"retrieval too weak to call catalog-gap: {len(cands)} candidates, "
             f"best coverage {cov_best:.2f}, {n_failed} judge failures")
    return {"class": cls, "why": why, "best_new_gain": best_new,
            "best_original_gain": best_orig, "n_candidates": len(cands),
            "n_judge_failed": n_failed, "best_coverage": cov_best,
            "n_fresh_exact": len(fresh_exact),
            "n_stale_exact": len(stale_exact)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--dry-run", action="store_true",
                    help="sample + retrieve only, no judging")
    ap.add_argument("--reclassify", action="store_true",
                    help="rebuild audit.json/summary.md from the stored "
                         "judgments (no retrieval, no API calls); used after "
                         "fixing the id-normalization join")
    args = ap.parse_args()

    pool = load_empty_pool_queries()
    by_sector = Counter(q["sector"] for q in pool)
    print(f"empty-pool queries: {len(pool)} "
          f"({', '.join(f'{s}:{by_sector[s]}' for s in SECTORS)})")
    assert len(pool) == 200, len(pool)

    sampled = sample_queries(pool)
    assert len(sampled) == 50
    print("sampled qids:", json.dumps(
        {s: [q["qid"] for q in sampled if q["sector"] == s] for s in SECTORS}))
    if args.limit:
        sampled = sampled[:args.limit]

    if args.reclassify:
        prev = json.loads((OUT_DIR / "audit.json").read_text())["results"]
        by_qid = {q["qid"]: q for q in pool}
        results = []
        for r in prev:
            q = by_qid[r["qid"]]
            cands = r["candidates"]
            for c in cands:
                key = _norm_id(c["id"])
                c["was_returned"] = key in q["returned"]
                c["original_label"] = q["returned"].get(key, (None, None))[1]
            judgments = [{"label": c["judged_label"], "score": c["judged_gain"],
                          "reasoning": c.get("judge_reasoning", ""),
                          "failed": c["judge_failed"]} for c in cands]
            verdict = classify(q, cands, judgments)
            results.append({"qid": q["qid"], "sector": q["sector"],
                            "complexity": q["complexity"], "query": q["text"],
                            "n_originally_returned": len(q["returned"]),
                            **verdict, "candidates": cands})
        write_outputs(results)
        return

    if not args.dry_run and not os.environ.get("GEMINI_API_KEY", "").strip():
        sys.exit("GEMINI_API_KEY not in environment")
    if not args.dry_run:
        sys.path.insert(0, str(ROOT))
        from pipeline.llm_judge import judge_products
    else:
        judge_products = None

    results = []
    def process(q):
        cands = retrieve(q)
        if args.dry_run:
            judgments = [{"label": "Irrelevant", "score": 0.0,
                          "reasoning": "dry-run", "failed": True}
                         for _ in cands]
        else:
            judgments = judge_products(
                q["text"],
                [{k: c[k] for k in ("title", "description", "price",
                                    "discount_price", "image_url")}
                 for c in cands],
                complexity=q["complexity"])
        for c, j in zip(cands, judgments):
            c["judged_label"] = j["label"]
            c["judged_gain"] = j["score"]
            c["judge_reasoning"] = j["reasoning"]
            c["judge_failed"] = bool(j.get("failed"))
            c.pop("description", None)     # keep the JSON output compact
        verdict = classify(q, cands, judgments)
        return {"qid": q["qid"], "sector": q["sector"],
                "complexity": q["complexity"], "query": q["text"],
                "n_originally_returned": len(q["returned"]),
                **verdict, "candidates": cands}

    # preload catalogs serially (heavy), then judge queries concurrently
    for s in sorted({q["sector"] for q in sampled}):
        catalog(s)
    with ThreadPoolExecutor(max_workers=3) as ex:
        for i, res in enumerate(ex.map(process, sampled), 1):
            results.append(res)
            print(f"[{i}/{len(sampled)}] {res['sector']}/{res['qid']} -> "
                  f"{res['class']} (best new gain {res['best_new_gain']}, "
                  f"“{res['query'][:60]}”)")
            if i % 10 == 0:
                (OUT_DIR / "audit_partial.json").write_text(
                    json.dumps(results, ensure_ascii=False))

    write_outputs(results)


def write_outputs(results):
    results.sort(key=lambda r: (r["sector"], r["qid"]))
    (OUT_DIR / "audit.json").write_text(json.dumps({
        "seed": SEED, "n_candidates_per_query": N_CANDIDATES,
        "strata": STRATA, "judge_model": "gemini-3.5-flash",
        "catalog_source": str(CATALOG_DIR),
        "classification_rules": classify.__doc__ or "see script docstring",
        "results": results}, ensure_ascii=False, indent=1))

    # ── Summary ──────────────────────────────────────────────────────────────
    classes = ["engines-missed", "partial", "catalog-gap", "inconclusive"]
    by_class = Counter(r["class"] for r in results)
    lines = [
        "# Empty-pool audit: did the catalog contain what the engines missed?",
        "",
        f"Sample: 50 of the 200 recall-excluded queries (no engine returned "
        f"anything judged Exact), stratified proportionally by sector "
        f"({', '.join(f'{s} {STRATA[s]}' for s in SECTORS)}), seed {SEED}. "
        f"Candidates: up to {N_CANDIDATES} per query by BM25 text matching "
        f"over the sector's full indexed catalog "
        f"(datasets/data/normalized/<sector>.parquet; product ids normalized "
        f"— lowercased, dashes stripped — giving a verified 100% id-join "
        f"with the benchmark's judged hits for every engine in every "
        f"sector). Judge: the benchmark's own "
        f"pipeline.llm_judge.judge_products — gemini-3.5-flash, same "
        f"per-tier system prompts, same batch format, images included.",
        "",
        "**Caveat: this audit's candidate retrieval (BM25 keyword matching) "
        "is itself imperfect — it can miss relevant products that better "
        "retrieval would find, so the engines-missed count is a LOWER "
        "bound; catalog-gap requires confident retrieval and judge-found "
        "nothing, and anything weaker is marked inconclusive rather than "
        "guessed.**",
        "",
        "## Split",
        "",
        "| class | overall | " + " | ".join(SECTORS) + " |",
        "|---|---:|" + "---:|" * len(SECTORS),
    ]
    for cls in classes:
        row = [str(sum(1 for r in results
                       if r["class"] == cls and r["sector"] == s))
               for s in SECTORS]
        lines.append(f"| {cls} | {by_class.get(cls, 0)} | "
                     + " | ".join(row) + " |")
    lines.append(f"| **total** | **{len(results)}** | "
                 + " | ".join(str(sum(1 for r in results
                                      if r["sector"] == s))
                              for s in SECTORS) + " |")
    lines += ["", "## Worked examples", ""]
    for cls in classes:
        picks = [r for r in results if r["class"] == cls][:3]
        if not picks:
            continue
        lines.append(f"### {cls}\n")
        for r in picks:
            best = max((c for c in r["candidates"]
                        if not c["judge_failed"]),
                       key=lambda c: (c["judged_gain"], c["bm25"]),
                       default=None)
            lines.append(f"- **{r['sector']}/{r['qid']}** "
                         f"({r['complexity']}): “{r['query']}”")
            if best:
                lines.append(f"  - best candidate: “{best['title'][:100]}” "
                             f"→ judged **{best['judged_label']}** "
                             f"(gain {best['judged_gain']})"
                             + (f"; originally returned by an engine and "
                                f"judged {best['original_label']}"
                                if best["was_returned"] else
                                "; not returned by any engine"))
                if best["judge_reasoning"]:
                    lines.append(f"  - judge: {best['judge_reasoning'][:220]}")
            lines.append(f"  - {r['why']}")
        lines.append("")
    n_inc = by_class.get("inconclusive", 0)
    lines += [
        "## Notes",
        "",
        f"- inconclusive count: {n_inc} of {len(results)} — retrieval or "
        f"judging too weak to call, reported rather than guessed.",
        f"- 'partial' uses BOTH the new catalog sweep and the engines' "
        f"original returned hits (many empty-pool queries already had "
        f"Substitutes returned, just nothing Exact).",
        f"- an Exact-judged candidate that an engine originally returned "
        f"(judged differently in the benchmark run) is JUDGE INCONSISTENCY, "
        f"not an engine miss — such queries are marked inconclusive "
        f"({sum(1 for r in results if r['n_stale_exact'] > 0 and r['n_fresh_exact'] == 0)} "
        f"queries).",
        f"- files: audit.json (full per-candidate judgments), this summary. "
        f"Seed {SEED}.",
        "",
    ]
    (OUT_DIR / "summary.md").write_text("\n".join(lines))
    print(f"\n{by_class}")
    print(f"Wrote {OUT_DIR / 'audit.json'} and summary.md")


if __name__ == "__main__":
    main()
