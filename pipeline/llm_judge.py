import os
import sys
import gzip
import json
import time
import re
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
import csv
import argparse
import httpx
from pathlib import Path
from collections import defaultdict
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()
if not GEMINI_API_KEY:
    sys.exit("GEMINI_API_KEY not found in .env")

JUDGE_MODEL = "gemini-3.5-flash"

client = genai.Client(api_key=GEMINI_API_KEY)

SYSTEM_PROMPT_SIMPLE = """You are an objective e-commerce relevance judge. The user typed a short, single-concept query (e.g. "webcam", "lipstick", "brake pads", "office chair", "ibuprofen").

You will be provided with the query and a numbered list of products. Each product has details (title, description, price, discounted price) and may be preceded by its image - each image belongs to the product whose numbered text block immediately follows it. Judge EACH product independently against the query: never compare products to one another, and never let the rest of the list influence a product's label.

Assign exactly one of four relevance labels:

Exact - the product IS that exact item or a direct variant of it (e.g. "headphones" → over-ear headphones, on-ear headphones, wireless headphones; "ibuprofen" → any brand, strength, or pack size of ibuprofen; "lipstick" → any shade or finish of lipstick). Variants in size, count, dosage strength, color/shade, or flavor are still Exact. The image confirms the product is the right item when the title is ambiguous.

Substitute - the product is not the queried item but is functionally similar and could serve the same core need (e.g. "headphones" → earbuds; "ibuprofen" → a different pain reliever such as acetaminophen; "sofa" → a loveseat).

Complementary - the product is an accessory, replacement part, refill, or add-on used WITH the queried item rather than being the item itself (e.g. "headphones" → headphone stand, headphone cable, ear pads; "razor" → razor blade refills; "bed frame" → mattress).

Irrelevant - the product merely shares a keyword but belongs to a different category or serves a different audience/need (e.g. "webcam" → webcam cover sticker; "dog shampoo" → human shampoo), or the image clearly shows something other than the queried item.

Be strict: accessories and peripherals are Complementary, never Exact.

Output ONLY a JSON array with exactly one object per product, in the same numbered order: [{"index": <product number>, "label": "Exact" | "Substitute" | "Complementary" | "Irrelevant", "reasoning": "brief 1-sentence explanation"}, ...]"""

SYSTEM_PROMPT_MEDIUM = """You are an objective e-commerce relevance judge. The user typed a multi-word query specifying a product type plus one or more concrete attributes (e.g. "waterproof action camera", "oil-free face moisturizer", "ceramic brake pads for a Honda Civic", "king size wooden bed frame").

You will be provided with the query and a numbered list of products. Each product has details (title, description, price, discounted price) and may be preceded by its image - each image belongs to the product whose numbered text block immediately follows it. Judge EACH product independently against the query: never compare products to one another, and never let the rest of the list influence a product's label.

Assign exactly one of four relevance labels:

Exact - the product is the correct product type AND plausibly has the key attribute(s) stated in the query. This includes widely known products whose brand/model implies the attribute (e.g. GoPro Hero → waterproof action camera), and products of the correct type that could reasonably satisfy the user's need even if the specific attribute is not explicitly stated (e.g. "noise-cancelling sport earbuds" → Sony LinkBuds S are earbuds with ANC). The image confirms type and attributes when text is ambiguous.

Substitute - the product is the correct (or a closely related) product type but clearly lacks a key queried attribute, or is a functionally similar alternative that could still serve the user's core need (e.g. "portable USB-C monitor" → a portable HDMI-only monitor; "brake pads for a Honda Civic" → brake pads that fit a different vehicle; "oil-free moisturizer" → an oil-based moisturizer). A product made for a clearly different compatibility target stated in the query (car model, phone model, cartridge number, dosage) lacks a key attribute.

Complementary - the product is an accessory, mount, case, cable, refill, or add-on used WITH the queried item rather than the item itself (e.g. "waterproof action camera" → action camera chest mount; "king size bed frame" → king size mattress protector).

Irrelevant - the product is the wrong type entirely and does not serve the queried need, even if it shares an attribute keyword (e.g. "waterproof action camera" → waterproof phone case; "ceramic brake pads" → ceramic cookware), or the image clearly shows an unrelated product category.

Price constraint: if the query states a price restriction (e.g. "under $50", "for $20"), treat it as a key attribute. Compare against the Discounted Price when available, otherwise the Price; a product that would otherwise be Exact but exceeds the stated budget is Substitute, not Exact.

Output ONLY a JSON array with exactly one object per product, in the same numbered order: [{"index": <product number>, "label": "Exact" | "Substitute" | "Complementary" | "Irrelevant", "reasoning": "brief 1-sentence explanation"}, ...]"""

