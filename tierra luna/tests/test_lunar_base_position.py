"""Tests of the team decision of 2026-11-15 08:55 CET (the team lead's delegate on his
behalf): Lunar base pairs by thermal POSITION and real terrain (rule
percentile_and_real_tolerance, design D4b of docs/LUNAR_BASE_PROPOSAL.md), and the six
lunar regions of docs/MISSION_ZONES.md (moon_base.bin 'region', mission_zones.json).

Tolerances, weights, populations and zones are read from engine_config.json; the figures
typed here are those of the checked proposal that the implementation must reproduce.
"""
import copy
import json
import os
import re
import sys

import numpy as np
import pandas as pd
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from engine.bundle_v2 import load_bundle, validate_bundle_v2  # noqa: E402
from engine.config import Setting, load_engine_config  # noqa: E402
from engine.export import write_bundle  # noqa: E402
from engine.lunar_regions import load_zone_texts, region_codes  # noqa: E402
from engine.real_similarity import group_nopair_kinds, group_reasons, midrank_percentile, rule_spec  # noqa: E402

REAL = "real_1deg"
CHECKER_PAIRS = "/tmp/claude-0/-home-user-NASA/7228bb30-9725-52d9-8d71-762c955fd0bd/scratchpad/stars/lunarbase-check/pairs_D4b.csv"


@pytest.fixture(scope="module")
def ecfg():
    return load_engine_config(dataset=REAL)


@pytest.fixture(scope="module")
def real():
    from engine.build import build_bundle
    return build_bundle(dataset=REAL)


@pytest.fixture(scope="module")
def real_dir(real, tmp_path_factory):
    d = str(tmp_path_factory.mktemp("v2lb"))
    write_bundle(real["files"], d)
    return d


@pytest.fixture(scope="module")
def lb(real_dir):
    b = load_bundle(real_dir)
    m = next(x for x in b.json("missions.json")["missions"] if x["id"] == "lunar_base")
    twin = b.int_column("earth_lunar_base.bin", "twin")
    return b, m, twin != b.manifest["encoding"]["int32_missing"]


# ----------------------------------------------------------------------------- configuration
def test_the_confirmed_design_is_configured_with_who_set_it(ecfg):
    rv = ecfg.v("real_value_similarity")
    m = rv["missions"]["lunar_base"]
    assert ecfg.v("similarity_rule")["lunar_base"] == m["rule"] == "percentile_and_real_tolerance"
    got = [(v["variable"], v["role"], v["scale"], v["weight"], v["tolerance"]) for v in m["variables"]]
    assert got == [("tmin_k", "key", "percentile_within_population", 0.4, 10.0),
                   ("lst_diurnal_amp_k", "key", "percentile_within_population", 0.4, 10.0),
                   ("slope_deg", "secondary", "real", 0.1, 2.0), ("roughness_m", "secondary", "real", 0.1, 30.0)]
    spec = rule_spec(m, rv["filter_bound_multiplier"], int(rv["score_decimals"]))
    assert list(spec.bound) == [10.0, 10.0, 4.0, 60.0]
    for v in m["variables"]:
        assert "2026-11-15 08:55 CET" in v["tolerance_set_by"] and v["why"] and v["unit"] and v["real_unit"]
    for v in m["variables"][2:]:
        assert "illustrative team values" in v["tolerance_set_by"] and "rover_preset.py" in v["tolerance_set_by"]
    assert m["zone"] == {**m["zone"], "kind": "similarity_zone", "similarity_zones_key": "lunar_base"}
    assert "Artemis" not in m["zone"]["name"] and m["zone"]["name"] == "NASA's nine candidate landing regions near the lunar south pole"
    assert set(m["populations"]) == {"EARTH", "MOON"} and m["percentile"]["formula"]
    assert m["nopair_groups"] == {"thermal_position": ["tmin_k", "lst_diurnal_amp_k"], "terrain": ["slope_deg", "roughness_m"]}
    assert rv["info_differences"]["lunar_base"] == ["temp_k", "elevation_rel_m", "irradiance_kwh_m2_day"]
    # the Earth coldest temperature is MODELLED air temperature, the lunar one a MEASURED surface value
    src = rv["variables"]["tmin_k"]["sources"]
    assert "MODELLED" in src["EARTH"]["level"] and "AIR" in src["EARTH"]["text"]
    assert "MEASURED" in src["MOON"]["level"] and "SURFACE" in src["MOON"]["text"]


