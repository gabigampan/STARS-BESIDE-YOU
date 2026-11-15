# Cost of testing rovers and space hardware on Earth: summary with sources

For the NASA Space Apps 2026 project: terrestrial analogs of the Moon and Mars, ranked by similarity per euro of testing.

Full data in `data/earth_tests.csv`: 49 rows, comma separator, decimal point and UTF-8 encoding.
- `verified = yes` means the page was opened and the figure is on it.
- `verified = no` means the figure was only seen in a search excerpt or the page could not be opened.

Conversions to euros use the ECB reference rate of 13-11-2026 (1 EUR = 1.1052 USD). They are nominal amounts, not adjusted for inflation. **They are my own estimates, not figures from the sources.**

---

## 1. The essentials for the "similarity per euro" model

| Item | Cost in original currency | ≈ EUR (estimate) | Source |
|---|---|---|---|
| Crew member at MDRS (Utah), 2-week rotation | 3,500 USD (2,000 USD for students) | 3,167 € | Mars Society |
| Crew of 6 at MDRS, 2 weeks (6 × 3,500) | 21,000 USD | 19,001 € | calculated from the fee |
| Typical 10-day mission at Aquarius (NEEMO), external client (FY2019-21) | 209,790 USD | 189,821 € | FIU rate |
| Saturation day at Aquarius, external client | 18,426 USD/day | 16,672 €/day | FIU rate |
| Vibration, TVAC or ADCS bench at HSFL (Hawaii) | 3,500 USD/day | 3,167 €/day | HSFL |
| Vibration campaign (1 week) plus TVAC (2 weeks) at HSFL | 52,500 USD | 47,503 € | calculated with the durations HSFL gives |
| High-fidelity lunar or Mars simulant in bulk (LHS-1 or MGS-1) | 29,250 USD/t | 26,466 €/t | Space Resource Technologies |
| Engineering-grade simulant (LMS-E) | 3,550 USD/t | 3,212 €/t | Space Resource Technologies |
| 200 t lunar test bed at MSFC (volcanic ash plus transport, 2013) | 41,400 USD (≈207 USD/t) | 37,459 € (≈187 €/t) | NASA TM-2013-217497 |
| Three rover campaigns in the Atacama (Hyperion/Zoë), 2003-2005 | 3.0 M USD + 0.9 M USD | ≈3.53 M € | Carnegie Mellon |
| Construction of the FMARS habitat (Arctic, 2000) | 1.3 M USD | ≈1.18 M € | Wikipedia |

### Ideas for the model

1. **Transport.**
   - For bulk regolith, the cost is dominated by transport, not material. At the MSFC test bed, 200 t cost 1,400 USD and moving it from Arizona cost about 40,000 USD. NASA sums it up: "transportation was more than 90 % of the acquisition cost".
   - A natural analog (you go to the terrain) vs. an artificial one (you bring the terrain) changes the model's "euro" by orders of magnitude. Distance and logistics should be included as a variable.
2. **Fidelity.**
   - High-fidelity simulant costs about 8 times more per tonne than engineering grade (29,250 vs. 3,550 USD/t).
   - Road fill costs about 20 USD/t delivered on site.
   - The 2009 NASA document warns that the price per tonne between simulants can vary "by more than a factor of 100".
3. **There are no public rates for NASA's large facilities.**
   - The Plum Brook/Armstrong Space Environments Complex is offered on a "full cost reimbursable" basis.
   - The Aerospace Sourcing guide (updated in 2026) confirms there is no neutral published rate.
   - HSFL's rates are the best public anchor I have found for vibration and TVAC.

---

## 2. Analogs and their cost

### NASA and Mars Society analogs

- **MDRS (Utah).**
  - 3,500 USD per person per 2-week rotation; 2,000 USD for full-time students. The website warns it will probably rise.
  - In 2023-24 it was 1,750 USD per week. This figure is not verified: I only saw it in the search-excerpt PDF.
  - https://reports.marssociety.org/apply-to-become-a-crew-member/
- **FMARS (Devon Island, Canada).** The project cost 1.3 M USD in total in 2000. https://en.wikipedia.org/wiki/Flashline_Mars_Arctic_Research_Station
- **NEEMO / Aquarius (Florida).** External rate FY2019-21:
  - preparation of 25,530 USD per mission;
  - 18,426 USD per saturation day;
  - 4,096 USD per day in 1-ATA mode, useful for testing sensors without saturation.
  - https://environment.fiu.edu/aquarius/training/_assets/day_rates_fy2017-18_external.pdf
  - Current internal rates: 12,111 USD start-up and 11,336 USD per day. https://research.fiu.edu/facilities-and-administrative-costs/facilities/recharge/aquarius-rates/
