"""Auditor's own helpers for points 8 and 9 (p4_*): bundle reader, geodesy, percentiles,
TOA insolation and the pair rule, written from docs/DATA_CONTRACT.md (revision 6) and the
method text, WITHOUT importing the engine (independent code path).

Nothing here writes to the repository except under tierra luna/audit/out/.
"""
from __future__ import annotations

import json
import math
import os
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
BUNDLE = os.path.join(REPO, "app", "public", "data", "v2")
TABLES = os.path.join(REPO, "tierra luna", "output_real")
ENGINE_DATA = os.path.join(REPO, "tierra luna", "engine", "data")
OUT = os.path.join(HERE, "out")
R_EARTH = 6371.0
R_MOON = 1737.4
INT32_MISSING = -2147483648


# ----------------------------------------------------------------------------- bundle reader
class Bundle:
    """Reads the static bundle with the manifest's column index only (contract rev. 6)."""

    def __init__(self, path: str = BUNDLE):
        self.path = path
        self.manifest = self.json("manifest.json")
        assert self.manifest["contract_revision"] == 6, self.manifest["contract_revision"]
        self._files = {f["name"]: f for f in self.manifest["files"]}

    def json(self, name: str):
        with open(os.path.join(self.path, name), encoding="utf-8") as fh:
            return json.load(fh)

    def columns(self, file: str) -> List[str]:
        return [c["name"] for c in self._files[file]["columns"]]

    def col(self, file: str, name: str) -> np.ndarray:
        c = next(c for c in self._files[file]["columns"] if c["name"] == name)
        dt = "<f4" if c["type"] == "float32" else "<i4"
        raw = np.fromfile(os.path.join(self.path, file), dtype=dt, count=c["length"], offset=c["offset"])
        if c["type"] == "int32":
            out = raw.astype(np.float64)
            out[raw == INT32_MISSING] = np.nan
            if c.get("divisor"):
                out = out / float(c["divisor"])
            return out
        return raw.astype(np.float64)

    def raw_f32(self, file: str, name: str) -> np.ndarray:
        c = next(c for c in self._files[file]["columns"] if c["name"] == name)
        return np.fromfile(os.path.join(self.path, file), dtype="<f4", count=c["length"], offset=c["offset"])


# ----------------------------------------------------------------------------- tables
def load_tables() -> Tuple[pd.DataFrame, pd.DataFrame]:
    e = pd.read_csv(os.path.join(TABLES, "earth_real_1deg.csv"), low_memory=False)
    m = pd.read_csv(os.path.join(TABLES, "moon_real_1deg.csv"), low_memory=False)
    for d in (e, m):
        d["id"] = d["row"] * 360 + d["col"]
        assert (d["id"].values == np.arange(64800)).all()
    return e, m


def cell_latlon(cid: int) -> Tuple[float, float]:
    r, c = divmod(int(cid), 360)
    return 90.0 - (r + 0.5), -180.0 + (c + 0.5)


# ----------------------------------------------------------------------------- geodesy
def haversine_km(lat1, lon1, lat2, lon2, R):
    p1, p2 = np.radians(lat1), np.radians(lat2)
    dl = np.radians(np.asarray(lon2, dtype=float) - np.asarray(lon1, dtype=float))
    a = np.sin((p2 - p1) / 2) ** 2 + np.cos(p1) * np.cos(p2) * np.sin(dl / 2) ** 2
    return 2 * R * np.arcsin(np.sqrt(np.clip(a, 0, 1)))


def initial_bearing_deg(lat1, lon1, lat2, lon2) -> float:
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dl = math.radians(lon2 - lon1)
    x = math.sin(dl) * math.cos(p2)
    y = math.cos(p1) * math.sin(p2) - math.sin(p1) * math.cos(p2) * math.cos(dl)
    return (math.degrees(math.atan2(x, y)) + 360.0) % 360.0


COMPASS8 = ["north", "northeast", "east", "southeast", "south", "southwest", "west", "northwest"]


