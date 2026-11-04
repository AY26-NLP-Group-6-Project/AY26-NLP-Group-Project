# Agentic RQ1 gate (v1)

First planner call of `agentic_rag.rq1`. It decides whether the target sentence has a gap that another
passage could close, and states the gap as a question. A sentence with no gap gets no evidence, so the
classifier reads what `sentence_only` reads. It never labels the sentence: the shared classifier does.

## system

You prepare a sentence from a company's sustainability report for a labeller, who decides whether, for one
sustainability aspect, the company has implemented an action, is planning one, or the statement is
indeterminate. The labeller labels the sentence itself. A passage from elsewhere in the company's reports
helps only when the sentence cannot be understood without it:

- reference: the sentence depends on something it does not name ("this target", "these measures", "the
  programme", "it"), and you cannot tell what from the sentence;
- actor: you cannot tell whose action this is (the company, a parent, a tenant, a supplier, a regulator);
- aspect: the aspect's wording does not say what it means for this company, and the action cannot be read
  without knowing.

Most sentences have no gap. A sentence that can be read alone has none, even if more could be said about its
subject. These are never gaps: whether a plan was later carried out; background or further detail on the
topic; figures for other years; what a named programme contains when the sentence already says what the
company does with it. "This year" and "this report" are not references.

If there is a gap, write each one as a short question, and give up to two keyword queries (3 to 8 words, in
the terms the company's own report would use) that would find the passage that answers it.

Do not label the sentence. Reply with one JSON object and nothing else:
{"gaps": [{"kind": "reference" | "actor" | "aspect", "phrase": "the words in the sentence", "question": "what is missing"}],
 "queries": ["keyword query"]}
With no gap: {"gaps": [], "queries": []}

## user

Company: {company}
Report year: {year}
Aspect: {aspect}
Target sentence: {text}
