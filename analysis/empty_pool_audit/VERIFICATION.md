# Independent verification of the empty-pool audit

Four independent agents verified this audit (workflow run `wf_35d2197d-e7a`,
2026-07-16), followed by one fix and a reclassification (no re-judging).

| Check | Result |
|---|---|
| Sampling | CONFIRMED: 200 empty-pool queries (auto 6, cosmetics 11, electronics 13, fast_fashion 35, furniture 17, marketplace 77, pharmacy 41); the 50-qid sample reproduces exactly from the documented procedure (shared `random.Random(42)`, fixed sector order, qid-sorted populations); strata are exactly round(0.25 × sector count) |
| Classification | CONFIRMED: all 50 classes re-derive exactly from the stored per-candidate fields; split table matches cell-for-cell; 0 judge failures across all 1,405 candidates; all 12 worked examples quote real candidates with verbatim judge reasoning |
| Cross-check vs primary sources | CONFIRMED: all 6 fresh-Exact candidates in the 3 engines-missed queries are absent from every engine's judged hits and present in the sector catalogs; all 50 queries genuinely had zero Exact hits in the original run; the 2 judge-inconsistency queries' stale Exacts (q_0807: 1, q_0808: 8) were all originally judged Substitute, never Exact; spot-checked partial-from-returns queries all have real Substitute/Complementary hits in the original data |
| Script review (adversarial) | Verdict: sound, with one CONFIRMED bug (fixed, see below). Also verified: the 'puzzle' 0-candidate case is a no-stemming artifact that correctly landed in inconclusive (retrieval and coverage share the tokenizer, so stemming misses systematically push toward inconclusive, never catalog-gap); all 5 catalog-gap calls survive empirical re-examination; short-token drops ('4k', 'cv', '90') only affected queries that landed in the conservative classes |

## The bug and the fix

The reviewer found that Quissly's marketplace hit ids are dashed UUIDs while
the catalog stores undashed hex, so the `was_returned` join missed all 2,286
quissly marketplace hits ("verified 100% id-join" had only been checked on
electronics). Measured impact: 16 `was_returned` flips, none judged Exact,
**zero classification changes** — the 3 engines-missed queries are in
fast_fashion/furniture where ids join cleanly.

Fix applied: `_norm_id()` (lowercase, strip dashes) on both sides of every
id comparison — after which the id-join is a verified 100% for every engine
in every sector — and `--reclassify` reran classification from the stored
judgments. Split unchanged: engines-missed 3, partial 35, catalog-gap 5,
inconclusive 7; same fresh-exact and judge-inconsistency queries.
