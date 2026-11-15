# Solar panels mission video

**Credit line to show in the app:**
"Solar panels mission video: 3D simulation by the Stars Beside You team, driven by table data, over real LOLA and Kaguya relief (SLDEM2015, 59 m per pixel); fine surface texture procedural (not real footage)"

A 3D simulation, not real footage. The first caption cue and the closing card say so, and a line at the bottom of every frame says "3D simulation driven by table data. Not real footage."

Re-rendered on 2026-11-15 for the first of the five Solar panels analogs of the shipped bundle after the Solar panels criteria were corrected (`missions.json` `missions[solar].top5.ids[0]` = 40184, overall rank 1; confirmed by the independent re-audit). It replaces the video of the earlier method (lunar cell M59479 at 75.5° S 100.5° W in the south-polar zone, with Earth cell E44120), which is not a pair of the shipped bundle. The scenario is written from the bundle by `app/video-sim/tools/solar_pair.py`; no value of the pair is typed by hand.

Story (44 s): one lunar daytime, accelerated, at lunar cell **M23206 (25.5° N, 13.5° W)**, 38.5 km from Timocharis, in the **low equatorial plains (the maria)**, the Solar panels zone (within 30° of the equator and at or below −1,200 m). The camera descends to a stowed array at sunrise; a short mast rises and two wings of hinged panels unfold and come to rest flat (horizontal), as the mission's irradiance (a horizontal surface) assumes; the Sun climbs in the east to 66.0° in the south at local noon and descends to the west; the shadows shorten and lengthen again; in the last 0.3 s the Sun goes behind the real terrain to the west (2.5° high there) while still 2° above the flat horizon. The panel shows the Sun's elevation and azimuth, the real terrain horizon, the modelled power and energy per m² of a flat panel, the elapsed Earth days, the time compression and a graph of the power over one whole lunar cycle with the night half shaded. Closing card (38-44 s): pair number 1 (the first of the five shown), the Earth analog **E40184 (21.5° S, 44.5° E, Menabe, Madagascar; 18.8 km from Manja)** against the lunar cell, with real values, differences, levels, the sunlight reaching the ground at the Earth site and the share lost in the atmosphere, and the per-pair sentence.

## Files

| File | What it is | Size (bytes) |
|---|---|---|
| `solar.mp4` | H.264 High@L4.1, yuv420p, 1920x1080, 30 fps, 44.000 s, 1320 frames, no audio, faststart, CRF 25 | @MP4@ |
| `solar.webm` | VP9 profile 0, yuv420p, 1920x1080, 30 fps, 44.000 s, 1320 frames, two-pass CRF 34 | @WEBM@ |
| `solar-poster.jpg` | Frame 570 (t = 19 s): local noon, Sun 66.0° up in the south, panels flat, short shadows | @JPG@ |
| `solar-poster.webp` | Same frame, WebP quality 88 | @WEBP@ |
| `solar.en.vtt` | English descriptive captions, 14 cues, 0-44 s; cue boundaries at every status change | @ENVTT@ |
| `solar.es.vtt` | Spanish descriptive captions, 14 cues, 0-44 s | @ESVTT@ |

ffprobe (`-count_frames`): @FFPROBE@; both VTT files parse in ffmpeg's WebVTT demuxer.

```html
<video controls playsinline preload="metadata" poster="/media/solar/solar-poster.webp">
  <source src="/media/solar/solar.webm" type="video/webm">
  <source src="/media/solar/solar.mp4" type="video/mp4">
  <track kind="captions" src="/media/solar/solar.en.vtt" srclang="en" label="English">
  <track kind="captions" src="/media/solar/solar.es.vtt" srclang="es" label="Español">
</video>
```

## How to re-render

Renderer and scenario: `app/video-sim/` (see its README). Everything shown comes from `app/video-sim/scenarios/solar.json`. The relief file must be in `$W/cache/` (one file, 1,415,577,600 bytes; URL below).

```sh
cd app/video-sim && npm install
W=/path/to/scratch/work; mkdir -p $W/cache
curl -o $W/cache/sldem2015_512_00n_30n_315_360_float.img https://pds-geosciences.wustl.edu/lro/lro-l-lola-3-rdr-v1/lrolol_1xxx/data/sldem2015/tiles/float_img/sldem2015_512_00n_30n_315_360_float.img
python3 -I tools/solar_pair.py                               # scenarios/solar.json from the bundle (first of top5) and the tables
python3 -I tools/prepare.py scenarios/solar.json --work $W   # ~40 s: table and bundle checks, relief, georeference check, horizons
node render.js scenarios/solar.json --work $W --timeline     # label of every frame (no rendering)
python3 -I tools/solar_pair.py --timeline $W/solar/timeline.json   # adds the cues where the real terrain hides the Sun
node render.js scenarios/solar.json --work $W                # 1320 frames, then encodes, captions, ffprobe
```

