# Marketplace id-spelling overlap check — 2026-07-18

**Question**: Quissly's marketplace hits carry dashed UUIDs while the other
four engines carry undashed hex of the same namespace, and all pools were
built by raw id string. Does any real product appear in a marketplace pool
under two spellings, and what happens to the published numbers when the
pools are normalized?

**Verdict (details below): AFFECTED.** Collisions are pervasive (129/180
marketplace queries), every published marketplace recall and pooled-nDCG
value moves materially when pools are deduplicated (recall by +11 to +24pp
absolute, all engines), and therefore this stops here per the stop
condition: nothing outside `analysis/id_overlap_check/` has been changed,
and the options are presented at the end for a human decision. No
significance status flips and no engine ordering changes — every tested
report-critical comparison gets *stronger* — but the absolute values in the
Appendix B marketplace row and `cells.json` are understated as published.

## 1. Collisions in marketplace

| | |
|---|---:|
| queries with ≥1 collision | **129 / 180** |
| colliding pairs (distinct raw-spelling pairs, same `_norm_id`, same query) | **1,142** |
| pairs that are Quissly-versus-rival | **1,142 (100%)** |
| pairs where the two judgments agree | **1,142 (100%)** |
| label disagreements | **0** — the disagreement table is empty |

The report's "a product returned by several engines is judged once"
guarantee is **empirically violated for marketplace**: 1,142 product
instances across 129 queries were judged twice — once under Quissly's
dashed spelling, once under the rivals' undashed spelling. The violation is
label-silent: every one of the 1,142 double judgments produced the same
label under both spellings, so no judgment contradicts another; the damage
is confined to double-counting in pool construction (denominators and
ideals), not to the labels themselves.

## 2. The other six sectors

| sector | queries with collisions | colliding pairs |
|---|---:|---:|
| auto | 0 | 0 |
| cosmetics | 0 | 0 |
| electronics | 0 | 0 |
| fast_fashion | 0 | 0 |
| furniture | 0 | 0 |
| pharmacy | 3 | **3** (see below) |

Pharmacy's 3 hits are a **different phenomenon**, not the UUID
double-spelling: slug ids differing by one dash (`omez-d-sr-capsule-15-s`
vs `omez-d-sr-capsule-15s` in q_1149; `collashot-c2-capsule-10-s` vs
`collashot-c2-capsule-10s` in q_1250 and q_1192), each pair mostly within a
single engine's own results, labels agreeing in all 3 pairs
(Substitute/Substitute, Exact/Exact, Irrelevant/Irrelevant). Whether these
are two listings of one product or two pack variants, their metric
influence is at most 3 pool entries across 3 queries — negligible — and
`_norm_id` merging them is itself debatable (dash-stripping conflates slug
variants). Recorded here; no remediation attempted.

## 3. Marketplace recomputed under the unified-judgment policy

Policy as specified: normalize every judged id with `_norm_id`; for each
(query, normalized id) with >1 judged record, draw one canonical judgment
with `random.Random(42)` from records sorted by (raw id, engine), applied
to every engine at its recorded ranks; Exact pool and pooled ideal rebuilt
from one canonical gain per normalized id. Since all colliding pairs agree
on label, the draw never actually chooses between different labels.

Before diffing, the raw-id side of the harness was asserted to reproduce
the published numbers **exactly**: all 10 marketplace pooled-nDCG cells in
`analysis/ndcg_pooled/cells.json` to 1e-9, and the committed bootstrap
CSV's recall@10 means (0.365323 / 0.286642, n=103) to the CSV's precision.

Pooled entries across the 180 queries: 8,362 raw → 7,220 unified (the
1,142 duplicates removed). Included-query counts unchanged: recall 103
(Exact-pool non-empty), nDCG 154 (pooled IDCG > 0).

| engine | nDCG@10 | nDCG@20 | recall@10 | recall@20 |
|---|---|---|---|---|
| Quissly | 59.64 → 67.13 | 60.34 → 70.04 | 36.53 → 56.42 | 50.38 → 74.42 |
| Doofinder | 49.81 → 55.88 | 48.68 → 56.70 | 28.66 → 46.56 | 36.56 → 57.75 |
| Luigi's Box | 37.02 → 41.70 | 35.59 → 41.88 | 19.07 → 32.91 | 25.72 → 42.76 |
| Clerk.io | 33.91 → 37.90 | 33.69 → 39.10 | 19.98 → 33.33 | 27.20 → 43.80 |
| Algolia | 28.61 → 32.16 | 28.42 → 33.42 | 15.35 → 26.96 | 22.27 → 37.54 |

Mechanism: the duplicated spellings inflated every query's Exact-pool
denominator and pooled ideal (the same real product contributed gain
twice to IDCG and twice to the recall pool), depressing all engines'
recall and pooled nDCG. Deduplication lifts every engine; because the
duplicated products are by construction products Quissly *and* a rival
both returned and both got right, the correction lifts the leader most.
**Engine ordering is unchanged on every metric at both cutoffs.**

## 4. Report-critical cells: paired bootstrap (B=10,000, seed 42, percentile 95% CI, two-sided p)

