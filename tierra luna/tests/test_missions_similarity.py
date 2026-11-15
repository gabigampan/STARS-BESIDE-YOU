"""Tests of the team lead's decisions of 2026-11-14 (engine 3.0.0).

1. three offered missions; lunar_base is an exact copy of thermal; thermal and ice
   stay as components; 2. the funnel (gates, required variables, reasons, coverage,
   alpha); 3. the repository's similarity reproduced exactly, per-body z-scores, the
   rock variable removed on the real tables, zero-variation detection; 4. the two
   similarity rules (repo_global_mean, zone_twin) and the bundle recompute for both;
   5. the lunar permafrost label.

Thresholds and weights are read from the configuration files, never typed here,
except in the hand-built tables.
"""
import copy
import json
import os
import subprocess
import sys

import numpy as np
import pandas as pd
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import mission_scoring  # noqa: E402
from engine.bundle_v2 import load_bundle, tile_column, tile_int_column, validate_bundle_v2  # noqa: E402
from engine.config import (MISSION_DEFINITION_KEYS, Setting, check_components, load_engine_config,  # noqa: E402
                           load_mission_config, mission_components, mission_ids, resolve_path)
from engine.export import write_bundle  # noqa: E402
from engine.gates import evaluate_gates, reason_step, reason_texts  # noqa: E402
from engine.repo_similarity import (BodyNorm, active_weights, best_twins, normalise_body,  # noqa: E402
                                    repo_features_and_weights, similarity_from_sq, sq_distance,
                                    variation_report, zone_mask)
from engine.suitability import evaluate_suitability  # noqa: E402

REAL, LEGACY = "real_1deg", "legacy_2deg"
OFFERED = ["rover", "solar", "lunar_base"]


def _cfg(dataset, rule=None):
    e = load_engine_config(dataset=dataset)
    if rule is not None:
        e.similarity_rule = Setting(value=rule, why="test")
    return e


@pytest.fixture(scope="module")
def mcfg():
    return load_mission_config(engine_cfg=load_engine_config())


@pytest.fixture(scope="module")
def computed():
    """compute() of both datasets under both repository rules."""
    from engine.build import compute
    return {(ds, rule): compute(ds, similarity_rule=rule)
            for ds in (LEGACY, REAL) for rule in ("repo_global_mean", "zone_twin")}


# ----------------------------------------------------------------------------- decision 1
def test_lunar_base_equals_thermal_field_by_field(mcfg):
    lb, th = mcfg["missions"]["lunar_base"], mcfg["missions"]["thermal"]
    for key in MISSION_DEFINITION_KEYS:
        assert lb[key] == th[key], key
    assert list(lb["soft"]) == list(th["soft"]) and list(lb["gates"]) == list(th["gates"])
    for var, spec in th["soft"].items():
        for k in ("weight", "bad", "good", "map", "default"):
            assert lb["soft"][var].get(k) == spec.get(k), (var, k)
    assert "lunar base" in lb["description"].lower() or "base lunar" in lb["description"].lower()
    # the loader refuses a lunar_base that drifts from thermal
    bad = copy.deepcopy(mcfg)
    bad["missions"]["lunar_base"]["soft"]["tmin_c"]["weight"] += 0.01
    with pytest.raises(ValueError):
        check_components(bad, OFFERED)


def test_exactly_three_missions_offered_and_components_kept(mcfg):
    ecfg = load_engine_config()
    assert mission_ids(mcfg, ecfg) == OFFERED == mcfg["offered_missions"]
    assert {"thermal", "ice"} <= set(mcfg["missions"])                     # untouched, as components
    assert mission_components(mcfg, "lunar_base") == {"core": "thermal", "info": ["ice"]}
    for m in ("rover", "solar"):
        assert mission_components(mcfg, m) == {"core": None, "info": []}
    wrong = copy.deepcopy(mcfg)
    wrong["offered_missions"] = ["rover", "solar", "thermal"]
    with pytest.raises(ValueError):
        mission_ids(wrong, ecfg)