`render.js` runs `prepare.py --checks-only` first and refuses to start if a value of the scenario differs from the tables or from the shipped bundle.

Render time: @RTIME@

## Status labels (what the picture shows)

| Label on the panel | From - to (s) | Picture |
|---|---|---|
| Sunrise: low Sun in the east, panels stowed | 0.00-2.00 | camera descends from 1.9 km over the mare; Sun 1.6-9.9° up in the east (az 89-93°); real craters and ridges throw long shadows; array folded; exposure x8.0 falling to x2.5 stated |
| Morning: Sun climbing, panels stowed | 2.00-5.00 | camera reaches the folded array; Sun 10.0-22.5°; shadows shorten; exposure stated until 4.33 s |
| Unfolding the flat panels | 5.00-10.00 | mast rises, the two wings unfold upwards and fold down to flat (they move until 10.00 s) |
| Panels deployed, lying flat | 10.00-11.50 | array at rest, panels horizontal, cells facing the sky (from frame 300, the first at rest) |
| Morning: Sun climbing in the east | 11.50-15.03 | Sun 48.5-60.0°, az 120-140°; short shadows under the wings |
| Sun high in the sky: short shadows, most power | 15.03-23.00 | Sun above 60° (66.0° in the south at 19.0 s, local noon); shadows almost under the panels; power 1,179-1,244 W/m² |
| Afternoon: Sun descending towards the west | 23.00-36.03 | Sun 60.0° down to 10.0°, az 220-267°; shadows lengthen to the east; exposure stated from 33.70 s |
| Low Sun in the west: long shadows | 36.03-37.73 | Sun 9.9° down to 2.8° (az 267-270°); very long shadows of the array and the craters; exposure x2.5 rising to x8.0 stated |
| Sun partly behind the terrain | 37.73-37.87 | the solar disc goes behind the real western terrain (horizon 2.5° at az 270°); light on the array fades |
| Sun behind the terrain | 37.87-38.00 (held on the card fade 38.0-38.8) | array and nearby ground in terrain shadow, power 0 W/m², distant sunlit ground still bright; Sun 2.1-1.7° above the flat horizon |
| (closing card) | 38.0-44.0 | pair card, no panel |

The labels are computed from the same values the picture is rendered from (`page/main.js` `solarStatus`): the deployment labels from the deployment times (the unfolding is a smoothstep that reaches exactly 1 at 10.0 s), the others from the Sun's elevation at the array (below 10° "low", from 60° "high") and the sign of the hour angle (morning or afternoon); the real terrain horizon at the array (−0.25° to 3.27°, highest towards az 312°) hides the Sun only at the very end, and the labels say so. Caption cues start at the frames where the label changes (2.0, 5, 10, 11.5, 15.033, 23.0, 36.033, 37.733, 37.867 s, from `render.js --timeline`) plus 19 s (noon), 30 s and the card (38, 41 s); `render.js` refuses to write the captions if the label changes inside a cue.

## Inputs, sources and levels