SYSTEM_PROMPT_COMPLEX = """You are an objective e-commerce relevance judge. The user typed a natural-language problem or question (e.g. "how to best manage and hide cables for a wall-mounted TV", "what helps with dandruff and an itchy scalp", "my brakes squeak when I stop").

Your job is to infer what product category would solve the problem, then judge whether each given product belongs to that category.

You will be provided with the query and a numbered list of products. Each product has details (title, description, price, discounted price) and may be preceded by its image - each image belongs to the product whose numbered text block immediately follows it. Judge EACH product independently against the query: never compare products to one another, and never let the rest of the list influence a product's label.

Assign exactly one of four relevance labels:

Exact - the product is a primary solution to the described problem (e.g. cable management query → cable raceway, cable clips, cable box; dandruff query → anti-dandruff shampoo; squeaky brakes → brake pads, anti-squeal shims). Its function directly addresses the user's stated need, even if the exact words differ; the image confirms it is a practical solution.

Substitute - the product is an alternative or partial solution: it addresses the problem, but less directly or less completely than a primary solution would (e.g. a general-purpose solution when a purpose-built one exists; dandruff query → a general scalp moisturizer).

Complementary - the product does not itself solve the problem but would naturally be used alongside the solution or the equipment mentioned in the query (e.g. wall-mounted TV cable query → TV wall mount; dandruff query → a scalp massager brush).

Irrelevant - the product shares surface-level keywords with the query but does not solve the problem (e.g. "crackling audio fix" → decorative speaker stand; "squeaky brakes" → a bicycle bell), or the image shows a product that clearly would not address the described need.

Price constraint: if the query states a price restriction (e.g. "under $50", "for $20"), treat it as a key requirement. Compare against the Discounted Price when available, otherwise the Price. A product that would otherwise be Exact but exceeds the stated budget is Substitute, not Exact. If the budget clearly applies to a whole set or basket of items (e.g. "ingredients for taco night under $35"), a single product only violates it if that one product alone exceeds the total budget. Price does not affect Complementary or Irrelevant labels.

Output ONLY a JSON array with exactly one object per product, in the same numbered order: [{"index": <product number>, "label": "Exact" | "Substitute" | "Complementary" | "Irrelevant", "reasoning": "brief 1-sentence explanation"}, ...]"""

# ESCI-style graded relevance: label -> gain
GAIN_MAP = {
    "exact":         1.0,
    "substitute":    0.1,
    "complementary": 0.01,
    "complement":    0.01,  # tolerate the ESCI spelling
    "irrelevant":    0.0,
}

def label_to_gain(label: str) -> float:
    return GAIN_MAP[label.strip().lower()]

_CONFIGS = {
    "simple":  types.GenerateContentConfig(system_instruction=SYSTEM_PROMPT_SIMPLE),
    "medium":  types.GenerateContentConfig(system_instruction=SYSTEM_PROMPT_MEDIUM),
    "complex": types.GenerateContentConfig(system_instruction=SYSTEM_PROMPT_COMPLEX),
}

def _judge_config(complexity: str) -> types.GenerateContentConfig:
    return _CONFIGS.get(complexity, _CONFIGS["medium"])