- **HI-SEAS (Mauna Loa).** New NASA grant of 750,000 USD to reopen the facility (April 2026). https://www.hawaiitribune-herald.com/2026/04/24/hawaii-news/research-could-resume-at-space-simulation-facility-on-mauna-loa/ The 2013 grant of 1.2 M USD is not verified.
- **Atacama (Carnegie Mellon, "Life in the Atacama").**
  - NASA ASTEP grant of 3 M USD over 3 years, plus 0.9 M USD for instruments.
  - The plan was to cover 10 km in 2003, 50 km in 2004 and 200 km in 2005.
  - https://www.cmu.edu/cmnews/030425/030425_lifeseeking.html
- **HERA (NASA JSC).** Crew members are paid about 10 USD per hour (not verified). I have not found the cost per campaign.
- **D-RATS.** There is only a cap of 30,000 USD per investigator (ROSES C.29, not verified). No public total budget.
- **Haughton-Mars Project.** No verifiable figure.

### Test facilities (no public price)

These facilities are only described; none publishes a price:

- **JPL Mars Yard:** more than 2,000 m² of test terrain and 7 slopes of varying incline and cohesion. https://robotics.jpl.nasa.gov/how-we-do-it/facilities/marsyard-iii/
- **Glenn SLOPE:** a 4,368 ft² building with:
  - a 12×3×0.3 m tank of GRC-1;
  - a tilting bed up to 45°;
  - a 12×3×0.6 m sinkage tank.
- **JSC Rock Yard.**

### ESA and Spanish analogs

- **PANGAEA-X in Lanzarote (2017):** 50 people, 4 agencies and 18 organizations. No published cost.
- **ExoMars tests:** ExoFiT in Tabernas (Almería), in October 2018, and in the Atacama, in February 2019. The new test in Tabernas (2026) lasted 8 days, covered 220 m and brought together about 100 people. None has a published cost.
- **MOONWALK (FP7, EU, 2013-2016):** simulations at Río Tinto (Huelva) and underwater off Marseille. The full project cost 3,143,516 €, with an EU contribution of 2,372,660 €. It includes technology development, not only the campaigns. Not verified: I saw it in the CORDIS excerpt. https://cordis.europa.eu/project/id/607346/reporting
- **CNES and ESA analog budgets:** I have not found public figures.

---

## 3. How much testing weighs within a mission

- **Share of AIV in the budget.**
  - Industry literature puts AIV (assembly, integration and verification) at around 35 % of the total program budget (MATED paper by ESA and Thales Alenia Space, 2018). https://ecss.nl/wp-content/uploads/2022/05/ATS-paper_MATED-Improvement-(October-2018).pdf
  - ESA Bulletin 109 (2002) speaks of 20-30 % of the cost and 60-70 % of the schedule. Not verified: the PDF returns 404 and the figure is cited in a Politecnico di Milano thesis.
- **Escalation of the cost of errors (Stecklein et al., NASA 2004).** Fixing a requirements error costs:
  - 1× in the requirements phase;
  - 3-8× in design;
  - 7-16× in manufacturing;
  - **21-78× in integration and test**;
  - **29× to 1,615× in operations** (Tables 12–13; the abstract rounds the upper end to "more than 1,500×").
  - Caveat: the study's sources have been criticized.
  - https://ntrs.nasa.gov/citations/20100036670
- **APL I&T cost model.**
  - I&T is normally estimated as a percentage (wrap factor) on top of hardware.
  - APL fits: I&T cost (thousand USD FY2015) = 30,805·ln(integration points) − 69,164.
  - For small satellites there is a cost "floor", and each additional unit saves on average 23 % of I&T.
  - https://digitalcommons.usu.edu/cgi/viewcontent.cgi?article=4992&context=smallsat
- **"Test like you fly".** NASA explicitly acknowledges that this JPL maxim was not followed with Curiosity's wheels (see section 4).

---

## 4. Failures that Earth testing detected or could have detected

