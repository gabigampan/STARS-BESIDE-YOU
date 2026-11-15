"""Full build: read a dataset and the configs, compute everything, serialise the bundle.

The dataset (engine/datasets.json) sets the input tables, grid, provenance, column
aliases and the bundle format: v1 (JSON, the legacy table) or v2 (JSON metadata and
binary typed arrays, the real tables).
"""
from __future__ import annotations

import json
import os
from typing import Dict, Optional

import numpy as np

from engine import schema
from engine.config import (DATASETS_PATH, Setting, ENGINE_CONFIG_PATH, ENGINE_DIR, load_engine_config, load_mission_config,
                           resolve_path, sha256_bytes, sha256_file)
from engine.dataset import Dataset, load_dataset, provenance_files
from engine.export import (build_cells, build_explain, build_iau_features, build_manifest, build_missions,
                           build_variables, dumps, land_mask, write_bundle)
from engine.pipeline import run_all
from engine.places import earth_places, load_country_polygons, load_lunar_features, nearest_lunar_feature

IAU_SOURCE_JSON = os.path.join(ENGINE_DIR, "data", "iau_source.json")


def earth_land(ds: Dataset, mission_cfg: Dict, engine_cfg) -> np.ndarray:
    """Earth land cells of the dataset (descriptor setting earth_land_cells)."""
    rule = engine_cfg.v("earth_land_cells")
    earth = ds.cells["EARTH"]
    if rule["rule"] == "common_gate":
        return land_mask(earth, {"common_gates": {rule["variable"]: mission_cfg["common_gates"][rule["variable"]]}})
    if rule["rule"] == "positive":
        v = earth[rule["variable"]].to_numpy(dtype=np.float64)
        return np.isfinite(v) & (v > 0)
    raise ValueError(f"unknown earth_land_cells rule {rule['rule']!r}")


def compute(dataset: Optional[str] = None, input_paths: Optional[Dict[str, str]] = None,
            engine_config_path: Optional[str] = None, mission_config_path: Optional[str] = None,
            similarity_rule: Optional[str] = None) -> Dict:
    """Load a dataset and run every mission. Returns the pieces both formats need.

    ``similarity_rule`` overrides engine_config similarity_rule for this run only (used
    to build the unshipped zone_twin preview bundle); the manifest records the rule used."""
    ecfg = load_engine_config(engine_config_path, dataset)
    if similarity_rule is not None:
        ecfg.similarity_rule = Setting(value=similarity_rule,
                                       why=f"command-line override of engine_config similarity_rule ({ecfg.similarity_rule.value!r}) for this build only")
    mpath = mission_config_path or resolve_path(ecfg.v("mission_config"))
    mcfg = load_mission_config(mpath)
    ds = load_dataset(ecfg, input_paths)
    if ecfg.v("on_invalid_value") != "report":
        raise ValueError("only on_invalid_value = 'report' is implemented (never fix silently)")
    validity = schema.validate_table(ds.cells, ds.reg, float(ecfg.v("coordinate_tolerance_deg")), ds.grid)
    radii = ecfg.v("body_radius_km")
    earth, moon = ds.cells["EARTH"], ds.cells["MOON"]
    land = earth_land(ds, mcfg, ecfg)
    polygons = load_country_polygons(resolve_path(ecfg.v("earth_country_polygons")))
    e_places = earth_places(earth["lat_deg"].to_numpy(), earth["lon_deg"].to_numpy(), land,
                            float(ecfg.v("antarctic_label_lat_max")), radii["EARTH"], polygons,
                            float(ecfg.v("region_max_place_km")))
    feats = load_lunar_features(resolve_path(ecfg.v("lunar_gazetteer_csv")), ecfg.v("lunar_feature_exclude_types"))
    m_feat = nearest_lunar_feature(moon["lat_deg"].to_numpy(), moon["lon_deg"].to_numpy(), feats, radii["MOON"])
    results = run_all(ds.cells, mcfg, ecfg, ds.reg)
    with open(IAU_SOURCE_JSON, encoding="utf-8") as fh:
        iau_source = json.load(fh)
    cfg_hashes = {
        "mission_scoring.json": sha256_file(mpath),
        "engine_config.json": sha256_file(engine_config_path or ENGINE_CONFIG_PATH),
        "datasets.json": sha256_file(DATASETS_PATH),
        **{name: sha256_file(p) for name, p in provenance_files(ecfg).items()},
        "iau_moon_nomenclature.csv": sha256_file(resolve_path(ecfg.v("lunar_gazetteer_csv"))),
        "ne_110m_admin_0_countries.geojson": sha256_file(resolve_path(ecfg.v("earth_country_polygons"))),
    }
    if ecfg.v("lunar_regions"):
        texts = resolve_path(ecfg.v("lunar_regions")["texts_file"])
        if os.path.exists(texts):
            cfg_hashes[os.path.basename(texts)] = sha256_file(texts)
    regions = resolve_path(ecfg.v("similarity_zones")["lunar_base"]["regions_file"])
    if os.path.exists(regions):
        cfg_hashes[os.path.basename(regions)] = sha256_file(regions)
    return {"engine_cfg": ecfg, "mission_cfg": mcfg, "dataset": ds, "cells": ds.cells, "registry": ds.reg,
            "validity": validity, "land": land, "earth_places": e_places, "features": feats, "moon_features": m_feat,
            "results": results, "iau_source": iau_source, "config_sha256": cfg_hashes}


