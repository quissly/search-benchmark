# Cross-family judge — Claude re-judge of the full benchmark

**Question**: do the published five-engine results depend on the Gemini
judge family, or do they survive a judge from a different model family?

**Answer: they survive.** Re-judging all 1,259 queries / 64,350 pooled
items with claude-sonnet-5 (Vertex AI, thinking disabled) reproduces the
published engine ordering exactly on EZR, P@10, P@20, nDCG@10, and nDCG@20
(Spearman 1.0 for each), and near-exactly on pooled recall (0.9 — one
adjacent swap between Luigi's Box and Clerk, whose recall@20 values differ
by at most 0.005 under either judge). Quissly is first and Algolia last on every
metric under both judges.

This check is part of the v1.0 report (Section 3 and Appendix E), run
18 July 2026 before publication. It modifies no benchmark number; the
operational record below stands as run.

## Run facts

| | |
|---|---|
| model | `claude-sonnet-5` on Vertex AI, `region=global`, thinking disabled |
| queries | 1,259/1,259 (100%), 0 unrecovered failures, 0 refusals |
| items | 64,350 pooled products, identical batches to the original run (first-seen dedup over all engines' top-20) |
| tokens | 160,382,458 input / 3,203,165 output |
| cost | **$352.80** by per-call usage fields ($320.76 in + $32.03 out at intro $2/$10 per MTok) vs the $500 cap; ≈ $3 more was spent on invalidated early-pilot calls |
| wall-clock | 07:44–09:37 UTC 2026-07-18 (≈ 1h53m elapsed incl. one harness restart; ≈ 80 min of actual runtime at 25-parallel) |
| retries | 28 queries needed a second attempt (transient API errors); 2 queries exceeded Vertex's 30MB request limit and succeeded after a size-based chunk split (see RUN_STATE.md) |
| images | base64, downscaled to the API's 2576px many-image cap; 10,667 of 64,350 image slots unresolvable (dead URLs, dominated by pharmacy's 10,213 dead links — those products judged text-only, as in the original run) |

## Item-level agreement (all 64,350 items)

| pair | agreement | Cohen's kappa |
|---|---:|---:|
| **Claude vs shipped (Gemini 3.5 family)** | **82.2%** | **0.745** |
| Claude vs Gemini 2.5 re-judge | 81.8% | 0.738 |
| Gemini 2.5 re-judge vs shipped (context) | 86.1% | 0.798 |

Crossing model families costs only ~4 points of agreement relative to
crossing model *versions* within the Gemini family — the labels are
substantially judge-invariant.

Confusion (Claude rows, shipped columns):

| | Exact | Substitute | Complementary | Irrelevant |
|---|---:|---:|---:|---:|
| Exact | 23,289 | 2,109 | 313 | 320 |
| Substitute | 1,884 | 6,039 | 374 | 2,193 |
| Complementary | 376 | 436 | 6,204 | 1,845 |
| Irrelevant | 200 | 868 | 548 | 17,352 |

The disagreement is structured, not random: Claude is systematically
slightly more lenient (2,193 shipped-Irrelevant items upgraded to
Substitute; 2,109 shipped-Substitutes upgraded to Exact) — a calibration
shift that moves every engine the same direction and therefore cannot
reorder them.

Agreement by tier: simple 86.8% > medium 81.9% > complex 74.9% — judge
ambiguity concentrates in complex queries, matching the within-family
stability study. By sector: 78.7% (cosmetics) to 85.2% (marketplace).

## Metrics under Claude labels (shipped → Claude)

| engine | nDCG@10 | P@10 | EZR | recall@20 |
|---|---|---|---|---|
| Quissly | 0.728 → 0.712 | 0.564 → 0.576 | 0.074 → 0.055 | 0.631 → 0.629 |
| Doofinder | 0.535 → 0.526 | 0.446 → 0.454 | 0.118 → 0.077 | 0.396 → 0.392 |
| Luigi's Box | 0.502 → 0.497 | 0.439 → 0.452 | 0.245 → 0.205 | 0.361 → 0.354 |
| Clerk.io | 0.487 → 0.476 | 0.413 → 0.421 | 0.198 → 0.156 | 0.365 → 0.351 |
| Algolia | 0.436 → 0.431 | 0.387 → 0.394 | 0.379 → 0.357 | 0.322 → 0.309 |