RESULTS_DIR = Path(__file__).resolve().parents[1] / "comparison_final_results"
TOP_N = 20


def extract_json_array(text: str) -> list:
    match = re.search(r"\[.*\]", text, re.DOTALL)
    if match:
        return json.loads(match.group())
    return json.loads(text.strip())


SUPPORTED_IMAGE_MIMES = {"image/jpeg", "image/png", "image/webp", "image/gif"}

def _fetch_image_part(url: str):
    try:
        r = httpx.get(url, timeout=10, follow_redirects=True)
        r.raise_for_status()
        mime = r.headers.get("content-type", "image/jpeg").split(";")[0]
        if mime not in SUPPORTED_IMAGE_MIMES:
            return None
        return types.Part.from_bytes(data=r.content, mime_type=mime)
    except Exception:
        return None


FAILED_JUDGMENT = {"label": "Irrelevant", "score": 0.0, "reasoning": "judge failed after retries", "failed": True}


def _format_price(value) -> str:
    try:
        return f"{float(value):.2f}" if value is not None else "N/A"
    except (ValueError, TypeError):
        return str(value)


def _product_text(idx: int, item: dict) -> types.Part:
    return types.Part.from_text(
        text=(
            f"Product {idx}:\n"
            f"Title: {item.get('title') or ''}\n"
            f"Description: {item.get('description') or ''}\n"
            f"Price: {_format_price(item.get('price'))}\n"
            f"Discounted Price: {_format_price(item.get('discount_price'))}"
        )
    )


def judge_products(query: str, items: list, complexity: str = "medium") -> list:
    """Judge a batch of products against one query in a single API call.
    items: dicts with title/description/image_url/price/discount_price.
    Returns one judgment dict per item, aligned by position."""
    if not items:
        return []

    with ThreadPoolExecutor(max_workers=8) as ex:
        images = list(ex.map(
            lambda it: _fetch_image_part(it["image_url"]) if it.get("image_url") else None,
            items,
        ))

    use_images = True
    for attempt in range(4):
        parts = [types.Part.from_text(
            text=f"Search Query: {query}\nJudge each of the following {len(items)} products independently."
        )]
        for i, item in enumerate(items, 1):
            if use_images and images[i - 1]:
                parts.append(images[i - 1])
            parts.append(_product_text(i, item))

        try:
            response = client.models.generate_content(
                model=JUDGE_MODEL,
                contents=types.Content(role="user", parts=parts),
                config=_judge_config(complexity),
            )
            by_index = {int(o["index"]): o for o in extract_json_array(response.text or "") if "index" in o}
            judgments = []
            for i in range(1, len(items) + 1):
                o = by_index.get(i)
                if o is None:
                    judgments.append(dict(FAILED_JUDGMENT))
                    continue
                label = str(o.get("label", "")).strip().capitalize()
                if label.lower() not in GAIN_MAP:  # unknown label -> retry on next run
                    judgments.append(dict(FAILED_JUDGMENT))
                    continue
                judgments.append({
                    "label":     label,
                    "score":     label_to_gain(label),
                    "reasoning": str(o.get("reasoning", "")),
                })
            return judgments
        except Exception as e:
            msg = str(e)
            transient = any(t in msg for t in ("429", "RESOURCE_EXHAUSTED", "500", "503", "UNAVAILABLE")) \
                        or any(t in msg.lower() for t in ("quota", "disconnect", "timeout", "timed out",
                                                          "connection", "deadline"))
            if transient:  # rate limit / server hiccup -> back off, keep images
                wait = 15 * (attempt + 1)
                print(f"    Judge attempt {attempt + 1} rate-limited/unavailable ({msg[:120]}), retrying in {wait}s…")
                time.sleep(wait)
                continue
            if use_images and any(images):  # a bad/oversized image can fail the request -> retry text-only
                use_images = False
                print(f"    Judge attempt {attempt + 1} failed ({msg[:120]}), retrying without images…")
                continue
            wait = 3 * (attempt + 1)
            print(f"    Judge attempt {attempt + 1} failed ({msg[:120]}), retrying in {wait}s…")
            time.sleep(wait)
    return [dict(FAILED_JUDGMENT) for _ in items]


