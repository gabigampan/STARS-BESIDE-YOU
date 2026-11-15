# Path map for the final reorganisation (read-only analysis)

Repository: `/home/user/stars-beside-you`, branch `final-integration`, working tree as found on 2026-11-15. Nothing was moved or edited.
The machine-readable version is `path_map.json` in this folder. It has every row, every edit with its exact old and new text, and the command groups.
The counting scripts are in the same folder: `count_refs.py`, `md_refs.py`, `edits.py` and `make_map.py`. Re-run them just before executing. Other agents were editing files while this map was made (`app/src/a11y/audio.ts`, `app/tests/a11y.mjs`, `tierra luna/engine/engine_config.json` and the bundle), so line numbers can drift. Match every edit by its `old` text.

## 1. Recommendation

**Move `tierra luna/` as a whole to `engine/`** with one `git mv`. Do not split it between engine/ and data/.

Why:
- **The engine needs no edits.** Every engine path is resolved against the package's parent folder (`engine/config.py:24-25`, `resolve_path` at 194-196). Every test computes `ROOT = dirname(dirname(__file__))` and `REPO = dirname(ROOT)`, for example `tests/test_texts_1210.py:14-15`. `datasets.json` writes to `../app/public/data/v2`. All of these keep working when the folder is renamed at the same depth. Not one test contains the string "tierra luna".
- **Splitting `output_real/` and `real_data/` into data/ costs far more than a handful of edits:**
  - 73 Python code references: 42 to output_real and 31 to real_data, across 64 files.
  - 8 configuration values in `datasets.json`.
  - 7 test lines.
  - the build scripts' `HERE.parent` output paths.
  - a bundle rebuild, because `lunar_named_sites.json` `source` = `real_data/lunar_named_sites.csv` and the manifest hashes `datasets.json`.
- **`tierra luna/data/` cannot move at all without editing team modules.** These lines hard-code `dirname(__file__)/data/...`:
  - `pds_reader.py:11` (the PDS cache)
  - `config.py:6` (`ldem_4.img`)
  - `analog_finder.py:24` (`presets.json`)
  - `rover_integration.py:50` (`analog_benchmark.csv`)
  - `tests/conftest.py:13`
- **Team modules: 0 lines change.** This covers `mission_scoring.json`, `mission_scoring.py`, `analog_finder.py`, `mission_filters.*`, `rover_preset.py`, `rover_integration.py`, `config.py`, `pds_reader.py`, the extractors, `harmonizer_cleaner.py` and `main.py`. `mission_scoring.json` keeps its sha256, so the manifest `config_sha256` does not change.

## 2. Target structure

```
.gitignore                 (line 11: tierra luna/ -> engine/)
README.md                  (English, for the judge; another agent writes it)
                           (no LICENSE/NOTICE exists today; add one only if the team picks a licence)
app/                       web, unchanged in place: public/data/v2, public/audio (MP3), public/media (videos) stay
engine/                    = former "tierra luna/" (same depth)
  engine/                  the Python package (python -m engine build, run from engine/)
  tests/  validation/  research/  audit/
  data/{benchmark,cache,presets}   (must stay next to the team modules)
  output_real/  output_py/  real_data/
  mission_scoring.json mission_scoring.py analog_finder.py mission_filters.{py,json}
  rover_preset.py rover_integration.py config.py pds_reader.py lunar_extractor.py
  earth_extractor.py harmonizer_cleaner.py main.py gee_earth_grid_export.js
  requirements.txt README.md
data/README.md             index only: where each table is (engine/output_real, engine/real_data,
                           engine/data/*, app/public/data/v2), sizes, sha256, rebuild commands
docs/                      unchanged names, + ASSUMPTIONS.md, - AUDIO_TOP5.json, - AUDIO_RERECORD.md
audio/README.md  audio/AUDIO_TOP5.json  audio/AUDIO_RERECORD.md  audio/tools/make_audio_top5.py
video/README.md  video/video-sim/          (renderer; the MP4/WebM stay in app/public/media)
economics/README.md        placeholder: the repository holds no economics material today (do not invent it)
archive/README.md  archive/STARS-BESIDE-YOU-main (2).zip  archive/team_notes/Instruciones filtros solar y temp
archive/old_web/
scripts/deploy_vercel.sh   unchanged (it uses REPO_ROOT/app, scripts/deploy_vercel.sh:26; no tierra luna reference)
```

