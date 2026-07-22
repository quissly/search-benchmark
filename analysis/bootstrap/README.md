# Provenance note — superseded nDCG normalization in this directory

The bootstrap run retained here (`20260718_112921Z/`, the 2026-07-18
normalized-pool rerun; its raw-id predecessor `20260715_070827Z/` is
archived in `analysis/_superseded_rawid_pools/`) keeps the original nDCG
treatment: its `ndcg_at_10` / `ndcg_at_20` rows use the **superseded
self-normalized** definition (IDCG over each engine's own returned hits —
overall values like 82.91 / 73.28 / 67.35 / 67.35 / 54.80), NOT the
pooled-ideal definition used in the published report. It is retained for
provenance: its precision and recall rows are valid and are the source of
the recall CIs used in the published significance tables.

**Authoritative statistics live in:**

- `analysis/ndcg_pooled/` — pooled-ideal nDCG per-query scores, cells, and
  the corrected bootstrap (`bootstrap_results.csv`), and
- `analysis/report_inputs/consolidated_holm.csv` — the single consolidated
  236-test Holm family (229 significant) that the report cites.

The live pipeline (`pipeline/metrics_dashboard.py`) has since been patched
to the pooled-ideal definition and reproduces `analysis/ndcg_pooled/cells.json`
exactly — this directory is now the ONLY place the superseded normalization
survives. Do not quote nDCG numbers from this directory.
