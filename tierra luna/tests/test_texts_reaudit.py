"""Text corrections of the independent re-audit of the corrected model (15-11-2026).

docs/stats_audit/9_reauditoria_rover.json (T1, T4, T5, T6, T7, T8) and
9_reauditoria_solar.json / .md (F1, F2, F4, the note under F3, stability). Each test asserts
that the stale phrase is gone from the shipped bundle and that the figure written equals the
one in the re-audit JSON (or the configuration). No number of the model is read from here.
"""
import json
import os
import re
import sys

import numpy as np
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO = os.path.dirname(ROOT)
sys.path.insert(0, ROOT)

from engine.bundle_v2 import load_bundle  # noqa: E402

BUNDLE = os.path.join(REPO, "app", "public", "data", "v2")
AUD = os.path.join(REPO, "docs", "stats_audit")


def _j(*p):
    return json.load(open(os.path.join(*p), encoding="utf-8"))


@pytest.fixture(scope="module")
def b():
    return load_bundle(BUNDLE)


@pytest.fixture(scope="module")
def sim(b):
    return b.json("similarity.json")


@pytest.fixture(scope="module")
def mis(b):
    return {m["id"]: m for m in b.json("missions.json")["missions"]}


@pytest.fixture(scope="module")
def rover():
    return _j(AUD, "9_reauditoria_rover.json")


@pytest.fixture(scope="module")
def solar():
    return _j(AUD, "9_reauditoria_solar.json")


@pytest.fixture(scope="module")
def cfg():
    return _j(ROOT, "engine", "engine_config.json")


def _sigma(cfg):
    out = {}

    def walk(o):
        if isinstance(o, dict):
            if "variable" in o and isinstance(o.get("uncertainty_scale"), dict) and "sigma" in o["uncertainty_scale"]:
                out[o["variable"]] = float(o["uncertainty_scale"]["sigma"])
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)
    walk(cfg)
    return out


def _all_strings(o):
    if isinstance(o, dict):
        for v in o.values():
            yield from _all_strings(v)
    elif isinstance(o, list):
        for v in o:
            yield from _all_strings(v)
    elif isinstance(o, str):
        yield o


# ---------------------------------------------------------------- T1 Rover score formula
def test_t1_rover_score_is_the_dead_band_per_mission(sim, mis, cfg):
    sg = _sigma(cfg)
    sc = mis["rover"]["similarity"]["score"]
    assert "max(0," in sc and "/ tolerance)^2" not in sc
    assert repr(sg["slope_deg"]) in sc and repr(sg["roughness_m"]) in sc
    by = sim["real_value"]["score_by_mission"]
    assert by["rover"] == sc and by["solar"] == mis["solar"]["similarity"]["score"] and "/ tolerance)^2" in by["solar"]
    t = sim["texts"]["similarity_meaning_real_values"]["text"]
    assert f"slope {sg['slope_deg']:.2f} degrees, roughness {sg['roughness_m']:.1f} m" in t and "max(0" in t


def test_t1_pair_score_columns_are_described_per_mission(b, cfg):
    sg = _sigma(cfg)
    rov = next(x for x in b.manifest["files"] if x["name"] == "earth_rover.bin")
    d = {c["name"]: c.get("description", "") for c in rov["columns"]}
    sol = next(x for x in b.manifest["files"] if x["name"] == "earth_solar.bin")
    assert all("/ tolerance)^2" in c["description"] for c in sol["columns"] if c["name"].startswith("s."))
    assert repr(sg["slope_deg"]) in d["s.slope_deg"] and "max(0" in d["s.slope_deg"]
    assert repr(sg["roughness_m"]) in d["s.roughness_m"]


# ---------------------------------------------------------------- T7 slope minimum
def test_t7_slope_minimum_figures_are_the_shipped_rule(sim, rover):
    t = sim["texts"]["rover_slope_minimum"]["text"]
    sm = rover["slope_minimum"]["slope_min_study_corrected"]
    w, wo = sm["with_min"], sm["without_min"]
    assert "28 of the top 50" not in t and "from 4 to 13" not in t and "13.9 %" not in t
    assert f"{sm['added']:,} more points pass" in t
    assert sm["top50_added_slope_lt_0_5"] == sm["top50_added_points"]
    assert f"{sm['top50_added_points']} of the top 50 would be added points, all of them flats with a slope below 0.5 degrees" in t
    assert f"from {w['water_cci210_in_top50']} to {wo['water_cci210_in_top50']}" in t
    assert f"{100 * wo['largest_twin_share']:.1f} % of the pairs instead of {100 * w['largest_twin_share']:.1f} %" in t
    assert "no official source" in t and "measured effect" in t


