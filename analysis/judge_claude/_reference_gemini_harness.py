"""Phase 1 of the judge-stability check: re-judge queries with a Gemini 2.5
judge and cache the raw responses.

- Population: ALL 1,259 benchmark queries (upgraded from the original
  126-query stratified sample, which is recorded in sampled_queries.json;
  already-cached queries resume without re-billing). The full id list is
  written to population_queries.json. Failure threshold: the run aborts
  outstanding queries once more than MAX_FAIL=60 have permanently failed.
- Concurrency: one shared semaphore over the WHOLE per-query pipeline —
  each finishing query immediately frees its slot to the next (no wave
  barrier), and at most `concurrency` queries hold images in memory.
- Judging context reconstructs the main run exactly (pipeline/llm_judge.py):
  the pooled UNIQUE products across all five engines' hits[:20] in stored
  first-seen order, the tier-specific system prompt (extracted verbatim from
  pipeline/llm_judge.py via AST at runtime - byte-identical, pipeline files
  untouched), the same single-batched-call format with each product's image
  (fetched from its URL) preceding its numbered text block.
- Model/concurrency are parameterized here (NOT in the pipeline):
  --model (default gemini-2.5-flash: the 2.5 counterpart of the shipped
  gemini-3.5-flash judge; no other 2.5 judge string exists anywhere in this
  repo's history - see analysis/report_inputs/REPORT_INPUTS.md ASK-7),
  --concurrency (default 50 requests in flight, asyncio semaphore).
- Retries: max 5 attempts per query; exponential backoff with jitter on
  429/5xx; honors a Retry-After / retry_delay hint when the error carries
  one. Sustained hard rate limiting steps the effective concurrency down
  (permits are withheld) and the value used is recorded.
- Write-once cache: raw/{query_id}.json persisted immediately on receipt;
  on startup any query whose raw file exists and parses is skipped, so a
  partial failure resumes without re-billing. Permanent failures go to
  failed/{query_id}.json (kept out of raw/ so a later re-run retries them).
- Validation per response: parseable JSON array, one object per product
  (every index 1..n present), labels canonical (Exact / Substitute /
  Complementary / Irrelevant; the ESCI spelling "Complement" is
  canonicalized to Complementary, counted). One re-ask on invalid (within
  the 5 attempts), then the query is recorded failed and the run continues.
- If more than 6 queries fail permanently the run STOPS and reports.

Requires GEMINI_API_KEY in the environment (never printed).
Usage: judge_25.py [--limit N] [--model M] [--concurrency C]
"""
import argparse
import ast
import asyncio
import gzip
import json
import os
import random
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx
from google import genai
from google.genai import types

ROOT = Path(__file__).resolve().parents[2]
JUDGED_DIR = ROOT / "comparison_final_judged" / "judged"
OUT = Path(__file__).resolve().parent
RAW = OUT / "raw"
FAILED = OUT / "failed"

SECTORS = ["auto", "cosmetics", "electronics", "fast_fashion",
           "furniture", "marketplace", "pharmacy"]
TIERS = ["simple", "medium", "complex"]
PER_CELL = 6
SEED = 42
TOP_N = 20
MAX_FAIL = 60   # full-population run: stop once failures exceed this
CANONICAL = {"Exact", "Substitute", "Complementary", "Irrelevant"}
SUPPORTED_IMAGE_MIMES = {"image/jpeg", "image/png", "image/webp", "image/gif"}


def load_prompts():
    """Byte-identical system prompts from the pipeline, via AST (read-only)."""
    tree = ast.parse((ROOT / "pipeline/llm_judge.py").read_text())
    prompts = {}
    for node in tree.body:
        if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name) \
                and node.targets[0].id.startswith("SYSTEM_PROMPT_") \
                and isinstance(node.value, ast.Constant):
            prompts[node.targets[0].id.split("_")[-1].lower()] = node.value.value
    assert set(prompts) == {"simple", "medium", "complex"}
    return prompts


