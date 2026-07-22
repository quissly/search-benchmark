# Chart manifest — Quissly Search Benchmark report figures

## Palette (extracted, used identically in every chart)

Source: `client/src/pages/comparison/data.ts` lines 28–32 in the sibling
`website` repo (checked out beside this repo)
(`ENGINE_META`, the interactive benchmark page's per-engine mapping — reused
exactly per the palette rule; the `#C5E73B` fallback was NOT needed):

| engine | hex |
|---|---|
| Quissly | `#6366f1` |
| Doofinder | `#ef4444` |
| Algolia | `#f59e0b` |
| Luigi's Box | `#10b981` |
| Clerk.io | `#ec4899` |

Supporting colors: text/axes ink `#141414` (brand token); C2 "All results
junk" warning tone `#7c2d12` (chosen distinct from all five engine colors);
"No results" `#d4d4d8`; C7 neutral `#64748b`.

Font: the site uses `'General Sans'` with system-sans fallbacks
(`../website/client/src/pages/comparison/comparison.css:42`). General Sans
is not installed on this machine and is not a standard sans, so per the
fallback rule the charts use **Helvetica Neue** (the effective member of the
site's own `-apple-system` fallback chain on macOS). SVG text is not
converted to paths, so a viewer with General Sans available could restyle.

## Figure numbering (locked) and captions (verbatim, live in the document, never in the image)

| file | figure |
|---|---|
| C1_ezr | Figure 1. Effective zero-result rate, pooled and by complexity tier (n = 1,259 queries per engine). |
| C2_outcomes | Figure 2. Outcome of every query by tier: useful results, all-junk results, or nothing returned. |
| C3_ndcg | Figure 3. Pooled-ideal nDCG@10 by complexity tier. |
| C4_recall | Figure 4. Pooled recall@20 by complexity tier. |
| C6_sectors | Figure 5. Effective zero-result rate and pooled-ideal nDCG@10 by sector. |
| C5_forest | Figure 6. Pooled differences from Quissly with 95% confidence intervals, Holm-corrected family. |
| C7_audit | (no figure number — web use only, excluded from the report) |

## Data sources per chart

- C1, C2: recomputed from `comparison_final_judged/judged/*.json.gz`
  (EZR / zero-result / all-junk per engine per tier).
- C3: `analysis/ndcg_pooled/cells.json` complexity cells (nDCG is NEVER
  sourced from the website bundle, whose nDCG values are stale).
- C4: recomputed from the judged files (pooled recall@20 per tier).
- C5: EZR CIs from `analysis/ezr_bootstrap/ezr_results.csv` (pooled rows,
  sign flipped to rival-minus-Quissly); nDCG@10 CIs from
  `analysis/ndcg_pooled/bootstrap_results.csv` (pooled rows); Recall@20 CIs
  from the committed `analysis/bootstrap/20260718_112921Z/
  bootstrap_results.csv` (the 2026-07-18 normalized-pool run; its raw-id
  predecessor is archived in `analysis/_superseded_rawid_pools/`).
- C6: `analysis/report_inputs/sector_grid.json`, every cell reconciled
  against the ASK-1 tables in `analysis/report_inputs/REPORT_INPUTS.md`.
- C7: `analysis/empty_pool_audit/audit.json` class counts.

## Reconciliation

**All 177 checks PASS** — full list with computed-vs-expected values in
`analysis/charts/reconciliation.md`. The gate aborts rendering on any
mismatch. Four checks matched under the report's truncation-to-2dp
convention rather than rounding (C1/C2 EZR: Quissly simple 2.1053→"2.10",
Luigi's Box simple 6.5263→"6.52", Algolia medium 30.9168→"30.91", Algolia
complex 96.5079→"96.50"); max deviation 0.008 pp, and at the 1-decimal
precision displayed in the charts both conventions agree exactly.

## Final pixel dimensions (PNG, 300 DPI, = stated print size)

| file | inches | pixels |
|---|---|---|
| C1_ezr | 7.0 × 4.2 | 2100 × 1260 |
| C2_outcomes | 6.5 × 7.5 | 1950 × 2250 |
| C3_ndcg | 6.5 × 4.0 | 1950 × 1200 |
| C4_recall | 6.5 × 4.0 | 1950 × 1200 |
| C5_forest | 6.5 × 6.5 | 1950 × 1950 |
| C6_sectors | 6.5 × 4.8 | 1950 × 1440 |
| C7_audit | 6.5 × 2.6 | 1950 × 780 |

## SVG vector-text confirmation

Rendered with `svg.fonttype: none` (text stays text, never rasterized or
outlined):

- C1_ezr.svg: vector text confirmed (41 `<text>` elements)
- C2_outcomes.svg: vector text confirmed (60 `<text>` elements)
- C3_ndcg.svg: vector text confirmed (32 `<text>` elements)
- C4_recall.svg: vector text confirmed (36 `<text>` elements)
- C5_forest.svg: vector text confirmed (38 `<text>` elements)
- C6_sectors.svg: vector text confirmed (94 `<text>` elements)
- C7_audit.svg: vector text confirmed (19 `<text>` elements)

## Label-size and layout notes (8 pt rule)

- Minimum text size used anywhere is 8 pt at print size (C2/C6 cell and
  segment labels, C1 bar values); nothing falls below 8 pt. The C2 footnote
  and C5 notes are 7.5–8 pt small-type by design (footnote/caption class).
- C2: stacked-bar segments **below 4.0 %** carry no in-segment label (an
  8 pt label cannot fit); the unlabeled segments are Quissly simple
  (junk 1.9, zero 0.2), Doofinder simple zero 0.2 / medium zero 0.0 /
  complex zero 0.0, Clerk.io zero segments (0.6 / 0.2 / 0.6), Luigi's Box
  simple zero 1.5, Algolia simple zero 1.5 and complex useful 3.5 /
  junk 0.6, Quissly complex junk 2.5. Every value is recoverable from the
  two labeled segments (bars sum to 100).
- C2 has no spec-provided in-image title; the baked title is "Outcome of
  every query: useful, all-junk, or nothing" (echoes the caption without
  the figure number). The legend's "Useful results" swatch is a neutral
  gray proxy because that series is engine-colored per bar.
- C1's four-shade legend (Pooled/Simple/Medium/Complex) uses neutral gray
  tints as proxies for the per-engine color tints, mirroring the website
  dashboard's legend-stub convention.
- C5 prints point estimates at 1 dp beside each marker; the EZR sign flip
  is stated in the in-figure note above the axes.

## Render provenance

`prepare_data.py` (reconciliation gate; writes `chart_data.json` only if
all checks pass) → `render_charts.py` (matplotlib 3.10.9, Python 3.14.4,
Agg backend). Contact sheet: `contact_sheet.png`. Every PNG was opened and
inspected at full resolution before finishing; one legend/annotation
collision found in C4 and fixed (annotation height now capped inside the
axes), and the C2 segment-label threshold was tightened from 4.5 % to
4.0 % for consistency (Algolia simple junk 4.4 now labeled like Clerk.io's
4.6).
