# Judge stability — Gemini 2.5 vs shipped Gemini 3.5 Flash

## Section-3 summary (paste-ready)

Re-judging all 1,259 benchmark queries with gemini-2.5-flash reproduced the shipped gemini-3.5-flash labels on 86.1% of 64,350 individual product judgments (Cohen's kappa 0.80), and under the re-judged labels the overall five-engine ordering is identical on every metric (sector/tier-level orderings correlate at Spearman rho >= 0.70). The largest movement in any metric cell is -8.3 pp (EZR for doofinder, sector:marketplace scope), so judge substitution materially moves the numbers and the report should treat absolute metric values as judge-dependent.

---

## Provenance

- shipped judge: gemini-3.5-flash (pipeline/llm_judge.py, unchanged in all
  of git history); re-judge model: **gemini-2.5-flash** — the 2.5
  counterpart of the shipped judge, used as the specified default because no
  other 2.5 judge string exists anywhere on disk or in history (see
  analysis/report_inputs/REPORT_INPUTS.md ASK-7).
- prompts and batch format: byte-identical to the main run (system prompts
  AST-extracted from pipeline/llm_judge.py at runtime; pooled unique
  products across all five engines' top-20 hits in stored first-seen order;
  one batched call per query; product images fetched from their URLs and
  inlined before each product's text block). Pipeline files untouched.
- population: all 1,259 queries
  (population_queries.json; the original 126-query stratified sample —
  seed 42, 6 per sector x tier — is
  recorded in sampled_queries.json).
- scored: 1,259 queries; 0
  permanently-failed re-judgings excluded from BOTH sides
  (qids: none).
- write-once cache: raw/<qid>.json (one file per query, immediate persist,
  resume-without-re-billing verified in practice mid-run).

## Phase 1 report
- model: gemini-2.5-flash
- queries: 1259 in population; 26 judged this run, 1233 already cached (write-once resume), 0 permanently failed
- API calls made this run: 30 (retries within them: 4, 429s: 0)
- concurrency: requested 25, effective at end 25 (no step-down)
- unresolved image URLs: 1529 of 1529 items this run (those items were judged text-only; per-query lists in raw/*.json image_missing)
- wall-clock: 184.6s

Note: the counters above cover the final (resume) invocation only.
Cumulative image resolution across the whole run:

| sector | images resolved | rate |
|---|---:|---:|
| auto | 8,143/9,808 | 83.0% |
| cosmetics | 8,614/8,903 | 96.8% |
| electronics | 9,090/9,222 | 98.6% |
| fast_fashion | 9,732/9,746 | 99.9% |
| furniture | 8,093/8,096 | 100.0% |
| marketplace | 7,902/8,362 | 94.5% |
| pharmacy | 0/10,213 | 0.0% |
| **all** | **51,574/64,350** | **80.1%** |

### Run incidents and caveats

- **Pharmacy was judged entirely text-only** in the re-judge (0 of 10,213
  image URLs resolved — the Netmeds CDN links are dead). Whether the
  original 3.5 run had working pharmacy images at its judging time is not
  knowable from disk, so pharmacy label disagreement may partly reflect a
  changed judging context rather than judge behavior. Notably, the lowest
  engine-ordering correlation in any scope is pharmacy precision@10.
- Mid-run stall: after a burst of API 503s, 21 in-flight calls hung
  indefinitely (the Gemini call had no client timeout). Fixed by adding a
  300s per-attempt `asyncio.wait_for` ceiling and resuming from the
  write-once cache; only in-flight work was repeated.
- 5 queries failed all 5 attempts during the main pass (invalid JSON — a
  visibly higher malformed-output rate than 3.5); all 5 succeeded with
  fresh attempts on the resume run, so the final population has **zero
  exclusions**.

---

## Phase 2 — agreement results (population 1259; 1259 scored; 0 failed re-judgings excluded from both sides)

### Item level (64,350 product judgments)

- exact label agreement: **86.12%**
- Cohen's kappa (4 labels): **0.7980**
- mean |gain delta|: **0.0624**

Confusion matrix (rows = shipped 3.5 label, cols = 2.5 label):

| 3.5 \ 2.5 | Exact | Substitute | Complementary | Irrelevant | total |
|---|---:|---:|---:|---:|---:|
| Exact | 24690 | 863 | 83 | 113 | 25749 |
| Substitute | 2218 | 6204 | 169 | 861 | 9452 |
| Complementary | 391 | 192 | 5960 | 896 | 7439 |
| Irrelevant | 356 | 1688 | 1103 | 18563 | 21710 |

### Metric level — overall scope (pools & pooled-IDCG rebuilt per label set)

Populations: total 1259; recall n 1059 (3.5) vs 1087 (2.5); nDCG n 1212 (3.5) vs 1229 (2.5).

**EZR** (Spearman rho of engine ordering, overall: 1.000)

| engine | 3.5 | 2.5 | delta (2.5-3.5) |
|---|---:|---:|---:|
| quissly | 7.39 | 6.27 | -1.11 |
| doofinder | 11.83 | 9.05 | -2.78 |
| luigisbox | 24.46 | 22.95 | -1.51 |
| clerk | 19.78 | 16.92 | -2.86 |
| algolia | 37.89 | 36.30 | -1.59 |

**Precision@10** (Spearman rho of engine ordering, overall: 1.000)

| engine | 3.5 | 2.5 | delta (2.5-3.5) |
|---|---:|---:|---:|
| quissly | 56.36 | 60.06 | +3.70 |
| doofinder | 44.59 | 47.61 | +3.01 |
| luigisbox | 43.93 | 47.32 | +3.40 |
| clerk | 41.35 | 43.90 | +2.55 |
| algolia | 38.69 | 40.70 | +2.01 |

**Pooled recall@20** (Spearman rho of engine ordering, overall: 1.000)

| engine | 3.5 | 2.5 | delta (2.5-3.5) |
|---|---:|---:|---:|
| quissly | 63.15 | 61.60 | -1.55 |
| doofinder | 39.64 | 39.70 | +0.06 |
| luigisbox | 36.12 | 35.50 | -0.62 |
| clerk | 36.53 | 35.84 | -0.69 |
| algolia | 32.23 | 31.58 | -0.65 |

**Pooled-ideal nDCG@10** (Spearman rho of engine ordering, overall: 1.000)

| engine | 3.5 | 2.5 | delta (2.5-3.5) |
|---|---:|---:|---:|
| quissly | 72.83 | 74.15 | +1.32 |
| doofinder | 53.47 | 55.21 | +1.75 |
| luigisbox | 50.22 | 51.53 | +1.31 |
| clerk | 48.73 | 50.49 | +1.76 |
| algolia | 43.61 | 44.75 | +1.15 |

**Largest single cell delta anywhere** (across overall, 7 sectors, 3 tiers): sector:marketplace / EZR / doofinder: **-8.33 pp**

**Lowest Spearman in any scope:** sector:pharmacy / Precision@10: rho = 0.700 (1.000 = identical engine ordering)

---

### Side task — Claude-family judging trial records

**Not found.** A read-only search of the repository, its full git
history, and the legacy output directories found no surviving judgment
records from any Claude-family judging trial: every claude/anthropic hit
was development tooling, an unrelated AWS Bedrock connectivity test, or
coincidental
product text ("Claude Monet ... Folding Screen", "philanthropic"). Nothing
from that trial was used in this stability computation.

---

## Files

- JUDGE_STABILITY.md - this report
- item_agreement.csv - one row per (query, product): both labels, gains, agreement flag
- confusion_matrix.csv - 4x4, rows = 3.5 labels, cols = 2.5 labels
- metric_comparison.json - every metric x engine x scope cell under both label sets, deltas, Spearman by scope, populations
- sampled_queries.json / population_queries.json - query id listings (seed 42)
- raw/ - write-once per-query Gemini 2.5 responses; failed/ - permanent failures
- judge_25.py (Phase 1) / score_agreement.py (Phase 2) / assemble_stability.py (this)

---

## 2026-07-18 normalized-pool correction (marketplace id spelling)

**The metric-level recall/nDCG values above are SUPERSEDED** (computed with
raw-id pools that double-counted 1,142 label-consistent duplicate
marketplace judgments — see `analysis/id_overlap_check/ID_OVERLAP_REPORT.md`).
Item-level agreement (86.12%, kappa 0.798) compares per judged record and
is unchanged. Corrected overall values (pools and pooled ideals keyed by
`_norm_id`, dedup by max gain), gemini-3.5 labels → gemini-2.5 labels:

| engine | EZR % | P@10 % | recall@20 % | nDCG@10 |
|---|---|---|---|---|
| Quissly | 7.39 → 6.27 | 56.36 → 60.06 | 65.49 → 64.00 | 73.78 → 75.10 |
| Doofinder | 11.83 → 9.05 | 44.59 → 47.61 | 41.70 → 41.79 | 54.24 → 55.99 |
| Luigi's Box | 24.46 → 22.95 | 43.93 → 47.32 | 37.78 → 37.19 | 50.81 → 52.10 |
| Clerk.io | 19.78 → 16.92 | 41.35 → 43.90 | 38.14 → 37.41 | 49.24 → 51.02 |
| Algolia | 37.89 → 36.30 | 38.69 → 40.70 | 33.72 → 33.05 | 44.06 → 45.22 |

The engine ordering remains unchanged under both label sets at the overall
scope. EZR and P@10 involve no pooling and are identical to the original
tables; `metric_comparison.json` is regenerated in place, with the raw-id
predecessor preserved in `analysis/_superseded_rawid_pools/judge_metrics/`.
