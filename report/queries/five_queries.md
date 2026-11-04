# Five example queries, timed

Median of three calls after a warm-up call, k = 5, statement store `d8a62bfe40c6`. Dense and hybrid include the query embedding call; hybrid+rerank adds the cross-encoder.

| query | filter | bm25 ms | dense ms | hybrid ms | hybrid+rerank ms | top hit (hybrid+rerank) |
|---|---|---|---|---|---|---|
| Q1 Scope 3 greenhouse gas emissions reporting | Gallant Venture, 2022–2025 | 3.8 | 19.2 | 23.3 | 571.6 | Gallant Venture 2023 p.26: Disclose Scope 1, 2, and, if appropriate, Scope 3 greenhouse gas (GHG) emissions and the related risks.… |
| Q2 100% ISPO certification of mills and estates | Indofood Agri, 2021–2025 | 2.3 | 20.5 | 23.5 | 430.0 | Indofood Agri 2024 p.43: Sustainability certification of all estates’ hectarage is ISPO certified of nucleus CPO production is ISPO certified 89%… |
| Q3 electricity consumption per square foot target | Old Chang Kee, 2021–2025 | 2.9 | 19.3 | 22.3 | 130.1 | Old Chang Kee 2021 p.14: Our target is to maintain or lower our electricity consumption (kwh) per square foot in FY2022.… |
| Q4 solar rooftops installed at distribution centers | ThaiBev, 2023–2025 | 2.4 | 20.5 | 21.0 | 180.9 | ThaiBev 2023 p.169: In 2023, ThaiBev installed solar rooftops at two distribution centers in Nakhon Ratchasima and Surat Thani.… |
| Q5 commitment to achieve net zero emissions by 2050 | any company, —–— | 20.2 | 22.4 | 44.6 | 125.4 | ThaiBev 2025 p.31: In this context, Thailand has committed to achieving Net-Zero greenhouse gas emissions by 2050.… |

## Q1 · Scope 3 greenhouse gas emissions reporting (cross-year aspect lookup)
- **bm25** (3.8 ms):
  - Gallant Venture 2022 p.34: Disclose Scope 1, Scope 2, and, if appropriate, Scope 3 greenhouse gas (GHG) emissions, and the related risks.
  - Gallant Venture 2023 p.26: Disclose Scope 1, 2, and, if appropriate, Scope 3 greenhouse gas (GHG) emissions and the related risks.
  - Gallant Venture 2022 p.5: We also extended our greenhouse gas (“GHG”) inventory to include Scope 2 emissions.
- **dense** (19.2 ms):
  - Gallant Venture 2023 p.26: We are looking into incorporating several Scope 3 GHG emission categories into our subsequent reports.
  - Gallant Venture 2024 p.27: We are exploring including several Scope 3 GHG emission categories in our future reports.
  - Gallant Venture 2023 p.26: Disclose Scope 1, 2, and, if appropriate, Scope 3 greenhouse gas (GHG) emissions and the related risks.
- **hybrid** (23.3 ms):
  - Gallant Venture 2022 p.34: Disclose Scope 1, Scope 2, and, if appropriate, Scope 3 greenhouse gas (GHG) emissions, and the related risks.
  - Gallant Venture 2023 p.26: Disclose Scope 1, 2, and, if appropriate, Scope 3 greenhouse gas (GHG) emissions and the related risks.
  - Gallant Venture 2022 p.5: We also extended our greenhouse gas (“GHG”) inventory to include Scope 2 emissions.
- **hybrid+rerank** (571.6 ms):
  - Gallant Venture 2023 p.26: Disclose Scope 1, 2, and, if appropriate, Scope 3 greenhouse gas (GHG) emissions and the related risks.
  - Gallant Venture 2025 p.27: Disclose Scope 1, Scope 2, and, if appropriate, Scope 3 greenhouse gas (“GHG”) emissions, and the related risks.
  - Gallant Venture 2025 p.28: To address these developments, the Group plans to: Develop a centralised emissions monitoring system covering Scope 1 and Scope 2 emissions, with progressive inclusion of Scope 3 emissions; Strengthen
- graph joins on the top hit: aspects 0 (12.8 ms), follow-ups 0 (12.6 ms)
- related dated targets: 0 (33.7 ms)

## Q2 · 100% ISPO certification of mills and estates (promise follow-up inside the deadline window)
- **bm25** (2.3 ms):
  - Indofood Agri 2025 p.45: In this section UPDATES FOR 2025 Sustainability certification 89% of all nucleus estates’ hectarage production is ISPO certified 85% of nucleus CPO production is ISPO certified Supply chain traceabili
  - Indofood Agri 2023 p.40: of all estates’ hectarage is ISPO certified of nucleus CPO production is ISPO certified Sustainability certification In this section Supply chain traceability and transparency of FFB processed in mill
  - Indofood Agri 2023 p.15: As a demonstration of our dedication to responsible sourcing, we aim to achieve 100% ISPO certification for all our mills and nucleus estates by the end of 2024.
