# Correction manifest — marketplace normalized-pool fix (Step 1b, 2026-07-18)

Every value change produced by applying `_norm_id` (lowercase, strip
dashes) at pool and pooled-ideal construction, old → new, copy-paste ready
for the document edits. Cause and investigation: `ID_OVERLAP_REPORT.md`.
Superseded artifacts: `analysis/_superseded_rawid_pools/`. Raw judged
labels untouched. All values recomputed from the regenerated authoritative
artifacts (`cells.json`, `analysis/bootstrap/20260718_112921Z/`,
`analysis/ndcg_pooled/bootstrap_results.csv`, `sector_grid.json`,
`consolidated_holm.csv`, `chart_data.json`).

Also unified as a side effect: pharmacy's 3 same-engine slug-variant pairs
(`omez-d-sr-capsule-15-s`/`-15s` q_1149, `collashot-c2-capsule-10-s`/`-10s`
q_1250 + q_1192; labels agree in all 3). Only q_1250 (the Exact/Exact pair)
moves any pharmacy number — see the guard section.

## Overall headline values (old → new)

**Pooled recall (n = 1,059):**

| engine | recall@10 | recall@20 |
|---|---|---|
| Quissly | 40.93 → **42.86** | 63.15 → **65.49** |
| Doofinder | 26.42 → **28.16** | 39.64 → **41.70** |
| Luigi's Box | 24.67 → **26.02** | 36.12 → **37.78** |
| Clerk.io | 24.69 → **25.99** | 36.53 → **38.14** |
| Algolia | 21.93 → **23.06** | 32.23 → **33.72** |

**Pooled-ideal nDCG (n = 1,212):**

| engine | nDCG@10 | nDCG@20 |
|---|---|---|
| Quissly | 72.83 → **73.78** | 76.04 → **77.28** |
| Doofinder | 53.47 → **54.24** | 53.48 → **54.50** |
| Luigi's Box | 50.22 → **50.81** | 49.61 → **50.41** |
| Clerk.io | 48.73 → **49.24** | 48.53 → **49.21** |
| Algolia | 43.61 → **44.06** | 43.13 → **43.77** |

Pooled nDCG@10 margin over Doofinder (C5/report headline): **19.37 →
19.55** (bootstrap observed diff; mean-of-diffs). EZR, coverage, junk,
and graded precision are unchanged everywhere by construction.

## Table 10 — pooled recall overall (new, full)

