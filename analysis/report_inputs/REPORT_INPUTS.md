# Report inputs — consolidated deliverable

> **Errata (2026-07-20).** Recorded deliverable, kept as assembled; four
> points have since been superseded: (1) ASK-5's "no generator script
> exists" — `queries/query_generator.py` has since been added; (2) ASK-7's
> "a 2.5-era judgment set would have to be regenerated" — full re-judges
> now ship in `analysis/judge_stability/` and `analysis/judge_claude/`;
> (3) the ASK-3 note's marketplace recall@10 example (p_holm 0.0994,
> non-significant) predates the 2026-07-18 marketplace pool correction —
> the cell is now significant (p_holm 0.0416; `consolidated_holm.csv` is
> authoritative); (4) line-number citations into README.md and providers.py
> have drifted with later edits.

Everything below was produced read-only from this repo, the datasets repo, and the published website bundle; all new files live in `analysis/report_inputs/`. Machine-readable companions: `sector_grid.json`, `consolidated_holm.csv`. Where something is not on disk it is marked **not found on disk, needs human input** rather than guessed.

Python 3.14.4, numpy 2.5.1, pandas 3.0.3. Seeds: bootstrap seed 42 (B=10,000) in all three bootstrap CSVs; empty-pool-audit sampling seed 42; consolidated Holm is deterministic (no resampling).

---

## Reconciliation gate

- quissly: EZR 93/1259  corrected nDCG@10/@20 = 73.78/77.28  -> match
- doofinder: EZR 149/1259  corrected nDCG@10/@20 = 54.24/54.50  -> match
- luigisbox: EZR 308/1259  corrected nDCG@10/@20 = 50.81/50.41  -> match
- clerk: EZR 249/1259  corrected nDCG@10/@20 = 49.24/49.21  -> match
- algolia: EZR 477/1259  corrected nDCG@10/@20 = 44.06/43.77  -> match
- populations: total 1259, corrected-nDCG 1212 (exclusions {'cosmetics': 3, 'electronics': 2, 'fast_fashion': 6, 'furniture': 2, 'marketplace': 26, 'pharmacy': 8}), recall 1059 -> match
- published bundle cross-check: recall n per engine = 1,059; zero-result(CSV) + all-junk(bundle rich) reproduces every EZR count -> match

**GATE PASSED — all expected values reproduced from raw judged data and cross-checked against the published bundle.**

---

## ASK-1 — Full per-sector grid

All percentages to 2 decimals. n's: EZR/coverage over all sector queries; junk over answered queries (>=1 hit); recall over pool>0 queries; corrected nDCG over pooled-IDCG>0 queries.

### auto (queries 180, recall pool n 174, nDCG included n 180)

| engine | EZR | coverage | junk@10 | junk@20 | (junk n) | recall@10 | recall@20 | nDCG@10 | nDCG@20 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| quissly | 0.00% (0/180) | 100.00% (180/180) | 9.83% | 11.50% | 180 | 37.15% | 59.62% | 80.06 | 82.74 |
| doofinder | 2.22% (4/180) | 100.00% (180/180) | 18.69% | 20.72% | 180 | 26.37% | 40.85% | 59.54 | 60.91 |
| luigisbox | 12.78% (23/180) | 92.78% (167/180) | 13.21% | 15.75% | 167 | 23.64% | 35.41% | 57.30 | 56.75 |
| clerk | 6.67% (12/180) | 100.00% (180/180) | 22.11% | 23.68% | 180 | 25.10% | 38.89% | 58.11 | 59.08 |
| algolia | 26.67% (48/180) | 74.44% (134/180) | 9.67% | 11.58% | 134 | 21.79% | 33.21% | 51.06 | 51.36 |

### cosmetics (queries 180, recall pool n 169, nDCG included n 177)

| engine | EZR | coverage | junk@10 | junk@20 | (junk n) | recall@10 | recall@20 | nDCG@10 | nDCG@20 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| quissly | 1.67% (3/180) | 99.44% (179/180) | 9.98% | 12.55% | 179 | 36.50% | 61.23% | 79.07 | 81.38 |
| doofinder | 2.78% (5/180) | 100.00% (180/180) | 18.39% | 22.40% | 180 | 27.91% | 43.26% | 66.24 | 64.74 |
| luigisbox | 12.78% (23/180) | 95.56% (172/180) | 16.86% | 18.30% | 172 | 26.64% | 41.83% | 62.74 | 61.75 |
| clerk | 5.56% (10/180) | 100.00% (180/180) | 22.39% | 25.34% | 180 | 24.97% | 39.45% | 58.26 | 57.54 |
| algolia | 30.56% (55/180) | 71.67% (129/180) | 10.63% | 13.59% | 129 | 21.26% | 33.75% | 53.12 | 51.96 |

