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


def browser_scores(u: Dict[str, np.ndarray], s: Dict[str, np.ndarray], weights: Dict[str, float],
                   order: List[str], alpha: float):
    """DATA_CONTRACT recompute formulas on decoded arrays, summing in ``order`` (the
    mission's weighted-variable order). Returns (suitability, similarity, final)."""
    n = len(next(iter(u.values())))
    un, ud, sn, sd = np.zeros(n), np.zeros(n), np.zeros(n), np.zeros(n)
    for v in order:
        if v in u:
            ok = np.isfinite(u[v])
            un = un + np.where(ok, weights[v] * np.where(ok, u[v], 0.0), 0.0)
            ud = ud + np.where(ok, weights[v], 0.0)
        if v in s:
            ok = np.isfinite(s[v])
            sn = sn + np.where(ok, weights[v] * np.where(ok, s[v], 0.0), 0.0)
            sd = sd + np.where(ok, weights[v], 0.0)
    suit = np.where(ud > 0, 100.0 * un / np.where(ud > 0, ud, 1.0), np.nan)
    sim = np.where(sd > 0, 100.0 * sn / np.where(sd > 0, sd, 1.0), np.nan)
    return suit, sim, alpha * sim + (1.0 - alpha) * suit


def rank_rule(final: np.ndarray, ids: np.ndarray) -> np.ndarray:
    """1..n by final descending, ties by id ascending; 0 where final is NaN."""
    ok = np.isfinite(final)
    order = np.lexsort((ids, -np.where(ok, final, -np.inf)))
    order = order[ok[order]]
    r = np.zeros(len(final), dtype=np.int64)
    r[order] = np.arange(1, len(order) + 1)
    return r


def validate_bundle_v2(path: str, weights: Optional[Dict[str, Dict[str, float]]] = None) -> Dict[str, Any]:
    """Check hashes, column layout, cross-file consistency and the exact recompute of
    suitability, similarity, final and rank for every passing cell of every mission.
    ``weights`` defaults to each mission's published weights."""
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
    land_n = b.file_entry("earth_base.bin")["row_sets"]["land"]
    earth_ids = b.int_column("earth_base.bin", "id")
    if np.any(np.diff(earth_ids) <= 0):
        raise ValueError("earth_base.bin ids are not increasing")
    checked = 0
    for m in missions["missions"]:
        ef, mf = m["files"]["EARTH"], m["files"]["MOON"]
        bits = b.int_column(ef, "fail_bits")
        li = b.int_column(ef, "land_index")
        if len(bits) != land_n or not np.array_equal(np.flatnonzero(bits == 0), li):
            raise ValueError(f"{m['id']}: passing cells and fail bits disagree")
        if int((bits == 0).sum()) != m["pass_counts"]["EARTH"]:
            raise ValueError(f"{m['id']}: Earth pass count")
        mbits = b.int_column(mf, "fail_bits")
        if int((mbits == 0).sum()) != m["pass_counts"]["MOON"]:
            raise ValueError(f"{m['id']}: Moon pass count")
        twin = b.int_column(ef, "twin")
        sent = man["encoding"]["int32_missing"]
        has_twin = twin != sent
        if np.any(mbits[twin[has_twin]] != 0):
            raise ValueError(f"{m['id']}: a twin fails the mission on the Moon")
        tc = b.int_column(mf, "twin_count")
        if int(tc.sum()) != int(has_twin.sum()):
            raise ValueError(f"{m['id']}: twin counts do not add up")
        order = [w["variable"] for w in m["weighted_variables"]]
        w = (weights or {}).get(m["id"]) or {x["variable"]: x["weight"] for x in m["weighted_variables"]}
        u = {v: b.column(ef, f"u.{v}") for v in order}
        s = {v: b.column(ef, f"s.{v}") for v in m["similarity_variables"]}
        for v in m["excluded_from_similarity"]:
            if f"s.{v}" in b.columns(ef):
                raise ValueError(f"{m['id']}: excluded variable {v} has similarities")
        suit, sim, fin = browser_scores(u, s, w, order, m["mix_factor"])
        st_suit, st_sim = b.column(ef, "suitability"), b.column(ef, "similarity")
        st_fin, st_rank = b.column(ef, "final"), b.int_column(ef, "rank")
        if weights is None:
            for name, mine, stored in (("suitability", suit, st_suit), ("similarity", sim, st_sim), ("final", fin, st_fin)):
                mr = np.array([round(float(x), 2) if np.isfinite(x) else np.nan for x in mine])
                if not np.array_equal(np.isnan(mr), np.isnan(stored)) or np.any(mr[np.isfinite(mr)] != stored[np.isfinite(stored)]):
                    raise ValueError(f"{m['id']}: recomputed {name} differs from the stored value")
            fr = np.array([round(float(x), 2) if np.isfinite(x) else np.nan for x in fin])
            ids = earth_ids[li]
            rr = rank_rule(fr, ids)
            if not np.array_equal(np.where(st_rank == sent, 0, st_rank), rr):
                raise ValueError(f"{m['id']}: stored rank does not follow the rank rule")
            if not np.array_equal(np.isnan(st_fin), ~has_twin):
                raise ValueError(f"{m['id']}: final must be missing exactly when there is no twin")
        checked += len(li)
    return {"ok": True, "cells_checked": checked, "files": [f["name"] for f in man["files"]]}
