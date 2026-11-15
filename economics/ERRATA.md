# Errata corrected in the repository copy

The package was delivered on 2026-11-15 at 14:42 CET as `Economic_analysis_EN.zip`
(SHA256 `f0f9f03d261af4fb2c1104e89f7ce3c1da91370a4ae1286d146f9e034aca8a16`). The checksum of every
delivered file, taken before any edit, is in [`SHA256SUMS.txt`](SHA256SUMS.txt). Run
`sha256sum -c SHA256SUMS.txt` inside this folder: the only files that should fail are the four text
files listed below (`README.md`, `theoretical_framework.md`, `earth_tests_summary.md`,
`report_src/pdf_en.py`). `ERRATA.md` and `SHA256SUMS.txt` were added here.

Only wording was corrected. No figure in any data file was changed, and no binary (PDF, XLSX, PNG)
was edited or regenerated. Regenerating the binaries is up to the team.

---

## 1. Wrong section cross-reference in `theoretical_framework.md`

**Deciding fact.** In `theoretical_framework.md` the historical failure rate p₀ (5 of 16 Mars surface
elements = 31.25 %) and the in-situ test cost C_T^X (demonstrator mission, Mars Pathfinder 613 M$) are
both worked out in **section 3, "Numerical example"**. Section 4 is "Supporting theory" and gives neither.

| File:line | Before | After |
|---|---|---|
| `theoretical_framework.md:19` | `\| p₀ \| … \| historical rate (section 4) \|` | `\| p₀ \| … \| historical rate (section 3) \|` |
| `theoretical_framework.md:23` | `\| C_T^X \| … \| cost of a demonstrator mission (section 4) \|` | `\| C_T^X \| … \| cost of a demonstrator mission (section 3) \|` |

Not an erratum: `earth_tests_summary.md:107` ("see section 4") points to its own section 4, "Failures
that Earth testing detected or could have detected", which does hold the Curiosity wheels row. It is
correct and was left as it was.

Binaries: neither the PDF nor the workbook contains this cross-reference.

---

## 2. Cost-of-error range in operations: unified to **29–1,615×**

The package gave the operations multiplier from Stecklein et al. (2004) in three different forms:
">1,600×" ("more than 1,600"), "29 to more than 1,615" and "29× to more than 1,500×".

**Deciding data.**

- `data/macro_error_cost_escalation.csv`, row `Operations`: `method1_bottom_up = 29`,
  `method2 = 157–186`, `method3_hypothetical_project = 1615`, **`systems_composite_min = 29`,
  `systems_composite_max = 1615`** (Stecklein Tables 12–13). The same file gives the other phases as
  design 3–8, manufacturing 7–16 and integration and test 21–78, which are the ranges the package
  quotes everywhere.
- `dashboard/outputs/escalation.csv`: row `Table 13, systems_composite_of_methods_1_3, Operations`
  gives 29 and 1615. Row `Abstract, abstract_summary, Operations` gives 29 and 1500.
- `data/earth_tests.csv`, rows 38–39 (data lines 37–38): `29-1500`, note "Upper end: more than
  1,500x". These rows cite the study's **abstract**, which rounds the upper end down to "more than
  1,500×".

**Computation.** Range = [min(composite), max(composite)] = [min(29, 29), max(1615, 1615)] = **29–1,615×**.
The abstract's "more than 1,500×" is a rounded wording of the same table maximum: 1,615 > 1,500, so the
two agree. Both forms are wrong: "more than 1,600" is not a figure in the study, and "more than 1,615"
is wrong because 1,615 is the table maximum, not a lower bound. The report chart `report_src/g3_escalation.png`
already reads "29–1615×", and so does page 3 of the PDF. The prose now matches them.

