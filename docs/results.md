# Results

The findings in one place; the RQ2 summary for reading is `results/rq2-final/README.md`. Every number names the published run (`results/<group>/<name>/`) or the
check sheet (`kb/annotation/spotchecks/`) it comes from. Dev split unless a section says test: each question's test split has been read once, RQ2's on
2026-10-31 and 2026-11-04 and RQ1's on 2026-11-05, with the comparisons recorded in `history.md` before the read
("On the test split" in each section).
Classifier `gpt-5.6-luna`, reasoning effort low, three uncached repeats per condition
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

### On the test split (669 items, read once on 2026-11-05)

Configurations as published from dev, comparisons recorded in `history.md` before the read. Majority votes over
three repeats; flips and p are McNemar against the run's own `sentence_only`.

| arm | run | vote macro-F1 (95 % CI) | none F1 | flips vs own sentence only | p | retrieval p50 | USD / 1k |
|---|---|---|---|---|---|---|---|
| sentence only | `baseline/statement-hybrid-cited-test` | 0.7644 (0.725–0.800) | 0.833 | — | — | — | 0.211 |
| neighbouring sentences | same | 0.7701 (0.731–0.807) | 0.693 | +23 / −40 | 0.043 | — | 0.247 |
| hybrid, same report | same | 0.7731 (0.735–0.809) | 0.723 | +21 / −33 | 0.134 | 500 ms | 0.257 |
| hybrid, other years | same | 0.7662 (0.726–0.803) | 0.730 | +20 / −36 | 0.044 | 173 ms | 0.253 |
| sentence only | `graph/graph-arms-cited-test` | 0.7663 (0.727–0.803) | 0.833 | — | — | — | 0.211 |
| neighbouring sentences | same | 0.7769 (0.739–0.813) | 0.701 | +20 / −34 | 0.076 | — | 0.245 |
| graph, other years | same | 0.7708 (0.733–0.807) | 0.831 | +12 / −11 | 1.00 | 6 ms | 0.225 |
| graph + BM25 fused | same | 0.7582 (0.718–0.793) | 0.774 | +16 / −29 | 0.072 | 9 ms | 0.248 |
| sentence only | `baseline/passage-hybrid-cited-test` | 0.7642 (0.723–0.801) | 0.830 | — | — | — | 0.211 |
| neighbouring sentences | same | 0.7704 (0.732–0.807) | 0.697 | +29 / −44 | 0.101 | — | 0.244 |
| passages, same report | same | 0.7385 (0.697–0.776) | 0.704 | +24 / −55 | 0.001 | 1,124 ms | 0.280 |
| passages, other years | same | 0.7740 (0.736–0.812) | 0.719 | +31 / −45 | 0.135 | 832 ms | 0.293 |
| sentence only | `agentic/rq1-test-all-arms` | 0.7706 (0.731–0.807) | 0.843 | — | — | — | 0.211 |
| neighbouring sentences | same | 0.7858 (0.747–0.824) | 0.659 | +23 / −42 | 0.025 | — | 0.247 |
| hybrid, same report | same | 0.7642 (0.724–0.801) | 0.693 | +21 / −46 | 0.003 | 2.8 s (8 workers) | 0.259 |
| hybrid, other years | same | 0.7564 (0.717–0.795) | 0.733 | +16 / −41 | 0.001 | 1.6 s | 0.253 |
| agent, other years (`cross_year_agentic`) | same | 0.7644 (0.726–0.803) | 0.796 | +15 / −26 | 0.117 | 2.9 s | 0.468 |
| agent, every report (`company_agentic`) | same | 0.7734 (0.735–0.809) | 0.761 | +19 / −30 | 0.152 | 2.3 s | 0.484 |