| Mission | Cost | What happened | Role of ground testing |
|---|---|---|---|
| **Mars Polar Lander** (1999) | 165 M USD (plus DS2, 29.6 M USD) | Spurious signals from the legs as they deployed shut down the engine at ~40 m | The deployment test was not repeated after the wiring was fixed. NASA: repeating it "probably would have detected" the fault. Program underfunded by ≥30 %. [LLIS 938](https://llis.nasa.gov/lesson/938), [Science News](https://www.sciencenews.org/article/reviewers-see-red-over-recent-mars-programs) |
| **Schiaparelli** (2016) | no verified figure | The IMU saturated when the parachute opened, the estimated altitude came out negative and the module went into free fall | Insufficiently conservative parachute model; the IMU saturation persistence time was never tested after delivery; the cancelled subsonic test would not have revealed the supersonic problem. [ESA report](https://sci.esa.int/documents/33431/35950/1567260317467-ESA_ExoMars_2016_Schiaparelli_Anomaly_Inquiry.pdf) |
| **Beresheet** (2019) | 100 M USD | IMU reset, computer resets and engine shut down | Many components "never tested in space". Landing drills were cancelled because of workload. [Davidson](https://davidson.org.il/read-experience/en/science-panorama-en/what-happened-beresheet/) |
| **Hakuto-R M1** (2023) | 90 M USD (not verified) | The software discarded valid altitude data when passing a crater rim | The simulations did not properly incorporate the route's terrain after the landing site was changed. [ispace](https://www.ispace-inc.com/2023/05/26/ispace-announces-results-of-the-hakuto-r-mission-1-lunar-landing/) |
| **Peregrine** (2024) | CLPS contract of 79.5 M USD (not verified) | The PCV2 valve lost its seal after loosening from vibration and the tank ruptured | The failure **was reproduced on the ground** with a spare valve. The valve was not removed because that would invalidate "costly" acceptance tests and the launch date would be missed. [Astrobotic report](https://www.astrobotic.com/wp-content/uploads/2024/08/PM1_Post-Mission-Report_2.4_Web.pdf) |
| **Curiosity's wheels** (2013-) | no figure for the damage | Punctures and fatigue on fixed pointed rocks (ventifacts) | They were tested in the Mars Yard, but on smooth terrain and with a single wheel. NASA: "test as you fly" was not followed. After the failure, the Mars Yard was used to define routes and reverse driving. [LLIS 22401](https://llis.nasa.gov/lesson/22401) |
| **InSight's mole** (2019-21) | mission of 813.6 M USD plus 180 M USD international | The mole did not get past ~40 cm because of a cohesive duricrust | Verification correct, validation failed: only cohesionless sands were used, and the real Martian soil was outside the tested domain (cohesion ~5.8 kPa). [arXiv 2112.03234](https://arxiv.org/pdf/2112.03234), [Planetary Society](https://www.planetary.org/space-policy/cost-of-mars-insight) |
| **Spirit at Troy** (2009) | MER: 1,080 M USD in total | Stuck in soft soil | The situation was replicated in a JPL sandbox with test rovers for months. Even so, NASA warned of a "high probability" of not freeing it. [JPL](https://www.jpl.nasa.gov/news/nasa-to-begin-attempts-to-free-sand-trapped-mars-rover/), [Planetary Society](https://www.planetary.org/space-policy/cost-of-the-mars-exploration-rovers) |

Extra case: **HESSI** (75 M USD) was damaged *by* a wrongly applied vibration test, at 10 times the planned acceleration (Science News). Testing also carries risk and cost.

---

## 5. Cost of the analog vs. cost of the failure (own estimates, illustrative)

I have not found any published study that directly compares the cost of an analog with that of an in-situ failure. The following ratios are mine. They compare orders of magnitude; they do **not** show that that specific test would have prevented the failure.

| Comparison | Ratio |
|---|---|
| Vibration (1 week) plus TVAC (2 weeks) at HSFL (52,500 USD) vs. Mars Polar Lander (165 M USD) | **≈0.03 %** |
| The three HSFL campaigns (105,000 USD) vs. Beresheet (100 M USD) | **≈0.1 %** |
| 10 t of high-fidelity simulant (292,500 USD) vs. NASA's cost for InSight (813.6 M USD) | **≈0.04 %** |
| 200 t lunar test bed at MSFC (41,400 USD) vs. InSight | **≈0.005 %** |
| 10-day mission at Aquarius (209,790 USD) vs. Mars Polar Lander | **≈0.13 %** |

Reading: an analog test costs 3 to 4 orders of magnitude less than the mission it protects. The Stecklein multiplier (21-78× in I&T, up to 1,615× in operations) gives the qualitative basis for valuing the "testing euro" as insurance.

The Peregrine and InSight cases show the limit of the argument: the obstacle was the schedule or the representativeness of the analog, not the price of the test. This fits a *similarity* indicator: a cheap but unrepresentative analog (cohesionless sands, smooth terrain) would not have protected the mission.

---

## 6. Gaps (what I could not establish)

- **Rates for large chambers.** There is no public rate for NASA Plum Brook/Armstrong SEC, JSC Chamber A, or the ESTEC Large Space Simulator or Phenix. Everything is quoted case by case. For Europe I have not found any price per day of TVAC or vibration.
- **Analogs without a published cost.**
  - Total campaign cost: D-RATS, PANGAEA and PANGAEA-X, ExoFiT (Tabernas and Atacama), SAFER (Atacama 2013), Haughton-Mars Project.
  - ESA and CNES analog budgets.
- **Facilities without a rate:** JPL Mars Yard, Glenn SLOPE, JSC Rock Yard. Only dimensions are available.
- **HERA cost per campaign.**
- **Prices for drop and impact tests.**
- **Powers (2014) study on the I&T fraction** in NASA missions: not consulted; it only appears as a citation.
- **Unverified figures** (marked `no` in the CSV):
  - Hakuto-R module cost (90 M USD) and Peregrine contract (79.5 M USD);
  - AIV of 20-30 % from the ESA Bulletin;
  - HI-SEAS 2013;
  - MDRS 2023-24;
  - Aquarius annual;
  - MOONWALK.
- **Cost of Schiaparelli and of Curiosity:** not verified; the CSV does not include them.
- **Currencies and inflation.** The CSV keeps the original currency and year; inflation has not been corrected.
