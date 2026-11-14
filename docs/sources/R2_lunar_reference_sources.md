# R2 - Lunar reference sources for the audit

Task R2, team "Stars Beside You", NASA Space Apps Challenge 2026. Prepared 2026-11-14. All pages were accessed on **2026-11-14**.
Labels: **MEASURED** = official product or published figure. **DERIVED** = computed here from a MEASURED product by the formula given. **MODELLED** = simulation or estimate in a source.
The team repository was not readable from this session, so nothing here checks their code directly.

## 1. Solar mission concept: polar ridges, not PSRs

**Verdict (supported by the sources below):** the team lead is right. A permanently shadowed region (PSR) receives no direct sunlight, by definition. A lunar solar-power test should target the highly illuminated rims, ridges and massifs next to the PSRs. A PSR is the right target for the ice/ISRU and cold-thermal tests, not for the solar test.

| Fact | Level | Quote | Source |
|---|---|---|---|
| PSR definition | MEASURED (definition) | "permanently shadowed regions (PSRs, defined as areas that never receive direct solar illumination)" | Mazarico et al. 2011, Icarus 211:1066, abstract on NTRS: https://ntrs.nasa.gov/api/citations/20120010094 |
| PSR definition (NASA outreach) | MEASURED | "sunlight never shines on the floors of some craters near the Moon's poles ... These areas are known as Permanently Shadowed Regions, or PSRs." | NASA LRO lithograph LG-2013-11-086-GSFC: https://science.nasa.gov/wp-content/uploads/2024/01/lro-litho5-shadowed.pdf |
| PSRs still get scattered light | MODELLED | "every PSR does receive some amount of scattered light during the year" | Mazarico 2011 (NTRS, above) |
| PSR area | MODELLED | "12,866 and 16,055 sq. km, in the north and south respectively" | Mazarico 2011 (NTRS, above) |
| Axial tilt, value A | MEASURED | "The Moon's axis tilts only 1.5 degrees from the ecliptic plane" | LRO lithograph (above) |
| Axial tilt, value B | MEASURED | "The spin axis of the Moon is tilted by only 1.54°." | NASA Photojournal PIA13720: https://science.nasa.gov/photojournal/south-pole-illumination-map |
| Maximum solar elevation at the poles | MEASURED | "At the Moon's North and South Poles, the Sun is never more than 1.5° above or below the horizon." | NASA SVS 4893 (2021-04-01): https://svs.gsfc.nasa.gov/4893 |
| Lit and shadowed areas sit side by side | MEASURED | "leaving some areas near the poles in permanent shadow" / "other nearby regions remain sunlit for the majority of the year" | PIA13720 (above) |

**The two tilt values (1.5° and 1.54°) are close and agree within rounding.** Use 1.54° in calculations and cite PIA13720.

### Most-illuminated south-polar sites (published percentages and the heights they refer to)

| Site | Official IAU name? (checked in gazetteer file, sec. 2) | Published illumination | Height above ground | Level | Source and quote |
|---|---|---|---|---|---|
| "Connecting Ridge" (ridge between Shackleton and de Gerlache) | **No.** Informal name. Shackleton and de Gerlache are IAU craters. | 92.27 % of time; 95.65 % of time | 2 m; 10 m | MODELLED (20 m/px LOLA DTM, 19-year run) | Gläser et al. 2014, Icarus 243:78. "We identified locations receiving sunlight for 92.27% of the time at 2 m above ground" / "and 95.65% of the time at 10 m above ground." Longest darkness "typically only 3-5 days". https://elib.dlr.de/94240 |
| Location near Shackleton rim | Shackleton = IAU crater | "sunlit continuously for 240 days" per year; longest darkness "about 1.5 days" | Not stated (surface). "small height gains (~10 m) can dramatically improve their average illumination" | MODELLED (LOLA 240 m, 6 h steps) | Mazarico 2011 (NTRS, above) |
| Three points on Shackleton rim | Shackleton = IAU | "remain collectively sunlit for more than 90% of the year" | Not stated | MODELLED / summary | NASA Science (2022-04-20): https://science.nasa.gov/resource/shackleton-craters-illuminated-rim-shadowed-interior/ ; same sentence on nasa.gov (VIPER, 2021-07-15): https://www.nasa.gov/missions/artemis/new-maps-help-developers-plan-lunar-road-trip-for-vipers-artemis-mission/ |
| Same VIPER page, caveat | - | "no location on the Moon stays continuously illuminated" | - | - | VIPER page (above) |

