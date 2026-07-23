# The Quissly E-Commerce Search Benchmark

A reproducible benchmark of five e-commerce search engines — **Quissly,
Doofinder, Clerk.io, Luigi's Box, Algolia** — across seven retail sectors,
1,259 queries, and 99,168 LLM-judged results — 64,350 unique query-product
judgments; a product returned by several engines is judged once per query
(ESCI-style graded relevance, judged by Gemini 3.5 Flash).

- **Report:** doi [10.5281/zenodo.21410544](https://doi.org/10.5281/zenodo.21410544)
- **Interactive results:** [quissly.com/benchmarks/search](https://quissly.com/benchmarks/search)
- **Contact:** hello@quissly.com

## Headline results (pooled over all 1,259 queries)

| Engine      | Effective zero-result rate ↓ | Pooled-ideal nDCG@10 ↑ | Pooled recall@20 ↑ | Graded P@10 ↑ |
| ----------- | ---------------------------: | ---------------------: | -----------------: | ------------: |
| **Quissly** |                    **7.39%** |              **73.78** |         **65.49%** |     **56.36** |
| Doofinder   |                       11.83% |                  54.24 |             41.70% |         44.59 |
| Clerk.io    |                       19.78% |                  49.24 |             38.14% |         41.35 |
| Luigi's Box |                       24.46% |                  50.81 |             37.78% |         43.93 |
| Algolia     |                       37.89% |                  44.06 |             33.72% |         38.69 |

229 of 236 paired-bootstrap comparisons are significant after Holm
correction (`analysis/report_inputs/consolidated_holm.csv`). Metric
definitions and population conventions (1,259 / 1,212 / 1,059): `METRICS.md`.

> **Changelog — 2026-07-18 pre-publication correction.** Recall and
> pooled-ideal nDCG are computed over pools keyed by _normalized_ product
> id (lowercase, dashes stripped): Quissly's marketplace hits carry dashed
> UUIDs where the other engines carry undashed hex of the same ids, and
> raw-id pools double-counted 1,142 label-consistent duplicate judgments
> (marketplace recall understated by 11–24pp for every engine). Engine
> ordering is unchanged on every metric at every scope; EZR, coverage,
> junk, and precision are unaffected. Full investigation:
> `analysis/id_overlap_check/ID_OVERLAP_REPORT.md`; before/after:
> `analysis/id_overlap_check/CORRECTION_MANIFEST.md`; superseded raw-id
> artifacts: `analysis/_superseded_rawid_pools/`.

## Five-minute quickstart (no API keys needed)

```bash
git clone https://github.com/quissly/search-benchmark && cd search-benchmark
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 1. verify the shipped data reproduces the report's headline counts
python scripts/verify_release.py

# 2. prove the harness is wired end-to-end (mocked search + judge, no network)
python scripts/harness_dry_run.py
```

Interactive results for every cell are published at
quissly.com/benchmarks/search; the same numbers reproduce locally via
`scripts/verify_release.py`, which recomputes them from
`comparison_final_judged/judged/` with `pipeline/metrics_dashboard.py`.

## What's in this repo

```
comparison_final_judged/   THE core artifact: per-query, per-engine, per-hit
  judged/                  LLM judgments (label, graded gain, judge rationale)
  aggregates/              per-sector precision / zero-result CSVs
queries/                   the 1,259 queries with tier labels (generation
                           procedure described below)
pipeline/                  harness: run queries (run_final_comparison.py),
                           judge results (llm_judge.py — the three verbatim
                           tier prompts live at the top), metric computation
                           (metrics_dashboard.py)
catalogs/                  fetch + normalize + validate scripts that rebuild
                           the seven sector catalogs (not committed — see
                           DATA_LICENSES.md), plus format_data.py,
                           which rebuilds the exact upload files indexed by
                           every provider (md5-gated, byte-verified)
analysis/                  every published statistic, reproducible:
  ndcg_pooled/             pooled-ideal nDCG (authoritative) + bootstrap
  ezr_bootstrap/           effective zero-result rate bootstrap
  bootstrap/               original bootstrap run (see its README: nDCG rows
                           there use a superseded normalization)
  empty_pool_audit/        catalog audit of the 200 queries with no Exact
  judge_stability/         full Gemini 2.5 re-judge incl. raw/ responses
  judge_claude/            full Claude Sonnet 5 cross-family re-judge:
                           raw/ responses + agreement scoring (CLAUDE_JUDGE.md)
  id_overlap_check/        marketplace id-normalization correction: the
                           overlap report + before/after CORRECTION_MANIFEST
  _superseded_rawid_pools/ pre-correction (raw-id pool) artifacts, preserved
  report_inputs/           consolidated report tables + 236-test Holm family
  charts/                  the report's figures + reconciliation-gated
                           render pipeline
providers.py               engine search adapters + per-sector credential
                           routing (SECTOR_CFG)
scripts/                   verify_release.py, harness_dry_run.py
config.example.env         every environment variable, no values
```

## Three reproduction paths

**1. Rerun the harness on your own catalog.** Index your product data into
the engines you want to compare, copy `config.example.env` to `.env` and
fill in your keys (engine credentials, `GEMINI_API_KEY`,
`QUISSLY_SEARCH_URL` or your own engine's adapter in `providers.py`),
add your engine to `SECTOR_CFG` in `providers.py` for each sector it should
answer (engines are only queried for sectors listed there; Quissly itself
has no entry by default), then
`python pipeline/run_final_comparison.py <sector>` followed by
`python pipeline/llm_judge.py --sector <sector>`.
`scripts/harness_dry_run.py` exercises this entire path with mocks so you
can check your wiring before spending API calls.

**2. Recompute every published number from the shipped judgments.** No keys,
no network: `scripts/verify_release.py` (headline counts), then any analysis
script — e.g. `analysis/ndcg_pooled/pooled_ndcg.py` (nDCG),
`analysis/ezr_bootstrap/ezr_bootstrap.py` (EZR + significance). Bootstrap
seeds are fixed (42); the core statistics directories (`ndcg_pooled`,
`ezr_bootstrap`, `empty_pool_audit`, `judge_stability`) each carry a
VERIFICATION.md with an independent re-derivation record, the figures are
gated by `analysis/charts/reconciliation.md`, and the consolidated tables
by `analysis/report_inputs/gate.md`.

**3. Re-judge the shipped results with any LLM.**
`analysis/judge_stability/judge_25.py` is a parameterized re-judging harness
(model and concurrency are flags) that rebuilds the exact batched judging
context per query; `score_agreement.py` then scores label agreement and
recomputes all metrics under both label sets. Shipped example:
gemini-2.5-flash reproduced the shipped gemini-3.5-flash labels on 86.12%
of items (kappa 0.80) with the pooled engine ordering unchanged on every
metric. Two full re-judge replications ship with the benchmark:
`analysis/judge_stability/` (Gemini 2.5, within-family) and
`analysis/judge_claude/` (Claude Sonnet 5 on Vertex AI, cross-family:
82.2% agreement, kappa 0.745, engine ordering reproduced at Spearman 1.0
on EZR/P@10/P@20/nDCG@10/nDCG@20 and recall@10; recall@20 0.9, one
adjacent Luigi's Box/Clerk.io swap with values within 0.005 — see
CLAUDE_JUDGE.md) — each with complete raw responses,
agreement scoring, and operational record.

## How the queries were generated

The per-sector query files live in `queries/query_outputs/`; the generator
is `queries/query_generator.py`. Queries were generated with Gemini 2.5 Pro:
for each sector and tier, the model was prompted with tier-specific rules
(word count, required attributes, or natural-language intent shapes such as
problem-solution / relational / budget-constrained) plus a few handwritten
seed examples, and returned a JSON array of query strings (batches accepted
at an 80% minimum-yield threshold). The design targets 225 slots per
category split 0.30 / 0.30 / 0.20 / 0.20 across simple / medium / complex /
visual, i.e. 68 simple + 67 medium + 45 complex text queries per sector
plus 45 reserved visual slots (see caveats). Furniture has 179 text queries
(one simple-tier slot lost to an ID-numbering off-by-one at generation
time), giving 1,259 benchmarked queries total.

## Caveats and known data quirks

- **Grocery.** The generator's category list includes grocery. Grocery was
  not benchmarked: no grocery catalog was prepared and no grocery queries
  were retained.
- **Reserved visual slots.** The generator reserves 45 visual slots per
  category (0.20 of the 225-slot design) for a planned multimodal edition.
  They were never populated — each is defined to carry no query text and a
  placeholder image reference only — so none could be executed in this
  text-only study. The retained query files contain only the three text
  tiers; the visual slots remain in the generator's design so a future
  edition can extend the same query set.
- **RTV_LoadTest (one row).** The Myntra source data contains an internal
  load-testing record (id 28319, title "RTV_LoadTest", a Red Tape sandal at
  price 0). It survives as 1 of 44,417 rows in the normalized fast-fashion
  catalog, was **never retrieved by any engine for any query** (0 of 13,437
  fast-fashion judged hits), and affects no number.
- **Catalog test/placeholder records.** A handful of similar source-data
  placeholders exist in the catalogs (e.g. fast_fashion id 12348
  "test dispName", two "#N/A"-titled Amazon records). Exactly **one** ever
  surfaced in the benchmark: "test dispName" was returned once for the
  query "gloves" (rank 9) and judged Irrelevant (gain 0), which if anything
  penalized the engine that returned it.
- **Dashed/undashed product ids.** One engine returns marketplace product
  ids as dashed UUIDs while the catalog stores them undashed. All analysis
  code normalizes ids (lowercase, dashes stripped) before joining; anything
  you build directly on the raw files should do the same.
- **Pharmacy image URLs no longer resolve.** The Netmeds CDN links in the
  pharmacy catalog are dead. The original judging run fetched product
  images at judging time; any future re-judge of pharmacy is text-only (the
  shipped judge-stability re-judge was — see its VERIFICATION.md), so
  pharmacy-sector judge comparisons carry a changed-context caveat.

## Licensing and citation

The code in this repository is licensed under Apache-2.0 (`LICENSE`,
`NOTICE`). The Quissly-generated artifacts in this repository — the query
sets, the relevance judgments with rationales, the per-query scores, and
the analysis outputs — are released under CC BY 4.0. Upstream catalog data
remains under the source terms already documented in `DATA_LICENSES.md`
(Amazon Reviews 2023: Hou et al., 2024, arXiv:2403.03952, CC BY-SA 4.0;
plus three Kaggle datasets).

**Cite as:** Chikhladze, K., Lezhava, T., and the Quissly Team (2026). _The
Quissly E-Commerce Search Benchmark v1.0._ doi:10.5281/zenodo.21410544.
Machine-readable metadata in `CITATION.cff` (GitHub's "Cite this repository").
