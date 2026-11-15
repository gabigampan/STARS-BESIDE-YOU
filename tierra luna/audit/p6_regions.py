"""Point C (3), Lunar base: for each lunar cell of the 5 Lunar base pairs, the share of the 1-degree cell
inside each of NASA's nine candidate regions (engine data artemis_iii_regions.geojson), whether the cell
centre lies inside, and the distance from the centre to the nearest edge of each region; own code
(south polar stereographic plane on the 1737.4 km sphere; scale error < 0.2 % poleward of 83 S).
Run:  $PY -I "tierra luna/audit/p6_regions.py"      Output: out/p6_regions.json
"""
import json
import os
import sys

import numpy as np
from pyproj import CRS, Transformer
from shapely.geometry import Point, Polygon

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from p6_common import ENGINE_DATA, REPO, R_MOON, dump  # noqa: E402

sp = CRS.from_proj4(f"+proj=stere +lat_0=-90 +lon_0=0 +k=1 +R={R_MOON*1000} +units=m +no_defs")
geo = CRS.from_proj4(f"+proj=longlat +R={R_MOON*1000} +no_defs")
T = Transformer.from_crs(geo, sp, always_xy=True)
reg = json.load(open(os.path.join(ENGINE_DATA, "artemis_iii_regions.geojson"), encoding="utf-8"))
polys = {}
for f in reg["features"]:
    ring = np.array(f["geometry"]["coordinates"][0])
    x, y = T.transform(ring[:, 0], ring[:, 1])
    polys[f["properties"]["name"]] = Polygon(np.c_[x, y]).buffer(0)


def cell_poly(lat, lon, n=40):
    lons = np.r_[np.linspace(lon - .5, lon + .5, n), np.full(n, lon + .5), np.linspace(lon + .5, lon - .5, n), np.full(n, lon - .5)]
    lats = np.r_[np.full(n, lat - .5), np.linspace(lat - .5, lat + .5, n), np.full(n, lat + .5), np.linspace(lat + .5, lat - .5, n)]
    x, y = T.transform(lons, lats)
    return Polygon(np.c_[x, y]).buffer(0)


top = json.load(open(os.path.join(REPO, "docs", "AUDIO_TOP5.json"), encoding="utf-8"))
out = {"region_names_in_engine_file": sorted(polys)}
rows = []
for p in top["missions"]["lunar_base"]["pairs"]:
    mp = p["moon_place"]
    lat, lon = mp["cell_centre_lat"], mp["cell_centre_lon"]
    cp = cell_poly(lat, lon)
    c = Point(*T.transform(lon, lat))
    d = {n: round(pg.exterior.distance(c) / 1000, 1) * (-1 if pg.contains(c) else 1) for n, pg in polys.items()}
    rows.append(dict(rank=p["rank"], moon=p["moon_cell_id"], lat=lat, lon=lon, audio_region=mp.get("nasa_candidate_regions_intersected"),
                     cell_area_km2=round(cp.area / 1e6, 1),
                     share_of_cell_in_region={n: round(pg.intersection(cp).area / cp.area, 4) for n, pg in polys.items() if pg.intersects(cp)},
                     region_area_inside_cell_km2={n: round(pg.intersection(cp).area / 1e6, 2) for n, pg in polys.items() if pg.intersects(cp)},
                     centre_to_region_edge_km_negative_inside=dict(sorted(d.items(), key=lambda kv: kv[1])[:3])))
out["lunar_base_cells"] = rows
dump("p6_regions.json", out)
print(json.dumps(out, indent=1))
