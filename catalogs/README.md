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

```bash
pip install -r catalogs/requirements.txt
python catalogs/fetch.py            # downloads (Kaggle token required)
python catalogs/normalize.py        # builds data/normalized/*.parquet
python catalogs/validate_counts.py  # exact-count gate
```

**Determinism caveat:** the fetchers read live upstreams. The run's local
snapshot validates against these exact counts today, but upstream re-uploads
or reordering can drift a future rebuild. If `validate_counts.py` fails, your
catalog differs from the benchmarked snapshot; the shipped judged data
(`comparison_final_judged/`) remains the authoritative record of every
product actually retrieved and judged, and all published numbers recompute
from it without any catalog.
