"""Map a lossless sector JSON (from parquet_to_json.py) into Quissly's
ProductItem upload shape: a dict keyed by id, ready to chunk + sign + POST
to /v1beta/catalog.

Field mapping (12-col source -> Quissly ProductItem):
    id               <- product_id          (also the dict key)
    title            <- title
    description       <- description
    category          <- category
    original_price    <- price               (float >= 0)
    discounted_price   <- attributes.discountedPrice
    discount_percent   <- round((price-discounted)/price*100) when both exist
    images            <- [image_url]         (valid http urls only)
    in_stock           = True
    url               <- source_url          (valid http url, else omitted)
    metadata          <- brand, currency, sector, source + all attributes keys (flat)

Usage:
    python scripts/cleanup.py fast_fashion
    python scripts/cleanup.py fast_fashion --limit 7000
"""

import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"

PROMOTED_ATTR_KEYS = {"discountedPrice", "discounted_price"}  # moved to top-level, not duplicated in metadata


def is_http_url(v) -> bool:
    return isinstance(v, str) and v.strip().lower().startswith(("http://", "https://"))


def clean_str(v) -> str:
    if v is None:
        return ""
    s = str(v).strip()
    return "" if s.lower() == "nan" else s


def as_attrs(raw) -> dict:
    """`attributes` is stored as a JSON string; parse it to a dict."""
    if isinstance(raw, dict):
        return raw
    if not raw:
        return {}
    try:
        obj = json.loads(raw)
        return obj if isinstance(obj, dict) else {}
    except (json.JSONDecodeError, TypeError):
        return {}


def parse_ruby_specs(raw) -> str:
    """Clean a Flipkart product_specifications Ruby-hash string into readable text.

    e.g. '{"product_specification"=>[{"key"=>"Fabric", "value"=>"Cotton Lycra"},
          {"value"=>"3 shorts"}]}'  ->  'Fabric: Cotton Lycra | 3 shorts'
    Returns '' if the value isn't in that format (leaves it untouched upstream).
    """
    if not isinstance(raw, str) or "=>" not in raw:
        return ""
    parts = []
    for entry in re.findall(r"\{[^{}]*\}", raw):        # each spec entry
        k = re.search(r'"key"\s*=>\s*"(.*?)"', entry)
        v = re.search(r'"value"\s*=>\s*"(.*?)"', entry)
        if not v:
            continue
        val = v.group(1).strip()
        key = k.group(1).strip() if k else ""
        parts.append(f"{key}: {val}" if key else val)
    return " | ".join(parts)


def to_float(v):
    try:
        if v is None or v == "":
            return None
        f = float(v)
        return f if f >= 0 else None
    except (TypeError, ValueError):
        return None


def extract_number(v):
    """Numeric value from `v`, incl. numbers embedded in strings.

    Plain '999' -> 999.0 ; 'MRP ₹381.46  Save 12 %' -> 381.46 (first number).
    """
    f = to_float(v)
    if f is not None:
        return f
    if isinstance(v, str):
        m = re.search(r"[0-9]+(?:\.[0-9]+)?", v)
        if m:
            return float(m.group())
    return None


def prune_dict(v, drop_subkeys=()) -> dict:
    """Keep a nested dict as a dict, dropping given sub-keys and empty values."""
    if not isinstance(v, dict):
        return v
    return {k: val for k, val in v.items()
            if k not in drop_subkeys and val not in (None, "", [], {})}


def flatten_attr(v, drop_subkeys=()) -> str:
    """Flatten a nested dict/list attribute into readable ' | '-joined text.

    dict -> 'Key: Value | Key: Value' (skipping `drop_subkeys` and empties)
    list -> 'a | b | c'
    """
    if isinstance(v, dict):
        parts = [f"{k}: {val}" for k, val in v.items()
                 if k not in drop_subkeys and val not in (None, "", [], {})]
        return " | ".join(parts)
    if isinstance(v, list):
        return " | ".join(str(x).strip() for x in v if x not in (None, ""))
    return str(v)


def clean_meta_prefix(val, prefix: str) -> str:
    """Strip a leading '*' marker and an optional label prefix from a value.

    '*10 Tablet(s)...'                 -> '10 Tablet(s)...'
    '* Country of Origin: India'       -> 'Country of Origin: India'
    'Generic Name  Tetrabenazine 25mg' (prefix 'Generic Name') -> 'Tetrabenazine 25mg'
    """
    s = str(val).lstrip("*").strip()
    if prefix and s.startswith(prefix):
        s = s[len(prefix):].strip()
    return s


def raw_id(product_id: str) -> str:
    """Strip the '<sector>:' namespace, returning the raw id as a string."""
    return clean_str(product_id).split(":")[-1]