Across runs on the same items: sentence only against sentence only +13 / −13 (p = 1.00); hybrid other years against
graph other years +32 / −15 (p = 0.019, the graph arm ahead), against fused +16 / −13 (p = 0.71); statements against
passages, same report +42 / −22 (p = 0.017, statements ahead), other years +27 / −28 (p = 1.00). **Dev holds: no
evidence condition raises action macro-F1 beyond the noise (every evidence arm within ±0.013 of its own sentence
only), and what evidence does on test is cost `none` detection**: shown a span, the model more often reads a pair
into a sentence the annotators said has none (none F1 0.83 → 0.69–0.77), a significant loss of accuracy for the
neighbouring sentences and for cross-year hybrid evidence. The graph arm keeps none F1 at 0.83 because it shows
nothing for 58 % of items, which is why it is ahead of the hybrid arm on the same items; the fused arm, which fills
every item, gives that back. On the granularity ablation the direction holds and the detail moves: on dev the
cross-year comparison separated the units (p = 0.043), on test the same-report one (p = 0.017); statements are never
worse and are cheaper. Evidence is cited in 1.3–8.1 % of items, as on dev.

The agentic arms, run as frozen (`agentic.md` section 6, R1–R6): the gate opens on 155 of 669 sentences; the spans it
hands over are cited on 12–18 % of the items given evidence against 2–8 % for plain retrieval, at USD 0.47–0.48 per
1,000 items. R1 `company_agentic` against `sentence_only` +19 / −30 (p = 0.15); R2 and R3, each agentic arm against
`cross_year_rrf`, +31 / −17 (p = 0.059), the agent ahead because it shows evidence on a sixth of the items. R4, the
text rule's slice (133 sentences): `local` against `sentence_only` +8 / −8 (p = 1.00) where dev had +9 / −0; R5, routing
by the rule, 0.7706 → 0.7763 (+8 / −8); R6, routing by the gate to the agent, +6 / −17 (p = 0.035, worse). **The text-rule
finding of dev does not replicate; no arm of any system improves the label on test.**

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
disappeared 0.67 / 1.00.

### Retrieval arms on RQ2 (`gw-eval --task rq2`, dev, 123 promises, shared judge v2, three repeats)

| arm | run | accuracy mean ± sd | vote accuracy | vote κ | vote macro-F1 | verdict where gold unclear | unclear where gold settled | verdicts right | statements / promise | retrieval p50 |
|---|---|---|---|---|---|---|---|---|---|---|
| trajectory finder (graph) | `graph/promise-window-trajectory` | 0.791 ± 0.005 | 0.789 | 0.69 | 0.769 | 5 / 22 | 17 / 101 | 80 / 89 (0.90) | 11.7 | 261 ms |
| hybrid, top 20 in the window | `baseline/promise-window-hybrid` | 0.783 ± 0.009 | 0.789 | 0.68 | 0.771 | 3 / 22 | 21 / 101 | 78 / 83 (0.94) | 20.0 | 641 ms |

Paired on the 123 promises (majority votes, McNemar): +4 / −4, p = 1.00; the hybrid arm is unstable
across repeats on 20 promises, the finder on 10. On RQ2 as on RQ1, the graph line's structured
retrieval and plain hybrid retrieval are not distinguishable on dev. The finder reads 11.7 statements
where the baseline reads 20, so its judgements cost less (USD 1.30 against 1.62 per 1,000) and are
steadier; the baseline is more cautious (fewer verdicts, more of them right).

The agentic arm, in one later batch of runs paired among themselves (`results/agentic/`, `agentic.md`): hybrid
top 20 vote 0.805, a fixed budget per report year with no planner 0.813 (11.6 statements, paired +7 / −6, p = 1.00), the
planner on top of it 0.789 (14.3 statements, USD 0.84 per 1,000 more, against hybrid +4 / −6, p = 0.75). **Retrieval is
not what limits RQ2 on this store**: in 14 of the 17 errors that could be checked, a phrase of the answer was already
in front of the judge, and doubling the evidence to 40 statements lowers the vote to 0.772 (+3 / −7, p = 0.34). The
same hybrid configuration scored 0.789 and 0.805 on two days, which is the noise to read these against.

