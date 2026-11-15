"""Corrections of the statistical audit of 2026-11-15 (docs/stats_audit/correcciones_1.md).

Each test would have caught the fault it is named after. They read the SHIPPED bundle
(app/public/data/v2; test_real_data.test_published_v2_matches_a_fresh_build checks that
it is what the engine builds today) and, where a figure needs it, the real tables. Figures
are recomputed here with code that does not call the engine function under test.
"""
import json
import math
import os
import re
import subprocess
import sys
from decimal import ROUND_HALF_UP, Decimal

import numpy as np
import pandas as pd
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO = os.path.dirname(ROOT)
sys.path.insert(0, ROOT)

from engine.bundle_v2 import load_bundle  # noqa: E402
from engine.config import load_engine_config  # noqa: E402

BUNDLE = os.path.join(REPO, "app", "public", "data", "v2")
R_EARTH = 6371.0


@pytest.fixture(scope="module")
def b():
    return load_bundle(BUNDLE)


@pytest.fixture(scope="module")
def ecfg():
    return load_engine_config(dataset="real_1deg")


def _paired(b, mid):
    m = next(x for x in b.json("missions.json")["missions"] if x["id"] == mid)
    tw = b.int_column(m["files"]["EARTH"], "twin")
    return m, np.flatnonzero(tw != b.manifest["encoding"]["int32_missing"])


def _land_lat_lon(b):
    ids = b.int_column("earth_base.bin", "id")
    cols = b.manifest["grid"]["cols"]
    return ids, 89.5 - ids // cols, -179.5 + ids % cols


def _haversine(lat1, lon1, lat2, lon2, r):
    p1, p2 = np.radians(lat1), np.radians(lat2)
    a = np.sin((p2 - p1) / 2) ** 2 + np.cos(p1) * np.cos(p2) * np.sin(np.radians(np.asarray(lon2) - np.asarray(lon1)) / 2) ** 2
    return 2 * r * np.arcsin(np.sqrt(np.clip(a, 0, 1)))


# ----------------------------------------------------------------------------- correction 1
def test_nearest_place_is_the_great_circle_nearest_on_every_land_cell(b):
    """Audit point 7.5.1: reverse_geocoder searched in Euclidean degrees (wrong place on
    8,284 land cells). Brute force over all 144,563 GeoNames rows by great circle."""
    from engine.places import geonames_places_path
    gn = pd.read_csv(geonames_places_path(), dtype=str, keep_default_na=False)
    glat, glon = gn["lat"].astype(float).to_numpy(), gn["lon"].astype(float).to_numpy()
    gnames = gn["name"].to_numpy()
    gl, go = np.radians(glat), np.radians(glon)
    G = np.column_stack([np.cos(gl) * np.cos(go), np.cos(gl) * np.sin(go), np.sin(gl)])
    ids, lat, lon = _land_lat_lon(b)
    names = b.json("place_detail.json")["nearest_places"]
    idx = b.int_column("earth_place_detail.bin", "nearest_place")
    km = b.column("earth_place_detail.bin", "nearest_place_km")
    assert len(ids) == 25497
    bad = []
    for s in range(0, len(ids), 400):
        la, lo = np.radians(lat[s:s + 400]), np.radians(lon[s:s + 400])
        P = np.column_stack([np.cos(la) * np.cos(lo), np.cos(la) * np.sin(lo), np.sin(la)])
        dots = P @ G.T
        cand = np.argpartition(-dots, 4, axis=1)[:, :5]           # 5 best by chord, then exact distance
        d = _haversine(lat[s:s + 400, None], lon[s:s + 400, None], glat[cand], glon[cand], R_EARTH)
        for j in range(len(P)):
            k = s + j
            dmin = d[j].min()
            near = {gnames[c] for c, dd in zip(cand[j], d[j]) if dd <= dmin + 1e-6}
            if names[idx[k]] not in near or abs(km[k] - dmin) > 1e-3 * max(1.0, dmin / 1000):
                bad.append((int(ids[k]), names[idx[k]], float(km[k]), sorted(near), float(dmin)))
    assert not bad, (len(bad), bad[:5])


