# Paired bootstrap — nDCG corrected to pooled IDCG

Same harness as analysis/bootstrap/paired_bootstrap.py (seed 42, B=10,000, fixed cell order, Holm over the full 192-test family); only the ndcg_at_10/ndcg_at_20 per-query scores changed to the pooled-IDCG definition (queries with pooled IDCG=0 excluded, n=1,212 pooled instead of 1,259).

Sanity: precision matches the aggregates CSVs and pooled nDCG matches pooled_ndcg.py's cells.json per sector, engine and cutoff, including populations (worst deviation 0.003944 pp).

Cross-check vs the committed original run: all 128 precision/recall cells reproduce it exactly (p_raw bit-identical; means/CIs equal within the CSV's 6-decimal rounding; same n) — the RNG consumed identical draws for them. Only the 64 nDCG cells changed.

## nDCG cells (pooled-IDCG)

- significant after Holm: 64 of 64 (original run: 64 of 64)
- significance status changes vs original: 0

### Pooled (all-sectors) nDCG cells

- ndcg_at_10 vs Algolia: quissly 72.83 vs 43.61, diff +29.23 pp [27.09, 31.39], p_holm=0 (n=1212; original diff was +28.10 pp)
- ndcg_at_10 vs Clerk.io: quissly 72.83 vs 48.73, diff +24.10 pp [22.06, 26.17], p_holm=0 (n=1212; original diff was +15.56 pp)
- ndcg_at_10 vs Doofinder: quissly 72.83 vs 53.47, diff +19.37 pp [17.43, 21.34], p_holm=0 (n=1212; original diff was +9.63 pp)
- ndcg_at_10 vs Luigi's Box: quissly 72.83 vs 50.22, diff +22.61 pp [20.58, 24.70], p_holm=0 (n=1212; original diff was +15.56 pp)
- ndcg_at_20 vs Algolia: quissly 76.04 vs 43.13, diff +32.91 pp [30.84, 35.02], p_holm=0 (n=1212; original diff was +27.64 pp)
- ndcg_at_20 vs Clerk.io: quissly 76.04 vs 48.53, diff +27.52 pp [25.39, 29.62], p_holm=0 (n=1212; original diff was +14.94 pp)
- ndcg_at_20 vs Doofinder: quissly 76.04 vs 53.48, diff +22.56 pp [20.59, 24.55], p_holm=0 (n=1212; original diff was +9.08 pp)
- ndcg_at_20 vs Luigi's Box: quissly 76.04 vs 49.61, diff +26.44 pp [24.37, 28.55], p_holm=0 (n=1212; original diff was +15.23 pp)

### All nDCG cells, new vs original observed diff (pp)

| metric | sector | vendor | new diff | orig diff | new p_holm | sig |
|---|---|---|---:|---:|---:|---|
| ndcg_at_10 | auto | Algolia | +29.01 | +28.60 | 0 | yes |
| ndcg_at_10 | auto | Clerk.io | +21.96 | +15.46 | 0 | yes |
| ndcg_at_10 | auto | Doofinder | +20.52 | +11.57 | 0 | yes |
| ndcg_at_10 | auto | Luigi's Box | +22.76 | +14.81 | 0 | yes |
| ndcg_at_10 | cosmetics | Algolia | +25.96 | +28.12 | 0 | yes |
| ndcg_at_10 | cosmetics | Clerk.io | +20.81 | +9.11 | 0 | yes |
| ndcg_at_10 | cosmetics | Doofinder | +12.83 | +3.99 | 0 | yes |
| ndcg_at_10 | cosmetics | Luigi's Box | +16.34 | +10.75 | 0 | yes |
| ndcg_at_10 | electronics | Algolia | +29.54 | +23.76 | 0 | yes |
| ndcg_at_10 | electronics | Clerk.io | +26.83 | +15.14 | 0 | yes |
| ndcg_at_10 | electronics | Doofinder | +24.62 | +9.91 | 0 | yes |
| ndcg_at_10 | electronics | Luigi's Box | +25.89 | +16.59 | 0 | yes |
| ndcg_at_10 | fast_fashion | Algolia | +29.49 | +33.01 | 0 | yes |
| ndcg_at_10 | fast_fashion | Clerk.io | +25.69 | +18.28 | 0 | yes |
| ndcg_at_10 | fast_fashion | Doofinder | +20.16 | +10.74 | 0 | yes |
| ndcg_at_10 | fast_fashion | Luigi's Box | +24.96 | +24.88 | 0 | yes |
| ndcg_at_10 | furniture | Algolia | +29.80 | +26.34 | 0 | yes |
| ndcg_at_10 | furniture | Clerk.io | +24.13 | +12.95 | 0 | yes |
| ndcg_at_10 | furniture | Doofinder | +18.93 | +6.64 | 0 | yes |
| ndcg_at_10 | furniture | Luigi's Box | +21.39 | +10.86 | 0 | yes |
| ndcg_at_10 | marketplace | Algolia | +31.04 | +31.38 | 0 | yes |
| ndcg_at_10 | marketplace | Clerk.io | +25.73 | +23.21 | 0 | yes |
| ndcg_at_10 | marketplace | Doofinder | +9.83 | +6.48 | 0.002 | yes |
| ndcg_at_10 | marketplace | Luigi's Box | +22.62 | +20.55 | 0 | yes |
| ndcg_at_10 | pharmacy | Algolia | +30.02 | +25.50 | 0 | yes |
| ndcg_at_10 | pharmacy | Clerk.io | +23.83 | +14.74 | 0 | yes |
| ndcg_at_10 | pharmacy | Doofinder | +27.63 | +18.08 | 0 | yes |
| ndcg_at_10 | pharmacy | Luigi's Box | +24.41 | +10.45 | 0 | yes |
| ndcg_at_10 | pooled | Algolia | +29.23 | +28.10 | 0 | yes |
| ndcg_at_10 | pooled | Clerk.io | +24.10 | +15.56 | 0 | yes |
| ndcg_at_10 | pooled | Doofinder | +19.37 | +9.63 | 0 | yes |
| ndcg_at_10 | pooled | Luigi's Box | +22.61 | +15.56 | 0 | yes |
| ndcg_at_20 | auto | Algolia | +31.39 | +26.83 | 0 | yes |
| ndcg_at_20 | auto | Clerk.io | +23.66 | +14.03 | 0 | yes |
| ndcg_at_20 | auto | Doofinder | +21.83 | +10.10 | 0 | yes |
| ndcg_at_20 | auto | Luigi's Box | +26.00 | +13.26 | 0 | yes |
| ndcg_at_20 | cosmetics | Algolia | +29.41 | +27.04 | 0 | yes |
| ndcg_at_20 | cosmetics | Clerk.io | +23.84 | +9.08 | 0 | yes |
| ndcg_at_20 | cosmetics | Doofinder | +16.63 | +4.12 | 0 | yes |
| ndcg_at_20 | cosmetics | Luigi's Box | +19.62 | +10.31 | 0 | yes |
| ndcg_at_20 | electronics | Algolia | +33.49 | +23.69 | 0 | yes |
| ndcg_at_20 | electronics | Clerk.io | +30.25 | +14.53 | 0 | yes |
| ndcg_at_20 | electronics | Doofinder | +27.12 | +8.64 | 0 | yes |
| ndcg_at_20 | electronics | Luigi's Box | +29.26 | +16.69 | 0 | yes |
| ndcg_at_20 | fast_fashion | Algolia | +35.16 | +32.26 | 0 | yes |
| ndcg_at_20 | fast_fashion | Clerk.io | +31.18 | +17.07 | 0 | yes |
| ndcg_at_20 | fast_fashion | Doofinder | +24.62 | +10.37 | 0 | yes |
| ndcg_at_20 | fast_fashion | Luigi's Box | +30.74 | +24.58 | 0 | yes |
| ndcg_at_20 | furniture | Algolia | +33.77 | +25.04 | 0 | yes |
| ndcg_at_20 | furniture | Clerk.io | +28.25 | +12.04 | 0 | yes |
| ndcg_at_20 | furniture | Doofinder | +22.98 | +6.38 | 0 | yes |
| ndcg_at_20 | furniture | Luigi's Box | +25.94 | +9.57 | 0 | yes |
| ndcg_at_20 | marketplace | Algolia | +31.93 | +30.96 | 0 | yes |
| ndcg_at_20 | marketplace | Clerk.io | +26.65 | +22.52 | 0 | yes |
| ndcg_at_20 | marketplace | Doofinder | +11.67 | +5.33 | 0.002 | yes |
| ndcg_at_20 | marketplace | Luigi's Box | +24.75 | +20.72 | 0 | yes |
| ndcg_at_20 | pharmacy | Algolia | +35.24 | +27.65 | 0 | yes |
| ndcg_at_20 | pharmacy | Clerk.io | +28.83 | +15.32 | 0 | yes |
| ndcg_at_20 | pharmacy | Doofinder | +31.93 | +18.61 | 0 | yes |
| ndcg_at_20 | pharmacy | Luigi's Box | +28.65 | +11.42 | 0 | yes |
| ndcg_at_20 | pooled | Algolia | +32.91 | +27.64 | 0 | yes |
| ndcg_at_20 | pooled | Clerk.io | +27.52 | +14.94 | 0 | yes |
| ndcg_at_20 | pooled | Doofinder | +22.56 | +9.08 | 0 | yes |
| ndcg_at_20 | pooled | Luigi's Box | +26.44 | +15.23 | 0 | yes |
