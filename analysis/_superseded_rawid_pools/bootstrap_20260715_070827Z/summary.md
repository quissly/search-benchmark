# Paired bootstrap significance — Quissly vs competitors (20260715_070827Z)

- Data: `comparison_final_judged/judged/<sector>_judged.json.gz` (read-only), 7 sectors, 1,259 paired queries pooled (furniture has 179, not 180).
- Pairings: Quissly vs Algolia, Clerk.io, Doofinder, Luigi's Box (the 5 compared engines; the recall pool is their union, matching this repo's pipeline and the published /compare bundle).
- Metrics: precision@10/@20 (persisted per-query scalars), pooled recall@10/@20 and nDCG@10/@20 (derived per query from persisted per-hit judgments with the pipeline's exact formulas; both cutoffs of recall and nDCG are published on the website's /compare page). Recall excludes queries whose pool is empty (see n_queries per cell), same as the pipeline.
- Method: paired bootstrap on per-query differences (Quissly minus vendor), resampling whole queries with replacement, B=10,000, seed=42 (numpy default_rng, fixed cell order). 95% CI = 2.5/97.5 percentiles. Two-sided empirical p; p_raw=0 means no replicate crossed zero (p < 0.0002).
- Multiple comparisons: Holm-Bonferroni across the full family of **192 tests** (6 metrics x 4 pairings x [7 sectors + pooled]). Significance threshold alpha=0.05.
- Environment: Python 3.12.12, numpy 2.4.6, pandas 3.0.3.

## Sanity check

All per-query means reproduce the reported aggregates: P@10/P@20 match the aggregates CSVs, nDCG@10 + recall@20 match this repo's pipeline exactly, and recall@10/@20 + nDCG@10/@20 match the published website bundle exactly per complexity band (worst deviation 0.0039 pp).

## Headline

**192 of 192 comparisons are significant after Holm correction; 0 are not.** 192 of 192 observed differences favor Quissly.

### Pooled (all sectors) results

- ndcg_at_10, pooled, vs Algolia: +28.10 pp [25.81, 30.43], p_holm=0
- ndcg_at_10, pooled, vs Clerk.io: +15.56 pp [13.59, 17.59], p_holm=0
- ndcg_at_10, pooled, vs Doofinder: +9.63 pp [7.84, 11.46], p_holm=0
- ndcg_at_10, pooled, vs Luigi's Box: +15.56 pp [13.47, 17.73], p_holm=0
- ndcg_at_20, pooled, vs Algolia: +27.64 pp [25.37, 29.87], p_holm=0
- ndcg_at_20, pooled, vs Clerk.io: +14.94 pp [13.00, 16.94], p_holm=0
- ndcg_at_20, pooled, vs Doofinder: +9.08 pp [7.35, 10.78], p_holm=0
- ndcg_at_20, pooled, vs Luigi's Box: +15.23 pp [13.13, 17.31], p_holm=0
- precision_at_10, pooled, vs Algolia: +17.66 pp [15.76, 19.51], p_holm=0
- precision_at_10, pooled, vs Clerk.io: +15.01 pp [13.32, 16.74], p_holm=0
- precision_at_10, pooled, vs Doofinder: +11.76 pp [10.20, 13.44], p_holm=0
- precision_at_10, pooled, vs Luigi's Box: +12.43 pp [10.71, 14.20], p_holm=0
- precision_at_20, pooled, vs Algolia: +16.24 pp [14.49, 17.95], p_holm=0
- precision_at_20, pooled, vs Clerk.io: +13.76 pp [12.13, 15.43], p_holm=0
- precision_at_20, pooled, vs Doofinder: +10.89 pp [9.33, 12.47], p_holm=0
- precision_at_20, pooled, vs Luigi's Box: +11.25 pp [9.57, 12.95], p_holm=0
- recall_at_10, pooled, vs Algolia: +19.01 pp [17.10, 20.95], p_holm=0
- recall_at_10, pooled, vs Clerk.io: +16.24 pp [14.33, 18.17], p_holm=0
- recall_at_10, pooled, vs Doofinder: +14.51 pp [12.71, 16.41], p_holm=0
- recall_at_10, pooled, vs Luigi's Box: +16.26 pp [14.29, 18.20], p_holm=0
- recall_at_20, pooled, vs Algolia: +30.92 pp [28.51, 33.33], p_holm=0
- recall_at_20, pooled, vs Clerk.io: +26.63 pp [24.22, 29.05], p_holm=0
- recall_at_20, pooled, vs Doofinder: +23.51 pp [21.13, 25.95], p_holm=0
- recall_at_20, pooled, vs Luigi's Box: +27.04 pp [24.54, 29.54], p_holm=0

## Narrowest significant margins (10 smallest observed diffs that survived Holm)