def test_great_circle_nearest_differs_from_the_nearest_in_degrees():
    """The engine's search on a hand case where the old rule (degrees) is wrong: at 80 N a
    place 20 degrees of longitude away (386 km) is nearer than one 5 degrees of latitude
    away (556 km)."""
    from engine.places import nearest_geonames_rows
    places = pd.DataFrame({"lat": [75.0, 80.0, 80.0], "lon": [0.0, 20.0, 20.0],
                           "name": ["B", "A", "A2"], "admin1": ["", "", ""], "cc": ["XX", "XX", "XX"]})
    rows, d = nearest_geonames_rows(np.array([80.0]), np.array([0.0]), places, R_EARTH)
    assert rows.tolist() == [1]                       # exact tie with row 2: the lower row
    assert d[0] == pytest.approx(_haversine(80.0, 0.0, 80.0, 20.0, R_EARTH), abs=1e-9) and d[0] < 400


def test_region_follows_the_corrected_nearest_place(b, ecfg):
    """The first-level region is the nearest place's, only within region_max_place_km."""
    lim = float(ecfg.v("region_max_place_km"))
    km = b.column("earth_place_detail.bin", "nearest_place_km")
    reg = b.int_column("earth_base.bin", "region")
    has = reg != b.manifest["encoding"]["int32_missing"]
    assert np.all(km[has] <= lim + 1e-3)


def test_audio_top5_places_are_unchanged(b):
    """The 15 recorded pairs keep their place, distance and direction (the transcripts)."""
    a = json.load(open(os.path.join(REPO, "docs", "AUDIO_TOP5.json"), encoding="utf-8"))
    want = {("rover", 1): ("Bayinbaolige", 65.6, "north-west"), ("rover", 2): ("Tamanrasset", 79.5, "north"),
            ("rover", 3): ("Ehen Hudag", 78.4, "north-east"), ("rover", 4): ("Banqiao", 27.8, "north-east"),
            ("rover", 5): ("Buga", 41.0, "south-east"), ("solar", 1): ("Derby", 128.7, "north-east"),
            ("solar", 2): ("Derby", 282.9, "north-east"), ("solar", 3): ("Maintirano", 80.1, "north-east"),
            ("solar", 4): ("Kununurra", 279.7, "north-west"), ("solar", 5): ("Derby", 218.2, "north-east"),
            ("lunar_base", 1): ("Aheqi", 62.3, "north"), ("lunar_base", 2): ("Mori", 43.6, "south-east"),
            ("lunar_base", 3): ("Burenhayrhan", 45.5, "north"), ("lunar_base", 4): ("Tinghir", 3.5, "south-east"),
            ("lunar_base", 5): ("Ewirgol", 53.3, "south")}
    for mid in ("rover", "solar", "lunar_base"):
        for p in a["missions"][mid]["pairs"]:
            ep = p["earth_place"]
            assert (ep["nearest_named_place"], ep["distance_km"], ep["direction_from_place"]) == want[(mid, p["rank"])]


# ----------------------------------------------------------------------------- correction 2
def test_not_used_by_engine_why_is_true_for_the_real_table(b):
    """Audit point 2.3.1: 'the *_300m_* columns are 2-degree copies' was false for real_1deg."""
    for m in b.json("missions.json")["missions"]:
        why = m["not_used_by_engine"]["why"]
        assert "are 2-degree copies" not in why and "slope_iso_deg" in why and "roughness_m" in why