def precision_at_k(judged_hits: list, k: int) -> float:
    """Graded precision: mean gain of the top-k hits (Exact=1.0, Substitute=0.1,
    Complementary=0.01, Irrelevant=0.0)."""
    top = judged_hits[:k]
    if not top:
        return 0.0
    return round(sum(h["score"] for h in top) / len(top), 4)


def read_judged(path: Path):
    """Load a judged JSON file, transparently decompressing .gz files."""
    if path.suffix == ".gz":
        with gzip.open(path, "rt", encoding="utf-8") as f:
            return json.load(f)
    return json.loads(path.read_text())


def write_judged(path: Path, entries):
    """Write judged entries as JSON, gzip-compressed when path ends in .gz."""
    text = json.dumps(entries, indent=2, ensure_ascii=False)
    if path.suffix == ".gz":
        with gzip.open(path, "wt", encoding="utf-8", compresslevel=6) as f:
            f.write(text)
    else:
        path.write_text(text)


def load_cache(path: Path) -> dict:
    """Returns (query_id, product_id) -> judgment from an existing judged file.

    Only hits that carry a 4-level `label` are reused; old binary (0/1)
    judgments are skipped so they get re-judged on the graded scale.
    """
    if not path.exists():
        return {}
    cache = {}
    for entry in read_judged(path):
        qid = entry["query_id"]
        for pdata in entry.get("providers", {}).values():
            for hit in pdata.get("hits", []):
                if "label" not in hit:
                    continue
                if hit.get("reasoning") == "judge failed after retries":
                    continue  # don't reuse failures; re-judge on resume
                key = (qid, str(hit["id"]))
                cache[key] = {
                    "label":     hit["label"],
                    "score":     hit["score"],
                    "reasoning": hit["reasoning"],
                }
    return cache


def generate_csv(raw_results: list, judged_results: list, csv_path: Path) -> None:
    """Aggregate judged results into comparison_results_aggregated.csv."""

    # Build zero-result lookup: (query_id, provider) -> bool
    zero_result: dict[tuple, bool] = {}
    for entry in raw_results:
        qid = entry["query_id"]
        for provider, pdata in entry.get("providers", {}).items():
            zero_result[(qid, provider)] = len(pdata.get("hits", [])) == 0

    # Aggregate by (engine, category, complexity)
    # stats[engine][category][complexity] = {"p10": [], "p20": [], "zero": []}
    stats: dict = defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: {"p10": [], "p20": [], "zero": []})))

    for entry in judged_results:
        qid = entry["query_id"]
        cat = entry["category"]
        cx  = entry["complexity"]
        for provider, pdata in entry.get("providers", {}).items():
            bucket = stats[provider][cat][cx]
            bucket["p10"].append(pdata["precision_at_10"])
            bucket["p20"].append(pdata["precision_at_20"])
            bucket["zero"].append(1 if zero_result.get((qid, provider), False) else 0)

    rows = []
    for engine in sorted(stats):
        for category in sorted(stats[engine]):
            for complexity in sorted(stats[engine][category]):
                b = stats[engine][category][complexity]
                n = len(b["p10"])
                avg_p10  = round(sum(b["p10"])  / n * 100, 2) if n else 0.0
                avg_p20  = round(sum(b["p20"])  / n * 100, 2) if n else 0.0
                zero_rate = round(sum(b["zero"]) / n * 100, 2) if n else 0.0
                rows.append({
                    "Engine Name":        engine,
                    "Category":           category,
                    "Complexity":         complexity,
                    "Zero-Result Rate (%)": zero_rate,
                    "Precision@10 (%)":   avg_p10,
                    "Precision@20 (%)":   avg_p20,
                    "Query Count":        n,
                })

    fieldnames = [
        "Engine Name", "Category", "Complexity",
        "Zero-Result Rate (%)", "Precision@10 (%)", "Precision@20 (%)", "Query Count",
    ]
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"CSV saved to {csv_path}  ({len(rows)} rows)")


