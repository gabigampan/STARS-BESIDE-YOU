"""Tests of the dataset-aware engine on the real 1-degree tables and of the v2 bundle.

Thresholds, weights and data values are read from mission_scoring.json, the dataset
descriptors and the real tables at run time, never typed here (except in the
hand-built cases of the unit tests).
"""
import csv
import json
import math
import os
import sys

import numpy as np
import pandas as pd
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from engine import config as engine_config_module  # noqa: E402
from engine.bundle_v2 import (browser_real_similarity, browser_similarity, browser_suitability, load_bundle,  # noqa: E402
                              rank_rule, tile_column, validate_bundle_v2)  # noqa: E402
from engine.config import (DATASET_SETTINGS, ENGINE_CONFIG_PATH, dataset_ids, default_dataset,  # noqa: E402
                           load_engine_config, load_mission_config, resolve_path)
from engine.confidence import pair_confidence  # noqa: E402
from engine.dataset import (Grid, grid_of, normalise_level, override_baseline, read_provenance_csv,  # noqa: E402
                            resolve_columns)
from engine.export import write_bundle  # noqa: E402
from engine.export_v2 import BinFile, reason_entries, row_constant  # noqa: E402
from engine.gates import evaluate_gates  # noqa: E402
from engine.pairing import pair_twins  # noqa: E402
from engine.report import benchmark_lookup, read_sites, site_cell  # noqa: E402
from engine.suitability import evaluate_suitability, soft_weights  # noqa: E402

REAL = "real_1deg"
LEGACY = "legacy_2deg"
BENCHMARK_CSV = os.environ.get("STARS_BENCHMARK_CSV", "/home/user/NASA/docs/research/02_analog_benchmark.csv")


# ----------------------------------------------------------------------------- fixtures
@pytest.fixture(scope="module")
def real():
    from engine.build import build_bundle
    return build_bundle(dataset=REAL)


@pytest.fixture(scope="module")
def real_dir(real, tmp_path_factory):
    d = str(tmp_path_factory.mktemp("v2"))
    write_bundle(real["files"], d)
    return d


@pytest.fixture(scope="module")
def ecfg():
    return load_engine_config(dataset=REAL)


@pytest.fixture(scope="module")
def mcfg(ecfg):
    # revision 8: the mission config the build uses = the team's file with the selected
    # criteria set applied (engine/criteria.py; the team's file itself is unchanged)
    from engine.criteria import apply_criteria_sets
    return apply_criteria_sets(ecfg, load_mission_config(engine_cfg=ecfg))[1]


def _nan_equal(a, b):
    a, b = np.asarray(a, dtype=np.float64), np.asarray(b, dtype=np.float64)
    return a.shape == b.shape and np.array_equal(np.isnan(a), np.isnan(b)) and np.array_equal(a[~np.isnan(a)], b[~np.isnan(b)])


def _present(s):
    t = s.astype(str).str.strip().str.lower()
    return (s.notna() & ~t.isin(["", "nan"])).to_numpy()


# ----------------------------------------------------------------------------- 1. dataset switch
def test_dataset_switch_selects_grid_inputs_format_and_output():
    assert set(dataset_ids()) >= {REAL, LEGACY}
    assert default_dataset() == REAL
    legacy, real_cfg = load_engine_config(dataset=LEGACY), load_engine_config(dataset=REAL)
    assert load_engine_config().dataset_id == REAL                      # the default
    assert (grid_of(legacy).rows, grid_of(legacy).cols) == (90, 180)
    assert (grid_of(real_cfg).rows, grid_of(real_cfg).cols) == (180, 360)
    assert legacy.v("bundle_format") == "v2" and real_cfg.v("bundle_format") == "v2"
    assert real_cfg.v("output_dir").endswith("public/data/v2")
    assert "public" not in os.path.normpath(resolve_path(legacy.v("output_dir"))).split(os.sep)
    assert legacy.v("provenance")["kind"] == "registry" and real_cfg.v("provenance")["kind"] == "csv"
    with pytest.raises(KeyError):
        load_engine_config(dataset="no_such_dataset")