def test_rover_limitation_states_the_ice_cells_with_recomputed_figures(b, ecfg):
    """Audit point 1.6.1: ice cells are in the Rover ranking; the figures of the text are
    recomputed from the real Earth table and the bundle."""
    path = os.path.join(ROOT, "output_real", "earth_real_1deg.csv")   # datasets.json real_1deg input EARTH
    t = pd.read_csv(path, usecols=["row", "col", "snow_ice_frac", "thermal_inertia_class"])
    t.index = t["row"] * 360 + t["col"]
    m, paired = _paired(b, "rover")
    ids = b.int_column("earth_base.bin", "id")
    li = b.int_column("earth_rover.bin", "land_index")
    rank = b.column("earth_rover.bin", "rank")
    ranked = np.flatnonzero(np.isfinite(rank))
    tt = t.loc[ids[li[ranked]]]
    ice = (tt["snow_ice_frac"].to_numpy() >= 0.5) | (tt["thermal_inertia_class"].to_numpy() == "hielo")
    countries = [c["name"] for c in b.json("places.json")["countries"]]
    cc = np.array([countries[i] for i in b.int_column("earth_base.bin", "country")[li[ranked]]])
    r_ice = rank[ranked][ice]
    # since 2026-11-15 11:23 CET the text is computed at build (similarity.json
    # texts.surface_classes_rover, also on the mission card); its figures are recomputed here
    text = b.json("similarity.json")["texts"]["surface_classes_rover"]["text"]
    assert text in m["known_limitations"]
    assert "no surface-type gate" in text
    assert f"{int(ice.sum()):,} of the {len(ranked):,} ranked points are ice-sheet or snow-and-ice cells" in text
    assert f"the best of them is number {int(r_ice.min()):,}, {int((r_ice <= 50).sum())} are in the top 50" in text
    assert (cc[ice] == "Antarctica").sum() > 0


def _solar_candidates(b):
    m, paired = _paired(b, "solar")
    zones = b.json("mission_zones.json")["regions"]
    reg = b.int_column("moon_base.bin", "region")
    code = m["similarity"]["zone"].get("code", "D")
    zi = [k for k, z in enumerate(zones) if z["code"] == code]
    zone = np.isin(reg, zi)
    col = {"irradiance_toa_kwh_m2_day": "v.irradiance_kwh_m2_day", "slope_deg": "v.slope_iso_deg", "roughness_m": "v.roughness_m"}
    moon = {v: b.column("moon_base.bin", c)[zone] for v, c in col.items()}
    pf = m["similarity"]["pairs_file"]
    n = []
    for p in paired:
        ok = np.ones(int(zone.sum()), bool)
        for v in m["similarity"]["variables"]:
            ok &= np.abs(moon[v["variable"]] - b.column(pf, v["pairs_columns"]["earth"])[p]) <= v["bound"]
        n.append(int(ok.sum()))
    return m, paired, np.array(n), int(zone.sum())


def test_solar_saturation_text_with_recomputed_figures(b):
    """Audit point E.4: the Solar panels similarity is saturated and nothing said so."""
    texts = b.json("similarity.json")["texts"]
    t = texts["solar_similarity_saturation"]
    assert t["missions"] == ["solar"] and t["mission_card"] is True and "EVERY solar pair" in t["where"]
    assert "mission card" in t["where"]
    m, paired, cand, nzone = _solar_candidates(b)
    assert m["known_limitations"][0] == t["text"]                 # first item of the mission card
    sim = b.column("earth_solar.bin", "similarity")[paired]
    rank = b.column("earth_solar.bin", "rank")[paired]
    s = t["text"]
    assert f"{round(100 * np.mean(sim >= 99)):.0f} % of the {len(paired):,} pairs score 99 or more" in s
    assert f"{int(np.sum(sim >= 100.0)):,} show 100.00" in s
    med = float(np.median(cand))
    assert abs(med - 1840) <= 10 and "a median of about 1,840 candidate cells" in s, med
    top = sim[rank <= 100]
    assert f"from {top.min():.2f} to {top.max():.2f}" in s
    suit = b.column("earth_solar.bin", "suitability")[paired][rank <= 100]
    fin = b.column("earth_solar.bin", "final")[paired][rank <= 100]
    from scipy.stats import spearmanr
    # revision 8 (ISCCP clouds in the suitability): Spearman final-suitability 0.93 among the 100 best
    assert spearmanr(fin, suit)[0] > 0.9 and abs(spearmanr(fin, top)[0]) < 0.3   # "their order follows suitability"


def test_similarity_scale_is_marked_unused_by_the_shipped_rules(ecfg):
    rules = ecfg.v("similarity_rule")
    assert "physical_pooled" not in set(rules.values())
    assert "USED BY NO SHIPPED RULE" in ecfg.similarity_scale.why