### electronics (queries 180, recall pool n 167, nDCG included n 178)

| engine | EZR | coverage | junk@10 | junk@20 | (junk n) | recall@10 | recall@20 | nDCG@10 | nDCG@20 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| quissly | 2.22% (4/180) | 98.89% (178/180) | 14.28% | 16.41% | 178 | 45.83% | 67.72% | 76.00 | 79.49 |
| doofinder | 2.22% (4/180) | 100.00% (180/180) | 23.80% | 26.71% | 180 | 28.07% | 40.38% | 51.37 | 52.37 |
| luigisbox | 16.67% (30/180) | 90.56% (163/180) | 21.00% | 23.30% | 163 | 27.20% | 37.98% | 50.11 | 50.23 |
| clerk | 9.44% (17/180) | 100.00% (180/180) | 31.07% | 33.38% | 180 | 26.20% | 38.42% | 49.17 | 49.24 |
| algolia | 26.11% (47/180) | 75.56% (136/180) | 15.24% | 18.54% | 136 | 25.65% | 35.10% | 46.45 | 46.00 |

### fast_fashion (queries 180, recall pool n 145, nDCG included n 174)

| engine | EZR | coverage | junk@10 | junk@20 | (junk n) | recall@10 | recall@20 | nDCG@10 | nDCG@20 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| quissly | 8.33% (15/180) | 93.89% (169/180) | 17.10% | 18.28% | 169 | 38.18% | 61.36% | 69.35 | 74.17 |
| doofinder | 16.11% (29/180) | 100.00% (180/180) | 40.94% | 44.57% | 180 | 20.30% | 32.78% | 49.20 | 49.56 |
| luigisbox | 40.00% (72/180) | 75.00% (135/180) | 30.07% | 31.86% | 135 | 19.24% | 29.01% | 44.40 | 43.44 |
| clerk | 27.78% (50/180) | 100.00% (180/180) | 47.76% | 49.38% | 180 | 18.26% | 27.94% | 43.66 | 43.00 |
| algolia | 47.22% (85/180) | 59.44% (107/180) | 26.42% | 27.42% | 107 | 18.37% | 27.32% | 39.87 | 39.02 |

### furniture (queries 179, recall pool n 162, nDCG included n 177)

| engine | EZR | coverage | junk@10 | junk@20 | (junk n) | recall@10 | recall@20 | nDCG@10 | nDCG@20 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| quissly | 1.68% (3/179) | 100.00% (179/179) | 11.34% | 13.61% | 179 | 47.19% | 72.22% | 76.86 | 81.20 |
| doofinder | 2.79% (5/179) | 100.00% (179/179) | 18.88% | 21.96% | 179 | 33.06% | 49.43% | 57.93 | 58.22 |
| luigisbox | 12.85% (23/179) | 89.94% (161/179) | 13.07% | 14.40% | 161 | 30.84% | 45.60% | 55.47 | 55.26 |
| clerk | 9.50% (17/179) | 100.00% (179/179) | 26.13% | 28.67% | 179 | 33.57% | 47.72% | 52.73 | 52.95 |
| algolia | 27.93% (50/179) | 74.86% (134/179) | 14.42% | 16.93% | 134 | 27.20% | 41.65% | 47.06 | 47.43 |

### marketplace (queries 180, recall pool n 103, nDCG included n 154)

| engine | EZR | coverage | junk@10 | junk@20 | (junk n) | recall@10 | recall@20 | nDCG@10 | nDCG@20 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| quissly | 23.89% (43/180) | 85.56% (154/180) | 31.64% | 33.23% | 154 | 56.42% | 74.42% | 67.13 | 70.04 |
| doofinder | 26.11% (47/180) | 100.00% (180/180) | 50.75% | 54.41% | 180 | 46.56% | 57.75% | 55.88 | 56.70 |
| luigisbox | 48.89% (88/180) | 68.89% (124/180) | 38.96% | 39.82% | 124 | 32.90% | 42.76% | 41.70 | 41.88 |
| clerk | 46.67% (84/180) | 99.44% (179/180) | 64.30% | 65.82% | 179 | 33.33% | 43.80% | 37.90 | 39.10 |
| algolia | 58.33% (105/180) | 50.56% (91/180) | 38.14% | 40.07% | 91 | 26.96% | 37.54% | 32.16 | 33.42 |

