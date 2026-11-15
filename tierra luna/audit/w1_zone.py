"""w1: Lunar base zone rule (question 1). Options, computed in memory, nothing applied:
 (a) as now: 1-degree cells whose square TOUCHES the footprint of the nine regions;
 (b) cells whose CENTRE is inside a region;
 (c) cells with >= 50 % of their area inside the footprint (union of the nine);
 (d) cells with >= 5 %.
Areas in a south-polar Lambert azimuthal equal-area projection (sphere R = 1737.4 km), cell
squares densified along the parallels. For each option the whole Lunar base pairing is recomputed
(the lunar percentile population changes with the zone).

    python "tierra luna/audit/w1_zone.py"

Writes audit/out/w1_zone.json and w1_zone_cells.csv.
"""
import os

import numpy as np
import pandas as pd
from shapely.geometry import Point, Polygon, shape
from shapely.ops import transform, unary_union

from w_common import OUT, TL, audio_top5, base_run, compare_tracks, dump, jload, latlon, load, run, summary

R = 1737400.0


def laea(lon, lat):
    lon = np.radians(np.asarray(lon, float))
    colat = np.radians(90.0 + np.asarray(lat, float))
    rho = 2 * R * np.sin(colat / 2)
    return rho * np.sin(lon), rho * np.cos(lon)


def cell_poly(la, lo, n=40):
    lons = np.linspace(lo - 0.5, lo + 0.5, n)
    top = np.column_stack(laea(lons, np.full(n, la + 0.5)))
    bot = np.column_stack(laea(lons[::-1], np.full(n, la - 0.5)))
    return Polygon(np.vstack([top, bot]))


def main():
    eng, ms, e, m = load()
    g = jload(os.path.join(TL, "engine", "data", "artemis_iii_regions.geojson"))
    names = [f["properties"]["name"] for f in g["features"]]
    polys = [transform(lambda x, y, z=None: laea(x, y), shape(f["geometry"])) for f in g["features"]]
    foot = unary_union(polys)
    base = base_run("lunar_base")
    zone_a = np.zeros(64800, bool)
    zone_a[base["zone"]] = True
    rows = []
    cand = np.flatnonzero(m["lat_deg"].to_numpy() < -80)
    for cid in cand:
        la, lo = latlon(cid)
        cp = cell_poly(la, lo)
        if not cp.intersects(foot) and not zone_a[cid]:
            continue
        area = cp.area
        fr = cp.intersection(foot).area / area
        per = {names[k]: p.intersection(cp).area / area for k, p in enumerate(polys) if p.intersects(cp)}
        cx, cy = laea(lo, la)
        cin = [names[k] for k, p in enumerate(polys) if p.contains(Point(cx, cy))]
        rows.append({"moon_id": int(cid), "lat": la, "lon": lo, "zone_a": bool(zone_a[cid]), "frac_footprint": fr,
                     "centre_in": ";".join(cin), "regions_touched": ";".join(per),
                     "frac_by_region": ";".join(f"{k}:{v:.5f}" for k, v in per.items())})
    df = pd.DataFrame(rows).sort_values("moon_id")
    df.to_csv(os.path.join(OUT, "w1_zone_cells.csv"), index=False)
    print("zone (a) recomputed by touch in LAEA:", int((df.frac_footprint > 0).sum() | 0), "cells with area>0;",
          "zone_a cells", int(df.zone_a.sum()), "of which outside every square in LAEA:", int((df.zone_a & (df.frac_footprint <= 0)).sum()))

    opts = {"b_centre_inside": df.loc[df.centre_in != "", "moon_id"].to_numpy(),
            "c_area_ge_50pct": df.loc[df.frac_footprint >= 0.5, "moon_id"].to_numpy(),
            "d_area_ge_5pct": df.loc[df.frac_footprint >= 0.05, "moon_id"].to_numpy()}
    out = {"method": __doc__, "options": {}}
    # (a): share of each current top-5 twin inside its region
    sa = summary(base)
    for t in sa["top"]:
        rr = df[df.moon_id == int(t["moon_id"][1:])].iloc[0]
        t["twin_frac_footprint"] = round(float(rr.frac_footprint), 5)
        t["twin_frac_by_region"] = rr.frac_by_region
        t["twin_centre_in"] = rr.centre_in
    sa["tracks"], sa["tracks_broken"] = compare_tracks("lunar_base", sa["top"], base)
    out["options"]["a_touch_as_now"] = sa
    print("a", sa["zone_cells"], sa["passing"], sa["paired"], sa["distinct_twins"])
    for t in sa["top"]:
        print("   ", t["rank"], t["earth_id"], t["moon_id"], t["twin_frac_footprint"], t["twin_frac_by_region"])
    for k, ids in opts.items():
        zm = np.zeros(64800, bool)
        zm[ids] = True
        r = run("lunar_base", zone_override={"lunar_base": zm})
        s = summary(r)
        s["tracks"], s["tracks_broken"] = compare_tracks("lunar_base", s["top"], r)
        s["zone_by_region_centre"] = df[df.moon_id.isin(ids)].centre_in.value_counts().to_dict()
        out["options"][k] = s
        print(k, "zone", s["zone_cells"], "pass", s["passing"], "paired", s["paired"], "twins", s["distinct_twins"],
              "broken tracks", s["tracks_broken"])
        for t in s["top"]:
            print("   ", t["rank"], t["earth_id"], t["earth_place"]["place"], t["moon_id"], t["moon_feature"]["feature"],
                  t["similarity"], t["suitability"], t["final"])
        for tr in s["tracks"]:
            print("      track", tr)
    dump(out, "w1_zone.json")


if __name__ == "__main__":
    main()
