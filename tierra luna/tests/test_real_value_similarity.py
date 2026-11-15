"""Tests of the team decision of 2026-11-15 (morning): similarity on real values within
stated tolerances for Rover and Solar panels; Lunar base unchanged (zone_twin).

Tolerances, weights and zones are read from engine_config.json, never typed here,
except in the hand-built cases and in the figures of the checked proposal
(docs/ANALOG_PRINCIPLE.md) that the implementation must reproduce.
"""
import hashlib
import json
import os
import re
import sys

import numpy as np
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from engine.bundle_v2 import load_bundle, validate_bundle_v2  # noqa: E402
from engine.config import (Setting, load_engine_config, mission_similarity_rule, similarity_rule,  # noqa: E402
                           similarity_rules)
from engine.export import write_bundle  # noqa: E402
from engine.real_similarity import (NOPAIR_KINDS, area_weighted_mean, find_twins, list_order,  # noqa: E402
                                    rule_spec, toa_daily_insolation_kwh, zone_mask_real)

REAL = "real_1deg"

# The shipped bundle before this change (contract revision 4, built 2026-11-15 from the
# same inputs): the Lunar base files and JSON parts must stay exactly as they were.
LUNAR_BASE_BEFORE = {
    "earth_lunar_base.bin": "56c1fc9a29ae825057f292929330ec60de6494c6df78422db59526b84e577f98",
    "moon_lunar_base.bin": "55f1843246be6f6afdb09babc4b04eb4d006b8bba41ddfc0aca3547d924fd635",
    "twins.json/missions/lunar_base": "412ccab94727bd95151dd11843f06551f4a479347356f3b3b603e00951ce3895",
    "explain.json/missions/lunar_base": "f43a8af63e2ba2a5e91b6d302d8af36f7b6cae8bab2a8e8af854b5024a750143",
    "missions.json/missions[lunar_base]": "12316c9ccd0962cc799ef7cf26b230a520ca0e5a978f7a77609b5efe719354f5",
}