# ---------------------------------------------------------------- T6 Rover stability
def test_t6_rover_stability_from_the_reaudit(sim, mis, rover):
    st = sim["texts"]["top5_stability_rover"]
    assert st["status"] == "audited" and "pending" not in st["text"].lower()
    c = rover["stability"]["corrected"]
    assert [int(x["id"][1:]) for x in c["per_analog"]] == mis["rover"]["top5"]["ids"]
    t = st["text"]
    for k, x in enumerate(c["per_analog"]):
        assert (f"number {k + 1} is among the five shown in {x['in_five_share_pct']:.1f} % of the simulations and stays in the "
                f"group tied at the top in {x['in_tied_top_group_share_pct']:.1f} %") in t
    assert f"{rover['stability']['simulations']} simulations" in t
    assert f"{c['five_repeat_exact_pct']:.1f} % of the simulations ({c['distinct_fives']} different fives" in t
    tw = [x["twin_kept_share_pct"] for x in c["per_analog"]]
    assert f"kept in {min(tw):g} to {max(tw):g} %" in t
    assert f"about {round(100 * c['tied_group']['base_tied_still_tied_share_median_p5_p95'][0])} % of its members" in t
    assert "which five are shown is not stable" in t


# ---------------------------------------------------------------- T4 water skip confirmed
def test_t4_water_skip_is_confirmed(cfg):
    raw = json.dumps(cfg, ensure_ascii=False)
    assert "TO BE CONFIRMED by the team lead" not in raw
    assert "confirmed by the team lead at 12:10 CET on 15 November 2026" in raw


# ---------------------------------------------------------------- T5 far places
def test_t5_no_text_names_a_cell_after_a_place_beyond_300_km(b, sim, mis):
    """The screen names the nearest populated place only within 300 km (detail panel);
    no sentence of the bundle may present a farther place as a cell's name."""
    names = b.json("place_detail.json")["nearest_places"]
    ex = b.json("explain.json")
    far = {r["place"]["nearest_place"] for v in ex["missions"].values() for r in v
           if (r.get("place") or {}).get("nearest_place_km") and r["place"]["nearest_place_km"] > 300}
    assert "Gjoa Haven" in far
    texts = list(_all_strings(sim["texts"])) + list(_all_strings([m.get("known_limitations") for m in mis.values()])) \
        + list(_all_strings([m.get("top5") for m in mis.values()]))
    for n in far:
        assert not any(re.search(r"\b" + re.escape(n) + r"\b", t) for t in texts), n
    assert len(names) > 0


# ---------------------------------------------------------------- T8 rover tie / saturation reference
def test_t8_tie_sentence_once_and_saturation_reference(sim, mis):
    t = sim["texts"]["rover_tie"]["text"]
    assert t.count("slope 0.27 degrees, roughness 17.4 m") == 1
    ex = sim["texts"]["rover_suitability_saturation"]["text"]
    first_rank = mis["rover"]["top5"]["overall_ranks"][0]
    assert f"against the first analog shown (number {first_rank}," in ex
    assert "against the tied site at the top" not in ex


# ---------------------------------------------------------------- F1 clear-sky weight
def test_f1_clear_sky_is_half_of_the_suitability(sim, mis, b):
    t = sim["texts"]["solar_suitability_clouds"]["text"]
    assert "35 % of the suitability" not in t
    w = {x["variable"]: x["weight"] for x in mis["solar"]["weighted_variables"]}
    tot = sum(w.values())
    assert f"its weight {w['clear_frac_isccp']:g} out of the {tot:.2f}" in t and "half of the suitability" in t
    assert f"({100 * w['clear_frac_isccp'] / tot:g} %" in t
    pts = next(x["points"] for x in b.json("explain.json")["missions"]["solar"][0]["breakdown"] if x["variable"] == "clear_frac_isccp")
    assert pts == pytest.approx(100 * w["clear_frac_isccp"] / tot, abs=0.01)
    for kl in mis["solar"]["known_limitations"]:
        assert "35 % of the suitability" not in kl


