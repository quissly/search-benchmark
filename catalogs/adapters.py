"""Per-sector adapters: native columns -> the common schema.

Each adapter reads the raw files in data/raw/<sector>/ and returns a
schema-conforming DataFrame via schema.build_frame(). Adapters must NOT crash on
a missing optional column: everything is looked up defensively and anything not
explicitly mapped is routed into the `attributes` JSON.

Add new adapters to the ADAPTERS registry at the bottom.
"""

from __future__ import annotations

import csv
import glob
import json
import sys
from pathlib import Path
from typing import Any, Iterator

import pandas as pd

from schema import build_frame, clean_str

RAW = Path("data/raw")

# Some raw catalogs carry feature strings longer than the csv module's default limit.
csv.field_size_limit(min(sys.maxsize, 2**31 - 1))


def _raw(sector: str) -> Path:
    return RAW / sector


def _read_csv(path: Path, **kw) -> pd.DataFrame:
    """Robust CSV read: utf-8 with latin-1 fallback, keep everything as string."""
    kw.setdefault("dtype", str)
    kw.setdefault("keep_default_na", False)
    try:
        return pd.read_csv(path, encoding="utf-8", **kw)
    except UnicodeDecodeError:
        return pd.read_csv(path, encoding="latin-1", **kw)


def _first(row: dict, *keys: str) -> str:
    """First non-empty value among the given keys."""
    for k in keys:
        v = clean_str(row.get(k))
        if v:
            return v
    return ""


# --------------------------------------------------------------------------- #
# auto / electronics — Amazon Reviews 2023 raw_meta_* (JSONL)
# --------------------------------------------------------------------------- #
def _iter_jsonl(path: Path) -> Iterator[dict]:
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                try:
                    yield json.loads(line)
                except json.JSONDecodeError:
                    continue


def _amazon_image_url(images: Any) -> str:
    """Amazon `images` is a dict of parallel lists (hi_res/large/thumb) OR a
    list of dicts. Return the first usable URL, preferring higher resolution."""
    if isinstance(images, dict):
        for key in ("hi_res", "large", "thumb"):
            seq = images.get(key)
            if isinstance(seq, list):
                for u in seq:
                    if isinstance(u, str) and u.startswith("http"):
                        return u
    if isinstance(images, list):
        for item in images:
            if isinstance(item, dict):
                for key in ("hi_res", "large", "thumb"):
                    u = item.get(key)
                    if isinstance(u, str) and u.startswith("http"):
                        return u
            elif isinstance(item, str) and item.startswith("http"):
                return item
    return ""


def _adapt_amazon(sector: str, config: str) -> pd.DataFrame:
    path = _raw(sector) / f"{config}.jsonl"
    rows = []
    for rec in _iter_jsonl(path):
        parent = clean_str(rec.get("parent_asin"))
        categories = rec.get("categories") or []
        if isinstance(categories, list) and categories:
            category = " > ".join(clean_str(c) for c in categories if clean_str(c))
        else:
            category = clean_str(rec.get("main_category"))

        # Brand: prefer the structured details, fall back to the store name.
        details = rec.get("details") if isinstance(rec.get("details"), dict) else {}
        brand = ""
        for k in ("Brand", "Brand Name", "Manufacturer"):
            if clean_str(details.get(k)):
                brand = clean_str(details.get(k))
                break
        if not brand:
            brand = clean_str(rec.get("store"))

        attrs = {
            "main_category": rec.get("main_category"),
            "features": rec.get("features"),
            "average_rating": rec.get("average_rating"),
            "rating_number": rec.get("rating_number"),
            "store": rec.get("store"),
            "categories": categories,
            "details": details,
        }
        rows.append({
            "raw_id": parent,
            "title": rec.get("title"),
            "description": rec.get("description"),
            "brand": brand,
            "category": category,
            "price": rec.get("price"),
            "currency": "USD",
            "image_url": _amazon_image_url(rec.get("images")),
            "source_url": f"https://www.amazon.com/dp/{parent}" if parent else "",
            "attributes": attrs,
        })
    return build_frame(rows, sector, f"huggingface:McAuley-Lab/Amazon-Reviews-2023:{config}")


