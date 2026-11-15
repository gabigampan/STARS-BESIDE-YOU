"""Decisions of 2026-11-15 11:23 CET (taken by the delegate on the team lead's behalf),
contract revision 7:

1. Rover similarity on slope and roughness only (50 % each, both key, tolerances 2 deg and
   30 m); relative elevation out of the similarity and of the pair filter, shown as an
   information row. The Rover slope minimum of 0.5 deg is KEPT (justified with data in
   docs/DECISIONS.md).
2. The five shown in Rover and Solar panels keep a 2-degree separation (greedy by rank);
   Lunar base ranks 1 to 5. missions.json missions[].top5.
3. Lunar base zone kept; every Lunar base twin says 'in' or 'at the edge of' its NASA region.
4. Honest-limits texts in similarity.json texts, with 'show'.
Solar panels and Lunar base pairing unchanged: their .bin files are byte-identical to the
bundle shipped before 11:23 (hashes below, taken from that bundle).

Figures are recomputed here from the shipped bundle and the input tables; settings are read
from engine_config.json.
"""
import hashlib
import json
import math
import os
import re
import sys

import numpy as np
import pandas as pd
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO = os.path.dirname(ROOT)
sys.path.insert(0, ROOT)

from engine.bundle_v2 import load_bundle  # noqa: E402
from engine.config import load_engine_config  # noqa: E402
from engine.limits import stability_sentence  # noqa: E402
from engine.top5 import central_angle_deg, select  # noqa: E402

BUNDLE = os.path.join(REPO, "app", "public", "data", "v2")
SHOW = {"mission_card", "top5", "pair_panel", "data_and_limits"}

# sha256 of the files of the bundle shipped before 11:23 CET (scratchpad ref-before-1123)
UNCHANGED_BINS = {
    "earth_solar.bin": "a07219d6bcd5198d47b836893277a4dd7bd8143dcbfbe77f522b41fc3aa0d5fd",
    "earth_solar_pairs.bin": "f0658d8b938ae99e6ad2cab46a58f2d7f4241bc46b707cff95e4edcb58487834",
    "moon_solar.bin": "7d4b328f4ead1e8de974d6f12ff1a090be14bfc76b2441387d42598660cd2516",
    "earth_lunar_base.bin": "2c5135cb2f943dd2d6e3c6e4b9e470e913a988b37afd7e84267f59fdd22d2b13",
    "earth_lunar_base_pairs.bin": "6eeffe876b67e23973bdc69f7766b79d0ab4d2783edf0233de537bdf0d2767d8",
    "moon_lunar_base.bin": "c76615c124b1d3793e85e62a827674a5cb1e183dadbce7456322ae0804e02019",
}


@pytest.fixture(scope="module")
def b():
    return load_bundle(BUNDLE)


@pytest.fixture(scope="module")
def ecfg():
    return load_engine_config(dataset="real_1deg")


@pytest.fixture(scope="module")
def missions(b):
    return {m["id"]: m for m in b.json("missions.json")["missions"]}


@pytest.fixture(scope="module")
def earth():
    p = os.path.join(ROOT, "output_real", "earth_real_1deg.csv")
    t = pd.read_csv(p)
    t.index = t["row"] * 360 + t["col"]
    return t


# ----------------------------------------------------------------------------- decision 1
def test_rover_rule_is_slope_and_roughness_half_each(ecfg):
    rv = ecfg.v("real_value_similarity")
    vs = rv["missions"]["rover"]["variables"]
    assert [(v["variable"], v["role"], v["weight"], v["tolerance"]) for v in vs] == [
        ("slope_deg", "key", 0.5, 2.0), ("roughness_m", "key", 0.5, 30.0)]
    assert all("11:23 CET" in v["weight_set_by"] for v in vs)
    assert "11:23 CET" in rv["missions"]["rover"]["weights_why"] and "filter" in rv["missions"]["rover"]["weights_why"]
    assert rv["info_differences"]["rover"][0] == "elevation_rel_m"
    assert rv["info_in_pairs_file"]["rover"] == ["elevation_rel_m"] and rv["info_in_pairs_file"]["solar"] == []


