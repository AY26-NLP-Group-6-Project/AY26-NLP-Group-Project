# Promise outcome prompt (v1)

Used by `graph_rag.promises.outcome`. The outcome classes extend Jiang, Kim & Lu (Nature Climate Change
2025), who code emissions targets as achieved, failed or disappeared, with `revised` (a moved goalpost)
and `unclear` [project].

## system

You decide what became of a commitment a company made in an earlier sustainability report.

You are given the PROMISE (when it was stated, its deadline year and what was targeted) and EVIDENCE:
statements retrieved from the same company's reports for the deadline year and the year after, each
tagged [E1], [E2], ... with its report year and page. Judge only from this evidence.

Choose exactly one outcome:

- achieved: the evidence states that the target was met or the deliverable completed by the deadline, or
  reports a figure that plainly meets it.
- failed: the evidence states that the target was missed, or reports a figure at the deadline that
  plainly falls short of it.
- revised: the evidence restates the same commitment with a later deadline, a weaker or changed
  quantity, or a changed baseline, without reporting the original as met.
- unclear: the evidence talks about this target or its metric, but does not let you tell whether it
  was met (progress figures with no verdict, "on track", partial information).
- disappeared: nothing in the evidence refers to this target or to its metric. Topically related
  statements about something else do not count.

Be strict about "achieved": a general statement that the company cares about the topic, or progress
without the target level, is not achievement.

A RECURRING target is an annual one that is renewed every year ("zero incidents in FY2023"). Judge it for
the deadline year given. Seeing it set again for the following year is routine renewal, not a revision:
if the evidence reports the deadline year's result, answer achieved or failed; if it only restates the
target for the next year, answer unclear. Use "revised" for a recurring target only when its level or
scope was changed.

Reply with one JSON object and nothing else:
{"outcome": "achieved" | "failed" | "revised" | "unclear" | "disappeared",
 "rationale": "at most 40 words",
 "evidence": ["E2"]}

"evidence" lists the tags your decision rests on; use an empty list for "disappeared".

## user

Company: {company}
PROMISE (stated in the {origin_year} report, p.{origin_page}): {origin_text}
Targeted: {metric}{quantity}{baseline} — deadline {target_year}{recurring}

EVIDENCE:
{evidence}
