# Lunar base mission video

**Credit line to show in the app:**
"Lunar base mission video: 3D simulation by the Stars Beside You team, driven by table data (not real footage)"

A 3D simulation, not real footage. The first caption cue and the closing card say so, and a line at the bottom of every frame says "3D simulation driven by table data. Not real footage."

Story (46 s): part of one lunar day, accelerated, at lunar cell **M63528 (86.5° S, 11.5° W)**, 25.1 km from Mons Malapert, in **NASA's nine candidate landing regions near the lunar south pole** (the Lunar base zone; the cell's 1-degree square touches the edge of the Haworth region). The camera descends to the site while the Sun is up but still behind the northern terrain (site in shadow, exposure raised and said so on screen); the Sun rises over the terrain; a cylindrical module is lowered onto its legs and rests on the ground; an inflatable section expands; a regolith berm is built around it; the Sun, never above 5°, moves west low over the terrain and goes behind the western terrain; the site stays in shadow and cools. The panel shows the modelled surface temperature, the measured minimum and maximum, the diurnal amplitude, the Sun's elevation and azimuth, the terrain horizon, whether the habitat point is sunlit, the time compression and the Earth (hidden by the terrain from here at its mean position); a small inset shows a restrained thermal tint (blue at the minimum, warm grey at the maximum) over a shaded relief of the patch. Closing card (40-46 s): **analog 2 of the five Lunar base analogs shown (overall rank 3)**, the Earth analog **E17538 (41.5° N, 78.5° E, Xinjiang Uygur Zizhiqu, China; 62.3 km from Aheqi)** against the lunar cell, with real values, percentiles, real differences and the per-pair sentence. The pair matches by relative thermal position, not by equal temperatures.

## Files

| File | What it is | Size (bytes) |
|---|---|---|
| `lunar-base.mp4` | H.264 High@L4.1, yuv420p, 1920x1080, 30 fps, 46.000 s, 1380 frames, no audio, faststart (`moov` at byte 36, before `mdat`), CRF 25 | 11,168,347 |
| `lunar-base.webm` | VP9 profile 0, yuv420p, 1920x1080, 30 fps, 46.000 s, 1380 frames, two-pass CRF 34 | 11,824,940 |
| `lunar-base-poster.jpg` | Frame 600 (t = 20 s): module and inflatable in sunlight, berm being built, long shadows | 332,974 |
| `lunar-base-poster.webp` | Same frame, WebP quality 88 | 197,072 |
| `lunar-base.en.vtt` | English descriptive captions, 14 cues, 0-46 s; cue boundaries at every status change | 4,710 |
| `lunar-base.es.vtt` | Spanish descriptive captions, 14 cues, 0-46 s | 5,400 |

ffprobe (`-count_frames`): mp4 `h264 High level 41 yuv420p 1920x1080 30/1, 1380 frames, duration 46.000000, 1.94 Mb/s`; webm `vp9 Profile 0 yuv420p 1920x1080 30/1, 1380 frames, duration 46.000000, 2.06 Mb/s`; both VTT files parse in ffmpeg's WebVTT demuxer.

```html
<video controls playsinline preload="metadata" poster="/media/lunar-base/lunar-base-poster.webp">
  <source src="/media/lunar-base/lunar-base.webm" type="video/webm">
  <source src="/media/lunar-base/lunar-base.mp4" type="video/mp4">
  <track kind="captions" src="/media/lunar-base/lunar-base.en.vtt" srclang="en" label="English">
  <track kind="captions" src="/media/lunar-base/lunar-base.es.vtt" srclang="es" label="Español">
</video>
```

## Closing card re-rendered on 2026-11-15 (corrected Lunar base criteria)

The Lunar base suitability criteria were corrected on 2026-11-15 and the corrected model was confirmed by the independent re-audit. The pair is unchanged (E17538 with M63528, same values, percentiles, differences and similarity 97.31), but it is no longer the first: it is **analog 2 of the five shown** (`missions.json` `top5.ids` = 21054, 17538, 21833, 18627, 19672; overall ranks 1, 3, 5, 6, 7), with **suitability 43.15 and final 70.23** (before: "pair number 1", suitability 47.27, final 72.29). What changed:

