# RAG answer-level metrics · 20261029T143225Z-baseline-rag-rq1

- judge: `gpt-5.6-luna` (effort `low`), embeddings `text-embedding-3-small` · prompt `rag_judge.md` · repeat 0
- LLM-judged. Read together with the human spot-check before quoting.

| condition | n | faithfulness | answer relevance | context precision | context relevance | statements / answer | noncommittal |
|---|---|---|---|---|---|---|---|
| cross_year_rrf | 331 | 0.973 | 0.568 | 0.371 | 0.286 | 2.115 | 0.000 |
| local | 331 | 0.961 | 0.573 | — | — | 2.127 | 0.000 |
| same_report_rrf | 331 | 0.976 | 0.563 | 0.497 | 0.369 | 2.151 | 0.000 |
| sentence_only | 331 | 0.964 | 0.574 | — | — | 2.030 | 0.000 |

## Faithfulness by whether the label was right

| condition | correct: n / faithfulness | wrong: n / faithfulness |
|---|---|---|
| cross_year_rrf | 246 / 0.972 | 85 / 0.976 |
| local | 245 / 0.968 | 86 / 0.942 |
| same_report_rrf | 240 / 0.974 | 91 / 0.982 |
| sentence_only | 250 / 0.964 | 81 / 0.963 |
