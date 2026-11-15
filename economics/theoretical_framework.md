# Theoretical framework: how much is saved by testing at terrestrial analogs instead of on the Moon or Mars?

NASA Space Apps 2026, team Stars Beside You. Economic component: cost-effectiveness of the "planetary twin finder".

**Thesis to be demonstrated.** A test at a terrestrial analog costs between three and four orders of magnitude less than the same test carried out on the Moon or Mars. It only needs to detect a very small fraction of failures to pay for itself. Our tool also lowers the cost of choosing the analog and raises its similarity, that is, its detection power. It is therefore cost-effective.

Document conventions:
- All sourced figures are in the `macro_*.csv` files in the `data/` folder, with their URLs.
- Anything marked **ASSUMPTION** is a scenario parameter, not a data point.

---

## 1. Notation

| Symbol | Meaning | Where it comes from |
|---|---|---|
| C_M | Life-cycle cost of the actual mission | `macro_mission_cost_vs_outcome.csv` (Planetary Society) |
| V | Scientific or social value of the mission if it succeeds (≥ C_M if the mission was approved) | conservative: V = 0, only C_M is counted |
| p₀ | Probability of failure without prior analog testing | historical rate (section 3) |
| s ∈ [0,1] | Similarity of the analog site to the destination | output of our tool |
| q(s) | Detection power: fraction of latent failures the test uncovers | **ASSUMPTION**, increasing in s |
| C_T^E(s) | Cost of the test on Earth, at a site with similarity s | `earth_tests.csv`, `macro_earth_analog_costs.csv` |
| C_T^X | Cost of the same test in situ (X = Moon or Mars) | cost of a demonstrator mission (section 3) |
| p_T^X | Probability that the in-situ test itself fails (landing, etc.) | historical rate |
| k_f | Multiplier of the cost of fixing an error discovered in phase f | Stecklein et al. 2004 |
| c₀ | Cost of fixing a defect in the requirements phase | relative scale |

---

## 2. Model equations

### 2.1 Expected cost without and with testing (decision analysis)

Without prior testing, the mission fails with probability p₀ and C_M is lost, plus V if value is counted:

  **E[C | no test] = C_M + p₀·(C_M + V)**

With a test at a terrestrial analog, a fraction q(s) of the failures is detected before flight and fixed in the test phase, at cost c₀·k_test:

  **E[C | Earth test] = C_T^E(s) + C_M + p₀·q(s)·c₀·k_test + p₀·(1 − q(s))·(C_M + V)**

### 2.2 Expected savings = expected value of information (EVI) net of its cost

  **ΔE(s) = E[C | no test] − E[C | test] = p₀·q(s)·(C_M + V − c₀·k_test) − C_T^E(s)**

The term p₀·q(s)·(C_M + V − c₀·k_test) is the **expected value of sample information** (EVSI). It is the expected loss avoided thanks to what the test reveals (Raiffa and Schlaifer, 1961; Howard, 1966). The test is worth doing if ΔE > 0.

### 2.3 Break-even point (detection threshold)

Since c₀·k_test ≪ C_M, that term can be neglected:

  **q* = C_T^E / (p₀·(C_M + V))  ≈  C_T^E / (p₀·C_M)**   (conservative bound, with V = 0)

If the test detects more than q* of the failures, it pays off. Equivalently, the maximum justifiable spending on testing is:

  **C_T,max = p₀·q·C_M**

### 2.4 Earth vs. Moon or Mars comparison (the core of the project)

For the same detection power q, the in-situ test costs C_T^X and can also fail itself:

  **ΔE^X = p₀·q·(1 − p_T^X)·C_M − C_T^X**
  **ΔE^E = p₀·q(s)·C_M − C_T^E(s)**

  **Savings from testing on Earth = ΔE^E − ΔE^X = (C_T^X − C_T^E) − p₀·C_M·[q·(1 − p_T^X) − q(s)]**

- If the analog is similar enough that q(s) ≈ q·(1 − p_T^X), the savings are simply C_T^X − C_T^E.
- The in-situ test only wins if its detection advantage offsets the cost difference:

  **q_X·(1 − p_T^X) − q_E(s) > (C_T^X − C_T^E) / (p₀·C_M)**

