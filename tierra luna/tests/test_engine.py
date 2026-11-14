"""Tests of the engine package (engine/) and of the hard-filter rule in analog_finder.py.

Thresholds and weights are always read from mission_scoring.json / engine_config.json,
never typed here, except in the hand-built tables of the formula tests.
"""
import json
import math
import os
import sys

import numpy as np
import pandas as pd
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import mission_scoring  # noqa: E402
from engine import provenance, schema  # noqa: E402
from engine.config import load_engine_config, load_mission_config, resolve_path  # noqa: E402
from engine.confidence import pair_confidence  # noqa: E402
from engine.contract import validate_bundle_dir  # noqa: E402
from engine.explain import explain_cell  # noqa: E402
from engine.gates import evaluate_gates  # noqa: E402
from engine.pairing import pair_twins  # noqa: E402
from engine.pipeline import rank_scores, run_mission  # noqa: E402
from engine.similarity import (categorical_similarity, numeric_similarity, pooled_scale,  # noqa: E402
                               weighted_similarity)
from engine.suitability import evaluate_suitability, recompute_from_utilities, soft_weights  # noqa: E402
from engine.dataset import grid_of  # noqa: E402
from engine.table import load_cells, split_bodies  # noqa: E402

MISSIONS = ["rover", "solar", "thermal", "ice"]
LEGACY = "legacy_2deg"  # these tests check the engine on the legacy 2-degree table (test_real_data.py: real tables)


# ----------------------------------------------------------------------------- fixtures
@pytest.fixture(scope="module")
def ecfg():
    return load_engine_config(dataset=LEGACY)


@pytest.fixture(scope="module")
def grid(ecfg):
    return grid_of(ecfg)


@pytest.fixture(scope="module")
def mcfg(ecfg):
    return load_mission_config(engine_cfg=ecfg)


@pytest.fixture(scope="module")
def reg():
    return provenance.load_registry()


@pytest.fixture(scope="module")
def cells(ecfg, grid):
    return load_cells(resolve_path(ecfg.v("input_csv")), grid)


@pytest.fixture(scope="module")
def bundle():
    from engine.build import build_bundle
    return build_bundle(dataset=LEGACY)


def _passing_row(df, body, mission, mcfg, ecfg, n=1):
    g = evaluate_gates(df, body, mission, mcfg, ecfg)
    idx = np.flatnonzero(g.passed)[:n]
    return df.iloc[idx].reset_index(drop=True).copy()


def _gate(mcfg, mission, var):
    m = mcfg["missions"][mission]
    return m["gates"].get(var) or mcfg["common_gates"][var]


# ----------------------------------------------------------------------------- gates
def test_gate_boundary_values_exactly_at_min_and_max(cells, mcfg, ecfg):
    base = _passing_row(cells["EARTH"], "EARTH", "solar", mcfg, ecfg)
    gmin = _gate(mcfg, "solar", "irradiance_kwh_m2_day")["min"]
    gmax = _gate(mcfg, "solar", "slope_deg")["max"]
    df = pd.concat([base] * 4, ignore_index=True)
    df.loc[0, "irradiance_kwh_m2_day"] = gmin                          # exactly at min: passes
    df.loc[1, "irradiance_kwh_m2_day"] = np.nextafter(gmin, -np.inf)    # just below: fails
    df.loc[2, "slope_deg"] = gmax                                       # exactly at max: passes
    df.loc[3, "slope_deg"] = np.nextafter(gmax, np.inf)                 # just above: fails
    g = evaluate_gates(df, "EARTH", "solar", mcfg, ecfg)
    assert g.passed.tolist() == [True, False, True, False]
    assert g.reasons[1] == ("irradiance_kwh_m2_day:below_min",)
    assert g.reasons[3] == ("slope_deg:above_max",)


def test_categorical_gate_and_all_failed_criteria_recorded(cells, mcfg, ecfg):
    base = _passing_row(cells["EARTH"], "EARTH", "thermal", mcfg, ecfg)
    excl = _gate(mcfg, "thermal", "thermal_inertia_class")["exclude"][0]
    df = base.copy()
    df.loc[0, "thermal_inertia_class"] = excl
    df.loc[0, "tmin_c"] = _gate(mcfg, "thermal", "tmin_c")["max"] + 1.0
    g = evaluate_gates(df, "EARTH", "thermal", mcfg, ecfg)
    assert not g.passed[0]
    assert set(g.reasons[0]) == {"thermal_inertia_class:excluded", "tmin_c:above_max"}