- the card (frames 1200-1379, 40-46 s, fade-in included): title "Earth analog and lunar twin: lunar base, analog 2 of the five shown"; subtitle "Analog 2 of the five shown (overall rank 3). Suitability 43.15, similarity 97.31, final 70.23. ..."; the table, sentence and legend are unchanged;
- caption cue 13 (40 s, both languages) now starts with the analog's position, overall rank and the three scores;
- `scenarios/lunar-base.json` `pair_values` (rank 3, `top5_position` 2, suitability, final) and the check in `tools/prepare.py`, which now finds the item by its Earth id and refuses a rank, position, title or score that differs from the bundle.

Only the 180 card frames were rendered again (944 ms per frame); frames 0-1199 are the same PNG files as the first render. After re-encoding with the same settings, decoded frames 0-1164 of the mp4 and 0-1196 of the webm are bit-identical to the previous files (ffmpeg framemd5). Frames 1165-1199 (mp4) and 1197-1199 (webm) differ only by encoder look-ahead near the new frames: PSNR against the previous encode at least 57.9 dB (mp4, mean 61.9 dB on luma) and 74.5 dB (webm), against about 49 dB between either encode and the source PNG. The poster (frame 600) is byte-identical.

## How to re-render

Renderer and scenario: `app/video-sim/` (see its README). Everything shown comes from `app/video-sim/scenarios/lunar-base.json`.

```sh
cd app/video-sim && npm install
python3 -I tools/prepare.py scenarios/lunar-base.json --work $W   # ~3 min: table and bundle checks, DEM rows, horizons
node render.js scenarios/lunar-base.json --work $W --timeline     # optional: label of every frame (no rendering)
node render.js scenarios/lunar-base.json --work $W                # 1380 frames, then encodes, captions, ffprobe
```

Render time: 2,198 ms per frame on average (SwiftShader, no GPU, 4 cores shared with other jobs, screenshot included), 1380 frames in about 51 minutes; encodes about 4 minutes; `prepare.py` 208 s.

## Status labels (what the picture shows)

| Label on the panel | From - to (s) | Picture |
|---|---|---|
| Sun up, behind the northern terrain | 0.00-4.07 | camera descends from 1.5 km; habitat point in terrain shadow, the northern ridge in sunlight (overexposed); exposure x16 stated |
| Sun rising over the terrain | 4.07-5.50 | the solar disc clears the northern terrain; ground lights up, exposure falls to x1.2 |
| Lowering the module | 5.50-9.50 | module descends from 22 m onto its legs, in sunlight |
| Module placed | 9.50-11.00 | module at rest on the ground (from frame 285) |
| Inflatable section deploying | 11.00-15.50 | inflatable section expands from the end of the module |
| Inflatable section deployed | 15.50-16.50 | inflatable at full size, at rest |
| Building the regolith berm | 16.50-22.50 | berm rises around the habitat |
| Regolith berm built | 22.50-24.00 | berm complete |
| Habitat assembled, sunlit | 24.00-27.97 | complete habitat in low sunlight, long shadows |
| Sun partly behind the terrain | 27.97-29.10 | solar disc partly behind the western terrain; light dims, exposure rises |
| Sun behind the terrain: site in shadow | 29.10-40.00 (held on the card fade 40-40.8) | habitat and ground in terrain shadow under the uniform fill, distant sunlit terrain overexposed; exposure x16 stated |
| (closing card) | 40.0-46.0 | pair card, no panel |

"Module placed" appears from frame 285 (t = 9.5 s), the first frame at which the module rests on its legs (its descent is a smoothstep that reaches exactly 1 at 9.5 s); while it moves (5.5-9.5 s) the label is "Lowering the module". The same rule holds for "Inflatable section deployed" (from 15.5 s) and "Regolith berm built" (from 22.5 s). Caption cues start at the same frames, and the renderer refuses to write captions if the label changes inside a cue.

## Inputs, sources and levels

