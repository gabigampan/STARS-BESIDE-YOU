# Guide to building the economics dashboard

Internal team document, originally written in Spanish (this is the English translation of `GUIA_DASHBOARD_ECONOMIA.md`). Everything delivered to NASA (dashboard texts and labels) is in English; that is why the titles and sentences in the data file already come in English.

## Which file to use

Just one: `economics/outputs/dashboard_data.json` (in this package: `dashboard/outputs/dashboard_data.json`). It comes fully calculated and verified; the dashboard does not have to calculate anything, only draw and filter. The same tables are also available as CSV in the same folder, in case you prefer a spreadsheet.

| Block of the file | What it contains |
|---|---|
| `meta` | The question, the answer in one line, what the calculation includes and excludes, the cut-off date (2026-11-14) and the exchange rate used (1.1052 USD per euro, ECB, 2026-11-13) |
| `headlines` (16) | The headline figures. Each comes with a value, a range, `allowed_sentence` (the sentence the data allow) and `must_not_mean` (what it must not be made to say) |
| `charts` (21) | One dataset per chart, each with `title`, `unit`, `takeaway` (the conclusion in one sentence), `rows` (the rows to draw), `notes`, `flags` and `depends_on_illustrative` |
| `sites` (9) and `mass_classes` (3) | The sites with coordinates and the three prototype sizes (11 kg, 174 kg, 475 kg) |
| `voi` | The value-of-information example, all illustrative |
| `flags` and `sources` | The meaning of each flag and the record for each source |

## Proposed order, for someone who does not know the project

1. **The answer.** `meta.answer_in_one_line` and three big figures from `headlines`: `campaigns_per_delivery_mid`, `moon_delivery_by_class` and `earth_campaign_range`.
2. **Moon vs. Earth.** Chart `moon_vs_earth`, with a prototype-size selector. Use a logarithmic scale: the two sides differ by between a hundred and tens of thousands of times, and on a linear scale the Earth bar is not visible.
3. **What a kilo to the Moon costs.** `price_per_kg` (each contract divided by its payload) and `viper_contracted` (what NASA actually contracted for VIPER).
4. **And sometimes it fails.** `landing_outcomes` (5 of 13 fully successful) and the effect on the cost per successful landing (`headlines`, `cost_per_successful_test_multiplier`).
5. **What a campaign costs at each site.** `site_costs` with P10–P90 range bars, `site_components` stacked by cost item, and `site_map`.
6. **What drives that cost.** `tornado`, with a site selector.
7. **Why test first.** `escalation` (how much more it costs to fix late) and `voi_fidelity`, labeled as an illustrative example.

Optional detail: `per_diem_compare`, `workable_days_monthly`, `seasonality`, `dsn_accounting`, `facility_per_test`, `mc_histogram` and `mc_convergence`.

## Six rules the dashboard must not break

1. **Headlines:** use `allowed_sentence` as is or shorter, never stronger. Whatever `must_not_mean` says is not claimed anywhere.
2. **Assumptions in view:** if `depends_on_illustrative` is true, the chart carries a visible text label ("illustrative assumption"), not just a color.
3. **Ties:** in `site_costs`, use `rank_tiers`. Within the same tier the sites are tied and are not ranked (Tabernas, Río Tinto and Bardenas go together; Teide and Lanzarote come out identical).
4. **What is not added:** DSN communications and NASA facility agreements go in separate panels; they are never added to the delivery cost or the campaign cost.
5. **Dates:** success and failure counts always carry "2019 to 14 November 2026".
6. **What each side is:** the Moon side counts only the delivery, so it is a minimum of the total cost of testing there. The Earth side is one campaign at official rates and excludes salaries, insurance, customs and the prototype.

## Four limits you should know before designing

- **Weather is the same for all sites in the base case.** The station data ended up with low confidence (no wind, and no data for Atacama or Holuhraun), so the model uses the same illustrative range at all nine. The site ranking reflects distance and rates, not weather. It will change when NASA POWER data are available.
- **The price per kilo is applied linearly.** For the VIPER class that overestimates: the actual contracts were 190 to 323 million dollars, compared with 662 from the linear calculation. At that size, show the contracts.
- **Earth costs are official reimbursement rates, not market prices.** The file also includes the scenario with US per diems, which raises the Spanish sites to between 25,000 and 44,000 euros and changes the order of the overseas ones.
- **The value of information is an example.** Probability, sensitivity and redesign cost are made up to show the method; only the shape is defended (it rises with fidelity and never exceeds the ceiling).

## How to regenerate the data

`python3 economics/model/run_all.py` recalculates everything in about two seconds and gives the same result (seed 42). Assumptions are changed in `economics/config/model_assumptions.json`; the workable-day thresholds, in `economics/config/campaign.json`.
