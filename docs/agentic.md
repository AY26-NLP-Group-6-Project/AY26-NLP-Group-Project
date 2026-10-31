# The agentic arm

A bounded planner over the shared corpus tools, one retriever for both research questions
(`src/agentic-rag`). The shared classifier and judge read what it returns, unchanged and under the same
budget as every other arm. It reads only the statement store (hash `d8a62bfe40c6`), never the claim graph.
Everything below is on dev; **the test split has not been read** (section 6).

## 1. What it does

```
query -> policy for the question -> planner: ask, call fenced tools, update the pool, stop?
      -> choose the evidence -> shared classifier or judge -> gw-eval
```

The tools are `gw_common.corpus` (`search`, `neighbours`, `page`, `reports`) behind a fence in code
(`agentic_rag/tools.py`): a planner that names another company, a year outside the window or the sentence
being classified gets nothing. The agent never names a label or an outcome.

**RQ1 (`agentic_rag/rq1.py`, conditions `cross_year_agentic` and `company_agentic`).** The classifier cites
retrieved evidence on 1–9 % of items, so the first planner call is a gate: does the sentence have a gap
another passage could close (an unresolved reference, an unclear actor, an aspect it cannot read)? No gap, no
evidence, and the classifier reads exactly what `sentence_only` reads. With a gap, the planner writes it as a
question and gives queries; `company_agentic` also reads the sentences beside the target; a verifier call
says which passages answer the question, and only those reach the classifier, in cross-encoder order against
the question. `cross_year_agentic` is the same over other years only, like for like with `cross_year_rrf`.

**RQ2 (`agentic_rag/rq2.py`, condition `promise_window`).** Hop 0 makes no LLM call: a budget per report year (6
statements from the first report at or after the deadline, 3 from each later one, 2 from each earlier one) and
the neighbours of the two best hits, the trajectory finder's rules over the statement store.
`AGENTIC_MAX_HOPS=0` stops there: the fixed-budget arm. With hops, one fixed search looks for a moved or
dropped deadline, so a statement that looks like success does not end the search for the contrary one. Then
the planner reads what has been gathered and asks for what is missing: the deadline-year result, a change, a
report of the window (`search`, `around`, `page`). Its finds keep 8 of the 20 slots.

The first version of this arm (`results/agent-rag/passage-hybrid` on the branch `dev/luyuanzhi`: passage
store, label classifier) spent 3.2× the plain search, and 839 of its 879 spans were what hop 0 had found anyway,
because rank fusion gave the first search's list all three slots. The gate and the verifier replace that.

## 2. RQ1 on dev

`agentic/rq1-dev-all-arms`, 331 items, three uncached repeats, cited classifier, flips of the majority votes against
`sentence_only`. "Items citing evidence" is the share of the items given evidence.

| arm | macro-F1 mean ± sd | vote | `none` F1 | flips | p | spans / item | items citing evidence | USD / 1k |
|---|---|---|---|---|---|---|---|---|
| `sentence_only` | 0.7561 ± 0.015 | 0.7686 | 0.804 | — | — | 0 | — | 0.184 |
| `local` | 0.7598 ± 0.026 | 0.7745 | 0.848 | +21 / −14 | 0.31 | — | — | 0.226 |
| `same_report_rrf` | 0.7544 ± 0.002 | 0.7528 | 0.837 | +15 / −14 | 1.00 | 2.00 | 10.5 % | 0.245 |
| `cross_year_rrf` | 0.7841 ± 0.010 | 0.7988 | 0.787 | +19 / −12 | 0.28 | 2.66 | 1.3 % | 0.242 |
| `cross_year_agentic` | 0.7544 ± 0.002 | 0.7609 | 0.792 | +8 / −10 | 0.82 | 0.11 | 7.4 % | 0.432 |
| `company_agentic` | 0.7624 ± 0.011 | 0.7645 | 0.828 | +11 / −8 | 0.65 | 0.18 | 23.5 % | 0.445 |

Paired: `company_agentic` against `cross_year_rrf` +10 / −14 (p = 0.54); `cross_year_agentic` against
`cross_year_rrf` +12 / −21 (p = 0.16). **The agent does not improve the label, and it costs nearly twice
any fixed arm**, because the gate is a call on every item.

What it does change is what the classifier receives. It hands over under a tenth of the evidence and that evidence
gets used: 18.0 % of its spans are cited against 0.5 % for `cross_year_rrf`. The gate leaves 262 of 331
sentences with no evidence at all. On those the two arms read one identical prompt and the votes still flip +4 /
−6, which is pure model noise and swallows the +7 / −2 on the 69 sentences the gate opened (p = 0.18 when the
closed ones are held on the same labels).