def test_missing_value_in_a_gate_eliminates_the_cell(cells, mcfg, ecfg):
    assert mcfg["on_missing_gate"] == "drop"
    base = _passing_row(cells["EARTH"], "EARTH", "solar", mcfg, ecfg)
    df = pd.concat([base] * 3, ignore_index=True)
    df.loc[0, "irradiance_kwh_m2_day"] = np.nan   # mission gate + require_present
    df.loc[1, "elevation_m"] = np.nan             # common gate, not in require_present
    g = evaluate_gates(df, "EARTH", "solar", mcfg, ecfg)
    assert g.passed.tolist() == [False, False, True]
    assert "irradiance_kwh_m2_day:missing" in g.reasons[0]
    assert g.reasons[1] == ("elevation_m:missing",)
    s = evaluate_suitability(df, "EARTH", "solar", mcfg, ecfg)
    assert np.isnan(s.score[0]) and np.isnan(s.score[1]) and np.isfinite(s.score[2])


def test_land_mask_applies_to_earth_only(cells, mcfg, ecfg):
    assert ecfg.v("gate_body_applicability")["elevation_m"]["bodies"] == ["EARTH"]
    gmin = mcfg["common_gates"]["elevation_m"]["min"]
    e = _passing_row(cells["EARTH"], "EARTH", "thermal", mcfg, ecfg)
    m = _passing_row(cells["MOON"], "MOON", "thermal", mcfg, ecfg)
    e.loc[0, "elevation_m"] = gmin - 1000.0
    m.loc[0, "elevation_m"] = gmin - 1000.0
    assert not evaluate_gates(e, "EARTH", "thermal", mcfg, ecfg).passed[0]
    assert evaluate_gates(m, "MOON", "thermal", mcfg, ecfg).passed[0]


# ----------------------------------------------------------------------------- suitability
def _utility(v, spec):
    return min(1.0, max(0.0, (v - spec["bad"]) / (spec["good"] - spec["bad"])))


def test_missing_weighted_variable_is_renormalised_and_flagged(cells, mcfg, ecfg):
    base = _passing_row(cells["EARTH"], "EARTH", "solar", mcfg, ecfg)
    soft = mcfg["missions"]["solar"]["soft"]
    ungated = [v for v in soft if v not in mcfg["missions"]["solar"]["gates"]
               and v not in mcfg["missions"]["solar"]["require_present"]]
    target = ungated[0]
    df = base.copy()
    df.loc[0, target] = np.nan
    s = evaluate_suitability(df, "EARTH", "solar", mcfg, ecfg)
    assert s.passed[0] and s.missing_n[0] == 1 and np.isnan(s.utilities[target][0])
    num = sum(spec["weight"] * _utility(float(df.loc[0, v]), spec) for v, spec in soft.items() if v != target)
    den = sum(spec["weight"] for v, spec in soft.items() if v != target)
    assert s.score[0] == pytest.approx(100 * num / den, abs=0.006)


def test_replacement_weights_at_call_time(cells, mcfg, ecfg):
    earth = cells["EARTH"]
    first = next(iter(mcfg["missions"]["solar"]["soft"]))
    new_w = {first: 0.0}
    default = evaluate_suitability(earth, "EARTH", "solar", mcfg, ecfg)
    replaced = evaluate_suitability(earth, "EARTH", "solar", mcfg, ecfg, weights=new_w)
    ok = default.passed
    assert not np.allclose(default.score[ok], replaced.score[ok])
    w = soft_weights(mcfg, "solar", new_w)
    re = recompute_from_utilities({v: u[ok] for v, u in replaced.utilities.items()}, w)
    assert np.max(np.abs(re - replaced.score[ok])) <= 0.06


# ----------------------------------------------------------------------------- similarity
def test_similarity_formula_hand_cases():
    assert numeric_similarity(10.0, 7.0, 6.0) == pytest.approx(0.5)
    assert numeric_similarity(10.0, 20.0, 5.0) == 0.0          # clipped at 0
    assert numeric_similarity(3.0, 3.0, 0.0) == 1.0            # zero scale: exact match
    assert numeric_similarity(3.0, 4.0, 0.0) == 0.0
    assert np.isnan(numeric_similarity(np.nan, 4.0, 2.0))      # missing stays missing
    assert categorical_similarity(np.array([1]), np.array([1]))[0] == 1.0
    assert categorical_similarity(np.array([1]), np.array([2]))[0] == 0.0
    assert np.isnan(categorical_similarity(np.array([-1]), np.array([2]))[0])
    sims = {"a": np.array([0.5, np.nan]), "b": np.array([1.0, 0.25])}
    out = weighted_similarity(sims, {"a": 0.6, "b": 0.4})
    assert out[0] == pytest.approx(100 * (0.6 * 0.5 + 0.4 * 1.0))
    assert out[1] == pytest.approx(25.0)                        # 'a' missing: renormalised over 'b'
    sc = pooled_scale(np.array([0.0, 10.0]), np.array([20.0, 30.0]), 5, 95)
    assert sc["scale"] == pytest.approx(np.percentile([0, 10, 20, 30], 95) - np.percentile([0, 10, 20, 30], 5))