| File:line | Before | After |
|---|---|---|
| `README.md:13` (Key results) | `…costs between 29 and more than 1,600 times what it costs in the requirements phase…` | `…costs between 29 and 1,615 times what it costs in the requirements phase…` |
| `theoretical_framework.md:102` | `\| Operations \| 29 to more than 1,615 \|` | `\| Operations \| 29 to 1,615 \|` |
| `earth_tests_summary.md:99` | `- **29× to more than 1,500× in operations**.` | `- **29× to 1,615× in operations** (Tables 12–13; the abstract rounds the upper end to "more than 1,500×").` |
| `earth_tests_summary.md:140` | `…(21-78× in I&T, up to more than 1,500× in operations)…` | `…(21-78× in I&T, up to 1,615× in operations)…` |
| `report_src/pdf_en.py:27` (string literal of the PDF's Thesis paragraph; script not run) | `…costs between 29 and more than 1,600 times what it would cost…` | `…costs between 29 and 1,615 times what it would cost…` |

**Deliberately not changed** (these are data or model inputs, not prose):

- `data/earth_tests.csv` rows 38–39 (`29-1500`, "more than 1,500x"). They are the data record of
  the abstract's wording.
- `dashboard/README.md:76` (M7), `dashboard/outputs/dashboard_data.json` (headline `includes` and
  `allowed_sentence`: "29-1,500"), `dashboard/outputs/escalation.csv` and `VERIFICATION.md:52`.
  The dashboard model M7 uses the **abstract row (29–1,500)** on purpose. Its derived ratios
  (operations/test 1.38–19.2, widest 0.372–71.4) depend on it, so changing the wording there would
  change model figures. These are labeled as the abstract summary and are consistent with it.

**Still inside binaries** (not edited):

- `Economic_feasibility_Earth_vs_space_testing.pdf`, page 1, "Thesis" paragraph: "between 29 and
  more than 1,600 times". Page 3 already says "29–1,615 in operations".
- `Space_testing_cost_data.xlsx`, sheet "Tests on Earth" (mirror of `earth_tests.csv`): `29-1500`,
  "more than 1,500x" and "operations 29x to more than 1,500x". This sheet holds data from the abstract,
  so it is consistent and was left as it was. Sheet "Error cost escalation" holds 1615.

---

## 3. Break-even threshold q*: **0.37 % (InSight) and 0.84 % (Pathfinder)**

The prose (README, `theoretical_framework.md` section 3, PDF text, `pdf_en.py`) says 0.37 % and 0.84 %.
The legend of the savings chart (`report_src/g5_savings.png`, also on PDF page 4) says 0.38 % and 0.83 %.

**Deciding data.** q* = C_T / (p₀·C_M), with C_T = 1.6 M$ and p₀ = 0.3125 (5/16,
`data/macro_mars_failures_by_decade.csv`, 1990s–2020s surface elements). C_M comes from
`data/macro_mission_cost_vs_outcome.csv` (2025 M$): Pathfinder 613, InSight 1,365.5, Curiosity 4,020.6.

| Mission | C_M | q* exact | rounded to 2 dp | `q_breakeven_threshold` in `macro_illustrative_savings_model.csv` | legend (`"%.2f"` of the CSV value) |
|---|---|---|---|---|---|
| Pathfinder | 613.0 | 1.6/191.5625 = 0.8352 % | **0.84 %** | 0.00835 | 0.83 % |
| InSight | 1,365.5 | 1.6/426.71875 = 0.3750 % (0.374954…) | **0.37 %** | 0.00375 | 0.38 % |
| Curiosity | 4,020.6 | 1.6/1,256.4375 = 0.1273 % | **0.13 %** | 0.00127 | 0.13 % |

The CSV stores q* rounded to three significant figures. `report_src/charts_en.py:54` then rounds that
stored value again (`q_breakeven_threshold*100:.2f`), and the double rounding gives 0.83 / 0.38.
Computed straight from the sourced inputs, the values are 0.84 / 0.37, which is what the text says.
`dashboard/outputs/voi.json` does not hold this q*, because it is a different model (M4, EVSI tree).

**Version kept: 0.37 % / 0.84 %.** No text file needed a change: all prose already used it.

**Still inside binaries** (not edited): `report_src/g5_savings.png` legend ("InSight … q*=0.38 %",
"Mars Pathfinder … q*=0.83 %") and the same chart on page 4 of the PDF. The workbook sheet "Savings
model" stores the same 3-significant-figure values as the CSV (0.00375, 0.00835). These are numbers
only, with no legend. To fix the chart when the team regenerates it, `charts_en.py` should compute the
legend value as `1.6/(p0*C_M)` from the row's own columns instead of reformatting the rounded column.
That code was not changed here.