Ablations of `company_agentic`, all inside that noise (`agentic/rq1-dev-*`): no verifier (one hop, vote 0.7814,
`none` 0.774; two hops with cross-encoder selection, 0.7629, 0.800), three hops (0.7560, 0.816), neighbours kept
whatever the verifier says (0.7684, 0.800). The frozen configuration was chosen for the cleanest flips where the
gate opens and the best `none` F1, not its vote, which is not the highest.

**A cheaper signal.** A text rule frozen before the full run (`agentic_rag.analyze`: "this target", a leading
"it" or "such", a third-party actor; 75 of 331 sentences, crude, reading only the sentence) found what the LLM
gate did not. On those 75, `local` against `sentence_only` is +9 / −0, p = 0.004, macro-F1 0.663 to 0.771; on the
other 256 it is +12 / −14. Routing by the rule and leaving the rest on `sentence_only` scores 0.7924 at no
planner cost, composed from the run's labels; routing by the LLM gate gives +9 / −5. So the sentences that need
context are identifiable, and what they need is the neighbouring sentences, not retrieval. It is a dev finding
from one of ten slice comparisons (Bonferroni 0.04), so the test split is what would confirm it.

## 3. RQ2 on dev

123 promises, shared judge v2, three repeats, votes against the gold.

| arm | run | vote accuracy | κ | macro-F1 | verdict where gold unclear | unclear where gold settled | verdicts right | statements / promise | USD / 1k |
|---|---|---|---|---|---|---|---|---|---|
| hybrid, top 20 | `agentic/rq2-dev-hybrid-k20` | 0.805 | 0.71 | 0.788 | 5 / 22 | 16 / 101 | 82 / 90 | 20.0 | 1.67 |
| hybrid, top 40 | `agentic/rq2-dev-hybrid-k40` | 0.772 | 0.66 | 0.741 | 3 / 22 | 20 / 101 | 76 / 84 | 40.0 | 2.39 |
| fixed budget, no planner | `agentic/rq2-dev-fixed-budget` | 0.813 | 0.72 | 0.798 | 3 / 22 | 16 / 101 | 81 / 88 | 11.6 | 1.32 |
| agent, two hops | `agentic/rq2-dev-two-hops` | 0.789 | 0.69 | 0.761 | 3 / 22 | 21 / 101 | 78 / 83 | 14.3 | 1.43 + 0.84 planner |

Paired: fixed budget against hybrid +7 / −6, p = 1.00; agent against hybrid +4 / −6, p = 0.75; agent against fixed
budget +2 / −5, p = 0.45. **The planner adds cost and no accuracy. The fixed budget does as well as anything, on the
fewest statements and without an LLM call.** Published results for the trajectory finder (vote 0.789, 11.7
statements) are close to the fixed budget, which follows the same rules without the graph; they were not paired here.
Note the noise: the same hybrid configuration scored 0.789 on 2026-10-30 and 0.805 here.

**Why: retrieval is not what limits RQ2.** Of the 24 errors of the hybrid run, 17 could be checked by matching a phrase
from the annotators' notes against the evidence (a dev-only audit by regular expression, so a rough one; the agent
never sees the notes). In 14 of those 17 the phrase was already in front of the judge. By its rationales the judge
held back, mostly on `this_target` strictness: "no significant fines" for a target of zero non-compliance cases, "zero"
with a table's dashes, a contradiction between two statements. Doubling the evidence points the same way: phrases
shown go from 14 to 16 of 17 while accuracy falls (+3 / −7, p = 0.34), and settled promises left unclear rise from 16
to 20. The agent reached 15 of 17. The planner mostly stops after one call (1.30 per promise; 4 of 123 hit the cap of
two), so more hops were not run. Any further gain on RQ2 has to come from the judge.

### Judge v3

