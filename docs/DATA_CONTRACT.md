# Data contract: static bundle v2

The engine (`tierra luna/engine`) writes a static, versioned bundle that the browser app reads with plain `fetch()`; no server is needed.

| command (run from `tierra luna/`) | dataset | output | shipped |
|---|---|---|---|
| `python -m engine build` (same as `--dataset real_1deg`) | real 1-degree tables (`output_real/*.csv`) | `app/public/data/v2/` (this contract) | yes |
| `python -m engine build --dataset legacy_2deg` | legacy 2-degree table | `build/legacy_2deg/` (v1 format, appendix) | no |

Datasets are described in `tierra luna/engine/datasets.json`. The machine check of this contract is `engine/bundle_v2.py` (`validate_bundle_v2`), run by the tests; it also shows, in Python, every decoding step below.

## General rules

- **Files.** JSON (UTF-8, compact, keys in a fixed order) for metadata and small tables; little-endian binary typed arrays (`.bin`) for per-cell numbers. Two builds from the same inputs are byte-identical.
- **Version.** `bundle_version` is `"v2"` in every JSON file and in the folder name. An incompatible change goes to `v3`.
- **Missing values.** A missing value is never `0` and never a default:
  - JSON: `null`;
  - Float32 column: `NaN`;
  - Int32 column: the sentinel `-2147483648` (INT32_MIN; `manifest.encoding.int32_missing`), which is never a valid value in this bundle.
- **Grid.** 180 rows x 360 columns of 1-degree cells per body (`manifest.grid`).
  - `id = row * 360 + col` (0..64799); Earth and Moon ids are separate namespaces.
  - Row 0 is at the north, column 0 at the west. Cell centre: `lat = 90 - (row + 0.5)`, `lon = -180 + (col + 0.5)`, longitude positive east, -180..180.
  - Earth latitudes are the source products' WGS84 geodetic latitudes (at most 0.19 deg from geocentric).
- **True cell size.** Earth 111.2 km north-south (6371 km sphere); Moon 30.3 km (1737.4 km sphere). East-west the cell is that size x cos(latitude): a polar cell is a narrow strip (0.26 km wide on the Moon next to the pole).
- **What a value means.** Every per-cell value is an aggregate over a whole cell (a mean, a share or a percentile of finer pixels; see `variables.json` `aggregation`). Nothing in this bundle describes a point or a rover-scale site.
- **Text from team files** (gate `source`, weight `why`, mission `description`, class names such as `roca`, `suelo`, `continuo`) is copied verbatim, in Spanish where the team wrote Spanish.

## Files

Sizes from the build of 2026-11-14 (`manifest.files[].bytes` is authoritative).

| file | format | loaded | rows | content | bytes |
|---|---|---|---|---|---|
| `manifest.json` | JSON | start | - | index of every file and every binary column, grid, encoding, counts, credits | 33,443 |
| `missions.json` | JSON | start | - | missions, gates, weights, reason codes, counts, missing-data losses, scales, distributions, notes | 38,429 |
| `variables.json` | JSON | start | - | per variable and body: real column, level, source, licence, native resolution, true baseline, caveat, comparability | 62,912 |
| `places.json` | JSON | start | - | Earth country and region tables | 34,993 |
| `earth_base.bin` | bin | start | Earth land cells (25,497) | id, coordinates, country, region, values | 1,431,432 |
| `earth_rover.bin` | bin | start (default mission) | land / passing | fail bits, utilities, scores, twin, rank, confidence | 680,860 |
| `earth_solar.bin`, `earth_thermal.bin`, `earth_ice.bin` | bin | on demand | land / passing | same layout per mission | 1,679,256 / 266,480 / 377,988 |
| `moon_base.bin` | bin | on demand | all 64,800 lunar cells | values, nearest IAU feature | 2,338,560 |
| `moon_<mission>.bin` (4) | bin | on demand | all lunar cells | fail bits, twin counts | 518,400 each |
| `earth_place_detail.bin` | bin | on demand | Earth land cells | label rule, nearest populated place and its distance | 305,964 |
| `place_detail.json` | JSON | on demand | - | label rules, nearest-place names | 113,175 |
| `explain.json` | JSON | on demand | - | top 25 ranked Earth cells per mission, explained per variable | 140,848 |
| `iau_moon_features.json` | JSON | on demand | - | 2,023 primary IAU lunar features | 105,663 |
| `lunar_named_sites.json` | JSON | on demand | - | 18 named lunar sites, their cell and per-mission outcome | 13,105 |
| `validity.json` | JSON | on demand | - | schema validation report of the input tables | 251 |

- **First view** (`manifest.load.first_view` plus the manifest): 2,282,069 bytes, under the 2,500,000-byte target. **Total**: 9,696,959 bytes, under 14,000,000. Both targets are `engine_config.json` `first_view_budget_bytes`; the tests check them.
- Earth files hold only **land cells**: cells with any land (`mask_fraction > 0`, datasets.json `earth_land_cells`). Pure-ocean cells are absent from every Earth file; they fail every mission on the land gates.

## manifest.json

