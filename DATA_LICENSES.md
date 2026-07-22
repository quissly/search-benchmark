# Data sources, licenses, and why catalogs are rebuilt rather than committed

**Licensing of this repository's contents:** the code is licensed under
Apache-2.0 (`LICENSE`, `NOTICE`). The Quissly-generated artifacts in this
repository — the query sets, the relevance judgments with rationales, the
per-query scores, and the analysis outputs — are released under CC BY 4.0.
Upstream catalog data remains under the source terms documented below.
The CC BY 4.0 grant covers Quissly's own annotations and derived numbers;
the judged files also embed upstream product metadata (titles,
descriptions, image URLs, prices) quoted for judging provenance — that
embedded content remains under its source terms, not CC BY. Full CC BY
4.0 text: https://creativecommons.org/licenses/by/4.0/.

The benchmark's seven sector catalogs (288,355 products) are **not
committed** to this repository. They are rebuilt from their upstream sources
with the scripts in `catalogs/` (fetch → normalize → validate exact row
counts). This page records every source, the license as stated by that
source, and the reasoning.

## Sources and attributions

### Amazon Reviews 2023 (sectors: auto, electronics, cosmetics, furniture — 199,999 products)

- **Dataset:** Amazon Reviews 2023, McAuley Lab (UCSD). Metadata subsets
  `raw_meta_Automotive`, `raw_meta_Electronics`,
  `raw_meta_Beauty_and_Personal_Care`, `raw_meta_Home_and_Kitchen`,
  streamed from the HuggingFace CDN capped at 50,000 rows per sector.
- **Citation:** Hou, Y., Li, J., He, Z., Yan, A., Chen, X., McAuley, J.
  (2024). *Bridging Language and Items for Retrieval and Recommendation.*
  arXiv:2403.03952.
- **License (as listed by the source):** CC BY-SA 4.0 — attribution and
  share-alike obligations apply to redistribution of the data itself.

### Kaggle datasets (sectors: fast_fashion, pharmacy, marketplace — 88,356 products)

| sector | Kaggle dataset | upstream origin | license as claimed by the re-uploader |
|---|---|---|---|
| fast_fashion (44,417) | `paramaggarwal/fashion-product-images-dataset` | Myntra product metadata (`styles.csv` + per-item JSON; images deliberately NOT used — URL references only) | MIT |
| pharmacy (23,939) | `drowsyng/medicines-dataset` | Netmeds medicines scrape | Apache-2.0 |
| marketplace (20,000) | `atharvjairath/flipkart-ecommerce-dataset` | Flipkart product listings | CC0-1.0 |

Kaggle acquisition requires a Kaggle account and API token and is subject to
Kaggle's terms of service.

## Why rebuilt, not committed

1. **Unverified license grants.** The Kaggle licenses above are the
   *re-uploaders'* claims, not verified grants from the original retailers
   (Myntra, Netmeds, Flipkart). Committing those catalogs to a public repo
   would redistribute scraped retailer data on the strength of a third
   party's license label.
2. **Share-alike burden.** ~69% of the corpus (the four Amazon sectors) is
   CC BY-SA 4.0; redistribution obligations are cleaner to satisfy by
   pointing at the canonical source than by shipping a derivative snapshot.
3. **Image content.** Product records carry image *URLs* hotlinking
   third-party CDNs; the image content itself is not covered by any of the
   dataset licenses. This repo never commits image bytes.
4. **Size.** The normalized snapshot is ~750 MB of parquet.

The rebuild is validated by `catalogs/validate_counts.py` against the exact
per-sector row counts of the benchmark run. If upstream drift makes exact
reconstruction impossible in the future, the shipped judged data
(`comparison_final_judged/`) remains the complete record of every product
actually retrieved and judged — all published numbers recompute from it
without any catalog.
