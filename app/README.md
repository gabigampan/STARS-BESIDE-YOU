# Stars Beside You: web app (scene and shell)

A static site (Vite + TypeScript + CesiumJS 1.147.0) showing a 3D Earth and a 3D Moon side by side
(stacked on narrow screens), lit by the same Sun from one shared clock. It is the base on which the
mission panels, data layers and videos are built. It needs no key and no server.

```
npm install
npm run dev        # http://localhost:5173
npm run typecheck  # tsc --noEmit, strict
npm run build      # -> dist/ (static, deployable as is)
npm run smoke      # build, serve dist/, check both globes in headless Chromium, save screenshots
                   # options: --no-build --skip-4k --only=desktop,phone,fullmoon,tablet,uhd
npm run iau        # rebuild public/static/iau_moon_features.json from the IAU gazetteer .dbf
```

Node 22. Build size (2026-11-14): about 12 MB on disk without the engine's `data/` folder
(JS bundle 3.97 MB, 1.06 MB gzipped; Cesium workers, star map and textures 7.7 MB; fonts and
IAU names under 0.3 MB), 5.4 MB as a gzipped archive. `dist/` is self-contained: Cesium's workers, star map and textures are copied to
`dist/cesium/` and the fonts are bundled (no font CDN).

## What is on screen

| Body | Layer | Source (all key-free, CORS checked 2026-11-14) |
|---|---|---|
| Earth | Base imagery | NASA GIBS `BlueMarble_NextGeneration`, EPSG:4326, matrix set `500m` |
| Earth | Sharper imagery below ~1,300 km altitude (fades in) | EOX Sentinel-2 cloudless **2016** (`s2cloudless`, WGS84), CC BY 4.0 |
| Earth | Night lights, night side only (`nightAlpha`) | NASA GIBS `VIIRS_Black_Marble` 2016 |
| Earth | Country and city names (switchable) | NASA GIBS `Reference_Labels_15m` |
| Earth | Sky and ground atmosphere, Sun lighting, Sun and Moon discs | CesiumJS |
| Moon | Imagery on `Ellipsoid.MOON` | NASA Moon Trek `LRO_WAC_Mosaic_Global_303ppd_v02`, matrix set `default028mm` (standard 2x1 geographic tiling, levels 0-8) |
| Moon | Feature names (switchable), shown by size and decluttered | USGS/IAU Gazetteer of Planetary Nomenclature, `public/static/iau_moon_features.json` |
| Both | Star background | Cesium's bundled Tycho-2 sky box |

GIBS EPSG:4326 tiles are 512 px with a level-0 grid that overhangs the globe (2 x 1 tiles of
288 deg), so `src/imagery/gibsTilingScheme.ts` describes the real extents (adapted from NASA's
gibs-web-examples). The Moon Trek WAC set is a standard geographic scheme.

**Sun on the Moon.** Cesium lights a globe with the Sun in Earth's frame. For the Moon the Sun
direction is computed in the Moon's body-fixed frame from the shared clock (Simon 1994 positions
and the IAU WGCCRE lunar orientation model, `src/scene/sun.ts`) and set as the Moon scene's
`DirectionalLight`. A small globe material makes the night side dark (airless body, hard
terminator). Shading and night lights fade out when the camera is close (below ~650 km on the
Moon, ~2,500 km on Earth) so any site can be inspected whatever the local time of day. The
header's **Sunlight** control picks the instant (see "Sunlight and time" below); the default is
the computed Full Moon instant, **24 Nov 2026, 10:45 UTC**. Add `?time=2026-11-24T12:00:00Z`
(any ISO time) to the page URL to light both globes for that moment instead, or
`?light=now|even|full-moon` to start on one of the three choices.

**Not included (and why).** Clouds: the NASA Visible Earth host for the Blue Marble cloud composite
(eoimages.gsfc.nasa.gov) reset every connection from the build container, so no cloud image could
be verified or bundled; there is no cloud layer. The star background in the Moon view is oriented
with Cesium's Earth-frame logic (cosmetic only).

## Optional Cesium ion upgrade

`.env.local` (git-ignored) may hold `VITE_CESIUM_ION_TOKEN`. It is used only when the build also
sets `VITE_USE_ION=1`:

