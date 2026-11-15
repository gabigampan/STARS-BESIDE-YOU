# Stars Beside You

Team "Stars Beside You", NASA Space Apps Challenge 2026 (Málaga), challenge "Earth analogs for Permanent
Moon Base and Mars".

Stars Beside You is a web app that shows **analog pairs**: for each of three missions it lists places on
Earth where the mission could be tested because they resemble a place on the Moon, and names that lunar place.
It is built on real 1-degree tables of both bodies (NASA, NOAA, ESA and other public products) and on an engine
that pairs each Earth point with its lunar "twin" and explains every number. It is meant for mission and test
planners, students and the public, and for the jury: every value shown carries its source and its data level
(measured, derived or modelled).

> **What is new here and what the team wrote.** The repository had no root README; the team's own
> documentation is `tierra luna/README.md` (the original Earth-Moon extraction, harmonisation and cleaning
> pipeline, `main.py`, `analog_finder.py`, `web/index.html`), and it is kept unchanged. Everything below
> describes the work added on the branch `final-integration`: the real-data tables, the analog engine
> (`tierra luna/engine/`), the web app (`app/`), the mission videos and the documents in `docs/`.
> On this branch three of the team's files were edited (`tierra luna/analog_finder.py`, `rover_preset.py`,
> `data/presets/presets.json`; see [docs/PR_DESCRIPTION.md](docs/PR_DESCRIPTION.md)); the team's
> `tierra luna/mission_scoring.json` is read and quoted, never edited.

## The three missions

| mission | Earth side (where to test) | lunar side (the twin) | what the pair is matched on |
|---|---|---|---|
| **Rover** | flat, smooth, bare ground that passes the team's rover filters | a cell of the south-polar Rover zone (lunar latitude -75 or lower) | slope and roughness in real values (tolerances 2 deg and 30 m; differences within the elevation models' measurement error, 0.27 deg and 17.4 m, count as equal) |
| **Solar panels** | sunny, flat ground that passes the solar filters; suitability includes the satellite clear-sky fraction (ISCCP) | a cell of the low equatorial plains, the maria (within 30 deg of the equator and at or below -1,200 m) | sunlight above the atmosphere (tolerance 0.6 kWh/m2/day), slope and roughness as secondary criteria |
| **Lunar base** | cold places with a strong daily thermal swing (gate: swing at least 15 K) | a cell touching one of NASA's nine candidate landing regions near the lunar south pole (280 cells) | thermal **position** (coldest temperature and daily swing as percentiles of each body's population, within 10 points), slope and roughness in real values |

For every mission the list is ordered by a final score: 50 % similarity to the lunar twin and 50 % the team's
suitability for the mission. The app shows five spread-out sites per mission and the full ranking. What these
lists can and cannot claim is in [docs/KNOWN_LIMITATIONS.md](docs/KNOWN_LIMITATIONS.md).

## How to run it

### Web app (`app/`)

Node 22 or later (`app/package.json` `engines`). No API key and no server are needed; the site is static.

```sh
cd app
npm ci
npm run dev          # development server, http://localhost:5173
npm run typecheck    # tsc --noEmit
npm run build        # typecheck + vite build -> app/dist/ (static, deployable as is)
npm run preview      # serve the built dist/
```

Test scripts defined in `app/package.json` (they start headless Chromium; see `app/README.md` for options):

```sh
npm run smoke         # build, serve dist/, check both globes, save screenshots
npm run test:modules  # interaction modules (markers, beams, paired fly-to, video dialog, sunlight)
npm run test:data     # store and recompute against the data bundle, no browser
npm run test:flow     # the whole flow at desktop and phone sizes
npm run iau           # rebuild public/static/iau_moon_features.json from the IAU gazetteer .dbf
```

**Optional Cesium ion token.** The key-free build is the one to deploy. `app/.env.local` (git-ignored, as is
every `.env.*` except `.env.example`) may hold `VITE_CESIUM_ION_TOKEN`; it is used only when the build also sets
`VITE_USE_ION=1` (`VITE_USE_ION=1 npm run build`), and otherwise it is replaced by an empty string so it never
reaches `dist/` (the smoke test checks this). Anything built with `VITE_USE_ION=1` contains the token in public
JavaScript: never use a token with write scopes there; use a read-only token, or none.

### Engine (`tierra luna/engine/`)

Python 3 with the packages in `tierra luna/requirements.txt` and `tierra luna/engine/requirements.txt`
(numpy, pandas, scipy, pydantic, reverse_geocoder, tzdata, among others; `pytest` for the tests). The repository
does not pin a Python version: the team's README records Python 3.12 and `docs/VALIDATION.md` used Python 3.13.