### pharmacy (queries 180, recall pool n 139, nDCG included n 172)

| engine | EZR | coverage | junk@10 | junk@20 | (junk n) | recall@10 | recall@20 | nDCG@10 | nDCG@20 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| quissly | 13.89% (25/180) | 97.78% (176/180) | 26.53% | 27.74% | 176 | 44.00% | 65.20% | 66.75 | 70.62 |
| doofinder | 30.56% (55/180) | 99.44% (179/180) | 51.49% | 53.45% | 179 | 19.68% | 30.89% | 39.12 | 38.68 |
| luigisbox | 27.22% (49/180) | 91.11% (164/180) | 38.80% | 41.91% | 164 | 23.16% | 31.90% | 42.34 | 41.97 |
| clerk | 32.78% (59/180) | 97.22% (175/180) | 47.34% | 50.85% | 175 | 21.86% | 30.56% | 42.92 | 41.78 |
| algolia | 48.33% (87/180) | 60.56% (109/180) | 28.78% | 33.10% | 109 | 20.86% | 27.24% | 36.74 | 35.37 |

Sanity: weighted sector aggregation reproduces the pooled value for EZR (exact counts), junk@10, recall@20 and nDCG@10 for all engines (quissly, doofinder, luigisbox, clerk, algolia) within 2-decimal rounding.

---

## ASK-2 — Corrected pooled-IDCG nDCG by complexity tier

| engine | simple @10 / @20 (n=466) | medium @10 / @20 (n=448) | complex @10 / @20 (n=298) |
|---|---:|---:|---:|
| quissly | 91.02 / 91.64 | 65.93 / 70.75 | 58.65 / 64.62 |
| doofinder | 72.39 / 72.25 | 55.78 / 56.00 | 23.53 / 24.51 |
| luigisbox | 70.64 / 70.57 | 55.90 / 55.43 | 12.17 / 11.33 |
| clerk | 66.57 / 66.95 | 51.01 / 50.34 | 19.46 / 19.78 |
| algolia | 67.54 / 68.42 | 48.17 / 46.57 | 1.16 / 1.00 |

### 8 narrowest significant margins in the corrected bootstrap (any metric, any scope; family m=192, seed 42)

Note: significance here is within the corrected bootstrap's own m=192 family; the consolidated m=236 pass is ASK-3.

- precision_at_10 / marketplace / quissly_vs_doofinder: diff +5.41 pp [2.11, 9.06], p_holm=0.0036
- precision_at_20 / marketplace / quissly_vs_doofinder: diff +6.43 pp [2.94, 10.16], p_holm=0.0036
- precision_at_20 / marketplace / quissly_vs_luigisbox: diff +6.84 pp [2.58, 11.32], p_holm=0.0036
- precision_at_20 / furniture / quissly_vs_luigisbox: diff +6.91 pp [2.70, 11.10], p_holm=0.0036
- precision_at_10 / marketplace / quissly_vs_luigisbox: diff +8.09 pp [3.87, 12.54], p_holm=0.0036
- recall_at_10 / cosmetics / quissly_vs_doofinder: diff +8.59 pp [5.50, 12.05], p_holm=0
- precision_at_10 / cosmetics / quissly_vs_doofinder: diff +8.78 pp [5.53, 12.13], p_holm=0
- precision_at_20 / cosmetics / quissly_vs_luigisbox: diff +9.17 pp [5.87, 12.64], p_holm=0

---

## ASK-3 — One consolidated Holm pass across all 236 tests

Family: 128 precision/recall tests (original grid, p_raw bit-identical in both bootstrap CSVs — verified), 64 nDCG tests with CORRECTED pooled-IDCG scores (analysis/ndcg_pooled/bootstrap_results.csv), 44 effective zero-rate tests (analysis/ezr_bootstrap/ezr_results.csv). Provenance verified: row counts 64+64+64+44, seed 42 and B=10,000 in every row. No resampling performed — single Holm-Bonferroni pass over the 236 committed p_raw values.

**229 of 236 significant after Holm; 7 not significant.**

