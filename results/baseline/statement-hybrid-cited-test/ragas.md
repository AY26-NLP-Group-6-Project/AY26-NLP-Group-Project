# RAG answer-level metrics · 20261105T103924Z-baseline-rag-rq1

- judge: `gpt-5.6-luna` (effort `low`), embeddings `text-embedding-3-small` · prompt `rag_judge.md` · repeat 0
- LLM-judged. Read together with the human spot-check before quoting.

| condition | n | faithfulness | answer relevance | context precision | context relevance | statements / answer | noncommittal |
|---|---|---|---|---|---|---|---|
| cross_year_rrf | 669 | 0.975 | 0.569 | 0.335 | 0.273 | 2.179 | 0.000 |
| local | 669 | 0.977 | 0.563 | — | — | 2.094 | 0.000 |
| same_report_rrf | 669 | 0.980 | 0.567 | 0.527 | 0.402 | 2.187 | 0.000 |
| sentence_only | 669 | 0.970 | 0.570 | — | — | 2.037 | 0.000 |

## Faithfulness by whether the label was right

| condition | correct: n / faithfulness | wrong: n / faithfulness |
|---|---|---|
| cross_year_rrf | 492 / 0.979 | 177 / 0.964 |
| local | 493 / 0.982 | 176 / 0.964 |
| same_report_rrf | 498 / 0.985 | 171 / 0.966 |
| sentence_only | 508 / 0.973 | 161 / 0.959 |
