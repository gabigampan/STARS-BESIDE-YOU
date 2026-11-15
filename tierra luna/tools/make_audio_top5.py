"""Facts for the audio descriptions of the 5 best analog pairs of each mission.

Reads the shipped static bundle (app/public/data/v2, docs/DATA_CONTRACT.md revision 6)
and writes docs/AUDIO_TOP5.json: per mission (rover, solar, lunar_base) the paired
Earth points ranked 1 to 5 by the bundle, with the Earth place, the lunar twin, the
scores, the key and secondary variables on both sides, common traits backed by numbers
and a sentence a narrator can read.

Deterministic: no clock, no network, no randomness. Run from anywhere:

    python "tierra luna/tools/make_audio_top5.py" [--bundle DIR] [--out FILE]

Two code paths: every number is taken from explain.json (the bundle's published
values) and checked against the binary columns (earth_<m>.bin, earth_<m>_pairs.bin,
earth_base.bin, earth_place_detail.bin, moon_base.bin) and twins.json. Place names are
checked against the dataset they are attributed to, and distances are recomputed.
The script stops with an AssertionError on any mismatch.

Sources outside the bundle (read only):
* GeoNames cities1000 as shipped in the reverse_geocoder package (rg_cities1000.csv),
  the populated places the engine uses (tierra luna/engine/places.py): only to find the
  coordinates of the nearest place the bundle names, for the compass direction;
* tierra luna/engine/data/artemis_iii_regions.geojson: the names of the NASA candidate
  regions a Lunar base twin cell intersects (the bundle has only the zone, region A),
  with the engine's own rule (the 1-degree cell square intersects the region), and the
  share of the cell's area inside each of them (south-polar Lambert azimuthal
  equal-area projection on the 1737.4 km sphere, written out here), which decides the
  words "in" (half of the cell or more) or "at the edge of" (less than half).

Statistical audit corrections of 2026-11-15 (docs/stats_audit/correcciones_1.md):
distances are rounded once, from the stored float32 (engine/display.py displayed, half
up), never from the 1-decimal value (15.47 km was spoken 16); the Lunar base twins are
said to be "in" a NASA region only when at least half of the cell lies inside it; the
caveats say that the daily swing is DERIVED from MODIS land-surface temperature and how
much more ground an Earth cell averages than its twin (computed from the pairs).
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import os
import sys
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
BUNDLE = os.path.join(REPO, "app", "public", "data", "v2")
OUT = os.path.join(REPO, "docs", "AUDIO_TOP5.json")
ENGINE_DATA = os.path.join(REPO, "tierra luna", "engine", "data")
sys.path.insert(0, os.path.join(REPO, "tierra luna"))
from engine.display import SHARE_LOST_PYTHON, displayed, share_lost_percent, tenths  # noqa: E402  (one display rule with the engine)
SCRIPT_REL = "tierra luna/tools/make_audio_top5.py"
GENERATED_ON = "2026-11-15"
MISSIONS = ["rover", "solar", "lunar_base"]
TOP = 5
LUNAR_BASE_ZONE_TEXT = ("the 280 lunar cells that overlap NASA's nine candidate landing regions near the lunar south pole "
                        "(the engine's zone: the 1-degree cell square intersects a region outline)")
REGION_IN_MIN_SHARE = 0.5   # "in NASA's ... region" only when at least half of the cell lies inside it

CHECKS: List[str] = []


def check(cond: bool, msg: str) -> None:
    if not cond:
        raise AssertionError(msg)


# ----------------------------------------------------------------------------- bundle reading
class Bundle:
    def __init__(self, path: str):
        self.path = path
        self.manifest = self.json("manifest.json")
        self.missing_int = self.manifest["encoding"]["int32_missing"]

    def json(self, name: str) -> Any:
        with open(os.path.join(self.path, name), encoding="utf-8") as fh:
            return json.load(fh)

    def _entry(self, file: str, column: str) -> Dict[str, Any]:
        f = next(f for f in self.manifest["files"] if f["name"] == file)
        return next(c for c in f["columns"] if c["name"] == column)

    def col(self, file: str, column: str) -> np.ndarray:
        """Decoded column (float64, NaN = missing; quantised columns divided)."""
        c = self._entry(file, column)
        with open(os.path.join(self.path, file), "rb") as fh:
            fh.seek(c["offset"])
            raw = np.frombuffer(fh.read(4 * c["length"]), dtype="<f4" if c["type"] == "float32" else "<i4")
        if c["type"] == "float32":
            return raw.astype(np.float64)
        out = raw.astype(np.float64)
        out[raw == self.missing_int] = np.nan
        if c.get("divisor"):
            out = out / c["divisor"]
        return out


def great_circle_km(lat1, lon1, lat2, lon2, r):
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dl = math.radians(lon2 - lon1)
    c = math.sin(p1) * math.sin(p2) + math.cos(p1) * math.cos(p2) * math.cos(dl)
    return r * math.acos(max(-1.0, min(1.0, c)))


def spoken_km(raw: float) -> int:
    """A distance as spoken: rounded ONCE to the unit, half up, from the stored float32
    (the value the browser displays, engine/display.py), never from a 1-decimal copy."""
    return int(displayed(raw, 0))


def cell_area_km2(lat_centre: float, r: float, deg: float = 1.0) -> float:
    """Area of a deg x deg cell on a sphere of radius r: r^2 * dlon * |sin(lat2) - sin(lat1)|."""
    a, b = math.radians(lat_centre - deg / 2), math.radians(lat_centre + deg / 2)
    return r * r * math.radians(deg) * abs(math.sin(b) - math.sin(a))


def cell_east_west_km(lat_centre: float, r: float, deg: float = 1.0) -> float:
    """East-west width of a cell at its centre latitude."""
    return 2 * math.pi * r * deg / 360.0 * math.cos(math.radians(lat_centre))


def south_laea(lon: float, lat: float, r: float) -> Tuple[float, float]:
    """South-polar Lambert azimuthal equal-area projection on a sphere of radius r (km):
    rho = 2 r sin(c / 2), c = angular distance from the south pole."""
    c = math.radians(90.0 + lat)
    rho = 2.0 * r * math.sin(c / 2.0)
    return rho * math.sin(math.radians(lon)), rho * math.cos(math.radians(lon))


def project_geom(g, r: float, step_deg: float = 0.01):
    """A lon/lat shapely geometry densified to step_deg and projected (equal area)."""
    import shapely

    def fwd(c):
        lon, lat = c[:, 0], c[:, 1]
        rho = 2.0 * r * np.sin(np.radians(90.0 + lat) / 2.0)
        return np.column_stack([rho * np.sin(np.radians(lon)), rho * np.cos(np.radians(lon))])
    return shapely.transform(shapely.segmentize(g, step_deg), fwd)


def region_share_of_cell(lat: float, lon: float, region_geom, r: float) -> float:
    """Share of the area of the 1-degree cell centred at (lat, lon) inside a region (0-1)."""
    from shapely.geometry import box
    cell = project_geom(box(lon - 0.5, lat - 0.5, lon + 0.5, lat + 0.5), r)
    return float(cell.intersection(project_geom(region_geom, r)).area / cell.area)


def bearing_deg(lat1, lon1, lat2, lon2) -> float:
    """Initial bearing from point 1 to point 2, degrees clockwise from north."""
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dl = math.radians(lon2 - lon1)
    y = math.sin(dl) * math.cos(p2)
    x = math.cos(p1) * math.sin(p2) - math.sin(p1) * math.cos(p2) * math.cos(dl)
    return (math.degrees(math.atan2(y, x)) + 360.0) % 360.0


COMPASS = ["north", "north-east", "east", "south-east", "south", "south-west", "west", "north-west"]


def compass(b: float) -> str:
    return COMPASS[int((b + 22.5) // 45) % 8]


def decimals_of(x: float) -> int:
    s = repr(float(x))
    if "e" in s:
        return 6
    return len(s.split(".")[1].rstrip("0")) if "." in s else 0


def same(published: float, raw: float, what: str) -> None:
    """The published (rounded) value equals the raw binary value at its precision."""
    d = decimals_of(published)
    tol = 0.5 * 10 ** (-d) + 1e-6 * max(1.0, abs(raw)) + 1e-9
    check(abs(published - raw) <= tol, f"{what}: published {published} != binary {raw}")


def mid_rank_pct(values: np.ndarray, x: float) -> float:
    """Mid-rank percentile of x within values (100 * (rank - 0.5) / n, ties averaged)."""
    v = values[~np.isnan(values)]
    below = float(np.sum(v < x))
    equal = float(np.sum(v == x))
    rank = below + (equal + 1.0) / 2.0 if equal else below + 0.5
    return 100.0 * (rank - 0.5) / len(v)


def ordinal(n: int) -> str:
    if 10 <= n % 100 <= 20:
        return f"{n}th"
    return f"{n}{ {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th') }"


def fnum(x: float, d: int) -> str:
    s = f"{x:,.{d}f}"
    return s


def speak_num(x: float, d: int) -> str:
    """Number for speech: no thousands comma problems, sensible decimals."""
    return f"{round(x, d):.{d}f}" if d else f"{int(round(x)):,}"


# ----------------------------------------------------------------------------- level lookup
def level_table(variables_json: Dict) -> Dict[Tuple[str, str], str]:
    out = {}
    for v in variables_json["variables"]:
        for body, b in v["bodies"].items():
            out[(v["name"], body)] = b["level"]
    return out


def side_level(sim_var: Dict, body: str, levels: Dict) -> Dict[str, Optional[str]]:
    """Level of a similarity variable on one side: from variables.json when the
    variable (or the column it is made from) is there, else the missions.json side."""
    side = sim_var["sides"][body]
    name = sim_var["variable"]
    if (name, body) in levels:
        return {"level": levels[(name, body)], "from": f"variables.json {name} {body}"}
    col = side.get("column")
    if col and (col, body) in levels:
        lv = levels[(col, body)]
        note = None
        if side["level"] not in (lv,) and side["level"] not in ("MEASURED", "DERIVED", "MODELLED"):
            if lv not in side["level"]:
                note = f"missions.json side text says '{side['level']}'"
        return {"level": lv, "from": f"variables.json {col} {body}", "note": note}
    return {"level": side["level"], "from": f"missions.json similarity.variables[{name}].sides.{body}.level"}


def moon_tmin_level(sim_var: Dict) -> Dict[str, Any]:
    """Lunar coldest temperature: MEASURED (Diviner tmin_k, real_data/provenance_moon.csv);
    the table's tmin_c is that value in degrees C, listed DERIVED in variables.json for the
    conversion only. Wording of the note from missions.json."""
    prov = os.path.join(REPO, "tierra luna", "real_data", "provenance_moon.csv")
    with open(prov, encoding="utf-8") as fh:
        row = next(r for r in csv.reader(fh) if r[:2] == ["tmin_k", "MOON"])
    check(row[2] == "MEASURED", f"provenance_moon.csv tmin_k MOON is {row[2]}")
    side_text = sim_var["sides"]["MOON"]["text"]
    check("MEASURED" in sim_var["sides"]["MOON"]["level"], "missions.json lunar tmin_k side level")
    return {"level": "MEASURED", "from": "tierra luna/real_data/provenance_moon.csv tmin_k MOON (Diviner GCP, tbol)",
            "note": f"missions.json: {side_text}. variables.json lists the table column tmin_c as DERIVED only "
                    f"because it is this measured value converted to degrees C."}


# ----------------------------------------------------------------------------- main build
def build(bundle_path: str) -> Dict[str, Any]:
    b = Bundle(bundle_path)
    man = b.manifest
    check(man["contract_revision"] == 6, "expected contract revision 6")
    missions_json = b.json("missions.json")
    mission_by_id = {m["id"]: m for m in missions_json["missions"]}
    explain = b.json("explain.json")
    twins = b.json("twins.json")
    places = b.json("places.json")
    pdetail = b.json("place_detail.json")
    iau = b.json("iau_moon_features.json")
    zones = b.json("mission_zones.json")
    sim_json = b.json("similarity.json")
    levels = level_table(b.json("variables.json"))
    grid = man["grid"]
    R_E = grid["bodies"]["EARTH"]["radius_km"]
    R_M = grid["bodies"]["MOON"]["radius_km"]
    cols = grid["cols"]

    # Earth base / place detail (land rows)
    land_ids = b.col("earth_base.bin", "id").astype(np.int64)
    land_pos = {int(i): k for k, i in enumerate(land_ids)}
    e_lat_rows = b.col("earth_base.bin", "lat")
    e_lon_cols = b.col("earth_base.bin", "lon")
    e_country = b.col("earth_base.bin", "country")
    e_region = b.col("earth_base.bin", "region")
    e_slope = b.col("earth_base.bin", "v.slope_iso_deg")
    e_rough = b.col("earth_base.bin", "v.roughness_m")
    e_tmin = b.col("earth_base.bin", "v.tmin_c")
    e_ground = b.col("earth_base.bin", "v.irradiance_kwh_m2_day")
    np_idx = b.col("earth_place_detail.bin", "nearest_place")
    np_km = b.col("earth_place_detail.bin", "nearest_place_km")
    lr_idx = b.col("earth_place_detail.bin", "label_rule")

    # Moon base (all cells)
    m_lat_rows = b.col("moon_base.bin", "lat")
    m_lon_cols = b.col("moon_base.bin", "lon")
    m_slope = b.col("moon_base.bin", "v.slope_iso_deg")
    m_rough = b.col("moon_base.bin", "v.roughness_m")
    m_feat = b.col("moon_base.bin", "feature")
    m_feat_km = b.col("moon_base.bin", "feature_km")
    m_region = b.col("moon_base.bin", "region")
    m_irr = b.col("moon_base.bin", "v.irradiance_kwh_m2_day")
    m_tmin = b.col("moon_base.bin", "v.tmin_c")

    # populations for the qualitative words (slope, roughness): every cell with a value
    pop = {
        "slope": {"EARTH": e_slope, "MOON": m_slope},
        "rough": {"EARTH": e_rough, "MOON": m_rough},
    }
    pop_text = {
        "EARTH": f"all {int(np.sum(~np.isnan(e_slope))):,} Earth land cells with a value (earth_base.bin)",
        "MOON": f"all {int(np.sum(~np.isnan(m_slope))):,} lunar cells with a value (moon_base.bin)",
    }

    # GeoNames places (the engine's populated places) for the direction
    import reverse_geocoder  # noqa: the engine's own dependency (engine/places.py)
    rg_csv = os.path.join(os.path.dirname(reverse_geocoder.__file__), "rg_cities1000.csv")
    gn = pd.read_csv(rg_csv, dtype=str, keep_default_na=False)
    gn_names = set(gn["name"])
    bundle_place_names = set(pdetail["nearest_places"])

    # IAU names (bundle and engine copy)
    iau_names = set(iau["name"])
    with open(os.path.join(ENGINE_DATA, "iau_moon_nomenclature.csv"), encoding="utf-8") as fh:
        engine_iau_names = {r["name"] for r in csv.DictReader(fh)} if True else set()

    # Artemis region outlines (engine data) for the Lunar base twin's region names
    from shapely.geometry import box, shape
    with open(os.path.join(ENGINE_DATA, "artemis_iii_regions.geojson"), encoding="utf-8") as fh:
        gj = json.load(fh)
    art = [(f["properties"]["name"], shape(f["geometry"])) for f in gj["features"]]
    art_names = {n for n, _ in art}

    country_names = [c["name"] for c in places["countries"]]
    region_names = places["regions"]
    region_names = [r["name"] if isinstance(r, dict) else r for r in region_names]

    out_missions: Dict[str, Any] = {}
    for mid in MISSIONS:
        mj = mission_by_id[mid]
        sim = mj["similarity"]
        efile = f"earth_{mid}.bin"
        pfile = f"earth_{mid}_pairs.bin"
        li = b.col(efile, "land_index").astype(np.int64)
        rank = b.col(efile, "rank")
        twin = b.col(efile, "twin")
        suit = b.col(efile, "suitability")
        simv = b.col(efile, "similarity")
        final = b.col(efile, "final")
        lorder = b.col(pfile, "list_order")
        ex_items = {it["rank"]: it for it in explain["missions"][mid]}
        twin_rows = {t["id"]: t for t in twins["missions"][mid]["twins"]}
        pairs: List[Dict[str, Any]] = []
        for r in range(1, TOP + 1):
            hit = np.flatnonzero(rank == r)
            check(len(hit) == 1, f"{mid}: rank {r} found {len(hit)} times")
            p = int(hit[0])
            check(not np.isnan(twin[p]), f"{mid} rank {r}: not a paired point")
            check(lorder[p] == r, f"{mid} rank {r}: list_order {lorder[p]}")
            eid = int(land_ids[li[p]])
            mid_cell = int(twin[p])
            it = ex_items[r]
            check(it["id"] == eid, f"{mid} rank {r}: explain id {it['id']} != binary {eid}")
            st = it["similarity"]
            check(st["twin"]["id"] == mid_cell, f"{mid} rank {r}: explain twin != binary twin")
            same(it["suitability"], suit[p], f"{mid} r{r} suitability")
            same(st["value"], simv[p], f"{mid} r{r} similarity")
            same(it["final"], final[p], f"{mid} r{r} final")

            # ---- Earth place
            erow, ecol = divmod(eid, cols)
            elat, elon = 90 - (erow + 0.5), -180 + (ecol + 0.5)
            check(elat == it["lat"] and elon == it["lon"], f"{mid} r{r}: Earth lat/lon")
            check(abs(e_lat_rows[erow] - elat) < 1e-4 and abs(e_lon_cols[ecol] - elon) < 1e-4, "earth_base lat/lon")
            k = land_pos[eid]
            pl = it["place"]
            cname = country_names[int(e_country[k])]
            check(cname == pl["country"], f"{mid} r{r}: country {cname} != {pl['country']}")
            rname = None if np.isnan(e_region[k]) else region_names[int(e_region[k])]
            check(rname == pl["region"], f"{mid} r{r}: region {rname} != {pl['region']}")
            nname = pdetail["nearest_places"][int(np_idx[k])]
            check(nname == pl["nearest_place"], f"{mid} r{r}: nearest place")
            same(pl["nearest_place_km"], np_km[k], f"{mid} r{r} nearest_place_km")
            check(nname in bundle_place_names and nname in gn_names, f"{nname} not in GeoNames/bundle")
            cand = gn[gn["name"] == nname]
            best = None
            for _, row in cand.iterrows():
                d = great_circle_km(elat, elon, float(row["lat"]), float(row["lon"]), R_E)
                if best is None or abs(d - np_km[k]) < abs(best[0] - np_km[k]):
                    best = (d, row)
            dkm, prow = best
            check(abs(dkm - np_km[k]) < 0.2, f"{nname}: recomputed {dkm} km vs bundle {np_km[k]}")
            plat, plon = float(prow["lat"]), float(prow["lon"])
            direction = compass(bearing_deg(plat, plon, elat, elon))
            label_rule = pdetail["label_rules"][int(lr_idx[k])]
            km_say = spoken_km(np_km[k])
            where_bits = [x for x in (pl["region"], pl["country"]) if x]
            speakable = f"about {km_say} km {direction} of {nname}, {', '.join(where_bits)}"
            earth_place = {
                "speakable": speakable,
                "nearest_named_place": nname,
                "nearest_named_place_source": "GeoNames cities1000 populated places (the engine's offline copy in the "
                                              "reverse_geocoder package, tierra luna/engine/places.py); bundle: "
                                              "place_detail.json nearest_places / earth_place_detail.bin",
                "nearest_named_place_admin1_in_geonames": prow["admin1"] or None,
                "nearest_named_place_country_code_in_geonames": prow["cc"],
                "distance_km": pl["nearest_place_km"],
                "distance_km_spoken": km_say,
                "distance_rounding": "distance_km_spoken is rounded once to the unit, half up, from the stored float32 "
                                     "(earth_place_detail.bin nearest_place_km), not from the 1-decimal distance_km",
                "distance_km_recomputed": round(dkm, 1),
                "direction_from_place": direction,
                "direction_note": "initial great-circle bearing from the named place to the cell centre, 8-point compass",
                "region": pl["region"],
                "country": pl["country"],
                "country_code": pl["country_code"],
                "country_label_rule": label_rule,
                "region_country_source": "bundle places.json (indexed by earth_base.bin country / region)",
                "cell_centre_lat": elat,
                "cell_centre_lon": elon,
            }
            if pl["region"] is None:
                earth_place["region_note"] = "the bundle gives no first-level region for this cell (the nearest place is farther than the engine's region_max_place_km or in another country)"

            # ---- Moon place
            mrow, mcol = divmod(mid_cell, cols)
            mlat, mlon = 90 - (mrow + 0.5), -180 + (mcol + 0.5)
            check(mlat == st["twin"]["lat"] and mlon == st["twin"]["lon"], f"{mid} r{r}: Moon lat/lon")
            check(abs(m_lat_rows[mrow] - mlat) < 1e-4 and abs(m_lon_cols[mcol] - mlon) < 1e-4, "moon_base lat/lon")
            fi = int(m_feat[mid_cell])
            fname, ftype = iau["name"][fi], iau["type"][fi]
            check(fname == st["twin"]["feature"], f"{mid} r{r}: feature {fname}")
            same(st["twin"]["feature_km"], m_feat_km[mid_cell], f"{mid} r{r} feature_km")
            tw = twin_rows[mid_cell]
            check(tw["feature"]["name"] == fname and tw["feature"]["type"] == ftype, "twins.json feature")
            check(tw["feature"]["distance_km"] == st["twin"]["feature_km"], "twins.json feature distance")
            check(fname in iau_names and fname in engine_iau_names, f"{fname} not in IAU lists")
            fkm = great_circle_km(mlat, mlon, iau["lat"][fi], iau["lon"][fi], R_M)
            check(abs(fkm - m_feat_km[mid_cell]) < 0.2, f"{fname}: recomputed {fkm} vs {m_feat_km[mid_cell]}")
            reg = zones["regions"][int(m_region[mid_cell])]
            moon_place = {
                "nearest_named_feature": fname,
                "feature_type": ftype,
                "distance_km": st["twin"]["feature_km"],
                "distance_km_spoken": spoken_km(m_feat_km[mid_cell]),
                "distance_km_recomputed": round(fkm, 1),
                "feature_source": "bundle iau_moon_features.json (USGS/IAU Gazetteer of Planetary Nomenclature), "
                                  "moon_base.bin feature / feature_km",
                "cell_centre_lat": mlat,
                "cell_centre_lon": mlon,
                "lunar_region_code": reg["code"],
                "lunar_region_label": reg["label"],
                "cell_east_west_km": round(cell_east_west_km(mlat, R_M), 2),
            }
            if mid == "lunar_base":
                check(reg["code"] == "A", f"lunar_base twin {mid_cell} outside region A")
                cellbox = box(mlon - 0.5, mlat - 0.5, mlon + 0.5, mlat + 0.5)
                hits = sorted(n for n, g in art if g.intersects(cellbox))
                check(len(hits) >= 1 and all(h in art_names for h in hits), "Artemis region names")
                moon_place["zone"] = LUNAR_BASE_ZONE_TEXT
                moon_place["nasa_candidate_regions_intersected"] = hits
                shares = {n: region_share_of_cell(mlat, mlon, g, R_M) for n, g in art if n in hits}
                main_region = max(sorted(shares), key=lambda n: shares[n])
                share = shares[main_region]
                pct = 100.0 * share
                from shapely.geometry import Point
                centre_in = bool(project_geom(dict(art)[main_region], R_M).contains(project_geom(Point(mlon, mlat), R_M)))
                moon_place["cell_centre_inside_nasa_candidate_region"] = centre_in
                pct_txt = f"{pct:.1f}" if pct < 10 else f"{pct:.0f}"
                moon_place["nasa_candidate_region_share_of_cell"] = {n: round(v, 4) for n, v in shares.items()}
                moon_place["nasa_candidate_region_share_method"] = (
                    "area of the 1-degree cell inside the region outline over the cell's area, south-polar Lambert "
                    "azimuthal equal-area projection on the 1737.4 km sphere (edges densified to 0.01 degrees); the outline "
                    "is the union of the region's 1 km grid squares, an upper bound of the region")
                moon_place["nasa_candidate_region_wording"] = (
                    f"in NASA's {main_region} candidate region" if share >= REGION_IN_MIN_SHARE else
                    f"at the edge of NASA's {main_region} candidate region ({pct_txt} % of the cell lies inside it; "
                    f"its centre is {'inside' if centre_in else 'outside'})")
                moon_place["nasa_candidate_region_wording_rule"] = (
                    f"'in' when at least {REGION_IN_MIN_SHARE:.0%} of the cell lies inside the region, else 'at the edge of'")
                moon_place["nasa_candidate_regions_source"] = (
                    "tierra luna/engine/data/artemis_iii_regions.geojson (engine data; the bundle has only region A); "
                    "engine rule: the 1-degree cell square intersects the region outline (an upper bound)")

            # ---- variables
            vars_out = []
            for v in sim["variables"]:
                name = v["variable"]
                ev = next(x for x in st["variables"] if x["variable"] == name)
                le, lm = side_level(v, "EARTH", levels), side_level(v, "MOON", levels)
                if mid == "lunar_base" and name == "tmin_k":
                    lm = moon_tmin_level(v)
                if mid == "lunar_base":
                    pc = v["pairs_columns"]
                    same(ev["earth_real"], b.col(pfile, pc["earth"])[p], f"{mid} r{r} {name} earth")
                    same(ev["moon_real"], b.col(pfile, pc["moon"])[p], f"{mid} r{r} {name} moon")
                    same(ev["difference_real"], b.col(pfile, pc["diff"])[p], f"{mid} r{r} {name} diff")
                    same(ev["moon_real"], tw["values"][name], f"twins.json {name}")
                    row = {"variable": name, "label": v["label"], "role": v["role"], "weight": v["weight"],
                           "tolerance": v["tolerance"], "bound": v["bound"], "real_unit": v["real_unit"],
                           "earth_real": ev["earth_real"], "moon_real": ev["moon_real"],
                           "difference_real": ev["difference_real"],
                           "earth_level": le, "moon_level": lm, "score": ev["score"]}
                    if v["scale"] == "percentile_within_population":
                        same(ev["earth"], b.col(pfile, pc["earth_pct"])[p], f"{mid} r{r} {name} earth_pct")
                        same(ev["moon"], b.col(pfile, pc["moon_pct"])[p], f"{mid} r{r} {name} moon_pct")
                        same(ev["difference"], b.col(pfile, pc["diff_pct"])[p], f"{mid} r{r} {name} diff_pct")
                        same(ev["moon"], tw["percentiles"][name], f"twins.json pct {name}")
                        row.update({"compared_unit": "percentile points", "earth_percentile": ev["earth"],
                                    "moon_percentile": ev["moon"], "difference_points": ev["difference"],
                                    "earth_real_c": round(ev["earth_real"] - 273.15, 2),
                                    "moon_real_c": round(ev["moon_real"] - 273.15, 2),
                                    "population_earth": sim["populations"]["EARTH"]["cells"],
                                    "population_moon": sim["populations"]["MOON"]["cells"]})
                        if name == "lst_diurnal_amp_k":
                            row["c_note"] = "a temperature difference: 1 K = 1 degree C, so the swing in degrees C equals the value in K"
                            row.pop("earth_real_c"); row.pop("moon_real_c")
                            row["earth_real_c_swing"] = ev["earth_real"]
                            row["moon_real_c_swing"] = ev["moon_real"]
                    vars_out.append(row)
                else:
                    pc = v["pairs_columns"]
                    same(ev["earth"], b.col(pfile, pc["earth"])[p], f"{mid} r{r} {name} earth")
                    same(ev["moon"], b.col(pfile, pc["moon"])[p], f"{mid} r{r} {name} moon")
                    same(ev["difference"], b.col(pfile, pc["diff"])[p], f"{mid} r{r} {name} diff")
                    same(ev["moon"], tw["values"][name], f"twins.json {name}")
                    vars_out.append({"variable": name, "label": v["label"], "role": v["role"], "weight": v["weight"],
                                     "tolerance": v["tolerance"], "bound": v["bound"], "unit": v["unit"],
                                     "earth": ev["earth"], "moon": ev["moon"], "difference": ev["difference"],
                                     "earth_level": le, "moon_level": lm, "score": ev["score"]})
            # second path for slope / roughness: the raw base tables
            V = {x["variable"]: x for x in vars_out}
            for nm, ea, ma in (("slope_deg", e_slope, m_slope), ("roughness_m", e_rough, m_rough)):
                if nm in V:
                    ek = "earth_real" if mid == "lunar_base" else "earth"
                    mk = "moon_real" if mid == "lunar_base" else "moon"
                    same(V[nm][ek], ea[k], f"{mid} r{r} {nm} vs earth_base")
                    same(V[nm][mk], ma[mid_cell], f"{mid} r{r} {nm} vs moon_base")

            pair = {
                "mission": {"id": mid, "name": mj["title"]},
                "rank": r,
                "earth_cell_id": f"E{eid}",
                "moon_cell_id": f"M{mid_cell}",
                "ids_note": "reference only, not to be read aloud",
                "earth_place": earth_place,
                "moon_place": moon_place,
                "similarity": st["value"],
                "suitability": it["suitability"],
                "final": it["final"],
                "variables": vars_out,
                "not_part_of_similarity": st.get("not_part_of_similarity"),
            }

            # ---- solar: atmosphere
            if mid == "solar":
                atm = st["atmosphere"]
                same(atm["ground_kwh_m2_day"], b.col(pfile, "atm.ground_kwh_m2_day")[p], "atm ground")
                same(atm["toa_kwh_m2_day"], b.col(pfile, "atm.toa_kwh_m2_day")[p], "atm toa")
                same(atm["lost_share"], b.col(pfile, "atm.lost_share")[p], "atm lost")
                same(atm["ground_kwh_m2_day"], e_ground[k], "atm ground vs earth_base")
                # the two numbers as the web displays them (1 decimal, half up, from the stored
                # float32) and the share lost from those two numbers, in integers: the rule of
                # similarity.json texts.solar_limitation {loss_pct} (engine/display.py)
                g_raw, t_raw = b.col(pfile, "atm.ground_kwh_m2_day")[p], b.col(pfile, "atm.toa_kwh_m2_day")[p]
                g1, t1 = tenths(g_raw) / 10, tenths(t_raw) / 10
                lost_pct = share_lost_percent(t_raw, g_raw)
                if st.get("pair_sentence") is not None:
                    check(f"only {g1:.1f} of those {t1:.1f} kWh/m²/day reach the ground ({lost_pct} % is lost" in st["pair_sentence"],
                          f"solar r{r}: the share lost differs from the bundle's per-pair sentence")
                pair["earth_atmosphere"] = {
                    "ground_kwh_m2_day": atm["ground_kwh_m2_day"],
                    "ground_level": levels[("irradiance_kwh_m2_day", "EARTH")],
                    "above_atmosphere_kwh_m2_day": atm["toa_kwh_m2_day"],
                    "above_atmosphere_level": V["irradiance_toa_kwh_m2_day"]["earth_level"]["level"],
                    "lost_share_bundle": atm["lost_share"],
                    "display": {"ground_kwh_m2_day": g1, "above_atmosphere_kwh_m2_day": t1,
                                "lost_percent": lost_pct,
                                "rule": "the rule of similarity.json texts.solar_limitation {loss_pct} (engine/display.py, docs/DATA_CONTRACT.md "
                                        "'wording and display rounding, 2026-11-15'): ground and above as displayed (1 decimal, half up, "
                                        "from the stored float32), as integers of tenths G and A; lost_percent = "
                                        f"{SHARE_LOST_PYTHON} (100 x (A - G) / A rounded half up), "
                                        "so a listener checking by hand gets the same percentage"},
                    "lost_percent_from_bundle_share": round(100.0 * atm["lost_share"]),
                }
                same(V["irradiance_toa_kwh_m2_day"]["moon"], m_irr[mid_cell], "solar moon irradiance vs moon_base")

            if mid == "lunar_base":
                same(V["tmin_k"]["earth_real"], e_tmin[k] + 273.15, "tmin earth vs earth_base")
                same(V["tmin_k"]["moon_real"], m_tmin[mid_cell] + 273.15, "tmin moon vs moon_base")
                pair["pair_sentence_from_bundle"] = st["pair_sentence"]

            ea, ma = cell_area_km2(elat, R_E), cell_area_km2(mlat, R_M)
            pair["cell_area_km2"] = {"earth": round(ea, 1), "moon": round(ma, 1), "earth_over_moon": round(ea / ma, 1),
                                     "earth_east_west_km": round(cell_east_west_km(elat, R_E), 1),
                                     "moon_east_west_km": round(cell_east_west_km(mlat, R_M), 2),
                                     "rule": "1-degree cell on the sphere: R^2 x dlon x |sin(lat2) - sin(lat1)|; "
                                             "east-west width 2 pi R / 360 x cos(lat)"}
            pair["common_traits"] = traits(mid, pair, k, mid_cell, pop, pop_text)
            pair["say"] = say(mid, mj, pair)
            pairs.append(pair)
        out_missions[mid] = {
            "name": mj["title"],
            "similarity_rule": man["similarity_rules"][mid],
            "zone": sim["zone"]["name"] if mid != "lunar_base" else LUNAR_BASE_ZONE_TEXT,
            "similarity_variables": [{k2: v[k2] for k2 in ("variable", "role", "weight", "tolerance", "bound", "unit")}
                                     for v in sim["variables"]],
            "pair_filter": sim["filter"],
            "status": "verified",
            "pairs": pairs,
        }
        note = shared_twin_note(mid, pairs)
        if note:
            out_missions[mid]["note_for_narration"] = note
        CHECKS.append(f"{mid}: ranks 1..{TOP} found once each, all paired, list_order 1..{TOP}; ids, scores, "
                      f"variables, places and features equal across explain.json, twins.json and the binary files")

    def span(xs, d=0):
        lo, hi = min(xs), max(xs)
        f = (lambda x: f"{x:.{d}f}")
        return f(lo) if f(lo) == f(hi) else f"{f(lo)} to {f(hi)}"
    ratio = {m: [p["cell_area_km2"]["earth_over_moon"] for p in out_missions[m]["pairs"]] for m in MISSIONS}
    lb_w = [p["cell_area_km2"]["moon_east_west_km"] for p in out_missions["lunar_base"]["pairs"]]
    cell_caveat = (f"East-west a cell narrows towards the poles: the lunar twin of a Lunar base pair is only {span(lb_w, 1)} km "
                   f"wide east-west (30 km north-south), so each Earth cell averages {span(ratio['lunar_base'])} times more "
                   f"ground than its twin ({span(ratio['solar'])} times for Solar panels, {span(ratio['rover'])} for Rover); "
                   f"see cell_area_km2 in each pair.")
    return {
        "generated_on": GENERATED_ON,
        "generated_by": SCRIPT_REL,
        "bundle": "app/public/data/v2",
        "contract_revision": man["contract_revision"],
        "engine_version": man["engine_version"],
        "dataset": man["dataset"]["id"],
        "similarity_rules": man["similarity_rules"],
        "how_to_read": {
            "similarity": "How alike the Earth point and its lunar twin are, 0 to 100, from the mission's variables compared within stated tolerances.",
            "suitability": "How well the Earth point meets the mission's own needs as a test site, 0 to 100, from its weighted criteria.",
            "final": "The ranking score: half similarity and half suitability (alpha 0.5).",
            "rules": "Rover and Solar panels pair on real values within tolerances; Lunar base pairs on thermal position (coldest temperature and daily swing ranked within each world's own population) plus slope and roughness in real values.",
            "levels": "MEASURED = from a named measured product; DERIVED = a stated formula on measured values; MODELLED = a model or climatology, not a measurement of the cell (variables.json).",
            "percentile_words": "Words such as gentle, smooth, coldest are used only when both sides fall in the same quarter (or tenth) of their own population; the population is named in each trait's basis.",
        },
        "status": {m: out_missions[m]["status"] for m in MISSIONS},
        "caveats": [
            "Each place is a 1-degree cell, about 111 km north-south on Earth (about 30 km on the Moon); values are cell averages.",
            cell_caveat,
            "Earth coldest air temperature and ground sunlight are modelled climatologies (WorldClim); the daily temperature swing is derived from MODIS land-surface temperature (daytime minus night-time overpass); none of them is a site measurement.",
            "Names are the nearest named feature or populated place to the cell centre, not a landing site or the cell's own name.",
            "Lunar base pairs are a likeness of thermal position within each world's population, not of temperature: the real temperatures are about 200 K apart.",
            "Sunlight above the atmosphere is alike for Solar panels pairs, but on Earth a large share is lost in the atmosphere; panels would not charge the same.",
        ],
        "missions": out_missions,
        "checks": CHECKS,
    }


def shared_twin_note(mid: str, pairs: List[Dict[str, Any]]) -> Optional[str]:
    """One plain sentence when two or more of the top pairs share a lunar twin (counts from the data)."""
    from collections import Counter
    cnt = Counter(p["moon_cell_id"] for p in pairs)
    groups = [(c, [p for p in pairs if p["moon_cell_id"] == m]) for m, c in cnt.items() if c >= 2]
    if not groups:
        return None
    words = {2: "two", 3: "three", 4: "four", 5: "five"}
    bits = []
    for c, ps in groups:
        feat = ps[0]["moon_place"]["nearest_named_feature"]
        ranks = ", ".join(str(p["rank"]) for p in ps)
        whole = "All " + words[c] + " of the" if c == len(pairs) else f"{words[c].capitalize()} of the {words[len(pairs)]}"
        bits.append(f"{whole} {'top ' + words[len(pairs)] + ' ' if c == len(pairs) else ''}pairs "
                    f"{'' if c == len(pairs) else '(numbers ' + ranks + ') '}share the same lunar twin, "
                    f"the spot near {feat}, so the Moon side is the same place each time.")
    return " ".join(bits)


# ----------------------------------------------------------------------------- traits
def band(p_e: float, p_m: float, low_word: str, high_word: str) -> Optional[Tuple[str, str]]:
    hi = max(p_e, p_m)
    lo = min(p_e, p_m)
    if hi <= 10:
        return low_word, "tenth"
    if hi <= 25:
        return low_word, "quarter"
    if lo >= 90:
        return high_word, "tenth"
    if lo >= 75:
        return high_word, "quarter"
    return None


def terrain_trait(name: str, ev: float, mv: float, dv: float, unit_say: str, d: int, k: int, mcell: int,
                  pop: Dict, pop_text: Dict, low_word: str, high_word: str, label: str, col: str) -> Dict[str, Any]:
    key = "slope" if name == "slope_deg" else "rough"
    pe = mid_rank_pct(pop[key]["EARTH"], pop[key]["EARTH"][k])
    pm = mid_rank_pct(pop[key]["MOON"], pop[key]["MOON"][mcell])
    bd = band(pe, pm, low_word, high_word)
    num = f"{ev:.{d}f} {unit_say} on Earth and {mv:.{d}f} on the Moon, {dv:.{d}f} apart"
    if bd:
        word, part = bd
        which = "lowest" if word == low_word else "highest"
        text = (f"Both are {word}: {label} of {num}; each lies in the {which} {part} of its own world "
                f"({ordinal(max(1, int(round(pe))))} percentile on Earth, {ordinal(max(1, int(round(pm))))} on the Moon).")
    else:
        text = f"Similar {label}: {num}."
    return {"text": text,
            "basis": {"columns": [f"{col} (Earth)", f"{col} (Moon)", "earth_base.bin v." + ("slope_iso_deg" if key == "slope" else "roughness_m"),
                                  "moon_base.bin v." + ("slope_iso_deg" if key == "slope" else "roughness_m")],
                      "earth": ev, "moon": mv, "difference": dv,
                      "earth_percentile_in_population": round(pe, 1), "moon_percentile_in_population": round(pm, 1),
                      "populations": pop_text, "word_rule": f"'{low_word}' if both <= 25th percentile, '{high_word}' if both >= 75th, else no word"}}


def traits(mid: str, pair: Dict, k: int, mcell: int, pop: Dict, pop_text: Dict) -> List[Dict[str, Any]]:
    V = {v["variable"]: v for v in pair["variables"]}
    out = []
    if mid in ("rover", "solar"):
        if mid == "solar":
            s = V["irradiance_toa_kwh_m2_day"]
            a = pair["earth_atmosphere"]["display"]
            out.append({"text": (f"Nearly the same sunlight above the atmosphere: {s['earth']:.2f} kWh per square metre per day at the Earth site "
                                 f"and {s['moon']:.2f} on the Moon ({('less than 0.01' if s['difference'] < 0.01 else format(s['difference'], '.2f'))} apart). On Earth only about {a['ground_kwh_m2_day']:.1f} "
                                 f"of {a['above_atmosphere_kwh_m2_day']:.1f} reaches the ground, about {a['lost_percent']} percent being lost in the atmosphere; "
                                 f"the Moon has no atmosphere, so this is a likeness of sunlight above the air, not of what panels would collect."),
                        "basis": {"columns": ["irradiance_toa_kwh_m2_day.earth", "irradiance_toa_kwh_m2_day.moon",
                                              "irradiance_toa_kwh_m2_day.diff", "atm.ground_kwh_m2_day", "atm.toa_kwh_m2_day"],
                                  "earth": s["earth"], "moon": s["moon"], "difference": s["difference"],
                                  "ground": pair["earth_atmosphere"]["ground_kwh_m2_day"],
                                  "lost_percent_display": a["lost_percent"]}})
        sl, ro = V["slope_deg"], V["roughness_m"]
        out.append(terrain_trait("slope_deg", sl["earth"], sl["moon"], sl["difference"], "degrees", 2, k, mcell, pop, pop_text,
                                 "gentle", "steep", "slopes", "slope_deg"))
        out.append(terrain_trait("roughness_m", ro["earth"], ro["moon"], ro["difference"], "metres", 1, k, mcell, pop, pop_text,
                                 "smooth", "rugged", "roughness", "roughness_m"))
        if mid == "rover":
            e = V["elevation_rel_m"]
            if e["difference"] <= e["tolerance"]:
                def hs(x):
                    return f"{abs(round(x, -1)):,.0f} metres {'above' if x >= 0 else 'below'}"
                out.append({"text": (f"Similar height relative to each world's mean level: {hs(e['earth'])} Earth's mean and "
                                     f"{hs(e['moon'])} the Moon's, {round(e['difference']):,.0f} metres apart."),
                            "basis": {"columns": ["elevation_rel_m.earth", "elevation_rel_m.moon", "elevation_rel_m.diff"],
                                      "earth": e["earth"], "moon": e["moon"], "difference": e["difference"],
                                      "note": "elevation minus the body's area-weighted mean elevation (Earth 695.9244 m, Moon -248.3894 m)"}})
            out = out[:3]
    else:
        tm, am = V["tmin_k"], V["lst_diurnal_amp_k"]
        pe, pm = tm["earth_percentile"], tm["moon_percentile"]
        bd = band(pe, pm, "coldest", "least cold")
        lead = (f"Both rank in the {bd[0]} {bd[1]} of their own population" if bd else
                f"A similar cold position within their own population")
        out.append({"text": (f"{lead} by coldest temperature ({ordinal(max(1, int(round(pe))))} percentile on Earth, "
                             f"{ordinal(max(1, int(round(pm))))} on the Moon, {tm['difference_points']:.1f} points apart), "
                             f"although the temperatures themselves are far apart: about {tm['earth_real_c']:.0f} degrees C "
                             f"air on Earth against {tm['moon_real_c']:.0f} degrees C surface on the Moon, {tm['difference_real']:.0f} K."),
                    "basis": {"columns": ["tmin_k.earth_pct", "tmin_k.moon_pct", "tmin_k.diff_pct", "tmin_k.earth", "tmin_k.moon", "tmin_k.diff"],
                              "earth_percentile": pe, "moon_percentile": pm, "difference_points": tm["difference_points"],
                              "earth_k": tm["earth_real"], "moon_k": tm["moon_real"], "difference_k": tm["difference_real"],
                              "populations": {"EARTH": f"{tm['population_earth']:,} Earth points passing the Lunar base funnel",
                                              "MOON": f"{tm['population_moon']} lunar cells overlapping NASA's nine candidate regions"},
                              "percentile_direction": "low percentile = colder"}})
        pe, pm = am["earth_percentile"], am["moon_percentile"]
        bd = band(pe, pm, "smallest", "largest")
        lead = (f"Both have one of the {bd[0]} daily temperature swings of their own population (the {bd[0]} {bd[1]})" if bd else
                "A similar position for the daily temperature swing within their own population")
        out.append({"text": (f"{lead}: {ordinal(max(1, int(round(pe))))} percentile on Earth, {ordinal(max(1, int(round(pm))))} on the Moon, "
                             f"{am['difference_points']:.1f} points apart; in real terms the swing is {am['earth_real']:.0f} K on Earth "
                             f"and {am['moon_real']:.0f} K on the Moon, {am['difference_real']:.0f} K apart."),
                    "basis": {"columns": ["lst_diurnal_amp_k.earth_pct", "lst_diurnal_amp_k.moon_pct", "lst_diurnal_amp_k.diff_pct",
                                          "lst_diurnal_amp_k.earth", "lst_diurnal_amp_k.moon", "lst_diurnal_amp_k.diff"],
                              "earth_percentile": pe, "moon_percentile": pm, "difference_points": am["difference_points"],
                              "earth_k": am["earth_real"], "moon_k": am["moon_real"], "difference_k": am["difference_real"],
                              "percentile_direction": "low percentile = smaller swing"}})
        sl, ro = V["slope_deg"], V["roughness_m"]
        t_s = terrain_trait("slope_deg", sl["earth_real"], sl["moon_real"], sl["difference_real"], "degrees", 1, k, mcell, pop, pop_text,
                            "gentle", "steep", "slopes", "slope_deg")
        t_r = terrain_trait("roughness_m", ro["earth_real"], ro["moon_real"], ro["difference_real"], "metres", 0, k, mcell, pop, pop_text,
                            "smooth", "rugged", "roughness", "roughness_m")
        out.append({"text": (f"Similar terrain: slope {sl['earth_real']:.1f} against {sl['moon_real']:.1f} degrees "
                             f"({sl['difference_real']:.1f} apart) and roughness {ro['earth_real']:.0f} against {ro['moon_real']:.0f} metres "
                             f"({ro['difference_real']:.1f} apart)."
                             + terrain_words(t_s, "slope") + terrain_words(t_r, "roughness")),
                    "basis": {"columns": ["slope_deg.earth", "slope_deg.moon", "slope_deg.diff",
                                          "roughness_m.earth", "roughness_m.moon", "roughness_m.diff"],
                              "slope": t_s["basis"], "roughness": t_r["basis"]}})
    return out


def terrain_words(t: Dict, what: str) -> str:
    """The qualitative word of a terrain trait with its percentiles, or nothing."""
    if not t["text"].startswith("Both are"):
        return ""
    word = t["text"][len("Both are "):].split(":")[0]
    bb = t["basis"]
    return (f" By {what} both are {word}: {ordinal(max(1, int(round(bb['earth_percentile_in_population']))))} percentile of "
            f"Earth land cells, {ordinal(max(1, int(round(bb['moon_percentile_in_population']))))} of lunar cells.")


# ----------------------------------------------------------------------------- say
def spoken_diff(x: float, d: int, unit: str) -> str:
    """A difference as spoken at d decimals; never read as zero when it is not zero:
    'less than 1 metre' / 'less than 0.1 degrees' when the rounded value would be 0."""
    if round(abs(x), d) == 0 and x != 0:
        step = 10 ** (-d)
        one = f"{step:.{d}f}"
        return f"less than {one} {unit if step != 1 else UNIT_SINGULAR.get(unit, unit)}"
    return f"{abs(x):.{d}f} {unit}"


UNIT_SINGULAR = {"metres": "metre", "degrees": "degree", "kelvin": "kelvin", "kilometres": "kilometre"}


NTH = {1: "Number one", 2: "Number two", 3: "Number three", 4: "Number four", 5: "Number five"}
SAY_MISSION = {"rover": "for the rover", "solar": "for solar panels", "lunar_base": "for a lunar base"}


def feature_phrase(name: str, ftype: str) -> str:
    t = ftype.split(",")[0].strip().lower()
    if t == "crater":
        return f"the crater {name}"
    if t.capitalize() in name.split():  # Mons Malapert, Mare ...
        return name
    return f"{name}, a {t}"


def say(mid: str, mj: Dict, pair: Dict) -> str:
    ep, mp = pair["earth_place"], pair["moon_place"]
    where = ", ".join(x for x in (ep["region"], ep["country"]) if x)
    km = ep["distance_km_spoken"]
    earth = f"a site about {km} kilometres {ep['direction_from_place']} of {ep['nearest_named_place']}, in {where}"
    mkm = mp["distance_km_spoken"]
    moon = f"a spot about {mkm} kilometres from {feature_phrase(mp['nearest_named_feature'], mp['feature_type'])}"
    V = {v["variable"]: v for v in pair["variables"]}
    sim = f"{pair['similarity']:.1f}"
    if sim == "100.0":
        sim = f"{pair['similarity']:.2f}"
    if pair["similarity"] >= 100.0:
        sim = "100 (rounded)"
    head = f"{NTH[pair['rank']]} {SAY_MISSION[mid]}: {earth}, pairs with {moon}"
    if mid == "rover":
        sl, ro = V["slope_deg"], V["roughness_m"]
        return (f"{head}, in the lunar south-polar region. The Earth site has a slope of {sl['earth']:.1f} degrees and a roughness of "
                f"{ro['earth']:.0f} metres, the Moon spot {sl['moon']:.1f} degrees and {ro['moon']:.0f} metres; similarity {sim} out of 100.")
    if mid == "solar":
        s = V["irradiance_toa_kwh_m2_day"]
        a = pair["earth_atmosphere"]["display"]
        return (f"{head}, on the lunar equatorial plains. Above the atmosphere both get about {s['earth']:.1f} kilowatt hours "
                f"per square metre a day, but on Earth about {a['lost_percent']} percent is lost in the air and only "
                f"{a['ground_kwh_m2_day']:.1f} reach the ground; similarity {sim} out of 100.")
    tm, am = V["tmin_k"], V["lst_diurnal_amp_k"]
    return (f"{head}, {mp['nasa_candidate_region_wording']}, near the lunar south pole. They are not equally cold, the Moon spot's coldest temperature is about "
            f"{spoken_diff(tm['difference_real'], 0, 'kelvin')} lower and its daily swing {spoken_diff(am['difference_real'], 0, 'kelvin')} larger, but each holds "
            f"a similar place in its own world's range of cold and swing, and slopes differ by {spoken_diff(V['slope_deg']['difference_real'], 1, 'degrees')} "
            f"and roughness by {spoken_diff(V['roughness_m']['difference_real'], 0, 'metres')}; similarity {sim} out of 100.")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--bundle", default=BUNDLE)
    ap.add_argument("--out", default=OUT)
    a = ap.parse_args(argv)
    data = build(a.bundle)
    with open(a.out, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=1)
        fh.write("\n")
    for c in CHECKS:
        print("CHECK ok:", c)
    for m in MISSIONS:
        for p in data["missions"][m]["pairs"]:
            print(m, p["rank"], p["earth_cell_id"], p["moon_cell_id"], "|", p["say"])
    print("wrote", a.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
