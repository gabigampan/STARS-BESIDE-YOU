"""Metric 6: every ranked point falls where it says.

Checks, on EVERY ranked (paired) point of each mission in the shipped bundle (not a
sample: 10,192 + 6,360 + 450 points):
  (a) the stored cell centre lies inside the cell its id names;
  (b) the centre is on land by an independent mask: point-in-polygon against the
      Natural Earth 1:110m admin-0 polygons already in engine/data (this script's own
      shapely call; the engine's labelling code is not used), and, for centres outside
      every polygon, whether any polygon touches the 1-degree cell;
  (c) the country the bundle names equals the polygon that contains the centre
      (ISO code, or the polygon's ADMIN name where Natural Earth has no ISO code);
      centres outside every polygon are checked against the named country's polygon
      touching the cell; Antarctic cells (label rule antarctic_treaty_area) are checked
      for latitude only;
  (d) the region: no admin-1 polygons exist in the repository, so the region the bundle
      names (GeoNames admin-1 of the nearest populated place) cannot be checked against
      polygons; reported: share labelled and distance to the place it comes from;
  (e) each lunar twin's nearest named feature and distance recomputed from the IAU file
      (engine/data/iau_moon_nomenclature.csv) with this script's own great-circle code,
      on the sphere and feature-type exclusion stated in engine_config.json.
"""
from __future__ import annotations

import json
from typing import Dict

import numpy as np
import pandas as pd

from common import (ENGINE_CONFIG, IAU_CSV, MISSIONS, NE_GEOJSON, bundle, haversine_km, load_json, write_csv)


def ne_polygons():
    from shapely.geometry import shape
    gj = load_json(NE_GEOJSON)
    polys = []
    for f in gj["features"]:
        p = f["properties"]
        code = str(p.get("ISO_A2") or "").strip()
        polys.append({"code": code if len(code) == 2 and code.isalpha() else None, "name": p.get("ADMIN"),
                      "geom": shape(f["geometry"])})
    return polys