- ndcg_at_10, cosmetics, vs Doofinder: +3.99 pp [1.38, 6.81], p_holm=0.013
- ndcg_at_20, cosmetics, vs Doofinder: +4.12 pp [1.70, 6.76], p_holm=0.0072
- ndcg_at_20, marketplace, vs Doofinder: +5.33 pp [0.13, 10.68], p_holm=0.0454
- precision_at_10, marketplace, vs Doofinder: +5.41 pp [2.11, 9.06], p_holm=0.0084
- ndcg_at_20, furniture, vs Doofinder: +6.38 pp [3.23, 9.57], p_holm=0
- precision_at_20, marketplace, vs Doofinder: +6.43 pp [2.94, 10.16], p_holm=0.0072
- ndcg_at_10, marketplace, vs Doofinder: +6.48 pp [1.27, 11.90], p_holm=0.0426
- ndcg_at_10, furniture, vs Doofinder: +6.64 pp [3.28, 10.23], p_holm=0
- precision_at_20, marketplace, vs Luigi's Box: +6.84 pp [2.58, 11.32], p_holm=0.0072
- precision_at_20, furniture, vs Luigi's Box: +6.91 pp [2.70, 11.10], p_holm=0.0072

## Within noise (0 cells: not significant after Holm, or CI crosses zero)

None — every comparison survived correction.

## Observed per-engine means (sanity-check against reported aggregates, %)

| Sector | Engine | P@10 | P@20 | R@10 | R@20 | nDCG@10 | nDCG@20 |
|---|---|---|---|---|---|---|---|
| auto | Quissly | 68.61 | 64.18 | 37.15 | 59.62 | 93.45 | 91.60 |
| auto | Algolia | 48.74 | 46.95 | 21.79 | 33.21 | 64.85 | 64.78 |
| auto | Clerk.io | 52.24 | 49.95 | 25.10 | 38.89 | 77.98 | 77.57 |
| auto | Doofinder | 54.93 | 52.28 | 26.37 | 40.85 | 81.88 | 81.50 |
| auto | Luigi's Box | 54.57 | 50.43 | 23.64 | 35.41 | 78.64 | 78.34 |
| cosmetics | Quissly | 68.05 | 63.76 | 36.50 | 61.23 | 90.57 | 89.39 |
| cosmetics | Algolia | 50.13 | 46.68 | 21.26 | 33.75 | 62.45 | 62.35 |
| cosmetics | Clerk.io | 54.21 | 50.86 | 24.97 | 39.45 | 81.46 | 80.31 |
| cosmetics | Doofinder | 59.27 | 54.12 | 27.91 | 43.26 | 86.58 | 85.27 |
| cosmetics | Luigi's Box | 58.33 | 54.60 | 26.64 | 41.83 | 79.82 | 79.08 |
| electronics | Quissly | 61.95 | 56.72 | 45.83 | 67.72 | 87.56 | 86.15 |
| electronics | Algolia | 40.33 | 36.71 | 25.65 | 35.10 | 63.80 | 62.46 |
| electronics | Clerk.io | 42.23 | 38.60 | 26.20 | 38.42 | 72.42 | 71.62 |
| electronics | Doofinder | 44.58 | 41.84 | 28.07 | 40.38 | 77.65 | 77.51 |
| electronics | Luigi's Box | 43.72 | 40.02 | 27.20 | 37.98 | 70.97 | 69.46 |
| fast_fashion | Quissly | 52.40 | 50.02 | 38.18 | 61.36 | 80.31 | 80.11 |
| fast_fashion | Algolia | 37.02 | 35.49 | 18.37 | 27.32 | 47.31 | 47.85 |
| fast_fashion | Clerk.io | 38.47 | 37.16 | 18.26 | 27.94 | 62.03 | 63.04 |
| fast_fashion | Doofinder | 40.97 | 38.59 | 20.30 | 32.78 | 69.57 | 69.74 |
| fast_fashion | Luigi's Box | 40.93 | 39.35 | 19.24 | 29.01 | 55.43 | 55.52 |
| furniture | Quissly | 61.46 | 55.90 | 47.19 | 72.22 | 88.75 | 87.04 |
| furniture | Algolia | 44.03 | 40.96 | 27.20 | 41.65 | 62.42 | 62.00 |
| furniture | Clerk.io | 47.59 | 43.36 | 33.57 | 47.72 | 75.80 | 75.00 |
| furniture | Doofinder | 50.76 | 46.52 | 33.06 | 49.43 | 82.11 | 80.66 |
| furniture | Luigi's Box | 51.92 | 48.99 | 30.84 | 45.60 | 77.90 | 77.47 |
| marketplace | Quissly | 34.53 | 32.18 | 36.53 | 50.38 | 66.06 | 65.61 |
| marketplace | Algolia | 20.04 | 18.88 | 15.35 | 22.27 | 34.68 | 34.65 |
| marketplace | Clerk.io | 22.33 | 20.82 | 19.98 | 27.20 | 42.85 | 43.09 |
| marketplace | Doofinder | 29.12 | 25.76 | 28.66 | 36.56 | 59.58 | 60.28 |
| marketplace | Luigi's Box | 26.44 | 25.35 | 19.07 | 25.72 | 45.51 | 44.89 |
| pharmacy | Quissly | 47.54 | 44.29 | 44.02 | 65.21 | 73.68 | 74.72 |
| pharmacy | Algolia | 30.59 | 27.72 | 20.86 | 27.24 | 48.18 | 47.06 |
| pharmacy | Clerk.io | 32.42 | 30.01 | 21.86 | 30.56 | 58.94 | 59.40 |
| pharmacy | Doofinder | 32.56 | 31.73 | 19.67 | 30.88 | 55.61 | 56.11 |
| pharmacy | Luigi's Box | 31.63 | 29.57 | 23.15 | 31.88 | 63.23 | 63.30 |