| source | metric | scope | pair | diff pp | 95% CI | p_raw | p_holm |
|---|---|---|---|---:|---|---:|---:|
| ezr | effective_zero_rate | auto | vs doofinder | -2.22 | [-4.44, -0.56] | 0.034 | 0.204 |
| ezr | effective_zero_rate | cosmetics | vs doofinder | -1.11 | [-2.78, 0.00] | 0.2656 | 1 |
| ezr | effective_zero_rate | electronics | vs doofinder | +0.00 | [-1.67, 1.67] | 1 | 1 |
| ezr | effective_zero_rate | fast_fashion | vs doofinder | -7.78 | [-13.89, -2.22] | 0.0094 | 0.0658 |
| ezr | effective_zero_rate | furniture | vs doofinder | -1.12 | [-2.79, 0.00] | 0.2664 | 1 |
| ezr | effective_zero_rate | marketplace | vs doofinder | -2.22 | [-8.89, 4.44] | 0.5506 | 1 |
| ezr | effective_zero_rate | tier_complex | vs doofinder | -4.44 | [-9.21, 0.00] | 0.0692 | 0.346 |

### The marketplace-vs-Doofinder questions

- ndcg_at_10 (corrected scores): p_raw=0, p_holm=0 -> **SURVIVES** (under the old self-normalized scores these cells had p_raw 0.0162/0.0454, p_holm 0.0426/0.0454 at m=192, and died at m=236; corrected diffs are much larger).
- ndcg_at_20 (corrected scores): p_raw=0.0002, p_holm=0.0036 -> **SURVIVES** (under the old self-normalized scores these cells had p_raw 0.0162/0.0454, p_holm 0.0426/0.0454 at m=192, and died at m=236; corrected diffs are much larger).
- recall_at_10 (normalized pools): p_raw=0.0052, p_holm=0.0416 -> **now significant** (raw-id pools: p_raw 0.0142, non-significant at m=236).

---

## ASK-4 — Catalogs

**Per-sector product counts** (`$CATALOG_DIR/data/normalized/<sector>.parquet`, row counts):

| sector | products |
|---|---:|
| auto | 50,000 |
| cosmetics | 50,000 |
| electronics | 50,000 |
| fast_fashion | 44,417 |
| furniture | 49,999 |
| marketplace | 20,000 |
| pharmacy | 23,939 |
| (luxury_fashion — in the datasets repo but NOT used in this benchmark) | 5,000 |

Benchmark total (7 used sectors): 288,355 products.

**Indexing scripts: not found on disk, needs human input.** The datasets repo
is acquisition+normalization only (its README states there is no search
engine in it); this repo has no upload/index/ingest code in the working tree
or in any of its 3 git commits; Quissly's own service code contains no
Algolia/Doofinder/Luigi's Box/Clerk.io references; and the feed files the
code names (`data/<sector>_quissly.json`, `electronics_quissly.json` in
providers.py:74) were not retained. The catalogs were indexed
into the 5 engines out-of-band.

**Fields per engine — read-side evidence only** (from `providers.py`, the
search-time adapters; the exact pushed fields need human input):

- **Quissly** (providers.py:106-120): id, title, metadata.brand, category, images[], image, description, url, original_price, discounted_price.
- **Algolia** (:141-148): same Quissly-shaped document (id, title, metadata.brandName, category, images[], description, url, original_price, discounted_price) — consistent with a shared JSON feed.
- **Doofinder** (:177-178, the most direct indexing evidence on disk — a comment listing the CSV feed columns): `id,title,description,link,image_link,images,price,sale_price,availability,brand,category,categories,specs,metadata`.
- **Luigi's Box** (:229-244): product id stored in the `url` field (comment: "identity we indexed (product id)"); attributes: title, brand, category, image_link, images[], description, web_url, price, price_old.
- **Clerk.io** (:261-263): products uploaded with label "Benchmark" (search filters on `labels:["Benchmark"]`); attributes: id, name, description, image, url, price, list_price, brand, category.

**Provenance on disk** (`datasets/README.md` sources+licenses table, FILES.md, fetch.py):

| sector(s) | source | license as listed |
|---|---|---|
| furniture, auto, electronics, cosmetics | HuggingFace McAuley-Lab/Amazon-Reviews-2023 (raw_meta_* categories, streamed JSONL capped at 50k) | CC BY-SA 4.0 |
| pharmacy | Kaggle drowsyng/medicines-dataset (Netmeds scrape) | Apache-2.0 |
| fast_fashion | Kaggle paramaggarwal/fashion-product-images-dataset (Myntra); images deliberately NOT extracted | MIT |
| marketplace | Kaggle atharvjairath/flipkart-ecommerce-dataset | CC0-1.0 |

Per-row provenance is embedded in the parquet `source` column (e.g.
`huggingface:McAuley-Lab/Amazon-Reviews-2023:raw_meta_Automotive`).