Judge v3 on those same statements (`agentic/rq2-dev-v3-*`, `agentic.md`): adds a differently worded measure of the same
commitment, a stated part delivery and a figure compared in code. Fixed budget 0.813 → 0.870 (+9 / −2, p = 0.065), agent
0.789 → 0.837 (+9 / −3, p = 0.15), hybrid 0.805 → 0.813 (+6 / −5, p = 1.00). The trajectory finder, judged with v3 on its stored dev evidence
(`graph/promise-window-trajectory-v3`, 2026-11-04): 0.789 → 0.837 (+8 / −2, p = 0.11), settled promises left
unclear 17 → 10 of 101, a verdict on 5 of 22 gold-unclear promises both times, verdict precision 0.90 both times;
the 22 human-labelled rows stay at 15 right and the gain is on the model-labelled rows (82 → 88 of 101). Settled promises left unclear on the fixed budget
fall from 16 to 8 of 101, with verdicts where the gold is unclear 3 → 4 of 22. Designed on this split, so optimistic. The
planner still adds nothing (agent against fixed budget +2 / −6, p = 0.29): of the 195 statements its own actions added, the
judge gave a result label to 1. Over eight v3 repeats on the fixed budget's evidence the mean is about 0.85, single repeats
0.829–0.870, so 0.870 is the top of the noise.

### On the test split (`agentic/rq2-test-*`, 250 promises, read once; `agentic.md` section 6)

| arm | judge | vote accuracy | verdict where gold unclear | unclear where gold settled | verdicts right | USD per 1,000 promises |
|---|---|---|---|---|---|---|
| hybrid, top 20 (baseline) | v2 | 0.768 | 15 / 64 | 38 / 186 | 143 / 163 | 5.02 |
| fixed budget, no planner | v3 | 0.808 | 21 / 64 | 25 / 186 | 159 / 182 | 4.52 |
| agent, two hops | v3 | 0.840 | 18 / 64 | 20 / 186 | 164 / 184 | 5.72 |
| chosen pipeline: agent, filter, v3 twice | v3 | 0.808 | 22 / 64 | 23 / 186 | 160 / 185 | 10.26 |
| trajectory finder, graph (`graph/promise-window-trajectory-test`, 2026-11-04) | v2 | 0.736 | 11 / 64 | 51 / 186 | 131 / 146 | 4.00 |
| hybrid, top 20, second run (`baseline/promise-window-hybrid-test`, 2026-11-04) | v2 | 0.708 | 18 / 64 | 49 / 186 | 131 / 155 | 4.98 |
| trajectory finder, graph, judge v3 on the same evidence (`graph/promise-window-trajectory-test-v3`) | v3 | 0.804 | 18 / 64 | 27 / 186 | 155 / 177 | 4.56 |
| hybrid, top 20, second run, judge v3 on the same evidence (`baseline/promise-window-hybrid-test-v3`) | v3 | 0.748 | 27 / 64 | 33 / 186 | 150 / 180 | 5.64 |
| fixed budget, second batch (`agentic/rq2-test-fixed-budget-v2-b2`, 2026-11-05) | v2 | 0.748 | 12 / 64 | 45 / 186 | 135 / 153 | 3.96 |
| fixed budget, second batch, judge v3 on the same evidence (`agentic/rq2-test-fixed-budget-v3-b2`) | v3 | 0.768 | 22 / 64 | 29 / 186 | 150 / 179 | 4.59 |
| agent, two hops, second batch (`agentic/rq2-test-agent-v2-b2`, 2026-11-05) | v2 | 0.744 | 16 / 64 | 44 / 186 | 138 / 158 | 5.75 |
| agent, two hops, second batch, judge v3 on the same evidence (`agentic/rq2-test-agent-v3-b2`) | v3 | 0.800 | 21 / 64 | 24 / 186 | 157 / 183 | 6.32 |