- The Speyerer & Robinson (2013) abstract (Icarus 222:122, doi:10.1016/j.icarus.2012.10.010) and the Bussey et al. (2010) abstract could not be read: ScienceDirect returned 403 and ADS returned 405. **Their percentages are not used here.**
- Search snippets attributed 94 % to an LROC page and 86.3 % to an NTRS report. **Neither page was opened, so neither figure is used.**

### NASA's current candidate landing regions (Artemis III)

NASA release RELEASE24-136 (2024-10-28) says: "The refined candidate Artemis III lunar landing regions are, in no priority order:"
https://www.nasa.gov/news-release/nasa-provides-update-on-artemis-iii-moon-landing-regions/

| NASA region name | Closest IAU gazetteer feature | IAU lat, lon (planetocentric, 0-360 E) |
|---|---|---|
| Peak near Cabeus B | Cabeus B (satellite feature) | -82.2587, 305.4154 |
| Haworth | Haworth (crater) | -87.45, 354.83 |
| Malapert Massif | **Mons Malapert** (the IAU name; "Malapert Massif" is informal) | -85.98, 358.33 |
| Mons Mouton Plateau / Mons Mouton | Mons Mouton | -84.60, 31.00 |
| Nobile Rim 1 / Nobile Rim 2 | Nobile (crater) | -85.2752, 53.2725 |
| de Gerlache Rim 2 | de Gerlache (crater) | -88.4849, 271.6553 |
| Slater Plain | Slater (crater) | -88.0792, 111.2881 |

- The coordinates are feature **centres**, not landing-region boundaries. NASA's release gives no coordinates.
- The release names "lighting conditions" among the selection criteria.
- A search of nasa.gov found nothing newer than this 2024 list. An NTRS record "Downselection From Thirteen to Nine" (20250011660) was listed but not opened.

### Contrast: mid and low latitudes

