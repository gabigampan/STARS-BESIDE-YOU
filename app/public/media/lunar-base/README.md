# Lunar base mission video

**Credit line to show in the app:**
"Lunar base mission video: 3D simulation by the Stars Beside You team, driven by table data (not real footage)"

A 3D simulation, not real footage. The first caption cue and the closing card say so, and a line at the bottom of every frame says "3D simulation driven by table data. Not real footage."

Story (46 s): one full lunar day-night cycle, accelerated, at lunar cell **M62859 (84.5° S, 39.5° E)** on the Mons Mouton plateau ("Mons Mouton Plateau" is one of the nine candidate Artemis III landing regions, NASA RELEASE24-136, 2024-10-28). Night (the Earth low in the north-west), sunrise, a cylindrical module lowered onto its legs, an inflatable section expanding, a regolith berm built around it, the Sun going behind the western terrain, sunset and night cooling. The panel shows the modelled surface temperature, the measured minimum and maximum, the diurnal amplitude, the Sun's elevation and azimuth, the terrain horizon and the time compression; a small inset shows a restrained thermal tint (blue at the minimum, warm grey at the maximum) over a shaded relief of the patch. Closing card (40-46 s): the Earth analog **E19345 (36.5° N, 85.5° E, Kunlun Mountains, Xinjiang, China)** against the lunar cell.

## Files

| File | What it is | Size (bytes) |
|---|---|---|
| `lunar-base.mp4` | H.264 High@L4.1, yuv420p, 1920x1080, 30 fps, 46.000 s, 1380 frames, no audio, faststart (`moov` at byte 36, before `mdat`), CRF 25 | 8,786,493 |
| `lunar-base.webm` | VP9 profile 0, yuv420p, 1920x1080, 30 fps, 46.000 s, 1380 frames, two-pass CRF 34 | 7,976,069 |
| `lunar-base-poster.jpg` | Frame 600 (t = 20 s): module and inflatable in sunlight, berm nearly complete, long shadows | 317,149 |
| `lunar-base-poster.webp` | Same frame, WebP quality 88 | 177,846 |
| `lunar-base.en.vtt` | English descriptive captions, 12 cues, 0-46 s | 3,492 |
| `lunar-base.es.vtt` | Spanish descriptive captions, 12 cues, 0-46 s | 3,979 |

ffprobe (`-count_frames`): mp4 `h264 High level 41 yuv420p 1920x1080 30/1, 1380 frames, duration 46.000000, 1.53 Mb/s`; webm `vp9 Profile 0 yuv420p 1920x1080 30/1, 1380 frames, duration 46.000000, 1.39 Mb/s`; both VTT files parse in ffmpeg's WebVTT demuxer.

```html
<video controls playsinline preload="metadata" poster="/media/lunar-base/lunar-base-poster.webp">
  <source src="/media/lunar-base/lunar-base.webm" type="video/webm">
  <source src="/media/lunar-base/lunar-base.mp4" type="video/mp4">
  <track kind="captions" src="/media/lunar-base/lunar-base.en.vtt" srclang="en" label="English">
  <track kind="captions" src="/media/lunar-base/lunar-base.es.vtt" srclang="es" label="Español">
</video>
```

## How to re-render

Renderer and scenario: `app/video-sim/` (see its README). Everything shown comes from `app/video-sim/scenarios/lunar-base.json`.

```sh
cd app/video-sim && npm install
python3 -I tools/prepare.py scenarios/lunar-base.json --work $W   # 77 s: table check, DEM rows, horizons
node render.js scenarios/lunar-base.json --work $W                # 1380 frames, then encodes, captions, ffprobe
```

Render time: 1,139 ms per frame on average (SwiftShader, no GPU, 4 cores, screenshot included), 1380 frames in about 26 minutes; encodes about 4 minutes.

## Inputs, sources and levels

| On screen | Value | Level | Source |
|---|---|---|---|
| Lunar cell | M62859, 84.5° S 39.5° E (id checked against the coordinates) | grid | `tierra luna/output_real/moon_real_1deg.csv` |
| Measured min / max | 68.5 K / 255.56 K (`tmin_k`, `tmax_k`) | measured (Diviner GCP tbol, bolometric brightness temperature, all seasons 2009-2015) | moon table; `real_data/provenance_moon.csv` |
| Diurnal amplitude | 187.06 K | derived (tmax − tmin) | moon table |
| Card, Moon: min −204.65 °C, mean 152.45 K, elevation 6055.9 m, slope 9.608° | as in the table | derived / measured as tagged | moon table |
| Card, Earth: amplitude 27.12 K (MODIS LST, derived), min −28.68 °C (WorldClim air, modelled, non-commercial licence), mean 271.65 K (derived), elevation 4926 m (ETOPO 2022, measured, geoid), slope 2.003° (derived), permafrost class "continuo" shown as "continuous" (modelled, Obu et al.) | as in the table | as tagged | `earth_real_1deg.csv`; `real_data/provenance_earth.csv` |
| S0, obliquity, synodic period | 1361.0 W/m², 1.54°, 29.53 d | measured | NSSDC Moon fact sheet; NASA PIA13720 |
| Place | Mons Mouton, IAU centre 84.6° S 31.0° E, diameter 130 km; the cell centre is 24.6 km from it | gazetteer | https://planetarynames.wr.usgs.gov/Feature/16070 |
| Earth | drawn at az 320.37°, elevation 3.95°: the 2026-2044 mean from JPL Horizons (DE441, observer at 39.5° E −84.5°, every 12 h; range az 312.0-328.7°, elevation −3.33 to +11.25°, above a flat horizon 70.2 % of the time). The real terrain horizon in that direction is −2.49°, so the whole disc (radius 0.95°) clears it. Phase from the Sun's direction. | computed | Horizons API |