```
VITE_USE_ION=1 npm run build
```

Then `src/scene/ionUpgrade.ts` adds Cesium World Terrain (water mask, vertex normals), Bing aerial
imagery (ion asset 2) and the Cesium Moon tileset (asset 2684829, if the account has it). Without
`VITE_USE_ION=1` the token is replaced by an empty string at build time, so it never reaches
`dist/` (the smoke test checks this). The key-free build is the one to deploy.

## API for the next stage (`src/api.ts`)

```ts
import { globesApi, type Body } from './api';   // Body = 'earth' | 'moon'

await globesApi.ready;          // both scenes exist
await globesApi.imageryReady;   // both globes drew their first imagery (rejects with the shown message)

// Look straight down at lat/lon (degrees, longitude east -180..180) from heightKm.
// Resolves true when the flight ends, false if cancelled. Instant under prefers-reduced-motion.
await globesApi.flyTo('moon', -43.3, -11.2, 400, 2);

// Canvas position (CSS px, relative to that body's canvas) or null on the far side.
const p = globesApi.toCanvas('earth', 40.4, -3.7);   // { x, y, inView } | null

// Called whenever either camera moves; returns an unsubscribe function.
const off = globesApi.onCameraMove((body) => { /* reposition markers for `body` */ });

globesApi.viewer('earth');      // CesiumWidget
globesApi.scene('moon');        // Cesium Scene (requestRenderMode is on: call scene.requestRender() after changes)
globesApi.resetView();          // both, or resetView('moon')
globesApi.setLabelsVisible(false);
globesApi.prefersReducedMotion();
```

The same object is on `window.starsBesideYou` for the console and tests.

Notes for adding layers: both scenes use `requestRenderMode`, so after adding entities or
primitives call `scene.requestRender()`. Use `Ellipsoid.MOON` (or `globesApi.scene('moon').ellipsoid`)
for every Moon coordinate conversion. `Ellipsoid.default` is left as WGS84.

## Shell

- `#mission-panel` (left) and `#detail-panel` (right; bottom on narrow screens) exist in
  `index.html` as empty `hidden` asides with styles ready. Remove `hidden` to show them.
- Credits dialog lists every source with its credit line and licence (`src/ui/credits.ts`);
  Cesium's own credit line stays visible on each globe.
- Loading screen stays until both globes have drawn their first imagery; a failed or slow source
  is named in the message, with a Reload button.
- Keyboard: `Home` resets both views (`R` now repeats the audio guide, see below); double click resets one globe. Every control is at
  least 44 px and shows a focus ring.

## Accessibility layer (`src/a11y/`)

One product: the layer is built into the flow above, not a second app.

### Keyboard map

| Key | Where | What it does |
| --- | --- | --- |
| `1` `2` `3` | Start screen | Choose the Rover, Solar panels or Lunar base mission (the order of the bundle's offered missions); each choice shows "Press 1" ... as a visible key hint |
| `1` to `5` | Mission screen | Open one of the five best analogs (the five large numbered buttons first in the mission panel) |
| `Esc` | Anywhere | Back one step: pair to mission, mission to start. An open dialog (shortcuts, Data and limits, zone, video) closes first |
| `R` | Anywhere | Repeat the audio guide's current track from the start (or start it after a reload, when the browser refused to start sound on its own) |
| `?` | Anywhere | The list of shortcuts (also the "Keys" button in the header, on every screen) |
| `Home` | Anywhere | Reset both globe views |
| `Tab`, `Space`, `Enter` | Anywhere | Move between controls and use them; `↑` `↓` move through the ranked list |

Shortcuts never fire with Ctrl, Alt or Cmd held down, inside a text field (the search), a slider,
a select or a radio group, or while a dialog is open. Focus moves to the heading of each new step;
the single live region (`#flow-status`) announces each step in one sentence. The five best analogs
are the team's (ranks 1 to 5 of the bundle under the team's weights, read at run time); when the
user's own weights are in use the panel says so in words.

### Audio guide and captions

