# Results

The findings in one place. Every number names the published run (`results/<group>/<name>/`) or the
check sheet (`kb/annotation/spotchecks/`) it comes from. Dev split only, 331 items; the test split has
not been opened. Classifier `gpt-5.6-luna`, reasoning effort low, three uncached repeats per condition
unless stated; "vote" is the majority over the repeats. Every arm retrieves over the same knowledge
base: every statement of the parsed reports with five words or more (`baseline.md`).

## 1. Does retrieved evidence improve the label? (RQ1)

### Headline: statement-level evidence, cited classifier

| arm | run | macro-F1 mean ± sd | vote | none F1 | items citing evidence |
|---|---|---|---|---|---|
| sentence only | `baseline/statement-hybrid-cited` | 0.7451 ± 0.019 | 0.7397 | 0.766 | — |
| sentence only, second run | `graph/graph-arms-cited` | 0.7450 ± 0.014 | 0.7498 | 0.753 | — |
| sentence only, third run | `baseline/passage-hybrid-cited` | 0.7517 ± 0.005 | 0.7580 | 0.739 | — |
| neighbouring sentences | `baseline/statement-hybrid-cited` | 0.7453 ± 0.007 | 0.7617 | 0.705 | — |
| hybrid, same report | `baseline/statement-hybrid-cited` | 0.7380 ± 0.006 | 0.7442 | 0.690 | 9.1 % |
| hybrid, other years | `baseline/statement-hybrid-cited` | 0.7676 ± 0.004 | 0.7767 | 0.739 | 1.1 % |
| graph, other years | `graph/graph-arms-cited` | 0.7472 ± 0.010 | 0.7449 | 0.731 | 1.3 % |
| graph + BM25 fused | `graph/graph-arms-cited` | 0.7708 ± 0.006 | 0.7668 | 0.711 | 1.0 % |

Paired on the same 331 items (majority votes, McNemar): the three sentence-only runs differ pairwise
on 10–12 items, p = 1.00 and 0.77; the best hybrid arm (other years) against the best graph arm
(fused), +6 / −11 items, p = 0.33; hybrid other years against its own sentence only, +0.037 with
p = 0.21; graph fused against its own, +0.017 with p = 1.00. **Retrieved evidence moves vote macro-F1
by at most 0.04, with p ≥ 0.21, against a spread of 0.018 between three runs of the no-evidence
configuration; the graph is not distinguishable from plain hybrid retrieval.** What differs is cost:
graph lookups take 9 ms at the median (20 ms fused) against 191–734 ms for the hybrid path, which needs
a query embedding and a cross-encoder pass. The latencies were measured with three runs sharing one
machine.

### Why so little: the classifier rarely uses what it is given

The classifier cites a retrieved span in 1–9 % of items: 9 % with same-report evidence, about 1 %
with other-year evidence from either retriever. The RAG-metric judge (`baseline/statement-hybrid-cited`,
`ragas.md`) finds the rationales faithful (0.96–0.98 of their statements supported) and a minority of
the retrieved statements relevant (0.37 same report, 0.29 other years; precision 0.50 and 0.37). A
human calibration of that judge (`ragas-check.result.json`, 186 rows from an earlier run) found it
strict on faithfulness (agreement 0.976) and lenient on relevance by about 1.7× (agreement 0.831, 9
passages called relevant that the person did not), so the corrected relevance is about 0.22 and 0.17.
Relevant sentences are often there and still not needed: for labelling what a sentence says, the
sentence carries the answer.

### Statements beat passages as cross-year evidence

Runs `baseline/passage-hybrid-cited` and `baseline/statement-hybrid-cited`, majority votes paired on
the 331 items; the passage store holds windows of about 200 words over the same statements.

| arm | passage store, vote (none F1) | statement store, vote (none F1) | flips passage → statement | p |
|---|---|---|---|---|
| hybrid, same report | 0.7499 (0.705) | 0.7442 (0.690) | +11 / −12 | 1.00 |
| hybrid, other years | 0.7396 (0.703) | 0.7767 (0.739) | +18 / −7 | 0.043 |
| neighbouring sentences | 0.7509 (0.674) | 0.7617 (0.705) | +9 / −6 | 0.61 |
| sentence only | 0.7580 (0.739) | 0.7397 (0.766) | +5 / −7 | 0.77 |

Three 200-word passages from the company's other years are worse than three statements (p = 0.043, one
of four comparisons, so a direction rather than a settled fact); inside the same report the two units
tie. The statement is also what the graph's edges point at, so the comparison with the graph is on one
unit.

### Cost

USD 0.21–0.30 per 1,000 items with prices of 0.20 / 1.20 per million input / output tokens; about 540
input and 89 output tokens per item without evidence, 660–990 and 86–105 with.