```json
{"bundle_version":"v2","engine_version":"2.0.0",
 "dataset":{"id":"real_1deg","why":"..."},
 "build_time":"inputs-sha256:fc3e098c44b0e487",
 "inputs":[{"key":"EARTH","file":"earth_real_1deg.csv","sha256":"3eb11d43...","rows":64800},
           {"key":"MOON","file":"moon_real_1deg.csv","sha256":"906de058...","rows":64800}],
 "config_sha256":{"mission_scoring.json":"...","engine_config.json":"...","datasets.json":"...",
                  "provenance_earth.csv":"...","provenance_moon.csv":"...","column_aliases.json":"...",
                  "iau_moon_nomenclature.csv":"...","ne_110m_admin_0_countries.geojson":"..."},
 "grid":{"rows":180,"cols":360,"cell_deg":1.0,"cell_id":"row * 360 + col","lat_center":"90 - (row + 0.5) * 1.0",
         "lon_center":"-180 + (col + 0.5) * 1.0 (positive east, -180..180)","row0":"north","col0":"west",
         "bodies":{"EARTH":{"radius_km":6371.0,"cell_ns_km":111.2,...},"MOON":{"radius_km":1737.4,"cell_ns_km":30.3,...}}},
 "encoding":{"byte_order":"little","float32_missing":"NaN","int32_missing":-2147483648,"column_rule":"...","quantised_rule":"..."},
 "counts":{"EARTH":{"cells":64800,"land_cells":25497,"invalid_records":0},"MOON":{"cells":64800,"invalid_records":0},
           "missions":{"rover":{"pass_EARTH":10337,"pass_MOON":60988,"ranked_EARTH":10337,"distinct_twins":7215},...},
           "lunar_features_for_labels":2023},
 "load":{"first_view":["missions.json","variables.json","places.json","earth_base.bin","earth_rover.bin"],"default_mission":"rover"},
 "files":[{"name":"earth_rover.bin","bytes":680860,"sha256":"...","format":"bin","load":"start","description":"...",
           "body":"EARTH","mission":"rover","row_sets":{"land":25497,"passing":10337},
           "columns":[{"name":"fail_bits","type":"int32","rows":"land","length":25497,"offset":0,"missing":-2147483648,"scale":null,"description":"..."},
                      {"name":"land_index","type":"int32","rows":"passing","length":10337,"offset":101988,...},
                      {"name":"u.slope_300m_deg","type":"int32","rows":"passing","length":10337,"offset":143336,
                       "missing":-2147483648,"scale":1e-06,"divisor":1000000,"decode":"value = q / divisor",...}, ...]},
          {"name":"missions.json","bytes":38126,"sha256":"...","format":"json","load":"start","description":"..."}, ...],
 "sizes":{"first_view_bytes_without_manifest":2248626,"total_bytes_without_manifest":9663516,
          "budget":{"first_view_max":2500000,"total_max":14000000}},
 "credits":["Lunar feature names: ...", "...one entry per data product actually used, verbatim from the provenance files..."]}
```

