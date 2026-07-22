"""Cross-family judge harness: Claude on Vertex AI, mirroring the
judge-stability harness (analysis/judge_stability/judge_25.py, copied here
as _reference_gemini_harness.py; the original is untouched).

Reconstructs the EXACT judging context of the reported run per query —
pooled unique products across all five engines' top-20 hits in stored
first-seen order, the tier-specific system prompts (AST-extracted verbatim
from pipeline/llm_judge.py), one batched call per query — and judges with a
Claude model through AnthropicVertex (ADC auth; no API keys).

Models:
  --model claude-opus-4-8   thinking omitted  (= off on Opus 4.8)
  --model claude-sonnet-5   thinking {"type": "disabled"} sent explicitly
                            (on Sonnet 5, OMITTING thinking runs adaptive
                            thinking by default and bills thinking tokens
                            as output — a labeling task doesn't need it;
                            decision 2026-07-18: thinking OFF)

Images (--image-mode, default base64): product images are prefetched
client-side and inlined base64 with a size guard (> IMAGE_MAX_BYTES or
unfetchable -> the item is judged text-only and flagged, matching the
established convention; pharmacy URLs are dead and will be 100% text-only).
--image-mode url sends URL source blocks instead (server-side fetch; a dead
URL can fail the whole call — probe in the pilot before trusting it).
--image-mode none judges all items text-only. The mode used is recorded in
every raw file and the ops report.

Cost accounting: real usage fields (input_tokens/output_tokens) accumulate
per call; dollars via PRICE_IN/PRICE_OUT per MTok — CLEARLY MARKED
CONSTANTS, verify against current Vertex pricing before trusting totals
(token totals are always reported separately so cost recomputes trivially).

Write-once cache: raw/{query_id}.json on receipt; on startup any query
whose raw file exists and parses is skipped (resume without re-billing).
Failures -> failed/{query_id}.json (refusals recorded with stop_details
category verbatim, never content). Stop conditions: > --max-failures
permanent failures, or accumulated spend exceeding --max-budget-usd.

Usage:
  python judge_claude.py --emit-sample            # write pilot_sample.json (no API)
  python judge_claude.py --pilot --model ...      # 9 pilot queries, all in parallel
  python judge_claude.py --model ... [--limit N]  # full population (resumes)
"""
import argparse
import ast
import asyncio
import base64
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

ROOT = Path(__file__).resolve().parents[2]
JUDGED_DIR = ROOT / "comparison_final_judged" / "judged"
STABILITY_RAW = ROOT / "analysis" / "judge_stability" / "raw"
OUT = Path(__file__).resolve().parent
RAW = OUT / "raw"
FAILED = OUT / "failed"

SECTORS = ["auto", "cosmetics", "electronics", "fast_fashion",
           "furniture", "marketplace", "pharmacy"]
TIERS = ["simple", "medium", "complex"]
TOP_N = 20
SEED = 42
CANONICAL = {"Exact", "Substitute", "Complementary", "Irrelevant"}
IMAGE_MAX_BYTES = 4 * 1024 * 1024
IMAGE_LIMIT_PER_CALL = 100   # Claude rejects requests with > 100 images; a
# query whose batch carries more is split into image-bounded chunks (each
# its own self-contained call, products renumbered 1..n) and the labels are
# aggregated back in product order. Recorded as "chunks" in the raw file.
CHUNK_MAX_B64_BYTES = 20 * 1024 * 1024   # Vertex rejects requests > 30MB
# ("The request size (32537136 bytes) exceeds 30.000MB limit." — q_0730,
# q_0738 in the full run). Chunks also split when cumulative base64 image
# payload would exceed this cap (20MB leaves headroom for product text).
SUPPORTED_IMAGE_MIMES = {"image/jpeg", "image/png", "image/webp", "image/gif"}

# ---- PRICES: per-MTok USD. MARKED CONSTANTS — verify against current -------
# ---- Vertex pricing for the exact model string before trusting dollars. ----
PRICES = {
    "claude-opus-4-8": {"in": 5.00, "out": 25.00},
    # Sonnet 5 introductory pricing through 2026-08-31 ($3/$15 after):
    "claude-sonnet-5": {"in": 2.00, "out": 10.00},
}

