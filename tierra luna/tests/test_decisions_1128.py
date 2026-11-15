"""Decisions of 2026-11-15 11:28, 11:36 and 11:51 CET (docs/DECISIONS.md, 'Decisiones de
las 11:28 y 11:36'): criteria sets per mission, Solar panels suitability with ISCCP clouds
(research 2, E2), Lunar base suitability (research 3, R), Rover similarity desaturated by
the elevation models' uncertainty (research 5), the rules for the five, the per-pair
confidence removed and the stability text in its two states.
"""
from __future__ import annotations

import copy
import json
import os
import sys

import numpy as np
import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

from engine.bundle_v2 import load_bundle  # noqa: E402
from engine.config import load_engine_config, load_mission_config  # noqa: E402
from engine.criteria import apply_criteria_sets  # noqa: E402
from engine.limits import stability_sentence  # noqa: E402
from engine import top5 as t5  # noqa: E402

BUNDLE = os.path.join(os.path.dirname(ROOT), "app", "public", "data", "v2")
SCR = "/tmp/claude-0/-home-user/7228bb30-9725-52d9-8d71-762c955fd0bd/scratchpad"
REF_MORNING = os.environ.get("REF_MORNING_BUNDLE", os.path.join(SCR, "ref-rev6"))
MISSIONS = ("rover", "solar", "lunar_base")


@pytest.fixture(scope="module")
def b():
    return load_bundle(BUNDLE)


@pytest.fixture(scope="module")
def mj(b):
    return {m["id"]: m for m in b.json("missions.json")["missions"]}


@pytest.fixture(scope="module")
def ecfg():
    return load_engine_config(dataset="real_1deg")


# ----------------------------------------------------------------------------- criteria sets
def test_team_file_is_unchanged_and_deviations_quote_it(ecfg):
    team = json.load(open(os.path.join(ROOT, "mission_scoring.json"), encoding="utf-8"))["missions"]
    cs = ecfg.v("criteria_sets")
    assert cs["selected"] == {"rover": "corrected", "solar": "corrected", "lunar_base": "corrected"}
    for m in MISSIONS:
        assert set(cs["missions"][m]["sets"]) == {"audited_morning", "corrected"}
        assert cs["missions"][m]["sets"]["audited_morning"]["mission_scoring_deviations"] == []
        for d in cs["missions"][m]["sets"]["corrected"]["mission_scoring_deviations"]:
            assert team[m]["soft"].get(d["criterion"]) == d["team"]
            assert d["reason"] and d["source"]


def test_corrected_soft_criteria(ecfg):
    mcfg = load_mission_config(engine_cfg=ecfg)
    _, m2, info = apply_criteria_sets(ecfg, mcfg)
    so = m2["missions"]["solar"]["soft"]
    assert set(so) == {"slope_deg", "lst_diurnal_amp_k", "roughness_m", "clear_frac_isccp"}
    assert so["clear_frac_isccp"]["weight"] == 0.35 and (so["clear_frac_isccp"]["bad"], so["clear_frac_isccp"]["good"]) == (0.308, 0.671)
    assert (so["slope_deg"]["weight"], so["lst_diurnal_amp_k"]["weight"], so["roughness_m"]["weight"]) == (0.15, 0.1, 0.1)
    assert "clear_frac_isccp" not in m2["missions"]["solar"]["require_present"]
    lb = m2["missions"]["lunar_base"]
    assert "thermal_inertia_class" not in lb["soft"] and "permafrost_class" not in lb["soft"]
    assert lb["soft"]["rock_or_bare_frac"] == {**mcfg["missions"]["lunar_base"]["soft"]["rock_or_bare_frac"], "weight": 0.25}
    assert "thermal_inertia_class" in lb["require_present"] and lb["gates"]["thermal_inertia_class"]["exclude"] == ["agua"]
    assert lb["gates"]["lst_diurnal_amp_k"]["min"] == 15.0
    # the core component stays an exact copy
    assert m2["missions"]["thermal"]["soft"] == lb["soft"]
    # the team's dict is untouched
    assert "thermal_inertia_class" in mcfg["missions"]["lunar_base"]["soft"]


def test_bundle_states_the_criteria_set(b):
    ex = b.json("explain.json") if any(f["name"] == "explain.json" for f in b.manifest["files"]) else None
    mj = b.json("missions.json")
    for m in mj["missions"]:
        assert m["criteria_set"]["set"] == "corrected", m["id"]