def detect_id_mode(rows: list) -> str:
    """Decide a single id type for the whole batch.

    Quissly's ProductAddRequest validates `data` as ONE dict type
    (all-int | all-uuid | all-str), so the batch must be uniform. If every raw
    id is integer-parseable we use 'int' (matches the BIGINT catalog); otherwise
    'str' (ASINs, hex, slugs -> ProductItemStr / VARCHAR catalog).
    """
    for row in rows:
        r = raw_id(row.get("product_id"))
        if not r or not r.lstrip("-").isdigit():
            return "str"
    return "int"


def map_record(row: dict, id_mode: str, category_mode: str = "leaf",
               list_price_attr: str | None = None,
               drop_meta: set | None = None,
               strip_prefix: dict | None = None,
               flatten: dict | None = None,
               dict_attrs: dict | None = None,
               hoist_attrs: dict | None = None) -> tuple[str, dict] | None:
    raw = raw_id(row.get("product_id"))
    title = clean_str(row.get("title"))
    if not raw or not title:
        return None  # Quissly requires an id + a title
    pid = int(raw) if id_mode == "int" else raw

    attrs = as_attrs(row.get("attributes"))
    schema_price = to_float(row.get("price"))

    if list_price_attr:
        # Inverted layout: the LIST price lives in an attribute and the schema
        # `price` is the SELLING price. The attribute may be a plain number
        # (marketplace retail_price) or a string ('MRP ₹381.46 …' for pharmacy).
        list_price = extract_number(attrs.get(list_price_attr))
        if list_price is not None:
            original_price = list_price
            # selling price becomes the discount only when it's genuinely lower
            discounted = schema_price if (schema_price is not None and schema_price < list_price) else None
        else:
            # no list price -> nothing to recover (the price-less rows) -> 0.0, no discount
            original_price = schema_price if schema_price is not None else 0.0
            discounted = None
    else:
        # Default layout (fast_fashion): schema `price` IS the list/original price;
        # the sale price sits in a discountedPrice attribute.
        original_price = schema_price if schema_price is not None else 0.0
        discounted = to_float(attrs.get("discountedPrice") or attrs.get("discounted_price"))
        # Only a genuine markdown counts. If the source repeats the list price
        # (discountedPrice >= price), the item isn't on sale -> null, no percent.
        if discounted is not None and discounted >= original_price:
            discounted = None

    discount_percent = None
    if discounted is not None and original_price > 0:
        discount_percent = round((original_price - discounted) / original_price * 100, 2)

    image = clean_str(row.get("image_url"))
    images = [image] if is_http_url(image) else []

    source_url = clean_str(row.get("source_url"))

    # Full path -> metadata.breadcrumbs; a single segment -> top-level `category`.
    # 'leaf' (last segment) suits clean taxonomies (fast_fashion, pharmacy);
    # 'top' (first segment) suits trees whose leaf is the product name (marketplace).
    full_category = clean_str(row.get("category"))
    parts = [p.strip() for p in re.split(r">>|>", full_category) if p.strip()]
    category = (parts[0] if category_mode == "top" else parts[-1]) if parts else ""

    metadata = {
        "brand": clean_str(row.get("brand")),
        "currency": clean_str(row.get("currency")),
        "sector": clean_str(row.get("sector")),
        "source": clean_str(row.get("source")),
        "breadcrumbs": full_category,
    }
    for k, v in attrs.items():
        if k not in PROMOTED_ATTR_KEYS:
            metadata[k] = v

    # Clean the Flipkart Ruby-hash spec blob into readable 'Key: Value' text.
    if metadata.get("product_specifications"):
        cleaned = parse_ruby_specs(metadata["product_specifications"])
        if cleaned:
            metadata["product_specifications"] = cleaned

    # Keep chosen nested-dict attributes as pruned dicts (structured, e.g. details).
    for k, drop_sub in (dict_attrs or {}).items():
        if k in metadata:
            metadata[k] = prune_dict(metadata[k], drop_sub)

    # Flatten nested dict/list attributes (e.g. features) into readable text.
    for k, drop_sub in (flatten or {}).items():
        if k in metadata:
            metadata[k] = flatten_attr(metadata[k], drop_sub)

    # Clean leading '*'/label prefixes off messy metadata values.
    for k, prefix in (strip_prefix or {}).items():
        if metadata.get(k):
            metadata[k] = clean_meta_prefix(metadata[k], prefix)

    # The list-price attribute is now `original_price` -> drop the redundant copy.
    if list_price_attr:
        metadata.pop(list_price_attr, None)
    # Prune requested bookkeeping keys (still preserved in the lossless _full.json).
    for k in (drop_meta or ()):
        metadata.pop(k, None)

    # Hoist a nested dict's sub-keys directly into metadata (no wrapper), dropping
    # the given sub-keys; never overwrite an existing top-level metadata key.
    for k, drop_sub in (hoist_attrs or {}).items():
        v = metadata.pop(k, None)
        if isinstance(v, dict):
            for sk, sv in v.items():
                if sk in drop_sub or sv in (None, "", [], {}) or sk in metadata:
                    continue
                metadata[sk] = sv

    item = {
        "id": pid,
        "title": title,
        "original_price": original_price,
        "description": clean_str(row.get("description")),
        "category": category,
        "images": images,
        "in_stock": True,
        "metadata": metadata,
        "discounted_price": discounted,        # null when not on sale
    }
    if discount_percent is not None:
        item["discount_percent"] = discount_percent
    if is_http_url(source_url):
        item["url"] = source_url

    return pid, item