Nothing in app/ depends on where `app/video-sim` is:
- `app/tsconfig.json:20` includes only `src`, `vite.config.ts` and `scripts/mediaIndex.ts`.
- Nothing imports video-sim.
- The only mentions are text in `app/public/media/*/README.md`, which are copied to dist.

The renderer, however, depends on app/. `prepare.py:54` and `solar_pair.py:20,245` use `HERE/../public`, and the scenarios' `output_dir` is `../../public/media/...` (resolved at `render.js:21`).

## 3. Inventory (one row per top-level item and per item directly under "tierra luna/")

| Path | Size | What it is | Who reads it (evidence) | Destination |
|---|---|---|---|---|
| .gitignore | 4K | ignore rules | git; `.gitignore:11` names `tierra luna/output_real/earth_moon_real_1deg.csv` | kept, line 11 edited |
| ASSUMPTIONS.md | 116K | assumptions doc | `tests/test_verification_fixes.py:145`, `tests/test_texts_reaudit.py:249` | docs/ASSUMPTIONS.md |
| Instruciones filtros solar y temp | 4K | team note (Spanish) on designing mission_scoring (commit bfa0995) | nothing; cited by docs/FILTERS.md | archive/team_notes/ |
| README.md | 24K | main README | people | kept (links at :130 and :163 change) |
| STARS-BESIDE-YOU-main (2).zip | 14M | zip of the team's original main (d4a11e4). 46 of 50 files identical to today's tree; differs in analog_finder.py, presets.json, mission_scoring.json, rover_preset.py. No token patterns inside | nothing (docs only) | archive/ (name kept) |
| app/ | 421M on disk | web | `scripts/deploy_vercel.sh:26-37` | app/ |
| app/video-sim/ | 30M on disk, 15 tracked | video renderer | nothing in app/ (`app/tsconfig.json:20`) | video/video-sim/ |
| docs/ | 2.0M | docs and dated records | engine tests (e.g. `tests/test_mission_zone_texts.py:15`) | docs/ |
| docs/AUDIO_TOP5.json | 200K | pair list and audio texts | `app/tests/a11y.mjs:50`; `tests/test_audit_corrections_1.py:121,299,331` | audio/ |
| docs/AUDIO_RERECORD.md | 32K | recording list, generated | `tools/make_audio_top5.py:78,1317` writes it | audio/ |
| scripts/ | 12K | deploy_vercel.sh | `scripts/deploy_vercel.sh:26` | scripts/ |
| tierra luna/ | 100M on disk | pipeline + engine | see below | engine/ |
| tierra luna/.pytest_cache | 52K | cache (ignored) | pytest | moves along |
| tierra luna/README.md | 8K | team pipeline README | people | engine/README.md |
| tierra luna/\_\_pycache\_\_ | 432K | 8 tracked .pyc (+1 in tests/) | regenerated; `.gitignore:1` | `git rm -r --cached` |
| analog_finder.py | 32K | team module | `engine/repo_similarity.py:49`; `tests/test_pipeline.py:15` | engine/ |
| audit/ | 9.2M | audit scripts + out/ | nothing at build or test; `audit/p1_common.py:18` TL=HERE/.. | engine/audit/ |
| config.py | 4K | team grid config | `tests/test_pipeline.py:10` | engine/ |
| data/ | 13M | benchmark, cache, presets | `pds_reader.py:11`, `config.py:6`, `analog_finder.py:24`, `rover_integration.py:50`, `engine_config.json` external_validation.benchmark_csv | engine/data/ |
| earth_extractor.py | 12K | team pipeline | `tests/test_pipeline.py:12` | engine/ |
| engine/ | 3.1M | the engine package | `engine/config.py:24-31` | engine/engine/ |
| gee_earth_grid_export.js | 4K | team GEE script | no code; documented at `tierra luna/README.md:8` | engine/ (part of the team pipeline) |
| harmonizer_cleaner.py | 12K | team pipeline | `tests/test_pipeline.py:13` | engine/ |
| lunar_extractor.py | 12K | team pipeline | `tests/test_pipeline.py:11` | engine/ |
| main.py | 8K | team pipeline entry; writes output_py/ and web/ | no importer; `main.py:207` | engine/ |
| mission_filters.json/.py | 8K/16K | older team filters | `analog_finder.py:10,21`; `tests/test_pipeline.py:268` | engine/ |
| mission_scoring.json | 12K | **team scoring file** | `engine/config.py:192-203` (mission_config); `tests/test_decisions_1123.py:120,130` | engine/, 0 bytes changed |
| mission_scoring.py | 16K | team loader | `engine/config.py:33`, `gates.py:24`, `pipeline.py:19`, `suitability.py:26`, `export.py:21` | engine/, 0 lines |
| output_py/ | 18M | 2-degree pipeline outputs | `datasets.json` legacy_2deg input; `tests/test_engine.py:35`; `tests/test_missions_similarity.py:95` | engine/output_py/ |
| output_real/ | 41M | real 1-degree tables | `datasets.json` real_1deg.inputs; `tests/test_mission_zone_texts.py:16`; `app/video-sim/tools/prepare.py:25` | engine/output_real/ |
| pds_reader.py | 8K | team PDS reader | `tests/test_pipeline.py:14` | engine/ |
| real_data/ | 8.1M | table builders, provenance, aliases, supplements | `datasets.json` provenance/column_aliases/lunar_named_sites/supplements | engine/real_data/ |
| requirements.txt | 4K | team requirements | pip | engine/ |
| research/ | 3.6M | r1-r5 scripts and outputs | nothing at build or test; `research/r4_rank_sites.py:28` | engine/research/ |
| rover_integration.py | 12K | team rover hook | `tests/test_rover_integration.py:16` | engine/ |
| rover_preset.py | 48K | team rover preset | `analog_finder.py:11`; `engine/limits.py:107` (names_module) | engine/ |
| tests/ | 1.7M | engine suite | pytest | engine/tests/ |
| tools/make_audio_top5.py | - | audio text generator | `tests/test_audit_corrections_1.py:297` (skipped) | audio/tools/ (depth 2 kept) |
| validation/ | 604K | validation m1-m9 | nothing at build or test; `validation/common.py:20-22` | engine/validation/ |
| web/ | 2.6M | team's first static web | nothing serves it; `main.py:207` writes into it (tests use tmp_path, `tests/test_pipeline.py:170`) | archive/old_web/ |

