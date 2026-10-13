# Promise fulfilment and stock prices: a literature screen

Written 2026-09-14. Trigger: supervisor feedback suggested highlighting fulfilled / unfulfilled promises as
case studies and "probably" testing whether fulfilment correlates with stock price. This note records a
targeted screen (three parallel searches: prior evidence, inference methodology, Singapore evidence and data)
and the design it supports. Tags: [full] full text or key sections read, [abs] abstract only,
[unverified] snippet or inference. Numbers are as reported by the screen and must be spot-checked before
they go into the report.

## 1. Verdict

- **Case studies and descriptive fulfilment statistics: do it.** It is RQ2 with a sharper taxonomy, and no
  SGX study checks whether earlier sustainability commitments were met.
- **Stock-price analysis: only as a clearly labelled exploratory section.** The prior is a small or null
  effect, the only detected short-window effect needed thousands of events, and our checkable promise sample
  covers roughly 20–28 firms. A null result is the expected outcome and says nothing about "no effect".
- **Do not let it compete with RQ1/RQ2 for time.**

## 2. What the prior evidence says

| Work | Setting | Finding relevant to us | Tag |
|---|---|---|---|
| Jiang, Kim & Lu 2025, *Nature Climate Change* 15:279 | CDP, 1,041 firms, 1,541 targets ending 2020 | Targets coded **achieved / failed / disappeared**; 31 % of firms' targets disappeared. **No significant market reaction to failed targets** (report-release CAAR [-1,3] -0.127 %, n.s.); only media-amplified cases fell (-4 % to -6 %). Disappearing was penalised less than admitting failure | [full] WP |
| Bauer, Huber, Offner & Wilms, FRBSF WP 2024-36 | US, 7,166 pledge events, 995 firms | Pledges +0.14–0.34 % (daily), only for ambitious or specific pledges; GPT-4 pledge labels, 91 % human agreement | [full] intro |
| Ko & Prakash 2024, *npj Climate Action* 3:69 | S&P 500 SBTi tiers | No abnormal returns for any tier | [full] |
| Guerrero-Escobar et al. 2025, *Global Finance J.* 67 | Global SBTi, 1,379 firms | No return effect; volatility falls in some countries | [abs] |
| Desai, Lam, Li & Rajgopal 2023, *Management Science* 69(6) | 69 US oil & gas | Net-zero pledges without governance links get a more negative reaction | [abs] |
| Bolton & Kacperczyk, *Management Science* 72(3), NBER w31244 | 17,385 firms | >60 % of committing firms are behind on targets; returns not an outcome | [full] |
| Bingler et al. 2022 *FRL*; 2024 *JBF* 164 | TCFD supporters; MSCI World | ClimateBERT "cheap talk" relates to negative news and emissions growth, not tested on returns | [abs] |
| Wan et al. 2024, *HSSC* 11:1008 | China, 5,297 firm-years | CSR say-do gap raises crash risk; only 10 % significance with firm FE | [full] |
| Friede et al. 2015; Whelan et al. 2021 (meta) | ~2,200 / 1,000+ studies | ESG–performance mostly non-negative, but only 26 % of disclosure-only studies positive vs 53 % for performance measures | [abs] / [full] |

Singapore: Loh, Thomas & Wang 2017 (*Sustainability* 9:2112; 502 SGX firms, one pre-mandate cross-section,
reporting quality positively related to market value) [full]; Chen 2024 (*JAAR* 25(3); market reaction to first
mandatory SGX sustainability reports) [abs]; Hardiningsih et al. 2024 (87 SGX firms, disclosure and firm
value) [abs]; Phutthadet & Akartwipart 2026 (*JRFM*; 43 Thai/SG REITs, 215 REIT-years: disclosure relates to
lower risk, not returns, and the effect vanishes with year FE) [abs]. NUS CGS–SGX reviews: in 2023 only 12 %
of 535 issuers had transition plans and about half of those lacked quantitative, time-bound targets.
**None tests fulfilment of earlier promises**, which is the gap we can claim.

## 3. Our sample, measured

Regex estimate over the 108,948 parsed statements (noisy, sentence text only; table targets are missed):
613 future-dated target statements from 46 firms; **182 unique statements with a target year ≤ 2025** (so
checkable inside the corpus) from **28 firms**, 20 of them with ≥3. The modal target year is 2030 (188),
which the corpus cannot resolve.

Power, illustrative (80 % power, 5 % two-sided, MDE ≈ 2.8 SE): a firm-level correlation over ~28 firms needs
|r| ≈ 0.5; a 3-day CAR comparison of 100 vs 100 events needs about 1.7 %. Both are far above any effect in
section 2. Bartholdy, Olson & Peare (2007, small exchanges) put the floor at ≥25 events and warn that effects
below ~1–2 % are undetectable with thinly traded stocks [full, WP abstract].

## 4. Design, if we run it

**4.1 Fulfilment coding (the part that matters most).** Adopt Jiang, Kim & Lu's taxonomy per promise:
*achieved* (later implemented statement or metric meeting the target), *failed* (target year passed, evidence
of a miss), *disappeared* (target no longer mentioned), *revised* (target or baseline moved), *ongoing*
(target year not reached). Promise = planning statement with a target year and, where present, a quantity and
baseline (M3 structured targets).

