"""Reading and checking a v2 bundle with numpy (the same steps the browser takes).

    from engine.bundle_v2 import load_bundle, validate_bundle_v2
    b = load_bundle("../app/public/data/v2")
    u = b.column("earth_rover.bin", "u.slope_300m_deg")      # float64, NaN = missing
    validate_bundle_v2("../app/public/data/v2")              # raises on the first problem

Decoding rules (docs/DATA_CONTRACT.md): little-endian; float32 NaN = missing; int32
-2147483648 = missing; a column with 'divisor' holds q and value = q / divisor.
"""
from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import numpy as np


@dataclass
class Bundle:
    """A v2 bundle folder with its manifest."""

    path: str
    manifest: Dict[str, Any]

    def file_entry(self, name: str) -> Dict[str, Any]:
        for f in self.manifest["files"]:
            if f["name"] == name:
                return f
        raise KeyError(name)

    def json(self, name: str) -> Any:
        with open(os.path.join(self.path, name), encoding="utf-8") as fh:
            return json.load(fh)

    def raw_column(self, file: str, column: str) -> np.ndarray:
        """The stored array as written (float32 or int32), no decoding."""
        entry = self.file_entry(file)
        col = next((c for c in entry["columns"] if c["name"] == column), None)
        if col is None:
            raise KeyError(f"{file}: no column {column}")
        dtype = "<f4" if col["type"] == "float32" else "<i4"
        with open(os.path.join(self.path, file), "rb") as fh:
            fh.seek(col["offset"])
            data = fh.read(4 * col["length"])
        return np.frombuffer(data, dtype=dtype).copy()

    def column(self, file: str, column: str) -> np.ndarray:
        """Decoded column: float64 with NaN for missing (quantised columns divided by
        their divisor); integer columns without a divisor stay int64 with the sentinel
        replaced by -1 only when the caller asks via :meth:`int_column`."""
        entry = self.file_entry(file)
        col = next(c for c in entry["columns"] if c["name"] == column)
        a = self.raw_column(file, column)
        if col["type"] == "float32":
            return a.astype(np.float64)
        miss = a == self.manifest["encoding"]["int32_missing"]
        if col.get("divisor"):
            return np.where(miss, np.nan, a.astype(np.float64) / col["divisor"])
        return np.where(miss, np.nan, a.astype(np.float64))

    def int_column(self, file: str, column: str) -> np.ndarray:
        """Integer column as int64; the missing sentinel stays as it is."""
        return self.raw_column(file, column).astype(np.int64)

    def columns(self, file: str) -> List[str]:
        return [c["name"] for c in self.file_entry(file)["columns"]]


def load_bundle(path: str) -> Bundle:
    with open(os.path.join(path, "manifest.json"), encoding="utf-8") as fh:
        return Bundle(path=path, manifest=json.load(fh))


def browser_suitability(u: Dict[str, np.ndarray], weights: Dict[str, float], order: List[str]) -> np.ndarray:
    """DATA_CONTRACT step 4 on decoded utilities: 100 * sum(w*u) / sum(w with a utility),
    summed in ``order`` (the mission's weighted-variable order)."""
    n = len(next(iter(u.values())))
    un, ud = np.zeros(n), np.zeros(n)
    for v in order:
        ok = np.isfinite(u[v])
        un = un + np.where(ok, weights[v] * np.where(ok, u[v], 0.0), 0.0)
        ud = ud + np.where(ok, weights[v], 0.0)
    return np.where(ud > 0, 100.0 * un / np.where(ud > 0, ud, 1.0), np.nan)


def browser_similarity(ez: Dict[str, np.ndarray], mz: Dict[str, np.ndarray], norm_w: Dict[str, float],
                       decay: float) -> np.ndarray:
    """DATA_CONTRACT step 5 on decoded z-scores (similarity.json formula), summed in the
    order of ``norm_w``: d^2 = sum(norm_w * diff^2) when every variable is present, else
    that sum / sum(norm_w present); similarity = round(100 * exp(-decay * d), 2)."""
    sq = wsum = full = None
    for f, w in norm_w.items():
        diff = np.asarray(ez[f], dtype=np.float64) - np.asarray(mz[f], dtype=np.float64)
        ok = np.isfinite(diff)
        part = np.where(ok, w * np.where(ok, diff, 0.0) ** 2, 0.0)
        sq = part if sq is None else sq + part
        wsum = np.where(ok, w, 0.0) if wsum is None else wsum + np.where(ok, w, 0.0)
        full = ok if full is None else full & ok
    d2 = np.where(full, sq, np.where(wsum > 0, sq / np.where(wsum > 0, wsum, 1.0), np.nan))
    return np.round(100.0 * np.exp(-decay * np.sqrt(d2)), 2)