- **dense** (20.5 ms):
  - Indofood Agri 2023 p.40: of all estates’ hectarage is ISPO certified of nucleus CPO production is ISPO certified Sustainability certification In this section Supply chain traceability and transparency of FFB processed in mill
  - Indofood Agri 2021 p.30: Responsible sourcing Material topics Goal/target Progress in 2021 Sustainability Certification By end 2023: ISPO certification for all estates Achieved 83% of targeted hectarage* By end 2023: ISPO cer
  - Indofood Agri 2022 p.5: Currently, 86% of our estates are ISPO certified, along with 20 of 27 mills and 84% of nucleus CPO production.
- **hybrid** (23.5 ms):
  - Indofood Agri 2023 p.40: of all estates’ hectarage is ISPO certified of nucleus CPO production is ISPO certified Sustainability certification In this section Supply chain traceability and transparency of FFB processed in mill
  - Indofood Agri 2025 p.45: In this section UPDATES FOR 2025 Sustainability certification 89% of all nucleus estates’ hectarage production is ISPO certified 85% of nucleus CPO production is ISPO certified Supply chain traceabili
  - Indofood Agri 2021 p.30: Responsible sourcing Material topics Goal/target Progress in 2021 Sustainability Certification By end 2023: ISPO certification for all estates Achieved 83% of targeted hectarage* By end 2023: ISPO cer
- **hybrid+rerank** (430.0 ms):
  - Indofood Agri 2024 p.43: Sustainability certification of all estates’ hectarage is ISPO certified of nucleus CPO production is ISPO certified 89% 84% of FFB processed in mills is traceable to estates of CPO processed in refin
  - Indofood Agri 2021 p.11: As part of our commitment to responsible sourcing, we aim to have 100% of our mills and estates ISPO certified by 2023.
  - Indofood Agri 2025 p.45: In this section UPDATES FOR 2025 Sustainability certification 89% of all nucleus estates’ hectarage production is ISPO certified 85% of nucleus CPO production is ISPO certified Supply chain traceabili
- graph joins on the top hit: aspects 0 (5.0 ms), follow-ups 0 (3.9 ms)
- related dated targets: 0 (0.7 ms)

## Q3 · electricity consumption per square foot target (annual target and its result)
- **bm25** (2.9 ms):
  - Old Chang Kee 2021 p.14: For FY2021, our electricity consumption was 61 kwh per square foot (FY2020: 68 kwh per square foot).
  - Old Chang Kee 2023 p.14: For FY2023, our electricity consumption was 66 kwh per square foot (FY2022: 69 kwh per square foot).
  - Old Chang Kee 2022 p.14: For FY2022, our electricity consumption was 69 kwh per square foot (FY2021: 61 kwh per square foot).
- **dense** (19.3 ms):
  - Old Chang Kee 2021 p.14: Our target is to maintain or lower our electricity consumption (kwh) per square foot in FY2022.
  - Old Chang Kee 2022 p.14: For FY2022, our electricity consumption was 69 kwh per square foot (FY2021: 61 kwh per square foot).
  - Old Chang Kee 2021 p.14: For FY2021, our electricity consumption was 61 kwh per square foot (FY2020: 68 kwh per square foot).
- **hybrid** (22.3 ms):
  - Old Chang Kee 2021 p.14: For FY2021, our electricity consumption was 61 kwh per square foot (FY2020: 68 kwh per square foot).
  - Old Chang Kee 2021 p.14: Our target is to maintain or lower our electricity consumption (kwh) per square foot in FY2022.
  - Old Chang Kee 2022 p.14: For FY2022, our electricity consumption was 69 kwh per square foot (FY2021: 61 kwh per square foot).
- **hybrid+rerank** (130.1 ms):
  - Old Chang Kee 2021 p.14: Our target is to maintain or lower our electricity consumption (kwh) per square foot in FY2022.
  - Old Chang Kee 2022 p.14: Our target is to maintain or lower our electricity consumption (kwh) per square foot in FY2023 as compared to FY2022.
  - Old Chang Kee 2023 p.14: Our target for FY2024 is to maintain or lower our electricity consumption (kwh) per square foot in FY2024 as compared to FY2023.
- graph joins on the top hit: aspects 1 (10.8 ms), follow-ups 0 (4.0 ms)
- related dated targets: 0 (0.6 ms)

