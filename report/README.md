# Report

The course report in the ACL LaTeX template (`acl.sty`, `acl_natbib.bst` from
https://github.com/acl-org/acl-style-files, fetched 2026-11-03).

| file | what |
|---|---|
| `main.tex` | the report; the author block, the data and code links and the chat-model name are macros at the top |
| `references.bib` | the reference list, every entry checked against Crossref by DOI on 2026-11-06 |
| `queries/five_queries.{json,md}` | the five timed example queries of the brief (Question 2), every search mode, with every hit |
| `figures/ui-rq1.png`, `figures/ui-rq2.png` | the demo front end (`frontend/`) after a run on one dev item of each question, captured headless on 2026-11-03 |
| `acl.sty`, `acl_natbib.bst` | the ACL style |

Build (MiKTeX or TeX Live; pdflatex, bibtex):

```bash
cd report && latexmk -pdf main.tex
```

Every number in the report names the published run under `results/` or the check sheet under
`kb/annotation/spotchecks/` it comes from; `docs/results.md` is the source of the findings, `docs/history.md`
the dated record. Placeholders to fill before submission: the six names, matriculation numbers and emails, and the two links.
No `[Pending Result]` remains: the rank-aware retrieval metrics rest on relevance grades the group's model made
(`docs/evaluation.md`, section 8), which the discussion's `Model judgements` paragraph says.
The submission file must be named after the group number (`6.pdf`).