def run() -> Dict:
    from shapely.geometry import Point, box
    from shapely.strtree import STRtree
    b = bundle()
    miss = b.manifest["encoding"]["int32_missing"]
    ids = b.int_column("earth_base.bin", "id")
    lat_r, lon_c = b.column("earth_base.bin", "lat"), b.column("earth_base.bin", "lon")
    rows_, cols_ = ids // 360, ids % 360
    lat, lon = lat_r[rows_], lon_c[cols_]
    country = b.int_column("earth_base.bin", "country")
    region = b.int_column("earth_base.bin", "region")
    places = b.json("places.json")
    rule = b.int_column("earth_place_detail.bin", "label_rule")
    place_km = b.column("earth_place_detail.bin", "nearest_place_km")
    pdj = b.json("place_detail.json")
    rule_names = pdj.get("label_rules") or pdj.get("rules")
    polys = ne_polygons()
    tree = STRtree([p["geom"] for p in polys])
    ecfg = load_json(ENGINE_CONFIG)
    ant_lat = float(ecfg["antarctic_label_lat_max"]["value"])
    summ, fails = [], []
    for m in MISSIONS:
        f = f"earth_{m}.bin"
        li = b.int_column(f, "land_index")
        rank = b.int_column(f, "rank")
        sel = li[rank != miss]
        n = len(sel)
        cnt = {"mission": m, "ranked_points_checked": n}
        # (a)
        r, cc = rows_[sel], cols_[sel]
        inside = (lat[sel] < 90 - r) & (lat[sel] > 89 - r) & (lon[sel] > -180 + cc) & (lon[sel] < -179 + cc)
        cnt["centre_inside_cell"] = int(inside.sum())
        # (b), (c)
        on_land = cell_touch = agree = agree_touch = disagree = no_label = ant_ok = ant_n = 0
        rlabelled = 0
        for k, i in enumerate(sel):
            pt = Point(float(lon[i]), float(lat[i]))
            hit = [j for j in tree.query(pt, predicate="within")]
            hit = sorted(int(j) for j in hit)
            cbox = box(float(lon[i]) - 0.5, float(lat[i]) - 0.5, float(lon[i]) + 0.5, float(lat[i]) + 0.5)
            touch = sorted(int(j) for j in tree.query(cbox, predicate="intersects"))
            if hit:
                on_land += 1
            elif touch:
                cell_touch += 1
            ci = country[i]
            if region[i] != miss:
                rlabelled += 1
            if ci == miss:
                no_label += 1
                fails.append({"mission": m, "id": int(ids[i]), "kind": "no_country_label", "detail": ""})
                continue
            bc = places["countries"][ci]
            rn = rule_names[rule[i]] if rule_names and 0 <= rule[i] < len(rule_names) else str(rule[i])
            rn = rn if isinstance(rn, str) else rn.get("code", str(rn))
            if bc["code"] == "AQ":
                ant_n += 1
                if lat[i] <= ant_lat:
                    ant_ok += 1
                else:
                    fails.append({"mission": m, "id": int(ids[i]), "kind": "antarctic_label_north_of_limit", "detail": f"lat {lat[i]}"})
                continue

            def same(j):
                p = polys[j]
                return (p["code"] == bc["code"]) if p["code"] else (p["name"] == bc["name"])
            if hit:
                if same(hit[0]):
                    agree += 1
                else:
                    disagree += 1
                    fails.append({"mission": m, "id": int(ids[i]), "kind": "country_differs_from_polygon",
                                  "detail": f"bundle {bc['code']} {bc['name']}; polygon {polys[hit[0]]['code']} {polys[hit[0]]['name']}"})
            else:
                if any(same(j) for j in touch):
                    agree_touch += 1
                else:
                    disagree += 1
                    near = ", ".join(f"{polys[j]['code']} {polys[j]['name']}" for j in touch) or "no polygon touches the cell"
                    fails.append({"mission": m, "id": int(ids[i]), "kind": "centre_off_polygons_named_country_not_in_cell",
                                  "detail": f"bundle {bc['code']} {bc['name']}; touching: {near}; rule {rn}"})
        off = n - on_land
        cnt.update({"centre_on_NE_land": on_land, "centre_off_land_but_cell_touches_land": cell_touch,
                    "no_land_polygon_in_cell": n - on_land - cell_touch,
                    "country_agrees_centre_polygon": agree, "country_agrees_polygon_touching_cell": agree_touch,
                    "country_disagrees": disagree, "antarctic_label": ant_n, "antarctic_label_lat_ok": ant_ok,
                    "no_country_label": no_label, "region_labelled": rlabelled,
                    "nearest_place_km_median": float(np.nanmedian(place_km[sel])),
                    "nearest_place_km_p90": float(np.nanpercentile(place_km[sel], 90))})
        summ.append(cnt)
    # (e) lunar twins: nearest primary IAU feature
    feats = pd.read_csv(IAU_CSV)
    excl = set(ecfg["lunar_feature_exclude_types"]["value"])
    feats = feats[~feats["type"].isin(excl)].reset_index(drop=True)
    flat = feats["center_lat"].to_numpy(float)
    flon = ((feats["center_lon_e360"].to_numpy(float) + 180.0) % 360.0) - 180.0
    R = float(ecfg["body_radius_km"]["value"]["MOON"])
    tw = b.json("twins.json")
    twin_rows = []
    for m in MISSIONS:
        for t in tw["missions"][m]["twins"]:
            d = haversine_km(t["lat"], t["lon"], flat, flon, R)
            j = int(np.argmin(d))
            name_ok = feats["name"].iat[j] == t["feature"]["name"]
            km_ok = abs(float(d[j]) - float(t["feature"]["distance_km"])) <= 0.1
            twin_rows.append({"mission": m, "twin": t["id"], "lat": t["lat"], "lon": t["lon"],
                              "bundle_feature": t["feature"]["name"], "bundle_km": t["feature"]["distance_km"],
                              "recomputed_feature": feats["name"].iat[j], "recomputed_km": round(float(d[j]), 3),
                              "name_agrees": bool(name_ok), "km_within_0.1": bool(km_ok)})
            # a twin's cell centre must also be the lunar cell its id names
            row, col = t["id"] // 360, t["id"] % 360
            if abs(t["lat"] - (89.5 - row)) > 1e-6 or abs(t["lon"] - (-179.5 + col)) > 1e-6:
                fails.append({"mission": m, "id": t["id"], "kind": "twin_centre_not_its_cell", "detail": ""})
    tdf = pd.DataFrame(twin_rows)
    write_csv(tdf, "m6_twin_features.csv")
    for s in summ:
        g = tdf[tdf["mission"] == s["mission"]]
        s.update({"distinct_twins": int(len(g)), "twin_feature_name_agrees": int(g["name_agrees"].sum()),
                  "twin_feature_km_agrees": int(g["km_within_0.1"].sum()),
                  "twin_feature_km_median": float(g["recomputed_km"].median()), "twin_feature_km_max": float(g["recomputed_km"].max())})
    sdf = pd.DataFrame(summ)
    write_csv(sdf, "m6_coordinates_summary.csv")
    fdf = pd.DataFrame(fails, columns=["mission", "id", "kind", "detail"]).sort_values(["mission", "kind", "id"], kind="mergesort")
    write_csv(fdf, "m6_coordinate_failures.csv")
    return {"summary": sdf.to_dict("records"), "failures_by_kind": fdf.groupby(["mission", "kind"]).size().reset_index(name="n").to_dict("records")}


if __name__ == "__main__":
    print(json.dumps(run(), indent=1, default=str))