## Q4 · solar rooftops installed at distribution centers (milestone with named sites)
- **bm25** (2.4 ms):
  - ThaiBev 2023 p.169: In 2023, ThaiBev installed solar rooftops at two distribution centers in Nakhon Ratchasima and Surat Thani.
  - ThaiBev 2023 p.169: In 2024, ThaiBev plans to install solar rooftops at two additional distribution centers in Chon Buri and Pathum Thani provinces.
  - ThaiBev 2023 p.39: In 2023, ThaiBev started Phase 4 to expand solar panel installation to cover all business groups in Thailand, with solar rooftops and floating solar panels to be installed at the breweries and non-alc
- **dense** (20.5 ms):
  - ThaiBev 2023 p.169: In 2023, ThaiBev installed solar rooftops at two distribution centers in Nakhon Ratchasima and Surat Thani.
  - ThaiBev 2023 p.169: In 2024, ThaiBev plans to install solar rooftops at two additional distribution centers in Chon Buri and Pathum Thani provinces.
  - ThaiBev 2023 p.39: Solar System Project The solar system project’s phases 1–3 cover the installation of solar rooftops and floating solar panels at the spirits factories, breweries, non-alcoholic beverage factories, and
- **hybrid** (21.0 ms):
  - ThaiBev 2023 p.169: In 2023, ThaiBev installed solar rooftops at two distribution centers in Nakhon Ratchasima and Surat Thani.
  - ThaiBev 2023 p.169: In 2024, ThaiBev plans to install solar rooftops at two additional distribution centers in Chon Buri and Pathum Thani provinces.
  - ThaiBev 2023 p.39: Solar System Project The solar system project’s phases 1–3 cover the installation of solar rooftops and floating solar panels at the spirits factories, breweries, non-alcoholic beverage factories, and
- **hybrid+rerank** (180.9 ms):
  - ThaiBev 2023 p.169: In 2023, ThaiBev installed solar rooftops at two distribution centers in Nakhon Ratchasima and Surat Thani.
  - ThaiBev 2023 p.169: In 2024, ThaiBev plans to install solar rooftops at two additional distribution centers in Chon Buri and Pathum Thani provinces.
  - ThaiBev 2023 p.169: Moving forward, ThaiBev will continue to increase the proportion of corporate electric vehicles as one of the key initiatives to achieve net-zero emission by 2040 (Scopes 1 and 2). - At Lampang region
- graph joins on the top hit: aspects 0 (4.7 ms), follow-ups 0 (3.8 ms)
- related dated targets: 0 (1.1 ms)

## Q5 · commitment to achieve net zero emissions by 2050 (generic, no company filter (templated ESG prose))
- **bm25** (20.2 ms):
  - Suntec Reit 2023 p.28: As part of our commitment towards achieving longterm sustainable development, in FY 2023, the Manager launched its Net-Zero roadmap, highlighting our plans to achieve our target of net-zero carbon emi
  - VICOM Ltd 2023 p.42: In line with the Paris Agreement, Singapore aims to achieve net-zero emissions by 2050.
  - Uni-Asia Grp 2025 p.18: In Japan, “Beyond Zero” is a roadmap that calls for the country to achieve net zero GHG emissions by 2050.
- **dense** (22.4 ms):
  - Abundance International 2024 p.27: Reach net-zero emission by 2050.
  - FSL Trust 2025 p.21: Reach net-zero emissions by 2050.
  - Venture 2024 p.17: In Malaysia3 and China4, commitments have been made to reach carbon neutrality by 2050 and 2060 respectively.
- **hybrid** (44.6 ms):
  - VICOM Ltd 2023 p.42: In line with the Paris Agreement, Singapore aims to achieve net-zero emissions by 2050.
  - FSL Trust 2025 p.21: Reach net-zero emissions by 2050.
  - CSE Global 2025 p.17: Aligned with the Singapore Green Plan positioning Singapore to achieve its 2050 net zero emissions goal, we are committed to contributing to Singapore’s national agenda on sustainable development and 
- **hybrid+rerank** (125.4 ms):
  - ThaiBev 2025 p.31: In this context, Thailand has committed to achieving Net-Zero greenhouse gas emissions by 2050.
  - CSE Global 2025 p.17: Aligned with the Singapore Green Plan positioning Singapore to achieve its 2050 net zero emissions goal, we are committed to contributing to Singapore’s national agenda on sustainable development and 
  - Centurion 2025 p.3: The Group has articulated a long-term ambition to achieve Net Zero Scope 1 and Scope 2 greenhouse gas (“GHG”) emissions by 2050.
- graph joins on the top hit: aspects 0 (5.0 ms), follow-ups 0 (3.9 ms)
