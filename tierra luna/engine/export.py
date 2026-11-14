"""Static, deterministic, versioned JSON bundle for the browser app.

Files (structure in docs/DATA_CONTRACT.md):
    manifest.json, missions.json, variables.json, earth_cells.json, moon_cells.json,
    explain.json, iau_moon_features.json, validity.json

Determinism: no clock is read. The build time is passed in, or else derived from the
input file's sha256. Keys keep insertion order, floats are rounded per
engine_config.json, NaN becomes null, and JSON is written compactly with
allow_nan=False. Two builds from the same inputs are byte-identical.
"""
from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

import mission_scoring
from engine import provenance
from engine.config import BODIES, CELL_DEG, GRID_COLS, GRID_ROWS, EngineConfig, sha256_bytes
from engine.explain import explain_cell
from engine.gates import GateResult, effective_gates, gate_origin, top_reasons
from engine.pipeline import MissionResult
from engine.places import cell_size_km
from engine.suitability import soft_weights

FILES_ORDER = ["missions.json", "variables.json", "earth_cells.json", "moon_cells.json",
               "explain.json", "iau_moon_features.json", "validity.json"]


# ----------------------------------------------------------------------------- helpers
def rnd(x: Any, d: int) -> Optional[float]:
    """Round to ``d`` decimals; None for missing/NaN; -0.0 becomes 0.0."""
    if x is None:
        return None
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    if not np.isfinite(v):
        return None
    r = round(v, d)
    return 0.0 if r == 0 else r


def dumps(obj: Any) -> bytes:
    """Compact, deterministic JSON bytes (UTF-8, no NaN)."""
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode("utf-8")


def _dec(engine_cfg: EngineConfig, key: str) -> int:
    d = engine_cfg.v("export_decimals")
    return int(d.get(key, d["default"]))


def _category(x: Any) -> Optional[str]:
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return None
    t = str(x).strip()
    return None if t.lower() in ("", "nan") else t


def value_column(df: pd.DataFrame, var: str, kind: str, engine_cfg: EngineConfig) -> List[Any]:
    """Export one variable column: rounded numbers or category strings, null when missing."""
    if kind == "categorical":
        return [_category(x) for x in df[var].tolist()]
    d = _dec(engine_cfg, var)
    return [rnd(x, d) for x in pd.to_numeric(df[var], errors="coerce").tolist()]


def blank_ocean_fills(values: Dict[str, List[Any]], earth: pd.DataFrame, land: np.ndarray,
                      engine_cfg: EngineConfig, reg: Dict) -> Dict[str, Any]:
    """Replace, in place, the exported values of the fill variables with null on Earth
    cells that are not land (engine_config earth_ocean_fill), and return the record of
    what was blanked: the variables, the number of cells and each variable's fill
    constant as found in the input (null if the ocean values are not one constant)."""
    spec = engine_cfg.v("earth_ocean_fill")
    ocean = np.flatnonzero(~np.asarray(land, dtype=bool))
    fills: Dict[str, Any] = {}
    for v in spec["variables"]:
        raw = earth[v].iloc[ocean]
        uniq = pd.unique(raw.dropna())
        fills[v] = (rnd(uniq[0], _dec(engine_cfg, v)) if provenance.kind(reg, v) == "numeric" else str(uniq[0])) \
            if len(uniq) == 1 and raw.notna().all() else None
        col = values[v]
        for i in ocean:
            col[i] = None
    return {"cells": spec["cells"], "rule": "land == 0", "cell_count": int(len(ocean)),
            "variables": list(spec["variables"]), "fill_values_in_input": fills,
            "why": engine_cfg.earth_ocean_fill.why}


def land_mask(earth: pd.DataFrame, mission_cfg: Dict) -> np.ndarray:
    """Earth land cells: those passing the common land gate (elevation_m) as written in
    mission_scoring.json, applied through mission_scoring.apply_gates."""
    g = mission_cfg.get("common_gates", {}).get("elevation_m")
    if g is None:
        return np.ones(len(earth), dtype=bool)
    gate = {k: v for k, v in g.items() if k != "why"}
    passed, _, _ = mission_scoring.apply_gates(earth, {"elevation_m": gate}, [], "drop")
    return np.asarray(passed, dtype=bool)