Marketplace, Quissly vs Doofinder, resampling unit the query. "Published"
= the committed row in `analysis/ndcg_pooled/bootstrap_results.csv` (and,
for recall@10, the identical row in `analysis/bootstrap/…`); the report
text describes the recall cell as non-significant after its m=236 Holm
family. My raw-id rerun reproduces the observed diffs exactly; CI/p differ
only by Monte-Carlo noise (the committed run consumed one RNG stream
across its whole 192-cell family; this rerun seeds per cell).

| cell | published (raw ids) | raw-id rerun | **unified** |
|---|---|---|---|
| recall@10 diff | +7.87pp, CI [1.52, 14.45], p_raw 0.0142 | +7.87pp, CI [1.64, 14.47], p 0.0120 | **+9.86pp, CI [2.87, 17.49], p 0.0060** |
| nDCG@10 diff | +9.83pp, CI [3.89, 15.87], p_raw 0.0002 | +9.83pp, CI [3.88, 15.64], p 0.0006 | **+11.25pp, CI [5.02, 17.48], p < 0.0002** |
| nDCG@20 diff | +11.67pp, CI [5.53, 17.79], p_raw 0.0002 | +11.67pp, CI [5.42, 17.80], p 0.0000 | **+13.33pp, CI [6.84, 19.82], p < 0.0002** |

Every report-critical comparison moves **further from zero** under
unification, with smaller p-values. Whatever Holm family is applied, a
cell that was significant stays significant, and the recall cell's
evidence strengthens (its raw p drops by half); **no significance status
flips against any published claim.**

## 5. Sensitivity to the tie-break

All 1,142 colliding pairs agree on label, so the canonical draw never
selects between different labels: **the seeded-random tie-break is moot**
and the always-max / always-min recomputation is skipped per the spec.
The unified numbers above are the unique deterministic outcome of any
tie-break policy.

## 6. Verdict

**AFFECTED.** The collisions are real (129 queries, 1,142 double-judged
product instances, all label-consistent), and normalizing the pools moves
every published marketplace recall value by +11 to +24pp absolute and
every pooled-nDCG value by +3.5 to +10pp — far beyond negligible, so the
published Appendix B marketplace row and `cells.json` understate every
engine's marketplace recall and pooled nDCG. Mitigating facts, stated for
the decision: engine ordering is unchanged on every metric, all
report-critical significance results strengthen (nothing flips), the bias
direction is uniform (all engines rise; the gap widens slightly in
Quissly's favor), and the other six sectors are clean, so no non-marketplace
number is implicated. Per the stop condition, nothing has been changed
anywhere; the decision on scope of correction is human:

1. **Correct before launch** (v1.0 is not yet published — the Zenodo DOI
   is a reserved draft and the public repo is not yet initialized):
   recompute the marketplace row of Appendix B / `cells.json` /
   the bootstrap CSVs under normalized ids, with a one-paragraph
   methodology note. Cleanest outcome; no versioned erratum ever needed.
2. **Ship as-is with a disclosed known issue**: publish unchanged, add
   this report to the repo and a caveat to the report text (marketplace
   recall/pooled-nDCG absolute values are conservatively understated;
   ordering and significance unaffected). A labeled correction (Zenodo
   v1.0.1) can follow later if desired.
3. **Hybrid**: ship the benchmark unchanged but include this directory and
   a README caveat, deferring the numeric correction to a v1.1.

A new *labeled Zenodo version* is only forced if the current draft has
already been published — it has not, so option 1 carries no versioning
cost.

## 7. Forward-looking fix (for the record; not implemented)

Version 2's pipeline should apply `_norm_id` at pool-construction time —
when building the judging batches and every pool/ideal — so a product
returned under two spellings is judged once and counted once, making
double-judging structurally impossible. This belongs in the v2
preregistration. Not implemented now; nothing outside
`analysis/id_overlap_check/` was touched.

## Files

- `id_overlap.py` — the complete check (collision finder, six-sector
  sweep, published-number replication asserts, unified recompute,
  bootstrap). Deterministic; run with any Python with numpy.
- `results.json` — machine-readable everything, including all 1,142
  colliding pairs with spellings, engines, and labels.

---

## RESOLUTION (2026-07-18)

**Option 1 taken — corrected before launch** (authorized supersede-and-
preserve, Step 1b). `_norm_id` is now applied at pool construction and
pooled-ideal construction in `pipeline/metrics_dashboard.py`,
`analysis/ndcg_pooled/pooled_ndcg.py` + its bootstrap,
`analysis/bootstrap/paired_bootstrap.py`,
`analysis/report_inputs/report_inputs_core.py`,
`analysis/charts/prepare_data.py`, and the metric paths of both judge
replications. Everything downstream was recomputed (cells.json, both
bootstrap CSVs, the m=236 consolidated Holm pass — now 229/236
significant, marketplace recall@10 vs Doofinder survives — the sector
grid, REPORT_INPUTS tables, figures C3–C6, and both judge metric
comparisons). Raw judged labels untouched. Pre-correction artifacts are
preserved in `analysis/_superseded_rawid_pools/`. The complete before/after
record is **`CORRECTION_MANIFEST.md`** in this directory; document (report
PDF) edits are produced from that manifest separately.