def test_no_offset_population_or_region_threshold_is_typed_in_the_code():
    """Numbers in the code (strings and comments aside): no kelvin offset, tolerance,
    region threshold or population size is typed; they are read from engine_config."""
    import io
    import tokenize
    numbers = set()
    for f in ("real_similarity.py", "pipeline.py", "lunar_regions.py"):
        with open(os.path.join(ROOT, "engine", f), encoding="utf-8") as fh:
            for tok in tokenize.generate_tokens(io.StringIO(fh.read()).readline):
                if tok.type == tokenize.NUMBER:
                    numbers.add(float(tok.string))
    for value in (273.15, 90.0, 75.0, 30.0, 1200.0, 2.0 * 30.0, 2419.0, 280.0, 103.0, 450.0):
        assert value not in numbers, value


# ----------------------------------------------------------------------------- the rule on hand-built cases
def test_midrank_percentile_by_hand():
    p = midrank_percentile(np.array([3.0, 1.0, np.nan, 2.0, 2.0]))
    assert np.isnan(p[2])                                       # no value: no percentile, not counted in n
    assert list(p[[0, 1, 3, 4]]) == [87.5, 12.5, 50.0, 50.0]     # 100 * (rank - 0.5) / 4, ties averaged
    assert np.all(np.isnan(midrank_percentile(np.array([np.nan, np.nan]))))


def test_group_reasons_by_hand():
    rule = {"variables": [{"variable": "a", "role": "key", "weight": 0.4, "tolerance": 10.0, "scale": "percentile_within_population"},
                          {"variable": "b", "role": "key", "weight": 0.4, "tolerance": 10.0, "scale": "percentile_within_population"},
                          {"variable": "s", "role": "secondary", "weight": 0.1, "tolerance": 2.0},
                          {"variable": "r", "role": "secondary", "weight": 0.1, "tolerance": 30.0}]}
    spec = rule_spec(rule, {"key": 1.0, "secondary": 2.0}, 6)
    groups = {"thermal_position": ["a", "b"], "terrain": ["s", "r"]}
    kinds = group_nopair_kinds(groups)
    mv = np.array([[50.0, 50.0, 1.0, 10.0],      # cell 0: thermal match for row 0, terrain far
                   [90.0, 90.0, 5.0, 100.0]])    # cell 1: terrain match for row 0, thermal far
    ev = np.array([[52.0, 48.0, 5.5, 110.0],     # each group met by a different cell -> no single cell
                   [52.0, 48.0, 20.0, 400.0],    # thermal met, terrain nowhere
                   [10.0, 10.0, 5.0, 100.0],     # terrain met, thermal nowhere
                   [10.0, 10.0, 20.0, 400.0],    # neither
                   [np.nan, 10.0, 1.0, 10.0]])   # key value missing on Earth
    out = group_reasons(ev, mv, spec, groups, np.arange(5))
    assert [kinds[k] for k in out["kind"]] == ["no_single_cell_meets_both", "no_cell_meets_terrain",
                                               "no_cell_meets_thermal_position", "no_cell_meets_either",
                                               "key_value_missing_on_earth"]
    assert out["var"][1] == 3 and out["gap"][1] == pytest.approx(300.0)       # roughness 300 m at cell 1 (ratio 5 > slope's 3.75)
    assert out["var"][2] == 0 and out["gap"][2] == pytest.approx(40.0)        # 40 points from cell 0
    assert out["var2"][3] == 3 and np.isfinite(out["gap2"][3]) and out["var2"][1] == -1


