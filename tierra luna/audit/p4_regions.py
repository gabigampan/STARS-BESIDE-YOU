"""Point 8, Lunar base tracks: how much of each top-5 twin cell lies inside the NASA region the
track names, and whether the cell centre is inside it (own code: south polar stereographic on the
1737.4 km sphere, cell edges densified, shapely for the geometry). Does not import the engine.

Run:  <venv python> "tierra luna/audit/p4_regions.py"   ->  tierra luna/audit/out/p4_regions.json
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np
from shapely.geometry import Point, Polygon, shape
from shapely.ops import unary_union

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from p4_common import ENGINE_DATA, OUT, R_MOON, cell_latlon  # noqa: E402

TWINS = {"base_1": (63528, "Haworth"), "base_2": (63841, "de Gerlache Rim 2"), "base_3": (64018, "Slater Plain"),
         "base_4": (62517, "Nobile Rim 2"), "base_5": (62523, "Nobile Rim 2")}


def st(lat, lon):
    k = 2 * R_MOON * np.tan(np.pi / 4 + np.radians(lat) / 2)
    return k * np.sin(np.radians(lon)), k * np.cos(np.radians(lon))


def main():
    gj = json.load(open(os.path.join(ENGINE_DATA, "artemis_iii_regions.geojson"), encoding="utf-8"))
    regs = {}
    for f in gj["features"]:
        g = shape(f["geometry"])
        ps = [g] if g.geom_type == "Polygon" else list(g.geoms)
        regs[f["properties"]["name"]] = unary_union([Polygon([st(c[1], c[0]) for c in p.exterior.coords]) for p in ps])
    out = {"n_regions": len(regs), "regions": sorted(regs)}
    for track, (cid, name) in TWINS.items():
        la, lo = cell_latlon(cid)
        t = np.linspace(0, 1, 201)
        lat = np.concatenate([np.full(201, la - .5), la - .5 + t, np.full(201, la + .5), la + .5 - t])
        lon = np.concatenate([lo - .5 + t, np.full(201, lo + .5), lo + .5 - t, np.full(201, lo - .5)])
        cell = Polygon(list(zip(*st(lat, lon))))
        r = regs[name]
        c = Point(*st(la, lo))
        out[track] = {"cell": cid, "centre": [la, lo], "region_named": name,
                      "centre_inside": bool(r.contains(c)),
                      "centre_to_region_km": round(float(r.distance(c)), 2),
                      "cell_area_km2": round(cell.area, 1),
                      "share_of_cell_in_region": round(cell.intersection(r).area / cell.area, 4),
                      "other_regions_touched": sorted(n for n, g in regs.items() if n != name and g.intersects(cell))}
    # the whole zone: 280 cells of moon_base.bin region A (bundle, own reader)
    from p4_common import Bundle
    B = Bundle()
    reg = B.col("moon_base.bin", "region")
    codes = [r["code"] for r in B.json("mission_zones.json")["regions"]]
    zone = [i for i in range(reg.size) if codes[int(reg[i])] == "A"]
    allr = unary_union(list(regs.values()))
    shares, inside = [], 0
    for cid in zone:
        la, lo = cell_latlon(cid)
        t = np.linspace(0, 1, 41)
        lat = np.concatenate([np.full(41, la - .5), la - .5 + t, np.full(41, la + .5), la + .5 - t])
        lon = np.concatenate([lo - .5 + t, np.full(41, lo + .5), lo + .5 - t, np.full(41, lo - .5)])
        cell = Polygon(list(zip(*st(lat, lon))))
        shares.append(cell.intersection(allr).area / cell.area)
        inside += int(allr.contains(Point(*st(la, lo))))
    s = np.array(shares)
    out["zone_A"] = {"cells": len(zone), "centre_inside_a_region": inside,
                     "share_ge_50pct": int((s >= 0.5).sum()), "share_lt_5pct": int((s < 0.05).sum()),
                     "median_share": round(float(np.median(s)), 4)}
    with open(os.path.join(OUT, "p4_regions.json"), "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1, sort_keys=True)
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
