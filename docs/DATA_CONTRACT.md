# Data contract: static bundle v2 (contract revision 3, engine 3.0.0)

The engine (`tierra luna/engine`) writes a static, versioned bundle that the browser app reads with plain `fetch()`; no server is needed.

| command (run from `tierra luna/`) | dataset | output | shipped |
|---|---|---|---|
| `python -m engine build` (same as `--dataset real_1deg`) | real 1-degree tables (`output_real/*.csv`) | `app/public/data/v2/` (this contract) | yes |
| `python -m engine build --dataset legacy_2deg` | legacy 2-degree table | `build/legacy_2deg/` (same v2 format) | no |
| `python -m engine build --similarity-rule zone_twin --out DIR` | any | `DIR` (preview of the zone_twin rule) | no |

Datasets are described in `tierra luna/engine/datasets.json`, engine settings in `engine_config.json`. The machine check of this contract is `engine/bundle_v2.py` (`validate_bundle_v2`), run by the tests; it also shows, in Python, every decoding and recompute step below.

**What changed in revision 3** (engine 3.0.0, team lead decisions of 2026-11-14):

- exactly three offered missions: `rover`, `solar`, `lunar_base` (an exact copy of the team's `thermal` block); the `ice` block is an information component of `lunar_base`; `thermal` and `ice` are no longer separate missions or files;
- the funnel is exported step by step (`missions.json` `funnel`, reason codes with their step and one-line text);
- the similarity is the repository's own (`analog_finder`), described in the new `similarity.json`; the active rule is `repo_global_mean` (no twin); `twin`, `twin_count` and `twins.json` exist only when the rule has twins (`zone_twin`);
- utilities, z-scores and the ice component moved to the tiled detail files `earth_detail_NN.bin`; the per-mission `earth_<mission>.bin` keep the map columns;
- per-variable similarities `s.<v>`, `missing_n` and the v1 appendix were removed.

## General rules

- **Files.** JSON (UTF-8, compact, keys in a fixed order) for metadata and small tables; little-endian binary typed arrays (`.bin`) for per-cell numbers. Two builds from the same inputs are byte-identical. The build removes `.json` / `.bin` files of an earlier bundle that are not in the new one.
- **Version.** `bundle_version` is `"v2"` in every JSON file and the folder name; `manifest.contract_revision` is `3`.
- **Missing values.** A missing value is never `0` and never a default:
  - JSON: `null`;
  - Float32 column: `NaN`;
  - Int32 column: the sentinel `-2147483648` (INT32_MIN; `manifest.encoding.int32_missing`), never a valid value in this bundle.
- **Grid.** 180 rows x 360 columns of 1-degree cells per body (`manifest.grid`).
  - `id = row * 360 + col` (0..64799); Earth and Moon ids are separate namespaces.
  - Row 0 is at the north, column 0 at the west. Cell centre: `lat = 90 - (row + 0.5)`, `lon = -180 + (col + 0.5)`, longitude positive east, -180..180.
  - Earth latitudes are the source products' WGS84 geodetic latitudes (at most 0.19 deg from geocentric).
- **True cell size.** Earth 111.2 km north-south (6371 km sphere); Moon 30.3 km (1737.4 km sphere). East-west the cell is that size x cos(latitude): a polar cell is a narrow strip.
- **What a value means.** Every per-cell value is an aggregate over a whole cell (`variables.json` `aggregation`). Nothing in this bundle describes a point or a rover-scale site.
- **Text from team files** (gate `source`, weight `why`, mission `description`, class names such as `roca`, `suelo`, `continuo`, `ninguno`, and the `team_text` of a reason) is copied verbatim, in Spanish where the team wrote Spanish.

## Files

Sizes from the build of 2026-11-15 (`manifest.files[].bytes` is authoritative).

| file | format | loaded | rows | content | bytes |
|---|---|---|---|---|---|
| `manifest.json` | JSON | start | - | index of every file and binary column, grid, encoding, counts, detail tiles, credits | 158,884 |
| `missions.json` | JSON | start | - | offered missions, funnel steps, gates, weights, reason codes, counts, components, alpha, notes | 37,292 |
| `similarity.json` | JSON | start | - | the active similarity rule, formula, variables and weights, per-body statistics, variation findings, target | 9,790 |
| `variables.json` | JSON | start | - | per variable and body: real column, level, source, licence, baseline, caveat, comparability; lunar information columns | 64,922 |
| `places.json` | JSON | start | - | Earth country and region tables | 34,993 |
| `earth_base.bin` | bin | start | Earth land cells (25,497) | id, coordinates, country, region, values | 1,431,432 |
| `earth_rover.bin` | bin | start (default mission) | land / passing | fail bits; suitability, similarity, final, rank, confidence | 391,424 |
| `earth_solar.bin`, `earth_lunar_base.bin` | bin | on demand | land / passing | same layout | 627,744 / 169,720 |
| `earth_detail_00.bin` .. `earth_detail_17.bin` | bin | on demand (one per selected cell) | land cells of 10 grid rows | z-scores, utilities of every mission, the ice component | 7,392 - 332,160 each, 2,447,712 in all |
| `moon_base.bin` | bin | on demand | all 64,800 lunar cells | values, information column, nearest IAU feature | 2,598,480 |
| `moon_<mission>.bin` (3) | bin | on demand | all lunar cells | fail bits (and twin counts when the rule has twins) | 259,200 each |
| `twins.json` | JSON | on demand | - | only with a twin rule: every distinct twin per mission | absent today |
| `earth_place_detail.bin` | bin | on demand | Earth land cells | label rule, nearest populated place and its distance | 305,964 |
| `place_detail.json` | JSON | on demand | - | label rules, nearest-place names | 113,175 |
| `explain.json` | JSON | on demand | - | top 25 ranked Earth cells per mission with the whole funnel | 103,232 |
| `iau_moon_features.json` | JSON | on demand | - | 2,023 primary IAU lunar features | 105,663 |
| `lunar_named_sites.json` | JSON | on demand | - | named lunar sites, their cell and per-mission outcome | 13,951 |
| `validity.json` | JSON | on demand | - | schema validation report of the input tables | 251 |

- **First view** (`manifest.load.first_view` plus the manifest): 2,128,737 bytes, under the 2,500,000-byte target. **Total**: 9,392,229 bytes, under 14,000,000. Both targets are `engine_config.json` `first_view_budget_bytes`; the tests check them. The unshipped zone_twin preview (with `twins.json`, 831,574 bytes) totals 11,135,032 bytes and its first view 2,172,955.
- **Showing the funnel of one land cell** needs the first view (values, gates, reason tables, scores of the default mission), the mission file of each mission shown (fail bits and scores; 0.17-0.63 MB) and **one** detail tile (at most 332,160 bytes): never the whole set of tiles.
- Earth files hold only **land cells**: cells with any land (`mask_fraction > 0`, datasets.json `earth_land_cells`). Pure-ocean cells are absent; they fail every mission on the land gates.

## manifest.json

```json
{"bundle_version":"v2","contract_revision":3,"engine_version":"3.0.0",
 "dataset":{"id":"real_1deg","why":"..."},
 "build_time":"inputs-sha256:...","similarity_rule":"repo_global_mean",
 "inputs":[{"key":"EARTH","file":"earth_real_1deg.csv","sha256":"...","rows":64800},{"key":"MOON",...}],
 "config_sha256":{"mission_scoring.json":"...","engine_config.json":"...","datasets.json":"...","provenance_earth.csv":"...",
                  "provenance_moon.csv":"...","column_aliases.json":"...","iau_moon_nomenclature.csv":"...",
                  "ne_110m_admin_0_countries.geojson":"...","artemis_iii_regions.geojson":"..."},
 "grid":{...},"encoding":{"byte_order":"little","float32_missing":"NaN","int32_missing":-2147483648,"column_rule":"...","quantised_rule":"..."},
 "counts":{"EARTH":{"cells":64800,"land_cells":25497,"invalid_records":0},"MOON":{"cells":64800,"invalid_records":0},
           "missions":{"rover":{"pass_EARTH":10337,"pass_MOON":60988,"ranked_EARTH":10337,"distinct_twins":0},...},
           "lunar_features_for_labels":2023},
 "load":{"first_view":["missions.json","similarity.json","variables.json","places.json","earth_base.bin","earth_rover.bin"],
         "default_mission":"rover"},
 "detail_tiles":{"rows_per_tile":10,"lookup":"...",
                 "files":[{"name":"earth_detail_00.bin","row_start":0,"row_end":9,"land_cells":346}, ...]},
 "files":[{"name":"earth_rover.bin","bytes":391424,"sha256":"...","format":"bin","load":"start","description":"...",
           "body":"EARTH","mission":"rover","row_sets":{"land":25497,"passing":10337},
           "columns":[{"name":"fail_bits","type":"int32","rows":"land","length":25497,"offset":0,"missing":-2147483648,"scale":null,"description":"..."},
                      {"name":"suitability","type":"int32","rows":"passing","length":10337,"offset":...,"missing":-2147483648,
                       "scale":0.01,"divisor":100,"decode":"value = q / divisor"}, ...]}, ...],
 "sizes":{"first_view_bytes_without_manifest":1969853,"total_bytes_without_manifest":9233345,"detail_tile_max_bytes":332160,
          "budget":{"first_view_max":2500000,"total_max":14000000}},
 "credits":["...place-name credits...","...one entry per data product used, verbatim from the provenance files..."]}
```

- `build_time` is the `--build-time` text if one was passed, else `inputs-sha256:` and 16 hex digits of a hash of the input hashes. No clock is read.
- `similarity_rule` is the rule that produced the numbers (engine_config `similarity_rule`, or the `--similarity-rule` override of an unshipped preview).
- `files` lists every other file in load order with its size and sha256. The manifest does not list itself.

## Binary layout

Every `.bin` file is a plain concatenation of columns, without a header; the column index is in `manifest.files[]`.

| column key | meaning |
|---|---|
| `name` | column name (per-file tables below) |
| `type` | `float32` or `int32`, little-endian, 4 bytes per value |
| `length`, `offset` | number of values; byte offset of the first one (a multiple of 4; columns are contiguous, in index order) |
| `rows` | the row set the values follow (below) |
| `missing` | `"NaN"` (float32) or `-2147483648` (int32) |
| `scale`, `divisor`, `decode` | quantised columns only: Int32 `q`, `value = q / divisor` |
| `codes` | index columns: the JSON table the integer indexes |
| `unit`, `variables`, `per_grid_row`, `description` | value columns: unit, the mission variables read from this real column, stored once per grid row or not |

| `rows` | one value per | order |
|---|---|---|
| `land` | Earth land cell | `earth_base.bin` `id`, ascending |
| `passing` | Earth land cell passing the mission's hard filters | ascending id; `land_index` gives its position in `land` |
| `tile_land` | Earth land cell of one detail tile | ascending id; the tile's own `id` column |
| `all` | lunar cell | position = lunar cell id |
| `grid_rows`, `grid_cols` | grid row (180) / grid column (360) | a cell's row is `floor(id / 360)`, its column `id % 360` |

A value column constant along every grid row on the whole body (detected from the data: the sun-geometry formulas and the lunar values set by definition) is stored once per grid row (`per_grid_row = true`); the value of a cell is `column[floor(id / 360)]`.

Quantised columns store exactly the published value: `q / divisor` in double precision is the same double as the engine's number (utilities and similarities 6 decimals... see `engine_config.json` `binary_encoding`: utilities 6, z-scores 4, scores 2, confidence scores 3). Always divide; `q * scale` can differ in the last bit.

### Reading a column in TypeScript

```ts
type Column = { name: string; type: 'float32' | 'int32'; rows: string; length: number; offset: number;
                missing: 'NaN' | number; scale: number | null; divisor?: number; codes?: string };
type FileEntry = { name: string; bytes: number; format: 'json' | 'bin'; load: 'start' | 'on_demand';
                   row_sets?: Record<string, number>; columns?: Column[] };

const BASE = 'data/v2/';
const INT32_MISSING = -2147483648;   // manifest.encoding.int32_missing

async function loadBin(entry: FileEntry): Promise<Record<string, Float32Array | Int32Array>> {
  const buf = await (await fetch(BASE + entry.name)).arrayBuffer();
  const out: Record<string, Float32Array | Int32Array> = {};
  const littleEndianHost = new Uint8Array(new Uint32Array([1]).buffer)[0] === 1;
  for (const c of entry.columns!) {
    if (littleEndianHost) {          // every browser in practice: zero-copy views (offsets are 4-byte aligned)
      out[c.name] = c.type === 'float32' ? new Float32Array(buf, c.offset, c.length)
                                         : new Int32Array(buf, c.offset, c.length);
    } else {                         // big-endian host: decode with DataView
      const dv = new DataView(buf, c.offset, 4 * c.length);
      const a = c.type === 'float32' ? new Float32Array(c.length) : new Int32Array(c.length);
      for (let i = 0; i < c.length; i++) a[i] = c.type === 'float32' ? dv.getFloat32(4 * i, true) : dv.getInt32(4 * i, true);
      out[c.name] = a;
    }
  }
  return out;
}

const decodeQ = (q: number, c: Column) => (q === INT32_MISSING ? null : q / c.divisor!);
const rowValue = (col: Float32Array, id: number, cols = 360) => col[Math.floor(id / cols)];
const latOf = (lat: Float32Array, id: number) => lat[Math.floor(id / 360)];
const lonOf = (lon: Float32Array, id: number) => lon[id % 360];
// Reason codes of a cell from its fail bits (missions.json reason_codes[k].bit == k), in bit order.
const reasonsOf = (bits: number, codes: { bit: number; code: string; text: string; step: number }[]) =>
  codes.filter(r => (bits >>> r.bit) & 1);
// One-line elimination reason (missions.json elimination_line_rule).
const eliminationLine = (bits: number, codes: { bit: number; text: string }[]) =>
  codes.filter(r => (bits >>> r.bit) & 1).map(r => r.text).join('; ');
// Detail tile of a cell, and its position in that tile.
function tileOf(manifest: any, id: number) {
  const row = Math.floor(id / 360);
  return manifest.detail_tiles.files.find((t: any) => t.row_start <= row && row <= t.row_end);
}
function positionInTile(ids: Int32Array, id: number): number {   // binary search; -1 = not a land cell
  let lo = 0, hi = ids.length - 1;
  while (lo <= hi) { const m = (lo + hi) >> 1; if (ids[m] === id) return m; if (ids[m] < id) lo = m + 1; else hi = m - 1; }
  return -1;
}
```

## The funnel (team lead decision 2)

Identical for the three missions; `missions.json` `funnel` gives the text of each step.

| step | name | where in the bundle |
|---|---|---|
| 1 | common gates: land mask `elevation_m >= 1` (Earth only), `mask_fraction >= 0.3` (both bodies) | `missions[].gates[]` with `step: 1`; reason codes with `step: 1` |
| 2 | required variables: a missing one eliminates with `<variable> no data` | `missions[].require_present`; reason codes with `step: 2` |
| 3 | the mission's hard filters: failing one eliminates the cell for that mission (no score, no rank) | `gates[]` with `step: 3`; reason codes with `step: 3` |
| 4 | suitability 0-100, survivors only | `earth_<m>.bin` `suitability`; utilities in the detail tile |
| 5 | similarity | `earth_<m>.bin` `similarity`; z-scores in the detail tile; `similarity.json` |
| 6 | final = alpha x similarity + (1 - alpha) x suitability | `earth_<m>.bin` `final`, `rank`; `missions.json` `alpha` |

For every Earth land cell `id` and mission `m`, the panel shows:

1. **Gates.** For each `gates[g]` with `"EARTH"` in `applies_to`: the limit (`limit`, e.g. `"[2.5, inf]"`, or `min`, `max`, `allow`, `exclude`), the cell's value (`earth_base.bin` `v.<columns.EARTH>`; categories index `variables.json` `categories`) and pass or fail (fail when a reason code of that variable has its bit set in `earth_<m>.bin` `fail_bits[landPos]`). A gate value that is missing fails with the `missing` code.
2. **Elimination reason** in one line: the `text` of the set reason codes in bit order, joined with `"; "` (e.g. `"irradiance_kwh_m2_day outside [2.5, inf]; thermal_inertia_class not allowed"`); `team_text` is mission_scoring.py's own wording (`"... fuera de [2.5, inf]"`, `"... no permitido"`, `"... sin dato"`). An eliminated cell has no suitability, similarity, final or rank for that mission, whatever the weights, but may pass another mission.
3. **Suitability breakdown** (survivors): per weighted variable (`weighted_variables[]`): value (`earth_base.bin`), utility `u = tile "<m>.u.<v>"` (missing = the cell has no value: ignored, weights renormalised), weight `w`, contribution `w * u`; sort by contribution; points `= 100 * w * u / sum(w over variables with a utility)`; **coverage** `= sum(w with a utility) / sum(all w)`.
4. **Similarity, alpha, final**: `earth_<m>.bin` `similarity`, `final`, `rank`; `alpha` from `missions.json`; the z-scores and absolute values of both sides (section "similarity.json").
5. **Confidence**: `confidence` (index into `confidence_codes`) and `confidence_score`; the **level** of every value (`MEASURED`, `DERIVED`, `MODELLED`, `NO_DATA`) is in `variables.json` `variables[].bodies[EARTH|MOON].level` (per variable and body) and in `similarity.json` `variables[].levels`.
6. **lunar_base only, the ice component** (information, never changes the ranking): tile `lunar_base.ice.fail_bits` (bits index `missions[lunar_base].component_results.ice.reason_codes`), `lunar_base.ice.suitability` and `lunar_base.ice.u.<v>` (missing unless the cell passes ice).

## earth_base.bin (start)

| column | type | rows | content |
|---|---|---|---|
| `id` | int32 | land | Earth cell id |
| `lat`, `lon` | float32 | grid_rows, grid_cols | cell-centre coordinates |
| `country`, `region` | int32 | land | index into `places.json` `countries`, `regions` (sentinel: no label) |
| `v.<column>` | float32 / int32 | land or grid_rows | value of the real column `<column>`; categories are int32 indexes into `variables.json` `categories` |

Stored columns (real column, mission variables read from it): `elevation_m`, `mask_fraction`, `slope_iso_deg` (slope_300m_deg, slope_deg), `roughness_m` (rough_300m_m, roughness_m), `rock_or_bare_frac`, `irradiance_kwh_m2_day`, `sun_elev_max_deg` (per grid row), `sun_low_frac_0_5deg` (per grid row), `thermal_inertia_class`, `lst_diurnal_amp_k`, `tmin_c`, `permafrost_class`, `temp_k`.

## earth_\<mission\>.bin (rover at start, the others on demand)

| column | type | rows | content |
|---|---|---|---|
| `fail_bits` | int32 | land | bit k set when `missions.json` `reason_codes[k]` failed; `0` = the cell passes |
| `land_index` | int32 | passing | position of the cell in `earth_base.bin` |
| `suitability` | int32 q, /100 | passing | 0-100 |
| `similarity` | int32 q, /100 | passing | 0-100, the active rule (`similarity.json`); missing when the cell has no similarity variable with a value |
| `final` | int32 q, /100 | passing | 0-100 |
| `rank` | int32 | passing | 1 = best; sentinel when not ranked (no similarity) |
| `twin` | int32 | passing | **only when the rule has twins**: lunar twin id (= `moon_base.bin` position) |
| `confidence` | int32 | passing | index into `missions.json` `confidence_codes` (`low`, `medium`, `high`); sentinel = no confidence |
| `confidence_score` | int32 q, /1000 | passing | 0-1 |

## earth_detail_NN.bin (on demand, one tile per 10 grid rows)

`manifest.detail_tiles.files[k]` covers grid rows `row_start..row_end`; tiles are in row order, so concatenating every tile's rows gives the `land` order of `earth_base.bin`. All columns follow `tile_land`.

| column | content |
|---|---|
| `id` | Earth cell id (land cells of the tile, ascending) |
| `z.<variable>` | int32 q, /1e4: the per-body z-score of each active similarity variable (`similarity.json` `active_variables`); missing when the cell has no value or is outside the normalised population (`elevation_m > 0`) |
| `<mission>.u.<variable>` | int32 q, /1e6: utility 0-1 of each weighted variable of the mission; missing when the cell is eliminated for the mission or has no value |
| `lunar_base.ice.fail_bits` | bits of `missions[lunar_base].component_results.ice.reason_codes`; 0 = passes ice |
| `lunar_base.ice.u.<variable>`, `lunar_base.ice.suitability` | ice utilities (/1e6) and suitability (/100); missing unless the cell passes ice |

## moon_base.bin and moon_\<mission\>.bin (on demand)

`moon_base.bin`: `lat`, `lon`, the `v.<column>` value columns where the Moon has data (`rain_mm_day` and `wind_max_ms` have none; `mask_fraction`, `rock_or_bare_frac`, `thermal_inertia_class` and `permafrost_class` are constant by definition and stored per grid row), `info.rock_abundance_frac` (float32: Diviner rock abundance, information only, a different quantity from `rock_or_bare_frac`; its provenance is in `variables.json` `lunar_info_columns`), `feature` (index into `iau_moon_features.json`: the nearest primary IAU feature) and `feature_km` (great-circle km to its centre).

`moon_<mission>.bin`: `fail_bits` (all lunar cells, same bit table as Earth; information only: **lunar cells are not filtered for the similarity**) and, only when the rule has twins, `twin_count` (Earth cells whose twin is this cell).

Lunar z-scores are not stored per cell: `z = clip((value - median) / scale, -4, 4)` rounded to 4 decimals with the Moon's `median` and `scale` from `similarity.json`; a twin's z-scores are in `twins.json`.

## missions.json

```json
{"bundle_version":"v2","dataset":"real_1deg","config_version":"v1-draft","config_note":"...",
 "offered_missions":["rover","solar","lunar_base"],"default_mission":"rover",
 "components_not_offered":{"thermal":"core of lunar_base (...)","ice":"information component of lunar_base, ..."},
 "alpha":0.5,"alpha_why":"...","similarity_rule":"repo_global_mean",
 "funnel":[{"step":1,"name":"common gates","text":"..."}, ... {"step":6,"name":"final","text":"..."}],
 "elimination_line_rule":"the cell's reason codes (fail_bits) in bit order, their 'text' joined with '; '",
 "confidence_codes":["low","medium","high"],
 "missions":[{
   "id":"solar","title":"Solar array placement","description":"Colocacion de placas solares","author":"...",
   "threshold_status":{"status":"team_design_values","text":"Team design values: ... no external source ..."},
   "provisional":false,"provisional_note":null,"frozen_at":null,"components":{"core":null,"info":[]},
   "on_missing_gate":"drop","require_present":["irradiance_kwh_m2_day","sun_elev_max_deg","sun_low_frac_0_5deg","slope_deg"],
   "files":{"EARTH":"earth_solar.bin","MOON":"moon_solar.bin"},
   "gates":[{"variable":"elevation_m","step":1,"columns":{"EARTH":"elevation_m","MOON":"elevation_m"},"origin":"common",
             "applies_to":["EARTH"],"min":1.0,"max":null,"max_from":null,"allow":null,"exclude":null,"limit":"[1.0, inf]",
             "source":"solo tierra firme (...)"}, ...],
   "weighted_variables":[{"variable":"irradiance_kwh_m2_day","kind":"numeric","label":"Solar irradiance","unit":"kWh/m2/day",
             "columns":{...},"levels":{"EARTH":"MODELLED","MOON":"DERIVED"},"weight":0.35,"bad":2.5,"good":6.0,"map":null,
             "default":null,"why":"energia disponible","also_in_similarity":false}, ...],
   "reason_codes":[{"bit":2,"code":"irradiance_kwh_m2_day:below_min","variable":"irradiance_kwh_m2_day","kind":"below_min",
                    "label":"below minimum: irradiance_kwh_m2_day","step":3,
                    "text":"irradiance_kwh_m2_day outside [2.5, inf]","team_text":"irradiance_kwh_m2_day fuera de [2.5, inf]"}, ...],
   "pass_counts":{"EARTH":18777,"EARTH_LAND_CELLS":25497,"MOON":52400,"MOON_CELLS":64800},
   "ranked_count":18777,"passing_without_similarity":0,
   "top_failure_reasons":{"EARTH_LAND":[...],"MOON":[...]},
   "missing_data":{"EARTH_LAND":{"cells_with_missing_data":...,"cells_failing_only_on_missing_data":...,"by_variable":{...}},"MOON":{...}},
   "alpha":0.5,
   "similarity":{"rule":"repo_global_mean","twins":null,"no_twin_reason":"..."},
   "confidence_counts":{"low":6060,"medium":12717,"high":0},
   "distributions":{"suitability":{"min":...,"p05":...,"p25":...,"median":...,"p75":...,"p95":...,"max":...,"mean":...,"n":...},
                    "similarity":{...},"final":{...},"confidence_score":{...}},
   "component_results":{},
   "known_limitations":["..."],
   "facts":{"moon_pass_abs_lat_max":...,"distinct_twins":0,"twins":[],"twin_abs_lat_range":null,"top_n":25,
            "top_n_country_counts":{...},"confidence_constant":false},
   "not_used_by_engine":{"tolerances":null,"workable_days":null,"domain_weights":{...},"why":"..."}}, ...]}
```

- **`threshold_status`**: `provisional` (rover: its JSON block says so; `provisional_note` is the block's text) or `team_design_values` (solar and lunar_base: the JSON note says the solar and thermal thresholds have no external source). Show it next to every number of the mission.
- **`reason_codes`**: the bit table of `fail_bits` (both bodies). `kind` is `missing`, `below_min`, `above_max`, `not_allowed` or `excluded`; `step` is the funnel step; `text` the English line; `team_text` mission_scoring.py's own reason text (the engine checks, on every cell, that the join of the `team_text` of a cell's codes equals the reason string mission_scoring.apply_gates gives). At most 31 codes per mission.
- **`gates[].applies_to`**: the land gate `elevation_m` applies to EARTH only; `mask_fraction` to both bodies (it is 1 on the Moon by definition).
- **`weighted_variables[].also_in_similarity`**: true when the same variable is also one of the repository similarity variables (e.g. solar `slope_deg`, `roughness_m`).
- **`similarity`**: the rule; with `zone_twin` also `zone` (`name`, `kind`, `used`, `reason`, `cells`, `regions`), `distinct_twins`, `earth_cells_with_twin`, `largest_share` (`twin_id`, `earth_cells`, `share`).
- **`component_results`** (`lunar_base` only): `ice` with its gates, weighted variables, reason codes (the bit table of the tile's `lunar_base.ice.fail_bits`), pass counts (`EARTH`, `MOON`, `EARTH_passing_both`), top failure reasons and suitability distribution, and `role`: information only.
- **`distributions`**: of the passing Earth cells (suitability) and the ranked ones (the rest).

## similarity.json (start)

```json
{"bundle_version":"v2","dataset":"real_1deg","rule":"repo_global_mean","rule_why":"...","rule_options":{...},"alpha":0.5,
 "function":"analog_finder.compute_analog_ranking + analog_finder.normalize_planetary_features",
 "features_and_weights":"analog_finder.ANALOG_FEATURES and analog_finder.DEFAULT_WEIGHTS, imported at build time (not copied)",
 "formula":{"z":"...","distance":"...","similarity":"...","decay":0.45,"final":"..."},
 "meaning":"Each body is normalised on its own, so 'similar' means the same RELATIVE position on each body ...",
 "earth_population":{"rule":"elevation_m > 0.0","cells":25095},"moon_population":{"rule":"every lunar cell","cells":64800},
 "variables":[{"variable":"elevation_rel_m","status":"active","status_reason":null,"weight":0.15,"norm_weight":0.2,
               "columns":{"EARTH":"elevation_m","MOON":"elevation_m"},"column_note":"...","levels":{"EARTH":"MEASURED","MOON":"MEASURED"},
               "stats":{"EARTH":{"valid":true,"n":25095,"median":470.6,"scale":1006.7828,"mean":...,"min":...,"max":...,
                                 "iqr":...,"std_dev":...,"distinct_values":...,"variation":"ok"},"MOON":{...}},
               "target_global_mean":{"z":0.1425,"value":-521.3786}},
              {"variable":"rock_or_bare_frac","status":"excluded","status_reason":"Team lead decision 3: ...","norm_weight":null,...},
              {"variable":"sar_sigma0_db","status":"inactive","status_reason":"no values on at least one body ...",...}, ...],
 "active_variables":["elevation_rel_m","slope_deg","roughness_m","temp_k"],
 "variation_threshold":1e-06,
 "variation_findings":[{"variable":"rock_or_bare_frac","body":"MOON","variation":"zero","action":"removed from the similarity (similarity_excluded)"}, ...],
 "not_part_of_similarity":["irradiance_kwh_m2_day","lst_diurnal_amp_k","tmin_c","thermal_inertia_class","permafrost_class","rock_or_bare_frac"],
 "not_part_of_similarity_note":"...","z_decimals":4,
 "target":{"kind":"global_mean","name":"Global Lunar Surface Mean (-90° to +90°)",
           "profile":{"elevation_rel_m":{"z":0.1425,"value":-521.3786}, ...},
           "info_not_in_similarity":{"irradiance_kwh_m2_day":{"mean":6.4848,"level":"DERIVED","part_of_similarity":false}, ...}},
 "twins":null,"no_twin_reason":"..."}
```

With `zone_twin`, `target` is `{"kind":"zone_twin","tie_rule":"lowest_lunar_id","lunar_cells_filtered":false,"zones":{"rover":{...},"solar":{...},"lunar_base":{...}}}` and `twins`/`no_twin_reason` are absent.

- **Meaning.** Each body is normalised on its own, so a high similarity means the same **relative** position on each body, not equal absolute values. Show both: the Earth cell's z (tile `z.<v>`) and value (`earth_base.bin` `v.<columns.EARTH>`), and the lunar side's z and value (`target.profile`, or the twin's in `twins.json`).
- **`status`**: `active` (in the distance, `norm_weight` = weight / sum of active weights), `excluded` (a dataset decision; reason given), `inactive` (no values on a body: the repository's own rule drops it).
- **`variation`** per body: `ok`, `near_zero` (at least half the cells share one value), `zero` (every value equal: the repository would give every cell z = 0 and still count the variable), `no_data`.
- **Not part of the similarity**: the variables in `not_part_of_similarity` are shown for both points with the mark "not part of the similarity": Earth from `earth_base.bin`, the Moon from `target.info_not_in_similarity` (whole-Moon mean or commonest class) or from the twin (`twins.json` `not_part_of_similarity`).

## twins.json (on demand; only with a twin rule)

```json
{"bundle_version":"v2","dataset":"real_1deg","gazetteer":"...",
 "missions":{"rover":{"rule":"zone_twin","distinct_twins":744,"earth_cells_with_twin":10337,
   "largest_share":{"twin_id":59479,"earth_cells":895,"share":0.0866},
   "twins":[{"id":59479,"lat":-75.5,"lon":-100.5,"earth_cells":895,
             "z":{"elevation_rel_m":...,"slope_deg":...,"roughness_m":...,"temp_k":...},
             "values":{"elevation_rel_m":...,"slope_deg":...,"roughness_m":...,"temp_k":...},
             "not_part_of_similarity":{"irradiance_kwh_m2_day":...,"lst_diurnal_amp_k":...,"tmin_c":...,
                                       "thermal_inertia_class":"regolito","permafrost_class":"ninguno","rock_or_bare_frac":1.0},
             "feature":{"name":"Boltzmann","type":"Crater, craters","distance_km":80.9,
                        "url":"http://planetarynames.wr.usgs.gov/Feature/..."}}, ...]}, ...}}
```

Twins are listed by Earth-cell count descending, then id. `earth_cells` is the number of Earth points sharing the twin; `feature` is the nearest primary feature of the USGS/IAU gazetteer with the great-circle distance and the gazetteer URL.

## variables.json

As before: per variable `name`, `label`, `unit`, `kind`, `description`, `categories`, `used_by`, `in_engine`, `comparability`, and per body `column`, `stored_as`, `level`, `level_text`, `level_note`, `product`, `version`, `url`, `licence_credit`, `native_resolution`, `aggregation`, `formula`, `true_baseline`, `true_baseline_km`, `cell_ns_km`, `caveat`, `provenance_caveat`. New: `lunar_info_columns` (`[{column, stored_as, label, unit, note, level, product, url, licence_credit, caveat, used_by_engine: false}]`).

- Show `level` and `caveat` next to every value, and the true baseline for relief variables (never "300 m").
- Only `MEASURED` may be presented as measured. Lunar `permafrost_class` is `MODELLED`: the label `ninguno` on every cell, set by definition (team lead decision 5), not a measurement.
- `comparability` describes the physical quantities; it no longer selects similarity variables (the repository similarity uses its own fixed list, `similarity.json`).

## places.json, place_detail.json, earth_place_detail.bin

Unchanged: `places.json` `countries` (`[{code, name}]`, indexed by `earth_base.bin` `country`), `regions`, `region_rule`; `earth_place_detail.bin` (land rows) `label_rule`, `nearest_place`, `nearest_place_km`; label rules `natural_earth_polygon`, `natural_earth_polygon_geonames_code`, `nearest_geonames_place`, `antarctic_treaty_area`.

## explain.json, iau_moon_features.json, lunar_named_sites.json, validity.json

- `explain.json`: `{"top_n":25,"missions":{"rover":[item, ...], ...}}`, the top 25 ranked Earth cells per mission. Item: `rank`, `id`, `lat`, `lon`, `place`, `suitability`, `coverage`, `breakdown` (per weighted variable `variable`, `value`, `utility`, `weight`, `contribution`, `points`, `level`; sorted by contribution), `similarity` (`value`, `rule`, `earth` and `moon` z and value per active variable; with `zone_twin` also `twin`), `alpha`, `final`, `confidence`, `confidence_score`; `lunar_base` items also carry `components.ice` (`pass`, `fail` texts, `suitability`).
- `iau_moon_features.json`: column-oriented `name`, `type`, `lat`, `lon`, `diameter_km`; `moon_base.bin` `feature` indexes these arrays.
- `lunar_named_sites.json`: per site `missions.<m>` = `{pass, fail, fail_text, twin_of_count}` (`twin_of_count` null without a twin rule).
- `validity.json`: `{"valid", "bodies": {...}}`.

## Recompute formulas (browser)

For mission `m` and a passing Earth cell (`land_index` gives `landPos`; the tile and its position from `manifest.detail_tiles`):

```
V      = weighted_variables (order matters), w_v = weight (or a slider weight)
u_v    = tile "<m>.u.<v>" / 1e6        (null = missing)
U      = { v in V : u_v != null }
suitability = 100 * sum_{v in U} w_v * u_v / sum_{v in U} w_v                 (sum in V order; null if empty)
coverage    = sum_{v in U} w_v / sum_{v in V} w_v

F      = similarity.json active_variables, nw_f = variables[f].norm_weight (sum in F order)
ze_f   = tile "z.<f>" / 1e4;  zm_f = target.profile[f].z (repo_global_mean) or the twin's twins.json z[f] (zone_twin)
P      = { f in F : ze_f != null and zm_f != null }
d2     = sum_{f in F} nw_f * (ze_f - zm_f)^2                 if P == F
       = sum_{f in P} nw_f * (ze_f - zm_f)^2 / sum_{f in P} nw_f   otherwise      (null if P is empty)
similarity = round2(100 * exp(-decay * sqrt(d2)))            decay = formula.decay; round2 = numpy.round(x, 2)

final  = alpha * similarity + (1 - alpha) * suitability       (alpha = missions.json alpha; unrounded suitability)
rank   = order the cells with a final by round(final, 2) descending, ties by cell id ascending, from 1
```

- With the published weights this reproduces every stored value exactly (`round(x, 2) == q / 100`) and the stored rank; `validate_bundle_v2` checks every passing cell of the three missions from the bundle alone, under both rules (`test_recompute_from_bundle_for_both_rules`).
- A slider changes `w_v` (suitability only); the similarity weights and the twins are fixed at build time. Cells that fail the mission are never scored or ranked.
- Rounding: stored suitability and final use Python's `round`; similarity uses `numpy.round` as analog_finder does. `Math.round(x * 100) / 100` can differ on an exact half; such a difference can only swap cells whose finals differ by less than 0.01.

Build-time quantities (display only):

```
numeric utility      u = clip((value - bad) / (good - bad), 0, 1)
categorical utility  u = map[class], or default for a class not in the map; null when the value is missing
z (per body)         z = clip((value - median) / scale, -4, 4), rounded to 4 decimals (analog_finder.normalize_planetary_features)
twin (zone_twin)     = the zone cell with the smallest d2; ties -> lowest lunar id; lunar cells are not filtered
confidence score     = min(Earth level score, Moon level score) * coverage (engine_config confidence); without a twin
                       a variable counts on the Moon when the lunar table has data for it
```

## Units

| variable (mission name) | unit | | variable | unit |
|---|---|---|---|---|
| elevation_m, rough_300m_m, roughness_m | m | | irradiance_kwh_m2_day | kWh/m2/day (per 24 h, horizontal surface) |
| slope_300m_deg, slope_deg, sun_elev_max_deg | deg | | temp_k, lst_diurnal_amp_k | K |
| tmin_c | degC | | mask_fraction, rock_or_bare_frac, sun_low_frac_0_5deg, rock_abundance_frac | fraction 0-1 |
| thermal_inertia_class, permafrost_class | category | | z-scores | dimensionless (robust spreads from the body's median) |

Scores are 0-100; utilities and confidence scores 0-1; distances km.

## Meaning of NaN, null and sentinels

| where | marker | meaning |
|---|---|---|
| `v.<column>` float32 | NaN | the input table has no value for that cell |
| `v.<column>` int32 (category) | sentinel | no class for that cell (e.g. Earth permafrost south of the map) |
| `<m>.u.<v>` | sentinel | eliminated for `m` (check `fail_bits`), or no value for `v` (the weight drops out) |
| `z.<f>` | sentinel | no value for `f`, or outside the normalised population; the variable drops out of the distance |
| `similarity`, `final`, `rank` | sentinel | no similarity variable with a value on the cell |
| `country`, `region`, `label_rule`, `nearest_place` | sentinel | no label |
| JSON | `null` | missing |

`0` is always a real value.

## Bundle v1 (retired)

Engine 3.0.0 no longer writes the v1 JSON bundle: the legacy table goes through the v2 exporter too (`build/legacy_2deg/`, not shipped). The v1 exporter (`engine/export.py`, `engine/contract.py`) remains in the code for reference; its format assumed a lunar twin for every ranked cell, which the default rule does not have.
