"""Phase 2 of the judge-stability check: local-only agreement scoring over
the FULL population (all 1,259 queries; permanently-failed re-judgings are
excluded from BOTH sides and the final n is stated).

Computes everything from analysis/judge_stability/raw/*.json (Gemini 2.5
responses) plus the shipped Gemini 3.5 Flash judgments. No API calls.

Item level: percent exact label agreement, Cohen's kappa over the 4 labels,
the 4x4 confusion matrix (rows = shipped 3.5 label, cols = 2.5 label), mean
absolute gain delta.

Metric level, per scope (overall, each of 7 sectors, each of 3 tiers):
EZR, precision@10, pooled recall@20, pooled-ideal nDCG@10 for all five
engines, computed twice — once under each label set, with relevance pools
and pooled IDCG rebuilt per label set (each set carries its own
recall/nDCG exclusions; populations reported). Reports per-engine deltas
(2.5 minus 3.5), the Spearman rank correlation of the five-engine ordering
per metric (overall scope and worst scope), and the single largest cell
delta anywhere across all scopes.

Writes: item_agreement.csv, confusion_matrix.csv, metric_comparison.json,
phase2_fragment.md.
"""
import csv
import gzip
import json
import math
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
JUDGED_DIR = ROOT / "comparison_final_judged" / "judged"
OUT = Path(__file__).resolve().parent
RAW = OUT / "raw"

SECTORS = ["auto", "cosmetics", "electronics", "fast_fashion",
           "furniture", "marketplace", "pharmacy"]
TIERS = ["simple", "medium", "complex"]
ENGINES = ["quissly", "doofinder", "luigisbox", "clerk", "algolia"]
LABELS = ["Exact", "Substitute", "Complementary", "Irrelevant"]
GAIN = {"Exact": 1.0, "Substitute": 0.1, "Complementary": 0.01,
        "Irrelevant": 0.0}
TOP_N = 20
METRICS = ["ezr", "p10", "recall20", "ndcg10"]
NAMES = {"ezr": "EZR", "p10": "Precision@10",
         "recall20": "Pooled recall@20", "ndcg10": "Pooled-ideal nDCG@10"}


def _dcg(gains):
    return sum(g / math.log2(i + 2) for i, g in enumerate(gains))


def load():
    raws = {}
    for p in sorted(RAW.glob("*.json")):
        r = json.loads(p.read_text())
        raws[r["query_id"]] = r
    failed = sorted(p.stem for p in (OUT / "failed").glob("*.json")) \
        if (OUT / "failed").exists() else []
    judged, total = {}, 0
    for sector in SECTORS:
        for e in json.load(gzip.open(JUDGED_DIR / f"{sector}_judged.json.gz",
                                     "rt", encoding="utf-8")):
            total += 1
            if e["query_id"] in raws:
                e["_sector"] = sector
                judged[e["query_id"]] = e
    return raws, failed, judged, total


def label35_map(e):
    d = {}
    for pdata in e["providers"].values():
        for h in pdata.get("hits", [])[:TOP_N]:
            d.setdefault(str(h["id"]), h["label"])
    return d


def spearman(vals_a, vals_b):
    def ranks(vals):
        order = sorted(range(len(vals)), key=lambda i: -vals[i])
        rk = [0.0] * len(vals)
        i = 0
        while i < len(order):
            j = i
            while j + 1 < len(order) and vals[order[j + 1]] == vals[order[i]]:
                j += 1
            avg = (i + j) / 2 + 1
            for k in range(i, j + 1):
                rk[order[k]] = avg
            i = j + 1
        return rk
    a, b = ranks(vals_a), ranks(vals_b)
    ma, mb = sum(a) / len(a), sum(b) / len(b)
    num = sum((x - ma) * (y - mb) for x, y in zip(a, b))
    den = math.sqrt(sum((x - ma) ** 2 for x in a)
                    * sum((y - mb) ** 2 for y in b))
    return num / den if den else 1.0