### The agentic arm (`agentic/rq1-dev-all-arms`, `agentic.md`)

A planner that first decides whether the sentence has a gap, then searches and verifies, does not improve the
label: `company_agentic` vote 0.7645 against 0.7686 for `sentence_only` in the same run (+11 / −8, p = 0.65),
and against `cross_year_rrf` +10 / −14 (p = 0.54), at USD 0.445 per 1,000 items against 0.184 and 0.242. It
hands over 0.18 spans per item against 2.66, and 18.0 % of them are cited against 0.5 %. One finding beyond the
agent: on the 75 sentences a text rule frozen in advance marks as depending on their context, the neighbouring
sentences go +9 / −0 against `sentence_only` (p = 0.004, macro-F1 0.663 to 0.771), and +12 / −14 on the rest.
One of ten slice comparisons, on dev.

## 2. What became of dated commitments? (RQ2)

Details in `promises.md`; the pipeline: 3,164 candidate statements → 1,273 validated targets (extracted
by sub-agents; the small model gets 1,462, statement-level κ 0.79) → 880 promises (restatements across
years merged) → **374 checkable inside the corpus** (32 companies, deadlines 2021–2025).

### The system, as checked

| | first version | final version |
|---|---|---|
| evidence | top 6 statements of the deadline-year reports; one dense ranking that covered sentence-shaped statements only | every later report up to the year after the deadline, both rankings over every statement, a budget per year, neighbours of the best hits, linked targets; 11.6 statements per promise |
| judge | the model names the outcome | the model labels each statement (about this target? states the deadline year's result? moves it?), a fixed rule names the outcome, majority of three runs |
| human check | 75 promises, `promise-check-first-evidence.xlsx` | 60 held-out promises, `promise-check-trajectory.xlsx` |
| accuracy, weighted to the pool | 0.82 (0.72–0.90) | 0.82 (0.70–0.92) |
| verdict given where the check says unclear | 31 % (20–42) | **14 % (2–33)** |
| unclear where the check has a verdict | 0 % | 15 % (3–29) |
| verdicts that are right | 75 % (63–86) | 85 % (74–94) |

Outcomes are reported on four classes: achieved, **failed** (missed, or re-dated or weakened: the
deadline passed without the target being reported as met), unclear, disappeared. The judge's finer
`revised` label is not reliable, for the system or between two rounds of annotation, and stays in the
data as detail only.

### What the commitments did, human-verified

| outcome | on the first evidence | on the complete evidence |
|---|---|---|
| achieved | 36 % (28–42) | **50 % (41–59)** |
| failed, including re-dated | 8 % (5–11) | **13 % (8–21)** |
| unclear | 49 % (40–58) | **31 % (22–39)** |
| disappeared | 5 % (4–7) | 6 % (1–14) |

Where the outcome can be told, four in five commitments were met and one in five was missed or
re-dated. The 49 % that could not be judged on the first evidence was in large part the retrieval: its
dense ranking covered only the sentence-shaped statements, which leaves out most sentences that report
a result, and rank fusion buried what one ranking could not see (1.6 % of the evidence shown came from
outside that index). With both rankings over every statement the human-verified `unclear` share is 31 %.

### What a reader of the system's output can rely on

| system says | checked | agrees |
|---|---|---|
| achieved | 13 | 13 |
| failed | 24 | 18 (and it misses 4 of 22) |
| unclear | 18 | 12 |
| disappeared | 5 | 4 |

Counts over the 374: achieved 169, failed 56, unclear 134, disappeared 15.

### Against the gold set

Every checkable promise now has a settled outcome (`data/eval/rq2promises.pair_gold.a6f35618dd6e.jsonl`:
137 double-annotated by the group, 236 by two model annotators of different families calibrated on
those rows and adjudicated, one row dropped as not a promise; `promises.md` section 8), split dev 123 /
test 250. Gold over the 373: achieved 206, failed 68, unclear 86, disappeared 13. On dev the judge
agrees with the gold on 96 of 123 (0.780, κ 0.67); it gives a verdict on 5 of the 22 gold-unclear
promises (23 %), leaves 18 of the 101 settled ones unclear (18 %), and 90 % of its verdicts are right.
Precision / recall per class: achieved 0.94 / 0.84, failed 0.88 / 0.65, unclear 0.49 / 0.77,
disappeared 0.67 / 1.00. The test split has not been opened.

### Retrieval arms on RQ2 (`gw-eval --task rq2`, dev, 123 promises, shared judge v2, three repeats)

| arm | run | accuracy mean ± sd | vote accuracy | vote κ | vote macro-F1 | verdict where gold unclear | unclear where gold settled | verdicts right | statements / promise | retrieval p50 |
|---|---|---|---|---|---|---|---|---|---|---|
| trajectory finder (graph) | `graph/promise-window-trajectory` | 0.791 ± 0.005 | 0.789 | 0.69 | 0.769 | 5 / 22 | 17 / 101 | 80 / 89 (0.90) | 11.7 | 261 ms |
| hybrid, top 20 in the window | `baseline/promise-window-hybrid` | 0.783 ± 0.009 | 0.789 | 0.68 | 0.771 | 3 / 22 | 21 / 101 | 78 / 83 (0.94) | 20.0 | 641 ms |

Paired on the 123 promises (majority votes, McNemar): +4 / −4, p = 1.00; the hybrid arm is unstable
across repeats on 20 promises, the finder on 10. On RQ2 as on RQ1, the graph line's structured
retrieval and plain hybrid retrieval are not distinguishable on dev. The finder reads 11.7 statements
where the baseline reads 20, so its judgements cost less (USD 1.30 against 1.62 per 1,000) and are
steadier; the baseline is more cautious (fewer verdicts, more of them right). The test split has not
been opened.

The agentic arm, in one later batch of runs paired among themselves (`results/agentic/`, `agentic.md`): hybrid
top 20 vote 0.805, a fixed budget per report year with no planner 0.813 (11.6 statements, paired +7 / −6, p = 1.00), the
planner on top of it 0.789 (14.3 statements, USD 0.84 per 1,000 more, against hybrid +4 / −6, p = 0.75). **Retrieval is
not what limits RQ2 on this store**: in 14 of the 17 errors that could be checked, a phrase of the answer was already
in front of the judge, and doubling the evidence to 40 statements lowers the vote to 0.772 (+3 / −7, p = 0.34). The
same hybrid configuration scored 0.789 and 0.805 on two days, which is the noise to read these against.

### Case studies

`case-studies.md`: ten commitments from eight companies as page-cited timelines, one per pattern:
delivered on time; delivered late and disclosed; deadline moved then exceeded; moved twice with reasons,
still open; a dated commitment dissolving into intent; a milestone slipping a year per report; missed and
admitted; one issuer both ways; partial delivery not reconciled; never mentioned again.

## 3. What can be claimed

1. Statement-level evidence from the company's own reports neither helps nor hurts action
   classification beyond run-to-run noise; passage-level evidence from other years is worse than
   statement-level evidence.
2. A temporal claim graph retrieves cross-year evidence at the same accuracy as hybrid retrieval and at
   9–20 ms against 190–730 ms; it does not improve accuracy.
3. Following a dated commitment through later reports is feasible: on held-out promises the final
   system's verdicts are right 85 % of the time, and it over-commits on 14 % (2–33) of the commitments
   a person cannot settle.
4. About half of dated commitments in these reports can be verified as met from the issuer's own later
   reports (55 % in the gold set of 373); about one in six failed, by missing the deadline or moving it;
   a quarter cannot be judged from the text, and a few vanish from the reports.
5. Checking outcomes needs every statement in the index, table rows and result lines included: an index
   of sentence-shaped statements alone hid most of the sentences that report results, and the
   human-verified unclear share fell from 49 % to 31 % once every statement was ranked.
6. On dev, letting an LLM plan the retrieval improves neither question and costs more. On RQ1 what helps is narrower:
   the neighbouring sentences, for sentences that a text rule marks as depending on their context; on RQ2, a fixed
   budget per report year does as well as anything, and the judge rather than retrieval is the limit. Test not read.

## 4. Limits

- The promise gold rests on two human annotators for 137 promises and on calibrated model annotators
  (two model families, adjudicated) for the other 236; six annotators but one per row for 950 of the
  1,000 classification items.
- The judge is noisy: 16 % of promises do not get the same outcome in three runs; the majority is used.
  The over-commitment rate rests on 17 human-unclear rows, hence its interval.
- Flattened multi-column tables can be read across columns and produce a wrong `achieved`; a bare
  "this target" can be mis-attributed.
- Extraction lacks a scope or baseline the promise sentence left to its context (fields right 0.82 on
  the stricter second check); targets that exist only inside tables are not extracted.
- Aspect canonicalisation failed its gate, so cross-year aspect edges rely on exact normalised matches.
- Retrieval latencies were measured with three runs sharing one machine.
- Test split unread (`agentic.md`, section 6: an attempt stopped when the API account ran out of credit, before any
  metric was written); retrieval metrics need pooled judgements that were not collected; the front end was not built;
  the stock-price analysis is a literature screen only.
- The agentic arm reads the statement store, so it cannot see the 1,938 statements under five words, one-word result
  cells among them; the graph arms are cited unpaired.