`gw_common/judges/promise.py`, `promise_outcome_v3.md`. The design stays: the model labels each statement and a rule
names the outcome. It adds `proxy` (the company's own account of the same matter in other words, "no significant fines"
for zero fines), `partial` (a commitment stated to be part delivered, which counts as a miss) and `figure` (the deadline
year's number, compared with the target in code, only for a target stated as a level in the same unit), and shows 1,000
characters of a statement instead of 500. `--judge v3` selects it; v2 stays the default. `--evidence <run>/evidence.jsonl`
judges an earlier run's statements again, so what differs below is the judge alone (`agentic/rq2-dev-v3-*`).

| evidence | v2 vote | v3 vote | flips v2 → v3 | p | verdict where gold unclear, v2 → v3 | unclear where gold settled, v2 → v3 | verdicts right, v2 → v3 | judge USD / 1k, v3 |
|---|---|---|---|---|---|---|---|---|
| hybrid, top 20 | 0.805 | 0.813 | +6 / −5 | 1.00 | 5 → 6 of 22 | 16 → 12 of 101 | 82/90 → 84/95 | 1.88 |
| fixed budget | 0.813 | **0.870** | +9 / −2 | 0.065 | 3 → 4 of 22 | 16 → 8 of 101 | 81/88 → 89/97 | 1.49 |
| agent, two hops | 0.789 | 0.837 | +9 / −3 | 0.15 | 3 → 5 of 22 | 21 → 11 of 101 | 78/83 → 86/95 | 1.62, plus 0.84 planner |

**v3 reads more promises through at about the same over-commitment, and no comparison is significant at 0.05.** It was
designed after reading the errors and the annotators' notes on this same split, so these numbers are optimistic, and
only the test split can say how much of the gain holds. The 22 promises the group labelled itself went 0.727 → 0.818 on
the fixed budget and 0.682 → 0.818 on the agent's evidence, so the gain is not only on the model annotators' rows.

Each feature helps a little when the rule is re-run on the saved labels (`python -m agentic_rag.analyze_judge`), with
`proxy` the largest; on the fixed budget's evidence none gives 0.789, `proxy` 0.846, all three 0.870. The longer statements
show no gain: on the agent's evidence 500 characters gives 0.854 against 0.837 at 1,000 (9 against 11 settled left
unclear, 6 against 5 verdicts where gold is unclear, 21 against 11 unstable), inside the noise, so 1,000 stays for its
steadier votes and at about the same cost.

**The planner still adds nothing.** Under v3, agent against fixed budget is +2 / −6 (p = 0.29), hybrid against fixed
budget +9 / −2 (p = 0.065), hybrid against agent +6 / −3 (p = 0.51). The reason shows in the labels: of the 195
statements the planner's own actions added, the judge gave a result label to 1, and to 6 of the 144 from the fixed search
for a change, against 120 of 1,419 from hop 0 (first repeat). What it adds is mostly other topics, which can only move
a verdict by accident: on P00760 two statements it found turn a correct `disappeared` into `unclear`. **On this evidence
the pipeline to carry forward is the fixed budget with judge v3**, with the agent kept as the measured comparison.

**Two further attempts did not beat it, and this is where tuning stopped.** Keeping only the added statements the judge's
labels found a use for (17 of 339, on 10 promises; `analyze_judge --write-verified`, a simulated verifier and an optimistic
one) lifts the agent's evidence from 0.837 to 0.862, level with the fixed budget at 0.870 (+2 / −3, p = 1.00) and with a planner
still to pay for: the noise was the cost, and removing it recovers no more than what hop 0 already had
(`agentic/rq2-dev-v3-agent-verified`). Five repeats on the fixed budget's evidence give 0.862, not better than three, at 5/3
the cost (`agentic/rq2-dev-v3-fixed-budget-5-repeats`). That run also shows how far 0.870 is the top of the noise: single
repeats range from 0.829 to 0.870, and the mean over the eight v3 repeats is about 0.85, the better estimate on dev.

The 16 errors left split into 9 that change between repeats and 7 that do not, and many sit on boundaries the annotators
themselves had to settle: one day past a "first half" deadline (P00811), an antecedent the promise never names (P00463). Fixes
for single cases conflict: P00092 and P00406 both pit `met` against `missed`, and in the second the `missed` is a list number
read as a count. More changes here would fit this split rather than the task.

## 4. Cost and speed

Planner: 530–550 input and 115–120 output tokens per RQ1 item, 1.2 calls; USD 0.84 per 1,000 promises on RQ2, 1.3
calls. Retrieval p50 on RQ2 is 5.5 s for the agent, 0.4 s for the fixed budget and 1.0 s for hybrid. These latencies
were measured with several runs sharing one machine, and the agent's runs used 8 retrieval workers, so compare them
only roughly.

## 5. Limits

- The statement store holds statements of five words or more, so a one-word result cell ("Achieved") cannot be read.
  1,938 statements are outside it. The finder reads them from the graph; this arm does not, by decision. What this
  costs is not measured; the audit above suggests a small part of the errors.
- Findings are on dev: 331 and 123 items, against 0.018–0.025 of run-to-run noise on RQ1 and 0.016 on RQ2. The
  RQ2 prompt was not iterated once the audit showed retrieval was not the limit, so its result is a first version.
- `same_report_rrf` shows two statements rather than three, here and in the published baseline: the target ranks
  first in its own report, and the harness drops it after the cut.
