# R4 - Frontend assets, Earth data access and reachability from the cloud session

Team "Stars Beside You", NASA Space Apps Challenge 2026. Reference material only; nothing here was read from the team's code.
**Access date for every source and test below: 2026-11-14** (one session). Levels: MEASURED = an official figure or a test result from this container; DERIVED = computed by a stated formula; MODELLED = estimate. Quotes are copied from the page text that `curl` downloaded, not from memory.

## 1. Assets: source, endpoint, licence, key, free-tier limits

### 1.1 CesiumJS and Cesium ion

| Item | Fact (quote) | Source |
|---|---|---|
| CesiumJS current stable | npm `dist-tags.latest` = `1.147.0`, published `2026-11-02T20:17:19Z`; CHANGES.md: "## 1.147 - 2026-11-02" | https://registry.npmjs.org/cesium ; https://raw.githubusercontent.com/CesiumGS/cesium/1.147/CHANGES.md |
| CesiumJS licence | npm `license` = `Apache-2.0`; file header of cdnjs build: "Licensed under the Apache Li[cense]" | registry.npmjs.org/cesium ; https://cdnjs.cloudflare.com/ajax/libs/cesium/1.147.0/Cesium.js (HTTP 200) |
| Cesium ion token | Ion.js 1.147: "Please assign *Cesium.Ion.defaultAccessToken* with an access token from your ion account before making any Cesium API calls. You can sign up for a free ion account" | https://raw.githubusercontent.com/CesiumGS/cesium/1.147/packages/engine/Source/Core/Ion.js |
| Earth terrain (Cesium World Terrain) | `createWorldTerrainAsync.js`: `return CesiumTerrainProvider.fromIonAssetId(1, {` → **asset id 1**; used via `Terrain.fromWorldTerrain()` (page code sample) | .../Source/Core/createWorldTerrainAsync.js ; https://cesium.com/platform/cesium-ion/content/cesium-world-terrain/ |
| Earth imagery (ion "Bing Maps") | `IonWorldImageryStyle.js`: "AERIAL: 2", "AERIAL_WITH_LABELS: 3", "ROAD: 4" → **asset ids 2/3/4** | .../Source/Scene/IonWorldImageryStyle.js |
| Moon (Cesium Moon, 3D Tiles) | Code sample: "Cesium.Ellipsoid.default = Cesium.Ellipsoid.MOON;" … "globe : false" … "Cesium3DTileset.fromIonAssetId ( 2684829 )" → **asset id 2684829**; must be added from the Asset Depot to the user's ion library | https://cesium.com/platform/cesium-ion/content/cesium-moon/ (moon-terrain URL redirects here) |
| Cesium Moon sources | Table: "Imagery 60N - 60S … LRO LROC WAC Global Morphology Mosaic 100 m"; "Terrain 60N - 60S … LOLA - SELENE Kaguya TC Shaded Relief Merge 60N60S 59 m"; "Terrain 87.5S - 90S … LOLA RDR Gridded Data Collection 5 m"; "Imagery 85.5S - 90S LROC NAC images of the South pole 1 m" | same page |
| Moon sample code limits | "2D and Columbus View are not currently supported for global 3D Tiles tilesets"; "Geocoder is not currently supported for lunar locations" | same page |
| Community (free) tier | "Personal and non-commercial use"; quotas: "Storage 10 GB", "Streaming 15 GB / month", "Global Imagery (Bing Maps, Google Maps…) 1,000 sessions / month", "Google Photorealistic 3D Tiles 1,000 root tiles / month", "Geocodes 50,000 / month" | https://cesium.com/platform/cesium-ion/pricing/ |
| When paid is needed | FAQ: paid needed "If your company currently makes more than $50K in annual gross revenues …, or If you are working on a government project, or If you are working on funded educational research, or If you exceed the usage limits"; free may be used for "Non-commercial personal projects … or Unfunded educational activities" | same page |
| Credit line | No attribution requirement stated on the pricing page; no official credit-line text found. CesiumJS shows provider credits on screen by itself (Credit class in Ion.js). | — |

Risk: Bing/Google imagery via ion is capped at 1,000 sessions/month on Community; a public Vercel demo during judging could hit it. Key-free NASA layers below avoid the cap.

### 1.2 Key-free Earth imagery: NASA GIBS (WMTS)

