"""Texts of the team lead's points of 2026-11-15 12:10 CET and of the Lunar base re-audit
(docs/DECISIONS.md "Puntos del líder de las 12:10"): their figures are frozen against the
shipped bundle (app/public/data/v2), and no text the web prints names a file, a column,
a rule identifier or an internal code."""
import csv
import json
import math
import os
import re
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO = os.path.dirname(ROOT)
sys.path.insert(0, ROOT)

BUNDLE = os.path.join(REPO, "app", "public", "data", "v2")
AUDIT = os.path.join(REPO, "docs", "stats_audit", "9_reauditoria_base.json")

# a file name, a snake_case identifier, or a cell id such as E5130
TECH = re.compile(r"\b\w+\.(?:py|json|csv|md|bin|geojson)\b|\b[a-z][a-z0-9]*_[a-z0-9_]+\b|\bE\d{3,5}\b")
# fields the contract marks as not shown to the user (references are kept there)
NOT_SHOWN = {"placeholders", "display_rule", "show_why", "number_1_example", "variant_note", "figures",
             "region_column", "texts_status", "how_computed", "where", "source", "sources", "decision", "why",
             "note", "formula", "set_by", "status_reason", "source_url", "tolerance_set_by", "columns_in", "kind",
             "rule_id", "criterion", "variable", "code", "id", "status", "score", "score_column", "column",
             "pairs_columns", "compared_columns", "files", "sites", "mission", "missions", "show", "criteria_set",
             "alternative_rule", "scale", "real_unit", "level"}
PLACEHOLDER = re.compile(r"\{[a-z0-9_]+\}")


def _load(name, folder=BUNDLE):
    with open(os.path.join(folder, name), encoding="utf-8") as fh:
        return json.load(fh)


@pytest.fixture(scope="module")
def sim():
    return _load("similarity.json")


@pytest.fixture(scope="module")
def missions():
    return {m["id"]: m for m in _load("missions.json")["missions"]}


def _user_strings(x, path, out):
    if isinstance(x, dict):
        for k, v in x.items():
            if k not in NOT_SHOWN:
                _user_strings(v, f"{path}/{k}", out)
    elif isinstance(x, list):
        for i, v in enumerate(x):
            _user_strings(v, f"{path}[{i}]", out)
    elif isinstance(x, str) and " " in x:
        out.append((path, x))


def _printed_texts(folder=BUNDLE):
    out = []
    _user_strings(_load("similarity.json", folder).get("texts"), "similarity.texts", out)
    for m in _load("missions.json", folder)["missions"]:
        _user_strings(m.get("known_limitations"), f"{m['id']}.known_limitations", out)
        t = m.get("top5") or {}
        _user_strings({k: t[k] for k in ("rule", "sentence", "text") if k in t}, f"{m['id']}.top5", out)
        _user_strings({"r": (m.get("similarity") or {}).get("no_twin_reason")}, f"{m['id']}.no_twin_reason", out)
    _user_strings(_load("mission_zones.json", folder), "mission_zones", out)
    return out


def test_no_technical_reference_in_a_printed_text():
    bad = [(p, TECH.findall(PLACEHOLDER.sub("", s))) for p, s in _printed_texts()]
    bad = [(p, h) for p, h in bad if h]
    assert not bad, bad


def test_known_offenders_are_gone(sim):
    t = sim["texts"]
    assert "twins.json" not in t["zone_edge_lunar_base"]["text"]
    assert "Beside each twin we print" in t["zone_edge_lunar_base"]["text"]
    for w in ("rover_preset.py", "slope_300m_deg", "rough_300m_m"):
        assert w not in t["external_validation_rover"]["text"]
    for w in ("mask_fraction", "sun_elev_max_deg", "mission_scoring.json"):
        assert w not in t["numbers_without_effect"]["text"]
    assert t["numbers_without_effect"]["text"].count("the team's scoring file") == 1


def test_no_twin_reason_of_the_fixture_is_plain():
    import engine.export_v2 as ex

    src = open(ex.__file__, encoding="utf-8").read()
    reasons = re.findall(r'\["no_twin_reason"\] = "([^"]+)"', src)
    assert len(reasons) == 2
    for r in reasons:
        assert not TECH.findall(r), r
    fixture = os.environ.get("STARS_GLOBAL_MEAN_BUNDLE")
    if fixture and os.path.isdir(fixture):
        for p, s in _printed_texts(fixture):
            if p.endswith("no_twin_reason/r"):
                assert not TECH.findall(s), (p, s)


def test_rover_five_wording_reads_n_from_the_data(missions, sim):
    t5 = missions["rover"]["top5"]
    n = t5["top_tie_n"]
    s = f"These are five of the {n:,} sites tied at the top of our model, chosen to be spread across the world"
    assert t5["rule"].startswith(s)
    assert s in sim["texts"]["list_order_rover"]["text"]
    assert "highest-scoring" not in t5["rule"] and "highest-scoring" not in sim["texts"]["list_order_rover"]["text"]
    assert "0.27 degrees" in t5["rule"] and "17.4 m" in t5["rule"]


