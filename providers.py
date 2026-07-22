"""Search-provider adapters used by the comparison runners.

Each search_<provider>(query, limit, [sector]) returns a tuple:
    (hits, latency_ms, total)
where hits is a list of normalized hit dicts (id/title/subtitle/image/
description/url/price/discount_price/score/score_details).

Sector-aware providers (see SECTOR_CFG) resolve their credentials per sector;
a provider absent from a sector returns no results (stub).
"""
import os
import time
import requests
from algoliasearch.search.client import SearchClientSync
from dotenv import load_dotenv

load_dotenv()


# --- Provider search implementations ---

# Set QUISSLY_SEARCH_URL in .env (see config.example.env). The benchmark ran
# against a Quissly deployment exposing /api/search; any deployment with the
# same contract works.
QUISSLY_SEARCH_URL = os.environ.get("QUISSLY_SEARCH_URL", "")


# ── Sector-aware routing ──────────────────────────────────────────────
# Each sector maps a provider -> its live connection params. Values that name a
# credential (app_id, search_key, ...) are ENV VAR NAMES resolved at query time;
# index/store/org strings are literals. A provider absent from a sector returns
# no results (stub), so selecting a sector never leaks another sector's data.
DEFAULT_SECTOR = "fast-fashion"
SECTOR_CFG = {
    # Quissly is intentionally absent for these sectors -> its column stubs empty
    # (no store provisioned yet). Add "quissly": {"store": "<name>"} once set up.
    "fast-fashion": {
        "algolia": {"app_id": "APP_ID", "search_key": "SEARCH_API_KEY", "index": "fast_fashion"},
        "clerk":   {"public_key": "CLERK_PUBLIC_KEY"},
        "luigisbox": {"tracker_id": "LUIGISBOX_FAST_FASHION_TRACKER_ID"},
        "doofinder": {"hashid": "DOOFINDER_FAST_FASHION_HASH_ID"},
    },
    "marketplace": {
        "algolia": {"app_id": "APP_ID", "search_key": "SEARCH_API_KEY", "index": "marketplace"},
        "clerk":   {"public_key": "CLERK_MARKETPLACE_PUBLIC_KEY"},
        # account #4 (shared with pharmacy)
        "doofinder": {"hashid": "DOOFINDER_MARKETPLACE_HASH_ID", "api_key": "DOOFINDER_MARKETPLACE_API_KEY"},
        "luigisbox": {"tracker_id": "LUIGISBOX_MARKETPLACE_TRACKER_ID"},
    },
    "pharmacy": {
        "algolia": {"app_id": "APP_ID", "search_key": "SEARCH_API_KEY", "index": "pharmacy"},
        "clerk":   {"public_key": "CLERK_PHARMACY_PUBLIC_KEY"},
        "luigisbox": {"tracker_id": "LUIGISBOX_PHARMACY_TRACKER_ID"},
        # separate Doofinder account (#4) with its own key/quota
        "doofinder": {"hashid": "DOOFINDER_PHARMACY_HASH_ID", "api_key": "DOOFINDER_PHARMACY_API_KEY"},
    },
    "auto": {
        "algolia": {"app_id": "APP_ID", "search_key": "SEARCH_API_KEY", "index": "auto"},
        "clerk":   {"public_key": "CLERK_AUTO_PUBLIC_KEY"},
        "luigisbox": {"tracker_id": "LUIGISBOX_AUTO_TRACKER_ID"},
        # Doofinder account #3 free tier: 1000 search req/month, one 225-query
        # run costs ~23% of the monthly budget; run with --delay and don't --force.
        "doofinder": {"hashid": "DOOFINDER_AUTO_HASH_ID"},
    },
    "cosmetics": {
        "algolia": {"app_id": "APP_ID", "search_key": "SEARCH_API_KEY", "index": "cosmetics"},
        "clerk":   {"public_key": "CLERK_COSMETICS_PUBLIC_KEY"},
        "doofinder": {"hashid": "DOOFINDER_COSMETICS_HASH_ID"},
        "luigisbox": {"tracker_id": "LUIGISBOX_COSMETICS_TRACKER_ID"},
    },
    "furniture": {
        "algolia": {"app_id": "APP_ID", "search_key": "SEARCH_API_KEY", "index": "furniture"},
        "clerk":   {"public_key": "CLERK_FURNITURE_PUBLIC_KEY"},
        "luigisbox": {"tracker_id": "LUIGISBOX_FURNITURE_TRACKER_ID"},
        "doofinder": {"hashid": "DOOFINDER_FURNITURE_HASH_ID"},
    },
    # New 50k electronics (electronics_quissly.json).
    "electronics": {
        "algolia": {"app_id": "APP_ID", "search_key": "SEARCH_API_KEY", "index": "electronics"},
        "clerk":   {"public_key": "CLERK_ELECTRONICS_PUBLIC_KEY"},
        "doofinder": {"hashid": "DOOFINDER_ELECTRONICS_HASH_ID"},
        "luigisbox": {"tracker_id": "LUIGISBOX_ELECTRONICS_TRACKER_ID"},
    },
}


