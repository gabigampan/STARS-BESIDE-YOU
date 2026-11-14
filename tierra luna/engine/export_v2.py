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
from engine.config import BODIES, EngineConfig, mission_components, resolve_path, sha256_bytes, similarity_rule
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


def reason_entries(codes: List[str], engine_cfg: EngineConfig) -> List[Dict[str, Any]]:
    """[{bit, code, variable, kind, label}] for a mission's reason codes."""
    md = engine_cfg.v("missing_data_reason")
    text = {"below_min": "below minimum", "above_max": "above maximum", "not_allowed": "class not allowed",
            "excluded": "class excluded", md["code_suffix"]: md["label"]}
    out = []
    for i, c in enumerate(codes):
        var, kind = c.rsplit(":", 1)
        out.append({"bit": i, "code": c, "variable": var, "kind": kind, "label": f"{text.get(kind, kind)}: {var}"})
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
    return {"bundle_version": engine_cfg.v("bundle_version"), "dataset": ds.id, "levels": reg["levels"],
            "comparability_statuses": {
                "comparable": "Same physical quantity and definition on both bodies; used in the similarity.",
                "comparable_with_caveat": "Used in the similarity; the reason says how the two values differ (show it).",
                "not_comparable": "Not the same quantity on both bodies (or no data on one): left out of the similarity and the twin search; still counts in suitability."},
            "variables": out}


