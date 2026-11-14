"""Checks for the rover preset v3 integration (rover_preset.py, rover_integration.py,
the hook in analog_finder.export_web_bundle and data/benchmark/analog_benchmark.csv).
They check wiring and data presence only; no threshold, weight or score is asserted."""
import csv
import inspect
import os
import sys

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import analog_finder  # noqa: E402
import rover_integration as ri  # noqa: E402
import rover_preset as rp  # noqa: E402


def test_rover_preset_selftest_passes():
    assert rp.selftest() == 0


def test_rover_integration_selftest_passes():
    assert ri.selftest() == 0


def test_benchmark_file_has_expected_columns_and_every_check_site():
    assert os.path.exists(ri.BENCHMARK_CSV)
    with open(ri.BENCHMARK_CSV, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 44
    for col in ("name", "lat", "lon", "coord_quality", "source_url", "source_status"):
        assert col in rows[0]
    names = [r["name"].lower() for r in rows]
    for site in list(rp.MOBILITY_POSITIVES) + list(rp.MOBILITY_MISMATCHES):
        assert any(site.lower() in n for n in names), site


def test_check_sites_read_from_benchmark_not_fallback():
    coords = ri.load_site_coords()
    with open(ri.BENCHMARK_CSV, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    for site, (lat, lon) in coords.items():
        match = next(r for r in rows if site.lower() in r["name"].lower())
        assert (lat, lon) == (float(match["lat"]), float(match["lon"])), site


def test_hook_is_in_export_web_bundle():
    src = inspect.getsource(analog_finder.export_web_bundle)
    assert "from rover_integration import apply_rover_extras" in src
    assert "meta = apply_rover_extras(earth_scored, meta)" in src


def test_rover_lunar_target_is_south_pole_zone():
    src = inspect.getsource(analog_finder.compute_mission_optimality_scores)
    assert '"rover": polar_target' in src


def test_apply_rover_extras_never_raises_and_adds_check():
    lats = np.arange(-89.0, 90.0, 2.0)
    lons = np.arange(-179.0, 180.0, 2.0)
    la, lo = np.meshgrid(lats, lons, indexing="ij")
    df = pd.DataFrame({"lat_deg": la.ravel(), "lon_deg": lo.ravel()})
    df["score_rover"] = np.nan
    df["slope_300m_deg"] = 3.0
    df["rough_300m_m"] = 20.0
    meta = ri.apply_rover_extras(df, {"optimal_mission_zones": {"rover": []}})
    assert "integration_error" not in meta["rover_preset"]
    assert meta["rover_preset"]["ranking_check"]["coordinates_from"] == ri.BENCHMARK_CSV