def _cfg(sector, provider):
    """Connection params for (sector, provider), or None if not configured."""
    return SECTOR_CFG.get(sector or DEFAULT_SECTOR, {}).get(provider)


def search_quissly(query, limit=24, sector=DEFAULT_SECTOR):
    cfg = _cfg(sector, "quissly")
    if not cfg:
        return [], 0.0, 0
    t0 = time.perf_counter()
    resp = requests.post(QUISSLY_SEARCH_URL, json={
        "query": query,
        "store": cfg["store"],
        "page": 1,
        "limit": limit,
    }, timeout=30)
    if not resp.ok and not resp.content:
        raise Exception(f"{resp.status_code}: {resp.text}")
    elapsed = (time.perf_counter() - t0) * 1000
    body = resp.json()

    hits = []
    for doc in body.get("documents", []):
        meta = doc.get("metadata") or doc
        images = meta.get("images") or []
        hits.append({
            "id": doc.get("id"),
            "title": meta.get("title") or "",
            "subtitle": (meta.get("metadata") or {}).get("brand") or meta.get("category") or "",
            "image": images[0] if images else meta.get("image") or "",
            "description": meta.get("description") or "",
            "url": meta.get("url") or "",
            "price": meta.get("original_price"),
            "discount_price": meta.get("discounted_price"),
            "score": doc.get("score"),
            "score_details": {},
        })
    return hits, round(elapsed, 1), body.get("num_total_results", len(hits))


def search_algolia(query, limit=10, sector=DEFAULT_SECTOR):
    cfg = _cfg(sector, "algolia")
    if not cfg:
        return [], 0.0, 0
    client = SearchClientSync(os.environ[cfg["app_id"]], os.environ[cfg["search_key"]])
    t0 = time.perf_counter()
    resp = client.search_single_index(
        index_name=cfg["index"],
        search_params={"query": query, "hitsPerPage": limit},
    )
    elapsed = (time.perf_counter() - t0) * 1000
    client.close()

    hits = []
    for hit in resp.hits:
        h = hit.to_dict()
        hits.append({
            "id": h.get("id"),
            "title": h.get("title") or "",
            "subtitle": (h.get("metadata") or {}).get("brandName") or h.get("category") or "",
            "image": (h.get("images") or [""])[0],
            "description": h.get("description") or "",
            "url": h.get("url") or "",
            "price": h.get("original_price"),
            "discount_price": h.get("discounted_price"),
            "score": None,
            "score_details": {},
        })
    return hits, round(elapsed, 1), resp.nb_hits


