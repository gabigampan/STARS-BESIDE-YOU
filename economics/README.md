# Economic analysis: testing on Earth analogs vs. testing in space

**Project:** Planetary twin finder · **Team:** Stars Beside You · NASA Space Apps Challenge 2026 (Málaga)
**Author of the economic analysis:** Facundo Casalanguida (economics/data)

This folder holds the economic part of the project: how much it costs to test hardware (rovers, solar arrays, drills) at terrestrial analog sites compared with testing it on the Moon or Mars, and why a tool that finds better analogs is worth paying for. It is an English translation of the team's original Spanish materials. All figures, sources and URLs are kept as they appear in the originals; only number formatting was changed to English conventions (decimal point, comma as thousands separator).

## Key results

- **Testing in space costs 3 to 40 times more.** Testing a rover, a solar array or a drill on the Moon or Mars costs between 3 and 40 times more than building and testing it on Earth, according to the documented space–Earth pairs.
- **TRIDENT drill, the only direct pair.** The CLPS delivery of the PRIME-1 TRIDENT drill to the Moon cost 50 M$; manufacturing and testing the same flight drill on Earth cost 7.6 M$ (7,608,630 USD): ratio ×6.6. The lunar demonstration was not completed because the lander tipped over.
- **Space tests fail too.** Of NASA's first four commercial lunar flights (CLPS), only one (Blue Ghost) was fully successful. On Mars, 31 % of the surface elements launched since 1990 failed (5 of 16). At the CLPS rate (1 in 4), each valid lunar TRIDENT test comes to about 200 M$, between 13 and 26 times the Earth cost.
- **Late fixes are expensive.** Fixing an error discovered in operations costs between 29 and 1,615 times what it costs in the requirements phase, versus 21–78 times if it is detected in testing (Stecklein et al., NASA, 2004).
- **Break-even threshold q\* of 0.1–1 %.** With p₀ = 31.25 % and a 1.6 M$ analog campaign (Nomad rover, Atacama, 1997), the test pays for itself if it detects 0.13 % of failures on a Curiosity-type mission (4,021 M$ in 2025 dollars), 0.37 % on InSight or 0.84 % on Pathfinder. If it detected 10 %, it would avoid about 124 M$ of expected loss on a Curiosity-type mission.
- **Entry price on the Moon.** Public rates to land cargo on the lunar surface are around 0.85–1.5 M$ per kg. The 1.2 M$ for 1 kg at Astrobotic's rate would pay for a week in a NASA vacuum chamber (≈58 k$, estimated) about 20 times.

## Method

1. **Data collection.** Costs of space technology demonstrations, Earth tests, analog campaigns and robotic missions to the Moon and Mars, each with its source URL and a `verified` flag (yes = page opened and figure found; no = search excerpt only).
2. **Space–Earth pairs.** Eight pairs comparing the cost of testing an artifact in space with testing it (or a close equivalent) on Earth. Only TRIDENT is a direct pair; the rest are labeled proxy or estimate.
3. **Decision model (expected value of information).**
   - Expected cost without testing: E₀ = C_M + p₀·C_M
   - Expected cost with an Earth test: E₁ = C_T + C_M + p₀·(1 − q)·C_M
   - Net savings: ΔE = p₀·q·C_M − C_T
   - Break-even threshold: q\* = C_T / (p₀·C_M)
   - Earth vs. space with the same detection: savings = C_T^space/(1 − p_T) − C_T^Earth
   - Finder indicator: similarity per euro = s / C_T(s)

   C_M is the mission cost, p₀ the probability of failure, q the fraction of failures the test detects, C_T the cost of the test, p_T the probability that the space test itself fails and s the analog's similarity. The mission's scientific value is ignored, so the calculation is conservative.
4. **Theory.** Cost-effectiveness analysis, expected value of information (Raiffa and Schlaifer, 1961; Howard, 1966), real options (Dixit and Pindyck, 1994), economies of scope, learning curves (Wright, 1936) and error-cost escalation (Stecklein et al., 2004). Full derivation in `theoretical_framework.md`.
5. **Dashboard model.** A separate scenario model (`dashboard/`) compares one lunar delivery with one field campaign at nine Earth analog sites at official rates, with a 20,000-draw Monte Carlo (seed 42), a tornado analysis and an independent verification.

## In this repository

This folder is part of the Stars Beside You repository; the main [README](../README.md) explains the web app and the analog pairs. The economics answer the question the app raises: is it worth finding better Earth analogs? Errata fixed in the text of the original materials are listed in [ERRATA.md](ERRATA.md), and [SHA256SUMS.txt](SHA256SUMS.txt) holds the checksum of every delivered file.

