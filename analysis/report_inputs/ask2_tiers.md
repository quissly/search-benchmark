## ASK-2 — Corrected pooled-IDCG nDCG by complexity tier

| engine | simple @10 / @20 (n=466) | medium @10 / @20 (n=448) | complex @10 / @20 (n=298) |
|---|---:|---:|---:|
| quissly | 91.02 / 91.64 | 65.93 / 70.75 | 58.65 / 64.62 |
| doofinder | 72.39 / 72.25 | 55.78 / 56.00 | 23.53 / 24.51 |
| luigisbox | 70.64 / 70.57 | 55.90 / 55.43 | 12.17 / 11.33 |
| clerk | 66.57 / 66.95 | 51.01 / 50.34 | 19.46 / 19.78 |
| algolia | 67.54 / 68.42 | 48.17 / 46.57 | 1.16 / 1.00 |

### 8 narrowest significant margins in the corrected bootstrap (any metric, any scope; family m=192, seed 42)

Note: significance here is within the corrected bootstrap's own m=192 family; the consolidated m=236 pass is ASK-3.

- precision_at_10 / marketplace / quissly_vs_doofinder: diff +5.41 pp [2.11, 9.06], p_holm=0.0036
- precision_at_20 / marketplace / quissly_vs_doofinder: diff +6.43 pp [2.94, 10.16], p_holm=0.0036
- precision_at_20 / marketplace / quissly_vs_luigisbox: diff +6.84 pp [2.58, 11.32], p_holm=0.0036
- precision_at_20 / furniture / quissly_vs_luigisbox: diff +6.91 pp [2.70, 11.10], p_holm=0.0036
- precision_at_10 / marketplace / quissly_vs_luigisbox: diff +8.09 pp [3.87, 12.54], p_holm=0.0036
- recall_at_10 / cosmetics / quissly_vs_doofinder: diff +8.59 pp [5.50, 12.05], p_holm=0
- precision_at_10 / cosmetics / quissly_vs_doofinder: diff +8.78 pp [5.53, 12.13], p_holm=0
- precision_at_20 / cosmetics / quissly_vs_luigisbox: diff +9.17 pp [5.87, 12.64], p_holm=0
