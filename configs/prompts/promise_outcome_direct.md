# Promise outcome, no evidence (the closed-book baseline for RQ2)

Used by `gw_common.judges.promise.propose_direct` through `gw-eval --task rq2 --rq2-baseline direct`. The model
sees the commitment alone, never a retrieved statement, and names the outcome from what it already knows. It is
the floor a retrieval arm must beat; the other floor is the majority class of the development split.

## system

A company made a dated commitment in one of its sustainability reports. You will be shown only the
commitment: the company, the report year and page it was stated in, the sentence, the target as
extracted, and the deadline year. You are shown no later report.

Say what the company's own later reports, from the year after the one that stated the commitment up to
the year after the deadline, say became of it. Use exactly one of these outcomes:

- "achieved": a later report states the target as met by the deadline year.
- "failed": the deadline passed without the target being reported as met, whether a report admits the
  miss or moves the target to a later date.
- "unclear": later reports mention the target or its metric but do not settle whether it was met.
- "disappeared": no later report mentions the target or its metric again.

You have no evidence, so answer from what you know about the company, the sector and commitments of
this kind. Do not invent a later report; if you cannot tell, "unclear" is the honest answer.

Reply with one JSON object and nothing else:
{"outcome": "achieved|failed|unclear|disappeared", "rationale": "at most 30 words"}

## user

Company: {company}
Stated in the {origin_year} report, page {origin_page}: "{origin_text}"
Targeted: {metric}{quantity}{baseline}
Deadline year: {target_year}{recurring}
