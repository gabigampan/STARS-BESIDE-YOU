"""Compact v2 bundle: JSON metadata plus little-endian binary typed arrays.

Files (structure in docs/DATA_CONTRACT.md):

    manifest.json               index of every file and of every binary column
    missions.json               missions, gates, weights, scales, reason codes, counts
    variables.json              per variable and body: column, level, source, licence, baseline, caveat, comparability
    places.json                 Earth country / region / label-rule tables (indexed by earth_base.bin)
    earth_base.bin              Earth land cells: id, place indexes, values
    earth_<mission>.bin         fail bits for every land cell; scores of the passing cells
    moon_base.bin               every lunar cell (position = id): values, nearest IAU feature
    moon_<mission>.bin          fail bits and twin counts for every lunar cell
    explain.json                top-N ranked Earth cells per mission, fully explained
    iau_moon_features.json      IAU feature table (indexed by moon_base.bin 'feature')
    lunar_named_sites.json      lunar sites that matter to the missions, their cell and pass flags

Binary columns are Float32 (NaN = missing) or Int32 (INT32_MIN = missing, see
engine_config binary_encoding). Published scores, utilities and similarities are
Int32 q with value = q / 10^decimals, so the browser decodes exactly the published
values the engine computed with. Deterministic: no clock is read, arrays are in id
order, JSON keys keep insertion order.
"""
from __future__ import annotations

import csv
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from engine import provenance
from engine.config import (BODIES, REAL_RULES, REPO_RULES, TWIN_RULES, EngineConfig, mission_components, resolve_path,
                           sha256_bytes, similarity_rule, similarity_rules)
from engine.dataset import Dataset
from engine.export import (_dec, _subset, build_explain, build_iau_features, dumps, mission_facts, reason_code_table,
                           rnd)
from engine.gates import GateResult, effective_gates, gate_origin, reason_step, reason_texts, top_reasons
from engine.pipeline import MissionResult
from engine.suitability import soft_weights

CONF_CODES = ["low", "medium", "high"]
MAX_REASON_BITS = 31


# ----------------------------------------------------------------------------- binary writer
class BinFile:
    """Columns of one binary file, concatenated in order (each 4-byte aligned)."""

    def __init__(self, name: str, enc: Dict):
        self.name = name
        self.enc = enc
        self.buf = bytearray()
        self.columns: List[Dict[str, Any]] = []
        self.row_sets: Dict[str, int] = {}

    def _add(self, name: str, arr: np.ndarray, typ: str, rows: str, meta: Dict) -> None:
        if rows in self.row_sets and self.row_sets[rows] != len(arr):
            raise ValueError(f"{self.name}:{name} has {len(arr)} rows, '{rows}' has {self.row_sets[rows]}")
        self.row_sets[rows] = len(arr)
        off = len(self.buf)
        self.buf += arr.tobytes()
        col = {"name": name, "type": typ, "rows": rows, "length": int(len(arr)), "offset": off}
        col.update(meta)
        self.columns.append(col)

    def f32(self, name: str, values, rows: str, **meta) -> None:
        a = np.asarray(values, dtype=np.float64).astype("<f4")
        self._add(name, a, "float32", rows, {"missing": "NaN", "scale": None, **meta})

    def i32(self, name: str, values, rows: str, missing: Optional[np.ndarray] = None, **meta) -> None:
        v = np.asarray(values)
        a = v.astype(np.int64)
        if missing is not None:
            a = np.where(missing, self.enc["int32_missing"], a)
        if a.size and (a.max() > np.iinfo(np.int32).max or a.min() < np.iinfo(np.int32).min):
            raise OverflowError(f"{self.name}:{name} does not fit in int32")
        self._add(name, a.astype("<i4"), "int32", rows, {"missing": self.enc["int32_missing"], "scale": None, **meta})

    def quantised(self, name: str, values, decimals: int, rows: str, **meta) -> None:
        """Int32 q with value = q / 10**decimals; ``values`` must already be rounded to
        ``decimals`` (the published values). Checks that decoding gives them back exactly."""
        v = np.asarray(values, dtype=np.float64)
        ok = np.isfinite(v)
        div = 10 ** decimals
        q = np.where(ok, np.rint(np.where(ok, v, 0.0) * div), 0).astype(np.int64)
        back = q[ok] / div
        if not np.array_equal(back, v[ok]):
            bad = int(np.flatnonzero(back != v[ok])[0])
            raise ValueError(f"{self.name}:{name}: {v[ok][bad]!r} is not exact at {decimals} decimals")
        self.i32(name, q, rows, missing=~ok, **{"divisor": div, "decode": "value = q / divisor", **meta})
        self.columns[-1]["scale"] = 1.0 / div

    def index(self) -> Dict[str, Any]:
        return {"row_sets": dict(self.row_sets), "columns": self.columns}



def _conf_on(engine_cfg) -> bool:
    """engine_config confidence 'export_per_pair' (revision 8: false; the label was uniform per mission)."""
    return bool((engine_cfg.v("confidence") or {}).get("export_per_pair", True))

def _round_array(values: np.ndarray, decimals: int) -> np.ndarray:
    """Python round per finite value (the published precision); NaN stays NaN."""
    a = np.asarray(values, dtype=np.float64)
    return np.array([round(float(x), decimals) if np.isfinite(x) else np.nan for x in a], dtype=np.float64)


def category_codes(values: pd.Series, categories: List[str]) -> Tuple[np.ndarray, np.ndarray]:
    """(codes into ``categories``, missing mask) for a categorical column."""
    txt = values.astype(str).str.strip()
    miss = (values.isna() | txt.str.lower().isin(["", "nan"])).to_numpy()
    lut = {c: i for i, c in enumerate(categories)}
    codes = np.array([lut.get(t, -1) if not m else 0 for t, m in zip(txt, miss)], dtype=np.int64)
    if np.any(codes < 0):
        raise KeyError("a category value is not in the registry's category list")
    return codes, miss


# ----------------------------------------------------------------------------- helpers
def engine_variables(mission_cfg: Dict, missions: List[str]) -> List[str]:
    """Variables used by a configured mission (common gates, gates, require_present, soft), in first-use order."""
    out: List[str] = list(mission_cfg.get("common_gates", {}).keys())
    for m in missions:
        spec = mission_cfg["missions"][m]
        out += list(spec.get("gates", {})) + list(spec.get("require_present", [])) + list(spec.get("soft", {}))
    return list(dict.fromkeys(out))


def variable_roles(mission_cfg: Dict, missions: List[str], var: str) -> Dict[str, List[str]]:
    """{mission: [roles]} of a variable (common_gate, gate, require_present, soft, workable_days)."""
    out: Dict[str, List[str]] = {}
    for m in missions:
        spec = mission_cfg["missions"][m]
        roles = []
        if var in mission_cfg.get("common_gates", {}):
            roles.append("common_gate")
        for key, role in (("gates", "gate"), ("require_present", "require_present"), ("soft", "soft")):
            if var in spec.get(key, {}):
                roles.append(role)
        for k in (spec.get("workable_days") or {}):
            if k.startswith(var):
                roles.append("workable_days (not read by mission_scoring.py)")
        if roles:
            out[m] = roles
    return out


def stored_columns(reg: Dict, eng_vars: List[str], raw: Dict[str, pd.DataFrame]) -> Dict[str, List[str]]:
    """Real columns stored per body: those behind engine variables that hold any value on that body."""
    out: Dict[str, List[str]] = {}
    for b in BODIES:
        cols = []
        for v in eng_vars:
            c = reg["columns"][v][b]["column"]
            s = raw[b][c]
            has = bool((s.notna() & ~s.astype(str).str.strip().str.lower().isin(["", "nan"])).any())
            if has and c not in cols:
                cols.append(c)
        out[b] = cols
    return out


def column_kind(reg: Dict, column: str, body: str) -> Tuple[str, List[str]]:
    """(kind, variables) of a real column: the registry variables read from it, in registry order."""
    vs = [v for v in reg["variables"] if reg["columns"][v][body]["column"] == column]
    if not vs:
        raise KeyError(column)
    kinds = {reg["variables"][v]["kind"] for v in vs}
    if len(kinds) != 1:
        raise ValueError(f"column {column} is read as both numeric and categorical")
    return kinds.pop(), vs


def quantiles(values: np.ndarray, decimals: int) -> Optional[Dict[str, float]]:
    """min, p05, p25, median, p75, p95, max, mean and n of the finite values (None when empty)."""
    v = np.asarray(values, dtype=np.float64)
    v = v[np.isfinite(v)]
    if v.size == 0:
        return None
    qs = np.percentile(v, [0, 5, 25, 50, 75, 95, 100])
    keys = ["min", "p05", "p25", "median", "p75", "p95", "max"]
    out = {k: rnd(x, decimals) for k, x in zip(keys, qs)}
    out["mean"] = rnd(float(v.mean()), decimals)
    out["n"] = int(v.size)
    return out


def missing_summary(g: GateResult, suffix: str) -> Dict[str, Any]:
    """How many cells fail because a gated or required value is empty."""
    by_var: Dict[str, int] = {}
    any_missing = only_missing = 0
    for r in g.reasons:
        miss = [c for c in r if c.endswith(":" + suffix)]
        if miss:
            any_missing += 1
            if len(miss) == len(r):
                only_missing += 1
        for c in miss:
            v = c.rsplit(":", 1)[0]
            by_var[v] = by_var.get(v, 0) + 1
    return {"cells_with_missing_data": any_missing, "cells_failing_only_on_missing_data": only_missing,
            "by_variable": dict(sorted(by_var.items(), key=lambda kv: (-kv[1], kv[0])))}


def reason_entries(codes: List[str], engine_cfg: EngineConfig,
                   labels: Optional[Dict[str, str]] = None) -> List[Dict[str, Any]]:
    """[{bit, code, variable, kind, label}] for a mission's reason codes. ``label`` uses
    the variable's display label when ``labels`` has one (so a mission variable name such
    as 'slope_300m_deg' never reaches a label); the variable name stays in ``variable``."""
    md = engine_cfg.v("missing_data_reason")
    text = {"below_min": "below minimum", "above_max": "above maximum", "not_allowed": "class not allowed",
            "excluded": "class excluded", md["code_suffix"]: md["label"]}
    out = []
    for i, c in enumerate(codes):
        var, kind = c.rsplit(":", 1)
        shown = (labels or {}).get(var) or var
        out.append({"bit": i, "code": c, "variable": var, "kind": kind, "label": f"{text.get(kind, kind)}: {shown}"})
    return out


def fail_bits(g: GateResult, codes: List[str]) -> np.ndarray:
    """Int bitmask per cell: bit k set when reason code k failed; 0 = passes."""
    if len(codes) > MAX_REASON_BITS:
        raise ValueError(f"{len(codes)} reason codes do not fit in 31 bits")
    lut = {c: 1 << i for i, c in enumerate(codes)}
    return np.array([sum(lut[c] for c in r) for r in g.reasons], dtype=np.int64)


# ----------------------------------------------------------------------------- JSON files
def build_variables_v2(ds: Dataset, mission_cfg: Dict, missions: List[str], stored: Dict[str, List[str]],
                       engine_cfg: EngineConfig) -> Dict[str, Any]:
    reg = ds.reg
    eng = set(engine_variables(mission_cfg, missions))
    overrides_why = engine_cfg.column_overrides.why if engine_cfg.v("column_overrides") else None
    out = []
    for v, e in reg["variables"].items():
        bodies = {}
        for b in BODIES:
            pb = e["bodies"][b]
            col = reg["columns"][v][b]["column"]
            is_stored = v in eng and col in stored[b]
            reason = None
            if not is_stored:
                reason = "not used by the engine" if v not in eng else "no data on this body"
            bodies[b] = {
                "column": col, "alias_column": reg["columns"][v][b]["alias_column"],
                "column_override": bool(reg["columns"][v][b]["override"]),
                "column_override_why": overrides_why if reg["columns"][v][b]["override"] else None,
                "stored": is_stored, "stored_as": f"v.{col}" if is_stored else None, "not_stored_reason": reason,
                "level": pb["level"], "level_text": pb.get("audit_level"), "level_note": pb.get("level_note"),
                "product": pb.get("product", pb.get("claimed_source")), "version": pb.get("version"),
                "url": pb.get("url"), "licence_credit": pb.get("licence_credit"),
                "native_resolution": pb.get("native_resolution"), "aggregation": pb.get("aggregation"),
                "formula": pb.get("formula"),
                "true_baseline": pb.get("true_baseline"), "true_baseline_km": pb.get("true_baseline_km"),
                "cell_ns_km": rnd(pb["resolution_km"], _dec(engine_cfg, "distance_km")),
                "caveat": pb.get("caveat"), "provenance_caveat": pb.get("provenance_caveat"),
            }
        out.append({
            "name": v, "label": e["label"], "unit": e["unit"], "kind": e["kind"], "description": e["description"],
            "categories": e.get("categories"), "used_by": variable_roles(mission_cfg, missions, v),
            "in_engine": v in eng,
            "comparability": {"status": e.get("comparability"), "reason": e["comparability_note"]},
            "bodies": bodies,
        })
    return {"bundle_version": engine_cfg.v("bundle_version"), "dataset": ds.id, "levels": levels_in_use(reg["levels"], out),
            "comparability_statuses": {
                "comparable": "Same physical quantity and definition on both bodies; used in the similarity.",
                "comparable_with_caveat": "Used in the similarity; the reason says how the two values differ (show it).",
                "not_comparable": "Not the same quantity on both bodies (or no data on one): left out of the similarity and the twin search; still counts in suitability."},
            "variables": out}