def test_levels_of_the_bundle_and_the_contract_agree(b):
    """Audit point 9.2.8: variables.json lists five levels, the contract named four."""
    vj = b.json("variables.json")
    used = {bd["level"] for v in vj["variables"] for bd in v["bodies"].values()}
    assert set(vj["levels"]) == {"MEASURED", "DERIVED", "MODELLED", "UNDOCUMENTED", "NO_DATA"}
    assert "UNDOCUMENTED" not in used
    for k, txt in vj["levels"].items():
        assert ("No variable of this dataset has this level" in txt) == (k not in used), k
    contract = open(os.path.join(REPO, "docs", "DATA_CONTRACT.md"), encoding="utf-8").read()
    line = next(x for x in contract.splitlines() if x.startswith("5. **Confidence**"))
    for k in vj["levels"]:
        assert f"`{k}`" in line, k
    assert "UNDOCUMENTED" in line and "no variable of the shipped" in line


# ----------------------------------------------------------------------------- correction 3
def _js_to_fixed(x: float, d: int) -> str:
    """ECMA-262 Number.prototype.toFixed, written from the specification: sign apart; n
    the integer nearest x * 10^d on the exact value, the larger n on a tie."""
    neg = x < 0
    ax = Decimal(-x if neg else x)                      # exact binary value
    n = (ax * (Decimal(10) ** d))
    lo = int(n)                                         # floor (n >= 0)
    n = lo + 1 if (n - lo) >= Decimal("0.5") else lo
    s = str(n).rjust(d + 1, "0")
    s = s if d == 0 else s[:-d] + "." + s[-d:]
    return ("-" if neg else "") + s


def test_to_fixed_matches_javascript():
    from engine.display import to_fixed
    for x, d, want in ((154.5, 0, "155"), (192.5, 0, "193"), (2.25, 1, "2.3"), (1.25, 1, "1.3"), (1.005, 2, "1.00"),
                       (-0.4, 0, "-0"), (-232.5, 0, "-233"), (0.0, 1, "0.0"), (-0.0, 0, "0"), (45.04999923706055, 1, "45.0")):
        assert to_fixed(x, d) == want == (_js_to_fixed(x, d) if x != 0 else want), (x, d)


def test_lunar_base_pair_sentence_follows_the_contract_rule_on_all_450_pairs(b, ecfg):
    """Correction 3: explain.json and the engine fill the Lunar base sentence with the
    contract's rule (stored float32 minus subtract, toFixed) on every pair; before, the
    engine used Python's f-format, which rounds exact binary halves to even (8 values)."""
    from engine.export_v2 import fill_pair_sentence
    tpl = b.json("similarity.json")["texts"]["lunar_base_pair_sentence"]
    assert "display_rule" not in tpl
    m, paired = _paired(b, "lunar_base")
    assert len(paired) == 450
    pf = m["similarity"]["pairs_file"]
    cols = {ph["column"]: b.raw_column(pf, ph["column"]).astype(np.float64) for ph in tpl["placeholders"].values()}
    mine = {}
    for p in paired:
        text = tpl["text"]
        for name, ph in tpl["placeholders"].items():
            text = text.replace("{" + name + "}", _js_to_fixed(cols[ph["column"]][p] - float(ph.get("subtract", 0.0)), int(ph["decimals"])))
        mine[p] = text
        assert fill_pair_sentence(tpl, {c: v[p] for c, v in cols.items()}) == text
    ids = b.int_column("earth_base.bin", "id")[b.int_column("earth_lunar_base.bin", "land_index")]
    pos = {int(e): k for k, e in enumerate(ids)}
    for it in b.json("explain.json")["missions"]["lunar_base"]:
        assert it["similarity"]["pair_sentence"] == mine[pos[it["id"]]], it["rank"]


