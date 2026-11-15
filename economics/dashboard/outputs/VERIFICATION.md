# Verification of the economics model (2026-11-14)

An independent verifier checked the model. The verifier did not build it and assumed it contained mistakes. Scope: the code in `economics/model/`, the outputs in `economics/outputs/`, and the rules in `data/README.md`, `data/audit/nasa_report.md` and `data/audit/public_report.md`.

**Verdict: the arithmetic is correct.** Every recomputed number matches the builder's within 0.41% (213 comparisons; none above the 1% deterministic or 3% Monte Carlo threshold). No model formula had to change. Seven headline sentences and seven chart takeaways overclaimed or were badly worded, and two `includes` fields contained raw template text. These are fixed in `model/bundle.py` and `model/core.py`, and the outputs were regenerated with `run_all.py`. All tests pass (15, two of them new) and all 14 sanity checks are OK.

## 1. What was recomputed, and how

`model/verify/recompute.py` was written from the README formulas and the processed tables only. It does not import or copy any builder code. It reads `data/processed/*.csv` (never `data/quarantine/`), `config/model_assumptions.json` and `config/sites.csv`, and it has its own Monte Carlo: 200,000 draws, seed 12345, numpy's own triangular sampler, and no copula (the seasonal factors are drawn independently). `model/verify/compare.py` lines the results up against `outputs/`. It is the only verifier file that calls builder code, and only to evaluate `campaign_cost` at the same mid point. All 213 rows are in `model/verify/comparison.csv`.

To re-run:

```
python3 -I economics/model/verify/recompute.py
python3 economics/model/verify/compare.py
```

Mid values: each PERT or triangular input at its mode; the air-cargo rate at its lognormal median sqrt(3.13 x 2.90) = 3.013 USD/kg; seasonal factors at 1; travel at the Erasmus+ non-green band; workable fraction 0.80, which gives 13 on-site days and 15 field days.

### Comparison table (selection; full table in `model/verify/comparison.csv`)

| Quantity | Builder | Verifier | Difference |
|---|---|---|---|
| Price per kg, Blue Ghost 1 (19D): $93.3 M / 94 kg | 0.9926 | 0.9926 | 0 |
| Price per kg, IM-3 (CP-11): $77.5 M / 92 kg | 0.8424 | 0.8424 | 0 |
| Price per kg, IM-4 (CP-22): $116.9 M / 79 kg | 1.4797 | 1.4797 | 0 |
| Price per kg, IM 2030 award: $180.4 M / 75 kg | 2.4053 | 2.4053 | 0 |
| OIG 2019 / 2023 estimates (USD M/kg) | 1.0 / 1.2 | 1.0 / 1.2 | 0 |
| Set median, min, max (USD M/kg) | 1.10, 0.842, 2.405 | same | 0 |
| Moon delivery P50, 11 kg (EUR) | 13.88 M | 13.89 M | -0.1% |
| Moon delivery P50, 174 kg (EUR) | 219.5 M | 219.8 M (analytic triangular median 219.7 M) | -0.1% |
| Moon delivery P50, 475 kg (EUR) | 599.3 M | 599.9 M | -0.1% |
| Lunar tallies 2019-01-01 to 2026-11-14: strict / operator / +IM-1 | 5/3/5, 6/2/5, 7/1/5 of 13 | same | 0 |
| Beta posterior, strict / operator | Beta(6,9) mean 0.40; Beta(7,8) mean 0.467 | same | 0 |
| Median of 1/p, strict / operator | 2.526 / 2.146 | 2.526 / 2.151 | 0.0% / -0.2% |
| Per successful test, 174 kg, strict P50 (EUR) | 568.9 M | 568.7 M | +0.04% |
| Campaign at mid values, Tabernas: per diem 9,303.3 + travel 1,266 + freight 133.5 + 4x4 2,448.9 + fees 0 | 13,151.7 | 13,151.7 | 0 |
| Campaign at mid values, Bardenas: 9,303.3 + 1,854 + 451.9 + 2,448.9 + 0 | 14,058.1 | 14,058.1 | 0 |
| Campaign at mid values, Teide: 9,303.3 + 1,854 + 4,561.6 + 2,448.9 + 0 | 18,167.8 | 18,167.8 | 0 |
| Campaign at mid values, Holuhraun: 13,468.5 + 3,480 + 4,561.6 + 4,662.9 + 0 | 26,173.0 | 26,173.0 | 0 |
| Campaign at mid values, Atacama: 13,739.4 + 10,410 + 4,561.6 + 2,700 + 0 | 31,411.0 | 31,411.0 | 0 |
| Campaign at mid values, Death Valley: 19,148.4 + 10,410 + 4,561.6 + 4,028.4 + 271.4 | 38,419.9 | 38,419.9 | 0 |
| Campaign at mid values, MDRS: 19,148.4 + 10,410 + 4,561.6 + 4,028.4 + 19,001.1 | 57,149.5 | 57,149.5 | 0 |
| Campaign MC P50, all nine sites | 13,128-57,207 | 13,137-57,206 | at most 0.08% |
| Campaign MC P10 / P90, all nine sites | | | at most 0.41% |
| Moon/Earth ratio P50, 11 kg: MDRS / Tabernas | 235 / 1,056 | 235 / 1,057 | under 0.1% |
| Moon/Earth ratio P50, 174 kg: MDRS / Tabernas | 3,594 / 16,706 | 3,593 / 16,716 | under 0.1% |
| Moon/Earth ratio P50, 475 kg: MDRS / Tabernas | 9,262 / 45,605 | 9,270 / 45,633 | under 0.1% |
| VOI, 174 kg, high_twin: L, EVPI, EVSI (USD) | 242.6 M, 29.12 M, 20.62 M | 242.9 M, 29.14 M, 20.64 M | -0.09% (from L) |
| VOI posteriors: P+, p+, p- | 0.2125, 0.600, 0.02857 | same | 0 |
| Stecklein test/design: same end, widest | 7-9.75; 2.625-26 | same | 0 |
| Stecklein operations/test: same end, widest | 1.38-19.2; 0.372-71.4 | same | 0 |
| 1 kg Moon (OIG 1.2 M) / 1 kg air cargo (Xeneta 3.13) | 383,387 | 383,387 | 0 |