**Redistribution flags:**
1. `datasets/README.md:60`: "Licenses are reported as shown by the source at fetch time; verify before redistribution" — the stated licenses are re-uploader claims, not verified grants.
2. The four Amazon sectors (199,999 rows, ~69% of the 288,355-product benchmark corpus) are CC BY-SA 4.0 — share-alike + attribution obligations.
3. Scraped upstreams: pharmacy = Netmeds scrape, fast_fashion = Myntra, marketplace = Flipkart; the permissive Kaggle licenses come from re-uploaders, not the retailers. Kaggle acquisition also requires a Kaggle account/token (Kaggle ToS).
4. Image URLs are hotlinks to third-party CDNs (Amazon media, myntassets, Flipkart, Netmeds); image content is NOT covered by the dataset licenses (the repo enforces URL-only, never bytes).
5. The datasets repo itself declines to publish: `.gitignore` excludes `data/raw/` and `data/normalized/`, committing only ~300-row samples. Caution: `datasets/data.zip` (283 MB, the full normalized catalogs) is untracked and NOT gitignored — a careless `git add .` would publish it.

**Net: the catalogs are not clearly safe to redistribute in a public repo
as-is** — Amazon sectors need CC BY-SA 4.0 compliance at minimum, and the
Kaggle-sourced sectors rest on unverified re-uploader licenses.

---

## ASK-5 — Queries

**Generation prompt: not found on disk, needs human input.** No generator
script or prompt file exists in the repo or its git history (the query files
arrive fully formed in the initial commit; no deleted files in history). The
only on-disk record is this description, README.md:68-73, quoted verbatim:

> The per-sector query files live in `queries/query_outputs/`. They were
> generated with Gemini 2.5 Pro: for each sector and tier, the model was prompted
> with tier-specific rules (word count, required attributes, or natural-language
> intent shapes such as problem-solution / relational / budget-constrained)
> plus a few handwritten seed examples, and returned a JSON array of query
> strings.

**Generation model:** Gemini 2.5 Pro (README.md:69, :179-180, :203;
`config.example.env` groups GEMINI_API_KEY under "LLM judge (and query generation)").
Distinct from the judge model (gemini-3.5-flash).

**Tier assignment: at generation time, not post-hoc.** The model was prompted
separately per (sector, tier); structurally, every sector file stores each
tier as a perfectly contiguous, non-interleaved query_id block in fixed order
simple → medium → complex (e.g. electronics: simple q_0450–q_0517, medium
q_0518–q_0584, complex q_0585–q_0629) — consistent with per-batch generation
and impossible under post-hoc classification of a mixed pool. Downstream code
only consumes the stored label (llm_judge.py selects the tier-specific judge
prompt from `entry["complexity"]`).

**Why 475/469/315 and not 60/60/60:** the generation quotas were never
60/60/60 — every sector file contains exactly **68 simple + 67 medium + 45
complex** = 180 (furniture: 67 simple = 179). The judged files match these
counts exactly, sector by sector — zero attrition between generation, running
and judging. Arithmetic: simple 7×68−1 = 475, medium 7×67 = 469, complex
7×45 = 315. The ~38/37/25 tier weighting was a generation-time quota
decision.

**Why furniture has 179:** the shortfall is in the source query file itself
(`furniture_queries.json`: 179 queries, 67 simple vs 68 everywhere else);
the judged file matches it exactly, so nothing was dropped at run or judge
time. No duplicates, no empty texts, no gaps inside the range. The tell is an
ID-numbering off-by-one at the sector block boundary: sectors occupy 225-wide
ID blocks; fashion numbers base+1..base+180, five other sectors
base+0..base+179, and furniture uniquely mixes the conventions — starts at
base+1 (q_0226) but ends at base+179 (q_0404), losing exactly one simple-tier
slot. `q_0225` appears in no query or judged file (verified). The exact mechanism
(generator off-by-one) is not on disk — needs human input for certainty.

**3 real examples per tier:**

| tier | sector | query |
|---|---|---|
| simple | electronics | webcam |
| simple | pharmacy | Prilosec |
| simple | furniture | plant stand |
| medium | electronics | waterproof action camera |
| medium | auto | remanufactured starter motor |
| medium | cosmetics | long-lasting floral perfume |
| complex | auto | what causes a strong smell of gasoline inside the car cabin |
| complex | furniture | outdoor bistro set for a small apartment balcony under $150 |
| complex | fast_fashion | appropriate and respectful outfit for attending a funeral |

---

## ASK-6 — Label -> gain mapping

Exact code (`pipeline/llm_judge.py`):

