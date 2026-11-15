"""Point 8: sensitivity of the spoken Earth distances and directions to the Earth model.
Own spherical haversine (R 6371 km, as p4_common) against the WGS84 ellipsoid (pyproj Geod, an
independent library), for the named place of each of the 15 pair tracks (place coordinates from the
GeoNames cities1000 copy in reverse_geocoder, matched by name and nearest distance).

Run:  <venv python> "tierra luna/audit/p4_geodesy.py"  ->  tierra luna/audit/out/p4_geodesy.json
"""
from __future__ import annotations

import csv
import json
import os
import sys

import numpy as np
import reverse_geocoder
from pyproj import Geod

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from p4_common import OUT, R_EARTH, compass8, haversine_km, initial_bearing_deg  # noqa: E402

FACTS = os.path.join(OUT, "p4_audio_facts.json")
GEONAMES = os.path.join(os.path.dirname(reverse_geocoder.__file__), "rg_cities1000.csv")
SPOKEN = {("rover", 1): (66, "northwest"), ("rover", 2): (80, "north"), ("rover", 3): (78, "northeast"),
          ("rover", 4): (28, "northeast"), ("rover", 5): (41, "southeast"),
          ("solar", 1): (130, "northeast"), ("solar", 2): (280, "northeast"), ("solar", 3): (80, "northeast"),
          ("solar", 4): (280, "northwest"), ("solar", 5): (220, "northeast"),
          ("lunar_base", 1): (62, "north"), ("lunar_base", 2): (44, "southeast"), ("lunar_base", 3): (46, "north"),
          ("lunar_base", 4): (4, "southeast"), ("lunar_base", 5): (53, "south")}


def main():
    facts = json.load(open(FACTS, encoding="utf-8"))
    gn = list(csv.DictReader(open(GEONAMES, encoding="utf-8")))
    g = Geod(ellps="WGS84")
    out = {}
    for (mid, r), (km_said, dir_said) in SPOKEN.items():
        it = facts[mid][r - 1]
        la, lo = it["earth_latlon"]
        name = it["earth_place_own"]["name"]
        cands = [x for x in gn if x["name"] == name]
        best = min(cands, key=lambda x: float(haversine_km(la, lo, float(x["lat"]), float(x["lon"]), R_EARTH)))
        plat, plon = float(best["lat"]), float(best["lon"])
        d_s = float(haversine_km(plat, plon, la, lo, R_EARTH))
        b_s = initial_bearing_deg(plat, plon, la, lo)
        az, _, d_e = g.inv(plon, plat, lo, la)
        b_e = az % 360
        out[f"{mid}_{r}"] = {"place": name, "place_latlon": [plat, plon], "cell_centre": [la, lo],
                             "sphere_km": round(d_s, 3), "wgs84_km": round(d_e / 1000, 3),
                             "sphere_bearing": round(b_s, 2), "wgs84_bearing": round(b_e, 2),
                             "compass_sphere": compass8(b_s), "compass_wgs84": compass8(b_e),
                             "spoken_km": km_said, "spoken_direction": dir_said,
                             "direction_ok_both": compass8(b_s) == dir_said == compass8(b_e)}
    with open(os.path.join(OUT, "p4_geodesy.json"), "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1, sort_keys=True)
    for k, v in out.items():
        print(k, v["place"], v["sphere_km"], v["wgs84_km"], v["spoken_km"], v["sphere_bearing"], v["wgs84_bearing"],
              v["spoken_direction"], v["direction_ok_both"])


if __name__ == "__main__":
    main()