def test_mission_scoring_selftest_and_cli_still_pass(tmp_path):
    mission_scoring.selftest()
    out = tmp_path / "scores.csv"
    r = subprocess.run([sys.executable, os.path.join(ROOT, "mission_scoring.py"), "run", "--cells",
                        os.path.join(ROOT, "output_py", "earth_moon_harmonized_clean.csv"),
                        "--missions", "solar,thermal,lunar_base,ice", "--out", str(out)],
                       capture_output=True, text=True, cwd=ROOT)
    assert r.returncode == 0, r.stderr
    df = pd.read_csv(out)
    assert (df["pass_lunar_base"] == df["pass_thermal"]).all()
    assert df["score_lunar_base"].equals(df["score_thermal"])


def test_ice_component_is_information_only(computed):
    for ds in (LEGACY, REAL):
        res = computed[(ds, "repo_global_mean")]["results"]
        lb = res["lunar_base"]
        assert set(lb.components) == {"ice"} and not res["rover"].components
        ice = lb.components["ice"]
        # the ranking does not depend on ice: lunar_base ranks exactly as thermal would
        assert not np.array_equal(ice.earth_gates.passed, lb.earth_gates.passed)
        cfg = computed[(ds, "repo_global_mean")]["mission_cfg"]
        ecfg = computed[(ds, "repo_global_mean")]["engine_cfg"]
        th = evaluate_suitability(computed[(ds, "repo_global_mean")]["cells"]["EARTH"], "EARTH", "thermal", cfg, ecfg)
        assert np.array_equal(th.passed, lb.earth_gates.passed)
        assert np.array_equal(np.isnan(th.score), np.isnan(lb.earth_suit.score))


# ----------------------------------------------------------------------------- decision 2: funnel
@pytest.mark.parametrize("ds", [LEGACY, REAL])
@pytest.mark.parametrize("rule", ["repo_global_mean", "zone_twin"])
def test_an_eliminated_cell_is_never_ranked(computed, ds, rule):
    c = computed[(ds, rule)]
    ids = c["cells"]["EARTH"]["id"].to_numpy()
    for mid in OFFERED:
        r = c["results"][mid]
        out = ~r.earth_gates.passed
        assert np.all(r.rank[out] == 0) and np.all(np.isnan(r.final[out])) and np.all(np.isnan(r.earth_suit.score[out]))
        assert np.all(r.twin_id[out] == -1)
        assert (r.rank > 0).sum() == r.earth_gates.passed.sum()
        top = {int(ids[i]) for i in np.flatnonzero(r.rank > 0)}
        assert not top & set(ids[out].tolist())
    # a cell eliminated for one mission may pass another
    p = {m: c["results"][m].earth_gates.passed for m in OFFERED}
    assert (p["solar"] & ~p["rover"]).any() and (p["rover"] & ~p["solar"]).any()