def search_doofinder(query, limit=10, sector=DEFAULT_SECTOR):
    cfg = _cfg(sector, "doofinder")
    if not cfg:
        return [], 0.0, 0
    hashid  = os.environ[cfg["hashid"]]
    # sectors may live on separate Doofinder accounts, each with its own key
    api_key = os.environ[cfg.get("api_key", "DOOFINDER_API_KEY")]
    region = api_key.split("-")[0]

    t0 = time.perf_counter()
    resp = requests.get(
        f"https://{region}-search.doofinder.com/6/{hashid}/_search",
        headers={"Authorization": f"Token {api_key}"},
        params={"query": query, "rpp": limit},
        timeout=30,
    )
    resp.raise_for_status()
    elapsed = (time.perf_counter() - t0) * 1000

    body = resp.json()
    hits = []
    for r in body.get("results", []):
        # CSV feed columns: id,title,description,link,image_link,images,price,
        # sale_price,availability,brand,category,categories,specs,metadata
        images = r.get("images", "")
        if isinstance(images, str):
            try:
                import json as _json
                images = _json.loads(images)
            except Exception:
                images = []
        def _num(v):  # CSV feed stringifies numbers; missing values arrive as "None"
            try:
                return float(v)
            except (TypeError, ValueError):
                return None
        hits.append({
            "id": r.get("id"),
            "title": r.get("title") or "",
            "subtitle": r.get("brand") or r.get("category") or "",
            "image": r.get("image_link") or (images[0] if images else ""),
            "description": r.get("description") or "",
            "url": r.get("link") or "",
            "price": _num(r.get("price")),
            "discount_price": _num(r.get("sale_price")),
            "score": r.get("dfscore"),
            "score_details": {},
        })
    return hits, round(elapsed, 1), body.get("total", len(hits))


def search_luigisbox(query, limit=10, sector=DEFAULT_SECTOR):
    cfg = _cfg(sector, "luigisbox")
    if not cfg:
        return [], 0.0, 0
    tracker_id = os.environ[cfg["tracker_id"]]

    t0 = time.perf_counter()
    resp = requests.get(
        "https://live.luigisbox.com/search",
        params={"tracker_id": tracker_id, "q": query, "size": limit},
        timeout=30,
    )
    resp.raise_for_status()
    elapsed = (time.perf_counter() - t0) * 1000

    def _first(v):
        if isinstance(v, list):
            return v[0] if v else None
        return v

    body    = resp.json()
    results = body.get("results", {}) or {}
    hits = []
    for r in results.get("hits", []):
        attrs   = r.get("attributes", {}) or {}
        old     = attrs.get("price_old")
        current = attrs.get("price")
        hits.append({
            "id":             r.get("url"),  # identity we indexed (product id)
            "title":          attrs.get("title") or "",
            "subtitle":       _first(attrs.get("brand")) or _first(attrs.get("category")) or "",
            "image":          attrs.get("image_link") or _first(attrs.get("images")) or "",
            "description":    attrs.get("description") or "",
            "url":            _first(attrs.get("web_url")) or "",
            "price":          old if old is not None else current,
            "discount_price": current if old is not None else None,
            "score":          None,  # Luigi's Box does not return a relevance score
            "score_details":  {},
        })
    return hits, round(elapsed, 1), results.get("total_hits", len(hits))


def search_clerk(query, limit=10, sector=DEFAULT_SECTOR):
    cfg = _cfg(sector, "clerk")
    if not cfg:
        return [], 0.0, 0
    public_key = os.environ[cfg["public_key"]]

    t0 = time.perf_counter()
    resp = requests.post(
        "https://api.clerk.io/v2/search/search",
        json={
            "key":        public_key,
            "query":      query,
            "limit":      limit,
            "labels":     ["Benchmark"],
            "attributes": ["id", "name", "description", "image", "url",
                           "price", "list_price", "brand", "category"],
        },
        timeout=30,
    )
    resp.raise_for_status()
    elapsed = (time.perf_counter() - t0) * 1000

    body = resp.json()
    if body.get("status") == "error":
        raise Exception(body.get("message", "clerk error"))

    # Clerk returns parallel arrays: result[] (ids) + product_data[] (objects).
    products = body.get("product_data")
    if not products:
        products = [{"id": pid} for pid in body.get("result", [])]

    hits = []
    for p in products:
        old = p.get("list_price")
        cur = p.get("price")
        hits.append({
            "id":             p.get("id"),
            "title":          p.get("name") or "",
            "subtitle":       p.get("brand") or p.get("category") or "",
            "image":          p.get("image") or "",
            "description":    p.get("description") or "",
            "url":            p.get("url") or "",
            "price":          old if old is not None else cur,
            "discount_price": cur if old is not None else None,
            "score":          None,  # Clerk does not return a per-hit relevance score
            "score_details":  {},
        })
    return hits, round(elapsed, 1), body.get("count", len(hits))


PROVIDERS = {
    "quissly":       search_quissly,
    "algolia":       search_algolia,
    "doofinder":     search_doofinder,
    "luigisbox":     search_luigisbox,
    "clerk":         search_clerk,
}