def funnel_steps(mission_cfg: Dict, engine_cfg: EngineConfig) -> List[Dict[str, Any]]:
    """Text of the six funnel steps. Limits and constants are read from the configuration
    (mission_scoring.json common_gates, engine_config gate_body_applicability and
    repo_similarity decay), never typed here."""
    app = engine_cfg.v("gate_body_applicability") or {}
    parts = []
    for var, g in mission_cfg.get("common_gates", {}).items():
        lim = []
        if g.get("min") is not None:
            lim.append(f"{var} >= {g['min']}")
        if g.get("max") is not None:
            lim.append(f"{var} <= {g['max']}")
        bodies = app.get(var, {}).get("bodies", list(BODIES))
        where = "Earth only" if list(bodies) == ["EARTH"] else ("both bodies" if len(bodies) == len(BODIES) else ", ".join(bodies))
        parts.append(f"{' and '.join(lim) or var} ({where})")
    rs = engine_cfg.v("repo_similarity") or {}
    decay = rs.get("decay")
    rules = similarity_rules(engine_cfg)
    parts5 = []
    real_ms = [m for m, r in rules.items() if r == "real_value_tolerance"]
    repo_ms = [m for m, r in rules.items() if r in REPO_RULES]
    if real_ms:
        rv = engine_cfg.v("real_value_similarity")
        mult = rv["filter_bound_multiplier"]
        parts5.append(f"{', '.join(real_ms)}: similarity on real values (similarity.json real_value): per variable s = exp(-0.5 * (|earth - moon| / tolerance)^2), "
                      f"similarity = 100 * weighted mean of s; the twin is the lunar zone cell with every key variable within {mult['key']:g} x its tolerance "
                      f"and every secondary within {mult['secondary']:g} x its tolerance that has the highest similarity; a point with no such cell has no twin, "
                      "no similarity and no final (it keeps its suitability).")
    pct_ms = [m for m, r in rules.items() if r == "percentile_and_real_tolerance"]
    if pct_ms:
        rv = engine_cfg.v("real_value_similarity")
        mult = rv["filter_bound_multiplier"]
        parts5.append(f"{', '.join(pct_ms)}: similarity on thermal position and real terrain (missions.json similarity, rule percentile_and_real_tolerance): "
                      "the variables with scale 'percentile_within_population' are compared as their percentile within their own population "
                      "(Earth: the points passing the mission's funnel; Moon: the cells of the zone), the others in real values; per variable "
                      f"s = exp(-0.5 * (difference / tolerance)^2), similarity = 100 * weighted mean of s; the twin is the zone cell with every key variable within {mult['key']:g} x its tolerance "
                      f"and every secondary within {mult['secondary']:g} x its tolerance that has the highest similarity; a point with no such cell has no twin, "
                      "no similarity and no final (it keeps its suitability). A likeness of position, not of equal values: the real values are shown with every pair.")
    if repo_ms and decay is not None:
        parts5.append(f"{', '.join(repo_ms)}: the repository's similarity (similarity.json): per-body z-scores of the analog_finder variables, "
                      f"weighted distance d, similarity = 100 * exp(-{decay} * d).")
    sim_text = " ".join(parts5) or "The active similarity rule (similarity.json)."
    return [
        {"step": 1, "name": "common gates",
         "text": "Common hard filters of every mission: " + "; ".join(parts) + ". Failing one eliminates the cell for the mission."},
        {"step": 2, "name": "required variables",
         "text": "Every variable in the mission's require_present list must have a value; a missing one eliminates the cell with the reason '<variable> no data'."},
        {"step": 3, "name": "mission hard filters",
         "text": "The mission's own gates (missions[].gates, with their limits); failing one eliminates the cell for that mission (no score, no rank), with the exact reason, e.g. '<variable> outside [<min>, <max>]'. An eliminated cell may still pass another mission."},
        {"step": 4, "name": "suitability",
         "text": "Survivors only: suitability = 100 * sum(w * u) / sum(w over weighted variables with a value); utility u runs linearly from 0 at 'bad' to 1 at 'good', clipped (tables for classes); contribution = w * u; a missing weighted variable is ignored and the remaining weights renormalised; coverage = weight with a value / total weight."},
        {"step": 5, "name": "similarity", "text": sim_text},
        {"step": 6, "name": "final",
         "text": "final = alpha * similarity + (1 - alpha) * suitability (alpha in missions.json 'alpha'); survivors with a similarity are ranked by the published final, ties by Earth cell id; survivors without a twin (real-value missions) follow, by published suitability, ties by Earth cell id."},
    ]

NOT_IN_SIMILARITY = ["irradiance_kwh_m2_day", "lst_diurnal_amp_k", "tmin_c", "thermal_inertia_class", "permafrost_class"]


def gate_rows(mission_cfg: Dict, mid: str, reg: Dict, engine_cfg: EngineConfig) -> List[Dict[str, Any]]:
    """Gates of a mission with their funnel step, limits and body applicability."""
    m = mission_cfg["missions"][mid]
    rows = []
    all_gate_vars = list(dict.fromkeys(list(mission_cfg.get("common_gates", {})) + list(m.get("gates", {}))))
    for var in all_gate_vars:
        origin = gate_origin(mission_cfg, mid, var)
        g = m["gates"][var] if origin == "mission" else mission_cfg["common_gates"][var]
        if "min" in g or "max" in g:
            limit = f"[{g.get('min', '-inf')}, {g.get('max', 'inf')}]"
        elif g.get("exclude"):
            limit = "not in " + ", ".join(g["exclude"])
        else:
            limit = "in " + ", ".join(g.get("allow", []) or [])
        rows.append({"variable": var, "step": 1 if origin == "common" else 3,
                     "columns": {b: reg["columns"][var][b]["column"] for b in BODIES},
                     "origin": origin,
                     "applies_to": [b for b in BODIES if var in effective_gates(mission_cfg, mid, b, engine_cfg)],
                     "min": g.get("min"), "max": g.get("max"), "max_from": g.get("max_from"),
                     "allow": g.get("allow"), "exclude": g.get("exclude"), "limit": limit,
                     "source": g.get("source", g.get("why"))})
    return rows


def weighted_rows(mission_cfg: Dict, mid: str, reg: Dict, sim_vars: List[str]) -> List[Dict[str, Any]]:
    """Weighted (soft) variables of a mission, in the JSON order."""
    m = mission_cfg["missions"][mid]
    out = []
    for var, spec in m.get("soft", {}).items():
        e = reg["variables"][var]
        out.append({
            "variable": var, "kind": e["kind"], "label": e["label"], "unit": e["unit"],
            "columns": {b: reg["columns"][var][b]["column"] for b in BODIES},
            "levels": {b: e["bodies"][b]["level"] for b in BODIES},
            "weight": spec["weight"], "bad": spec.get("bad"), "good": spec.get("good"),
            "map": spec.get("map"), "default": spec.get("default"), "why": spec.get("why"),
            "also_in_similarity": var in sim_vars,
        })
    return out


def reason_entries_v2(codes: List[str], mission_cfg: Dict, mid: str, engine_cfg: EngineConfig,
                      reg: Optional[Dict] = None) -> List[Dict[str, Any]]:
    """Bit table of a mission's reason codes with funnel step, English text and the
    team module's own text (mission_scoring.py, verbatim). Labels use the registry's
    display labels (``reg``)."""
    labels = {v: e.get("label") for v, e in (reg or {}).get("variables", {}).items()}
    out = reason_entries(codes, engine_cfg, labels)
    for e in out:
        e["step"] = reason_step(e["code"], mission_cfg, mid)
        e.update(reason_texts(e["code"], mission_cfg, mid))
    return out


def twin_summary(twin: np.ndarray, moon_ids: np.ndarray) -> Dict[str, Any]:
    """Distinct twins and the largest share of Earth cells on one twin."""
    tw = twin[twin >= 0]
    if tw.size == 0:
        return {"distinct_twins": 0, "earth_cells_with_twin": 0, "largest_share": None}
    uniq, cnt = np.unique(tw, return_counts=True)
    k = int(np.lexsort((uniq, -cnt))[0])
    return {"distinct_twins": int(uniq.size), "earth_cells_with_twin": int(tw.size),
            "largest_share": {"twin_id": int(uniq[k]), "earth_cells": int(cnt[k]),
                              "share": rnd(float(cnt[k]) / float(tw.size), 4)}}


