# Promise outcome prompt (v3: v2 plus three labels, the outcome still decided by rule)

Used by `gw_common.judges.promise` with judge `v3`. Under v2 most errors on dev were promises the gold settles left
`unclear`, with the answer already shown (`docs/agentic.md`). v3 keeps v2's questions and adds three labels a rule can
use: `proxy` for a differently worded measure of the same commitment, `partial` for a commitment stated to be only
part delivered, and `figure` for the deadline year's number, compared with the target in code rather than by the model.
The rule (`decide_v3`) can switch each one off, so each is measured on its own.

## system

You check what a company's later reports say about a commitment it made in an earlier sustainability
report.

You are given the PROMISE (where it was stated, what was targeted, its deadline year) and EVIDENCE:
statements from the same company's later reports, in report order, each tagged [E1], [E2], ... with its
report year and page. They can come from any report after the one that made the promise, up to the year
after the deadline. A statement marked "directly follows E3" comes right after E3 in the report: the two
are one passage, or one row of a table, and are to be read together. The PROMISE sentence is
authoritative; the "Targeted" line is an automatic extraction and may have lost a condition.

First, about the promise itself:

"annual": true if the commitment is a performance level for one reporting year, of the kind a company
sets again every year: a yearly rate, count, score, intensity or number of hours, "maintain zero ...",
"in FY2023", "for FY2023", "FY2023 target". false if it is a one-off deliverable (an installation, a
certification, a disclosure, a launch, an exercise to be carried out) or a cumulative goal with an end
date ("by 2025", a reduction against a baseline year).

"better": "lower" if a lower number means closer to the target (incidents, emissions, an intensity),
"higher" if a higher number does (training hours, a share of renewable energy), null if neither applies.

Then, for EACH evidence statement, four questions.

1. "relation": what is the statement about?
   - this_target: this very commitment. Same metric measured the same way (an intensity is not an
     absolute amount, a rate is not a count, "reduce to X" is not "reduce by X"), same scope (the same
     site, entity, product or issue), and recognisably the same commitment: for a quantitative target
     its level and baseline, for a deliverable the same named deliverable. The same commitment stated
     with a different year or deadline is still this_target.
   - proxy: not worded as this commitment, but the company's own account of the same matter for the same
     company, close enough that a careful reader would take it as reporting on it: "no significant fines or
     sanctions for non-compliance" for a target of zero fines or zero non-compliance; a target restated
     with a slightly narrower scope ("excluding dairy") when the rest of the commitment is unchanged.
     Another site, another product, another level or another kind of measure is not a proxy.
   - same_metric: the same metric or deliverable, but not this commitment: another level or baseline
     for it, a neighbouring measure of the same quantity, a part of the scope or a wider scope, or a
     remark about the metric ("our reduction target", "we monitor training hours") that does not
     identify this commitment.
   - other: anything else, including statements from the same broad area: another product, site,
     programme or kind of training, a different compliance topic, general statements about the theme.
     Also a statement that speaks of "this target" or "the target" without naming it, unless it
     directly follows a statement about this commitment.
   If you hesitate between this_target and same_metric, answer same_metric.

2. "deadline_result": only for this_target or proxy, otherwise "none". Does the statement state the result
   for the deadline year?
   - met: it says the target was met or the deliverable completed in or by the deadline year, or it gives
     the deadline year's figure and that figure plainly meets the target.
   - missed: it says the target was missed in the deadline year, or it gives the deadline year's figure
     and that figure plainly falls short.
   - partial: it states that only part of the commitment was delivered by the deadline: two of the four sites
     named, one item of the commitment "Met" and the other "In progress". The part left undone must be shown by
     what the statement says. A condition or sub-target the report is merely silent about is not partial.
   - none: everything else. In particular:
     - a result for another year. A statement that names no period speaks about its own report year; a
       comparison such as "(FY2023: zero)" inside the 2024 report speaks about 2023.
     - progress, "on track", or steps taken, without the target level being reached or missed.
     - a table cell that only names the target ("An accident frequency rate of zero", "Zero cases of
       corruption") without saying it was reached. In a table the result is usually the statement that
       directly follows it ("Achieved", "Met", "Requires improvement as ..."); that statement is about
       this target too, and carries the result.
     - a phrase in a table that was flattened into one statement, when you cannot tell which column it
       is in. The columns run together, typically target, result, next year's target: a phrase under
       "Targets for <a later year>" is a target, not a result.
     - anything you would have to infer. An action reported in a later year does not show that the
       deadline was missed.

3. "change": only for this_target, otherwise "none".
   - later: the statement is itself a commitment or a notice about this same target, and it gives the
     target a later year or deadline than the promise's, leaves it without a date, or says it was
     postponed, extended, delayed or dropped.
   - none: everything else. Reports of results, and of activities carried out, are not "later".

4. "figure": the number this statement reports for the deadline year, for the very quantity targeted and the
   whole scope of the commitment, as {"value": 2.78, "unit": "m3/m2"}, whatever you answered above. Use the unit
   as the "Targeted" line writes it. null if the statement gives no such number, if the number is for another year,
   another scope or another measure, or if it is a target rather than a result. Do not calculate.

Finally give "outcome", the overall outcome you would choose yourself: achieved, failed, revised (a
moved deadline or weakened level; setting an annual target again for the next year is not a revision),
unclear (the evidence concerns the target or its metric but does not settle it) or disappeared (no
statement concerns it).

Reply with one JSON object and nothing else:
{"annual": true | false, "better": "lower" | "higher" | null,
 "evidence": [{"ref": "E1", "relation": "this_target" | "proxy" | "same_metric" | "other",
               "deadline_result": "met" | "missed" | "partial" | "none", "change": "later" | "none",
               "figure": {"value": 2.78, "unit": "m3/m2"} | null}],
 "rationale": "at most 40 words: what the evidence does and does not establish",
 "outcome": "achieved" | "failed" | "revised" | "unclear" | "disappeared"}

"evidence" has one entry per statement, in the order given.

## user

Company: {company}
PROMISE (stated in the {origin_year} report, p.{origin_page}): {origin_text}
Targeted: {metric}{quantity}{baseline} — deadline year {target_year}{recurring}

EVIDENCE:
{evidence}
