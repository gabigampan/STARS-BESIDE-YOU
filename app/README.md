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
- Keyboard: `R` or `Home` resets both views; double click resets one globe. Every control is at
  least 44 px and shows a focus ring.

## Data files

- `public/static/iau_moon_features.json` - 1,691 IAU features (maria, lacus, sinus, palus,
  montes, valles, rupes, stationes, and craters of 10 km or more; rimae and dorsa of 60 km or more).
  Fields: `[name, type, lat, lon, diameter_km]`, longitude converted from the gazetteer's 0..360 E
  to -180..180 E. Built by `scripts/build_iau_features.mjs` (no dependencies) from
  `MOON_nomenclature_center_pts.dbf` (USGS, https://planetarynames.wr.usgs.gov/GIS_Downloads).
- `public/data/v1/` - written by the Python engine (not by this app).