def test_pairing_on_tiny_hand_built_table():
    kinds = {"x": "numeric", "c": "categorical"}
    w = {"x": 0.6, "c": 0.4}
    earth = {"x": np.array([1.0, 9.0]), "c": np.array([0, 1])}
    moon = {"x": np.array([2.0, 8.0, 1.0]), "c": np.array([1, 1, 1])}
    twin, best = pair_twins(earth, moon, kinds, {"x": 10.0, "c": None}, w, np.array([0, 1, 2]))
    # e0: m0 0.54, m1 0.18, m2 0.60 -> 2 ; e1: m0 0.58, m1 0.94, m2 0.52 -> 1
    assert twin.tolist() == [2, 1]
    assert best == pytest.approx([60.0, 94.0])
    # missing value: general path, renormalised over 'c' only; all tie -> lowest id
    earth2 = {"x": np.array([np.nan]), "c": np.array([1])}
    twin2, best2 = pair_twins(earth2, moon, kinds, {"x": 10.0, "c": None}, w, np.array([5, 6, 7]))
    assert twin2.tolist() == [5] and best2[0] == pytest.approx(100.0)


def test_pairing_tie_goes_to_lowest_id_and_paths_agree():
    kinds = {"x": "numeric"}
    t, _ = pair_twins({"x": np.array([5.0])}, {"x": np.array([4.0, 6.0, 6.0])}, kinds, {"x": 10.0},
                      {"x": 1.0}, np.array([10, 11, 12]))
    assert t.tolist() == [10]
    rng = np.random.default_rng(0)
    e = {"x": rng.normal(size=50), "y": rng.normal(size=50)}
    m = {"x": rng.normal(size=80), "y": rng.normal(size=80)}
    k = {"x": "numeric", "y": "numeric"}
    t1, b1 = pair_twins(e, m, k, {"x": 2.0, "y": 3.0}, {"x": 0.7, "y": 0.3}, np.arange(80), chunk_rows=7)
    m2 = {"x": np.append(m["x"], np.nan), "y": np.append(m["y"], np.nan)}  # forces the general path
    t2, b2 = pair_twins(e, m2, k, {"x": 2.0, "y": 3.0}, {"x": 0.7, "y": 0.3}, np.arange(81))
    assert t1.tolist() == t2.tolist() and np.allclose(b1, b2)


def test_rank_ties_broken_by_cell_id():
    r = rank_scores(np.array([50.0, 60.0, 50.0, np.nan]), np.array([3, 1, 2, 0]))
    assert r.tolist() == [3, 1, 2, 0]


def test_run_mission_on_small_table_with_missing_similarity_variable(cells, mcfg, ecfg, reg):
    e = _passing_row(cells["EARTH"], "EARTH", "solar", mcfg, ecfg, n=3)
    m = _passing_row(cells["MOON"], "MOON", "solar", mcfg, ecfg, n=5)
    e.loc[0, "roughness_m"] = np.nan
    res = run_mission("solar", e, m, mcfg, ecfg, reg)
    assert np.isnan(res.sims["roughness_m"][0]) and res.earth_suit.missing_n[0] == 1
    w = {v: mcfg["missions"]["solar"]["soft"][v]["weight"] for v in res.sim_vars}
    num = sum(w[v] * res.sims[v][0] for v in res.sim_vars if v != "roughness_m")
    den = sum(w[v] for v in res.sim_vars if v != "roughness_m")
    assert res.similarity_pct[0] == pytest.approx(100 * num / den)
    assert set(res.twin_id.tolist()) <= set(m["id"].tolist())


# ----------------------------------------------------------------------------- confidence
def test_confidence_rule(ecfg):
    rule = ecfg.v("confidence")
    w = {"a": 0.5, "b": 0.5}
    meas = {"a": "MEASURED", "b": "MEASURED"}
    model = {"a": "MODELLED", "b": "MODELLED"}
    small = rule["high_max_cell_km"]
    assert pair_confidence(meas, meas, w, ["a", "b"], small, rule) == ("high", 1.0)
    label, score = pair_confidence(meas, meas, w, ["a", "b"], 222.4, rule)   # 2-degree cell: never high
    assert label == "medium" and score == 1.0
    assert pair_confidence(meas, model, w, ["a", "b"], small, rule)[0] == "low"  # weaker body limits
    lbl, sc = pair_confidence(meas, meas, w, ["a"], small, rule)              # half the weight missing
    assert sc == pytest.approx(0.5) and lbl == ("medium" if 0.5 >= rule["medium_min"] else "low")


