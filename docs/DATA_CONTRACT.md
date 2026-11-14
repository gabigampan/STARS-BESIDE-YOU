# Data contract: static bundle v1

The engine (`tierra luna/engine`, command `python -m engine build` run from `tierra luna/`) writes a static, versioned bundle to `app/public/data/v1/`. The browser app reads it with plain `fetch()`; no server is needed. The machine check of this contract is `engine/contract.py` (`validate_bundle_dir`), run by the tests.

## General rules

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

## Units

| variable | unit | | variable | unit |
|---|---|---|---|---|
| elevation_m, elevation_rel_m, roughness_m, rough_300m_m | m | | irradiance_kwh_m2_day | kWh/m2/day |
| slope_deg, slope_300m_deg, sun_elev_max_deg | deg | | temp_k, lst_diurnal_amp_k | K |
| tmin_c | degC | | rock_or_bare_frac, mask_fraction, sun_low_frac_0_5deg | fraction 0-1 |
| sar_sigma0_db | dB | | rain_mm_day | mm/day |
| wind_max_ms | m/s | | thermal_inertia_class, permafrost_class | category |

Scores (`suitability`, `similarity`, `final`) are 0-100. Utilities and per-variable similarities are 0-1. Distances are in km.

## Files

### manifest.json

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

### missions.json

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

### variables.json

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

### earth_cells.json and moon_cells.json (column-oriented)

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

### explain.json

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

### iau_moon_features.json

```json
{"credit":"Gazetteer of Planetary Nomenclature, IAU WGPSN and USGS Astrogeology Science Center","source":{...},
 "excluded_types":["Satellite Feature"],"longitude_convention":"-180..180 degrees, positive east (...)","count":2023,
 "name":["8 Homeward",...],"type":["Crater, craters",...],"lat":[-12.0249,...],"lon":[97.0932,...],"diameter_km":[12.52,...]}
```

### validity.json

```json
{"valid":true,"bodies":{"EARTH":{"body":"EARTH","records":16200,"failing_records":0,"field_failures":{},"failures":[],"duplicate_ids":[]},"MOON":{...}}}
```

- Each failure is `{"id","field","value","reason"}`.
- Values are never fixed. A failing cell is listed here and in that body's `invalid_fields`.

## Formulas the browser must use (slider weights)

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
