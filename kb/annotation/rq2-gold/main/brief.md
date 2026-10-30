# Promise check: annotation brief

You are one of two independent annotators. Label each promise from the evidence shown and nothing else: no outside knowledge of the company, no guess about what a company of this kind usually does. You do not see the other annotator's labels or the system's proposal.

**Promise check**: One row = one dated commitment a company made in an earlier sustainability report.


## What you see

**stated_in**: The report (year, page) where the commitment was first found.

**promise_sentence**: The statement as it appears in that report.

**extracted**: What the pipeline read out of it: metric, quantity, baseline, deadline year, kind.

**restated_in**: Later report years that repeat the same commitment.

**other_versions**: The same company's commitments on a similar metric with a different deadline or quantity: possible moved goalposts.

**evidence**: Statements retrieved from the company's later reports, in report order, tagged E1, E2, ... with report year and page. They come from every report after the one that made the promise, up to the year after the deadline; the deadline year's block is marked. 'directly follows E3' means the statement comes right after E3 in the report: one passage, or one row of a table (a target cell and then its result), to be read together.


## What you fill

**outcome**: Judge only from the evidence shown, for the deadline year the promise names. Choose not_a_promise if the row is no forward-looking commitment of the company's own with a deadline (a result already achieved, a national or regulatory goal, a wrong deadline), and say why in the note.

- **achieved**: The evidence says the target was met or the deliverable completed in or by the deadline year, or reports a figure that plainly meets it. A deliverable reported as finished before the deadline counts.
- **failed**: The deadline year has passed and the evidence does not report the target as met: it says it was missed, reports a figure at the deadline that falls short, or gives the same commitment a later date, a weaker level or a new baseline, or says it was postponed. A moved deadline is a failed deadline.
- **unclear**: The evidence from the deadline year or later talks about this target or its metric but does not let you tell whether it was met: progress with no verdict, 'on track', a result for part of the commitment, a result for another year.
- **disappeared**: Nothing in the evidence from the deadline year or later refers to this target or its metric. A restatement in an earlier year does not count: the question is whether the company still speaks of it once the deadline has come.
**note**: The tag(s) your outcome rests on (e.g. E2; E5), and anything worth knowing: a wrong extracted field, evidence that is about something else, a case worth writing up.

**Be strict**: General statements that the company cares about the topic are not 'achieved'. Do not infer: an action reported in a later year does not show that the deadline was missed, and a related measure (an absolute amount for an intensity target, another site, another product) is not this target.

**Annual targets**: An annual target ('zero incidents in FY2023') is judged on the result reported for its own year: achieved if met, failed if missed. Seeing it set again for the next year tells nothing by itself: with no result for the deadline year, choose unclear.

**Tables**: A table is parsed into fragments. A fragment that only names the target ('An accident frequency rate of zero') is not a result; the result is usually the fragment marked 'directly follows'. In one long flattened row the columns run together (target, result, next year's target): if you cannot tell which column a phrase is in, do not rely on it.


## Boundaries the group settled

Three places where the first calibration round drifted from the group's labels; follow the group.

- **unclear, not disappeared**, when the evidence from the deadline year or later speaks of the subject of the target (the system, project, activity or metric area) without settling the target: a ticketing system described but no satisfaction rating recorded, sludge waste discussed but no sludge-drying project named. `disappeared` is for evidence that touches none of it.
- **achieved for a practice that is shown running.** A commitment to track, monitor, report, maintain or operate something is met when the deadline-year evidence shows that practice in operation (occurrences tracked and reported to the board, training delivered, the system in use). No sentence has to say 'target met'. A figure or a general statement of concern is still not enough for a quantitative target.
- **unclear when it may not be the same target.** If the extracted fields omit a qualifier that the evidence attaches to the target (a baseline, intensity rather than absolute, a named certification or scope) and you cannot tell whether the evidence speaks of this commitment or a neighbouring one, do not read a 'not achieved' or a figure as this target's verdict: choose unclear and say in the note what the mismatch is.

## Output

For every promise in your batch write one JSON object per line, in batch order, to the file named in your instructions:

    {"promise_id": "P00145", "outcome": "achieved", "note": "E3: FY2023 figure under the cap"}

`outcome` is one of achieved, failed, unclear, disappeared, not_a_promise. `note` names the evidence tags the outcome rests on and, in one clause, why; if an extracted field is wrong or the evidence is about another target, say so. Label every promise; never skip one, never add one. Decide each promise on its own evidence; the reference examples show how the group applied the guide, not what share of each label to expect.