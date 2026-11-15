"""C3 (second independent auditor): permanent ice at cell E4037 (78-79 N, 103-102 W).

Sources, independent of ESA CCI LC (the model's land cover):
 (a) Natural Earth 1:10m glaciated areas, GitHub mirror nvkelso/natural-earth-vector (master).
 (b) ESA WorldCover 2021 v200 (Sentinel-1/2, 10 m), public bucket esa-worldcover, tile N78W105,
     read at a coarse COG overview (windowed HTTP range reads).
Usage: python -I c3_hielo_E4037.py <download_dir> <out_json>
"""
import json, sys, urllib.request, os
import numpy as np
from shapely.geometry import shape, box
import rasterio
from rasterio.windows import from_bounds

dl, out = sys.argv[1], sys.argv[2]
CELL = box(-103.0, 78.0, -102.0, 79.0)
res = {"cell": "E4037", "bounds_lonlat": [-103, 78, -102, 79]}

# (a) Natural Earth
ne_url = "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/ne_10m_glaciated_areas.geojson"
ver_url = "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/VERSION"
p = os.path.join(dl, "glac.geojson")
if not os.path.exists(p):
    urllib.request.urlretrieve(ne_url, p)
try:
    ne_ver = urllib.request.urlopen(ver_url, timeout=30).read().decode().strip()
except Exception as e:  # noqa
    ne_ver = f"not reached ({e})"
g = json.load(open(p))
inter, near = 0.0, []
for f in g["features"]:
    s = shape(f["geometry"])
    if not s.is_valid:
        s = s.buffer(0)
    if s.intersects(CELL):
        inter += s.intersection(CELL).area
    d = s.distance(CELL)
    if d < 1.0:
        near.append(round(d, 3))
# planar degree areas; within a 1-deg cell the cos(lat) factor cancels in the share
res["natural_earth"] = {
    "product": "Natural Earth 1:10m Physical, glaciated areas (ne_10m_glaciated_areas)",
    "version": ne_ver, "url": ne_url, "n_features": len(g["features"]),
    "share_of_cell": inter / CELL.area,
    "nearest_polygon_distance_deg_within_1deg": sorted(near)[:5],
}

# (b) ESA WorldCover 2021 v200
wc_url = "https://esa-worldcover.s3.eu-central-1.amazonaws.com/v200/2021/map/ESA_WorldCover_10m_2021_v200_N78W105_Map.tif"
env = rasterio.Env(GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR", CPL_VSIL_CURL_ALLOWED_EXTENSIONS=".tif",
                   GDAL_HTTP_MERGE_CONSECUTIVE_RANGES="YES")
with env:
    with rasterio.open("/vsicurl/" + wc_url) as src0:
        ovr = src0.overviews(1)
    lvl = 2 if len(ovr) > 2 else len(ovr) - 1  # factor ~ 8 -> ~80 m pixels
    with rasterio.open("/vsicurl/" + wc_url, overview_level=lvl) as src:
        win = from_bounds(-103.0, 78.0, -102.0, 79.0, src.transform).round_offsets().round_lengths()
        a = src.read(1, window=win)
        info = {"overviews": ovr, "overview_level_used": lvl, "factor": ovr[lvl],
                "pixel_deg": [src.transform.a, -src.transform.e], "window_shape": list(a.shape)}
valid = a[a != 0]
names = {10: "tree", 20: "shrub", 30: "grass", 40: "crop", 50: "built", 60: "bare/sparse",
         70: "snow and ice", 80: "permanent water", 90: "herbaceous wetland", 95: "mangrove", 100: "moss and lichen"}
vals, cnt = np.unique(valid, return_counts=True)
share = {f"{int(v)} {names.get(int(v), '?')}": float(c) / valid.size for v, c in zip(vals, cnt)}
res["worldcover"] = {
    "product": "ESA WorldCover 10 m 2021 v200 (Sentinel-1/2; produced independently of CCI LC)",
    "url": wc_url, **info, "n_valid": int(valid.size), "n_nodata0": int((a == 0).sum()),
    "class_share": share,
    "share_70_snow_ice": share.get("70 snow and ice", 0.0),
    "share_80_water": share.get("80 permanent water", 0.0),
    "share_60_bare_sparse": share.get("60 bare/sparse", 0.0),
    "note": "overview pixels are a decimated (nearest/mode) sample of the 10 m map",
}
json.dump(res, open(out, "w"), indent=1)
print(json.dumps(res, indent=1))