def test_reason_strings(mcfg):
    assert reason_texts("irradiance_kwh_m2_day:below_min", mcfg, "solar") == {
        "text": "irradiance_kwh_m2_day outside [2.5, inf]", "team_text": "irradiance_kwh_m2_day fuera de [2.5, inf]"}
    assert reason_texts("slope_deg:above_max", mcfg, "solar")["text"] == "slope_deg outside [-inf, 15.0]"
    assert reason_texts("tmin_c:missing", mcfg, "lunar_base")["text"] == "tmin_c no data"
    assert reason_texts("thermal_inertia_class:excluded", mcfg, "lunar_base")["text"] == "thermal_inertia_class not allowed"
    assert reason_step("elevation_m:below_min", mcfg, "solar") == 1
    assert reason_step("mask_fraction:missing", mcfg, "solar") == 1
    assert reason_step("tmin_c:missing", mcfg, "lunar_base") == 2          # required variable
    assert reason_step("tmin_c:above_max", mcfg, "lunar_base") == 3
    # on a hand table the team module's own reason text is the join of the codes' team texts
    ecfg = load_engine_config(dataset=LEGACY)
    df = pd.DataFrame({"id": [0, 1, 2], "elevation_m": [10.0, 10.0, -5.0], "mask_fraction": [1.0, 1.0, 1.0],
                       "irradiance_kwh_m2_day": [1.0, np.nan, 5.0], "slope_deg": [3.0, 30.0, 3.0],
                       "sun_elev_max_deg": [50.0, 50.0, 50.0], "sun_low_frac_0_5deg": [0.1, 0.1, 0.1],
                       "thermal_inertia_class": ["roca", "agua", "roca"]})
    g = evaluate_gates(df, "EARTH", "solar", mcfg, ecfg)
    _, team, _ = mission_scoring.apply_gates(df, {**mcfg["common_gates"], **mcfg["missions"]["solar"]["gates"]},
                                             mcfg["missions"]["solar"]["require_present"], "drop")
    assert g.reasons[0] == ("irradiance_kwh_m2_day:below_min",)
    assert set(g.reasons[1]) == {"irradiance_kwh_m2_day:missing", "slope_deg:above_max", "thermal_inertia_class:excluded"}
    assert g.reasons[2] == ("elevation_m:below_min",)
    for i in range(3):
        assert "; ".join(dict.fromkeys(reason_texts(c, mcfg, "solar")["team_text"] for c in g.reasons[i])) == team[i]


def test_coverage_and_renormalisation(mcfg):
    ecfg = load_engine_config(dataset=LEGACY)
    soft = mcfg["missions"]["solar"]["soft"]
    df = pd.DataFrame({"id": [0, 1], "elevation_m": [10.0, 10.0], "mask_fraction": [1.0, 1.0],
                       "irradiance_kwh_m2_day": [6.0, 6.0], "slope_deg": [1.0, 1.0], "sun_elev_max_deg": [70.0, 70.0],
                       "sun_low_frac_0_5deg": [0.03, 0.03], "thermal_inertia_class": ["roca", "roca"],
                       "lst_diurnal_amp_k": [np.nan, 10.0], "roughness_m": [400.0, 400.0]})
    s = evaluate_suitability(df, "EARTH", "solar", mcfg, ecfg)
    total = sum(x["weight"] for x in soft.values())
    w_amp, w_rough = soft["lst_diurnal_amp_k"]["weight"], soft["roughness_m"]["weight"]
    # row 0: amplitude missing -> ignored, weights renormalised; roughness at 'bad' -> utility 0
    assert np.isnan(s.utilities["lst_diurnal_amp_k"][0]) and s.missing_n[0] == 1
    assert s.coverage[0] == pytest.approx(round((total - w_amp) / total, 3))
    assert s.score[0] == pytest.approx(100 * (total - w_amp - w_rough) / (total - w_amp))
    assert s.coverage[1] == pytest.approx(1.0)
    assert s.score[1] == pytest.approx(100 * (total - w_rough) / total)


def test_alpha_mixes_similarity_and_suitability(computed):
    for rule in ("repo_global_mean", "zone_twin"):
        c = computed[(LEGACY, rule)]
        alpha = c["engine_cfg"].v("mix_factor")
        assert alpha == 0.5
        for r in c["results"].values():
            ok = r.rank > 0
            want = alpha * r.similarity_pct[ok] + (1 - alpha) * r.earth_suit.score[ok]
            assert np.max(np.abs(r.final[ok] - want)) < 1e-9 and r.alpha == alpha
    from engine.pipeline import run_all
    c = computed[(LEGACY, "repo_global_mean")]
    e = _cfg(LEGACY)
    e.mix_factor = Setting(value=0.3, why="test")
    r = run_all(c["cells"], c["mission_cfg"], e, c["registry"])["solar"]
    ok = r.rank > 0
    assert np.max(np.abs(r.final[ok] - (0.3 * r.similarity_pct[ok] + 0.7 * r.earth_suit.score[ok]))) < 1e-9