- Switch "Audio guide" in the header, **off by default**, remembered in `localStorage`
  (`starsBesideYou.audioGuide`; a browser without storage keeps it for the page only). While it is
  off nothing sounds and no audio file is requested.
- `src/a11y/audio.ts` owns the only `<audio>` element of the page. Starting a track pauses and
  rewinds the previous one; two tracks never sound at once.
- The files are the team's recordings, in `public/audio/` (served as `audio/` beside
  `index.html`): `00_welcome.mp3`; `m1_rover.mp3`, `m2_solar.mp3`, `m3_base.mp3` (mission
  introductions); `rover_1.mp3` ... `rover_5.mp3`, `solar_1.mp3` ... `solar_5.mp3`, `base_1.mp3` ...
  `base_5.mp3` (the five best pairs of each mission). They were recorded by the team (text to speech,
  American English voice) and are shipped unchanged; `SHA256SUMS.txt` holds their checksums and
  `npm run test:a11y` checks them. The app never generates, synthesises or edits audio and does not
  use the browser's speech synthesis.
- `transcripts.json` maps each file name to the exact text spoken in it: it is the caption, shown
  character for character, read at run time.
- `tracks.json` (written for the app) lists every track: `id`, `step` (`start`, `mission`, `pair`),
  `file`, and for pair tracks `mission`, `rank`, `earth_cell_id` and `moon_cell_id` (from
  `docs/AUDIO_TOP5.json`: rank n of each mission there is track `<mission>_n`). It holds no caption
  text. A pair track plays only when the pair on screen has exactly those two cell ids (and the
  team's weights are in use); otherwise the caption is built from the data on screen and nothing plays.
- **The five analogs** come from the bundle: `missions.json` `missions[].top5` (`ids` in order,
  `overall_ranks`, `rule`, revision 7); without it, ranks 1 to 5. A button whose pair is elsewhere in
  the full ranking says "Ranked N overall"; the rule text and the notes marked `top5` are shown
  under the five. A pair track plays only for the button number it was recorded as and the same two
  cell ids; a mission introduction (which names the five) plays only when all five recordings match
  the bundle's five, otherwise a caption from the screen is shown.
- **Tracks awaiting a new recording**: `public/audio/pending.json`
  (`{"pending_rerecord": ["m1_rover.mp3", ...], "note": "..."}`, maintained by the director; absent
  or empty = none). A listed track shows its (new) caption with "Text only: new recording pending"
  and is never requested, not even with R.
- **Notes from the bundle**: every `similarity.json` text with `show` is rendered verbatim in each
  place it names (`mission_card`: behind "Limits of this list" in the mission panel; `top5`: under
  the five; `pair_panel`: next to the similarity of every pair; `data_and_limits`: in the dialog),
  for the missions it names; no per-key code.
- **Replacing a track**: overwrite the MP3 under the same name, put its new text in
  `transcripts.json` under the same key and update `SHA256SUMS.txt`
  (`sha256sum *.mp3 > SHA256SUMS.txt` in `public/audio`). No code change.
- The caption area (under the steps, on every screen) shows the title of the step, the state in words
  (Playing, Paused, Finished, Text only, Press R to play, Audio not available: text shown) and a
  Repeat control. A missing or failing file shows its caption with "Audio not available: text shown"
  and no error. **Screen readers**: the caption area is not a live region; the live region only
  announces the step in one short sentence, so the recording and the screen reader never read the
  same long text and nothing is heard twice. The caption stays readable as ordinary text (and can be
  scrolled with the keyboard).

### Colour-blind mode and palettes

- Switch "Colour-blind mode" in the header, off by default, remembered
  (`starsBesideYou.colourBlind`). It swaps the whole palette at once: interface tokens (text,
  accent, focus ring, buttons, badges, states, zone swatch) and the globe overlays (marker score ramp,
  selection ring, beam, zone outline, cell outlines), all defined in `src/a11y/palette.ts`.
- The colour-blind-safe palette uses the Okabe-Ito colours: M. Okabe and K. Ito, "Color Universal
  Design (CUD): how to make figures and presentations that are friendly to colorblind people",
  J*Fly, https://jfly.uni-koeln.de/color/ (orange #E69F00, sky blue #56B4E9, bluish green #009E73,
  yellow #F0E442, blue #0072B2, vermillion #D55E00, reddish purple #CC79A7).
- Checked by `npm run test:a11y` with the colour-vision-deficiency simulation of the `culori`
  package (`filterDeficiencyProt`, `filterDeficiencyDeuter`, `filterDeficiencyTrit`, after Machado,
  Oliveira and Fernandes 2009; https://culorijs.org) and CIEDE2000 distances: in the colour-blind
  palette every pair of colours that must be told apart stays at least 10 apart under protanopia,
  deuteranopia and tritanopia, and text contrast is at least 4.5:1 in both palettes. axe-core runs on
  every screen in both palettes. Independently of colour, every state carries text or an icon.

## Data files

- `public/static/iau_moon_features.json` - 1,691 IAU features (maria, lacus, sinus, palus,
  montes, valles, rupes, stationes, and craters of 10 km or more; rimae and dorsa of 60 km or more).
  Fields: `[name, type, lat, lon, diameter_km]`, longitude converted from the gazetteer's 0..360 E
  to -180..180 E. Built by `scripts/build_iau_features.mjs` (no dependencies) from
  `MOON_nomenclature_center_pts.dbf` (USGS, https://planetarynames.wr.usgs.gov/GIS_Downloads).
- `public/data/v1/` - written by the Python engine (not by this app).

## Interaction modules (`src/modules/`)

Five small typed modules, reached through `globesApi` (after `await globesApi.ready`) and
`window.starsBesideYou`. None of them shows anything until it is given data: no markers, no
beam canvas, no outline and no video dialog exist in the page before the first call.
Types are exported from `src/api.ts`.

### Sunlight and time (`modules/sunlight.ts`, `scene/fullMoon.ts`)

A radio group in the header (`#sunlight`, native radios: Tab to reach it, arrow keys to change)
with three choices, a visible line that states the active one in words (`#sun-time`) and a polite
live region (`#sunlight-status`) that announces each change.

| Choice | Light | Header line |
|---|---|---|
| `full-moon` (default) | Physical, clock stopped at the Full Moon instant | `Full Moon light, 24 Nov 2026, 10:45 UTC` |
| `now` | Physical, real time, running | `Light now, <date time> UTC` |
| `even` | Day/night shading, night lights and dynamic atmosphere off on both globes | `Even light: day and night shading off (not physical)` |

The Full Moon instant is **computed at start-up, not typed in**: `computeFullMoonInstant()` scans
Cesium's own `Simon1994PlanetaryPositions` Sun and Moon positions hourly from
`FULL_MOON_SEARCH_FROM` (2026-11-14) for the first maximum of the Sun-Earth-Moon elongation
(opposition, refined by golden-section search), then moves to the nearest instant at which the
sub-solar point is on 15 deg E (central Europe and central Africa), rounded to the minute. Result
for this build: opposition (maximum elongation, 175.0 deg; the Moon is about 5 deg off the
ecliptic, so it is not 180) on 24 Nov 2026 at about 15:10 UTC; chosen instant
**2026-11-24T10:45:00Z**, elongation 174.4 deg (99.8 % of the near side lit), Sun overhead near
20.6 S, 15 E. Both values come from the same Cesium functions the app uses.
On load, and on every change, cameras still on their home view turn to face the sunlit hemisphere
(Earth: the sub-solar meridian, latitude pulled north; Moon: the sub-solar point).

```ts
globesApi.sunlight.mode();            // 'full-moon' | 'now' | 'even' | 'link' (opened with ?time=)
globesApi.sunlight.set('even');
globesApi.sunlight.fullMoonDate();    // Date (UTC)
globesApi.sunlight.describe();        // the header sentence
globesApi.sunlight.subsolar('moon');  // { lat, lon } where the Sun is overhead now
const off = globesApi.sunlight.onChange((mode) => {});
```

### Marker layers (`modules/markers.ts`)

One `PointPrimitiveCollection` per body (no entity per marker), rank numbers in a
`LabelCollection`. Encoding without colour alone: size (3 to 10 px) and brightness/opacity follow
the score on a single warm-white ramp (readable in greyscale and for every colour-vision type); the
`topLabels` best ranks carry their number with a dark halo; the selected marker gets a ring and its
label (`"<rank>  <label>"`). Markers on the far side are hidden, markers within ~12 deg of the limb
fade. Desktop: pointer cursor and a hover look (bigger, white outline, label) within 6 px. Touch and
pen: a tap picks the nearest marker within 22 px of its edge (a 44 px target). Drags do not pick.

```ts
type MarkerItem = { id: string | number; lat: number; lon: number; score: number; rank?: number; label?: string };
globesApi.markers.setMarkers('earth', items, { topLabels: 10 });   // replaces that body's markers
globesApi.markers.clearMarkers('moon');
globesApi.markers.setSelected('earth', id);    // or null
globesApi.markers.selected('earth');
globesApi.markers.setHighlighted('moon', id);  // hover look, e.g. while its list row has focus
const off = globesApi.markers.onPick((body, id, source) => {});   // source: 'mouse' | 'touch' | 'pen' | 'keyboard'
globesApi.markers.activate('moon', id);        // call on Enter in the results list: fires onPick ('keyboard')
globesApi.markers.setAutoSelect(false);        // default true: a pick also selects
globesApi.markers.screenState('earth', id);    // { x, y, visible, fade, size } in canvas CSS px
```

### Paired fly-to (`modules/focus.ts`)

```ts
const cell = { west: 12, south: 23, east: 13, north: 24 };            // passed by the caller, never assumed
await globesApi.focus.focusPair(
  { earth: { lat: 23.4, lon: 12.6, cell }, moon: { lat: -43.3, lon: -11.2, cell: moonCell } },
  { durationMs: 1000, fill: 0.4 },     // defaults; duration capped at 1400 ms
);                                     // resolves true when both cameras arrive (false if interrupted)
await globesApi.focus.exitFocus();     // both cameras back to the views they had, layout restored
globesApi.focus.isFocused();
globesApi.focus.lastFlight();          // { plannedMs, animationMs, wallMs, completed }
```

Both cameras move in one animation loop with one clock, look straight down, and stop at a height
at which the cell spans `fill` of the smaller canvas side (a 1-degree cell, about 111 km on Earth
and 30 km on the Moon, when no cell is given). Instant under reduced motion. A pointer down or
wheel on a globe stops a running flight. A thin light outline with a dark underlay is drawn for each
`cell`. While focused, `body.is-focused` gives room to `#detail-panel` (when it is not `hidden`):
a third column beside the globes on wide landscape screens (900 px and up), a bottom sheet
(`min(42dvh, 380px)`) on phones and portrait screens, with the globes shrunk above it so the two
points stay visible. `options.timeSource` (a function returning ms) drives the flight from another
clock, for frame-exact tests and recordings.

### Light beam (`modules/beams.ts`)

```ts
globesApi.beams.setBeams([
  { earth: { lat, lon }, moon: { lat, lon }, strength: 1 },      // the selected pair
  { earth: ..., moon: ..., strength: 0.25 },                     // optional faint companions
]);
globesApi.beams.clearBeams();
globesApi.beams.lastDrawn();   // ends as drawn, page px, kind 'point' | 'limb' | 'edge' | 'hidden'
```

A full-page `canvas.beam-overlay` (created on first use, `pointer-events: none`, `aria-hidden`,
z-index above the globes and below the panels). Additive light: five stacked strokes from a wide
faint halo to a narrow core (soft falloff across), a gradient along it that is brighter near both
ends, and a small radial glow on each surface point; no line caps or arrowheads. An end on the far
side stops at the body's limb and fades out; an end outside its globe's canvas stops at the canvas
edge and fades. Redrawn only when a camera moved (checked after each render), on resize, or when
the list changes; otherwise a slow +-5 % breath (7 s period), none under reduced motion.

### Mission video dialog (`modules/video.ts`)

```ts
await globesApi.video.openVideo({
  title: 'Rover mission',
  sources: [{ src: 'media/rover/rover.webm', type: 'video/webm' }, { src: 'media/rover/rover.mp4', type: 'video/mp4' }],
  poster: 'media/rover/rover-poster.jpg',
  tracks: [{ src: 'media/rover/rover.en.vtt', srclang: 'en', label: 'English', default: true },
           { src: 'media/rover/rover.es.vtt', srclang: 'es', label: 'Español' }],
  credit: 'Rover mission video: 3D simulation by the Stars Beside You team (not real footage)',
  note: '...',
});                                     // resolves when the dialog closes
globesApi.video.closeVideo();
globesApi.video.isOpen();
```

A modal `<dialog>` built on first call: native controls, captions on (the `default` track, else
the first), credit and note under the player, focus starts on the 44 px close button (an X with
the accessible name "Close video"), Tab is trapped, Escape, the X or a backdrop click closes, and
focus returns to the element that opened it. If no source can be loaded, the player is replaced by
an alert that names the file, says what happened and offers **Try again**.

### Tests

`npm run test:modules` (`tests/modules.mjs`, add `--no-build` to reuse `dist/`,
`--only=desktop,phone,reduced`) drives every module through `window.starsBesideYou` with synthetic
items made inside the test, at 1440x900 (mouse) and 375x812 (touch), plus a reduced-motion run,
fails on any console error or failed request, and saves screenshots to `$SHOTS_DIR`. The video
checks use `public/media/rover/` when present, else a clip in `$TEST_MEDIA_DIR` served as
`/test-media/clip.webm` and `/test-media/clip.en.vtt`.

## Product flow (`src/flow/`, `src/data/`)

Choose a mission -> pick a point -> compare the pair -> start the mission, with a step indicator
(`#steps`) that can go back or forward from every step.

- `src/data/store.ts` reads bundle v2 exactly as `docs/DATA_CONTRACT.md` (revision 4) describes:
  the first view at start, mission files, one detail tile per selected cell (all tiles only when a
  weight slider moves), place details and, only when the rule has twins, `twins.json`. Twins are
  decided from the bundle itself (`similarity.json` target kind and the manifest), so the shipped
  `zone_twin` bundle and a `repo_global_mean` bundle work without code changes.
- `src/data/recompute.ts`: suitability, similarity, final and rank from the exported utilities
  and z-scores (Python / numpy rounding reproduced).
- Every approved sentence (similarity meaning, rock note, missing-temperature mark and note, twin
  sharing, solar limitation) is read from `similarity.json` `texts`; no threshold or weight is typed
  in code. Mission short names and one-line descriptions are in `src/flow/copy.ts`.
- Videos: `scripts/mediaIndex.ts` writes `media-index.json` at build time from the folders present
  in `public/media/`; "Start mission" appears only for missions with files. Rebuild after a new
  video folder lands.

Tests: `npm run test:data` (store and recompute on every passing cell of both bundle variants, no
browser) and `npm run test:flow` (the whole flow in Chromium on both variants at 1440x900 and
375x812, forced failures, 768 and 3840 px layouts; screenshots in `$SHOTS_DIR`). The no-twin
variant is read from `$OTHER_BUNDLE` and served from a temporary copy.

## Deployment

The app is a static site on Vercel (project `stars-beside-you`, production URL
https://stars-beside-you.vercel.app). It is deployed prebuilt: Vercel runs no build; `vercel.json`
only sets caching headers (hashed `assets/` immutable for a year, `cesium/` a week, `data/` an hour,
`audio/`, `media/` and `static/` a day). Vercel serves the text files compressed (brotli).

From the repository root, with the token in the environment (never on the command line):

```sh
set -a; . /root/.config/stars/vercel.env; set +a
bash scripts/deploy_vercel.sh            # production; add --preview for a preview deployment
```

The script builds `app/` key-free (`VITE_USE_ION=0`, empty `VITE_CESIUM_ION_TOKEN`, so
`.env.local` is never used), refuses to deploy if the build holds the local ion token, the Vercel
token or any JWT-shaped string that CesiumJS does not ship itself (CesiumJS's own public default
token in `Ion.js` is the one `eyJ` string expected in `dist/`), checks Vercel's CLI limits (100 MB
per file on Hobby, 15,000 files), deploys `dist/` and prints the URL. The build is about 82 MB in
about 440 files; the largest files are the four videos (about 11 MB each). Preview deployments are
behind Vercel Authentication; production is public.



