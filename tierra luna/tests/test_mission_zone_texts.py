"""Mission-zone web texts (engine/mission_zone_texts.json) against docs/MISSION_ZONES.md and the lunar table.

Reads only the json, the document and output_real/moon_real_1deg.csv; fast (a few seconds).
"""
import json
import re
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

HERE = Path(__file__).resolve().parents[1]
JSON = HERE / "engine" / "mission_zone_texts.json"
DOC = HERE.parent / "docs" / "MISSION_ZONES.md"
MOON = HERE / "output_real" / "moon_real_1deg.csv"
EARTH = HERE / "output_real" / "earth_real_1deg.csv"
BUNDLE = HERE.parent / "app" / "public" / "data" / "v2"

KEYS = ["consulted_on", "source_document", "approved_by", "region_labels", "general_note", "zone_why", "outside", "figures"]
OUTSIDE = {"rover": list("CDEF"), "solar": list("ABCEF"), "lunar_base": list("BCDEF")}
FORBIDDEN = [r"\bno missions?\b", r"never visited", r"cannot work", r"can't work", r"best by data", r"best by (the )?data",
             r"\bregion [A-F]\b", r"\b[EM]\d{2,5}\b", r"Artemis III\b", r"\bnot driven\b", r"\bno rover\b",
             r"\bendorse", r"\bpartner",
             # equatorial ground outside the maria gets as much sunlight (fact check 2026-11-15)
             r"the most sunlight", r"most sunlight in our data"]
# Mission designations are names, not figures.
NAMES = [r"Chang'e \d( and \d)?", r"Apollo \d+(, \d+)*( and \d+)?", r"IM-\d", r"Lunokhod \d", r"Yutu-\d", r"Queqiao-\d",
         r"Chandrayaan-\d"]