def _digest(obj) -> str:
    return hashlib.sha256(json.dumps(obj, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()


@pytest.fixture(scope="module")
def ecfg():
    return load_engine_config(dataset=REAL)


@pytest.fixture(scope="module")
def real():
    from engine.build import build_bundle
    return build_bundle(dataset=REAL)


@pytest.fixture(scope="module")
def real_dir(real, tmp_path_factory):
    d = str(tmp_path_factory.mktemp("v2rv"))
    write_bundle(real["files"], d)
    return d


# ----------------------------------------------------------------------------- configuration
def test_rule_is_a_per_mission_setting(ecfg):
    rules = similarity_rules(ecfg)
    assert rules == {"rover": "real_value_tolerance", "solar": "real_value_tolerance", "lunar_base": "zone_twin"}
    assert similarity_rule(ecfg) == "per_mission"
    assert mission_similarity_rule(ecfg, "lunar_base") == "zone_twin"
    e = load_engine_config(dataset=REAL)
    e.similarity_rule = Setting(value="zone_twin", why="test")   # one string = every mission (earlier rules stay available)
    assert set(similarity_rules(e).values()) == {"zone_twin"} and similarity_rule(e) == "zone_twin"


def test_every_tolerance_weight_and_zone_is_configured_with_who_set_it(ecfg):
    rv = ecfg.v("real_value_similarity")
    for mid in ("rover", "solar"):
        m = rv["missions"][mid]
        assert m["zone"]["source"] and m["zone"]["why"] and m["weights_why"]
        keys = [v for v in m["variables"] if v["role"] == "key"]
        assert sum(v["weight"] for v in keys) == pytest.approx(0.8)            # key variables carry 80 %
        assert sum(v["weight"] for v in m["variables"]) == pytest.approx(1.0)
        for v in m["variables"]:
            assert v["tolerance"] > 0 and v["unit"] and v["tolerance_set_by"] and v["why"]
            assert v["variable"] in rv["variables"]
    assert rv["filter_bound_multiplier"] == {"key": 1.0, "secondary": 2.0}
    by = {(mid, v["variable"]): v for mid in ("rover", "solar") for v in rv["missions"][mid]["variables"]}
    assert "illustrative team values" in by[("rover", "slope_deg")]["tolerance_set_by"]
    assert "delegate" in by[("rover", "elevation_rel_m")]["tolerance_set_by"]
    assert "delegate" in by[("solar", "irradiance_toa_kwh_m2_day")]["tolerance_set_by"]
    assert "not used" in json.dumps(rv["reference_tolerances_not_used"])


def test_no_tolerance_or_zone_is_typed_in_the_engine_code():
    src = open(os.path.join(ROOT, "engine", "real_similarity.py"), encoding="utf-8").read()
    src += open(os.path.join(ROOT, "engine", "pipeline.py"), encoding="utf-8").read()
    code = "\n".join(l for l in src.splitlines() if not l.strip().startswith(("#", '"', "*")))
    for literal in ("0.6", "500.0", "30.0", "-75", "-1200", "1361", "23.44", "0.0167", "282.9"):
        assert not re.search(r"(?<![\w.])" + re.escape(literal) + r"(?![\w])", code), literal


# ----------------------------------------------------------------------------- derived variables
def test_toa_formula_reproduces_the_checked_figures(ecfg):
    toa = ecfg.v("toa_insolation")
    lats = [float(k) for k in toa["reference_values_kwh_m2_day"]]
    got = toa_daily_insolation_kwh(np.array(lats), toa)
    assert [round(float(x), 2) for x in got] == list(toa["reference_values_kwh_m2_day"].values())  # 9.97 / 8.77 / 7.37 / 5.67
    # Kepler orbit sampled in time: the annual mean is the same in both hemispheres
    lat = np.arange(-89.5, 90.0, 1.0)
    q = toa_daily_insolation_kwh(lat, toa)
    assert np.allclose(q, q[::-1], atol=1e-9) and np.all(np.diff(q[90:]) < 0)


def test_relative_elevation_is_centred_on_each_body_area_weighted_mean(real):
    real_ctx = real["results"]["rover"].extra["real"]
    notes = real_ctx["derived"].notes["elevation_rel_m"]
    e, m = real["cells"]["EARTH"], real["cells"]["MOON"]
    for body, df in (("EARTH", e), ("MOON", m)):
        el = df["elevation_m"].to_numpy(dtype=np.float64)
        w = np.cos(np.radians(df["lat_deg"].to_numpy(dtype=np.float64)))
        ok = np.isfinite(el)
        mean = (el[ok] * w[ok]).sum() / w[ok].sum()
        assert notes[body]["body_mean"] == pytest.approx(mean, abs=1e-9)
        assert np.allclose(real_ctx["derived"].values["elevation_rel_m"][body][ok], el[ok] - mean)
    assert round(notes["EARTH"]["body_mean"], 1) == 695.9 and round(notes["MOON"]["body_mean"], 1) == -248.4
    assert area_weighted_mean(np.array([np.nan]), np.array([0.0])) is None


def test_solar_zone_is_analog_finders_equatorial_maria(real, ecfg):
    import inspect
    import analog_finder
    src = inspect.getsource(analog_finder.build_lunar_reference_zones)
    assert '(np.abs(lat) <= 30.0) & (moon_norm_df["elevation_m"] <= -1200.0)' in src
    z = ecfg.v("real_value_similarity")["missions"]["solar"]["zone"]
    moon = real["cells"]["MOON"]
    mask = zone_mask_real(moon, z)
    lat, el = moon["lat_deg"].to_numpy(), moon["elevation_m"].to_numpy()
    assert np.array_equal(mask, (np.abs(lat) <= 30.0) & (el <= -1200.0))
    assert int(mask.sum()) == 6686 == real["results"]["solar"].extra["real"]["zone_cells"]


# ----------------------------------------------------------------------------- the rule on hand-built cases
def _spec(variables):
    return rule_spec({"variables": variables}, {"key": 1.0, "secondary": 2.0}, 6)


def test_score_filter_tie_and_missing_values_by_hand():
    spec = _spec([{"variable": "a", "role": "key", "weight": 0.8, "tolerance": 1.0},
                  {"variable": "b", "role": "secondary", "weight": 0.2, "tolerance": 10.0}])
    moon = np.array([[0.0, 0.0], [5.0, 0.0], [5.0, 0.0], [9.0, np.nan], [20.0, 0.0]])
    ids = np.array([3, 7, 8, 11, 12])
    earth = np.array([
        [0.5, 15.0],       # zone cell 3: a within 1, b within 2 x 10 -> pair
        [5.0, 0.0],        # cells 7 and 8 tie exactly -> lowest id 7
        [9.2, 50.0],       # cell 11 has no b: the secondary is ignored -> pair with a only
        [2.6, 0.0],        # no cell has a within 1 -> no_zone_cell_within_bound, gap 2.4
        [np.nan, 0.0],     # key missing on Earth -> no pair
        [20.0, 25.0],      # cell 12: a equal but b at 25 > 20 -> no_joint_match on b
    ])
    rt = find_twins(earth, moon, ids, spec, chunk_rows=2)
    assert rt.twin.tolist() == [3, 7, 11, -1, -1, -1]
    s0 = [round(float(np.exp(-0.5 * 0.5 ** 2)), 6), round(float(np.exp(-0.5 * 1.5 ** 2)), 6)]
    assert rt.scores[0].tolist() == s0
    assert rt.similarity[0] == 100.0 * (0.8 * s0[0] + 0.2 * s0[1]) / (0.8 + 0.2)
    assert rt.similarity[1] == 100.0
    assert np.isnan(rt.scores[2, 1]) and rt.similarity[2] == 100.0 * (0.8 * round(float(np.exp(-0.5 * 0.2 ** 2)), 6)) / 0.8
    assert [NOPAIR_KINDS[k] for k in rt.nopair_kind[3:]] == ["no_zone_cell_within_bound", "key_value_missing_on_earth",
                                                             "no_joint_match"]
    assert rt.nopair_var[3:].tolist() == [0, 0, 1] and rt.nopair_gap[3] == pytest.approx(2.4) and rt.nopair_gap[5] == 25.0
    assert np.all(rt.nopair_kind[:3] == -1) and np.all(np.isnan(rt.similarity[3:]))


def test_list_order_puts_unpaired_cells_after_the_pairs_by_suitability():
    rank = np.array([2, 0, 1, 0, 0, 0])
    suit = np.array([50.0, 80.0, 40.0, 80.0, np.nan, 90.0])
    passing = np.array([True, True, True, True, False, True])
    ids = np.array([10, 30, 20, 25, 5, 40])
    assert list_order(rank, suit, passing, ids).tolist() == [2, 4, 1, 5, 0, 3]


# ----------------------------------------------------------------------------- the results (checked proposal)
def test_rover_results_match_the_checked_proposal(real):
    r = real["results"]["rover"]
    e = real["cells"]["EARTH"]
    p = r.earth_gates.passed
    assert r.rule == "real_value_tolerance"
    assert int(p.sum()) == 10337 and int((r.twin_id[p] >= 0).sum()) == 10192
    top = int(np.flatnonzero(r.rank == 1)[0])
    assert int(e["id"].iat[top]) == 17566 and int(r.twin_id[top]) == 59895
    assert len(np.unique(r.twin_id[r.twin_id >= 0])) == 401


def test_solar_results_match_the_checked_proposal(real):
    r = real["results"]["solar"]
    e = real["cells"]["EARTH"]
    p = r.earth_gates.passed
    paired = p & (r.twin_id >= 0)
    assert int(p.sum()) == 18777 and int(paired.sum()) == 6360 and int((p & ~paired).sum()) == 12417
    top = int(np.flatnonzero(r.rank == 1)[0])
    assert int(e["id"].iat[top]) == 38464 and int(r.twin_id[top]) == 24296
    # a point without a twin keeps its suitability, has no similarity, final or rank, and carries a reason
    un = p & ~paired
    assert np.all(np.isfinite(r.earth_suit.score[un])) and np.all(np.isnan(r.similarity_pct[un]))
    assert np.all(np.isnan(r.final[un])) and np.all(r.rank[un] == 0)
    real_ctx = r.extra["real"]
    assert np.all(real_ctx["nopair_kind"][un] >= 0) and np.all(real_ctx["nopair_kind"][paired] == -1)
    k = real_ctx["spec"].variables.index("irradiance_toa_kwh_m2_day")
    assert (real_ctx["nopair_var"][un] == k).sum() >= 12416      # the commonest reason: sunlight above the atmosphere


@pytest.mark.parametrize("mission", ["rover", "solar"])
def test_every_surviving_pair_is_within_its_bounds(real, real_dir, mission):
    """The team lead's 04:48 check: no key variable beyond its tolerance and no secondary
    beyond twice its tolerance, on every pair (engine, double precision) and in the bundle."""
    r = real["results"][mission]
    rc = r.extra["real"]
    spec = rc["spec"]
    paired = r.earth_gates.passed & (r.twin_id >= 0)
    for q, v in enumerate(spec.variables):
        d = rc["diff"][paired, q]
        if spec.roles[q] == "key":
            assert np.all(np.isfinite(d)) and np.all(d <= spec.tau[q]), v
        else:
            assert np.all(d[np.isfinite(d)] <= 2.0 * spec.tau[q]), v
        assert np.allclose(d, np.abs(rc["earth_values"][paired, q] - rc["moon_values"][paired, q]), equal_nan=True)
    b = load_bundle(real_dir)
    m = next(x for x in b.json("missions.json")["missions"] if x["id"] == mission)
    for v in m["similarity"]["variables"]:
        d = b.column(m["similarity"]["pairs_file"], f"{v['variable']}.diff")
        d = d[np.isfinite(d)]
        assert d.size == int(paired.sum()) or v["role"] == "secondary"
        assert np.all(d <= v["bound"] * (1 + 1e-6)), v["variable"]


def test_lunar_base_is_unchanged_from_the_previous_bundle(real):
    files, objs = real["files"], real["objects"]
    assert hashlib.sha256(files["earth_lunar_base.bin"]).hexdigest() == LUNAR_BASE_BEFORE["earth_lunar_base.bin"]
    assert hashlib.sha256(files["moon_lunar_base.bin"]).hexdigest() == LUNAR_BASE_BEFORE["moon_lunar_base.bin"]
    assert _digest(objs["twins.json"]["missions"]["lunar_base"]) == LUNAR_BASE_BEFORE["twins.json/missions/lunar_base"]
    assert _digest(objs["explain.json"]["missions"]["lunar_base"]) == LUNAR_BASE_BEFORE["explain.json/missions/lunar_base"]
    lb = next(m for m in objs["missions.json"]["missions"] if m["id"] == "lunar_base")
    assert _digest(lb) == LUNAR_BASE_BEFORE["missions.json/missions[lunar_base]"]
    assert real["results"]["lunar_base"].rule == "zone_twin"
    assert objs["similarity.json"]["target"]["zones"].keys() == {"lunar_base"}


# ----------------------------------------------------------------------------- bundle (contract revision 5)
def test_bundle_carries_the_real_value_pairs(real, real_dir):
    b = load_bundle(real_dir)
    man = b.manifest
    assert man["contract_revision"] == 5 and man["similarity_rule"] == "per_mission"
    assert man["similarity_rules"] == {"rover": "real_value_tolerance", "solar": "real_value_tolerance",
                                       "lunar_base": "zone_twin"}
    ms = {m["id"]: m for m in b.json("missions.json")["missions"]}
    sj = b.json("similarity.json")
    assert sj["rules"] == man["similarity_rules"] and set(sj["real_value"]["missions"]) == {"rover", "solar"}
    for mid in ("rover", "solar"):
        sb = ms[mid]["similarity"]
        assert sb["rule"] == "real_value_tolerance" and sb["paired_count"] == ms[mid]["ranked_count"]
        assert sb["paired_count"] + sb["unpaired_count"] == ms[mid]["pass_counts"]["EARTH"]
        assert sb["unpaired_count"] == ms[mid]["passing_without_similarity"]
        assert {v["role"] for v in sb["variables"]} == {"key", "secondary"}
        cols = set(b.columns(f"earth_{mid}.bin"))
        assert {f"s.{v['variable']}" for v in sb["variables"]} <= cols
        assert not {"sim_vars_used", "sim_missing_bits"} & cols
        pcols = set(b.columns(sb["pairs_file"]))
        for v in sb["variables"]:
            assert {f"{v['variable']}.earth", f"{v['variable']}.moon", f"{v['variable']}.diff"} <= pcols
        assert {"list_order", "nopair_kind", "nopair_var", "nopair_gap"} <= pcols
        tw = b.json("twins.json")["missions"][mid]
        assert set(tw["twins"][0]["values"]) == {v["variable"] for v in sb["variables"]}
        assert "z" not in tw["twins"][0] and "temp_k" in tw["twins"][0]["not_part_of_similarity"]
        ex = b.json("explain.json")["missions"][mid][0]
        assert ex["rank"] == 1 and [x["variable"] for x in ex["similarity"]["variables"]] == [v["variable"] for v in sb["variables"]]
    assert {"lunar_base"} == {m for m, r in sj["rules"].items() if r == "zone_twin"}
    # the Earth sunlight above the atmosphere is stored per grid row and labelled DERIVED
    col = next(c for c in b.file_entry("earth_base.bin")["columns"] if c["name"] == "d.irradiance_toa_kwh_m2_day")
    assert col["rows"] == "grid_rows" and col["level"] == "DERIVED"
    assert validate_bundle_v2(real_dir)["ok"]


def test_solar_pairs_carry_ground_sunlight_and_the_share_lost(real, real_dir, ecfg):
    b = load_bundle(real_dir)
    pf = "earth_solar_pairs.bin"
    g, t, s = (b.column(pf, f"atm.{k}") for k in ("ground_kwh_m2_day", "toa_kwh_m2_day", "lost_share"))
    twin = b.int_column("earth_solar.bin", "twin")
    paired = twin != b.manifest["encoding"]["int32_missing"]
    assert np.all(np.isfinite(g[paired]) & np.isfinite(t[paired]) & np.isfinite(s[paired]))
    assert np.allclose(s[paired], 1.0 - g[paired].astype(np.float64) / t[paired], atol=1e-6)
    assert np.allclose(t, b.column(pf, "irradiance_toa_kwh_m2_day.earth"), equal_nan=True)
    i = int(np.flatnonzero(b.int_column(pf, "list_order") == 1)[0])          # number 1: 6.2 of 9.6, 36 % lost
    assert (round(float(g[i]), 1), round(float(t[i]), 1), round(100 * float(s[i]))) == (6.2, 9.6, 36)
    text = b.json("similarity.json")["texts"]["solar_limitation"]
    assert "29.5 Earth days" in text["text"] and "{lunar_day}" not in text["text"]
    assert len(re.findall(r"[.!?](?:\s|$)", text["text"])) <= 3
    assert not re.search(r"same (energy|charge|output)|charge(s)? the same|as much (energy|power)", text["text"], re.I)
    for name, ph in text["placeholders"].items():
        assert "{" + name + "}" in text["text"] and ph["column"] in b.columns(ph["file"])
    solar = next(m for m in b.json("missions.json")["missions"] if m["id"] == "solar")
    assert text["text"] not in solar["known_limitations"]                  # a per-pair text, not the mission card
    old = "Read the pair as 'similar terrain', not 'similar sunlight'."
    assert all(old not in x for x in solar["known_limitations"]) and old not in json.dumps(b.json("similarity.json"))


def test_meaning_texts_per_rule(real):
    texts = real["objects"]["similarity.json"]["texts"]
    assert "real values within stated tolerances" in texts["similarity_meaning_real_values"]["text"]
    assert texts["similarity_meaning_real_values"]["missions"] == ["rover", "solar"]
    assert texts["similarity_meaning"]["missions"] == ["lunar_base"]
    assert "same place in each world's range" in texts["similarity_meaning"]["text"]


def test_slider_on_similarity_weights_recomputes_exactly(real, real_dir):
    """The browser recompute with replacement similarity weights (twin fixed) equals the
    same formula applied to the engine's published scores, and the published weights
    reproduce every stored value (validate_bundle_v2)."""
    b = load_bundle(real_dir)
    new = {"rover": {"slope_deg": 0.2, "roughness_m": 0.2, "elevation_rel_m": 0.6}}
    rep = validate_bundle_v2(real_dir, sim_weights=new)
    r = real["results"]["rover"]
    rc = r.extra["real"]
    p = r.earth_gates.passed
    sc = rc["scores"][p]
    w = np.array([new["rover"][v] for v in rc["spec"].variables])
    num = np.zeros(sc.shape[0])
    den = np.zeros(sc.shape[0])
    for q in range(sc.shape[1]):
        ok = np.isfinite(sc[:, q])
        num = num + np.where(ok, w[q] * np.where(ok, sc[:, q], 0.0), 0.0)
        den = den + np.where(ok, w[q], 0.0)
    want = np.where(den > 0, 100.0 * num / np.where(den > 0, den, 1.0), np.nan)
    got = rep["recomputed"]["rover"]["similarity"]
    assert np.array_equal(np.isnan(got), np.isnan(want)) and np.array_equal(got[np.isfinite(got)], want[np.isfinite(want)])
    assert np.array_equal(rep["recomputed"]["rover"]["rank"] > 0, np.isfinite(want))
    assert validate_bundle_v2(real_dir)["ok"]
