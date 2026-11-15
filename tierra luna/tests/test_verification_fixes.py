"""Regression tests for the faults found by the independent verification of engine
stages 2 and 3 (2026-11-15). One test per fault; thresholds and constants are read
from the configuration files, never typed here.
"""
import copy
import json
import os
import re
import sys
from collections import Counter

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO = os.path.dirname(ROOT)
sys.path.insert(0, ROOT)

from engine.bundle_v2 import load_bundle, tile_int_column  # noqa: E402
from engine.config import load_engine_config, load_mission_config, resolve_path  # noqa: E402
from engine.export_v2 import funnel_steps, reason_entries, reason_entries_v2  # noqa: E402
from engine.places import polygon_codes_from_places  # noqa: E402
from engine.similarity_context import load_region_cells  # noqa: E402

SHIPPED = os.path.join(REPO, "app", "public", "data", "v2")


def _stored(b, fname):
    return {c["name"] for c in b.file_entry(fname)["columns"]}


# Fault 1: similarity.json named the alias column 'slope_deg', which the bundle does not
# store (the real column is slope_iso_deg), so the panel could not show slope values.
def test_similarity_columns_are_stored_columns():
    b = load_bundle(SHIPPED)
    sim = b.json("similarity.json")
    stored = {"EARTH": _stored(b, "earth_base.bin"), "MOON": _stored(b, "moon_base.bin")}
    for v in sim["variables"]:
        if v["status"] != "active":
            continue
        for body, col in v["columns"].items():
            assert f"v.{col}" in stored[body], (v["variable"], body, col)
    ovr = load_engine_config().v("column_overrides") or {}
    slope = next(v for v in sim["variables"] if v["variable"] == "slope_deg")
    assert slope["columns"]["EARTH"] == ovr.get("slope_deg", "slope_deg")


# Fault 2: inside NE 110m polygons without an ISO code each cell took the code of its own
# nearest GeoNames place, giving 'AD France', 'BE France' and 'RU Norway'.
def test_polygon_without_iso_code_gets_one_code():
    polys = [{"code": None}, {"code": "XX"}, {"code": None}]
    poly_of = [0, 0, 0, 0, 1, None, 2, 2]
    cc = ["FR", "AD", "FR", "BE", "YY", "ZZ", "SE", "NO"]
    assert polygon_codes_from_places(poly_of, cc, polys) == {0: "FR", 2: "NO"}  # tie -> alphabetical


def test_every_country_name_has_one_code_in_the_bundle():
    places = load_bundle(SHIPPED).json("places.json")
    names = Counter(c["name"] for c in places["countries"])
    assert [n for n, k in names.items() if k > 1] == []


# Fault 3: the funnel text typed the common-gate limits and the decay in code.
def test_funnel_text_is_built_from_the_configuration():
    ecfg = load_engine_config()
    mcfg = load_mission_config(engine_cfg=ecfg)
    steps = funnel_steps(mcfg, ecfg)
    assert [s["step"] for s in steps] == [1, 2, 3, 4, 5, 6]
    for var, g in mcfg["common_gates"].items():
        assert f"{var} >= {g['min']}" in steps[0]["text"]
    assert f"exp(-{ecfg.v('repo_similarity')['decay']} * d)" in steps[4]["text"]
    changed = copy.deepcopy(mcfg)
    var = next(iter(changed["common_gates"]))
    changed["common_gates"][var]["min"] = changed["common_gates"][var]["min"] + 1.0
    assert f"{var} >= {changed['common_gates'][var]['min']}" in funnel_steps(changed, ecfg)[0]["text"]
    shipped = load_bundle(SHIPPED).json("missions.json")["funnel"]
    assert shipped == steps


# Fault 4: reason-code labels showed the mission variable names such as 'slope_300m_deg'.
def test_reason_labels_never_show_300m_names():
    ecfg = load_engine_config()
    reg = {"variables": {"slope_300m_deg": {"label": "Slope (rover)"}}}
    e = reason_entries(["slope_300m_deg:above_max"], ecfg, {"slope_300m_deg": "Slope (rover)"})[0]
    assert e["label"].endswith("Slope (rover)") and e["variable"] == "slope_300m_deg"
    mcfg = load_mission_config(engine_cfg=ecfg)
    e2 = reason_entries_v2(["slope_300m_deg:above_max"], mcfg, "rover", ecfg, reg)[0]
    assert "300m" not in e2["label"] and "300m" in e2["text"]  # the exact reason keeps the variable
    for m in load_bundle(SHIPPED).json("missions.json")["missions"]:
        for r in m["reason_codes"] + m["component_results"].get("ice", {}).get("reason_codes", []):
            assert not re.search(r"300 ?m", r["label"]), r


# Fault 5: the lunar_base zone was described as 'USGS outlines'; the footprints are the
# union of the 1 km navigational grid squares (an upper bound of each region).
def test_artemis_zone_is_not_called_an_outline():
    ecfg = load_engine_config()
    z = ecfg.v("similarity_zones")["lunar_base"]
    assert "outlines," not in z["source"] and "upper bound" in z["source"]
    import pandas as pd
    lat = np.repeat(90.0 - (np.arange(180) + 0.5), 360)
    lon = np.tile(-180.0 + (np.arange(360) + 0.5), 180)
    moon = pd.DataFrame({"lat_deg": lat, "lon_deg": lon})
    mask, reason, names = load_region_cells(resolve_path(z["regions_file"]), z["verified_flag"], moon, 1.0)
    assert mask is not None and len(names) == 9
    assert "outline" not in reason and "upper bound" in reason


# Fault 6: ASSUMPTIONS.md said fewer than 2 % of cells reach the z clip of 4.
def test_documented_z_clip_share_matches_the_bundle():
    b = load_bundle(SHIPPED)
    sim = b.json("similarity.json")
    act = sim["active_variables"]
    zs = [tile_int_column(b, f"z.{f}") for f in act]
    sent = b.manifest["encoding"]["int32_missing"]
    present = np.zeros(len(zs[0]), dtype=bool)
    clipped = np.zeros(len(zs[0]), dtype=bool)
    for q in zs:
        ok = q != sent
        present |= ok
        clipped |= ok & (np.abs(q) == 40000)  # |z| == 4 at 4 decimals (z_decimals in similarity.json)
    assert sim["z_decimals"] == 4
    n_pop = sim["earth_population"]["cells"]
    assert int(present.sum()) == n_pop
    share = 100.0 * clipped.sum() / n_pop
    text = open(os.path.join(REPO, "ASSUMPTIONS.md"), encoding="utf-8").read()
    assert f"{share:.1f} %" in text and "fewer than 2 %" not in text