# ----------------------------------------------------------------------------- decision 3: the repository formula
def test_repository_formula_reproduced_on_the_legacy_table(computed, monkeypatch):
    import analog_finder
    monkeypatch.setattr(analog_finder, "get_rover_preset_bundle", lambda: {})
    c = computed[(LEGACY, "repo_global_mean")]
    earth, moon = c["cells"]["EARTH"], c["cells"]["MOON"]
    _, scored, meta = analog_finder.compute_analog_ranking(moon.drop(columns="id"), earth.drop(columns="id"))
    ref = dict(zip(zip(scored["row"], scored["col"]), scored["similarity_pct"]))
    ctx = c["results"]["rover"].extra["repo_context"]
    mine = ctx.global_similarity
    want = np.array([ref.get(k, np.nan) for k in zip(earth["row"], earth["col"])])
    assert np.isfinite(want).sum() == len(scored) > 5000
    assert np.array_equal(np.isfinite(mine), np.isfinite(want))
    assert np.array_equal(mine[np.isfinite(want)], want[np.isfinite(want)])        # exact, 2 decimals
    assert ctx.active == meta["active_features"]
    assert ctx.norm_w == pytest.approx(meta["weights_normalized"], abs=0, rel=0)
    tgt = meta["lunar_zones"]["Global Lunar Surface Mean (-90° to +90°)"]
    assert all(ctx.target[f]["z"] == tgt[f"{f}_z"] for f in ctx.active)
    # the repository's similarity is the same for every mission (no twin)
    for r in c["results"].values():
        ok = r.earth_gates.passed
        assert np.array_equal(r.similarity_pct[ok], mine[ok]) and np.all(r.twin_id == -1)


def test_z_scores_are_computed_per_body():
    feats = ["a"]
    e = normalise_body({"a": np.array([1.0, 2.0, 3.0, 4.0, 5.0, np.nan])}, np.array([True] * 5 + [False]))
    m1 = normalise_body({"a": np.array([100.0, 200.0, 300.0])}, np.ones(3, dtype=bool))
    m2 = normalise_body({"a": np.array([-7.0, 0.0, 7.0])}, np.ones(3, dtype=bool))
    q25, q75 = np.percentile([1, 2, 3, 4, 5], [25, 75])
    scale = (q75 - q25) / 1.349                                     # analog_finder's robust scale
    want = np.clip((np.array([1, 2, 3, 4, 5.0]) - 3.0) / scale, -4, 4).round(4)
    assert np.array_equal(e.z["a"][:5], want) and np.isnan(e.z["a"][5])   # outside the population: missing
    assert np.array_equal(m1.z["a"], m2.z["a"])                     # same relative position, different values
    assert m1.stats["a"]["median"] == 200.0 and e.stats["a"]["median"] == 3.0
    # a shift of a whole body leaves its z unchanged (why elevation_m stands in for elevation_rel_m)
    sh = normalise_body({"a": np.array([1.0, 2.0, 3.0, 4.0, 5.0, np.nan]) - 1047.422}, np.array([True] * 5 + [False]))
    assert np.allclose(sh.z["a"][:5], e.z["a"][:5], atol=1e-4)
    del feats


def test_rock_variable_removed_on_real_data_with_proportional_redistribution(computed):
    ctx = computed[(REAL, "repo_global_mean")]["results"]["rover"].extra["repo_context"]
    feats, w = repo_features_and_weights()
    assert "rock_or_bare_frac" in ctx.excluded and "rock_or_bare_frac" not in ctx.active
    assert "sar_sigma0_db" not in ctx.active                       # no radar column: dropped by the repo rule
    assert ctx.active == ["elevation_rel_m", "slope_deg", "roughness_m", "temp_k"]
    rest = sum(w[f] for f in ctx.active)
    for f in ctx.active:
        assert ctx.norm_w[f] == w[f] / rest
    assert ctx.norm_w["slope_deg"] / ctx.norm_w["temp_k"] == pytest.approx(w["slope_deg"] / w["temp_k"])
    # the legacy table keeps all six (nothing excluded there)
    lctx = computed[(LEGACY, "repo_global_mean")]["results"]["rover"].extra["repo_context"]
    assert lctx.active == feats and not lctx.excluded


