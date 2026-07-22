# Superseded raw-id pool artifacts (2026-07-18)

These are the pre-correction versions of every derived artifact superseded
by the marketplace pool correction (Step 1b, Option 1 — correct before
launch). Cause: pools, Exact pools, and pooled ideals were built by raw id
string, and Quissly's marketplace hits carry dashed UUIDs while the other
four engines carry undashed hex of the same ids — so 1,142 label-consistent
duplicate judgments across 129/180 marketplace queries were double-counted
in recall denominators and pooled ideals (all engines' marketplace recall
understated by 11-24pp, pooled nDCG by 3.5-10pp; ordering and significance
conclusions unaffected). See analysis/id_overlap_check/ID_OVERLAP_REPORT.md
for the full investigation and analysis/id_overlap_check/
CORRECTION_MANIFEST.md for the complete before/after. The authoritative
versions were regenerated in the original locations with `_norm_id`
(lowercase, strip dashes) applied at pool construction. Raw judged data
(labels) is untouched — all duplicates agreed on label.

Note: the `charts/` subfolder archives only the correction-affected
figures (C3–C6, `chart_data.json`, the contact sheet and reconciliation);
C1/C2/C7 and the render scripts were unaffected and live only in
`analysis/charts/`. The archived MANIFEST is a verbatim pre-correction
copy and still references those unarchived files.
