## Reconciliation gate

- quissly: EZR 93/1259  corrected nDCG@10/@20 = 73.78/77.28  -> match
- doofinder: EZR 149/1259  corrected nDCG@10/@20 = 54.24/54.50  -> match
- luigisbox: EZR 308/1259  corrected nDCG@10/@20 = 50.81/50.41  -> match
- clerk: EZR 249/1259  corrected nDCG@10/@20 = 49.24/49.21  -> match
- algolia: EZR 477/1259  corrected nDCG@10/@20 = 44.06/43.77  -> match
- populations: total 1259, corrected-nDCG 1212 (exclusions {'cosmetics': 3, 'electronics': 2, 'fast_fashion': 6, 'furniture': 2, 'marketplace': 26, 'pharmacy': 8}), recall 1059 -> match
- published bundle cross-check: recall n per engine = 1,059; zero-result(CSV) + all-junk(bundle rich) reproduces every EZR count -> match

**GATE PASSED — all expected values reproduced from raw judged data and cross-checked against the published bundle.**