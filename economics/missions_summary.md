# Costs and outcomes of robotic missions to the Moon and Mars: summary

Dataset: `data/missions.csv` (31 missions, 17 columns). Compiled on 13-11-2026. All figures are in **nominal USD of the year indicated** (not adjusted for inflation), unless otherwise stated. "ESTIMATE" entries are flagged as such in the CSV.

## Main conclusions

1. **NASA "flagship" missions to Mars cost between 2,500 and 2,700 M USD** and increasingly run out of control in the development phase.
   - Perseverance: 2,725 M USD = 2,200 for development + 243 for launch + ~300 for operations ([Planetary Society](https://www.planetary.org/space-policy/cost-of-perseverance)). Development exceeded the plan by 359.3 M USD (+21.4 %) ([GAO-20-405](https://www.gao.gov/assets/gao-20-405.pdf)).
   - Curiosity/MSL: development rose 86 % (from 969 M to 1,800 M USD) and the life cycle 56 % (from 1,600 M to 2,500 M USD), due to the launch delay from 2009 to 2011 ([NASA OIG IG-11-019](https://oig.nasa.gov/wp-content/uploads/2024/02/IG-11-019.pdf)).
2. **"Faster, better, cheaper" (1990s)**: Pathfinder came in at 280 M USD with launch and operations included and was a success. The two 1999 missions, MCO and MPL, failed because of software and engineering errors: imperial vs. metric units and a premature engine shutdown. MPL cost 165 M USD.
3. **Mars Sample Return is the big cost sinkhole.** The life-cycle estimate went from 2,500–3,000 M USD (2020) to 5,900–6,200 M (2022) and to an unofficial 7,400 M (June 2023) ([NASA OIG IG-24-008](https://oig.nasa.gov/wp-content/uploads/2024/03/ig-24-008.pdf)). The independent review board put it at **8,000–11,000 M USD** ([MSR IRB, Sept. 2023](https://www.nasa.gov/wp-content/uploads/2023/09/mars-sample-return-independent-review-board-report.pdf)) and NASA accepted that range in April 2024.
4. **VIPER is a textbook sunk-cost case.** It was approved in 2021 for 433.5 M USD and the estimate reached 609.6 M (+30 %). NASA cancelled it in July 2024 with about 450 M already spent (~74 %), claiming savings of **only 84 M USD**, and still kept the contract of about 322 M USD for Griffin to land without the rover ([SpaceNews](https://spacenews.com/nasa-cancels-viper-lunar-rover/), [Planetary Society](https://www.planetary.org/articles/nasa-cancels-viper)). According to the Planetary Society, in September 2025 NASA contracted Blue Origin to take it to the Moon in 2027.
5. **The commercial CLPS model is much cheaper per mission, but it also has cost overruns and more risk** ([NASA OIG IG-24-013](https://oig.nasa.gov/wp-content/uploads/2024/06/final-report-ig-24-013-nasas-commercial-lunar-payload-services-initiative.pdf)).
   - The 8 delivery contracts went from 781.4 to 984.3 M USD (+26 %), with an average delay of 14 months. About 171.4 M of the increase (82 %) came from changes requested by NASA itself.
   - Price per kilo: NASA estimated ~**1 M USD/kg** delivered to the lunar surface in 2019, rising to ~**1.2 M USD/kg** with the 2023 contracts.
   - OIG comparison: the LRO orbiter cost ~590 M USD, while IM-1 charged ~122 M to carry 6 instruments that had cost ~9.5 M.
   - Outcomes of the first four CLPS flights: Peregrine failed (propellant leak), IM-1 was a partial success (tipped over), IM-2 nearly failed (tipped over) and Blue Ghost 1 was a full success. That is, **1 of 4 fully successful**.
   - Masten went bankrupt in 2022 after receiving 66.1 M USD.
6. **Non-US agencies land for a fraction of the price**, although their figures often exclude salaries or infrastructure:
   - Chandrayaan-3: 615 crore INR, ≈75–87 M USD, launch included ([Times of India](https://timesofindia.indiatimes.com/india/chandrayaan-3-to-cost-rs-615-crore-launch-could-stretch-to-2021/articleshow/73055941.cms)).
   - SLIM: 18,000 M JPY (≈121.5 M USD).
   - Beresheet: ≈100 M USD, and it failed.
   - China does not publish costs. There is only an analogy for Chang'e 4 ("what one kilometer of subway costs", ≈72–172 M USD, ESTIMATE).
7. **Launch cost per kg to low Earth orbit (LEO)**, according to [Jones, NASA Ames, ICES-2018-81](https://ntrs.nasa.gov/api/citations/20200001093/downloads/20200001093.pdf), in 2018 dollars:

   | System | USD/kg |
   |---|---|
   | Space Shuttle | 61,700 (54,500 in the paper's abstract) |
   | Average of 1970–2000 launchers | 18,500 |
   | Saturn V | 5,200 |
   | Falcon 9 | 2,720 |
   | Falcon Heavy | 1,410 |

   That is a ~20× drop relative to the Shuttle. [CSIS](https://aerospace.csis.org/data/space-launch-to-low-earth-orbit-how-much-does-it-cost/) describes the same trend (a steep decline between 2005 and 2020), but its per-vehicle figures are only in an interactive chart that I could not read. **Note:** carrying 1 kg to the lunar surface with CLPS (~1–1.2 M USD/kg) costs about 400 times more than putting it in LEO with Falcon 9.
8. **Own calculation for the dashboard** (not from any source): Perseverance comes to 2,725 M USD / 1,025 kg of rover ≈ **2.7 M USD per kg of rover on Mars**, the same order as the CLPS price per kg on the Moon.

## Historical success rates

- **Mars, NASA History:** of 26 attempts to reach Mars between 1960 and 1996, only 12 were fully or partially successful ([nasa.gov](https://www.nasa.gov/history/25-years-of-continuous-robotic-mars-exploration-from-pathfinder-to-perseverance)).
- **Mars, InSight press kit (JPL, 2018):** "only about 40 % of the missions ever sent to Mars by any space agency have been successful" (file `raw/insight_kit.pdf` in the original data folder; not included in this package).
- **Space Osmosis (independent secondary source, data up to October 2026; method based on NSSDCA and GCAT)** ([spaceosmosis.com/missions](https://spaceosmosis.com/missions/)):
  - Mars: 54 missions, of which 22 were successes, 8 partial successes and 22 failures (2 still ongoing). Among those with a final outcome, 42 % successes and 42 % failures.
  - Moon: 141 missions, with 71 successes, 16 partial and 54 failures, and 28 soft landings.
- **Our sample of Moon landings from 2019 to 2025** (Beresheet, Chandrayaan-2 and 3, Chang'e 4, 5 and 6, Hakuto-R 1 and 2, SLIM, Luna 25, IM-1, IM-2, Peregrine and Blue Ghost; Peregrine did not even get to attempt the landing):
  - China (Chang'e 4, 5 and 6) and Chandrayaan-3 succeeded.
  - Private companies (Beresheet, Hakuto-R 1 and 2, IM-1, IM-2, Peregrine and Blue Ghost) had 1 full success, 2 partial and 4 failures.
  - Among national agencies: Luna 25 and the Chandrayaan-2 lander crashed, and SLIM landed, although upside down.
  - This count is our own, compiled from the CSV.

## Methodological caveats

- The figures are **not homogeneous**. Some are life-cycle costs (with launch and operations), others development only, and others contract prices (CLPS: fixed-price delivery service, excluding the cost of NASA's instruments). Use the `includes_launch` and `includes_operations` columns.
- They are in **nominal USD**. To compare eras, deflate (for example, with the US GDP price index) before charting.
- Many figures for masses, non-US costs and outcomes come from **Wikipedia**, which I read in its source text. NASA's main figures are verified against primary sources (OIG, GAO, MSR IRB, NASA releases).
