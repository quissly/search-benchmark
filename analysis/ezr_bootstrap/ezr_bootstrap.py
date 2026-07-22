"""Paired bootstrap significance testing for the EFFECTIVE ZERO-RESULT RATE.

Metric (per engine, per query — binary):
  1 if the engine returned no hits at all, OR returned hits and every one was
  judged Irrelevant (gain 0). Else 0. "The shopper got nothing useful."
  Denominator: ALL queries, no exclusions (n = 1,259 for every engine —
  asserted from the data).

Method: identical harness to analysis/bootstrap/paired_bootstrap.py — paired
on query, resample whole queries with replacement, B = 10,000 replicates,
numpy default_rng(seed=42) consumed in a fixed deterministic cell order.
Cells: Quissly vs each of the 4 rivals x [7 sectors + 3 complexity tiers +
pooled] = 44 new tests. Sign convention: observed_diff = quissly_rate -
vendor_rate, so NEGATIVE favors Quissly (lower effective-zero rate is
better).

Holm correction spans the COMBINED family: these 44 tests plus the 192
previously run tests (precision/recall p_raw from the committed
analysis/bootstrap/20260718_112921Z/bootstrap_results.csv; nDCG p_raw from
the pooled-IDCG run analysis/ndcg_pooled/bootstrap_results.csv, matching
the published consolidated family) = 236 tests.
Any previously-significant cell that loses significance in the larger family
is reported.

Reads judged data + committed CSVs read-only. Writes only into
analysis/ezr_bootstrap/ (ezr_results.csv, summary.md).
Run with a venv that has numpy + pandas (pipeline import needs pandas).
"""
import csv
import gzip
import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
JUDGED_DIR = ROOT / "comparison_final_judged" / "judged"
AGGREGATES_DIR = ROOT / "comparison_final_judged" / "aggregates"
ORIGINAL_CSV = ROOT / "analysis/bootstrap/20260718_112921Z/bootstrap_results.csv"
POOLED_NDCG_CSV = ROOT / "analysis/ndcg_pooled/bootstrap_results.csv"
OUT_DIR = Path(__file__).resolve().parent

SEED = 42
N_REPLICATES = 10_000
ALPHA = 0.05

QUISSLY = "quissly"
COMPARATORS = ["algolia", "clerk", "doofinder", "luigisbox"]
ENGINES = [QUISSLY] + COMPARATORS
SECTORS = ["auto", "cosmetics", "electronics", "fast_fashion",
           "furniture", "marketplace", "pharmacy"]
TIERS = ["simple", "medium", "complex"]
DISPLAY = {"algolia": "Algolia", "clerk": "Clerk.io", "doofinder": "Doofinder",
           "luigisbox": "Luigi's Box", "quissly": "Quissly"}


def load_scores():
    """(sector, qid) -> {complexity, engine -> ezr(0/1),
    engine -> (zero, alljunk)}."""
    rows = []
    for sector in SECTORS:
        judged = json.load(gzip.open(JUDGED_DIR / f"{sector}_judged.json.gz",
                                     "rt", encoding="utf-8"))
        for entry in judged:
            providers = entry["providers"]
            assert set(providers) == set(ENGINES), entry["query_id"]
            rec = {"sector": sector, "qid": entry["query_id"],
                   "complexity": entry["complexity"], "ezr": {}, "parts": {}}
            for eng in ENGINES:
                hits = providers[eng].get("hits", [])
                scores = [h["score"] for h in hits]
                zero = not hits
                alljunk = bool(hits) and all(s == 0 for s in scores)
                rec["ezr"][eng] = 1 if (zero or alljunk) else 0
                rec["parts"][eng] = (zero, alljunk)
            rows.append(rec)
    return rows