```sh
cd "tierra luna"
pip install -r requirements.txt -r engine/requirements.txt pytest
python -m engine build        # computes everything and writes the bundle to app/public/data/v2
python -m engine validate     # checks the cell tables against the schema
python -m engine report       # counts, failure reasons, distributions, top cells
python -m engine datasets     # lists the dataset descriptors (real_1deg is the default)
python -m pytest -q           # the test suite in tierra luna/tests/
```

`python -m engine build --dataset legacy_2deg` writes the team's earlier 2-degree table in the same format to
`tierra luna/build/legacy_2deg/` (not shipped), for comparison. The validation scripts run with
`cd "tierra luna" && python validation/run_all.py && python validation/report_tables.py` (about 12 minutes;
`docs/VALIDATION.md`).

### Data bundle

The app reads the static bundle `app/public/data/v2/` (binary cell files and JSON; structure in
[docs/DATA_CONTRACT.md](docs/DATA_CONTRACT.md), revision 8, engine 3.4.0). It is written only by
`python -m engine build` from the real tables in `tierra luna/output_real/` and the settings in
`tierra luna/mission_scoring.json` (the team's file), `tierra luna/engine/engine_config.json` and
`tierra luna/engine/datasets.json`. To regenerate it, rebuild the tables if needed (below), run the build, then
`npm run build` in `app/`.

### Real-data builders (`tierra luna/real_data/`)

They download public files (no accounts, logins or keys), reduce them to 1-degree cells and write
`tierra luna/output_real/earth_real_1deg.csv`, `moon_real_1deg.csv` and `earth_moon_real_1deg.csv`, with the
provenance and manifest files. Raw files are kept outside the repository. The Earth builder needs numpy, pandas,
rasterio, pyproj and netCDF4; a clean Earth build transfers about 5.7 GB and took about 35 minutes
(`real_data/README_EARTH.md`).

```sh
python -I "tierra luna/real_data/build_earth.py"      # --no-download reuses the files on disk
python -I "tierra luna/real_data/build_moon.py"
python -I "tierra luna/real_data/build_combined.py"   # concatenation + mission_readiness.json
python -I "tierra luna/real_data/check_earth.py"      # Earth self-check -> checks_earth.txt
```

Details, sha256 of the current tables and the independent re-computation: [docs/REAL_DATA.md](docs/REAL_DATA.md).
The supplementary columns (ISCCP clear-sky fraction, extra terrain statistics) are in
`tierra luna/real_data/supplement/` with their own provenance files; their scripts are in `tierra luna/research/`.

### Mission video renderer (`app/video-sim/`)

A development tool, not shipped with the site, that renders the Solar panels and Lunar base videos frame by
frame from the bundle and real lunar relief (three.js in headless Chromium). Commands and inputs:
[app/video-sim/README.md](app/video-sim/README.md); per-video notes in `app/public/media/*/README.md`.

## Repository layout

```
.
├── README.md                 this file
├── ASSUMPTIONS.md            engine settings, assumptions and decisions, with their effect
├── app/                      web app (Vite, TypeScript, CesiumJS)
│   ├── src/                  scene, data store, flow, UI, interaction modules
│   ├── tests/                smoke, modules, data and flow tests
│   ├── public/data/v2/       the data bundle written by the engine
│   ├── public/media/         the three mission videos with captions and READMEs
│   ├── public/audio/         the audio guide (19 tracks, transcripts.json)
│   └── video-sim/            renderer of the Solar panels and Lunar base videos
├── docs/                     documents (see below); stats_audit/ holds the statistical audit
└── tierra luna/              the team's pipeline and everything built on it
    ├── README.md             the team's original documentation
    ├── mission_scoring.json  the team's mission filters, criteria and weights
    ├── engine/               the analog engine (python -m engine)
    ├── real_data/            builders, provenance, manifests and verification of the real tables
    ├── output_real/          the real 1-degree tables of Earth and Moon
    ├── validation/           validation scripts (docs/VALIDATION.md)
    ├── audit/                independent audit scripts and their outputs
    ├── research/             research scripts behind the supplementary columns
    └── tests/                pytest suite
```

## Documents

| document | what it is for |
|---|---|
| [docs/DATA_CONTRACT.md](docs/DATA_CONTRACT.md) | the exact structure of the data bundle the app reads (files, columns, encodings, sizes) |
| [ASSUMPTIONS.md](ASSUMPTIONS.md) | every engine setting and assumption: what was assumed, why, its effect, where to change it |
| [docs/DECISIONS.md](docs/DECISIONS.md) | the team's design decisions, dated, with the options and figures before and after (in Spanish) |
| docs/STATS_AUDIT.md and [docs/stats_audit/](docs/stats_audit/) | the independent statistical audit (parts 1 to 9, re-audits of Rover and Lunar base, research notes; in Spanish) |
| [docs/VALIDATION.md](docs/VALIDATION.md) | what was checked about the shipped pairs, how, and what each check does not show |
| [docs/UX_CHECKLIST.md](docs/UX_CHECKLIST.md) and [docs/UX_REPORT.md](docs/UX_REPORT.md) | the local jury's UX checklist and the app measured against it |
| [docs/REAL_DATA.md](docs/REAL_DATA.md) | the real tables: products, definitions, licences, provenance levels, verification |
| [docs/MISSION_ZONES.md](docs/MISSION_ZONES.md) | the lunar zones of each mission and why each test is searched where it is |
| [docs/AUDIT.md](docs/AUDIT.md) | the Phase 0 audit of what the team's original pipeline really does |
| [docs/KNOWN_LIMITATIONS.md](docs/KNOWN_LIMITATIONS.md) | what the results can and cannot claim |
| [docs/AI_USE.md](docs/AI_USE.md) | how AI tools were used (draft) |
| [docs/PR_DESCRIPTION.md](docs/PR_DESCRIPTION.md) | the text of the pull request from `final-integration` to the team's repository |

## Credits and licences

Taken from the repository's provenance files (`tierra luna/real_data/provenance_earth.csv`,
`provenance_moon.csv`, `real_data/supplement/*provenance*.csv`), `docs/REAL_DATA.md`, `app/README.md`, the
credits dialog of the app (`app/src/ui/credits.ts`) and the media READMEs. The full licence and credit text of
every column is also exported in the bundle (`variables.json` `licence_credit`, `manifest.json` `credits`).