def test_rover_pairs_file_has_relative_elevation_as_information_row(b, missions):
    cols = set(b.columns("earth_rover_pairs.bin"))
    assert {"info.elevation_rel_m.earth", "info.elevation_rel_m.moon", "info.elevation_rel_m.diff"} <= cols
    assert not any(c.startswith("elevation_rel_m.") or c == "s.elevation_rel_m" for c in cols | set(b.columns("earth_rover.bin")))
    e, m, d = (b.column("earth_rover_pairs.bin", f"info.elevation_rel_m.{s}") for s in ("earth", "moon", "diff"))
    ok = np.isfinite(d)
    assert ok.sum() > 10000
    assert np.allclose(np.abs(e[ok] - m[ok]), d[ok], atol=0.01)
    assert not (d[ok] <= 1000.0).all()            # the old bound of 1,000 m no longer filters pairs
    sim = missions["rover"]["similarity"]
    assert [v["variable"] for v in sim["variables"]] == ["slope_deg", "roughness_m"]
    assert sim["info_columns"][0]["variable"] == "elevation_rel_m"


def test_rover_similarity_and_filter_use_slope_and_roughness_only(b, missions):
    s1 = b.column("earth_rover.bin", "s.slope_deg")
    s2 = b.column("earth_rover.bin", "s.roughness_m")
    sim = b.column("earth_rover.bin", "similarity")
    ok = np.isfinite(sim)
    assert np.allclose(np.round(100 * (0.5 * s1[ok] + 0.5 * s2[ok]), 2), sim[ok], atol=0.0101)
    for v in missions["rover"]["similarity"]["variables"]:
        dd = b.column("earth_rover_pairs.bin", f"{v['variable']}.diff")
        assert np.nanmax(dd) <= v["bound"] + 1e-6


@pytest.mark.skip(reason='superseded by the decisions of 2026-11-15 11:28/11:36/11:51 CET (contract revision 8): this test pins the pre-revision-8 state; the audited_morning criteria set reproduces that state (tests/test_decisions_1128.py::test_audited_morning_reproduces_42d8bba_bundle)')
def test_solar_and_lunar_base_bins_are_byte_identical_to_the_bundle_before_1123(b):
    for name, want in UNCHANGED_BINS.items():
        with open(os.path.join(BUNDLE, name), "rb") as fh:
            assert hashlib.sha256(fh.read()).hexdigest() == want, name


def test_rover_slope_minimum_is_kept_as_the_team_wrote_it(missions):
    team = json.load(open(os.path.join(ROOT, "mission_scoring.json"), encoding="utf-8"))
    assert team["missions"]["rover"]["gates"]["slope_300m_deg"]["min"] == 0.5
    g = next(x for x in missions["rover"]["gates"] if x["variable"] == "slope_300m_deg")
    assert g["min"] == 0.5 and g["max"] == 15.0
    decisions = open(os.path.join(REPO, "docs", "DECISIONS.md"), encoding="utf-8").read()
    assert "pendiente mínima" in decisions and "se mantiene" in decisions


def test_mission_scoring_json_is_quoted_unchanged(b):
    import hashlib as h
    want = h.sha256(open(os.path.join(ROOT, "mission_scoring.json"), "rb").read()).hexdigest()
    assert b.manifest["config_sha256"]["mission_scoring.json"] == want
    assert b.manifest["contract_revision"] == 8


