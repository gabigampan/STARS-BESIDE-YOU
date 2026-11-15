"""Point 7: how much of each Lunar base twin cell lies inside the NASA candidate region the audio
names, measured on the Moon sphere (not in degree space), and how far the cell centre is from it.

    <venv>/bin/python "tierra luna/audit/p1_regions.py"

Own code: both the 1-degree cell (densified edges) and the region polygons of
engine/data/artemis_iii_regions.geojson are projected to a south-polar Lambert azimuthal
equal-area projection on the 1737.4 km sphere (pyproj, +R=1737400), then intersected (shapely).
Writes out/p1_regions.csv. Also checks the 280-cell zone count with the same intersection rule.
"""
from __future__ import annotations

import os
import sys

import numpy as np
import pandas as pd

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import p1_common as C  # noqa: E402


def main():
    from pyproj import Transformer
    from shapely.geometry import Polygon, Point, shape
    from shapely.ops import transform
    tr = Transformer.from_crs("+proj=longlat +R=1737400 +no_defs",
                              "+proj=laea +lat_0=-90 +lon_0=0 +R=1737400 +units=m +no_defs", always_xy=True)
    proj = lambda g: transform(lambda x, y, z=None: tr.transform(x, y), g)
    gj = C.jload(C.ARTEMIS)
    regs = [(f["properties"]["name"], shape(f["geometry"])) for f in gj["features"]]
    regs_p = [(n, proj(g)) for n, g in regs]

    def cell_poly(lat, lon, n=50):
        s, w, nn, e = lat - 0.5, lon - 0.5, lat + 0.5, lon + 0.5
        pts = [(w + (e - w) * k / n, s) for k in range(n)] + [(e, s + (nn - s) * k / n) for k in range(n)] + \
              [(e - (e - w) * k / n, nn) for k in range(n)] + [(w, nn - (nn - s) * k / n) for k in range(n)]
        return proj(Polygon(pts))

    top = C.jload(os.path.join(C.REPO, "docs", "AUDIO_TOP5.json"))
    trans = C.jload(os.path.join(C.REPO, "app", "public", "audio", "transcripts.json"))
    rows = []
    for p in top["missions"]["lunar_base"]["pairs"]:
        mid = int(p["moon_cell_id"][1:])
        lat, lon = map(float, C.cell_centre(mid))
        cp = cell_poly(lat, lon)
        cen = proj(Point(lon, lat))
        said = p["moon_place"].get("nasa_candidate_regions_intersected")
        for name, g in regs_p:
            inter = g.intersection(cp).area
            d = g.distance(cen) / 1000.0
            if inter > 0 or d < 30:
                rows.append({"rank": p["rank"], "moon_cell": p["moon_cell_id"], "lat": lat, "lon": lon,
                             "region": name, "named_in_audio": name in (said or []),
                             "cell_area_km2": cp.area / 1e6, "overlap_km2": inter / 1e6,
                             "overlap_share": inter / cp.area, "centre_inside": g.contains(cen),
                             "centre_to_region_km": d, "transcript": trans[f"base_{p['rank']}.mp3"].split(". ")[2]})
    df = pd.DataFrame(rows)
    df.to_csv(os.path.join(C.OUT, "p1_regions.csv"), index=False, float_format="%.4f")
    # zone count with the same rule (any positive overlap of the 1-degree square), only |lat|>=75 S cells
    n = 0
    for mid in range(64800):
        lat, lon = map(float, C.cell_centre(mid))
        if lat > -75:
            continue
        cp = cell_poly(lat, lon, n=8)
        if any(g.intersects(cp) for _, g in regs_p):
            n += 1
    pd.set_option("display.width", 250)
    print(df.drop(columns=["transcript"]).round(4).to_string())
    print("zone cells by own equal-area intersection:", n)
    with open(os.path.join(C.OUT, "p1_regions_zone_count.txt"), "w") as fh:
        fh.write(f"{n}\n")


if __name__ == "__main__":
    main()
