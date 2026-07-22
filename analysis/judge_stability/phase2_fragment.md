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
| quissly | 65.49 | 64.00 | -1.49 |
| doofinder | 41.70 | 41.79 | +0.09 |
| luigisbox | 37.78 | 37.19 | -0.59 |
| clerk | 38.14 | 37.41 | -0.73 |
| algolia | 33.72 | 33.05 | -0.67 |

**Pooled-ideal nDCG@10** (Spearman rho of engine ordering, overall: 1.000)

| engine | 3.5 | 2.5 | delta (2.5-3.5) |
|---|---:|---:|---:|
| quissly | 73.78 | 75.10 | +1.31 |
| doofinder | 54.24 | 55.99 | +1.75 |
| luigisbox | 50.81 | 52.10 | +1.28 |
| clerk | 49.24 | 51.02 | +1.79 |
| algolia | 44.06 | 45.22 | +1.16 |

**Largest single cell delta anywhere** (across overall, 7 sectors, 3 tiers): sector:marketplace / EZR / doofinder: **-8.33 pp**

**Lowest Spearman in any scope:** sector:pharmacy / Precision@10: rho = 0.700 (1.000 = identical engine ordering)