| On screen | Value | Level | Source |
|---|---|---|---|
| Lunar cell | M63528, 86.5° S 11.5° W (id checked against the coordinates) | grid | `tierra luna/output_real/moon_real_1deg.csv` |
| Zone | NASA's nine candidate landing regions near the lunar south pole (region A, 280 cells); the cell's 1-degree square intersects the Haworth footprint at its edge | team zone | `mission_zones.json`; `tierra luna/engine/data/artemis_iii_regions.geojson` (USGS navigational grids, McClernan 2024, DOI 10.5066/P1MEQ6UK; NASA release 24-136, 2024-10-28) |
| Place | 25.1 km from Mons Malapert (IAU centre 85.98° S 1.67° W, diameter 67 km), the cell's nearest primary IAU feature | gazetteer | `explain.json` (`similarity.twin.feature_km`), `lunar_named_sites.json`; http://planetarynames.wr.usgs.gov/Feature/16338 |
| Measured min / max | 41.23 K / 194.51 K (`tmin_k`, `tmax_k`) | measured (Diviner GCP tbol, bolometric brightness temperature, all seasons 2009-2015) | moon table; `real_data/provenance_moon.csv` |
| Diurnal amplitude | 153.27 K | derived (tmax − tmin) | moon table |
| Card, pair values | coldest temperature 248.61 K (−24.54 °C) / 41.23 K (−231.92 °C), real difference 207.38 K, percentiles 8.37 / 8.04 (0.34 points); daily swing 15.60 / 153.27 K, difference 137.67 K, percentiles 6.72 / 10.18 (3.46 points); slope 6.652 / 7.179° (0.527°); roughness 238.81 / 238.49 m (0.32 m); mean temperature 272.06 / 77.49 K (194.57 K) and relative elevation 2,807.0 / 680.7 m (2,126.3 m), both not part of the similarity; card title "lunar base, analog 2 of the five shown" (position 2 of `missions.json` `missions[lunar_base].top5.ids`, overall rank 3); suitability 43.15, similarity 97.31, final 70.23; the per-pair sentence verbatim | Earth coldest temperature modelled (WorldClim 2.1 air, non-commercial licence); Moon coldest temperature measured (Diviner surface); the rest derived | `app/public/data/v2/explain.json` (lunar_base, the item of E17538) and `missions.json` (`top5`), checked number by number by `prepare.py` (it refuses a wrong rank, position, card title or score); levels from `variables.json` and `missions.json` |
| Earth analog | E17538, 41.5° N 78.5° E, Xinjiang Uygur Zizhiqu, China; nearest populated place Aheqi, 62.3 km | grid / place labels | `explain.json` `place`; `earth_real_1deg.csv` |
| S0, obliquity, synodic period | 1361.0 W/m², 1.54°, 29.53 d | measured | NSSDC Moon fact sheet; NASA PIA13720 |
| Earth | not drawn: at its 2026-2044 mean position from JPL Horizons (DE441, observer at 348.5° E −86.5°, every 12 h, 13,879 rows; az 11.52°, elevation 3.14°; range az 3.5-19.7°, elevation −3.79 to +10.09°, above a flat horizon 65.5 % of the time) the real terrain horizon in that direction is 5.41°, so the disc (radius 0.95°) is hidden. Panel: "behind terrain (mean pos.)" | computed | Horizons API, queried 2026-11-15 |

### Terrain (real relief)

- **Near patch:** LOLA **LDEM_80S_20M** V2.0, https://pds-geosciences.wustl.edu/lro/lro-l-lola-3-rdr-v1/lrolol_1xxx/data/lola_gdr/polar/img/ldem_80s_20m.img, rows 9818-10177 by HTTP range. Scale factor at 86.5° S k = 1.0009, **true spacing 19.98 m/px**; ±3.0 km (301 x 301 nodes, no upsampling). Shown on screen as "20.0 m/px".
- **Far field:** LOLA **LDEM_80S_80M** V2.0 (79.9 m/px), rows 1758-3240, native spacing for horizons out to ±50 km, meshed at every 4th pixel (**320 m/px**, on screen).
- **Georeference check:** polar product cell mean 435.71 m against the table's 432.3 m (difference 3.4 m); LDEM_16 recomputation 432.32 m. Near and far products differ by 1.48 m RMS. The habitat point (cell centre) is at 528.8 m; local slope 2.5° at 20 m; 481 m of relief within ±3 km (352-833 m). The habitat stands on legs at the highest ground under its footprint; the berm follows the real ground.

## Computed and modelled values