def main():
    parser = argparse.ArgumentParser(description="LLM-as-a-Judge: score search results with Gemini 3.5 Flash.")
    parser.add_argument(
        "--sample", action="store_true",
        help="Milestone check: judge the sample run (electronics_results_sample.json)",
    )
    parser.add_argument(
        "--force", action="store_true",
        help="Re-judge all hits even if they are already in the cache",
    )
    parser.add_argument(
        "--sector", default=None,
        help="Judge comparison_final_results/<sector>_results.json (new sectors).",
    )
    parser.add_argument(
        "--workers", type=int, default=8,
        help="Number of queries judged in parallel (each query = 1 API call).",
    )
    args = parser.parse_args()

    if args.sector:
        root = Path(__file__).resolve().parents[1]
        out_dir = root / "comparison_final_judged"
        (out_dir / "judged").mkdir(parents=True, exist_ok=True)
        (out_dir / "aggregates").mkdir(parents=True, exist_ok=True)
        results_file = root / "comparison_final_results" / f"{args.sector}_results.json"
        judged_file  = out_dir / "judged" / f"{args.sector}_judged.json.gz"
        csv_file     = out_dir / "aggregates" / f"{args.sector}_aggregated.csv"
        print(f"SECTOR MODE - judging {results_file.name}")
    elif args.sample:
        results_file = RESULTS_DIR / "electronics_results_sample.json"
        judged_file  = RESULTS_DIR / "electronics_judged_sample.json"
        csv_file     = RESULTS_DIR / "comparison_results_aggregated_sample.csv"
        print("SAMPLE MODE - judging electronics_results_sample.json")
    else:
        results_file = RESULTS_DIR / "electronics_results.json"
        judged_file  = RESULTS_DIR / "electronics_judged.json"
        csv_file     = RESULTS_DIR / "comparison_results_aggregated.csv"

    if not results_file.exists():
        sys.exit(f"Results file not found: {results_file}\nRun pipeline/run_final_comparison.py first.")

    raw_results = json.loads(results_file.read_text())
    cache = {} if args.force else load_cache(judged_file)

    if args.force:
        print("FORCE mode - ignoring cache, re-judging all hits\n")
    elif cache:
        print(f"Resuming - {len(cache)} judgments already cached\n")

    # Load existing judged entries so we can merge (preserve providers not in current run)
    existing_judged: dict[str, dict] = {}
    if judged_file.exists():
        for e in read_judged(judged_file):
            existing_judged[e["query_id"]] = e

    judged_entries = []
    write_lock = threading.Lock()
    done_count = 0

    def _process_query(entry):
        """Judge one query: dedupe products across providers, one API call, build entry."""
        qid  = entry["query_id"]
        text = entry["text_query"]
        cx   = entry["complexity"]

        judged_entry = {
            "query_id":   qid,
            "category":   entry["category"],
            "complexity": cx,
            "text_query": text,
            "providers":  {},
        }
        lines = []

        # Collect the unique products across all providers for this query, the same
        # product returned by several engines is judged once.
        unique_items: dict[str, dict] = {}
        for pdata in entry.get("providers", {}).values():
            for hit in pdata.get("hits", [])[:TOP_N]:
                pid = str(hit["id"])
                if pid not in unique_items:
                    unique_items[pid] = {
                        "title":          hit.get("title") or "",
                        "description":    hit.get("description") or "",
                        "image_url":      hit.get("image") or "",
                        "price":          hit.get("price"),
                        "discount_price": hit.get("discount_price"),
                    }

        to_judge = [pid for pid in unique_items if (qid, pid) not in cache]

        fresh: set[str] = set()
        failed_this_query: dict[str, dict] = {}
        judgments = judge_products(text, [unique_items[p] for p in to_judge], cx)
        for pid, judgment in zip(to_judge, judgments):
            fresh.add(pid)
            if judgment.get("failed"):  # never cache failures -> a re-run retries them
                failed_this_query[pid] = judgment
            else:
                cache[(qid, pid)] = judgment

        if to_judge:
            lines.append(f"  {len(unique_items)} unique products across providers - "
                         f"{len(to_judge)} judged in 1 API call")

        for provider, pdata in entry.get("providers", {}).items():
            hits = pdata.get("hits", [])[:TOP_N]
            judged_hits = []
            for rank, hit in enumerate(hits, 1):
                pid = str(hit["id"])
                judgment = cache.get((qid, pid)) or failed_this_query.get(pid) or dict(FAILED_JUDGMENT)
                judged_hits.append({
                    "rank":           rank,
                    "id":             pid,
                    "title":          hit.get("title") or "",
                    "description":    hit.get("description") or "",
                    "image":          hit.get("image") or "",
                    "price":          hit.get("price"),
                    "discount_price": hit.get("discount_price"),
                    "label":          judgment["label"],
                    "score":          judgment["score"],
                    "reasoning":      judgment["reasoning"],
                    "cached":         pid not in fresh,
                })

            p10 = precision_at_k(judged_hits, 10)
            p20 = precision_at_k(judged_hits, 20)
            judged_entry["providers"][provider] = {
                "latency_ms":      pdata.get("latency_ms"),
                "precision_at_10": p10,
                "precision_at_20": p20,
                "hits":            judged_hits,
            }
            lines.append(f"  {provider}: P@10={p10}  P@20={p20}")

        # Merge: preserve providers from a previous judged run that aren't in this run
        if qid in existing_judged:
            for prov, pdata in existing_judged[qid].get("providers", {}).items():
                if prov not in judged_entry["providers"]:
                    judged_entry["providers"][prov] = pdata

        return judged_entry, lines

    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        futures = {ex.submit(_process_query, e): e for e in raw_results}
        for future in as_completed(futures):
            entry = futures[future]
            try:
                judged_entry, lines = future.result()
            except Exception as e:
                print(f'ERROR judging {entry["query_id"]} "{entry["text_query"]}": {e}')
                continue
            with write_lock:
                done_count += 1
                judged_entries.append(judged_entry)
                write_judged(judged_file, judged_entries)
                print(f'[{done_count}/{len(raw_results)}] {judged_entry["query_id"]}  '
                      f'[{judged_entry["category"]} / {judged_entry["complexity"]}]  '
                      f'"{judged_entry["text_query"]}"')
                for line in lines:
                    print(line)

    print(f"\nDone. Judged results saved to {judged_file}")

    failed = sum(1 for e in judged_entries for p in e["providers"].values()
                 for h in p["hits"] if h.get("reasoning") == "judge failed after retries")
    if failed:
        print(f"WARNING: {failed} hits could not be judged (scored 0.0). "
              f"Re-run the same command to retry just those.")

    # Generate aggregated CSV
    generate_csv(raw_results, judged_entries, csv_file)

    # Aggregate summary
    print("\n--- Aggregate Summary ---")
    provider_stats: dict[str, dict] = {}
    for entry in judged_entries:
        for provider, pdata in entry["providers"].items():
            s = provider_stats.setdefault(provider, {"p10": [], "p20": []})
            s["p10"].append(pdata["precision_at_10"])
            s["p20"].append(pdata["precision_at_20"])

    for provider, s in provider_stats.items():
        avg_p10 = round(sum(s["p10"]) / len(s["p10"]) * 100, 2) if s["p10"] else 0
        avg_p20 = round(sum(s["p20"]) / len(s["p20"]) * 100, 2) if s["p20"] else 0
        print(f"  {provider}: avg P@10={avg_p10}%  avg P@20={avg_p20}%  (over {len(s['p10'])} queries)")


if __name__ == "__main__":
    main()