@pytest.mark.parametrize("mid", ["solar", "lunar_base"])
def test_other_fives_say_highest_scoring_with_their_ranks(missions, sim, mid):
    txt = sim["texts"][f"list_order_{mid}"]["text"]
    assert "five of the highest-scoring analogs in our model" in txt
    t5 = missions[mid]["top5"]
    ranks = t5.get("ranks")
    if ranks:
        assert ", ".join(str(r) for r in ranks[:-1]) in txt


def test_rover_saturation_figures(sim, missions):
    t = sim["texts"]["rover_suitability_saturation"]
    assert set(t["show"]) == {"mission_card", "data_and_limits"}
    n = missions["rover"]["top5"]["top_tie_n"]
    assert f"of the {n:,} sites tied at the top" in t["text"]
    assert "Bardenas Reales" in t["text"] and "Tabernas Desert" in t["text"]
    assert "weakness of the suitability criteria" in t["text"]


def test_rule_parts_and_slope_minimum(sim):
    p = sim["texts"]["top5_rule_parts"]["text"]
    assert "Ice (" in p and "Land (" in p and "Distance (" in p and "separately switchable" in p
    s = sim["texts"]["rover_slope_minimum"]
    assert "no official source" in s["text"] and "7,847" in s["text"]
    assert set(s["show"]) == {"mission_card", "data_and_limits"}


def _cell(lat, lon):
    return min(int(math.floor(90.0 - lat)), 179) * 360 + min(int(math.floor(lon + 180.0)), 359)


def test_lunar_base_external_validation_matches_the_audit(sim):
    t = sim["texts"]["external_validation_lunar_base"]["text"]
    assert "have no twin among" not in t
    assert "Mars Desert Research Station (MDRS) (number 335)" in t
    assert "Craters of the Moon National Monument (number 179)" in t
    a = json.load(open(AUDIT, encoding="utf-8"))
    assert any("335" in f.get("what", "") and "179" in f.get("what", "") for f in a["faults"])


def test_solar_external_validation_is_computed(sim):
    t = sim["texts"]["external_validation_solar"]["text"]
    assert "No external validation exists" not in t
    path = os.path.join(ROOT, "data", "benchmark", "validation_sites_solar.csv")
    rows = list(csv.DictReader([ln for ln in open(path, encoding="utf-8") if not ln.startswith("#")]))
    pos = sum(r["role"] == "positive" for r in rows)
    neg = sum(r["role"] == "negative" for r in rows)
    assert t.startswith(f"What was checked against known places: {pos} solar radiation stations")
    assert f"and {neg} cloudy stations" in t
    assert "BSRN " not in t.replace("(BSRN)", "")


def test_lunar_base_stability_from_the_auditor(sim, missions):
    a = json.load(open(AUDIT, encoding="utf-8"))["stability"]
    per = a["corrected"]["per_analog"]
    t = sim["texts"]["top5_stability_lunar_base"]
    ids = missions["lunar_base"]["top5"]["ids"]
    assert [int(k) for k in per] == list(ids)
    for k, i in enumerate(ids, 1):
        e = per[str(i)]
        assert (f"number {k} stays in the top 5 in {100 * e['share_in_five']:.1f} % of the simulations "
                f"and in the top 20 in {100 * e['share_top20']:.1f} %") in t["text"]
    assert f"in {round(a['corrected']['five_identical_set'] * a['runs'])} of the {a['runs']} simulations" in t["text"]
    for mid in ("rover", "solar"):
        assert sim["texts"][f"top5_stability_{mid}"]["text"] == "Stability figures pending the independent re-audit."


def test_lunar_base_weights_renormalised_and_rock_level(sim, missions):
    w = [x["weight"] for x in missions["lunar_base"]["weighted_variables"]]
    assert abs(sum(w) - 0.95) < 1e-9
    assert "sum to 95 %" in sim["texts"]["lunar_base_criteria"]["text"]
    dev = sim["texts"]["deviations_from_team"]["text"]
    assert "the fraction is MEASURED" in dev and "is DERIVED, continuous" not in dev
    rock = [x for x in missions["lunar_base"]["weighted_variables"] if x["variable"] == "rock_or_bare_frac"][0]
    assert rock["levels"]["EARTH"] == "MEASURED"
    tmin = [x for x in missions["lunar_base"]["weighted_variables"] if x["variable"] == "tmin_c"][0]
    assert tmin["also_in_similarity"] is True


def test_rover_scale_source_names_both_documents():
    cfg = json.load(open(os.path.join(ROOT, "engine", "engine_config.json"), encoding="utf-8"))
    s = json.dumps(cfg["real_value_similarity"])
    assert "https://doi.org/10.5194/essd-17-1835-2025" in s and "https://doi.org/10.1029/2010GL043751" in s
    assert "ETOPO 2022 measures a global RMSE of 7.17 m" in s