Capabilities (HTTP 200, 5.3 MB): `https://gibs.earthdata.nasa.gov/wmts/epsg4326/best/1.0.0/WMTSCapabilities.xml` (also `epsg3857`, HTTP 200). Tiles return `access-control-allow-origin: *` (MEASURED, HEAD with Origin header), so CesiumJS can load them directly.

| Layer id (exact) | Title in capabilities | Matrix set / format | Time | Tile template (from capabilities) |
|---|---|---|---|---|
| `BlueMarble_NextGeneration` | "Blue Marble (MODIS)" | 500m / image/jpeg | none | `https://gibs.earthdata.nasa.gov/wmts/epsg4326/best/BlueMarble_NextGeneration/default/{TileMatrixSet}/{TileMatrix}/{TileRow}/{TileCol}.jpeg` (test tile 0/0/0: 200, 29 474 B) |
| `BlueMarble_ShadedRelief_Bathymetry` | (present) | 500m / image/jpeg | none | same pattern |
| `VIIRS_Black_Marble` (night lights) | "Black Marble (VIIRS, Suomi NPP)" | 500m / image/png | `2012-01-01`, `2016-01-01` (Default 2016-01-01) | `.../VIIRS_Black_Marble/default/{Time}/{TileMatrixSet}/{TileMatrix}/{TileRow}/{TileCol}.png` (test: 200, 81 239 B) |
| `MODIS_Terra_CorrectedReflectance_TrueColor`, `VIIRS_SNPP_CorrectedReflectance_TrueColor` (real daily clouds) | (present) | 250m / image/jpeg | daily, e.g. VIIRS "2015-11-24/2022-07-27/P1D" … | per-date pattern |
| `MODIS_Aqua_Cloud_Fraction_Day` etc. | cloud-property layers (science colour maps, not photo clouds) | — | daily | — |

