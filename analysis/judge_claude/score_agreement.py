"""Phase 2: score the Claude cross-family judge against the shipped labels.

Compares three label sources on the identical pooled item set:
  shipped  — comparison_final_judged/judged/*.json.gz (Gemini 3.5 family,
             the labels behind every published number)
  g25      — analysis/judge_stability/raw/*.json (Gemini 2.5 re-judge)
  claude   — analysis/judge_claude/raw/*.json (claude-sonnet-5 on Vertex)

Item level: percent agreement, Cohen's kappa, 4x4 confusion matrices,
gain deltas — claude-vs-shipped, claude-vs-g25, and g25-vs-shipped (context),
overall and per sector/tier.

Metric level: EZR, graded P@10/P@20, pooled recall@10/@20, pooled-ideal
nDCG@10/@20 per engine recomputed under Claude labels with the exact
published conventions (precision_at_k mean-gain+round4, recall pool =
Exact-anywhere, nDCG pool = max-gain dedup + pooled IDCG with IDCG==0
excluded), side by side with the same code run on shipped labels, plus
Spearman rank correlation of the five-engine ordering per metric.

Reads everything read-only; writes only analysis/judge_claude/agreement/.
"""
import csv
import gzip
import json
import math
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
JUDGED_DIR = ROOT / "comparison_final_judged" / "judged"
G25_RAW = ROOT / "analysis" / "judge_stability" / "raw"
CLAUDE_RAW = Path(__file__).resolve().parent / "raw"
OUT = Path(__file__).resolve().parent / "agreement"

SECTORS = ["auto", "cosmetics", "electronics", "fast_fashion",
           "furniture", "marketplace", "pharmacy"]
ENGINES = ["quissly", "doofinder", "luigisbox", "clerk", "algolia"]
LABELS = ["Exact", "Substitute", "Complementary", "Irrelevant"]
GAIN = {"Exact": 1.0, "Substitute": 0.1, "Complementary": 0.01,
        "Irrelevant": 0.0}
KS = (10, 20)


def load_shipped():
    """Per query: sector, tier, first-seen pooled labels (mirrors the batch
    construction both re-judges used), and per-engine ranked hit ids."""
    queries = {}
    inconsistent = 0
    for sector in SECTORS:
        judged = json.load(gzip.open(JUDGED_DIR / f"{sector}_judged.json.gz",
                                     "rt", encoding="utf-8"))
        for e in judged:
            pooled, eng_ids = {}, {}
            for eng, pdata in e["providers"].items():
                hits = sorted(pdata.get("hits", []), key=lambda h: h["rank"])
                eng_ids[eng] = [str(h["id"]) for h in hits]
                for h in hits[:20]:
                    hid = str(h["id"])
                    if hid in pooled:
                        if pooled[hid] != h["label"]:
                            inconsistent += 1
                    else:
                        pooled[hid] = h["label"]
            queries[e["query_id"]] = {
                "sector": sector, "tier": e["complexity"],
                "labels": pooled, "eng_ids": eng_ids}
    return queries, inconsistent


def load_rejudge(raw_dir):
    out = {}
    for p in sorted(raw_dir.glob("q_*.json")):
        r = json.loads(p.read_text())
        out[r["query_id"]] = dict(zip(r["product_ids"],
                                      [str(l) for l in r["labels"]]))
    return out


def kappa(conf):
    n = sum(sum(row) for row in conf)
    if not n:
        return float("nan")
    po = sum(conf[i][i] for i in range(len(LABELS))) / n
    pe = sum(sum(conf[i]) * sum(row[i] for row in conf)
             for i in range(len(LABELS))) / (n * n)
    return (po - pe) / (1 - pe) if pe < 1 else float("nan")


def pair_stats(items, a_key, b_key):
    """items: list of dicts with labels under a_key/b_key."""
    conf = [[0] * len(LABELS) for _ in LABELS]
    gd = []
    for it in items:
        a, b = it[a_key], it[b_key]
        conf[LABELS.index(a)][LABELS.index(b)] += 1
        gd.append(GAIN[a] - GAIN[b])
    n = len(items)
    agree = sum(conf[i][i] for i in range(len(LABELS)))
    return {"n": n, "agreement": round(agree / n, 4) if n else None,
            "kappa": round(kappa(conf), 4) if n else None,
            "mean_gain_delta": round(sum(gd) / n, 5) if n else None,
            "mean_abs_gain_delta": round(sum(abs(d) for d in gd) / n, 5)
            if n else None, "confusion": conf}


def _dcg(gains):
    return sum(g / math.log2(i + 2) for i, g in enumerate(gains))


def _norm_id(s):
    """Pool join key: lowercase, dashes stripped. Quissly's marketplace hits
    carry dashed UUIDs where the other engines carry undashed hex of the
    same ids — see analysis/id_overlap_check/ID_OVERLAP_REPORT.md."""
    return str(s).lower().replace("-", "")


def engine_metrics(queries, label_of):
    """Published-convention metrics per engine under label_of(qid, pid).
    Pools and pooled ideals keyed by _norm_id, dedup by max gain; item-level
    agreement elsewhere in this script is untouched (per judged record)."""
    acc = {e: defaultdict(list) for e in ENGINES}
    for qid, q in queries.items():
        gain = {}
        for pid in q["labels"]:
            nid = _norm_id(pid)
            gain[nid] = max(gain.get(nid, 0.0), GAIN[label_of(qid, pid)])
        pool_exact = {nid for nid, g in gain.items() if g == 1.0}
        ideal = sorted(gain.values(), reverse=True)
        idcg = {k: _dcg(ideal[:k]) for k in KS}
        for eng in ENGINES:
            ids = [_norm_id(p) for p in q["eng_ids"][eng]]
            gains20 = [gain[p] for p in ids[:20]]
            acc[eng]["ezr"].append(
                1.0 if (not ids or all(g == 0.0 for g in gains20)) else 0.0)
            for k in KS:
                top = gains20[:k]
                acc[eng][f"p@{k}"].append(
                    round(sum(top) / len(top), 4) if top else 0.0)
                if pool_exact:
                    found = len({p for p in ids[:k]
                                 if gain.get(p) == 1.0})
                    acc[eng][f"recall@{k}"].append(found / len(pool_exact))
                if idcg[k] > 0:
                    acc[eng][f"ndcg@{k}"].append(_dcg(top) / idcg[k])
    return {e: {m: round(sum(v) / len(v), 4) for m, v in ms.items()}
            for e, ms in acc.items()}