### Earth data

| product | version | provider | used for | licence / credit |
|---|---|---|---|---|
| ETOPO 2022 Global Relief Model, 60 arc-second surface | v1 (2022) | NOAA NCEI | elevation, slope, roughness | US Government work, no restrictions. NOAA NCEI (2022), doi:10.25921/fd45-gt74 |
| ESA CCI / Copernicus C3S Land Cover map 2020, 300 m (copy on Microsoft Planetary Computer) | v2.1.1, year 2020 | ESA CCI, Copernicus C3S | land share, bare and snow/ice share, thermal-inertia class | free use with attribution: "ESA Climate Change Initiative - Land Cover led by UCLouvain (2017)" and Copernicus C3S Climate Data Store |
| OpenLandMap long-term MODIS LST climatology (Hengl 2018), from NASA MODIS Terra MOD11A2 v006, 2000-2017 | v1.0 (Zenodo 1420115) | OpenLandMap; NASA LP DAAC | land surface temperature, diurnal amplitude | **CC BY-SA 4.0** (derived data must carry the same licence). Hengl (2018) doi:10.5281/zenodo.1420115; MOD11A2 by Wan, Hook, Hulley, NASA LP DAAC |
| WorldClim 2.1 monthly climate normals 1970-2000, 10 arc-minute (Fick & Hijmans 2017) | 2.1 | WorldClim | coldest-month minimum air temperature, ground irradiance (also rain and wind, not stored in the bundle) | **Not an open licence.** worldclim.org: "freely available for academic use and other non-commercial use. Redistribution or commercial use is not allowed without prior permission." The bundle ships 1-degree aggregates of two WorldClim columns; use outside a non-commercial academic context may need WorldClim's permission (a pending team decision, ASSUMPTIONS.md 10.5) |
| Obu et al. permafrost probability (PERPROB), ESA DUE GlobPermafrost: Northern Hemisphere 2000-2016 (PANGAEA 888600), Antarctic 2000-2017 (PANGAEA 902576) | v5.0 | PANGAEA | permafrost class | NH CC BY 3.0, Antarctic CC BY 4.0 |
| ISCCP H-series Basic HGM, mean cloud amount (monthly means 2012-2016 as used) | v01r00 | NOAA NCEI Climate Data Record | clear-sky fraction (Solar panels suitability) | "No constraints on data access or use." Cite Rossow and Schiffer 1999, BAMS 80:2261-2287, and the NCEI ISCCP-H CDR |
| Earth obliquity (formula, no download) | IAU 2006, IERS Conventions 2010 | IERS | sun elevation columns | n/a; cite IERS Conventions 2010 (Petit & Luzum eds.) |

### Moon data