| On screen | Value | Level | Source |
|---|---|---|---|
| Lunar cell | M23206, 25.5° N 13.5° W (id checked against the coordinates) | grid | `tierra luna/output_real/moon_real_1deg.csv`; `explain.json` solar item of E40184, `similarity.twin` |
| Pair selection | the first id of `missions.json` `missions[solar].top5.ids` (40184; overall rank 1) | bundle | `tools/solar_pair.py`; `prepare.py` refuses a scenario whose Earth point is not that first id |
| Zone | "Low equatorial plains (the maria)": absolute latitude ≤ 30° and elevation ≤ −1,200 m, 6,686 cells; the cell's elevation is −2,187.3 m | team zone | `mission_zones.json` region D label (`mission_zone_regions.solar`); rule and cell count from `missions.json` `missions[solar].similarity.zone` |
| Place | 38.5 km from Timocharis, the cell's nearest primary IAU feature | gazetteer | `explain.json` (`similarity.twin.feature`, `feature_km`) |
| Earth analog | E40184, 21.5° S 44.5° E, Menabe, Madagascar; nearest populated place Manja, 18.8 km | grid / place labels | `explain.json` `place`; `earth_real_1deg.csv` |
| Card: sunlight above the atmosphere (key variable, tolerance 0.6 kWh/m²/day) | Earth 9.3437, Moon 9.383, difference 0.0393 kWh/m²/day | Earth derived (formula from latitude, top of the atmosphere); Moon derived (table surface irradiance, horizontal, whole lunar cycle) | `explain.json` `similarity.variables`; levels from `missions.json` `similarity.variables[].sides` |
| Card: sunlight reaching the ground | Earth 5.745 kWh/m²/day; Moon 9.383 (no atmosphere); share lost **39 %** ("5.7 of 9.3") | Earth modelled (WorldClim 2.1, non-commercial licence); Moon derived | `explain.json` `similarity.atmosphere` (ground 5.745, top 9.3437, lost_share 0.3851); the 39 % follows the display rule of `similarity.json` `texts.solar_limitation` (`share_lost_of_displayed_tenths`: A = 93, G = 57, floor((200 (A − G) + A) / (2A)) = 39), recomputed by `prepare.py` |
| Card: slope (secondary, tolerance 2°) | 0.753° / 0.757°, difference 0.004° | derived | `explain.json`; `variables.json` |
| Card: roughness (secondary, tolerance 30 m) | 26.56 m / 27.15 m, difference 0.59 m | derived | `explain.json`; `variables.json` |
| Card: mean surface temperature, daily swing (not part of the similarity) | 300.56 / 212.81 K (87.75 K); 13.6 / 289.73 K (276.13 K) | derived | `explain.json` `not_part_of_similarity`; `variables.json` |
| Card: scores | pair number 1; suitability 97.94, similarity 99.83, final 98.88; the per-pair sentence and the saturation note (`similarity.json` `texts.solar_similarity_saturation`) verbatim | derived | `explain.json`, `similarity.json` |
| S0, obliquity, synodic period | 1361.0 W/m², 1.54°, 29.53 d (the bundle's `lunar_day_earth_days`) | measured | NSSDC Moon fact sheet, https://nssdc.gsfc.nasa.gov/planetary/factsheet/moonfact.html; NASA PIA13720, https://science.nasa.gov/photojournal/south-pole-illumination-map |
| Earth (panel row) | not drawn; "~61° up, mean pos.": at its mean position (sub-Earth point 0° N 0° E) the Earth is 61.4° up (90° minus the 28.6° arc from the site; parallax and libration ignored, a geometric estimate), above the camera's view | computed | formula |

`prepare.py` checks 16 table values against the two 1-degree tables and 70 values of the scenario's `pair_values` block against the bundle (that the pair is the bundle's first, ids, coordinates, scores, every Earth, Moon and difference value with its tolerance, role and weight, the atmosphere values and the displayed 9.3 / 5.7 / 39 %, the per-pair sentence, the saturation note, the lunar day, place names, the zone rule, cell count and label, and the level of every value on the card against `variables.json` and `missions.json`). A changed number, level or text stops the render (tested: share lost 36, a MEASURED level, a slope each refused, on the previous pair).

### Terrain (real relief)

- **Product (near and far):** **SLDEM2015** (LOLA altimetry co-registered with SELENE/Kaguya Terrain Camera stereo, Barker et al. 2016), tile **SLDEM2015_512_00N_30N_315_360_FLOAT**, 512 pixels per degree, simple cylindrical, float32 heights in km above the 1737.4 km sphere; file `sldem2015_512_00n_30n_315_360_float.img`, 1,415,577,600 bytes, https://pds-geosciences.wustl.edu/lro/lro-l-lola-3-rdr-v1/lrolol_1xxx/data/sldem2015/tiles/float_img/sldem2015_512_00n_30n_315_360_float.img (label `..._float.lbl` beside it; NASA PDS Geosciences Node, LOLA archive, `sldem2015/tiles/float_img`; file date 2015-07-14, label PRODUCT_CREATION_TIME 2015-09-15; downloaded in full on 2026-11-15, no account; sha256 1f1bdbead0e872362b4e828697de9ff97524b96671f487714ade724547ba8904). It is finer than the tables' LDEM_16 (about 1.9 km per pixel) by a factor of 32.
- **Near patch:** ±5.98 km around the cell centre at the product's true north-south spacing, **59.2 m/px** (203 x 203 nodes; east-west the product is finer, 53.5 m at 25.5° N, so nothing is upsampled), rows 2202-2406.
- **Far field:** the same file sampled every 4 pixels (236.9 m) for the horizons out to ±60 km, meshed at **474 m/px** (on screen); rows 1291-3325 (heights −4,800 to −1,077 m within ±60 km).
- **Georeference check:** the cos-lat weighted mean of the product over the 1-degree cell is −2,187.2 m against the table's `elevation_m` −2,187.3 m (difference 0.09 m); recomputed from LDEM_16 −2,187.30 m. The near patch and the far sampling differ by 3.0 m RMS. Cell centre −2,220.2 m; 463 m of relief within ±6 km (−2,547 to −2,084 m).
- **Shaded-relief check:** the renderer's straight-down view of the near patch and the shaded relief computed directly from the elevation grid (both lit from the north-west at 25°) correlate at 0.933 (`tools/check_relief.py`).
- The same file also covers the previous candidate M24296 (22.5° N 3.5° W): its terrain was prepared and checked too (cell mean −1,841.6 m against −1,842.7 m), in case the verdict had gone the other way.

