# Solar mission video

> **This video shows the EARLIER method, not today's pairs (note of 2026-11-15, statistical audit, `docs/stats_audit/4_audios_coherencia.md` 9.2.7).** It was made when Solar panels used the south-polar zone (latitude 75 S or further south) and the z-score twin rule; both were replaced on the morning of 2026-11-15 (`docs/DECISIONS.md`, "Decisiones tomadas (15-11-2026, mañana)"). Today Solar panels pair on sunlight above the atmosphere with cells of the equatorial maria (latitude within 30 degrees, elevation -1,200 m or lower). The pair in the video, lunar cell M59479 (75.5 S, 100.5 W) with Earth cell E44120 (Western Cape), is not a pair of the shipped bundle: E44120 now ranks 5,786th, with the twin M21923, and M59479 is outside today's Solar panels zone. The vertical tracking panels and the low polar Sun of the video do not describe today's Solar panels pairs either. Nothing in the video or its captions has been changed; a re-render on the number 1 pair (E38464 with M24296) is being scheduled separately. Until then, do not present this video as one of today's pairs.

**Credit line to show in the app:**
"Solar mission video: 3D simulation by the Stars Beside You team, driven by table data (not real footage)"

A 3D simulation, not real footage. The first caption cue and the closing card say so, and a line at the bottom of every frame says "3D simulation driven by table data. Not real footage."

Story (42 s): local dawn over the real relief of lunar cell **M59479 (75.5° S, 100.5° W)**, west of Boltzmann crater on the far side; the camera descends to a stowed array; the mast extends and two wings of hinged panels unfold; the vertical panels turn with the Sun as it moves along the horizon through an accelerated lunar day; long shadows sweep the ground; the Sun goes behind the western terrain at the end. Closing card (36-42 s): the Earth analog **E44120 (32.5° S, 20.5° E, Western Cape, South Africa)** against the lunar cell.

## Files

| File | What it is | Size (bytes) |
|---|---|---|
| `solar.mp4` | H.264 High@L4.1, yuv420p, 1920x1080, 30 fps, 42.000 s, 1260 frames, no audio, faststart (`moov` at byte 36, before `mdat`), CRF 25 | 11,051,971 |
| `solar.webm` | VP9 profile 0, yuv420p, 1920x1080, 30 fps, 42.000 s, 1260 frames, two-pass CRF 34 | 11,414,025 |
| `solar-poster.jpg` | Frame 780 (t = 26 s): array tracking, mast shadow, panel readable | 281,261 |
| `solar-poster.webp` | Same frame, WebP quality 88 | 161,626 |
| `solar.en.vtt` | English descriptive captions, 14 cues, 0-42 s | 3,888 |
| `solar.es.vtt` | Spanish descriptive captions, 14 cues, 0-42 s | 4,406 |

ffprobe (`-count_frames`): mp4 `h264 High level 41 yuv420p 1920x1080 30/1, 1260 frames, duration 42.000000, 2.11 Mb/s`; webm `vp9 Profile 0 yuv420p 1920x1080 30/1, 1260 frames, duration 42.000000, 2.17 Mb/s`; both VTT files parse in ffmpeg's WebVTT demuxer.

```html
<video controls playsinline preload="metadata" poster="/media/solar/solar-poster.webp">
  <source src="/media/solar/solar.webm" type="video/webm">
  <source src="/media/solar/solar.mp4" type="video/mp4">
  <track kind="captions" src="/media/solar/solar.en.vtt" srclang="en" label="English">
  <track kind="captions" src="/media/solar/solar.es.vtt" srclang="es" label="Español">
</video>
```

## How to re-render

Renderer and scenario: `app/video-sim/` (see its README). Everything shown comes from `app/video-sim/scenarios/solar.json`.

```sh
cd app/video-sim && npm install
python3 -I tools/prepare.py scenarios/solar.json --work $W   # 29 s: table check, DEM rows, horizons
node render.js scenarios/solar.json --work $W                # 1260 frames, then encodes, captions, ffprobe
```

Render time: 1,046 ms per frame on average (WebGL in SwiftShader, no GPU, 4 CPU cores, screenshot included), 1260 frames in about 22 minutes; encodes about 4 minutes.

## Inputs, sources and levels

| On screen | Value | Level | Source |
|---|---|---|---|
| Lunar cell, coordinates | M59479, 75.5° S 100.5° W (id checked against the coordinates) | grid | `tierra luna/output_real/moon_real_1deg.csv` |
| Earth cell | E44120, 32.5° S 20.5° E | grid | `tierra luna/output_real/earth_real_1deg.csv` |
| Card, Moon: irradiance 2.372 kWh/m²/day; highest Sun 16.04°; Sun below 5° for 0.2271 of daylight; sunlit 0.4543 of the time; slope 10.693°; elevation 122.4 m | as in the table | derived (elevation measured) | moon table; levels and formulas in `real_data/provenance_moon.csv` |
| Card, Earth: irradiance 5.518 kWh/m²/day; highest Sun 80.939°; Sun below 5° 0.07016; slope 2.137°; elevation 1127.1 m | as in the table | irradiance modelled (WorldClim 2.1 srad, non-commercial licence); Sun values and slope derived; elevation measured (ETOPO 2022) | earth table; `real_data/provenance_earth.csv` |
| Solar constant S0 | 1361.0 W/m² | measured | NSSDC Moon fact sheet, https://nssdc.gsfc.nasa.gov/planetary/factsheet/moonfact.html (same value as the table formula) |
| Lunar obliquity | 1.54° | measured | NASA PIA13720, https://science.nasa.gov/photojournal/south-pole-illumination-map |
| Synodic period | 29.53 days | measured | NSSDC Moon fact sheet |
| Place name | Boltzmann crater, IAU centre 74.82° S 269.59° E (90.41° W), diameter 72.3 km: the cell centre lies about 80 km from the crater centre, outside its rim | gazetteer | https://planetarynames.wr.usgs.gov/Feature/805 |
| Earth visibility | not drawn: from the site the Earth's elevation (JPL Horizons, DE441, observer at 259.5° E −75.5°, 2026-2044 every 12 h) is −11.43° to +5.63°, mean −2.88°, azimuth 90.8-109.5°; above a flat horizon 35.1 % of the time; the real terrain horizon in that direction is 3.8°, so the Earth is behind the terrain nearly always and below the horizon on average | computed | Horizons API |