def main():
    raws, failed, judged, n_total = load()
    qids = sorted(judged)
    print(f"population {n_total}, re-judged {len(qids)}, "
          f"failed+excluded {len(failed)}")

    # ── item level ───────────────────────────────────────────────────────────
    rows = []
    confusion = {a: {b: 0 for b in LABELS} for a in LABELS}
    for qid in qids:
        r, e = raws[qid], judged[qid]
        l35 = label35_map(e)
        for pid, l25 in zip(r["product_ids"], r["labels"]):
            a = l35[pid]
            confusion[a][l25] += 1
            rows.append({
                "query_id": qid, "sector": r["sector"], "tier": r["tier"],
                "product_id": pid, "label_35": a, "label_25": l25,
                "gain_35": GAIN[a], "gain_25": GAIN[l25],
                "agree": int(a == l25),
                "image_missing": int(pid in r.get("image_missing", [])),
            })
    n_items = len(rows)
    po = sum(r["agree"] for r in rows) / n_items
    row_m = Counter(r["label_35"] for r in rows)
    col_m = Counter(r["label_25"] for r in rows)
    pe = sum(row_m[l] * col_m[l] for l in LABELS) / n_items ** 2
    kappa = (po - pe) / (1 - pe)
    mad_gain = sum(abs(r["gain_35"] - r["gain_25"]) for r in rows) / n_items

    with open(OUT / "item_agreement.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    with open(OUT / "confusion_matrix.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["label_35 \\ label_25"] + LABELS)
        for a in LABELS:
            w.writerow([a] + [confusion[a][b] for b in LABELS])

    # ── per-query per-engine per-label-set metric primitives ────────────────
    per_query = {}   # qid -> set -> {"pools":..., engine -> metric values}
    for qid in qids:
        e = judged[qid]
        sets = {"35": label35_map(e),
                "25": dict(zip(raws[qid]["product_ids"],
                               raws[qid]["labels"]))}
        rec = {"sector": e["_sector"], "tier": e["complexity"]}
        for tag, lab in sets.items():
            # pools keyed by _norm_id (lowercase, dashes stripped), dedup by
            # max gain: Quissly's marketplace hits carry dashed UUIDs where
            # the other engines carry undashed hex of the same ids — see
            # analysis/id_overlap_check/ID_OVERLAP_REPORT.md. Item-level
            # agreement is untouched (it compares per judged record).
            gain = {}
            for pid, l in lab.items():
                nid = str(pid).lower().replace("-", "")
                gain[nid] = max(gain.get(nid, 0.0), GAIN[l])
            pool_ids = {nid for nid, g in gain.items() if g == 1.0}
            idcg10 = _dcg(sorted(gain.values(), reverse=True)[:10])
            engs = {}
            for eng in ENGINES:
                hits = sorted(e["providers"][eng].get("hits", [])[:TOP_N],
                              key=lambda h: h["rank"])
                ids = [str(h["id"]).lower().replace("-", "") for h in hits]
                g = [gain[i] for i in ids]
                top = g[:10]
                engs[eng] = {
                    "ezr": 1.0 if (not g or all(x == 0 for x in g)) else 0.0,
                    "p10": sum(top) / len(top) if top else 0.0,
                    "recall20": (len({i for i in ids[:20] if i in pool_ids})
                                 / len(pool_ids)) if pool_ids else None,
                    "ndcg10": (_dcg(top) / idcg10) if idcg10 > 0 else None,
                }
            rec[tag] = {"engines": engs, "has_pool": bool(pool_ids),
                        "has_idcg": idcg10 > 0}
        per_query[qid] = rec

    SCOPES = [("overall", lambda r: True)] + \
        [(f"sector:{s}", lambda r, s=s: r["sector"] == s) for s in SECTORS] + \
        [(f"tier:{t}", lambda r, t=t: r["tier"] == t) for t in TIERS]

    def agg(scope_pred, tag):
        vals = defaultdict(lambda: defaultdict(list))
        pops = Counter()
        for qid in qids:
            rec = per_query[qid]
            if not scope_pred(rec):
                continue
            pops["total"] += 1
            side = rec[tag]
            pops["recall"] += side["has_pool"]
            pops["ndcg"] += side["has_idcg"]
            for eng in ENGINES:
                for m in METRICS:
                    v = side["engines"][eng][m]
                    if v is not None:
                        vals[m][eng].append(v)
        return ({m: {e: sum(v) / len(v) * 100 for e, v in engs.items()}
                 for m, engs in vals.items()}, pops)

    cells = {}
    for scope, pred in SCOPES:
        m35, p35 = agg(pred, "35")
        m25, p25 = agg(pred, "25")
        cells[scope] = {"m35": m35, "m25": m25,
                        "pop35": dict(p35), "pop25": dict(p25)}

    ov = cells["overall"]
    deltas = {m: {e: ov["m25"][m][e] - ov["m35"][m][e] for e in ENGINES}
              for m in METRICS}
    rho = {m: spearman([ov["m35"][m][e] for e in ENGINES],
                       [ov["m25"][m][e] for e in ENGINES]) for m in METRICS}
    all_cell_deltas = [(scope, m, e,
                        c["m25"][m][e] - c["m35"][m][e])
                       for scope, c in cells.items()
                       for m in METRICS for e in ENGINES
                       if e in c["m25"].get(m, {}) and e in c["m35"].get(m, {})]
    largest = max(all_cell_deltas, key=lambda x: abs(x[3]))
    rho_by_scope = {scope: {m: spearman(
        [c["m35"][m][e] for e in ENGINES], [c["m25"][m][e] for e in ENGINES])
        for m in METRICS} for scope, c in cells.items()}
    worst_rho = min(((s, m, r) for s, ms in rho_by_scope.items()
                     for m, r in ms.items()), key=lambda x: x[2])

    json.dump({
        "population": n_total, "n_queries_scored": len(qids),
        "n_failed_excluded": len(failed), "failed_qids": failed,
        "item_level": {"n_items": n_items, "percent_agreement": po * 100,
                       "cohens_kappa": kappa,
                       "mean_abs_gain_delta": mad_gain,
                       "confusion_rows_35_cols_25": confusion},
        "cells": cells, "overall_deltas_25_minus_35": deltas,
        "spearman_overall": rho, "spearman_by_scope": rho_by_scope,
        "largest_cell_delta": {"scope": largest[0], "metric": largest[1],
                               "engine": largest[2], "delta_pp": largest[3]},
    }, open(OUT / "metric_comparison.json", "w"), indent=1)

    # ── markdown fragment ────────────────────────────────────────────────────
    fr = [f"## Phase 2 — agreement results (population {n_total}; "
          f"{len(qids)} scored; {len(failed)} failed re-judgings excluded "
          f"from both sides)\n",
          f"### Item level ({n_items:,} product judgments)\n",
          f"- exact label agreement: **{po * 100:.2f}%**",
          f"- Cohen's kappa (4 labels): **{kappa:.4f}**",
          f"- mean |gain delta|: **{mad_gain:.4f}**\n",
          "Confusion matrix (rows = shipped 3.5 label, cols = 2.5 label):\n",
          "| 3.5 \\ 2.5 | " + " | ".join(LABELS) + " | total |",
          "|---|" + "---:|" * 5]
    for a in LABELS:
        fr.append(f"| {a} | " + " | ".join(str(confusion[a][b])
                                           for b in LABELS)
                  + f" | {sum(confusion[a].values())} |")
    fr.append("\n### Metric level — overall scope "
              "(pools & pooled-IDCG rebuilt per label set)\n")
    fr.append(f"Populations: total {ov['pop35']['total']}; recall n "
              f"{ov['pop35']['recall']} (3.5) vs {ov['pop25']['recall']} "
              f"(2.5); nDCG n {ov['pop35']['ndcg']} (3.5) vs "
              f"{ov['pop25']['ndcg']} (2.5).\n")
    for m in METRICS:
        fr.append(f"**{NAMES[m]}** (Spearman rho of engine ordering, "
                  f"overall: {rho[m]:.3f})\n")
        fr.append("| engine | 3.5 | 2.5 | delta (2.5-3.5) |")
        fr.append("|---|---:|---:|---:|")
        for e in ENGINES:
            fr.append(f"| {e} | {ov['m35'][m][e]:.2f} | "
                      f"{ov['m25'][m][e]:.2f} | {deltas[m][e]:+.2f} |")
        fr.append("")
    fr.append(f"**Largest single cell delta anywhere** (across overall, "
              f"7 sectors, 3 tiers): {largest[0]} / {NAMES[largest[1]]} / "
              f"{largest[2]}: **{largest[3]:+.2f} pp**\n")
    fr.append(f"**Lowest Spearman in any scope:** {worst_rho[0]} / "
              f"{NAMES[worst_rho[1]]}: rho = {worst_rho[2]:.3f} "
              f"(1.000 = identical engine ordering)\n")
    (OUT / "phase2_fragment.md").write_text("\n".join(fr))
    print(f"items {n_items}: agreement {po * 100:.2f}%, kappa {kappa:.4f}; "
          f"largest cell delta {largest[0]}/{largest[1]}/{largest[2]} "
          f"{largest[3]:+.2f}pp; worst rho {worst_rho[2]:.3f}")


if __name__ == "__main__":
    main()