def adapt_auto() -> pd.DataFrame:
    return _adapt_amazon("auto", "raw_meta_Automotive")


def adapt_electronics() -> pd.DataFrame:
    return _adapt_amazon("electronics", "raw_meta_Electronics")


def adapt_cosmetics_amazon() -> pd.DataFrame:
    return _adapt_amazon("cosmetics", "raw_meta_Beauty_and_Personal_Care")


def adapt_furniture_amazon() -> pd.DataFrame:
    return _adapt_amazon("furniture", "raw_meta_Home_and_Kitchen")


def _join_path(*parts: str, sep: str = " > ") -> str:
    """Join non-empty hierarchy parts into a path string."""
    return sep.join(p for p in (clean_str(x) for x in parts) if p)


def _strip_quotes(value: Any) -> str:
    """Strip matched leading/trailing single or double quotes (luxury data)."""
    s = clean_str(value)
    while len(s) >= 2 and s[0] == s[-1] and s[0] in ("'", '"'):
        s = s[1:-1].strip()
    return s


def _parse_jsonish_list(value: Any) -> list:
    """Parse a stringified JSON list like '["a", "b"]'. Returns [] on failure."""
    s = clean_str(value)
    if not s:
        return []
    try:
        parsed = json.loads(s)
        return parsed if isinstance(parsed, list) else [parsed]
    except (json.JSONDecodeError, TypeError):
        return [s]


# --------------------------------------------------------------------------- #
# pharmacy — Netmeds medicines.csv
# --------------------------------------------------------------------------- #
def _clean_manufacturer(value: Any) -> str:
    """'* Mkt: Centaur Pharmaceuticals Pvt Ltd' -> 'Centaur Pharmaceuticals Pvt Ltd'."""
    s = clean_str(value).lstrip("* ").strip()
    for prefix in ("Mkt:", "Mfr:", "Marketer:", "Manufacturer:"):
        if s.lower().startswith(prefix.lower()):
            s = s[len(prefix):].strip()
    return s


def adapt_pharmacy() -> pd.DataFrame:
    # Primary handle writes medicines.csv; fallback (drug-dataset) differs, so
    # detect whichever file is present.
    raw = _raw("pharmacy")
    primary = raw / "medicines.csv"
    if primary.exists():
        return _adapt_pharmacy_netmeds(primary)
    # Fallback: aadyasingh55/drug-dataset (generic CSV) — map best-effort.
    csvs = sorted(raw.glob("*.csv"))
    if not csvs:
        raise FileNotFoundError(f"no pharmacy CSV in {raw}")
    return _adapt_pharmacy_generic(csvs[0])


def _adapt_pharmacy_netmeds(path: Path) -> pd.DataFrame:
    df = _read_csv(path)
    mapped = {"med_name", "drug_content", "drug_manufacturer", "disease_name",
              "final_price", "img_urls", "med_url"}
    rows = []
    for i, native in enumerate(df.to_dict("records")):
        med_url = clean_str(native.get("med_url"))
        raw_id = med_url.rstrip("/").rsplit("/", 1)[-1] if med_url else str(i)
        category = clean_str(native.get("disease_name"))
        # Trim a trailing " (123)" count from the disease/category label.
        if category.endswith(")") and "(" in category:
            head = category[: category.rfind("(")].strip()
            if head:
                category = head
        images = [u.strip() for u in clean_str(native.get("img_urls")).split(",")]
        image_url = next((u for u in images if u.startswith("http")), "")
        attrs = {k: v for k, v in native.items() if k not in mapped and clean_str(v)}
        rows.append({
            "raw_id": raw_id,
            "title": native.get("med_name"),
            "description": native.get("drug_content"),
            "brand": _clean_manufacturer(native.get("drug_manufacturer")),
            "category": category,
            "price": native.get("final_price"),
            "currency": "INR",
            "image_url": image_url,
            "source_url": med_url,
            "attributes": attrs,
        })
    return build_frame(rows, "pharmacy", "kaggle:drowsyng/medicines-dataset")