# ----------------------------------------------------------------------------- schema
def test_schema_reports_and_does_not_fix(cells, reg, grid):
    m = cells["MOON"].iloc[:3].copy()
    e = cells["EARTH"].iloc[:3].copy()
    m.loc[m.index[0], "temp_k"] = -5.0
    m.loc[m.index[1], "lat_deg"] = 12.0
    e.loc[e.index[2], "thermal_inertia_class"] = "lava"
    before_m, before_e = m.copy(), e.copy()
    rm = schema.validate_body(m, "MOON", reg, grid=grid)
    re = schema.validate_body(e, "EARTH", reg, grid=grid)
    fields_m = {(f["id"], f["field"]) for f in rm["failures"]}
    assert (int(m["id"].iloc[0]), "temp_k") in fields_m
    assert any(f["id"] == int(m["id"].iloc[1]) for f in rm["failures"])
    assert re["failures"][0]["field"] == "thermal_inertia_class"
    pd.testing.assert_frame_equal(m, before_m)
    pd.testing.assert_frame_equal(e, before_e)


def test_schema_accepts_the_committed_table_and_units(cells, reg, grid):
    rep = schema.validate_table(cells, reg, grid=grid)
    assert rep["valid"], rep["bodies"]["EARTH"]["field_failures"]
    assert reg["variables"]["temp_k"]["unit"] == "K" and reg["variables"]["tmin_c"]["unit"] == "degC"
    assert reg["variables"]["elevation_m"]["bodies"]["MOON"]["level"] == "MEASURED"
    assert reg["variables"]["elevation_m"]["bodies"]["EARTH"]["level"] == "UNDOCUMENTED"


# ----------------------------------------------------------------------------- missions
@pytest.mark.parametrize("mission", MISSIONS)
def test_mission_configuration(mission, mcfg, cells):
    m = mcfg["missions"][mission]
    assert sum(s["weight"] for s in m["soft"].values()) == pytest.approx(1.0, abs=1e-9)
    cols = set(cells["EARTH"].columns) & set(cells["MOON"].columns)
    for var in list(m["gates"]) + list(m.get("require_present", [])) + list(m["soft"]) + list(mcfg["common_gates"]):
        assert var in cols, var
    for spec in m["soft"].values():
        assert ("map" in spec) or (spec["bad"] != spec["good"])


def test_author_declared_counts_reproduce_on_earth(cells, mcfg, bundle):
    earth = cells["EARTH"]
    res = mission_scoring.evaluate(earth, ["solar", "thermal"], mcfg)
    assert int(res["pass_solar"].sum()) == 5192
    assert int(res["pass_thermal"].sum()) == 2613
    assert int(res["pass_all"].sum()) == 1986
    res4 = mission_scoring.evaluate(earth, MISSIONS, mcfg)
    assert [int(res4[f"pass_{m}"].sum()) for m in MISSIONS] == [5297, 5192, 2613, 3023]
    assert int(res4["pass_all"].sum()) == 1728
    counts = bundle["manifest"]["counts"]["missions"]
    assert [counts[m]["pass_EARTH"] for m in MISSIONS] == [5297, 5192, 2613, 3023]


# ----------------------------------------------------------------------------- bundle
def test_no_gate_failed_cell_in_any_new_ranking(bundle):
    earth = bundle["objects"]["earth_cells.json"]
    pos = {c: i for i, c in enumerate(earth["id"])}
    for mid, blk in earth["missions"].items():
        for cid, rank in zip(blk["passing"]["id"], blk["passing"]["rank"]):
            assert blk["pass"][pos[cid]] == 1
        failed = {c for c, p in zip(earth["id"], blk["pass"]) if p == 0}
        assert not failed & set(blk["passing"]["id"])
        for item in bundle["objects"]["explain.json"]["missions"][mid]:
            assert blk["pass"][pos[item["id"]]] == 1
    for mid, r in bundle["results"].items():
        assert np.all(r.rank[~r.earth_gates.passed] == 0)
        assert np.all(np.isnan(r.final[~r.earth_gates.passed]))


