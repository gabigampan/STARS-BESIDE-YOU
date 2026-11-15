# Economics models (plan part 7)

The question: **how much does NASA save by testing prototypes such as rovers on Earth, compared with what it would cost to test them on the Moon?** The answer is scenario-based. It compares the cost of ONE test: delivering the prototype to the lunar surface (a delivery-only estimate, so a lower bound on the whole cost of a lunar test) against one field campaign at an Earth analog site (at official rates), and it says what each side leaves out.

## How to run

```
python3 economics/model/run_all.py            # unit tests, then every model; writes economics/outputs/
python3 economics/model/run_all.py --no-tests # skip the tests
python3 economics/model/test_model.py         # tests only
```

Python 3 with numpy and pandas only. Runtime is under a minute. `run_all.py` exits 1 if a unit test fails (nothing is written), and 2 if an output sanity check fails (`outputs/sanity_checks.json`). The road distances Malaga to the mainland sites were captured once with `python3 economics/scrape/origin_road_access.py` (OSRM, through `common.fetch`; table `data/processed/origin_road_access.csv`). The models never fetch anything.

## Rules the code enforces (`core.py`)

- Every number is read from a processed table by code (`Tables.get`/`Tables.rows` return a `Ref` with table, row key and column) or is an assumption in `config/model_assumptions.json` (name, value or low/mode/high, unit, label ILLUSTRATIVE, distribution, flag, one-sentence rationale). Unit conversions (lb to kg, million, days per week) and the Earth radius are the only literals. Campaign values duplicated from `config/campaign.json` are checked against it at load.
- `data/quarantine/` is never read. Rows with confidence `low` raise `LowConfidence` unless a labelled sensitivity asks for them. **Consequence:** every `workable_days_*` row is confidence low (station-based, rain and cold only), so the base case uses a generic ILLUSTRATIVE workable-day range for every site, and the station data enter only the sensitivity `station_weather_low_conf` (with the ILLUSTRATIVE wind-loss range; Atacama and Holuhraun use declared ILLUSTRATIVE ranges because they have no station).
- Money stays in source currency and year until the end. Conversion uses the ECB reference rate of 2026-11-13 (1.1052 USD/EUR, 136.6 ISK/EUR, from `fx_rates`). The base case is nominal. The inflation variant (Spain HICP for EUR amounts, US CPI from the IMF relay for USD amounts, each to the mean of the 2026 months published) is a sensitivity only.
- Each output figure records its dependencies (`Deps`) in `outputs/model_manifest.json`, with `any_illustrative` and any low-confidence input. Each output carries flags; `core.FLAG_TEXT` gives the plain-language sentence for each.

## Models

| Module | Model | What it can claim | What it cannot claim |
|---|---|---|---|
| `m1_field_campaign.py` | M1 field campaign per site | Relative ranking of the nine sites at official rates; which item dominates | Market prices; salaries, insurance, customs and the prototype are left out |
| `m2_monte_carlo.py` | M2 Monte Carlo, tornado, convergence | The spread that follows from the declared ranges | More precision than those ranges |
| `m6_moon_vs_earth.py` | M6 Moon vs Earth (headline) | Order of magnitude: one lunar delivery equals hundreds (11 kg rover) to tens of thousands (larger rovers) of Earth campaigns; the Moon side is delivery only | A booked saving; a like-for-like test (Earth analogs do not reproduce lunar gravity, vacuum, dust and thermal conditions together) |
| `m4_voi.py` | M4 value of information | Value rises with fidelity and never exceeds EVPI; order of magnitude against a campaign | Anything measured: p, s, c and R are ILLUSTRATIVE |
| `m7_escalation.py` | M7 late-fix escalation | Stecklein factors by phase as captured; derived ratios | A multiple for a specific rover |
| `m8_landing_outcomes.py` | M8 landing outcomes | Tallies as of 2026-11-14 under both classifications, with the counting unit | "To date" without the date |
| `m3_pareto_hook.py` | M3 Pareto frontier | Not built: similarity scores do not exist. Documented interface only | |
| `bundle.py` | dashboard bundle, ASSUMPTIONS.md, sanity checks | | |

## Formulas

**M1** (per site; `x` are the Monte Carlo inputs)

```
on_site_days = ceil(test_days / f)            f = workable-day fraction (base: ILLUSTRATIVE PERT 0.60/0.80/0.95)
field_days   = on_site_days + travel_days     sensitivity: f = station fraction x (1 - wind loss)
per_diem     = people x field_days x (lodging x s_lodg + meals)      Spanish RD 462/2002 Group 2 by country (base)
                                                                     US GSA FY2027 / State Dept (upper scenario)
travel       = people x Tri(min, Erasmus+ non-green, max of scheme bands)(u) x s_trav
               band chosen by the great-circle distance AGP -> chosen airport (site_airports)
freight_air  = mass x 2 legs x rate_USD/kg x markup / 1.1052 + 2 x DG surcharge (island and overseas sites)
freight_road = road_km(AGP -> site, OSRM) x 2 x 0.26 EUR/km             (mainland Spain)
vehicles     = 2 x field_days x rate_EU27 x PLI(country, A01, 2024) / 100
fees         = published fees only (Death Valley special-use application, MDRS crew fee per person per 14-day rotation);
               Timanfaya and BLM state no fee; elsewhere 0 + flag "authorisation required, fee not published"
```

