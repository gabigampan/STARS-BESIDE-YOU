# R1 - VIPER rover preset: official sources

Task R1, Stars Beside You (NASA Space Apps 2026). Prepared 2026-11-14. Every source below was opened on **2026-11-14** (access date for all rows unless stated otherwise).
Evidence levels: **MEASURED** = a figure printed in an official or primary document; **DERIVED** = computed here from a MEASURED figure by the formula shown; **MODELLED** = an estimate or simulation (none used here).
The team repository was not readable from this session, so the rover config is described only as the task gave it (slope <= 15 deg on P90 slope; tolerances 300 m: 5 deg / 10 m, 5 km: 2 deg / 30 m).

## Source key

| Key | Document | URL |
|---|---|---|
| B25 | NASA, "VIPER Industry Day: Technical Briefing, Questions and Answers", Feb 13, 2025 (97 pp.) | https://assets.science.nasa.gov/content/dam/science/psd/lunar-science/documents/2025-02-13_VIPER_Updated_Technical_Briefing_Presentation-Shared.pdf |
| F26 | T. Fong (NASA Ames, VIPER Rover Deputy Manager), "Volatiles Investigating Polar Exploration Rover", 29 April 2026, NTRS 20260002876 | https://ntrs.nasa.gov/api/citations/20260002876/downloads/viper-2026-04-29_v2.pdf |
| M24 | B. Bluethmann, "VIPER Rover Overview and Mobility and Hardware", Nov 14, 2024 (LSIC), NTRS 20240013903 | https://ntrs.nasa.gov/api/citations/20240013903/downloads/LSIC_2024-Tech%20Infusion_Panel-VIPER_Mob-HW.pdf |
| F22 | T. Fong, "Volatiles Investigating Polar Exploration Rover", 2 November 2022, NTRS 20220016618 | https://ntrs.nasa.gov/api/citations/20220016618/downloads/viper-2022-11-02.pdf |
| SRI | NASA Science, VIPER "Rover and Instruments" page | https://science.nasa.gov/mission/viper/rover-and-instruments/ |
| SMP | NASA Science, VIPER mission page | https://science.nasa.gov/mission/viper/ |
| OIG22 / OIG24 | NASA OIG IG-22-010 / IG-24-013 (already in team economics data; re-opened via the team's raw snapshots and quotes) | https://oig.nasa.gov/docs/IG-22-010.pdf ; https://oig.nasa.gov/wp-content/uploads/2024/06/final-report-ig-24-013-nasas-commercial-lunar-payload-services-initiative.pdf |

"p." = PDF page number (checked with pdftotext page by page).

## 1. VIPER physical and operational parameters

| Parameter | Value (level) | Source, locator | Exact quote |
|---|---|---|---|
| Mass, launch | 490 kg (MEASURED) | B25 p.46; M24 p.2 | "Mass: launch = 490kg, roving = 447kg"; M24: "Launch: 490 kg (with lander I/F), roving: 447 kg" |
| Mass, roving | 447 kg (MEASURED); "~450 kg" rolling mass on B25 p.17 | B25 p.46, p.17 | "Rolling Mass: ~450kg" |
| Mass, older/other figures | ~500 kg (OIG round figure); 475 kg contracted delivery mass (+15 kg option); "approx. 490 kg" (2022) | OIG24 p.25; OIG22 p.22; F22 p.13 | "a large mission weighing approximately 500 kilograms (kg)"; "deliver VIPER at a weight of 475 kilograms (1,047 pounds)"; "Mass: approx. 490 kg" |
| Dimensions (L x W x H) | 1.7 m x 1.7 m x 2.5 m (MEASURED, current) | B25 p.17 and p.46; M24 p.2 | "Dimensions: 1.7m x 1.7m x 2.5m" |
| Dimensions, conflicting | 1.8 x 1.8 x 2.6 m (2022); 1.5 m L/W, 2.5 m tall (web page) | F22 p.13; SRI | "Approx. 1.8m x 1.8m x 2.6m (L x W x H)"; "Measuring 8 feet (2.5 meters) tall and 5 feet (1.5 meters) in length and width." |
| Wheel count | 4 | M24 p.4; F26 p.10 | "Four-wheel architecture"; "Independent Wheel Modules (4x)" |
| Wheel diameter / width | 50 cm diameter, 20 cm wide, 2.5 cm grousers | B25 p.47; F26 p.10 | "Wheels: 50 cm diameter with 2.5 cm grousers"; "50 cm diameter, 20 cm wide" |
| Wheelbase | **no official source found** | - | Only overall footprint (1.7 x 1.7 m) is published. |
| Track width | **no official source found** | - | as above |
| Ground clearance | 7 to 43 cm, adjustable (MEASURED) | B25 p.47; M24 p.4 | "Adjustable ground clearance from 7- 43cm" |
| Centre of gravity height | **no official source found** | - | Not in B25, F26, M24, F22, SRI, SMP. |
| Suspension / steering travel | suspension +/-40 deg, steering +/-50 deg | F26 p.10 | "Suspension: ± 40º, 200 N⋅m torque"; "Steering: ± 50º, 130 N⋅m torque" |
| Top speed | 20 cm/s (0.5 mph) | B25 p.17, p.47; F26 p.5 | "Top Speed: 20cm/s (0.5MPH)" |
| Top speed, web page | 0.45 mph (0.72 kph) | SRI | "VIPER will drive at about 0.45 mph (0.72 kph)" |
| Top speed, DERIVED | 20 cm/s x 3.6 = 0.72 km/h (consistent with SRI) | - | - |
| Prospecting / nominal speed | 10 cm/s (0.25 mph) | B25 p.17; F26 p.22 | "Prospecting Speed: 10cm/s (0.25MPH)"; "10 cm/s drive speed while prospecting (instrument limit)" |
| Speed made good | 0.8 cm/s | F26 p.5 | "0.8 cm/s “Speed Made Good”" |
| Slope capability | **15 deg** (requirement / design limit) | M24 p.4; B25 p.17, p.47; F26 p.22; F22 p.13; SRI | M24: "Slopes up to 15 deg (reqt)"; B25: "Slopes up to 15 deg and obstacles to 15 cm"; F26: "15 deg slopes + 20 cm step obstacles (design limit)"; SRI: "Capable of traversing an incline of as much as 15 degrees." |
| Slope test (not a limit) | slip testing on a 30 deg slope | F26 p.16 | "Slip Testing (30° Slope)" (slide title only; no claim that 30 deg is operable) |
| Obstacle size | 15 cm (requirement) **vs** 20 cm (design limit) - sources differ | M24 p.4, B25 p.17 vs F26 p.22, F22 p.13 | "Obstacles to 15 cm (reqt)" vs "20 cm step obstacles (design limit)"; F22: "20 cm obstacles, 15 deg slopes" |
| Hazard detection | 8 m range for obstacles > 10 cm | B25 p.48 | "Up to 8m range for obstacles greater than 10 cm" |
| Power source / array output | solar arrays + battery; 450 W corner-facing or 320 W per array | B25 p.46 | "Solar generation: 450W (corner-facing) or 320W per array" |
| Battery | 5420 W-hr (beginning of life at 0 C) | B25 p.46 | "Battery capacity (beginning of life @ 0C): 5420 W-hr" |
| Shadow endurance | 50+ h hibernation; 9 h ops in PSR | B25 p.46 | "50+ hours survival (hibernation) in low power mode"; "9 hours ops in Permanently Shadowed Region (PSR)" |
| Drill (TRIDENT) depth | 1020 mm maximum; "1 m" in summaries | B25 p.39; SMP | "Maximum Drill Depth (mm) 1020"; SMP: "a 3.28-foot (1-meter) drill" |
| Mission duration | 100 days (releases) / 5-6 lunar days (B25) / 4+ lunar days, ops Sept 2027 to Jan 2028 (F26) | NASA release 2025-09-19; B25 p.30; F26 p.5, p.42 | "its 100-day mission"; "5-6 lunar days of operations"; "4+ lunar days near Nobile crater"; "Sept 2027 Landing / start operations ... Jan 2028 End of surface operations" |
| Traverse distance | 20 km, potential 30+ km | F26 p.5; Oct 2026 article | "20 km of traverse distance (with potential for 30+ km)"; "will travel more than 18 miles (30 kilometers)" |
| Landing site | Mons Mouton, west of Nobile crater | SMP; NASA release 2021-09-20 | SMP: "delivered to Mons Mouton by a Blue Origin Blue Moon MK-1 lander"; 2021: "will land near the western edge of the Nobile Crater" |
| Landing site coordinates | "approx. 84.6°S, 31.0°W" (F26) **vs** Mons Mouton centre -84.60, +31.00 East (USGS) | F26 p.5; https://planetarynames.wr.usgs.gov/Feature/16070 | F26: "4+ lunar days near Nobile crater (approx. 84.6°S, 31.0°W)"; USGS: "Center Latitude -84.60 °", "Center Longitude 31.00 °", "Planetographic, +East, -180 - 180", "Diameter 130.00 km" |
| Communications | X-band direct-to-Earth; gimballed HGA + fixed LGA | B25 p.46; SRI | "Communications: X-band DTE/DFE"; "Gimballed high gain antenna, fixed low gain antenna"; SRI: "X-band communications system that connects directly with Earth" |
| Data rates | TX 250 sps / 8 Msps; RX 250 sps / 75 ksps | B25 p.46 | "Transmit: 250sps/8Msps (min/max)"; "Receive: 250sps/75ksps (min/max)" |
| Localisation | absolute 20 m; relative 3 m over 224 m (95%) | B25 p.48 | "Absolute localization: 20m (95% confidence)"; "Relative localization: 3m over 224m (95% confidence)" |
| Instruments | NSS, NIRVSS, MSolo, TRIDENT (count shown as 4 on SMP sidebar; body text says three instruments + drill) | SMP; B25 p.45 | SMP: "using its three instruments and a 3.28-foot (1-meter) drill" |

Notes. The USGS Gazetteer footprint polygon for Mons Mouton runs through longitudes around +43 to +53 E, and Nobile crater is centred at "-85.28 °" / "53.27 °" East (https://planetarynames.wr.usgs.gov/Feature/4321), so the "31.0°W" in F26 looks like a sign error; this is an inference, not an official correction. Use the USGS value (84.6 S, 31.0 E) for the feature centre, and note that NASA has not published the exact touchdown point in anything found.

## 2. Programme status (as of 2026-11-14)

| Date | Event | Source | Exact quote |
|---|---|---|---|
| 2021-09-20 | Landing site named (Nobile region), 100-day mission, then on Griffin / Falcon Heavy | https://www.nasa.gov/news-release/nasas-artemis-rover-to-land-near-nobile-region-of-moons-south-pole | "will land near the western edge of the Nobile Crater at the Moon's South Pole"; "100-day journey" |
| 2024-07-17 | NASA intends to discontinue VIPER (RELEASE24-094) | https://www.nasa.gov/news-release/nasa-ends-viper-project-continues-moon-exploration/ | "NASA announced Wednesday its intent to discontinue development of its VIPER (Volatiles Investigating Polar Exploration Rover) project." Reasons: "cost increases, delays to the launch date, and the risks of future cost growth" |
| 2024-07-17 | Griffin Mission One continues without VIPER | same | "The landing without VIPER will provide a flight demonstration of the Griffin lander and its engines." |
| 2025-02-13 | NASA Industry Day technical briefing (B25) offering the rover system | B25 p.1-2 | "VIPER Industry Day: Technical Briefing, Questions and Answers Feb 13, 2025" |
| 2025-09-19 | Blue Origin selected, CLPS task order CS-7, Blue Moon MK1, landing late 2027 | https://www.nasa.gov/news-release/nasa-selects-blue-origin-to-deliver-viper-rover-to-moons-south-pole/ | "Blue Origin will deliver VIPER to the lunar surface in late 2027, using a second Blue Moon MK1 lander"; "The CLPS task order has a total potential value of $190 million."; delivery is an option: "NASA will make the decision to exercise that option after the execution and review of the base task" |
| 2026-04-29 | Planned schedule (NASA Ames presentation) | F26 p.42 | "Jan 2027 Flight rover integration to MK1 lander (SN-002)"; "Aug 2027 Launch (Cape Canaveral)"; "Sept 2027 Landing / start operations"; "Sept 2028 End of mission (data release to PDS)" |
| 2026-10-20 | Rover fully built, final testing at JSC | https://www.nasa.gov/missions/moon-base/nasa-provides-progress-update-on-moon-base-rovers/ | "The VIPER rover is currently at NASA’s Johnson Space Center in Houston where it is fully built and undergoing final testing before traveling to NASA’s Kennedy Space Center in Florida for launch to the Moon." |

No official source found that NASA has exercised the CS-7 delivery option; the 2026-10-20 article says the rover "will embark on a mission to the lunar South Pole region in 2027".

## 3. Slope limits for lunar surface mobility (official sources)

| Vehicle / context | Slope figure | Level | Source | Exact quote |
|---|---|---|---|---|
| VIPER | 15 deg (requirement / design limit) | MEASURED (spec) | M24 p.4; F26 p.22; B25 p.47; SRI | see section 1 |
| Apollo LRV | about 25 deg climb/descend | MEASURED (historical) | https://www.nasa.gov/image-detail/amf-7022567/ (image dated 1971-08-01) | "It could climb and descend slopes of about 25 degrees." |
| Apollo LRV (crew account) | above 25 deg | MEASURED (narrative) | NASA SP-350, ch. 14 appendix "Touring the Moon", https://www.nasa.gov/wp-content/uploads/static/history/SP-350/ch-14-8.html | "The Rover's mobility was quite high; it could climb and descend slopes above 25°." |
| Apollo LRV (design) | 20-23 deg favourable, max 25 deg | MEASURED (citing design docs) | NASA NTRS 20250011301, LPSC 57 abstract (Jacob et al.), https://ntrs.nasa.gov/citations/20250011301 | "The LRVs were designed to navigate a 20 – 23° slope in "favorable conditions" with a max of 25°." |
| Apollo LRV geometry (for comparison) | wheelbase 2.3 m, clearance 36 cm, mass 210 kg | MEASURED | https://nssdc.gsfc.nasa.gov/planetary/lunar/apollo_lrv.html | "The frame was 3.1 meters long with a wheelbase of 2.3 meters."; "Fully loaded the LRV had a ground clearance of 36 cm." |
| South Pole terrain (architecture) | >10 deg common; up to 20 deg on landing-to-habitat traverses | MEASURED (planning statement) | NASA, "Lunar Mobility Drivers and Needs", 2024 ACR white paper, https://www.nasa.gov/wp-content/uploads/2024/06/acr24-lunar-mobility-drivers-and-needs.pdf | "Slopes of more than 10 degrees are common at the lunar South Pole"; "Traverses from landing zones to habitation zones could encounter slopes of up to 20 degrees." |
| Lunar Terrain Vehicle (LTV) requirement | **no official source found** | - | Searched nasa.gov and NTRS; only a secondary blog states 20 deg. The 2026-10-20 NASA LTV update gives range (6 km/day, 10 km per charge) but no slope. | - |

Verdict for the audit: the 15 deg VIPER limit is **supported** by four NASA documents (labelled "reqt" and "design limit"), so "estimate" can be replaced by a sourced value. Caveat: it is a rover-scale capability; the team applies it to a P90 slope from a DEM at 300 m or 5 km. See section 4: slope magnitude falls as baseline grows, so 15 deg on a 300 m P90 slope is not the same terrain as 15 deg at wheel scale.

## 4. Slope and roughness definitions in the LOLA literature

**Rosenburg et al. 2011**, "Global surface slopes and roughness of the Moon from the Lunar Orbiter Laser Altimeter", J. Geophys. Res., 116, E02001, doi:10.1029/2010JE003716, published 3 February 2011 (metadata confirmed via api.crossref.org; text read from the publisher PDF hosted by Caltech, https://authors.library.caltech.edu/records/ew7nz-d9e91/files/Rosenburg2011p12818J_Geophys_Res-Planet.pdf; the Wiley page returned 403).

| Quantity | Definition (exact quote) | Units | Baselines |
|---|---|---|---|
| Roughness parameters used | "median absolute slope, both directional (along‐track) and bidirectional (in two dimensions); median differential slope; and Hurst exponent, over baselines ranging from ∼17 m to ∼2.7 km" (abstract) | slopes: angle | ~17 m to ~2.7 km |
| RMS slope | "it is defined as the RMS difference in height, Dz, between each pair of points (also known as the deviation, n) divided by the distance between them, Dx" (sec. 3.1; Greek letters lost in text extraction: deviation = nu, D = Delta) | angle (rise/run) | shot spacing "∼57 m" |
| Median differential slope | "it isolates roughness features on the order of L by subtracting the point‐to‐point slope at twice the given baseline" (sec. 3.2) | angle | "∼57 m) to 25 shot spacings apart (∼1.4 km)" |
| RMS deviation / deviogram | "We calculate the RMS deviation for a range of baselines from ∼57 m to ∼2.7 km (1 to 50 shot spacings) and analyze the deviogram, or structure function" (sec. 3.3) | **metres** (height difference; DERIVED from the definition, not printed as a unit) | 57 m to 2.7 km |
| Hurst exponent H | deviation scales as (Dx)^H; "H can thus be estimated as the slope of a best‐fit line to log[n(Dx)] versus log(Dx)" | dimensionless | fit range 57 m to breakover |

DERIVED consequence: RMS slope = nu(Dx)/Dx scales as Dx^(H-1); with the paper's median H of 0.95 (highlands) and 0.76 (maria) (abstract), slopes fall as the baseline grows. A 15 deg threshold therefore means different terrain at 300 m and at 5 km.

**Archived products**

| Product | What it holds | Units / grid | Archive | Exact quote |
|---|---|---|---|---|
| MAS_57M_16, MAS_225M_16, MAS_560M_16 (.IMG/.LBL), HE_8 | Median absolute along-track slope at 3 baselines; Hurst exponent | degrees; 16 px/deg (HE: 8 px/deg); DATA_SET_ID "LRO-L-LOLA-16-GDR-V1.0" | PDS Geosciences Node, https://pds-geosciences.wustl.edu/lro/lro-l-lola-3-rdr-v1/lrolol_1xxx/extras/fractal/ | README: "Three products are provided for baselines of 57m, 225m, and 560m, with values then interpolated to a 16 pixels per degree grid."; label: "UNIT = DEGREE"; "these files are made available, but are unsupported by the LOLA Science Team." |
| Same, NASA GSFC PGDA page | as above | degrees | https://pgda.gsfc.nasa.gov/products/70 | "Map values are in units of degrees." |
| ODE help page RMMAS | same product | degrees | https://ode.rsl.wustl.edu/moon/pagehelp/Content/Missions_Instruments/LRO/LOLA/RMMAS.htm | states baselines "57 m, 225 m, and 450 m" - **conflicts** with the PDS README/file names (560 m); trust the file names |
| LDRM polar roughness (Barker et al. 2025, PSJ 6, 83, doi 10.3847/PSJ/adbc9d) | "the spread of height residuals of individual LOLA spots around a plane fit to the LDEM" within a window whose diameter equals the baseline; also RMSD "RMS height deviation (in meters)" | **metres**; baselines 100, 200, 400, 800, 1600 m; 50 and 1000 m/px; poles only | NASA GSFC PGDA, https://pgda.gsfc.nasa.gov/products/98 (data doi 10.60903/gsfcpgda-lola-poles) | file names e.g. "LDRM_80N_50MPP_ADJ_ROUGH_100M.TIF"; "the 50-m baseline roughness is taken from the LOLA single-shot roughness product" on PDS |

Verdict for the audit: "roughness in metres at a baseline" **is** a standard LOLA quantity (RMS deviation in Rosenburg 2011; plane-fit height spread / RMSD in Barker et al. 2025), but no official product found uses a 300 m or 5 km baseline: PDS slope maps are 57/225/560 m, polar roughness maps 100-1600 m. The team must say which definition it computes on Earth DEMs (RMS deviation between point pairs vs residual spread about a plane) because the two are not numerically identical. Slope at a baseline in LOLA work is an angle in degrees (median absolute, RMS, or differential), not P90; P90 is the team's own statistic.

## Verification log

| Opened | Result |
|---|---|
| grep -ril viper economics/data/processed (9 files) | Reused OIG22/OIG24 mass and 2024-07-17 / 2025-09-19 / 2026-10-20 status rows; re-opened the three NASA pages live (OK); OIG PDFs not re-downloaded, quotes taken from team raw snapshots as recorded |
| B25, F26, M24, F22 PDFs (curl into scratchpad/stars/r1_*) | OK, text extracted with pdftotext; page numbers checked per page |
| science.nasa.gov VIPER main + rover-and-instruments | OK |
| nasa.gov releases 2021-09-20, 2024-07-17, 2025-09-19; 2026-10-20 article | OK |
| svs.gsfc.nasa.gov/4937 | OK ("an area west of Nobile crater") |
| planetarynames.wr.usgs.gov Feature/16070 (Mons Mouton), 4321 (Nobile) | OK; Feature/15961 tried first was Oort (Pluto), not relevant |
| NSSDC LRV page; SP-350 ch.14; nasa.gov image amf-7022567; NTRS 20250011301 | OK |
| ALSJ LRV Operations Handbook Pt1 (nasa.gov/wp-content/.../LRV_OpsNAS8-25145Pt1.pdf) | FAILED: HTTP 404 |
| NTRS 19730002507 | Opened; scale-model LRV manual (WES 1972), not usable |
| LTV requirement on nasa.gov / NTRS | not found (2 searches) |
| acr24 Lunar Mobility Drivers and Needs PDF | OK |
| agupubs.onlinelibrary.wiley.com Rosenburg 2011 | FAILED: HTTP 403; used Crossref metadata + Caltech-hosted publisher PDF |
| ui.adsabs.harvard.edu | FAILED: HTTP 405 |
| PDS fractal directory, README_FRACTAL.TXT, MAS_225M_16.LBL | OK |
| PGDA products 70 and 98; ODE RMMAS help | OK |
| NASA POWER API | not called (per limits) |

## Open questions for the team

1. Replace "15 deg (estimate)" with "15 deg, NASA requirement/design limit (M24 p.4, F26 p.22)"? Note it is rover-scale, not DEM-baseline.
2. Obstacle height: use 15 cm (requirement, M24/B25) or 20 cm (design limit, F26/F22)? Suggest storing both.
3. Wheelbase, track width and CG height have no official source: leave them null, or derive an upper bound from the 1.7 m footprint and label DERIVED?
4. Which mass for the preset: 447 kg roving (B25) is the mobility-relevant figure; 490 kg is launch mass.
5. How exactly is "roughness (m)" computed in the pipeline (RMS deviation of point pairs, detrended residual std, or something else), and is the 300 m / 5 km baseline the DEM pixel size or the lag?
6. Is the P90 slope computed from Earth DEM pixels at the same baseline as the lunar comparison? If not, the 15 deg filter compares different scales.
7. Landing coordinate for the globe marker: USGS Mons Mouton centre (84.60 S, 31.00 E) or F26's "84.6°S, 31.0°W"? Recommend USGS plus a note.
8. Mission duration field: 100 days (releases) vs Sept 2027-Jan 2028 surface ops (F26)? Pick one and cite it.