def _adapt_pharmacy_generic(path: Path) -> pd.DataFrame:
    """Best-effort mapping for the aadyasingh55/drug-dataset fallback."""
    df = _read_csv(path)
    cols = {c.lower(): c for c in df.columns}

    def pick(*names):
        for n in names:
            if n in cols:
                return cols[n]
        return None

    title_c = pick("med_name", "drug_name", "name", "medicine_name", "product_name")
    desc_c = pick("description", "drug_content", "uses", "composition")
    brand_c = pick("manufacturer", "drug_manufacturer", "brand", "marketer")
    cat_c = pick("category", "disease_name", "therapeutic_class", "type")
    price_c = pick("final_price", "price", "mrp")
    img_c = pick("img_urls", "image_url", "image")
    mapped = {c for c in (title_c, desc_c, brand_c, cat_c, price_c, img_c) if c}
    rows = []
    for i, native in enumerate(df.to_dict("records")):
        attrs = {k: v for k, v in native.items() if k not in mapped and clean_str(v)}
        rows.append({
            "raw_id": str(i),
            "title": native.get(title_c) if title_c else "",
            "description": native.get(desc_c) if desc_c else "",
            "brand": native.get(brand_c) if brand_c else "",
            "category": native.get(cat_c) if cat_c else "",
            "price": native.get(price_c) if price_c else None,
            "currency": "INR",
            "image_url": native.get(img_c) if img_c else "",
            "source_url": "",
            "attributes": attrs,
        })
    return build_frame(rows, "pharmacy", "kaggle:aadyasingh55/drug-dataset")


# --------------------------------------------------------------------------- #
# luxury_fashion — chitwanmanchanda/luxury-apparel-data
# --------------------------------------------------------------------------- #
def adapt_luxury_fashion() -> pd.DataFrame:
    path = _raw("luxury_fashion") / "Luxury_Products_Apparel_Data.csv"
    df = _read_csv(path)
    id_col = "Unnamed: 0" if "Unnamed: 0" in df.columns else None
    rows = []
    for i, native in enumerate(df.to_dict("records")):
        raw_id = clean_str(native.get(id_col)) if id_col else str(i)
        rows.append({
            "raw_id": raw_id or str(i),
            "title": _strip_quotes(native.get("ProductName")),
            "description": _strip_quotes(native.get("Description")),
            "brand": "",  # no brand column in this dataset
            "category": _join_path(native.get("Category"), native.get("SubCategory")),
            "price": None,  # no price column
            "currency": "",
            "image_url": "",  # no image URL column
            "source_url": "",
            "attributes": {},  # all native columns are mapped
        })
    return build_frame(rows, "luxury_fashion", "kaggle:chitwanmanchanda/luxury-apparel-data")


# --------------------------------------------------------------------------- #
# marketplace — Flipkart flipkart_com-ecommerce_sample.csv
# --------------------------------------------------------------------------- #
def adapt_marketplace() -> pd.DataFrame:
    path = _raw("marketplace") / "flipkart_com-ecommerce_sample.csv"
    df = _read_csv(path)
    mapped = {"uniq_id", "product_name", "description", "brand",
              "product_category_tree", "discounted_price", "image", "product_url"}
    rows = []
    for native in df.to_dict("records"):
        tree = _parse_jsonish_list(native.get("product_category_tree"))
        category = clean_str(tree[0]) if tree else ""
        images = _parse_jsonish_list(native.get("image"))
        image_url = next((clean_str(u) for u in images if clean_str(u).startswith("http")), "")
        attrs = {k: v for k, v in native.items() if k not in mapped and clean_str(v)}
        rows.append({
            "raw_id": native.get("uniq_id"),
            "title": native.get("product_name"),
            "description": native.get("description"),
            "brand": native.get("brand"),
            "category": category,
            "price": native.get("discounted_price"),
            "currency": "INR",
            "image_url": image_url,
            "source_url": native.get("product_url"),
            "attributes": attrs,
        })
    return build_frame(rows, "marketplace", "kaggle:atharvjairath/flipkart-ecommerce-dataset")


