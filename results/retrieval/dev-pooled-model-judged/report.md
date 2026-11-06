# 20261106T013739Z-retrieval-pooled

> **Model-judged relevance.** The pooled judgements were made by a model under `relevance_judge.md` (gpt-5.6-luna); no human has graded this pool. Read the numbers as a comparison between configurations under one judge, not as absolute retrieval quality.

- task: `retrieval` · queries: `data/eval/retrieval.queries.jsonl` (80; company_claim 30, cross_year_aspect 30, generic 20)
- qrels: `data/eval/retrieval.qrels.jsonl` · pooled documents judged: 1658 · relevant at grade ≥ 2: 1081 (≥ 1: 1461)
- k = 10 · configurations: `bm25`, `dense`, `rrf`, `rrf+rerank`, `graph-rag:graph`, `graph-rag:fused`
- git: `b38c7da3`

## All queries

| configuration | n | returned | P@5 | R@10 | MRR | nDCG@10 | wrong-company@10 | nDCG@10 (grade ≥ 1) |
|---|---|---|---|---|---|---|---|---|
| `bm25` | 78 | 10.0 | 0.728 | 0.471 | 0.886 | 0.706 | 0.000 | 0.892 |
| `dense` | 78 | 10.0 | 0.805 | 0.564 | 0.900 | 0.793 | 0.000 | 0.959 |
| `rrf` | 78 | 10.0 | 0.785 | 0.543 | 0.913 | 0.782 | 0.000 | 0.957 |
| `rrf+rerank` | 78 | 10.0 | 0.797 | 0.555 | 0.934 | 0.800 | 0.000 | 0.952 |
| `graph-rag:graph` | 78 | 1.7 | 0.228 | 0.108 | 0.490 | 0.209 | 0.000 | 0.235 |
| `graph-rag:fused` | 78 | 7.4 | 0.567 | 0.409 | 0.664 | 0.547 | 0.000 | 0.675 |

## Queries of type `company_claim`

| configuration | n | returned | P@5 | R@10 | MRR | nDCG@10 | wrong-company@10 | nDCG@10 (grade ≥ 1) |
|---|---|---|---|---|---|---|---|---|
| `bm25` | 28 | 10.0 | 0.586 | 0.456 | 0.775 | 0.570 | 0.000 | 0.830 |
| `dense` | 28 | 10.0 | 0.693 | 0.588 | 0.817 | 0.699 | 0.000 | 0.955 |
| `rrf` | 28 | 10.0 | 0.679 | 0.555 | 0.809 | 0.677 | 0.000 | 0.941 |
| `rrf+rerank` | 28 | 10.0 | 0.686 | 0.550 | 0.896 | 0.705 | 0.000 | 0.929 |
| `graph-rag:graph` | 28 | 1.8 | 0.221 | 0.109 | 0.400 | 0.182 | 0.000 | 0.245 |
| `graph-rag:fused` | 28 | 10.0 | 0.686 | 0.521 | 0.801 | 0.653 | 0.000 | 0.879 |

## Queries of type `cross_year_aspect`

| configuration | n | returned | P@5 | R@10 | MRR | nDCG@10 | wrong-company@10 | nDCG@10 (grade ≥ 1) |
|---|---|---|---|---|---|---|---|---|
| `bm25` | 30 | 9.9 | 0.793 | 0.505 | 0.978 | 0.749 | 0.000 | 0.885 |
| `dense` | 30 | 10.0 | 0.820 | 0.593 | 0.928 | 0.809 | 0.000 | 0.940 |
| `rrf` | 30 | 10.0 | 0.840 | 0.586 | 0.978 | 0.826 | 0.000 | 0.947 |
| `rrf+rerank` | 30 | 10.0 | 0.833 | 0.612 | 0.951 | 0.827 | 0.000 | 0.943 |
| `graph-rag:graph` | 30 | 2.6 | 0.387 | 0.180 | 0.900 | 0.374 | 0.000 | 0.383 |
| `graph-rag:fused` | 30 | 9.9 | 0.833 | 0.576 | 0.978 | 0.812 | 0.000 | 0.935 |

## Queries of type `generic`

| configuration | n | returned | P@5 | R@10 | MRR | nDCG@10 | wrong-company@10 | nDCG@10 (grade ≥ 1) |
|---|---|---|---|---|---|---|---|---|
| `bm25` | 20 | 10.0 | 0.830 | 0.441 | 0.902 | 0.832 | — | 0.989 |
| `dense` | 20 | 10.0 | 0.940 | 0.487 | 0.975 | 0.902 | — | 0.993 |
| `rrf` | 20 | 10.0 | 0.850 | 0.460 | 0.960 | 0.862 | — | 0.996 |
| `rrf+rerank` | 20 | 10.0 | 0.900 | 0.475 | 0.960 | 0.891 | — | 0.997 |
| `graph-rag:graph` | 20 | 0.0 | 0.000 | 0.000 | 0.000 | 0.000 | — | 0.000 |
| `graph-rag:fused` | 20 | 0.0 | 0.000 | 0.000 | 0.000 | 0.000 | — | 0.000 |

## Against `rrf+rerank` (nDCG@10, paired over the same queries)

| configuration | queries | Δ mean | 95% CI | wins / losses |
|---|---|---|---|---|
| `bm25` | 78 | -0.094 | -0.130 … -0.057 | 13 / 49 |
| `dense` | 78 | -0.007 | -0.042 … +0.028 | 29 / 35 |
| `rrf` | 78 | -0.018 | -0.045 … +0.010 | 23 / 34 |
| `graph-rag:graph` | 78 | -0.591 | -0.663 … -0.517 | 3 / 74 |
| `graph-rag:fused` | 78 | -0.253 | -0.350 … -0.156 | 21 / 47 |

Pooled recall: the relevant set of a query is every pooled document at or above the grade, so R@10 is recall against the union of the configurations compared, not against the store. A configuration that returns nothing for a query type (the graph arms need a company) scores 0 on those queries; read it on the types it serves.