STATS = {"calls": 0, "retries": 0, "failures": 0, "refusals": 0,
         "images_missing": 0, "images_total": 0, "e429": 0,
         "in_tokens": 0, "out_tokens": 0, "spend_usd": 0.0}


def load_prompts():
    """Byte-identical tier system prompts from the pipeline (read-only)."""
    tree = ast.parse((ROOT / "pipeline/llm_judge.py").read_text())
    prompts = {}
    for node in tree.body:
        if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name) \
                and node.targets[0].id.startswith("SYSTEM_PROMPT_") \
                and isinstance(node.value, ast.Constant):
            prompts[node.targets[0].id.split("_")[-1].lower()] = node.value.value
    assert set(prompts) == {"simple", "medium", "complex"}
    return prompts


def load_queries():
    """All 1,259 queries with pooled unique products, exactly as the main
    run built its batches (providers in stored order, hits[:20], first-seen
    dedup)."""
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


def emit_pilot_sample(queries):
    """Deterministic 9-query pilot: 3 per tier, >=5 sectors, exactly one
    pharmacy query (text-only; dead image URLs), and >=2 image-heavy
    queries with large pooled batches. Image counts come from the
    judge-stability raw cache (products minus unresolved URLs). Selection
    rule (reproducible, seed only breaks residual ties):
      - image-heavy slots: the two non-pharmacy queries with the highest
        resolvable-image count, in distinct sectors and distinct tiers.
      - pharmacy slot: the pharmacy query with the largest batch.
      - remaining slots: fill 3-per-tier, maximizing sector diversity,
        preferring median batch sizes (rank by |size - median|)."""
    img_count = {}
    for p in STABILITY_RAW.glob("*.json"):
        r = json.loads(p.read_text())
        img_count[r["query_id"]] = (len(r["product_ids"])
                                    - len(r.get("image_missing", [])))
    for q in queries:
        q["n_items"] = len(q["items"])
        q["n_images"] = img_count.get(q["query_id"], 0)

    rng = random.Random(SEED)
    chosen = []
    used_sectors, used = set(), set()

    def take(q):
        chosen.append(q)
        used.add(q["query_id"])
        used_sectors.add(q["sector"])

    heavy = sorted((q for q in queries if q["sector"] != "pharmacy"),
                   key=lambda q: (-q["n_images"], q["query_id"]))
    take(heavy[0])
    take(next(q for q in heavy if q["sector"] != heavy[0]["sector"]
              and q["tier"] != heavy[0]["tier"]))
    pharm = sorted((q for q in queries if q["sector"] == "pharmacy"),
                   key=lambda q: (-q["n_items"], q["query_id"]))
    take(pharm[0])

    sizes = sorted(q["n_items"] for q in queries)
    median = sizes[len(sizes) // 2]
    for tier in TIERS:
        while sum(1 for c in chosen if c["tier"] == tier) < 3:
            pool = [q for q in queries if q["tier"] == tier
                    and q["query_id"] not in used]
            fresh = [q for q in pool if q["sector"] not in used_sectors]
            pool = fresh or pool
            pool.sort(key=lambda q: (abs(q["n_items"] - median), q["query_id"]))
            take(pool[0])
    rng.shuffle(chosen)  # call order only; membership is deterministic
    assert len(chosen) == 9 and len(used_sectors) >= 5
    assert sum(1 for c in chosen if c["sector"] == "pharmacy") == 1
    sample = [{"query_id": q["query_id"], "sector": q["sector"],
               "tier": q["tier"], "n_products": q["n_items"],
               "n_resolvable_images": q["n_images"]} for q in chosen]
    (OUT / "pilot_sample.json").write_text(json.dumps(
        {"seed": SEED, "rule": emit_pilot_sample.__doc__, "sample": sample},
        indent=1))
    print(json.dumps(sample, indent=1))
    return {q["query_id"] for q in chosen}


def product_text(idx, item):
    def price(v):
        try:
            return f"{float(v):.2f}" if v is not None else "N/A"
        except (ValueError, TypeError):
            return str(v)
    return (f"Product {idx}:\nTitle: {item.get('title') or ''}\n"
            f"Description: {item.get('description') or ''}\n"
            f"Price: {price(item.get('price'))}\n"
            f"Discounted Price: {price(item.get('discount_price'))}")


_IMG_FETCH_SEM = asyncio.Semaphore(32)   # bound concurrent image fetches:
# without this, N parallel queries fetch ~N*60 images at once through the
# 100-connection pool and pool-wait time eats the request timeout — the
# pilot on 2026-07-18 resolved only 99/587 images this way. 32 concurrent
# fetches with a generous pool timeout matches the Gemini run's ~80%.


async def fetch_image_b64(http, url):
    if not url:
        return None
    timeout = httpx.Timeout(10.0, pool=120.0)
    for attempt in (1, 2):
        try:
            async with _IMG_FETCH_SEM:
                r = await http.get(url, timeout=timeout, follow_redirects=True)
            r.raise_for_status()
            if len(r.content) > IMAGE_MAX_BYTES:
                return None
            # trust magic bytes over the server's content-type header —
            # mislabeled data caused a 400 on q_0687 in the pilot
            b = r.content
            if b.startswith(b"\xff\xd8"):
                mime = "image/jpeg"
            elif b.startswith(b"\x89PNG"):
                mime = "image/png"
            elif b.startswith(b"GIF8"):
                mime = "image/gif"
            elif b[:4] == b"RIFF" and b[8:12] == b"WEBP":
                mime = "image/webp"
            else:
                return None   # not a supported image, whatever the header says
            # Vertex 400s many-image requests when any image's long edge
            # exceeds 2576 px ("max allowed size for many-image requests") —
            # downscale to the API's own maximum, preserving aspect ratio.
            # This is the max fidelity the API accepts, not a cost tradeoff.
            import io
            from PIL import Image
            try:
                im = Image.open(io.BytesIO(b))
                if max(im.size) > 2576:
                    im.thumbnail((2576, 2576))
                    buf = io.BytesIO()
                    im.convert("RGB").save(buf, format="JPEG", quality=88)
                    b, mime = buf.getvalue(), "image/jpeg"
                    STATS["images_resized"] = STATS.get("images_resized", 0) + 1
            except Exception:
                return None
            return {"type": "base64", "media_type": mime,
                    "data": base64.standard_b64encode(b).decode()}
        except Exception:
            if attempt == 1:
                await asyncio.sleep(0.5)
    return None


def extract_json_array(text):
    m = re.search(r"\[.*\]", text, re.DOTALL)
    return json.loads(m.group()) if m else json.loads(text.strip())


def validate(raw_text, n_items):
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
        reasoning = str(o.get("reasoning", "")).strip()
        if not reasoning:
            raise ValueError(f"empty rationale at index {i}")
        labels.append(label)
        reasonings.append(reasoning)
    return labels, reasonings


class Gate:
    def __init__(self, size):
        self.sem = asyncio.Semaphore(size)
        self.size = size
        self.withheld = 0
        self._lock = asyncio.Lock()

    async def step_down(self):
        async with self._lock:
            while self.withheld < self.size // 2:
                await self.sem.acquire()
                self.withheld += 1

    @property
    def effective(self):
        return self.size - self.withheld


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


async def judge_query(q, client, http, gate, prompts, args, progress):
    qid = q["query_id"]
    raw_path = RAW / f"{qid}.json"
    if raw_path.exists():
        try:
            json.loads(raw_path.read_text())
            progress(f"[skip] {qid} cached")
            return "cached"
        except json.JSONDecodeError:
            pass
    if STATS["failures"] > args.max_failures:
        progress(f"[abort] {qid} — failure threshold exceeded")
        return "aborted"
    if STATS["spend_usd"] > args.max_budget_usd:
        progress(f"[abort] {qid} — budget cap reached")
        return "aborted"

    async with gate.sem:
        pids = list(q["items"])
        items = [q["items"][p] for p in pids]
        missing = []
        if args.image_mode == "base64":
            imgs = await asyncio.gather(
                *(fetch_image_b64(http, it["image_url"]) for it in items))
        elif args.image_mode == "url":
            imgs = [{"type": "url", "url": it["image_url"]}
                    if it["image_url"] else None for it in items]
        else:
            imgs = [None] * len(items)
        for pid, img in zip(pids, imgs):
            if img is None:
                missing.append(pid)
        STATS["images_total"] += len(items)
        STATS["images_missing"] += len(missing)

        # chunk so no single call carries > IMAGE_LIMIT_PER_CALL images or
        # > CHUNK_MAX_B64_BYTES of base64 image payload (30MB request limit)
        chunks, cur, cur_imgs, cur_bytes = [], [], 0, 0
        for i in range(len(items)):
            has_img = imgs[i] is not None
            sz = (len(imgs[i]["data"])
                  if has_img and imgs[i].get("type") == "base64" else 0)
            if cur and (cur_imgs + (1 if has_img else 0) > IMAGE_LIMIT_PER_CALL
                        or cur_bytes + sz > CHUNK_MAX_B64_BYTES):
                chunks.append(cur)
                cur, cur_imgs, cur_bytes = [], 0, 0
            cur.append(i)
            cur_imgs += 1 if has_img else 0
            cur_bytes += sz
        if cur:
            chunks.append(cur)

        kwargs = {}
        if args.model.startswith("claude-sonnet"):
            # Sonnet 5 defaults to adaptive thinking when omitted — turn OFF
            kwargs["thinking"] = {"type": "disabled"}
        # Opus 4.8: omitting `thinking` runs without thinking (desired).

        started = datetime.now(timezone.utc).isoformat()

        async def call_chunk(idxs):
            """One self-contained call for a product subset (renumbered
            1..len). Returns (labels, reasonings, usage, latency, attempts)
            or raises RuntimeError(last_err) on permanent failure."""
            content = [{"type": "text",
                        "text": f"Search Query: {q['text']}\nJudge each of "
                                f"the following {len(idxs)} products "
                                f"independently."}]
            for j, i in enumerate(idxs, 1):
                if imgs[i] is not None:
                    content.append({"type": "image", "source": imgs[i]})
                content.append({"type": "text",
                                "text": product_text(j, items[i])})
            attempts, last_err = 0, ""
            while attempts < 5:
                attempts += 1
                t0 = time.monotonic()
                try:
                    STATS["calls"] += 1
                    msg = await asyncio.wait_for(
                        client.messages.create(
                            model=args.model, max_tokens=16000,
                            system=prompts[q["tier"]],
                            messages=[{"role": "user", "content": content}],
                            **kwargs),
                        timeout=300)
                    latency = time.monotonic() - t0
                    usage = {"input_tokens": msg.usage.input_tokens,
                             "output_tokens": msg.usage.output_tokens}
                    STATS["in_tokens"] += usage["input_tokens"]
                    STATS["out_tokens"] += usage["output_tokens"]
                    p = PRICES[args.model]
                    STATS["spend_usd"] += (usage["input_tokens"] * p["in"]
                                           + usage["output_tokens"] * p["out"]) / 1e6
                    if msg.stop_reason == "refusal":
                        cat = getattr(getattr(msg, "stop_details", None),
                                      "category", None)
                        STATS["refusals"] += 1
                        raise RuntimeError(f"refusal (category={cat})")
                    text = "".join(b.text for b in msg.content
                                   if b.type == "text")
                    labels, reasonings = validate(text, len(idxs))
                    return labels, reasonings, usage, latency, attempts
                except RuntimeError:
                    raise                     # refusal — not transient
                except ValueError as e:
                    last_err = f"invalid response: {e}"
                    STATS["retries"] += 1
                    progress(f"[re-ask] {qid} att{attempts}: {last_err[:100]}")
                    continue
                except Exception as e:
                    msg_s = str(e) or type(e).__name__
                    last_err = msg_s[:300]
                    # a single rejected image 400s the whole call — drop that
                    # image (item becomes text-only, flagged) and retry
                    m_img = re.search(r"content\.(\d+)\.image", msg_s)
                    if m_img and "400" in msg_s:
                        bad_ct = int(m_img.group(1))
                        # content layout: [0]=header, then per product:
                        # image block (if any) FOLLOWED by its text block
                        pos = 0
                        for i in idxs:
                            if imgs[i] is not None:
                                pos += 1                  # image block index
                                if pos == bad_ct:
                                    imgs[i] = None
                                    if pids[i] not in missing:
                                        missing.append(pids[i])
                                        STATS["images_missing"] += 1
                                    break
                            pos += 1                      # text block index
                        else:
                            progress(f"[fail-hard] {qid}: unmappable image "
                                     f"400 at content.{bad_ct}")
                            break
                        # rebuild content without the bad image
                        content = [content[0]]
                        for j, i in enumerate(idxs, 1):
                            if imgs[i] is not None:
                                content.append({"type": "image",
                                                "source": imgs[i]})
                            content.append({"type": "text",
                                            "text": product_text(j, items[i])})
                        STATS["retries"] += 1
                        progress(f"[img-drop] {qid} att{attempts}: dropped "
                                 f"rejected image at content.{bad_ct}")
                        continue
                    transient = isinstance(e, (asyncio.TimeoutError,
                                               TimeoutError)) \
                        or any(t in msg_s for t in
                               ("429", "RESOURCE_EXHAUSTED", "500", "502",
                                "503", "529", "UNAVAILABLE", "overloaded")) \
                        or any(t in msg_s.lower() for t in
                               ("quota", "timeout", "timed out", "connection"))
                    if not transient:
                        progress(f"[fail-hard] {qid} att{attempts}: "
                                 f"{msg_s[:140]}")
                        break
                    STATS["retries"] += 1
                    if "429" in msg_s or "RESOURCE_EXHAUSTED" in msg_s:
                        STATS["e429"] += 1
                        if STATS["e429"] >= 10 and gate.withheld == 0:
                            await gate.step_down()
                            progress(f"[rate-limit] concurrency -> "
                                     f"{gate.effective}")
                    hint = retry_hint_seconds(msg_s)
                    wait = hint if hint is not None else \
                        min(2 ** attempts, 60) * (1 + random.random())
                    progress(f"[retry] {qid} att{attempts} ({msg_s[:90]}) "
                             f"wait {wait:.0f}s")
                    await asyncio.sleep(wait)
            raise RuntimeError(last_err)

        try:
            labels, reasonings = [], []
            usage_tot = {"input_tokens": 0, "output_tokens": 0}
            latency_tot, attempts_max = 0.0, 0
            for idxs in chunks:
                cl, cr, cu, clat, catt = await call_chunk(idxs)
                labels += cl
                reasonings += cr
                usage_tot["input_tokens"] += cu["input_tokens"]
                usage_tot["output_tokens"] += cu["output_tokens"]
                latency_tot += clat
                attempts_max = max(attempts_max, catt)
            raw_path.write_text(json.dumps({
                "query_id": qid, "sector": q["sector"], "tier": q["tier"],
                "text_query": q["text"], "model": args.model,
                "region": args.region, "image_mode": args.image_mode,
                "chunks": len(chunks), "product_ids": pids,
                "labels": labels, "reasonings": reasonings,
                "image_missing": missing, "attempts": attempts_max,
                "latency_s": round(latency_tot, 2), "usage": usage_tot,
                "started_utc": started,
                "finished_utc": datetime.now(timezone.utc).isoformat(),
            }, ensure_ascii=False))
            progress(f"[ok] {qid} {q['sector']}/{q['tier']} {len(items)}p"
                     f"{'/' + str(len(chunks)) + 'chunks' if len(chunks) > 1 else ''} "
                     f"att{attempts_max} {latency_tot:.0f}s "
                     f"in={usage_tot['input_tokens']} "
                     f"out={usage_tot['output_tokens']} "
                     f"img {len(items) - len(missing)}/{len(items)} "
                     f"spend=${STATS['spend_usd']:.2f}")
            return "ok"
        except RuntimeError as e:
            last_err = str(e)
        STATS["failures"] += 1
        FAILED.mkdir(exist_ok=True)
        (FAILED / f"{qid}.json").write_text(json.dumps(
            {"query_id": qid, "error": last_err[:300],
             "refusal": last_err.startswith("refusal"),
             "started_utc": started}))
        progress(f"[FAILED] {qid}: {last_err[:110]}")
        return "failed"


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="claude-sonnet-5",
                    choices=list(PRICES))
    ap.add_argument("--project", default=os.environ.get(
        "VERTEX_PROJECT", ""))
    ap.add_argument("--region", default=os.environ.get(
        "VERTEX_REGION", "europe-west1"))
    ap.add_argument("--concurrency", type=int, default=10)
    ap.add_argument("--image-mode", default="base64",
                    choices=["base64", "url", "none"])
    ap.add_argument("--max-failures", type=int, default=60)
    ap.add_argument("--max-budget-usd", type=float,
                    default=float(os.environ.get("MAX_BUDGET_USD", "0")))
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--pilot", action="store_true")
    ap.add_argument("--emit-sample", action="store_true")
    args = ap.parse_args()

    queries = load_queries()
    if args.emit_sample:          # local only, no API — no project needed
        emit_pilot_sample(queries)
        return
    if not args.project:
        ap.error("--project or the VERTEX_PROJECT env var is required")
    if args.max_budget_usd <= 0:
        sys.exit("Set --max-budget-usd (or MAX_BUDGET_USD env) — the run "
                 "will not start without a hard spend cap.")
    RAW.mkdir(exist_ok=True)

    if args.pilot:
        sample_ids = {s["query_id"] for s in json.loads(
            (OUT / "pilot_sample.json").read_text())["sample"]}
        queries = [q for q in queries if q["query_id"] in sample_ids]
    if args.limit:
        queries = queries[:args.limit]

    from anthropic import AsyncAnthropicVertex
    client = AsyncAnthropicVertex(project_id=args.project, region=args.region)
    prompts = load_prompts()
    gate = Gate(args.concurrency)
    log = open(OUT / "progress.log", "a", buffering=1)
    done = {"n": 0}

    def progress(line):
        done["n"] += 1 if line.startswith(("[ok]", "[FAILED]", "[skip]",
                                           "[abort]")) else 0
        stamp = datetime.now(timezone.utc).strftime("%H:%M:%S")
        log.write(f"{stamp} ({done['n']}/{len(queries)}) {line}\n")
        print(f"({done['n']}/{len(queries)}) {line}", flush=True)

    t0 = time.monotonic()
    limits = httpx.Limits(max_connections=100, max_keepalive_connections=50)
    async with httpx.AsyncClient(limits=limits) as http:
        results = await asyncio.gather(
            *(judge_query(q, client, http, gate, prompts, args, progress)
              for q in queries))
    wall = time.monotonic() - t0
    n = {k: sum(1 for r in results if r == k)
         for k in ("ok", "cached", "failed", "aborted")}
    p = PRICES[args.model]
    report = [
        f"## Ops report — {datetime.now(timezone.utc).isoformat()}",
        f"- model: {args.model} @ {args.region} ({args.project}); "
        f"image_mode={args.image_mode}; thinking="
        f"{'disabled (explicit)' if args.model.startswith('claude-sonnet') else 'omitted (= off on Opus 4.8)'}",
        f"- queries: {len(queries)} — ok {n['ok']}, cached {n['cached']}, "
        f"failed {n['failed']} (refusals {STATS['refusals']}), "
        f"aborted {n['aborted']}",
        f"- calls {STATS['calls']}, retries {STATS['retries']}, "
        f"429s {STATS['e429']}, concurrency requested {args.concurrency} "
        f"effective {gate.effective}",
        f"- unresolved images: {STATS['images_missing']}/"
        f"{STATS['images_total']} items this run",
        f"- tokens: in {STATS['in_tokens']:,} out {STATS['out_tokens']:,}",
        f"- spend: ${STATS['spend_usd']:.2f} at ${p['in']}/{p['out']} per "
        f"MTok (MARKED CONSTANTS — recompute from token totals if prices "
        f"changed); cap ${args.max_budget_usd:.2f}",
        f"- wall-clock: {wall:.1f}s",
    ]
    mode = "pilot" if args.pilot else "full"
    (OUT / f"ops_report_{mode}.md").write_text("\n".join(report) + "\n")
    print("\n".join(report))
    if n["failed"] > args.max_failures:
        sys.exit(f"STOP: {n['failed']} failures > {args.max_failures}")


if __name__ == "__main__":
    asyncio.run(main())