# ----------------------------------------------------------------------------- results of the checked proposal
def test_results_match_the_checked_proposal(real):
    r = real["results"]["lunar_base"]
    ex = r.extra["real"]
    p = r.earth_gates.passed
    earth = real["cells"]["EARTH"]
    assert int(p.sum()) == 2419 and ex["zone_cells"] == 280
    assert ex["populations"] == {"tmin_k": {"EARTH": 2419, "MOON": 280}, "lst_diurnal_amp_k": {"EARTH": 2419, "MOON": 280}}
    paired = r.rank > 0
    assert int(paired.sum()) == 450
    tw = r.twin_id[paired]
    uniq, cnt = np.unique(tw, return_counts=True)
    k = int(np.lexsort((uniq, -cnt))[0])
    assert (len(uniq), int(uniq[k]), int(cnt[k]), round(100 * cnt[k] / tw.size, 1)) == (103, 62848, 25, 5.6)
    i = int(np.flatnonzero(r.rank == 1)[0])
    assert (int(earth["id"].iat[i]), int(r.twin_id[i])) == (17538, 63528)
    assert (round(r.similarity_pct[i], 1), round(r.final_published[i], 1)) == (97.3, 72.3)
    assert (earth["lat_deg"].iat[i], earth["lon_deg"].iat[i]) == (41.5, 78.5)
    kinds = ex["nopair_kinds"]
    nk = ex["nopair_kind"][p]
    assert {kd: int((nk == j).sum()) for j, kd in enumerate(kinds)} == {
        "key_value_missing_on_earth": 0, "no_cell_meets_thermal_position": 237, "no_cell_meets_terrain": 943,
        "no_cell_meets_either": 196, "no_single_cell_meets_both": 593}
    # every unpaired point keeps its suitability and has no similarity, final or rank
    un = p & ~paired
    assert np.all(np.isfinite(r.earth_suit.score[un])) and np.all(np.isnan(r.similarity_pct[un]))
    assert np.all(np.isnan(r.final[un])) and np.all(r.rank[un] == 0)
    if os.path.exists(CHECKER_PAIRS):                 # the checker's own code, pair by pair
        chk = pd.read_csv(CHECKER_PAIRS)
        mine = dict(zip(earth["id"].to_numpy()[paired].tolist(), r.twin_id[paired].tolist()))
        assert dict(zip(chk["id"].tolist(), chk["twin"].tolist())) == mine


def test_every_pair_is_within_its_tolerance_or_bound(real, lb):
    """The team lead's check after every change of method: no key variable beyond its
    tolerance and no secondary beyond its bound, on any pair, in the engine (double
    precision, compared unit) and in the bundle (float32)."""
    r = real["results"]["lunar_base"]
    ex = r.extra["real"]
    spec = ex["spec"]
    paired = r.rank > 0
    d = ex["compared_diff"][paired]
    for q in range(len(spec.variables)):
        assert np.all(np.isfinite(d[:, q])) and np.all(d[:, q] <= spec.bound[q]), spec.variables[q]
    assert np.all(d[:, spec.key] <= spec.tau[spec.key])          # keys: within one tolerance
    b, m, pb = lb
    pf = m["similarity"]["pairs_file"]
    for v in m["similarity"]["variables"]:
        dd = b.column(pf, v["compared_columns"]["diff"])[pb]
        assert np.all(dd <= v["bound"] * (1 + 1e-6)), v["variable"]
    assert validate_bundle_v2(b.path)["ok"]