Unused by build and tests:
- `web/`, the zip, the note, the `.pyc` files.
- `gee_earth_grid_export.js` and `main.py` (kept because they are documented parts of the team pipeline).
- Inside output_py/, the files other than `earth_moon_harmonized_clean.csv`. Kept as one folder.

## 4. Every reference that must change

Totals by kind:

| Kind | Required | Optional |
|---|---|---|
| Python | 44 lines | 19 labels, comments and messages |
| JSON configuration | 3 (`output_dir` in 3 video scenarios) | 27 engine prose strings (G8) + 2 (`lunar-base.json:29`, `tracks.json:3`) |
| JavaScript/TypeScript | 1 (`app/tests/a11y.mjs:50`) | 3 (`fixtures.mjs:5`, `a11y.mjs:79`, `audio.ts:172`) |
| .gitignore | 1 | |
| Markdown links | 2 | |
| Shell / package.json / vercel.json | 0 | |
| Bundle | 0 | 24 strings if G8 runs |
| **Total** | **51** | |

Every one of these lines is listed with its exact `old` and `new` text in `path_map.json` → `edits`.

**Python, required (44):**
- **G1, 33 lines, "tierra luna" → "engine":**
  - `audit/a2_audio_integration_check.py:16,84`
  - `audit/p1_grid.py:37,38`
  - `audit/p2_common.py:16`
  - `audit/p4_common.py:20,21`
  - `audit/p4_docs_coherence.py:26`
  - `audit/p5_inventory.py:80-82`
  - `audit/p6_common.py:18`
  - `audit/t_audio_texts.py:155,159,166,343`
  - `audit/v_check_validation.py:4,52,53`
  - `real_data/verification/sanity.py:6`, `vearth.py:8,9`, `vmoon.py:8`, `vmoon_iso.py:4`, `vmoon_temp.py:4` (absolute `/home/user/stars-beside-you/tierra luna`)
  - `tools/make_audio_top5.py:79-83,303`
  - `app/video-sim/tools/prepare.py:25`, `solar_pair.py:21`
