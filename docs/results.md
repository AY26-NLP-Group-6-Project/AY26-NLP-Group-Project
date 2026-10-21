# Results

The findings in one place. Every number names the published run (`results/<group>/<name>/`) or the
check sheet (`kb/annotation/spotchecks/`) it comes from. Dev split only, 331 items; the test split has
not been opened. Classifier `gpt-5.6-luna`, reasoning effort low, three uncached repeats per condition
unless stated; "vote" is the majority over the repeats.

## 1. Does retrieved evidence improve the label? (RQ1)

### Headline: sentence-level evidence, cited classifier

| arm | run | macro-F1 mean ± sd | vote | none F1 | items citing evidence |
|---|---|---|---|---|---|
| sentence only | `baseline/sentence-hybrid-cited` | 0.7553 ± 0.009 | 0.7647 | 0.800 | — |
| sentence only, second run | `graph/graph-arms-cited` | 0.7556 ± 0.012 | 0.7633 | 0.792 | — |
| neighbouring sentences | `baseline/sentence-hybrid-cited` | 0.7449 ± 0.006 | 0.7519 | 0.825 | — |
| hybrid, same report | `baseline/sentence-hybrid-cited` | 0.7492 ± 0.013 | 0.7550 | 0.825 | 7.4 % |
| hybrid, other years | `baseline/sentence-hybrid-cited` | 0.7657 ± 0.005 | 0.7804 | 0.837 | 2.0 % |
| graph, other years | `graph/graph-arms-cited` | 0.7731 ± 0.007 | 0.7728 | 0.800 | 1.3 % |
| graph + hybrid fused | `graph/graph-arms-cited` | 0.7759 ± 0.015 | 0.7799 | 0.849 | 2.0 % |

Paired on the same 331 items (majority votes, McNemar): the two sentence-only runs differ on 11 items,
p = 1.00; the best hybrid arm against the best graph arm, p = 1.00; graph fused against its own
sentence-only, +0.020 with p = 0.078. **Retrieved evidence moves action F1 by at most 0.02, within the
noise between two runs of the same configuration, and the graph is not distinguishable from plain
hybrid retrieval.** What differs is cost: graph lookups take about 10 ms against 117–326 ms for the
hybrid path, which needs a query embedding and a cross-encoder pass.

### Why so little: the classifier rarely uses what it is given

The classifier cites a retrieved span in 1–11 % of items. The RAG-metric judge (`baseline/sentence-hybrid-cited`,
`ragas.md`) finds the rationales faithful (0.94–0.95 of their statements supported) and about half of
the retrieved passages relevant (0.46 same report, 0.38 other years); a human calibration of the judge
(`ragas-check.result.json`, 186 rows) found it strict on faithfulness (agreement 0.976) and lenient on
relevance by about 1.7× (agreement 0.831, 9 passages called relevant that the person did not), so the
corrected relevance is about 0.27 and 0.22. Relevant sentences are often there and still not needed:
for labelling what a sentence says, the sentence carries the answer.

### The retrieval unit matters; the graph does not

Label-style classifier (one word, no rationale), earlier runs:

| arm | unit | vote | none F1 | p vs graph fused |
|---|---|---|---|---|
| hybrid, same report | passage (about 200 words) | 0.7484 | 0.689 | 0.024 |
| hybrid, other years | passage | 0.7464 | 0.598 | 0.002 |
| hybrid, same report | sentence | 0.7648 | 0.820 | 1.000 |
| hybrid, other years | sentence | 0.7510 | 0.788 | 0.345 |
| graph + hybrid fused | sentence | 0.7810 | 0.808 | — |

Runs `baseline/passage-hybrid`, `baseline/sentence-hybrid`, `graph/graph-arms`. A 200-word passage of
ESG prose talks the model into finding an aspect–action in sentences that have none (none F1 falls to
0.60); sentence-sized evidence does not. With sentences, the hybrid retriever equals the graph.

### The prose filter does not matter for RQ1

The sentence store keeps only statements that pass a prose filter (65.8 % of statements of five words
or more; the rest fail mostly for lacking one of its listed verbs and pronouns, 20.3 %, or exceeding 60
words, 6.9 %). Re-run over every statement (`baseline/all-statements-hybrid-cited`, 108,376 chunks),
paired against the prose-store run: same report 0.7550 → 0.7591 (p = 1.00), other years 0.7804 → 0.7722
(p = 0.52), sentence only 0.7647 → 0.7686 (p = 0.63), although 30 % and 23 % of the evidence spans
changed kind. The filter was decisive for RQ2 (below), not for RQ1.

