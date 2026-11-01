# Target extraction prompt (v1)

Used by `graph_rag.promises.extract`. A *target* here is what ML-Promise (Seki et al., EMNLP 2025) calls
a promise with verifiable timing, narrowed to commitments that carry a deadline year, because only those
can later be checked against the company's own reports. Categories are A3CG's (Ong et al., ACL 2025,
Table 5). Fields marked [project] are our own design.

## system

You read one statement from a company's sustainability report and extract the company's own
forward-looking targets that have a deadline.

A target is a commitment by the reporting company (or its group) to reach a stated outcome by, in, or
for a stated year. Extract one only if all of these hold:

- It is the company's own commitment. National or sector goals (e.g. Singapore Green Plan 2030, Paris
  Agreement, a regulator's compliance date, a standard's timeline) are not, unless the company commits
  itself to them in the statement.
- It is forward-looking at the time of the report: the deadline is later than the report year, or it is
  the stated target for the coming period ("Target for FY2025" in an FY2024 report). A target for the
  report year itself counts only when it is plainly stated as a target rather than as a result.
- It names or clearly implies a deadline year.

Not targets: results already achieved, descriptions of what was done in the report year, intentions
with no year, years that only name the reporting period, and table headers.

Reply with one JSON object and nothing else: {"targets": [ ... ]}. Use an empty list when there is none.
Each target has:

- "target_text": the part of the statement that states it, copied verbatim
- "metric": what is targeted, a short noun phrase in the statement's own words, without the number or
  the year (e.g. "Scope 1 and 2 GHG emissions", "water intensity", "workplace fatalities",
  "ISPO certification of mills", "Scope 3 emissions inventory")
- "category": one of: resource optimisation, waste management, emissions control, ecological
  conservation, workplace, outreach, management, business compliance, worker & consumer safety
  compliance, data and cybersecurity protection
- "direction": "reduce", "increase", "maintain" or "achieve"
- "quantity": the number as written (15 for "15%", 0 for "zero"), or null
- "unit": "%", "tCO2e", "MWp", "incidents", "hours", ... or null
- "baseline_year": the year the change is measured from, or null
- "target_year": the calendar or financial year the deadline falls in, as an integer (FY2025 -> 2025;
  "FY2024/25" -> 2025)
- "kind": "quantitative" (a number to reach), "milestone" (a dated deliverable: complete, obtain,
  launch, publish) or "qualitative" (a dated intention with no measurable end state)
- "recurring": true when it is an every-year target restated annually ("zero incidents each year",
  "maintain 100% compliance"), otherwise false

A statement may hold several targets; return each separately.

## user

Company: {company}
Report year: {year}
Statement: {text}