def extract_json_array(text):
    m = re.search(r"\[.*\]", text, re.DOTALL)
    return json.loads(m.group()) if m else json.loads(text.strip())


def load_queries():
    """ALL queries (full population), in sector/file order. Each record
    carries the pooled unique products rebuilt EXACTLY like the main run:
    providers in stored order, hits[:TOP_N], first-seen dedup."""
    out = []
    for sector in SECTORS:
        judged = json.load(gzip.open(JUDGED_DIR / f"{sector}_judged.json.gz",
                                     "rt", encoding="utf-8"))
        for e in judged:
            items = {}
            for pdata in e["providers"].values():
                for hit in pdata.get("hits", [])[:TOP_N]:
                    pid = str(hit["id"])
                    if pid not in items:
                        items[pid] = {
                            "title": hit.get("title") or "",
                            "description": hit.get("description") or "",
                            "image_url": hit.get("image") or "",
                            "price": hit.get("price"),
                            "discount_price": hit.get("discount_price"),
                        }
            out.append({"query_id": e["query_id"], "sector": sector,
                        "tier": e["complexity"], "text": e["text_query"],
                        "items": items})
    return out


def _format_price(v):
    try:
        return f"{float(v):.2f}" if v is not None else "N/A"
    except (ValueError, TypeError):
        return str(v)


def product_part(idx, item):
    return types.Part.from_text(text=(
        f"Product {idx}:\n"
        f"Title: {item.get('title') or ''}\n"
        f"Description: {item.get('description') or ''}\n"
        f"Price: {_format_price(item.get('price'))}\n"
        f"Discounted Price: {_format_price(item.get('discount_price'))}"))


def retry_hint_seconds(err_text):
    for pat in (r"[Rr]etry-?[Aa]fter[\"':\s]+([0-9.]+)",
                r"retry_?delay[^0-9]*([0-9.]+)"):
        m = re.search(pat, err_text)
        if m:
            try:
                return min(float(m.group(1)), 120.0)
            except ValueError:
                pass
    return None


class Gate:
    """Semaphore whose effective size can be stepped down under sustained
    rate limiting (withheld permits are never released)."""

    def __init__(self, size):
        self.sem = asyncio.Semaphore(size)
        self.size = size
        self.withheld = 0
        self._lock = asyncio.Lock()

    async def step_down(self):
        async with self._lock:
            target_hold = self.size // 2   # halve once; floor at half
            while self.withheld < target_hold:
                await self.sem.acquire()
                self.withheld += 1

    @property
    def effective(self):
        return self.size - self.withheld


async def fetch_image(http, url):
    if not url:
        return None
    try:
        r = await http.get(url, timeout=10, follow_redirects=True)
        r.raise_for_status()
        mime = r.headers.get("content-type", "image/jpeg").split(";")[0]
        if mime not in SUPPORTED_IMAGE_MIMES:
            return None
        return types.Part.from_bytes(data=r.content, mime_type=mime)
    except Exception:
        return None


def validate(raw_text, n_items):
    """Returns (labels, reasonings) or raises ValueError."""
    arr = extract_json_array(raw_text)
    if not isinstance(arr, list):
        raise ValueError("not a JSON array")
    by_index = {}
    for o in arr:
        if not isinstance(o, dict) or "index" not in o:
            raise ValueError("array item without index")
        by_index[int(o["index"])] = o
    labels, reasonings = [], []
    for i in range(1, n_items + 1):
        o = by_index.get(i)
        if o is None:
            raise ValueError(f"missing index {i}")
        label = str(o.get("label", "")).strip().capitalize()
        if label == "Complement":
            label = "Complementary"
        if label not in CANONICAL:
            raise ValueError(f"non-canonical label {o.get('label')!r}")
        labels.append(label)
        reasonings.append(str(o.get("reasoning", "")))
    return labels, reasonings


STATS = {"calls": 0, "retries": 0, "failures": 0, "images_missing": 0,
         "images_total": 0, "e429": 0}


