# Pilot report — claude-sonnet-5 @ global, 9 queries, 2026-07-18

All 9 pilot queries judged successfully (3 harness defects found and fixed
along the way — see below). Pilot spend: **$3.53** (incl. re-judging after
fixes). No 429s at 9-parallel. Thinking disabled; image mode base64.

## Measured per-call numbers (final, images working)

| query | sector/tier | products | images | input tok | output tok | latency |
|---|---|---:|---:|---:|---:|---:|
| q_0234 | furniture/simple | 51 | 51/51 | 112,606 | 2,349 | 32s |
| q_0026 | fast_fashion/simple | 51 | 50/51 | 162,426 | 2,351 | 29s |
| q_0589 | electronics/complex | 51 | 51/51 | 90,656 | 2,864 | 36s |
| q_0628 | electronics/complex | 51 | 51/51 | 115,750 | 2,564 | 37s |
| q_0561 | electronics/medium | 51 | 51/51 | 107,161 | 2,747 | 41s |
| q_1046 | cosmetics/complex | 52 | 52/52 | 115,858 | 3,012 | 42s |
| q_0687 | marketplace/simple | 96 | 96/96 | 158,213 | 3,999 | 49s |
| q_1418 | auto/medium | 87 | 70/87 | 153,957 | 4,076 | 52s |
| q_1199 | pharmacy/medium (text-only, dead URLs) | 97 | 0/97 | 324,559 | 5,567 | 45s |

Fitted components: ~1,400–3,000 tokens/image (avg ≈ 1,800); text-only
products ~200–800 tokens except pharmacy ≈ 3,300 (monograph descriptions);
output ≈ 47–58 tokens/item.

## Full-run projection (measured basis)

- Input: ≈ 140–160M tokens (56M text incl. pharmacy's 34M + ~93M images)
  → **$280–320** at intro $2/MTok
- Output: ≈ 3.0–3.5M tokens → **$30–35** at intro $10/MTok
- **Total ≈ $310–355** vs the $500 cap (≈30–40% headroom)
- Wall-clock at 25-parallel: ≈ 50 waves × 40–50s ≈ **35–45 min** if the
  global-endpoint quota sustains a ~3.5–4.5M input-TPM draw; the pilot
  sustained ~800k TPM at 9-parallel with zero 429s, so throttling above
  that is possible — the harness steps down and keeps going.

## GO decision

Projected cost is within MAX_BUDGET_USD = $500 → per the pilot gate,
**proceed to the full run** (model claude-sonnet-5, region global,
concurrency 25, budget cap $500, resume-safe write-once cache).

## Defects found by the pilot (all fixed before the full run)

1. **Image-fetch pool starvation** — 9 parallel queries fetched ~530 images
   at once; pool-wait ate the 10s timeout → only 99/587 images resolved.
   Fix: 32-way fetch semaphore + pool timeout. 7 degraded pilot results
   invalidated and re-judged (re-bill ≈ $1.4).
2. **Mislabeled image data** — content-type headers lie; magic-byte sniffing
   now sets media_type.
3. **2576px many-image dimension limit** — Vertex 400s many-image requests
   when any image's long edge exceeds 2576px (verbatim error recorded).
   Fix: downscale to the API's own maximum (aspect preserved, JPEG q88);
   a per-image 400 fallback drops-and-flags any residual rejection.
   The >100-images-per-request split is also implemented (no current query
   exceeds 100 resolvable images; max observed 96).