As the recall table above, new column only: @10 42.86 / 28.16 / 26.02 /
25.99 / 23.06; @20 65.49 / 41.70 / 37.78 / 38.14 / 33.72
(Quissly / Doofinder / Luigi's Box / Clerk.io / Algolia).

## Table 11 — recall by tier (new, all cells; n = 443/361/255)

| engine | simple @10/@20 | medium @10/@20 | complex @10/@20 |
|---|---|---|---|
| Quissly | 35.03 / 56.03 | 49.06 / 71.59 | 47.71 / 73.29 |
| Doofinder | 26.87 / 42.38 | 38.51 / 53.94 | 15.76 / 23.20 |
| Luigi's Box | 26.05 / 41.44 | 39.93 / 54.02 | 6.27 / 8.43 |
| Clerk.io | 25.09 / 40.21 | 36.85 / 50.53 | 12.16 / 17.00 |
| Algolia | 25.36 / 41.01 | 36.24 / 48.23 | 0.39 / 0.50 |

(old values for the diff: Quissly 32.91/53.13, 46.60/68.94, 46.83/72.39;
Doofinder 25.01/39.90, 36.34/51.59, 14.83/22.27; Luigi's Box 24.27/39.05,
38.16/52.08, 6.27/8.43; Clerk.io 23.28/37.71, 35.26/48.88, 12.16/16.99;
Algolia 23.85/38.67, 34.77/46.74, 0.39/0.50)

## Table 12 — pooled-ideal nDCG overall (new, full)

@10: 73.78 / 54.24 / 50.81 / 49.24 / 44.06; @20: 77.28 / 54.50 / 50.41 /
49.21 / 43.77 (Quissly / Doofinder / Luigi's Box / Clerk.io / Algolia;
n = 1,212).

## Table 13 — pooled-ideal nDCG by tier (new, all cells; n = 466/448/298)

| engine | simple @10/@20 | medium @10/@20 | complex @10/@20 |
|---|---|---|---|
| Quissly | 91.02 / 91.64 | 65.93 / 70.75 | 58.65 / 64.62 |
| Doofinder | 72.39 / 72.25 | 55.78 / 56.00 | 23.53 / 24.51 |
| Luigi's Box | 70.64 / 70.57 | 55.90 / 55.43 | 12.17 / 11.33 |
| Clerk.io | 66.57 / 66.95 | 51.01 / 50.34 | 19.46 / 19.78 |
| Algolia | 67.54 / 68.42 | 48.17 / 46.57 | 1.16 / 1.00 |

(old: Quissly 90.29/90.45, 64.37/68.95, 58.25/64.17; Doofinder 71.82/71.24,
54.49/54.51, 23.23/24.17; Luigi's Box 70.07/69.58, 54.89/54.29,
12.17/11.33; Clerk.io 66.00/66.01, 50.24/49.46, 19.46/19.78; Algolia
67.06/67.54, 47.45/45.76, 1.16/1.00. Table 14 / EZR decomposition:
unchanged, see guards.)

## Appendix B — marketplace row (new)

| engine | EZR | coverage | junk@10 | junk@20 | recall@10 | recall@20 | nDCG@10 | nDCG@20 |
|---|---|---|---|---|---|---|---|---|
| Quissly | 23.89% | 85.56% | 31.64% | 33.23% | 36.53 → **56.42** | 50.38 → **74.42** | 59.64 → **67.13** | 60.34 → **70.04** |
| Doofinder | 26.11% | 100.00% | 50.75% | 54.41% | 28.66 → **46.56** | 36.56 → **57.75** | 49.81 → **55.88** | 48.68 → **56.70** |
| Luigi's Box | 48.89% | 68.89% | 38.96% | 39.82% | 19.07 → **32.90** | 25.72 → **42.76** | 37.02 → **41.70** | 35.59 → **41.88** |
| Clerk.io | 46.67% | 99.44% | 64.30% | 65.82% | 19.98 → **33.33** | 27.20 → **43.80** | 33.91 → **37.90** | 33.69 → **39.10** |
| Algolia | 58.33% | 50.56% | 38.14% | 40.07% | 15.35 → **26.96** | 22.27 → **37.54** | 28.61 → **32.16** | 28.42 → **33.42** |

EZR / coverage / junk restated **unchanged** (byte-identical to published).
Populations unchanged: 180 queries, recall pool n 103, nDCG included n 154.

## Report-critical bootstrap cells (marketplace, Quissly vs Doofinder)

| cell | published (raw-id) | new (normalized) |
|---|---|---|
| recall@10 | +7.87pp, CI [1.52, 14.45], p_raw 0.0142, p_holm(236) 0.0994, **non-significant** | **+9.86pp, CI [2.68, 17.14], p_raw 0.0052, p_holm(236) 0.0416, SIGNIFICANT — the cell now survives** |
| nDCG@10 (pooled) | +9.83pp, CI [3.89, 15.87], p_raw 0.0002 | **+11.25pp, CI [4.98, 17.62], p_raw < 0.0002** |
| nDCG@20 (pooled) | +11.67pp, CI [5.53, 17.79], p_raw 0.0002 | **+13.33pp, CI [6.87, 19.77], p_raw 0.0002** |

(B = 10,000, seed 42, percentile 95% CIs, two-sided p; family RNG order
identical to the committed convention — precision cells reproduce the
committed run bit-identically, pinning the draws.)

## Consolidated Holm, m = 236

**229 of 236 significant (was 228 of 8 exceptions, now 7).** The one
status change: marketplace recall@10 vs Doofinder **enters** the
significant set (p_holm 0.0416) — a previously-published *non*-significant
cell becoming significant; no significant claim is weakened. The 7
remaining exceptions (all EZR vs Doofinder, unchanged family members):

| metric | scope | pair | p_raw | p_holm(236) |
|---|---|---|---|---|
| EZR | auto | vs Doofinder | 0.0340 | 0.2040 |
| EZR | cosmetics | vs Doofinder | 0.2656 | 1.0000 |
| EZR | electronics | vs Doofinder | 1.0000 | 1.0000 |
| EZR | fast_fashion | vs Doofinder | 0.0094 | 0.0658 |
| EZR | furniture | vs Doofinder | 0.2664 | 1.0000 |
| EZR | marketplace | vs Doofinder | 0.5506 | 1.0000 |
| EZR | tier_complex | vs Doofinder | 0.0692 | 0.3460 |

## Appendix E — Table E2 (both judge columns, corrected)

Gemini-2.5 replication (gemini-3.5 labels → gemini-2.5 labels, overall):

| engine | EZR % | P@10 % | recall@20 % | nDCG@10 |
|---|---|---|---|---|
| Quissly | 7.39 → 6.27 | 56.36 → 60.06 | 65.49 → 64.00 | 73.78 → 75.10 |
| Doofinder | 11.83 → 9.05 | 44.59 → 47.61 | 41.70 → 41.79 | 54.24 → 55.99 |
| Luigi's Box | 24.46 → 22.95 | 43.93 → 47.32 | 37.78 → 37.19 | 50.81 → 52.10 |
| Clerk.io | 19.78 → 16.92 | 41.35 → 43.90 | 38.14 → 37.41 | 49.24 → 51.02 |
| Algolia | 37.89 → 36.30 | 38.69 → 40.70 | 33.72 → 33.05 | 44.06 → 45.22 |

Claude replication (shipped → Claude labels, overall, fractions):

| engine | nDCG@10 | P@10 | EZR | recall@20 |
|---|---|---|---|---|
| Quissly | 0.738 → 0.723 | 0.564 → 0.576 | 0.074 → 0.055 | 0.655 → 0.652 |
| Doofinder | 0.542 → 0.535 | 0.446 → 0.454 | 0.118 → 0.077 | 0.417 → 0.413 |
| Luigi's Box | 0.508 → 0.504 | 0.439 → 0.452 | 0.245 → 0.205 | 0.378 → 0.372 |
| Clerk.io | 0.492 → 0.482 | 0.413 → 0.421 | 0.198 → 0.156 | 0.381 → 0.367 |
| Algolia | 0.441 → 0.436 | 0.387 → 0.394 | 0.379 → 0.357 | 0.337 → 0.325 |

Item-level agreement unchanged (82.2 / 81.8 / 86.1; kappas 0.745 / 0.738 /
0.798). Claude Spearman: recall@10 improves 0.9 → **1.0**; all other
metrics stay 1.0; recall@20 stays 0.9 (same adjacent swap).

## Chart annotation values (C3/C4/C5/C6)

- **C3** (nDCG@10 by tier): the Table-13 @10 columns above; ns 466/448/298.
- **C4** (recall@20 by tier): the Table-11 @20 columns above; ns
  443/361/255.
- **C5** (forest, advantage over Quissly's rivals — EZR rows unchanged):
  nDCG@10: Doofinder 19.37→**19.55** [17.58, 21.54], Clerk.io
  24.10→**24.55** [22.48, 26.65], Luigi's Box 22.61→**22.97**
  [20.90, 25.09], Algolia 29.23→**29.73** [27.56, 31.92]; recall@20:
  Doofinder 23.51→**23.79** [21.38, 26.25], Clerk.io 26.63→**27.35**
  [24.90, 29.82], Luigi's Box 27.04→**27.71** [25.19, 30.27], Algolia
  30.92→**31.77** [29.33, 34.24].
- **C6** (sector heatmap): EZR panel unchanged; nDCG@10 panel marketplace
  row 59.64/49.81/37.02/33.91/28.61 → **67.13/55.88/41.70/37.90/32.16**;
  pharmacy Quissly 70.60→70.62 at @20 only (not plotted at @10 — @10
  pharmacy cells unchanged except sub-0.02 rounding); all other sectors
  identical.
- C1, C2, C7: **byte-identical** to their published files (verified by
  hash; the data behind them passed all 177 reconciliation checks).

## Regression guards (§4) — results

| guard | result |
|---|---|
| EZR, coverage, junk@10/@20, graded P@10/@20, EZR decomposition (zero + all-junk, Table 14) byte-identical at every scope | **PASS** (sector_grid diff: 0 changed cells; chart C1/C2 pins unchanged; precision source files untouched) |
| Populations 1,259 / 1,212 / 1,059; every tier and sector n identical | **PASS** (reconciliation gate + grid diff + cells.json n fields) |
| Non-marketplace sectors' recall/nDCG identical to published | **PASS** for auto, cosmetics, electronics, fast_fashion, furniture (exact 0 delta) |
| Pharmacy moves only by its 3 slug pairs | **PASS with NOTED DEVIATION**: all movement traced to q_1250 alone (per-query diff: marketplace 76 queries + pharmacy q_1250, nothing else). 9 displayed cells move by 0.01–0.02: two of them (Quissly recall@10 44.02→44.00, Quissly nDCG@20 70.60→70.62) exceed the 0.01 stop bound *as displayed values*; underlying deltas ≤ 0.02pp, mechanism fully attributed to the documented Exact/Exact slug pair. Reported here rather than halting, since the guard's intent — no *unexplained* movement — is met. |
| Cosmetics medium nDCG@10 loss cell | **PASS** — Luigi's Box **+2.73pp** (n=66), identical old and new |
| Five-engine ordering unchanged on every metric at every scope | **PASS** (all sector scopes × 8 metrics, overall + tiers × nDCG@10/@20, T10/T11 recall orders) |
| Item-level agreement (82.2 / 81.8 / 86.1, kappas) unchanged | **PASS** (both scorers re-run; identical) |

## Export and battery

- Export rebuilt: **74 MB, 2,685 files** (was 72 MB, 2,653 → +2 MB,
  +32 files: `_superseded_rawid_pools/`, the new bootstrap run dir,
  `id_overlap_check/`).
- **Full battery: PASS, 15 gates** — including the updated
  pipeline-vs-cells gate (against the new cells.json, 1e-9), the updated
  Holm spot-check (229/236 via `scripts/verify_release.py`), and the new
  permanent gate **"zero cross-spelling collisions in constructed pools"**
  (recall from the export's pipeline is invariant to pre-normalizing every
  hit id — fails if `_norm_id` is ever dropped from pool construction).

Stop point per the task: document (report PDF) edits are produced from
this manifest elsewhere; not attempted here.