def reason_code_table(res: MissionResult) -> List[str]:
    """Sorted list of every reason code seen for a mission on either body."""
    codes = set()
    for g in (res.earth_gates, res.moon_gates):
        for r in g.reasons:
            codes.update(r)
    return sorted(codes)


# ----------------------------------------------------------------------------- files
def mission_facts(res: MissionResult, cells: Dict[str, pd.DataFrame], moon_feat: Dict[str, list],
                  earth_places: Dict[str, list], engine_cfg: EngineConfig) -> Dict[str, Any]:
    """Numbers behind each mission's known limitations, computed from the results
    (nothing typed): lunar latitude reach of passing cells, twin concentration,
    countries of the top-ranked cells and whether confidence varies across cells."""
    earth, moon = cells["EARTH"], cells["MOON"]
    ll = _dec(engine_cfg, "lat_lon")
    mlat = moon["lat_deg"].to_numpy(dtype=np.float64)
    mpass = res.moon_gates.passed
    tw = res.twin_id[res.twin_id >= 0]
    uniq, cnt = np.unique(tw, return_counts=True)
    order = sorted(range(len(uniq)), key=lambda k: (-int(cnt[k]), int(uniq[k])))
    pos = {int(i): p for p, i in enumerate(moon["id"])}
    twins_top = [{"id": int(uniq[k]), "lat": rnd(moon["lat_deg"].iat[pos[int(uniq[k])]], ll),
                  "lon": rnd(moon["lon_deg"].iat[pos[int(uniq[k])]], ll),
                  "feature": moon_feat["name"][pos[int(uniq[k])]], "earth_cells": int(cnt[k])} for k in order[:5]]
    twin_abs_lat = [abs(float(moon["lat_deg"].iat[pos[int(t)]])) for t in uniq]
    n_top = int(engine_cfg.v("explain_top_n"))
    top_idx = [i for i in np.argsort(np.where(res.rank > 0, res.rank, np.iinfo(np.int64).max), kind="mergesort")
               if res.rank[i] > 0][:n_top]
    cc: Dict[str, int] = {}
    for i in top_idx:
        key = earth_places["country_code"][i] or "null"
        cc[key] = cc.get(key, 0) + 1
    conf = res.confidence_score[res.rank > 0]
    conf = conf[np.isfinite(conf)]
    return {
        "moon_pass_abs_lat_max": rnd(float(np.max(np.abs(mlat[mpass]))), ll) if mpass.any() else None,
        "distinct_twins": int(len(uniq)),
        "twins": twins_top,
        "twin_abs_lat_range": [rnd(min(twin_abs_lat), ll), rnd(max(twin_abs_lat), ll)] if twin_abs_lat else None,
        "top_n": n_top,
        "top_n_country_counts": dict(sorted(cc.items(), key=lambda kv: (-kv[1], kv[0]))),
        "confidence_constant": bool(len(np.unique(conf)) <= 1),
    }