| product | version | provider | used for | licence / credit |
|---|---|---|---|---|
| LOLA LDEM_16 gridded elevation, 16 px/deg | V3.1 (2019-03-15) | NASA PDS Geosciences Node | elevation, slope, roughness | NASA PDS, publicly released (no licence string on the product page). LOLA team, Smith et al. 2010, GRL 37, L18204 |
| Diviner Global Cumulative Products, column tbol | GCP v1, files *_002 (2016-05-27) | NASA PDS Geosciences Node | surface temperatures (max, min, mean, diurnal amplitude) | NASA PDS, public. Diviner team (UCLA), Williams et al. 2017, Icarus 283:300-325 |
| Diviner rock abundance DGDR_RA_AVG_CYL_032 | V4.0 | NASA PDS Geosciences Node | rock abundance (information only) | NASA PDS, public. Bandfield et al. 2011, JGR 116, E00H02 |
| LOLA average solar illumination AVGVISIB_65S/65N_240M_201608 | V1.05 (2016-09-15) | NASA GSFC PGDA | polar lit fraction | NASA, public. Mazarico et al. 2011, Icarus 211:1066 |
| NSSDC Moon fact sheet (solar constant 1361 W/m2, radius 1737.4 km); NASA Photojournal PIA13720 (obliquity 1.54 deg); science.nasa.gov Moon facts | n/a | NASA | constants, irradiance geometry, regolith assumption | NASA |
| SLDEM2015 (LOLA + SELENE/Kaguya), tile 00N-30N 315-360, 512 px/deg (Barker et al. 2016) | as in `app/public/media/solar/README.md` | NASA PDS Geosciences Node | relief in the Solar panels video only | NASA PDS, public |

### Gazetteers

- **Lunar feature names:** Gazetteer of Planetary Nomenclature, IAU Working Group for Planetary System
  Nomenclature (WGPSN) and USGS Astrogeology Science Center (planetarynames.wr.usgs.gov); a USGS publication
  (US Government work).
- **Earth place names:** GeoNames (geonames.org, CC BY 4.0) cities1000 list as packaged by the
  `reverse_geocoder` Python library (offline); nearest populated place to the cell centre.
- **Earth countries:** Natural Earth 1:110m admin-0 countries (public domain).
- **NASA candidate landing regions:** the USGS Artemis III region grids (1 km navigational grid squares),
  converted by `python -m engine artemis`.

### Globe imagery and textures (from `app/README.md` and the app's credits dialog)

| source | used for | licence |
|---|---|---|
| NASA Global Imagery Browse Services (GIBS): Blue Marble Next Generation, VIIRS Black Marble 2016, Reference Labels 15 m | Earth base imagery, night lights, place-name overlay | NASA Earth science data, open; credit line requested by GIBS: "We acknowledge the use of imagery provided by services from NASA's Global Imagery Browse Services (GIBS), part of NASA's Earth Science Data and Information System (ESDIS)." |
| Sentinel-2 cloudless 2016 by EOX IT Services GmbH (contains modified Copernicus Sentinel data 2016) | sharper Earth imagery when zoomed in | CC BY 4.0 (2016 edition only) |
| NASA Moon Trek: LRO LROC Wide Angle Camera global mosaic, NASA/GSFC/Arizona State University | Moon imagery | NASA mission data; no separate licence text published, NASA/GSFC/ASU credited |
| Tycho Catalog Skymap (Version 2.0), NASA GSFC Scientific Visualization Studio, bundled with CesiumJS | star background | NASA imagery; terms as in the CesiumJS licence file |
| nasa-gibs/gibs-web-examples (tiling scheme adapted) | GIBS geographic tiling | Apache License 2.0 |

### Fonts and libraries (`app/package.json`, `app/video-sim/README.md`)

- CesiumJS 1.147.0 (Cesium GS, Inc. and contributors), Apache License 2.0.
- Barlow and Barlow Semi Condensed by Jeremy Tribby (`@fontsource/barlow` 5.3.0,
  `@fontsource/barlow-semi-condensed` 5.3.0), SIL Open Font License 1.1, bundled (no font service).
- Build tools: Vite 8.3.8, TypeScript 7.0.2, vite-plugin-static-copy 4.1.1, @types/node.
- Video renderer: three.js 0.170.0 (`app/video-sim`, not shipped with the site).
- Engine: numpy, pandas, scipy, pydantic, reverse_geocoder, tzdata; real-data builders: rasterio, pyproj, netCDF4.

### Mission videos (`app/public/media/*/README.md`)

None of the three videos is real footage, and each says so.

- **Rover:** "Rover mission video: 3D simulation by the Stars Beside You team (not real footage)". The team's
  own 3D simulation (a VIPER-like rover on a lunar surface), re-encoded with nothing changed in picture or timing.
- **Solar panels:** "3D simulation by the Stars Beside You team, driven by table data, over real LOLA and Kaguya
  relief (SLDEM2015, 59 m per pixel); fine surface texture procedural (not real footage)". Rendered by
  `app/video-sim` from the project's data.
- **Lunar base:** "3D simulation by the Stars Beside You team, driven by table data (not real footage)".
  Rendered by `app/video-sim` from the project's data.

### Audio guide

19 tracks (`app/public/audio/*.mp3`) recorded by the team with a text-to-speech service; the texts are in
`app/public/audio/transcripts.json` and checksums in `app/public/audio/SHA256SUMS.txt`.