def test_engine_config_holds_no_dataset_setting(tmp_path):
    raw = json.load(open(ENGINE_CONFIG_PATH, encoding="utf-8"))
    assert not set(raw) & set(DATASET_SETTINGS)
    for name in ("GRID_ROWS", "GRID_COLS", "CELL_DEG"):
        assert not hasattr(engine_config_module, name)
    raw["input_csv"] = {"value": "x.csv", "why": "a dataset setting in the wrong file"}
    p = tmp_path / "engine_config.json"
    p.write_text(json.dumps(raw), encoding="utf-8")
    with pytest.raises(ValueError):
        load_engine_config(str(p))


def test_cli_takes_a_dataset_id(capsys):
    from engine.cli import main
    assert main(["datasets"]) == 0
    out = capsys.readouterr().out
    assert f"{REAL} (default)" in out and LEGACY in out


# ----------------------------------------------------------------------------- 2. aliases
def test_mission_variables_read_the_aliased_real_columns(real):
    ds = real["dataset"]
    aliases = json.load(open(resolve_path(real["engine_cfg"].v("column_aliases")), encoding="utf-8"))
    overrides = real["engine_cfg"].v("column_overrides")
    supp = {c for sp in real["engine_cfg"].v("supplements") for c in sp["columns"]}
    for v, per in ds.reg["columns"].items():
        for b in ("EARTH", "MOON"):
            if v in supp:  # supplementary column (datasets.json supplements): identity, its own provenance
                assert per[b]["column"] == v
                continue
            want = aliases[b][v]["column"]
            want = overrides.get(want, want)
            assert per[b]["column"] == want, (v, b)
            assert _nan_equal(pd.to_numeric(ds.cells[b][v], errors="coerce"),
                              pd.to_numeric(ds.raw[b][want], errors="coerce")) or \
                ds.cells[b][v].astype(str).equals(ds.raw[b][want].astype(str)), (v, b)


def test_every_slope_variable_uses_the_isotropic_column_on_both_bodies(real, mcfg):
    reg = real["dataset"].reg
    slope_vars = [v for v in reg["columns"] if reg["columns"][v]["EARTH"]["alias_column"] in ("slope_deg", "slope_p90_deg")]
    assert {"slope_300m_deg", "slope_deg"} <= set(slope_vars)
    for v in slope_vars:
        for b in ("EARTH", "MOON"):
            assert reg["columns"][v][b]["column"].startswith("slope_iso"), (v, b)
            assert reg["columns"][v][b]["override"]


def test_baseline_and_caveat_reach_variables_json(real, real_dir):
    var = {v["name"]: v for v in load_bundle(real_dir).json("variables.json")["variables"]}
    for v in ("slope_300m_deg", "slope_deg", "rough_300m_m", "roughness_m"):
        for b in ("EARTH", "MOON"):
            e = var[v]["bodies"][b]
            assert e["true_baseline"] and "300 m" not in e["true_baseline"], (v, b)
            assert e["true_baseline_km"] is not None and 1.0 < e["true_baseline_km"] < 5.0
            assert e["caveat"] and e["level"] in ("MEASURED", "DERIVED", "MODELLED", "NO_DATA")
            assert e["licence_credit"] and e["native_resolution"]
    s = var["slope_300m_deg"]["bodies"]
    for b in ("EARTH", "MOON"):
        prow = read_provenance_csv(resolve_path(real["engine_cfg"].v("provenance")[b]), b)["slope_iso_deg"]
        assert s[b]["true_baseline"] == override_baseline(prow)
        assert s[b]["column_override_why"]
    rover = next(m for m in load_bundle(real_dir).json("missions.json")["missions"] if m["id"] == "rover")
    assert any("300 m" in n for n in rover["known_limitations"])


