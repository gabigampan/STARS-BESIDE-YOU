"""Common helpers for the point 1 / 2 / 7 audit scripts (independent reviewer).

Own implementations (not the engine's): bundle binary reader, great-circle distance,
initial bearing, 8-point compass, point-in-cell, mid-rank percentile.
Read-only on the repository; outputs go to tierra luna/audit/out/.
"""
from __future__ import annotations

import json
import math
import os
from typing import Dict

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
TL = os.path.abspath(os.path.join(HERE, ".."))                 # 'tierra luna'
REPO = os.path.abspath(os.path.join(TL, ".."))
BUNDLE = os.path.join(REPO, "app", "public", "data", "v2")
OUT = os.path.join(HERE, "out")
EARTH_CSV = os.path.join(TL, "output_real", "earth_real_1deg.csv")
MOON_CSV = os.path.join(TL, "output_real", "moon_real_1deg.csv")
RAW = "/tmp/claude-0/-home-user-NASA/7228bb30-9725-52d9-8d71-762c955fd0bd/scratchpad/stars/realdata"
VENV_SITE = "/tmp/claude-0/-home-user-NASA/7228bb30-9725-52d9-8d71-762c955fd0bd/scratchpad/stars/venv/lib/python3.13/site-packages"
RG_CSV = os.path.join(VENV_SITE, "reverse_geocoder", "rg_cities1000.csv")
IAU_CSV = os.path.join(TL, "engine", "data", "iau_moon_nomenclature.csv")
ARTEMIS = os.path.join(TL, "engine", "data", "artemis_iii_regions.geojson")
NE110 = os.path.join(TL, "engine", "data", "ne_110m_admin_0_countries.geojson")

# Radii the audit uses (stated in the report). Mean radii; the engine uses the same values,
# which is what makes the published distances reproducible.
R_EARTH_KM = 6371.0
R_MOON_KM = 1737.4

os.makedirs(OUT, exist_ok=True)


def jload(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


# ------------------------------------------------------------------ bundle reader (own code)
class Bundle:
    def __init__(self, path: str = BUNDLE):
        self.path = path
        self.manifest = jload(os.path.join(path, "manifest.json"))
        self.files = {f["name"]: f for f in self.manifest["files"]}

    def json(self, name):
        return jload(os.path.join(self.path, name))

    def col(self, fname: str, cname: str) -> np.ndarray:
        f = self.files[fname]
        c = [c for c in f["columns"] if c["name"] == cname][0]
        dt = {"int32": "<i4", "float32": "<f4"}[c["type"]]
        with open(os.path.join(self.path, fname), "rb") as fh:
            fh.seek(c["offset"])
            a = np.frombuffer(fh.read(4 * c["length"]), dtype=dt).copy()
        if c["type"] == "int32":
            miss = a == -2147483648
            if c.get("divisor"):
                v = a.astype(np.float64) / float(c["divisor"])
                v[miss] = np.nan
                return v
            if c.get("scale"):
                v = a.astype(np.float64) * float(c["scale"])
                v[miss] = np.nan
                return v
            v = a.astype(np.float64)
            v[miss] = np.nan
            return v
        return a.astype(np.float64)

    def columns(self, fname):
        return [c["name"] for c in self.files[fname]["columns"]]


def ranked_points(b: Bundle, mission: str) -> pd.DataFrame:
    """Ranked (paired) Earth points of a mission: id, rank, twin, scores (from the bundle)."""
    ids = b.col("earth_base.bin", "id").astype(np.int64)
    li = b.col(f"earth_{mission}.bin", "land_index").astype(np.int64)
    df = pd.DataFrame({
        "earth_id": ids[li],
        "land_index": li,
        "rank": b.col(f"earth_{mission}.bin", "rank"),
        "twin": b.col(f"earth_{mission}.bin", "twin"),
        "similarity": b.col(f"earth_{mission}.bin", "similarity"),
        "suitability": b.col(f"earth_{mission}.bin", "suitability"),
        "final": b.col(f"earth_{mission}.bin", "final"),
    })
    return df


# ------------------------------------------------------------------ geometry (own code)
def cell_id(lat, lon):
    """Grid of the tables: row 0 at the north (centre 89.5), col 0 at -180 (centre -179.5)."""
    r = np.floor(90.0 - np.asarray(lat, float)).astype(int)
    c = np.floor(np.asarray(lon, float) + 180.0).astype(int)
    r = np.clip(r, 0, 179)
    c = np.where(c == 360, 0, c)
    return r * 360 + c


def cell_centre(cid):
    cid = np.asarray(cid, int)
    r, c = np.divmod(cid, 360)
    return 89.5 - r, -179.5 + c


def gc_km(lat1, lon1, lat2, lon2, R):
    """Great-circle distance by the spherical law of cosines in vector form (atan2, stable)."""
    p1, l1, p2, l2 = map(lambda x: np.radians(np.asarray(x, float)), (lat1, lon1, lat2, lon2))
    v1 = np.stack([np.cos(p1) * np.cos(l1), np.cos(p1) * np.sin(l1), np.sin(p1)], -1)
    v2 = np.stack([np.cos(p2) * np.cos(l2), np.cos(p2) * np.sin(l2), np.sin(p2)], -1)
    cr = np.linalg.norm(np.cross(v1, v2), axis=-1)
    dt = np.sum(v1 * v2, axis=-1)
    return R * np.arctan2(cr, dt)


def bearing(lat1, lon1, lat2, lon2):
    """Initial great-circle bearing from point 1 to point 2, degrees clockwise from north."""
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dl = math.radians(lon2 - lon1)
    y = math.sin(dl) * math.cos(p2)
    x = math.cos(p1) * math.sin(p2) - math.sin(p1) * math.cos(p2) * math.cos(dl)
    return (math.degrees(math.atan2(y, x)) + 360.0) % 360.0


COMPASS8 = ["north", "north-east", "east", "south-east", "south", "south-west", "west", "north-west"]


def compass8(b):
    return COMPASS8[int(((b + 22.5) % 360.0) // 45.0)]


def midrank_pct(values: np.ndarray) -> np.ndarray:
    """100*(rank-0.5)/n with ties averaged (own code, scipy-free)."""
    v = np.asarray(values, float)
    order = np.argsort(v, kind="mergesort")
    sv = v[order]
    ranks = np.empty(len(v))
    i = 0
    while i < len(v):
        j = i
        while j + 1 < len(v) and sv[j + 1] == sv[i]:
            j += 1
        ranks[order[i:j + 1]] = (i + j) / 2.0 + 1.0
        i = j + 1
    return 100.0 * (ranks - 0.5) / len(v)


def load_tables():
    e = pd.read_csv(EARTH_CSV, keep_default_na=True, na_values=[""], low_memory=False)
    m = pd.read_csv(MOON_CSV, keep_default_na=True, na_values=[""], low_memory=False)
    return e, m


def write_json(name, obj):
    p = os.path.join(OUT, name)
    with open(p, "w", encoding="utf-8") as fh:
        json.dump(obj, fh, indent=1, ensure_ascii=False, default=_default)
        fh.write("\n")
    return p


def _default(o):
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating,)):
        return None if not np.isfinite(o) else float(o)
    if isinstance(o, np.ndarray):
        return o.tolist()
    if isinstance(o, (np.bool_,)):
        return bool(o)
    raise TypeError(type(o))