VOI by hand: p L = 0.15 x 242.9 M = 36.4 M < R = 48.6 M, so E0 = 36.4 M (fly as is). After a positive test p+ L = 145.7 M > R, so redesign: 0.2125 x 48.6 = 10.32 M. After a negative test p- L = 6.94 M < R: 0.7875 x 6.94 = 5.47 M. E1 = 15.79 M, so EVSI = 20.64 M; EVPI = 36.4 - 0.15 x 48.6 = 29.14 M.

**One discrepancy, on the verifier's side.** The first run differed by 2.5% on the Bardenas P50. The verifier's band lookup had kept the C(2024) 5405 *land* band (400-600 km, EUR 133) for the 720 km AGP-PNA trip. The builder falls back to the air band 601-1600 (EUR 365), and the audit table itself gives 365 for Bardenas. The builder was right, and the verifier's script was corrected. A test for this case was added to `test_model.py`.

## 2. Rules

| Rule | Status | Where checked |
|---|---|---|
| Firefly 494.5 kg row never used | Respected. The row is confidence low and attribute `payload_mass_planned_incl_lunar_orbit_relay`; `price_per_kg_table` never pairs it (assert plus test). The verifier's own pairing excludes it too. | m6, test_model, recompute |
| VIPER $505.4 M and "about $500 M" never added; $4.8 M and $9 M never added | Respected. M4 uses only `project_cost_latest` (505.4); the headline quotes the rounded restatement once. The $4.8 M and $9 M rows are not read. | run_all.build_voi, bundle |
| DSN shown as an accounting line, not summed into cash cost | Respected. `dsn_usd` is never added to any total; the column note says "not included in any total". | run_all M6 block |
| Facility agreements not presented as a per-rover-test price | **Was violated in the headline** (value "USD 59,491 per test-week"; takeaway "per test-week, against hundreds of millions for a delivery"). **Fixed:** the headline is now `facility_agreements` (whole-agreement value $0.72-1.19 M, audit sentence verbatim), and the per-test-week split stays only in `facility_per_test.csv` with its must-not text. | bundle |
| EU travel amounts not called airfares | Respected. Label "Travel (EU flat rate)"; the flag says "not airfares". "Air fares" appears only for the Eurostat HICP CP0733 passenger-air index, which is what that index measures. | bundle, core |
| Analog awards not summed | Respected. `analog_program_awards` is not read by any model. | grep |
| Outcome tallies dated | Headlines were dated. **Two chart takeaways were undated** ("Fewer than half of recent lunar landing attempts..."; "Best estimate about 40%..."). **Fixed:** both now say "2019 to 14 November 2026". | bundle |
| No confidence-low row in the base case | Respected for every value: no base figure in the manifest lists a low-confidence input. One base-case *choice* uses low rows: for Holuhraun, all three airport drive times are confidence low and still decide EGS. `run_all` checks that every usable airport gives the same travel band (1 band set), and the verifier confirmed it. Flag `AIRPORT_CHOICE_LOW_TIME`. | manifest, sanity_checks |
| No quarantined value used | Respected. `Tables.df` refuses the quarantine path. The quarantined values (AMADEE country counts, 11 awards, 11 USAspending rows, Chandrayaan-2 launch date, 5 Moon leads) feed no model. | core, quarantine listing |
| Every constant is physical, a conversion, or from `model_assumptions.json` | Respected in the model code. The literals found are a 1e-9 ceiling guard, the PLI base of 100, histogram bins and grid, tornado quantiles 0.1/0.9, and sanity-check thresholds that never enter outputs. The new display tie rule (P50 within 1%) is a wording rule, not a model input. | grep of model/*.py |
| ILLUSTRATIVE and missing-weather flags reach `dashboard_data.json` | Respected. Every chart or headline with an ILLUSTRATIVE flag has `depends_on_illustrative = true`. Base site outputs carry `WEATHER_GENERIC`; the station sensitivities carry `WEATHER_STATION_LOW` / `WEATHER_NO_DATA` (Atacama, Holuhraun) and `WIND_ILLUSTRATIVE`. | programmatic check |

## 3. Sense checks

- **Units and currency.** Native currency is kept until conversion at the ECB reference rate of 2026-11-13 (1.1052 USD/EUR, 136.6 ISK/EUR). The base case is nominal. The verifier reproduces the base exactly with no inflation step, so none is applied. Per diem is in EUR per day, travel in EUR per participant (return), freight in USD/kg, and the Moon side in USD M per kg, converted to EUR. The price-per-kg set mixes nominal 2019-2026 USD; this is stated in the money rule.
- **Field campaign against published fees.** The MDRS crew fee is USD 3,500 per person per 2-week rotation, so USD 21,000 (EUR 19,001) for six people. The model's MDRS campaign is EUR 57k P50, and the fee is 36% of it. The Spanish lodging allowance (EUR 66 per night in Spain, 143 in the US) lies inside the published field-station lodging range of USD 10-139 per person per night (Zzyzx, WMRC). A two-week campaign for six at about EUR 13-19k in Spain and 27-57k abroad is the right order of magnitude.
- **Lunar delivery against actual task orders.** The 174 kg P50 of $243 M sits inside NASA's contracted Griffin/VIPER delivery prices ($199.5-322.8 M; that lander could carry 475 kg), so the order of magnitude is consistent. For 475 kg, linear scaling ($663 M) is 2-3.5 times the actual contracts ($190-323 M). The builder flags this, but the headline also called it a "lower bound"; that wording is fixed. For 11 kg, the linear $15 M assumes a shared ride, while a whole CLPS task order was $77.5-180.4 M at award. The flag text now says so.
- **Triangular skew.** The price-per-kg distribution is Tri(0.84, 1.10, 2.41). Its P50 (1.395) is above the set median (1.10) and above the OIG 2023 estimate (1.2), because one point (the 2026 IM award, 2.41) sets the long tail. At the OIG figure, the 174 kg delivery would be $209 M instead of $243 M (-14%). This is a declared ILLUSTRATIVE method, not an error.
- **Monte Carlo convergence.** The builder's check passes (mean and P90 within 0.5% between N/2 and N). An independent sampler with 10 times the draws and a different seed agrees within 0.41% on P10, P50 and P90 at every site, and within 0.25% on every Moon P50.
- **Linear-per-kg flag.** `LINEAR_PER_KG` is present on every output that contains the 11 kg class: `moon_cost_by_class`, `moon_vs_earth`, `earth_vs_moon.csv`, the Moon tornado rows, `voi.json` and the headlines.

### Can the sites be ranked?

Base P10-P90 bands, in EUR:

| Site | P10-P90 |
|---|---|
| Tabernas | 11.8-14.7k |
| Río Tinto | 11.9-14.7k |
| Bardenas | 13.2-16.0k |
| Teide and Lanzarote (identical) | 17.0-21.2k |
| Holuhraun | 24.7-30.3k |
| Atacama | 28.6-34.3k |
| Death Valley | 35.2-42.0k |
| MDRS | 53.9-77.9k |

Five tiers can be told apart: {Tabernas, Río Tinto, Bardenas} < {Teide, Lanzarote} < {Holuhraun, Atacama} < Death Valley < MDRS. Within a tier the sites are a tie. Tabernas and Río Tinto differ by EUR 21; Teide and Lanzarote are identical. Atacama and Death Valley are separated by only EUR 0.9k between bands. These tiers are now in `charts.site_costs.rank_tiers`.

Paired draws give P(A < B) = 1.000 for every adjacent pair. This is an artefact: every site shares the same generic weather and the same markup draws, so the model holds no site-specific uncertainty. It is not evidence that the order is certain.

The order also depends on the per-diem system. With US government rates (`upper_us_rates`):
- Atacama (47.1k) rises above Death Valley (38.3k).
- Holuhraun (49.4k) comes close to MDRS (52.8k).
- The Spanish sites spread from 25k to 44k.

What holds in both systems: every site is far below one lunar delivery. Under Spanish official rates, mainland Spain is cheapest and the US sites are dearest.

## 4. Wording: what was rewritten

| Headline or field | Problem | Now |
|---|---|---|
| `campaigns_per_delivery_mid` includes; `earth_campaign_range` includes | Not f-strings: raw `{people}`, `{A.val('vehicles_count')}` in the dashboard | Formatted. A guard in `bundle.py` now refuses any `{` or `}` left in headline text. |
| `campaigns_per_delivery_mid` sentence | Called the 174 kg linear estimate "a lower bound"; named Tabernas alone as cheapest; floor counts given to 5 digits | "If CLPS prices per kg scale linearly with mass ... counting the delivery only; at the median that equals about 3,600 (MDRS) to 17,000 (Tabernas and Río Tinto, a tie) one-off Earth field campaigns at official rates." |
| `moon_delivery_by_class` | "(lower bounds; ... linear scaling overstates the largest class)": a contradiction | States that 11 kg assumes a shared ride (whole task order $77.5-180.4 M) and that for 475 kg linear overstates (contracts $190-323 M). The must-not says it is a lower bound only on the whole cost of a lunar test, not on the delivery. |
| `earth_campaign_range` | Tabernas named cheapest (tied with Río Tinto); no band | Tie named, P10-P90 across sites added, the MDRS fee/lodging overlap and the tiers stated |
| `kg_moon_vs_air_cargo` | "one kg on the Moon costs ..." in the present tense (audit: not the price of a kg on the Moon today); "2026-08" | "The NASA OIG's estimate of about $1.2 million per kg for CLPS deliveries (based on 2023 task-order prices) is about 380,000 times the Xeneta global average air-cargo spot rate for August 2026 (3.13 USD/kg)." |
| `cost_per_successful_test_multiplier` | Called a median the "expected" cost | "median; the mean is 2.3-2.8 times", dated "2019 and 14 November 2026" |
| `facility_per_test_week` -> `facility_agreements` | Presented a per-test-week price next to the lunar delivery | Whole-agreement value, with the audit sentence verbatim |
| `late_fix_escalation` | Headline value (operations/test 1.4-19x) not in the sentence | Sentence now states it |
| `per_diem_gap` | "abroad" was ambiguous and the years were merged | Names the sites and the State Dept table date; "2002 (abroad) or 2005 (Spain)" |
| `meta.answer_in_one_line`, `moon_vs_earth` takeaway | "thousands of Earth campaigns": false for the 11 kg class (235-1,056) | "hundreds (11 kg) to tens of thousands (larger rovers)"; the 475 kg class is quoted at the actual VIPER contracts (2,700-22,000 campaigns) |
| `site_costs`, `site_components`, `tornado`, `price_per_kg`, `facility_per_test`, `landing_outcomes`, `landing_posterior` takeaways | Tie hidden; "per diem and travel dominate" was false (4x4s outweigh travel in mainland Spain, and the crew fee is largest at MDRS); weather not called ILLUSTRATIVE; undated tallies | Rewritten |
| `LOWER_BOUND_MOON`, `LINEAR_PER_KG` flag text (`core.py`); `model/README.md` | Same overclaims | Aligned |

Headlines checked and left as they were: `price_per_kg_range`, `landing_success`, `viper_contracted`, `dsn_viper`, `voi_mid_high_twin`, `mars_outcomes`, `fx`, `top_driver`. Each is an audit sentence or carries its date, what it includes and excludes, and its must-not.

## 5. What remains uncertain (not fixed: these are modelling choices, flagged)

1. **Shared weather.** The base case uses one generic ILLUSTRATIVE weather range for every site, so the ranking reflects official rates and distance, not site conditions. Every workable-days row is confidence low.
2. **VOI for the VIPER class.** L = linear delivery P50 ($663 M, which overstates the delivery) + $505.4 M project cost. The VOI is ILLUSTRATIVE anyway, but the VIPER-class L would be about $830 M with the Feb 2024 contract instead.
3. **Road freight at the mainland sites.** The car-mileage proxy does not grow with the prototype mass, so in M6 the Earth side for the 475 kg class at Tabernas, Río Tinto and Bardenas is understated. This is negligible against the Moon side.
4. **MDRS.** The crew fee may already include habitat lodging (up to about EUR 12.9k counted twice). The P90 jumps to EUR 78k because a workable fraction below 10/14 (about 14% of draws) needs a second rotation.
5. **The 2.41 USD M/kg point.** The IM 2030 award sets the top of the price-per-kg triangle alone and pulls the P50 above the OIG estimate.
6. **Landing attempts after June 2025.** The audit could check non-US attempts only on agency English news pages. Re-check on pitch day.
7. **Order under the US-rates scenario.** The order of the overseas sites changes there (section 3).
