# RAG answer-level metrics · 20260930T083207Z-baseline-rag-rq1

- judge: `gpt-5.6-luna` (effort `low`), embeddings `text-embedding-3-small` · prompt `rag_judge.md` · repeat 0
- LLM-judged. Read together with the human spot-check before quoting.

| condition | n | faithfulness | answer relevance | context precision | context relevance | statements / answer | noncommittal |
|---|---|---|---|---|---|---|---|
| cross_year_rrf | 331 | 0.943 | 0.624 | 0.439 | 0.375 | 2.471 | 0.000 |
| local | 331 | 0.949 | 0.618 | — | — | 2.465 | 0.000 |
| same_report_rrf | 331 | 0.951 | 0.621 | 0.571 | 0.459 | 2.486 | 0.000 |
| sentence_only | 331 | 0.952 | 0.618 | — | — | 2.387 | 0.000 |

## Faithfulness by whether the label was right

| condition | correct: n / faithfulness | wrong: n / faithfulness |
|---|---|---|
| cross_year_rrf | 257 / 0.942 | 74 / 0.947 |
| local | 255 / 0.953 | 76 / 0.934 |
| same_report_rrf | 251 / 0.951 | 80 / 0.952 |
| sentence_only | 251 / 0.965 | 80 / 0.910 |