### 2.5 Cost-effectiveness ratio (CEA)

The metric shown on the dashboard. It measures how much it costs to reduce the probability of failure by one percentage point:

  **CER = C_T / (p₀·q)**   (€ per unit of risk removed; lower is better)

And the incremental ratio of moving from Earth to the Moon or Mars:

  **ICER = (C_T^X − C_T^E) / (p₀·[q_X(1 − p_T^X) − q_E])**

If the ICER is greater than the value at stake per unit of risk (C_M), the in-situ test is dominated.

To compare terrestrial sites with each other: **similarity-per-euro index = s / C_T^E(s)**.

Efficient frontier: a site i is dominated if there is another site j with s_j ≥ s_i and C_j ≤ C_i, with at least one strict inequality. The non-dominated sites form the similarity–cost frontier.

### 2.6 Escalation of the cost of fixing errors

Discovering a defect in the test phase instead of in operations (that is, on the Moon or Mars) saves, per defect:

  **savings per defect = c₀·(k_op − k_test)**

Values from Stecklein et al. (2004), NASA JSC, for systems:

| Phase | Multiplier k |
|---|---|
| Requirements | 1 |
| Design | 3–8 |
| Manufacturing | 7–16 |
| Integration and test | 21–78 |
| Operations | 29 to 1,615 |

The 1,615× corresponds to errors that mean total loss of the system. Data in `macro_error_cost_escalation.csv`.

### 2.7 Insurance

The premium is P = r·I, where I is the insured value. With an actuarially fair rate plus a loading θ, r ≈ p·LGD·(1 + θ), where LGD is the loss given a claim. If the test reduces p by Δp = p₀·q, the premium falls by:

  **ΔP = I·Δp·LGD·(1 + θ)**

Market references: the launch + 1 year rate for a GEO satellite on Falcon 9 went from less than 6% to about 10% of insured value after 2023. The annual in-orbit rate went from 0.6% to 1.2% (`macro_space_insurance.csv`). This channel applies mainly to the commercial sector, because NASA science missions are not insured.

### 2.8 Economies of scope and scale ("wildcard" Moon + Mars sites)

- Scope index: **SC = [C(Moon) + C(Mars) − C(Moon, Mars)] / C(Moon, Mars)**. If SC > 0, a single campaign at a wildcard site is cheaper than two separate campaigns.
- Scale: with a fixed campaign cost F and a variable cost c per test, **AC = F/n + c**. The average cost falls with the number n of tests per campaign.

### 2.9 Real option to learn before committing C_M

The test is a call option on the flight decision:

  **NPV_flexible = NPV_static + option value**
  **option value = E[max(V_post − C_M, 0)] − max(E[V] − C_M, 0) ≥ 0**

Dixit and Pindyck (1994). The test buys the right to redesign or cancel with new information.

### 2.10 Uncertainty

- p₀, q(s) and C_T are modeled as distributions: triangular or beta.
- Monte Carlo: 10,000 simulations of ΔE. P(ΔE > 0) and the 5th percentile of savings are reported.
- Tornado sensitivity chart over p₀, q, C_T and C_M.

---

## 3. Numerical example (the data are sourced; q is an ASSUMPTION)

**p₀ = 31.25%.** This is the historical failure rate of surface elements on Mars (landers, rovers, penetrators, helicopter) launched since 1990: 5 failures out of 16. We calculated it from Wikipedia's list of missions (`macro_mars_failures_by_decade.csv`).

| Decade | Failure or partial: missions | Failure or partial: surface elements |
|---|---|---|
| 1960s | 75% (n = 12) | 100% (n = 1) |
| 1970s | 27% (n = 11) | 67% (n = 6) |
| 1990s | 71% (n = 7) | 60% (n = 5) |
| 2000s | 0% (n = 6) | 25% (n = 4) |
| 2010s | 17% (n = 6) | 33% (n = 3) |
| 2020s | 0% (n = 3) | 0% (n = 4) |

**C_M** (life-cycle cost in 2025 dollars, Planetary Society):

