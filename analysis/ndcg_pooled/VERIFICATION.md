# Independent verification of the pooled-IDCG correction

> **Superseded values note (2026-07-18).** This record verifies the
> pooled-IDCG *methodology* as it stood on 2026-07-16. The specific numeric
> values quoted below (e.g. overall nDCG@10 72.83 / 53.47 / 50.22 / 48.73 /
> 43.61) were subsequently superseded by the marketplace id-normalization
> correction — pools are now keyed by `_norm_id`, giving overall nDCG@10
> **73.78 / 54.24 / 50.81 / 49.24 / 44.06** (@20 **77.28 / 54.50 / 50.41 /
> 49.21 / 43.77**). The authoritative current values live in `cells.json`;
> the correction is documented in `analysis/id_overlap_check/` and the
> pre-correction artifacts are preserved in
> `analysis/_superseded_rawid_pools/`. The methodology findings below
> (exclusion set, orderings, bootstrap provenance) still hold; only the
> marketplace-affected magnitudes moved.

Four independent agents verified this directory's outputs (workflow run
`wf_ec88f271-c29`, 2026-07-16). The numbers verifier and orderings verifier
reimplemented the definition from the spec text alone without reading any
code or reports in this directory.

| Check | Result |
|---|---|
| From-spec reimplementation | CONFIRMED: excluded 47 (marketplace 26, pharmacy 8, fast_fashion 6, cosmetics 3, electronics 2, furniture 2, auto 0; tiers 9/21/17), identical exclusion set at both k, n=1212, strict subset of recall's 200 (gap 153); all ten overall nDCG values match (@10: 72.8327 / 53.4667 / 50.2194 / 48.7296 / 43.6063; @20: 76.0415 / 53.4841 / 49.6054 / 48.5252 / 43.1291); max per-query nDCG exactly 1.0; every hit id present in its query's pool |
| Ordering changes | CONFIRMED: exactly the 12 claimed (cell, k) orderings change; Quissly first in all 22 corrected cells, no ties; medium@20 flip does NOT persist (quissly 68.951 vs doofinder 54.514); Quissly's margin over the best rival widens in every (cell, k) of the design. Extra probe outside the requested design: at sector×tier granularity, cosmetics-medium@10 has Quissly behind Luigi's Box under BOTH definitions (-2.41pp shipped → -2.73pp corrected) |
| Script review (adversarial) | Verdict: sound. Independent from-spec run reproduces cells.json with zero deviation; shipped column matches `compute_rich_metrics` (max dev 2.8e-14 pp); no exclusion leakage; bootstrap harness reproduces all 192 committed cells bit-identically before the nDCG substitution. Non-invalidating notes: the overall clerk/luigisbox "ordering change" starts from a near-tied shipped baseline (0.001pp); summary hardcodes n=1,212; docstring mentions a recall check that actually lives in the merge cross-check |
| Bootstrap outputs | CONFIRMED: 128 precision/recall rows identical to the committed run (p_raw bit-exact); nDCG n = 1212 pooled + correct per-sector; Holm recomputed independently — consistent, m=192; all 8 pooled nDCG observed_diffs reproduced to 6 decimals from per_query_pooled.json; 64/64 nDCG rows significant; 0 status changes. Expected family effect: 8 precision/recall p_holm values decreased (nDCG p_raws shrank, lowering the Holm running max); no significance flag changed anywhere (192/192 significant in both runs) |