def build_missions(results: Dict[str, MissionResult], mission_cfg: Dict, engine_cfg: EngineConfig,
                   reg: Dict, earth_land: np.ndarray, cells: Dict[str, pd.DataFrame],
                   moon_feat: Dict[str, list], earth_places: Dict[str, list]) -> Dict:
    """missions.json content. ``earth_land`` selects Earth land cells for the land-only
    failure summary (ocean cells are a constant fill and fail the land gate anyway)."""
    titles = engine_cfg.v("mission_titles")
    notes = engine_cfg.v("mission_notes")
    n_top = int(engine_cfg.v("top_failure_reasons_n"))
    out = []
    for mid, res in results.items():
        m = mission_cfg["missions"][mid]
        gates = []
        all_gate_vars = list(dict.fromkeys(list(mission_cfg.get("common_gates", {}).keys()) + list(m.get("gates", {}).keys())))
        for var in all_gate_vars:
            applies = [b for b in BODIES if var in effective_gates(mission_cfg, mid, b, engine_cfg)]
            origin = gate_origin(mission_cfg, mid, var)
            g = m["gates"][var] if origin == "mission" else mission_cfg["common_gates"][var]
            gates.append({
                "variable": var, "origin": origin, "applies_to": applies,
                "min": g.get("min"), "max": g.get("max"), "max_from": g.get("max_from"),
                "allow": g.get("allow"), "exclude": g.get("exclude"),
                "source": g.get("source", g.get("why")),
            })
        sdec = _dec(engine_cfg, "scale")
        weighted = []
        for var, spec in m.get("soft", {}).items():
            item = {
                "variable": var, "kind": provenance.kind(reg, var),
                "label": reg["variables"][var]["label"], "unit": reg["variables"][var]["unit"],
                "weight": spec["weight"], "bad": spec.get("bad"), "good": spec.get("good"),
                "map": spec.get("map"), "default": spec.get("default"), "why": spec.get("why"),
                "in_similarity": var in res.sim_vars,
                "similarity_exclusion": res.sim_excluded.get(var),
            }
            weighted.append(item)
        scales = {}
        for var, sc in res.scales.items():
            if sc["kind"] == "numeric":
                scales[var] = {"kind": "numeric", "scale": rnd(sc["scale"], sdec), "p_low": rnd(sc["p_low"], sdec),
                               "p_high": rnd(sc["p_high"], sdec), "n_cells": sc["n"]}
            else:
                scales[var] = {"kind": "categorical", "rule": sc["rule"], "categories": sc["categories"]}
        ranked = res.rank > 0
        conf_counts = {k: int(sum(1 for c in res.confidence if c == k)) for k in ("high", "medium", "low")}
        prov = m.get("provisional")
        out.append({
            "id": mid,
            "title": titles.get(mid, mid),
            "description": m.get("description"),
            "author": m.get("author"),
            "provisional": bool(prov),
            "provisional_note": prov if prov else None,
            "frozen_at": m.get("frozen_at"),
            "on_missing_gate": mission_cfg.get("on_missing_gate"),
            "require_present": m.get("require_present", []),
            "gates": gates,
            "weighted_variables": weighted,
            "reason_codes": reason_code_table(res),
            "pass_counts": {"EARTH": int(res.earth_gates.passed.sum()), "MOON": int(res.moon_gates.passed.sum())},
            "ranked_count": int(ranked.sum()),
            "passing_without_twin": int((res.earth_gates.passed & ~ranked).sum()),
            "top_failure_reasons": {"EARTH": top_reasons(res.earth_gates, n_top),
                                    "EARTH_LAND": top_reasons(_subset(res.earth_gates, earth_land), n_top),
                                    "MOON": top_reasons(res.moon_gates, n_top)},
            "mix_factor": res.alpha,
            "similarity_scales": scales,
            "confidence_counts": conf_counts,
            "excluded_from_similarity": dict(res.sim_excluded),
            "known_limitations": list(notes.get(mid, [])),
            "facts": mission_facts(res, cells, moon_feat, earth_places, engine_cfg),
            "not_used_by_engine": {
                "tolerances": m.get("tolerances"),
                "workable_days": m.get("workable_days"),
                "domain_weights": m.get("weights"),
                "why": engine_cfg.v("not_used_by_engine_why"),
            },
        })
    return {
        "bundle_version": engine_cfg.v("bundle_version"),
        "config_version": mission_cfg.get("version"),
        "config_note": mission_cfg.get("note"),
        "twin_rule": "Each passing Earth cell's lunar twin is the lunar cell passing the same mission with the highest weighted similarity under the JSON soft weights, over the mission's similarity variables (weighted variables that are the same quantity on both bodies; see excluded_from_similarity). Ties: lowest id. Twins are fixed at build time; moving a weight slider recomputes scores against the same twin.",
        "missions": out,
    }


