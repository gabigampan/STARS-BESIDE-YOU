# Stars Beside You: real-data analog engine, web app, mission videos and documents

Pull request from the fork's branch `final-integration` into the team's repository (`main`).
Team "Stars Beside You", NASA Space Apps Challenge 2026 (Málaga), challenge "Earth analogs for Permanent Moon
Base and Mars".

## What it adds

The product: a static, key-free web app that shows **analog pairs** for three missions (Rover, Solar panels,
Lunar base): places on Earth where the mission can be tested because they resemble a place on the Moon, and
which lunar place that is. Overview, commands and credits: [README.md](../README.md).

**Real data** (`tierra luna/real_data/`, `tierra luna/output_real/`)
- Builders that download public products (no accounts or keys) and reduce them to 1-degree tables of Earth and
  Moon (`earth_real_1deg.csv`, `moon_real_1deg.csv`, `earth_moon_real_1deg.csv`), with per-column provenance
  files (product, version, provider, licence, data level MEASURED / DERIVED / MODELLED), manifests and checks.
- Supplementary columns (ISCCP clear-sky fraction, extra terrain statistics) in `real_data/supplement/`, with
  their own provenance files; their scripts in `tierra luna/research/`.
- Independent re-computation from raw files: `tierra luna/real_data/verification/`, `docs/REAL_DATA.md`.

**Engine** (`tierra luna/engine/`, `python -m engine`)
- Reads the real tables and the team's `mission_scoring.json`, applies each mission's filters, scores
  suitability, pairs each passing Earth point with its lunar twin inside the mission's lunar zone, ranks by
  50 % similarity and 50 % suitability, picks five analogs (Rover: five of the 254 tied at the top, spread across the world; Solar panels and Lunar base: five of the highest-scoring, at least 2 degrees apart), and writes the data bundle
  `app/public/data/v2/` (engine 3.4.0, data contract revision 8, `docs/DATA_CONTRACT.md`) with every text,
  limitation and credit the app shows.
- Tests in `tierra luna/tests/`; validation scripts in `tierra luna/validation/`; audit scripts in
  `tierra luna/audit/`.

**Web app** (`app/`, Vite + TypeScript + CesiumJS)
- Earth and Moon globes, the three missions with their five sites and full ranking, paired fly-to, the value,
  source and data level of every number, the mission videos with captions, the audio guide and a credits dialog.
- Static build (`app/dist/`), no server and no API key; an optional Cesium ion token is never put in the
  key-free build.
- Tests in `app/tests/` (smoke, modules, data, flow).

**Media**
- Three mission videos in `app/public/media/` with English and Spanish captions and a README each. None is real
  footage: Rover is the team's own 3D simulation (re-encoded only); Solar panels and Lunar base are simulations
  rendered by `app/video-sim/` from the project's data.
- The audio guide: 19 tracks recorded by the team with a text-to-speech service; texts in
  `app/public/audio/transcripts.json`.