def test_coldest_temperature_difference_is_in_kelvin(real, lb):
    """The proposal's tables wrote the coldest-temperature difference in degrees C (207.9).
    Both tables store tmin_c in degrees C (the lunar one is tmin_k - 273.15), so the
    difference is the same number in K; the bundle stores K on both sides."""
    moon = real["cells"]["MOON"]
    assert np.allclose(moon["tmin_c"], moon["tmin_k"] - 273.15, atol=1e-9)
    b, m, pb = lb
    pf = m["similarity"]["pairs_file"]
    v = next(x for x in m["similarity"]["variables"] if x["variable"] == "tmin_k")
    assert v["real_unit"] == "K" and v["unit"] == "percentile points"
    e, mo, d = (b.column(pf, f"tmin_k.{s}")[pb].astype(np.float64) for s in ("earth", "moon", "diff"))
    assert np.all(e > 230) and np.all(mo < 80)                    # both in K (Earth >= -35.5 C, Moon <= -198 C)
    assert round(float(np.median(d)), 1) == 207.9 and round(float(np.percentile(d, 90)), 1) == 210.6
    col = next(c for c in b.file_entry(pf)["columns"] if c["name"] == "tmin_k.diff")
    assert col["unit"] == "K"


# ----------------------------------------------------------------------------- bundle (contract revision 6)
def test_bundle_carries_positions_real_values_and_reasons(lb):
    b, m, paired = lb
    sb = m["similarity"]
    assert sb["rule"] == "percentile_and_real_tolerance" and sb["paired_count"] == 450 == m["ranked_count"]
    assert sb["unpaired_count"] == 1969 == m["passing_without_similarity"]
    assert sb["populations"]["EARTH"]["cells"] == 2419 and sb["populations"]["MOON"]["cells"] == 280
    assert sb["zone"]["cells"] == 280 and "Artemis" not in sb["zone"]["name"]
    assert sb["distinct_twins"] == 103 and sb["largest_share"] == {"twin_id": 62848, "earth_cells": 25, "share": 0.0556}
    pcols = set(b.columns(sb["pairs_file"]))
    for v in sb["variables"]:
        assert set(v["pairs_columns"].values()) <= pcols and set(v["compared_columns"].values()) <= pcols
        if v["scale"] == "percentile_within_population":
            e, mo, d = (b.column(sb["pairs_file"], v["pairs_columns"][k]) for k in ("earth_pct", "moon_pct", "diff_pct"))
            assert np.allclose(np.abs(e - mo)[paired], d[paired], atol=1e-4)
            assert np.all((e[paired] > 0) & (e[paired] < 100))
    for x in sb["info_columns"]:
        assert set(x["columns"].values()) <= pcols
    assert {"nopair_kind", "nopair_var", "nopair_gap", "nopair_var2", "nopair_gap2", "list_order"} <= pcols
    assert set(b.columns("earth_lunar_base.bin")) >= {f"s.{v['variable']}" for v in sb["variables"]}
    kind = b.int_column(sb["pairs_file"], "nopair_kind")
    sent = b.manifest["encoding"]["int32_missing"]
    assert np.array_equal(kind == sent, paired)
    both = kind == sb["nopair_kinds"].index("no_cell_meets_either")
    assert np.all(b.int_column(sb["pairs_file"], "nopair_var2")[both] != sent)
    assert np.all(b.int_column(sb["pairs_file"], "nopair_var2")[~both] == sent)
    tw = b.json("twins.json")["missions"]["lunar_base"]
    assert tw["rule"] == "percentile_and_real_tolerance" and set(tw["twins"][0]["percentiles"]) == {"tmin_k", "lst_diurnal_amp_k"}
    assert {"temp_k", "elevation_rel_m"} <= set(tw["twins"][0]["not_part_of_similarity"])
    assert "z" not in tw["twins"][0]
    man = b.manifest
    assert man["contract_revision"] == 6 and man["counts"]["missions"]["lunar_base"]["ranked_EARTH"] == 450
    assert man["counts"]["missions"]["lunar_base"]["unpaired_EARTH"] == 1969


