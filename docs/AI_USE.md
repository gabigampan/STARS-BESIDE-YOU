# Use of AI tools (draft)

> **Draft for the team.** Adapt it to the disclosure form of the NASA Space Apps Challenge before submitting.
> It describes the branch `final-integration` of the repository as of 15 November 2026.

## What AI wrote

An AI coding assistant (Claude Code) wrote, under the team's direction:

- the integration engine `tierra luna/engine/` (`python -m engine`) and its tests in `tierra luna/tests/`;
- the real-data builders and their verification scripts in `tierra luna/real_data/`, and the research,
  validation and audit scripts in `tierra luna/research/`, `tierra luna/validation/` and `tierra luna/audit/`;
- the web app `app/` (Vite, TypeScript, CesiumJS) and its tests in `app/tests/`;
- the renderer `app/video-sim/` that produced the Solar panels and Lunar base videos from the project's data;
- the documents in `docs/`, `ASSUMPTIONS.md` and the root `README.md`;
- the texts of the audio guide (`app/public/audio/transcripts.json`), drafted from the bundle's figures.

It also edited three of the team's original files (`tierra luna/analog_finder.py`, `tierra luna/rover_preset.py`,
`tierra luna/data/presets/presets.json`); the first two carry `[AI-assisted]` comments.
The team's scoring file `tierra luna/mission_scoring.json` was read and quoted, never edited.

Independent AI reviewers (separate sessions of the assistant) re-computed the figures and checked the texts: the statistical audit and the re-audits
of the three missions (Rover, Solar panels and Lunar base) in `docs/stats_audit/`, the independent re-read of every
published text (`11_textos_finales.md`), the check of the 19 audio texts (`10_textos_audio.md`), the external
contrast of the fifteen published sites (`12_contraste_realidad_nuevos.md`), the checks of the validation
(`13_comprobacion_validacion.md`) and of the videos (`14_comprobacion_videos.md`, provisional), the validation in `docs/VALIDATION.md`, and the independent
re-computation of the real tables from raw files (`docs/REAL_DATA.md` section 6,
`tierra luna/real_data/verification/`).

## What the team did

- **Design decisions.** The missions, the lunar zones, the filters, criteria and weights
  (`tierra luna/mission_scoring.json`) and every later choice between options were taken by the team: by the team
  lead or, where an entry says so, by a delegate on the team lead's behalf. Each decision is dated in
  `docs/DECISIONS.md` (options, figures before and after) and its effect is recorded in `ASSUMPTIONS.md`.
- **Original pipeline.** The team's Earth-Moon extraction, harmonisation and cleaning pipeline and its
  documentation (`tierra luna/README.md`, `main.py`, `analog_finder.py`, `web/index.html`) predate this branch.
- **Audio guide.** The 19 tracks were recorded by the team with a text-to-speech service. No audio was
  generated or edited by the AI assistant.
- **Rover video.** The team's own 3D simulation (`app/public/media/rover/README.md`), only re-encoded, with
  nothing changed in picture or timing. None of the three videos is real footage.

## What was checked against official sources, and where

- **Data products, versions and licences:** each column's product, version, provider, URL and licence, with the
  date the provider page was read, in `tierra luna/real_data/provenance_earth.csv`, `provenance_moon.csv` and
  `tierra luna/real_data/supplement/*provenance*.csv`; summary in `docs/REAL_DATA.md` section 3. The WorldClim
  licence was corrected after this check (an earlier build had called it CC BY 4.0).
- **Measurement uncertainty of the elevation models** (ETOPO 2022 RMSE 7.17 m; LOLA about 10 m radial), read on
  the publications' pages: `docs/stats_audit/9_reauditoria_rover.md`.
- **Lunar zones and NASA's nine candidate regions:** `docs/MISSION_ZONES.md` (every page opened on 2026-11-15).
- **Thresholds against official sources:** `docs/sources/R3_threshold_sources.md`; rover and lunar references in
  `docs/sources/R1_viper_rover_spec_sources.md` and `R2_lunar_reference_sources.md`. Criteria with no official
  source are listed in `docs/KNOWN_LIMITATIONS.md` section 5.
- **Known analog and reference sites** used as external checks: `docs/VALIDATION.md` section 3 and
  `docs/stats_audit/research_4_validacion_externa.md`.

AI output was not taken on trust: figures quoted in the app and in the documents come from the shipped data
bundle or from the audit files named next to them. What the results cannot claim is in
[KNOWN_LIMITATIONS.md](KNOWN_LIMITATIONS.md).