def test_override_baseline_is_read_from_the_row_or_refused():
    assert override_baseline({"formula": "x; east-west baseline = 3.5 km in both directions"}) == "3.5 km in both directions"
    assert override_baseline({"formula": "", "caveats": "Baseline 4.25 km in both directions at every latitude."}) == \
        "4.25 km in both directions"
    with pytest.raises(ValueError):
        override_baseline({"variable": "x", "formula": "no baseline", "caveats": ""})


def test_identity_columns_on_the_legacy_dataset():
    cols = resolve_columns(["a", "b"], None, {})
    assert all(cols[v][b]["column"] == v and not cols[v][b]["override"] for v in cols for b in ("EARTH", "MOON"))


# ----------------------------------------------------------------------------- 3. levels and comparability
def test_levels_come_from_the_provenance_files(real):
    ecfg_ = real["engine_cfg"]
    reg = real["dataset"].reg
    for b in ("EARTH", "MOON"):
        rows = read_provenance_csv(resolve_path(ecfg_.v("provenance")[b]), b)
        from engine.dataset import supplement_provenance_rows
        rows.update(supplement_provenance_rows(ecfg_)[b])
        for v, e in reg["variables"].items():
            col = reg["columns"][v][b]["column"]
            assert e["bodies"][b]["level"] == normalise_level(rows[col]["level"])[0], (v, b)
    # team lead decision 5: a MODELLED label 'ninguno' on every lunar cell, never NO_DATA / empty
    assert reg["variables"]["permafrost_class"]["bodies"]["MOON"]["level"] == "MODELLED"
    with pytest.raises(ValueError):
        normalise_level("probably measured")


def test_comparability_statuses_reach_variables_json(real, real_dir):
    reg = real["dataset"].reg
    b = load_bundle(real_dir)
    var = {v["name"]: v for v in b.json("variables.json")["variables"]}
    assert all(v["comparability"]["status"] and v["comparability"]["reason"] for v in var.values())
    assert reg["variables"]["irradiance_kwh_m2_day"]["comparability"] == "comparable_with_caveat"
    assert "ninguno" in var["permafrost_class"]["comparability"]["reason"]


# ----------------------------------------------------------------------------- 4. hard filters and missing data
def test_missing_gated_value_eliminates_the_cell_with_no_data_reason(real, mcfg):
    ecfg_ = real["engine_cfg"]
    earth = real["cells"]["EARTH"]
    g = evaluate_gates(earth, "EARTH", "lunar_base", mcfg, ecfg_)
    df = earth.iloc[np.flatnonzero(g.passed)[:3]].reset_index(drop=True).copy()
    df.loc[0, "lst_diurnal_amp_k"] = np.nan          # gated and required
    df.loc[1, "elevation_m"] = np.nan                # common land gate
    g2 = evaluate_gates(df, "EARTH", "lunar_base", mcfg, ecfg_)
    assert g2.passed.tolist() == [False, False, True]
    assert "lst_diurnal_amp_k:missing" in g2.reasons[0] and g2.reasons[1] == ("elevation_m:missing",)
    s = evaluate_suitability(df, "EARTH", "lunar_base", mcfg, ecfg_)
    assert np.isnan(s.score[0]) and np.isnan(s.score[1]) and np.isfinite(s.score[2])
    label = ecfg_.v("missing_data_reason")["label"]
    ent = {e["code"]: e for e in reason_entries(["lst_diurnal_amp_k:missing", "tmin_c:above_max"], ecfg_)}
    assert ent["lst_diurnal_amp_k:missing"]["label"] == f"{label}: lst_diurnal_amp_k"
    assert ent["lst_diurnal_amp_k:missing"]["bit"] == 0 and ent["tmin_c:above_max"]["bit"] == 1


