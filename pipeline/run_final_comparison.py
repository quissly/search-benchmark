"""Sector-parameterized comparison runner for the new _quissly.json sectors.

For a given sector it runs that sector's queries against every provider the
sector is indexed on (from providers.SECTOR_CFG), and saves the results, same shape
as the original electronics_results.json, into comparison_final_results/.

    python pipeline/run_final_comparison.py fast_fashion
    python pipeline/run_final_comparison.py marketplace --sample 10

Then judge with:
    python pipeline/llm_judge.py --sector fast_fashion
"""
import sys
import json
import time
import inspect
import argparse
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from providers import PROVIDERS, SECTOR_CFG  # noqa: E402

# data/<sector>_quissly.json  ->  (SECTOR_CFG slug, queries/query_outputs/<prefix>_queries.json)
SECTOR_MAP = {
    "fast_fashion": ("fast-fashion", "fashion"),
    "marketplace":  ("marketplace",  "marketplace"),
    "pharmacy":     ("pharmacy",     "pharmaceuticals"),
    "auto":         ("auto",         "auto_parts"),
    "cosmetics":    ("cosmetics",    "personal_care"),
    "furniture":    ("furniture",    "furniture"),
    "electronics":  ("electronics",  "electronics"),
}

ROOT        = Path(__file__).resolve().parents[1]
QUERIES_DIR = ROOT / "queries" / "query_outputs"
OUT_DIR     = ROOT / "comparison_final_results"
LIMIT       = 24


def normalize_hits(raw_hits: list) -> list:
    return [
        {
            "id":             str(h.get("id") or ""),
            "title":          (h.get("title") or "").strip(),
            "description":    (h.get("description") or "").strip(),
            "image":          h.get("image") or "",
            "price":          h.get("price"),
            "discount_price": h.get("discount_price"),
        }
        for h in raw_hits[:LIMIT]
    ]


def run_query(query_obj: dict, slug: str, providers: list, existing: dict) -> dict:
    text = query_obj.get("text_query")
    result = {
        "query_id":   query_obj["query_id"],
        "category":   query_obj["category"],
        "complexity": query_obj["complexity"],
        "text_query": text,
        "providers":  {},
    }
    for name in providers:
        if name in existing and not existing[name].get("error"):
            continue                  # already have this provider cached

        fn = PROVIDERS[name]
        try:
            if "sector" in inspect.signature(fn).parameters:
                hits, latency_ms, total = fn(text, limit=LIMIT, sector=slug)
            else:
                hits, latency_ms, total = fn(text, limit=LIMIT)
            result["providers"][name] = {
                "latency_ms": latency_ms, "total": total,
                "hits": normalize_hits(hits), "error": None,
            }
        except Exception as e:
            result["providers"][name] = {
                "latency_ms": None, "total": 0, "hits": [], "error": str(e),
            }
    return result


def load_existing(path: Path) -> dict:
    if path.exists():
        return {r["query_id"]: r for r in json.loads(path.read_text())}
    return {}


def main():
    ap = argparse.ArgumentParser(description="Run a sector's queries against its indexed providers.")
    ap.add_argument("sector", choices=list(SECTOR_MAP))
    ap.add_argument("--sample", type=int, default=None, metavar="N",
                    help="Run only the first N text queries (milestone check).")
    ap.add_argument("--force", action="store_true", help="Re-run all queries, ignore cache.")
    ap.add_argument("--delay", type=float, default=0.3, metavar="SEC",
                    help="Pause between queries (rate-limit friendliness, default 0.3).")
    args = ap.parse_args()

    slug, qprefix = SECTOR_MAP[args.sector]
    providers = [p for p in SECTOR_CFG.get(slug, {}) if p in PROVIDERS]
    if not providers:
        sys.exit(f"No providers configured for sector '{args.sector}' (slug '{slug}') in SECTOR_CFG.")

    queries = json.loads((QUERIES_DIR / f"{qprefix}_queries.json").read_text())
    text_queries = [q for q in queries if q.get("text_query")]
    if args.sample:
        text_queries = text_queries[: args.sample]

    OUT_DIR.mkdir(exist_ok=True)
    out_path = OUT_DIR / f"{args.sector}_results.json"
    done = {} if args.force else load_existing(out_path)
    all_results = dict(done)

    def needs_run(q):
        prov = done.get(q["query_id"], {}).get("providers", {})
        return any(p not in prov or prov[p].get("error") for p in providers)

    pending = [q for q in text_queries if args.force or needs_run(q)]
    print(f"[{args.sector}] providers={providers} | {len(text_queries)} text queries | {len(pending)} to run\n")

    for i, q in enumerate(pending, 1):
        qid = q["query_id"]
        print(f'[{i}/{len(pending)}] {qid} [{q["complexity"]}] "{q["text_query"]}"')
        existing = all_results.get(qid, {}).get("providers", {})
        res = run_query(q, slug, providers, existing)
        if qid in all_results:
            all_results[qid]["providers"].update(res["providers"])
        else:
            all_results[qid] = res
        for name, pdata in res["providers"].items():
            tag = f"ERROR {pdata['error']}" if pdata["error"] else f"{len(pdata['hits'])} hits {pdata['latency_ms']}ms"
            print(f"    {name}: {tag}")
        out_path.write_text(json.dumps(list(all_results.values()), indent=2, ensure_ascii=False))
        if i < len(pending):
            time.sleep(args.delay)

    print(f"\nDone. {len(all_results)} results -> {out_path.relative_to(ROOT)}")
    print("\n--- summary ---")
    entries = list(all_results.values())
    for name in providers:
        lat = [e["providers"][name]["latency_ms"] for e in entries
               if e["providers"].get(name, {}).get("latency_ms") is not None]
        errs = sum(1 for e in entries if e["providers"].get(name, {}).get("error"))
        avg = round(sum(lat) / len(lat), 1) if lat else "n/a"
        print(f"  {name}: {len(lat)} ok, {errs} errors, avg {avg} ms")


if __name__ == "__main__":
    main()