# --------------------------------------------------------------------------- #
# fast_fashion — Myntra fashion-product-images-dataset
#   styles.csv  : id, gender, masterCategory, subCategory, articleType,
#                 baseColour, season, year, usage, productDisplayName
#   styles/<id>.json : data.{brandName, price, productDescriptors.description,
#                 styleImages.default.imageURL, landingPageUrl, ...}
# --------------------------------------------------------------------------- #
def _strip_html(value: Any) -> str:
    """Crude tag stripper for the HTML product descriptions in Myntra JSON."""
    import re

    s = clean_str(value)
    if not s:
        return ""
    s = re.sub(r"<[^>]+>", " ", s)
    s = re.sub(r"\s+", " ", s)
    return s.strip()


def _myntra_json(json_dir: Path, pid: str) -> dict:
    """Return the `data` block of styles/<id>.json, or {} if absent/bad."""
    fp = json_dir / f"{pid}.json"
    if not fp.exists():
        return {}
    try:
        obj = json.loads(fp.read_text(encoding="utf-8", errors="replace"))
    except (json.JSONDecodeError, OSError):
        return {}
    data = obj.get("data") if isinstance(obj, dict) else None
    return data if isinstance(data, dict) else {}


def adapt_fast_fashion() -> pd.DataFrame:
    raw = _raw("fast_fashion")
    styles_csv = raw / "styles.csv"
    json_dir = raw / "styles"

    # styles.csv has a ragged tail (commas in productDisplayName); tolerate it.
    df = _read_csv(styles_csv, on_bad_lines="skip", engine="python")

    rows = []
    for native in df.to_dict("records"):
        pid = clean_str(native.get("id"))
        if not pid:
            continue
        data = _myntra_json(json_dir, pid)

        # Title: prefer styles.csv, fall back to JSON.
        title = clean_str(native.get("productDisplayName")) or clean_str(data.get("productDisplayName"))
        category = _join_path(native.get("masterCategory"),
                              native.get("subCategory"),
                              native.get("articleType"))

        # JSON-only enrichment (brand, description, price, CDN image URL, page url)
        brand = clean_str(data.get("brandName"))
        descriptors = data.get("productDescriptors") if isinstance(data.get("productDescriptors"), dict) else {}
        desc_block = descriptors.get("description") if isinstance(descriptors.get("description"), dict) else {}
        description = _strip_html(desc_block.get("value"))
        price = data.get("price")
        style_images = data.get("styleImages") if isinstance(data.get("styleImages"), dict) else {}
        default_img = style_images.get("default") if isinstance(style_images.get("default"), dict) else {}
        image_url = clean_str(default_img.get("imageURL"))
        landing = clean_str(data.get("landingPageUrl"))
        source_url = f"https://www.myntra.com/{landing}" if landing else ""

        attrs = {
            "gender": native.get("gender"),
            "masterCategory": native.get("masterCategory"),
            "subCategory": native.get("subCategory"),
            "articleType": native.get("articleType"),
            "baseColour": native.get("baseColour"),
            "season": native.get("season"),
            "year": native.get("year"),
            "usage": native.get("usage"),
        }
        if data:
            attrs["ageGroup"] = data.get("ageGroup")
            attrs["discountedPrice"] = data.get("discountedPrice")
            attrs["myntraRating"] = data.get("myntraRating")
            attrs["enriched_from_json"] = True

        rows.append({
            "raw_id": pid,
            "title": title,
            "description": description,
            "brand": brand,
            "category": category,
            "price": price,
            "currency": "INR",
            "image_url": image_url,
            "source_url": source_url,
            "attributes": attrs,
        })
    return build_frame(rows, "fast_fashion", "kaggle:paramaggarwal/fashion-product-images-dataset")


# --------------------------------------------------------------------------- #
# registry
# --------------------------------------------------------------------------- #
# furniture/cosmetics point at the Amazon adapters.
ADAPTERS = {
    "furniture": adapt_furniture_amazon,
    "auto": adapt_auto,
    "electronics": adapt_electronics,
    "cosmetics": adapt_cosmetics_amazon,
    "pharmacy": adapt_pharmacy,
    "fast_fashion": adapt_fast_fashion,
    "luxury_fashion": adapt_luxury_fashion,
    "marketplace": adapt_marketplace,
}
