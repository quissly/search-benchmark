"""Shared product schema for the e-commerce search benchmark.

Every sector adapter maps its native columns into ONE common schema. The 12
columns below are written, in this exact order, to data/normalized/<sector>.parquet.

    product_id   str    namespaced "<sector>:<raw_id>"
    sector       str    one of SECTORS
    title        str    product name (rows with empty title are dropped)
    description  str    free-text description
    brand        str    brand / store / manufacturer
    category     str    native category hierarchy or path
    price        float  nullable
    currency     str    ISO-ish code ("USD", "INR", ...) or "" if unknown
    attributes   str    JSON object of ALL leftover native fields
    image_url    str    URL ONLY — never image bytes
    source       str    dataset handle (e.g. "kaggle:nadyinky/sephora-...")
    source_url   str    canonical product/page URL if present, else ""

Adapters build a list of "raw row" dicts and hand them to `build_frame`, which
does the type coercion, attribute JSON-encoding, product_id namespacing and the
"drop rows with no title" rule in one place.
"""

from __future__ import annotations

import json
import math
from typing import Any, Iterable, Mapping

import pandas as pd

SECTORS = [
    "furniture",
    "auto",
    "electronics",
    "cosmetics",
    "pharmacy",
    "fast_fashion",
    "luxury_fashion",
    "marketplace",
]

# Exact column order for every normalized parquet file.
SCHEMA_COLUMNS = [
    "product_id",
    "sector",
    "title",
    "description",
    "brand",
    "category",
    "price",
    "currency",
    "attributes",
    "image_url",
    "source",
    "source_url",
]

# Everything except `price` is a string column.
STRING_COLUMNS = [c for c in SCHEMA_COLUMNS if c != "price"]

# Fields a raw row may set directly; anything else goes into `attributes`.
_MAPPED_FIELDS = {
    "raw_id",
    "title",
    "description",
    "brand",
    "category",
    "price",
    "currency",
    "image_url",
    "source_url",
    "attributes",
}

_EMPTY_TOKENS = {"", "nan", "none", "null", "n/a", "na", "<na>"}


def clean_str(value: Any) -> str:
    """Coerce any scalar to a clean stripped string ("" for missing/NaN)."""
    if value is None:
        return ""
    if isinstance(value, float) and math.isnan(value):
        return ""
    # Lists/dicts (common in HF datasets) -> JSON so nothing is silently lost.
    if isinstance(value, (list, tuple)):
        parts = [clean_str(v) for v in value]
        return " ".join(p for p in parts if p)
    if isinstance(value, Mapping):
        return json.dumps(_jsonable(value), ensure_ascii=False, sort_keys=True)
    s = str(value).strip()
    if s.lower() in _EMPTY_TOKENS:
        return ""
    return s