# ---------------------------------------------------------------- F2 the cell without a cloud value
def test_f2_missing_cloud_cell_ranked_16th(sim, solar, mis):
    t = sim["texts"]["solar_suitability_clouds"]["text"]
    f2 = next(f for f in solar["faults"] if f["id"] == "F2")["fact"]
    m = re.search(r"E(\d+) \(([-\d.]+), ([-\d.]+), (\w+)\).*?suitability ([\d.]+), rank (\d+)", f2)
    assert f"in {m.group(4)}" in t and f"number {m.group(6)} in the full ranking, suitability {m.group(5)}" in t
    assert int(m.group(1)) not in mis["solar"]["top5"]["ids"] and "it is not among the five shown" in t


# ---------------------------------------------------------------- F4 stale known limitation
def test_f4_solar_known_limitation_rewritten(mis):
    kl = mis["solar"]["known_limitations"]
    assert not any("sun geometry and the diurnal amplitude are suitability criteria" in x for x in kl)
    new = next(x for x in kl if x.startswith("Earth irradiance at the ground and sun geometry no longer weigh"))
    assert "2.5 kWh per square metre a day or more" in new
    for v, wt in ((x["variable"], x["weight"]) for x in mis["solar"]["weighted_variables"]):
        lab = {"clear_frac_isccp": "clear-sky fraction", "slope_deg": "slope", "lst_diurnal_amp_k": "daily temperature swing",
               "roughness_m": "roughness"}[v]
        assert f"{lab} ({wt:g})" in new


# ---------------------------------------------------------------- note under F3: within-row validation
def test_external_validation_solar_within_row(sim, solar):
    t = sim["texts"]["external_validation_solar"]["text"]
    v = {x["criteria_set"]: x for x in solar["validation"]}
    c, m = v["corrected"], v["audited_morning"]
    assert (f"{c['overall']['positives']['median_pct_passing']:.1f} % against "
            f"{m['overall']['positives']['median_pct_passing']:.1f} %") in t
    assert (f"median {c['within_row_rank']['positives']['median_pct_passing']:.1f} % against "
            f"{m['within_row_rank']['positives']['median_pct_passing']:.1f} %") in t
    assert "not shown to say more than latitude" in t


# ---------------------------------------------------------------- Solar stability
def test_solar_stability_from_the_reaudit(sim, mis, solar):
    st = sim["texts"]["top5_stability_solar"]
    assert st["status"] == "audited" and "pending" not in st["text"].lower()
    c = solar["stability"]["corrected"]
    ids = mis["solar"]["top5"]["ids"]
    assert list(c["per_analog"]) == [f"E{x}" for x in ids]
    t = st["text"]
    for k, e in enumerate(ids):
        p = c["per_analog"][f"E{e}"]
        assert f"number {k + 1} stays in the top 5 in {100 * p['share_in_five']:.1f} % of the simulations and in the top 20 in {100 * p['share_top20']:.1f} %" in t
        assert p["weights_pm10_in_five_same_twin"] == p["weights_pm10_of"]
    n = c["per_analog"][f"E{ids[0]}"]["weights_pm10_of"]
    assert f"in {n} of the {n} weight changes" in t
    assert c["five_same_set"] == 0.0 and f"0 of the {c['runs']} simulations" in t
    assert not any("Stability figures pending" in x for x in mis["solar"]["known_limitations"] + mis["rover"]["known_limitations"])


# ---------------------------------------------------------------- documents
def test_documents_carry_the_reaudit_section():
    d = open(os.path.join(REPO, "docs", "DECISIONS.md"), encoding="utf-8").read()
    assert "## Reauditoría independiente del modelo corregido (15-11-2026)" in d
    for x in ("6c3750c", "89a5c52", "57ab46a", "E17538", "97,31", "43,15", "70,23", "47,27", "72,29"):
        assert x in d
    c = open(os.path.join(REPO, "docs", "DATA_CONTRACT.md"), encoding="utf-8").read()
    assert "text passes of 15-11-2026" in c.lower()
    a = open(os.path.join(REPO, "docs", "ANALOG_PRINCIPLE.md"), encoding="utf-8").read()
    assert "9_reauditoria_rover" in a
    for p in (os.path.join(REPO, "docs", "DATA_CONTRACT.md"), os.path.join(REPO, "ASSUMPTIONS.md"),
              os.path.join(REPO, "docs", "DECISIONS.md"), os.path.join(REPO, "docs", "ANALOG_PRINCIPLE.md")):
        assert "35 % of the suitability" not in open(p, encoding="utf-8").read()
