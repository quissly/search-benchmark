"""Assemble JUDGE_STABILITY.md from Phase 1 + Phase 2 outputs.

Generates the two-sentence Section-3 summary from the actual numbers in
metric_comparison.json (never hand-typed), then stitches together: run
provenance (model strings, seed, concurrency, failure accounting), the
population/sample listings, item-level agreement, metric-level comparison,
the Claude-trial side-task result, and file pointers.
"""
import json
from collections import defaultdict
from pathlib import Path

OUT = Path(__file__).resolve().parent


def image_table():
    """Cumulative image-resolution accounting across ALL raw files (the
    phase1_report.md counters only cover the final resume invocation)."""
    tot = defaultdict(lambda: [0, 0])
    for p in (OUT / "raw").glob("*.json"):
        r = json.loads(p.read_text())
        tot[r["sector"]][0] += len(r.get("image_missing", []))
        tot[r["sector"]][1] += len(r["product_ids"])
    lines = ["| sector | images resolved | rate |", "|---|---:|---:|"]
    gm = gn = 0
    for s in sorted(tot):
        miss, n = tot[s]
        gm += miss
        gn += n
        lines.append(f"| {s} | {n - miss:,}/{n:,} | {(n - miss) / n * 100:.1f}% |")
    lines.append(f"| **all** | **{gn - gm:,}/{gn:,}** | "
                 f"**{(gn - gm) / gn * 100:.1f}%** |")
    return "\n".join(lines)

# NOTE: JUDGE_STABILITY.md carries a manually-appended 2026-07-18
# normalized-pool correction addendum; regenerating overwrites the file —
# re-append the addendum (see git history) if you rerun this script.
CLAUDE_TRIAL_RESULT = """### Side task — Claude-family judging trial records

**Not found.** A read-only search of the repository, its full git
history, and the legacy output directories found no surviving judgment
records from any Claude-family judging trial: every claude/anthropic hit
was development tooling, an unrelated AWS Bedrock connectivity test, or
coincidental
product text ("Claude Monet ... Folding Screen", "philanthropic"). Nothing
from that trial was used in this stability computation."""


def main():
    mc = json.loads((OUT / "metric_comparison.json").read_text())
    phase1 = (OUT / "phase1_report.md").read_text().strip()
    phase2 = (OUT / "phase2_fragment.md").read_text().strip()
    pop = json.loads((OUT / "population_queries.json").read_text())
    sample = json.loads((OUT / "sampled_queries.json").read_text())

    item = mc["item_level"]
    rho = mc["spearman_overall"]
    big = mc["largest_cell_delta"]
    NAMES = {"ezr": "EZR", "p10": "precision@10",
             "recall20": "pooled recall@20", "ndcg10": "pooled-ideal nDCG@10"}
    min_rho = min(rho.values())
    min_scope_rho = min(r for ms in mc["spearman_by_scope"].values()
                        for r in ms.values())
    orderings = ((f"the overall five-engine ordering is identical on every "
                  f"metric (sector/tier-level orderings correlate at "
                  f"Spearman rho >= {min_scope_rho:.2f})")
                 if min_rho == 1.0 else
                 f"engine orderings correlate at Spearman rho >= "
                 f"{min_rho:.2f} across the four metrics")
    # The verdict clause is DERIVED from the numbers, never presumed:
    # disagreement is a desired finding and must be reported as such.
    stable = min_rho >= 0.9 and abs(big["delta_pp"]) < 5.0
    verdict = ("so the benchmark's engine comparisons are stable under "
               "judge substitution"
               if stable else
               "so judge substitution materially moves the numbers and the "
               "report should treat absolute metric values as "
               "judge-dependent")
    summary = (
        f"Re-judging all {mc['population']:,} benchmark queries with "
        f"gemini-2.5-flash reproduced the shipped gemini-3.5-flash labels on "
        f"{item['percent_agreement']:.1f}% of {item['n_items']:,} individual "
        f"product judgments (Cohen's kappa {item['cohens_kappa']:.2f}), and "
        f"under the re-judged labels {orderings}. The largest movement in "
        f"any metric cell is {big['delta_pp']:+.1f} pp "
        f"({NAMES[big['metric']]} for {big['engine']}, {big['scope']} "
        f"scope), {verdict}."
    )

    doc = f"""# Judge stability — Gemini 2.5 vs shipped Gemini 3.5 Flash

## Section-3 summary (paste-ready)

{summary}

---

## Provenance

- shipped judge: gemini-3.5-flash (pipeline/llm_judge.py, unchanged in all
  of git history); re-judge model: **gemini-2.5-flash** — the 2.5
  counterpart of the shipped judge, used as the specified default because no
  other 2.5 judge string exists anywhere on disk or in history (see
  analysis/report_inputs/REPORT_INPUTS.md ASK-7).
- prompts and batch format: byte-identical to the main run (system prompts
  AST-extracted from pipeline/llm_judge.py at runtime; pooled unique
  products across all five engines' top-20 hits in stored first-seen order;
  one batched call per query; product images fetched from their URLs and
  inlined before each product's text block). Pipeline files untouched.
- population: all {mc['population']:,} queries
  (population_queries.json; the original 126-query stratified sample —
  seed {sample['seed']}, {sample['per_cell']} per sector x tier — is
  recorded in sampled_queries.json).
- scored: {mc['n_queries_scored']:,} queries; {mc['n_failed_excluded']}
  permanently-failed re-judgings excluded from BOTH sides
  (qids: {', '.join(mc['failed_qids']) or 'none'}).
- write-once cache: raw/<qid>.json (one file per query, immediate persist,
  resume-without-re-billing verified in practice mid-run).

{phase1}

Note: the counters above cover the final (resume) invocation only.
Cumulative image resolution across the whole run:

{image_table()}

### Run incidents and caveats

- **Pharmacy was judged entirely text-only** in the re-judge (0 of 10,213
  image URLs resolved — the Netmeds CDN links are dead). Whether the
  original 3.5 run had working pharmacy images at its judging time is not
  knowable from disk, so pharmacy label disagreement may partly reflect a
  changed judging context rather than judge behavior. Notably, the lowest
  engine-ordering correlation in any scope is pharmacy precision@10.
- Mid-run stall: after a burst of API 503s, 21 in-flight calls hung
  indefinitely (the Gemini call had no client timeout). Fixed by adding a
  300s per-attempt `asyncio.wait_for` ceiling and resuming from the
  write-once cache; only in-flight work was repeated.
- 5 queries failed all 5 attempts during the main pass (invalid JSON — a
  visibly higher malformed-output rate than 3.5); all 5 succeeded with
  fresh attempts on the resume run, so the final population has **zero
  exclusions**.

---

{phase2}

---

{CLAUDE_TRIAL_RESULT}

---

## Files

- JUDGE_STABILITY.md - this report
- item_agreement.csv - one row per (query, product): both labels, gains, agreement flag
- confusion_matrix.csv - 4x4, rows = 3.5 labels, cols = 2.5 labels
- metric_comparison.json - every metric x engine x scope cell under both label sets, deltas, Spearman by scope, populations
- sampled_queries.json / population_queries.json - query id listings (seed {sample['seed']})
- raw/ - write-once per-query Gemini 2.5 responses; failed/ - permanent failures
- judge_25.py (Phase 1) / score_agreement.py (Phase 2) / assemble_stability.py (this)
"""
    (OUT / "JUDGE_STABILITY.md").write_text(doc)
    print(f"Wrote {OUT / 'JUDGE_STABILITY.md'}")
    print("\n--- Section-3 summary ---\n" + summary)


if __name__ == "__main__":
    main()