def test_missing_data_losses_are_counted_per_mission(real, real_dir):
    earth, land = real["cells"]["EARTH"], real["land"]
    res = real["results"]["lunar_base"]
    no_lst = land & ~_present(earth["lst_diurnal_amp_k"])
    assert no_lst.sum() > 0
    assert all("lst_diurnal_amp_k:missing" in res.earth_gates.reasons[i] for i in np.flatnonzero(no_lst))
    ant = land & (earth["lat_deg"].to_numpy() <= -65)
    assert ant.sum() > 0 and not _present(earth["lst_diurnal_amp_k"])[ant].any()   # no LST in Antarctica here
    m = {x["id"]: x for x in load_bundle(real_dir).json("missions.json")["missions"]}
    md = m["lunar_base"]["missing_data"]["EARTH_LAND"]
    assert md["by_variable"]["lst_diurnal_amp_k"] == int(no_lst.sum())
    # the ice component: no lunar cell passes (permafrost 'ninguno' is excluded by the ice gate), never 'no data'
    ice = real["results"]["lunar_base"].components["ice"]
    assert not ice.moon_gates.passed.any()
    assert all(r == ("permafrost_class:excluded",) for r in ice.moon_gates.reasons)
    assert m["lunar_base"]["component_results"]["ice"]["pass_counts"]["MOON"] == 0


def test_land_gate_is_earth_only_and_mask_fraction_is_land_share(real, mcfg):
    ecfg_ = real["engine_cfg"]
    assert ecfg_.v("gate_body_applicability")["elevation_m"]["bodies"] == ["EARTH"]
    moon = real["cells"]["MOON"]
    below = moon["elevation_m"].to_numpy() < mcfg["common_gates"]["elevation_m"]["min"]
    assert below.any()
    for r in real["results"].values():
        assert not any("elevation_m" in c for i in np.flatnonzero(below) for c in r.moon_gates.reasons[i])
    land = real["land"]
    mf = real["cells"]["EARTH"]["mask_fraction"].to_numpy()
    assert np.array_equal(land, np.isfinite(mf) & (mf > 0))


