# RAG answer-level judge prompts (v1)

Used by `gw_common.eval.rag_metrics`. The three metrics follow the definitions of RAGAS (Es et al.,
EACL 2024 demo): faithfulness, answer relevance, context precision. Implemented here rather than through
the `ragas` package so every judgement is stored and can be checked by hand.

The judge is an LLM. When it is the same model that wrote the answers it may be lenient towards them;
the human spot-check (`gw-eval --ragas-export-check`) measures how far its verdicts can be trusted.

## faithfulness

You check whether an answer is supported by the sources it was given.

The answer is a label plus a short rationale about one sentence from a company's sustainability report.
Do two things:

1. Break the RATIONALE into atomic statements: each a single factual claim, self-contained, with
   pronouns resolved. Do not include the label itself, and do not add claims the rationale does not make.
2. For each statement decide whether it can be directly inferred from the SOURCES alone. A statement is
   supported only if the sources say it or clearly entail it. If it needs outside knowledge, or it
   states more than the sources do, it is not supported.

Judgements about the label scheme ("this counts as a commitment", "this is hedged language") are
supported when the wording they point to is in the sources.

Reply with one JSON object and nothing else:
{"statements": [{"statement": "...", "supported": true, "source": "T"}]}

"source" is the tag of the source that supports the statement (T, C, E1, E2, ...), or "none".

## answer_relevance

You are given an answer. Write the three most likely questions that this answer was written to answer.
Each question must be specific enough that the answer would address it directly, and must be answerable
from the answer alone. Also say whether the answer is noncommittal: evasive, or declining to answer
("it is unclear", "cannot be determined" with no reason given). An answer that gives a definite label,
including the label "indeterminate" with a reason, is NOT noncommittal.

Reply with one JSON object and nothing else:
{"questions": ["...", "...", "..."], "noncommittal": false}

## context_precision

You judge whether retrieved passages were useful for a classification question.

QUESTION: what a TARGET sentence from a company's sustainability report says about the company's
action on one ASPECT (implemented, planning, indeterminate, or none). The REFERENCE label is the
correct answer.

For each retrieved passage decide whether it is relevant: it helps a reader reach or confirm the
reference label for THIS target sentence, for example by resolving what the sentence refers to, who the
actor is, or whether the stated action on this aspect exists. A passage on the same broad topic that
says nothing bearing on the target sentence's claim about the aspect is NOT relevant. A passage that
merely repeats the target sentence is NOT relevant.

Reply with one JSON object and nothing else:
{"verdicts": [{"ref": "E1", "relevant": true, "reason": "at most 15 words"}]}

Give one verdict per passage, in the order shown.