**4.2 Labels for the statistics.** At ~180 checkable promises, **human-verify all of them** instead of
correcting model labels statistically. If the analysis grows to every target (including tables), label a
random or stratified subset with recorded inclusion probabilities and use design-based supervised learning
(Egami et al., NeurIPS 2023, `dsl` package supports fixed effects) or prediction-powered inference
(Angelopoulos et al., *Science* 2023; PPI++). Reason: regressions on ML-generated variables are biased, with
a possibly unknown sign (Battaglia et al., arXiv 2402.15585) [full]; in Egami et al.'s simulation, using
surrogate labels directly at 90 % accuracy gave 95 % CIs that covered the truth only 40 % of the time [full].

**4.3 Tests (pre-specify, report all).**
- H1 (short window): CAR[-1,+1] around the SGXNet release of the year t+1 report is lower for firms whose
  year-t promises failed or disappeared than for firms that achieved them. Market model with Scholes–Williams or
  Dimson betas, trade-to-trade returns; Corrado rank test and Kolari–Pynnönen adjusted BMP (reports cluster in
  the same weeks). Flag that the sustainability report is usually released with the annual report.
- H2 (annual): firm-level fulfilment rate vs 12-month market-adjusted buy-and-hold return after the report,
  controls for log size, book-to-market (REIT dummy), leverage, ROA, prior 12-month return, year and broad
  sector FE; firm-clustered SEs plus wild cluster bootstrap (Petersen 2009; Cameron, Gelbach & Miller 2008).
- Report CIs and MDEs, Holm or Benjamini–Hochberg across specifications, "associational and exploratory".

**Do not attempt:** long-horizon BHAR or calendar-time alphas, firm FE (fulfilment barely varies within a
firm), sector subgroup splits, causal or "fulfilment premium" language, return prediction from text. Realised
2020–2025 green returns reflect climate-concern shocks rather than expected returns (Pástor, Stambaugh &
Taylor 2022, *JFE*) [abs].

**4.4 Data path.**
- Prices, dividends, adjustment factors: NTU S&P Capital IQ Pro (Excel plug-in) or WRDS if NTU subscribes to
  Compustat Global security daily (covers delisted firms) [unverified]; Bloomberg in the Business Library for
  spot checks. yfinance only for prototyping (Yahoo ToS bars automated collection; non-US data error-prone).
- Report release dates: record by hand from SGXNet for the ~28 firms, or take filing dates from Capital IQ.
- Benchmark and factors: FTSE ST All-Share total return (STI as robustness), MAS T-bill yield as risk-free,
  JKP Global Factors for Singapore (CC BY-NC 4.0), Ken French Asia Pacific ex Japan as USD robustness.

## 5. Compliance flag

The screen reports that SGX's website terms, including AI-specific terms, forbid extracting SGX content for
ML or "any other form of data analysis software". We could not confirm the wording ourselves (the page renders
client-side). Three kept reports were downloaded from `links.sgx.com` (SGX Group 2025, VICOM 2023, Tritech
2024); the other 237 came from company IR sites. Replace those three with company-hosted copies, and do not
bulk-scrape SGXNet for release dates.

## 6. Sources

Jiang, Kim & Lu 2025 https://www.nature.com/articles/s41558-024-02236-3 ·
Bauer et al. https://www.frbsf.org/wp-content/uploads/wp2024-36.pdf ·
Ko & Prakash 2024 https://www.nature.com/articles/s44168-024-00148-8 ·
Guerrero-Escobar et al. 2025 https://ideas.repec.org/a/eee/glofin/v67y2025ics1044028325000924.html ·
Desai et al. 2023 https://pubsonline.informs.org/doi/10.1287/mnsc.2023.4765 ·
Bolton & Kacperczyk https://www.nber.org/papers/w31244 ·
Bingler et al. 2024 https://ideas.repec.org/a/eee/jbfina/v164y2024ics0378426624001080.html ·
Wan et al. 2024 https://www.nature.com/articles/s41599-024-03521-4 ·
Whelan et al. 2021 https://www.stern.nyu.edu/sites/default/files/assets/documents/NYU-RAM_ESG-Paper_2021.pdf ·
Loh, Thomas & Wang 2017 https://doi.org/10.3390/su9112112 ·
Chen 2024 https://doi.org/10.1108/JAAR-02-2023-0060 ·
Battaglia et al. https://arxiv.org/abs/2402.15585 ·
Egami et al. https://arxiv.org/abs/2306.04746 ·
Angelopoulos et al. https://www.science.org/doi/10.1126/science.adi6000 ·
Ludwig, Mullainathan & Rambachan https://arxiv.org/abs/2412.07031 ·
Bartholdy, Olson & Peare 2007 https://pure.au.dk/ws/files/321/F_2006_03.pdf ·
Kolari & Pynnönen 2010 https://ideas.repec.org/a/oup/rfinst/v23y2010i11p3996-4025.html ·
Petersen 2009 https://www.nber.org/papers/w11280 ·
Harvey, Liu & Zhu 2016 https://www.nber.org/papers/w20592 ·
Pástor, Stambaugh & Taylor 2022 https://ideas.repec.org/a/eee/jfinec/v146y2022i2p403-424.html ·
CGS–SGX Climate Reporting Review 2024 https://bschool.nus.edu.sg/cgs/wp-content/uploads/sites/145/2025/03/CGS_SGX_Climate-Reporting-Review-2024_Report.pdf ·
JKP factors https://jkpfactors.com