def test_no_gate_failed_cell_ranked_in_old_analog_finder(cells, tmp_path, monkeypatch):
    """Old path after removing the x0.35 penalty: a gate-failed cell has no score
    (NaN, null in JSON) and never appears in the per-mission zone ranking.
    (Previously such a cell kept 35% of its score; no existing test asserted that.)"""
    import analog_finder
    monkeypatch.setattr(analog_finder, "get_rover_preset_bundle", lambda: {})
    moon, earth = cells["MOON"].drop(columns="id"), cells["EARTH"].drop(columns="id")
    _, scored, meta = analog_finder.compute_analog_ranking(moon, earth, top_k=20)
    for m in MISSIONS + ["all"]:
        failed = scored[f"pass_{m}"] == 0
        assert failed.any() and scored.loc[failed, f"score_{m}"].isna().all()
        assert scored.loc[~failed, f"score_{m}"].notna().all()
        for z in meta["optimal_mission_zones"][m]:
            row = scored[(scored["lat_deg"] == z["lat"]) & (scored["lon_deg"] == z["lon"])]
            assert int(row[f"pass_{m}"].iloc[0]) == 1
    paths = analog_finder.export_web_bundle(moon, earth, out_dir=str(tmp_path), web_dir=str(tmp_path))
    data = json.load(open(paths["web_json"]))
    for c in data["earth_cells"]:
        for p, s in (("p_rov", "s_rov"), ("p_sol", "s_sol"), ("p_thm", "s_thm"), ("p_ice", "s_ice"), ("p_all", "s_all")):
            assert (c[p] == 1) == (c[s] is not None)


def test_old_analog_finder_uses_the_engine_gates(cells, mcfg, ecfg, monkeypatch):
    """analog_finder's pass flags are those of mission_scoring.json as applied by the
    engine (review: it used mission_filters.json and ranked gate-failed cells)."""
    import analog_finder
    monkeypatch.setattr(analog_finder, "get_rover_preset_bundle", lambda: {})
    moon, earth = cells["MOON"].drop(columns="id"), cells["EARTH"].drop(columns="id")
    top, scored, meta = analog_finder.compute_analog_ranking(moon, earth, top_k=200)
    sub = cells["EARTH"].set_index(["row", "col"]).loc[list(zip(scored["row"], scored["col"]))].reset_index()
    for m in MISSIONS:
        g = evaluate_gates(sub, "EARTH", m, mcfg, ecfg)
        assert scored[f"pass_{m}"].tolist() == g.passed.astype(int).tolist(), m
        assert meta["mission_stats"][m]["pass"] == int(g.passed.sum())
    assert (top["pass_all"] == 1).all() and len(top) == 200
    assert top["rank"].tolist() == list(range(1, 201))


def test_bundle_is_deterministic(bundle):
    from engine.build import build_bundle
    again = build_bundle(dataset=LEGACY)
    assert again["files"].keys() == bundle["files"].keys()
    for name, data in bundle["files"].items():
        assert data == again["files"][name], name


def test_bundle_validates_against_contract(bundle, tmp_path):
    from engine.export import write_bundle
    write_bundle(bundle["files"], str(tmp_path))
    assert validate_bundle_dir(str(tmp_path))["ok"]
    total = sum(len(b) for b in bundle["files"].values())
    assert total < 12 * 1024 * 1024


def test_published_bundle_matches_a_fresh_build(bundle, ecfg):
    """The last v1 bundle (app/public/data/v1, built by engine 1.1.0) has the same content
    as a fresh legacy build: the dataset refactor changed no legacy result. The manifest
    differs (engine version, config hashes) and is not compared. The legacy build now goes
    to a folder outside app/public (it is not shipped)."""
    out = resolve_path(ecfg.v("output_dir"))
    assert "public" not in os.path.normpath(out).split(os.sep)
    v1 = resolve_path("../app/public/data/v1")
    if not os.path.isdir(v1):
        pytest.skip("app/public/data/v1 was removed")
    for name, data in bundle["files"].items():
        if name == "manifest.json":
            continue
        with open(os.path.join(v1, name), "rb") as fh:
            assert fh.read() == data, f"{name}: a fresh legacy build differs from app/public/data/v1"


def _browser_scores(p, w, k, alpha):
    """DATA_CONTRACT formulas on one passing cell, from the bundle alone, summing in
    the mission's variable order (as the browser does)."""
    un = ud = sn = sd = 0.0
    for v in p["u"]:
        if p["u"][v][k] is not None:
            un += w[v] * p["u"][v][k]
            ud += w[v]
    for v in p["sim"]:
        if p["sim"][v][k] is not None:
            sn += w[v] * p["sim"][v][k]
            sd += w[v]
    suit, sim = 100.0 * un / ud, 100.0 * sn / sd
    return suit, sim, alpha * sim + (1.0 - alpha) * suit


