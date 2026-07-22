"""Validate rebuilt catalogs against the exact row counts used in the
benchmark run. Run after `fetch.py` + `normalize.py`:

    python catalogs/validate_counts.py [normalized_dir]

Default normalized_dir: $CATALOG_DIR, else ./data/normalized relative to cwd.
Exits non-zero on any mismatch. NOTE: the fetchers stream from live upstreams
(HuggingFace CDN, Kaggle); if an upstream re-uploads or reorders its data,
counts can drift — a mismatch here means your rebuild differs from the
snapshot the benchmark ran on, and the shipped judged data remains the
authoritative record of what was actually benchmarked.
"""
import os
import sys
from pathlib import Path

import pandas as pd

EXPECTED = {
    "auto": 50_000,
    "cosmetics": 50_000,
    "electronics": 50_000,
    "furniture": 49_999,
    "fast_fashion": 44_417,
    "pharmacy": 23_939,
    "marketplace": 20_000,
}


def main():
    base = Path(sys.argv[1]) if len(sys.argv) > 1 else \
        Path(os.environ.get("CATALOG_DIR") or "data/normalized")
    bad = 0
    for sector, want in EXPECTED.items():
        p = base / f"{sector}.parquet"
        if not p.exists():
            print(f"MISSING {p}")
            bad += 1
            continue
        got = len(pd.read_parquet(p, columns=["product_id"]))
        ok = got == want
        bad += not ok
        print(f"{'PASS' if ok else 'FAIL'} {sector}: {got:,} rows "
              f"(expected {want:,})")
    total = sum(EXPECTED.values())
    print(f"expected total: {total:,} products across 7 sectors")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