```python
# ESCI-style graded relevance: label -> gain
GAIN_MAP = {
    "exact":         1.0,
    "substitute":    0.1,
    "complementary": 0.01,
    "complement":    0.01,  # tolerate the ESCI spelling
    "irrelevant":    0.0,
}
```

Distinct label strings actually present in the judged data:

| label | count |
|---|---:|
| Exact | 46,738 |
| Irrelevant | 26,894 |
| Substitute | 14,071 |
| Complementary | 11,465 |
| **total judged hits** | **99,168** |

Confirmed: only the four canonical strings occur, mapping Exact=1.0, Substitute=0.1, Complementary=0.01, Irrelevant=0.0.

### Judging prompts, verbatim (pipeline/llm_judge.py)

#### Simple tier (`SYSTEM_PROMPT_SIMPLE`)

```
You are an objective e-commerce relevance judge. The user typed a short, single-concept query (e.g. "webcam", "lipstick", "brake pads", "office chair", "ibuprofen").

You will be provided with the query and a numbered list of products. Each product has details (title, description, price, discounted price) and may be preceded by its image - each image belongs to the product whose numbered text block immediately follows it. Judge EACH product independently against the query: never compare products to one another, and never let the rest of the list influence a product's label.

Assign exactly one of four relevance labels:

Exact - the product IS that exact item or a direct variant of it (e.g. "headphones" → over-ear headphones, on-ear headphones, wireless headphones; "ibuprofen" → any brand, strength, or pack size of ibuprofen; "lipstick" → any shade or finish of lipstick). Variants in size, count, dosage strength, color/shade, or flavor are still Exact. The image confirms the product is the right item when the title is ambiguous.

Substitute - the product is not the queried item but is functionally similar and could serve the same core need (e.g. "headphones" → earbuds; "ibuprofen" → a different pain reliever such as acetaminophen; "sofa" → a loveseat).

Complementary - the product is an accessory, replacement part, refill, or add-on used WITH the queried item rather than being the item itself (e.g. "headphones" → headphone stand, headphone cable, ear pads; "razor" → razor blade refills; "bed frame" → mattress).

Irrelevant - the product merely shares a keyword but belongs to a different category or serves a different audience/need (e.g. "webcam" → webcam cover sticker; "dog shampoo" → human shampoo), or the image clearly shows something other than the queried item.

Be strict: accessories and peripherals are Complementary, never Exact.

Output ONLY a JSON array with exactly one object per product, in the same numbered order: [{"index": <product number>, "label": "Exact" | "Substitute" | "Complementary" | "Irrelevant", "reasoning": "brief 1-sentence explanation"}, ...]
```

#### Medium tier (`SYSTEM_PROMPT_MEDIUM`)

```
You are an objective e-commerce relevance judge. The user typed a multi-word query specifying a product type plus one or more concrete attributes (e.g. "waterproof action camera", "oil-free face moisturizer", "ceramic brake pads for a Honda Civic", "king size wooden bed frame").

You will be provided with the query and a numbered list of products. Each product has details (title, description, price, discounted price) and may be preceded by its image - each image belongs to the product whose numbered text block immediately follows it. Judge EACH product independently against the query: never compare products to one another, and never let the rest of the list influence a product's label.

Assign exactly one of four relevance labels:

Exact - the product is the correct product type AND plausibly has the key attribute(s) stated in the query. This includes widely known products whose brand/model implies the attribute (e.g. GoPro Hero → waterproof action camera), and products of the correct type that could reasonably satisfy the user's need even if the specific attribute is not explicitly stated (e.g. "noise-cancelling sport earbuds" → Sony LinkBuds S are earbuds with ANC). The image confirms type and attributes when text is ambiguous.

Substitute - the product is the correct (or a closely related) product type but clearly lacks a key queried attribute, or is a functionally similar alternative that could still serve the user's core need (e.g. "portable USB-C monitor" → a portable HDMI-only monitor; "brake pads for a Honda Civic" → brake pads that fit a different vehicle; "oil-free moisturizer" → an oil-based moisturizer). A product made for a clearly different compatibility target stated in the query (car model, phone model, cartridge number, dosage) lacks a key attribute.

Complementary - the product is an accessory, mount, case, cable, refill, or add-on used WITH the queried item rather than the item itself (e.g. "waterproof action camera" → action camera chest mount; "king size bed frame" → king size mattress protector).

Irrelevant - the product is the wrong type entirely and does not serve the queried need, even if it shares an attribute keyword (e.g. "waterproof action camera" → waterproof phone case; "ceramic brake pads" → ceramic cookware), or the image clearly shows an unrelated product category.

Price constraint: if the query states a price restriction (e.g. "under $50", "for $20"), treat it as a key attribute. Compare against the Discounted Price when available, otherwise the Price; a product that would otherwise be Exact but exceeds the stated budget is Substitute, not Exact.

Output ONLY a JSON array with exactly one object per product, in the same numbered order: [{"index": <product number>, "label": "Exact" | "Substitute" | "Complementary" | "Irrelevant", "reasoning": "brief 1-sentence explanation"}, ...]
```