No frozen comparison reaches 0.05: the chosen pipeline against the baseline is +28 / −18 (p = 0.18), against the fixed budget with v3
+5 / −5 (p = 1.00), and its filter loses to no filter +5 / −13 (p = 0.096). v3 against v2 is the one change in one direction on every
arm (fixed budget +23 / −12, p = 0.090; hybrid +24 / −12, p = 0.065), at more verdicts where the gold is unclear. The gain lies on the
model-labelled rows (fixed budget 99 → 111 of 135; on the group's 115 rows 92 → 91). The unfiltered agent with v3 came top, at +32 / −14
against the baseline (p = 0.011 uncorrected), but it is a best of seven picked after the fact and test is spent.

The graph line, read once on 2026-11-04 as a frozen system (the finder unchanged since 2026-10-03, judge v2): the
finder 0.736 against the hybrid baseline run again the same day 0.708, paired +20 / −13, p = 0.30; both more cautious
than on dev (settled promises left unclear 27 % and 26 %), the finder's verdicts right 0.90 against 0.85, on 11.6
statements against 20. Judge v3 on the same stored evidence: the finder 0.736 → 0.804 (+26 / −9, p = 0.006), the baseline
0.708 → 0.748 (+28 / −18, p = 0.18); under v3 the finder is ahead of the baseline, +24 / −10, p = 0.024 (one of four
comparisons in this batch, about 0.1 corrected), holding verdict precision at 0.88 where the baseline's falls to 0.83
because v3 doubles its verdicts on gold-unclear promises (18 → 27 of 64). On the group's 115 rows the finder goes 85 → 88
and the baseline 81 → 83; on the 135 model-labelled rows 99 → 113 and 96 → 104. The same hybrid configuration scored
0.768 in the 2026-10-31 batch and 0.708 here, on another machine on another day, so test rows are paired within a batch
only (`history.md`, 2026-11-04). The agentic system's two RQ2 arms run again in this batch on 2026-11-05, so all four
retrievers pair on one machine: under v2 fixed budget 0.748, agent 0.744, finder 0.736, baseline 0.708, no pair
separating (closest: fixed budget over baseline +17 / −7, p = 0.064); under v3 finder 0.804, agent 0.800, fixed budget
0.768, baseline 0.748, with the agent's v2 → v3 +23 / −9 (p = 0.020), finder against agent +14 / −15 (p = 1.00), agent
against baseline +27 / −14 (p = 0.060), fixed budget v2 → v3 +21 / −16 (p = 0.51). The planner costs USD 1.13 per 1,000
promises on top of the judge, 1.8 calls per promise, retrieval p50 11.5 s against 0.6 s (fixed budget) and 0.2 s
(finder), 32 % of its evidence from later hops.

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
6. RQ2, on test: letting an LLM plan the retrieval is not shown to help or to hurt, and the chosen agent pipeline is not shown
   to beat the hybrid baseline (0.808 against 0.768, p = 0.18) at twice the cost. A judge that reads more wordings as this
   commitment moves every arm by 11 to 14 promises of 250, more than any retrieval change, short of significance and mainly on
   model-labelled rows.
7. RQ1, on dev and test: letting an LLM plan the retrieval does not improve the label and costs more. The one narrower
   gain seen on dev, the neighbouring sentences for sentences that a text rule marks as depending on their context, does
   not replicate on test (+8 / −8); on test every shown span costs `none` detection.

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
- Both test splits have been read once and are spent (RQ1 on 2026-11-05; RQ2 on 2026-10-31 for the agentic batch and
  2026-11-04 for the graph line and a second baseline run), so a change made from here on cannot be checked on them;
  the two RQ2 test batches ran on different machines on different days and are paired within a batch only. Retrieval
  metrics need pooled judgements that were not collected; the front end (`frontend/`) is a demo over single dev items,
  not a source of numbers; the stock-price analysis is a literature screen only.
- The agentic arm reads the statement store, so it cannot see the 1,938 statements under five words, one-word result
  cells among them.