def _subset(g: GateResult, mask: np.ndarray) -> GateResult:
    idx = np.flatnonzero(mask)
    return GateResult(passed=g.passed[idx], reasons=[g.reasons[i] for i in idx])


def build_variables(reg: Dict) -> Dict:
    """variables.json content (from the provenance registry)."""
    out = []
    for var in provenance.variables(reg):
        e = reg["variables"][var]
        bodies = {}
        for b in BODIES:
            pb = e["bodies"][b]
            bodies[b] = {k: pb.get(k) for k in ("level", "audit_level", "level_note", "caveat", "claimed_source",
                                                  "code", "resolution_km", "valid_min", "valid_max")}
        out.append({"name": var, "label": e["label"], "unit": e["unit"], "kind": e["kind"],
                    "description": e["description"], "categories": e.get("categories"),
                    "range_source": e["range_source"],
                    "comparable_across_bodies": e["comparable_across_bodies"],
                    "comparability_note": e["comparability_note"], "bodies": bodies})
    return {"levels": reg["levels"], "variables": out}


def build_cells(body: str, df: pd.DataFrame, results: Dict[str, MissionResult], engine_cfg: EngineConfig,
                reg: Dict, places: Dict[str, list], invalid: Dict[int, List[str]],
                land: Optional[np.ndarray]) -> Dict:
    """earth_cells.json / moon_cells.json content (column-oriented)."""
    ll = _dec(engine_cfg, "lat_lon")
    dkm = _dec(engine_cfg, "distance_km")
    obj: Dict[str, Any] = {
        "bundle_version": engine_cfg.v("bundle_version"),
        "body": body,
        "count": int(len(df)),
        "id": [int(x) for x in df["id"]],
        "lat": [rnd(x, ll) for x in df["lat_deg"]],
        "lon": [rnd(x, ll) for x in df["lon_deg"]],
    }
    if land is not None:
        obj["land"] = [int(x) for x in land]
    obj["invalid_fields"] = {str(k): v for k, v in sorted(invalid.items())}
    obj["values"] = {v: value_column(df, v, provenance.kind(reg, v), engine_cfg) for v in provenance.variables(reg)}
    if body == "EARTH" and land is not None:
        obj["ocean_fill"] = blank_ocean_fills(obj["values"], df, land, engine_cfg, reg)
    if body == "EARTH":
        obj["place"] = {
            "country_code": places["country_code"], "country": places["country"], "region": places["region"],
            "nearest_place": places["nearest_place"],
            "nearest_place_km": [rnd(x, dkm) for x in places["nearest_place_km"]],
            "label_rule": places["label_rule"],
        }
    else:
        obj["feature"] = {
            "name": places["name"], "type": places["type"],
            "diameter_km": [rnd(x, _dec(engine_cfg, "diameter_km")) for x in places["diameter_km"]],
            "distance_km": [rnd(x, dkm) for x in places["distance_km"]],
        }
    ud, sd, scd, cd = (_dec(engine_cfg, k) for k in ("utility", "similarity", "score", "confidence_score"))
    missions: Dict[str, Any] = {}
    for mid, res in results.items():
        codes = reason_code_table(res)
        lut = {c: i for i, c in enumerate(codes)}
        g = res.earth_gates if body == "EARTH" else res.moon_gates
        block: Dict[str, Any] = {
            "reason_codes": codes,
            "pass": [int(x) for x in g.passed],
            "fail": [None if not r else [lut[c] for c in r] for r in g.reasons],
        }
        if body == "EARTH":
            idx = np.flatnonzero(g.passed)
            s = res.earth_suit
            block["passing"] = {
                "id": [int(df["id"].iat[i]) for i in idx],
                "u": {v: [rnd(s.utilities[v][i], ud) for i in idx] for v in res.soft_vars},
                "suitability": [rnd(s.score[i], scd) for i in idx],
                "missing_n": [int(s.missing_n[i]) for i in idx],
                "twin": [int(res.twin_id[i]) if res.twin_id[i] >= 0 else None for i in idx],
                "sim": {v: [rnd(res.sims[v][i], sd) for i in idx] for v in res.sim_vars},
                "similarity": [rnd(res.similarity_pct[i], scd) for i in idx],
                "final": [rnd(res.final_published[i], scd) for i in idx],
                "rank": [int(res.rank[i]) if res.rank[i] > 0 else None for i in idx],
                "confidence": [res.confidence[i] for i in idx],
                "confidence_score": [rnd(res.confidence_score[i], cd) for i in idx],
            }
        else:
            block["twin_of_count"] = [int(x) for x in res.moon_twin_count]
        missions[mid] = block
    obj["missions"] = missions
    return obj


