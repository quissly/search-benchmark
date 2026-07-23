"""Rebuild the exact Quissly upload files (data/final_data) from the
normalized parquets — the second half of the data chain, after fetch.py +
normalize.py.

Chain per sector:
  data/normalized/<sector>.parquet
    -> parquet_to_json.py  -> data/full/<sector>_full.json      (lossless)
    -> cleanup.py       -> data/final_data/<sector>_final.json
    -> post-processing (below), applied in place

Both converter scripts are verbatim copies from the internal benchmark repo;
this driver supplies the exact per-sector flags (SECTOR_FLAGS), byte-verified
against the shipped upload files.

Post-processing (what the flags alone don't produce):
  1. Price fill — every record whose original_price mapped to 0.0 (source
     price missing) gets round(median, 2) of the positive original_price
     values in its `category`; if the category has no priced records, the
     global median across all categories is used instead. Verified to
     reproduce all 94,662 filled prices across the seven sectors.
  2. fast_fashion fixups (this sector was processed first, with an earlier
     script revision, so three deltas are replayed):
       a. record "28319" ("RTV_LoadTest", a Myntra load-test junk row) is
          dropped — the indexed corpus is 44,416, not 44,417;
       b. metadata["breadcrumbs"] is moved to the end of each metadata dict
          (the old revision appended it after the attribute keys);
       c. record "45675" (Tabac Men Original EDT) gets original_price 1512.0
          — a hand-looked-up real price, not derivable from any source field
          or category median (the only such value in all seven sectors).

Every output is gated on the md5 of the file actually uploaded to the
providers (EXPECTED_MD5). A mismatch means your rebuild differs from the
benchmarked corpus — most likely because the upstream fetch drifted (see
validate_counts.py).

Usage:
    python catalogs/format_data.py            # all seven sectors
    python catalogs/format_data.py marketplace pharmacy
"""

from __future__ import annotations

import hashlib
import json
import statistics
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
NORMALIZED = Path("data/normalized")
FULL = Path("data/full")
READY = Path("data/final_data")

# Flag sets for cleanup.py, byte-verified against the shipped uploads.
AMAZON_FLAGS = [
    "--drop-meta", "sector,source,average_rating,rating_number,main_category,store,categories",
    "--flatten-attr", "features",
    "--hoist-attr", "details:Date First Available;Brand;Best Sellers Rank;UPC",
]
SECTOR_FLAGS: dict[str, list[str]] = {
    "fast_fashion": ["--drop-meta", "sector,source,enriched_from_json"],
    "marketplace": [
        "--category", "top",
        "--list-price-attr", "retail_price",
        "--drop-meta", "sector,source,crawl_timestamp,is_FK_Advantage_product,"
                       "overall_rating,pid,product_rating",
    ],
    "pharmacy": [
        "--list-price-attr", "price",
        "--drop-meta", "sector,source,disease_url",
        "--strip-meta-prefix", "generic_name:Generic Name,drug_varient,drug_manufacturer_origin",
    ],
    "auto": AMAZON_FLAGS,
    "cosmetics": AMAZON_FLAGS,
    "electronics": AMAZON_FLAGS,
    "furniture": AMAZON_FLAGS,
}

# md5 of each file as uploaded to every provider in the benchmark run.
EXPECTED_MD5 = {
    "auto": "ff92752e0d54f3fb7928ed8cc5399c5f",
    "cosmetics": "20f0d59c7074f268a056bce3befbfc10",
    "electronics": "8a530e9c8a28274f9e2f6c995a05f578",
    "fast_fashion": "beb8def00ed7dcd2b11a972a77064054",
    "furniture": "0be207625c04b341e97d567f444582ee",
    "marketplace": "3b07756bb9a6671cb70622592066308a",
    "pharmacy": "ead0d1350adb7ad204c4dbf5caf18386",
}


def fill_prices(recs: dict) -> int:
    """0.0-priced records -> round(category median, 2), else global median."""
    by_cat: dict[str, list[float]] = defaultdict(list)
    for item in recs.values():
        if item["original_price"] > 0:
            by_cat[item["category"]].append(item["original_price"])
    global_median = statistics.median([v for vals in by_cat.values() for v in vals])
    filled = 0
    for item in recs.values():
        if item["original_price"] == 0.0:
            vals = by_cat.get(item["category"])
            item["original_price"] = round(statistics.median(vals) if vals else global_median, 2)
            filled += 1
    return filled


def fixup_fast_fashion(recs: dict) -> None:
    recs.pop("28319", None)                      # RTV_LoadTest junk row
    for item in recs.values():                   # legacy key order: breadcrumbs last
        meta = item["metadata"]
        if "breadcrumbs" in meta:
            meta["breadcrumbs"] = meta.pop("breadcrumbs")
    if "45675" in recs:                          # hand-looked-up price (see module docstring)
        recs["45675"]["original_price"] = 1512.0


def build_sector(sector: str) -> bool:
    parquet = NORMALIZED / f"{sector}.parquet"
    if not parquet.exists():
        print(f"[{sector}] SKIPPED — {parquet} missing. Run fetch.py + normalize.py first.")
        return False

    FULL.mkdir(parents=True, exist_ok=True)
    READY.mkdir(parents=True, exist_ok=True)
    # absolute paths: cleanup.py prints its output path relative to its own
    # repo root, which requires an absolute path under the cwd
    full_json = (FULL / f"{sector}_full.json").resolve()
    out = (READY / f"{sector}_final.json").resolve()

    subprocess.run([sys.executable, str(HERE / "parquet_to_json.py"),
                    str(parquet), "-o", str(full_json)], check=True)
    subprocess.run([sys.executable, str(HERE / "cleanup.py"), sector,
                    "--input", str(full_json), "--output", str(out),
                    *SECTOR_FLAGS[sector]], check=True)

    recs = json.loads(out.read_text())
    if sector == "fast_fashion":
        fixup_fast_fashion(recs)
    filled = fill_prices(recs)
    out.write_text(json.dumps(recs, ensure_ascii=False, indent=2))

    md5 = hashlib.md5(out.read_bytes()).hexdigest()
    ok = md5 == EXPECTED_MD5[sector]
    print(f"[{sector}] {len(recs):,} records, {filled:,} prices filled, md5={md5} "
          f"-> {'MATCHES the benchmarked upload' if ok else 'MISMATCH (expected ' + EXPECTED_MD5[sector] + ')'}")
    return ok


def main() -> None:
    targets = sys.argv[1:] or list(SECTOR_FLAGS)
    unknown = [s for s in targets if s not in SECTOR_FLAGS]
    if unknown:
        sys.exit(f"unknown sector(s): {unknown}; known: {list(SECTOR_FLAGS)}")
    results = {s: build_sector(s) for s in targets}
    bad = [s for s, ok in results.items() if not ok]
    if bad:
        sys.exit(f"\nFAILED verification: {bad}")
    print(f"\nAll {len(results)} sector(s) byte-identical to the benchmarked uploads.")


if __name__ == "__main__":
    main()
