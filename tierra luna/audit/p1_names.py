"""Point 7 (place names): recompute, with own code, every place phrase of the 15 audio pairs
and of a random sample of 60 more ranked points (20 per mission), and compare with what the
bundle, docs/AUDIO_TOP5.json and app/public/audio/transcripts.json say.

    <venv>/bin/python "tierra luna/audit/p1_names.py"

Deterministic (seed 20261115). Writes out/p1_names_pairs.csv, out/p1_names_sample.csv,
out/p1_names_mismatches.csv and out/p1_names_summary.json.

Independent code paths:
* nearest populated place: brute-force great-circle distance (own vector formula, R = 6371.0 km)
  to EVERY row of the GeoNames cities1000 file shipped in reverse_geocoder 1.5.1
  (rg_cities1000.csv), not the library's KD-tree;
* bearing: own initial great-circle bearing, from the place to the cell centre, 8-point compass;
* nearest lunar feature: brute force over the engine's IAU extract (Satellite Features excluded,
  as engine_config lunar_feature_exclude_types), R = 1737.4 km; the extract itself is checked
  against the raw MOON_nomenclature_center_pts.zip shapefile;
* country: own point-in-polygon test on the Natural Earth 110m polygons (shapely contains);
* NASA region of a Lunar base twin: own polygon-box intersection, plus the share of the cell
  area inside each region and whether the cell centre is inside.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import re
import sys

import numpy as np
import pandas as pd

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import p1_common as C  # noqa: E402

SEED = 20261115
N_PER_MISSION = 20
MISSIONS = ["rover", "solar", "lunar_base"]
AUDIO_PREFIX = {"rover": "rover", "solar": "solar", "lunar_base": "base"}
WORDS = {1: "one", 2: "two", 3: "three", 4: "four", 5: "five"}


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for blk in iter(lambda: fh.read(1 << 20), b""):
            h.update(blk)
    return h.hexdigest()


# ---------------------------------------------------------------- sources
def load_geonames():
    gn = pd.read_csv(C.RG_CSV, dtype={"name": str, "admin1": str, "admin2": str, "cc": str},
                     keep_default_na=False)
    gn["lat"] = gn["lat"].astype(float)
    gn["lon"] = gn["lon"].astype(float)
    return gn


def load_iau():
    df = pd.read_csv(C.IAU_CSV)
    allrows = len(df)
    df = df[df["type"] != "Satellite Feature"].copy()
    df["lon"] = np.where(df["center_lon_e360"] > 180.0, df["center_lon_e360"] - 360.0, df["center_lon_e360"])
    df["lat"] = df["center_lat"].astype(float)
    return df.reset_index(drop=True), allrows


def check_iau_against_raw(iau: pd.DataFrame):
    """Compare the engine's CSV extract with the raw shapefile in the zip (geopandas)."""
    import geopandas as gpd
    z = os.path.join(C.RAW, "moon", "MOON_nomenclature_center_pts.zip")
    res = {"zip": z, "zip_sha256": sha256(z)}
    try:
        g = gpd.read_file(f"zip://{z}")
    except Exception as exc:  # pragma: no cover
        res["error"] = repr(exc)
        return res
    res["raw_rows"] = int(len(g))
    res["raw_columns"] = [c for c in g.columns if c != "geometry"]
    g = g[g["type"] != "Satellite Feature"]
    raw = pd.DataFrame({"name": g["clean_name"].astype(str), "lat": g["center_lat"].astype(float),
                        "lon360": g["center_lon"].astype(float), "type": g["type"].astype(str)})
    m = iau.merge(raw, on=["name", "type"], how="left", suffixes=("", "_raw"))
    res["features_non_satellite_extract"] = int(len(iau))
    res["features_non_satellite_raw"] = int(len(raw))
    res["max_abs_dlat"] = float(np.nanmax(np.abs(m["lat_raw"] - m["lat"])))
    res["max_abs_dlon360"] = float(np.nanmax(np.abs(m["lon360"] - m["center_lon_e360"])))
    res["unmatched"] = int(m["lat_raw"].isna().sum())
    # date fields if the raw file has them
    for col in ("approvaldt", "approval_date", "updated", "date"):
        if col in g.columns:
            res["latest_" + col] = str(pd.Series(g[col]).astype(str).max())
    return res