def test_zero_variation_detection(computed):
    thr = 1e-6
    stats = {"flat": {"valid": True, "n": 5, "iqr": 0.0, "std_dev": 0.0},
             "mostly": {"valid": True, "n": 5, "iqr": 0.0, "std_dev": 0.4},
             "fine": {"valid": True, "n": 5, "iqr": 1.0, "std_dev": 0.8},
             "none": {"valid": False, "n": 0, "iqr": None, "std_dev": None}}
    assert variation_report(stats, thr) == {"flat": "zero", "mostly": "near_zero", "fine": "ok", "none": "no_data"}
    ctx = computed[(REAL, "repo_global_mean")]["results"]["rover"].extra["repo_context"]
    assert ctx.variation["MOON"]["rock_or_bare_frac"] == "zero"
    assert ctx.variation["MOON"]["sar_sigma0_db"] == ctx.variation["EARTH"]["sar_sigma0_db"] == "no_data"
    others = {f: v for b in ("EARTH", "MOON") for f, v in ctx.variation[b].items()
              if f not in ("rock_or_bare_frac", "sar_sigma0_db")}
    assert set(others.values()) == {"ok"}
    assert ctx.variation["EARTH"]["rock_or_bare_frac"] == "ok"
    # the repository's normaliser gives the flat lunar variable z = 0 everywhere
    assert np.all(ctx.moon.z["rock_or_bare_frac"] == 0.0)


def test_missing_z_is_dropped_and_renormalised():
    w = {"a": 0.5, "b": 0.3, "c": 0.2}
    ez = {"a": np.array([1.0, 1.0]), "b": np.array([0.0, np.nan]), "c": np.array([2.0, 2.0])}
    tz = {"a": np.float64(0.0), "b": np.float64(1.0), "c": np.float64(0.0)}
    sq = sq_distance(ez, tz, w)
    assert sq[0] == 0.5 * 1 + 0.3 * 1 + 0.2 * 4                      # every value present: no division
    assert sq[1] == pytest.approx((0.5 * 1 + 0.2 * 4) / 0.7)
    assert similarity_from_sq(np.array([0.0]), 0.45)[0] == 100.0


# ----------------------------------------------------------------------------- decision 4: zone_twin
def test_zone_twin_on_a_hand_built_table():
    moon = pd.DataFrame({"id": [0, 1, 2, 3, 4], "lat_deg": [-80.5, -76.5, -75.0, -74.5, -88.5]})
    zone = {"kind": "lat_max", "lat_max": -75.0}
    mask = zone_mask(moon, zone)
    assert mask.tolist() == [True, True, True, False, True]          # at or below -75
    mz_all = {"x": np.array([0.0, 1.0, 1.0, 0.5, 3.0]), "y": np.array([0.0, 0.0, 0.0, 0.0, 0.0])}
    zi = np.flatnonzero(mask)
    ez = {"x": np.array([0.9, 1.0, 0.5, 2.9]), "y": np.array([0.0, 0.0, 0.0, 0.0])}
    w = {"x": 0.5, "y": 0.5}
    tw, sq = best_twins(ez, {f: mz_all[f][zi] for f in w}, w, moon["id"].to_numpy()[zi], chunk_rows=2)
    # e0 -> 1 (cells 1 and 2 tie at 1.0: lowest id); e1 -> 1 (tie, lowest id);
    # e2 -> 0 or 1/2 at the same distance 0.125: lowest id 0; cell 3 (0.5, exact) is outside the zone
    assert tw.tolist() == [1, 1, 0, 4]
    assert sq[1] == 0.0 and sq[2] == pytest.approx(0.5 * 0.25)
    uniq, cnt = np.unique(tw, return_counts=True)
    assert dict(zip(uniq.tolist(), cnt.tolist())) == {0: 1, 1: 2, 4: 1}   # sharing counts
    assert similarity_from_sq(sq, 0.45)[1] == 100.0


