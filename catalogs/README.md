# Catalogs — fetch and rebuild

The benchmark's seven sector catalogs (288,355 products) are **rebuilt, not
committed** — see `DATA_LICENSES.md` at the repo root for why (upstream
licenses and redistribution caveats).

These scripts are the exact acquisition + normalization code that produced
the run's catalogs (imported verbatim from the internal data-prep repo at
its final state, commit `a7afb21`):

| file | role |
|---|---|
| `fetch.py` | downloads raw data per sector into `data/raw/<sector>/` — Amazon Reviews 2023 metadata streamed from the HuggingFace CDN (capped at 50k rows/sector), Kaggle datasets via the `kaggle` CLI (needs `~/.kaggle/kaggle.json`), Myntra archive with selective metadata extraction |
| `adapters.py` | one adapter per sector mapping native columns → the shared schema |
| `schema.py` | the 12-column schema: ids namespaced `<sector>:<raw_id>`, price coercion, drop-rows-with-no-title rule, validators |
| `normalize.py` | runs adapters → writes `data/normalized/<sector>.parquet` + sample CSVs + a validation report |
| `validate_counts.py` | asserts the exact per-sector row counts of the benchmark run (50,000 / 50,000 / 50,000 / 49,999 / 44,417 / 23,939 / 20,000) |
| `parquet_to_json.py` | lossless parquet → JSON array (verbatim copy from the internal benchmark repo) |
| `cleanup.py` | maps a lossless sector JSON → the Quissly ProductItem upload dict (verbatim copy from the internal benchmark repo) |
| `format_data.py` | driver for the two scripts above: exact per-sector flags + post-processing (price-fill rule, fast_fashion fixups) → `data/final_data/<sector>_final.json`, gated on the md5 of the file actually uploaded to the providers |

```bash
pip install -r catalogs/requirements.txt
python catalogs/fetch.py               # downloads (Kaggle token required)
python catalogs/normalize.py           # builds data/normalized/*.parquet
python catalogs/validate_counts.py     # exact-count gate
python catalogs/format_data.py         # rebuilds the exact upload files (md5 gate)
```

## Upload files

`format_data.py` rebuilds the exact JSON files that were uploaded to
**every** provider in the run (the shared indexed corpus, 288,354 products —
the fast_fashion junk row `28319` is dropped during this stage). The whole
chain is **byte-verified**: rebuilding from the run's parquet snapshot
reproduces all seven files md5-identically (auto also verified end-to-end
from a fresh `fetch.py` download, 2026-07-22).

Two post-mapping steps are not expressible as flags and are replayed by the
driver (full details in its module docstring):

1. **Price fill** — records with no source price (94,662 across the seven
   sectors) get the rounded median price of their category, falling back to
   the global median for unpriced categories.
2. **fast_fashion fixups** — junk-row drop, legacy metadata key order, and
   one hand-looked-up price (record `45675`, the only value in the corpus
   not derivable from source data).

**Determinism caveat:** the fetchers read live upstreams. The run's local
snapshot validates against these exact counts today, but upstream re-uploads
or reordering can drift a future rebuild. If `validate_counts.py` fails, your
catalog differs from the benchmarked snapshot; the shipped judged data
(`comparison_final_judged/`) remains the authoritative record of every
product actually retrieved and judged, and all published numbers recompute
from it without any catalog.