- **G2, 3 lines:** `prepare.py:54`, `solar_pair.py:20,245`. HERE/.. becomes video/, so these change to `HERE, "..", "..", "app", "public", ...`.
- **G3, 6 lines:**
  - `make_audio_top5.py:76,78` (outputs move to audio/)
  - `tests/test_audit_corrections_1.py:121,299,331` (`REPO/audio/AUDIO_TOP5.json`)
  - `tests/test_audit_corrections_1.py:297` (`REPO/audio/tools/make_audio_top5.py`)
- **G4, 2 lines:** `tests/test_verification_fixes.py:145`, `tests/test_texts_reaudit.py:249` (`REPO/docs/ASSUMPTIONS.md`).

**Keep unchanged:**
- `validation/m5_reproduction.py:29`: `git show 618bc45:tierra luna/...` names a path inside an old commit.
- `research/r3_base_lunar.py:15,23`: reads a snapshot of an older commit.
- The 944 occurrences in `*/out/*` (25 files): recorded outputs of past runs.

Further Python mentions, not functional:
- 83 "tierra luna" in comments and docstrings.
- 20 audit-script references to docs/AUDIO_TOP5.json (`audit/p1_names.py` 7, `p1_grid`, `p1_regions`, `p2_top5`, `p3_common`, `p4_docs_coherence`, `p5_shown_numbers`, `p6_*`, `w0_reproduce`, `w_common`). Optional: update them only if those audits must stay re-runnable.

**JSON configuration read by the engine** (prose only, no path value):
- `engine_config.json`: 18 strings (12 `tolerance_set_by`, 5 `external_validation...source`, 1 `limit_texts.deviations_from_team.source`).
- `datasets.json`: 3 (`_note`, `output_dir.why`, `supplements.why`).
- `mission_zone_texts.json`: 6 (`figures[].how_computed`).
- Every path *value* in these files is relative to the project folder, so none has to change.

**Bundle strings** produced by those sources:
- `similarity.json` 12: 6 `tolerance_set_by` from engine_config `real_value_similarity` / `criteria_sets.engine_patch`, plus 6 `texts.*.source` from `external_validation` / `limit_texts`. Written by `engine/export_v2.py`.
- `missions.json` 6: `tolerance_set_by`.
- `mission_zones.json` 6: `how_computed`, copied verbatim from `mission_zone_texts.json`.
- The web shows `tolerance_set_by` only up to the first colon (`app/src/flow/copy.ts:90`), so the old path is not on screen.
- The manifest stores input names as basenames only, so moving files changes nothing in it.
- **Default: leave these strings.** If G8 runs, rebuild the bundle and prove that:
  - every .bin is byte-identical;
  - the JSON differs only in those 24 strings plus the manifest's `config_sha256` and `files[].sha256` entries.

**Markdown (textual rule; living documents only).**
- 51 Markdown files mention moved paths: 376 "tierra luna", 22 app/video-sim, 32 AUDIO_TOP5.json, 16 make_audio_top5, 3 AUDIO_RERECORD.md, 51 ASSUMPTIONS.md.
- Living documents: 23 files, with 199 "tierra luna" and 19 app/video-sim. Per document:

| Document | "tierra luna" | app/video-sim |
|---|---|---|
| README.md | 25 | 7 |
| docs/STATS_AUDIT.md | 42 | |
| ASSUMPTIONS.md | 26 | |
| docs/REAL_DATA.md | 18 | |
| docs/PR_DESCRIPTION.md | 18 | 2 |
| docs/AI_USE.md | 15 | 1 |
| docs/VALIDATION.md | 11 | |
| docs/MISSION_ZONES.md | 10 | |
| docs/ANALOG_PRINCIPLE.md | 8 | |
| docs/DATA_CONTRACT.md | 7 | |
| docs/FILTERS.md | 4 | |
| docs/KNOWN_LIMITATIONS.md | 3 | 1 |
| docs/DATA_DICTIONARY.md | 3 | |
| docs/LUNAR_BASE_PROPOSAL.md | 2 | |
| docs/SIMILARITY_PROPOSAL.md | 2 | |
| app/public/media/lunar-base/README.md | 2 | 3 |
| app/public/media/solar/README.md | 1 | 4 |
| app/public/media/rover/README.md | 1 | |
| docs/AUDIO_RERECORD.md | 1 | |
| app/video-sim/README.md | | 1 |

  docs/UX_REPORT.md, app/README.md and docs/ZONE_CONTRAST.md mention only AUDIO_TOP5.json or ASSUMPTIONS.md. Full counts are in the JSON.