def test_zone_twin_results_and_zones(computed):
    c = computed[(REAL, "zone_twin")]
    moon = c["cells"]["MOON"]
    zones = c["results"]["rover"].extra["repo_context"].zones
    for mid in OFFERED:
        r = c["results"][mid]
        z = zones[mid]
        assert z["used"] in ("lat_max", "artemis_regions", "fallback_south_pole")
        tw = r.twin_id[r.rank > 0]
        assert np.all(tw >= 0) and np.all(z["mask"][tw])             # every twin inside the zone
        assert r.moon_twin_count.sum() == (r.rank > 0).sum()
        assert np.array_equal(np.flatnonzero(r.moon_twin_count), np.unique(tw))
        # lunar cells are not filtered: some twins fail the mission on the Moon when any zone cell does
        if (~r.moon_gates.passed & z["mask"]).any():
            pass
    for mid in ("rover", "solar"):
        assert zones[mid]["lat_max"] == -75.0
        assert zones[mid]["cells"] == int((moon["lat_deg"] <= -75.0).sum())
    lb = zones["lunar_base"]
    assert lb["used"] in ("artemis_regions", "fallback_south_pole")       # never the global mean
    if lb["used"] == "fallback_south_pole":
        assert "not available" in lb["reason"] and lb["cells"] == zones["rover"]["cells"]


def test_artemis_regions_file_selects_the_intersecting_cells(tmp_path):
    from engine.similarity_context import load_region_cells
    moon = pd.DataFrame({"id": [0, 1, 2], "lat_deg": [-84.5, -85.5, -60.5], "lon_deg": [0.5, 10.5, 0.5]})
    poly = {"type": "Polygon", "coordinates": [[[0.2, -84.8], [0.8, -84.8], [0.8, -84.2], [0.2, -84.2], [0.2, -84.8]]]}
    gj = {"type": "FeatureCollection", "verified": True,
          "features": [{"type": "Feature", "properties": {"name": "R1"}, "geometry": poly}]}
    p = tmp_path / "r.geojson"
    p.write_text(json.dumps(gj))
    mask, status, names = load_region_cells(str(p), "verified", moon, 1.0)
    assert mask.tolist() == [True, False, False] and names == ["R1"]
    gj["verified"] = False
    p.write_text(json.dumps(gj))
    mask, status, _ = load_region_cells(str(p), "verified", moon, 1.0)
    assert mask is None and "not marked" in status
    assert load_region_cells(str(tmp_path / "none.geojson"), "verified", moon, 1.0)[0] is None


@pytest.mark.parametrize("ds", [LEGACY, REAL])
@pytest.mark.parametrize("rule", ["repo_global_mean", "zone_twin"])
def test_recompute_from_bundle_for_both_rules(ds, rule, tmp_path):
    from engine.build import build_bundle
    b = build_bundle(dataset=ds, similarity_rule=rule)
    write_bundle(b["files"], str(tmp_path))
    rep = validate_bundle_v2(str(tmp_path))
    assert rep["ok"] and rep["rule"] == rule
    assert rep["cells_checked"] == sum(int(r.earth_gates.passed.sum()) for r in b["results"].values())
    bun = load_bundle(str(tmp_path))
    sj = bun.json("similarity.json")
    if rule == "repo_global_mean":
        assert "twins.json" not in b["files"] and sj["twins"] is None and sj["no_twin_reason"]
    else:
        tj = bun.json("twins.json")
        for mid in OFFERED:
            rows = tj["missions"][mid]["twins"]
            assert sum(t["earth_cells"] for t in rows) == b["manifest"]["counts"]["missions"][mid]["ranked_EARTH"]
            assert all(t["feature"]["name"] and t["feature"]["distance_km"] is not None for t in rows)
            assert all(t["feature"]["url"].startswith("http") for t in rows)
            assert all(set(t["not_part_of_similarity"]) >= {"irradiance_kwh_m2_day", "tmin_c"} for t in rows)
    # z-scores and absolute values of both sides are exported, and the "not part of the similarity" list
    assert set(sj["not_part_of_similarity"]) >= {"irradiance_kwh_m2_day", "lst_diurnal_amp_k", "tmin_c",
                                                 "thermal_inertia_class", "permafrost_class"}
    for f in sj["active_variables"]:
        z = tile_column(bun, f"z.{f}")
        assert np.isfinite(z).any()
    assert np.array_equal(tile_int_column(bun, "id"), bun.int_column("earth_base.bin", "id"))