FUNNEL_STEPS = [
    {"step": 1, "name": "common gates",
     "text": "Common hard filters of every mission: the land mask elevation_m >= 1 (Earth only) and mask_fraction >= 0.3 (both bodies). Failing one eliminates the cell for the mission."},
    {"step": 2, "name": "required variables",
     "text": "Every variable in the mission's require_present list must have a value; a missing one eliminates the cell with the reason '<variable> no data'."},
    {"step": 3, "name": "mission hard filters",
     "text": "The mission's own gates; failing one eliminates the cell for that mission (no score, no rank), with the exact reason, e.g. 'irradiance_kwh_m2_day outside [2.5, inf]'. An eliminated cell may still pass another mission."},
    {"step": 4, "name": "suitability",
     "text": "Survivors only: suitability = 100 * sum(w * u) / sum(w over weighted variables with a value); utility u runs linearly from 0 at 'bad' to 1 at 'good', clipped (tables for classes); contribution = w * u; a missing weighted variable is ignored and the remaining weights renormalised; coverage = weight with a value / total weight."},
    {"step": 5, "name": "similarity",
     "text": "The repository's similarity (similarity.json): per-body z-scores of the analog_finder variables, weighted distance d, similarity = 100 * exp(-0.45 * d)."},
    {"step": 6, "name": "final",
     "text": "final = alpha * similarity + (1 - alpha) * suitability (alpha in missions.json 'alpha'); survivors are ranked by the published final, ties by Earth cell id."},
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


def reason_entries_v2(codes: List[str], mission_cfg: Dict, mid: str, engine_cfg: EngineConfig) -> List[Dict[str, Any]]:
    """Bit table of a mission's reason codes with funnel step, English text and the
    team module's own text (mission_scoring.py, verbatim)."""
    out = reason_entries(codes, engine_cfg)
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
                      codes: Dict[str, List[str]], comp_codes: Dict[str, Dict[str, List[str]]]) -> Dict[str, Any]:
    reg = ds.reg
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
                "reason_codes": reason_entries_v2(comp_codes[mid][cid], mission_cfg, cid, engine_cfg),
                "pass_counts": {"EARTH": int(cpass.sum()), "EARTH_LAND_CELLS": int(land.sum()),
                                "MOON": int(cres.moon_gates.passed.sum()), "MOON_CELLS": int(len(cres.moon_gates.passed)),
                                "EARTH_passing_both": int((cpass & passing).sum())},
                "top_failure_reasons": {"EARTH_LAND": top_reasons(_subset(cres.earth_gates, land), n_top),
                                        "MOON": top_reasons(cres.moon_gates, n_top)},
                "distributions": {"suitability": quantiles(cres.earth_suit.score[cpass], scd)},
                "columns_in": "earth_detail_*.bin: <mission>.<component>.fail_bits, .u.<variable>, .suitability",
            }
        sim_block: Dict[str, Any] = {"rule": res.rule}
        if res.rule == "zone_twin":
            z = res.extra["repo_context"].zones[mid]
            sim_block["zone"] = {k: z.get(k) for k in ("name", "kind", "lat_max", "source", "used", "reason", "cells", "regions")}
        if res.rule in ("zone_twin", "physical_pooled"):
            sim_block.update(twin_summary(res.twin_id[ranked], moon_ids))
        else:
            sim_block["twins"] = None
            sim_block["no_twin_reason"] = "repo_global_mean compares every Earth cell with the mean profile of the whole Moon (the repository's default target), so there is no lunar twin; twins ship when the team lead approves zone_twin (engine_config similarity_rule)."
        out.append({
            "id": mid, "title": titles.get(mid, mid), "description": m.get("description"), "author": m.get("author"),
            "threshold_status": status[mid], "provisional": bool(prov), "provisional_note": prov if prov else None,
            "frozen_at": m.get("frozen_at"), "components": comps,
            "on_missing_gate": mission_cfg.get("on_missing_gate"), "require_present": m.get("require_present", []),
            "files": {"EARTH": f"earth_{mid}.bin", "MOON": f"moon_{mid}.bin"},
            "gates": gate_rows(mission_cfg, mid, reg, engine_cfg),
            "weighted_variables": weighted_rows(mission_cfg, mid, reg, list(res.sim_vars)),
            "reason_codes": reason_entries_v2(codes[mid], mission_cfg, mid, engine_cfg),
            "pass_counts": {"EARTH": int(passing.sum()), "EARTH_LAND_CELLS": int(land.sum()),
                            "MOON": int(res.moon_gates.passed.sum()), "MOON_CELLS": int(len(res.moon_gates.passed))},
            "ranked_count": int(ranked.sum()),
            "passing_without_similarity": int((passing & ~ranked).sum()),
            "top_failure_reasons": {"EARTH_LAND": top_reasons(land_g, n_top), "MOON": top_reasons(res.moon_gates, n_top)},
            "missing_data": {"EARTH_LAND": missing_summary(land_g, suffix), "MOON": missing_summary(res.moon_gates, suffix)},
            "alpha": res.alpha,
            "similarity": sim_block,
            "confidence_counts": {k: int(sum(1 for c in res.confidence if c == k)) for k in CONF_CODES},
            "distributions": {
                "suitability": quantiles(res.earth_suit.score[passing], scd),
                "similarity": quantiles(res.similarity_pct[ranked], scd),
                "final": quantiles(res.final_published[ranked], scd),
                "confidence_score": quantiles(res.confidence_score[ranked], cd),
            },
            "component_results": comp_out,
            "known_limitations": list(notes.get(mid, [])),
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
        "funnel": FUNNEL_STEPS,
        "elimination_line_rule": "the cell's reason codes (fail_bits) in bit order, their 'text' joined with '; '",
        "confidence_codes": CONF_CODES,
        "missions": out,
    }


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


def build_similarity_json(ds: Dataset, results: Dict[str, MissionResult], engine_cfg: EngineConfig) -> Dict[str, Any]:
    """similarity.json: the active rule, the repository formula and every number it uses."""
    rule = similarity_rule(engine_cfg)
    first = next(iter(results.values()))
    ctx = first.extra.get("repo_context")
    base = {"bundle_version": engine_cfg.v("bundle_version"), "dataset": ds.id, "rule": rule,
            "rule_why": engine_cfg.similarity_rule.why, "rule_options": engine_cfg.v("similarity_rule_options"),
            "alpha": float(engine_cfg.v("mix_factor"))}
    if ctx is None:
        base["note"] = "physical_pooled rule: per-mission scales and variables are in missions.json"
        return base
    rs = engine_cfg.v("repo_similarity")
    sc = engine_cfg.v("similarity_columns")
    cols = {v: {b: e.get(b) for b in BODIES} for v, e in sc.items()}
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
    })
    if rule == "repo_global_mean":
        base["target"] = {"kind": "global_mean", "name": "Global Lunar Surface Mean (-90° to +90°)",
                          "profile": {f: ctx.target[f] for f in ctx.active},
                          "info_not_in_similarity": lunar_info_summary(ds, engine_cfg)}
        base["twins"] = None
        base["no_twin_reason"] = "repo_global_mean has no twin: the target is the mean profile of the whole Moon (the repository's default). Twins ship when similarity_rule is switched to zone_twin after the team lead approves docs/SIMILARITY_PROPOSAL.md."
    else:
        base["target"] = {"kind": "zone_twin", "tie_rule": engine_cfg.v("twin_tie_rule"),
                          "lunar_cells_filtered": False,
                          "zones": {m: {k: z.get(k) for k in ("name", "kind", "lat_max", "source", "used", "reason", "cells", "regions")}
                                    for m, z in ctx.zones.items()}}
    return base


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
                     moon_feat: Dict[str, list], feats: pd.DataFrame) -> Optional[Dict[str, Any]]:
    """twins.json (twin rules only): every distinct twin per mission with its z-scores,
    values, nearest IAU feature (name, distance, gazetteer URL) and Earth-cell count."""
    if not any(r.rule in ("zone_twin", "physical_pooled") for r in results.values()):
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
            if ctx is not None:
                row["z"] = {f: rnd(ctx.moon.z[f][p], zd) for f in ctx.active}
                row["values"] = {f: rnd(ctx.moon.values[f][p], 4) for f in ctx.active}
            info = {}
            for v in NOT_IN_SIMILARITY + list(ctx.excluded if ctx is not None else []):
                if v in moon.columns and v in ds.reg["variables"]:
                    x = moon[v].iat[p]
                    info[v] = (None if pd.isna(x) else str(x)) if ds.reg["variables"][v]["kind"] == "categorical" \
                        else rnd(x, _dec(engine_cfg, v))
            row["not_part_of_similarity"] = info
            row["feature"] = {"name": moon_feat["name"][p], "type": moon_feat["type"][p],
                              "distance_km": rnd(moon_feat["distance_km"][p], dkm),
                              "url": str(feats["link"].iat[fi]) if "link" in feats.columns else None}
            rows.append(row)
        out[mid] = {"rule": res.rule, **twin_summary(tw, moon["id"].to_numpy()), "twins": rows}
    return {"bundle_version": engine_cfg.v("bundle_version"), "dataset": ds.id,
            "gazetteer": "Gazetteer of Planetary Nomenclature (IAU WGPSN, USGS Astrogeology); 'url' is the feature's gazetteer page",
            "missions": out}