def clean_price(value: Any) -> float | None:
    """Parse a price into a float, or None. Handles "$12.99", "1,299", ranges."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        f = float(value)
        return None if math.isnan(f) else f
    s = str(value).strip()
    if s.lower() in _EMPTY_TOKENS:
        return None
    # Ranges like "$10.00 - $20.00" -> take the lower bound.
    if " - " in s:
        s = s.split(" - ", 1)[0]
    # Keep digits, dot and minus; drop currency symbols, commas, words.
    cleaned = "".join(ch for ch in s if ch.isdigit() or ch in ".-")
    cleaned = cleaned.strip(".-")
    if not cleaned or cleaned.count(".") > 1:
        return None
    try:
        return float(cleaned)
    except ValueError:
        return None


def _jsonable(value: Any) -> Any:
    """Recursively make a value JSON-serializable, dropping empties/NaN."""
    if isinstance(value, float) and math.isnan(value):
        return None
    if isinstance(value, Mapping):
        out = {}
        for k, v in value.items():
            jv = _jsonable(v)
            if jv not in (None, "", [], {}):
                out[str(k)] = jv
        return out
    if isinstance(value, (list, tuple)):
        items = [_jsonable(v) for v in value]
        return [v for v in items if v not in (None, "", [], {})]
    if isinstance(value, (str, int, bool)):
        return value
    if isinstance(value, float):
        return value
    # Fallback for numpy scalars, etc.
    try:
        if hasattr(value, "item"):
            return value.item()
    except Exception:  # noqa: BLE001
        pass
    return clean_str(value)


def encode_attributes(attrs: Any) -> str:
    """JSON-encode a dict of leftover fields. Returns "{}" when empty."""
    if attrs is None:
        return "{}"
    if isinstance(attrs, str):
        # Already encoded by the adapter.
        return attrs or "{}"
    clean = _jsonable(attrs)
    if not isinstance(clean, dict):
        clean = {"value": clean}
    return json.dumps(clean, ensure_ascii=False, sort_keys=True)


def build_frame(rows: Iterable[Mapping[str, Any]], sector: str, source: str) -> pd.DataFrame:
    """Turn adapter "raw rows" into a schema-conforming DataFrame.

    Each row dict may set any of the mapped fields (title, description, brand,
    category, price, currency, image_url, source_url, raw_id) plus an optional
    "attributes" dict of leftover native fields. Anything missing defaults to ""
    (or None for price). Rows with an empty title are dropped.
    """
    if sector not in SECTORS:
        raise ValueError(f"unknown sector {sector!r}; expected one of {SECTORS}")

    records: list[dict[str, Any]] = []
    for row in rows:
        title = clean_str(row.get("title"))
        if not title:
            continue  # hard rule: drop rows with no title

        raw_id = clean_str(row.get("raw_id"))
        attrs = row.get("attributes")
        record = {
            "product_id": f"{sector}:{raw_id}" if raw_id else "",
            "sector": sector,
            "title": title,
            "description": clean_str(row.get("description")),
            "brand": clean_str(row.get("brand")),
            "category": clean_str(row.get("category")),
            "price": clean_price(row.get("price")),
            "currency": clean_str(row.get("currency")),
            "attributes": encode_attributes(attrs),
            "image_url": clean_str(row.get("image_url")),
            "source": source,
            "source_url": clean_str(row.get("source_url")),
        }
        records.append(record)

    df = pd.DataFrame(records, columns=SCHEMA_COLUMNS)
    # Enforce dtypes: strings as object (with ""), price as nullable float.
    for col in STRING_COLUMNS:
        df[col] = df[col].fillna("").astype("string").fillna("")
    df["price"] = pd.to_numeric(df["price"], errors="coerce").astype("Float64")
    return df


def collect_leftovers(native: Mapping[str, Any], used_keys: Iterable[str]) -> dict[str, Any]:
    """Return native fields not already mapped, for the attributes JSON."""
    used = set(used_keys)
    return {k: v for k, v in native.items() if k not in used}


def validate(df: pd.DataFrame, sector: str) -> dict[str, Any]:
    """Compute the per-sector validation report.

    Returns row count and % non-empty for the headline fields. A string field is
    "non-empty" when it is a non-blank string; price is non-empty when not null.
    """
    n = len(df)
    report: dict[str, Any] = {"sector": sector, "rows": n}
    fields = ["title", "description", "brand", "category", "price", "image_url"]
    for field in fields:
        if n == 0:
            report[field] = 0.0
            continue
        if field == "price":
            non_empty = int(df["price"].notna().sum())
        else:
            col = df[field].astype("string").fillna("")
            non_empty = int((col.str.len() > 0).sum())
        report[field] = round(100.0 * non_empty / n, 1)
    return report


def format_report(reports: list[dict[str, Any]]) -> str:
    """Render a list of `validate` dicts as an aligned text table."""
    fields = ["title", "description", "brand", "category", "price", "image_url"]
    header = f"{'sector':<16}{'rows':>9}  " + "  ".join(f"{f:>11}" for f in fields)
    lines = [header, "-" * len(header)]
    for r in reports:
        cells = "  ".join(f"{r.get(f, 0.0):>10.1f}%" for f in fields)
        lines.append(f"{r['sector']:<16}{r['rows']:>9}  {cells}")
    return "\n".join(lines)
