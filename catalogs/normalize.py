"""Normalize raw sector data -> data/normalized/<sector>.parquet + a sample CSV.

For each requested sector this:
  1. runs the sector adapter (adapters.ADAPTERS[sector]) over data/raw/<sector>/,
  2. writes the full schema-conforming table to data/normalized/<sector>.parquet,
  3. writes a ~300-row sample to data/samples/<sector>_sample.csv (committed to git),
  4. prints a validation report (row count + % non-empty per headline field).

Usage:
    python normalize.py --all
    python normalize.py furniture cosmetics
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from adapters import ADAPTERS
from schema import SCHEMA_COLUMNS, SECTORS, format_report, validate

NORMALIZED = Path("data/normalized")
SAMPLES = Path("data/samples")
SAMPLE_ROWS = 300


def normalize_sector(sector: str) -> dict:
    adapter = ADAPTERS.get(sector)
    if adapter is None:
        raise KeyError(f"no adapter registered for {sector!r}")

    print(f"[{sector}] running adapter ...")
    df = adapter()
    # Guarantee exact column order.
    df = df[SCHEMA_COLUMNS]

    NORMALIZED.mkdir(parents=True, exist_ok=True)
    SAMPLES.mkdir(parents=True, exist_ok=True)

    parquet_path = NORMALIZED / f"{sector}.parquet"
    df.to_parquet(parquet_path, index=False)

    sample = df.head(SAMPLE_ROWS)
    sample_path = SAMPLES / f"{sector}_sample.csv"
    sample.to_csv(sample_path, index=False)

    print(f"[{sector}] wrote {parquet_path} ({len(df):,} rows) + "
          f"{sample_path} ({len(sample)} rows)")
    return validate(df, sector)


def main() -> None:
    ap = argparse.ArgumentParser(description="Normalize raw data into the common schema.")
    ap.add_argument("sectors", nargs="*", help="sectors to normalize (default: all registered)")
    ap.add_argument("--all", action="store_true", help="normalize every registered sector")
    args = ap.parse_args()

    available = [s for s in SECTORS if s in ADAPTERS]
    if args.all or not args.sectors:
        targets = available
    else:
        targets = args.sectors

    unknown = [s for s in targets if s not in ADAPTERS]
    if unknown:
        sys.exit(f"no adapter for: {unknown}; registered: {available}")

    reports = []
    for sector in targets:
        print(f"\n=== normalize: {sector} ===")
        try:
            reports.append(normalize_sector(sector))
        except FileNotFoundError as exc:
            print(f"[{sector}] SKIPPED — raw data missing ({exc}). Run fetch.py first.")
        except Exception as exc:  # noqa: BLE001
            print(f"[{sector}] ERROR — {exc!r}")

    if reports:
        print("\n" + "=" * 100)
        print("VALIDATION REPORT  (% non-empty)")
        print("=" * 100)
        print(format_report(reports))


if __name__ == "__main__":
    main()
