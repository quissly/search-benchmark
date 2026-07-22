# Cross-family judge run (Claude on Vertex AI) — complete record

**Status: COMPLETE (2026-07-18). 1,259/1,259 queries judged, 0 unrecovered
failures, 0 refusals. Spend $352.80 by usage fields (160.4M in / 3.2M out,
intro $2/$10) + ≈$3 invalidated pilot calls, vs the $500 cap.**
Findings and agreement scoring: `CLAUDE_JUDGE.md`. Everything below is the
operational record: what was run, what failed, every decision, and how to
replicate.

## Full-run log (2026-07-18, appended in order)

1. **Quota blocker resolved**: the model was enabled for the **Global**
   endpoint only — `region="global"` works; every regional endpoint 429s
   at zero quota. The "Region europe-west1" decision below is superseded.
2. **Pilot (9 queries)**: complete, $3.53 incl. re-runs; found and fixed
   three image defects (fetch-pool starvation, lying content-type headers,
   the 2576px many-image dimension cap) — `PILOT_REPORT.md`. GO at
   projected $310–355 vs $500.
3. **Full run** (25-parallel, region=global, thinking disabled): 1,206
   queries completed in ~65 min, then the harness process was
   terminated externally partway through.
   **No data lost** — write-once cache.
4. **30MB request limit**: q_0730 (32.5MB) and q_0738 (41.4MB) failed with
   Vertex `FAILED_PRECONDITION: request size exceeds 30.000MB limit`
   (image-dense marketplace queries). Fix: chunks now also split when
   cumulative base64 payload exceeds `CHUNK_MAX_B64_BYTES` (20MB); both
   queries succeeded on retry (the run's only 2 multi-chunk queries).
5. **Resume pass**: remaining 53 queries in ~12 min, 0 failures ($26.68
   this pass). 28 queries across the run needed a 2nd attempt (transient).
6. **Scoring** (`score_agreement.py`, local, no API): agreement 82.2% /
   kappa 0.745 vs shipped; Spearman 1.0 on EZR/P@10/P@20/nDCG@10/nDCG@20,
   0.9 on recall. Full results in `CLAUDE_JUDGE.md` +
   `agreement/summary.json`.

## What has run (all of it non-billing)

| date (UTC+4) | action | result |
|---|---|---|
| 2026-07-17 | Path 1: Google API key vs Vertex Claude endpoint | **disproven** — `401 UNAUTHENTICATED: "API keys are not supported by this API. Expected OAuth2 access token"` (this path can never work) |
| 2026-07-17 | Raw REST probes (hand-built URLs), all regions/models | HTML 404s — an artifact of malformed URLs, superseded by SDK probes |
| 2026-07-17 | `AnthropicVertex` SDK probes, ADC as `<adc-principal>` | `403 aiplatform.endpoints.predict denied` → granted `roles/aiplatform.user` on `<gcp-project-id>` (binding left in place) |
| 2026-07-17 | Post-grant probes | `claude-opus-4-8` **exists** in `us-east5`, `europe-west1`, `europe-west4` (429 quota errors = model present, quota zero); clean "publisher model not found" in `europe-west3/9/southwest1` |
| 2026-07-17 | Full quota diagnosis | `429 RESOURCE_EXHAUSTED: Quota exceeded for aiplatform.googleapis.com/online_prediction_input_tokens_per_minute_per_base_model with base model: anthropic-claude-opus-4-8. Please submit a quota increase request.` — a 1-token call trips it ⇒ limit is zero |
| 2026-07-18 | `--emit-sample` (local, no API) | `pilot_sample.json` written — 9 queries, deterministic rule recorded in the file |

## Gate-0 pre-run state (all resolved — superseded by the full-run log above)

At the end of Gate-0 (2026-07-17/18) nothing had been judged yet: every
probe call above returned an auth/quota error before billing, and `raw/`,
`failed/` were empty. Both blockers were then cleared and the pilot, full
run, Phase-2 scoring, and Phase-3 deliverables all completed (see the
full-run log at the top of this file, `CLAUDE_JUDGE.md`, and `agreement/`):

1. ~~Vertex quota is zero~~ **RESOLVED**: the model was enabled for the
   **Global** endpoint only — `region="global"` works, where every regional
   endpoint (europe-west1 etc.) 429s at zero quota. No quota-increase
   request was needed.
2. ~~Budget caps never provided~~ **RESOLVED 2026-07-18**: MAX_BUDGET_USD =
   $500, concurrency 25 (user directives; cap-stop preserves all completed
   results via the write-once cache). The full run landed at $352.80, well
   under the cap.

## Decisions log

| decision | value | why |
|---|---|---|
| Auth path | `AnthropicVertex` + application-default credentials | Path 1 (API key) is impossible on this API — verbatim error above |
| Region | `europe-west1` (team preference; model confirmed present) | user instruction 2026-07-17 |
| Model | **claude-sonnet-5** (DECIDED) | user directive 2026-07-18; ~$225 projected vs $500 cap = 2.2x headroom, no planned partial |
| Thinking | **OFF** (user decision 2026-07-18) | labeling task; thinking bills as output. Opus 4.8: omit `thinking` (= off). Sonnet 5: MUST send `{"type": "disabled"}` explicitly — omitting it runs adaptive thinking by default. Note: fixed "thinking budgets" (`budget_tokens`) no longer exist on these models — the options are off/adaptive, so "lowest" = off. |
| Images | prefetch + base64 with 4MB guard (default) | dead URL can't fail a whole batched call, matches the Gemini-run convention; `--image-mode url` kept for a pilot probe |
| Concurrency | 25 (user final directive 2026-07-18; earlier 10 and 50 superseded) | see timing table |
| Pilot | 9 queries, ALL IN PARALLEL (user instruction 2026-07-17) | doubles as the concurrency probe |
| Prices in code | Opus $5/$25, Sonnet 5 intro $2/$10 per MTok | MARKED CONSTANTS in `judge_claude.py`; token totals always reported separately so cost recomputes if prices change. Sonnet intro pricing ends 2026-08-31 ($3/$15 after). **Recorded correction: pricing is per-MTok in DOLLARS, not $0.10/MTok — see projections.** |

## Pre-pilot projections (to be replaced by fitted pilot numbers)

Token envelope (both models — same tokenizer): **80–110M input**
(≈64,350 product text blocks + ≈51,574 resolvable images; pharmacy's
10,213 images are dead → text-only), **≈2.6–3.5M output** (per-item JSON
label + one-sentence rationale; no thinking tokens since thinking is off).

| | Opus 4.8 ($5/$25) | Sonnet 5 intro ($2/$10) | Sonnet 5 std ($3/$15) |
|---|---:|---:|---:|
| input | $400–550 | $160–220 | $240–330 |
| output | $65–100 | $26–35 | $39–53 |
| **total** | **≈$550–600** | **≈$190–255** | **≈$280–385** |

Wall-clock (1,259 calls; per-call ~30–60s at these batch sizes):

| concurrency | compute-bound | quota-bound overrides at |
|---|---|---|
| 25 | ~45–70 min | < ~2M input-TPM (then ≈ 100M/TPM minutes) |
| **10** | **~75–105 min** | < ~1M input-TPM |
| 5 | ~2.5–3.5 h | < ~500k input-TPM |

At 10-parallel the run draws ≈ 0.8–1.1M input tokens/min, so any quota
grant ≥ 1M TPM leaves concurrency as the binding constraint.

## Replication

```bash
pip install "anthropic[vertex]" httpx
gcloud auth application-default login          # principal needs roles/aiplatform.user
python analysis/judge_claude/judge_claude.py --emit-sample   # no API; writes pilot_sample.json
python analysis/judge_claude/judge_claude.py --pilot \
    --model claude-sonnet-5 --region europe-west1 \
    --concurrency 9 --max-budget-usd 10       # 9 calls, all parallel
# inspect ops_report_pilot.md + raw/, then (within the caps):
python analysis/judge_claude/judge_claude.py \
    --model claude-sonnet-5 --region europe-west1 \
    --concurrency 10 --max-budget-usd <CAP>   # resumes from raw/ forever
```

`_reference_gemini_harness.py` is a verbatim copy of the stability harness
this one mirrors (original in `analysis/judge_stability/`, untouched).
Every raw response persists to `raw/{query_id}.json` with model, region,
image mode, per-call latency, and real token usage — the write-once cache
means interrupted runs never re-bill.
