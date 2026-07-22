# Paired bootstrap — effective zero-result rate (zero-result OR all-junk)

- Metric: binary per (engine, query): 1 if no hits OR every hit judged Irrelevant (gain 0); else 0. Lower is better, so observed_diff = quissly - vendor is NEGATIVE when Quissly wins.
- Population: all 1259 queries, no exclusions (asserted per engine).
- Method: paired bootstrap on per-query differences, whole-query resampling, B=10,000, numpy default_rng(seed=42), fixed cell order (vendor: algolia, clerk, doofinder, luigisbox; slots: auto, cosmetics, electronics, fast_fashion, furniture, marketplace, pharmacy, simple, medium, complex, pooled).
- Multiple comparisons: Holm-Bonferroni across the COMBINED family of **236 tests** = 192 committed tests (precision/recall from analysis/bootstrap/20260718_112921Z/, nDCG from the pooled-IDCG run analysis/ndcg_pooled/, p_raw reused) + these 44 effective-zero cells.
- Environment: Python 3.14.4, numpy 2.5.1, pandas 3.0.3.
- Outputs: analysis/ezr_bootstrap/ezr_results.csv (this family's 44 cells), this summary.

## Reconciliation with shipped numbers (before bootstrapping)

Queries per engine: 1259 (asserted identical for all engines; no exclusions).

| engine | zero-result n (%) | CSV zero-result % | all-junk n (%) | pipeline all-junk % | EZR n (%) = sum |
|---|---:|---:|---:|---:|---:|
| quissly | 44 (3.49%) | 3.49% | 49 (3.89%) | 3.89% | 93 (7.39%) |
| algolia | 419 (33.28%) | 33.28% | 58 (4.61%) | 4.61% | 477 (37.89%) |
| clerk | 6 (0.48%) | 0.48% | 243 (19.30%) | 19.30% | 249 (19.78%) |
| doofinder | 1 (0.08%) | 0.08% | 148 (11.76%) | 11.76% | 149 (11.83%) |
| luigisbox | 173 (13.74%) | 13.74% | 135 (10.72%) | 10.72% | 308 (24.46%) |

Spot checks: Quissly all-junk = 49/1259 = 3.89% (shipped 3.89%); Algolia zero-results on complex tier = 302/315 (claim in task: 302/315).

## Headline

**37 of 44 effective-zero cells are significant after Holm (family m=236); 7 are within noise** (not significant, or 95% CI crosses zero). 43 of 44 observed differences favor Quissly (negative diff).

Effect of enlarging the family on the 192 committed tests: 0 previously-significant cell(s) lose significance at m=236.

## Pooled cells

- vs Algolia: quissly 7.39% vs 37.89%, diff -30.50 pp [-33.12, -27.88], p_holm=0
- vs Clerk.io: quissly 7.39% vs 19.78%, diff -12.39 pp [-14.46, -10.33], p_holm=0
- vs Doofinder: quissly 7.39% vs 11.83%, diff -4.45 pp [-6.20, -2.70], p_holm=0
- vs Luigi's Box: quissly 7.39% vs 24.46%, diff -17.08 pp [-19.38, -14.85], p_holm=0

## All 44 cells

| sector/tier | vendor | quissly % | vendor % | diff pp | 95% CI | p_raw | p_holm | verdict |
|---|---|---:|---:|---:|---|---:|---:|---|
| auto | Algolia | 0.00 | 26.67 | -26.67 | [-33.33, -20.56] | 0 | 0 | quissly better |
| cosmetics | Algolia | 1.67 | 30.56 | -28.89 | [-35.56, -22.22] | 0 | 0 | quissly better |
| electronics | Algolia | 2.22 | 26.11 | -23.89 | [-30.00, -17.78] | 0 | 0 | quissly better |
| fast_fashion | Algolia | 8.33 | 47.22 | -38.89 | [-46.11, -31.67] | 0 | 0 | quissly better |
| furniture | Algolia | 1.68 | 27.93 | -26.26 | [-32.96, -20.11] | 0 | 0 | quissly better |
| marketplace | Algolia | 23.89 | 58.33 | -34.44 | [-41.67, -27.22] | 0 | 0 | quissly better |
| pharmacy | Algolia | 13.89 | 48.33 | -34.44 | [-42.22, -26.67] | 0 | 0 | quissly better |
| tier_simple | Algolia | 2.11 | 5.89 | -3.79 | [-5.68, -2.11] | 0.0002 | 0.0036 | quissly better |
| tier_medium | Algolia | 8.53 | 30.92 | -22.39 | [-26.65, -18.12] | 0 | 0 | quissly better |
| tier_complex | Algolia | 13.65 | 96.51 | -82.86 | [-86.98, -78.41] | 0 | 0 | quissly better |
| pooled | Algolia | 7.39 | 37.89 | -30.50 | [-33.12, -27.88] | 0 | 0 | quissly better |
| auto | Clerk.io | 0.00 | 6.67 | -6.67 | [-10.56, -3.33] | 0 | 0 | quissly better |
| cosmetics | Clerk.io | 1.67 | 5.56 | -3.89 | [-6.67, -1.11] | 0.0026 | 0.0234 | quissly better |
| electronics | Clerk.io | 2.22 | 9.44 | -7.22 | [-11.11, -3.89] | 0 | 0 | quissly better |
| fast_fashion | Clerk.io | 8.33 | 27.78 | -19.44 | [-26.11, -12.78] | 0 | 0 | quissly better |
| furniture | Clerk.io | 1.68 | 9.50 | -7.82 | [-11.73, -3.91] | 0 | 0 | quissly better |
| marketplace | Clerk.io | 23.89 | 46.67 | -22.78 | [-30.00, -16.11] | 0 | 0 | quissly better |
| pharmacy | Clerk.io | 13.89 | 32.78 | -18.89 | [-26.67, -11.11] | 0 | 0 | quissly better |
| tier_simple | Clerk.io | 2.11 | 5.26 | -3.16 | [-4.84, -1.47] | 0 | 0 | quissly better |
| tier_medium | Clerk.io | 8.53 | 21.75 | -13.22 | [-16.63, -9.81] | 0 | 0 | quissly better |
| tier_complex | Clerk.io | 13.65 | 38.73 | -25.08 | [-30.79, -19.37] | 0 | 0 | quissly better |
| pooled | Clerk.io | 7.39 | 19.78 | -12.39 | [-14.46, -10.33] | 0 | 0 | quissly better |
| auto | Doofinder | 0.00 | 2.22 | -2.22 | [-4.44, -0.56] | 0.034 | 0.204 | within noise |
| cosmetics | Doofinder | 1.67 | 2.78 | -1.11 | [-2.78, 0.00] | 0.2656 | 1 | within noise |
| electronics | Doofinder | 2.22 | 2.22 | +0.00 | [-1.67, 1.67] | 1 | 1 | within noise |
| fast_fashion | Doofinder | 8.33 | 16.11 | -7.78 | [-13.89, -2.22] | 0.0094 | 0.0658 | within noise |
| furniture | Doofinder | 1.68 | 2.79 | -1.12 | [-2.79, 0.00] | 0.2664 | 1 | within noise |
| marketplace | Doofinder | 23.89 | 26.11 | -2.22 | [-8.89, 4.44] | 0.5506 | 1 | within noise |
| pharmacy | Doofinder | 13.89 | 30.56 | -16.67 | [-23.89, -10.00] | 0 | 0 | quissly better |
| tier_simple | Doofinder | 2.11 | 5.68 | -3.58 | [-5.47, -1.89] | 0 | 0 | quissly better |
| tier_medium | Doofinder | 8.53 | 13.86 | -5.33 | [-8.10, -2.56] | 0 | 0 | quissly better |
| tier_complex | Doofinder | 13.65 | 18.10 | -4.44 | [-9.21, 0.00] | 0.0692 | 0.346 | within noise |
| pooled | Doofinder | 7.39 | 11.83 | -4.45 | [-6.20, -2.70] | 0 | 0 | quissly better |
| auto | Luigi's Box | 0.00 | 12.78 | -12.78 | [-17.78, -8.33] | 0 | 0 | quissly better |
| cosmetics | Luigi's Box | 1.67 | 12.78 | -11.11 | [-16.11, -6.67] | 0 | 0 | quissly better |
| electronics | Luigi's Box | 2.22 | 16.67 | -14.44 | [-20.00, -8.89] | 0 | 0 | quissly better |
| fast_fashion | Luigi's Box | 8.33 | 40.00 | -31.67 | [-38.89, -25.00] | 0 | 0 | quissly better |
| furniture | Luigi's Box | 1.68 | 12.85 | -11.17 | [-16.20, -6.70] | 0 | 0 | quissly better |
| marketplace | Luigi's Box | 23.89 | 48.89 | -25.00 | [-31.67, -18.89] | 0 | 0 | quissly better |
| pharmacy | Luigi's Box | 13.89 | 27.22 | -13.33 | [-20.56, -6.11] | 0.0006 | 0.009 | quissly better |
| tier_simple | Luigi's Box | 2.11 | 6.53 | -4.42 | [-6.32, -2.74] | 0 | 0 | quissly better |
| tier_medium | Luigi's Box | 8.53 | 17.91 | -9.38 | [-12.79, -5.97] | 0 | 0 | quissly better |
| tier_complex | Luigi's Box | 13.65 | 61.27 | -47.62 | [-53.33, -41.90] | 0 | 0 | quissly better |
| pooled | Luigi's Box | 7.39 | 24.46 | -17.08 | [-19.38, -14.85] | 0 | 0 | quissly better |

## Narrowest significant margins (smallest |diff| that survived Holm and whose CI excludes zero)

- tier_simple vs Clerk.io: -3.16 pp [-4.84, -1.47], p_holm=0
- tier_simple vs Doofinder: -3.58 pp [-5.47, -1.89], p_holm=0
- tier_simple vs Algolia: -3.79 pp [-5.68, -2.11], p_holm=0.0036
- cosmetics vs Clerk.io: -3.89 pp [-6.67, -1.11], p_holm=0.0234
- tier_simple vs Luigi's Box: -4.42 pp [-6.32, -2.74], p_holm=0
- pooled vs Doofinder: -4.45 pp [-6.20, -2.70], p_holm=0
- tier_medium vs Doofinder: -5.33 pp [-8.10, -2.56], p_holm=0
- auto vs Clerk.io: -6.67 pp [-10.56, -3.33], p_holm=0

## Within-noise cells (7) — desired findings, not failures

- auto vs Doofinder: diff -2.22 pp [-4.44, -0.56], p_holm=0.204
- cosmetics vs Doofinder: diff -1.11 pp [-2.78, 0.00], p_holm=1
- electronics vs Doofinder: diff +0.00 pp [-1.67, 1.67], p_holm=1
- fast_fashion vs Doofinder: diff -7.78 pp [-13.89, -2.22], p_holm=0.0658
- furniture vs Doofinder: diff -1.12 pp [-2.79, 0.00], p_holm=1
- marketplace vs Doofinder: diff -2.22 pp [-8.89, 4.44], p_holm=1
- tier_complex vs Doofinder: diff -4.44 pp [-9.21, 0.00], p_holm=0.346