Airport: the site_airports rows not downgraded to low (same island for island sites), then the shortest OSRM drive time. Seasonal factors s_lodg, s_trav: triangular between the lowest and highest 2025 month of Spain HICP CP112 (accommodation) and CP0733 (air), relative to the 2025 mean, joined by a Gaussian copula with Spearman 0.45 (declared; the 2025 months themselves give a Spearman reported in the bundle).

**M2.** 20,000 draws, seed 42. PERT (lambda 4) for expert ranges, triangular for ranges set by published values, lognormal for the air-cargo rate (P10, P90 = the two primary index values; sigma = (ln P90 - ln P10) / 2.563), Beta for landing success. Convergence: mean and P90 at N/8, N/4, N/2, N, pass if within 0.5% at N/2 and N (`outputs/mc_convergence.csv`). Tornado: each input at its own P10 and P90 (from its draws) with every other input at its P50.

**M6.**

```
price_per_kg   in { award_USD / planned NASA payload kg (same NASA release): 19D, CP-11, CP-22, IM 2026 award;
                    OIG 2019 estimate (1.0), OIG 2023 estimate (1.2) }            USD M per kg
               ~ Tri(min, median, max) of that set                                (Firefly 494.5 kg row never used)
delivery       = mass_kg x price_per_kg                                           (delivery only; linear scaling flagged: shared ride for small, overstated for large)
p_success      ~ Beta(1 + full successes, 1 + attempts - full successes)          13 attempts 2019-01-01..2026-11-14
                 strict 5/13 -> Beta(6, 9), mean 0.40; operator's claim (SLIM success) 6/13 -> Beta(7, 8), mean 0.47
per_success    = delivery / p_success
DSN (separate) = surface_days x hours_per_day x RB 1,792 USD/h x AW 1 x MW 1     accounting charge, never added
ratio          = delivery_EUR / earth_campaign_EUR (per draw);  campaigns per delivery = floor(ratio)
facility week  = agreement value / max tests (JSC: 5 per year x 4 years; KSC: weeks of the term) ... up to the whole value
```

Mass classes from `prototype_mass_classes`: Sojourner 11 kg, MER 174 kg, VIPER 475 kg contracted delivery mass. Earth freight for a class = 400 kg kit + the class mass. For the VIPER class the contracted delivery values (TO-20A June 2020 $199.5 M, Dec 2021 $235.6 M, Feb 2024 $322.8 M; CS-7 2025 potential $190 M) are reported next to the linear estimate, each labelled for what it is and never added together. They show that linear scaling overstates the largest class by about 2-3x.

**M4.** `E0 = min(pL, R)`, `EVPI = E0 - p min(L, R)`, `P+ = sp + (1-c)(1-p)`, `p+ = sp/P+`, `p- = (1-s)p/(1-P+)`, `E1 = P+ min(p+ L, R) + (1-P+) min(p- L, R)`, `EVSI = E0 - E1`, net = EVSI - campaign P50 (USD). L = M6 delivery P50, plus the VIPER project cost ($505.4 M, OIG, Jan 2024) for the VIPER class only; R = 20% of L (range 10-40%); p = 0.15 (0.05-0.30); s, c by fidelity level (`voi_fidelity_levels`). Prior sweep 0.01-0.50.

**M7.** Factors exactly as captured (requirements = 1). Derived from the abstract summary row: test/design = 21/3 to 78/8 (7 to 9.75, same end), widest 21/8 to 78/3; operations/test = 29/21 to 1500/78, widest 29/78 to 1500/21.

**M8.** Lunar: landing attempts (landing_attempted = yes) landed from 2019-01-01 to 2026-11-14: strict 5/3/5, operator's claim 6/2/5, plus the unsourced IM-1 variant 7/1/5 marked `sourced = false`. Mars: landed elements 10/1/7 (18), InSight partial 9/2/7, by mission 17 with 6 failures.

## Outputs (`economics/outputs/`)

`site_costs.csv` (exact columns), `site_cost_breakdown.csv` (component x scenario), `tornado.csv`, `mc_convergence.csv`, `earth_vs_moon.csv`, `moon_price_per_kg.csv`, `facility_per_test.csv`, `voi.json`, `escalation.csv`, `landing_outcomes.csv`, `dashboard_data.json` (one bundle: tidy chart arrays with unit, labels, source ids and flags; headline numbers each with the allowed sentence and what it must not be taken to mean; FX rate and date; as-of date; source registry), `model_manifest.json`, `ASSUMPTIONS.md`, `sanity_checks.json`.

## Scenarios in `site_cost_breakdown.csv`

`base` (no low-confidence row), `upper_us_rates` (US GSA/State Dept per diem; higher abroad, about equal at the US sites), `station_weather_low_conf`, `low_conf_all` (adds the 2.30 USD/kg press freight row and the Holuhraun ISK 50,000 filming fee), `inflation_adjusted`, `rho_low` / `rho_high` (rank correlation 0.3 / 0.6).