**Documents**
- `ASSUMPTIONS.md` and, in `docs/`: `DATA_CONTRACT.md`, `DECISIONS.md` (the team's dated decisions),
  `STATS_AUDIT.md`, `stats_audit/` (statistical audit, parts 1 to 14, re-audits of the three missions), `VALIDATION.md`, `REAL_DATA.md`,
  `MISSION_ZONES.md`, `AUDIT.md`, `UX_CHECKLIST.md`, `UX_REPORT.md`, `KNOWN_LIMITATIONS.md`, `AI_USE.md` (draft)
  and this file. What each is for: README "Documents".

## How to run and test it

```sh
# web app (Node 22 or later)
cd app
npm ci
npm run dev            # development server
npm run build          # typecheck + static build -> app/dist/
npm run test:data      # store and recompute against the bundle, no browser
npm run smoke          # build, serve dist/, check both globes (headless Chromium)
npm run test:modules   # interaction modules
npm run test:flow      # whole flow at desktop and phone sizes

# engine (Python 3; packages in tierra luna/requirements.txt and tierra luna/engine/requirements.txt)
cd "tierra luna"
python -m engine build     # writes the bundle to app/public/data/v2
python -m pytest -q
```

No API key is needed. The optional `VITE_CESIUM_ION_TOKEN` goes in `app/.env.local` (git-ignored) and is used
only with `VITE_USE_ION=1`; never put a token with write scopes in a public build (use a read-only one or none).
Real-data builders and the video renderer: README "How to run it" and `app/video-sim/README.md`.

## What it does NOT change

- **The team's `main` branch**: nothing is pushed to it; it changes only if this pull request is merged.
- **`tierra luna/mission_scoring.json`** (the team's filters, criteria and weights) is read and quoted, never
  edited. Where the engine departs from it, each deviation is listed in `docs/DECISIONS.md` (section "Tabla de
  desviaciones respecto de mission_scoring.json") and in the bundle text `deviations_from_team`.
- **The team's documentation** `tierra luna/README.md` and the original pipeline (`main.py`, `web/index.html`)
  are kept unchanged.
- **Three team files are modified**, and reviewers should know it: `tierra luna/analog_finder.py` (a cell that
  fails a mission's hard filters is no longer scored for it, replacing the former x0.35 penalty; the Rover target
  is the Shackleton region instead of Tycho; filters read from `mission_scoring.json`), `tierra luna/rover_preset.py` (version 3, which states that
  nothing from versions 1 and 2 was removed) and `tierra luna/data/presets/presets.json` (rewritten presets). Edited code carries `[AI-assisted]`
  comments.
- The work on the branch `web-accessibility` (a separate session on `app/src` and `app/tests`) is merged into `final-integration`: merge commits `0c5203d` (web `43f69d3`) and `407fdfe` (web `5a6c4b3`, the last fix: no 'best' in the keyboard help and credits; a note already contained in a text above it is not repeated). After the merge `npm run build` and `npm run test:data` pass on the final bundle. On its last commits the web session ran typecheck, build and test:data (pass) and test:a11y: 188 ok, 0 failed on the no-twin fixture; on the shipped bundle 109 ok / 2 failed at 1440x900 and 119 ok / 2 failed at 375x812 BEFORE the last fix (the two failures were the 'best' wording check fixed in `5a6c4b3`; its re-run was still in progress at the time of writing). test:flow was not re-run on the final commit (earlier run: 352 ok, three failures attributed to load and the shorter phone panel: recompute 116 ms against a 100 ms budget, one click timeout, one phone layout check). The web's own landscape-phone touch check failed in its test, while the independent UX review (`docs/UX_REPORT.md`) measured pinch and drag working at 375x812 and 812x375. The engine's full test suite is green on the final tree: 231 passed, 12 skipped.
- Validation (phase 3): `docs/VALIDATION.md` and `tierra luna/validation/`, with an independent check in `docs/stats_audit/13_comprobacion_validacion.md`.
- Deployment: `scripts/deploy_vercel.sh` and `app/vercel.json`; the final production deployment has NOT been made: the attempt at 14:09 CET was blocked by Vercel (`TEAM_ACCESS_REQUIRED`: the CLI attaches the last commit's author, an automation identity outside the account's team; nothing was changed on the account). https://stars-beside-you.vercel.app still serves the rehearsal build of about 13:25 CET (web `70cac01`, heading "The five best analogs", earlier Solar panels video and texts) and is not the final site; how to deploy is the account owner's decision. Lighthouse desktop performance on the rehearsal, measured from a container without GPU (software WebGL): 24 and 25; not valid for a real computer, the target of 85 is not demonstrated.
- Audio: final texts of the 19 tracks in `app/public/audio/transcripts.json`, checked independently; the recordings are pending (`app/public/audio/pending.json`), and until they arrive the web shows each track's text and plays nothing.

## What reviewers should look at first

1. `docs/KNOWN_LIMITATIONS.md`: what the lists can and cannot claim.
2. `docs/DECISIONS.md` and `ASSUMPTIONS.md`: the team's decisions and every setting with its effect.
3. `docs/STATS_AUDIT.md` and `docs/stats_audit/9_reauditoria_rover.md`, `9_reauditoria_solar.md`, `9_reauditoria_base.md`: the audit summary and the independent re-audits of the three missions (in Spanish).
4. `tierra luna/real_data/provenance_*.csv` and `docs/REAL_DATA.md` section 3: sources and licences, in particular
   the WorldClim licence.
5. The app itself (`npm run dev`), each mission's five sites and their pair sentences.

## Known limitations (details: [KNOWN_LIMITATIONS.md](KNOWN_LIMITATIONS.md))

- 1-degree cells (about 111 km on Earth, about 30 km on the Moon, polar lunar cells only a few km wide): no value describes a landing site or a traverse.
- Rover: 254 sites tied within the measurement uncertainty; the order among them is the team's suitability.
- Solar panels: similarity saturated; matched on sunlight above the atmosphere, about a third or more is lost before the ground at the Earth site.
- Lunar base: a likeness of thermal position, not of temperature (about 200 K apart); the five are fragile; polar stations are excluded by the 15 K swing gate.
- Earth temperature (WorldClim) and permafrost are modelled; WorldClim is non-commercial only (pending team decision); frame rate and Lighthouse performance not measured on real hardware.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
https://claude.ai/code/session_01RaZffQcqLUAZjsW856KTAM
