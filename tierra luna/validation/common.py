"""Shared helpers for the validation scripts (docs/VALIDATION.md).

Read-only with respect to the project: the scripts read the engine, the configuration
files, the data tables and the shipped bundle, and write only into validation/out/.
Nothing here changes a threshold, weight, tolerance or zone; every variant used for
sensitivity or proposals is built in memory as a deep copy.
"""
from __future__ import annotations

import copy
import json
import math
import os
import sys
from typing import Dict, Iterable, List, Optional

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.dirname(HERE)            # ".../tierra luna"
REPO = os.path.dirname(PROJECT)            # repository root
OUT = os.path.join(HERE, "out")
BUNDLE = os.path.join(REPO, "app", "public", "data", "v2")
BENCHMARK = os.path.join(PROJECT, "data", "benchmark", "analog_benchmark.csv")
LEGACY_CSV = os.path.join(PROJECT, "output_py", "earth_moon_harmonized_clean.csv")
REAL_DIR = os.path.join(PROJECT, "output_real")
PROV_EARTH = os.path.join(PROJECT, "real_data", "provenance_earth.csv")
PROV_MOON = os.path.join(PROJECT, "real_data", "provenance_moon.csv")
ENGINE_CONFIG = os.path.join(PROJECT, "engine", "engine_config.json")
MISSION_CONFIG = os.path.join(PROJECT, "mission_scoring.json")
IAU_CSV = os.path.join(PROJECT, "engine", "data", "iau_moon_nomenclature.csv")
NE_GEOJSON = os.path.join(PROJECT, "engine", "data", "ne_110m_admin_0_countries.geojson")

MISSIONS = ("rover", "solar", "lunar_base")
LEVELS = ("MEASURED", "DERIVED", "MODELLED")

if PROJECT not in sys.path:
    sys.path.insert(0, PROJECT)

os.makedirs(OUT, exist_ok=True)


def write_csv(df: pd.DataFrame, name: str) -> str:
    """Write a table to validation/out/<name> (fixed float format: byte-stable reruns)."""
    path = os.path.join(OUT, name)
    df.to_csv(path, index=False, float_format="%.6g", lineterminator="\n")
    return path


def write_json(obj, name: str) -> str:
    path = os.path.join(OUT, name)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(clean(obj), fh, ensure_ascii=False, indent=1, sort_keys=False)
        fh.write("\n")
    return path


def clean(o):
    """JSON-safe copy: numpy scalars to Python, NaN/inf to None, floats rounded to 6 significant digits."""
    if isinstance(o, dict):
        return {str(k): clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [clean(v) for v in o]
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.bool_,)):
        return bool(o)
    if isinstance(o, (float, np.floating)):
        f = float(o)
        if not math.isfinite(f):
            return None
        return float(f"{f:.6g}")
    return o


def load_json(path: str):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


_CTX: Dict = {}


def context() -> Dict:
    """The engine's own computation of the shipped dataset (real_1deg), computed once.
    This is the same call `python -m engine build` makes (engine.build.compute)."""
    if "c" not in _CTX:
        from engine.build import compute
        cache = os.environ.get("VALIDATION_DEV_CACHE")  # development only: a pickle outside the repo
        if cache and os.path.exists(cache):
            import pickle
            with open(cache, "rb") as fh:
                _CTX["c"] = pickle.load(fh)
        else:
            _CTX["c"] = compute()
            if cache:
                import pickle
                with open(cache, "wb") as fh:
                    pickle.dump(_CTX["c"], fh)
    return _CTX["c"]


def bundle():
    """The shipped bundle (app/public/data/v2), read with the engine's numpy reader."""
    if "b" not in _CTX:
        from engine.bundle_v2 import load_bundle
        _CTX["b"] = load_bundle(BUNDLE)
    return _CTX["b"]


def real_context(c: Dict) -> Dict:
    """{"settings", "derived"} of the real-value rules, rebuilt from the base results
    (the derived values do not depend on tolerances, thresholds or weights)."""
    r = c["results"]["rover"]
    return {"settings": c["engine_cfg"].v("real_value_similarity"), "derived": r.extra["real"]["derived"]}


def run_mission_variant(c: Dict, mission: str, mission_cfg: Optional[Dict] = None,
                        real_settings: Optional[Dict] = None):
    """Run one mission through the engine's own pipeline with an in-memory variant of
    mission_scoring.json and/or of engine_config real_value_similarity. No file is written."""
    from engine.config import Setting
    from engine.pipeline import run_mission

    ecfg = c["engine_cfg"].model_copy(deep=True)
    real = real_context(c)
    if real_settings is not None:
        ecfg.real_value_similarity = Setting(value=copy.deepcopy(real_settings),
                                             why="validation: in-memory variant (never written)")
        real = {"settings": copy.deepcopy(real_settings), "derived": real["derived"]}
    mcfg = mission_cfg if mission_cfg is not None else c["mission_cfg"]
    ctx = c["results"]["rover"].extra["repo_context"]
    return run_mission(mission, c["cells"]["EARTH"], c["cells"]["MOON"], mcfg, ecfg, c["registry"], ctx, real)


def ranked_ids(res, earth_ids: np.ndarray) -> np.ndarray:
    """Earth ids of the ranked points, best first."""
    idx = np.flatnonzero(res.rank > 0)
    return earth_ids[idx[np.argsort(res.rank[idx])]]


def spearman(a: np.ndarray, b: np.ndarray) -> float:
    """Spearman rank correlation of two equal-length arrays (average ranks for ties)."""
    from scipy.stats import spearmanr
    if len(a) < 3:
        return float("nan")
    return float(spearmanr(a, b).correlation)


def cell_of(lat: float, lon: float) -> int:
    """1-degree cell id containing (lat, lon): row 0 at the north, column 0 at -180."""
    row = min(179, max(0, int(math.floor(90.0 - lat))))
    col = int(math.floor(lon + 180.0)) % 360
    return row * 360 + col


def haversine_km(lat1, lon1, lat2, lon2, r_km: float) -> np.ndarray:
    p1, p2 = np.radians(lat1), np.radians(lat2)
    dl = np.radians(np.asarray(lon2) - np.asarray(lon1))
    dp = p2 - p1
    a = np.sin(dp / 2) ** 2 + np.cos(p1) * np.cos(p2) * np.sin(dl / 2) ** 2
    return 2 * r_km * np.arcsin(np.sqrt(np.clip(a, 0, 1)))


def pct(n: float, d: float) -> Optional[float]:
    return None if not d else round(100.0 * n / d, 2)