def test_zone_twin_build_is_deterministic():
    from engine.build import build_bundle
    a = build_bundle(dataset=LEGACY, similarity_rule="zone_twin")
    b = build_bundle(dataset=LEGACY, similarity_rule="zone_twin")
    assert a["files"].keys() == b["files"].keys()
    assert all(a["files"][k] == b["files"][k] for k in a["files"])


# ----------------------------------------------------------------------------- funnel export
def test_funnel_of_every_land_cell_is_in_the_bundle(tmp_path):
    """For every Earth land cell and each mission the bundle gives each gate's limit and
    value, pass or fail, the one-line reason (English and the team text) and, for
    survivors, the utilities; the reasons equal the engine's and mission_scoring's."""
    from engine.build import build_bundle
    b = build_bundle(dataset=REAL)
    write_bundle(b["files"], str(tmp_path))
    bun = load_bundle(str(tmp_path))
    land = b["land"]
    earth = b["cells"]["EARTH"]
    ms = {m["id"]: m for m in bun.json("missions.json")["missions"]}
    for mid in OFFERED:
        m, r = ms[mid], b["results"][mid]
        bits = bun.int_column(f"earth_{mid}.bin", "fail_bits")
        table = {e["bit"]: e for e in m["reason_codes"]}
        assert all(e["step"] in (1, 2, 3) and e["text"] and e["team_text"] for e in m["reason_codes"])
        assert all(g["limit"] and g["step"] in (1, 3) for g in m["gates"])
        cfg = b["mission_cfg"]
        sub = earth.iloc[np.flatnonzero(land)].reset_index(drop=True)
        gates = {**{k: v for k, v in cfg["common_gates"].items() if k in [g["variable"] for g in m["gates"] if "EARTH" in g["applies_to"]]},
                 **cfg["missions"][mid]["gates"]}
        _, team, _ = mission_scoring.apply_gates(sub, {k: {kk: vv for kk, vv in g.items() if kk != "why"} for k, g in gates.items()},
                                                 cfg["missions"][mid]["require_present"], "drop")
        li = np.flatnonzero(land)
        for k in range(0, len(bits), 101):
            codes = [table[j]["code"] for j in sorted(table) if bits[k] >> j & 1]
            assert tuple(codes) == tuple(sorted(r.earth_gates.reasons[li[k]], key=lambda c: [e["code"] for e in m["reason_codes"]].index(c)))
            if codes:
                texts = [table[j]["team_text"] for j in sorted(table) if bits[k] >> j & 1]
                assert set(dict.fromkeys(texts)) == set(team[k].split("; "))
        for v in r.soft_vars:
            u = tile_column(bun, f"{mid}.u.{v}")
            assert np.all(np.isnan(u[bits != 0]))


# ----------------------------------------------------------------------------- decision 5
def test_lunar_permafrost_is_the_modelled_label_ninguno():
    from engine.dataset import normalise_level, read_provenance_csv
    ecfg = load_engine_config(dataset=REAL)
    moon = pd.read_csv(resolve_path(ecfg.v("inputs")["MOON"]), keep_default_na=False)
    assert (moon["permafrost_class"] == "ninguno").all() and len(moon) == 64800
    row = read_provenance_csv(resolve_path(ecfg.v("provenance")["MOON"]), "MOON")["permafrost_class"]
    assert normalise_level(row["level"])[0] == "MODELLED"
    assert "not a measurement" in row["caveats"]
    src = open(os.path.join(ROOT, "real_data", "build_moon.py"), encoding="utf-8").read()
    assert 'PERMAFROST_LABEL = "ninguno"' in src