## Files

| File | Content |
|---|---|
| `Economic_feasibility_Earth_vs_space_testing.pdf` | 4-page report with the thesis, data, charts, model and limits |
| `Space_testing_cost_data.xlsx` | All datasets in one workbook (17 sheets) |
| `theoretical_framework.md` | Notation, equations, numerical example, supporting theory, macro context, gaps |
| `demos_summary.md` | Technology demonstrations in space vs. Earth tests |
| `missions_summary.md` | Costs and outcomes of robotic Moon and Mars missions |
| `earth_tests_summary.md` | Cost of Earth testing and analogs, failures that ground testing could have caught |
| `data/*.csv` | 19 source datasets (UTF-8, comma separator, decimal point) |
| `dashboard/README.md`, `dashboard/DASHBOARD_GUIDE.md` | How the dashboard model works and how to present it |
| `dashboard/outputs/` | Model outputs (CSV/JSON), `ASSUMPTIONS.md`, `VERIFICATION.md` |
| `report_src/charts_en.py`, `report_src/pdf_en.py`, `report_src/g*.png` | Scripts and charts that generate the PDF (matplotlib, reportlab) |

Original Spanish file names, for reference: `space_earth_pairs.csv` = `pares_espacio_tierra.csv`, `space_demos.csv` = `demos_espacio.csv`, `earth_tests.csv` = `pruebas_tierra.csv`, `missions.csv` = `misiones.csv`; each `macro_*.csv` keeps its subject (for example `macro_illustrative_savings_model.csv` = `macro_modelo_ilustrativo_ahorro.csv`).

## Main data sources

- NASA OIG IG-24-013, CLPS initiative: https://oig.nasa.gov/wp-content/uploads/2024/06/final-report-ig-24-013-nasas-commercial-lunar-payload-services-initiative.pdf
- PRIME-1 / TRIDENT contracts, SAM.gov and GovTribe: https://sam.gov/opp/533e5147817945e0994c5634d9956983/view ; https://govtribe.com/award/federal-contract-award/purchase-order-80ksc020p0021
- The Planetary Society, Science Mission Impact dataset (CC BY 4.0): https://dashboards.planetary.org/science-mission-impact/data/exports/planetary-missions.csv
- Stecklein et al. 2004, error cost escalation (NTRS 20100036670): https://ntrs.nasa.gov/api/citations/20100036670/downloads/20100036670.pdf
- Astrobotic Payload User Guide: https://www.astrobotic.com/wp-content/uploads/2022/01/PUGLanders_011222.pdf
- NASA–Sandia agreement SAA-EA-23-39178 (JSC vacuum chamber): https://www.nasa.gov/saa/domestic/39178_SAA-EA-23-39178_Sandia_FINAL_Signed_2024-05-22.pdf
- NASA Ames press release 97-50 (Nomad, Atacama): https://www.cs.cmu.edu/afs/cs/project/lri-13/www/atacama-trek/media_coverage/NASA_Ames_press_rel.html
- GAO-20-405: https://www.gao.gov/assets/gao-20-405.pdf
- Wikipedia, List of missions to Mars: https://en.wikipedia.org/wiki/List_of_missions_to_Mars
- Jones 2018 (NASA Ames), launch cost per kg: https://ntrs.nasa.gov/api/citations/20200001093/downloads/20200001093.pdf
- Terzi & Nicoli 2026, PNAS Nexus, launcher learning curve: https://academic.oup.com/pnasnexus/article/5/7/pgag217/8693000
- Pathfinder costs (PMI) and airbags (ILC Dover): https://www.pmi.org/learning/library/pm-techniques-mars-pathfinder-mission-3556 ; https://www.ilcdover.com/en/company/news/how-ilc-dover-helped-pathfinder-land-safely-on-mars

Every row in `data/*.csv` and in the Excel workbook carries its own URL.

## Limitations

- **q has no empirical source.** No study was found that measures what fraction of failures analog tests detect; q is presented as a scenario with sensitivity analysis.
- **Only TRIDENT is a direct pair.** The other pairs are approximate or estimated and are labeled as such.
- **Nominal figures.** Costs are not adjusted for inflation; test costs are nominal and mission costs are in 2025 dollars unless stated. The adjustment does not change the order of magnitude.
- **Search excerpts.** Some per-kg rates and other figures come from search excerpts; they are flagged `verified = no`.
- **No published cost of "the same test" on the Moon or Mars.** Demonstrator missions and delivery prices are used as proxies.
- **What is solid** is the order of magnitude and the ranking, not the exact figure.
