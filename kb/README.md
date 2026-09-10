# kb/ — local corpus of SGX sustainability reports

**Academic use only, for the AI6127 course project.**

- Every report in `raw/` is published by, and remains the copyright of, the company that issued it. This project claims no ownership of any report.
- These files are **not redistributed**. `kb/` is git-ignored and must never be committed, uploaded, shared or published anywhere. If the project submission needs a knowledge base, it may contain only derived artefacts, such as chunk text for retrieval, metadata and source URLs, and only as far as the course requires.
- Each file's source URL and fetch date are recorded in `manifest.csv`, so provenance can always be traced.

## Corpus at a glance (collected 2026-09-10)

| | |
|---|---|
| Reports kept | **240** |
| Issuers | **56** SGX-listed companies / REITs / trusts |
| Reporting years | 2020–2025 (38 / 38 / 40 / 43 / 43 / 38 per year) |
| Issuers with ≥3 years | 41 (29 with all six years), which supports the cross-year experiments |
| Pages / words | 10,635 pages / 3,475,125 words |
| Approx. chunks | ~11.6k at 300 words, ~17.4k at 200 words (course minimum: 10k) |
| Disk | ~1.2 GB |

## Layout

```
kb/
├── README.md        this file
├── manifest.csv     one row per candidate document: kept / rejected / skipped, with the reason
├── _collect.log     collection log
└── raw/<company>/<year>_<sha256[:8]>.pdf
```

## Sources

| Origin | Kept | How the files were obtained |
|---|---|---|
| `listedcompany.com` | 229 | The company's own investor-relations site on the shared IR platform. Its `robots.txt` allows all generic crawlers. Requests were rate-limited to at most 1 per second per host. |
| `pilot` | 11 | Downloaded one at a time from company IR sites or SGXNet (`links.sgx.com`) during the feasibility pilot. |

SustainabilityReports.com was used **only** to discover which reports exist, via its public sitemap. No file was downloaded from it, because its terms prohibit mass downloading and scraping.

## Filtering

Every rejected or skipped document stays in `manifest.csv` with its reason, so the filter can be audited and re-tuned.

1. **URL year pre-filter.** If the URL shows a year outside 2019–2026, skip without downloading — `url_year_out_of_scope`.
2. **Exact duplicates.** Drop repeats by SHA-256 — `duplicate`.
3. **Text layer.** Reject when the whole document has fewer than 500 words (scanned or image-only) — `no_text_layer`. These could be recovered later with OCR.
4. **Length.** Reject documents under 8 pages, which are usually announcement cover letters — `too_short`.
5. **Language.** Reject when more than 20 % of the characters on the first pages are CJK or Thai (non-English editions) — `non_english`.
6. **AGM notices and circulars.** Reject documents whose opening pages match `notice of annual/extraordinary general meeting`, `proxy form` or `circular to shareholders/unitholders` — `agm_notice_or_circular`.
7. **Full annual reports.** Reject when page 1 says `annual report` but does not mention `sustainab` — `annual_report`.
8. **Other document types.** Reject GRI content indexes, appendices, performance-data books, standalone TCFD / IFRS S2 reports, corporate-governance reports, constitutions, policies and financing frameworks — `other_document_type`. The rule looks **only** at the filename and the first 12 words of the title page, and never fires when the document names itself a sustainability report. Contents pages of real reports routinely list "GRI Content Index", "TCFD" or "Appendix", so the body text is deliberately ignored here.
9. **Is it a sustainability report?** Keep only when the first 10 pages contain `sustainability report/statement` or `ESG report`, or the opening pages contain both `sustainability` and `report`. Letter-spaced covers such as `R E P O R T 2 0 2 1` are collapsed before matching — `not_sustainability_report`.
10. **Reporting year.** The year is the calendar year in which the reporting period **ends** (e.g. FY Apr 2023–Mar 2024 → 2024; "July 2024 – June 2025" → 2025). Sources are tried in order:
    1. an explicit year in the filename (`sr2021`, `FY2020-21`, `Sustainability_Report_2025`);
    2. a split fiscal year or month range in the title (`2023/24`);
    3. the year in the text (`Sustainability Report 2023`, `FY2023`, `financial year ended … 2023`);
    4. the publication date in the URL.

    Keep only 2020–2025 — `year_out_of_scope`.
11. **One per company-year.** When several documents survive for the same company and year (revised editions, GRI/TCFD supplements), keep the one with the most words — `same_company_year_duplicate`.

## Manual verification

- Every change made by the final consolidation pass was reviewed by hand, including year shifts for Stamford Land, SunMoonFood, Venture and ThaiBev, and the restored reports.
- A random sample of 15 kept reports was checked: all 15 are genuine sustainability reports of the named issuer with a plausible year.
- ThaiBev publishes English and Thai editions; only the English editions are kept.