- `build_time` is the `--build-time` text if one was passed, else `inputs-sha256:` and 16 hex digits of a hash of the input hashes. No clock is read.
- `files` lists every other file in load order with its size and sha256. The manifest does not list itself.
- `credits` are the place-name credits plus the `licence_credit` text of every product behind an engine variable, verbatim (WorldClim's says non-commercial use only; see ASSUMPTIONS.md section 10).

## Binary layout

Every `.bin` file is a plain concatenation of columns. There is no header: the column index is in `manifest.files[]`.

| column key | meaning |
|---|---|
| `name` | column name (see the per-file tables below) |
| `type` | `float32` or `int32`, little-endian, 4 bytes per value |
| `length` | number of values |
| `offset` | byte offset of the first value in the file (a multiple of 4; columns are contiguous, in index order) |
| `rows` | the row set the values follow (below) |
| `missing` | `"NaN"` (float32) or `-2147483648` (int32) |
| `scale`, `divisor`, `decode` | quantised columns only: Int32 `q`, `value = q / divisor` (`scale = 1 / divisor`) |
| `codes` | for index columns: the JSON table the integer indexes |
| `unit`, `variables`, `per_grid_row`, `description` | value columns: unit, the mission variables read from this real column, and whether it is stored once per grid row |

Row sets (`file.row_sets` gives each one's length):

| `rows` | one value per | order |
|---|---|---|
| `land` | Earth land cell | `earth_base.bin` `id`, ascending |
| `passing` | Earth land cell that passes the mission's hard filters | ascending id; `land_index` gives the position in `land` |
| `all` | lunar cell | position = lunar cell id |
| `grid_rows` | grid row (180) | row 0 = north; a cell's row is `floor(id / 360)` |
| `grid_cols` | grid column (360) | column 0 = west; a cell's column is `id % 360` |

A value column whose data is constant along every grid row on the whole body (detected at build time from the data, for example the sun-geometry formulas, or the lunar values set by definition) is stored once per grid row (`rows = "grid_rows"`, `per_grid_row = true`); the value of a cell is `column[floor(id / 360)]`.

Quantised columns store exactly the published value: `q / divisor` in double precision is the same double as the engine's published number (utilities and similarities 6 decimals, scores 2, confidence scores 3). Always divide; `q * scale` can differ in the last bit.

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

// Float32 value column: NaN = missing.
const isMissingFloat = (x: number) => Number.isNaN(x);
// Int32 index or count column: the sentinel = missing.
const isMissingInt = (x: number) => x === INT32_MISSING;
// Quantised column (has 'divisor'): the exact published value, or null.
const decodeQ = (q: number, c: Column) => (q === INT32_MISSING ? null : q / c.divisor!);
// Per-grid-row column: value of cell id.
const rowValue = (col: Float32Array, id: number, cols = 360) => col[Math.floor(id / cols)];
// Coordinates of a cell from the grid axes in earth_base.bin / moon_base.bin.
const latOf = (lat: Float32Array, id: number) => lat[Math.floor(id / 360)];
const lonOf = (lon: Float32Array, id: number) => lon[id % 360];
// Reason codes of a cell from its fail bits (missions.json reason_codes[k].bit == k).
const reasonsOf = (bits: number, codes: { bit: number; code: string; label: string }[]) =>
  codes.filter(r => (bits >>> r.bit) & 1);
```

## earth_base.bin (start)

| column | type | rows | content |
|---|---|---|---|
| `id` | int32 | land | Earth cell id |
| `lat` | float32 | grid_rows | cell-centre latitude per grid row |
| `lon` | float32 | grid_cols | cell-centre longitude per grid column |
| `country` | int32 | land | index into `places.json` `countries` (sentinel: no label) |
| `region` | int32 | land | index into `places.json` `regions` (sentinel: no region) |
| `v.<column>` | float32 / int32 | land or grid_rows | value of the real column `<column>`; categories are int32 indexes into `variables.json` `categories` of the variable(s) named in `variables` |

Stored columns (real column, mission variables read from it): `elevation_m`, `mask_fraction`, `slope_iso_deg` (slope_300m_deg, slope_deg), `roughness_m` (rough_300m_m, roughness_m), `rock_or_bare_frac`, `irradiance_kwh_m2_day`, `sun_elev_max_deg` (per grid row), `sun_low_frac_0_5deg` (per grid row), `thermal_inertia_class`, `lst_diurnal_amp_k`, `tmin_c`, `permafrost_class`, `temp_k`. `rain_mm_day` and `wind_max_ms` are only named by rover `workable_days`, which `mission_scoring.py` does not read, so they are not stored (`variables.json` says so).

## earth_\<mission\>.bin (rover at start, the others on demand)

| column | type | rows | content |
|---|---|---|---|
| `fail_bits` | int32 | land | bit k set when `missions.json` `reason_codes[k]` failed; `0` = the cell passes the mission |
| `land_index` | int32 | passing | position of the cell in `earth_base.bin` |
| `u.<variable>` | int32 q, /1e6 | passing | utility 0-1 of each weighted variable, in `weighted_variables` order; missing = no data (the weight is dropped) |
| `suitability` | int32 q, /100 | passing | 0-100 |
| `twin` | int32 | passing | lunar twin id (= `moon_base.bin` position); sentinel = no twin |
| `s.<variable>` | int32 q, /1e6 | passing | similarity 0-1 to the twin, similarity variables only (`similarity_variables`) |
| `similarity` | int32 q, /100 | passing | 0-100; missing when there is no twin |
| `final` | int32 q, /100 | passing | 0-100; missing when there is no twin |
| `rank` | int32 | passing | 1 = best; sentinel when not ranked (no twin) |
| `confidence` | int32 | passing | index into `missions.json` `confidence_codes` (`low`, `medium`, `high`); sentinel = no confidence |
| `confidence_score` | int32 q, /1000 | passing | 0-1 |
| `missing_n` | int32 | passing | weighted variables with no data on the Earth cell |

A land cell with `fail_bits != 0` failed the mission's hard filters: it has no scores, no twin and no rank, whatever the weights. With the real tables no lunar cell passes the ice mission (no lunar permafrost data), so every ice twin, similarity, final and rank is missing.

## moon_base.bin and moon_\<mission\>.bin (on demand)

`moon_base.bin`: `lat` (grid_rows), `lon` (grid_cols), the same `v.<column>` value columns as Earth where the Moon has data (`permafrost_class`, `rain_mm_day` and `wind_max_ms` have none and are not stored; `mask_fraction`, `rock_or_bare_frac` and `thermal_inertia_class` are constant by definition and stored per grid row), `feature` (int32 index into `iau_moon_features.json` arrays: the nearest primary IAU feature) and `feature_km` (float32, great-circle distance in km to that feature's centre).

`moon_<mission>.bin`: `fail_bits` (all lunar cells, same bit table as Earth) and `twin_count` (how many Earth cells chose the lunar cell as their twin).

## missions.json

```json
{"bundle_version":"v2","dataset":"real_1deg","config_version":"v1-draft","config_note":"...","default_mission":"rover",
 "twin_rule":"...","confidence_codes":["low","medium","high"],
 "missions":[{
   "id":"rover","title":"Rover mobility and trafficability","description":"...","author":"...","provisional":true,
   "provisional_note":"...","frozen_at":"...","on_missing_gate":"drop","require_present":["slope_300m_deg","rough_300m_m"],
   "files":{"EARTH":"earth_rover.bin","MOON":"moon_rover.bin"},
   "gates":[{"variable":"slope_300m_deg","columns":{"EARTH":"slope_iso_deg","MOON":"slope_iso_deg"},"origin":"mission",
             "applies_to":["EARTH","MOON"],"min":0.5,"max":15.0,"max_from":"...","allow":null,"exclude":null,"source":"..."}, ...],
   "weighted_variables":[{"variable":"slope_300m_deg","kind":"numeric","label":"Slope (rover)","unit":"deg",
             "columns":{"EARTH":"slope_iso_deg","MOON":"slope_iso_deg"},"weight":0.45,"bad":15.0,"good":1.0,"map":null,
             "default":null,"why":"...","in_similarity":true,"similarity_exclusion":null,
             "comparability":"comparable","comparability_note":"..."}, ...],
   "similarity_variables":["slope_300m_deg","rough_300m_m"],
   "reason_codes":[{"bit":0,"code":"elevation_m:below_min","variable":"elevation_m","kind":"below_min","label":"below minimum: elevation_m"},
                   {"bit":1,"code":"elevation_m:missing","variable":"elevation_m","kind":"missing","label":"no data: elevation_m"}, ...],
   "pass_counts":{"EARTH":10337,"EARTH_LAND_CELLS":25497,"MOON":60988,"MOON_CELLS":64800},
   "ranked_count":10337,"passing_without_twin":0,
   "top_failure_reasons":{"EARTH_LAND":[{"reason":"slope_300m_deg:below_min","cells":12639}, ...],"MOON":[...]},
   "missing_data":{"EARTH_LAND":{"cells_with_missing_data":714,"cells_failing_only_on_missing_data":0,
                                 "by_variable":{"slope_300m_deg":714,"rough_300m_m":376,"elevation_m":252}},"MOON":{...}},
   "mix_factor":0.5,
   "similarity_scales":{"slope_300m_deg":{"kind":"numeric","scale":9.419,"p_low":0.722,"p_high":10.141,"n_cells":71325}, ...},
   "confidence_counts":{"low":0,"medium":10337,"high":0},
   "distributions":{"suitability":{"min":...,"p05":...,"p25":...,"median":...,"p75":...,"p95":...,"max":...,"mean":...,"n":...},
                    "similarity":{...},"final":{...},"confidence_score":{...}},
   "excluded_from_similarity":{"rock_or_bare_frac":"not the same quantity on both bodies: ..."},
   "known_limitations":["The rover thresholds ... were written for a 300 m baseline ..."],
   "facts":{"moon_pass_abs_lat_max":89.5,"distinct_twins":7215,"twins":[...],"twin_abs_lat_range":[0.5,89.5],"top_n":25,
            "top_n_country_counts":{...},"confidence_constant":true},
   "not_used_by_engine":{"tolerances":{...},"workable_days":{...},"domain_weights":{...},"why":"..."}}, ...]}
```

- **`reason_codes`.** The bit table of `fail_bits`, shared by both bodies of a mission. `kind` is `missing` (label "no data"), `below_min`, `above_max`, `not_allowed` or `excluded`. At most 31 codes per mission (the build refuses more).
- **`missing_data`.** How many land cells (Earth) or cells (Moon) fail because a gated or required value is empty: with any missing reason, with only missing reasons (the cells the mission loses to missing data alone), and per variable.
- **`gates[].applies_to`.** The common `elevation_m` land gate applies to EARTH only; `mask_fraction` (land share) to both bodies (it is 1 on the Moon by definition).
- **`columns`.** The real column each mission variable is read from on each body (`variables.json` explains why).
- **`similarity_scales`.** 5th-95th percentile range of each numeric similarity variable, pooled over the passing cells of both bodies.
- **`distributions`.** Of the passing Earth cells (suitability) and the ranked ones (the rest).
- **`known_limitations`, `facts`.** Plain-language limits of this mission's results and the numbers they refer to, computed at build time.

## variables.json

```json
{"bundle_version":"v2","dataset":"real_1deg",
 "levels":{"MEASURED":"...","DERIVED":"...","MODELLED":"...","UNDOCUMENTED":"...","NO_DATA":"..."},
 "comparability_statuses":{"comparable":"...","comparable_with_caveat":"...","not_comparable":"..."},
 "variables":[{"name":"slope_300m_deg","label":"Slope (rover)","unit":"deg","kind":"numeric","description":"...",
   "categories":null,"used_by":{"rover":["gate","require_present","soft"]},"in_engine":true,
   "comparability":{"status":"comparable","reason":"Same definition on both bodies ... not 300 m slopes."},
   "bodies":{"EARTH":{"column":"slope_iso_deg","alias_column":"slope_deg","column_override":true,"column_override_why":"...",
      "stored":true,"stored_as":"v.slope_iso_deg","not_stored_reason":null,
      "level":"DERIVED","level_text":"DERIVED","level_note":null,
      "product":"ETOPO 2022 Global Relief Model, ...","version":"v1 (2022)","url":"...","licence_credit":"US Government work, ...",
      "native_resolution":"60 arc-second (1.853 km N-S; ...)","aggregation":"AREA-WEIGHTED (cos lat) mean of the land-pixel slopes",
      "formula":"...","true_baseline":"3.706 km in both directions","true_baseline_km":3.706,"cell_ns_km":111.2,
      "caveat":"no open global DEM-derived product at a 300 m baseline is used here; ...","provenance_caveat":"..."},
    "MOON":{"column":"slope_iso_deg",...,"true_baseline":"3.79 km in both directions","true_baseline_km":3.79,...}}}, ...]}
```

- The app must show `level` and `caveat` next to every value, and the true baseline for relief variables ("slope at a 3.7 km baseline"; never "300 m": no value here has a 300 m baseline).
- Only `MEASURED` may be presented as measured. `level` comes from the builders' provenance files (`real_data/provenance_*.csv`), row of the real column actually read; `level_text` is that file's wording; `NO_DATA` means the variable has no data on that body.
- `licence_credit` is the provenance file's licence and credit text, verbatim (licence and credit are one text there).
- `comparability.status`: `comparable` (used in the similarity), `comparable_with_caveat` (used; show `reason`), `not_comparable` (left out of the similarity and the twin search; still in suitability).
- `stored_as` names the `v.<column>` of the base files; `not_stored_reason` says why a variable has no column on a body.

## places.json, place_detail.json, earth_place_detail.bin

- `places.json`: `countries` (`[{code, name}]`, indexed by `earth_base.bin` `country`), `regions` (names, indexed by `region`), `region_rule`.
- `earth_place_detail.bin` (land rows): `label_rule` (index into `place_detail.json` `label_rules`), `nearest_place` (index into `nearest_places`), `nearest_place_km` (float32).
- Label rules: `natural_earth_polygon`, `natural_earth_polygon_geonames_code`, `nearest_geonames_place`, `antarctic_treaty_area` (texts in `place_detail.json` `label_rule_text`). A region is given only when the nearest GeoNames place is in the same country and within one cell (111.2 km) of the centre. A 111 km cell can span several countries: the label is that of the cell centre.

## explain.json, iau_moon_features.json, lunar_named_sites.json, validity.json

- `explain.json`: `{"bundle_version":"v2","top_n":25,"missions":{"rover":[item, ...], ...}}`, the top 25 ranked Earth cells per mission. Each item has the same structure as in v1 (appendix): `rank`, `id`, `lat`, `lon`, `place` (with `nearest_place`), `twin` (`id`, `lat`, `lon`, `feature`), `suitability`, `similarity`, `final`, `confidence`, `confidence_score`, `missing_n`, and per weighted variable `earth`, `moon`, `difference`, `utility`, `similarity`, weights and points, plus `helps_most` and `hurts_most`. Values are the mission variables (from the aliased real columns). Ice has no ranked cell, so its list is empty.
- `iau_moon_features.json`: as v1 (column-oriented `name`, `type`, `lat`, `lon`, `diameter_km`); `moon_base.bin` `feature` indexes these arrays.
- `lunar_named_sites.json`: `{"sites":[{"name","type","why","site_note","lat","lon","diameter_km","cell_id","feature_vs_cell","gazetteer_link","missions":{"rover":{"pass","fail","twin_of_count"},...}}]}` from `real_data/lunar_named_sites.csv`. A site without coordinates in that file has `null` coordinates, cell and missions. Its cell values are in `moon_base.bin` at position `cell_id`.
- `validity.json`: `{"valid", "bodies": {...}}` as in v1; 0 failing records today. The real tables have no physically-valid ranges in their provenance files, so only the grid, coordinates and category vocabularies are checked.

## Formulas the browser must use (slider weights)

For one mission and one passing Earth cell `k` (a row of the `passing` set):

- `V`: the mission's weighted variables, in `weighted_variables` order.
- `w_v`: the slider weights (defaults `weighted_variables[].weight`).
- `u_v = u.<v>[k] / 1e6` (null when the sentinel); `s_v = s.<v>[k] / 1e6` for `v` in `similarity_variables`.
- `a`: `mix_factor` (0.5).

```
U = { v in V : u_v != null }
S = { v in V : v in similarity_variables and s_v != null }

suitability = 100 * sum_{v in U} w_v * u_v / sum_{v in U} w_v          (null if the denominator is 0)
similarity  = 100 * sum_{v in S} w_v * s_v / sum_{v in S} w_v          (null if the denominator is 0, or no twin)
final       = a * similarity + (1 - a) * suitability                    (null if either is null)
rank        = order the cells with a final by round(final, 2) descending, ties by cell id ascending, from 1
```

- Sum in `weighted_variables` order: each sum starts at 0 and adds `w_v * u_v`; then divide `100 * num` by `den`. Do not round before computing `final`.
- With the default weights this reproduces the stored values exactly: `round(suitability, 2) == suitability_q / 100`, the same for `similarity` and `final`, and ranking the rounded finals by the rule gives the stored `rank`. `test_recompute_from_bundle_reproduces_every_passing_cell` checks all 37,283 passing cells of the four missions from the bundle alone.
- The twin is fixed at build time (chosen with the JSON weights). A slider re-scores each cell against the same twin; it never searches for a new twin. Cells that fail the mission are never scored or ranked.
- Rounding: the stored values use Python's `round` (correct rounding of the exact binary value, half to even). `Math.round(x * 100) / 100` can differ on a value exactly on a half; such a difference can only swap cells whose finals differ by less than 0.01.

Build-time quantities (display only; the browser does not recompute them):

```
numeric utility      u = clip((value - bad) / (good - bad), 0, 1)
categorical utility  u = map[class], or default for a class not in the map; null when the value is missing
numeric similarity   s = max(0, 1 - |earth - moon| / scale)          (scale from similarity_scales)
categorical sim.     s = 1 if earth == moon else 0
twin                 = lunar cell passing the same mission with the highest similarity (default weights), ties -> lowest id
confidence score     = min(Earth level score, Moon level score) * coverage; each body's score is the weight-averaged
                       level score over the weighted variables with data on that body's cell; coverage = share of the
                       weight with data on both the Earth cell and its twin; "high" needs score >= 0.8 and cells <= 1 km
```

## Units

| variable (mission name) | unit | | variable | unit |
|---|---|---|---|---|
| elevation_m, rough_300m_m, roughness_m | m | | irradiance_kwh_m2_day | kWh/m2/day (per 24 h, horizontal surface) |
| slope_300m_deg, slope_deg, sun_elev_max_deg | deg | | temp_k, lst_diurnal_amp_k | K |
| tmin_c | degC | | mask_fraction, rock_or_bare_frac, sun_low_frac_0_5deg | fraction 0-1 |
| thermal_inertia_class, permafrost_class | category | | rain_mm_day, wind_max_ms (not stored) | mm/day, m/s |

Scores are 0-100; utilities, similarities and confidence scores 0-1; distances km.

## Meaning of NaN, null and sentinels

| where | marker | meaning |
|---|---|---|
| `v.<column>` float32 | NaN | the input table has no value for that cell (e.g. no land surface temperature in Antarctica, no slope where a cell has no land DEM pixel) |
| `v.<column>` int32 (category) | -2147483648 | no class for that cell (e.g. Earth permafrost south of the map) |
| `u.<v>` | sentinel | the Earth cell has no value for `v`: the weight drops out of suitability (`missing_n` counts them) |
| `s.<v>`, `similarity`, `final` | sentinel | no value on one of the two cells, or no twin |
| `twin`, `rank`, `confidence` | sentinel | no twin (then no final and no rank), or no weighted variable with data |
| `country`, `region`, `label_rule`, `nearest_place` | sentinel | no label (region: the nearest place is too far or in another country) |
| JSON | `null` | missing |

`0` is always a real value.

## Appendix: bundle v1 (legacy 2-degree build, not shipped)

`python -m engine build --dataset legacy_2deg` writes this format to `build/legacy_2deg/` (outside `app/public`), for before-and-after comparison. It is the format of `app/public/data/v1/`, the last legacy bundle, whose content a fresh legacy build reproduces byte for byte except `manifest.json` (engine version and config hashes; `test_published_bundle_matches_a_fresh_build`). Its machine check is `engine/contract.py` (`validate_bundle_dir`). The text below is the v1 contract unchanged, except that the v1 manifest's `config_sha256` now also lists `datasets.json`.

The engine (`tierra luna/engine`, command `python -m engine build` run from `tierra luna/`) writes a static, versioned bundle to `app/public/data/v1/`. The browser app reads it with plain `fetch()`; no server is needed. The machine check of this contract is `engine/contract.py` (`validate_bundle_dir`), run by the tests.

### General rules

- **Encoding.** UTF-8 JSON, compact (no spaces), keys in a fixed order. Two builds from the same inputs are byte-identical.
- **Version.** `bundle_version` is `"v1"` in every file. It is also the folder name. An incompatible change goes to `v2`.
- **null means missing.** A missing value is `null`. It is never `0` and never a default. A `null` score means the cell has no score for that mission. On Earth ocean cells (`land = 0`) the cached bands are constant fills, not values, so they are `null` too (see `ocean_fill`).
- **Cell ids.** The grid has 90 rows and 180 columns of 2-degree cells, for each body.
  - `id = row * 180 + col` (0..16199).
  - Earth and Moon ids are separate namespaces.
  - Cell centre: `lat = 90 - (row + 0.5) * 2` and `lon = -180 + (col + 0.5) * 2`, in degrees, longitude positive east, -180..180.
  - Cell arrays are sorted by id. With the full grid, the array position equals the id.
- **Real cell size.**
  - Earth: 222.4 km north-south; east-west it is 222.4 km x cos(lat).
  - Moon: 60.6 km north-south.
  - The CSV column `resolution_m = 500` is wrong; ignore it.
- **Rounding** (engine_config.json `export_decimals`):
  - scores 2 decimals; utilities 6; per-variable similarities 6; scales 6; weights 6;
  - variable values 1 to 4 decimals depending on the variable; coordinates 3; IAU feature coordinates 4; diameters 2.
  - The engine computes suitability, similarity and the final score **from the published utilities and similarities**, and the rank from the **published final**, so the bundle is self-consistent (see "Formulas the browser must use").
- **Text from team files** (gate `source`, weight `why`, mission `description`, category names such as `roca`, `suelo`, `continuo`) is copied verbatim, in Spanish where the team wrote Spanish.

### Units

| variable | unit | | variable | unit |
|---|---|---|---|---|
| elevation_m, elevation_rel_m, roughness_m, rough_300m_m | m | | irradiance_kwh_m2_day | kWh/m2/day |
| slope_deg, slope_300m_deg, sun_elev_max_deg | deg | | temp_k, lst_diurnal_amp_k | K |
| tmin_c | degC | | rock_or_bare_frac, mask_fraction, sun_low_frac_0_5deg | fraction 0-1 |
| sar_sigma0_db | dB | | rain_mm_day | mm/day |
| wind_max_ms | m/s | | thermal_inertia_class, permafrost_class | category |

Scores (`suitability`, `similarity`, `final`) are 0-100. Utilities and per-variable similarities are 0-1. Distances are in km.

### Files

#### manifest.json

```json
{"bundle_version":"v1","engine_version":"1.1.0","build_time":"input-sha256:572b6ca64950ada9",
 "input":{"file":"earth_moon_harmonized_clean.csv","sha256":"572b6c...","rows":32400},
 "config_sha256":{"mission_scoring.json":"...","engine_config.json":"...","provenance.json":"...","iau_moon_nomenclature.csv":"...","ne_110m_admin_0_countries.geojson":"..."},
 "grid":{"rows":90,"cols":180,"cell_deg":2.0,"cell_id":"row * 180 + col","lat_center":"...","lon_center":"...",
         "bodies":{"EARTH":{"radius_km":6371.0,"cell_ns_km":222.4,"cell_ew_km_at_equator":222.4,"cell_ew_km_rule":"cell_ns_km * cos(latitude)"},
                   "MOON":{"radius_km":1737.4,"cell_ns_km":60.6,...}},"note":"..."},
 "counts":{"EARTH":{"cells":16200,"land":5927,"invalid_records":0},"MOON":{"cells":16200,"invalid_records":0},
           "missions":{"rover":{"pass_EARTH":5297,"pass_MOON":9062,"ranked_EARTH":5297},...},
           "pass_all_missions":{"EARTH":1728,"MOON":1191},"lunar_features_for_labels":2023},
 "files":[{"name":"missions.json","bytes":16772,"sha256":"..."}, ...],
 "credits":["..."]}
```

- `build_time` holds the `--build-time` text if one was passed. Otherwise it is `input-sha256:` followed by the first 16 hex digits of the input hash. No clock is read.
- `files` lists every other file with its size and sha256. The manifest does not list itself.

#### missions.json

```json
{"bundle_version":"v1","config_version":"v1-draft","config_note":"...","twin_rule":"...",
 "missions":[{
   "id":"ice","title":"Ice prospecting and drilling","description":"Perforacion y prospeccion de hielo (solo si sobra tiempo)",
   "author":"ISRU & Cryosphere Prospecting Team","provisional":true,"provisional_note":"Gate migrado tal cual; ...",
   "frozen_at":"2026-11-14T16:30:00+00:00","on_missing_gate":"drop","require_present":["permafrost_class"],
   "gates":[{"variable":"elevation_m","origin":"common","applies_to":["EARTH"],"min":1.0,"max":null,"max_from":null,
             "allow":null,"exclude":null,"source":"solo tierra firme (...)"}, ...],
   "weighted_variables":[{"variable":"temp_k","kind":"numeric","label":"Surface temperature","unit":"K","weight":0.55,
             "bad":280.0,"good":220.0,"map":null,"default":null,"why":"mas frio = hielo mas estable","in_similarity":true,
             "similarity_exclusion":null},
             {"variable":"permafrost_class","kind":"categorical",...,"map":{"continuo":1.0,"discontinuo":0.85,"esporadico":0.7},"default":0.55,
              "in_similarity":false,"similarity_exclusion":"not the same quantity on both bodies: ..."}],
   "reason_codes":["elevation_m:below_min","mask_fraction:below_min","permafrost_class:excluded"],
   "pass_counts":{"EARTH":3023,"MOON":4680},"ranked_count":3023,"passing_without_twin":0,
   "top_failure_reasons":{"EARTH":[{"reason":"permafrost_class:excluded","cells":13177},...],
                          "EARTH_LAND":[{"reason":"permafrost_class:excluded","cells":2904}],
                          "MOON":[{"reason":"permafrost_class:excluded","cells":11520}]},
   "mix_factor":0.5,
   "similarity_scales":{"temp_k":{"kind":"numeric","scale":213.19516,"p_low":56.59745,"p_high":269.79261,"n_cells":7703}},
   "confidence_counts":{"high":0,"medium":0,"low":3023},
   "excluded_from_similarity":{"permafrost_class":"not the same quantity on both bodies: ..."},
   "known_limitations":["Provisional team block. permafrost_class has no lunar equivalent ..."],
   "facts":{"moon_pass_abs_lat_max":89.0,"distinct_twins":1,
            "twins":[{"id":2253,"lat":65.0,"lon":7.0,"feature":"W  Bond","earth_cells":3023}],
            "twin_abs_lat_range":[65.0,65.0],"top_n":25,"top_n_country_counts":{"AQ":25},"confidence_constant":true},
   "not_used_by_engine":{"tolerances":null,"workable_days":null,"domain_weights":{...},"why":"..."}}]}
```

Field notes:

- **`gates`.**
  - `applies_to` gives the bodies a gate is applied on. The common `elevation_m` land mask applies to EARTH only.
  - `origin` is `common` or `mission`. A mission gate on the same variable replaces the common one.
- **`reason_codes`.** Each code is `<variable>:<kind>`, where kind is one of:
  - `missing`: no value;
  - `below_min` or `above_max`;
  - `not_allowed`: the category is not in `allow`;
  - `excluded`: the category is in `exclude`.
- **`top_failure_reasons.EARTH_LAND`.** Counts over the 5,927 land cells only. The 10,273 ocean cells are a constant fill and fail the land gate.
- **`similarity_scales`.** The scale for each numeric similarity variable was computed at build time. It is the 5th-95th percentile range, pooled over the passing cells of both bodies.
- **`excluded_from_similarity`** and `weighted_variables[].similarity_exclusion`. Weighted variables left out of the Earth-Moon similarity and the twin search, with the reason (usually: not the same physical quantity on both bodies, from `variables.json` `comparable_across_bodies`). They still count in suitability. They never appear in `passing.sim`.
- **`known_limitations`.** Plain-language notes on what the results of this mission can and cannot show (from `engine_config.json` `mission_notes`). The app should show them next to the ranking.
- **`facts`.** Numbers computed at build time that the notes refer to: `moon_pass_abs_lat_max` (most poleward passing lunar cell, null if none), `distinct_twins`, `twins` (up to 5 commonest twins with how many Earth cells chose each), `twin_abs_lat_range`, `top_n_country_counts` (countries of the top `top_n` ranked cells), and `confidence_constant` (true when every ranked cell has the same confidence score: show it once per mission, not per cell).

#### variables.json

```json
{"levels":{"MEASURED":"...","DERIVED":"...","MODELLED":"...","UNDOCUMENTED":"..."},
 "variables":[{"name":"elevation_m","label":"Elevation","unit":"m","kind":"numeric","description":"...","categories":null,
   "range_source":"...","bodies":{
     "EARTH":{"level":"UNDOCUMENTED","audit_level":"NOT DETERMINED (land) / MODELLED fill (ocean)","level_note":null,"caveat":"...",
              "claimed_source":"...","code":"earth_extractor.py:137-152 ...","resolution_km":222.4,"valid_min":-500.0,"valid_max":9000.0},
     "MOON":{"level":"MEASURED",...,"resolution_km":60.6,...}},
   "comparable_across_bodies":true,"comparability_note":"..."}, ...]}
```

- The app must show `level` and `caveat` next to every value.
- Only `MEASURED` may be presented as measured.
- `level_note` (or null) explains a level that differs from the audit's text: a DERIVED value computed from an UNDOCUMENTED input takes the weaker level.
- `comparable_across_bodies` is false when the variable is not the same physical quantity on Earth and on the Moon; `comparability_note` says why (or gives the caveat when it is comparable).

#### earth_cells.json and moon_cells.json (column-oriented)

The `//` comments below are annotations for this document; they do not appear in the files.

```json
{"bundle_version":"v1","body":"EARTH","count":16200,
 "id":[0,1,...],"lat":[89.0,...],"lon":[-179.0,...],
 "land":[0,0,...],                                  // EARTH only: 1 = passes the land gate elevation_m >= 1
 "invalid_fields":{},                               // {"<id>":["field",...]} cells that failed validation
 "values":{"elevation_m":[null,...],...,"thermal_inertia_class":["agua",...],...},   // all 19 variables, null = missing
 "ocean_fill":{"cells":"...","rule":"land == 0","cell_count":10273,"variables":["elevation_m",...],  // EARTH only
               "fill_values_in_input":{"elevation_m":-250.0,...},"why":"..."},
 "place":{"country_code":[null,...],"country":[...],"region":[...],"nearest_place":[...],"nearest_place_km":[...],"label_rule":[...]},
 "missions":{"ice":{
    "reason_codes":["elevation_m:below_min","mask_fraction:below_min","permafrost_class:excluded"],
    "pass":[0,0,...],                               // one per cell
    "fail":[[0,1,2],[0,1,2],...,null,...],          // indexes into reason_codes; null when the cell passes
    "passing":{                                     // EARTH only; arrays aligned with passing.id
      "id":[589,590,...],
      "u":{"temp_k":[0.467373,...],"permafrost_class":[1.0,...]},  // utilities, null = missing variable
      "suitability":[70.71,...],"missing_n":[0,...],
      "twin":[2253,...],                            // lunar cell id; null = no twin (then final and rank are null)
      "sim":{"temp_k":[0.231446,...]},              // per-variable similarity to the twin (similarity variables only)
      "similarity":[23.14,...],"final":[46.93,...],"rank":[1587,...],
      "confidence":["low",...],"confidence_score":[0.255,...]}}}}       // null when no weighted variable has data
```

`moon_cells.json` has the same layout, with these differences:

- `feature` replaces `place`: `{"name","type","diameter_km","distance_km"}`, the nearest IAU-named feature that is not a satellite feature.
- There is no `land` array.
- Each mission has `twin_of_count` (one per lunar cell: how many Earth cells chose it as their twin) and no `passing` block.

A cell that fails a mission's hard filters:

- has `pass = 0` and a non-null `fail` list;
- is absent from `passing`, so it has no suitability, twin, similarity, final score or rank;
- never appears in any ranking.

Earth place labels:

- `label_rule` says how the country was found:
  - `"natural_earth_polygon"`: the Natural Earth 1:110m admin-0 polygon containing the cell centre;
  - `"natural_earth_polygon_geonames_code"`: inside a polygon without an ISO code in that file (France, Norway, ...): name from the polygon, code from the nearest GeoNames place;
  - `"nearest_geonames_place"`: the centre is outside every 110m polygon; country of the nearest GeoNames populated place;
  - `"antarctic_treaty_area"`: land cells at or south of 60 S get `AQ / Antarctica` and a `null` region.
- `region` is the nearest GeoNames place's first-level region, only when that place is in the same country and within `region_max_place_km` of the centre; otherwise `null`.
- Ocean cells have `null` labels.
- `nearest_place_km` says how far away the named place is. A large distance means the label is approximate.

#### explain.json

```json
{"bundle_version":"v1","top_n":25,"missions":{"ice":[{
  "rank":1,"id":15092,"lat":-77.0,"lon":125.0,
  "place":{"country_code":"AQ","country":"Antarctica","region":null,"nearest_place":"Geeveston","nearest_place_km":3896.2},
  "twin":{"id":2253,"lat":65.0,"lon":7.0,"feature":{"name":"W  Bond","type":"Crater, craters","diameter_km":170.53,"distance_km":45.9}},
  "suitability":100.0,"similarity":39.37,"final":69.69,"confidence":"low","confidence_score":0.255,"missing_n":0,
  "variables":[{"variable":"temp_k","earth":217.36,"moon":88.11,"difference":129.25,"utility":1.0,"similarity":0.393739,
                "weight":0.55,"suitability_weight":0.55,"similarity_weight":1.0,"suitability_points":55.0,
                "similarity_points":39.37,"final_points":47.19,"lost_points":30.31}, ...],
  "helps_most":["temp_k","permafrost_class"],"hurts_most":["temp_k"]}]}}
```

Each per-variable entry is defined as follows:

- `difference` is earth minus moon, in the variable's unit; it is `null` for categories.
- `suitability_points` add up to `suitability`, and `similarity_points` add up to `similarity` (up to rounding).
- `final_points = a * similarity_points + (1 - a) * suitability_points`.
- `lost_points` is the share of the final score lost on that variable.

`helps_most` names the `explain_helps_n` (2) variables with the largest `final_points`; `hurts_most` names the `explain_hurts_n` (2) with the largest `lost_points` (only when above 0). `confidence` and `confidence_score` are null when no weighted variable has data.

#### iau_moon_features.json

```json
{"credit":"Gazetteer of Planetary Nomenclature, IAU WGPSN and USGS Astrogeology Science Center","source":{...},
 "excluded_types":["Satellite Feature"],"longitude_convention":"-180..180 degrees, positive east (...)","count":2023,
 "name":["8 Homeward",...],"type":["Crater, craters",...],"lat":[-12.0249,...],"lon":[97.0932,...],"diameter_km":[12.52,...]}
```

#### validity.json

```json
{"valid":true,"bodies":{"EARTH":{"body":"EARTH","records":16200,"failing_records":0,"field_failures":{},"failures":[],"duplicate_ids":[]},"MOON":{...}}}
```

- Each failure is `{"id","field","value","reason"}`.
- Values are never fixed. A failing cell is listed here and in that body's `invalid_fields`.

### Formulas the browser must use (slider weights)

Notation for one mission and one passing Earth cell:

- `V`: the mission's weighted variables (`weighted_variables`).
- `w_v`: the slider weights. The defaults are `weighted_variables[].weight`.
- `u_v`: `passing.u[v][k]`.
- `s_v`: `passing.sim[v][k]`.
- `a`: `mix_factor` (0.5).

```
U = { v in V : u_v != null }
S = { v in V : v in passing.sim and s_v != null }

suitability = 100 * sum_{v in U} w_v * u_v / sum_{v in U} w_v          (null if the denominator is 0)
similarity  = 100 * sum_{v in S} w_v * s_v / sum_{v in S} w_v          (null if the denominator is 0)
final       = a * similarity + (1 - a) * suitability                    (null if either is null; unrounded inputs)
rank        = order by round(final, 2) descending, ties by id ascending, starting at 1
```

Sum in the order of `weighted_variables` (each sum starts at 0 and adds `w_v * u_v`, then divide `100 * num` by `den`). Round only for display and for the rank, never before computing `final`.

- The twin is fixed at build time, chosen with the JSON weights. Moving a slider re-scores each cell against the same twin; it does not search for a new twin.
- Cells that fail the mission are never scored or ranked, whatever the weights.
- With the default weights, these formulas reproduce the exported values exactly: the engine computes `suitability`, `similarity` and `final` from the same published `u` and `s` with the same arithmetic, and ranks on the published 2-decimal `final`. So `round(suitability, 2)`, `round(similarity, 2)` and `round(final, 2)` equal the stored values, and ranking by the rule above gives the stored `rank`. The test `test_browser_recompute_matches_engine` checks this for every passing cell, and `engine/contract.py` checks that the stored rank follows the rule on the stored `final`.
- Rounding: the stored values use Python's `round` (correctly rounded, half to even on the exact binary value). JavaScript's `toFixed` or `Math.round(x * 100) / 100` can differ on a value that sits on a half. Such a difference can only swap the ranks of cells whose finals differ by less than 0.01.

How the build-time quantities are computed (for display only; the browser does not recompute them):

```
numeric utility      u = clip((value - bad) / (good - bad), 0, 1)
categorical utility  u = map[class], or default for a class not in the map
numeric similarity   s = max(0, 1 - |earth - moon| / scale)   (scale from similarity_scales; if scale = 0: 1 when equal, else 0)
categorical sim.     s = 1 if earth == moon else 0
similarity variables = weighted variables minus excluded_from_similarity
twin                 = lunar cell passing the same mission with the highest similarity (default weights), ties -> lowest id
```

Confidence uses `engine_config.json` `confidence`:

- `score = min(Earth level score, Moon level score) * coverage`.
- The label is "high" only when the score is at least `high_min` **and** the cell is at most `high_max_cell_km`. No 2-degree cell meets that size condition.
- Confidence is fixed at build time.