#### Complex tier (`SYSTEM_PROMPT_COMPLEX`)

```
You are an objective e-commerce relevance judge. The user typed a natural-language problem or question (e.g. "how to best manage and hide cables for a wall-mounted TV", "what helps with dandruff and an itchy scalp", "my brakes squeak when I stop").

Your job is to infer what product category would solve the problem, then judge whether each given product belongs to that category.

You will be provided with the query and a numbered list of products. Each product has details (title, description, price, discounted price) and may be preceded by its image - each image belongs to the product whose numbered text block immediately follows it. Judge EACH product independently against the query: never compare products to one another, and never let the rest of the list influence a product's label.

Assign exactly one of four relevance labels:

Exact - the product is a primary solution to the described problem (e.g. cable management query → cable raceway, cable clips, cable box; dandruff query → anti-dandruff shampoo; squeaky brakes → brake pads, anti-squeal shims). Its function directly addresses the user's stated need, even if the exact words differ; the image confirms it is a practical solution.

Substitute - the product is an alternative or partial solution: it addresses the problem, but less directly or less completely than a primary solution would (e.g. a general-purpose solution when a purpose-built one exists; dandruff query → a general scalp moisturizer).

Complementary - the product does not itself solve the problem but would naturally be used alongside the solution or the equipment mentioned in the query (e.g. wall-mounted TV cable query → TV wall mount; dandruff query → a scalp massager brush).

Irrelevant - the product shares surface-level keywords with the query but does not solve the problem (e.g. "crackling audio fix" → decorative speaker stand; "squeaky brakes" → a bicycle bell), or the image shows a product that clearly would not address the described need.

Price constraint: if the query states a price restriction (e.g. "under $50", "for $20"), treat it as a key requirement. Compare against the Discounted Price when available, otherwise the Price. A product that would otherwise be Exact but exceeds the stated budget is Substitute, not Exact. If the budget clearly applies to a whole set or basket of items (e.g. "ingredients for taco night under $35"), a single product only violates it if that one product alone exceeds the total budget. Price does not affect Complementary or Irrelevant labels.

Output ONLY a JSON array with exactly one object per product, in the same numbered order: [{"index": <product number>, "label": "Exact" | "Substitute" | "Complementary" | "Irrelevant", "reasoning": "brief 1-sentence explanation"}, ...]
```


---

## ASK-7 — Judge stability (Gemini 2.5 vs 3.5)

**Not stored — cannot be computed from disk; needs human input.** The only
judged set on disk is the current gemini-3.5-flash set
(`comparison_final_judged/judged/`). Per-hit records carry no judge-model
field. No separate judgment cache exists (`cached: true` means "reused from a
prior run of the same file", set by `load_cache()` in llm_judge.py — whose
docstring mentions skipping "old binary (0/1) judgments", proving an older
scheme existed, but none survive). Git history is exhausted: 3 commits, zero
deleted files, fsck clean, no stashes, `git log -S "gemini-2.5"` empty;
JUDGE_MODEL has been `"gemini-3.5-flash"` in every commit. All "Gemini 2.5"
mentions on disk refer to query generation, not judging. A 2.5-era judgment
set would have to be regenerated to compute the requested deltas.

---

## ASK-8 — Evaluation date window and plan/tier hints

**Raw response files: not found on disk.** `run_final_comparison.py` writes
raw engine responses to `comparison_final_results/<sector>_results.json`;
that directory does not exist, is gitignored, and was never committed. By
design the raw records would contain no wall-clock timestamps anyway
(only `latency_ms` durations). **Per-engine run dates need human input.**

**No timestamp fields exist in the judged data** (exhaustive key scan of all
7 files: top-level query_id/category/complexity/text_query/providers;
provider-level latency_ms/precision_at_10/precision_at_20/hits; hit-level
rank/id/title/description/image/price/discount_price/label/score/reasoning/
cached).

**Best supportable window from git evidence** (file mtimes are clone-time and
were ignored):
- All engine responses and all judgments existed by **2026-07-12 21:29:33
  +0400** (author date of the initial commit that added every judged +
  aggregates file; committer date 2026-07-14 13:40:26 +0400).