| Quantity | Level | Value and basis |
|---|---|---|
| Lunar day and night length | MEASURED | "each lunar day lasts 14 Earth days ... a lunar night lasts 14 Earth days" (LRO lithograph LG-2013-11-084-GSFC: https://science.nasa.gov/wp-content/uploads/2024/01/lrolitho7temperaturevariation27may2014.pdf) |
| Noon solar elevation at latitude φ | DERIVED | ≈ 90° − abs(φ), varying ±1.54° over the year (tilt from PIA13720). Equator ≈ 88.5-90°. 30° ≈ 58.5-61.5°. 60° ≈ 28.5-31.5°. |
| Illumination fraction on flat ground away from the poles | DERIVED | ≈ 50 % of time (day ≈ night, per the lithograph). This is not polar-style near-continuous light. **No official per-latitude table was found.** |

## 2. Products for cross-checking lunar points

The HEAD/GET column gives the result from this container on 2026-11-14 through the agent proxy.

| Product | URL | Format | Resolution | Coverage | Size | HEAD/GET result |
|---|---|---|---|---|---|---|
| IAU Gazetteer, Moon centre points (bulk) | https://asc-planetarynames-data.s3.us-west-2.amazonaws.com/MOON_nomenclature_center_pts.zip (listed on https://planetarynames.wr.usgs.gov/GIS_Downloads) | Shapefile (zip) | points | 9087 features | 23,845,070 B | 200. **Downloaded and parsed.** |
| Same, KML | ...MOON_nomenclature_center_pts.kmz | KMZ | points | same | 11,718,225 B | 200 (HEAD) |
| LOLA DEM (GDR) | https://pds-geosciences.wustl.edu/lro/lro-l-lola-3-rdr-v1/lrolol_1xxx/data/lola_gdr/cylindrical/img/ldem_{4,16,64,128}.img | PDS3 IMG int16, height = DN×0.5 m + 1737400 m | 4/16/64/128 px/deg | global | 2.07 MB / 33.2 MB / 531 MB / 2.12 GB | ldem_4.img: 200 |
| LOLA polar DEMs | .../lola_gdr/polar/img/ldec_*.img | IMG | down to 5 m (87.5°) | 45°-90° N/S tiles | 1.4 MB - 1.66 GB | listing 200 |
| LOLA slope | .../cylindrical/img/ldsm_16.img | IMG int16, deg = DN×0.0015+45 | 16 px/deg (1895 m) | global | 33,177,600 B | 200. Label: "slope baseline may vary from 30 to 120 meters" |
| LOLA roughness | .../cylindrical/img/ldrm_16.img; ldrm_32_{25,50,75,n}.img | IMG int16, m = DN×0.001 | 16 and 32 px/deg | global | 33.2 MB; 132.7 MB each | ldrm_16.img: 200 |
| Diviner GCP (all Tbol by local time; min/max/amplitude are derived from it) | https://pds-geosciences.wustl.edu/lro/urn-nasa-pds-lro_diviner_derived1/data_derived_gcp/ | ASCII table, 18 files of 10° latitude | 0.5°×0.5°, 0.25 h local time | global, 2009-07-05 to 2015-04-01 | 156,211,313 B each | 200. **Range-GET of 96 longitude strips done** (sec. 3) |
| Diviner PRP (polar annual average and max T, ice depth) | .../data_derived_prp/dlre_prp_{north,south}.tab | ASCII | not read | polar | 604,800,210 B each | 200 (HEAD) |
| Diviner PCP (seasonal polar Tbol) | .../data_derived_pcp/ | ASCII + raster | 240 m polar stereo, poleward of 80° | 2009-07-05 to 2020-03-15 | not listed | not tested |
| Diviner rock abundance (Bandfield et al. 2011; 2016 slope correction) | .../data_derived_gdr_l3/cylindrical/img/dgdr_ra_avg_cyl_{032,128}_img.img | IMG int16, RA = DN×0.001 | 32 and 128 px/deg (237 m) | 80°S-80°N, 2009-07-05 to 2016-10-10 | 88,473,600 B; 1,887,436,800 B | _032: 200 |
| LOLA polar illumination (Mazarico 2011) | https://pgda.gsfc.nasa.gov/products/69. TIF: https://pgda.gsfc.nasa.gov/data/MoonIllumination/AVGVISIB_85S_060M_201608.TIF. IMG: http://imbrium.mit.edu/EXTRAS/ILLUMINATION/IMG/ | IMG int16, JP2, GeoTIFF, COG | 240/120/60 m | 65-90°, 75-90°, 85-90° N/S. Average over 18.6 yr, hourly | 85S 60 m: TIF 33,994,464 B; IMG 51,166,728 B | TIF 200, IMG 200. **The COG links return an HTML "PGDA - Not Found" page with status 200**. |
| LROC WAC illumination % (Speyerer & Robinson 2013) | https://pds.mcp.nasa.gov/data/store/img/lunar_reconnaissance_orbiter/pds4/lroc/lro-l-lroc-5-rdr/LROLRC_2001/DATA/BDR/WAC_POLE/WAC_POLE_ILL_PCT_SOUTH/WAC_POLE_ILL_PCT_SOUTH_100M.IMG | IMG 8-bit (+ GeoTIFF) | 100 m | 88°-90° S; 2010-02-15 to 2011-02-05 (3807 images) | 5,904,896 B | 200. The lroc.im-ldi.com links redirect (302) to pds.mcp.nasa.gov. |
| LROC WAC global mosaic (643 nm) | same tree .../WAC_GLOBAL/WAC_GLOBAL_E000N1800_016P.IMG (also 100 m, 256/128/64/32/8/4 px/deg) | IMG | 100 m to 4 px/deg | global | 016P: 66,378,240 B | 200 |

### IAU gazetteer file: what was actually in it (parsed with a local DBF reader)

- **Rows and columns:** 9087 rows, 19 columns: `name, clean_name, approvaldt, origin, diameter, center_lon, center_lat, type, code, approval, min_lon, max_lon, min_lat, max_lat, ethnicity, continent, quad_name, quad_code, link`. All rows have `approval` = "Adopted by IAU".
- **Longitude in the data:** `center_lon` runs from 0.0039 to 359.9936, so it is **0-360 positive east**.
  - `max_lon` exceeds 360 in 60 rows. For example, Peary has max_lon 455.2. These extents wrap past 360.
  - One row has `min_lon` below 0.
- **Datum (.prj):** `SPHEROID["Moon_2000_IAU_IAG",1737400.0,0.0]`, a sphere of 1737.4 km.
- **The sources disagree on the coordinate convention:**

| Source | Quote |
|---|---|
| GIS_Downloads page | "The images and KML files are in east longitude, planetocentric latitude." |
| XML metadata, `CENTER_LON` | "Degrees 0 to 360 in an east or west system." |
| XML metadata, header block | `<lattype>Planetographic</lattype>`, `<londom>-180 to 180</londom>`, `<londir>Positive East</londir>` |
| TargetCoordinates page, Moon row | "Planetographic, +East, -180 - 180" (https://planetarynames.wr.usgs.gov/TargetCoordinates) |

- **Conclusion: trust the data, not the metadata header.** The data is 0-360 E. The latitude wording difference (planetocentric or planetographic) does not change any number on a sphere (sec. 4).

## 3. Lunar temperatures

| Quantity | Value | Level | Source and quote |
|---|---|---|---|
| Equatorial noon max | ~387-397 K | MEASURED | Diviner team (UCLA), quoting Williams et al. 2017 (Icarus 283:300): "∼387–397 K ... at noon at the equator, dropping to ∼95 K ... just before sunrise." https://diviner.ucla.edu/single-post/2018/04/20/new-diviner-level-4-data-products |
| Equatorial day / night (NASA outreach) | 400 K / 140 K | MEASURED (rounded outreach values) | "Daytime temperatures near the lunar equator reach ... (120° C, 400 K), while nighttime temperatures get to ... (-130° C, 140 K)." LRO lithograph LG-2013-11-084 (link in sec. 1) |
| **The two sources disagree on the night value: 95 K vs 140 K.** | | | **Use 95 K** (pre-dawn minimum, Diviner team and Williams 2017). 140 K matches an earlier-night value. The lithograph does not say which local time it means. |
| PSR / coldest | 25 K (Hermite crater, north pole) | MEASURED | "(minus 248 degrees Celsius or 25 kelvins)" NASA release 11-192 (2011-06-21): https://www.nasa.gov/news-release/nasa-details-achievements-of-lunar-spacecraft/ |
| South-pole PSR floors | similar to Hermite | MEASURED | "Extremely cold regions similar to the one in Hermite Crater were found at the bottoms of several permanently shadowed craters at the lunar south pole" (LRO lithograph LG-2013-11-084) |
| Cold-trap threshold | 110 K | MEASURED | "surfaces below 110 K, capable of cold trapping water over a billion years" (Diviner team, 2020: https://www.diviner.ucla.edu/single-post/2020/07/20/new-diviner-seasonal-polar-data-products ; Williams et al. 2019 JGR 124:2505) |
| Regolith thermal inertia | 55 ± 2 J m⁻² K⁻¹ s⁻½ at 273 K | MEASURED | Hayne et al. 2017 JGR, doi:10.1002/2017JE005387, abstract via Crossref |

### Diurnal amplitude by latitude (DERIVED from Diviner GCP)

**Method.**
- Source: the Diviner GCP files, column `tbol`. I fetched 8 longitude strips per 10° band (lon −179.75, −134.75, −89.75, −44.75, 0.25, 45.25, 90.25, 135.25) by HTTP Range.
- Per 0.5° cell, amplitude = max(tbol) − min(tbol) over all local-time bins. Only cells with at least 40 valid bins were kept.
- **Limitations.** This is a sample, not a full zonal mean. GCP combines all seasons from 2009 to 2015. Near the poles, the max and min therefore include seasonal swing, not one lunation.
- Script: /tmp/claude-0/-home-user-NASA/7228bb30-9725-52d9-8d71-762c955fd0bd/scratchpad/scripts/amp.py

| Latitude band | Cells | Median max (K) | Median min (K) | Median amplitude (K) | Amplitude range (K) |
|---|---|---|---|---|---|
| 0-10 N / 0-10 S | 160 / 160 | 391.8 / 391.3 | 94.4 / 94.6 | 297.7 / 297.0 | 289-306 |
| 20-30 N | 160 | 379.4 | 92.3 | 286.5 | 278-294 |
| 40-50 N | 160 | 353.8 | 87.6 | 265.7 | 249-278 |
| 60-70 N | 160 | 307.3 | 79.3 | 228.1 | 207-255 |
| 70-80 N / S | 160 / 160 | 275.8 / 275.4 | 71.5 / 71.7 | 204.2 / 204.1 | 140-259 |
| 80-90 N / S | 160 / 160 | 222.4 / 229.3 | 55.4 / 51.4 | 164.8 / 175.7 | 26-242 |

**Share of cells with amplitude between 63 and 180 K (the team's range):**

| Latitude | North | South |
|---|---|---|
| Below 75° | 0 % | 0 % |
| 80-82.5° | 47 % | 28 % |
| 82.5-85° | 65 % | 57 % |
| 85-87.5° | 97 % | 65 % |
| 87.5-90° | 97 % | 70 % |

The derived equatorial max (≈391 K) and min (≈94.5 K) agree with the published ~387-397 K and ~95 K. This supports the method.

**Verdict on the team's 63-180 K amplitudes:**
- **Plausible only poleward of about 80°**, and typical poleward of about 85°, in both hemispheres. That covers south-polar sites such as the Artemis regions.
- **Not plausible at low or mid latitudes.** There the measured amplitude is about 250-300 K.
- If any non-polar lunar site in their dataset has an amplitude of 63-180 K, that is an error. Likely causes: wrong units (°C vs K), daily mean vs extreme, or a mis-assigned latitude.

## 4. Coordinate conventions that cause errors

| Item | Statement | Source |
|---|---|---|
| Planetocentric vs planetographic | "planetocentric and planetographic latitude definitions are the same if a reference sphere is used" (the page recommends planetocentric anyway) | USGS PSDI data standards: https://psdi.astrogeology.usgs.gov/moon/standards/data_standards/ |
| LRO standard | "LRO instrument teams shall deliver data to the PDS with planetocentric coordinates in the ME" system. Longitude runs "from 0˚ toward 360˚". "+180˚ East / -180˚ West" conversion "is easily performed" | LRO Project White Paper v4 (2008-05-14): https://pds-imaging.jpl.nasa.gov/documentation/LRO_Coordinate_System.pdf |
| Reference radius | "a reference sphere of radius 1737.4 km" (white paper); "a reference sphere with a 1737.4 km radius" (USGS) | same two sources |
| Radius trap | GRGM1200A geoid "uses a radius of 1738km (and not the newer, IAU-endorsed radius of 1737.4km)" | USGS PSDI (above) |
| Frame | ME frame from DE421, "expected to shift to the 2021 JPL DE 440 ephemeris" | USGS PSDI (above) |
| Storage vs. use | Recommended storage is "a -180 to 180 positive East coordinate system". LRO and several agencies "have agreed to use a 0 to 360 longitude domain" | USGS PSDI (above) |

**Longitude domain of each product, read from its own label or file:**

| Product | Longitude domain | Note |
|---|---|---|
| IAU gazetteer shapefile | **0-360 E** (data) | Metadata header says −180 to 180, and the TargetCoordinates page says −180-180. These are inconsistent with the data. |
| LOLA LDEM / LDRM | 0-360 E | Labels: `WESTERNMOST_LONGITUDE = 0`, `EASTERNMOST = 360`, `CENTER_LONGITUDE = 180`. |
| LOLA LDSM | 0-360 E | Label has `WESTERNMOST = 360`, `EASTERNMOST = 0`, the reverse order of LDEM. **Verify the sample order before indexing.** |
| Diviner GCP | **−180 to 180 E** | `WESTERNMOST_LONGITUDE = -180`. Rows start at clon −179.75. |
| Diviner rock abundance | 0-360 E, planetocentric, 80°S-80°N only | |
| LOLA illumination, LROC WAC polar | polar stereographic, R = 1737.4 km | Convert (x, y) to lat/lon. Do not index by longitude. |
| LROC WAC global | both | Files centred at 180 use 0-360. Files centred at 0 use −180-180. The file name tells which (E000N1800 vs E000N0000). |
| All of the above | sphere of 1737.4 km | Planetocentric latitude equals planetographic latitude. **The real risk is the longitude wrap, not the latitude type.** |

## Verification log

**Opened successfully:**
- nasa.gov: RELEASE24-136, release 11-192, VIPER maps page.
- science.nasa.gov: PIA13720, Shackleton resource page, lithographs litho5 and litho7 (PDFs, text extracted).
- svs.gsfc.nasa.gov/4893.
- pgda.gsfc.nasa.gov/products/69.
- NTRS API record 20120010094 (Mazarico abstract).
- planetarynames.wr.usgs.gov: TargetCoordinates and GIS_Downloads.
- USGS PSDI data standards.
- LRO coordinate white paper (PDF).
- elib.dlr.de/94240 (Gläser abstract).
- diviner.ucla.edu posts from 2018 and 2020.
- pds-geosciences: Diviner page and directory listings; GCP, rock-abundance, LOLA LDEM/LDSM/LDRM labels.
- LROC: WAC_POLE_ILL_PCT_SOUTH readme, WAC_GLOBAL page and readme.
- Crossref API, used for abstracts of Hayne 2017, Vasavada 2012 and Paige 2010. The Paige 2010 record returned only the issue summary.

**Downloaded:**
- IAU zip into .../scratchpad/stars/iau/.
- 96 Diviner GCP strips into .../stars/diviner_gcp_strips/.
- PDFs into .../stars/litho7/ and .../stars/lrocoord/.

**Failed or not used:**
- ScienceDirect (Mazarico, Speyerer): 403.
- ADS abstracts: 405.
- NTRS citation page: timeout. The API worked instead.
- NTRS 20170007365 PDF: returned HTML, not read.
- luna1.diviner.ucla.edu Level-4 raster directory: TLS certificate error through the proxy. Verification was not disabled.
- PGDA `_COG.TIF` links: soft 404.
- The Williams 2017 abstract itself (Crossref has no abstract). Its numbers are cited via the Diviner team page.
- **NASA POWER API was not called.**

## Open questions for the team

1. **Solar test target.** Does the solar test currently score Earth cells against lunar PSR conditions? If so, re-target it to the illuminated ridges and rims: Connecting Ridge, the Shackleton rim, Mons Malapert. Keep PSRs for the ice and cold-thermal tests.
2. **Height above ground.** Which height should the solar test assume, 2 m (rover/panel) or 10 m (mast)? The published illumination differs: 92.27 % vs 95.65 % (Gläser 2014).
3. **Thermal amplitudes.** Which latitudes are the lunar points with 63-180 K amplitudes at? Below about 80° that range contradicts Diviner. Was the amplitude computed from max − min of one lunation, or across seasons?
4. **Longitude convention.** Which convention does the lunar point list use? If any point came from the Diviner GCP (−180..180) and was joined with LOLA or the gazetteer (0..360) without wrapping, its location is off by up to 180°.
5. **Landing-region list.** Should the Artemis III list (Oct 2024) be checked against any later NASA update before the final presentation? NTRS 20250011660 was found but not read.
6. **Downloads.** Does the team want the full-resolution products (LOLA 60 m polar illumination TIF, LDSM/LDRM, RA 32 ppd) downloaded? All HEAD tests passed.