def build_explain(results: Dict[str, MissionResult], cells: Dict[str, pd.DataFrame], mission_cfg: Dict,
                  engine_cfg: EngineConfig, reg: Dict, earth_places: Dict[str, list],
                  moon_feat: Dict[str, list]) -> Dict:
    """explain.json content: the top-N ranked Earth cells per mission, fully explained."""
    n = int(engine_cfg.v("explain_top_n"))
    earth, moon = cells["EARTH"], cells["MOON"]
    moon_pos = {int(i): p for p, i in enumerate(moon["id"])}
    ll, ud, sd, scd, cd, dkm = (_dec(engine_cfg, k) for k in
                                ("lat_lon", "utility", "similarity", "score", "confidence_score", "distance_km"))
    pts = _dec(engine_cfg, "score")
    out: Dict[str, Any] = {}
    for mid, res in results.items():
        order = [i for i in np.argsort(np.where(res.rank > 0, res.rank, np.iinfo(np.int64).max), kind="mergesort")
                 if res.rank[i] > 0][:n]
        weights = soft_weights(mission_cfg, mid)
        kinds = {v: provenance.kind(reg, v) for v in res.soft_vars}
        items = []
        for i in order:
            tp = moon_pos[int(res.twin_id[i])]
            ev = {v: _export_value(earth[v].iat[i], kinds[v], engine_cfg, v) for v in res.soft_vars}
            mv = {v: _export_value(moon[v].iat[tp], kinds[v], engine_cfg, v) for v in res.soft_vars}
            ex = explain_cell(res.soft_vars, kinds, ev, mv,
                              {v: res.earth_suit.utilities[v][i] for v in res.soft_vars},
                              {v: res.sims[v][i] for v in res.sim_vars}, weights, res.alpha,
                              int(engine_cfg.v("explain_helps_n")), int(engine_cfg.v("explain_hurts_n")))
            for r in ex["variables"]:
                r["difference"] = rnd(r["difference"], _dec(engine_cfg, r["variable"]))
                r["utility"] = rnd(r["utility"], ud)
                r["similarity"] = rnd(r["similarity"], sd)
                for k in ("suitability_weight", "similarity_weight"):
                    r[k] = rnd(r[k], _dec(engine_cfg, "weight"))
                for k in ("suitability_points", "similarity_points", "final_points", "lost_points"):
                    r[k] = rnd(r[k], pts)
            items.append({
                "rank": int(res.rank[i]), "id": int(earth["id"].iat[i]),
                "lat": rnd(earth["lat_deg"].iat[i], ll), "lon": rnd(earth["lon_deg"].iat[i], ll),
                "place": {k: earth_places[k][i] for k in ("country_code", "country", "region", "nearest_place")}
                | {"nearest_place_km": rnd(earth_places["nearest_place_km"][i], dkm)},
                "twin": {"id": int(res.twin_id[i]), "lat": rnd(moon["lat_deg"].iat[tp], ll),
                         "lon": rnd(moon["lon_deg"].iat[tp], ll),
                         "feature": {"name": moon_feat["name"][tp], "type": moon_feat["type"][tp],
                                     "diameter_km": rnd(moon_feat["diameter_km"][tp], _dec(engine_cfg, "diameter_km")),
                                     "distance_km": rnd(moon_feat["distance_km"][tp], dkm)}},
                "suitability": rnd(res.earth_suit.score[i], scd),
                "similarity": rnd(res.similarity_pct[i], scd),
                "final": rnd(res.final_published[i], scd),
                "confidence": res.confidence[i],
                "confidence_score": rnd(res.confidence_score[i], cd),
                "missing_n": int(res.earth_suit.missing_n[i]),
                "variables": ex["variables"],
                "helps_most": ex["helps_most"],
                "hurts_most": ex["hurts_most"],
            })
        out[mid] = items
    return {"bundle_version": engine_cfg.v("bundle_version"), "top_n": n, "missions": out}