- The `cached` flag distribution proves judging spanned multiple resumed runs
  before that commit (pharmacy all-fresh = final run; electronics almost
  all-cached = earlier run), but no dates for those earlier runs survive.
- Bootstrap analysis: 2026-07-15 07:08:27 UTC (embedded run stamp, committed
  2026-07-15 11:33 +0400). "remove old engine" 2026-07-15 11:39 +0400.
- The evaluation START date, per-engine run dates, and whether all engines
  were queried in the same session per sector: **needs human input**.

**Plan/tier hints visible in configs (no secrets printed):**
- **Doofinder**: explicit free-tier evidence — providers.py:58-59 comment:
  "Doofinder account #3 free tier: 1000 search req/month, one 225-query run
  costs ~23% of the monthly budget; run with --delay and don't --force";
  catalogs spread across ≥4 separate accounts with their own keys/quotas
  (marketplace and pharmacy have dedicated API-key env vars) — consistent
  with multiple free/low-quota accounts.
- **Algolia**: one app shared across all 7 sectors with per-sector indices;
  no tier stated on disk — needs human input.
- **Luigi's Box / Clerk.io**: 7 per-sector tracker IDs / public keys;
  README: "Luigi's Box and Clerk.io gate their semantic/AI search behind
  sales contact, so they are evaluated on their keyword search" — implies
  self-serve tier without the AI add-on; exact plans need human input.
- **Quissly**: no API key; endpoint is a first-party dev Cloud Run instance
  (`<internal dev endpoint>`), not a commercial plan.
- **Gemini judge**: gemini-3.5-flash; account tier unknown — needs human
  input.

---

## VERIFICATION note

- **Reconciliation gate** (above) recomputed every gated number from the raw
  judged files with fresh code and cross-checked the published website bundle
  (`<website repo>/comparison-data/`): recall n=1,059 per engine
  from the bundle's per-tier n's; every EZR count reproduced from
  zero-result (aggregates CSVs) + all-junk (bundle rich). ABORT-on-mismatch;
  it passed.
- **ASK-1 grid**: every junk/recall value asserted equal (1e-9) to the
  published per-sector bundle jsons; every corrected nDCG value asserted
  equal to `analysis/ndcg_pooled/cells.json` (itself verified this week by
  independent from-spec reimplementation, adversarial code review, and an
  independent Holm/bootstrap validation — see
  `analysis/ndcg_pooled/VERIFICATION.md`); weighted sector recombination
  reproduces the pooled value for all 8 grid metrics × 5 engines within
  2-decimal rounding (worst deviation 0.003pp).
- **ASK-3 provenance**: row counts 64+64+64+44 verified; seed=42 and
  B=10,000 in all 236 rows; precision/recall p_raw verified bit-identical
  between the original and corrected bootstrap CSVs before the family was
  assembled. The Holm pass is deterministic (no resampling). Note the earlier
  `analysis/ezr_bootstrap/summary.md` also reports an m=236 family — that one
  used the OLD self-normalized nDCG p_raws; this consolidated family uses the
  CORRECTED ones, so p_holm values for the same cell legitimately differ
  (e.g. marketplace recall@10 vs Doofinder: 0.1278 there vs 0.0994 here —
  both non-significant).
- **Discovery claims** (ASK-4/5/7/8) were produced by four read-only
  evidence-hunting agents citing file paths, then the load-bearing claims
  were spot-verified directly: README:68-73 quote, furniture file counts and
  the missing q_0225 / ID-range conventions, the Doofinder free-tier comment
  (providers.py:58-59), run_final_comparison.py output paths and absence of
  timestamps, and the judged-data label census (recomputed independently in
  ASK-6).
- Underlying analysis outputs consumed here were themselves adversarially
  verified in this repo: `analysis/ndcg_pooled/VERIFICATION.md`,
  `analysis/ezr_bootstrap/VERIFICATION.md`,
  `analysis/empty_pool_audit/VERIFICATION.md` (plus the internal
  nDCG-audit verification record).
- A final document-level proofread agent checked every cell of every table
  against `sector_grid.json`/`consolidated_holm.csv`/the source CSVs,
  recomputed the m=236 Holm pass from the 236 p_raws, verified the three
  judging prompts byte-identical to `pipeline/llm_judge.py` via AST, and
  re-verified all sums and populations. Its four findings (a p_raw/p_holm
  label mixup, a 68%-vs-69% share, a missing cross-reference between ASK-2
  and ASK-3, and a self-falsifying phrase) were fixed before this version.