def compass8(b: float) -> str:
    return COMPASS8[int(((b + 22.5) % 360) // 45)]


# ----------------------------------------------------------------------------- statistics
def midrank_pct(values: np.ndarray) -> np.ndarray:
    """100 * (rank - 0.5) / n with ties averaged, NaN kept out (own implementation)."""
    v = np.asarray(values, dtype=float)
    out = np.full(v.shape, np.nan)
    ok = ~np.isnan(v)
    x = v[ok]
    n = x.size
    order = np.argsort(x, kind="mergesort")
    xs = x[order]
    ranks = np.empty(n)
    i = 0
    while i < n:
        j = i
        while j + 1 < n and xs[j + 1] == xs[i]:
            j += 1
        ranks[order[i:j + 1]] = (i + j) / 2.0 + 1.0
        i = j + 1
    out[ok] = 100.0 * (ranks - 0.5) / n
    return out


def pct_of_value_in(pop: np.ndarray, value: float) -> float:
    """Mid-rank percentile that `value` would have inside `pop` (share below + half the ties)."""
    p = pop[~np.isnan(pop)]
    below = np.sum(p < value)
    eq = np.sum(p == value)
    return 100.0 * (below + 0.5 * eq) / p.size


# ----------------------------------------------------------------------------- TOA insolation
def toa_kwh_m2_day(lat_deg: np.ndarray, S0=1361.0, obl=23.44, ecc=0.0167, lam_peri=282.9, n=36500) -> np.ndarray:
    """Annual-mean daily TOA insolation on a horizontal surface (own code, Kepler orbit,
    mean anomaly uniform in time; 10x the engine's sample count to show convergence)."""
    M = (np.arange(n) + 0.5) / n * 2 * np.pi
    E = M.copy()
    for _ in range(50):
        E = E - (E - ecc * np.sin(E) - M) / (1 - ecc * np.cos(E))
    nu = 2 * np.arctan2(np.sqrt(1 + ecc) * np.sin(E / 2), np.sqrt(1 - ecc) * np.cos(E / 2))
    r = 1 - ecc * np.cos(E)
    lam = nu + np.radians(lam_peri)
    dec = np.arcsin(np.sin(np.radians(obl)) * np.sin(lam))
    out = []
    for la in np.atleast_1d(lat_deg):
        phi = np.radians(la)
        c = np.clip(-np.tan(phi) * np.tan(dec), -1, 1)
        h0 = np.arccos(c)
        Q = S0 / np.pi / r ** 2 * (h0 * np.sin(phi) * np.sin(dec) + np.cos(phi) * np.cos(dec) * np.sin(h0))
        out.append(Q.mean() * 24 / 1000)
    return np.array(out)


# ----------------------------------------------------------------------------- pair rule
def pair_all(E: np.ndarray, Mz: np.ndarray, mz_ids: np.ndarray, tol, roles, weights):
    """Own implementation of the pair rule.
    E: (nE, k) Earth compared values; Mz: (nZ, k) zone values; returns twin id (or -1),
    similarity (unrounded, 0-100) and per-variable scores of the twin.
    Filter: key |d| <= tol, secondary |d| <= 2 tol; a secondary missing on a side is dropped
    (weights renormalised); a key missing fails. Twin: highest similarity, ties lowest id."""
    tol = np.asarray(tol, float)
    w = np.asarray(weights, float)
    mult = np.array([1.0 if r == "key" else 2.0 for r in roles])
    iskey = np.array([r == "key" for r in roles])
    order = np.argsort(mz_ids)
    Mz = Mz[order]
    ids = mz_ids[order]
    nE = E.shape[0]
    twin = np.full(nE, -1, dtype=np.int64)
    sim = np.full(nE, np.nan)
    scores = np.full((nE, len(tol)), np.nan)
    for i in range(nE):
        e = E[i]
        if np.any(np.isnan(e[iskey])):
            continue
        d = np.abs(Mz - e)
        have = ~np.isnan(d)
        ok = np.all(np.where(have, d <= tol * mult, ~iskey), axis=1)
        if not ok.any():
            continue
        s = np.exp(-0.5 * (d / tol) ** 2)
        ws = np.where(have, w, 0.0)
        simv = 100 * np.nansum(np.where(have, s, 0) * ws, axis=1) / ws.sum(axis=1)
        simv[~ok] = -1
        j = int(np.argmax(simv))  # first max = lowest id (ids sorted)
        twin[i] = ids[j]
        sim[i] = simv[j]
        scores[i] = np.where(have[j], s[j], np.nan)
    return twin, sim, scores
