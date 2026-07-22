# How the metrics are defined

Every published number derives from one artifact: the per-query judged
results in `comparison_final_judged/judged/<sector>_judged.json.gz`
(1,259 queries × 5 engines, 99,168 judged items). This document defines each
metric exactly as implemented and states the population each one is averaged
over.

## Labels and graded gains

Each engine was queried for its top 24 results; the top 20 were judged. For
every query, the unique products across all engines are judged in one
batched LLM call (a product returned by several engines is judged once).
Labels map to graded gains (`GAIN_MAP` in `pipeline/llm_judge.py`):

| Label | Gain |
|---|---:|
| Exact | 1.0 |
| Substitute | 0.1 |
| Complementary | 0.01 |
| Irrelevant | 0.0 |

Every judged hit carries its label, gain (`score`), and the judge's
one-sentence rationale (70 of the 99,168 hits carry an empty rationale
string; labels and gains are complete on every hit).

## Population conventions (read this first)

| population | n | used by |
|---|---:|---|
| all queries | **1,259** | EZR, coverage, graded precision |
| answered queries (per engine) | engine-dependent | junk@k (conditional on ≥1 returned result — see the junk section) |
| pooled-ideal IDCG > 0 | **1,212** | pooled-ideal nDCG (47 queries excluded: nothing anywhere was judged above Irrelevant, so the ideal ranking has zero gain and nDCG is undefined; exclusions by sector: marketplace 26, pharmacy 8, fast_fashion 6, cosmetics 3, electronics 2, furniture 2, auto 0) |
| Exact pool non-empty | **1,059** | pooled recall (200 queries excluded: no engine returned anything judged Exact) |

All per-query metrics are macro-averaged: computed per query, then averaged
with equal weight per query. Per-tier populations: simple 475 / medium 469 /
complex 315 (nDCG: 466/448/298; recall: 443/361/255).

## Effective zero-result rate (EZR)

Binary per (engine, query): **1 if the engine returned no results at all,
OR returned results and every one was judged Irrelevant (gain 0)** — "the
shopper got nothing useful." Denominator: all 1,259 queries. The two failure
modes (zero-result, all-junk) are disjoint by construction, so
EZR = zero-result rate + all-junk rate exactly.
Implementation: `analysis/ezr_bootstrap/ezr_bootstrap.py`.

## Coverage and conditional junk

- **Coverage** = share of queries with ≥1 returned result
  (= 100% − zero-result rate); denominator all queries.
- **Junk@k** (conditional) = among queries with ≥1 result, the share of the
  top-k *returned* hits judged Irrelevant. Zero-result queries are excluded
  here — returning nothing is counted by EZR/coverage, keeping the failure
  modes disjoint. Implementation: `compute_rich_metrics` in
  `pipeline/metrics_dashboard.py`.

## Graded precision@k (P@10, P@20)

Mean gain of the engine's top-k returned hits; denominator is the number of
returned hits (max k); zero-result queries score 0. Implementation:
`precision_at_k` in `pipeline/llm_judge.py`. Substitutes count 0.1 and
complementary items 0.01, so an engine cannot score well returning
accessories for a product query.

## Pooled recall@k (recall@10, recall@20)

There is no engine-independent ground-truth annotation of the catalogs, so
recall is **pooled**: per query, the relevance pool is the union of products
judged **Exact** across all five engines, and an engine's recall is the
share of that pool in its own top k:

```
pool     = { products judged Exact for ANY engine on this query }
recall@k = |engine's top-k ∩ pool| / |pool|
```

Pool membership is keyed by **normalized product id** (lowercase, dashes
stripped — `_norm_id`): Quissly's marketplace hits carry dashed UUIDs where
the other engines carry undashed hex of the same ids, so raw-id pools
double-counted duplicate judgments (2026-07-18 pre-publication correction;
see `analysis/id_overlap_check/ID_OVERLAP_REPORT.md`).

Queries with an empty pool are excluded (n = 1,059). This is a *relative*
measure — engines are scored against what the group collectively found.
Implementation: `compute_recall_by_complexity` in
`pipeline/metrics_dashboard.py`; per-query scores in the bootstrap code.

## Pooled-ideal nDCG@k (nDCG@10, nDCG@20) — the authoritative definition

Standard pooled-IDCG normalization, exactly as implemented in
`analysis/ndcg_pooled/pooled_ndcg.py`:

```
pool     = union of judged (product_id, gain) pairs across all 5 engines,
           deduplicated by NORMALIZED product_id (lowercase, dashes
           stripped) keeping the MAX gain — see the recall section's
           normalization note
IDCG@k   = DCG of the pool's gains sorted descending, truncated at k
DCG      = Σ gain_i / log2(i + 2)          (i = 0-based position)
nDCG@k   = DCG(engine's top-k, own order) / IDCG@k
```

Queries whose pooled IDCG is 0 (nothing judged above Irrelevant anywhere)
are excluded — the same 47-query set at k=10 and k=20, giving n = 1,212.
Because the normalizer is the pooled ideal, an engine is penalized both for
mis-ranking what it returned *and* for failing to retrieve what other
engines found.

> **Superseded normalization.** An earlier internal pass normalized nDCG by
> the ideal reordering of each engine's *own returned* hits
> ("self-normalized"), which measures ordering only and scores every engine
> higher (e.g. 82.91 rather than 73.78 for the top engine, pooled @10).
> `pipeline/metrics_dashboard.py` has been patched to the pooled-ideal
> definition (it reproduces `analysis/ndcg_pooled/cells.json` to 1e-9,
> enforced by `scripts/verify_release.py`); the superseded normalization
> now survives only in the retained provenance run under
> `analysis/bootstrap/` — see the README there. Every number in the
> published report uses the pooled-ideal definition above; the authoritative
> statistics are `analysis/ndcg_pooled/` and
> `analysis/report_inputs/consolidated_holm.csv`.

## Significance testing

Paired bootstrap on per-query differences (Quissly minus rival), resampling
whole queries with replacement, B = 10,000, seed 42, 95% percentile CIs,
two-sided empirical p, Holm–Bonferroni across the consolidated 236-test
family (128 precision/recall + 64 pooled-ideal nDCG + 44 EZR tests):
**229 of 236 significant**. Code: `analysis/ndcg_pooled/pooled_bootstrap.py`,
`analysis/ezr_bootstrap/ezr_bootstrap.py`; consolidated pass in
`analysis/report_inputs/`.

## Reading the data files

`judged/<sector>_judged.json.gz` — one entry per query:

```json
{
  "query_id": "...", "text_query": "...",
  "category": "...", "complexity": "simple|medium|complex",
  "providers": {
    "quissly": {
      "latency_ms": 123, "precision_at_10": 0.62, "precision_at_20": 0.55,
      "hits": [
        {"rank": 1, "id": "...", "title": "...",
         "label": "Exact", "score": 1.0, "reasoning": "..."},
        ...
      ]
    }, ...
  }
}
```

Each hit also carries catalog provenance fields not used by any metric:
`description`, `image` (source image URL), `price`, `discount_price`, and
a `cached` flag.

`aggregates/<sector>_aggregated.csv` — one row per (engine, category,
complexity): `Engine Name, Category, Complexity, Zero-Result Rate (%),
Precision@10 (%), Precision@20 (%), Query Count`.