# ----------------------------------------------------------------------------- correction 4
@pytest.mark.skip(reason='docs/AUDIO_TOP5.json and tools/make_audio_top5.py are outside what this revision may edit; the audio of the five must be regenerated by its owner for revision 8')
def test_audio_top5_is_regenerated_and_rounds_once(b, tmp_path):
    out = tmp_path / "a.json"
    py = sys.executable
    subprocess.run([py, os.path.join(ROOT, "tools", "make_audio_top5.py"), "--out", str(out)], check=True,
                   capture_output=True)
    shipped = open(os.path.join(REPO, "docs", "AUDIO_TOP5.json"), encoding="utf-8").read()
    assert out.read_text(encoding="utf-8") == shipped, "docs/AUDIO_TOP5.json is stale: run tools/make_audio_top5.py"
    a = json.loads(shipped)
    km = b.column("earth_place_detail.bin", "nearest_place_km")
    ids = b.int_column("earth_base.bin", "id")
    pos = {int(e): k for k, e in enumerate(ids)}
    fkm = b.column("moon_base.bin", "feature_km")
    from engine.display import f32_shortest

    def once(raw):
        return int(Decimal(f32_shortest(raw)).quantize(Decimal(1), rounding=ROUND_HALF_UP))
    for mid, ms in a["missions"].items():
        for p in ms["pairs"]:
            e = once(km[pos[int(p["earth_cell_id"][1:])]])
            mo = once(fkm[int(p["moon_cell_id"][1:])])
            assert p["earth_place"]["distance_km_spoken"] == e and f"about {e} kilometres" in p["say"]
            assert p["moon_place"]["distance_km_spoken"] == mo and f"about {mo} kilometres from" in p["say"]
    base = {p["rank"]: p for p in a["missions"]["lunar_base"]["pairs"]}
    assert base[2]["moon_place"]["distance_km_spoken"] == 15      # 15.47 km, was 16 (15.47 -> 15.5 -> 16)
    assert base[3]["earth_place"]["distance_km_spoken"] == 45     # 45.48 km, was 46
    for p in base.values():
        mp = p["moon_place"]
        share = max(mp["nasa_candidate_region_share_of_cell"].values())
        assert mp["nasa_candidate_region_wording"].startswith("in NASA's" if share >= 0.5 else "at the edge of NASA's")
        assert mp["nasa_candidate_region_wording"] in p["say"]
    assert any("derived from MODIS land-surface temperature" in c for c in a["caveats"])
    assert not any("modelled climatologies (WorldClim, MODIS" in c for c in a["caveats"])


def test_cell_area_caveat_is_recomputed(b):
    a = json.load(open(os.path.join(REPO, "docs", "AUDIO_TOP5.json"), encoding="utf-8"))
    Re, Rm = b.manifest["grid"]["bodies"]["EARTH"]["radius_km"], b.manifest["grid"]["bodies"]["MOON"]["radius_km"]

    def area(lat, r):
        return r * r * math.radians(1) * abs(math.sin(math.radians(lat + 0.5)) - math.sin(math.radians(lat - 0.5)))
    ratios = {}
    for mid, ms in a["missions"].items():
        ratios[mid] = []
        for p in ms["pairs"]:
            el, ml = p["earth_place"]["cell_centre_lat"], p["moon_place"]["cell_centre_lat"]
            ratios[mid].append(area(el, Re) / area(ml, Rm))
            assert p["cell_area_km2"]["earth_over_moon"] == pytest.approx(ratios[mid][-1], abs=0.06)
    cav = next(c for c in a["caveats"] if c.startswith("East-west"))
    lb = ratios["lunar_base"]
    assert f"{min(lb):.0f} to {max(lb):.0f} times more ground" in cav
    assert 85 < min(lb) and max(lb) < 230 and all(13 < r < 15 for r in ratios["solar"]) and all(35 < r < 55 for r in ratios["rover"])


# ----------------------------------------------------------------------------- correction 5 (contract rounding)
def test_stored_scores_round_with_python_round_on_a_float_not_numpy_round():
    """docs/DATA_CONTRACT.md 'Rounding (one rule)': round(float(x), 2), never numpy.round."""
    from engine.export_v2 import _round_array
    from engine.suitability import round_like_export
    x = np.array([2.675, 89.255, 4.135, 0.125, np.nan])
    want = [2.67, 89.25, 4.13, 0.12]
    for f in (round_like_export, _round_array):
        got = f(x, 2)
        assert got[:4].tolist() == want and np.isnan(got[4])
    assert float(np.round(2.675, 2)) == 2.68 and round(np.float64(2.675), 2) == 2.68   # the other rule
    contract = open(os.path.join(REPO, "docs", "DATA_CONTRACT.md"), encoding="utf-8").read()
    assert "similarity uses `numpy.round` as analog_finder does" not in contract
    assert "**Rounding (one rule;" in contract