All metrics computed with the published conventions (graded gains
1/0.1/0.01/0, pooled-ideal IDCG with zero-IDCG queries excluded,
`precision_at_k` mean-gain, Exact-anywhere recall pool). Largest single
cell shift: Clerk.io EZR 0.198 → 0.156. Every shift is a small uniform
leniency effect; no gap between adjacent engines opens or closes enough
to change any published conclusion.

## Paste-ready paragraph (neutral wording)

> As a robustness check, we re-judged the complete benchmark — all 1,259
> queries and 64,350 pooled product judgments — with a judge from a
> different model family (Claude Sonnet 5 on Vertex AI) using the identical
> prompts, batches, and images. Item-level agreement with the published
> labels was 82.2% (Cohen's kappa 0.745, "substantial"), only ~4 points
> below the agreement between two Gemini versions (86.1%). The five-engine
> ordering was reproduced exactly on effective zero-result rate, graded
> precision@10/@20, and pooled-ideal nDCG@10/@20 (Spearman 1.0), with one
> adjacent swap on pooled recall between two engines separated by at most
> 0.005.
> The cross-family judge was marginally more lenient overall, shifting all
> engines' scores in the same direction; no published conclusion changes
> under the alternative judge.

## Files

- `judge_claude.py` — the harness (auth, batching, chunking, budget cap,
  write-once cache); `RUN_STATE.md` — complete operational record;
  `PILOT_REPORT.md` — 9-query gate.
- `raw/q_*.json` — 1,259 per-query responses with labels, reasonings,
  usage, latency, attempts.
- `ops_report_pilot.md` / `ops_report_full.md` — harness run summaries
  (the full-run file covers only the final 53-query resume pass; cumulative
  totals live in this document and RUN_STATE.md).
- `score_agreement.py` → `agreement/summary.json`,
  `agreement/confusion_*.csv`, `agreement/metrics_under_claude.csv`.

---

## 2026-07-18 normalized-pool correction (marketplace id spelling)

**The "Metrics under Claude labels" table above is SUPERSEDED** (its
recall and nDCG columns were computed with raw-id pools that double-counted
1,142 label-consistent duplicate judgments in marketplace — see
`analysis/id_overlap_check/ID_OVERLAP_REPORT.md`). Item-level agreement
(82.2% / 81.8% / 86.1%, kappas 0.745 / 0.738 / 0.798) compares per judged
record and is unchanged. Corrected values (pools and pooled ideals keyed by
`_norm_id`, dedup by max gain), shipped → Claude:

| engine | nDCG@10 | P@10 | EZR | recall@20 |
|---|---|---|---|---|
| Quissly | 0.738 → 0.723 | 0.564 → 0.576 | 0.074 → 0.055 | 0.655 → 0.652 |
| Doofinder | 0.542 → 0.535 | 0.446 → 0.454 | 0.118 → 0.077 | 0.417 → 0.413 |
| Luigi's Box | 0.508 → 0.504 | 0.439 → 0.452 | 0.245 → 0.205 | 0.378 → 0.372 |
| Clerk.io | 0.492 → 0.482 | 0.413 → 0.421 | 0.198 → 0.156 | 0.381 → 0.367 |
| Algolia | 0.441 → 0.436 | 0.387 → 0.394 | 0.379 → 0.357 | 0.337 → 0.325 |

Spearman orderings under normalized pools: **1.0 on EZR, P@10, P@20,
nDCG@10, nDCG@20 and now also recall@10** (previously 0.9 under raw-id
pools); recall@20 remains 0.9 (the same Luigi's Box/Clerk.io adjacent swap,
0.372 vs 0.367). The headline conclusion is unchanged and slightly
strengthened. P@10 and EZR columns are identical to the original table
(no pooling in those metrics).