def build_explain_v2(results: Dict[str, MissionResult], ds: Dataset, mission_cfg: Dict, engine_cfg: EngineConfig,
                     earth_places: Dict[str, list], moon_feat: Dict[str, list]) -> Dict[str, Any]:
    """explain.json: the top-N ranked Earth cells per mission with the whole funnel."""
    n = int(engine_cfg.v("explain_top_n"))
    earth = ds.cells["EARTH"]
    ll, ud, scd, cd, dkm = (_dec(engine_cfg, k) for k in ("lat_lon", "utility", "score", "confidence_score", "distance_km"))
    out: Dict[str, Any] = {}
    for mid, res in results.items():
        ctx = res.extra.get("repo_context")
        order = [i for i in np.argsort(np.where(res.rank > 0, res.rank, np.iinfo(np.int64).max), kind="mergesort")
                 if res.rank[i] > 0][:n]
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
            if ctx is not None:
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
                "confidence": res.confidence[i],
                "confidence_score": rnd(res.confidence_score[i], cd),
            }
            for cid, cres in res.components.items():
                cp = bool(cres.earth_gates.passed[i])
                item.setdefault("components", {})[cid] = {
                    "pass": cp, "fail": [reason_texts(c, mission_cfg, cid)["text"] for c in cres.earth_gates.reasons[i]],
                    "suitability": rnd(cres.earth_suit.score[i], scd) if cp else None}
            items.append(item)
        out[mid] = items
    return {"bundle_version": engine_cfg.v("bundle_version"), "top_n": n, "missions": out}


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
            "natural_earth_polygon_geonames_code": "inside a polygon without an ISO code in that file: name from the polygon, code from the nearest GeoNames place",
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
    has_twins = rule in ("zone_twin", "physical_pooled")
    ctx = next(iter(results.values())).extra.get("repo_context") if results else None

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

    # --- per mission: map columns
    ud, scd, cd = qd["utility"], qd["score"], qd["confidence_score"]
    for mid, res in results.items():
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
                     description="0-100, the active similarity rule (similarity.json)")
        ef.quantised("final", res.final_published[idx], scd, "passing", description="0-100")
        rk = res.rank[idx]
        ef.i32("rank", rk, "passing", missing=rk <= 0, description="1 = best; missing when there is no similarity")
        if has_twins:
            tw = res.twin_id[idx]
            ef.i32("twin", tw, "passing", missing=tw < 0, description="lunar twin cell id (= moon_base.bin position)")
        conf = [res.confidence[i] for i in idx]
        ccode = np.array([CONF_CODES.index(c) if c is not None else 0 for c in conf], dtype=np.int64)
        ef.i32("confidence", ccode, "passing", missing=np.array([c is None for c in conf]),
               codes="missions.json confidence_codes")
        ef.quantised("confidence_score", _round_array(res.confidence_score[idx], cd), cd, "passing")
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
        if ctx is not None:
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
                                                 earth_places, codes, comp_codes), "start",
             "missions, funnel, gates, weights, reason codes, counts, components")
    add_json("similarity.json", build_similarity_json(ds, results, engine_cfg), "start",
             "the active similarity rule, its formula, variables, weights, per-body statistics and target")
    variables_obj = build_variables_v2(ds, mission_cfg, missions + comp_ids, stored, engine_cfg)
    variables_obj["lunar_info_columns"] = lunar_info_entries(engine_cfg)
    add_json("variables.json", variables_obj, "start",
             "per variable and body: column, level, source, licence, baseline, caveat, comparability")
    add_json("places.json", places_obj, "start", "Earth country and region tables indexed by earth_base.bin")
    add_json("place_detail.json", detail_obj, "on_demand", "label rules and nearest-place names indexed by earth_place_detail.bin")
    twins = build_twins_json(ds, results, engine_cfg, moon_feat, feats)
    if twins is not None:
        add_json("twins.json", twins, "on_demand", "every distinct lunar twin per mission: z-scores, values, IAU feature, Earth-cell count")
    add_json("explain.json", build_explain_v2(results, ds, mission_cfg, engine_cfg, earth_places, moon_feat),
             "on_demand", "top-N ranked Earth cells per mission with the whole funnel")
    add_json("iau_moon_features.json", build_iau_features(feats, engine_cfg, iau_source), "on_demand",
             "IAU lunar features (non-satellite), indexed by moon_base.bin 'feature'")
    sites = build_named_sites(engine_cfg, ds, results, codes, mission_cfg)
    if sites is not None:
        add_json("lunar_named_sites.json", sites, "on_demand", "named lunar sites, their cell and per-mission outcome")
    add_json("validity.json", validity, "on_demand", "schema validation report of the input tables")

    order = ["missions.json", "similarity.json", "variables.json", "places.json", "earth_base.bin",
             f"earth_{missions[0]}.bin"] + [f"earth_{m}.bin" for m in missions[1:]] + [t["name"] for t in tiles] + \
        ["moon_base.bin"] + [f"moon_{m}.bin" for m in missions] + \
        ["twins.json", "earth_place_detail.bin", "place_detail.json", "explain.json", "iau_moon_features.json",
         "lunar_named_sites.json", "validity.json"]
    order = [n for n in order if n in files]
    first = [n for n in order if meta[n]["load"] == "start"]
    budget = engine_cfg.v("first_view_budget_bytes")
    radii = engine_cfg.v("body_radius_km")
    data_credits = sorted({reg["variables"][v]["bodies"][b].get("licence_credit") or "" for v in eng_vars for b in BODIES} - {""})
    manifest = {
        "bundle_version": engine_cfg.v("bundle_version"),
        "contract_revision": 3,
        "engine_version": engine_cfg.v("engine_version"),
        "dataset": {"id": ds.id, "why": engine_cfg.dataset.why},
        "build_time": build_time,
        "similarity_rule": rule,
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
    files["manifest.json"] = dumps(manifest)
    objs["manifest.json"] = manifest
    return files, objs, manifest


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