### Terrain (real relief)

- **Near patch:** LOLA **LDEM_80S_20M** V2.0, https://pds-geosciences.wustl.edu/lro/lro-l-lola-3-rdr-v1/lrolol_1xxx/data/lola_gdr/polar/img/ldem_80s_20m.img, rows 8546-8974 by HTTP range (the file is 1.85 GB). Scale factor at 84.5° S k = 1.0023, **true spacing 19.95 m/px**; ±2.99 km (301 x 301 nodes, no upsampling). Shown on screen as "20.0 m/px".
- **Far field:** LOLA **LDEM_80S_80M** V2.0 (79.8 m/px), rows 1305-3073, native spacing for horizons out to ±50 km, meshed at every 4th pixel (**319 m/px**, on screen).
- **Georeference check:** polar product cell mean 6056.25 m against the table's 6055.9 m (difference 0.35 m); my LDEM_16 recomputation 6055.91 m; lattice correlation with LDEM_16 0.995 (the other line sign: 0.126). Near and far products differ by 1.46 m RMS. The cell centre is at 6358.6 m; local slope 8.3° (downhill to the NNE); 955 m of relief within ±3 km, so "plateau" is the IAU feature, not flat ground at 20 m scale. The habitat stands on legs at the highest ground under its footprint; the berm follows the real ground.
- **Shaded-relief check:** straight-down render vs shaded relief from the grid (both lit from the NW at 25°): correlation 0.953 (the outer border of the render shows the far-field mesh where the near patch ends).

## Computed and modelled values

- Sun: sin h = sin(lat) sin(d) + cos(lat) cos(d) cos(H), lat = −84.5°, d = −1.54°, H linear from −150° to +210° (one full synodic day) over 40 s. Flat-horizon sunrise and sunset at H = ±106.2°.
- Terrain horizon and disc visibility: as for the solar video, from the habitat point 2 m above ground. Sun above the real terrain from 4.9 s to 24.7 s; between 24.7 s and the flat-horizon sunset (28.4 s) the Sun is above the horizon but behind the western terrain ("Sun blocked by terrain").
- **Surface temperature (model, stated on screen):** T = Tmin + (Tmax − Tmin) x g, g = cycle-normalised (sin h)^(1/4) while the Sun is up and more than half of its disc clears the real terrain, then g_sunset x exp(−t/τ) with τ = 3 Earth days, rescaled so that the cycle reaches exactly 68.5 K and 255.56 K (shown extremes 68.51 K and 255.56 K). Only the two end values are data; the curve shape, τ and the use of the local horizon are assumptions.
- Time compression = 29.53 d / 40 s = **x63,800**.
- Thermal tint: linear colour between the two measured values, one tint for the whole 6 km patch; the 3D terrain itself is never tinted.

## Assumptions (illustrative, stated)

- Habitat: rigid module 4.0 m diameter x 8.0 m; inflatable section 6.0 m x 5.0 m; regolith berm 1.5 m high, inner radius 11 m, 4 m wide, with an opening; order and timing (module 5-9 s, inflatable 9.5-14.5 s, berm 15-21.5 s) illustrative. Plain engineering shapes, not a real design.
- Season d = −1.54° (Sun reaches the table's `sun_elev_max_deg` 7.04° at noon).
- Night view: exposure raised to show earthshine (a light from the Earth's direction, 20 % of the Sun's display intensity times the Earth's lit fraction). Labelled on screen; not to scale. The Earth's mean position is held fixed (libration not animated).
- Fine surface texture procedural (as in the solar video); 3.5 % ambient fill; stars a seeded random background.

## Falls short of the brief / caveats

- The panel's status reads "Module placed" while the module is still being lowered (5-9 s); the captions say "Placing the module".
- 24.7-28.4 s: the Sun is behind the terrain while the Earth is a thin crescent (lit fraction about 0.14), so the frame is very dark for about 4 s.
- The Diviner min/max are cell averages over all seasons 2009-2015 for a 30 x 2.9 km strip; the curve applies them to one point.
- The Earth minimum is an air temperature (WorldClim, modelled) and the lunar minimum a surface brightness temperature: the card says so; they are not the same quantity.
