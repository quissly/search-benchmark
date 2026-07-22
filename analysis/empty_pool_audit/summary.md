# Empty-pool audit: did the catalog contain what the engines missed?

Sample: 50 of the 200 recall-excluded queries (no engine returned anything judged Exact), stratified proportionally by sector (auto 2, cosmetics 3, electronics 3, fast_fashion 9, furniture 4, marketplace 19, pharmacy 10), seed 42. Candidates: up to 30 per query by BM25 text matching over the sector's full indexed catalog (datasets/data/normalized/<sector>.parquet; product ids normalized — lowercased, dashes stripped — giving a verified 100% id-join with the benchmark's judged hits for every engine in every sector). Judge: the benchmark's own pipeline.llm_judge.judge_products — gemini-3.5-flash, same per-tier system prompts, same batch format, images included.

**Caveat: this audit's candidate retrieval (BM25 keyword matching) is itself imperfect — it can miss relevant products that better retrieval would find, so the engines-missed count is a LOWER bound; catalog-gap requires confident retrieval and judge-found nothing, and anything weaker is marked inconclusive rather than guessed.**

## Split

| class | overall | auto | cosmetics | electronics | fast_fashion | furniture | marketplace | pharmacy |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| engines-missed | 3 | 0 | 0 | 0 | 1 | 2 | 0 | 0 |
| partial | 35 | 2 | 2 | 3 | 5 | 2 | 12 | 9 |
| catalog-gap | 5 | 0 | 1 | 0 | 1 | 0 | 2 | 1 |
| inconclusive | 7 | 0 | 0 | 0 | 2 | 0 | 5 | 0 |
| **total** | **50** | 2 | 3 | 3 | 9 | 4 | 19 | 10 |

## Worked examples

### engines-missed

- **fast_fashion/q_0077** (medium): “women's high-waisted shorts”
  - best candidate: “Only  Women Black Shorts” → judged **Exact** (gain 1.0); not returned by any engine
  - judge: The product is a pair of women's shorts featuring a high, wide elasticated waistband.
  - 3 in-catalog product(s) judged Exact that no engine returned
- **furniture/q_0364** (complex): “childproof bookshelf with rounded edges and an anti-tip kit included”
  - best candidate: “SONGMICS 3 shelves Toy Storage Organizer, with Compartments, Shelves and Fabric Bins, for Kids Room,” → judged **Exact** (gain 1.0); not returned by any engine
  - judge: This is a children's book and toy storage organizer featuring curved edges and an included anti-tip kit for safety.
  - 2 in-catalog product(s) judged Exact that no engine returned
- **furniture/q_0366** (complex): “height-adjustable standing desk converter for an existing office setup”
  - best candidate: “Canary Products Height Adjustable Sit-Stand Desktop Workstation, 20 Inch Max, Black” → judged **Exact** (gain 1.0); not returned by any engine
  - judge: This is a height-adjustable desktop workstation designed to sit on top of and convert an existing desk.
  - 1 in-catalog product(s) judged Exact that no engine returned

### partial

- **auto/q_1463** (medium): “red silicone vacuum hose”
  - best candidate: “Shineyoo Silicone Vacuum Tubing Hose 6.6 FT, 5/32" (4MM) ID High Performance 130PSI, Engine Automoti” → judged **Substitute** (gain 0.1); originally returned by an engine and judged Substitute
  - judge: The product is a silicone vacuum hose, but it is black instead of the requested red.
  - best available is gain 0.1 (new catalog sweep); no Exact found
- **auto/q_1528** (complex): “CV axles with durable boots for lifted trucks with extreme suspension angles”
  - best candidate: “Heri 79713 New CV Axle” → judged **Substitute** (gain 0.1); originally returned by an engine and judged Irrelevant
  - judge: This is a standard OE-style replacement CV axle, but it is not specifically designed for lifted trucks with extreme suspension angles.
  - best available is gain 0.1 (new catalog sweep); no Exact found
- **cosmetics/q_0912** (simple): “dental floss”
  - best candidate: “Take Care with P&G Brands Oral Hygiene Kit” → judged **Substitute** (gain 0.1); not returned by any engine
  - judge: This is an oral hygiene kit that contains dental floss along with other oral care items, serving the core flossing need.
  - best available is gain 0.1 (new catalog sweep); no Exact found

### catalog-gap

- **cosmetics/q_0949** (simple): “menstrual cup”
  - best candidate: “Brandon M-515 6 in. 5X Suction Cup Mirror” → judged **Irrelevant** (gain 0.0); originally returned by an engine and judged Irrelevant
  - judge: The product is a makeup mirror with a suction cup, which is unrelated to a menstrual cup.
  - nothing above Irrelevant in 30 candidates (best term coverage 0.50) nor in original returns
- **fast_fashion/q_0031** (simple): “bikini”
  - best candidate: “Amante Women Pink Bikini Briefs PCLR02” → judged **Irrelevant** (gain 0.0); originally returned by an engine and judged Irrelevant
  - judge: The product is a pair of underwear (bikini briefs) rather than a bikini swimsuit.
  - nothing above Irrelevant in 30 candidates (best term coverage 1.00) nor in original returns
- **marketplace/q_0736** (simple): “yarn”
  - best candidate: “Great Art Floral Print Wool, Viscose, 20% Kashmiri wool, 50% Cashmilon and 30% Wool ruffle yarn Wome” → judged **Irrelevant** (gain 0.0); originally returned by an engine and judged Irrelevant
  - judge: The product is a finished women's stole (scarf), not the craft material yarn itself.
  - nothing above Irrelevant in 23 candidates (best term coverage 1.00) nor in original returns

### inconclusive

- **fast_fashion/q_0165** (complex): “finding stylish maternity work clothes for the office under $80 per item”
  - best candidate: “Murcia Women Big Office Leather Brown Bag” → judged **Irrelevant** (gain 0.0); not returned by any engine
  - judge: This is an office handbag, not maternity clothing.
  - retrieval too weak to call catalog-gap: 30 candidates, best coverage 0.38, 0 judge failures
- **fast_fashion/q_0180** (complex): “men's dress shirts that don't require ironing for under $60”
  - best candidate: “Gini and Jony Girls Black Dress” → judged **Irrelevant** (gain 0.0); not returned by any engine
  - judge: This is a girls' dress, which is completely irrelevant to the query for men's dress shirts.
  - retrieval too weak to call catalog-gap: 30 candidates, best coverage 0.33, 0 judge failures
- **marketplace/q_0717** (simple): “puzzle”
  - retrieval too weak to call catalog-gap: 0 candidates, best coverage 0.00, 0 judge failures

## Notes

- inconclusive count: 7 of 50 — retrieval or judging too weak to call, reported rather than guessed.
- 'partial' uses BOTH the new catalog sweep and the engines' original returned hits (many empty-pool queries already had Substitutes returned, just nothing Exact).
- an Exact-judged candidate that an engine originally returned (judged differently in the benchmark run) is JUDGE INCONSISTENCY, not an engine miss — such queries are marked inconclusive (2 queries).
- files: audit.json (full per-candidate judgments), this summary. Seed 42.