- The composed routes in section 2 use labels from separate conditions of one run, not a run of their own.
- A manifest records the commit at the end of a run. The two hybrid dev runs started from `040f330` and the four
  `rq1-dev-*` ablations from just before `c3a297f`, which reformatted one line; their code is the same as recorded
  for what they exercise.

## 6. The test split

Configuration frozen at commit `4a3d35f`, with judge v2: RQ1 `AGENTIC_MAX_HOPS=2`, `AGENTIC_SELECT=verified`; RQ2 two
hops; prompts `agentic_rq1_gate.md`, `agentic_rq1_verify.md`, `agentic_rq2_planner.md`. Judge v3 came later and is not
part of this freeze: comparisons with it must be added and committed before test is read. Hypotheses, to be read on test
once:

| # | comparison on test, majority votes, McNemar | what dev showed |
|---|---|---|
| R1 | `company_agentic` against `sentence_only` | +11 / −8, p = 0.65 |
| R2 | `company_agentic` against `cross_year_rrf` | +10 / −14, p = 0.54 |
| R3 | `cross_year_agentic` against `cross_year_rrf` | +12 / −21, p = 0.16 |
| R4 | `local` against `sentence_only`, on the sentences of the frozen text rule | +9 / −0, p = 0.004 |
| R5 | the text rule routes to `local`, the rest stay on `sentence_only`, composed from the run's labels | same flips, macro-F1 0.7686 to 0.7924 |
| R6 | the gate routes to the agent's evidence, the rest stay on `sentence_only`, composed | +7 / −2, p = 0.18 |
| Q1 | RQ2 agent, two hops, against the hybrid baseline | +4 / −6, p = 0.75 |
| Q2 | RQ2 fixed budget against the hybrid baseline | +7 / −6, p = 1.00 |
| Q3 | RQ2 agent, two hops, against the fixed budget | +2 / −5, p = 0.45 |

Six RQ1 comparisons and three RQ2 ones are made; a p-value near 0.05 is read against that number. Nothing is tuned
after test is read; a configuration that loses is reported as losing.

**Status: not run.** One attempt on 2026-10-31 stopped when the API account ran out of credit, with `sentence_only` and
`local` sampled on RQ1 and the RQ2 arms unfinished. No metrics were written and no test label was read. Those partial
directories (`20261031T063349Z`, `T063350Z`, `T063351Z`, `T065124Z` under `artifacts/runs/`) are to be left unread, and
the runs repeated in full. Since `4a3d35f` the agent and its prompts have not changed. Commit `39ffb79` adds judge v3,
`--judge`, and `--evidence` for RQ2, and stores the judge's labels in predictions; with the default v2 they change no
outcome.

```bash
export GW_RETRIEVAL_WORKERS=8                      # PowerShell: $env:GW_RETRIEVAL_WORKERS='8'
uv run gw-eval --system agentic-rag --split test --repeats 3 \
    --conditions sentence_only,local,same_report_rrf,cross_year_rrf,cross_year_agentic,company_agentic
AGENTIC_MAX_HOPS=2 uv run gw-eval --task rq2 --system agentic-rag --split test --repeats 3
AGENTIC_MAX_HOPS=0 uv run gw-eval --task rq2 --system agentic-rag --split test --repeats 3
uv run gw-eval --task rq2 --system baseline-rag --split test --repeats 3
uv run python -m agentic_rag.analyze artifacts/runs/<rq1 run> --conditions local,company_agentic   # R4-R6
uv run gw-eval --compare <rq1 run> <rq1 run> --pairs \
    sentence_only:company_agentic,cross_year_rrf:company_agentic,cross_year_rrf:cross_year_agentic  # R1-R3
uv run gw-eval --compare <baseline rq2 run> <agent rq2 run>                                         # Q1, and so on
```

About USD 8 by the dev rates.

## 7. Reproducing dev

```bash
GW_RETRIEVAL_WORKERS=8 uv run gw-eval --system agentic-rag --split dev --repeats 3 \
    --conditions sentence_only,local,same_report_rrf,cross_year_rrf,cross_year_agentic,company_agentic
AGENTIC_MAX_HOPS=0 uv run gw-eval --task rq2 --system agentic-rag --split dev --repeats 3
AGENTIC_MAX_HOPS=2 uv run gw-eval --task rq2 --system agentic-rag --split dev --repeats 3
uv run gw-eval --task rq2 --system baseline-rag --split dev --repeats 3 [--k 40]
```

`--publish` copies the summaries; per-item predictions and evidence stay in `artifacts/runs/`, and per-item planner
traces in `artifacts/agentic/traces-*.jsonl`, named in each manifest. `--compare` needs the predictions, so a
published folder alone cannot be paired.