@pytest.mark.skipif(not os.path.isdir(REF_MORNING), reason="copy of the 42d8bba bundle not available")
def test_audited_morning_reproduces_42d8bba_bundle():
    """Each mission built with audited_morning equals the bundle of commit 42d8bba:
    pairs, twins, scores, ranks and the five."""
    from engine.build import build_bundle
    from engine.export_v2 import build_v2_files  # noqa: F401  (same exporter)

    out = os.path.join(SCR, "c8", "morning_test")
    bb = build_bundle(criteria_sets={m: "audited_morning" for m in MISSIONS})
    from engine.export import write_bundle
    write_bundle(bb["files"], out)
    new, ref = load_bundle(out), load_bundle(REF_MORNING)
    for m in MISSIONS:
        f = f"earth_{m}.bin"
        for col in ("suitability", "similarity", "final", "rank", "twin"):
            a = new.raw_column(f, col)
            r = ref.raw_column(f, col)
            assert np.array_equal(a, r), (m, col)
        refm = {x["id"]: x for x in ref.json("missions.json")["missions"]}[m]
        newm = {x["id"]: x for x in new.json("missions.json")["missions"]}[m]
        five_ref = refm["top5"]["ids"] if refm.get("top5") else None
        rank = new.int_column(f, "rank")
        ids = new.int_column("earth_base.bin", "id") if "id" in new.columns("earth_base.bin") else None
        assert newm["top5"]["overall_ranks"] == [1, 2, 3, 4, 5]
        if five_ref is not None:
            assert newm["top5"]["ids"] == five_ref
        pf = f"earth_{m}_pairs.bin"
        if any(x["name"] == pf for x in ref.manifest["files"]):
            for col in ref.columns(pf):
                if col in new.columns(pf):
                    assert np.array_equal(new.raw_column(pf, col), ref.raw_column(pf, col), equal_nan=True), (m, col)


# ----------------------------------------------------------------------------- Solar panels
def test_solar_figures_of_research_2(mj, b):
    c = mj["solar"]["counts"] if "counts" in mj["solar"] else None
    t = b.json("missions.json")
    txt = [x for k, x in t.get("limit_texts", {}).items() if k == "solar_suitability_clouds"] if "limit_texts" in t else []
    v = b.json("variables.json")
    names = json.dumps(v)
    assert "clear_frac_isccp" in names and "ISCCP" in names


# ----------------------------------------------------------------------------- the five
def _arr(*xs):
    return [np.asarray(x, dtype=np.float64) for x in xs]


def test_rank_with_skips_skips_ice_water_and_neighbours():
    rank = np.array([1, 2, 3, 4, 5, 6, 7, 8])
    lat, lon = _arr([0, 0.5, 10, 20, 30, 40, 50, 60], [0, 0, 0, 0, 0, 0, 0, 0])
    ice = np.array([0, 0, 0.6, 0, 0, 0, 0, 0.0])
    land = np.array([1, 1, 1, 0.3, 1, 1, 1, 1.0])
    rule = {"count": 5, "rule": "rank_with_skips", "min_separation_deg": 2.0,
            "skips": {"ice": {"enabled": True, "column": "ice", "op": ">=", "value": 0.5},
                      "water": {"enabled": True, "column": "land", "op": "<", "value": 0.5}}}
    rows = t5.select(rank, lat, lon, rule, {"ice": ice, "land": land})
    assert rows == [0, 4, 5, 6, 7]
    rule["skips"]["water"]["enabled"] = False
    assert t5.select(rank, lat, lon, rule, {"ice": ice, "land": land}) == [0, 3, 4, 5, 6]


def test_spread_within_top_tie_is_farthest_point():
    n = 8
    rank = np.arange(1, n + 1)
    final = np.array([100.0] * 7 + [99.0])
    sim = np.array([99.0, 99.9, 99.0, 99.0, 99.0, 99.0, 99.0, 99.0])
    ids = np.arange(10, 10 + n)
    lat, lon = _arr([0, 0, 0, 0, 0, 0, 60, 0], [0, 1, 90, 180, -90, 45, 0, 10])
    rule = {"count": 5, "rule": "spread_within_top_tie", "min_separation_deg": 2.0, "skips": {}}
    rows = t5.select(rank, lat, lon, rule, {}, final, sim, ids)
    assert rows[0] == 1                       # highest similarity among the tied
    assert rows[1] == 3                       # antipode of lon 1 is lon 180 (farthest)
    assert len(rows) == 5 and 7 not in rows   # the untied point is never chosen
    # with five or fewer tied: rank order with the skips
    final2 = np.array([100.0, 100.0, 99, 98, 97, 96, 95, 94])
    assert t5.select(rank, lat, lon, rule, {}, final2, sim, ids)[:2] == [0, 2]