def browser_real_similarity(s: Dict[str, np.ndarray], weights: Dict[str, float], order: List[str]) -> np.ndarray:
    """Real-value rule on decoded per-variable scores (DATA_CONTRACT): 100 * sum(w * s) /
    sum(w over the variables with a score), summed in ``order``; NaN without any score."""
    n = len(next(iter(s.values())))
    num, den = np.zeros(n), np.zeros(n)
    for v in order:
        ok = np.isfinite(s[v])
        num = num + np.where(ok, weights[v] * np.where(ok, s[v], 0.0), 0.0)
        den = den + np.where(ok, weights[v], 0.0)
    return np.where(den > 0, 100.0 * num / np.where(den > 0, den, 1.0), np.nan)


def list_order_rule(rank: np.ndarray, suitability: np.ndarray, ids: np.ndarray) -> np.ndarray:
    """1..n: cells with a rank by rank, then the others by suitability descending, ties by id."""
    paired = np.flatnonzero(rank > 0)
    paired = paired[np.argsort(rank[paired], kind="mergesort")]
    un = np.flatnonzero(rank <= 0)
    un = un[np.lexsort((ids[un], -suitability[un]))]
    out = np.zeros(len(rank), dtype=np.int64)
    seq = np.concatenate([paired, un])
    out[seq] = np.arange(1, seq.size + 1)
    return out


def tile_column(b: "Bundle", name: str) -> np.ndarray:
    """A detail-tile column over every Earth land cell (tiles concatenated in order)."""
    parts = [b.column(t["name"], name) for t in b.manifest["detail_tiles"]["files"]]
    return np.concatenate(parts)


def tile_int_column(b: "Bundle", name: str) -> np.ndarray:
    parts = [b.int_column(t["name"], name) for t in b.manifest["detail_tiles"]["files"]]
    return np.concatenate(parts)


def rank_rule(final: np.ndarray, ids: np.ndarray) -> np.ndarray:
    """1..n by final descending, ties by id ascending; 0 where final is NaN."""
    ok = np.isfinite(final)
    order = np.lexsort((ids, -np.where(ok, final, -np.inf)))
    order = order[ok[order]]
    r = np.zeros(len(final), dtype=np.int64)
    r[order] = np.arange(1, len(order) + 1)
    return r


