"""Assemble REPORT_INPUTS.md from the numeric fragments (report_inputs_core.py
outputs) plus the discovery findings. Extracts the three judging prompts
verbatim from pipeline/llm_judge.py via AST so no transcription can drift."""
import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent


def judging_prompts():
    tree = ast.parse((ROOT / "pipeline/llm_judge.py").read_text())
    out = {}
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 \
                and isinstance(node.targets[0], ast.Name) \
                and node.targets[0].id.startswith("SYSTEM_PROMPT_") \
                and isinstance(node.value, ast.Constant):
            out[node.targets[0].id] = node.value.value
    assert set(out) == {"SYSTEM_PROMPT_SIMPLE", "SYSTEM_PROMPT_MEDIUM",
                        "SYSTEM_PROMPT_COMPLEX"}
    return out


def frag(name):
    return (OUT / name).read_text().rstrip()


ASK4 = """## ASK-4 — Catalogs

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
Kaggle-sourced sectors rest on unverified re-uploader licenses."""

ASK5_HEAD = """## ASK-5 — Queries

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
| complex | fast_fashion | appropriate and respectful outfit for attending a funeral |"""

ASK7 = """## ASK-7 — Judge stability (Gemini 2.5 vs 3.5)

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
set would have to be regenerated to compute the requested deltas."""

ASK8 = """## ASK-8 — Evaluation date window and plan/tier hints

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
  input."""

VERIFY = """## VERIFICATION note

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
  and ASK-3, and a self-falsifying phrase) were fixed before this version."""


def main():
    prompts = judging_prompts()
    ask6 = frag("ask6_labels.md") + "\n\n### Judging prompts, verbatim (pipeline/llm_judge.py)\n"
    for name, title in (("SYSTEM_PROMPT_SIMPLE", "Simple tier"),
                        ("SYSTEM_PROMPT_MEDIUM", "Medium tier"),
                        ("SYSTEM_PROMPT_COMPLEX", "Complex tier")):
        ask6 += f"\n#### {title} (`{name}`)\n\n```\n{prompts[name]}\n```\n"

    doc = "\n\n---\n\n".join([
        "# Report inputs — consolidated deliverable\n\n"
        "> **Errata (2026-07-20).** Recorded deliverable, kept as assembled; four\n"
        "> points have since been superseded: (1) ASK-5's \"no generator script\n"
        "> exists\" — `queries/query_generator.py` has since been added; (2) ASK-7's\n"
        "> \"a 2.5-era judgment set would have to be regenerated\" — full re-judges\n"
        "> now ship in `analysis/judge_stability/` and `analysis/judge_claude/`;\n"
        "> (3) the ASK-3 note's marketplace recall@10 example (p_holm 0.0994,\n"
        "> non-significant) predates the 2026-07-18 marketplace pool correction —\n"
        "> the cell is now significant (p_holm 0.0416; `consolidated_holm.csv` is\n"
        "> authoritative); (4) line-number citations into README.md and providers.py\n"
        "> have drifted with later edits.\n\n"
        "Everything below was produced read-only from this repo, the datasets "
        "repo, and the published website bundle; all new files live in "
        "`analysis/report_inputs/`. Machine-readable companions: "
        "`sector_grid.json`, `consolidated_holm.csv`. "
        "Where something is not on disk it is marked "
        "**not found on disk, needs human input** rather than guessed.\n\n"
        + frag("versions.md"),
        frag("gate.md"),
        frag("ask1_sector_grid.md"),
        frag("ask2_tiers.md"),
        frag("ask3_holm.md"),
        ASK4,
        ASK5_HEAD,
        ask6,
        ASK7,
        ASK8,
        VERIFY,
    ])
    (OUT / "REPORT_INPUTS.md").write_text(doc + "\n")
    print(f"Wrote {OUT / 'REPORT_INPUTS.md'} "
          f"({len(doc.splitlines())} lines)")


if __name__ == "__main__":
    main()
