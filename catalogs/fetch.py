"""Fetch raw data for each sector into data/raw/<sector>/.

Canonical sources ONLY (no mirrors/re-uploads):

    furniture       HF McAuley-Lab/Amazon-Reviews-2023, raw_meta_Home_and_Kitchen [no token]
    auto            HF McAuley-Lab/Amazon-Reviews-2023, raw_meta_Automotive       [no token]
    electronics     HF McAuley-Lab/Amazon-Reviews-2023, raw_meta_Electronics      [no token]
    cosmetics       HF McAuley-Lab/Amazon-Reviews-2023, raw_meta_Beauty_and_...   [no token]
    pharmacy        Kaggle drowsyng/medicines-dataset (fb aadyasingh55/drug-...)  [kaggle.json]
    fast_fashion    Kaggle paramaggarwal/fashion-product-images-dataset (Myntra)  [kaggle.json]
    luxury_fashion  Kaggle chitwanmanchanda/luxury-apparel-data                   [kaggle.json]
    marketplace     Kaggle atharvjairath/flipkart-ecommerce-dataset              [kaggle.json]

NOTE: furniture and cosmetics were repointed to Amazon (so they gain image_url, and
cosmetics gains description).

Usage:
    python fetch.py --all
    python fetch.py furniture cosmetics
    python fetch.py auto --limit 20000     # cap streamed Amazon rows
"""

from __future__ import annotations

import argparse
import gzip
import io
import json
import os
import subprocess
import sys
import zipfile
from pathlib import Path

import requests

from schema import SECTORS

RAW = Path("data/raw")

# Default cap for the two huge streamed Amazon catalogs (millions of rows each).
AMAZON_LIMIT = 50_000


AMAZON_REPO = "McAuley-Lab/Amazon-Reviews-2023"
AMAZON_CONFIG = {
    "auto": "raw_meta_Automotive",
    "electronics": "raw_meta_Electronics",
    # Repointed from Kaggle/GitHub so these sectors gain images (+ descriptions):
    "cosmetics": "raw_meta_Beauty_and_Personal_Care",
    "furniture": "raw_meta_Home_and_Kitchen",
}

KAGGLE_HANDLE = {
    "pharmacy": "drowsyng/medicines-dataset",
    "fast_fashion": "paramaggarwal/fashion-product-images-dataset",
    "luxury_fashion": "chitwanmanchanda/luxury-apparel-data",
    "marketplace": "atharvjairath/flipkart-ecommerce-dataset",
}
KAGGLE_FALLBACK = {"pharmacy": "aadyasingh55/drug-dataset"}


def _dest(sector: str) -> Path:
    d = RAW / sector
    d.mkdir(parents=True, exist_ok=True)
    return d


# --------------------------------------------------------------------------- #
# auto / electronics — Amazon Reviews 2023 metadata, streamed from HF
# --------------------------------------------------------------------------- #
def _amazon_meta_urls(config: str) -> list[str]:
    """Candidate raw JSONL(.gz) URLs for a raw_meta_<Category> config."""
    category = config.replace("raw_meta_", "")
    base = f"https://huggingface.co/datasets/{AMAZON_REPO}/resolve/main/raw/meta_categories"
    return [
        f"{base}/meta_{category}.jsonl.gz",
        f"{base}/meta_{category}.jsonl",
    ]


class _CategoryNotFound(Exception):
    """Raised when every candidate URL for a raw_meta_<Category> config 404s."""


def _amazon_available_categories() -> list[str]:
    """List the meta categories actually present in the HF repo (no loader script)."""
    try:
        from huggingface_hub import HfApi

        files = HfApi().list_repo_files(AMAZON_REPO, repo_type="dataset")
    except Exception as exc:  # noqa: BLE001
        print(f"[amazon] could not list repo files: {exc!r}")
        return []
    prefix, suffix = "raw/meta_categories/meta_", ".jsonl"
    cats = [f[len(prefix):-len(suffix)] for f in files
            if f.startswith(prefix) and f.endswith(suffix)]
    return sorted(cats)


