# Independent verification of the judge-stability computation

Four independent agents verified this directory's outputs (workflow run
`wf_6fe180df-828`, 2026-07-17) before assembly.

| Check | Result |
|---|---|
| Item level (from-scratch recompute) | CONFIRMED exactly: 64,350 items, agreement 86.1181%, kappa 0.798037 (pe = 0.312653), mean |gain delta| 0.062448, confusion diagonal 24690/6204/5960/18563, row totals 25749/9452/7439/21710; zero within-entry label conflicts, zero unknown labels |
| Metric level (from-scratch recompute) | CONFIRMED exactly: overall Spearman 1.000 on all four metrics; populations recall 1,059 vs 1,087 and nDCG 1,212 vs 1,229; largest of all 220 scope×metric×engine cell deltas = marketplace EZR doofinder −8.333pp (47/180 → 32/180); lowest scope rho = pharmacy P@10 0.700 (next lowest 0.900); the 3.5 side reproduces every shipped gate value in REPORT_INPUTS.md |
| Script review (adversarial) | Verdict: sound. Six findings, each verified moot on this data: no stale-marker reconciliation in code (failed/ is empty — markers were removed manually after later successes, so published n_failed=0 is correct); 3.5-side failure placeholders affect only ~0.006% of items; no model mixing (all 1,259 raw files record gemini-2.5-flash); the "Complement" spelling never occurs; batch-order fidelity vs the original run is unknowable from disk but pool composition is provably order-invariant and matching is by product id; degenerate Spearman tie case impossible here |
| Coverage + secrets | CONFIRMED: 1,259/1,259 raw files parse, ids exactly match the judged files, product_ids equal the rebuilt pooled unique lists in order and content, labels lengths all correct, failed/ empty; pharmacy image_missing covers every product in all 180 files (sector fully text-only); secrets sweep of 1,306 committable files under analysis/: none found |
