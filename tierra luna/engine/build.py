"""Full build: read the table and configs, compute everything, serialise the bundle."""
from __future__ import annotations

import json
import os
from typing import Dict, Optional

import numpy as np

from engine import provenance, schema
from engine.config import (ENGINE_CONFIG_PATH, ENGINE_DIR, PROVENANCE_PATH, load_engine_config,
                           load_mission_config, resolve_path, sha256_file)
from engine.export import (build_cells, build_explain, build_iau_features, build_manifest, build_missions,
                           build_variables, dumps, land_mask, write_bundle)
from engine.pipeline import run_all
from engine.places import earth_places, load_country_polygons, load_lunar_features, nearest_lunar_feature
from engine.table import load_cells

IAU_SOURCE_JSON = os.path.join(ENGINE_DIR, "data", "iau_source.json")


def build_bundle(input_csv: Optional[str] = None, build_time: Optional[str] = None,
                 engine_config_path: Optional[str] = None, mission_config_path: Optional[str] = None) -> Dict:
    """Compute the bundle. Returns {"files": {name: bytes}, "results": ..., "cells": ...}."""
    ecfg = load_engine_config(engine_config_path)
    mpath = mission_config_path or resolve_path(ecfg.v("mission_config"))
    mcfg = load_mission_config(mpath)
    reg = provenance.load_registry()
    csv_path = input_csv or resolve_path(ecfg.v("input_csv"))
    cells = load_cells(csv_path)

    validity = schema.validate_table(cells, reg, float(ecfg.v("coordinate_tolerance_deg")))
    if ecfg.v("on_invalid_value") != "report":
        raise ValueError("only on_invalid_value = 'report' is implemented (never fix silently)")

    radii = ecfg.v("body_radius_km")
    earth, moon = cells["EARTH"], cells["MOON"]
    land = land_mask(earth, mcfg)
    polygons = load_country_polygons(resolve_path(ecfg.v("earth_country_polygons")))
    e_places = earth_places(earth["lat_deg"].to_numpy(), earth["lon_deg"].to_numpy(), land,
                            float(ecfg.v("antarctic_label_lat_max")), radii["EARTH"], polygons,
                            float(ecfg.v("region_max_place_km")))
    feats = load_lunar_features(resolve_path(ecfg.v("lunar_gazetteer_csv")), ecfg.v("lunar_feature_exclude_types"))
    m_feat = nearest_lunar_feature(moon["lat_deg"].to_numpy(), moon["lon_deg"].to_numpy(), feats, radii["MOON"])

    results = run_all(cells, mcfg, ecfg, reg)

    with open(IAU_SOURCE_JSON, encoding="utf-8") as fh:
        iau_source = json.load(fh)
    objs = {
        "missions.json": build_missions(results, mcfg, ecfg, reg, land, cells, m_feat, e_places),
        "variables.json": build_variables(reg),
        "earth_cells.json": build_cells("EARTH", earth, results, ecfg, reg, e_places,
                                        schema.invalid_fields_by_id(validity["bodies"]["EARTH"]), land),
        "moon_cells.json": build_cells("MOON", moon, results, ecfg, reg, m_feat,
                                       schema.invalid_fields_by_id(validity["bodies"]["MOON"]), None),
        "explain.json": build_explain(results, cells, mcfg, ecfg, reg, e_places, m_feat),
        "iau_moon_features.json": build_iau_features(feats, ecfg, iau_source),
        "validity.json": validity,
    }
    files = {name: dumps(obj) for name, obj in objs.items()}

    in_hash = sha256_file(csv_path)
    input_info = {"file": os.path.basename(csv_path), "sha256": in_hash,
                  "rows": int(len(earth) + len(moon))}
    cfg_hashes = {
        "mission_scoring.json": sha256_file(mpath),
        "engine_config.json": sha256_file(engine_config_path or ENGINE_CONFIG_PATH),
        "provenance.json": sha256_file(PROVENANCE_PATH),
        "iau_moon_nomenclature.csv": sha256_file(resolve_path(ecfg.v("lunar_gazetteer_csv"))),
        "ne_110m_admin_0_countries.geojson": sha256_file(resolve_path(ecfg.v("earth_country_polygons"))),
    }
    all_e = np.logical_and.reduce([r.earth_gates.passed for r in results.values()])
    all_m = np.logical_and.reduce([r.moon_gates.passed for r in results.values()])
    counts = {
        "EARTH": {"cells": int(len(earth)), "land": int(land.sum()),
                  "invalid_records": validity["bodies"]["EARTH"]["failing_records"]},
        "MOON": {"cells": int(len(moon)), "invalid_records": validity["bodies"]["MOON"]["failing_records"]},
        "missions": {m: {"pass_EARTH": int(r.earth_gates.passed.sum()), "pass_MOON": int(r.moon_gates.passed.sum()),
                         "ranked_EARTH": int((r.rank > 0).sum())} for m, r in results.items()},
        "pass_all_missions": {"EARTH": int(all_e.sum()), "MOON": int(all_m.sum())},
        "lunar_features_for_labels": int(len(feats)),
    }
    bt = build_time if build_time else f"input-sha256:{in_hash[:16]}"
    manifest = build_manifest(files, ecfg, input_info, cfg_hashes, counts, bt)
    files["manifest.json"] = dumps(manifest)
    return {"files": files, "results": results, "cells": cells, "objects": objs, "manifest": manifest,
            "earth_places": e_places, "moon_features": m_feat, "engine_cfg": ecfg, "mission_cfg": mcfg,
            "registry": reg}


def build_and_write(out_dir: Optional[str] = None, **kw) -> Dict:
    """Build and write the bundle to ``out_dir`` (default from engine_config.json)."""
    b = build_bundle(**kw)
    out = out_dir or resolve_path(b["engine_cfg"].v("output_dir"))
    b["paths"] = write_bundle(b["files"], out)
    b["out_dir"] = out
    return b
