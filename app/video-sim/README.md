# video-sim: deterministic renderer for the Solar and Lunar-base mission videos

Development tool, not shipped with the site. It renders the "Start mission" videos for the
Solar panels and Lunar base missions so that they match the team's rover video (light-grey
lunar terrain, black sky, hard sunlight, dark data panel at the top left).

Every frame is a pure function of the video time `t`: the page never reads the clock, and the
Node script steps `t = frame / 30` one frame at a time and screenshots each 1920x1080 frame.
Nothing is recorded in real time (this container has no GPU; WebGL runs in SwiftShader).

## One command per video

```sh
cd app/video-sim
npm install                       # three@0.170.0 only (node_modules is git-ignored)
W=/path/to/scratch/work           # downloads, terrain assets, frames (large; keep out of git)
python3 -I tools/prepare.py scenarios/solar.json --work $W        # terrain + checks (~30 s)
node render.js scenarios/solar.json --work $W                     # frames + mp4/webm/posters/vtt + ffprobe
python3 -I tools/prepare.py scenarios/lunar-base.json --work $W   # (~80 s)
node render.js scenarios/lunar-base.json --work $W
```

To change a pair, edit only the scenario JSON (site cell and coordinates, the copied table
values, DEM products, Sun season and hour-angle range, object sizes, camera keys, card text,
captions) and run the same two commands. `prepare.py` refuses to run if a value in
`table_values` differs from the table row with that `cell_id`, or if the id does not match the
coordinates. For the Lunar base video it also refuses to run if a number of the scenario's
`pair_values` block (the closing card: real values, percentiles, differences, the per-pair
sentence, the place names, the population sizes and the zone name) differs from the shipped bundle
(`app/public/data/v2/explain.json`, the item of that rank, and `missions.json`).

Other modes: `--stills 3,14.5` (single frames into `<work>/<name>/stills/`), `--frames a:b`
(render a range only; already-rendered frames are skipped, so an interrupted render resumes),
`--encode-only`, `--captions-only`, `--topdown` (straight-down check view, see Checks),
`--timeline` (status label, Sun and exposure of every frame without rendering, into
`<work>/<name>/timeline.json`; prints the frames where the label changes). `prepare.py --checks-only`
runs the table and bundle checks without the terrain.

## Files

| Path | What it does |
|---|---|
| `scenarios/*.json` | All inputs of one video. Every number on screen comes from here or from a stated formula. |
| `tools/dem.py` | LOLA polar stereographic IMG access by HTTP range (only the needed rows), projection, LDEM_16 cross-check. |
| `tools/prepare.py` | Table check, DEM fetch and georeference check, local grids, horizon maps, shaded relief, `terrain.json`. |
| `tools/check_relief.py` | Side-by-side of the shaded relief and the renderer's straight-down view, with their correlation. |
| `page/model.js` | The formulas (Sun position, disc visibility, panel power, temperature model, time compression). |
| `page/main.js` | three.js scene, data panel, closing card. |
| `render.js` | Static server, Playwright stepping, ffmpeg encodes, captions from the logged panel values, ffprobe. |

## How the scene is built (and what is not data)

- **Terrain (data).** Real LOLA relief around the cell centre, resampled onto a local east/north
  grid at the product's true ground spacing at that latitude (polar stereographic scale factor
  k = 2/(1+sin|lat|); no upsampling), heights in the site's tangent frame with the Moon's
  curvature applied: z = (R+h)cos(d/R) - (R+h0). A near patch at full resolution and a far field
  (decimated, never upsampled) out to tens of km so that the real horizon is in the picture.
- **Terrain shadows (computed).** Horizon angles from the height field (with curvature) for 90
  azimuths on both grids; a surface point is lit when the Sun's elevation exceeds the horizon in
  the Sun's azimuth (linear over the 0.533 deg solar disc). This gives hard, real-relief shadows.
  Object shadows: a 4096 px shadow map over +/-170 m.
- **Fine surface texture (procedural, not data).** Small craters (cells of 23, 9 and 3.7 m)
  and noise are added to the shading normals only, near the camera (faded out by 320 m), plus a
  +/-5 % albedo variation. They change no height, no horizon and no number.
- **Light.** One Sun (parallel light), a faint 3.5 % ambient fill standing in for light
  reflected by the surrounding ground (assumption), black sky, stars as a dim fixed background
  (seeded random, not a catalogue). No atmosphere, no glow. Lunar base only: if the Earth is drawn,
  at night a light from the Earth's direction scaled by the Earth's lit fraction is shown with a
  raised exposure (labelled "exposure raised to show earthshine (not to scale)"); and, when the
  scenario sets `render.shadow_exposure` (EX), the display exposure (a camera setting; no light is
  changed) is 1 while the habitat point sees the whole solar disc, EX while it sees none of it and
  1 / (1/EX + (1 - 1/EX) x visible disc fraction) in between, a function of t only; the panel says
  "Exposure raised xN to show the ground in shadow (not to scale)" whenever it is above 1.25.
- **Status labels (Lunar base).** Each habitat step has an `active` label, shown from `t0` while the
  part moves, and a `done` label shown only from `t1`, the first frame at which the part is at rest
  (the motion is a smoothstep that reaches exactly 1 at `t1`). Outside the steps the label follows
  the Sun at the habitat point (`sun_status`). Captions quote the label at each cue's start;
  `render.js` refuses to write them if the label changes inside a cue (`captions.cue_rule`).
- **Earth.** Drawn only where it is above the real terrain horizon: positions from JPL Horizons
  (DE441) for an observer at the site, 2026-2044 every 12 h (see the scenario's
  `earth_visibility`). Lit by the Sun's direction, so its phase is geometric. Libration wander
  is not animated.
- **Time.** The local hour angle runs linearly between the scenario's start and end values over
  `sim_end_s`; one synodic day (29.53 d, NSSDC) is 360 deg. Compression = elapsed simulated
  seconds / video seconds, shown on screen.

See each video's README in `app/public/media/<mission>/` for the inputs, sources, levels,
assumptions and ffprobe facts of that video.