def main():
    ap = argparse.ArgumentParser(description="Map lossless sector JSON -> Quissly ProductItem dict.")
    ap.add_argument("sector", help="e.g. fast_fashion (reads data/<sector>_full.json)")
    ap.add_argument("--input", default=None, help="Override input path")
    ap.add_argument("--output", default=None, help="Override output path")
    ap.add_argument("--limit", type=int, default=0, help="Keep only first N mapped records (0 = all)")
    ap.add_argument("--category", choices=["leaf", "top"], default="leaf",
                    help="Which segment of the category tree to use as `category` "
                         "(leaf=last, top=first). Use 'top' for marketplace.")
    ap.add_argument("--list-price-attr", default=None, metavar="KEY",
                    help="Attribute key holding the LIST price when the schema `price` is "
                         "the selling price (inverted layout). Use 'retail_price' for marketplace.")
    ap.add_argument("--drop-meta", default="", metavar="K1,K2,...",
                    help="Comma-separated metadata keys to drop from each record "
                         "(bookkeeping fields; still preserved in the lossless _full.json).")
    ap.add_argument("--strip-meta-prefix", default="", metavar="key[:prefix],...",
                    help="Comma-separated metadata keys to clean: strips a leading '*' and, "
                         "if given after ':', a label prefix. e.g. 'generic_name:Generic Name,drug_varient'.")
    ap.add_argument("--flatten-attr", default="", metavar="key[:sub1;sub2],...",
                    help="Flatten nested dict/list metadata values to ' | ' text. "
                         "After ':', ';'-separated dict sub-keys to drop. e.g. "
                         "'details:Date First Available;Best Sellers Rank,features'.")
    ap.add_argument("--dict-attr", default="", metavar="key[:sub1;sub2],...",
                    help="Keep a nested-dict metadata value AS a dict (structured), dropping "
                         "the given ';'-separated sub-keys. e.g. 'details:Date First Available;Brand'.")
    ap.add_argument("--hoist-attr", default="", metavar="key[:sub1;sub2],...",
                    help="Spread a nested dict's sub-keys directly into metadata (no wrapper), "
                         "dropping the given ';'-separated sub-keys. e.g. 'details:Date First Available;Brand'.")
    args = ap.parse_args()
    drop_meta = {k.strip() for k in args.drop_meta.split(",") if k.strip()}
    strip_prefix = {}
    for entry in args.strip_meta_prefix.split(","):
        entry = entry.strip()
        if not entry:
            continue
        key, _, prefix = entry.partition(":")
        strip_prefix[key.strip()] = prefix.strip()
    def _parse_attr_map(spec):
        out = {}
        for entry in spec.split(","):
            entry = entry.strip()
            if not entry:
                continue
            key, _, subs = entry.partition(":")
            out[key.strip()] = {s.strip() for s in subs.split(";") if s.strip()}
        return out
    flatten = _parse_attr_map(args.flatten_attr)
    dict_attrs = _parse_attr_map(args.dict_attr)
    hoist_attrs = _parse_attr_map(args.hoist_attr)

    in_path = Path(args.input) if args.input else DATA / f"{args.sector}_full.json"
    rows = json.loads(in_path.read_text())

    id_mode = detect_id_mode(rows)

    records: dict[str, dict] = {}
    skipped = no_image = price_defaulted = dup = 0
    for row in rows:
        mapped = map_record(row, id_mode, args.category, args.list_price_attr, drop_meta, strip_prefix, flatten, dict_attrs, hoist_attrs)
        if mapped is None:
            skipped += 1
            continue
        pid, item = mapped
        if not item["images"]:
            no_image += 1
        if item["original_price"] == 0.0:
            price_defaulted += 1
        if pid in records:
            dup += 1
        records[pid] = item
        if args.limit and len(records) >= args.limit:
            break

    out_path = Path(args.output) if args.output else DATA / f"{args.sector}_final.json"
    out_path.write_text(json.dumps(records, ensure_ascii=False, indent=2))

    print(f"[{args.sector}] {len(rows)} source rows -> {len(records)} Quissly records  (id_mode={id_mode})")
    print(f"  skipped (no id/title): {skipped}")
    print(f"  duplicate ids overwritten: {dup}")
    print(f"  records with no valid image: {no_image}")
    print(f"  original_price defaulted to 0: {price_defaulted}")
    print(f"  wrote -> {out_path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