- **Left as dated records:** docs/stats_audit/\*\*, docs/audit_evidence/\*\*, docs/sources/\*\*, docs/AUDIT.md, docs/LOCAL_ZIP_COMPARISON.md and docs/DECISIONS.md. Together they hold 177 occurrences. DECISIONS.md is read verbatim by tests (`tests/test_real_data.py:478`) and quotes the lead.
- **Ordered literal replacements:**
  1. `tierra luna/tools/make_audio_top5.py` → `audio/tools/make_audio_top5.py`
  2. `tierra luna/web` → `archive/old_web`
  3. `docs/AUDIO_TOP5.json` → `audio/AUDIO_TOP5.json`
  4. `docs/AUDIO_RERECORD.md` → `audio/AUDIO_RERECORD.md`
  5. `app/video-sim` → `video/video-sim`
  6. `cd "tierra luna"` → `cd engine`
  7. `"tierra luna"` → `engine/`
  8. `tierra luna/` → `engine/`
  9. Review any remaining hits by hand.
- Skip `<sha>:tierra luna`.
- Leave bare `ASSUMPTIONS.md` and bare `engine/x.py` mentions as they are. Add one README sentence: paths written as `engine/...` in the documents are relative to the engine/ folder, and the package is engine/engine/.
- No test asserts a doc string that contains any of these patterns. Checked: approved_texts, the mission_zone_texts quotes and the doc assertions in the tests.
- **Relative links:** only two change, `README.md:130` (video-sim README) and `README.md:163` (ASSUMPTIONS.md). No link is broken today.

## 5. Risks, in order, and the test that proves each move safe

1. **Bundle drift.** Editing any config the engine reads changes `config_sha256` and fails `test_published_v2_matches_a_fresh_build`. Proof: after G1, build to /tmp and sha256-compare all 42 files.
2. **Team modules are tied to `dirname(__file__)/data` and to their sibling JSON files.** Proof: the full engine suite, mainly `test_pipeline`, `test_engine` and `test_rover_integration`.
3. **engine/engine nesting.** `python -m engine` works only from engine/. From the repository root, `engine` resolves as a namespace package. Proof: the suite and the build run from engine/; README says `cd engine`.
4. **Video renderer depth.** There are 6 path values, and the untracked node_modules/ and build/ move with the folder. Proof:
   - `prepare.py <scenario> --checks-only` for both scenarios;
   - `solar_pair.py` reproduces `solar.json` (`git diff --exit-code`);
   - `npm run build`.
5. **Readers of the audio list.** `a11y.mjs:50` and `test_audit_corrections_1.py:121,331` are not skipped. Proof:
   - `pytest tests/test_audit_corrections_1.py`;
   - `npm run -s test:a11y` (needs Playwright);
   - the generator's output before and after is identical except for `generated_by`.

Also:
- (6) Concurrent edits: start only from a clean `git status`.
- (7) A blind sed breaks the history paths.
- (8) The `.gitignore:11` edit must land in the same group as the rename, or a later `git add -A` commits the 41 MB combined table.
- (9) Machine paths `/home/user/...` remain in 6 scripts plus `tests/test_real_data.py:37` (it skips when the file is absent).

Secrets check:
- Tracked files: no token patterns found.
- The zip: none found.
- `app/.env.local` is untracked and ignored.

## 6. Execution order (each group is testable on its own)

`PY=/tmp/claude-0/-home-user-NASA/7228bb30-9725-52d9-8d71-762c955fd0bd/scratchpad/stars/venv/bin/python`, `BGM=/tmp/claude-0/-home-user-NASA/7228bb30-9725-52d9-8d71-762c955fd0bd/scratchpad/stars/bundle_global_mean`.

- **G0 Preflight.**
  - `git status --short` must be empty.
  - `sha256sum app/public/data/v2/* > /tmp/order_bundle_before.sha`
  - Optional baseline: `cd "tierra luna" && $PY tools/make_audio_top5.py --no-app-files --out /tmp/order_top5_before.json`