def test_browser_recompute_matches_engine(bundle, mcfg):
    """With default weights the browser reproduces the published scores exactly (the
    engine computes them from the published utilities and similarities), and ranking
    its rounded finals by (final desc, id) gives the stored rank."""
    earth = bundle["objects"]["earth_cells.json"]
    alpha = bundle["engine_cfg"].v("mix_factor")
    for mid, blk in earth["missions"].items():
        p = blk["passing"]
        w = soft_weights(mcfg, mid)
        mine = []
        for k in range(len(p["id"])):
            suit, sim, fin = _browser_scores(p, w, k, alpha)
            assert round(suit, 2) == p["suitability"][k]
            assert round(sim, 2) == p["similarity"][k]
            assert round(fin, 2) == p["final"][k]
            mine.append((-round(fin, 2), p["id"][k]))
        order = {cid: r + 1 for r, (_, cid) in enumerate(sorted(mine))}
        assert [order[c] for c in p["id"]] == p["rank"]


def test_provisional_flags_and_mix_factor_exported(bundle, mcfg):
    ms = {m["id"]: m for m in bundle["objects"]["missions.json"]["missions"]}
    for mid in MISSIONS:
        assert ms[mid]["provisional"] == bool(mcfg["missions"][mid].get("provisional"))
        assert ms[mid]["mix_factor"] == bundle["engine_cfg"].v("mix_factor")
    assert ms["rover"]["provisional"] and ms["ice"]["provisional"]


def test_explanations_add_up(bundle):
    for mid, items in bundle["objects"]["explain.json"]["missions"].items():
        assert [it["rank"] for it in items] == list(range(1, len(items) + 1))
        for it in items:
            sp = sum(v["suitability_points"] or 0 for v in it["variables"])
            mp = sum(v["similarity_points"] or 0 for v in it["variables"])
            assert abs(sp - it["suitability"]) <= 0.1
            assert abs(mp - it["similarity"]) <= 0.1
            assert len(it["helps_most"]) == 2


def test_explain_cell_hand_case():
    ex = explain_cell(["a", "b"], {"a": "numeric", "b": "numeric"}, {"a": 3.0, "b": 1.0}, {"a": 1.0, "b": 1.0},
                      {"a": 1.0, "b": 0.0}, {"a": 0.5, "b": 1.0}, {"a": 0.75, "b": 0.25}, 0.5, 2, 2)
    a, b = ex["variables"]
    assert a["difference"] == 2.0 and a["suitability_points"] == pytest.approx(75.0)
    assert a["similarity_points"] == pytest.approx(37.5) and b["similarity_points"] == pytest.approx(25.0)
    assert a["final_points"] == pytest.approx(56.25)
    assert ex["helps_most"] == ["a", "b"]
    assert ex["hurts_most"] == ["a", "b"]   # a loses 0.5*37.5 = 18.75; b loses 0.5*25 = 12.5


def test_places_are_computed(bundle):
    earth = bundle["objects"]["earth_cells.json"]
    moon = bundle["objects"]["moon_cells.json"]
    land = earth["land"]
    assert all((c is not None) == bool(l) for c, l in zip(earth["place"]["country_code"], land))
    assert all(n is not None for n in moon["feature"]["name"])
    feats = bundle["objects"]["iau_moon_features.json"]
    i = feats["name"].index("Tycho")
    assert feats["lat"][i] == pytest.approx(-43.3, abs=0.1) and feats["lon"][i] == pytest.approx(-11.2, abs=0.1)
    assert "Satellite Feature" not in set(feats["type"])


# ----------------------------------------------------------------------------- review fixes
def test_final_uses_unrounded_suitability(cells, mcfg, ecfg, reg):
    """final = alpha*similarity + (1-alpha)*suitability with the suitability NOT rounded
    to 2 decimals (review: mission_scoring rounds its score; final was built on it)."""
    res = run_mission("solar", cells["EARTH"], cells["MOON"], mcfg, ecfg, reg)
    ok = res.rank > 0
    soft = mcfg["missions"]["solar"]["soft"]
    exact, _, _ = mission_scoring.apply_soft(cells["EARTH"], soft)
    alpha = ecfg.v("mix_factor")
    want = alpha * res.similarity_pct[ok] + (1 - alpha) * exact[ok]
    assert np.max(np.abs(res.final[ok] - want)) < 1e-4
    # the old construction (team score rounded to 2 dp) differs by more than that somewhere
    old = alpha * res.similarity_pct[ok] + (1 - alpha) * res.earth_suit.score_team[ok]
    assert np.max(np.abs(old - want)) > 1e-3
    assert np.max(np.abs(res.earth_suit.score[ok] - exact[ok])) < 1e-4


def test_stored_rank_follows_the_contract_rule_on_stored_final(bundle):
    from engine.contract import check_rank_rule
    for mid, blk in bundle["objects"]["earth_cells.json"]["missions"].items():
        p = blk["passing"]
        check_rank_rule(mid, p["id"], p["final"], p["rank"])
    # a tie on the published final is broken by the lower id
    r = rank_scores(np.array([86.47, 86.47, 90.0]), np.array([10590, 10411, 5]))
    assert r.tolist() == [3, 2, 1]


