# Independent verification of the effective zero-result rate bootstrap

Three independent agents verified this directory's outputs (workflow run
`wf_f93a7083-983`, 2026-07-16).

| Check | Result |
|---|---|
| EZR counts (from-scratch stdlib recount) | CONFIRMED exactly: n=1259 for every engine; quissly 44 zero + 49 all-junk = 93 EZR; algolia 419+58=477; clerk 6+243=249; doofinder 1+148=149; luigisbox 173+135=308; the two conditions mutually exclusive for every engine (0 overlaps); Algolia complex-tier zero-results = 302/315; pooled diffs -30.50 / -12.39 / -4.45 / -17.08 pp |
| Script review (adversarial) | Verdict: sound. All 44 cells reproduced exactly to 6dp with the original harness's RNG order, CI, and p formulas. Key proof: reusing the committed CSV's 6dp-rounded p_raw for the combined Holm family is lossless — every p_raw (old and new) is an exact multiple of 2/B = 2e-4, Holm at m=192 from the CSV reproduces the committed p_holm with zero deviation, and 236 × 2e-4 = 0.0472 < 0.05 means a p<2e-4 cell can never flip at m=236. Minor hygiene: the summary's population count is hardcoded via dead code |
| Holm family validation (outputs only) | CONFIRMED: recomputed Holm over m=236 matches every p_holm to <1e-16; 37 significant / 7 within-noise, flags complementary; exactly 3 committed cells lose significance at m=236 (recall_at_10, ndcg_at_10, ndcg_at_20 — all marketplace quissly_vs_doofinder: p_holm 0.0426/0.0426/0.0454 → 0.1278/0.1296/0.2724); all 7 within-noise cells are vs Doofinder; observed_diff = quissly_mean − other_mean in all 236 rows; n per slot correct (sectors 180/furniture 179, tiers 475/469/315, pooled 1259); all 44 EZR means re-derived from raw judged data to 6dp |

> **2026-07-20 note.** `ezr_bootstrap.py` was repointed from the archived
> raw-id bootstrap CSV (`20260715_070827Z`, now under
> `analysis/_superseded_rawid_pools/`) to the committed 2026-07-18 run
> (`20260718_112921Z`), and its combined-family composition was corrected
> to match the published consolidated pass (pooled-IDCG nDCG rows from
> `analysis/ndcg_pooled/`, not the superseded self-normalized rows).
> Outputs regenerated: every EZR p_raw/CI/observed value is unchanged;
> only the family-dependent `p_holm` column moved, and the summary's
> family section now reports 0 committed-cell flips — consistent with
> `analysis/report_inputs/consolidated_holm.csv` (229/236). The record
> above verified the pre-correction outputs.
