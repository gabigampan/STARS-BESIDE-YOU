# AI-assisted (Claude, Anthropic). Declared in docs/AI_USE.md.
"""
rover_integration.py

Connects rover_preset.py (version 3) with analog_finder.py without changing
how the ranking is computed. It only ADDS information to the metadata that
export_web_bundle() already writes to the web bundle:

  1. Rover preset rebuilt with the real columns of the Earth grid, so the
     relief baseline (300 m / 5 km) and the p90 gate are chosen from data.
  2. Ranking sanity check (plan, section 5): rover score at the cells nearest
     to the known mobility analogs (Bardenas, Tabernas...) and to the sites
     that must score low (Rio Tinto, El Soplao...).
  3. Wear-test hint for every rover zone, from its GLiM lithology class when
     the Earth grid has a `lithology_class` column ("no_data" otherwise).

Scores, gates and weights are never modified here.

Integration (two lines in analog_finder.py, inside export_web_bundle, right
after `top_ranking, earth_scored, meta = compute_analog_ranking(...)`):

    from rover_integration import apply_rover_extras
    meta = apply_rover_extras(earth_scored, meta)

Self-check:  python rover_integration.py --selftest
"""
from __future__ import annotations

import csv
import math
import os
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from rover_preset import (
    DEFAULT_GRAVITY,
    PRESET_CONFIG,
    ROVER_SPEC,
    _json_safe,
    build_rover_preset,
    validate_rover_ranking,
    wear_test_hint,
    MOBILITY_MISMATCHES,
    MOBILITY_POSITIVES,
)

BENCHMARK_CSV = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "data", "benchmark", "analog_benchmark.csv"
)

# Fallback coordinates (approximate, decimal degrees). Used only when
# data/benchmark/analog_benchmark.csv is not in the repository; replace them
# with the benchmark file, which is the reference.
APPROX_SITE_COORDS = {
    "Bardenas": (42.20, -1.50),
    "Tabernas": (37.05, -2.40),
    "Dumont Dunes": (35.68, -116.23),
    "MDRS": (38.41, -110.79),
    "Yungay": (-24.08, -69.93),
    "Erfoud": (31.43, -4.23),
    "Dhofar": (18.60, 54.00),
    "Ramon": (30.60, 34.80),
    "Haughton": (75.38, -89.67),
    "Death Valley": (36.50, -117.00),
    "Qaidam": (37.00, 95.00),
    "Concordia": (-75.10, 123.33),
    "NEEMO": (24.95, -80.45),
    "HI-SEAS": (19.60, -155.48),
    "Rio Tinto": (37.70, -6.60),
    "El Soplao": (43.30, -4.42),
}


# --------------------------------------------------------------------------
# 1. Rover preset with the real Earth columns
# --------------------------------------------------------------------------
def rebuild_rover_bundle(earth_df: pd.DataFrame, previous_bundle: Optional[Dict] = None,
                         author: str = "Robotics 1 - Mobility Team") -> Dict:
    """Same bundle analog_finder builds, but the preset knows which columns
    exist (baseline and p90 gate are chosen from data). Not frozen here:
    freezing stays where the team already does it."""
    if previous_bundle and previous_bundle.get("preset_frozen"):
        # A frozen preset is never rebuilt or changed.
        return _json_safe(dict(previous_bundle))
    preset = build_rover_preset(
        ROVER_SPEC, PRESET_CONFIG, DEFAULT_GRAVITY, author=author,
        freeze=False, allow_unverified=True,
        available_columns=list(earth_df.columns),
    )
    bundle = dict(previous_bundle or {})
    bundle.update({
        "rover_spec": ROVER_SPEC,
        "preset_config": PRESET_CONFIG,
        "gravity": DEFAULT_GRAVITY,
        "preset": preset,
    })
    return _json_safe(bundle)


# --------------------------------------------------------------------------
# 2. Ranking sanity check at the known sites
# --------------------------------------------------------------------------
def _pick(row: Dict, *names):
    for n in names:
        for k in row:
            if k.strip().lower() == n:
                return row[k]
    return None