### Terrain (real relief)

- **Near patch:** LOLA **LDEM_75S_60M** V2.0 (polar stereographic, 60 m/px true at the pole), https://pds-geosciences.wustl.edu/lro/lro-l-lola-3-rdr-v1/lrolol_1xxx/data/lola_gdr/polar/img/ldem_75s_60m.img, rows 8845-9088 fetched by HTTP range. At 75.5° S the projection's scale factor is k = 2/(1+sin 75.5°) = 1.0162, so the **true ground spacing is 59.04 m/px**; the patch is ±6.02 km (205 x 205 nodes at that spacing, no upsampling). Shown on screen as "59.0 m/px".
- **Far field:** LOLA **LDEM_60S_240M** V2.0 (236.2 m/px true at the site), rows 3918-4515, used at native spacing for horizons out to ±60 km and meshed at every 2nd pixel (**472 m/px**, shown on screen).
- **Georeference check:** the cos-lat weighted mean of the polar product over the 1-degree cell is 127.7 m; the table's `elevation_m` is 122.4 m (LDEM_16; my recomputation from LDEM_16: 122.37 m). Difference 5.3 m. The polar grid and LDEM_16 sampled on a 41x41 lat/lon lattice around the site correlate at 0.998 (line = LINE_PROJECTION_OFFSET − y/scale; the other sign gives 0.735). The near and far products differ by 3.6 m RMS over the near patch. The site itself (cell centre) is at 324 m: the cell spans 2.4 km of relief within ±6 km (a crater wall; local slope at the site 4.6°).
- **Shaded-relief check:** a straight-down render of the near patch from the renderer, lit from the north-west at 25°, correlates with the shaded relief computed directly from the elevation grid at 0.985 (`tools/check_relief.py`).
- Units: metres above the 1737.4 km sphere (DN x 0.5, label `SCALING_FACTOR`). Heights in the scene include the Moon's curvature.

## Computed values (formulas)

- Sun position: sin h = sin(lat) sin(d) + cos(lat) cos(d) cos(H), the table's formula; azimuth from the east/north components. lat = −75.5°, d = −1.54° (see assumptions), H runs linearly from −86° to +96° over 36 s.
- Terrain horizon: the maximum elevation angle of the real terrain (with curvature) from the hub (6 m above ground) in the Sun's azimuth, from the DEMs, 0.5° azimuth steps.
- Visible part of the solar disc: linear across the 0.533° disc.
- Panel tilt 90° (vertical); incidence = Sun elevation (the mast turns the panels to the Sun's azimuth).
- **Power per m² of panel** = S0 x cos(incidence) x visible disc fraction: 0 while the real terrain hides the Sun (first 3 s; last 0.5 s goes to 31 W/m² with the Sun at −0.01°, almost all of its disc behind the 0.25° horizon).
- **Energy per m²** = time integral of the power (trapezoid, 4 steps per frame) from the end of deployment (t = 11 s), in kWh/m² of simulated time. End value 327.75 kWh/m² over 10.4 Earth days.
- Time compression = (182° / 360°) x 29.53 d / 36 s = **x35,800** (shown rounded to 3 figures).

**Why per square metre.** The table values and the formula only give the sunlight reaching a surface. A real array's output would also need a cell efficiency, an area, a temperature coefficient and losses, none of which is in the project data. Showing W/m² and kWh/m² of panel keeps every number traceable to S0 and the geometry; a reader can multiply by an efficiency and an area of their choice.

## Assumptions (illustrative, stated)

- The array: mast 8.0 m, hub 6.0 m, two wings of 3 hinged panels of 2.0 x 1.2 m each (14.4 m² in total); vertical panels with one-axis (azimuth) tracking; mast extension 5.0-7.4 s and wing unfolding 7.4-11.0 s of video. A plain engineering shape, not a real design. Shown on screen ("Array size and timing: illustrative").
- Season: d = −1.54° (southern-summer solstice), so local noon reaches the table's `sun_elev_max_deg` 16.04°. Any other season gives a lower Sun.
- Time compression x35,800; the hour angle advances linearly.
- Fine surface texture: procedural small craters (cell sizes 23, 9, 3.7 m) and noise on the shading normals near the camera only, and a ±5 % albedo variation. They change no height, horizon or number.
- Light: a faint 3.5 % ambient fill for light reflected by the surrounding ground; stars are a dim seeded random background, not a catalogue.
- Object shadows are rendered from a 4096 px shadow map over ±170 m around the array; terrain shadows come from the horizon maps (90 azimuths, interpolated).

## Falls short of the brief / caveats

- The 59 m DEM is smooth at the scale of a few metres; all near-field detail is the procedural texture.
- The final 0.5 s before the card shows the Sun 99 % hidden (31 W/m²), not exactly 0.
- The Earth's irradiance in the card is WorldClim 2.1 (modelled; licence: non-commercial use only, no redistribution without permission, see `provenance_earth.csv`).
- The camera is free to move; the view is not a specific real camera.