def build_missions_v2(ds: Dataset, results: Dict[str, MissionResult], mission_cfg: Dict, engine_cfg: EngineConfig,
                      land: np.ndarray, moon_feat: Dict[str, list], earth_places: Dict[str, list],
                      codes: Dict[str, List[str]], comp_codes: Dict[str, Dict[str, List[str]]],
                      limits: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    reg = ds.reg
    limits = limits or {"texts": {}, "top5": {}, "external_validation": {}}
    titles = engine_cfg.v("mission_titles")
    notes = engine_cfg.v("mission_notes")
    status = engine_cfg.v("mission_threshold_status")
    n_top = int(engine_cfg.v("top_failure_reasons_n"))
    suffix = engine_cfg.v("missing_data_reason")["code_suffix"]
    scd, cd = _dec(engine_cfg, "score"), _dec(engine_cfg, "confidence_score")
    rule = similarity_rule(engine_cfg)
    moon_ids = ds.cells["MOON"]["id"].to_numpy()
    out = []
    for mid, res in results.items():
        m = mission_cfg["missions"][mid]
        ranked = res.rank > 0
        land_g = _subset(res.earth_gates, land)
        passing = res.earth_gates.passed
        prov = m.get("provisional")
        comps = mission_components(mission_cfg, mid)
        comp_out = {}
        for cid, cres in res.components.items():
            cm = mission_cfg["missions"][cid]
            cpass = cres.earth_gates.passed
            comp_out[cid] = {
                "role": "information only: shown per Earth cell (passes or not, its score); never changes this mission's ranking",
                "description": cm.get("description"), "author": cm.get("author"),
                "provisional": bool(cm.get("provisional")), "provisional_note": cm.get("provisional") or None,
                "require_present": cm.get("require_present", []),
                "gates": gate_rows(mission_cfg, cid, reg, engine_cfg),
                "weighted_variables": weighted_rows(mission_cfg, cid, reg, []),
                "reason_codes": reason_entries_v2(comp_codes[mid][cid], mission_cfg, cid, engine_cfg, reg),
                "pass_counts": {"EARTH": int(cpass.sum()), "EARTH_LAND_CELLS": int(land.sum()),
                                "MOON": int(cres.moon_gates.passed.sum()), "MOON_CELLS": int(len(cres.moon_gates.passed)),
                                "EARTH_passing_both": int((cpass & passing).sum())},
                "top_failure_reasons": {"EARTH_LAND": top_reasons(_subset(cres.earth_gates, land), n_top),
                                        "MOON": top_reasons(cres.moon_gates, n_top)},
                "distributions": {"suitability": quantiles(cres.earth_suit.score[cpass], scd)},
                "columns_in": "earth_detail_*.bin: <mission>.<component>.fail_bits, .u.<variable>, .suitability",
            }
        sim_block: Dict[str, Any] = {"rule": res.rule}
        if res.rule in REAL_RULES:
            sim_block.update(real_similarity_block(res, reg, engine_cfg))
        if res.rule == "zone_twin":
            z = res.extra["repo_context"].zones[mid]
            sim_block["zone"] = {k: z.get(k) for k in ("name", "kind", "lat_max", "source", "used", "reason", "cells", "regions")}
        if res.rule in TWIN_RULES:
            sim_block.update(twin_summary(res.twin_id[ranked], moon_ids))
        else:
            sim_block["twins"] = None
            sim_block["no_twin_reason"] = "repo_global_mean compares every Earth cell with the mean profile of the whole Moon (the repository's default target), so there is no lunar twin; the shipped rule since the team decision of 2026-11-15 is zone_twin (engine_config similarity_rule)."
        out.append({
            "id": mid, "title": titles.get(mid, mid), "description": m.get("description"), "author": m.get("author"),
            "threshold_status": status[mid], "provisional": bool(prov), "provisional_note": prov if prov else None,
            "frozen_at": m.get("frozen_at"), "components": comps,
            "on_missing_gate": mission_cfg.get("on_missing_gate"), "require_present": m.get("require_present", []),
            "files": {"EARTH": f"earth_{mid}.bin", "MOON": f"moon_{mid}.bin"},
            "gates": gate_rows(mission_cfg, mid, reg, engine_cfg),
            "weighted_variables": weighted_rows(mission_cfg, mid, reg, list(res.sim_vars)),
            "reason_codes": reason_entries_v2(codes[mid], mission_cfg, mid, engine_cfg, reg),
            "pass_counts": {"EARTH": int(passing.sum()), "EARTH_LAND_CELLS": int(land.sum()),
                            "MOON": int(res.moon_gates.passed.sum()), "MOON_CELLS": int(len(res.moon_gates.passed))},
            "ranked_count": int(ranked.sum()),
            "passing_without_similarity": int((passing & ~ranked).sum()),
            "top_failure_reasons": {"EARTH_LAND": top_reasons(land_g, n_top), "MOON": top_reasons(res.moon_gates, n_top)},
            "missing_data": {"EARTH_LAND": missing_summary(land_g, suffix), "MOON": missing_summary(res.moon_gates, suffix)},
            "alpha": res.alpha,
            "similarity": sim_block,
            **({"confidence_counts": {k: int(sum(1 for c in res.confidence if c == k)) for k in CONF_CODES}}
               if _conf_on(engine_cfg) else {}),
            "distributions": {
                "suitability": quantiles(res.earth_suit.score[passing], scd),
                "similarity": quantiles(res.similarity_pct[ranked], scd),
                "final": quantiles(res.final_published[ranked], scd),
                **({"confidence_score": quantiles(res.confidence_score[ranked], cd)} if _conf_on(engine_cfg) else {}),
            },
            "criteria_set": ((engine_cfg.v("criteria_sets") or {}).get("applied", {}) if engine_cfg.criteria_sets is not None else {}).get(mid),
            "component_results": comp_out,
            "known_limitations": [t["text"] for t in (engine_cfg.v("approved_texts") or {}).values()
                                  if t.get("mission") == mid and t.get("mission_card", True)] + list(notes.get(mid, []))
                                 + [t["text"] for t in limits["texts"].values()
                                    if "mission_card" in t.get("show", []) and mid in (t.get("missions") or [mid])],
            "top5": limits["top5"].get(mid),
            "external_validation": limits["external_validation"].get(mid),
            "facts": mission_facts(res, ds.cells, moon_feat, earth_places, engine_cfg),
            "not_used_by_engine": {"tolerances": m.get("tolerances"), "workable_days": m.get("workable_days"),
                                   "domain_weights": m.get("weights"), "why": engine_cfg.v("not_used_by_engine_why")},
        })
    offered = list(results)
    not_offered = {}
    for mid in offered:
        comps = mission_components(mission_cfg, mid)
        if comps["core"]:
            not_offered[comps["core"]] = f"core of {mid} ({mid} is an exact copy of it); not offered as a mission"
        for c in comps["info"]:
            not_offered[c] = f"information component of {mid}, shown per Earth cell; not offered as a mission and never changes the {mid} ranking"
    return {
        "bundle_version": engine_cfg.v("bundle_version"), "dataset": ds.id,
        "config_version": mission_cfg.get("version"), "config_note": mission_cfg.get("note"),
        "offered_missions": offered, "default_mission": offered[0] if offered else None,
        "components_not_offered": not_offered,
        "alpha": float(engine_cfg.v("mix_factor")),
        "alpha_why": engine_cfg.mix_factor.why,
        "similarity_rule": rule,
        "similarity_rules": similarity_rules(engine_cfg, offered),
        "funnel": funnel_steps(mission_cfg, engine_cfg),
        "elimination_line_rule": "the cell's reason codes (fail_bits) in bit order, their 'text' joined with '; '",
        "confidence_codes": CONF_CODES,
        "missions": out,
    }


def real_variable_rows(res: MissionResult, reg: Dict, engine_cfg: EngineConfig) -> List[Dict[str, Any]]:
    """The similarity variables of a real-value mission: role, weight, tolerance, bound,
    unit, who set the tolerance, and how each side's value is made."""
    real = res.extra["real"]
    spec, mrule = real["spec"], real["mission_rule"]
    notes = real["derived"].notes
    rows = []
    for q, x in enumerate(mrule["variables"]):
        v = x["variable"]
        sides = {}
        for b in BODIES:
            n = notes[v][b]
            lvl = n.get("level")
            if n["kind"] == "column":
                col = n["column"]
                lvl = reg["variables"][col]["bodies"][b]["level"] if col in reg.get("variables", {}) else lvl
            sides[b] = {"kind": n["kind"], "column": n.get("column"), "level": lvl, "text": n.get("text"),
                        "body_mean": rnd(n.get("body_mean"), 4), "cells_in_mean": n.get("cells_in_mean")}
        row = {"variable": v, "label": x.get("label", v), "unit": x["unit"], "role": spec.roles[q],
               "weight": spec.weights[q], "tolerance": spec.tau[q], "bound": spec.bound[q],
               "tolerance_set_by": x["tolerance_set_by"], "why": x.get("why"), "sides": sides,
               "pairs_columns": {"earth": f"{v}.earth", "moon": f"{v}.moon", "diff": f"{v}.diff"},
               "score_column": f"s.{v}"}
        if real.get("rule") == "percentile_and_real_tolerance":
            pct = spec.scales[q] == "percentile_within_population"
            row["scale"] = spec.scales[q]
            row["real_unit"] = x.get("real_unit", x["unit"])
            if pct:
                row["pairs_columns"].update({"earth_pct": f"{v}.earth_pct", "moon_pct": f"{v}.moon_pct", "diff_pct": f"{v}.diff_pct"})
                row["population_size"] = real["populations"][v]
            row["compared_columns"] = ({"earth": f"{v}.earth_pct", "moon": f"{v}.moon_pct", "diff": f"{v}.diff_pct"} if pct
                                       else {"earth": f"{v}.earth", "moon": f"{v}.moon", "diff": f"{v}.diff"})
        rows.append(row)
    return rows


def real_similarity_block(res: MissionResult, reg: Dict, engine_cfg: EngineConfig) -> Dict[str, Any]:
    """missions.json similarity block of a real-value mission (rule real_value_tolerance)."""
    from engine.real_similarity import NOPAIR_KINDS, nopair_summary

    real = res.extra["real"]
    rv = real["settings"]
    mrule = real["mission_rule"]
    passing = np.flatnonzero(res.earth_gates.passed)
    paired = int((res.twin_id[passing] >= 0).sum())
    z = dict(mrule["zone"])
    z["cells"] = real["zone_cells"]
    if real.get("rule") == "percentile_and_real_tolerance":
        return percentile_similarity_block(res, reg, engine_cfg, z, passing, paired)
    return {
        "variables": real_variable_rows(res, reg, engine_cfg),
        "weights_why": mrule.get("weights_why"),
        "score": rv["score"], "similarity_formula": rv["similarity"],
        "filter": {"key": f"|difference| <= {rv['filter_bound_multiplier']['key']:g} x tolerance",
                   "secondary": f"|difference| <= {rv['filter_bound_multiplier']['secondary']:g} x tolerance",
                   "missing_key": rv["missing_key"], "missing_secondary": rv["missing_secondary"]},
        "score_decimals": int(rv["score_decimals"]),
        "zone": z,
        "passing_count": int(passing.size), "paired_count": paired, "unpaired_count": int(passing.size - paired),
        "nopair_kinds": NOPAIR_KINDS,
        "unpaired_reasons": nopair_summary(_rt_view(real), real["spec"], passing, 4),
        "pairs_file": f"earth_{res.mission}_pairs.bin",
        "list_rule": "paired points by rank, then the points without a twin by published suitability descending, ties by Earth cell id (earth_<mission>_pairs.bin list_order)",
        "info_columns": [{"variable": v, "columns": {s: f"info.{v}.{s}" for s in ("earth", "moon", "diff")},
                          "part_of_similarity": False}
                         for v in (rv.get("info_in_pairs_file") or {}).get(res.mission, [])],
        "info_in_explain_only": [v for v in real["info"] if v not in (rv.get("info_in_pairs_file") or {}).get(res.mission, [])],
    }


def percentile_similarity_block(res: MissionResult, reg: Dict, engine_cfg: EngineConfig, zone: Dict[str, Any],
                                passing: np.ndarray, paired: int) -> Dict[str, Any]:
    """missions.json similarity block of a percentile_and_real_tolerance mission (lunar_base)."""
    from engine.real_similarity import nopair_summary

    real = res.extra["real"]
    rv = real["settings"]
    mrule = real["mission_rule"]
    kinds = real["nopair_kinds"]
    nk = real["nopair_kind"][passing]
    info_units = {"temp_k": "K", "elevation_rel_m": "m", "irradiance_kwh_m2_day": "kWh/m2/day"}
    return {
        "variables": real_variable_rows(res, reg, engine_cfg),
        "weights_why": mrule.get("weights_why"),
        "meaning": "A likeness of thermal POSITION, not of temperature: the two key variables are compared as percentiles within their own population; slope and roughness in real values. Show the real values and differences of every pair (texts.lunar_base_pair_sentence).",
        "populations": {b: {"rule": mrule["populations"][b]["rule"], "why": mrule["populations"][b]["why"],
                            "cells": int(len(passing)) if b == "EARTH" else int(real["zone_cells"]),
                            "cells_with_value": {v: n[b] for v, n in real["populations"].items()}}
                        for b in BODIES},
        "percentile": mrule["percentile"],
        "score": rv["score"], "similarity_formula": rv["similarity"],
        "filter": {"key": f"|difference| <= {rv['filter_bound_multiplier']['key']:g} x tolerance (percentile points for the percentile variables)",
                   "secondary": f"|difference| <= {rv['filter_bound_multiplier']['secondary']:g} x tolerance (real values)",
                   "missing_key": rv["missing_key"] + "; a cell without a value has no percentile", "missing_secondary": rv["missing_secondary"]},
        "score_decimals": int(rv["score_decimals"]),
        "zone": zone,
        "passing_count": int(passing.size), "paired_count": paired, "unpaired_count": int(passing.size - paired),
        "nopair_kinds": kinds,
        "nopair_groups": mrule["nopair_groups"], "nopair_groups_why": mrule.get("nopair_groups_why"),
        "unpaired_by_kind": {k: int((nk == j).sum()) for j, k in enumerate(kinds)},
        "unpaired_reasons": nopair_summary(_rt_view(real), real["spec"], passing, 4, kinds),
        "info_columns": [{"variable": v, "unit": info_units.get(v), "columns": {s: f"info.{v}.{s}" for s in ("earth", "moon", "diff")},
                          "part_of_similarity": False} for v in real["info"]],
        "pair_sentence": mrule.get("pair_sentence"),
        "pairs_file": f"earth_{res.mission}_pairs.bin",
        "list_rule": "paired points by rank, then the points without a twin by published suitability descending, ties by Earth cell id (earth_<mission>_pairs.bin list_order)",
    }


class _rt_view:  # minimal view of the per-row reason arrays for nopair_summary
    def __init__(self, real: Dict) -> None:
        self.nopair_kind, self.nopair_var, self.nopair_gap = real["nopair_kind"], real["nopair_var"], real["nopair_gap"]


def real_pair_values(res: MissionResult, i: int, engine_cfg: EngineConfig) -> List[Dict[str, Any]]:
    """Per similarity variable of one paired Earth row: role, tolerance, both values, difference, score."""
    real = res.extra["real"]
    spec = real["spec"]
    out = []
    pct_rule = real.get("rule") == "percentile_and_real_tolerance"
    for q, v in enumerate(spec.variables):
        dd = _dec(engine_cfg, v)
        if not pct_rule:
            out.append({"variable": v, "role": spec.roles[q], "weight": spec.weights[q], "tolerance": spec.tau[q],
                        "bound": spec.bound[q], "earth": rnd(real["earth_values"][i, q], dd),
                        "moon": rnd(real["moon_values"][i, q], dd), "difference": rnd(real["diff"][i, q], dd),
                        "score": rnd(real["scores"][i, q], int(real["settings"]["score_decimals"]))})
            continue
        x = real["mission_rule"]["variables"][q]
        row = {"variable": v, "role": spec.roles[q], "scale": spec.scales[q], "weight": spec.weights[q],
               "tolerance": spec.tau[q], "bound": spec.bound[q], "unit": x["unit"],
               "earth": rnd(real["compared_earth"][i, q], dd), "moon": rnd(real["compared_moon"][i, q], dd),
               "difference": rnd(real["compared_diff"][i, q], dd),
               "real_unit": x.get("real_unit", x["unit"]), "earth_real": rnd(real["earth_values"][i, q], dd),
               "moon_real": rnd(real["moon_values"][i, q], dd), "difference_real": rnd(real["diff"][i, q], dd),
               "score": rnd(real["scores"][i, q], int(real["settings"]["score_decimals"]))}
        out.append(row)
    return out


UNUSED_LEVEL_NOTE = "No variable of this dataset has this level (defined for other tables only)."


def levels_in_use(levels: Dict[str, str], variables: List[Dict[str, Any]]) -> Dict[str, str]:
    """variables.json 'levels': every defined level with its text; a level that no
    variable of the dataset has on either body says so (statistical audit 2026-11-15,
    point 9.2.8: the real tables use MEASURED, DERIVED, MODELLED and NO_DATA, never
    UNDOCUMENTED, which only the legacy 2-degree table can carry)."""
    used = {b["level"] for v in variables for b in v["bodies"].values() if b.get("level")}
    return {k: (t if k in used else f"{t} {UNUSED_LEVEL_NOTE}") for k, t in levels.items()}


def fill_pair_sentence(template: Dict[str, Any], values: Dict[str, float]) -> str:
    """Fill a per-pair text template (approved_texts entry with placeholders {file, column,
    decimals[, subtract][, multiply]}) from the pair's values {column: value}; the browser
    does the same from the pairs file."""
    from engine.display import fill_placeholder

    text = template["text"]
    for name, ph in (template.get("placeholders") or {}).items():
        if not isinstance(ph, dict) or ph.get("filled_at_build"):
            continue
        if "display_rule" in template or "rule" in ph:
            # displayed exactly as the browser displays it; the share lost from the two
            # displayed values (engine/display.py, wording and display rounding 2026-11-15)
            text = text.replace("{" + name + "}", fill_placeholder(ph, values))
        else:  # templates without a display_rule (lunar_base_pair_sentence): the contract's
            # browser rule, stored float32 minus subtract with toFixed(decimals) (engine/display.py
            # to_fixed_of_stored; before the audit correction of 2026-11-15 Python's f"{x:.0f}",
            # which rounds an exact binary half to even where toFixed rounds it up)
            text = text.replace("{" + name + "}", fill_placeholder(ph, values, display_rule=False))
    return text


def similarity_levels(reg: Dict, columns: Dict[str, Dict[str, Optional[str]]], var: str) -> Dict[str, Optional[str]]:
    """Level of the column a similarity variable is read from, per body (registry
    variable of the same column; None when there is no column)."""
    out: Dict[str, Optional[str]] = {}
    for b in BODIES:
        col = columns[var][b]
        lvl = None
        if col is not None:
            for v, e in reg["variables"].items():
                if v == col or e["bodies"][b].get("column", v) == col:
                    lvl = e["bodies"][b]["level"]
                    break
        out[b] = lvl
    return out


def similarity_variables_used(ctx, rule: str, earth_rows: np.ndarray,
                               twin: Optional[np.ndarray]) -> Tuple[np.ndarray, np.ndarray]:
    """Per Earth row: how many active similarity variables have a z on both sides (the set
    P of DATA_CONTRACT) and a bit mask of the missing ones (bit k = active_variables[k])."""
    n = len(earth_rows)
    used = np.zeros(n, dtype=np.int64)
    bits = np.zeros(n, dtype=np.int64)
    for k, f in enumerate(ctx.active):
        ez = np.asarray(ctx.earth.z[f], dtype=np.float64)[earth_rows]
        if rule == "zone_twin":
            mz_all = np.asarray(ctx.moon.z[f], dtype=np.float64)
            mz = np.where(twin >= 0, mz_all[np.where(twin >= 0, twin, 0)], np.nan)
        else:
            t = ctx.target[f]["z"]
            mz = np.full(n, np.nan if t is None else float(t))
        ok = np.isfinite(ez) & np.isfinite(mz)
        used += ok
        bits |= np.where(ok, 0, 1 << k)
    return used, bits


def build_similarity_json(ds: Dataset, results: Dict[str, MissionResult], engine_cfg: EngineConfig,
                          limits: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """similarity.json: the active rule, the repository formula and every number it uses;
    'texts' = the approved texts plus the honest-limits texts of ``limits`` (revision 7)."""
    base = _build_similarity_json(ds, results, engine_cfg)
    if limits:
        base["texts"].update(limits["texts"])
    return base


def _build_similarity_json(ds: Dataset, results: Dict[str, MissionResult], engine_cfg: EngineConfig) -> Dict[str, Any]:
    rule = similarity_rule(engine_cfg)
    rules = {m: r.rule for m, r in results.items()}
    first = next(iter(results.values()))
    ctx = first.extra.get("repo_context")
    base = {"bundle_version": engine_cfg.v("bundle_version"), "dataset": ds.id, "rule": rule, "rules": rules,
            "rule_why": engine_cfg.similarity_rule.why, "rule_options": engine_cfg.v("similarity_rule_options"),
            "alpha": float(engine_cfg.v("mix_factor"))}
    real_ms = [m for m, r in rules.items() if r == "real_value_tolerance"]
    if real_ms:
        base["real_value"] = real_value_json(results, real_ms, ds, engine_cfg)
    pct_ms = [m for m, r in rules.items() if r == "percentile_and_real_tolerance"]
    if pct_ms:
        base["percentile_and_real"] = percentile_rule_json(results, pct_ms, ds, engine_cfg)
    repo_ms = [m for m, r in rules.items() if r in REPO_RULES]
    if ctx is None or not repo_ms:
        if any(r == "physical_pooled" for r in rules.values()):
            base["note"] = "physical_pooled rule: per-mission scales and variables are in missions.json"
        base["texts"] = approved_texts_json(engine_cfg)
        return base
    base["z_rule_missions"] = repo_ms
    rs = engine_cfg.v("repo_similarity")
    sc = engine_cfg.v("similarity_columns")
    ovr = engine_cfg.v("column_overrides") or {}
    # the real column each similarity variable is read from (after column_overrides, e.g.
    # slope_deg -> slope_iso_deg), i.e. the stored v.<column> the panel reads
    cols = {v: {b: (ovr.get(e.get(b), e.get(b)) if e.get(b) else None) for b in BODIES} for v, e in sc.items()}
    feats = []
    for f in ctx.features:
        status = "active" if f in ctx.active else ("excluded" if f in ctx.excluded else "inactive")
        why = ctx.excluded.get(f) if f in ctx.excluded else (
            None if f in ctx.active else "no values on at least one body (the repository's rule: a variable counts only when valid on both bodies)")
        stats = {}
        for b, bn in (("EARTH", ctx.earth), ("MOON", ctx.moon)):
            s = bn.stats[f]
            stats[b] = {"valid": bool(s.get("valid")), "n": s.get("n"), "median": s.get("median"),
                        "scale": s.get("std"), "mean": s.get("mean"), "min": s.get("min"), "max": s.get("max"),
                        "iqr": rnd(s.get("iqr"), 6), "std_dev": rnd(s.get("std_dev"), 6),
                        "distinct_values": s.get("distinct_values"), "variation": ctx.variation[b][f]}
        feats.append({"variable": f, "status": status, "status_reason": why,
                      "weight": ctx.weights[f], "norm_weight": rnd(ctx.norm_w.get(f), 12) if f in ctx.norm_w else None,
                      "columns": cols[f], "column_note": sc[f].get("note"),
                      "levels": similarity_levels(ds.reg, cols, f), "stats": stats,
                      "target_global_mean": ctx.target[f]})
    variation_findings = []
    for f in ctx.features:
        for b in BODIES:
            v = ctx.variation[b][f]
            if v != "ok":
                variation_findings.append({"variable": f, "body": b, "variation": v,
                                           "action": ("removed from the similarity (similarity_excluded)" if f in ctx.excluded
                                                      else "dropped by the repository rule (no data)" if v == "no_data"
                                                      else "kept (reported only)")})
    base.update({
        "function": rs["function"], "features_and_weights": rs["features_and_weights"],
        "formula": {
            "z": "z = clip((value - median) / scale, -4, 4), rounded to 4 decimals; median and scale (IQR / 1.349, else the standard deviation, else 1) of the body's own cells (Earth: elevation_m > 0; Moon: every cell). A missing value has no z (the repository would use 0).",
            "distance": "d = sqrt(sum_v norm_weight[v] * (z_earth[v] - z_moon[v])^2) over the active variables, summed in the order of 'variables'; when some variable has no z on either side, d^2 = that sum / sum of the present norm_weights",
            "similarity": "similarity = 100 * exp(-decay * d), rounded to 2 decimals (numpy.round, as analog_finder)",
            "decay": rs["decay"],
            "final": "final = alpha * similarity + (1 - alpha) * suitability",
        },
        "meaning": "Each body is normalised on its own, so 'similar' means the same RELATIVE position on each body (for example a cell as rough for Earth as the lunar target is for the Moon), not equal absolute values. z-scores and absolute values of both sides are exported so the panel can show both.",
        "earth_population": {"rule": f"{rs['earth_population']['variable']} > {rs['earth_population']['greater_than']}",
                             "cells": int(ctx.earth.population.sum())},
        "moon_population": {"rule": rs["moon_population"], "cells": int(ctx.moon.population.sum())},
        "variables": feats,
        "active_variables": list(ctx.active),
        "variation_threshold": rs["zero_variation_threshold"],
        "variation_findings": variation_findings,
        "not_part_of_similarity": [v for v in NOT_IN_SIMILARITY if v in ds.reg["variables"]]
                                  + [f for f in ctx.excluded if f in ds.reg["variables"]],
        "not_part_of_similarity_note": "Exported for both points and marked 'not part of the similarity': they are mission criteria or information, never in the distance.",
        "z_decimals": rs["z_decimals"],
        "texts": approved_texts_json(engine_cfg),
    })
    if rule == "repo_global_mean":
        base["target"] = {"kind": "global_mean", "name": "Global Lunar Surface Mean (-90° to +90°)",
                          "profile": {f: ctx.target[f] for f in ctx.active},
                          "info_not_in_similarity": lunar_info_summary(ds, engine_cfg)}
        base["twins"] = None
        base["no_twin_reason"] = "repo_global_mean has no twin: the target is the mean profile of the whole Moon (the repository's default). The shipped rule since the team decision of 2026-11-15 is zone_twin, which has twins."
    else:
        base["target"] = {"kind": "zone_twin", "tie_rule": engine_cfg.v("twin_tie_rule"),
                          "lunar_cells_filtered": False,
                          "zones": {m: {k: z.get(k) for k in ("name", "kind", "lat_max", "source", "used", "reason", "cells", "regions")}
                                    for m, z in ctx.zones.items() if rules.get(m) == "zone_twin"}}
    return base


def approved_texts_json(engine_cfg: EngineConfig) -> Dict[str, Any]:
    """similarity.json 'texts': the approved texts; build-time placeholders (the lunar
    day length, from engine_config lunar_day_earth_days) are filled here."""
    out = {}
    for k, t in (engine_cfg.v("approved_texts") or {}).items():
        t = dict(t)
        ph = t.get("placeholders") or {}
        for name, spec in list(ph.items()):
            if isinstance(spec, dict) and spec.get("filled_at_build"):
                if name == "lunar_day":
                    t["text"] = t["text"].replace("{lunar_day}", f"{float(engine_cfg.v('lunar_day_earth_days')):.1f}")
                    ph = {n: s for n, s in ph.items() if n != name}
                else:
                    raise KeyError(f"no build-time value for placeholder {name!r}")
        if "placeholders" in t:
            t["placeholders"] = ph
        out[k] = t
    return out


def real_value_json(results: Dict[str, MissionResult], missions: List[str], ds: Dataset,
                    engine_cfg: EngineConfig) -> Dict[str, Any]:
    """similarity.json 'real_value': the real-value rule, its derived variables and, per
    mission, its variables, tolerances and zone (also in missions.json similarity)."""
    rv = engine_cfg.v("real_value_similarity")
    toa = engine_cfg.v("toa_insolation")
    first = results[missions[0]].extra["real"]
    notes = first["derived"].notes
    derived = {}
    for v, d in notes.items():
        derived[v] = {b: {"kind": n["kind"], "column": n.get("column"), "level": n.get("level"), "text": n.get("text"),
                          "body_mean": rnd(n.get("body_mean"), 4), "cells_in_mean": n.get("cells_in_mean")}
                      for b, n in d.items()}
    from engine.real_similarity import toa_daily_insolation_kwh
    ref = {k: rnd(float(toa_daily_insolation_kwh(np.array([float(k)]), toa)[0]), 4)
           for k in toa["reference_values_kwh_m2_day"]}
    return {
        "rule": "real_value_tolerance", "missions": missions,
        "why": engine_cfg.real_value_similarity.why,
        "score": rv["score"], "similarity": rv["similarity"], "filter_bound_multiplier": rv["filter_bound_multiplier"],
        "missing_key": rv["missing_key"], "missing_secondary": rv["missing_secondary"],
        "score_decimals": int(rv["score_decimals"]),
        "twin": "the zone cell that passes the filter with the highest similarity, compared at full precision; ties: lowest lunar id; lunar cells are not passed through the mission filters",
        "published": "per-variable scores s.<variable> are rounded to score_decimals (int32 q / 10^score_decimals); the published similarity is 100 * sum(w * s) / sum(w) from those scores (unrounded in the final, rounded to 2 decimals when stored)",
        "meaning": "Similarity on real values within stated tolerances: the twin's key variables are within their tolerance of the Earth point and its secondary variables within twice theirs; a score of 1 means equal values, 0.61 a difference of one tolerance, 0.14 a difference of two.",
        "derived_variables": derived,
        "irradiance_toa": {"formula": "Q = S0 / pi / r^2 * (h0 sin(phi) sin(d) + cos(phi) cos(d) sin(h0)), annual mean over a Kepler orbit sampled uniformly in time, x hours_per_day / 1000 (kWh/m2/day); Earth only, from latitude; the Moon's value is its surface irradiance",
                           "settings": toa, "settings_why": engine_cfg.toa_insolation.why,
                           "computed_reference_kwh_m2_day": ref,
                           "level": "DERIVED (a formula of latitude; not a measurement)"},
        "lunar_day_earth_days": engine_cfg.v("lunar_day_earth_days"),
        "reference_tolerances_not_used": rv["reference_tolerances_not_used"],
        "info_differences": rv["info_differences"],
        "missions_detail": {m: {"variables": real_variable_rows(results[m], ds.reg, engine_cfg),
                                "zone": {**results[m].extra["real"]["mission_rule"]["zone"],
                                         "cells": results[m].extra["real"]["zone_cells"]},
                                "weights_why": results[m].extra["real"]["mission_rule"].get("weights_why")}
                            for m in missions},
    }


def percentile_rule_json(results: Dict[str, MissionResult], missions: List[str], ds: Dataset,
                         engine_cfg: EngineConfig) -> Dict[str, Any]:
    """similarity.json 'percentile_and_real': the rule of Lunar base (team decision of
    2026-11-15 08:55 CET) and, per mission, its variables, populations and zone."""
    rv = engine_cfg.v("real_value_similarity")
    opts = engine_cfg.v("similarity_rule_options")
    out = {"rule": "percentile_and_real_tolerance", "missions": missions,
           "why": opts["percentile_and_real_tolerance"],
           "score": rv["score"], "similarity": rv["similarity"], "filter_bound_multiplier": rv["filter_bound_multiplier"],
           "missing_key": rv["missing_key"] + "; a cell without a value has no percentile", "missing_secondary": rv["missing_secondary"],
           "score_decimals": int(rv["score_decimals"]),
           "twin": "the zone cell that passes the filter with the highest similarity, compared at full precision; ties: lowest lunar id; lunar cells are not passed through the mission filters",
           "meaning": "A likeness of thermal POSITION, not of temperature: a percentile variable says where a place ranks within its own population (Earth: the mission's candidates; Moon: the zone cells), so equal percentiles do not mean equal values. Terrain is compared in real values. The real values and differences are exported for every pair.",
           "missions_detail": {}}
    for m in missions:
        real = results[m].extra["real"]
        mrule = real["mission_rule"]
        out["missions_detail"][m] = {
            "variables": real_variable_rows(results[m], ds.reg, engine_cfg),
            "percentile": mrule["percentile"],
            "populations": {b: {"rule": mrule["populations"][b]["rule"],
                                "cells_with_value": {v: n[b] for v, n in real["populations"].items()}} for b in BODIES},
            "zone": {**mrule["zone"], "cells": real["zone_cells"]},
            "weights_why": mrule.get("weights_why"),
            "not_part_of_similarity": list(real["info"]),
        }
    return out


def lunar_info_summary(ds: Dataset, engine_cfg: EngineConfig) -> Dict[str, Any]:
    """Whole-Moon summary of the variables that are not part of the similarity (mean for
    numbers, commonest class for categories), for the repo_global_mean target."""
    moon = ds.cells["MOON"]
    out: Dict[str, Any] = {}
    for v in NOT_IN_SIMILARITY + ["rock_or_bare_frac"]:
        if v not in ds.reg["variables"] or v not in moon.columns:
            continue
        if ds.reg["variables"][v]["kind"] == "categorical":
            s = moon[v].dropna().astype(str)
            s = s[s.str.strip() != ""]
            out[v] = {"commonest": s.value_counts().sort_index().idxmax() if len(s) else None,
                      "level": ds.reg["variables"][v]["bodies"]["MOON"]["level"], "part_of_similarity": False}
        else:
            x = pd.to_numeric(moon[v], errors="coerce").to_numpy(dtype=np.float64)
            x = x[np.isfinite(x)]
            out[v] = {"mean": rnd(float(x.mean()), _dec(engine_cfg, v)) if x.size else None,
                      "level": ds.reg["variables"][v]["bodies"]["MOON"]["level"], "part_of_similarity": False}
    return out


def build_twins_json(ds: Dataset, results: Dict[str, MissionResult], engine_cfg: EngineConfig,
                     moon_feat: Dict[str, list], feats: pd.DataFrame,
                     region_share: Optional[Dict[str, Dict[int, Dict[str, Any]]]] = None) -> Optional[Dict[str, Any]]:
    """twins.json (twin rules only): every distinct twin per mission with its z-scores,
    values, nearest IAU feature (name, distance, gazetteer URL) and Earth-cell count."""
    if not any(r.rule in TWIN_RULES for r in results.values()):
        return None
    moon = ds.cells["MOON"]
    ll, dkm = _dec(engine_cfg, "lat_lon"), _dec(engine_cfg, "distance_km")
    zd = int(engine_cfg.v("repo_similarity")["z_decimals"])
    out: Dict[str, Any] = {}
    for mid, res in results.items():
        ctx = res.extra.get("repo_context")
        tw = res.twin_id[res.rank > 0]
        uniq, cnt = np.unique(tw[tw >= 0], return_counts=True)
        order = np.lexsort((uniq, -cnt))
        rows = []
        for k in order:
            p = int(uniq[k])  # lunar id = position (full grid in id order)
            fi = int(moon_feat["index"][p])
            row = {"id": p, "lat": rnd(moon["lat_deg"].iat[p], ll), "lon": rnd(moon["lon_deg"].iat[p], ll),
                   "earth_cells": int(cnt[k])}
            if res.rule == "real_value_tolerance":
                real = res.extra["real"]
                dv = real["derived"].values
                row["values"] = {v: rnd(dv[v]["MOON"][p], _dec(engine_cfg, v)) for v in real["spec"].variables}
                info_vars = ["temp_k"] + NOT_IN_SIMILARITY + list(ctx.excluded if ctx is not None else [])
            elif res.rule == "percentile_and_real_tolerance":
                real = res.extra["real"]
                dv = real["derived"].values
                spec = real["spec"]
                row["values"] = {v: rnd(dv[v]["MOON"][p], _dec(engine_cfg, v)) for v in spec.variables}
                row["percentiles"] = {v: rnd(real["moon_percentile"][p, q], 4) for q, v in enumerate(spec.variables)
                                      if spec.scales[q] == "percentile_within_population"}
                used = set(spec.variables) | {"tmin_c"}
                info_vars = ["temp_k"] + [v for v in NOT_IN_SIMILARITY if v not in used] + list(ctx.excluded if ctx is not None else [])

            else:
                if ctx is not None:
                    row["z"] = {f: rnd(ctx.moon.z[f][p], zd) for f in ctx.active}
                    row["values"] = {f: rnd(ctx.moon.values[f][p], 4) for f in ctx.active}
                info_vars = NOT_IN_SIMILARITY + list(ctx.excluded if ctx is not None else [])
            info = {}
            for v in info_vars:
                if v in moon.columns and v in ds.reg["variables"]:
                    x = moon[v].iat[p]
                    info[v] = (None if pd.isna(x) else str(x)) if ds.reg["variables"][v]["kind"] == "categorical" \
                        else rnd(x, _dec(engine_cfg, v))
            if res.rule in REAL_RULES:
                dv = res.extra["real"]["derived"].values
                for v in res.extra["real"]["info"]:
                    if v in dv and v not in info:      # derived (the centred relative elevation)
                        info[v] = rnd(dv[v]["MOON"][p], _dec(engine_cfg, v))
            row["not_part_of_similarity"] = info
            row["feature"] = {"name": moon_feat["name"][p], "type": moon_feat["type"][p],
                              "distance_km": rnd(moon_feat["distance_km"][p], dkm),
                              "url": str(feats["link"].iat[fi]) if "link" in feats.columns else None}
            if region_share and mid in region_share:
                row["nasa_region"] = region_share[mid].get(p)
            rows.append(row)
        if res.rule not in TWIN_RULES:
            continue
        out[mid] = {"rule": res.rule, **twin_summary(tw, moon["id"].to_numpy()), "twins": rows}
    return {"bundle_version": engine_cfg.v("bundle_version"), "dataset": ds.id,
            "gazetteer": "Gazetteer of Planetary Nomenclature (IAU WGPSN, USGS Astrogeology); 'url' is the feature's gazetteer page",
            "missions": out}


def build_explain_v2(results: Dict[str, MissionResult], ds: Dataset, mission_cfg: Dict, engine_cfg: EngineConfig,
                     earth_places: Dict[str, list], moon_feat: Dict[str, list],
                     top5_rows: Optional[Dict[str, List[int]]] = None) -> Dict[str, Any]:
    """explain.json: the top-N ranked Earth cells per mission with the whole funnel, plus
    the five shown (missions.json top5) when one of them ranks beyond N (revision 7)."""
    n = int(engine_cfg.v("explain_top_n"))
    earth = ds.cells["EARTH"]
    ll, ud, scd, cd, dkm = (_dec(engine_cfg, k) for k in ("lat_lon", "utility", "score", "confidence_score", "distance_km"))
    out: Dict[str, Any] = {}
    for mid, res in results.items():
        ctx = res.extra.get("repo_context")
        order = [i for i in np.argsort(np.where(res.rank > 0, res.rank, np.iinfo(np.int64).max), kind="mergesort")
                 if res.rank[i] > 0][:n]
        extra5 = sorted((i for i in (top5_rows or {}).get(mid, []) if i not in set(order)), key=lambda i: res.rank[i])
        order = list(order) + extra5
        weights = soft_weights(mission_cfg, mid)
        total = sum(weights.values())
        items = []
        for i in order:
            u = {v: res.earth_suit.utilities[v][i] for v in res.soft_vars}
            present = [v for v in res.soft_vars if np.isfinite(u[v])]
            den = sum(weights[v] for v in present)
            br = []
            for v in res.soft_vars:
                kind = ds.reg["variables"][v]["kind"]
                x = earth[v].iat[i]
                val = (None if pd.isna(x) else str(x)) if kind == "categorical" else rnd(x, _dec(engine_cfg, v))
                ok = np.isfinite(u[v])
                br.append({"variable": v, "value": val, "utility": rnd(u[v], ud) if ok else None,
                           "weight": weights[v], "contribution": rnd(weights[v] * u[v], 6) if ok else None,
                           "points": rnd(100.0 * weights[v] * u[v] / den, scd) if ok and den > 0 else None,
                           "level": ds.reg["variables"][v]["bodies"]["EARTH"]["level"]})
            br.sort(key=lambda r: (-(r["contribution"] if r["contribution"] is not None else -1.0), r["variable"]))
            sim = {"value": rnd(res.similarity_pct[i], scd), "rule": res.rule}
            if res.rule in REAL_RULES:
                real = res.extra["real"]
                t = int(res.twin_id[i])
                sim["twin"] = {"id": t, "lat": rnd(ds.cells["MOON"]["lat_deg"].iat[t], ll),
                               "lon": rnd(ds.cells["MOON"]["lon_deg"].iat[t], ll),
                               "feature": moon_feat["name"][t], "feature_km": rnd(moon_feat["distance_km"][t], dkm)}
                sim["variables"] = real_pair_values(res, i, engine_cfg)
                sim["not_part_of_similarity"] = {v: {"earth": rnd(x["earth"][i], _dec(engine_cfg, v)),
                                                     "moon": rnd(x["moon"][i], _dec(engine_cfg, v)),
                                                     "difference": rnd(x["diff"][i], _dec(engine_cfg, v))}
                                                 for v, x in real["info"].items()}
                if "atm" in real:
                    sim["atmosphere"] = {k: rnd(a[i], 4) for k, a in real["atm"].items()}
                if res.rule == "percentile_and_real_tolerance":
                    sim["meaning"] = "likeness of thermal position, not of temperature"
                    key = real["mission_rule"].get("pair_sentence")
                    tpl = (engine_cfg.v("approved_texts") or {}).get(key) if key else None
                    if tpl:
                        sim["pair_sentence"] = fill_pair_sentence(tpl, pair_columns_of_row(res, i))
                else:
                    # the mission's per-pair template (solar: texts.solar_limitation), filled for
                    # this pair as the browser fills it (wording and display rounding, 2026-11-15)
                    for key in per_pair_text_keys(engine_cfg, mid):
                        sim["pair_sentence"] = fill_pair_sentence(approved_texts_json(engine_cfg)[key],
                                                                  pair_columns_of_row(res, i))
            elif ctx is not None:
                sim["earth"] = {f: {"z": rnd(ctx.earth.z[f][i], 4), "value": rnd(ctx.earth.values[f][i], 4)} for f in ctx.active}
                if res.rule == "zone_twin":
                    t = int(res.twin_id[i])
                    sim["moon"] = {f: {"z": rnd(ctx.moon.z[f][t], 4), "value": rnd(ctx.moon.values[f][t], 4)} for f in ctx.active}
                    sim["twin"] = {"id": t, "lat": rnd(ds.cells["MOON"]["lat_deg"].iat[t], ll),
                                   "lon": rnd(ds.cells["MOON"]["lon_deg"].iat[t], ll),
                                   "feature": moon_feat["name"][t], "feature_km": rnd(moon_feat["distance_km"][t], dkm)}
                else:
                    sim["moon"] = {f: ctx.target[f] for f in ctx.active}
            item = {
                "rank": int(res.rank[i]), "id": int(earth["id"].iat[i]),
                "lat": rnd(earth["lat_deg"].iat[i], ll), "lon": rnd(earth["lon_deg"].iat[i], ll),
                "place": {k: earth_places[k][i] for k in ("country_code", "country", "region", "nearest_place")}
                | {"nearest_place_km": rnd(earth_places["nearest_place_km"][i], dkm)},
                "suitability": rnd(res.earth_suit.score[i], scd),
                "coverage": rnd(den / total, 6) if total > 0 else None,
                "breakdown": br,
                "similarity": sim,
                "alpha": res.alpha,
                "final": rnd(res.final_published[i], scd),
                **({"confidence": res.confidence[i], "confidence_score": rnd(res.confidence_score[i], cd)}
                   if _conf_on(engine_cfg) else {}),
            }
            for cid, cres in res.components.items():
                cp = bool(cres.earth_gates.passed[i])
                item.setdefault("components", {})[cid] = {
                    "pass": cp, "fail": [reason_texts(c, mission_cfg, cid)["text"] for c in cres.earth_gates.reasons[i]],
                    "suitability": rnd(cres.earth_suit.score[i], scd) if cp else None}
            items.append(item)
        out[mid] = items
    return {"bundle_version": engine_cfg.v("bundle_version"), "top_n": n,
            "top_n_rule": "the first top_n ranks of every mission, then any of the five shown (missions.json top5.ids) that ranks beyond top_n, by rank",
            "missions": out}


def pair_columns_of_row(res: MissionResult, i: int) -> Dict[str, float]:
    """{pairs-file column: value as stored (float32)} of one Earth row of a real-value
    mission, so a text filled here reads exactly what the browser reads."""
    real = res.extra["real"]
    out: Dict[str, float] = {}
    for q, v in enumerate(real["spec"].variables):
        for side, arr in (("earth", "earth_values"), ("moon", "moon_values"), ("diff", "diff")):
            out[f"{v}.{side}"] = float(np.float32(real[arr][i, q]))
    for v, x in real["info"].items():
        for side in ("earth", "moon", "diff"):
            out[f"info.{v}.{side}"] = float(np.float32(x[side][i]))
    for k, a in (real.get("atm") or {}).items():
        out[f"atm.{k}"] = float(np.float32(a[i]))
    return out


def per_pair_text_keys(engine_cfg: EngineConfig, mission: str) -> List[str]:
    """Keys of the approved per-pair templates of a mission whose placeholders are read
    from a pairs file (solar: solar_limitation; lunar_base: lunar_base_pair_sentence)."""
    out = []
    for k, t in (engine_cfg.v("approved_texts") or {}).items():
        ms = t.get("missions") or ([t["mission"]] if t.get("mission") else [])
        if mission in ms and any(isinstance(p, dict) and "file" in p for p in (t.get("placeholders") or {}).values()):
            out.append(k)
    return out


def build_places(earth_places: Dict[str, list], land_idx: np.ndarray) -> Tuple[Dict[str, Any], Dict[str, Any], Dict[str, np.ndarray]]:
    """places.json and place_detail.json content and the per-land-cell index arrays (missing = -1)."""
    def has(i: int) -> bool:
        return earth_places["country_code"][i] is not None or earth_places["country"][i] is not None

    pairs = sorted({(earth_places["country_code"][i] or "", earth_places["country"][i] or "") for i in land_idx if has(i)})
    regions = sorted({earth_places["region"][i] for i in land_idx if earth_places["region"][i] is not None})
    rules = sorted({earth_places["label_rule"][i] for i in land_idx if earth_places["label_rule"][i] is not None})
    names = sorted({earth_places["nearest_place"][i] for i in land_idx if earth_places["nearest_place"][i] is not None})
    plut = {p: k for k, p in enumerate(pairs)}
    rlut = {r: k for k, r in enumerate(regions)}
    llut = {r: k for k, r in enumerate(rules)}
    nlut = {r: k for k, r in enumerate(names)}
    idx: Dict[str, List[int]] = {"country": [], "region": [], "label_rule": [], "nearest_place": []}
    for i in land_idx:
        cc, cn = earth_places["country_code"][i], earth_places["country"][i]
        idx["country"].append(plut[(cc or "", cn or "")] if has(i) else -1)
        idx["region"].append(rlut[earth_places["region"][i]] if earth_places["region"][i] is not None else -1)
        idx["label_rule"].append(llut[earth_places["label_rule"][i]] if earth_places["label_rule"][i] else -1)
        idx["nearest_place"].append(nlut[earth_places["nearest_place"][i]] if earth_places["nearest_place"][i] else -1)
    places = {
        "countries": [{"code": c or None, "name": n or None} for c, n in pairs],
        "regions": regions,
        "region_rule": "first-level region of the nearest GeoNames place, only when that place is in the same country and within region_max_place_km of the cell centre; otherwise missing",
    }
    detail = {
        "label_rules": rules,
        "label_rule_text": {
            "natural_earth_polygon": "Natural Earth 1:110m admin-0 polygon containing the cell centre",
            "natural_earth_polygon_geonames_code": "inside a polygon without an ISO code in that file: name from the polygon, code = the commonest GeoNames country code of the nearest places of the polygon's cells (one code per polygon)",
            "nearest_geonames_place": "centre outside every 110m polygon: country of the nearest GeoNames populated place",
            "antarctic_treaty_area": "land cell at or south of the configured latitude (60 S): Antarctica, no region",
        },
        "nearest_places": names,
    }
    return places, detail, {k: np.asarray(v, dtype=np.int64) for k, v in idx.items()}


def lunar_info_entries(engine_cfg: EngineConfig) -> List[Dict[str, Any]]:
    """Lunar information columns (moon_base.bin 'info.<column>') with their provenance row."""
    from engine.dataset import normalise_level, read_provenance_csv

    out = []
    info = engine_cfg.v("lunar_info_columns")
    if not info:
        return out
    pcfg = engine_cfg.v("provenance")
    rows = read_provenance_csv(resolve_path(pcfg["MOON"]), "MOON") if pcfg.get("kind") == "csv" else {}
    for col, e in info.items():
        r = rows.get(col, {})
        lvl, note = normalise_level(r["level"]) if r else (None, None)
        out.append({"column": col, "stored_as": f"moon_base.bin info.{col}", "label": e["label"], "unit": e["unit"],
                    "note": e["note"], "level": lvl, "level_note": note, "product": r.get("product"),
                    "version": r.get("version"), "url": r.get("url"), "licence_credit": r.get("licence_credit"),
                    "caveat": r.get("caveats"), "used_by_engine": False})
    return out


def build_named_sites(engine_cfg: EngineConfig, ds: Dataset, results: Dict[str, MissionResult],
                      codes: Dict[str, List[str]], mission_cfg: Dict) -> Optional[Dict[str, Any]]:
    """lunar_named_sites.json: the dataset's named lunar sites, their cell and per-mission outcome."""
    p = engine_cfg.v("lunar_named_sites")
    if not p:
        return None
    with open(resolve_path(p), encoding="utf-8", newline="") as fh:
        rows = list(csv.DictReader(fh))
    ll = _dec(engine_cfg, "iau_lat_lon")
    moon_ids = ds.cells["MOON"]["id"].to_numpy()
    sites = []
    def num(x: str) -> Optional[float]:
        return float(x) if x not in (None, "") else None

    for r in rows:
        lat, lon = num(r.get("lat_deg", "")), num(r.get("lon_deg", ""))
        cid: Optional[int] = None
        per: Optional[Dict[str, Any]] = None
        if r.get("cell_row") not in (None, "") and r.get("cell_col") not in (None, ""):
            cid = int(ds.grid.cell_id(int(float(r["cell_row"])), int(float(r["cell_col"]))))
            pos = int(np.searchsorted(moon_ids, cid))
            if pos >= len(moon_ids) or moon_ids[pos] != cid:
                raise KeyError(f"named site {r['iau_name']}: cell {cid} not in the lunar table")
            per = {mid: {"pass": bool(res.moon_gates.passed[pos]), "fail": list(res.moon_gates.reasons[pos]),
                         "fail_text": [reason_texts(c, mission_cfg, mid)["text"] for c in res.moon_gates.reasons[pos]],
                         "twin_of_count": int(res.moon_twin_count[pos]) if res.rule != "repo_global_mean" else None}
                   for mid, res in results.items()}
        sites.append({"name": r["iau_name"], "type": r["iau_type"] or None, "why": r["why"],
                      "site_note": r["site_note"] or None,
                      "lat": rnd(lat, ll), "lon": rnd(lon, ll), "diameter_km": rnd(num(r.get("diameter_km", "")), 2),
                      "cell_id": cid, "feature_vs_cell": r["feature_vs_cell"] or None,
                      "gazetteer_link": r["gazetteer_link"] or None, "missions": per})
    return {"bundle_version": engine_cfg.v("bundle_version"), "source": p,
            "note": "Cell values are in moon_base.bin at position cell_id. A 1-degree polar cell is a strip that averages lit and shadowed ground (feature_vs_cell).",
            "sites": sites}


# ----------------------------------------------------------------------------- bundle
def build_v2_files(ds: Dataset, results: Dict[str, MissionResult], mission_cfg: Dict, engine_cfg: EngineConfig,
                   land: np.ndarray, earth_places: Dict[str, list], moon_feat: Dict[str, list],
                   feats: pd.DataFrame, iau_source: Dict, validity: Dict, config_hashes: Dict[str, str],
                   build_time: str) -> Tuple[Dict[str, bytes], Dict[str, Any], Dict[str, Any]]:
    """Return ({name: bytes}, {name: JSON object}, manifest)."""
    enc = engine_cfg.v("binary_encoding")
    qd = enc["quantised_decimals"]
    missions = list(results)
    reg = ds.reg
    earth, moon = ds.cells["EARTH"], ds.cells["MOON"]
    raw_e, raw_m = ds.raw["EARTH"], ds.raw["MOON"]
    if len(moon) != ds.grid.cells or not np.array_equal(moon["id"].to_numpy(), np.arange(ds.grid.cells)):
        raise ValueError("moon_base.bin assumes the full lunar grid in id order (position = id)")
    comp_ids = [c for r in results.values() for c in r.components]
    eng_vars = engine_variables(mission_cfg, missions + comp_ids)
    stored = stored_columns(reg, eng_vars, ds.raw)
    land_idx = np.flatnonzero(land)
    land_pos = np.full(len(earth), -1, dtype=np.int64)
    land_pos[land_idx] = np.arange(land_idx.size)
    codes = {m: reason_code_table(r) for m, r in results.items()}
    comp_codes = {m: {c: reason_code_table(cr) for c, cr in r.components.items()} for m, r in results.items()}
    rule = similarity_rule(engine_cfg)
    ctx = next(iter(results.values())).extra.get("repo_context") if results else None
    limits = None
    if engine_cfg.top5_selection is not None:
        from engine.limits import build_limits
        limits = build_limits(ds, results, mission_cfg, engine_cfg, land)

    files: Dict[str, bytes] = {}
    objs: Dict[str, Any] = {}
    meta: Dict[str, Dict[str, Any]] = {}

    def add_bin(bf: BinFile, load: str, desc: str, **extra) -> None:
        files[bf.name] = bytes(bf.buf)
        meta[bf.name] = {"format": "bin", "load": load, "description": desc, **extra, **bf.index()}

    def add_json(name: str, obj: Any, load: str, desc: str) -> None:
        objs[name] = obj
        files[name] = dumps(obj)
        meta[name] = {"format": "json", "load": load, "description": desc}

    # --- places and Earth base
    g = ds.grid
    places_obj, detail_obj, pidx = build_places(earth_places, land_idx)
    eb = BinFile("earth_base.bin", enc)
    eb.i32("id", earth["id"].to_numpy()[land_idx], "land", description="Earth cell id = row * cols + col")
    eb.f32("lat", g.lat_center(np.arange(g.rows)), "grid_rows", unit="deg",
           description="cell-centre latitude of grid row r = floor(id / cols)")
    eb.f32("lon", g.lon_center(np.arange(g.cols)), "grid_cols", unit="deg",
           description="cell-centre longitude of grid column c = id % cols")
    eb.i32("country", pidx["country"], "land", missing=pidx["country"] < 0, codes="places.json countries")
    eb.i32("region", pidx["region"], "land", missing=pidx["region"] < 0, codes="places.json regions")
    e_rows_all = raw_e["row"].to_numpy(dtype=np.int64)
    for col in stored["EARTH"]:
        full = raw_e[col]
        kind, _ = column_kind(reg, col, "EARTH")
        if kind == "categorical":
            vals_all, miss_all = category_codes(full, reg["variables"][_[0]]["categories"])
        else:
            vals_all = pd.to_numeric(full, errors="coerce").to_numpy(dtype=np.float64)
            miss_all = ~np.isfinite(vals_all)
        if row_constant(vals_all, miss_all, e_rows_all, g.rows) is not None:
            _add_value(eb, full, col, "EARTH", reg, "land", e_rows_all, g.rows)
        else:
            _add_value(eb, full.iloc[land_idx].reset_index(drop=True), col, "EARTH", reg, "land")
    real_any = next((r.extra["real"] for r in results.values() if r.rule == "real_value_tolerance"), None)
    if real_any is not None:
        for v, d in real_any["derived"].notes.items():
            if d["EARTH"]["kind"] == "toa_insolation":
                from engine.real_similarity import toa_daily_insolation_kwh
                eb.f32(f"d.{v}", toa_daily_insolation_kwh(g.lat_center(np.arange(g.rows)), engine_cfg.v("toa_insolation")),
                       "grid_rows", unit="kWh/m2/day", per_grid_row=True, level="DERIVED",
                       description="DERIVED: annual-mean daily sunlight on a horizontal surface at the top of Earth's atmosphere, from the cell-centre latitude (similarity.json real_value.irradiance_toa); not a measurement")
    pd_bin = BinFile("earth_place_detail.bin", enc)
    pd_bin.i32("label_rule", pidx["label_rule"], "land", missing=pidx["label_rule"] < 0,
               codes="place_detail.json label_rules")
    pd_bin.i32("nearest_place", pidx["nearest_place"], "land", missing=pidx["nearest_place"] < 0,
               codes="place_detail.json nearest_places")
    pd_bin.f32("nearest_place_km", np.asarray([earth_places["nearest_place_km"][i]
                                               if earth_places["nearest_place_km"][i] is not None else np.nan
                                               for i in land_idx], dtype=np.float64), "land", unit="km",
               description="distance from the cell centre to the nearest GeoNames populated place")

    # --- Moon base (values, information columns, nearest IAU feature)
    mb = BinFile("moon_base.bin", enc)
    mb.f32("lat", g.lat_center(np.arange(g.rows)), "grid_rows", unit="deg",
           description="cell-centre latitude of grid row r = floor(id / cols)")
    mb.f32("lon", g.lon_center(np.arange(g.cols)), "grid_cols", unit="deg",
           description="cell-centre longitude of grid column c = id % cols")
    m_rows_all = raw_m["row"].to_numpy(dtype=np.int64)
    for col in stored["MOON"]:
        _add_value(mb, raw_m[col], col, "MOON", reg, "all", m_rows_all, g.rows)
    for col, info in engine_cfg.v("lunar_info_columns").items():
        mb.f32(f"info.{col}", pd.to_numeric(raw_m[col], errors="coerce").to_numpy(dtype=np.float64), "all",
               unit=info["unit"], description=f"{info['label']} (information only, not used by any mission or the similarity)")
    mb.i32("feature", np.asarray(moon_feat["index"]), "all", codes="iau_moon_features.json (array position)")
    mb.f32("feature_km", moon_feat["distance_km"], "all", unit="km",
           description="great-circle distance from the cell centre to that feature's centre")
    zones_obj = zones_status = None
    if engine_cfg.v("lunar_regions"):
        from engine.lunar_regions import check_mission_zones, mission_zones_json, region_codes, zone_from_config
        rcodes, _ = region_codes(moon, engine_cfg)
        rv_m = (engine_cfg.v("real_value_similarity") or {}).get("missions", {})
        check_mission_zones(moon, engine_cfg, rcodes,
                            {m: zone_from_config(moon, engine_cfg, f"real_value_similarity.missions.{m}.zone") for m in rv_m})
        mb.i32("region", rcodes, "all", codes="mission_zones.json regions (array position)",
               description="lunar region of the cell (docs/MISSION_ZONES.md section 2: A the nine NASA regions, B south-polar outside them, C north-polar, D low equatorial plains, E far side, F the rest); for the web's 'why not here' texts")
        zones_obj, zones_status = mission_zones_json(moon, engine_cfg, rcodes)

    # --- per mission: map columns
    ud, scd, cd = qd["utility"], qd["score"], qd["confidence_score"]
    for mid, res in results.items():
        has_twins = res.rule in TWIN_RULES
        is_real = res.rule in REAL_RULES
        bits_e = fail_bits(res.earth_gates, codes[mid])
        outside = np.flatnonzero(res.earth_gates.passed & ~land)
        if outside.size:
            raise ValueError(f"{mid}: {outside.size} passing Earth cells are not land cells of the bundle")
        ef = BinFile(f"earth_{mid}.bin", enc)
        ef.i32("fail_bits", bits_e[land_idx], "land",
               description="bit k set when missions.json reason_codes[k] failed; 0 = the cell passes")
        idx = np.flatnonzero(res.earth_gates.passed)
        ef.i32("land_index", land_pos[idx], "passing", description="position of the cell in earth_base.bin")
        ef.quantised("suitability", _round_array(res.earth_suit.score[idx], scd), scd, "passing", description="0-100")
        ef.quantised("similarity", _round_array(res.similarity_pct[idx], scd), scd, "passing",
                     description=("0-100, real values within tolerances (missions.json similarity); missing when the cell has no lunar twin"
                                  if is_real else "0-100, the active similarity rule (similarity.json)"))
        ef.quantised("final", res.final_published[idx], scd, "passing", description="0-100")
        rk = res.rank[idx]
        ef.i32("rank", rk, "passing", missing=rk <= 0,
               description="1 = best; missing when there is no similarity" + (" (no lunar twin)" if is_real else ""))
        if has_twins:
            tw = res.twin_id[idx]
            ef.i32("twin", tw, "passing", missing=tw < 0,
                   description="lunar twin cell id (= moon_base.bin position)" + ("; missing = no lunar cell of the zone passes the pair filter" if is_real else ""))
        conf = [res.confidence[i] for i in idx] if _conf_on(engine_cfg) else [None] * len(idx)
        ccode = np.array([CONF_CODES.index(c) if c is not None else 0 for c in conf], dtype=np.int64)
        # revision 8: the per-pair confidence label is not exported (every value missing); the
        # columns stay so an older web build still reads the file and shows no label
        ef.i32("confidence", ccode, "passing", missing=np.array([c is None for c in conf]),
               codes="missions.json confidence_codes")
        csc = _round_array(res.confidence_score[idx], cd) if _conf_on(engine_cfg) else np.full(len(idx), np.nan)
        ef.quantised("confidence_score", csc, cd, "passing")
        if is_real:
            real = res.extra["real"]
            sdq = int(real["settings"]["score_decimals"])
            for q, v in enumerate(real["spec"].variables):
                ef.quantised(f"s.{v}", real["scores"][idx, q], sdq, "passing",
                             description=f"score of {v} for the pair: exp(-0.5 * (difference / tolerance)^2), 0-1; missing when there is no twin or no value on a side")
        if ctx is not None and res.rule in REPO_RULES:
            used, bits_sim = similarity_variables_used(ctx, res.rule, idx, res.twin_id[idx] if has_twins else None)
            ef.i32("sim_vars_used", used, "passing",
                   description="number of similarity variables (similarity.json active_variables) with a value on both sides of the pair, i.e. used in this cell's similarity")
            ef.i32("sim_missing_bits", bits_sim, "passing",
                   description="bit k set when similarity.json active_variables[k] has no value on the Earth cell or on its lunar side and was left out of the distance (weights renormalised); 0 = every variable used")
        add_bin(ef, "on_demand" if mid != missions[0] else "start",
                f"{mid}: fail bits for every Earth land cell; suitability, similarity, final, rank and confidence of the passing cells",
                body="EARTH", mission=mid)
        mf = BinFile(f"moon_{mid}.bin", enc)
        mf.i32("fail_bits", fail_bits(res.moon_gates, codes[mid]), "all",
               description="bit k set when missions.json reason_codes[k] failed; 0 = the cell passes (information: lunar cells are not filtered for the similarity)")
        if has_twins:
            mf.i32("twin_count", res.moon_twin_count, "all", description="Earth cells whose twin is this lunar cell")
        add_bin(mf, "on_demand", f"{mid}: fail bits{' and twin counts' if has_twins else ''} for every lunar cell",
                body="MOON", mission=mid)
        if is_real:
            add_bin(real_pairs_file(res, idx, enc), "on_demand",
                    f"{mid}: per passing cell, the list order, the real values on both sides, the difference of every similarity variable, the reason when there is no twin" + (" and the sunlight above and below the atmosphere" if "atm" in res.extra["real"] else ""),
                    body="EARTH", mission=mid)

    # --- per-cell funnel detail, tiled by grid rows
    tile_rows = int(engine_cfg.v("detail_tile_rows"))
    zd = int(engine_cfg.v("repo_similarity")["z_decimals"])
    land_rows = earth["row"].to_numpy(dtype=np.int64)[land_idx]
    tiles = []
    for t0 in range(0, g.rows, tile_rows):
        sel = land_idx[(land_rows >= t0) & (land_rows < t0 + tile_rows)]
        if sel.size == 0:
            continue
        name = f"earth_detail_{t0 // tile_rows:02d}.bin"
        tf = BinFile(name, enc)
        tf.i32("id", earth["id"].to_numpy()[sel], "tile_land", description="Earth cell id (land cells of this tile, ascending)")
        if ctx is not None and any(r.rule in REPO_RULES for r in results.values()):
            for f in ctx.active:
                tf.quantised(f"z.{f}", ctx.earth.z[f][sel], zd, "tile_land",
                             description=f"per-body z-score of {f} (similarity.json); missing = no value or outside the normalised population")
        for mid, res in results.items():
            ok = res.earth_gates.passed[sel]
            for v in res.soft_vars:
                tf.quantised(f"{mid}.u.{v}", np.where(ok, res.earth_suit.utilities[v][sel], np.nan), ud, "tile_land",
                             description=f"{mid}: utility of {v} (0-1); missing when the cell is eliminated or {v} has no value")
            for cid, cres in res.components.items():
                cbits = fail_bits(cres.earth_gates, comp_codes[mid][cid])
                tf.i32(f"{mid}.{cid}.fail_bits", cbits[sel], "tile_land",
                       description=f"{mid}: information component {cid}: bit k set when missions.json component_results.{cid}.reason_codes[k] failed")
                cok = cres.earth_gates.passed[sel]
                for v in cres.soft_vars:
                    tf.quantised(f"{mid}.{cid}.u.{v}", np.where(cok, cres.earth_suit.utilities[v][sel], np.nan), ud,
                                 "tile_land", description=f"{cid}: utility of {v}; missing unless the cell passes {cid}")
                tf.quantised(f"{mid}.{cid}.suitability", _round_array(np.where(cok, cres.earth_suit.score[sel], np.nan), scd),
                             scd, "tile_land", description=f"{cid}: suitability 0-100 (information only)")
        add_bin(tf, "on_demand", f"per-cell funnel detail of the Earth land cells in grid rows {t0}-{t0 + tile_rows - 1}",
                body="EARTH", grid_rows=[t0, min(t0 + tile_rows, g.rows) - 1])
        tiles.append({"name": name, "row_start": t0, "row_end": min(t0 + tile_rows, g.rows) - 1,
                      "land_cells": int(sel.size)})

    add_bin(eb, "start", "Earth land cells: id, coordinates (grid axes), place indexes and the values of the stored columns", body="EARTH")
    add_bin(pd_bin, "on_demand", "Earth land cells: how the country was found and the nearest populated place", body="EARTH")
    add_bin(mb, "on_demand", "Every lunar cell (position = id): values, information columns and nearest IAU feature", body="MOON")
    add_json("missions.json", build_missions_v2(ds, results, mission_cfg, engine_cfg, land, moon_feat,
                                                 earth_places, codes, comp_codes, limits), "start",
             "missions, funnel, gates, weights, reason codes, counts, components")
    add_json("similarity.json", build_similarity_json(ds, results, engine_cfg, limits), "start",
             "the active similarity rule, its formula, variables, weights, per-body statistics and target")
    variables_obj = build_variables_v2(ds, mission_cfg, missions + comp_ids, stored, engine_cfg)
    variables_obj["lunar_info_columns"] = lunar_info_entries(engine_cfg)
    add_json("variables.json", variables_obj, "start",
             "per variable and body: column, level, source, licence, baseline, caveat, comparability")
    add_json("places.json", places_obj, "start", "Earth country and region tables indexed by earth_base.bin")
    add_json("place_detail.json", detail_obj, "on_demand", "label rules and nearest-place names indexed by earth_place_detail.bin")
    twins = build_twins_json(ds, results, engine_cfg, moon_feat, feats, (limits or {}).get("region_share"))
    if twins is not None:
        add_json("twins.json", twins, "on_demand", "every distinct lunar twin per mission: z-scores, values, IAU feature, Earth-cell count")
    add_json("explain.json", build_explain_v2(results, ds, mission_cfg, engine_cfg, earth_places, moon_feat,
                                              (limits or {}).get("top5_rows")),
             "on_demand", "top-N ranked Earth cells per mission with the whole funnel")
    add_json("iau_moon_features.json", build_iau_features(feats, engine_cfg, iau_source), "on_demand",
             "IAU lunar features (non-satellite), indexed by moon_base.bin 'feature'")
    sites = build_named_sites(engine_cfg, ds, results, codes, mission_cfg)
    if sites is not None:
        add_json("lunar_named_sites.json", sites, "on_demand", "named lunar sites, their cell and per-mission outcome")
    add_json("validity.json", validity, "on_demand", "schema validation report of the input tables")
    if zones_obj is not None:
        add_json("mission_zones.json", zones_obj, "on_demand",
                 "the six lunar regions (moon_base.bin 'region'), each mission's zone as regions, and the texts for a cell outside a mission's zone")

    order = ["missions.json", "similarity.json", "variables.json", "places.json", "earth_base.bin",
             f"earth_{missions[0]}.bin"] + [f"earth_{m}.bin" for m in missions[1:]] + \
        [f"earth_{m}_pairs.bin" for m in missions] + [t["name"] for t in tiles] + \
        ["moon_base.bin"] + [f"moon_{m}.bin" for m in missions] + \
        ["twins.json", "earth_place_detail.bin", "place_detail.json", "explain.json", "iau_moon_features.json",
         "lunar_named_sites.json", "mission_zones.json", "validity.json"]
    order = [n for n in order if n in files]
    first = [n for n in order if meta[n]["load"] == "start"]
    budget = engine_cfg.v("first_view_budget_bytes")
    radii = engine_cfg.v("body_radius_km")
    data_credits = sorted({reg["variables"][v]["bodies"][b].get("licence_credit") or "" for v in eng_vars for b in BODIES} - {""})
    manifest = {
        "bundle_version": engine_cfg.v("bundle_version"),
        "contract_revision": 7,
        "engine_version": engine_cfg.v("engine_version"),
        "dataset": {"id": ds.id, "why": engine_cfg.dataset.why},
        "build_time": build_time,
        "similarity_rule": rule,
        "similarity_rules": {m: r.rule for m, r in results.items()},
        "inputs": ds.inputs,
        "config_sha256": config_hashes,
        "grid": ds.grid.describe(radii, _dec(engine_cfg, "distance_km")),
        "encoding": {
            "byte_order": enc["byte_order"], "float32_missing": "NaN", "int32_missing": enc["int32_missing"],
            "column_rule": "each column is 'length' values of 'type' starting at byte 'offset' of its file; 'rows' names the row set: land = the Earth cells of earth_base.bin (in id order), passing = the land cells passing the mission (in id order), tile_land = the land cells of one detail tile (in id order, its 'id' column), all = every lunar cell (position = id), grid_rows = one value per grid row (row = floor(id / cols)), grid_cols = one value per grid column (col = id % cols)",
            "quantised_rule": "a column with 'divisor' holds Int32 q; value = q / divisor (divide, do not multiply by scale, to get the exact published value)",
        },
        "counts": {
            "EARTH": {"cells": int(len(earth)), "land_cells": int(land.sum()),
                      "invalid_records": validity["bodies"]["EARTH"]["failing_records"]},
            "MOON": {"cells": int(len(moon)), "invalid_records": validity["bodies"]["MOON"]["failing_records"]},
            "missions": {m: {"pass_EARTH": int(r.earth_gates.passed.sum()), "pass_MOON": int(r.moon_gates.passed.sum()),
                             "ranked_EARTH": int((r.rank > 0).sum()),
                             "unpaired_EARTH": int((r.earth_gates.passed & (r.rank <= 0)).sum()),
                             "distinct_twins": int(len(np.unique(r.twin_id[(r.twin_id >= 0) & (r.rank > 0)])))}
                         for m, r in results.items()},
            "lunar_features_for_labels": int(len(feats)),
        },
        "load": {"first_view": first, "default_mission": missions[0]},
        "detail_tiles": {"rows_per_tile": tile_rows, "lookup": "tile file = detail_tiles.files[k] with row_start <= floor(id / cols) <= row_end; the cell's position in the tile = binary search of id in the tile's 'id' column",
                         "files": tiles},
        "files": [{"name": n, "bytes": len(files[n]), "sha256": sha256_bytes(files[n]), **meta[n]} for n in order],
        "sizes": {"first_view_bytes_without_manifest": int(sum(len(files[n]) for n in first)),
                  "total_bytes_without_manifest": int(sum(len(files[n]) for n in order)),
                  "detail_tile_max_bytes": int(max((len(files[t["name"]]) for t in tiles), default=0)),
                  "budget": budget},
        "credits": list(engine_cfg.v("credits")) + data_credits,
    }
    if zones_status is not None:
        manifest["mission_zone_texts"] = {"status": zones_status, "texts_present": zones_obj["texts"] is not None}
    files["manifest.json"] = dumps(manifest)
    objs["manifest.json"] = manifest
    return files, objs, manifest


def real_pairs_file(res: MissionResult, idx: np.ndarray, enc: Dict) -> BinFile:
    """earth_<mission>_pairs.bin of a real-value mission (rows: passing cells)."""
    from engine.real_similarity import NOPAIR_KINDS

    real = res.extra["real"]
    spec = real["spec"]
    if real.get("rule") == "percentile_and_real_tolerance":
        return percentile_pairs_file(res, idx, enc)
    pf = BinFile(f"earth_{res.mission}_pairs.bin", enc)
    pf.i32("list_order", real["list_order"][idx], "passing",
           description="display order of the passing cells: paired cells by rank, then cells without a twin by published suitability descending, ties by id")
    for q, v in enumerate(spec.variables):
        unit = real["mission_rule"]["variables"][q]["unit"]
        pf.f32(f"{v}.earth", real["earth_values"][idx, q], "passing", unit=unit,
               description=f"{v} of the Earth cell (real value; NaN = no value)")
        pf.f32(f"{v}.moon", real["moon_values"][idx, q], "passing", unit=unit,
               description=f"{v} of the lunar twin (NaN = no twin or no value)")
        pf.f32(f"{v}.diff", real["diff"][idx, q], "passing", unit=unit,
               description=f"|Earth - twin| of {v}, computed in double precision (NaN = no twin or no value)")
    units = {"temp_k": "K", "elevation_rel_m": "m", "irradiance_kwh_m2_day": "kWh/m2/day", "lst_diurnal_amp_k": "K"}
    for v in (real["settings"].get("info_in_pairs_file") or {}).get(res.mission, []):
        x = real["info"][v]
        for side, txt in (("earth", "of the Earth cell"), ("moon", "of the lunar twin"), ("diff", "|Earth - twin|")):
            pf.f32(f"info.{v}.{side}", x[side][idx], "passing", unit=units.get(v),
                   description=f"{v} {txt}: not part of the similarity, shown as a difference (NaN = no twin or no value)")
    nk = real["nopair_kind"][idx]
    pf.i32("nopair_kind", nk, "passing", missing=nk < 0,
           codes="missions.json similarity.nopair_kinds",
           description="why the cell has no twin: " + "; ".join(f"{k} = {t}" for k, t in enumerate(NOPAIR_KINDS)) + "; missing = paired")
    nv = real["nopair_var"][idx]
    pf.i32("nopair_var", nv, "passing", missing=nv < 0, codes="missions.json similarity.variables (array position)",
           description="the similarity variable that blocks the pair; missing = paired")
    pf.f32("nopair_gap", real["nopair_gap"][idx], "passing",
           description="the smallest gap found for that variable (its unit): the closest zone value (no_zone_cell_within_bound) or its difference at the zone cell nearest to meeting every bound (no_joint_match); NaN = paired or no Earth value")
    for k, a in real.get("atm", {}).items():
        pf.f32(f"atm.{k}", a[idx], "passing", unit=("fraction 0-1" if k == "lost_share" else "kWh/m2/day"),
               description={"ground_kwh_m2_day": "Earth irradiance at the ground (v.irradiance_kwh_m2_day)",
                            "toa_kwh_m2_day": "Earth sunlight above the atmosphere (DERIVED, toa_insolation)",
                            "lost_share": "1 - ground / above the atmosphere: the share lost in the atmosphere at the Earth site"}.get(k, k))
    return pf


def percentile_pairs_file(res: MissionResult, idx: np.ndarray, enc: Dict) -> BinFile:
    """earth_<mission>_pairs.bin of a percentile_and_real_tolerance mission (lunar_base;
    rows: passing cells)."""
    real = res.extra["real"]
    spec = real["spec"]
    kinds = real["nopair_kinds"]
    pf = BinFile(f"earth_{res.mission}_pairs.bin", enc)
    pf.i32("list_order", real["list_order"][idx], "passing",
           description="display order of the passing cells: paired cells by rank, then cells without a twin by published suitability descending, ties by id")
    for q, v in enumerate(spec.variables):
        x = real["mission_rule"]["variables"][q]
        ru = x.get("real_unit", x["unit"])
        pf.f32(f"{v}.earth", real["earth_values"][idx, q], "passing", unit=ru,
               description=f"{v} of the Earth cell, real value (NaN = no value)")
        pf.f32(f"{v}.moon", real["moon_values"][idx, q], "passing", unit=ru,
               description=f"{v} of the lunar twin, real value (NaN = no twin or no value)")
        pf.f32(f"{v}.diff", real["diff"][idx, q], "passing", unit=ru,
               description=f"|Earth - twin| of {v} in real values, double precision (NaN = no twin or no value)")
        if spec.scales[q] == "percentile_within_population":
            pf.f32(f"{v}.earth_pct", real["compared_earth"][idx, q], "passing", unit="percentile points",
                   description=f"percentile of the Earth cell's {v} among the Earth points passing the mission (mid-rank, 0-100)")
            pf.f32(f"{v}.moon_pct", real["compared_moon"][idx, q], "passing", unit="percentile points",
                   description=f"percentile of the twin's {v} among the cells of the zone (mid-rank, 0-100; NaN = no twin)")
            pf.f32(f"{v}.diff_pct", real["compared_diff"][idx, q], "passing", unit="percentile points",
                   description=f"|Earth percentile - twin percentile| of {v}: the compared difference (filter and score)")
    units = {"temp_k": "K", "elevation_rel_m": "m", "irradiance_kwh_m2_day": "kWh/m2/day"}
    for v, x in real["info"].items():
        for side, txt in (("earth", "of the Earth cell"), ("moon", "of the lunar twin"), ("diff", "|Earth - twin|")):
            pf.f32(f"info.{v}.{side}", x[side][idx], "passing", unit=units.get(v),
                   description=f"{v} {txt}: not part of the similarity, shown as a difference (NaN = no twin or no value)")
    nk = real["nopair_kind"][idx]
    pf.i32("nopair_kind", nk, "passing", missing=nk < 0, codes="missions.json similarity.nopair_kinds",
           description="why the cell has no twin: " + "; ".join(f"{k} = {t}" for k, t in enumerate(kinds)) + "; missing = paired")
    for suffix, which in (("", "first"), ("2", "second")):
        nv = real["nopair_var" + suffix][idx]
        pf.i32("nopair_var" + suffix, nv, "passing", missing=nv < 0,
               codes="missions.json similarity.variables (array position)",
               description=("the similarity variable that blocks the pair (the thermal group when both fail)" if not suffix
                            else "no_cell_meets_either only: the blocking variable of the second group (terrain)") + "; missing = paired or not set")
        pf.f32("nopair_gap" + suffix, real["nopair_gap" + suffix][idx], "passing",
               description=f"the smallest gap found for nopair_var{suffix}, in its compared unit (percentile points for the thermal variables): its difference at the zone cell nearest to meeting the group's bounds (no_single_cell_meets_both: every bound); NaN = paired or not set")
    return pf


def row_constant(values: np.ndarray, missing: np.ndarray, rows: np.ndarray, n_rows: int) -> Optional[Tuple[np.ndarray, np.ndarray]]:
    """(per-row values, per-row missing) when every grid row holds one value (or is all
    missing), else None. Detected from the data, never assumed from a column name."""
    out = np.zeros(n_rows, dtype=values.dtype)
    miss = np.ones(n_rows, dtype=bool)
    seen = np.zeros(n_rows, dtype=bool)
    for r in range(n_rows):
        sel = rows == r
        if not sel.any():
            continue
        seen[r] = True
        m = missing[sel]
        if m.all():
            continue
        if m.any():
            return None
        v = values[sel]
        if not np.all(v == v[0]):
            return None
        out[r], miss[r] = v[0], False
    if not seen.all():
        return None
    return out, miss


def _add_value(bf: BinFile, s: pd.Series, column: str, body: str, reg: Dict, rows: str,
               grid_rows: Optional[np.ndarray] = None, n_rows: int = 0) -> None:
    """One value column: Float32 for numbers, Int32 codes for categories. With
    ``grid_rows`` (the grid row of every cell of the full body table, in the order of
    ``s``) a column that is constant along every grid row is stored once per grid row
    (row set 'grid_rows'); the cell's value is then column[row of the cell]."""
    kind, vs = column_kind(reg, column, body)
    if kind == "categorical":
        cats = reg["variables"][vs[0]]["categories"]
        vals, miss = category_codes(s, cats)
        meta = {"codes": f"variables.json {vs[0]} categories", "variables": vs}
    else:
        vals = pd.to_numeric(s, errors="coerce").to_numpy(dtype=np.float64)
        miss = ~np.isfinite(vals)
        meta = {"unit": reg["variables"][vs[0]]["unit"], "variables": vs}
    per_row = row_constant(vals, miss, grid_rows, n_rows) if grid_rows is not None else None
    if per_row is not None:
        vals, miss = per_row
        rows = "grid_rows"
        meta["per_grid_row"] = True
    if kind == "categorical":
        bf.i32(f"v.{column}", vals, rows, missing=miss, **meta)
    else:
        bf.f32(f"v.{column}", np.where(miss, np.nan, vals), rows, **meta)