def reconcile(rows):
    """Reconciliation table: zero-result + all-junk counts from the judged
    data vs (a) the shipped aggregates CSVs (zero-result, query-weighted) and
    (b) the shipped pipeline compute_rich_metrics (all-junk). EZR must equal
    their sum, since the two failure modes are disjoint by construction."""
    sys.path.insert(0, str(ROOT))
    from pipeline.metrics_dashboard import compute_rich_metrics
    rich = compute_rich_metrics([JUDGED_DIR / f"{s}_judged.json.gz"
                                 for s in SECTORS])

    n = len(rows)
    lines = ["## Reconciliation with shipped numbers (before bootstrapping)\n",
             f"Queries per engine: {n} (asserted identical for all engines; "
             f"no exclusions).\n",
             "| engine | zero-result n (%) | CSV zero-result % | all-junk n "
             "(%) | pipeline all-junk % | EZR n (%) = sum |",
             "|---|---:|---:|---:|---:|---:|"]
    csv_zero = {}
    for sector in SECTORS:
        for r in csv.DictReader(open(
                AGGREGATES_DIR / f"{sector}_aggregated.csv",
                encoding="utf-8")):
            eng = r["Engine Name"]
            if eng not in csv_zero:
                csv_zero[eng] = [0.0, 0]
            cnt = int(r["Query Count"])
            csv_zero[eng][0] += float(r["Zero-Result Rate (%)"]) * cnt
            csv_zero[eng][1] += cnt
    for eng in ENGINES:
        assert sum(1 for r in rows if eng in r["ezr"]) == n
        zc = sum(1 for r in rows if r["parts"][eng][0])
        ac = sum(1 for r in rows if r["parts"][eng][1])
        ec = sum(r["ezr"][eng] for r in rows)
        assert ec == zc + ac, eng   # disjoint by construction
        csv_pct = csv_zero[eng][0] / csv_zero[eng][1]
        pipe_aj = rich[eng]["alljunk"]
        assert abs(zc / n * 100 - csv_pct) < 0.05, (eng, zc / n * 100, csv_pct)
        assert abs(ac / n * 100 - pipe_aj) < 1e-6, (eng, ac / n * 100, pipe_aj)
        lines.append(f"| {eng} | {zc} ({zc / n * 100:.2f}%) | {csv_pct:.2f}% "
                     f"| {ac} ({ac / n * 100:.2f}%) | {pipe_aj:.2f}% | "
                     f"{ec} ({ec / n * 100:.2f}%) |")
    # spot claims from the task
    alg_complex = [r for r in rows if r["complexity"] == "complex"]
    alg_zero_complex = sum(1 for r in alg_complex if r["parts"]["algolia"][0])
    lines.append(f"\nSpot checks: Quissly all-junk = "
                 f"{sum(1 for r in rows if r['parts']['quissly'][1])}/{n} = "
                 f"{sum(1 for r in rows if r['parts']['quissly'][1]) / n * 100:.2f}% "
                 f"(shipped 3.89%); Algolia zero-results on complex tier = "
                 f"{alg_zero_complex}/{len(alg_complex)} "
                 f"(claim in task: 302/315).")
    return lines


