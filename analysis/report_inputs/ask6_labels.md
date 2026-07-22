## ASK-6 — Label -> gain mapping

Exact code (`pipeline/llm_judge.py`):

```python
# ESCI-style graded relevance: label -> gain
GAIN_MAP = {
    "exact":         1.0,
    "substitute":    0.1,
    "complementary": 0.01,
    "complement":    0.01,  # tolerate the ESCI spelling
    "irrelevant":    0.0,
}
```

Distinct label strings actually present in the judged data:

| label | count |
|---|---:|
| Exact | 46,738 |
| Irrelevant | 26,894 |
| Substitute | 14,071 |
| Complementary | 11,465 |
| **total judged hits** | **99,168** |

Confirmed: only the four canonical strings occur, mapping Exact=1.0, Substitute=0.1, Complementary=0.01, Irrelevant=0.0.