def _small_bundle_objects(cells, mcfg, ecfg, reg, mission, edits):
    """Build earth_cells / explain objects for a few passing cells with edits applied."""
    from engine.export import build_cells, build_explain
    e = _passing_row(cells["EARTH"], "EARTH", mission, mcfg, ecfg, n=4)
    m = _passing_row(cells["MOON"], "MOON", mission, mcfg, ecfg, n=6)
    for (row, var), val in edits.items():
        e.loc[row, var] = val
    res = {mission: run_mission(mission, e, m, mcfg, ecfg, reg)}
    n = len(e)
    places = {k: [None] * n for k in ("country_code", "country", "region", "nearest_place", "nearest_place_km", "label_rule")}
    feats = {"name": ["x"] * len(m), "type": ["t"] * len(m), "diameter_km": [None] * len(m), "distance_km": [0.0] * len(m)}
    land = np.ones(n, dtype=bool)
    obj = build_cells("EARTH", e, res, ecfg, reg, places, {}, land)
    ex = build_explain(res, {"EARTH": e, "MOON": m}, mcfg, ecfg, reg, places, feats)
    return e, res[mission], obj, ex


def test_missing_values_are_exported_as_null_never_zero(cells, mcfg, ecfg, reg):
    """Review mutation M11 (rnd returning 0.0 for NaN) passed every test; this one fails it."""
    soft = mcfg["missions"]["solar"]
    ungated = [v for v in soft["soft"] if v not in soft["gates"] and v not in soft["require_present"]]
    sim_var = ungated[0]                       # a weighted, similarity variable without a gate
    gated = next(iter(soft["gates"]))          # a gated variable: the cell is eliminated
    e, res, obj, ex = _small_bundle_objects(cells, mcfg, ecfg, reg, "solar",
                                            {(0, sim_var): np.nan, (1, gated): np.nan})
    from engine.contract import check_values_match_input
    check_values_match_input(obj, e, provenance.variables(reg))
    assert obj["values"][sim_var][0] is None and obj["values"][gated][1] is None
    blk = obj["missions"]["solar"]
    assert blk["pass"][1] == 0 and e["id"].iat[1] not in blk["passing"]["id"]
    k = blk["passing"]["id"].index(int(e["id"].iat[0]))
    assert blk["passing"]["u"][sim_var][k] is None
    if sim_var in blk["passing"]["sim"]:
        assert blk["passing"]["sim"][sim_var][k] is None
    for item in ex["missions"]["solar"]:
        if item["id"] == int(e["id"].iat[0]):
            row = next(r for r in item["variables"] if r["variable"] == sim_var)
            assert row["earth"] is None and row["utility"] is None and row["difference"] is None


def test_cell_without_comparable_variable_has_no_twin_final_or_rank(cells, mcfg, ecfg, reg):
    e, res, obj, _ = _small_bundle_objects(cells, mcfg, ecfg, reg, "ice", {})
    sim_vars = res.sim_vars
    e2 = e.copy()
    for v in sim_vars:
        e2.loc[0, v] = np.nan
    m = _passing_row(cells["MOON"], "MOON", "ice", mcfg, ecfg, n=6)
    soft = mcfg["missions"]["ice"]
    if any(v in soft["gates"] or v in soft["require_present"] for v in sim_vars):
        pytest.skip("every similarity variable is gated: such a cell is eliminated instead")
    r = run_mission("ice", e2, m, mcfg, ecfg, reg)
    assert r.earth_gates.passed[0] and r.twin_id[0] == -1
    assert np.isnan(r.final[0]) and r.rank[0] == 0 and r.confidence[0] is None


def test_mask_fraction_gate_applies_on_both_bodies(cells, mcfg, ecfg):
    gmin = mcfg["common_gates"]["mask_fraction"]["min"]
    for body in ("EARTH", "MOON"):
        df = _passing_row(cells[body], body, "thermal", mcfg, ecfg)
        df.loc[0, "mask_fraction"] = np.nextafter(gmin, -np.inf)
        g = evaluate_gates(df, body, "thermal", mcfg, ecfg)
        assert not g.passed[0] and g.reasons[0] == ("mask_fraction:below_min",)


def test_scale_population_is_the_passing_cells_and_twins_pass(bundle):
    for mid, r in bundle["results"].items():
        n_pass = int(r.earth_gates.passed.sum() + r.moon_gates.passed.sum())
        for v, sc in r.scales.items():
            if sc["kind"] == "numeric":
                assert sc["n"] == n_pass, (mid, v)
        moon_ids = bundle["cells"]["MOON"]["id"].to_numpy()
        passing_moon = set(moon_ids[r.moon_gates.passed].tolist())
        twins = set(r.twin_id[r.twin_id >= 0].tolist())
        assert twins and twins <= passing_moon