- Sun: sin h = sin(lat) sin(d) + cos(lat) cos(d) cos(H), lat = −86.5°, d = −1.54°, H linear from −22° to +100° (122°, 10.0 Earth days) over 40 s. Flat-horizon sunrise and sunset at H = ±116.1°; highest Sun 5.04° at H = 0 (the table's `sun_elev_max_deg`).
- Terrain horizon and disc visibility: from the habitat point 2 m above ground, 720 azimuths. The Sun's disc starts to clear the northern terrain at 4.07 s (H = −9.6°) and is fully visible from 5.93 s; it starts to go behind the western terrain at 27.97 s (H = 63.3°) and is fully hidden from 29.1 s (H = 66.8°), while still 2.9° above the flat horizon. At this season the point is sunlit for about 76° of the 360° cycle; the table's `illum_frac` 0.0773 is the cell average over all seasons.
- **Surface temperature (model, stated on screen):** T = Tmin + (Tmax − Tmin) x g, g = cycle-normalised (sin h)^(1/4) while the Sun is up and more than half of its disc clears the real terrain, then g_sunset x exp(−t/τ) with τ = 3 Earth days, rescaled over the full cycle so that it reaches exactly 41.23 K and 194.51 K. Shown in this part of the day: 41.23-194.51 K (the shown extremes are the measured values, to 0.01 K). Only the two end values are data; the curve shape, τ and the use of the local horizon are assumptions.
- Time compression = 10.0 d / 40 s = **x21,600** (21,616 rounded to 3 figures).
- Thermal tint: linear colour between the two measured values, one tint for the whole 6 km patch; the 3D terrain itself is never tinted.

### Lighting (simulation)

This is a simulation, and the Sun is low here: at 86.5° S it never rises above 5.04° (southern-summer solstice, the most sunlit season, chosen for that reason), so shadows are long and the habitat point is sunlit only while the Sun clears the real terrain horizon. The light is one parallel Sun of fixed intensity with terrain shadows from the real LOLA horizons, plus a 3.5 % uniform fill standing in for light reflected by the surrounding sunlit ground (an assumption; the real reflected light is neither uniform nor computed). Nothing is brightened in the scene itself. What changes is the **display exposure**, as a camera's would: 1 while the habitat point sees the whole solar disc, x16 while it sees none of it, and 1 / (1/16 + (15/16) x visible disc fraction) in between, so the shadowed ground stays readable; whenever it is above 1.25 the panel says "Exposure raised xN to show the ground in shadow (not to scale)". Under the raised exposure the distant terrain still in sunlight shows as overexposed white, which is what a camera set for the shadow would record.

The video replaced (pair M62859 / E19345) had about 4 s that were almost black (24.7-28.6 s, scene-area mean luma 23.7-24.6 of 255): the Sun was behind the terrain and the only light was earthshine from a thin crescent Earth (lit fraction about 0.14) at a fixed exposure. Luminance of this render: mean luma of every frame (ffmpeg signalstats YAVG, 0-255) over 0-40 s: full frame 43.5-99.7, scene area (1100 x 900 px right of the panel) 44.8-126.6; per-second scene means 65-102; the lowest frame is t = 28.87 s (Sun almost hidden, exposure rising). No frame of the 3D part is below 43; the only frames below 40 are the closing card (dark background by design, 30-31, as the old card's 28.7).

## Assumptions (illustrative, stated)

- Habitat: rigid module 4.0 m diameter x 8.0 m; inflatable section 6.0 m x 5.0 m; regolith berm 1.5 m high, inner radius 11 m, 4 m wide, with an opening; order and timing (module 5.5-9.5 s, inflatable 11-15.5 s, berm 16.5-22.5 s) illustrative. Plain engineering shapes, not a real design.
- Season d = −1.54° (Sun reaches the table's `sun_elev_max_deg` 5.04° at noon); only part of the day is shown (the rest is terrain shadow or night at this point).
- Display exposure raised in shadow (above); 3.5 % uniform fill. The Earth's mean position is used (libration not animated); it is hidden by the terrain, so there is no earthshine.
- Fine surface texture procedural (as in the solar video); stars a seeded random background.

## Falls short of the brief / caveats

- In shadow the ground is lit only by the uniform fill, so relief and the habitat read as flat shapes; the real light reflected from the sunlit slopes would come from their directions.
- The Diviner min/max are cell averages over all seasons 2009-2015 for a 30 x 1.9 km strip; the curve applies them to one point.
- The Earth minimum is an air temperature (WorldClim, modelled) and the lunar minimum a surface brightness temperature: the card says so; they are not the same quantity.
- The Earth's place label is the bundle's (region, country, nearest populated place); no mountain-range name is shown because none is in the shipped data.