@pytest.fixture(scope="module")
def data():
    return json.loads(JSON.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def doc():
    return DOC.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def moon():
    m = pd.read_csv(MOON, usecols=["row", "col", "lat_deg", "lon_deg", "elevation_m", "slope_deg", "irradiance_kwh_m2_day"])
    return m.sort_values(["row", "col"]).reset_index(drop=True)


def strings(d):
    out = {"general_note": d["general_note"]}
    out.update({f"zone_why.{k}": v for k, v in d["zone_why"].items()})
    for mis, regs in d["outside"].items():
        out.update({f"outside.{mis}.{r}": v for r, v in regs.items()})
    return out


def test_keys_are_complete(data):
    assert list(data) == KEYS
    assert data["consulted_on"] == "2026-11-15"
    assert data["source_document"] == "docs/MISSION_ZONES.md"
    assert "2026-11-15 08:55 CET" in data["approved_by"]
    assert sorted(data["region_labels"]) == list("ABCDEF")
    assert sorted(data["zone_why"]) == ["lunar_base", "rover", "solar"]
    assert {k: sorted(v) for k, v in data["outside"].items()} == OUTSIDE
    for f in data["figures"]:
        assert sorted(f) == ["how_computed", "unit", "used_in", "value"]
        assert f["used_in"] and all(k in strings(data) for k in f["used_in"])


def test_every_string_is_in_the_document_verbatim(data, doc):
    for k, s in strings(data).items():
        assert f"> {s}\n" in doc, k
    for r, lab in data["region_labels"].items():
        assert f"| {r} | {lab} |" in doc, r


def test_strings_are_short_plain_and_free_of_forbidden_claims(data):
    for k, s in strings(data).items():
        assert len(s.split()) <= 70, (k, len(s.split()))
        for pat in FORBIDDEN:
            assert not re.search(pat, s, re.I), (k, pat)


def test_every_number_in_a_string_is_a_listed_figure(data):
    values = {f["value"]: f for f in data["figures"]}
    for k, s in strings(data).items():
        t = s
        for pat in NAMES:
            t = re.sub(pat, "", t)
        for num in re.findall(r"\d[\d,]*(?:\.\d+)?", t):
            num = num.rstrip(",")
            assert num in values, (k, num)
            assert k in values[num]["used_in"], (k, num)


def _wmedian(v, w):
    ok = np.isfinite(v)
    v, w = v[ok], w[ok]
    o = np.argsort(v, kind="stable")
    cw = np.cumsum(w[o]) / w.sum()
    return float(v[o][np.searchsorted(cw, 0.5)])


def test_regional_medians_and_polar_maxima_reproduce(data, moon):
    lat, lon, el = moon.lat_deg.to_numpy(), moon.lon_deg.to_numpy(), moon.elevation_m.to_numpy()
    w = np.cos(np.radians(lat))
    irr = moon.irradiance_kwh_m2_day.to_numpy()
    slope = moon.slope_deg.to_numpy()
    mid = (lat > -75) & (lat < 75)
    D = (np.abs(lat) <= 30) & (el <= -1200)
    E = mid & ~D & (np.abs(lon) > 90)
    F = mid & ~D & (np.abs(lon) <= 90)
    assert (D.sum(), E.sum(), F.sum()) == (6686, 25971, 21343)
    fig = {f["value"] for f in data["figures"]}
    # medians cited (rounded as in the strings)
    assert str(round(_wmedian(irr[D], w[D]))) in fig            # 10.02 -> "10"
    assert str(round(_wmedian(irr[E], w[E]))) in fig            # 8.96 -> "9"
    assert str(round(_wmedian(irr[F], w[F]))) in fig            # 8.25 -> "8"
    assert f"{_wmedian(slope[D], w[D]):.1f}" in fig             # 1.13 -> "1.1"
    # the maria are the flattest and the lowest of the regions the strings compare
    assert _wmedian(slope[D], w[D]) < min(_wmedian(slope[E], w[E]), _wmedian(slope[F], w[F]))
    assert _wmedian(el[D], w[D]) < min(_wmedian(el[E], w[E]), _wmedian(el[F], w[F]))
    # polar maxima of horizontal irradiance
    assert f"{np.nanmax(irr[lat <= -75]):.2f}" in fig            # 2.475 -> "2.48"
    assert f"{np.nanmax(irr[lat >= 75]):.2f}" in fig             # 2.451 -> "2.45"
    assert np.nanmax(irr[np.abs(lat) >= 75]) < 3.54


def test_maria_sunlight_is_not_above_other_equatorial_ground(moon):
    """Why the strings say 'as high as anywhere', not 'the most': within 30 degrees of the equator the
    ground outside the maria gets as much sunlight (area-weighted median 10.11 vs 10.02)."""
    lat, el = moon.lat_deg.to_numpy(), moon.elevation_m.to_numpy()
    w = np.cos(np.radians(lat))
    irr = moon.irradiance_kwh_m2_day.to_numpy()
    D = (np.abs(lat) <= 30) & (el <= -1200)
    H = (np.abs(lat) <= 30) & ~D
    assert _wmedian(irr[H], w[H]) >= _wmedian(irr[D], w[D])
    assert np.nanmax(irr[D]) == np.nanmax(irr)


def _bin(name):
    man = json.loads((BUNDLE / "manifest.json").read_text(encoding="utf-8"))
    f = next(x for x in man["files"] if x["name"] == name)
    buf = (BUNDLE / name).read_bytes()
    return {c["name"]: np.frombuffer(buf, dtype="<f4" if c["type"] == "float32" else "<i4", count=c["length"],
                                     offset=c["offset"]) for c in f["columns"]}


def _pair(ev, mv, tol, w, bound):
    """Real-value rule of engine_config real_value_similarity, written again here: twin index or -1, similarity."""
    tw = np.full(len(ev), -1)
    sim = np.full(len(ev), np.nan)
    for s in range(0, len(ev), 400):
        d = np.abs(ev[s:s + 400, None, :] - mv[None, :, :])
        sm = 100 * (np.exp(-0.5 * (d / tol) ** 2) * w).sum(axis=2) / w.sum()
        sm = np.where((d <= bound).all(axis=2), sm, -1.0)
        j = sm.argmax(axis=1)
        b = sm[np.arange(len(j)), j]
        tw[s:s + 400] = np.where(b >= 0, j, -1)
        sim[s:s + 400] = np.where(b >= 0, b, np.nan)
    return tw, sim


@pytest.mark.skipif(not (BUNDLE / "manifest.json").exists(), reason="no data bundle")
def test_rover_and_solar_figures_recompute(data):
    """The north- against south-pole Rover figures and the 3.54 of the Solar strings, recomputed from the
    real tables and the bundle's ranked lists (about 10 s)."""
    fig = {f["value"] for f in data["figures"]}
    moon = pd.read_csv(MOON, usecols=["cell_id", "lat_deg", "elevation_m", "slope_iso_deg", "roughness_m"])
    earth = pd.read_csv(EARTH, usecols=["cell_id", "row", "lat_deg", "elevation_m", "slope_iso_deg", "roughness_m"])
    earth.index = earth.cell_id.str[1:].astype(int)
    ew, mw = np.cos(np.radians(earth.lat_deg)), np.cos(np.radians(moon.lat_deg))
    ok = earth.elevation_m.notna()
    emean = (earth.elevation_m[ok] * ew[ok]).sum() / ew[ok].sum()
    mmean = (moon.elevation_m * mw).sum() / mw.sum()
    base = _bin("earth_base.bin")
    rover = _bin("earth_rover.bin")
    e = earth.loc[base["id"][rover["land_index"]]]
    ev = np.stack([e.slope_iso_deg, e.roughness_m, e.elevation_m - emean], axis=1)
    tol, w = np.array([2.0, 30.0, 500.0]), np.array([0.4, 0.4, 0.2])
    out = {}
    for name, m in (("S", moon.lat_deg <= -75), ("N", moon.lat_deg >= 75)):
        mm = moon[m]
        mv = np.stack([mm.slope_iso_deg, mm.roughness_m, mm.elevation_m - mmean], axis=1)
        tw, sim = _pair(ev, mv, tol, w, tol * np.array([1.0, 1.0, 2.0]))
        has = tw >= 0
        out[name] = (int(has.sum()), float(np.median(sim[has])),
                     float(np.median(np.abs(ev[has, 0] - mv[tw[has], 0]))))
    assert f"{out['N'][0]:,}" in fig and f"{out['S'][0]:,}" in fig          # 9,888 and 10,192
    assert f"{out['N'][1]:.1f}" in fig and f"{out['S'][1]:.1f}" in fig      # 99.7 and 93.3
    assert f"{out['N'][2]:.2f}" in fig and f"{out['S'][2]:.2f}" in fig      # 0.10 and 0.41
    assert out["N"][2] < out["S"][2] and out["N"][1] > out["S"][1]
    solar = _bin("earth_solar.bin")
    rows = earth.loc[base["id"][solar["land_index"]], "row"].to_numpy()
    need = float(base["d.irradiance_toa_kwh_m2_day"][rows].min()) - 0.6   # the key tolerance of solar
    assert f"{need:.2f}" in fig                                             # 3.54
    assert f"{len(rows):,}" in fig                                          # 18,777