def _stream_amazon_config(sector: str, config: str, limit: int) -> Path:
    """Stream one raw_meta_<Category> JSONL(.gz) off the HF CDN, capped at `limit`.

    Returns the written path. Raises _CategoryNotFound if every candidate URL 404s.
    """
    out = _dest(sector) / f"{config}.jsonl"
    saw_only_404 = True
    for url in _amazon_meta_urls(config):
        print(f"[{sector}] streaming {url} (limit={limit})")
        try:
            with requests.get(url, stream=True, timeout=300) as resp:
                if resp.status_code == 404:
                    print(f"[{sector}]   HTTP 404, trying next candidate")
                    continue
                resp.raise_for_status()
                saw_only_404 = False
                raw = resp.raw
                stream = gzip.GzipFile(fileobj=raw) if url.endswith(".gz") else raw
                text = io.TextIOWrapper(stream, encoding="utf-8")
                written = 0
                with out.open("w", encoding="utf-8") as fh:
                    for line in text:
                        line = line.strip()
                        if not line:
                            continue
                        fh.write(line + "\n")
                        written += 1
                        if written % 10_000 == 0:
                            print(f"[{sector}]   {written:,} rows")
                        if written >= limit:
                            break
            print(f"[{sector}] wrote {out} ({written:,} rows)")
            return out
        except _CategoryNotFound:
            raise
        except Exception as exc:  # noqa: BLE001 — transient error, try next URL
            saw_only_404 = False
            print(f"[{sector}]   {url} failed: {exc!r}")
    if saw_only_404:
        raise _CategoryNotFound(config)
    raise RuntimeError(f"could not fetch Amazon metadata for {sector} ({config})")


def fetch_amazon(sector: str, limit: int) -> None:
    config = AMAZON_CONFIG[sector]

    # Preferred: the `datasets` streaming loader (unavailable since datasets>=4 dropped
    # script-based loaders, but kept so we use it again if upstream re-publishes data).
    try:
        from datasets import load_dataset

        print(f"[{sector}] streaming {AMAZON_REPO}:{config} via datasets (limit={limit})")
        ds = load_dataset(AMAZON_REPO, config, split="full", streaming=True)
        out = _dest(sector) / f"{config}.jsonl"
        written = 0
        with out.open("w", encoding="utf-8") as fh:
            for rec in ds:
                fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
                written += 1
                if written % 10_000 == 0:
                    print(f"[{sector}]   {written:,} rows")
                if written >= limit:
                    break
        print(f"[{sector}] wrote {out} ({written:,} rows)")
        return
    except Exception as exc:  # noqa: BLE001 — fall back to raw file streaming
        print(f"[{sector}] datasets loader failed ({exc!r}); falling back to raw HF file")

    # Fallback: stream the raw JSONL directly. On a category-id miss, print the real
    # configs and retry with the exact matching name (case-insensitive).
    try:
        _stream_amazon_config(sector, config, limit)
    except _CategoryNotFound:
        want = config.replace("raw_meta_", "")
        cats = _amazon_available_categories()
        print(f"[{sector}] category {want!r} not found. Available Amazon raw_meta "
              f"categories ({len(cats)}):")
        for c in cats:
            print(f"    raw_meta_{c}")
        match = next((c for c in cats if c.lower() == want.lower()), None)
        if not match:
            raise RuntimeError(
                f"[{sector}] no Amazon category matches {want!r}; pick one from the list above"
            )
        corrected = f"raw_meta_{match}"
        print(f"[{sector}] using exact matching config {corrected!r}")
        _stream_amazon_config(sector, corrected, limit)


# --------------------------------------------------------------------------- #
# Kaggle sectors
# --------------------------------------------------------------------------- #
def _ensure_kaggle_token() -> None:
    token = Path.home() / ".kaggle" / "kaggle.json"
    if not token.exists() and not (os.environ.get("KAGGLE_USERNAME") and os.environ.get("KAGGLE_KEY")):
        sys.exit(
            "Kaggle token missing. Create one at https://www.kaggle.com/settings -> "
            "'Create New Token', then save it to ~/.kaggle/kaggle.json and run "
            "`chmod 600 ~/.kaggle/kaggle.json`."
        )


def _kaggle_download(handle: str, dest: Path, files: list[str] | None = None) -> None:
    """Download a whole dataset (or specific files) and unzip in place."""
    base = [sys.executable, "-m", "kaggle", "datasets", "download", "-d", handle, "-p", str(dest)]
    if files:
        for f in files:
            cmd = base + ["-f", f]
            print(f"[kaggle] {' '.join(cmd)}")
            subprocess.run(cmd, check=True)
    else:
        cmd = base + ["--unzip"]
        print(f"[kaggle] {' '.join(cmd)}")
        subprocess.run(cmd, check=True)
    # Unzip any leftover .zip archives (single-file downloads arrive zipped).
    for z in dest.glob("*.zip"):
        with zipfile.ZipFile(z) as zf:
            zf.extractall(dest)
        z.unlink()