def test_number_one_and_the_approved_pair_sentence(lb, ecfg):
    b, m, paired = lb
    ex = b.json("explain.json")["missions"]["lunar_base"][0]
    assert (ex["rank"], ex["id"], ex["similarity"]["twin"]["id"]) == (1, 17538, 63528)
    assert "position, not of temperature" in ex["similarity"]["meaning"]
    want = ("This pair matches by relative thermal position, not by equal temperatures: this site's coldest temperature and "
            "daily swing rank among Earth's lunar-base candidates where its twin's rank among the cells of NASA's nine candidate "
            "landing regions near the lunar south pole. In real values the twin is 195 K colder on average (minimum -232 °C "
            "at the surface against -24.5 °C air temperature here) and its day-night swing is 138 K larger; slope differs "
            "by 0.5° and roughness by 0.3 m.")
    assert ex["similarity"]["pair_sentence"] == want
    tpl = b.json("similarity.json")["texts"]["lunar_base_pair_sentence"]
    assert tpl["missions"] == ["lunar_base"] and tpl["mission_card"] is False and "Artemis" not in tpl["text"]
    for name, ph in tpl["placeholders"].items():
        assert "{" + name + "}" in tpl["text"] and ph["column"] in b.columns(ph["file"])
    # the sentence's fixed words hold on every pair: the twin is colder and swings more
    pf = m["similarity"]["pairs_file"]
    assert np.all(b.column(pf, "info.temp_k.moon")[paired] < b.column(pf, "info.temp_k.earth")[paired])
    assert np.all(b.column(pf, "lst_diurnal_amp_k.moon")[paired] > b.column(pf, "lst_diurnal_amp_k.earth")[paired])


def test_lunar_base_texts_say_position_not_temperature(lb, ecfg):
    b, m, _ = lb
    texts = b.json("similarity.json")["texts"]
    meaning = texts["similarity_meaning_lunar_base"]["text"]
    assert "positions" in meaning and "not equally cold" in meaning and "real values" in meaning
    rv = ecfg.v("real_value_similarity")["missions"]["lunar_base"]
    bounds = {v["variable"]: v["tolerance"] * (1 if v["role"] == "key" else 2) for v in rv["variables"]}
    assert f"{bounds['tmin_k']:g} percentile points" in meaning
    assert f"{bounds['slope_deg']:g} degrees and {bounds['roughness_m']:g} m" in meaning
    for k in ("similarity_meaning", "missing_temperature_mark", "missing_temperature_note"):
        assert texts[k]["missions"] == [] and "no longer applies" in texts[k]["status"]
    assert "FIRST sentence only" in texts["twin_sharing_note"]["where"]
    variants = texts["no_twin_note_lunar_base"]["variants"]
    assert set(variants) == set(m["similarity"]["nopair_kinds"])
    for t in [meaning, texts["lunar_base_pair_sentence"]["text"]] + list(variants.values()):
        assert "Artemis" not in t
    assert "lunar_base" not in json.dumps(b.json("similarity.json").get("z_rule_missions", []))


def test_slider_on_lunar_base_similarity_weights_recomputes_exactly(real, lb):
    b, m, paired = lb
    new = {"lunar_base": {"tmin_k": 0.25, "lst_diurnal_amp_k": 0.25, "slope_deg": 0.25, "roughness_m": 0.25}}
    rep = validate_bundle_v2(b.path, sim_weights=new)
    sc = real["results"]["lunar_base"].extra["real"]["scores"][real["results"]["lunar_base"].earth_gates.passed]
    want = np.where(np.isfinite(sc[:, 0]), 100.0 * (0.25 * sc[:, 0] + 0.25 * sc[:, 1] + 0.25 * sc[:, 2] + 0.25 * sc[:, 3]), np.nan)
    got = rep["recomputed"]["lunar_base"]["similarity"]
    assert np.allclose(got, want, equal_nan=True, rtol=0, atol=1e-9)
    assert np.array_equal(rep["recomputed"]["lunar_base"]["rank"] > 0, paired)