def spearman(xs, ys):
    def rank(v):
        order = sorted(range(len(v)), key=lambda i: v[i])
        r = [0.0] * len(v)
        i = 0
        while i < len(order):
            j = i
            while j + 1 < len(order) and v[order[j + 1]] == v[order[i]]:
                j += 1
            for t in range(i, j + 1):
                r[order[t]] = (i + j) / 2 + 1
            i = j + 1
        return r
    rx, ry = rank(xs), rank(ys)
    mx, my = sum(rx) / len(rx), sum(ry) / len(ry)
    num = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    den = math.sqrt(sum((a - mx) ** 2 for a in rx)
                    * sum((b - my) ** 2 for b in ry))
    return num / den if den else float("nan")


def write_confusion(path, conf, a_name, b_name):
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow([f"{a_name} \\ {b_name}"] + LABELS)
        for i, lab in enumerate(LABELS):
            w.writerow([lab] + conf[i])


def main():
    OUT.mkdir(exist_ok=True)
    shipped, inconsistent = load_shipped()
    claude = load_rejudge(CLAUDE_RAW)
    g25 = load_rejudge(G25_RAW)

    missing_claude = sorted(set(shipped) - set(claude))
    print(f"queries: shipped {len(shipped)}, claude {len(claude)}, "
          f"g25 {len(g25)}; missing from claude: {len(missing_claude)} "
          f"{missing_claude[:5]}")
    if inconsistent:
        print(f"note: {inconsistent} cross-engine label inconsistencies "
              f"in shipped data (first-seen wins, matching batch build)")

    # ---- item-level: only (qid, pid) present in ALL THREE sources --------
    items = []
    for qid, q in shipped.items():
        c, g = claude.get(qid), g25.get(qid)
        if not c or not g:
            continue
        for pid, lab in q["labels"].items():
            cl, gl = c.get(pid), g.get(pid)
            if cl in GAIN and gl in GAIN:
                items.append({"qid": qid, "pid": pid,
                              "sector": q["sector"], "tier": q["tier"],
                              "shipped": lab, "claude": cl, "g25": gl})
    pairs = {"claude_vs_shipped": ("claude", "shipped"),
             "claude_vs_g25": ("claude", "g25"),
             "g25_vs_shipped": ("g25", "shipped")}
    summary = {"n_items": len(items), "missing_claude": missing_claude,
               "pairs": {}, "per_sector": {}, "per_tier": {}}
    for name, (a, b) in pairs.items():
        st = pair_stats(items, a, b)
        summary["pairs"][name] = st
        write_confusion(OUT / f"confusion_{name}.csv", st["confusion"], a, b)
    for field, dest in (("sector", "per_sector"), ("tier", "per_tier")):
        groups = defaultdict(list)
        for it in items:
            groups[it[field]].append(it)
        for gname, gitems in sorted(groups.items()):
            summary[dest][gname] = {
                name: {k: v for k, v in
                       pair_stats(gitems, a, b).items() if k != "confusion"}
                for name, (a, b) in pairs.items()}

    # ---- metric-level under each label source (claude-complete queries) --
    scored = {qid: q for qid, q in shipped.items() if qid in claude}
    m_ship = engine_metrics(scored, lambda qid, pid:
                            scored[qid]["labels"][pid])
    m_claude = engine_metrics(scored, lambda qid, pid:
                              claude[qid].get(pid) if claude[qid].get(pid)
                              in GAIN else scored[qid]["labels"][pid])
    summary["metrics"] = {"shipped": m_ship, "claude": m_claude}
    metric_names = sorted(next(iter(m_ship.values())))
    summary["spearman_by_metric"] = {
        m: round(spearman([m_ship[e][m] for e in ENGINES],
                          [m_claude[e][m] for e in ENGINES]), 4)
        for m in metric_names}

    deltas = [(abs(m_claude[e][m] - m_ship[e][m]), e, m,
               m_ship[e][m], m_claude[e][m])
              for e in ENGINES for m in metric_names]
    d, e, m, sv, cv = max(deltas)
    summary["largest_cell_delta"] = {
        "engine": e, "metric": m, "shipped": sv, "claude": cv,
        "abs_delta": round(d, 4)}

    with open(OUT / "metrics_under_claude.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["engine"] + [f"{m}_{s}" for m in metric_names
                                 for s in ("shipped", "claude")])
        for eng in ENGINES:
            w.writerow([eng] + [round(x, 4) for m in metric_names
                                for x in (m_ship[eng][m], m_claude[eng][m])])

    (OUT / "summary.json").write_text(json.dumps(summary, indent=1))
    for name in pairs:
        st = summary["pairs"][name]
        print(f"{name}: n={st['n']} agree={st['agreement']} "
              f"kappa={st['kappa']}")
    print("spearman by metric:", summary["spearman_by_metric"])
    print("largest cell delta:", summary["largest_cell_delta"])


if __name__ == "__main__":
    main()