def test_shipped_rover_five_and_both_lists(mj, b):
    t = mj["rover"]["top5"]
    assert t["rule_id"] == "spread_within_top_tie" and t["alternative"]["rule_id"] == "rank_with_skips"
    assert t["skips"]["ice"]["column"] == "snow_ice_frac" and t["skips"]["water"]["column"] == "mask_fraction"
    assert t["top_tie_n"] == 254
    ids = b.int_column("earth_base.bin", "id") if "id" in b.columns("earth_base.bin") else None
    rank = b.int_column("earth_rover.bin", "rank")
    final = b.column("earth_rover.bin", "final")
    assert int(np.sum((rank > 0) & (final == np.nanmax(final)))) == t["top_tie_n"]
    assert str(t["top_tie_n_after_skips"]) in t["rule"].replace(",", "")


def test_solar_and_lunar_base_use_rank_with_skips(mj):
    for m in ("solar", "lunar_base"):
        assert mj[m]["top5"]["rule_id"] == "rank_with_skips"
        assert mj[m]["top5"]["min_separation_deg"] == 2.0


# ----------------------------------------------------------------------------- Rover scale
def test_rover_uncertainty_scale(ecfg):
    vs = {v["variable"]: v for v in ecfg.v("real_value_similarity")["missions"]["rover"]["variables"]}
    assert set(vs) == {"slope_deg", "roughness_m"}
    assert (vs["slope_deg"]["tolerance"], vs["roughness_m"]["tolerance"]) == (2.0, 30.0)
    import math
    s = math.degrees(math.sqrt((7.17 / (math.sqrt(2) * 1853)) ** 2 + (10 / (math.sqrt(2) * 1895.2)) ** 2))
    assert round(s, 6) == vs["slope_deg"]["uncertainty_scale"]["sigma"]
    assert round(math.sqrt(2 * 7.17 ** 2 + 2 * 10 ** 2), 6) == vs["roughness_m"]["uncertainty_scale"]["sigma"]


def test_rover_scores_follow_the_dead_band(b, ecfg):
    vs = {v["variable"]: v for v in ecfg.v("real_value_similarity")["missions"]["rover"]["variables"]}
    for v, spec in vs.items():
        d = b.column("earth_rover_pairs.bin", f"{v}.diff")
        s = b.column("earth_rover.bin", f"s.{v}")
        ok = np.isfinite(d) & np.isfinite(s)
        sig = spec["uncertainty_scale"]["sigma"]
        want = np.round(np.exp(-0.5 * np.maximum(0, d[ok] / sig - 1) ** 2), 6)
        assert np.allclose(want, s[ok], atol=2e-6)


# ----------------------------------------------------------------------------- confidence and stability
def test_per_pair_confidence_is_gone(b, mj):
    for m in MISSIONS:
        c = b.column(f"earth_{m}.bin", "confidence_score")
        assert not np.isfinite(c).any()
        assert "confidence_counts" not in mj[m]
    ex = b.json("explain.json")
    assert "confidence" not in json.dumps(ex["missions"]["rover"])[:200000].replace("confidence_codes", "")


def test_stability_text_two_states(ecfg):
    stab = copy.deepcopy(ecfg.v("top5_stability"))
    assert stab["show"] == ["mission_card", "data_and_limits"]
    five = [1, 2, 3, 4, 5]
    s = stability_sentence("rover", five, stab)
    assert s["status"] == "pending" and s["text"] == stab["pending_sentence"]
    assert "{" not in s["text"]
    stab["missions"]["rover"].update({"status": "audited", "ids": five, "in_top5_share": [90, 80, 70, 60, 50],
                                      "in_top20_share": [99, 98, 97, 96, 95], "simulations": 200,
                                      "weights_pm10_survivors": 5, "source": "x"})
    s = stability_sentence("rover", five, stab)
    assert s["status"] == "audited" and "200 simulations" in s["text"] and "{" not in s["text"]
    stab["missions"]["rover"]["in_top20_share"] = None
    assert stability_sentence("rover", five, stab)["status"] == "pending"


# ----------------------------------------------------------------------------- supplementary data
def test_supplement_column_is_joined_by_cell_id():
    import pandas as pd
    from engine.dataset import load_dataset
    e = load_engine_config(dataset="real_1deg")
    ds = load_dataset(e)
    sup = pd.read_csv(os.path.join(ROOT, "real_data", "supplement", "earth_cloud_isccp_1deg.csv"))
    ear = ds.cells["EARTH"].set_index("id")
    k = sup["cell_id"].str[1:].astype(int)
    a = ear.loc[k, "clear_frac_isccp"].to_numpy()
    assert np.allclose(a, sup["clear_frac_isccp"].to_numpy(), equal_nan=True)
    assert ds.cells["MOON"]["clear_frac_isccp"].isna().all()
    reg = ds.reg["variables"]["clear_frac_isccp"]
    assert reg["bodies"]["EARTH"]["level"] == "DERIVED" and reg["bodies"]["MOON"]["level"] == "NO_DATA"
    assert "ISCCP" in reg["bodies"]["EARTH"]["product"]