| Mission | C_M |
|---|---|
| Mars Pathfinder | 613 M$ |
| InSight | 1,365.5 M$ |
| Curiosity | 4,020.6 M$ |
| Mars Polar Lander (failed) | 306.4 M$ |
| Mars Climate Orbiter (failed) | 306.4 M$ |
| Mars Observer (failed) | 2,502.3 M$ |

The 8 failed missions in the dataset add up to about 3,526 M$ (2025 dollars) lost.

**C_T^E.** Reference: the Nomad rover, development plus 45 days in the Atacama, cost 1.6 M$ in nominal 1997 dollars (NASA press release). Other references: the Airbus Mars Yard, about £500,000 in 2014, and the MDRS fee (see `earth_tests.csv`).

**Break-even threshold q*** with C_T^E = 1.6 M$:

| Reference mission | q* |
|---|---|
| Pathfinder | 0.84% |
| InSight | 0.37% |
| Curiosity | 0.13% |

In other words, a campaign of that size pays for itself if it detects at least between 0.1% and 1% of the mission's failures. With an ASSUMPTION of q = 10% on a Curiosity-class mission: ΔE = 0.3125 × 0.10 × 4,020.6 − 1.6 ≈ **124 M$** of expected loss avoided, net of the cost of the test.

Full curve with q from 0 to 0.5 and C_T of 1.6, 5 and 20 M$: `macro_illustrative_savings_model.csv`.

**C_T^X.** An in-situ test requires a demonstrator mission. Mars Pathfinder, which was a technology demonstrator with a rover, cost 613 M$ (2025 dollars). In addition, the test itself may fail: p_T^X ≈ 31% using the surface rate calculated above. With these figures:

- C_T^X / C_T^E ≈ 613 / 1.6 ≈ **380 times**. The comparison mixes 2025 dollars with nominal 1997 dollars; adjusting the 1.6 M$ for inflation reduces the ratio somewhat but does not change the order of magnitude.
- For the same q, the Earth test dominates unless the in-situ test detects, in absolute terms, about (613 − 1.6) / (0.3125 × C_M) more points of failures than the terrestrial one. That is 48 more percentage points for a Curiosity-class mission and more than 100% for a Pathfinder-class one: impossible.

This is the central argument for the judges.

**Launch.** The cost per kg to low Earth orbit has also fallen: as a world average, from 87,023 $/kg in 1960 to 3,868 $/kg in 2025, with a 21.2% drop for each doubling of cumulative payload (Terzi and Nicoli, PNAS Nexus, 2026). Even so, reaching the surface of the Moon or Mars still costs orders of magnitude more than a truck to the Atacama or to Tenerife. This keeps Earth's advantage in place, although the ratio will narrow over time.

---

## 4. Supporting theory

- **Cost-effectiveness vs. cost-benefit analysis.** Cost-effectiveness (CEA) is used because the scientific benefit V is hard to monetize. Once the objective is fixed, "reduce the risk of failure", the cheapest option per unit of risk removed wins. Cost-benefit analysis (CBA) is the general case with V monetized (Boardman et al., *Cost-Benefit Analysis*).
- **Value of information and decision theory.** Raiffa and Schlaifer (1961), *Applied Statistical Decision Theory*; Howard (1966), "Information Value Theory", IEEE Trans. SSC. Formulas in section 2.2.
- **Learning curves and Wright's law.** C_n = C₁·n^(−b), with b = −log₂(LR). Wright (1936) is the original reference.
  - For launchers, the elasticity is −0.34 and the learning rate 21.2% (Terzi and Nicoli, 2026).
  - NASA uses 85% as its generic curve.
  - Application to the project: repeated analog campaigns make each test cheaper (`macro_launcher_experience_curve.csv`).