def _build_v1(c: Dict, build_time: Optional[str]) -> Dict:
    ecfg, mcfg, reg, cells = c["engine_cfg"], c["mission_cfg"], c["registry"], c["cells"]
    ds: Dataset = c["dataset"]
    results, land, validity = c["results"], c["land"], c["validity"]
    earth, moon = cells["EARTH"], cells["MOON"]
    objs = {
        "missions.json": build_missions(results, mcfg, ecfg, reg, land, cells, c["moon_features"], c["earth_places"]),
        "variables.json": build_variables(reg),
        "earth_cells.json": build_cells("EARTH", earth, results, ecfg, reg, c["earth_places"],
                                        schema.invalid_fields_by_id(validity["bodies"]["EARTH"]), land),
        "moon_cells.json": build_cells("MOON", moon, results, ecfg, reg, c["moon_features"],
                                       schema.invalid_fields_by_id(validity["bodies"]["MOON"]), None),
        "explain.json": build_explain(results, cells, mcfg, ecfg, reg, c["earth_places"], c["moon_features"]),
        "iau_moon_features.json": build_iau_features(c["features"], ecfg, c["iau_source"]),
        "validity.json": validity,
    }
    files = {name: dumps(obj) for name, obj in objs.items()}
    if len(ds.inputs) == 1:
        input_info = {k: ds.inputs[0][k] for k in ("file", "sha256", "rows")}
    else:
        input_info = {"files": ds.inputs}
    all_e = np.logical_and.reduce([r.earth_gates.passed for r in results.values()])
    all_m = np.logical_and.reduce([r.moon_gates.passed for r in results.values()])
    counts = {
        "EARTH": {"cells": int(len(earth)), "land": int(land.sum()),
                  "invalid_records": validity["bodies"]["EARTH"]["failing_records"]},
        "MOON": {"cells": int(len(moon)), "invalid_records": validity["bodies"]["MOON"]["failing_records"]},
        "missions": {m: {"pass_EARTH": int(r.earth_gates.passed.sum()), "pass_MOON": int(r.moon_gates.passed.sum()),
                         "ranked_EARTH": int((r.rank > 0).sum())} for m, r in results.items()},
        "pass_all_missions": {"EARTH": int(all_e.sum()), "MOON": int(all_m.sum())},
        "lunar_features_for_labels": int(len(c["features"])),
    }
    bt = build_time if build_time else f"input-sha256:{ds.inputs[0]['sha256'][:16]}"
    manifest = build_manifest(files, ecfg, input_info, c["config_sha256"], counts, bt, ds.grid)
    files["manifest.json"] = dumps(manifest)
    return {"files": files, "objects": objs, "manifest": manifest}


def _build_v2(c: Dict, build_time: Optional[str]) -> Dict:
    from engine.export_v2 import build_v2_files

    ds: Dataset = c["dataset"]
    joined = "".join(i["sha256"] for i in ds.inputs)
    bt = build_time if build_time else f"inputs-sha256:{sha256_bytes(joined.encode())[:16]}"
    files, objs, manifest = build_v2_files(ds, c["results"], c["mission_cfg"], c["engine_cfg"], c["land"],
                                           c["earth_places"], c["moon_features"], c["features"], c["iau_source"],
                                           c["validity"], c["config_sha256"], bt)
    return {"files": files, "objects": objs, "manifest": manifest}


def build_bundle(dataset: Optional[str] = None, input_csv: Optional[str] = None, build_time: Optional[str] = None,
                 engine_config_path: Optional[str] = None, mission_config_path: Optional[str] = None,
                 input_paths: Optional[Dict[str, str]] = None, bundle_format: Optional[str] = None,
                 similarity_rule: Optional[str] = None) -> Dict:
    """Compute the bundle of a dataset (default: datasets.json default_dataset).

    ``input_csv`` replaces a one-file dataset's input; ``input_paths`` ({"ALL" | body: path})
    replaces any dataset's inputs. ``bundle_format`` overrides the descriptor's format.
    Returns {"files": {name: bytes}, "objects", "manifest", "results", "cells", ...}.
    """
    if input_csv is not None:
        input_paths = {"ALL": input_csv}
    c = compute(dataset, input_paths, engine_config_path, mission_config_path, similarity_rule)
    fmt = bundle_format or c["engine_cfg"].v("bundle_format")
    if fmt == "v1":
        out = _build_v1(c, build_time)
    elif fmt == "v2":
        out = _build_v2(c, build_time)
    else:
        raise ValueError(f"unknown bundle format {fmt!r}")
    c.update(out)
    c["bundle_format"] = fmt
    return c


def build_and_write(out_dir: Optional[str] = None, **kw) -> Dict:
    """Build and write the bundle to ``out_dir`` (default: the dataset's output_dir)."""
    b = build_bundle(**kw)
    out = out_dir or resolve_path(b["engine_cfg"].v("output_dir"))
    b["paths"] = write_bundle(b["files"], out)
    b["out_dir"] = out
    return b
