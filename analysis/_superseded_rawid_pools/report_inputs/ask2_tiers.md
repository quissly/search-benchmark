## ASK-2 — Corrected pooled-IDCG nDCG by complexity tier

| engine | simple @10 / @20 (n=466) | medium @10 / @20 (n=448) | complex @10 / @20 (n=298) |
|---|---:|---:|---:|
| quissly | 90.29 / 90.45 | 64.37 / 68.95 | 58.25 / 64.17 |
| doofinder | 71.82 / 71.24 | 54.49 / 54.51 | 23.23 / 24.17 |
| luigisbox | 70.07 / 69.58 | 54.89 / 54.29 | 12.17 / 11.33 |
| clerk | 66.00 / 66.01 | 50.24 / 49.46 | 19.46 / 19.78 |
| algolia | 67.06 / 67.54 | 47.45 / 45.76 | 1.16 / 1.00 |

### 8 narrowest significant margins in the corrected bootstrap (any metric, any scope; family m=192, seed 42)

Note: significance here is within the corrected bootstrap's own m=192 family; the recall_at_10/marketplace/vs-Doofinder cell below flips to non-significant in the consolidated m=236 family of ASK-3.

- precision_at_10 / marketplace / quissly_vs_doofinder: diff +5.41 pp [2.11, 9.06], p_holm=0.0036
- precision_at_20 / marketplace / quissly_vs_doofinder: diff +6.43 pp [2.94, 10.16], p_holm=0.0036
- precision_at_20 / marketplace / quissly_vs_luigisbox: diff +6.84 pp [2.58, 11.32], p_holm=0.0036
- precision_at_20 / furniture / quissly_vs_luigisbox: diff +6.91 pp [2.70, 11.10], p_holm=0.0036
- recall_at_10 / marketplace / quissly_vs_doofinder: diff +7.87 pp [1.52, 14.45], p_holm=0.0142
- precision_at_10 / marketplace / quissly_vs_luigisbox: diff +8.09 pp [3.87, 12.54], p_holm=0.0036
- recall_at_10 / cosmetics / quissly_vs_doofinder: diff +8.59 pp [5.50, 12.05], p_holm=0
- precision_at_10 / cosmetics / quissly_vs_doofinder: diff +8.78 pp [5.53, 12.13], p_holm=0