# ---------------------------------------------------------------- per-cell recomputation
def nearest_place(gn, lat, lon):
    d = C.gc_km(lat, lon, gn["lat"].to_numpy(), gn["lon"].to_numpy(), C.R_EARTH_KM)
    order = np.argsort(d, kind="mergesort")
    i0, i1 = order[0], order[1]
    # what the library does: Euclidean distance in (lat, lon) degrees (reverse_geocoder 1.5.1
    # builds its cKDTree on the raw degree pairs)
    de = np.hypot(gn["lat"].to_numpy() - lat, gn["lon"].to_numpy() - lon)
    j = int(np.argmin(de))
    return {"gc_idx": int(i0), "gc_name": gn.at[i0, "name"], "gc_km": float(d[i0]),
            "gc_admin1": gn.at[i0, "admin1"], "gc_cc": gn.at[i0, "cc"],
            "gc_second_name": gn.at[i1, "name"], "gc_second_km": float(d[i1]),
            "deg_idx": j, "deg_name": gn.at[j, "name"], "deg_km": float(d[j]),
            "deg_admin1": gn.at[j, "admin1"], "deg_cc": gn.at[j, "cc"],
            "deg_lat": float(gn.at[j, "lat"]), "deg_lon": float(gn.at[j, "lon"]),
            "gc_lat": float(gn.at[i0, "lat"]), "gc_lon": float(gn.at[i0, "lon"])}


def nearest_feature(iau, lat, lon):
    d = C.gc_km(lat, lon, iau["lat"].to_numpy(), iau["lon"].to_numpy(), C.R_MOON_KM)
    i = int(np.argmin(d))
    return {"f_name": iau.at[i, "name"], "f_type": iau.at[i, "type"], "f_km": float(d[i]),
            "f_lat": float(iau.at[i, "lat"]), "f_lon": float(iau.at[i, "lon"]),
            "f_diam_km": float(iau.at[i, "diameter_km"]) if np.isfinite(iau.at[i, "diameter_km"]) else None}


def countries():
    from shapely.geometry import shape
    gj = C.jload(C.NE110)
    return [(f["properties"].get("ADMIN"), str(f["properties"].get("ISO_A2")), shape(f["geometry"]))
            for f in gj["features"]]


def own_country(polys, lat, lon):
    from shapely.geometry import Point
    p = Point(lon, lat)
    hits = [(n, c) for n, c, g in polys if g.contains(p)]
    return hits


def artemis_regions():
    from shapely.geometry import shape
    gj = C.jload(C.ARTEMIS)
    return [(f["properties"]["name"], shape(f["geometry"])) for f in gj["features"]]


def own_regions(regs, lat, lon):
    from shapely.geometry import box, Point
    cell = box(lon - 0.5, lat - 0.5, lon + 0.5, lat + 0.5)
    out = []
    for name, g in regs:
        if g.intersects(cell):
            out.append({"region": name, "cell_area_share": round(g.intersection(cell).area / cell.area, 4),
                        "centre_inside": bool(g.contains(Point(lon, lat)))})
    return out


# ---------------------------------------------------------------- phrase parsing
def parse_earth_phrase(text):
    """'About 66 kilometers northwest of Bayinbaolige, in Inner Mongolia, China.' -> parts."""
    m = re.search(r"[Aa]bout ([\d.]+) (?:kilometers|kilometres|km) ([a-z\-]+) of ([^,]+), in ([^.]+)\.", text)
    if not m:
        return None
    where = [w.strip() for w in m.group(4).split(",")]
    return {"km": float(m.group(1)), "dir": m.group(2).replace("-", ""), "place": m.group(3).strip(),
            "where": where}


def parse_moon_phrase(text):
    m = re.search(r"lies ([\d.]+) kilometers from ([^,.]+?)(?: crater)?(?:,|\.| in )", text)
    if m:
        return {"km": float(m.group(1)), "feature": m.group(2).strip()}
    m = re.search(r"near ([A-Z][\w' ]+?) crater", text)
    if m:
        return {"km": None, "feature": m.group(1).strip()}
    return None