- **Risk and cost overruns.** The GAO puts the cumulative cost overrun of NASA's major project portfolio at 4.7 billion $ and 14 years of delay (2026). The figure was 7.6 billion $ in 2023 (`macro_nasa_gao_cost_overruns.csv`). Detecting defects earlier reduces that cost tail.
- **Arrow–Lind (1970).** The government can act as risk-neutral in diversified investments, which justifies using expected values. In unique, very large missions, risk aversion is real; it can be quantified with insurance premiums or Monte Carlo percentiles.
- **Public goods and externalities.** Space R&D generates spillover effects. According to NASA, FY2023 produced 75.6 billion $ of output and 304,803 jobs on a budget of 25.4 billion $: a gross multiplier of about 2.98 times, calculated here. It is an input-output impact, not a net benefit. Shared test data from an open tool have the character of a public good.
- **Baumol.** One-off, craft-style engineering suffers from the "cost disease": its relative cost rises over time. Testing cheaply and often on Earth is one way to escape it.

---

## 5. Macro context (summary; details in the CSV files)

- **Global space economy** (Space Foundation): 613 billion $ in 2024 and 686 billion $ in 2025, of which 79% is commercial. McKinsey/WEF: 630 billion $ in 2023 and 1.8 trillion in 2035. OECD: public budgets of OECD countries add up to 75 billion $, 0.1% of their GDP (2022).
- **NASA:** 24.4 billion $ in FY2026, 0.33% of federal spending; the peak was 4.41% in 1966. Series since 1959 in `macro_nasa_budget.csv`.
- **ESA:** 7.79 billion € in 2024, 7.68 in 2025 and 8.26 in 2026. The 2025 Ministerial Council approved 22.3 billion €.
- **Artemis** (NASA OIG): 93 billion $ in fiscal years 2012–2025, and 4.1 billion $ per SLS/Orion launch (4.2 billion $ according to the 2024 update).
- **Moon:** PwC 2021 estimates 170 billion $ cumulative in 2020–2040. PwC 2026 gives between 93.9 and 127.3 billion $ in 2026–2050 (cited by New Scientist). NSR forecasts: 42.3, 105 and 188 billion $ depending on the edition.

---

## 6. Proposed charts for the dashboard

1. **Savings curve.** ΔE vs. q, with one line per reference mission and one band per C_T, marking q*. Data: `macro_illustrative_savings_model.csv`.
2. **Log-scale bars of test cost:** terrestrial analog (Nomad, MDRS, Mars Yard) vs. in-situ demonstrator (Pathfinder) vs. full mission (Curiosity). Data: `macro_earth_analog_costs.csv`, `earth_tests.csv`, `macro_mission_cost_vs_outcome.csv`.
3. **Similarity–cost frontier** of the analog sites, with dominated and non-dominated sites and the wildcards highlighted. Data: s from our tool and bottom-up C_T.
4. **Scatter of mission cost vs. outcome** (success or failure, and citations). Data: `macro_mission_cost_vs_outcome.csv`.
5. **Failure rate by decade on Mars**, missions and surface. Data: `macro_mars_failures_by_decade.csv`.
6. **Escalation of the cost of fixing errors by phase**, on a log scale. Data: `macro_error_cost_escalation.csv`.
7. **Cost per kg to LEO over time**, with Wright's line. Data: `macro_launch_cost_per_kg.csv`.
8. **Sensitivity tornado and Monte Carlo distribution of ΔE**, generated by the model.

---

## 7. Gaps (not verified or pending)

- **q(s) has no empirical source.** No study was found that quantifies what fraction of failures analog tests detect. It must be presented as a scenario, with sensitivity analysis.
- **There is no published cost of "the same test" on the Moon or Mars.** A demonstrator mission is used as a proxy: Pathfinder or, as a floor, MarCO, at 23.5 M$ (2025 dollars). No per-kg price to the lunar surface (CLPS) was opened either.
- **The PwC 2026 and NSR figures** come from press coverage or report summary pages, not from the full reports.
- **The 7,000 $ MDRS fee** comes from an old page and is not verified. The 2026 fee is in `earth_tests.csv`.
- **The Space Foundation figure of 570 billion $ for 2023** comes from a Breaking Defense excerpt.
- **Mixed price bases.** Test costs are nominal and mission costs are in 2025 dollars, unless otherwise stated. No deflator has been applied.
- **The classic references** (Raiffa–Schlaifer, Howard, Wright, Dixit–Pindyck, Arrow–Lind, Boardman, Baumol) are cited bibliographically and were not opened in this session.