- **G1 Rename.**
  - `git mv "tierra luna" engine`
  - `git rm -r --cached -q engine/__pycache__ engine/tests/__pycache__`
  - `find engine -name __pycache__ -prune -exec rm -rf {} +`
  - Apply the G1 edits.
  - Test:
    - `cd engine && STARS_GLOBAL_MEAN_BUNDLE=$BGM $PY -m pytest -q` (231/12)
    - `$PY -m engine build --out /tmp/order_v2`, then sha256-compare with `app/public/data/v2`
- **G2 Video.**
  - `mkdir -p video && git mv app/video-sim video/video-sim`
  - Apply the G2 edits.
  - Test:
    - `prepare.py --checks-only` for both scenarios
    - `solar_pair.py`, then `git diff --exit-code`
    - `cd app && npm run build`
- **G3 Audio.**
  - `mkdir -p audio/tools`
  - `git mv docs/AUDIO_TOP5.json docs/AUDIO_RERECORD.md audio/`
  - `git mv engine/tools/make_audio_top5.py audio/tools/`
  - Remove the empty `engine/tools`.
  - Apply the G3 edits.
  - Test:
    - `pytest tests/test_audit_corrections_1.py`
    - the generator diff against the baseline
    - `npm run -s test:a11y`
- **G4 ASSUMPTIONS.**
  - `git mv ASSUMPTIONS.md docs/`
  - Apply the 2 test edits and the README link.
  - Test: `pytest tests/test_verification_fixes.py tests/test_texts_reaudit.py`
- **G5 Archive.**
  - `mkdir -p archive/team_notes`
  - `git mv "STARS-BESIDE-YOU-main (2).zip" archive/`
  - `git mv "Instruciones filtros solar y temp" archive/team_notes/`
  - `git mv engine/web archive/old_web`
  - Write archive/README.md.
  - Test: `pytest tests/test_pipeline.py tests/test_engine.py tests/test_rover_integration.py`. Also `git grep "engine/web"` in code must find nothing.
- **G6 Index READMEs.** Write data/, audio/, video/ and economics/ README.md. Check that the top level is exactly: `.gitignore README.md app archive audio data docs economics engine scripts video`.
- **G7 Markdown rewrite.**
  - Apply the rule above to the living documents.
  - Check the links: `md_refs.py` should report 0 broken.
  - Test: the full engine suite, then `npm run build && npm run -s test:data`.
- **G8 (optional).** Change the engine JSON prose, rebuild the bundle, then run the masked comparison, the suite and test:data.

**Minimal fallback.** If the full plan is not green within an hour:
1. Do G1 only. The engine suite needs 0 edits; the 33 script lines are optional for green.
2. Then G5 (pure moves) and G6 (READMEs that point to the old locations of video-sim, AUDIO_TOP5.json and ASSUMPTIONS.md).
3. Leave those three where they are.
4. Prove with the suite, the build compare, `npm run build` and test:data, then stop.

## 7. Archive note (one line each)

- `archive/STARS-BESIDE-YOU-main (2).zip`: zip of the team's original main (commit d4a11e4).
  - 46 of its 50 files equal the current tree.
  - The other 4 are the team's original analog_finder.py, presets.json, mission_scoring.json and rover_preset.py.
  - sha256 `db67dcf04ba8417369871a05fd18aeccf5f490a1f2a3e63c7f84ee9b66f66254`.
- `archive/team_notes/Instruciones filtros solar y temp`: the team's note (Spanish) on how mission_scoring.py/json were designed; docs/FILTERS.md cites it.
- `archive/old_web/`: the team's first static web, replaced by app/. `engine/main.py:207` still writes `web/analog_data.js`, so create `engine/web/` before running main.py.
- Not archived but removed from the index: the 9 committed `.pyc` files. They are already ignored and stay in history.
- Records dated before this reorganisation use the old paths:
  - `tierra luna/` = `engine/`
  - `app/video-sim` = `video/video-sim`
  - `docs/AUDIO_TOP5.json` and `docs/AUDIO_RERECORD.md` = `audio/...`
  - `/ASSUMPTIONS.md` = `docs/ASSUMPTIONS.md`
