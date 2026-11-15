"""Auditor helpers for point 6 (B: contrast with published ranges; C: the 15 audio pairs).

Own code path: reads the two real tables, the configuration and the bundle (via the manifest
column index of docs/DATA_CONTRACT.md rev. 6). Does NOT import the engine nor other auditors'
helpers. Writes only under tierra luna/audit/out/.
"""
from __future__ import annotations

import json
import math
import os

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
TL = os.path.join(REPO, "tierra luna")
BUNDLE = os.path.join(REPO, "app", "public", "data", "v2")
EARTH_CSV = os.path.join(TL, "output_real", "earth_real_1deg.csv")
MOON_CSV = os.path.join(TL, "output_real", "moon_real_1deg.csv")
ENGINE_DATA = os.path.join(TL, "engine", "data")
OUT = os.path.join(HERE, "out")
os.makedirs(OUT, exist_ok=True)

R_EARTH = 6371.0088
R_MOON = 1737.4
I32_MISS = -2147483648


def load_tables():
    e = pd.read_csv(EARTH_CSV, low_memory=False)
    m = pd.read_csv(MOON_CSV, low_memory=False)
    return e, m


def haversine_km(lat1, lon1, lat2, lon2, r):
    p1, p2 = np.radians(lat1), np.radians(lat2)
    dphi = p2 - p1
    dl = np.radians(np.asarray(lon2) - np.asarray(lon1))
    a = np.sin(dphi / 2) ** 2 + np.cos(p1) * np.cos(p2) * np.sin(dl / 2) ** 2
    return 2 * r * np.arcsin(np.sqrt(np.clip(a, 0, 1)))


def weighted_quantile(x, w, qs):
    """Area-weighted quantile: sort, cumulative weight at the mid-point of each weight block."""
    x = np.asarray(x, float)
    w = np.asarray(w, float)
    ok = np.isfinite(x) & np.isfinite(w) & (w > 0)
    x, w = x[ok], w[ok]
    o = np.argsort(x, kind="mergesort")
    x, w = x[o], w[o]
    c = (np.cumsum(w) - 0.5 * w) / w.sum()
    return [float(np.interp(q, c, x)) for q in qs]


def toa_daily_mean_kwh(lat_deg, s0=1361.0, eps_deg=23.4392794, n=3600):
    """Own implementation: annual mean of the daily-mean horizontal TOA insolation,
    circular orbit, declination sin(d) = sin(eps) sin(L), L uniform. kWh/m2/day."""
    phi = math.radians(lat_deg)
    L = (np.arange(n) + 0.5) * 2 * math.pi / n
    d = np.arcsin(math.sin(math.radians(eps_deg)) * np.sin(L))
    x = -np.tan(phi) * np.tan(d)
    h0 = np.arccos(np.clip(x, -1, 1))
    q = s0 / math.pi * (h0 * math.sin(phi) * np.sin(d) + math.cos(phi) * np.cos(d) * np.sin(h0))
    return float(q.mean() * 24 / 1000)


class Bundle:
    def __init__(self, path=BUNDLE):
        self.path = path
        with open(os.path.join(path, "manifest.json"), encoding="utf-8") as fh:
            self.manifest = json.load(fh)
        self.files = {f["name"]: f for f in self.manifest["files"]}

    def json(self, name):
        with open(os.path.join(self.path, name), encoding="utf-8") as fh:
            return json.load(fh)

    def col(self, fname, cname):
        f = self.files[fname]
        c = [c for c in f["columns"] if c["name"] == cname][0]
        dt = "<f4" if c["type"] == "float32" else "<i4"
        with open(os.path.join(self.path, fname), "rb") as fh:
            fh.seek(c["offset"])
            a = np.frombuffer(fh.read(4 * c["length"]), dtype=dt).copy()
        if c["type"] == "int32" and c.get("divisor"):
            out = a.astype(float) / c["divisor"]
            out[a == I32_MISS] = np.nan
            return out
        return a


def dump(name, obj):
    p = os.path.join(OUT, name)
    with open(p, "w", encoding="utf-8") as fh:
        json.dump(obj, fh, indent=1, ensure_ascii=False, default=float)
    return p
