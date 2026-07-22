## ASK-3 — One consolidated Holm pass across all 236 tests

Family: 128 precision/recall tests (original grid, p_raw bit-identical in both bootstrap CSVs — verified), 64 nDCG tests with CORRECTED pooled-IDCG scores (analysis/ndcg_pooled/bootstrap_results.csv), 44 effective zero-rate tests (analysis/ezr_bootstrap/ezr_results.csv). Provenance verified: row counts 64+64+64+44, seed 42 and B=10,000 in every row. No resampling performed — single Holm-Bonferroni pass over the 236 committed p_raw values.

**228 of 236 significant after Holm; 8 not significant.**

| source | metric | scope | pair | diff pp | 95% CI | p_raw | p_holm |
|---|---|---|---|---:|---|---:|---:|
| ezr | effective_zero_rate | auto | vs doofinder | -2.22 | [-4.44, -0.56] | 0.034 | 0.204 |
| ezr | effective_zero_rate | cosmetics | vs doofinder | -1.11 | [-2.78, 0.00] | 0.2656 | 1 |
| ezr | effective_zero_rate | electronics | vs doofinder | +0.00 | [-1.67, 1.67] | 1 | 1 |
| ezr | effective_zero_rate | fast_fashion | vs doofinder | -7.78 | [-13.89, -2.22] | 0.0094 | 0.0752 |
| ezr | effective_zero_rate | furniture | vs doofinder | -1.12 | [-2.79, 0.00] | 0.2664 | 1 |
| ezr | effective_zero_rate | marketplace | vs doofinder | -2.22 | [-8.89, 4.44] | 0.5506 | 1 |
| ezr | effective_zero_rate | tier_complex | vs doofinder | -4.44 | [-9.21, 0.00] | 0.0692 | 0.346 |
| original_grid | recall_at_10 | marketplace | vs doofinder | +7.87 | [1.52, 14.45] | 0.0142 | 0.0994 |

### The marketplace-vs-Doofinder questions

- ndcg_at_10 (corrected scores): p_raw=0.0002, p_holm=0.004 -> **SURVIVES** (under the old self-normalized scores these cells had p_raw 0.0162/0.0454, p_holm 0.0426/0.0454 at m=192, and died at m=236; corrected diffs are much larger).
- ndcg_at_20 (corrected scores): p_raw=0.0002, p_holm=0.004 -> **SURVIVES** (under the old self-normalized scores these cells had p_raw 0.0162/0.0454, p_holm 0.0426/0.0454 at m=192, and died at m=236; corrected diffs are much larger).
- recall_at_10: p_raw=0.0142, p_holm=0.0994 -> **remains NON-significant** (within noise is a desired finding).