def main():
    rows = load_scores()
    recon_lines = reconcile(rows)
    print("\n".join(recon_lines))

    # ── Bootstrap the 44 new cells ───────────────────────────────────────────
    slots = SECTORS + TIERS + ["pooled"]

    def slot_rows(slot):
        if slot == "pooled":
            return rows
        if slot in SECTORS:
            return [r for r in rows if r["sector"] == slot]
        return [r for r in rows if r["complexity"] == slot]

    rng = np.random.default_rng(SEED)
    cells = []
    for vendor in COMPARATORS:              # fixed deterministic order
        for slot in slots:
            rs = slot_rows(slot)
            diffs = np.array([r["ezr"][QUISSLY] - r["ezr"][vendor]
                              for r in rs], dtype=float)
            n = len(diffs)
            idx = rng.integers(0, n, size=(N_REPLICATES, n))
            boot = diffs[idx].mean(axis=1)
            ci_low, ci_high = np.percentile(boot, [2.5, 97.5])
            p_raw = min(1.0, 2 * min((boot <= 0).mean(), (boot >= 0).mean()))
            cells.append({
                "metric": "effective_zero_rate",
                "sector": slot if slot in SECTORS + ["pooled"] else f"tier_{slot}",
                "vendor_pair": f"quissly_vs_{vendor}",
                "quissly_mean": float(np.mean([r["ezr"][QUISSLY] for r in rs])),
                "other_mean": float(np.mean([r["ezr"][vendor] for r in rs])),
                "observed_diff": float(diffs.mean()),
                "ci_low": float(ci_low), "ci_high": float(ci_high),
                "p_raw": float(p_raw), "n_queries": n,
                "n_replicates": N_REPLICATES, "seed": SEED,
            })

    # ── Holm across the combined 236-test family ─────────────────────────────
    # Family composition mirrors the published consolidated pass
    # (analysis/report_inputs/consolidated_holm.csv): precision/recall rows
    # from the committed bootstrap run + the POOLED-IDCG nDCG rows from
    # analysis/ndcg_pooled/ (not the superseded self-normalized nDCG rows).
    orig = pd.concat([
        pd.read_csv(ORIGINAL_CSV).query("~metric.str.startswith('ndcg')"),
        pd.read_csv(POOLED_NDCG_CSV).query("metric.str.startswith('ndcg')"),
    ], ignore_index=True)
    family = [{"id": ("orig", i), "p_raw": p} for i, p in
              enumerate(orig["p_raw"])]
    family += [{"id": ("new", i), "p_raw": c["p_raw"]}
               for i, c in enumerate(cells)]
    m = len(family)
    order = sorted(range(m), key=lambda i: family[i]["p_raw"])
    running = 0.0
    p_holm = {}
    for rank, i in enumerate(order):
        running = max(running, (m - rank) * family[i]["p_raw"])
        p_holm[family[i]["id"]] = min(1.0, running)
    for i, c in enumerate(cells):
        c["p_holm"] = p_holm[("new", i)]
        c["significant_after_holm"] = c["p_holm"] < ALPHA
        c["within_noise"] = (not c["significant_after_holm"]) or \
            (c["ci_low"] <= 0 <= c["ci_high"])
    orig["p_holm_236"] = [p_holm[("orig", i)] for i in range(len(orig))]
    orig_flips = orig[(orig["significant_after_holm"])
                      & (orig["p_holm_236"] >= ALPHA)]

    df = pd.DataFrame(cells)[[
        "metric", "sector", "vendor_pair", "quissly_mean", "other_mean",
        "observed_diff", "ci_low", "ci_high", "p_raw", "p_holm",
        "significant_after_holm", "within_noise", "n_queries",
        "n_replicates", "seed"]]
    df.to_csv(OUT_DIR / "ezr_results.csv", index=False, float_format="%.6f")

    # ── Summary ──────────────────────────────────────────────────────────────
    sig = df[df.significant_after_holm]
    noise = df[df.within_noise]
    lines = [
        "# Paired bootstrap — effective zero-result rate (zero-result OR "
        "all-junk)",
        "",
        f"- Metric: binary per (engine, query): 1 if no hits OR every hit "
        f"judged Irrelevant (gain 0); else 0. Lower is better, so "
        f"observed_diff = quissly - vendor is NEGATIVE when Quissly wins.",
        f"- Population: all {cells[0]['n_queries'] if False else 1259} "
        f"queries, no exclusions (asserted per engine).",
        f"- Method: paired bootstrap on per-query differences, whole-query "
        f"resampling, B={N_REPLICATES:,}, numpy default_rng(seed={SEED}), "
        f"fixed cell order (vendor: {', '.join(COMPARATORS)}; slots: "
        f"{', '.join(slots)}).",
        f"- Multiple comparisons: Holm-Bonferroni across the COMBINED family "
        f"of **{m} tests** = 192 committed tests "
        f"(precision/recall from analysis/bootstrap/20260718_112921Z/, nDCG "
        f"from the pooled-IDCG run analysis/ndcg_pooled/, p_raw reused) + these 44 effective-zero cells.",
        f"- Environment: Python {sys.version.split()[0]}, numpy "
        f"{np.__version__}, pandas {pd.__version__}.",
        f"- Outputs: analysis/ezr_bootstrap/ezr_results.csv (this family's "
        f"44 cells), this summary.",
        "",
        *recon_lines,
        "",
        "## Headline",
        "",
        f"**{len(sig)} of 44 effective-zero cells are significant after Holm "
        f"(family m={m}); {len(noise)} are within noise** (not significant, "
        f"or 95% CI crosses zero). "
        f"{int((df.observed_diff < 0).sum())} of 44 observed differences "
        f"favor Quissly (negative diff).",
        "",
        f"Effect of enlarging the family on the 192 committed tests: "
        f"{len(orig_flips)} previously-significant cell(s) lose significance "
        f"at m={m}.",
    ]
    if len(orig_flips):
        for r in orig_flips.itertuples():
            lines.append(f"- {r.metric} / {r.sector} / {r.vendor_pair}: "
                         f"p_holm {r.p_holm:.4f} -> {r.p_holm_236:.4f}")
    lines += ["", "## Pooled cells", ""]
    for r in df[df.sector == "pooled"].sort_values("vendor_pair").itertuples():
        star = " (within noise)" if r.within_noise else ""
        lines.append(
            f"- vs {DISPLAY[r.vendor_pair.split('_vs_')[1]]}: quissly "
            f"{r.quissly_mean * 100:.2f}% vs {r.other_mean * 100:.2f}%, diff "
            f"{r.observed_diff * 100:+.2f} pp "
            f"[{r.ci_low * 100:.2f}, {r.ci_high * 100:.2f}], "
            f"p_holm={r.p_holm:.4g}{star}")
    lines += ["", "## All 44 cells", "",
              "| sector/tier | vendor | quissly % | vendor % | diff pp | "
              "95% CI | p_raw | p_holm | verdict |",
              "|---|---|---:|---:|---:|---|---:|---:|---|"]
    for r in df.itertuples():
        verdict = "within noise" if r.within_noise else \
            ("quissly better" if r.observed_diff < 0 else "vendor better")
        lines.append(
            f"| {r.sector} | {DISPLAY[r.vendor_pair.split('_vs_')[1]]} | "
            f"{r.quissly_mean * 100:.2f} | {r.other_mean * 100:.2f} | "
            f"{r.observed_diff * 100:+.2f} | [{r.ci_low * 100:.2f}, "
            f"{r.ci_high * 100:.2f}] | {r.p_raw:.4g} | {r.p_holm:.4g} | "
            f"{verdict} |")
    sig_sorted = df[~df.within_noise].reindex(
        df[~df.within_noise].observed_diff.abs().sort_values().index)
    lines += ["", "## Narrowest significant margins (smallest |diff| that "
              "survived Holm and whose CI excludes zero)", ""]
    for r in sig_sorted.head(8).itertuples():
        lines.append(f"- {r.sector} vs "
                     f"{DISPLAY[r.vendor_pair.split('_vs_')[1]]}: "
                     f"{r.observed_diff * 100:+.2f} pp "
                     f"[{r.ci_low * 100:.2f}, {r.ci_high * 100:.2f}], "
                     f"p_holm={r.p_holm:.4g}")
    lines += ["", f"## Within-noise cells ({len(noise)}) — desired findings, "
              "not failures", ""]
    if noise.empty:
        lines.append("None.")
    else:
        for r in noise.itertuples():
            lines.append(
                f"- {r.sector} vs {DISPLAY[r.vendor_pair.split('_vs_')[1]]}: "
                f"diff {r.observed_diff * 100:+.2f} pp "
                f"[{r.ci_low * 100:.2f}, {r.ci_high * 100:.2f}], "
                f"p_holm={r.p_holm:.4g}")
    lines.append("")
    (OUT_DIR / "summary.md").write_text("\n".join(lines))
    print(f"\nWrote {OUT_DIR / 'ezr_results.csv'} and summary.md")
    print(f"Significant: {len(sig)}/44; within noise: {len(noise)}; "
          f"original-family flips: {len(orig_flips)}")


if __name__ == "__main__":
    main()