## Computed and modelled values

- Sun: sin h = sin(lat) sin(d) + cos(lat) cos(d) cos(H), the formula of the tables and of the Lunar base video, lat = 25.5°, d = +1.54° (northern-summer solstice, so that the noon Sun reaches the table's `sun_elev_max_deg` 66.04°), H linear from −89° to +89° over 38 s. Flat-horizon sunrise and sunset at H = ±90.73°: **14.9 Earth days of daylight and 14.6 of night in the 29.53-day lunar day**; the video shows 14.6 of the 14.9 daylight days (Sun 1.6° at the start). As the approved sentence says, the lunar day lasts 29.5 Earth days and about half of it is night; the panel says so and the graph shades the night.
- Terrain horizon and disc visibility: from a point 2.4 m above the ground at the array, 720 azimuths, from the real relief with curvature. The Sun starts to go behind the western terrain at 37.73 s and is fully hidden from 37.87 s (Sun 2.1° above the flat horizon, terrain 2.5°).
- **Power per m² of a flat panel (model, stated on the panel):** P = S0 x sin(h) x visible disc fraction, S0 = 1361 W/m²: 37 W/m² at the first frame, 1,244 W/m² at noon, 0 W/m² once the terrain hides the Sun. No cell efficiency, area, temperature coefficient or losses (none is in the project data), so the numbers are sunlight on the panel, not electrical output.
- **Energy per m²:** time integral of the power from the end of deployment (10 s), trapezoid with 4 steps per frame: @EEND@ kWh/m² by 38 s.
- Whole-cycle check: the same model at d = +1.54° gives 9.57 kWh/m²/day averaged over the 29.53-day cycle; at d = 0 it gives 9.384, the table's `irradiance_kwh_m2_day` 9.383 for this cell (the table does not use a season).
- Time compression = (178° / 360°) x 29.53 d / 38 s = **x33,200** (33,198 rounded to 3 figures).

### Lighting (simulation)

One parallel Sun of fixed intensity (3.2 in renderer units, lower than the polar videos' 7.0 so that the 69° noon Sun does not saturate the light-grey ground), terrain shadows from the real SLDEM2015 horizons, object shadows from a 4096 px shadow map over ±170 m, a 3.5 % uniform fill standing in for light reflected by the surrounding ground (assumption), black sky, stars a dim seeded background. At sunrise and sunset the flat ground is lit at 1.5-10° and would read as almost black on screen, so the **display exposure** (a camera setting; the light and the power are not changed) is min(8, max(1, sin 25° / sin h)), a function of t only: x8.0 at both ends, x2.4 at 10°, 1 from 25°; whenever it is above 1.25 (0-4.33 s and 33.70-38 s) the panel says "Exposure ×N for the low Sun (not to scale)". The Earth is not drawn, so there is no earthshine.

## Luminance check

@LUMA@

## Assumptions (illustrative, stated)

- Array: short mast, panels about 2.8 m above the ground; two wings of 3 hinged panels of 2.0 x 1.2 m (14.4 m² in total), unfolding 5.0-10.0 s and ending flat (tilt 0°), no tracking. A plain engineering shape, not a real design ("Array size and timing: illustrative" on screen).
- Season d = +1.54°; any other season changes the noon Sun by at most 3.1°.
- Display exposure raised for the low Sun (above); 3.5 % uniform fill.
- Fine surface texture procedural (small craters of 23, 9 and 3.7 m and noise on the shading normals near the camera, ±5 % albedo variation); it changes no height, horizon or number.

## Falls short of the brief / caveats

- The power is sunlight per m² on a flat panel, a model; it is not electrical output, and the panel does not say what a panel would produce on Earth. The card shows instead that only 5.745 of the 9.3437 kWh/m²/day above the atmosphere reach the ground at the Earth site (39 % lost, as displayed by the bundle's rule).
- 59 m per pixel resolves craters of a few hundred metres; everything smaller near the camera is the procedural texture.
- The Solar panels similarity is saturated (the card's legend quotes the bundle's note): 99.83 says that the pair is within the tolerances, not that it is closer than other pairs.
- The Earth's position is a geometric estimate (not drawn), not a Horizons query as in the Lunar base video.
- The Earth cell's place label is the bundle's (region, country and nearest populated place).
- In the last 0.13 s (frames 1136-1139) the array is in terrain shadow with the exposure at x8: the ground near it reads dark grey, not black (see the luminance check).
- The camera is free to move; the view is not a specific real camera.