### Cost

USD 0.18–0.24 per 1,000 items with prices of 0.20 / 1.20 per million input / output tokens; about 540
input and 63 output tokens per item without evidence, 650–690 and 85–90 with.

## 2. What became of dated commitments? (RQ2)

Details in `promises.md`; the pipeline: 3,164 candidate statements → 1,273 validated targets (extracted
by sub-agents; the small model gets 1,462, statement-level κ 0.79) → 880 promises (restatements across
years merged) → **374 checkable inside the corpus** (32 companies, deadlines 2021–2025).

### The system, as checked

| | first version | final version |
|---|---|---|
| evidence | top 6 statements of the deadline-year reports; dense ranking only over prose sentences | every later report up to the year after the deadline, both rankings over all statements, a budget per year, neighbours of the best hits, linked targets; 11.6 statements per promise |
| judge | the model names the outcome | the model labels each statement (about this target? states the deadline year's result? moves it?), a fixed rule names the outcome, majority of three runs |
| human check | 75 promises, `promise-check-first-evidence.xlsx` | 60 held-out promises, `promise-check-trajectory.xlsx` |
| accuracy, weighted to the pool | 0.82 (0.72–0.90) | 0.83 (0.71–0.93) |
| verdict given where the check says unclear | 31 % (20–42) | **8 % (3–15)** |
| unclear where the check has a verdict | 0 % | 15 % (4–24) |
| verdicts that are right | 75 % (63–86) | 84 % (71–93) |

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
dense ranking only covered the prose-sentence store, which rejects most sentences that report a result,
and rank fusion buried what one ranking could not see (1.6 % of the evidence shown came from outside the
store). With complete retrieval the human-verified `unclear` share is 31 %.

### What a reader of the system's output can rely on

| system says | checked | agrees |
|---|---|---|
| achieved | 14 | 13 |
| failed | 27 | 21 (and it misses 1 of 22) |
| unclear | 15 | 11 |
| disappeared | 4 | 3 |

Counts over the 374: achieved 173, failed 56, unclear 135, disappeared 10.

### Case studies

`case-studies.md`: ten commitments from eight companies as page-cited timelines, one per pattern:
delivered on time; delivered late and disclosed; deadline moved then exceeded; moved twice with reasons,
still open; a dated commitment dissolving into intent; a milestone slipping a year per report; missed and
admitted; one issuer both ways; partial delivery not reconciled; never mentioned again.

## 3. What can be claimed

1. Sentence-level evidence from the company's own reports neither helps nor hurts action
   classification beyond run-to-run noise; passage-level evidence hurts no-aspect detection.
2. A temporal claim graph retrieves cross-year evidence at the same accuracy as hybrid retrieval and at
   about a tenth of the latency; it does not improve accuracy.
3. Following a dated commitment through later reports is feasible: on held-out promises the final
   system's verdicts are right 84 % of the time, and it over-commits on 8 % of the commitments a person
   cannot settle.
4. About half of dated commitments in these reports can be verified as met from the issuer's own later
   reports; one in eight failed, by missing the deadline or moving it; a third cannot be judged from the text.
5. The prose filter that sentence classification relies on hides the sentences that report results;
   any system that checks outcomes must retrieve over every statement.

## 4. Limits

- One annotator with an AI-drafted first pass for the promise checks so far (a two-annotator sheet of
  150 promises is being filled); six annotators but one per row for 950 of the 1,000 classification items.
- The judge is noisy: 15 % of promises do not get the same outcome in three runs; the majority is used.
- Flattened multi-column tables can be read across columns and produce a wrong `achieved`; a bare
  "this target" can be mis-attributed.
- Extraction lacks a scope or baseline the promise sentence left to its context (fields right 0.82 on
  the stricter second check); targets that exist only inside tables are not extracted.
- Aspect canonicalisation failed its gate, so cross-year aspect edges rely on exact normalised matches.
- Test split unopened; retrieval metrics need pooled judgements that were not collected; the agentic arm
  and the front end were not built; the stock-price analysis is a literature screen only.