def main():
    b = C.Bundle()
    gn = load_geonames()
    iau, iau_rows = load_iau()
    polys = countries()
    regs = artemis_regions()
    top5 = C.jload(os.path.join(C.REPO, "docs", "AUDIO_TOP5.json"))
    trans = C.jload(os.path.join(C.REPO, "app", "public", "audio", "transcripts.json"))

    ids = b.col("earth_base.bin", "id").astype(np.int64)
    pos = {int(v): k for k, v in enumerate(ids)}
    country_idx = b.col("earth_base.bin", "country")
    region_idx = b.col("earth_base.bin", "region")
    places = b.json("places.json")
    pdetail = b.json("place_detail.json")
    np_idx = b.col("earth_place_detail.bin", "nearest_place")
    np_km = b.col("earth_place_detail.bin", "nearest_place_km")
    lrule = b.col("earth_place_detail.bin", "label_rule")
    feats = b.json("iau_moon_features.json")
    m_feat = b.col("moon_base.bin", "feature")
    m_fkm = b.col("moon_base.bin", "feature_km")
    m_region = b.col("moon_base.bin", "region")
    zones = b.json("mission_zones.json")

    def bundle_earth(eid):
        k = pos[eid]
        ci = country_idx[k]
        ri = region_idx[k]
        return {"b_place": pdetail["nearest_places"][int(np_idx[k])], "b_km": float(np_km[k]),
                "b_country": None if not np.isfinite(ci) else places["countries"][int(ci)]["name"],
                "b_cc": None if not np.isfinite(ci) else places["countries"][int(ci)]["code"],
                "b_region": None if not np.isfinite(ri) else places["regions"][int(ri)],
                "b_label_rule": pdetail["label_rules"][int(lrule[k])]}

    def bundle_moon(mid):
        fi = int(m_feat[mid])
        return {"b_feature": feats["name"][fi], "b_ftype": feats["type"][fi], "b_fkm": float(m_fkm[mid]),
                "b_lunar_region": zones["regions"][int(m_region[mid])]["code"]}

    def recompute(eid, mid):
        elat, elon = C.cell_centre(eid)
        elat, elon = float(elat), float(elon)
        row = {"earth_id": eid, "earth_lat": elat, "earth_lon": elon}
        row.update(bundle_earth(eid))
        npl = nearest_place(gn, elat, elon)
        row.update(npl)
        # bearing from the place the bundle names (its rg row) to the cell centre
        row["bearing_from_deg_place"] = C.bearing(npl["deg_lat"], npl["deg_lon"], elat, elon)
        row["dir_from_deg_place"] = C.compass8(row["bearing_from_deg_place"])
        row["bearing_from_gc_place"] = C.bearing(npl["gc_lat"], npl["gc_lon"], elat, elon)
        row["dir_from_gc_place"] = C.compass8(row["bearing_from_gc_place"])
        hits = own_country(polys, elat, elon)
        row["own_country_ne"] = "; ".join(f"{n} ({c})" for n, c in hits) if hits else None
        row["place_is_gc_nearest"] = row["b_place"] == npl["gc_name"] and abs(row["b_km"] - npl["gc_km"]) < 0.05
        row["b_km_minus_gc_km"] = row["b_km"] - npl["gc_km"]
        if mid is not None:
            mlat, mlon = C.cell_centre(mid)
            mlat, mlon = float(mlat), float(mlon)
            row.update({"moon_id": mid, "moon_lat": mlat, "moon_lon": mlon})
            row.update(bundle_moon(mid))
            nf = nearest_feature(iau, mlat, mlon)
            row.update(nf)
            row["feature_ok"] = row["b_feature"] == nf["f_name"] and abs(row["b_fkm"] - nf["f_km"]) < 0.05
            rr = own_regions(regs, mlat, mlon)
            row["artemis_regions_own"] = json.dumps(rr)
        return row

    mism = []

    # ------------------------------------------------ the 15 audio pairs
    pair_rows = []
    for mission in MISSIONS:
        for p in top5["missions"][mission]["pairs"]:
            eid = int(p["earth_cell_id"][1:])
            mid = int(p["moon_cell_id"][1:])
            r = recompute(eid, mid)
            r["mission"] = mission
            r["rank"] = p["rank"]
            ep, mp = p["earth_place"], p["moon_place"]
            r["a_speakable"] = ep["speakable"]
            r["a_place"], r["a_km"], r["a_dir"] = ep["nearest_named_place"], ep["distance_km"], ep["direction_from_place"]
            r["a_region"], r["a_country"] = ep["region"], ep["country"]
            r["a_feature"], r["a_ftype"], r["a_fkm"] = mp["nearest_named_feature"], mp["feature_type"], mp["distance_km"]
            r["a_nasa_regions"] = json.dumps(mp.get("nasa_candidate_regions_intersected"))
            key = f"{AUDIO_PREFIX[mission]}_{p['rank']}.mp3"
            t = trans[key]
            r["transcript_file"] = key
            pe = parse_earth_phrase(t)
            pm = parse_moon_phrase(t)
            r["t_km"] = pe["km"] if pe else None
            r["t_dir"] = pe["dir"] if pe else None
            r["t_place"] = pe["place"] if pe else None
            r["t_where"] = ", ".join(pe["where"]) if pe else None
            r["t_feature"] = pm["feature"] if pm else None
            r["t_fkm"] = pm["km"] if pm else None
            m_nasa = re.search(r"in NASA's (.+?) candidate region", t)
            r["t_nasa_region"] = m_nasa.group(1) if m_nasa else None
            pair_rows.append(r)

            def bad(field, said, true, note=""):
                mism.append({"mission": mission, "rank": p["rank"], "where": field, "said": said,
                             "recomputed": true, "note": note})

            # --- Earth: nearest place (great circle) and its distance / direction
            if not r["place_is_gc_nearest"]:
                bad("earth nearest place (bundle, AUDIO_TOP5, transcript)", f"{r['b_place']} {r['b_km']:.1f} km",
                    f"{r['gc_name']} {r['gc_km']:.1f} km",
                    "the bundle's place is the reverse_geocoder KD-tree nearest in (lat, lon) degrees, not the "
                    "great-circle nearest")
            if r["a_dir"] != r["dir_from_deg_place"]:
                bad("AUDIO_TOP5 direction", r["a_dir"], r["dir_from_deg_place"])
            if pe:
                if pe["place"] != r["a_place"]:
                    bad("transcript place", pe["place"], r["a_place"])
                if pe["dir"] != r["a_dir"].replace("-", ""):
                    bad("transcript direction", pe["dir"], r["a_dir"])
                spoken_said = int(round(r["a_km"]))
                if abs(pe["km"] - r["a_km"]) > 0.5:
                    bad("transcript distance (rounding)", f"about {pe['km']:g} km",
                        f"{r['a_km']:.1f} km (AUDIO_TOP5 speakable: about {spoken_said} km)",
                        "rounded to tens in the recording; still 'about'")
            else:
                bad("transcript earth phrase", t[:80], "", "could not parse")
            # region / country
            if r["a_country"] != r["b_country"]:
                bad("AUDIO_TOP5 country", r["a_country"], r["b_country"])
            if (r["a_region"] or None) != (r["b_region"] or None):
                bad("AUDIO_TOP5 region", r["a_region"], r["b_region"])
            # --- Moon
            if not r["feature_ok"]:
                bad("lunar nearest feature (bundle)", f"{r['b_feature']} {r['b_fkm']:.1f} km",
                    f"{r['f_name']} {r['f_km']:.1f} km")
            if r["a_feature"] != r["f_name"] or abs(r["a_fkm"] - r["f_km"]) > 0.05:
                bad("AUDIO_TOP5 feature", f"{r['a_feature']} {r['a_fkm']}", f"{r['f_name']} {r['f_km']:.1f}")
            if pm and pm["feature"] != r["f_name"]:
                bad("transcript feature", pm["feature"], r["f_name"])
            if pm and pm["km"] is not None and abs(pm["km"] - r["f_km"]) > 0.5:
                bad("transcript feature distance", pm["km"], round(r["f_km"], 1))
            # NASA regions (lunar base)
            if mission == "lunar_base":
                own = [x["region"] for x in json.loads(r["artemis_regions_own"])]
                said = json.loads(r["a_nasa_regions"]) or []
                if sorted(own) != sorted(said):
                    bad("NASA candidate region(s) of the twin cell", said, own)
                if r["t_nasa_region"] and r["t_nasa_region"] not in own:
                    bad("transcript NASA region", r["t_nasa_region"], own)
    pairs = pd.DataFrame(pair_rows)
    pairs.to_csv(os.path.join(C.OUT, "p1_names_pairs.csv"), index=False)

    # ------------------------------------------------ random sample of 60 more ranked points
    rng = np.random.default_rng(SEED)
    samp_rows = []
    for mission in MISSIONS:
        d = C.ranked_points(b, mission)
        d = d[d["rank"].notna() & (d["rank"] > 5)].sort_values("earth_id").reset_index(drop=True)
        pick = np.sort(rng.choice(len(d), size=N_PER_MISSION, replace=False))
        for k in pick:
            eid, mid = int(d.at[k, "earth_id"]), int(d.at[k, "twin"])
            r = recompute(eid, mid)
            r["mission"] = mission
            r["rank"] = int(d.at[k, "rank"])
            samp_rows.append(r)
    samp = pd.DataFrame(samp_rows)
    samp.to_csv(os.path.join(C.OUT, "p1_names_sample.csv"), index=False)

    # whole-bundle check of the place rule (every land cell), to size the KD-tree effect
    lat_all, lon_all = C.cell_centre(ids)
    from scipy.spatial import cKDTree
    # own 3-D unit-vector tree = great-circle nearest
    def unit(la, lo):
        la, lo = np.radians(la), np.radians(lo)
        return np.c_[np.cos(la) * np.cos(lo), np.cos(la) * np.sin(lo), np.sin(la)]
    tree = cKDTree(unit(gn["lat"].to_numpy(), gn["lon"].to_numpy()))
    _, gi = tree.query(unit(lat_all, lon_all))
    gc_km_all = C.gc_km(lat_all, lon_all, gn["lat"].to_numpy()[gi], gn["lon"].to_numpy()[gi], C.R_EARTH_KM)
    bname = np.array([pdetail["nearest_places"][int(i)] for i in np_idx])
    same = (bname == gn["name"].to_numpy()[gi]) & (np.abs(np_km - gc_km_all) < 0.05)
    longer = np_km - gc_km_all

    # ranked points of each mission: how many carry a non-nearest place
    ranked_stats = {}
    for mission in MISSIONS:
        d = C.ranked_points(b, mission)
        d = d[d["rank"].notna()]
        li = d["land_index"].to_numpy()
        ranked_stats[mission] = {"ranked": int(len(d)), "place_not_gc_nearest": int((~same[li]).sum()),
                                 "median_extra_km_when_wrong": float(np.median(longer[li][~same[li]])) if (~same[li]).any() else 0.0,
                                 "max_extra_km": float(longer[li].max())}

    # lunar features over every lunar cell
    mlat_all, mlon_all = C.cell_centre(np.arange(64800))
    ftree = cKDTree(unit(iau["lat"].to_numpy(), iau["lon"].to_numpy()))
    _, fi = ftree.query(unit(mlat_all, mlon_all))
    f_km_all = C.gc_km(mlat_all, mlon_all, iau["lat"].to_numpy()[fi], iau["lon"].to_numpy()[fi], C.R_MOON_KM)
    bnames = np.array(feats["name"])[m_feat.astype(int)]
    fsame = (bnames == iau["name"].to_numpy()[fi]) & (np.abs(m_fkm - f_km_all) < 0.05)

    summary = {
        "seed": SEED,
        "radii_km": {"EARTH": C.R_EARTH_KM, "MOON": C.R_MOON_KM},
        "geonames_file": {"path": C.RG_CSV, "rows": int(len(gn)), "sha256": sha256(C.RG_CSV),
                          "package": "reverse_geocoder 1.5.1 (PyPI; licence field 'lgpl'); data GeoNames cities1000 (CC BY 4.0 per GeoNames); snapshot date of the GeoNames extract: not stated in the package"},
        "iau_extract": {"path": C.IAU_CSV, "rows": iau_rows, "non_satellite": int(len(iau)), "sha256": sha256(C.IAU_CSV)},
        "iau_vs_raw_zip": check_iau_against_raw(iau),
        "earth_place_rule_all_land_cells": {"land_cells": int(len(ids)), "bundle_place_is_gc_nearest": int(same.sum()),
                                            "not_nearest": int((~same).sum()),
                                            "extra_km_when_not_nearest_median": float(np.median(longer[~same])),
                                            "extra_km_max": float(longer.max())},
        "earth_place_rule_ranked": ranked_stats,
        "lunar_feature_rule_all_cells": {"cells": 64800, "bundle_feature_is_gc_nearest": int(fsame.sum())},
        "pairs_place_not_nearest": int((~pairs["place_is_gc_nearest"]).sum()),
        "sample_place_not_nearest": int((~samp["place_is_gc_nearest"]).sum()),
        "sample_feature_not_nearest": int((~samp["feature_ok"]).sum()),
        "mismatches": len(mism),
    }
    pd.DataFrame(mism).to_csv(os.path.join(C.OUT, "p1_names_mismatches.csv"), index=False)
    C.write_json("p1_names_summary.json", summary)
    print(json.dumps(summary, indent=1, default=C._default))
    print(pd.DataFrame(mism).to_string())


if __name__ == "__main__":
    main()