# ----------------------------------------------------------------------------- lunar regions (revision 6)
def test_region_counts_and_mission_zones(real, ecfg):
    moon = real["cells"]["MOON"]
    codes, regs = region_codes(moon, ecfg)
    assert [r["code"] for r in regs] == list("ABCDEF")
    assert [int((codes == k).sum()) for k in range(6)] == [280, 5120, 5400, 6686, 25971, 21343]
    zr = ecfg.v("lunar_regions")["mission_zone_regions"]
    assert zr == {"rover": ["A", "B"], "solar": ["D"], "lunar_base": ["A"]}
    for mid, letters in zr.items():
        want = np.isin(codes, ["ABCDEF".index(c) for c in letters])
        assert np.array_equal(real["results"][mid].extra["real"]["zone_mask"], want), mid
    lat, lon = moon["lat_deg"].to_numpy(), moon["lon_deg"].to_numpy()
    assert np.all(lat[codes == 2] >= 75) and np.all(np.abs(lon[codes == 4]) > 90) and np.all(np.abs(lon[codes == 5]) <= 90)


def test_moon_region_column_and_mission_zones_json(real, real_dir):
    b = load_bundle(real_dir)
    reg = b.int_column("moon_base.bin", "region")
    codes, _ = region_codes(real["cells"]["MOON"], real["engine_cfg"])
    assert np.array_equal(reg, codes)
    mz = b.json("mission_zones.json")
    assert list(mz)[:5] == ["consulted_on", "source_document", "regions", "mission_zone_regions", "region_column"]
    assert [(r["code"], r["cells"]) for r in mz["regions"]] == list(zip("ABCDEF", [280, 5120, 5400, 6686, 25971, 21343]))
    assert all(r["label"] and r["rule"] for r in mz["regions"])
    texts, status = load_zone_texts(real["engine_cfg"])
    assert b.manifest["mission_zone_texts"]["status"] == status
    if texts is None:
        assert mz["texts"] is None and b.manifest["mission_zone_texts"]["texts_present"] is False
    else:                                   # verbatim from engine/mission_zone_texts.json
        assert mz["texts"] == {k: texts[k] for k in ("general_note", "zone_why", "outside")}
        assert [r["label"] for r in mz["regions"]] == [texts["region_labels"][c] for c in "ABCDEF"]
        assert mz["consulted_on"] == texts["consulted_on"]


def test_zone_texts_file_absent_incomplete_or_missing_a_text(tmp_path, ecfg):
    def cfg_with(path):
        e = load_engine_config(dataset=REAL)
        v = copy.deepcopy(e.v("lunar_regions"))
        v["texts_file"] = str(path)
        e.lunar_regions = Setting(value=v, why="test")
        return e
    t, status = load_zone_texts(cfg_with(tmp_path / "absent.json"))
    assert t is None and "absent" in status
    (tmp_path / "half.json").write_text('{"consulted_on": "2026-11-15"', encoding="utf-8")
    t, status = load_zone_texts(cfg_with(tmp_path / "half.json"))
    assert t is None and "not valid JSON" in status
    (tmp_path / "part.json").write_text(json.dumps({"consulted_on": "2026-11-15"}), encoding="utf-8")
    t, status = load_zone_texts(cfg_with(tmp_path / "part.json"))
    assert t is None and "incomplete" in status
    full = {"consulted_on": "2026-11-15", "source_document": "docs/MISSION_ZONES.md",
            "region_labels": {c: f"label {c}" for c in "ABCDEF"}, "general_note": "note",
            "zone_why": {m: "why" for m in ("rover", "solar", "lunar_base")},
            "outside": {"rover": {c: "x" for c in "CDEF"}, "solar": {c: "x" for c in "ABCEF"},
                        "lunar_base": {c: "x" for c in "BCDEF"}}, "approved_by": "test"}
    (tmp_path / "full.json").write_text(json.dumps(full), encoding="utf-8")
    t, status = load_zone_texts(cfg_with(tmp_path / "full.json"))
    assert t == full and "verbatim" in status
    del full["outside"]["solar"]["E"]
    (tmp_path / "gap.json").write_text(json.dumps(full), encoding="utf-8")
    with pytest.raises(ValueError, match="outside.solar.E"):
        load_zone_texts(cfg_with(tmp_path / "gap.json"))