def load_site_coords(path: str = BENCHMARK_CSV) -> Dict[str, tuple]:
    """Coordinates of the check sites. Reads the benchmark CSV when present
    (columns name/site/site_name and lat/latitude, lon/longitude) and keeps
    only the sites used by the check; otherwise the approximate fallback."""
    wanted = list(MOBILITY_POSITIVES) + list(MOBILITY_MISMATCHES)
    coords: Dict[str, tuple] = {}
    if os.path.exists(path):
        with open(path, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                name = _pick(row, "name", "site", "site_name") or ""
                lat = _pick(row, "lat", "latitude", "lat_deg")
                lon = _pick(row, "lon", "longitude", "lon_deg")
                try:
                    lat, lon = float(lat), float(lon)
                except (TypeError, ValueError):
                    continue
                norm = name.lower().replace("í", "i")
                for w in wanted:
                    if w.lower() in norm and w not in coords:
                        coords[w] = (lat, lon)
    for w in wanted:
        coords.setdefault(w, APPROX_SITE_COORDS[w])
    return coords


def _grid_step_deg(earth_df: pd.DataFrame) -> float:
    lats = np.unique(np.round(earth_df["lat_deg"].to_numpy(dtype=float), 4))
    if lats.size < 2:
        return 1.0
    return float(np.median(np.diff(np.sort(lats))))


def site_scores(earth_scored: pd.DataFrame, coords: Dict[str, tuple],
                score_col: str = "score_rover") -> Dict[str, Dict]:
    """Score of the nearest grid cell to each site. Sites farther than 1.5
    cells from any land cell get None (for example an underwater habitat)."""
    lat = earth_scored["lat_deg"].to_numpy(dtype=float)
    lon = earth_scored["lon_deg"].to_numpy(dtype=float)
    score = earth_scored[score_col].to_numpy(dtype=float)
    max_d = 1.5 * _grid_step_deg(earth_scored)
    out = {}
    for name, (slat, slon) in coords.items():
        dlon = ((lon - slon + 180.0) % 360.0) - 180.0
        d = np.hypot(lat - slat, dlon * math.cos(math.radians(slat)))
        i = int(np.argmin(d))
        near = bool(d[i] <= max_d)
        out[name] = {
            "score": round(float(score[i]), 2) if near and np.isfinite(score[i]) else None,
            "cell_lat": round(float(lat[i]), 3),
            "cell_lon": round(float(lon[i]), 3),
            "distance_deg": round(float(d[i]), 2),
        }
    return out


def rover_ranking_check(earth_scored: pd.DataFrame,
                        benchmark_csv: str = BENCHMARK_CSV) -> Dict:
    if "score_rover" not in earth_scored.columns:
        return {"ok": None, "problems": ["score_rover not in the scored grid"]}
    coords = load_site_coords(benchmark_csv)
    cells = site_scores(earth_scored, coords)
    report = validate_rover_ranking({k: v["score"] for k, v in cells.items()})
    report["cells"] = cells
    report["coordinates_from"] = (benchmark_csv if os.path.exists(benchmark_csv)
                                  else "APPROX_SITE_COORDS (replace with the benchmark CSV)")
    report["note"] = ("Grid cells are coarse: a site score is the score of the "
                      "nearest cell, not of the site itself.")
    return _json_safe(report)


# --------------------------------------------------------------------------
# 3. Wear-test hint for rover zones
# --------------------------------------------------------------------------
def add_wear_hints(zones: List[Dict], earth_scored: pd.DataFrame) -> List[Dict]:
    has_lith = "lithology_class" in earth_scored.columns
    if has_lith:
        lat = earth_scored["lat_deg"].to_numpy(dtype=float)
        lon = earth_scored["lon_deg"].to_numpy(dtype=float)
        lith = earth_scored["lithology_class"].astype(str).to_numpy()
    for z in zones:
        code = None
        if has_lith:
            i = int(np.argmin(np.hypot(lat - z["lat"], lon - z["lon"])))
            code = lith[i]
        h = wear_test_hint(code)
        z["wear_test_hint"] = h["hint"]
        z["wear_test_text"] = h["text"]
    return zones


# --------------------------------------------------------------------------
# One call for analog_finder.export_web_bundle
# --------------------------------------------------------------------------
def apply_rover_extras(earth_scored: pd.DataFrame, meta: Dict) -> Dict:
    """Adds the version 3 rover information to `meta` and returns it.
    Never raises: if something fails, the bundle is exported as before and
    the error is recorded in meta['rover_preset']['integration_error']."""
    try:
        meta["rover_preset"] = rebuild_rover_bundle(earth_scored, meta.get("rover_preset"))
        meta["rover_preset"]["ranking_check"] = rover_ranking_check(earth_scored)
        zones = meta.get("optimal_mission_zones", {})
        if "rover" in zones:
            zones["rover"] = add_wear_hints(zones["rover"], earth_scored)
    except Exception as exc:  # keep the export working
        meta.setdefault("rover_preset", {})["integration_error"] = f"{type(exc).__name__}: {exc}"
    return meta


def selftest() -> int:
    rng = np.random.default_rng(0)
    lats = np.arange(-89.0, 90.0, 2.0)
    lons = np.arange(-179.0, 180.0, 2.0)
    LA, LO = np.meshgrid(lats, lons, indexing="ij")
    df = pd.DataFrame({"lat_deg": LA.ravel(), "lon_deg": LO.ravel()})
    df["score_rover"] = rng.uniform(10, 30, len(df))
    df["slope_300m_deg"] = 3.0
    df["rough_300m_m"] = 20.0
    df["thermal_inertia_class"] = "arena"
    for name in MOBILITY_POSITIVES:
        la, lo = APPROX_SITE_COORDS[name]
        i = int(np.argmin(np.hypot(df.lat_deg - la, df.lon_deg - lo)))
        df.loc[i, "score_rover"] = 85.0
    meta = {"rover_preset": {"preset": {"frozen_at": None}},
            "optimal_mission_zones": {"rover": [{"lat": 42.0, "lon": -1.0}]}}
    meta = apply_rover_extras(df, meta)
    rp = meta["rover_preset"]
    checks = [
        ("no integration error", "integration_error" not in rp),
        ("baseline chosen from data (300m)", rp["preset"]["baseline"] == "300m"),
        ("unfrozen preset is rebuilt, not frozen", rp["preset"]["frozen_at"] is None),
        ("transfer card has wear and soft-soil rows",
         {"Abrasive wear of wheels, seals and bearings",
          "Getting stuck or sinking in loose soil"}
         <= {r["item"] for r in rp["preset"]["transfer_card"]}),
        ("ranking check ran", rp["ranking_check"]["ok"] is True),
        ("Bardenas scored from nearest cell",
         rp["ranking_check"]["cells"]["Bardenas"]["score"] == 85.0),
        ("wear hint added to rover zones (no lithology -> no_data)",
         meta["optimal_mission_zones"]["rover"][0]["wear_test_hint"] == "no_data"),
    ]
    frozen_meta = {"rover_preset": {"preset_frozen": True,
                                     "preset": {"frozen_at": "2026-11-14T19:30:00+00:00", "x": 1}}}
    fz = apply_rover_extras(df, frozen_meta)["rover_preset"]
    checks.append(("frozen preset kept unchanged",
                   fz["preset"] == {"frozen_at": "2026-11-14T19:30:00+00:00", "x": 1}))
    df["lithology_class"] = "vb"
    z = add_wear_hints([{"lat": 42.0, "lon": -1.0}], df)
    checks.append(("wear hint from lithology_class",
                   z[0]["wear_test_hint"] == "candidate_for_wear_tests"))
    bad = apply_rover_extras(df.drop(columns=["score_rover"]), {})
    checks.append(("missing score column does not break the export",
                   bad["rover_preset"]["ranking_check"]["ok"] is None))
    for n, ok in checks:
        print(("ok    " if ok else "FAIL  ") + n)
    failed = sum(1 for _, ok in checks if not ok)
    print(f"{len(checks) - failed}/{len(checks)} checks passed")
    return 1 if failed else 0


if __name__ == "__main__":
    import sys
    if "--selftest" in sys.argv:
        raise SystemExit(selftest())
    print(__doc__)