def fetch_kaggle(sector: str) -> None:
    _ensure_kaggle_token()
    dest = _dest(sector)
    handle = KAGGLE_HANDLE[sector]
    try:
        _kaggle_download(handle, dest)
    except subprocess.CalledProcessError as exc:
        fb = KAGGLE_FALLBACK.get(sector)
        if not fb:
            raise
        print(f"[{sector}] primary {handle} failed ({exc}); trying fallback {fb}")
        _kaggle_download(fb, dest)
    print(f"[{sector}] files: {sorted(p.name for p in dest.iterdir())}")


def fetch_fast_fashion(_limit: int | None = None) -> None:
    """Myntra: download the full archive once, then selectively extract ONLY
    `styles.csv` and the per-item `styles/<id>.json` files.

    The archive (~23 GB) bundles product image *bytes* we never want; we extract
    nothing from `images/`, keep just the metadata, and delete the archive to
    reclaim disk. Per-item JSONs hold brand, description, price and the CDN image
    URL — the image_url is a URL string only, never the image bytes.
    """
    _ensure_kaggle_token()
    dest = _dest("fast_fashion")
    handle = KAGGLE_HANDLE["fast_fashion"]

    styles_csv = dest / "styles.csv"
    json_dir = dest / "styles"
    if styles_csv.exists() and json_dir.exists() and any(json_dir.glob("*.json")):
        print(f"[fast_fashion] metadata already extracted in {dest}; skipping download")
        return

    # Download the archive without unzipping (avoids exploding 23 GB of images).
    archive = dest / "fashion-product-images-dataset.zip"
    if not archive.exists():
        cmd = [sys.executable, "-m", "kaggle", "datasets", "download", "-d", handle, "-p", str(dest)]
        print(f"[fast_fashion] {' '.join(cmd)}")
        subprocess.run(cmd, check=True)
    if not archive.exists():
        archive = next(dest.glob("*.zip"))

    extract_fast_fashion_metadata(archive, dest)
    archive.unlink(missing_ok=True)
    n = len(list(json_dir.glob("*.json")))
    print(f"[fast_fashion] extracted styles.csv + {n} per-item JSONs; archive removed")


def extract_fast_fashion_metadata(archive: Path, dest: Path) -> None:
    """Pull only styles.csv and styles/*.json out of the Myntra zip (skip images)."""
    json_dir = dest / "styles"
    json_dir.mkdir(exist_ok=True)
    with zipfile.ZipFile(archive) as zf:
        for info in zf.infolist():
            name = info.filename
            base = name.rsplit("/", 1)[-1]
            if name.endswith("/"):
                continue
            # styles.csv (ignore images.csv and any images/ bytes)
            if base == "styles.csv" and "/images/" not in name:
                with zf.open(info) as src, (dest / "styles.csv").open("wb") as out:
                    out.write(src.read())
            # per-item metadata: .../styles/<id>.json
            elif "/styles/" in f"/{name}" and base.endswith(".json"):
                with zf.open(info) as src, (json_dir / base).open("wb") as out:
                    out.write(src.read())


# --------------------------------------------------------------------------- #
# dispatch
# --------------------------------------------------------------------------- #
def fetch_sector(sector: str, limit: int | None) -> None:
    # AMAZON_CONFIG is checked first: furniture and cosmetics live here.
    if sector in AMAZON_CONFIG:
        fetch_amazon(sector, limit or AMAZON_LIMIT)
    elif sector == "fast_fashion":
        fetch_fast_fashion()
    elif sector in KAGGLE_HANDLE:
        fetch_kaggle(sector)
    else:
        raise ValueError(f"unknown sector {sector!r}")


def main() -> None:
    ap = argparse.ArgumentParser(description="Fetch raw data per sector.")
    ap.add_argument("sectors", nargs="*", help="sectors to fetch (default: all)")
    ap.add_argument("--all", action="store_true", help="fetch every sector")
    ap.add_argument("--limit", type=int, default=None,
                    help="row cap for Amazon / JSON cap for Myntra")
    args = ap.parse_args()

    targets = SECTORS if (args.all or not args.sectors) else args.sectors
    unknown = [s for s in targets if s not in SECTORS]
    if unknown:
        sys.exit(f"unknown sectors: {unknown}; valid: {SECTORS}")

    for sector in targets:
        print(f"\n=== fetch: {sector} ===")
        fetch_sector(sector, args.limit)


if __name__ == "__main__":
    main()
