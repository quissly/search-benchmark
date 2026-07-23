"""Lossless parquet -> JSON converter.

Reads a normalized sector parquet and writes every row, every column, exactly
as-is to a JSON array. Nothing is dropped, renamed, defaulted, truncated, or
reshaped. The `attributes` column stays exactly as stored in the parquet.

Usage:
    python scripts/parquet_to_json.py fast_fashion
    python scripts/parquet_to_json.py "data_raw/normalized/fast_fashion.parquet" -o out.json
"""

import argparse
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
NORMALIZED = ROOT / "data_raw" / "normalized"


def resolve_input(arg: str) -> Path:
    p = Path(arg)
    if p.exists():
        return p
    cand = NORMALIZED / f"{arg}.parquet"
    if cand.exists():
        return cand
    raise SystemExit(f"Input not found: tried '{arg}' and '{cand}'")


def main():
    ap = argparse.ArgumentParser(description="Lossless parquet -> JSON.")
    ap.add_argument("input", help="Sector name (e.g. fast_fashion) or a path to a .parquet file")
    ap.add_argument("-o", "--output", default=None, help="Output .json path")
    args = ap.parse_args()

    path = resolve_input(args.input)
    df = pd.read_parquet(path)

    out = Path(args.output) if args.output else ROOT / "data" / f"{path.stem}_full.json"
    # to_json preserves every column and value as stored; force_ascii off keeps unicode intact.
    df.to_json(out, orient="records", force_ascii=False, indent=2)

    print(f"{path}  ->  {out}")
    print(f"{len(df)} rows, columns: {list(df.columns)}")


if __name__ == "__main__":
    main()