def validate_bundle_v2(path: str, weights: Optional[Dict[str, Dict[str, float]]] = None,
                       sim_weights: Optional[Dict[str, Dict[str, float]]] = None) -> Dict[str, Any]:
    """Check hashes, column layout, cross-file consistency and the exact recompute of
    suitability, similarity, final and rank for every passing cell of every mission,
    from the bundle alone. ``weights`` defaults to each mission's published weights;
    ``sim_weights`` (real-value missions) to the published similarity weights. With
    slider weights the function returns the recomputed values instead of comparing them
    with the stored ones (``recomputed``)."""
    b = load_bundle(path)
    man = b.manifest
    for f in man["files"]:
        data = open(os.path.join(path, f["name"]), "rb").read()
        if len(data) != f["bytes"] or hashlib.sha256(data).hexdigest() != f["sha256"]:
            raise ValueError(f"manifest size/hash mismatch for {f['name']}")
        if f["format"] == "bin":
            end = 0
            for c in f["columns"]:
                if c["offset"] != end or c["length"] != f["row_sets"][c["rows"]]:
                    raise ValueError(f"{f['name']}:{c['name']}: offset/length do not follow the index")
                end = c["offset"] + 4 * c["length"]
            if end != len(data):
                raise ValueError(f"{f['name']}: columns do not cover the file")
    missions = b.json("missions.json")
    sim_json = b.json("similarity.json")
    land_n = b.file_entry("earth_base.bin")["row_sets"]["land"]
    earth_ids = b.int_column("earth_base.bin", "id")
    if np.any(np.diff(earth_ids) <= 0):
        raise ValueError("earth_base.bin ids are not increasing")
    if not np.array_equal(tile_int_column(b, "id"), earth_ids):
        raise ValueError("detail tiles do not cover the land cells in id order")
    rule = sim_json["rule"]
    rules = sim_json.get("rules") or {m["id"]: rule for m in missions["missions"]}
    sent = man["encoding"]["int32_missing"]
    has_z = "variables" in sim_json
    norm_w = {v["variable"]: v["norm_weight"] for v in sim_json["variables"] if v["status"] == "active"} if has_z else {}
    decay = sim_json["formula"]["decay"] if has_z else None
    ez = {f: tile_column(b, f"z.{f}") for f in norm_w}
    twins = b.json("twins.json") if any(r in ("zone_twin", "real_value_tolerance", "percentile_and_real_tolerance") for r in rules.values()) else None
    checked = 0
    recomputed: Dict[str, Dict[str, np.ndarray]] = {}
    for m in missions["missions"]:
        mid = m["id"]
        rule = rules[mid]
        ef, mf = m["files"]["EARTH"], m["files"]["MOON"]
        bits = b.int_column(ef, "fail_bits")
        li = b.int_column(ef, "land_index")
        if len(bits) != land_n or not np.array_equal(np.flatnonzero(bits == 0), li):
            raise ValueError(f"{mid}: passing cells and fail bits disagree")
        if int((bits == 0).sum()) != m["pass_counts"]["EARTH"]:
            raise ValueError(f"{mid}: Earth pass count")
        if int((b.int_column(mf, "fail_bits") == 0).sum()) != m["pass_counts"]["MOON"]:
            raise ValueError(f"{mid}: Moon pass count")
        order = [w["variable"] for w in m["weighted_variables"]]
        w = (weights or {}).get(mid) or {x["variable"]: x["weight"] for x in m["weighted_variables"]}
        u = {v: tile_column(b, f"{mid}.u.{v}")[li] for v in order}
        for v in order:  # utilities exist only for passing cells
            full = tile_column(b, f"{mid}.u.{v}")
            if np.any(np.isfinite(full[bits != 0])):
                raise ValueError(f"{mid}: an eliminated cell has a utility for {v}")
        suit = browser_suitability(u, w, order)
        if rule == "repo_global_mean":
            tz = {f: np.float64(next(x for x in sim_json["variables"] if x["variable"] == f)["target_global_mean"]["z"])
                  for f in norm_w}
            sim = browser_similarity({f: ez[f][li] for f in norm_w}, tz, norm_w, decay)
            mz = {f: np.full(len(li), tz[f]) for f in norm_w}
            if "twin" in b.columns(ef):
                raise ValueError(f"{mid}: repo_global_mean must not carry twins")
        elif rule == "zone_twin":
            twin = b.int_column(ef, "twin")
            tz_by_id = {t["id"]: t["z"] for t in twins["missions"][mid]["twins"]}
            mz = {f: np.array([tz_by_id[int(t)][f] if t != sent and tz_by_id[int(t)][f] is not None else np.nan
                               for t in twin], dtype=np.float64) for f in norm_w}
            sim = browser_similarity({f: ez[f][li] for f in norm_w}, mz, norm_w, decay)
            tc = b.int_column(mf, "twin_count")
            if int(tc.sum()) != int((twin != sent).sum()):
                raise ValueError(f"{mid}: twin counts do not add up")
            zone = sim_json["target"]["zones"][mid]
            if zone.get("lat_max") is not None and zone["kind"] == "lat_max":
                lat = b.column("moon_base.bin", "lat")
                if np.any(lat[twin[twin != sent] // man["grid"]["cols"]] > zone["lat_max"]):
                    raise ValueError(f"{mid}: a twin lies outside its zone")
        elif rule in ("real_value_tolerance", "percentile_and_real_tolerance"):
            sim, twin = _check_real_mission(b, m, li, earth_ids, twins, sent, sim_weights)
            mz = None
        else:
            raise ValueError(f"validate_bundle_v2 does not check rule {rule!r}")
        if "sim_missing_bits" in b.columns(ef) and rule not in ("real_value_tolerance", "percentile_and_real_tolerance"):  # contract revision 4: variables used per pair
            ok = {f: np.isfinite(ez[f][li]) & np.isfinite(mz[f]) for f in norm_w}
            want_bits = sum(np.where(ok[f], 0, 1 << k) for k, f in enumerate(sim_json["active_variables"]))
            want_n = sum(ok[f].astype(np.int64) for f in sim_json["active_variables"])
            if not (np.array_equal(b.int_column(ef, "sim_missing_bits"), want_bits)
                    and np.array_equal(b.int_column(ef, "sim_vars_used"), want_n)):
                raise ValueError(f"{mid}: similarity variables used / missing disagree with the z-scores")
        alpha = m["alpha"]
        fin = alpha * sim + (1.0 - alpha) * suit
        st_suit, st_sim = b.column(ef, "suitability"), b.column(ef, "similarity")
        st_fin, st_rank = b.column(ef, "final"), b.int_column(ef, "rank")
        if weights is not None or sim_weights is not None:
            fr = np.array([round(float(x), 2) if np.isfinite(x) else np.nan for x in fin])
            recomputed[mid] = {"suitability": suit, "similarity": sim, "final": fin, "rank": rank_rule(fr, earth_ids[li])}
        if weights is None and sim_weights is None:
            for name, mine, stored in (("suitability", suit, st_suit), ("similarity", sim, st_sim), ("final", fin, st_fin)):
                mr = np.array([round(float(x), 2) if np.isfinite(x) else np.nan for x in mine])
                if not np.array_equal(np.isnan(mr), np.isnan(stored)) or np.any(mr[np.isfinite(mr)] != stored[np.isfinite(stored)]):
                    raise ValueError(f"{mid}: recomputed {name} differs from the stored value")
            fr = np.array([round(float(x), 2) if np.isfinite(x) else np.nan for x in fin])
            rr = rank_rule(fr, earth_ids[li])
            if not np.array_equal(np.where(st_rank == sent, 0, st_rank), rr):
                raise ValueError(f"{mid}: stored rank does not follow the rank rule")
        checked += len(li)
    if weights is None and sim_weights is None:
        _check_pair_sentences(b, missions, sim_json, earth_ids, sent)
    return {"ok": True, "cells_checked": checked, "rule": sim_json["rule"], "rules": rules,
            "files": [f["name"] for f in man["files"]], "recomputed": recomputed}


def _check_pair_sentences(b: Bundle, missions: Dict[str, Any], sim_json: Dict[str, Any], earth_ids: np.ndarray,
                          sent: int) -> None:
    """Per-pair templates (similarity.json texts with placeholders read from a pairs file):
    every placeholder can be filled on every pair, with the browser's display rounding
    (engine/display.py; the solar share lost from the two displayed values), and the
    sentence the engine wrote in explain.json is the template filled from the binary
    columns (wording and display rounding, 2026-11-15)."""
    from engine.display import SHARE_LOST_RULE, fill_placeholder, share_lost_percent

    explain = b.json("explain.json")["missions"] if any(f["name"] == "explain.json" for f in b.manifest["files"]) else {}
    for m in missions["missions"]:
        mid = m["id"]
        ef = m["files"]["EARTH"]
        if "twin" not in b.columns(ef):
            continue
        paired = np.flatnonzero(b.int_column(ef, "twin") != sent)
        for key, t in (sim_json.get("texts") or {}).items():
            ms = t.get("missions") or ([t["mission"]] if t.get("mission") else [])
            specs = {n: p for n, p in (t.get("placeholders") or {}).items() if isinstance(p, dict) and "file" in p}
            if mid not in ms or not specs or not any(f["name"] == next(iter(specs.values()))["file"] for f in b.manifest["files"]):
                continue
            need = sorted({c for p in specs.values() for c in (p["columns"].values() if "columns" in p else [p["column"]])})
            cols = {c: b.column(next(iter(specs.values()))["file"], c) for c in need}
            for name, p in specs.items():
                if p.get("rule") == SHARE_LOST_RULE:
                    a, g = cols[p["columns"]["above"]], cols[p["columns"]["ground"]]
                    for i in paired:
                        share_lost_percent(a[i], g[i])          # raises when a value is missing or displays as 0.0
                elif not np.all(np.isfinite(cols[p["column"]][paired])):
                    raise ValueError(f"{mid}: texts.{key} {{{name}}} has no value on a pair")
            li = b.int_column(ef, "land_index")
            pos = {int(e): k for k, e in enumerate(earth_ids[li])}
            for it in explain.get(mid, []):
                if it.get("similarity", {}).get("pair_sentence") is None:
                    raise ValueError(f"{mid}: explain.json item {it['id']} has no pair_sentence (texts.{key})")
                k = pos[int(it["id"])]
                text = t["text"]
                for name, p in specs.items():
                    if "display_rule" in t or "rule" in p:
                        x = fill_placeholder(p, {c: float(v[k]) for c, v in cols.items()})
                    else:  # the engine's earlier formatting (lunar_base_pair_sentence)
                        x = f"{float(cols[p['column']][k]) * float(p.get('multiply', 1.0)) - float(p.get('subtract', 0.0)):.{int(p['decimals'])}f}"
                    text = text.replace("{" + name + "}", x)
                if text != it["similarity"]["pair_sentence"]:
                    raise ValueError(f"{mid}: explain.json pair_sentence of {it['id']} is not texts.{key} filled from the bundle")


def _check_real_mission(b: Bundle, m: Dict[str, Any], li: np.ndarray, earth_ids: np.ndarray, twins: Dict,
                        sent: int, sim_weights: Optional[Dict[str, Dict[str, float]]]):
    """Real-value mission: similarity from the published scores, pair bounds, twins in the
    zone, twin counts, reasons for the cells without a twin, list order. Returns
    (recomputed similarity, twin ids)."""
    mid = m["id"]
    ef, mf = m["files"]["EARTH"], m["files"]["MOON"]
    sb = m["similarity"]
    vars_ = sb["variables"]
    order = [v["variable"] for v in vars_]
    w = (sim_weights or {}).get(mid) or {v["variable"]: v["weight"] for v in vars_}
    sc = {v: b.column(ef, f"s.{v}") for v in order}
    twin = b.int_column(ef, "twin")
    paired = twin != sent
    sim = np.where(paired, browser_real_similarity(sc, w, order), np.nan)
    for v in order:
        if np.any(np.isfinite(sc[v][~paired])):
            raise ValueError(f"{mid}: a cell without a twin has a score for {v}")
    pf = sb["pairs_file"]
    for v in vars_:
        cc = v.get("compared_columns") or v["pairs_columns"]      # percentile variables: compared as percentiles
        d = b.column(pf, cc["diff"])
        e, mo = b.column(pf, cc["earth"]), b.column(pf, cc["moon"])
        fin = np.isfinite(d)
        if np.any(fin & ~paired):
            raise ValueError(f"{mid}: a cell without a twin has a difference for {v['variable']}")
        tol = 1e-6 * max(1.0, float(v["bound"]))
        if np.any(d[fin] > v["bound"] + tol):  # stored as float32; the engine checks in double precision
            raise ValueError(f"{mid}: {v['variable']} exceeds its bound on a pair")
        if v["role"] == "key" and np.any(paired & ~fin):
            raise ValueError(f"{mid}: a pair lacks its key variable {v['variable']}")
        if np.any(np.abs(np.abs(e - mo)[fin] - d[fin]) > 1e-3 * np.maximum(1.0, np.abs(e[fin]))):
            raise ValueError(f"{mid}: stored difference of {v['variable']} disagrees with the two values")
    tc = b.int_column(mf, "twin_count")
    if int(tc.sum()) != int(paired.sum()):
        raise ValueError(f"{mid}: twin counts do not add up")
    tz = {t["id"] for t in twins["missions"][mid]["twins"]}
    if not set(int(t) for t in twin[paired]) <= tz:
        raise ValueError(f"{mid}: a twin is missing from twins.json")
    zone = sb["zone"]
    lat = b.column("moon_base.bin", "lat")
    cols = b.manifest["grid"]["cols"]
    tl = lat[twin[paired] // cols]
    if zone["kind"] == "lat_max" and np.any(tl > zone["lat_max"]):
        raise ValueError(f"{mid}: a twin lies outside its zone")
    if zone["kind"] == "similarity_zone" and "region" in b.columns("moon_base.bin"):
        mz = b.json("mission_zones.json")
        codes = [r["code"] for r in mz["regions"]]
        allowed = [codes.index(c) for c in mz["mission_zone_regions"][mid]]
        if not np.all(np.isin(b.int_column("moon_base.bin", "region")[twin[paired]], allowed)):
            raise ValueError(f"{mid}: a twin lies outside its zone")
    if zone["kind"] == "abs_lat_max_elevation_max":
        el = b.column("moon_base.bin", f"v.{zone['elevation_column']}")[twin[paired]]
        if np.any(np.abs(tl) > zone["abs_lat_max"]) or np.any(el > zone["elevation_max_m"]):
            raise ValueError(f"{mid}: a twin lies outside its zone")
    nk = b.int_column(pf, "nopair_kind")
    if not np.array_equal(nk == sent, paired):
        raise ValueError(f"{mid}: no-pair reasons must be set exactly on the cells without a twin")
    if sb["paired_count"] != int(paired.sum()) or sb["unpaired_count"] != int((~paired).sum()):
        raise ValueError(f"{mid}: paired / unpaired counts")
    st_rank = b.int_column(ef, "rank")
    if np.any((st_rank != sent) != paired):
        raise ValueError(f"{mid}: only paired cells are ranked")
    suit = b.column(ef, "suitability")
    lo = list_order_rule(np.where(st_rank == sent, 0, st_rank), suit, earth_ids[li])
    if not np.array_equal(b.int_column(pf, "list_order"), lo):
        raise ValueError(f"{mid}: list order does not follow the rule")
    return sim, twin