def test_recompute_from_utilities_renormalises_over_missing():
    u = {"a": np.array([0.5, np.nan, np.nan]), "b": np.array([1.0, 0.25, np.nan])}
    out = recompute_from_utilities(u, {"a": 0.6, "b": 0.4})
    assert out[0] == pytest.approx(100 * (0.6 * 0.5 + 0.4 * 1.0))
    assert out[1] == pytest.approx(25.0) and np.isnan(out[2])


def test_non_comparable_variables_are_left_out_of_the_similarity(bundle, reg, mcfg):
    excluded = {v for v in provenance.variables(reg) if not provenance.comparable(reg, v)}
    assert {"rock_or_bare_frac", "permafrost_class"} <= excluded
    ms = {m["id"]: m for m in bundle["objects"]["missions.json"]["missions"]}
    for mid, r in bundle["results"].items():
        assert not excluded & set(r.sim_vars)
        soft = set(mcfg["missions"][mid]["soft"])
        assert set(ms[mid]["excluded_from_similarity"]) == soft & excluded
        assert not excluded & set(bundle["objects"]["earth_cells.json"]["missions"][mid]["passing"]["sim"])


def test_comparability_switch_restores_the_old_variable_set(cells, mcfg, reg):
    from engine.similarity import similarity_variables
    soft = list(mcfg["missions"]["rover"]["soft"])
    used, excl = similarity_variables(soft, cells["EARTH"], cells["MOON"], reg, False)
    assert used == soft and not excl
    used2, excl2 = similarity_variables(soft, cells["EARTH"], cells["MOON"], reg, True)
    assert "rock_or_bare_frac" in excl2 and "rock_or_bare_frac" not in used2


def test_ocean_fills_are_exported_as_null(bundle, ecfg):
    earth = bundle["objects"]["earth_cells.json"]
    spec = ecfg.v("earth_ocean_fill")
    land = earth["land"]
    for v in spec["variables"]:
        assert all(x is None for x, l in zip(earth["values"][v], land) if l == 0), v
        assert any(x is not None for x, l in zip(earth["values"][v], land) if l == 1), v
    assert earth["ocean_fill"]["fill_values_in_input"]["elevation_m"] is not None
    from engine.contract import check_values_match_input
    check_values_match_input(earth, bundle["cells"]["EARTH"], list(earth["values"]))


def test_derived_level_is_never_stronger_than_its_input(reg):
    from engine.build_provenance import DERIVED_FROM, LEVEL_STRENGTH
    for var, src in DERIVED_FROM.items():
        for body in ("EARTH", "MOON"):
            assert LEVEL_STRENGTH[provenance.level(reg, var, body)] <= max(
                LEVEL_STRENGTH[provenance.level(reg, src, body)], LEVEL_STRENGTH["DERIVED"] if
                provenance.level(reg, src, body) == "MEASURED" else -1)
    assert provenance.level(reg, "elevation_rel_m", "EARTH") == "UNDOCUMENTED"
    assert provenance.level(reg, "elevation_m", "MOON") == "MEASURED"
    measured = [(v, b) for v in provenance.variables(reg) for b in ("EARTH", "MOON")
                if provenance.level(reg, v, b) == "MEASURED"]
    assert measured == [("elevation_m", "MOON")]


def test_confidence_is_null_without_data(ecfg):
    rule = ecfg.v("confidence")
    assert pair_confidence({"a": "MEASURED"}, {"a": "MEASURED"}, {"a": 1.0}, [], 1.0, rule) == (None, None)


def test_country_by_polygon_and_region_only_when_near(bundle):
    earth = bundle["objects"]["earth_cells.json"]
    pos = {(la, lo): i for i, (la, lo) in enumerate(zip(earth["lat"], earth["lon"]))}
    pl = earth["place"]
    for (la, lo), cc in (((83.0, -29.0), "GL"), ((69.0, -141.0), "US"), ((25.0, -5.0), "MR")):
        i = pos[(la, lo)]
        if earth["land"][i]:
            assert pl["country_code"][i] == cc, (la, lo, pl["country_code"][i])
    lim = bundle["engine_cfg"].v("region_max_place_km")
    for r, d in zip(pl["region"], pl["nearest_place_km"]):
        if r is not None:
            assert d <= lim


def test_mission_notes_and_facts_exported(bundle, ecfg):
    notes = ecfg.v("mission_notes")
    for m in bundle["objects"]["missions.json"]["missions"]:
        assert m["known_limitations"] == notes.get(m["id"], [])
        f = m["facts"]
        assert f["distinct_twins"] >= 1 and isinstance(f["confidence_constant"], bool)