def _export_value(x: Any, kind: str, engine_cfg: EngineConfig, var: str) -> Any:
    if kind == "categorical":
        return _category(x)
    return rnd(x, _dec(engine_cfg, var))


def build_iau_features(features: pd.DataFrame, engine_cfg: EngineConfig, source_info: Dict) -> Dict:
    """iau_moon_features.json content: map labels (column-oriented)."""
    ll = _dec(engine_cfg, "iau_lat_lon")
    dd = _dec(engine_cfg, "diameter_km")
    return {
        "credit": "Gazetteer of Planetary Nomenclature, International Astronomical Union (IAU) WGPSN and USGS Astrogeology Science Center",
        "source": source_info,
        "excluded_types": engine_cfg.v("lunar_feature_exclude_types"),
        "longitude_convention": "-180..180 degrees, positive east (converted from the gazetteer's 0-360 positive east)",
        "count": int(len(features)),
        "name": features["name"].tolist(),
        "type": features["type"].tolist(),
        "lat": [rnd(x, ll) for x in features["lat"]],
        "lon": [rnd(x, ll) for x in features["lon"]],
        "diameter_km": [rnd(x, dd) for x in features["diameter_km"]],
    }


def build_manifest(files: Dict[str, bytes], engine_cfg: EngineConfig, input_info: Dict,
                   config_hashes: Dict[str, str], counts: Dict, build_time: str) -> Dict:
    """manifest.json content."""
    radii = engine_cfg.v("body_radius_km")
    dkm = _dec(engine_cfg, "distance_km")
    grid_bodies = {b: {"radius_km": radii[b],
                       "cell_ns_km": rnd(cell_size_km(radii[b], CELL_DEG), dkm),
                       "cell_ew_km_at_equator": rnd(cell_size_km(radii[b], CELL_DEG), dkm),
                       "cell_ew_km_rule": "cell_ns_km * cos(latitude)"} for b in BODIES}
    return {
        "bundle_version": engine_cfg.v("bundle_version"),
        "engine_version": engine_cfg.v("engine_version"),
        "build_time": build_time,
        "input": input_info,
        "config_sha256": config_hashes,
        "grid": {
            "rows": GRID_ROWS, "cols": GRID_COLS, "cell_deg": CELL_DEG,
            "cell_id": "row * 180 + col",
            "lat_center": "90 - (row + 0.5) * 2",
            "lon_center": "-180 + (col + 0.5) * 2 (positive east)",
            "bodies": grid_bodies,
            "note": "The CSV column resolution_m = 500 and the x_m/y_m columns are wrong; true cell sizes are given here.",
        },
        "counts": counts,
        "files": [{"name": n, "bytes": len(files[n]), "sha256": sha256_bytes(files[n])} for n in FILES_ORDER if n in files],
        "credits": engine_cfg.v("credits"),
    }


def write_bundle(files: Dict[str, bytes], out_dir: str) -> List[str]:
    """Write every file (bytes already serialised). Returns written paths."""
    os.makedirs(out_dir, exist_ok=True)
    paths = []
    for name, data in files.items():
        p = os.path.join(out_dir, name)
        with open(p, "wb") as fh:
            fh.write(data)
        paths.append(p)
    return paths
