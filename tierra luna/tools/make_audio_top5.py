"""Facts and texts of the audio guide: the five analogs shown for each mission.

Reads the shipped static bundle (app/public/data/v2, docs/DATA_CONTRACT.md revision 8)
and writes:

* docs/AUDIO_TOP5.json: per mission (rover, solar, lunar_base) the five analogs the web
  shows (missions.json ``top5.ids``, in that order, numbered 1 to 5, each with its rank
  in the full ranking), the rule by which they were chosen (recomputed here), the Earth
  place, the lunar twin, the scores, the variables on both sides with the values the
  screen prints, 2 or 3 common traits backed by figures, and the text of each of the 19
  audio tracks with the check of every figure in it;
* app/public/audio/transcripts.json: the TEXT of the 19 tracks (same keys; the audio
  files themselves are never touched);
* app/public/audio/pending.json: the tracks whose text changed (the team re-records them);
* docs/AUDIO_RERECORD.md: for the team (Spanish): old text, new text and reason per track,
  the table of the five of each mission, the list of files to record.

Deterministic: no clock, no network, no randomness. Run from anywhere:

    python "tierra luna/tools/make_audio_top5.py" [--bundle DIR] [--out FILE] [--no-app-files]

Two code paths: every number is taken from explain.json / twins.json / missions.json (the
bundle's published values) and checked against the binary columns (earth_<m>.bin,
earth_<m>_pairs.bin, earth_base.bin, earth_place_detail.bin, moon_base.bin), the rule of
the five is re-run here from the binary columns and the Earth table (snow_ice_frac), the
clear-sky fraction is checked against the supplementary table it was read from, place
names against the dataset they are attributed to, and distances are recomputed. Every
number in every track text must be one the screen prints for that track (the display
rules of app/src/flow/dom.ts and engine/display.py, written out here), or a distance
rounded once from the stored value. The script stops with an AssertionError on any
mismatch.

Sources outside the bundle (read only):
* GeoNames cities1000 as shipped in the reverse_geocoder package (rg_cities1000.csv),
  the populated places the engine uses (tierra luna/engine/places.py): the coordinates
  and country of the nearest place the bundle names, for the compass direction;
* tierra luna/engine/data/artemis_iii_regions.geojson and iau_moon_nomenclature.csv:
  second path for the Lunar base region phrase and the feature names;
* tierra luna/output_real/earth_real_1deg.csv: snow_ice_frac (the ice skip of the rule of
  the five; not in the bundle);
* tierra luna/real_data/supplement/earth_cloud_isccp_1deg.csv and its provenance file:
  second path for the clear-sky fraction;
* git: the text of the tracks as recorded (commit OLD_TEXTS_COMMIT), for
  docs/AUDIO_RERECORD.md and pending.json.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import os
import re
import subprocess
import sys
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
BUNDLE = os.path.join(REPO, "app", "public", "data", "v2")
OUT = os.path.join(REPO, "docs", "AUDIO_TOP5.json")
AUDIO_DIR = os.path.join(REPO, "app", "public", "audio")
RERECORD_MD = os.path.join(REPO, "docs", "AUDIO_RERECORD.md")
ENGINE_DATA = os.path.join(REPO, "tierra luna", "engine", "data")
EARTH_TABLE = os.path.join(REPO, "tierra luna", "output_real", "earth_real_1deg.csv")
CLOUD_TABLE = os.path.join(REPO, "tierra luna", "real_data", "supplement", "earth_cloud_isccp_1deg.csv")
CLOUD_PROV = os.path.join(REPO, "tierra luna", "real_data", "supplement", "provenance_earth_cloud_isccp.csv")
sys.path.insert(0, os.path.join(REPO, "tierra luna"))
from engine.display import SHARE_LOST_PYTHON, displayed, share_lost_percent, tenths, to_fixed  # noqa: E402  (one display rule with the engine)

SCRIPT_REL = "tierra luna/tools/make_audio_top5.py"
GENERATED_ON = "2026-11-15"
CONTRACT_REVISION = 8
OLD_TEXTS_COMMIT = "d24ebb3"   # the commit whose transcripts.json is the text of the recorded MP3s
MISSIONS = ["rover", "solar", "lunar_base"]
TOP = 5
NEAREST_PLACE_MAX_KM_ON_SCREEN = 300   # app/src/flow/detailPanel.ts NEAREST_PLACE_MAX_KM
NEAR_MAX_KM = 50                       # team lead's rule 2: "near" only under 50 km
WORDS_MIN, WORDS_MAX = 55, 105         # team lead's rule 8
TRACK_ORDER = ["00_welcome", "m1_rover", "m2_solar", "m3_base"] + [f"rover_{i}" for i in range(1, 6)] + \
              [f"solar_{i}" for i in range(1, 6)] + [f"base_{i}" for i in range(1, 6)]
TRACK_PREFIX = {"rover": "rover", "solar": "solar", "lunar_base": "base"}
FORBIDDEN = ["the five best", "the best", "charge the same", "equally cold", "plain"]

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
        """Decoded column (float64, NaN = missing; quantised columns divided). A float32
        column is returned as the double of each float32, as a Float32Array gives it."""
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


# ----------------------------------------------------------------------------- geometry
def great_circle_km(lat1, lon1, lat2, lon2, r):
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dl = math.radians(lon2 - lon1)
    c = math.sin(p1) * math.sin(p2) + math.cos(p1) * math.cos(p2) * math.cos(dl)
    return r * math.acos(max(-1.0, min(1.0, c)))


def central_angle_deg(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Own haversine (second path to engine/top5.py)."""
    p1, p2 = math.radians(lat1), math.radians(lat2)
    a = math.sin((p2 - p1) / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(math.radians(lon2 - lon1) / 2) ** 2
    return math.degrees(2 * math.asin(math.sqrt(min(1.0, max(0.0, a)))))


def cell_latlon(cid: int, cols: int = 360) -> Tuple[float, float]:
    r, c = divmod(int(cid), cols)
    return 90 - (r + 0.5), -180 + (c + 0.5)


def spoken_km(raw: float) -> int:
    """A distance as spoken: rounded ONCE to the unit, half up, from the stored float32
    (engine/display.py displayed), never from a 1-decimal copy."""
    return int(displayed(raw, 0))


def cell_area_km2(lat_centre: float, r: float, deg: float = 1.0) -> float:
    a, b = math.radians(lat_centre - deg / 2), math.radians(lat_centre + deg / 2)
    return r * r * math.radians(deg) * abs(math.sin(b) - math.sin(a))


def cell_east_west_km(lat_centre: float, r: float, deg: float = 1.0) -> float:
    return 2 * math.pi * r * deg / 360.0 * math.cos(math.radians(lat_centre))


def project_geom(g, r: float, step_deg: float = 0.01):
    """A lon/lat shapely geometry densified to step_deg and projected (south-polar Lambert
    azimuthal equal area on the sphere of radius r: rho = 2 r sin(c / 2))."""
    import shapely

    def fwd(c):
        lon, lat = c[:, 0], c[:, 1]
        rho = 2.0 * r * np.sin(np.radians(90.0 + lat) / 2.0)
        return np.column_stack([rho * np.sin(np.radians(lon)), rho * np.cos(np.radians(lon))])
    return shapely.transform(shapely.segmentize(g, step_deg), fwd)


def region_share_of_cell(lat: float, lon: float, region_geom, r: float) -> float:
    from shapely.geometry import box
    cell = project_geom(box(lon - 0.5, lat - 0.5, lon + 0.5, lat + 0.5), r)
    return float(cell.intersection(project_geom(region_geom, r)).area / cell.area)


def bearing_deg(lat1, lon1, lat2, lon2) -> float:
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dl = math.radians(lon2 - lon1)
    y = math.sin(dl) * math.cos(p2)
    x = math.cos(p1) * math.sin(p2) - math.sin(p1) * math.cos(p2) * math.cos(dl)
    return (math.degrees(math.atan2(y, x)) + 360.0) % 360.0


COMPASS = ["north", "northeast", "east", "southeast", "south", "southwest", "west", "northwest"]


def compass(b: float) -> str:
    return COMPASS[int((b + 22.5) // 45) % 8]


# ----------------------------------------------------------------------------- display rules
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


def strip0(s: str) -> str:
    return s.rstrip("0").rstrip(".") if "." in s else s


def screen_num(v: float, d: int) -> str:
    """app/src/flow/dom.ts num(v, d): Number(v.toFixed(d)) with trailing zeros dropped
    (thousands separators are not written here)."""
    s = strip0(to_fixed(float(v), d))
    return "0" if s in ("-0", "") else s


def screen_value(v: float, unit: str) -> str:
    """app/src/flow/dom.ts valueText(v, unit) without the unit: percentile points with 1
    fixed decimal; a fraction 0-1 with up to 3; otherwise up to 1 decimal from 100, 2 from
    10, 3 below 10 (trailing zeros dropped)."""
    if unit == "percentile points":
        return to_fixed(float(v), 1)
    if unit == "fraction 0-1":
        return screen_num(v, 3)
    a = abs(v)
    return screen_num(v, 1 if a >= 100 else 2 if a >= 10 else 3)


def screen_score(v: float) -> str:
    """dom.ts fixed(v, 2): scores (similarity, suitability, final)."""
    return to_fixed(float(v), 2)


def sentence_tenth(raw: float) -> str:
    """engine/display.py displayed(raw, 1): the 1-decimal numbers of the per-pair sentences."""
    return format(displayed(raw, 1), "f")


def with_commas(n: int) -> str:
    return f"{int(n):,}"


def mid_rank_pct(values: np.ndarray, x: float) -> float:
    v = values[~np.isnan(values)]
    below = float(np.sum(v < x))
    equal = float(np.sum(v == x))
    rank = below + (equal + 1.0) / 2.0 if equal else below + 0.5
    return 100.0 * (rank - 0.5) / len(v)


def ordinal(n: int) -> str:
    if 10 <= n % 100 <= 20:
        return f"{n}th"
    return f"{n}{ {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th') }"


# ----------------------------------------------------------------------------- level lookup
def level_table(variables_json: Dict) -> Dict[Tuple[str, str], str]:
    out = {}
    for v in variables_json["variables"]:
        for body, b in v["bodies"].items():
            out[(v["name"], body)] = b["level"]
    return out


def side_level(sim_var: Dict, body: str, levels: Dict) -> Dict[str, Optional[str]]:
    side = sim_var["sides"][body]
    name = sim_var["variable"]
    if (name, body) in levels:
        return {"level": levels[(name, body)], "from": f"variables.json {name} {body}"}
    col = side.get("column")
    if col and (col, body) in levels:
        return {"level": levels[(col, body)], "from": f"variables.json {col} {body}"}
    return {"level": side["level"], "from": f"missions.json similarity.variables[{name}].sides.{body}.level"}


def moon_tmin_level(sim_var: Dict) -> Dict[str, Any]:
    prov = os.path.join(REPO, "tierra luna", "real_data", "provenance_moon.csv")
    with open(prov, encoding="utf-8") as fh:
        row = next(r for r in csv.reader(fh) if r[:2] == ["tmin_k", "MOON"])
    check(row[2] == "MEASURED", f"provenance_moon.csv tmin_k MOON is {row[2]}")
    check("MEASURED" in sim_var["sides"]["MOON"]["level"], "missions.json lunar tmin_k side level")
    return {"level": "MEASURED", "from": "tierra luna/real_data/provenance_moon.csv tmin_k MOON (Diviner GCP, tbol)",
            "note": f"missions.json: {sim_var['sides']['MOON']['text']}. variables.json lists the table column tmin_c as "
                    f"DERIVED only because it is this measured value converted to degrees C."}


# ----------------------------------------------------------------------------- rule of the five (second path)
def recompute_five(mid: str, top5: Dict, rank: np.ndarray, final: np.ndarray, ids: np.ndarray,
                   s_cols: List[np.ndarray], weights: List[float], mask: Dict[int, float],
                   ice: Dict[int, float]) -> Dict[str, Any]:
    """Re-run the published rule of the five from the binary columns with own code:
    rank_with_skips (down the ranking, skip ice / water / within the separation) and, for
    spread_within_top_tie, the farthest-point spread among the tied points after skips."""
    sk = top5["skips"]
    check(sk["ice"]["column"] == "snow_ice_frac" and sk["ice"]["op"] == ">=" and sk["water"]["column"] == "mask_fraction"
          and sk["water"]["op"] == "<", f"{mid}: skips are not the documented ones")
    ice_v, water_v = float(sk["ice"]["value"]), float(sk["water"]["value"])

    def skip_reason(eid: int) -> Optional[str]:
        out = []
        if sk["ice"]["enabled"] and not math.isnan(ice.get(eid, math.nan)) and ice[eid] >= ice_v:
            out.append(f"ice: snow_ice_frac {ice[eid]:.3f} >= {ice_v}")
        if sk["water"]["enabled"] and not math.isnan(mask.get(eid, math.nan)) and mask[eid] < water_v:
            out.append(f"water: mask_fraction {mask[eid]:.3f} < {water_v}")
        return "; ".join(out) or None

    sep = float(top5["min_separation_deg"])
    ranked = np.flatnonzero(~np.isnan(rank))
    ranked = ranked[np.argsort(rank[ranked], kind="mergesort")]
    res: Dict[str, Any] = {"rule_id": top5["rule_id"]}
    best_final = float(np.nanmax(final))
    tied = [int(p) for p in ranked if final[p] == best_final]
    tied_kept = [p for p in tied if skip_reason(int(ids[p])) is None]
    res["top_tie_n_recomputed"] = len(tied)
    res["top_tie_n_after_skips_recomputed"] = len(tied_kept)
    res["top_final"] = screen_score(best_final)
    check(len(tied) == top5["top_tie_n"], f"{mid}: tied {len(tied)} != bundle {top5['top_tie_n']}")
    check(len(tied_kept) == top5["top_tie_n_after_skips"], f"{mid}: tied after skips {len(tied_kept)} != bundle")
    if top5["rule_id"] == "spread_within_top_tie" and len(tied_kept) > TOP:
        # start: the tied point with the highest similarity at full precision (from the 6-decimal
        # scores s.<v> with the published weights), ties to the lowest id
        sim_full = {p: 100.0 * sum(w * s[p] for w, s in zip(weights, s_cols)) / sum(weights) for p in tied_kept}
        start = min(tied_kept, key=lambda p: (-sim_full[p], int(ids[p])))
        chosen = [start]
        ll = {p: cell_latlon(int(ids[p])) for p in tied_kept}
        while len(chosen) < TOP:
            def mind(p):
                return min(central_angle_deg(*ll[p], *ll[c]) for c in chosen)
            nxt = max((p for p in tied_kept if p not in chosen), key=lambda p: (mind(p), -int(ids[p])))
            chosen.append(nxt)
        res["chosen_ids"] = [int(ids[p]) for p in chosen]
        res["start_rule"] = "the tied site with the highest similarity at full precision (s columns, published weights), ties lowest id"
        res["min_angle_between_chosen_deg"] = round(min(central_angle_deg(*ll[a], *ll[b]) for i, a in enumerate(chosen)
                                                         for b in chosen[i + 1:]), 2)
        res["tied_ice_or_water_left_out"] = [{"id": f"E{int(ids[p])}", "rank": int(rank[p]), "why": skip_reason(int(ids[p]))}
                                             for p in tied if skip_reason(int(ids[p])) is not None]
        # the alternative rule as well (rank_with_skips), to compare with top5.alternative
    kept, skipped = [], []
    for p in ranked:
        eid = int(ids[p])
        why = skip_reason(eid)
        if why is None and kept:
            close = [(int(ids[k]), central_angle_deg(*cell_latlon(eid), *cell_latlon(int(ids[k])))) for k in kept]
            close = [c for c in close if c[1] < sep]
            if close:
                why = f"within {sep:g} degrees of arc of E{close[0][0]} ({close[0][1]:.2f} degrees)"
        if why:
            skipped.append({"rank": int(rank[p]), "id": f"E{eid}", "final": screen_score(final[p]), "why": why})
            continue
        kept.append(p)
        if len(kept) == TOP:
            break
    rws = [int(ids[p]) for p in kept]
    if top5["rule_id"] == "rank_with_skips":
        res["chosen_ids"] = rws
        res["skipped_before_the_fifth"] = skipped
        res["highest_scoring_the_rule_allows"] = True
        res["finding"] = (f"The five are ranks {', '.join(str(int(rank[p])) for p in kept)} of the full ranking; every rank "
                          f"above the fifth that is not among them is skipped by the rule ("
                          + "; ".join(f"rank {s['rank']}: {s['why']}" for s in skipped) +
                          "), so they are the highest-scoring five that the rule of the five allows.")
    else:
        res["alternative_rank_with_skips_ids"] = rws
        check(rws == list(top5["alternative"]["ids"]), f"{mid}: alternative rule recomputed {rws} != bundle")
        res["highest_scoring_the_rule_allows"] = None
        res["finding"] = (f"{len(tied)} ranked sites share the top published final score {screen_score(best_final)}; "
                          f"{len(tied_kept)} remain after the ice and water skips. The five are a farthest-point spread "
                          f"among those {len(tied_kept)} (they all have the top score, so 'five of the highest-scoring' is "
                          f"not the wording: 'five of the {len(tied)} sites tied at the top of our model', as the bundle's "
                          f"list_order_rover text says; all five are also among the {len(tied_kept)} left after the skips).")
    check(res["chosen_ids"] == list(top5["ids"]), f"{mid}: rule of the five recomputed {res['chosen_ids']} != bundle {top5['ids']}")
    return res


# ----------------------------------------------------------------------------- words
TYPE_WORDS = {"crater": "the crater {n}", "mons": "{n}", "rima": "{n}, a lunar rille", "catena": "{n}, a chain of craters",
              "mare": "{n}", "lacus": "{n}", "vallis": "{n}, a lunar valley", "dorsum": "{n}, a lunar ridge",
              "promontorium": "{n}", "rupes": "{n}, a lunar scarp", "planitia": "{n}"}
NUM_WORD = {1: "one", 2: "two", 3: "three", 4: "four", 5: "five"}
MISSION_TITLE = {"rover": "Rover", "solar": "Solar panels", "lunar_base": "Lunar base"}


def feature_phrase(name: str, ftype: str) -> str:
    t = ftype.split(",")[0].strip().lower()
    return TYPE_WORDS.get(t, "{n}").format(n=name)


def clear_words(f: float) -> str:
    """A plain fraction close to the clear-sky fraction (checked within 0.015)."""
    opts = [(0.5, "half"), (0.6, "three fifths"), (2 / 3, "two thirds"), (0.7, "seven tenths"),
            (0.75, "three quarters"), (0.8, "four fifths")]
    v, w = min(opts, key=lambda o: abs(o[0] - f))
    check(abs(v - f) <= 0.015, f"no plain fraction within 0.015 of {f}")
    return w


# ----------------------------------------------------------------------------- main build
def build(bundle_path: str) -> Dict[str, Any]:
    b = Bundle(bundle_path)
    man = b.manifest
    check(man["contract_revision"] == CONTRACT_REVISION, f"expected contract revision {CONTRACT_REVISION}")
    missions_json = b.json("missions.json")
    mission_by_id = {m["id"]: m for m in missions_json["missions"]}
    explain = b.json("explain.json")
    twins = b.json("twins.json")
    places = b.json("places.json")
    pdetail = b.json("place_detail.json")
    iau = b.json("iau_moon_features.json")
    zones = b.json("mission_zones.json")
    sim_texts = b.json("similarity.json")["texts"]
    variables_json = b.json("variables.json")
    levels = level_table(variables_json)
    grid = man["grid"]
    R_E = grid["bodies"]["EARTH"]["radius_km"]
    R_M = grid["bodies"]["MOON"]["radius_km"]
    cols = grid["cols"]

    land_ids = b.col("earth_base.bin", "id").astype(np.int64)
    land_pos = {int(i): k for k, i in enumerate(land_ids)}
    e_country = b.col("earth_base.bin", "country")
    e_region = b.col("earth_base.bin", "region")
    e_slope = b.col("earth_base.bin", "v.slope_iso_deg")
    e_rough = b.col("earth_base.bin", "v.roughness_m")
    e_tmin = b.col("earth_base.bin", "v.tmin_c")
    e_ground = b.col("earth_base.bin", "v.irradiance_kwh_m2_day")
    e_mask = b.col("earth_base.bin", "v.mask_fraction")
    e_clear = b.col("earth_base.bin", "v.clear_frac_isccp")
    np_idx = b.col("earth_place_detail.bin", "nearest_place")
    np_km = b.col("earth_place_detail.bin", "nearest_place_km")
    lr_idx = b.col("earth_place_detail.bin", "label_rule")
    m_slope = b.col("moon_base.bin", "v.slope_iso_deg")
    m_rough = b.col("moon_base.bin", "v.roughness_m")
    m_feat = b.col("moon_base.bin", "feature")
    m_feat_km = b.col("moon_base.bin", "feature_km")
    m_region = b.col("moon_base.bin", "region")
    m_irr = b.col("moon_base.bin", "v.irradiance_kwh_m2_day")
    m_tmin = b.col("moon_base.bin", "v.tmin_c")
    mask_by_id = {int(i): float(e_mask[k]) for k, i in enumerate(land_ids)}

    # Earth table: snow_ice_frac (ice skip of the rule of the five) and a third check of mask_fraction
    et = pd.read_csv(EARTH_TABLE, usecols=["cell_id", "mask_fraction", "snow_ice_frac"])
    et_id = et["cell_id"].str[1:].astype(int).values
    ice_by_id = dict(zip(et_id.tolist(), et["snow_ice_frac"].astype(float).tolist()))
    tbl_mask = dict(zip(et_id.tolist(), et["mask_fraction"].astype(float).tolist()))

    # clear-sky fraction: supplementary table (second path) and its provenance
    ct = pd.read_csv(CLOUD_TABLE, usecols=["cell_id", "clear_frac_isccp", "n_months_isccp"])
    clear_tbl = dict(zip(ct["cell_id"].str[1:].astype(int).tolist(), ct["clear_frac_isccp"].astype(float).tolist()))
    clear_months = dict(zip(ct["cell_id"].str[1:].astype(int).tolist(), ct["n_months_isccp"].tolist()))
    with open(CLOUD_PROV, encoding="utf-8") as fh:
        prov_rows = {r["variable"]: r for r in csv.DictReader(fh)}
    clear_var = next(v for v in variables_json["variables"] if v["name"] == "clear_frac_isccp")
    clear_side = clear_var["bodies"]["EARTH"]
    check(clear_side["level"] == prov_rows["clear_frac_isccp"]["level"] == "DERIVED", "clear-sky level")

    pop = {"slope": {"EARTH": e_slope, "MOON": m_slope}, "rough": {"EARTH": e_rough, "MOON": m_rough}}
    pop_text = {"EARTH": f"all {int(np.sum(~np.isnan(e_slope))):,} Earth land cells with a value (earth_base.bin)",
                "MOON": f"all {int(np.sum(~np.isnan(m_slope))):,} lunar cells with a value (moon_base.bin)"}

    import reverse_geocoder  # noqa: the engine's own dependency (engine/places.py)
    rg_csv = os.path.join(os.path.dirname(reverse_geocoder.__file__), "rg_cities1000.csv")
    gn = pd.read_csv(rg_csv, dtype=str, keep_default_na=False)
    gn_names = set(gn["name"])
    bundle_place_names = set(pdetail["nearest_places"])
    iau_names = set(iau["name"])
    with open(os.path.join(ENGINE_DATA, "iau_moon_nomenclature.csv"), encoding="utf-8") as fh:
        engine_iau_names = {r["name"] for r in csv.DictReader(fh)}
    from shapely.geometry import box, shape, Point
    with open(os.path.join(ENGINE_DATA, "artemis_iii_regions.geojson"), encoding="utf-8") as fh:
        gj = json.load(fh)
    art = [(f["properties"]["name"], shape(f["geometry"])) for f in gj["features"]]
    art_names = {n for n, _ in art}
    country_names = [c["name"] for c in places["countries"]]
    country_by_code = {c["code"]: c["name"] for c in places["countries"]}
    region_names = [r["name"] if isinstance(r, dict) else r for r in places["regions"]]

    out_missions: Dict[str, Any] = {}
    for mid in MISSIONS:
        mj = mission_by_id[mid]
        sim = mj["similarity"]
        top5 = mj["top5"]
        efile, pfile = f"earth_{mid}.bin", f"earth_{mid}_pairs.bin"
        li = b.col(efile, "land_index").astype(np.int64)
        ids = land_ids[li]
        rank = b.col(efile, "rank")
        twin = b.col(efile, "twin")
        suit = b.col(efile, "suitability")
        simv = b.col(efile, "similarity")
        final = b.col(efile, "final")
        lorder = b.col(pfile, "list_order")
        s_cols = [b.col(efile, v["score_column"]) for v in sim["variables"]]
        weights = [float(v["weight"]) for v in sim["variables"]]
        ex_items = {it["id"]: it for it in explain["missions"][mid]}
        twin_rows = {t["id"]: t for t in twins["missions"][mid]["twins"]}
        check(len(top5["ids"]) == TOP and len(top5["overall_ranks"]) == TOP, f"{mid}: top5 has not five ids")
        for eid in top5["ids"]:
            check(abs(mask_by_id[eid] - tbl_mask[eid]) < 1e-4, f"E{eid}: mask_fraction bundle vs table")
        five_rule = recompute_five(mid, top5, rank, final, ids, s_cols, weights, mask_by_id, ice_by_id)
        CHECKS.append(f"{mid}: rule of the five '{top5['rule_id']}' re-run from the binary columns and the Earth table gives "
                      f"the bundle's five ({', '.join('E' + str(i) for i in top5['ids'])})")
        pairs: List[Dict[str, Any]] = []
        for num, (eid, orank) in enumerate(zip(top5["ids"], top5["overall_ranks"]), start=1):
            hit = np.flatnonzero(ids == eid)
            check(len(hit) == 1, f"{mid}: E{eid} found {len(hit)} times")
            p = int(hit[0])
            check(rank[p] == orank, f"{mid} #{num}: rank {rank[p]} != overall_ranks {orank}")
            check(lorder[p] == orank, f"{mid} #{num}: list_order {lorder[p]}")
            check(not np.isnan(twin[p]), f"{mid} #{num}: not a paired point")
            mcell = int(twin[p])
            it = ex_items[eid]
            check(it["rank"] == orank, f"{mid} #{num}: explain rank")
            st = it["similarity"]
            check(st["twin"]["id"] == mcell, f"{mid} #{num}: explain twin != binary twin")
            same(it["suitability"], suit[p], f"{mid} #{num} suitability")
            same(st["value"], simv[p], f"{mid} #{num} similarity")
            same(it["final"], final[p], f"{mid} #{num} final")
            sim_re = 100.0 * sum(w * s[p] for w, s in zip(weights, s_cols)) / sum(weights)
            check(round(sim_re, 2) == simv[p] or abs(sim_re - simv[p]) < 0.006, f"{mid} #{num}: similarity recompute {sim_re}")
            check(abs(0.5 * simv[p] + 0.5 * suit[p] - final[p]) < 0.0051, f"{mid} #{num}: final != half and half")

            # ---- Earth place
            elat, elon = cell_latlon(eid, cols)
            check(elat == it["lat"] and elon == it["lon"], f"{mid} #{num}: Earth lat/lon")
            k = land_pos[eid]
            pl = it["place"]
            cname = country_names[int(e_country[k])]
            check(cname == pl["country"], f"{mid} #{num}: country {cname} != {pl['country']}")
            rname = None if np.isnan(e_region[k]) else region_names[int(e_region[k])]
            check(rname == pl["region"], f"{mid} #{num}: region {rname} != {pl['region']}")
            nname = pdetail["nearest_places"][int(np_idx[k])]
            check(nname == pl["nearest_place"], f"{mid} #{num}: nearest place")
            same(pl["nearest_place_km"], np_km[k], f"{mid} #{num} nearest_place_km")
            check(nname in bundle_place_names and nname in gn_names, f"{nname} not in GeoNames/bundle")
            cand = gn[gn["name"] == nname]
            best = None
            for _, row in cand.iterrows():
                d = great_circle_km(elat, elon, float(row["lat"]), float(row["lon"]), R_E)
                if best is None or abs(d - np_km[k]) < abs(best[0] - np_km[k]):
                    best = (d, row)
            dkm, prow = best
            check(abs(dkm - np_km[k]) < 0.2, f"{nname}: recomputed {dkm} km vs bundle {np_km[k]}")
            direction = compass(bearing_deg(float(prow["lat"]), float(prow["lon"]), elat, elon))
            place_cc = prow["cc"]
            check(place_cc in country_by_code, f"{nname}: country code {place_cc} not in places.json")
            # one code can carry two names in places.json (SO: Somalia and Somaliland): take the name
            # of the land cell that holds the named place itself (earth_base.bin country)
            cc_names = [c["name"] for c in places["countries"] if c["code"] == place_cc]
            place_country = cc_names[0]
            if len(cc_names) > 1:
                plat, plon = float(prow["lat"]), float(prow["lon"])
                pcell = int(90 - plat) * cols + int(plon + 180)
                check(pcell in land_pos, f"{nname}: its own cell E{pcell} is not a land cell")
                place_country = country_names[int(e_country[land_pos[pcell]])]
                check(place_country in cc_names, f"{nname}: cell country {place_country} not among {cc_names}")
            earth_place = {
                "nearest_named_place": nname,
                "nearest_named_place_country": place_country,
                "nearest_named_place_country_rule": ("the country of the GeoNames code" if len(cc_names) == 1 else
                                                     f"code {place_cc} names {' and '.join(cc_names)} in places.json: the country of "
                                                     f"the land cell that holds the place (earth_base.bin)"),
                "nearest_named_place_same_country": place_country == pl["country"],
                "nearest_named_place_source": "GeoNames cities1000 populated places (the engine's offline copy in the reverse_geocoder "
                                              "package, tierra luna/engine/places.py); bundle: place_detail.json nearest_places / "
                                              "earth_place_detail.bin",
                "distance_km": pl["nearest_place_km"],
                "distance_km_spoken": spoken_km(np_km[k]),
                "distance_rounding": "rounded once to the unit, half up, from the stored float32 (earth_place_detail.bin nearest_place_km)",
                "distance_km_recomputed": round(dkm, 1),
                "distance_shown_on_screen": bool(np_km[k] <= NEAREST_PLACE_MAX_KM_ON_SCREEN),
                "direction_from_place": direction,
                "direction_note": "initial great-circle bearing from the named place to the cell centre, 8-point compass",
                "region": pl["region"], "country": pl["country"], "country_code": pl["country_code"],
                "country_label_rule": pdetail["label_rules"][int(lr_idx[k])],
                "region_country_source": "bundle places.json (indexed by earth_base.bin country / region)",
                "cell_centre_lat": elat, "cell_centre_lon": elon,
                "coordinates_on_screen": f"{screen_num(abs(elat), 1)}° {'N' if elat >= 0 else 'S'}, "
                                         f"{screen_num(abs(elon), 1)}° {'E' if elon >= 0 else 'W'}",
            }
            if pl["region"] is None:
                earth_place["region_note"] = "the bundle gives no first-level region for this cell"
            if not earth_place["distance_shown_on_screen"]:
                earth_place["screen_note"] = (f"the web prints the nearest populated place only within {NEAREST_PLACE_MAX_KM_ON_SCREEN} km "
                                              f"(app/src/flow/detailPanel.ts); this one is {pl['nearest_place_km']} km away")

            # ---- Moon place
            mlat, mlon = cell_latlon(mcell, cols)
            check(mlat == st["twin"]["lat"] and mlon == st["twin"]["lon"], f"{mid} #{num}: Moon lat/lon")
            fi = int(m_feat[mcell])
            fname, ftype = iau["name"][fi], iau["type"][fi]
            check(fname == st["twin"]["feature"], f"{mid} #{num}: feature {fname}")
            same(st["twin"]["feature_km"], m_feat_km[mcell], f"{mid} #{num} feature_km")
            tw = twin_rows[mcell]
            check(tw["feature"]["name"] == fname and tw["feature"]["type"] == ftype, "twins.json feature")
            check(tw["feature"]["distance_km"] == st["twin"]["feature_km"], "twins.json feature distance")
            check(fname in iau_names and fname in engine_iau_names, f"{fname} not in IAU lists")
            fkm = great_circle_km(mlat, mlon, iau["lat"][fi], iau["lon"][fi], R_M)
            check(abs(fkm - m_feat_km[mcell]) < 0.2, f"{fname}: recomputed {fkm} vs {m_feat_km[mcell]}")
            reg = zones["regions"][int(m_region[mcell])]
            moon_place = {
                "nearest_named_feature": fname, "feature_type": ftype,
                "distance_km": st["twin"]["feature_km"],
                "distance_km_spoken": spoken_km(m_feat_km[mcell]),
                "distance_km_on_screen": screen_num(m_feat_km[mcell], 1),
                "distance_km_recomputed": round(fkm, 1),
                "near_allowed": float(m_feat_km[mcell]) < NEAR_MAX_KM,
                "feature_source": "bundle iau_moon_features.json (USGS/IAU Gazetteer of Planetary Nomenclature), moon_base.bin feature / feature_km",
                "cell_centre_lat": mlat, "cell_centre_lon": mlon,
                "lunar_region_code": reg["code"], "lunar_region_label": reg["label"],
                "earth_points_sharing_this_twin": tw["earth_cells"],
            }
            if mid == "lunar_base":
                check(reg["code"] == "A", f"lunar_base twin {mcell} outside region A")
                nr = tw["nasa_region"]
                cellbox = box(mlon - 0.5, mlat - 0.5, mlon + 0.5, mlat + 0.5)
                hits = sorted(n for n, g in art if g.intersects(cellbox))
                check(nr["region"] in hits and all(h in art_names for h in hits), f"#{num}: bundle region {nr['region']} not among {hits}")
                shares = {n: region_share_of_cell(mlat, mlon, g, R_M) for n, g in art if n in hits}
                main_region = max(sorted(shares), key=lambda n: shares[n])
                check(main_region == nr["region"], f"#{num}: own main region {main_region} != bundle {nr['region']}")
                check(abs(shares[main_region] - nr["share_of_cell"]) < 0.01, f"#{num}: own share {shares[main_region]} vs bundle {nr['share_of_cell']}")
                phrase = "in" if nr["share_of_cell"] >= 0.5 else "at the edge of"
                check(phrase == nr["phrase"] and nr["text"] == f"{phrase} NASA's {nr['region']} candidate region", f"#{num}: region phrase")
                centre_in = bool(project_geom(dict(art)[main_region], R_M).contains(project_geom(Point(mlon, mlat), R_M)))
                moon_place.update({
                    "nasa_region_from_bundle": nr,
                    "nasa_region_phrase": nr["text"],
                    "nasa_candidate_regions_intersected": hits,
                    "nasa_region_share_of_cell_recomputed": {n: round(v, 4) for n, v in shares.items()},
                    "cell_centre_inside_region": centre_in,
                    "nasa_region_rule": "twins.json nasa_region: the region the cell shares most area with; 'in' at 50 % or more of the cell, "
                                        "else 'at the edge of'; recomputed here (south-polar Lambert equal-area on the 1737.4 km sphere)",
                })

            # ---- variables (published = explain.json; second path = pairs file, base tables, twins.json)
            vars_out = []
            for v in sim["variables"]:
                name = v["variable"]
                ev = next(x for x in st["variables"] if x["variable"] == name)
                le, lm = side_level(v, "EARTH", levels), side_level(v, "MOON", levels)
                pc = v["pairs_columns"]
                if mid == "lunar_base":
                    if name == "tmin_k":
                        lm = moon_tmin_level(v)
                    raw = {"earth": b.col(pfile, pc["earth"])[p], "moon": b.col(pfile, pc["moon"])[p], "diff": b.col(pfile, pc["diff"])[p]}
                    same(ev["earth_real"], raw["earth"], f"{mid} #{num} {name} earth")
                    same(ev["moon_real"], raw["moon"], f"{mid} #{num} {name} moon")
                    same(ev["difference_real"], raw["diff"], f"{mid} #{num} {name} diff")
                    same(ev["moon_real"], tw["values"][name], f"twins.json {name}")
                    row = {"variable": name, "label": v["label"], "role": v["role"], "weight": v["weight"],
                           "tolerance": v["tolerance"], "bound": v["bound"], "real_unit": v["real_unit"],
                           "earth_real": ev["earth_real"], "moon_real": ev["moon_real"], "difference_real": ev["difference_real"],
                           "on_screen_real": {s: screen_value(raw[s], v["real_unit"]) for s in raw},
                           "earth_level": le, "moon_level": lm, "score": ev["score"]}
                    if v["scale"] == "percentile_within_population":
                        rp = {"earth": b.col(pfile, pc["earth_pct"])[p], "moon": b.col(pfile, pc["moon_pct"])[p],
                              "diff": b.col(pfile, pc["diff_pct"])[p]}
                        same(ev["earth"], rp["earth"], f"{mid} #{num} {name} earth_pct")
                        same(ev["moon"], rp["moon"], f"{mid} #{num} {name} moon_pct")
                        same(ev["difference"], rp["diff"], f"{mid} #{num} {name} diff_pct")
                        same(ev["moon"], tw["percentiles"][name], f"twins.json pct {name}")
                        row.update({"compared_unit": "percentile points", "earth_percentile": ev["earth"],
                                    "moon_percentile": ev["moon"], "difference_points": ev["difference"],
                                    "on_screen_percentile": {s: screen_value(rp[s], "percentile points") for s in rp},
                                    "population_earth": sim["populations"]["EARTH"]["cells"],
                                    "population_moon": sim["populations"]["MOON"]["cells"]})
                    vars_out.append(row)
                else:
                    raw = {"earth": b.col(pfile, pc["earth"])[p], "moon": b.col(pfile, pc["moon"])[p], "diff": b.col(pfile, pc["diff"])[p]}
                    same(ev["earth"], raw["earth"], f"{mid} #{num} {name} earth")
                    same(ev["moon"], raw["moon"], f"{mid} #{num} {name} moon")
                    same(ev["difference"], raw["diff"], f"{mid} #{num} {name} diff")
                    same(ev["moon"], tw["values"][name], f"twins.json {name}")
                    vars_out.append({"variable": name, "label": v["label"], "role": v["role"], "weight": v["weight"],
                                     "tolerance": v["tolerance"], "bound": v["bound"], "unit": v["unit"],
                                     "earth": ev["earth"], "moon": ev["moon"], "difference": ev["difference"],
                                     "on_screen": {s: screen_value(raw[s], v["unit"]) for s in raw},
                                     "earth_level": le, "moon_level": lm, "score": ev["score"]})
            V = {x["variable"]: x for x in vars_out}
            for nm, ea, ma in (("slope_deg", e_slope, m_slope), ("roughness_m", e_rough, m_rough)):
                ek = "earth_real" if mid == "lunar_base" else "earth"
                mk = "moon_real" if mid == "lunar_base" else "moon"
                same(V[nm][ek], ea[k], f"{mid} #{num} {nm} vs earth_base")
                same(V[nm][mk], ma[mcell], f"{mid} #{num} {nm} vs moon_base")

            pair = {
                "mission": {"id": mid, "name": mj["title"]},
                "number": num,
                "rank": orank,
                "overall_rank": orank,
                "rank_note": "number = position among the five shown (1 to 5); rank / overall_rank = rank in the full ranking by final score",
                "earth_cell_id": f"E{eid}", "moon_cell_id": f"M{mcell}", "ids_note": "reference only, not to be read aloud",
                "earth_place": earth_place, "moon_place": moon_place,
                "similarity": st["value"], "suitability": it["suitability"], "final": it["final"],
                "on_screen_scores": {"similarity": screen_score(simv[p]), "suitability": screen_score(suit[p]), "final": screen_score(final[p])},
                "variables": vars_out,
                "not_part_of_similarity": st.get("not_part_of_similarity"),
            }
            if mid == "rover":
                pair["top_tie"] = {"in_top_tie": bool(final[p] == float(np.nanmax(final))),
                                   "tied_sites": top5["top_tie_n"], "tied_sites_after_skips": top5["top_tie_n_after_skips"],
                                   "final_on_screen": screen_score(final[p])}
                check(pair["top_tie"]["in_top_tie"], f"rover #{num} not in the top tie")

            if mid == "solar":
                atm = st["atmosphere"]
                g_raw, t_raw = b.col(pfile, "atm.ground_kwh_m2_day")[p], b.col(pfile, "atm.toa_kwh_m2_day")[p]
                same(atm["ground_kwh_m2_day"], g_raw, "atm ground")
                same(atm["toa_kwh_m2_day"], t_raw, "atm toa")
                same(atm["lost_share"], b.col(pfile, "atm.lost_share")[p], "atm lost")
                same(atm["ground_kwh_m2_day"], e_ground[k], "atm ground vs earth_base")
                same(V["irradiance_toa_kwh_m2_day"]["moon"], m_irr[mcell], "solar moon irradiance vs moon_base")
                moon_raw = b.col(pfile, "irradiance_toa_kwh_m2_day.moon")[p]
                lost_pct = share_lost_percent(t_raw, g_raw)
                g1, t1, m1 = sentence_tenth(g_raw), sentence_tenth(t_raw), sentence_tenth(moon_raw)
                check(st.get("pair_sentence") is not None and
                      f"{t1} kWh/m²/day at the top of Earth's atmosphere here and {m1} kWh/m²/day on the lunar surface" in st["pair_sentence"] and
                      f"only {g1} of those {t1} kWh/m²/day reach the ground ({lost_pct} % is lost" in st["pair_sentence"],
                      f"solar #{num}: the displayed numbers differ from the bundle's per-pair sentence")
                pair["earth_atmosphere"] = {
                    "ground_kwh_m2_day": atm["ground_kwh_m2_day"], "ground_level": levels[("irradiance_kwh_m2_day", "EARTH")],
                    "above_atmosphere_kwh_m2_day": atm["toa_kwh_m2_day"],
                    "above_atmosphere_level": V["irradiance_toa_kwh_m2_day"]["earth_level"]["level"],
                    "lost_share_bundle": atm["lost_share"],
                    "display": {"ground_kwh_m2_day": g1, "above_atmosphere_kwh_m2_day": t1, "moon_kwh_m2_day": m1, "lost_percent": lost_pct,
                                "rule": "similarity.json texts.solar_limitation display_rule (engine/display.py): each value with 1 decimal, half "
                                        f"up, from the stored float32; lost_percent = {SHARE_LOST_PYTHON} on the displayed tenths A and G"},
                    "pair_sentence_from_bundle": st["pair_sentence"],
                }
                cv = next(x for x in it["breakdown"] if x["variable"] == "clear_frac_isccp")
                same(cv["value"], e_clear[k], f"solar #{num} clear-sky vs earth_base")
                same(cv["value"], clear_tbl[eid], f"solar #{num} clear-sky vs supplementary table")
                crit = next(w for w in mj["weighted_variables"] if w["variable"] == "clear_frac_isccp")
                pair["clear_sky"] = {
                    "value": cv["value"], "on_screen": screen_value(e_clear[k], "fraction 0-1"),
                    "plain_words": clear_words(float(e_clear[k])),
                    "utility": cv["utility"], "weight": cv["weight"], "points_of_suitability": cv["points"],
                    "criterion": {"bad": crit["bad"], "good": crit["good"], "weight": crit["weight"]},
                    "valid_months_2012_2016": int(clear_months[eid]),
                    "level": clear_side["level"], "product": clear_side["product"], "version": clear_side["version"],
                    "source": f"variables.json clear_frac_isccp EARTH; {os.path.relpath(CLOUD_TABLE, REPO)} (second path)",
                    "cite": "Rossow and Schiffer 1999, BAMS 80:2261-2287; NOAA NCEI ISCCP-H Climate Data Record",
                }

            if mid == "lunar_base":
                same(V["tmin_k"]["earth_real"], e_tmin[k] + 273.15, "tmin earth vs earth_base")
                same(V["tmin_k"]["moon_real"], m_tmin[mcell] + 273.15, "tmin moon vs moon_base")
                pair["pair_sentence_from_bundle"] = st["pair_sentence"]

            ea, ma = cell_area_km2(elat, R_E), cell_area_km2(mlat, R_M)
            pair["cell_area_km2"] = {"earth": round(ea, 1), "moon": round(ma, 1), "earth_over_moon": round(ea / ma, 1),
                                     "rule": "1-degree cell on the sphere: R^2 x dlon x |sin(lat2) - sin(lat1)|"}
            pair["common_traits"] = traits(mid, pair, k, mcell, pop, pop_text)
            check(2 <= len(pair["common_traits"]) <= 3, f"{mid} #{num}: {len(pair['common_traits'])} traits")
            pairs.append(pair)

        mo: Dict[str, Any] = {
            "name": mj["title"],
            "similarity_rule": man["similarity_rules"][mid],
            "criteria_set": mj.get("criteria_set"),
            "zone": sim["zone"]["name"],
            "zone_why_on_screen": zones["texts"]["zone_why"][mid] if zones.get("texts") else None,
            "similarity_variables": [{k2: v.get(k2) for k2 in ("variable", "role", "weight", "tolerance", "bound", "unit")} for v in sim["variables"]],
            "pair_filter": sim["filter"],
            "rule_of_the_five": {"rule_text_on_screen": top5["rule"], "rule_id": top5["rule_id"], "skips": top5["skips"],
                                 "min_separation_deg": top5["min_separation_deg"], "min_separation_km": top5["min_separation_km"],
                                 "ids": [f"E{i}" for i in top5["ids"]], "overall_ranks": top5["overall_ranks"],
                                 "top_tie_n": top5["top_tie_n"], "top_tie_n_after_skips": top5["top_tie_n_after_skips"],
                                 "alternative": top5.get("alternative"), "recomputed": five_rule},
            "list_order_text_on_screen": sim_texts.get(f"list_order_{mid}", {}).get("text"),
            "status": "verified",
            "pairs": pairs,
        }
        if mid == "rover":
            mo["tie_text_on_screen"] = sim_texts["rover_tie"]["text"]
            mo["tie_figures"] = sim_texts["rover_tie"]["figures"]
            check(sim_texts["rover_tie"]["figures"]["tied_n"] == with_commas(top5["top_tie_n"]) and
                  sim_texts["rover_tie"]["figures"]["tied_kept_n"] == with_commas(top5["top_tie_n_after_skips"]), "rover_tie figures")
        if mid == "solar":
            crit = next(w for w in mj["weighted_variables"] if w["variable"] == "clear_frac_isccp")
            mo["suitability_criterion_clear_sky"] = {
                "variable": "clear_frac_isccp", "label": clear_var["label"], "weight": crit["weight"], "bad": crit["bad"], "good": crit["good"],
                "level": clear_side["level"], "product": clear_side["product"], "version": clear_side["version"],
                "period": prov_rows["clear_frac_isccp"]["period"], "formula": prov_rows["clear_frac_isccp"]["formula"],
                "caveat": clear_side["caveat"], "text_on_screen": sim_texts["solar_suitability_clouds"]["text"]}
            mo["saturation_text_on_screen"] = sim_texts["solar_similarity_saturation"]["text"]
        if mid == "lunar_base":
            mo["populations"] = {bd: sim["populations"][bd]["cells"] for bd in ("EARTH", "MOON")}
            mo["zone_edge_text_on_screen"] = sim_texts["zone_edge_lunar_base"]["text"]
        out_missions[mid] = mo
        CHECKS.append(f"{mid}: the five found once each, all paired, list_order = rank; ids, scores, variables, places, features"
                      f"{', region phrases' if mid == 'lunar_base' else ''}{', clear-sky fractions' if mid == 'solar' else ''} equal across "
                      f"explain.json, twins.json, missions.json and the binary files (and the extra tables named above)")

    tracks = make_tracks(out_missions, sim_texts, zones)
    verify_tracks(tracks, out_missions, sim_texts, zones)
    for mid in MISSIONS:
        for pr in out_missions[mid]["pairs"]:
            pr["say"] = tracks[f"{TRACK_PREFIX[mid]}_{pr['number']}"]["text"]

    lb = out_missions["lunar_base"]["pairs"]
    tdiff = [x["variables"][0]["on_screen_real"]["diff"] for x in lb]
    return {
        "generated_on": GENERATED_ON, "generated_by": SCRIPT_REL, "bundle": "app/public/data/v2",
        "contract_revision": man["contract_revision"], "engine_version": man["engine_version"], "dataset": man["dataset"]["id"],
        "similarity_rules": man["similarity_rules"],
        "how_to_read": {
            "number": "Position among the five the web shows (missions.json top5.ids, in order).",
            "overall_rank": "Rank in the full ranking by final score (unchanged by the rule of the five).",
            "similarity": "How alike the Earth point and its lunar twin are, 0 to 100, from the mission's variables compared within stated tolerances.",
            "suitability": "How well the Earth point meets the mission's own needs as a test site, 0 to 100, from its weighted criteria.",
            "final": "The ranking score: half similarity and half suitability (alpha 0.5).",
            "on_screen": "The value as the web prints it (app/src/flow/dom.ts valueText / fixed; per-pair sentence numbers with engine/display.py).",
            "levels": "MEASURED = from a named measured product; DERIVED = a stated formula on measured values; MODELLED = a model or climatology.",
            "percentile_words": "A word such as gentle or smooth is used only when both sides fall in the same quarter (or tenth) of their own population, named in the trait's basis.",
        },
        "status": {m: out_missions[m]["status"] for m in MISSIONS},
        "caveats": [
            "Each place is a 1-degree cell, about 111 km north-south on Earth (about 30 km on the Moon); values are cell averages.",
            "Rover: slope and roughness differences within the measurement error of the elevation models score as equal, so "
            f"{out_missions['rover']['rule_of_the_five']['top_tie_n']} sites tie at the top; the five are a geographic spread of the "
            f"{out_missions['rover']['rule_of_the_five']['top_tie_n_after_skips']} tied sites that are not mostly ice or water.",
            "Solar panels: the likeness is of sunlight above the atmosphere; on Earth a large share is lost in the atmosphere, so this is not a likeness of what panels would collect.",
            f"Lunar base: a likeness of thermal position within each world's population, not of temperature: the coldest temperatures of the five pairs are {min(tdiff, key=float)} to {max(tdiff, key=float)} K apart.",
            "Names are the nearest named feature or populated place to the cell centre, not a landing site or the cell's own name.",
        ],
        "missions": out_missions,
        "tracks": tracks,
        "checks": CHECKS,
    }


# ----------------------------------------------------------------------------- traits
def band(p_e: float, p_m: float, low_word: str, high_word: str) -> Optional[Tuple[str, str]]:
    hi, lo = max(p_e, p_m), min(p_e, p_m)
    if hi <= 10:
        return low_word, "tenth"
    if hi <= 25:
        return low_word, "quarter"
    if lo >= 90:
        return high_word, "tenth"
    if lo >= 75:
        return high_word, "quarter"
    return None


def terrain_trait(key: str, on: Dict[str, str], unit_say: str, k: int, mcell: int, pop: Dict, pop_text: Dict,
                  low_word: str, high_word: str, label: str) -> Dict[str, Any]:
    pe = mid_rank_pct(pop[key]["EARTH"], pop[key]["EARTH"][k])
    pm = mid_rank_pct(pop[key]["MOON"], pop[key]["MOON"][mcell])
    bd = band(pe, pm, low_word, high_word)
    nums = f"{on['earth']} {unit_say} on Earth and {on['moon']} on the Moon, {on['diff']} apart"
    if bd:
        word, part = bd
        which = "lowest" if word == low_word else "highest"
        text = (f"Both are {word}: {label} of {nums}; each lies in the {which} {part} of its own world "
                f"({ordinal(max(1, int(round(pe))))} percentile on Earth, {ordinal(max(1, int(round(pm))))} on the Moon).")
    else:
        text = f"Similar {label}: {nums} (no qualitative word: the two sides are not in the same quarter of their own world)."
    col = "slope_iso_deg" if key == "slope" else "roughness_m"
    return {"text": text, "word": bd[0] if bd else None,
            "basis": {"columns": [f"earth_base.bin v.{col}", f"moon_base.bin v.{col}"], "on_screen": on,
                      "earth_percentile_in_population": round(pe, 1), "moon_percentile_in_population": round(pm, 1),
                      "populations": pop_text, "word_rule": f"'{low_word}' if both <= 25th percentile, '{high_word}' if both >= 75th, else no word"}}


def traits(mid: str, pair: Dict, k: int, mcell: int, pop: Dict, pop_text: Dict) -> List[Dict[str, Any]]:
    V = {v["variable"]: v for v in pair["variables"]}
    out = []
    if mid in ("rover", "solar"):
        if mid == "solar":
            a = pair["earth_atmosphere"]["display"]
            s = V["irradiance_toa_kwh_m2_day"]["on_screen"]
            out.append({"text": (f"Nearly the same sunlight above the atmosphere: {s['earth']} kWh/m²/day at the Earth site and {s['moon']} "
                                 f"on the Moon ({s['diff']} apart). On Earth only {a['ground_kwh_m2_day']} of {a['above_atmosphere_kwh_m2_day']} "
                                 f"reaches the ground ({a['lost_percent']} % is lost in the atmosphere); the Moon has no atmosphere, so this is a "
                                 f"likeness of sunlight above the air, not of what panels would collect."),
                        "basis": {"columns": ["irradiance_toa_kwh_m2_day.earth/.moon/.diff", "atm.ground_kwh_m2_day", "atm.toa_kwh_m2_day"],
                                  "on_screen": s, "display": a}})
        out.append(terrain_trait("slope", V["slope_deg"]["on_screen"], "degrees", k, mcell, pop, pop_text, "gentle", "steep", "slope"))
        out.append(terrain_trait("rough", V["roughness_m"]["on_screen"], "meters", k, mcell, pop, pop_text, "smooth", "rugged", "roughness"))
        return out
    tm, am = V["tmin_k"], V["lst_diurnal_amp_k"]
    for row, lw, hw, what in ((tm, "coldest", "least cold", "coldest temperature"), (am, "smallest", "largest", "daily temperature swing")):
        pe, pm = row["earth_percentile"], row["moon_percentile"]
        bd = band(pe, pm, lw, hw)
        sp, sr = row["on_screen_percentile"], row["on_screen_real"]
        lead = f"Both rank in the {bd[0]} {bd[1]} of their own population" if bd else "A similar position within their own population"
        out.append({"text": (f"{lead} by {what}: percentile {sp['earth']} on Earth and {sp['moon']} on the Moon ({sp['diff']} points apart), "
                             f"while the real values are {sr['earth']} K and {sr['moon']} K ({sr['diff']} K apart)."),
                    "word": bd[0] if bd else None,
                    "basis": {"columns": [f"{row['variable']}.earth_pct/.moon_pct/.diff_pct", f"{row['variable']}.earth/.moon/.diff"],
                              "on_screen_percentile": sp, "on_screen_real": sr,
                              "populations": {"EARTH": f"{row['population_earth']:,} Earth points passing the Lunar base funnel",
                                              "MOON": f"{row['population_moon']} lunar cells overlapping NASA's nine candidate regions"},
                              "percentile_direction": "low percentile = colder" if row is tm else "low percentile = smaller swing"}})
    sl = V["slope_deg"]["on_screen_real"]
    ro = V["roughness_m"]["on_screen_real"]
    t_s = terrain_trait("slope", sl, "degrees", k, mcell, pop, pop_text, "gentle", "steep", "slope")
    t_r = terrain_trait("rough", ro, "meters", k, mcell, pop, pop_text, "smooth", "rugged", "roughness")
    out.append({"text": f"Terrain: slope {sl['earth']} against {sl['moon']} degrees ({sl['diff']} apart), roughness {ro['earth']} against "
                        f"{ro['moon']} meters ({ro['diff']} apart)." + (f" By slope both are {t_s['word']}." if t_s["word"] else "")
                        + (f" By roughness both are {t_r['word']}." if t_r["word"] else ""),
                "basis": {"slope": t_s["basis"], "roughness": t_r["basis"]}})
    return out


# ----------------------------------------------------------------------------- the 19 texts
def earth_phrase(ep: Dict[str, Any]) -> str:
    where = ", ".join(x for x in (ep["region"], ep["country"]) if x)
    of = ep["nearest_named_place"] if ep["nearest_named_place_same_country"] else \
        f"{ep['nearest_named_place']} in {ep['nearest_named_place_country']}"
    coords = ""
    if not ep["distance_shown_on_screen"] or ep["region"] is None:
        la, lo = ep["cell_centre_lat"], ep["cell_centre_lon"]
        coords = (f", at {screen_num(abs(la), 1)} degrees {'north' if la >= 0 else 'south'} and "
                  f"{screen_num(abs(lo), 1)} degrees {'east' if lo >= 0 else 'west'}")
    return (f"A site in {where}{coords}, about {with_commas(ep['distance_km_spoken'])} kilometers "
            f"{ep['direction_from_place']} of {of}.")


def moon_phrase(mp: Dict[str, Any]) -> str:
    return f"Its lunar twin lies about {mp['distance_km_spoken']} kilometers from {feature_phrase(mp['nearest_named_feature'], mp['feature_type'])}"


def make_tracks(M: Dict[str, Any], texts: Dict, zones: Dict) -> Dict[str, Dict[str, Any]]:
    rv = M["rover"]["rule_of_the_five"]
    n_tie, n_kept = rv["top_tie_n"], rv["top_tie_n_after_skips"]
    keys = "Press one to five to hear each one, or Escape to go back."
    t: Dict[str, str] = {}
    t["00_welcome"] = (
        "Welcome to Stars Beside You, a planetary twin finder. Before a rover, a solar panel or a lunar base ever reaches the Moon, "
        "it can be tested here on Earth, if we find the right place. We compare lunar data from NASA missions with data from all over "
        "the Earth, and pair each Earth site with a lunar twin. There are three missions. Press one for the Rover, matched on slope and "
        "roughness. Press two for Solar panels, matched on sunlight. Press three for the Lunar base, matched on the cold and its daily swing.")
    t["m1_rover"] = (
        "Rover. We match places on slope and roughness only: the ground a rover drives on. On the Moon we search near the "
        "south pole, where NASA plans to look for water ice. Many sites differ from their lunar twin by less than the elevation data can "
        f"measure, so they tie at the top score. Here are five of the {with_commas(n_tie)} sites tied at the top of our model, chosen "
        f"to be spread across the world. All five share the same final score, half "
        f"likeness and half suitability. {keys}")
    t["m2_solar"] = (
        "Solar panels. A solar panel lives on sunlight, so we match places on the sunlight that arrives each day above the atmosphere. "
        "On the Moon we search the low, flat maria near the equator, where the Sun stands high. "
        "Here are five of the highest-scoring analogs in our model, ordered by the final score: half likeness and half suitability. "
        "Almost every top site matches its twin's sunlight almost exactly, so the likeness is nearly the same for all of them, and "
        f"suitability, led by clear skies, decides the order. {keys}")
    pe, pm = M["lunar_base"]["populations"]["EARTH"], M["lunar_base"]["populations"]["MOON"]
    t["m3_base"] = (
        "Lunar base. A base must endure the cold, so we match on the coldest temperature and its daily swing. On the Moon we "
        "search NASA's nine candidate landing regions near the south pole, where NASA plans crewed landings. The Moon is far colder "
        "than Earth, so we compare position, not temperature: how each site ranks among Earth's "
        f"{with_commas(pe)} candidates, and its twin among the {pm} lunar cells of those regions. Here are five of the highest-scoring "
        f"analogs in our model, ordered by the final score: half likeness and half suitability. {keys}")
    for pr in M["rover"]["pairs"]:
        V = {v["variable"]: v["on_screen"] for v in pr["variables"]}
        s, r = V["slope_deg"], V["roughness_m"]
        t[f"rover_{pr['number']}"] = (
            f"Rover, analog {NUM_WORD[pr['number']]}. {earth_phrase(pr['earth_place'])} {moon_phrase(pr['moon_place'])}. "
            f"The slope is {s['earth']} degrees on Earth and {s['moon']} on the Moon; the roughness is {r['earth']} meters on Earth and "
            f"{r['moon']} on the Moon. Similarity: {strip0(pr['on_screen_scores']['similarity'])} out of 100. It is one of the "
            f"{with_commas(n_tie)} sites tied at the top: within what the elevation data can measure, they all match their twins equally well.")
    for pr in M["solar"]["pairs"]:
        a = pr["earth_atmosphere"]["display"]
        c = pr["clear_sky"]
        sunlight = (f"both get {a['above_atmosphere_kwh_m2_day']} kilowatt hours per square meter a day"
                    if a["above_atmosphere_kwh_m2_day"] == a["moon_kwh_m2_day"] else
                    f"the site gets {a['above_atmosphere_kwh_m2_day']} kilowatt hours per square meter a day, and its twin {a['moon_kwh_m2_day']}")
        simil = pr["on_screen_scores"]["similarity"]
        simil = "over 99.99" if simil == "100.00" else simil
        t[f"solar_{pr['number']}"] = (
            f"Solar panels, analog {NUM_WORD[pr['number']]}. {earth_phrase(pr['earth_place'])} {moon_phrase(pr['moon_place'])}. "
            f"Above the atmosphere, {sunlight}. But only {a['ground_kwh_m2_day']} of them reach the ground here: {a['lost_percent']} percent "
            f"is lost in the air, and the Moon has no air. On average, satellites see about {c['plain_words']} of the sky over the site "
            f"clear of clouds, a clear-sky fraction of {c['on_screen']}. Similarity: {simil} out of 100.")
    for pr in M["lunar_base"]["pairs"]:
        V = {v["variable"]: v for v in pr["variables"]}
        tm, am, sl = V["tmin_k"], V["lst_diurnal_amp_k"], V["slope_deg"]
        slope_txt = (f" The slope is alike: {sl['on_screen_real']['earth']} degrees on Earth and {sl['on_screen_real']['moon']} on the Moon."
                     if sl["difference_real"] <= sl["tolerance"] else "")
        t[f"base_{pr['number']}"] = (
            f"Lunar base, analog {NUM_WORD[pr['number']]}. {earth_phrase(pr['earth_place'])} {moon_phrase(pr['moon_place'])}, "
            f"{pr['moon_place']['nasa_region_phrase']}. The likeness is of position, not temperature: the Moon's coldest temperature is "
            f"{tm['on_screen_real']['diff']} kelvin lower. Among the candidates of each world, the coldest temperature ranks at percentile "
            f"{tm['on_screen_percentile']['earth']} on Earth and {tm['on_screen_percentile']['moon']} on the Moon, and the daily swings "
            f"rank close, at {am['on_screen_percentile']['earth']} and {am['on_screen_percentile']['moon']}.{slope_txt} "
            f"Similarity: {pr['on_screen_scores']['similarity']} out of 100.")
    return {k: {"file": f"{k}.mp3", "text": t[k]} for k in TRACK_ORDER}


NUM_RE = re.compile(r"(?<![\w.])\d[\d,]*(?:\.\d+)?")


def norm_num(tok: str) -> str:
    return tok.replace(",", "")


def verify_tracks(tracks: Dict[str, Dict[str, Any]], M: Dict[str, Any], texts: Dict, zones: Dict) -> None:
    """Every figure of every text against the screen; word counts; forbidden phrases; names."""
    rv = M["rover"]["rule_of_the_five"]
    common = {str(rv["top_tie_n"]): "missions.json rover top5.top_tie_n (texts.rover_tie, on screen)",
              str(rv["top_tie_n_after_skips"]): "missions.json rover top5.top_tie_n_after_skips (texts.rover_tie, on screen)",
              "100": "'out of 100' (scores are 0-100)"}
    solar_slope = re.search(r"median slope (\d+(?:\.\d+)?)°", zones["texts"]["zone_why"]["solar"]).group(1)
    allowed_by_track: Dict[str, Dict[str, str]] = {k: dict(common) for k in tracks}
    allowed_by_track["m2_solar"][solar_slope] = "mission_zones.json texts.zone_why.solar (on screen)"
    for bd in ("EARTH", "MOON"):
        allowed_by_track["m3_base"][str(M["lunar_base"]["populations"][bd])] = f"missions.json lunar_base similarity.populations.{bd}.cells"
    for mid in MISSIONS:
        for pr in M[mid]["pairs"]:
            key = f"{TRACK_PREFIX[mid]}_{pr['number']}"
            al = allowed_by_track[key]
            ep, mp = pr["earth_place"], pr["moon_place"]
            al[str(ep["distance_km_spoken"])] = "nearest_place_km rounded once from the stored float32"
            al[str(mp["distance_km_spoken"])] = "feature_km rounded once from the stored float32"
            al[screen_num(abs(ep["cell_centre_lat"]), 1)] = "cell centre latitude (on screen)"
            al[screen_num(abs(ep["cell_centre_lon"]), 1)] = "cell centre longitude (on screen)"
            for s, v in pr["on_screen_scores"].items():
                al[v] = f"{s} (on screen)"
                al[strip0(v)] = f"{s} (on screen, trailing zeros not spoken)"
            for v in pr["variables"]:
                for blk in ("on_screen", "on_screen_real", "on_screen_percentile"):
                    for side, x in (v.get(blk) or {}).items():
                        al[x] = f"{v['variable']}.{side} (on screen)"
            if mid == "solar":
                a = pr["earth_atmosphere"]["display"]
                for nm in ("ground_kwh_m2_day", "above_atmosphere_kwh_m2_day", "moon_kwh_m2_day", "lost_percent"):
                    al[str(a[nm])] = f"{nm} (per-pair sentence on screen)"
                al[pr["clear_sky"]["on_screen"]] = "clear_frac_isccp (suitability table on screen)"
                if pr["on_screen_scores"]["similarity"] == "100.00":
                    al["99.99"] = "rule 6: a similarity displayed as 100.00 is said 'over 99.99'"
    report = {}
    for key, tr in tracks.items():
        text = tr["text"]
        words = len(text.split())
        check(WORDS_MIN <= words <= WORDS_MAX, f"{key}: {words} words (limits {WORDS_MIN}-{WORDS_MAX})")
        low = text.lower()
        exempt = low
        region_names = [pr["moon_place"]["nasa_region_from_bundle"]["region"] for pr in M["lunar_base"]["pairs"]]
        for rn in region_names:   # official NASA region names (Slater Plain, Mons Mouton Plateau) are proper names
            exempt = exempt.replace(rn.lower(), "")
        for f in FORBIDDEN:
            check(f not in exempt, f"{key}: forbidden phrase '{f}'")
        for bad in ("plateau", "flat plain", "gently sloping"):
            check(bad not in exempt, f"{key}: landform word '{bad}' not backed")
        for m_ in re.finditer(r"\bnear\b ([^,.;]*)", low):
            what = m_.group(1)
            check(what.startswith("the south pole") or what.startswith("the equator"), f"{key}: 'near {what}' (rule 2)")
        for ph in ("five of the highest-scoring", "highest-scoring"):
            if ph in low:
                check(key in ("m2_solar", "m3_base"), f"{key}: '{ph}' outside the Solar panels and Lunar base introductions")
        found = []
        for tok in NUM_RE.findall(text):
            n = norm_num(tok)
            check(n in allowed_by_track[key], f"{key}: number {tok} is not one the screen shows for this track")
            found.append({"number": tok, "source": allowed_by_track[key][n]})
        for tok in NUM_RE.findall(text):
            if "," in tok:
                check(tok == with_commas(int(norm_num(tok))), f"{key}: {tok} badly grouped")
        tr["words"] = words
        tr["numbers"] = found
        report[key] = words
    # names as the gazetteers write them, and the mission-specific statements
    for mid in MISSIONS:
        for pr in M[mid]["pairs"]:
            key = f"{TRACK_PREFIX[mid]}_{pr['number']}"
            text = tracks[key]["text"]
            ep, mp = pr["earth_place"], pr["moon_place"]
            for nm in (ep["nearest_named_place"], ep["country"], mp["nearest_named_feature"]) + ((ep["region"],) if ep["region"] else ()):
                check(nm in text, f"{key}: name '{nm}' missing")
            check(f"about {with_commas(ep['distance_km_spoken'])} kilometers {ep['direction_from_place']} of" in text, f"{key}: Earth distance")
            check(f"about {mp['distance_km_spoken']} kilometers from" in text, f"{key}: Moon distance")
            if mid == "rover":
                check(f"one of the {with_commas(rv['top_tie_n'])} sites tied at the top" in text, f"{key}: tie statement")
            if mid == "solar":
                check("charge" not in text.lower(), f"{key}: charge")
                check(f"{pr['earth_atmosphere']['display']['lost_percent']} percent is lost" in text, f"{key}: share lost")
            if mid == "lunar_base":
                check(mp["nasa_region_phrase"] in text, f"{key}: region phrase")
                check("position, not temperature" in text, f"{key}: position statement")
                check(f"{pr['variables'][0]['on_screen_real']['diff']} kelvin" in text, f"{key}: kelvin difference")
    for k in ("m2_solar", "m3_base"):
        check("five of the highest-scoring analogs in our model" in tracks[k]["text"] and "final score" in tracks[k]["text"]
              and "half likeness and half suitability" in tracks[k]["text"], f"{k}: list order statement")
    check(f"five of the {with_commas(rv['top_tie_n'])} sites tied at the top of our model, chosen to be spread across the world"
          in tracks["m1_rover"]["text"], "m1_rover: tie statement")
    for mid in ("solar", "lunar_base"):
        check(M[mid]["rule_of_the_five"]["recomputed"]["highest_scoring_the_rule_allows"] is True,
              f"{mid}: 'five of the highest-scoring' needs the five to be the highest the rule allows")
    for k, tr in tracks.items():
        check("Press" in tr["text"] or k.split("_")[0] in ("rover", "solar", "base"), f"{k}: keys")
    CHECKS.append("tracks: 19 texts, word counts " + ", ".join(f"{k} {v}" for k, v in report.items()) +
                  f" (all within {WORDS_MIN}-{WORDS_MAX}); no forbidden phrase (official NASA region names exempt from 'plain'); "
                  "'near' only for 'near the south pole' / 'near the equator'; every number in every text is a value the screen "
                  "prints for that track, a distance rounded once from the stored value, or a count from the bundle's texts; "
                  "every place and feature name as the gazetteers write it")


# ----------------------------------------------------------------------------- app files and the Spanish note
REASONS = {
    "00_welcome": "Base lunar se emparejaba por 'temperature'; ahora se dice lo que se compara: el frío y su oscilación diaria (posición térmica); cada misión con su criterio.",
    "m1_rover": "Rover ya no comparte un único gemelo (Casatus) y decía 'the five best'; ahora: solo pendiente y rugosidad, empate de {n_tie} sitios en lo más alto (los cinco, repartidos por el mundo, entre los {n_kept} sin hielo ni agua).",
    "m2_solar": "Decía 'the five best'; ahora 'five of the highest-scoring analogs in our model', el orden por el final y la nota honesta: la similitud casi igual, decide la idoneidad (cielo despejado).",
    "m3_base": "Decía 'the five best' y comparaba 'temperature'; ahora posición, no temperatura, poblaciones de {pe} y {pm}, y el orden por el final.",
    "rover": "Los cinco de Rover son nuevos (regla de dispersión entre los empatados): lugar, gemelo, pendiente y rugosidad nuevos; sin elevación; dice que es uno de los {n_tie} empatados en lo más alto.",
    "solar": "Los cinco de Paneles solares son nuevos (idoneidad con cielo despejado ISCCP y regla de los cinco): lugar, gemelo, luz, suelo, parte perdida, cielo despejado y similitud nuevos.",
    "base": "Los cinco de Base lunar son nuevos (idoneidad corregida y regla de los cinco): lugar, gemelo, frase de región de la NASA ('at the edge of'), kelvin, percentiles y similitud nuevos.",
}


def old_texts() -> Dict[str, str]:
    try:
        s = subprocess.run(["git", "-C", REPO, "show", f"{OLD_TEXTS_COMMIT}:app/public/audio/transcripts.json"],
                           check=True, capture_output=True, text=True).stdout
        return json.loads(s)
    except Exception as exc:  # noqa
        raise AssertionError(f"cannot read the recorded texts from git commit {OLD_TEXTS_COMMIT}: {exc}")


def write_app_files(data: Dict[str, Any]) -> None:
    path = os.path.join(AUDIO_DIR, "transcripts.json")
    with open(path, encoding="utf-8") as fh:
        current = json.load(fh)
    old = old_texts()
    keys = list(current.keys())
    check(keys == [f"{k}.mp3" for k in TRACK_ORDER] and set(old) == set(keys), "transcripts.json keys changed")
    for k in keys:
        check(os.path.exists(os.path.join(AUDIO_DIR, k)), f"{k}: audio file missing (never created here)")
    new = {f"{k}.mp3": data["tracks"][k]["text"] for k in TRACK_ORDER}
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(new, fh, ensure_ascii=False, indent=1)
    changed = [k for k in keys if new[k] != old[k]]
    with open(os.path.join(AUDIO_DIR, "pending.json"), "w", encoding="utf-8") as fh:
        json.dump({"pending_rerecord": changed,
                   "note": "The team re-records these tracks; until the new recordings arrive the web shows their text only."},
                  fh, ensure_ascii=False, indent=1)
        fh.write("\n")
    write_rerecord_md(data, old, new, changed)
    CHECKS.append(f"app files: transcripts.json (19 keys, text only), pending.json ({len(changed)} tracks), docs/AUDIO_RERECORD.md")


def write_rerecord_md(data: Dict[str, Any], old: Dict[str, str], new: Dict[str, str], changed: List[str]) -> None:
    M = data["missions"]
    rv = M["rover"]["rule_of_the_five"]
    fmt = dict(n_tie=f"{rv['top_tie_n']:,}".replace(",", "."), n_kept=rv["top_tie_n_after_skips"],
               pe=f"{M['lunar_base']['populations']['EARTH']:,}".replace(",", "."), pm=M["lunar_base"]["populations"]["MOON"])
    L = ["# Audio: textos para volver a grabar (cinco de cada misión, contrato revisión 8)", "",
         f"Generado por `{SCRIPT_REL}` desde el paquete `app/public/data/v2` (revisión {data['contract_revision']}, motor "
         f"{data['engine_version']}); hechos y comprobaciones en `docs/AUDIO_TOP5.json`. Texto antiguo = `transcripts.json` del commit "
         f"`{OLD_TEXTS_COMMIT}` (lo que dicen los MP3 grabados). Ningún audio se ha generado, editado, renombrado ni borrado; "
         "`SHA256SUMS.txt` no se ha tocado. El equipo graba **una vez** con estos textos.", "",
         "Las cifras se dicen como las imprime la web (`app/src/flow/dom.ts` `valueText`, `fixed`; números de la frase de cada pareja "
         "con `engine/display.py`); las distancias se redondean una sola vez desde el valor guardado. El script comprueba cada número de "
         "cada texto contra la pantalla, el número de palabras (55 a 105) y las frases prohibidas.", "",
         "## Las 19 pistas", ""]
    for k in TRACK_ORDER:
        f = f"{k}.mp3"
        kind = k.split("_")[0] if k.split("_")[0] in ("rover", "solar", "base") else k
        L += [f"### {f}", "", f"- **Antes:** {old[f]}", f"- **Ahora:** {new[f]}",
              f"- **Motivo:** {REASONS[kind].format(**fmt)}" if f in changed else "- **Motivo:** sin cambio (el texto sigue siendo exacto).",
              f"- Palabras: {data['tracks'][k]['words']}.", ""]
    L += ["## Los cinco de cada misión", "",
          "Coordenadas = centro de la celda de 1°. Puesto = puesto en la clasificación completa. Distancias redondeadas una vez.", ""]
    for mid in MISSIONS:
        mo = M[mid]
        L += [f"### {MISSION_TITLE[mid]}", "", f"Regla de los cinco (`{mo['rule_of_the_five']['rule_id']}`): {mo['rule_of_the_five']['recomputed']['finding']}", ""]
        if mid == "rover":
            hdr = "| # | Lugar | Coordenadas | Puesto | Gemelo (rasgo, km) | Pendiente T / L (°) | Rugosidad T / L (m) | Sim. | Final |"
        elif mid == "solar":
            hdr = "| # | Lugar | Coordenadas | Puesto | Gemelo (rasgo, km) | Luz sobre la atmósfera T / L | Suelo T, perdida | Cielo despejado | Sim. | Final |"
        else:
            hdr = "| # | Lugar | Coordenadas | Puesto | Gemelo (rasgo, km), región | Diferencia de mínima (K) | Percentil mínima T / L | Percentil oscilación T / L | Sim. | Final |"
        L += [hdr, "|" + "---|" * (hdr.count("|") - 1)]
        for pr in mo["pairs"]:
            ep, mp = pr["earth_place"], pr["moon_place"]
            place = f"{ep['nearest_named_place']} ({', '.join(x for x in (ep['region'], ep['country']) if x)}), {ep['distance_km_spoken']} km {ep['direction_from_place']}"
            twin = f"{mp['nearest_named_feature']}, {mp['distance_km_spoken']} km"
            sc = pr["on_screen_scores"]
            V = {v["variable"]: v for v in pr["variables"]}
            if mid == "rover":
                s, r = V["slope_deg"]["on_screen"], V["roughness_m"]["on_screen"]
                row = [s["earth"] + " / " + s["moon"], r["earth"] + " / " + r["moon"]]
            elif mid == "solar":
                a, c = pr["earth_atmosphere"]["display"], pr["clear_sky"]
                row = [f"{a['above_atmosphere_kwh_m2_day']} / {a['moon_kwh_m2_day']}", f"{a['ground_kwh_m2_day']}, {a['lost_percent']} %",
                       c["on_screen"]]
            else:
                tm, am = V["tmin_k"], V["lst_diurnal_amp_k"]
                twin += f"; {mp['nasa_region_phrase'].replace(' candidate region', '').replace('NASA', 'NASA')}"
                row = [tm["on_screen_real"]["diff"], f"{tm['on_screen_percentile']['earth']} / {tm['on_screen_percentile']['moon']}",
                       f"{am['on_screen_percentile']['earth']} / {am['on_screen_percentile']['moon']}"]
            L.append("| " + " | ".join([str(pr["number"]), place, ep["coordinates_on_screen"], str(pr["overall_rank"]), twin] + row
                                       + [sc["similarity"], sc["final"]]) + " |")
        L.append("")
    L += ["## Ficheros que hay que grabar", "", f"{len(changed)} de 19 (también en `app/public/audio/pending.json`):", ""]
    L += [f"- `{f}`" for f in changed]
    L += ["", "Hasta que lleguen las nuevas grabaciones, la web muestra solo el texto de estas pistas.", ""]
    with open(RERECORD_MD, "w", encoding="utf-8") as fh:
        fh.write("\n".join(L))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--bundle", default=BUNDLE)
    ap.add_argument("--out", default=OUT)
    ap.add_argument("--no-app-files", action="store_true", help="write docs/AUDIO_TOP5.json only")
    a = ap.parse_args(argv)
    data = build(a.bundle)
    if not a.no_app_files:
        write_app_files(data)
    with open(a.out, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=1)
        fh.write("\n")
    for c in CHECKS:
        print("CHECK ok:", c)
    for k in TRACK_ORDER:
        print(k, data["tracks"][k]["words"], "|", data["tracks"][k]["text"])
    print("wrote", a.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