# ----------------------------------------------------------------------------- decision 2
def test_top5_shape_and_greedy_separation(b, missions, ecfg):
    sel = ecfg.v("top5_selection")
    radius = ecfg.v("body_radius_km")["EARTH"]
    lat_r = b.column("earth_base.bin", "lat")
    lon_c = b.column("earth_base.bin", "lon")
    for mid, m in missions.items():
        t = m["top5"]
        # revision 8 adds rule_id, skips, top_tie_n, top_tie_n_after_skips, alternative_rule (and alternative)
        assert {"rule", "min_separation_deg", "min_separation_km", "ids", "overall_ranks"} <= set(t)
        assert len(t["ids"]) == 5
        if t.get("rule_id") != "spread_within_top_tie":  # revision 8: spread order is the farthest-point order
            assert t["overall_ranks"] == sorted(t["overall_ranks"])
        ids = b.int_column("earth_base.bin", "id")
        li = b.int_column(f"earth_{mid}.bin", "land_index")
        rank = b.column(f"earth_{mid}.bin", "rank")
        rid = {int(ids[li[k]]): int(rank[k]) for k in np.flatnonzero(np.isfinite(rank))}
        assert [rid[i] for i in t["ids"]] == t["overall_ranks"]
        order = sorted(rid, key=rid.get)
        ll = {i: (float(lat_r[i // 360]), float(lon_c[i % 360])) for i in order[:200]}
        cfg = {**sel["missions"][mid], "rule": t.get("rule_id", sel["missions"][mid]["rule"])}  # the rule the bundle states (criteria set applied)
        if cfg["rule"] == "by_rank":
            assert t["overall_ranks"] == [1, 2, 3, 4, 5] and t["min_separation_deg"] is None
            continue
        sep = t["min_separation_deg"]
        assert t["min_separation_deg"] == sep and t["min_separation_km"] == round(math.radians(sep) * radius, 1) == 222.4
        if cfg["rule"] != "min_separation":
            # revision 8 rules (skips, spread within the top tie): tests/test_decisions_1128.py;
            # here only the separation between the five is checked
            for a in range(5):
                for c in range(a + 1, 5):
                    ia, ic = t["ids"][a], t["ids"][c]
                    pa = (89.5 - ia // 360, -179.5 + ia % 360)
                    pc = (89.5 - ic // 360, -179.5 + ic % 360)
                    assert central_angle_deg(*pa, np.array([pc[0]]), np.array([pc[1]]))[0] >= sep
            continue
        assert "2 degrees of arc (about 222.4 km)" in t["rule"]
        kept = []
        for i in order:          # every point above the last kept one is kept or within the separation of a kept one
            if rid[i] > t["overall_ranks"][-1]:
                break
            near = [k for k in kept if central_angle_deg(ll[i][0], ll[i][1], np.array([ll[k][0]]), np.array([ll[k][1]]))[0] < sep]
            if not near:
                kept.append(i)
        assert kept == t["ids"], mid
        for a in range(5):
            for c in range(a + 1, 5):
                d = central_angle_deg(*ll[t["ids"][a]], np.array([ll[t["ids"][c]][0]]), np.array([ll[t["ids"][c]][1]]))[0]
                assert d >= sep


def test_select_on_a_hand_built_case():
    rank = np.array([1, 2, 3, 4, 5, 6, 7, 0])
    lat = np.array([0.0, 0.0, 0.0, 10.0, 20.0, 30.0, 40.0, 50.0])
    lon = np.array([0.0, 1.0, 2.5, 0.0, 0.0, 0.0, 0.0, 0.0])
    rule = {"count": 5, "rule": "min_separation", "min_separation_deg": 2.0}
    assert select(rank, lat, lon, rule) == [0, 2, 3, 4, 5]        # 1 deg from the best: skipped; 2.5 deg: kept
    assert select(rank, lat, lon, {"count": 5, "rule": "by_rank"}) == [0, 1, 2, 3, 4]


def test_explain_holds_the_five_shown(b, missions):
    ex = b.json("explain.json")
    for mid, m in missions.items():
        have = {it["id"] for it in ex["missions"][mid]}
        assert set(m["top5"]["ids"]) <= have
        assert all("similarity" in it and "breakdown" in it for it in ex["missions"][mid])


# ----------------------------------------------------------------------------- point 4: texts
def test_new_texts_have_show_missions_and_no_empty_figures(b):
    texts = b.json("similarity.json")["texts"]
    new = {k: t for k, t in texts.items() if "show" in t}
    want = {f"{p}_{m}" for p in ("list_order", "top5_stability", "external_validation") for m in ("rover", "solar", "lunar_base")}
    want |= {"surface_classes_rover", "gate_elevation_land", "numbers_without_effect", "zone_edge_lunar_base",
             "solar_similarity_saturation"}
    assert want <= set(new)
    for k, t in new.items():
        assert set(t["show"]) <= SHOW and t["show"], k
        assert "missions" not in t or t["missions"], k
        assert not re.search(r"\{[a-z0-9_]+\}", t["text"]), k
    for m in ("rover", "solar", "lunar_base"):
        assert "ordered by the final score" in texts[f"list_order_{m}"]["text"]
    # 12:10 CET point 5: Rover's five are five of the sites tied at the top (test_texts_1210.py)
    for m in ("solar", "lunar_base"):
        assert "five of the highest-scoring analogs in our model" in texts[f"list_order_{m}"]["text"]
    assert "highest-scoring" not in texts["list_order_rover"]["text"]


@pytest.mark.skip(reason='superseded by the decisions of 2026-11-15 11:28/11:36/11:51 CET (contract revision 8): this test pins the pre-revision-8 state; the audited_morning criteria set reproduces that state (tests/test_decisions_1128.py::test_audited_morning_reproduces_42d8bba_bundle)')
def test_stability_is_pending_for_rover_and_solar_and_audited_for_lunar_base(b, missions, ecfg):
    texts = b.json("similarity.json")["texts"]
    cfg = ecfg.v("top5_stability")
    for m in ("rover", "solar"):
        assert texts[f"top5_stability_{m}"]["text"] == cfg["pending_sentence"] == "Stability figures pending the independent re-audit."
        assert texts[f"top5_stability_{m}"]["status"] == "pending"
    lb = texts["top5_stability_lunar_base"]
    assert lb["status"] == "audited" and "3_robustez_validacion_ranking.md" in lb["source"]
    assert "in 43.5 % of the simulations and in the top 20 in 61.0 %" in lb["text"] and "4 of the 5" in lb["text"]
    assert cfg["missions"]["lunar_base"]["ids"] == missions["lunar_base"]["top5"]["ids"]


@pytest.mark.skip(reason='superseded by the decisions of 2026-11-15 11:28/11:36/11:51 CET (contract revision 8): this test pins the pre-revision-8 state; the audited_morning criteria set reproduces that state (tests/test_decisions_1128.py::test_audited_morning_reproduces_42d8bba_bundle)')
def test_stability_sentence_refuses_incomplete_or_foreign_figures(ecfg):
    cfg = ecfg.v("top5_stability")
    ids = cfg["missions"]["lunar_base"]["ids"]
    assert stability_sentence("lunar_base", ids, cfg)["status"] == "audited"
    assert stability_sentence("lunar_base", ids[::-1], cfg)["text"] == cfg["pending_sentence"]
    cfg2 = json.loads(json.dumps(cfg))
    cfg2["missions"]["rover"].update({"status": "audited", "ids": [1, 2, 3, 4, 5], "in_top5_share": [1, 2, 3, 4, None]})
    assert stability_sentence("rover", [1, 2, 3, 4, 5], cfg2)["status"] == "pending"


def test_surface_classes_text_recomputed(b, missions, earth):
    t = b.json("similarity.json")["texts"]["surface_classes_rover"]["text"]
    ids = b.int_column("earth_base.bin", "id")
    li = b.int_column("earth_rover.bin", "land_index")
    rank = b.column("earth_rover.bin", "rank")
    k = np.flatnonzero(np.isfinite(rank))
    e = earth.loc[ids[li[k]]]
    ice = (e["snow_ice_frac"].to_numpy() >= 0.5) | (e["thermal_inertia_class"].astype(str).to_numpy() == "hielo")
    water = e["lc_dominant_cci_code"].to_numpy() == 210
    r = rank[k]
    assert f"{int(ice.sum()):,} of the {len(k):,} ranked points" in t
    assert f"the best of them is number {int(r[ice].min()):,}, {int((r[ice] <= 50).sum())} are in the top 50" in t
    assert f"{int(water.sum()):,} ranked points are cells whose single commonest land-cover class is water" in t
    shown = set(missions["rover"]["top5"]["ids"])
    n5 = sum(1 for i, w in zip(ids[li[k]], water) if w and int(i) in shown)
    assert f"and {n5} among the five shown" in t


def test_gate_elevation_text_recomputed(b, earth):
    t = b.json("similarity.json")["texts"]["gate_elevation_land"]["text"]
    el = earth["elevation_m"].to_numpy()
    below = np.isfinite(el) & (el < 1.0)
    n_land = int((below & (earth["mask_fraction"].to_numpy() >= 0.3)).sum())
    assert int(below.sum()) == 177 and n_land == 37          # docs/stats_audit/7_efecto_decisiones_pendientes.md P6
    assert "177 real land cells" in t and "37 of them" in t


def test_numbers_without_effect_lists_inert_gates_and_unread_values(b):
    t = b.json("similarity.json")["texts"]["numbers_without_effect"]
    assert "5_inventario_sentido_fisico.md" in t["source"]
    s = t["text"]
    # plain words since 12:10 CET point 6 (no column names in a text the user reads)
    for part in ("Rover: slope (degrees) at most 15, roughness (m) at least 5, roughness (m) at most 650",
                 "maximum sun elevation (degrees) at least 10", "share of time with the sun below 5 degrees at most 0.25",
                 "Lunar base: land share of the cell at least 0.3", "its block of tolerances", "its block of workable days"):
        assert part in s, part
    assert "slope (degrees) at least 0.5" not in s           # the slope minimum does work


def test_external_validation_percentiles_recomputed(b, missions):
    ev = missions["rover"]["external_validation"]
    ids = b.int_column("earth_base.bin", "id")
    li = b.int_column("earth_rover.bin", "land_index")
    rank = b.column("earth_rover.bin", "rank")
    rid = {int(ids[li[k]]): int(rank[k]) for k in np.flatnonzero(np.isfinite(rank))}
    n = len(rid)
    names = {r["name"]: r for r in ev["positives"]}
    for site in ("Qaidam", "Haughton", "Ramon", "Yungay"):
        r = names[site]
        assert r["verified_coordinates"] and r["rank"] == rid[r["cell"]]
        assert r["rank_percentile"] == round(100 * (r["rank"] - 0.5) / n, 1)
    assert names["Dhofar"]["rank"] is None and not names["Dhofar"]["passes_funnel"]
    text = b.json("similarity.json")["texts"]["external_validation_rover"]["text"]
    assert f"Qaidam (top {names['Qaidam']['rank_percentile']:.1f} %)" in text
    for m in ("solar", "lunar_base"):
        t = b.json("similarity.json")["texts"][f"external_validation_{m}"]
        # computed from the research r4 site lists since the Lunar base re-audit (test_texts_1210.py)
        assert t["text"].startswith("What was checked against known places") and "r4_rank_sites.py" in t["source"]


# ----------------------------------------------------------------------------- decision 3
def test_lunar_base_twins_carry_their_nasa_region_and_phrase(b):
    tw = {t["id"]: t for t in b.json("twins.json")["missions"]["lunar_base"]["twins"]}
    assert all(t["nasa_region"] and t["nasa_region"]["region"] for t in tw.values())
    for t in tw.values():
        r = t["nasa_region"]
        assert r["phrase"] == ("in" if r["share_of_cell"] >= 0.5 else "at the edge of")
        assert r["text"] == f"{r['phrase']} NASA's {r['region']} candidate region"
    # the auditor's shares of the five twins of the audio (docs/stats_audit/7 P1, own LAEA geometry)
    for cid, region, share in ((63528, "Haworth", 0.0043), (63841, "de Gerlache Rim 2", 0.078),
                               (64018, "Slater Plain", 0.329), (62517, "Nobile Rim 2", 0.446), (62523, "Nobile Rim 2", 0.0032)):
        if cid in tw:
            assert tw[cid]["nasa_region"]["region"] == region and abs(tw[cid]["nasa_region"]["share_of_cell"] - share) < 0.002
    text = b.json("similarity.json")["texts"]["zone_edge_lunar_base"]["text"]
    edge = sum(1 for t in tw.values() if t["nasa_region"]["phrase"] == "at the edge of")
    assert f"{edge} of the {len(tw)} Lunar base twins" in text and "(280 cells)" in text


# ----------------------------------------------------------------------------- rules
def test_no_separation_tolerance_or_weight_typed_in_the_new_code():
    for f in ("top5.py", "limits.py"):
        src = open(os.path.join(ROOT, "engine", f), encoding="utf-8").read()
        code = "\n".join(l for l in src.splitlines() if not l.strip().startswith(("#", '"', "*")))
        for literal in ("222.4", "6371", "1737.4", "210", "220", "0.3", "0.4", "15.0", "30.0"):   # 2.0 and 0.5 appear as halves in the haversine
            assert not re.search(r"(?<![\w.])" + re.escape(literal) + r"(?![\w])", code), (f, literal)
        for mission in ("rover", "solar", "lunar_base"):
            assert f'"{mission}"' not in code, (f, mission)
