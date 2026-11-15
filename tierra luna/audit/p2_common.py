"""Auditor 2 (points 3, 4, E): shared loaders written for the audit.

Independent code path: reads the CSV tables, the JSON configuration and the bundle
binaries directly (own decoder of DATA_CONTRACT revision 6). Does NOT import the
engine. Deterministic; no network.
"""
from __future__ import annotations

import json
import os

import numpy as np
import pandas as pd

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
TL = os.path.join(ROOT, "tierra luna")
BUNDLE = os.path.join(ROOT, "app", "public", "data", "v2")
OUT = os.path.join(TL, "audit", "out")
os.makedirs(OUT, exist_ok=True)

R_EARTH = 6371.0  # km, IUGG mean radius (same constant the engine cites; used only for distances)
R_MOON = 1737.4


def jload(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def configs():
    eng = jload(os.path.join(TL, "engine", "engine_config.json"))
    ms = jload(os.path.join(TL, "mission_scoring.json"))
    return eng, ms


def tables():
    e = pd.read_csv(os.path.join(TL, "output_real", "earth_real_1deg.csv"), low_memory=False)
    m = pd.read_csv(os.path.join(TL, "output_real", "moon_real_1deg.csv"), low_memory=False)
    for df in (e, m):
        df["id"] = df["row"].astype(int) * 360 + df["col"].astype(int)
        df.sort_values("id", inplace=True)
        df.reset_index(drop=True, inplace=True)
        assert np.array_equal(df["id"].to_numpy(), np.arange(64800))
    return e, m


# --------------------------------------------------------------------------- bundle
_MAN = None


def manifest():
    global _MAN
    if _MAN is None:
        _MAN = jload(os.path.join(BUNDLE, "manifest.json"))
    return _MAN


def read_bin(name):
    """{column: numpy array} with quantised columns decoded (q / divisor) and missing as NaN
    (float) / None-sentinel kept for int columns without divisor (returned as float with NaN)."""
    f = [x for x in manifest()["files"] if x["name"] == name][0]
    raw = open(os.path.join(BUNDLE, name), "rb").read()
    out = {}
    for c in f["columns"]:
        dt = "<f4" if c["type"] == "float32" else "<i4"
        a = np.frombuffer(raw, dtype=dt, count=c["length"], offset=c["offset"])
        if c["type"] == "int32":
            miss = a == -2147483648
            a = a.astype(np.float64)
            a[miss] = np.nan
            if c.get("divisor"):
                a = a / float(c["divisor"])
        else:
            a = a.astype(np.float64)
        out[c["name"]] = a
    return out


def mission_bundle(mission):
    """Decoded earth_<m>.bin and earth_<m>_pairs.bin with Earth cell ids of the passing rows."""
    base = read_bin("earth_base.bin")
    eb = read_bin(f"earth_{mission}.bin")
    pr = read_bin(f"earth_{mission}_pairs.bin")
    land_ids = base["id"].astype(np.int64)
    pass_ids = land_ids[eb["land_index"].astype(np.int64)]
    return base, eb, pr, pass_ids


# --------------------------------------------------------------------------- geometry
def gc_km(lat1, lon1, lat2, lon2, r):
    p1, p2 = np.radians(lat1), np.radians(lat2)
    dl = np.radians(np.asarray(lon2) - np.asarray(lon1))
    dp = p2 - p1
    a = np.sin(dp / 2) ** 2 + np.cos(p1) * np.cos(p2) * np.sin(dl / 2) ** 2
    return 2 * r * np.arcsin(np.sqrt(np.clip(a, 0, 1)))


def latlon(cid):
    cid = np.asarray(cid)
    return 89.5 - cid // 360, -179.5 + cid % 360


def qtl(a, qs=(0.0, 0.1, 0.25, 0.5, 0.75, 0.9, 0.99, 1.0)):
    a = np.asarray(a, dtype=float)
    a = a[np.isfinite(a)]
    if a.size == 0:
        return {}
    return {f"q{int(round(q * 100)):02d}": float(np.quantile(a, q)) for q in qs}


def dump(obj, name):
    path = os.path.join(OUT, name)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(obj, fh, ensure_ascii=False, indent=1, default=_np_default)
        fh.write("\n")
    return path


def _np_default(o):
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating,)):
        return None if not np.isfinite(o) else float(o)
    if isinstance(o, np.ndarray):
        return o.tolist()
    if isinstance(o, (np.bool_,)):
        return bool(o)
    raise TypeError(type(o))