Credit (GIBS docs, https://nasa-gibs.github.io/gibs-api-docs/): "We acknowledge the use of imagery provided by services from NASA's Global Imagery Browse Services (GIBS), part of NASA's Earth Science Data and Information System (ESDIS)." No key or account needed (MEASURED: tiles fetched without credentials). No official rate-limit figure found.
Note: GIBS has no static global "cloud texture"; the photographic cloud option is a dated true-colour layer. Ocean specular and atmosphere are rendering effects inside CesiumJS, not data.

### 1.3 Key-free Moon layers: NASA Moon Trek WMTS and USGS

| Layer id (Moon Trek, EQ) | Coverage (capabilities bbox) | Capabilities URL (all HTTP 200) |
|---|---|---|
| `LRO_WAC_Mosaic_Global_303ppd_v02` | global; jpeg; tile template `https://trek.nasa.gov/tiles/Moon/EQ/LRO_WAC_Mosaic_Global_303ppd_v02/1.0.0//{Style}/{TileMatrixSet}/{TileMatrix}/{TileRow}/{TileCol}.jpg`, matrix set `default028mm` (tile 0/0/0: 200, 49 475 B, `Access-Control-Allow-Origin: *`) | `https://trek.nasa.gov/tiles/Moon/EQ/LRO_WAC_Mosaic_Global_303ppd_v02/1.0.0/WMTSCapabilities.xml` |
| `LRO_LOLA_Shade_Global_256ppd_v06` (hillshade) | "-180 -90" to "180 90" (global, includes poles) | `.../LRO_LOLA_Shade_Global_256ppd_v06/1.0.0/WMTSCapabilities.xml` |
| `LRO_LOLA_ClrShade_Global_256ppd_v06` (colour hillshade) | global | `.../LRO_LOLA_ClrShade_Global_256ppd_v06/1.0.0/WMTSCapabilities.xml` |
| `LRO_LOLAKaguya_Hillshade_60N60S_512ppd` | **"-180.0 -60.0" to "180.0 60.0" only - no poles** | `.../LRO_LOLAKaguya_Hillshade_60N60S_512ppd/1.0.0/WMTSCapabilities.xml` |

Moon Trek credit line / licence: no official text found (capabilities files carry no attribution; the Trek app is JavaScript-only). USGS Astropedia, "Moon LRO LOLA DEM 118m" (https://astrogeology.usgs.gov/search/map/moon_lro_lola_dem_118m): "resolution of 256 pixels per degree. In projection, the pixels are 118 meters in size at the equator"; "Access Constraints public domain"; "Use Constraints Please cite authors"; file `https://planetarymaps.usgs.gov/mosaic/Lunar_LRO_LOLA_Global_LDEM_118m_Mar2014.tif` → 302 to S3, `Content-Length: 8494203833` (8.5 GB; not downloaded); "all pixel values should be divided by 2".
Cesium Moon terrain needs a heightmap in Cesium's format; a key-free alternative would mean tiling the USGS DEM ourselves (MODELLED effort, not tested).

### 1.4 Star background

NASA SVS "Deep Star Maps 2020", https://svs.gsfc.nasa.gov/4851: "plotting the position, brightness, and color of 1.7 billion stars from the" Hipparcos-2, Tycho-2 and Gaia DR2 catalogues; "half-float format" OpenEXR; plate carrée, celestial or galactic; 4k (4096×2048) to 64k. Credit: "NASA/Goddard Space Flight Center Scientific Visualization Studio. Gaia DR2: …" (ESA/Gaia/DPAC). Files under `https://svs.gsfc.nasa.gov/vis/a000000/a004800/a004851/`: `starmap_2020_4k_print.jpg` (HEAD 200, 42 786 B), `starmap_2020_8k.exr` (HEAD 200, 130 530 278 B). No key.
DERIVED: CesiumJS `SkyBox` takes six cube faces, so the equirectangular EXR must be converted (tone-mapped to PNG/JPEG and reprojected) offline. The 8k EXR alone exceeds the Vercel Hobby CLI upload limit (§5).

### 1.5 Labels

| Need | Source | Facts |
|---|---|---|
| Countries, cities (Earth) | Natural Earth, https://www.naturalearthdata.com/about/terms-of-use/ | "All versions of Natural Earth raster + vector map data … are in the public domain"; "No permission is needed to use Natural Earth. Crediting the authors is unnecessary." Optional credit: "Made with Natural Earth." Files: `https://naciscdn.org/naturalearth/10m/cultural/ne_10m_populated_places_simple.zip` (200, 652 145 B), `.../ne_10m_admin_0_countries.zip` (200, 4 930 492 B). Convert to GeoJSON offline. |
| IAU lunar names | USGS Gazetteer of Planetary Nomenclature, https://planetarynames.wr.usgs.gov/GIS_Downloads | Moon: `https://asc-planetarynames-data.s3.us-west-2.amazonaws.com/MOON_nomenclature_center_pts.kmz` (200, 11 718 225 B, Last-Modified 14 Nov 2026) and `MOON_nomenclature_center_pts.zip` (shapefile, 23 845 070 B); "These files are generated nightly." Search results page also offers CSV output. No CORS header observed on S3 → convert to a GeoJSON/CZML in the repo at build time. Credit text: none on the downloads page. |
| Labels when zoomed to city level | ion asset 3 ("AERIAL_WITH_LABELS") counts against the 1,000 sessions/month quota | §1.1 |

## 2. Reachability from this container (MEASURED, curl via proxy, TLS verified)

| Host | Purpose | Result |
|---|---|---|
| api.cesium.com | ion REST/token endpoint | `/` → 405 `"GET is not allowed"`; `/v1/assets` → `{"code":"InvalidCredentials","message":"No authorization token was found"}` - reachable, needs token |
| assets.ion.cesium.com | ion tiles | 401 `"Invalid access token"` - reachable, needs token |
| cdnjs.cloudflare.com | CesiumJS build | `/ajax/libs/cesium/1.147.0/Cesium.js` → 200 |
| gibs.earthdata.nasa.gov | Earth WMTS | capabilities 200 (5.3 MB); tiles 200 |
| trek.nasa.gov | Moon WMTS | 4 capabilities 200; tile 200 |
| planetarynames.wr.usgs.gov | IAU names | 200; S3 downloads 200 |
| svs.gsfc.nasa.gov | star maps | page 200; files HEAD 200 |
| earthengine.googleapis.com | EE API | `/` 404; `/v1/projects/earthengine-public/assets/USGS` → 401 "Request is missing required authentication credential" - reachable, needs OAuth |
| oauth2.googleapis.com | token exchange | `/` 404; `POST /token` (dummy) → 400 - reachable |
| api.vercel.com | deploy API | `/` 308; `/v2/user` → 404 `"The request is missing an authentication token"` - reachable, needs token |
| registry.npmjs.org | npm | 200 (in proxy `noProxy` list, direct) |
| naciscdn.org, planetarymaps.usgs.gov, cesium.com, developers.google.com, vercel.com | supporting | 200 |

No proxy refusal was seen for any host.

## 3. Google Earth Engine from a headless container

**Authentication (https://developers.google.com/earth-engine/guides/service_account, /guides/auth)**
- Service account: "A private key in JSON format is needed for the service account to access Google APIs. The Cloud project containing the service account must be registered to use Earth Engine and have the Earth Engine API enabled."
- REST use: "give it project-level permission, specifically the Earth Engine Resource Viewer role … you may also need to give the service account the Service Usage Consumer role".
- ADC: "Application Default Credentials (ADC) is the recommended way to authenticate in unattended environments … without managing private keys manually" (`google.auth.default()` then `ee.Initialize(credentials, project=...)`).
- Remote user login: "If you can install gcloud on both the remote machine and your local machine, use auth_mode=gcloud. If you can use an authentication project …, use auth_mode=notebook"; `quiet` "runs 'noninteractively' and doesn't prompt".
- Practical choice here (DERIVED): a service-account JSON key supplied as a secret file (not in git, not pasted in chat). `gcloud` is installed in this container.

**What the user must create:** a Google Cloud project → enable Earth Engine API → register it at the EE registration page for noncommercial use ("fill out the registration questionnaire in the Cloud console to confirm your project's eligibility", /guides/access) → create a service account + JSON key → grant Earth Engine Resource Viewer (+ Service Usage Consumer if needed). Exports to Drive also require the files to be shared or exported to Cloud Storage (no official text read on this; open question).

**Noncommercial quota (/guides/noncommercial_tiers):** "Since April 27, 2026, all noncommercial Earth Engine projects have a recurring monthly quota"; "Community Tier 150 EECU-hours (540,000 EECU-seconds)"; out of quota → "restricted mode … limits your online and batch concurrency".
**Limits (/guides/usage):** "Max concurrent requests (standard endpoint) 40"; "100 requests/s"; "Average concurrent batch tasks 2 tasks"; "Max asset storage space 250 GB"; "The size limit on computed results is 100 MiB"; "A single query … is limited to 10MB".
**Export (/apidocs/export-image-todrive):** "By default, you will see an error if the export exceeds 1e8 pixels"; `fileDimensions` splits large images; formats "GeoTIFF and TFRecord".

| Grid | Cells (DERIVED: 360/r × 180/r) | vs 1e8 maxPixels | Float32 single band (DERIVED ×4 B) |
|---|---|---|---|
| 0.1° | 3600 × 1800 = 6 480 000 | 6.5 % | ≈ 25.9 MB per band |
| 0.25° | 1440 × 720 = 1 036 800 | 1.0 % | ≈ 4.1 MB per band |

Both fit one image export. Exporting 6.5 M cells as a table (one feature per cell) is a different, much heavier path; recommend a multi-band GeoTIFF, then vectorise offline (MODELLED). ERA5-Land's native pixel is 11 132 m (≈0.1°), so 0.1° adds no climate detail; 0.25° vs 0.1° matters for DEM/LST/land cover only.

**Datasets (EE catalog pages, developers.google.com/earth-engine/datasets/catalog/…)**

| Need | EE id | Native | Bands / variables | Notes (quoted) |
|---|---|---|---|---|
| Elevation (SRTM) | `USGS/SRTMGL1_003` (ee.Image) | 30 m | `elevation` (m) | LP DAAC: "Spatial Extent N: 60 S: -56"; "all land between 60° N and 56° S latitude" (lpdaac.usgs.gov/products/srtmgl1v003/) |
| Elevation (SRTM reprocessed) | `NASA/NASADEM_HGT/001` | 30 m | `elevation`, `num` | built from SRTM, same latitude limit |
| Elevation global incl. >60°N | `COPERNICUS/DEM/GLO30` (ImageCollection) | 30 m | `DEM` | "available worldwide with a free license with the exception of two countries (Armenia and Azerbaijan)"; credit "© DLR e.V. 2010-2014 and © Airbus Defence and Space GmbH 2014-2018 provided under COPERNICUS by the European Union and ESA; all rights reserved." It is a DSM ("including buildings, infrastructure and vegetation"). |
| Slope | DERIVED: `ee.Terrain.slope(dem)` (used in the SRTM page's code sample) | — | — | compute at native res, then aggregate |
| LST day / night | `MODIS/061/MOD11A2` | 1000 m, 8-day | `LST_Day_1km`, `LST_Night_1km` (K, scale 0.02) | "average 8-day land surface temperature"; availability to 2026-11-01; "no restrictions on subsequent use, sale, or redistribution" |
| Land cover | `MODIS/061/MCD12Q1` | 500 m, yearly | `LC_Type1` (IGBP) … `LC_Type5` | 2001-2025 |
| 2 m T minimum | `ECMWF/ERA5_LAND/DAILY_AGGR` | 11 132 m | `temperature_2m_min` (K) "daily minimum temperature_2m value" | 1950-01-02 to 2026-11-06 |
| Surface solar radiation | same | 11 132 m | `surface_solar_radiation_downwards_sum` (J/m^2) | monthly: `ECMWF/ERA5_LAND/MONTHLY_AGGR` |
| ERA5 credit | — | — | — | "'Generated using Copernicus Climate Change Service Information [Year]'"; modified products: "'Contains modified Copernicus Climate Change Servi[ce information]'" |
| Permafrost | No dedicated EE catalog dataset found. Proxy: `WWF/HydroATLAS/v1/Basins/level07` (FeatureCollection) field `prm_pc_sse` "Permafrost Extent … spatial extent (%)" per sub-basin | basin polygons | — | Official raster/vector outside EE: NSIDC GGD318 "Circum-Arctic Map of Permafrost and Ground-Ice Conditions, Version 2", DOI 10.7265/skbg-kf16, "Shapefile", coverage "Northern latitude 90 Southern latitude 28" (nsidc.org/data/ggd318/versions/2), upload as an EE asset |

NASA POWER: not called (per rules); not in this table.

## 4. Browser recording (MEASURED in this container)

Environment: 4 vCPU, no `/dev/dri`, no `nvidia-smi`. Playwright 1.63.0 (preinstalled at /opt/node-tools), HeadlessChrome 153.0.8010.12. Script: `/tmp/claude-0/-home-user-NASA/7228bb30-9725-52d9-8d71-762c955fd0bd/scratchpad/stars/tools/webgl_probe.js`.

| Run | WebGL | Renderer string | Max texture | Trivial full-screen shader, 1920×1080 | While recording VP9 |
|---|---|---|---|---|---|
| default headless | webgl2 | `ANGLE (Google, Vulkan 1.3.0 (SwiftShader Device (Subzero) (0x0000C0DE)), SwiftShader driver)` | 8192 | 27.9 fps | 16.2 fps |
| `--use-angle=swiftshader --enable-unsafe-swiftshader --ignore-gpu-blocklist` | webgl2 | same | 8192 | 37.3 fps | 9.1 fps |

`MediaRecorder.isTypeSupported` returned true for `video/webm` (vp8, vp9, av1, h264) and `video/mp4` (avc1, avc1.42E01E, avc1.640028, vp9, av01). Actual 2 s recordings: `video/mp4;codecs=avc1.640028` → 490 743 B, blob type reported `avc1.64002a`; `video/webm;codecs=vp8` → 26 930 B. Official: Chrome 126 release notes, "MP4 container support for MediaRecorder … Adds support for muxing audio and video into MP4 containers with MediaRecorder." (https://developer.chrome.com/release-notes/126).
Conclusion (DERIVED): software WebGL works, but a trivial scene already drops to ~9-16 fps while encoding at 1080p, so a CesiumJS globe with terrain will be lower. Real-time capture here will stutter. Options: record on a team laptop with a GPU; or render frame by frame (deterministic clock, `canvas.toBlob` per frame) and encode offline - ffmpeg presence not checked.

## 5. Vercel

| Topic | Fact (quote) | Source |
|---|---|---|
| Deploy from a session | `vercel deploy --prebuilt` with `--token`; "VERCEL_TOKEN is the API authentication token, created from your account's tokens page or with vercel tokens add. VERCEL_ORG_ID and VERCEL_PROJECT_ID both live in the .vercel/project.json file that vercel login and vercel link generate" | https://vercel.com/kb/guide/how-can-i-use-github-actions-with-vercel ; https://vercel.com/docs/cli/deploy |
| No-account option | "The --temporary option creates a temporary deployment without logging in"; it "prints a live URL and a claim URL" | vercel.com/docs/cli/deploy |
| Upload size | "When using the CLI to deploy, the maximum size of the source files that can be uploaded is limited to 100 MB for Hobby and 1 GB for Pro." | https://vercel.com/docs/limits |
| File count | "The maximum number of files … when creating a CLI Deployment is 15,000 for source files"; "use the --archive=tgz option" | same |
| Other Hobby limits | "Deployments Created per Day 100"; "Concurrent Deployments 1"; "Build Time per Deployment (Minutes) 45" | same |
| Git LFS | "If you have LFS objects in your repository, you can enable or disable support for them from the project settings … You must redeploy your project after turning Git LFS on." | https://vercel.com/docs/project-configuration/git-settings |
| Hobby commercial terms | No statement found on /docs/plans/hobby or /docs/limits/fair-use-guidelines in the text fetched | — |

DERIVED: keep heavy assets (star map, DEM tiles) off the deploy; stream them from NASA/USGS/ion, or keep the deploy under 100 MB.

## Keys, accounts and files the user must supply (by urgency)

1. **GitHub access to the team repository** in this session - blocks the audit itself.
2. **Google Cloud project registered for noncommercial Earth Engine + service-account JSON key** (Earth Engine Resource Viewer role) - blocks all real Earth data. Supply as a file or secret, never in chat.
3. **Cesium ion access token** (free Community account, with Cesium Moon asset 2684829 added to "My Assets") - needed only for ion terrain/Moon 3D Tiles/Bing imagery.
4. **Vercel token + project (or `--temporary`)** - needed only to publish.
5. **Decision**: Copernicus GLO-30 vs SRTM for >60°N; which permafrost source.

**Buildable with none of them:** CesiumJS 1.147 app from npm/cdnjs; Earth with GIBS Blue Marble + Black Marble + dated true-colour clouds; Moon with Trek WAC mosaic + LOLA global hillshade on an ellipsoid (no 3D relief); SVS star sky box; Natural Earth and IAU labels; MediaRecorder capture (slow here).

## Verification log

Opened OK (200 unless noted): registry.npmjs.org/cesium; cdnjs Cesium 1.123.0 and 1.147.0; raw.githubusercontent.com CesiumGS 1.147 Ion.js, createWorldTerrainAsync.js, IonWorldImageryStyle.js, CHANGES.md (Ellipsoid.js 404 - not needed); cesium.com pages cesium-moon (via 301), cesium-world-terrain, pricing (bing-maps-aerial-imagery page 404); GIBS 4326 + 3857 capabilities and two tiles; GIBS API docs; Trek capabilities ×4 and one tile; nasa_trek_layers MCP search; SVS 4851 page and two HEADs; planetarynames GIS_Downloads, SearchResults, two S3 files (HEAD); Natural Earth terms + two HEADs; USGS Astropedia LOLA DEM page + HEAD (302→S3 200); EE guides service_account, auth, access, noncommercial_tiers, usage, exporting_images, apidocs export-image-todrive; EE catalog pages SRTMGL1_003, NASADEM, COPERNICUS GLO30, MOD11A2, MCD12Q1, ERA5_LAND DAILY/MONTHLY, HydroATLAS level07; EE STAC catalog.json and ESA sub-catalog; lpdaac SRTMGL1 page; NSIDC GGD318; Chrome 126 release notes; Vercel limits, git-settings, cli/deploy, plans/hobby, fair-use, KB GitHub Actions guide; Playwright probe.
Failed / not found: EE catalog tag page `/datasets/tags/permafrost` 404; no permafrost in EE ESA sub-catalog; no Moon Trek credit line; no Cesium ion attribution clause; no GIBS rate limit; no Vercel Hobby commercial clause. A web search returned a Cesium forum post claiming Cesium Moon sits ~2.5 km above LOLA heights - forum, not official, unverified. WebSearch summaries were not used as sources.

## Open questions for the team

1. Will the public demo use ion imagery (1,000 sessions/month cap) or NASA GIBS only?
2. Is Moon 3D relief required (needs ion token), or is LOLA hillshade on a smooth ellipsoid acceptable?
3. Grid resolution: 0.1° or 0.25°? (ERA5-Land is ~0.1° native.)
4. Above 60°N: Copernicus GLO-30 (DSM, excludes Armenia/Azerbaijan) or another DEM?
5. Permafrost: HydroATLAS basin % in EE, or upload NSIDC GGD318 shapefile as an asset?
6. Export target: Google Drive or a Cloud Storage bucket (bucket needs billing)?
7. Videos: recorded on a team laptop with GPU, or frame-by-frame offline encoding?
8. Does any team member's institution make this "funded educational research" under Cesium ion terms?
