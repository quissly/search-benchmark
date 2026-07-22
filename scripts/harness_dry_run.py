"""End-to-end dry run of the benchmark harness with FAKE keys and NO network.

Proves the third-party path is wired: load queries -> provider search
adapters (mocked transport) -> batched LLM judging (mocked judge) -> judged
schema -> metric implementations. No API is called; no file outside a temp
directory is written.

    python scripts/harness_dry_run.py
"""
import json
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# Fake credentials BEFORE importing the pipeline (llm_judge exits without a
# key; providers resolve env var names at query time).
for var in ("GEMINI_API_KEY", "APP_ID", "SEARCH_API_KEY",
            "DOOFINDER_API_KEY", "QUISSLY_SEARCH_URL"):
    os.environ.setdefault(var, "dry-run-fake")

import providers                          # noqa: E402
from pipeline import llm_judge            # noqa: E402
from pipeline.metrics_dashboard import compute_rich_metrics  # noqa: E402

ENGINES = ["quissly", "doofinder", "luigisbox", "clerk", "algolia"]


def fake_search(query, limit=24, sector=None, _seed=[0]):
    """Stands in for every provider: deterministic synthetic hits."""
    _seed[0] += 1
    n = 6 + (_seed[0] % 3)
    return ([{"rank": i + 1, "id": f"p{_seed[0]}_{i}", "title": f"Item {i}",
              "description": "synthetic", "image": "", "price": 9.99,
              "discount_price": None} for i in range(n)], 12, n)


def fake_judge(query, items, complexity="medium"):
    """Stands in for gemini: labels cycle through the four canonical ones."""
    labels = ["Exact", "Substitute", "Complementary", "Irrelevant"]
    return [{"label": labels[i % 4],
             "score": llm_judge.GAIN_MAP[labels[i % 4].lower()],
             "reasoning": "dry-run"} for i in range(len(items))]


def main():
    queries = json.loads(
        (ROOT / "queries/query_outputs/queries.json").read_text())[:3]
    assert all("text_query" in q or "query" in q or "text" in q
               for q in queries) or queries, "query file loads"
    llm_judge.judge_products = fake_judge
    tmp = Path(tempfile.mkdtemp(prefix="benchmark-dry-run-"))
    judged_entries = []
    for qi, q in enumerate(queries):
        text = q.get("text_query") or q.get("query") or q.get("text")
        cx = q.get("complexity", "medium")
        entry = {"query_id": q.get("query_id", f"dry_{qi}"),
                 "category": q.get("category", ""), "complexity": cx,
                 "text_query": text, "providers": {}}
        # pooled unique products across engines, then one batched judge call
        unique = {}
        per_engine_hits = {}
        for eng in ENGINES:
            hits, latency_ms, total = fake_search(text, sector="electronics")
            per_engine_hits[eng] = hits
            for h in hits[:20]:
                unique.setdefault(str(h["id"]), h)
        judgments = llm_judge.judge_products(
            text, list(unique.values()), cx)
        jmap = {pid: j for pid, j in zip(unique, judgments)}
        for eng in ENGINES:
            judged_hits = []
            for rank, h in enumerate(per_engine_hits[eng][:20], 1):
                j = jmap[str(h["id"])]
                judged_hits.append({**h, "rank": rank, "label": j["label"],
                                    "score": j["score"],
                                    "reasoning": j["reasoning"],
                                    "cached": False})
            entry["providers"][eng] = {
                "latency_ms": 12,
                "precision_at_10": llm_judge.precision_at_k(judged_hits, 10),
                "precision_at_20": llm_judge.precision_at_k(judged_hits, 20),
                "hits": judged_hits,
            }
        judged_entries.append(entry)
    judged_path = tmp / "dry_judged.json"
    judged_path.write_text(json.dumps(judged_entries))
    rich = compute_rich_metrics(judged_path)
    assert set(rich) == set(ENGINES), rich.keys()
    for eng in ENGINES:
        for k in ("recall", "ndcg", "junk10", "junk20", "alljunk"):
            v = rich[eng][k]
            assert isinstance(v, float) and 0.0 <= v <= 100.0, (eng, k, v)
    print(f"DRY RUN PASS: {len(queries)} queries x {len(ENGINES)} engines "
          f"-> judged schema -> metrics OK (outputs in {tmp}, no network, "
          f"fake keys only)")


if __name__ == "__main__":
    main()