# ----------------------------------------------------------------------------- 6. binary bundle
def test_binary_round_trip_equals_the_frames(real, real_dir):
    b = load_bundle(real_dir)
    ds, land = real["dataset"], real["land"]
    raw_e, raw_m = ds.raw["EARTH"], ds.raw["MOON"]
    li = np.flatnonzero(land)
    ids = b.int_column("earth_base.bin", "id")
    assert np.array_equal(ids, raw_e["id"].to_numpy()[li])
    rows, cols = ids // ds.grid.cols, ids % ds.grid.cols
    assert np.array_equal(b.column("earth_base.bin", "lat")[rows], raw_e["lat_deg"].to_numpy()[li])
    assert np.array_equal(b.column("earth_base.bin", "lon")[cols], raw_e["lon_deg"].to_numpy()[li])
    var = {v["name"]: v for v in b.json("variables.json")["variables"]}
    for body, fname, frame, sel, r_of in (("EARTH", "earth_base.bin", raw_e, li, rows),
                                          ("MOON", "moon_base.bin", raw_m, np.arange(len(raw_m)),
                                           np.arange(len(raw_m)) // ds.grid.cols)):
        entry = {c["name"]: c for c in b.file_entry(fname)["columns"]}
        for name, c in entry.items():
            if not name.startswith("v."):
                continue
            col = name[2:]
            arr = b.column(fname, name)
            if c["rows"] == "grid_rows":
                arr = arr[r_of]
            src = frame[col].iloc[sel]
            if c["type"] == "int32":
                cats = var[c["variables"][0]]["categories"]
                txt = [None if np.isnan(x) else cats[int(x)] for x in arr]
                want = [None if not p else str(t).strip() for t, p in zip(src, _present(src))]
                assert txt == want, (body, col)
            else:
                assert _nan_equal(arr, pd.to_numeric(src, errors="coerce").to_numpy().astype(np.float32)), (body, col)
    for mid, r in real["results"].items():
        ef = f"earth_{mid}.bin"
        assert np.array_equal(b.int_column(ef, "fail_bits") == 0, r.earth_gates.passed[li])
        for v in r.soft_vars:
            u = tile_column(b, f"{mid}.u.{v}")
            assert _nan_equal(u, np.where(r.earth_gates.passed[li], r.earth_suit.utilities[v][li], np.nan))
        assert "twin" in b.columns(ef) and "twin_count" in b.columns(f"moon_{mid}.bin")  # twin rules (zone_twin, real_value_tolerance)
        assert np.array_equal(b.int_column(ef, "twin"), np.where(r.twin_id[r.earth_gates.passed] >= 0,
                                                                   r.twin_id[r.earth_gates.passed], -2147483648))
        codes = [e["code"] for e in next(m for m in b.json("missions.json")["missions"] if m["id"] == mid)["reason_codes"]]
        mb = b.int_column(f"moon_{mid}.bin", "fail_bits")
        for i in range(0, len(mb), 997):
            assert tuple(sorted(c for k, c in enumerate(codes) if mb[i] >> k & 1)) == tuple(sorted(r.moon_gates.reasons[i]))


def test_recompute_from_bundle_reproduces_every_passing_cell(real, real_dir):
    """From the bundle alone (numpy reader), the DATA_CONTRACT formulas give the stored
    suitability, similarity, final (2 decimals) and rank for every passing cell."""
    b = load_bundle(real_dir)
    ids_all = b.int_column("earth_base.bin", "id")
    sent = b.manifest["encoding"]["int32_missing"]
    sj = b.json("similarity.json")
    assert sj["rule"] == "per_mission" and sj["rules"]["lunar_base"] == "percentile_and_real_tolerance"
    norm_w = {v["variable"]: v["norm_weight"] for v in sj.get("variables", []) if v["status"] == "active"}
    twins = b.json("twins.json")["missions"]
    total = 0
    r2 = np.vectorize(lambda x: round(float(x), 2) if np.isfinite(x) else np.nan)
    for m in b.json("missions.json")["missions"]:
        ef = m["files"]["EARTH"]
        li = b.int_column(ef, "land_index")
        order = [w["variable"] for w in m["weighted_variables"]]
        w = {x["variable"]: x["weight"] for x in m["weighted_variables"]}
        suit = browser_suitability({v: tile_column(b, f"{m['id']}.u.{v}")[li] for v in order}, w, order)
        tw = b.int_column(ef, "twin")
        if sj["rules"][m["id"]] in ("real_value_tolerance", "percentile_and_real_tolerance"):   # revisions 5-6: published scores
            sv = [x["variable"] for x in m["similarity"]["variables"]]
            sw = {x["variable"]: x["weight"] for x in m["similarity"]["variables"]}
            sim = browser_real_similarity({v: b.column(ef, f"s.{v}") for v in sv}, sw, sv)
            sim = np.where(tw == sent, np.nan, sim)
        else:
            tzid = {t["id"]: t["z"] for t in twins[m["id"]]["twins"]}
            tz = {f: np.array([np.nan if t == sent or tzid[int(t)][f] is None else tzid[int(t)][f] for t in tw]) for f in norm_w}
            sim = browser_similarity({f: tile_column(b, f"z.{f}")[li] for f in norm_w}, tz, norm_w, sj["formula"]["decay"])
        fin = m["alpha"] * sim + (1 - m["alpha"]) * suit
        for mine, stored in ((suit, "suitability"), (sim, "similarity"), (fin, "final")):
            assert _nan_equal(r2(mine), b.column(ef, stored)), (m["id"], stored)
        rank = b.int_column(ef, "rank")
        assert np.array_equal(np.where(rank == sent, 0, rank), rank_rule(r2(fin), ids_all[li]))
        total += len(li)
    assert total == sum(int(r.earth_gates.passed.sum()) for r in real["results"].values())
    assert validate_bundle_v2(real_dir)["cells_checked"] == total


def test_slider_weights_recompute_matches_the_engine(real, real_dir, mcfg):
    """Moving a slider: the browser formula on the bundle's utilities equals the engine's
    suitability with the replacement weights."""
    b = load_bundle(real_dir)
    m = next(x for x in b.json("missions.json")["missions"] if x["id"] == "solar")
    li = b.int_column("earth_solar.bin", "land_index")
    order = [w["variable"] for w in m["weighted_variables"]]
    new_w = {order[0]: 0.05, order[-1]: 0.5}
    w = soft_weights(mcfg, "solar", new_w)
    u = {v: tile_column(b, f"solar.u.{v}")[li] for v in order}
    suit = browser_suitability(u, w, order)
    eng = evaluate_suitability(real["cells"]["EARTH"], "EARTH", "solar", mcfg, real["engine_cfg"], weights=new_w)
    assert np.array_equal(suit, eng.score[eng.passed])


def test_bundle_is_deterministic(real):
    from engine.build import build_bundle
    again = build_bundle(dataset=REAL)
    assert again["files"].keys() == real["files"].keys()
    for name, data in real["files"].items():
        assert data == again["files"][name], name


def test_bundle_sizes_and_split(real, ecfg):
    man = real["manifest"]
    budget = ecfg.v("first_view_budget_bytes")
    sizes = {f["name"]: f["bytes"] for f in man["files"]}
    first = sum(sizes[n] for n in man["load"]["first_view"]) + len(real["files"]["manifest.json"])
    total = sum(sizes.values()) + len(real["files"]["manifest.json"])
    assert set(man["load"]["first_view"]) == {"missions.json", "similarity.json", "variables.json", "places.json",
                                              "earth_base.bin", f"earth_{man['load']['default_mission']}.bin"}
    assert first < budget["first_view_max"] and total < budget["total_max"], (first, total)
    # the funnel detail of any land cell is one tile, a small fraction of the bundle
    tiles = man["detail_tiles"]["files"]
    assert sum(t["land_cells"] for t in tiles) == int(real["land"].sum())
    assert max(sizes[t["name"]] for t in tiles) < budget["first_view_max"] / 5


def test_published_v2_matches_a_fresh_build(real, ecfg):
    out = resolve_path(ecfg.v("output_dir"))
    for name, data in real["files"].items():
        with open(os.path.join(out, name), "rb") as fh:
            assert fh.read() == data, f"{name} in app/public/data/v2 is stale: run python -m engine build"
    assert validate_bundle_v2(out)["ok"]


def test_quantised_columns_are_exact_and_missing_is_the_sentinel(ecfg):
    enc = ecfg.v("binary_encoding")
    bf = BinFile("t.bin", enc)
    bf.quantised("u", np.array([0.123457, np.nan, 1.0]), 6, "r")
    a = np.frombuffer(bytes(bf.buf), dtype="<i4")
    assert a.tolist() == [123457, enc["int32_missing"], 1000000] and a[0] / 10 ** 6 == 0.123457
    with pytest.raises(ValueError):
        BinFile("t.bin", enc).quantised("u", np.array([0.1234567]), 6, "r")


def test_row_constant_detection():
    rows = np.array([0, 0, 1, 1, 2, 2])
    v = np.array([1.0, 1.0, 2.0, 2.0, 0.0, 0.0])
    miss = np.array([False, False, False, False, True, True])
    out = row_constant(v, miss, rows, 3)
    assert out is not None and out[0][:2].tolist() == [1.0, 2.0] and out[1].tolist() == [False, False, True]
    assert row_constant(np.array([1.0, 2.0]), np.array([False, False]), np.array([0, 0]), 1) is None
    assert row_constant(np.array([1.0, 1.0]), np.array([False, True]), np.array([0, 0]), 1) is None


# ----------------------------------------------------------------------------- engine pieces
def test_confidence_counts_each_body_where_it_has_data(ecfg):
    rule = ecfg.v("confidence")
    w = {"a": 0.5, "b": 0.5}
    lv_e = {"a": "MEASURED", "b": "MEASURED"}
    lv_m = {"a": "DERIVED", "b": "NO_DATA"}
    label, score = pair_confidence(lv_e, lv_m, w, ["a"], 1.0, rule, ["a", "b"], ["a"])
    ls = rule["level_scores"]
    assert score == pytest.approx(min(ls["MEASURED"], ls["DERIVED"]) * 0.5)


def test_grouped_pairing_equals_the_general_path():
    rng = np.random.default_rng(1)
    e = {"x": rng.normal(size=60), "y": rng.normal(size=60)}
    e["x"][::7] = np.nan
    e["y"][::5] = np.nan
    m = {"x": rng.normal(size=40), "y": rng.normal(size=40)}
    k = {"x": "numeric", "y": "numeric"}
    sc, w = {"x": 2.0, "y": 3.0}, {"x": 0.7, "y": 0.3}
    t1, b1 = pair_twins(e, m, k, sc, w, np.arange(40), chunk_rows=8)                     # grouped fast path
    m2 = {"x": np.append(m["x"], np.nan), "y": np.append(m["y"], np.nan)}
    t2, b2 = pair_twins(e, m2, k, sc, w, np.arange(41), chunk_rows=8)                   # general path
    assert t1.tolist() == t2.tolist() and _nan_equal(b1, b2)
    assert t1[35] == -1 and np.isnan(b1[35])                                             # both values missing


# ----------------------------------------------------------------------------- 5. benchmark sites
def test_site_cell_lookup_on_the_grid():
    g = Grid(rows=180, cols=360, cell_deg=1.0)
    assert site_cell(89.99, -179.99, g)["id"] == 0
    c = site_cell(0.0, 0.0, g)                         # an edge belongs to the cell to its south / east
    assert (c["row"], c["col"]) == (90, 180) and c["lat_center"] == -0.5 and c["lon_center"] == 0.5
    assert site_cell(-90.0, 180.0, g)["row"] == 179 and site_cell(-90.0, 180.0, g)["col"] == 0
    c = site_cell(37.72, -6.56, g)
    assert c["id"] == 52 * 360 + 173 and math.isclose(c["lat_center"], 37.5)
    with pytest.raises(ValueError):
        site_cell(91.0, 0.0, g)


def test_benchmark_lookup_matches_the_results(real, tmp_path):
    earth = real["cells"]["EARTH"]
    r = real["results"]["rover"]
    k_pass = int(np.flatnonzero(r.rank == 1)[0])
    k_fail = int(np.flatnonzero(~r.earth_gates.passed & real["land"])[0])
    p = tmp_path / "sites.csv"
    with open(p, "w", newline="", encoding="utf-8") as fh:
        wr = csv.writer(fh)
        wr.writerow(["id", "name", "lat", "lon", "target_body"])
        wr.writerow(["T1", "top rover cell", earth["lat_deg"].iat[k_pass], earth["lon_deg"].iat[k_pass], "Moon"])
        wr.writerow(["T2", "failing land cell", earth["lat_deg"].iat[k_fail] + 0.2, earth["lon_deg"].iat[k_fail] - 0.2, "Moon"])
    out = benchmark_lookup(read_sites(str(p)), real["results"], earth["id"].to_numpy(), real["dataset"].grid,
                           real["land"], real["earth_places"])
    assert out[0]["cell"]["id"] == int(earth["id"].iat[k_pass]) and out[0]["missions"]["rover"]["rank"] == 1
    assert out[1]["cell"]["id"] == int(earth["id"].iat[k_fail])
    assert not out[1]["missions"]["rover"]["pass"] and out[1]["missions"]["rover"]["rank"] is None
    assert out[1]["missions"]["rover"]["fail"] == list(r.earth_gates.reasons[k_fail])
    if os.path.exists(BENCHMARK_CSV):
        sites = read_sites(BENCHMARK_CSV)
        res = benchmark_lookup(sites, real["results"], earth["id"].to_numpy(), real["dataset"].grid,
                               real["land"], real["earth_places"])
        assert len(res) == len(sites) and all(x["cell"]["id"] >= 0 for x in res)


# ----------------------------------------------------------------------------- team decisions of 2026-11-15
def test_similarity_variables_used_and_missing_per_pair(real_dir):
    """Decision 3 (zone_twin only): since contract revision 6 no shipped mission uses the
    z-score rule, so no mission file carries sim_vars_used / sim_missing_bits and the tiles
    carry no z-scores (the zone_twin build still does: test_missions_similarity)."""
    b = load_bundle(real_dir)
    for mid in ("rover", "solar", "lunar_base"):
        assert not {"sim_vars_used", "sim_missing_bits"} & set(b.columns(f"earth_{mid}.bin"))
    assert not [c for c in b.columns("earth_detail_05.bin") if c.startswith("z.")]


def test_approved_texts_are_in_the_bundle_verbatim(real, ecfg):
    """Decisions 1-5 (2026-11-15) and the morning decision of 2026-11-15: the English web
    texts are copied verbatim from docs/DECISIONS.md into similarity.json 'texts' (the
    lunar day length of the solar template is filled at build time); the solar pair text
    replaces the solar limitation of decision 5 and is a per-pair template, not a mission
    card text."""
    decisions = open(os.path.join(os.path.dirname(ROOT), "docs", "DECISIONS.md"), encoding="utf-8").read()
    assert ecfg.v("similarity_rule")["lunar_base"] == "percentile_and_real_tolerance"
    assert real["manifest"]["similarity_rule"] == "per_mission" and real["manifest"]["contract_revision"] == 8
    approved = ecfg.v("approved_texts")
    assert set(approved) == {"similarity_meaning", "similarity_meaning_real_values", "similarity_meaning_lunar_base",
                             "rock_note", "missing_temperature_mark", "missing_temperature_note", "twin_sharing_note",
                             "no_twin_note", "solar_limitation", "lunar_base_pair_sentence", "no_twin_note_lunar_base",
                             "solar_similarity_saturation"}
    lunar_base_texts = {"similarity_meaning_lunar_base", "lunar_base_pair_sentence", "no_twin_note_lunar_base"}
    audit_texts = {"solar_similarity_saturation"}   # statistical audit 2026-11-15: test_audit_corrections_1
    for key, t in approved.items():   # the Lunar base texts of 08:55 are checked in test_lunar_base_position
        if key != "missing_temperature_mark" and key not in lunar_base_texts | audit_texts:  # the short mark: the team's answer 3
            assert f'> "{t["text"]}"' in decisions, key
    assert approved["missing_temperature_mark"]["text"] == "no temperature data: similarity computed with 3 variables"
    sj = real["objects"]["similarity.json"]
    filled = {k: v["text"].replace("{lunar_day}", f"{ecfg.v('lunar_day_earth_days'):.1f}") for k, v in approved.items() if "text" in v}
    assert {k: v["text"] for k, v in sj["texts"].items() if "text" in v and k in approved} == filled
    assert sj["texts"]["no_twin_note_lunar_base"] == approved["no_twin_note_lunar_base"]
    solar = next(m for m in real["objects"]["missions.json"]["missions"] if m["id"] == "solar")
    assert approved["solar_limitation"]["mission_card"] is False
    assert all(filled["solar_limitation"] != x for x in solar["known_limitations"])
    # decision 2: bare ground is information only (revision 6: no z-score keys in the shipped
    # similarity.json; every twin row lists it as not part of the similarity)
    for mid, tw in real["objects"]["twins.json"]["missions"].items():
        assert "rock_or_bare_frac" in tw["twins"][0]["not_part_of_similarity"], mid
    assert "rock_or_bare_frac" not in json.dumps([m["similarity"].get("variables") for m in real["objects"]["missions.json"]["missions"]])