async def judge_query(q, client, http, gate, prompts, model, progress):
    qid = q["query_id"]
    raw_path = RAW / f"{qid}.json"
    if raw_path.exists():
        try:
            json.loads(raw_path.read_text())
            progress(f"[skip] {qid} already cached")
            return "cached"
        except json.JSONDecodeError:
            pass   # unparseable partial write -> redo
    if STATS["failures"] > MAX_FAIL:
        progress(f"[abort] {qid} skipped — failure threshold exceeded")
        return "aborted"

    # The WHOLE per-query pipeline (image fetches + API call + retries) runs
    # inside one concurrency slot: a finished query immediately frees its
    # slot for the next one (no wave barrier), and only ~concurrency queries'
    # images are ever held in memory at once.
    async with gate.sem:
        return await _judge_gated(q, client, http, gate, prompts, model,
                                  progress, raw_path)


async def _judge_gated(q, client, http, gate, prompts, model, progress,
                       raw_path):
    qid = q["query_id"]
    pids = list(q["items"])
    items = [q["items"][p] for p in pids]
    image_parts = await asyncio.gather(
        *(fetch_image(http, it["image_url"]) for it in items))
    n_missing = sum(1 for p in image_parts if p is None)
    STATS["images_total"] += len(items)
    STATS["images_missing"] += n_missing

    parts = [types.Part.from_text(
        text=f"Search Query: {q['text']}\nJudge each of the following "
             f"{len(items)} products independently.")]
    for i, (item, img) in enumerate(zip(items, image_parts), 1):
        if img is not None:
            parts.append(img)
        parts.append(product_part(i, item))

    started = datetime.now(timezone.utc).isoformat()
    attempts = 0
    last_err = ""
    while attempts < 5:
        attempts += 1
        try:
            STATS["calls"] += 1
            # Hard per-attempt ceiling: without it a dropped connection hangs
            # the coroutine forever (observed: 21 queries stuck >15 min after
            # 503s) and the final gather never completes.
            resp = await asyncio.wait_for(
                client.aio.models.generate_content(
                    model=model,
                    contents=types.Content(role="user", parts=parts),
                    config=types.GenerateContentConfig(
                        system_instruction=prompts[q["tier"]]),
                ),
                timeout=300,
            )
            raw_text = resp.text or ""
            labels, reasonings = validate(raw_text, len(items))
            raw_path.write_text(json.dumps({
                "query_id": qid, "sector": q["sector"], "tier": q["tier"],
                "text_query": q["text"], "model": model,
                "product_ids": pids, "labels": labels,
                "reasonings": reasonings,
                "image_missing": [pids[i] for i, p in enumerate(image_parts)
                                  if p is None],
                "attempts": attempts, "started_utc": started,
                "finished_utc": datetime.now(timezone.utc).isoformat(),
                "raw_text": raw_text,
            }, ensure_ascii=False))
            progress(f"[ok] {qid} {q['sector']}/{q['tier']} "
                     f"{len(items)} products, attempt {attempts}, "
                     f"images {len(items) - n_missing}/{len(items)}")
            return "ok"
        except ValueError as e:            # invalid response -> one re-ask
            last_err = f"invalid response: {e}"
            STATS["retries"] += 1
            progress(f"[re-ask] {qid} attempt {attempts}: {last_err}")
            continue
        except Exception as e:
            msg = str(e) or type(e).__name__
            last_err = msg[:300]
            transient = isinstance(e, (asyncio.TimeoutError, TimeoutError)) \
                or any(t in msg for t in
                       ("429", "RESOURCE_EXHAUSTED", "500", "502",
                        "503", "UNAVAILABLE", "DEADLINE")) or \
                any(t in msg.lower() for t in
                    ("quota", "timeout", "timed out", "connection",
                     "disconnect"))
            if not transient:
                progress(f"[fail-hard] {qid} attempt {attempts}: {msg[:160]}")
                break
            STATS["retries"] += 1
            if "429" in msg or "RESOURCE_EXHAUSTED" in msg:
                STATS["e429"] += 1
                if STATS["e429"] >= 10 and gate.withheld == 0:
                    await gate.step_down()
                    progress(f"[rate-limit] stepping concurrency down to "
                             f"{gate.effective}")
            hint = retry_hint_seconds(msg)
            wait = hint if hint is not None else \
                min(2 ** attempts, 60) * (1 + random.random())
            progress(f"[retry] {qid} attempt {attempts} "
                     f"({msg[:100]}) waiting {wait:.1f}s")
            await asyncio.sleep(wait)
    STATS["failures"] += 1
    FAILED.mkdir(exist_ok=True)
    (FAILED / f"{qid}.json").write_text(json.dumps({
        "query_id": qid, "error": last_err, "attempts": attempts,
        "started_utc": started}))
    progress(f"[FAILED] {qid} after {attempts} attempts: {last_err[:120]}")
    return "failed"


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="gemini-2.5-flash")
    ap.add_argument("--concurrency", type=int, default=25)
    ap.add_argument("--limit", type=int, default=None)
    args = ap.parse_args()

    key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not key:
        sys.exit("GEMINI_API_KEY not in environment")
    RAW.mkdir(exist_ok=True)

    prompts = load_prompts()
    sampled = load_queries()   # full population (write-once cache resumes)
    (OUT / "population_queries.json").write_text(json.dumps(
        {"scope": "full population (upgraded from the 126-query sample; "
                  "sampled_queries.json records the original sample)",
         "n": len(sampled),
         "query_ids": {s: {t: [q["query_id"] for q in sampled
                              if q["sector"] == s and q["tier"] == t]
                          for t in TIERS} for s in SECTORS}}, indent=1))
    if args.limit:
        sampled = sampled[:args.limit]

    log = open(OUT / "progress.log", "a", buffering=1)
    done = {"n": 0}

    def progress(line):
        done["n"] += 1 if line.startswith(("[ok]", "[FAILED]", "[skip]")) else 0
        stamp = datetime.now(timezone.utc).strftime("%H:%M:%S")
        log.write(f"{stamp} ({done['n']}/{len(sampled)}) {line}\n")
        print(f"({done['n']}/{len(sampled)}) {line}", flush=True)

    client = genai.Client(api_key=key)
    gate = Gate(args.concurrency)
    t0 = time.monotonic()
    limits = httpx.Limits(max_connections=100, max_keepalive_connections=50)
    async with httpx.AsyncClient(limits=limits) as http:
        results = await asyncio.gather(
            *(judge_query(q, client, http, gate, prompts, args.model,
                          progress) for q in sampled))
    wall = time.monotonic() - t0

    n_ok = sum(1 for r in results if r == "ok")
    n_cached = sum(1 for r in results if r == "cached")
    n_failed = sum(1 for r in results if r == "failed")
    n_aborted = sum(1 for r in results if r == "aborted")
    report = [
        "## Phase 1 report",
        f"- model: {args.model}",
        f"- queries: {len(sampled)} in population; "
        f"{n_ok} judged this run, {n_cached} already cached (write-once "
        f"resume), {n_failed} permanently failed"
        + (f", {n_aborted} aborted after failure threshold" if n_aborted
           else ""),
        f"- API calls made this run: {STATS['calls']} "
        f"(retries within them: {STATS['retries']}, 429s: {STATS['e429']})",
        f"- concurrency: requested {args.concurrency}, effective at end "
        f"{gate.effective}" + (" (stepped down under rate limiting)"
                               if gate.withheld else " (no step-down)"),
        f"- unresolved image URLs: {STATS['images_missing']} of "
        f"{STATS['images_total']} items this run (those items were judged "
        f"text-only; per-query lists in raw/*.json image_missing)",
        f"- wall-clock: {wall:.1f}s",
    ]
    (OUT / "phase1_report.md").write_text("\n".join(report) + "\n")
    print("\n".join(report))
    if n_failed > MAX_FAIL:
        sys.exit(f"STOP: {n_failed} permanent failures (> {MAX_FAIL}) — "
                 f"population too thin, not proceeding to scoring.")


if __name__ == "__main__":
    asyncio.run(main())
