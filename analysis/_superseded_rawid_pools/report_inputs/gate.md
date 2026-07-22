## Reconciliation gate

- quissly: EZR 93/1259  corrected nDCG@10/@20 = 72.83/76.04  -> match
- doofinder: EZR 149/1259  corrected nDCG@10/@20 = 53.47/53.48  -> match
- luigisbox: EZR 308/1259  corrected nDCG@10/@20 = 50.22/49.61  -> match
- clerk: EZR 249/1259  corrected nDCG@10/@20 = 48.73/48.53  -> match
- algolia: EZR 477/1259  corrected nDCG@10/@20 = 43.61/43.13  -> match
- populations: total 1259, corrected-nDCG 1212 (exclusions {'cosmetics': 3, 'electronics': 2, 'fast_fashion': 6, 'furniture': 2, 'marketplace': 26, 'pharmacy': 8}), recall 1059 -> match
- published bundle cross-check: recall n per engine = 1,059; zero-result(CSV) + all-junk(bundle rich) reproduces every EZR count -> match

**GATE PASSED — all expected values reproduced from raw judged data and cross-checked against the published bundle.**