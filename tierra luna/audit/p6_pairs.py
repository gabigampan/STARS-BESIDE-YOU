"""Point C (report point 12), internal part, own code:
 1. the 15 pairs of docs/AUDIO_TOP5.json against the bundle's current rank 1-5 (decoded from the
    .bin files with the manifest index only);
 2. Earth side: land share, land-cover make-up of the cell from the raw ESA CCI 2020 tiles
    (water 210, snow/ice 220, bare 200-202, sparse 150-153), distance from the cell centre to the
    nearest Natural Earth 110m coastline and to the nearest cell with land share < 0.5;
 3. Moon side: the zone rule recomputed, the NASA region by own polygon intersection in a south
    polar stereographic plane, the nearest primary IAU feature by own great-circle distance.
Run:  $PY -I "tierra luna/audit/p6_pairs.py"      Output: out/p6_pairs.json
"""
import glob
import json
import math
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from p6_common import ENGINE_DATA, OUT, REPO, R_MOON, Bundle, dump, haversine_km, load_tables  # noqa: E402

RAW = "/tmp/claude-0/-home-user-NASA/7228bb30-9725-52d9-8d71-762c955fd0bd/scratchpad/stars/realdata/earth_raw/cci"
top = json.load(open(os.path.join(REPO, "docs", "AUDIO_TOP5.json"), encoding="utf-8"))
e, m = load_tables()
ei, mi = e.set_index("cell_id"), m.set_index("cell_id")
B = Bundle()
res = {"top5_vs_bundle": {}, "earth": {}, "moon": {}}

# ---------------------------------------------------------------- 1. top 5 against the bundle
land_ids = B.col("earth_base.bin", "id")
for mis, x in top["missions"].items():
    f = f"earth_{mis}.bin"
    li = B.col(f, "land_index")
    rank = B.col(f, "rank")
    twin = B.col(f, "twin")
    sim = B.col(f, "similarity")
    fin = B.col(f, "final")
    suit = B.col(f, "suitability")
    rows = []
    for r in range(1, 6):
        k = int(np.where(rank == r)[0][0])
        rows.append(dict(rank=r, earth=f"E{int(land_ids[li[k]])}", moon=f"M{int(twin[k])}", similarity=sim[k], suitability=suit[k], final=fin[k]))
    audio = [dict(rank=p["rank"], earth=p["earth_cell_id"], moon=p["moon_cell_id"], similarity=p["similarity"], suitability=p["suitability"], final=p["final"]) for p in x["pairs"]]
    same = all(a["earth"] == b["earth"] and a["moon"] == b["moon"] and abs(a["final"] - b["final"]) < 0.006
               and abs(a["similarity"] - b["similarity"]) < 0.006 and abs(a["suitability"] - b["suitability"]) < 0.006 for a, b in zip(audio, rows))
    res["top5_vs_bundle"][mis] = dict(identical=bool(same), bundle=rows, audio=audio)

# ---------------------------------------------------------------- 2. Earth cells
import rasterio  # noqa: E402
from shapely.geometry import Point, shape  # noqa: E402
from shapely.ops import unary_union  # noqa: E402

ne = json.load(open(os.path.join(ENGINE_DATA, "ne_110m_admin_0_countries.geojson"), encoding="utf-8"))
landpoly = unary_union([shape(f["geometry"]) for f in ne["features"]])
coast = landpoly.boundary


def coast_km(lat, lon):
    # nearest point on the coastline in lon/lat, then the true great-circle distance; refine by sampling
    from shapely.ops import nearest_points
    p = Point(lon, lat)
    # scale longitude by cos(lat) for a fair nearest search
    best = None
    for geom in getattr(coast, "geoms", [coast]):
        q = nearest_points(p, geom)[1]
        d = float(haversine_km(lat, lon, q.y, q.x, 6371.0088))
        best = d if best is None or d < best else best
    return best, bool(landpoly.contains(p))


def cci_mix(lat, lon):
    tiles = glob.glob(os.path.join(RAW, "*.tif"))
    for t in tiles:
        with rasterio.open(t) as ds:
            b = ds.bounds
            if b.left <= lon < b.right and b.bottom <= lat < b.top:
                win = rasterio.windows.from_bounds(lon - 0.5, lat - 0.5, lon + 0.5, lat + 0.5, ds.transform)
                a = ds.read(1, window=win)
                vals, cnt = np.unique(a, return_counts=True)
                tot = cnt.sum()
                d = {int(v): int(c) for v, c in zip(vals, cnt)}
                share = lambda codes: round(sum(d.get(c, 0) for c in codes) / tot, 4)
                top3 = sorted(d.items(), key=lambda kv: -kv[1])[:3]
                return dict(tile=os.path.basename(t), px=int(tot), water_210=share([210]), snow_ice_220=share([220]),
                            bare_200_202=share([200, 201, 202]), sparse_150_153=share([150, 151, 152, 153]),
                            top3_classes=[(k, round(v / tot, 3)) for k, v in top3])
    return None


mask = e.set_index(["lat_deg", "lon_deg"])["mask_fraction"]
lowland = e[e["mask_fraction"] < 0.5]
for mis, x in top["missions"].items():
    for p in x["pairs"]:
        cid = p["earth_cell_id"]
        if cid in res["earth"]:
            res["earth"][cid]["uses"].append(f"{mis}#{p['rank']}")
            continue
        r = ei.loc[cid]
        lat, lon = float(r.lat_deg), float(r.lon_deg)
        ck, inside = coast_km(lat, lon)
        dwat = haversine_km(lat, lon, lowland.lat_deg.values, lowland.lon_deg.values, 6371.0088)
        j = int(np.argmin(dwat))
        res["earth"][cid] = dict(uses=[f"{mis}#{p['rank']}"], lat=lat, lon=lon, place=p["earth_place"]["speakable"],
                                 mask_fraction=float(r.mask_fraction), bare_frac=float(r.bare_frac), snow_ice_frac=float(r.snow_ice_frac),
                                 rock_or_bare_frac=float(r.rock_or_bare_frac), lc_dominant_cci_code=int(r.lc_dominant_cci_code),
                                 thermal_inertia_class=r.thermal_inertia_class, permafrost_class=r.permafrost_class,
                                 n_dem_land_px=int(r.n_dem_land_px), elevation_m=float(r.elevation_m), slope_iso_deg=float(r.slope_iso_deg),
                                 roughness_m=float(r.roughness_m), tmin_c=float(r.tmin_c), lst_diurnal_amp_k=float(r.lst_diurnal_amp_k),
                                 irradiance_kwh_m2_day=float(r.irradiance_kwh_m2_day), temp_k=float(r.temp_k),
                                 centre_inside_ne110m_land=inside, coast_km_ne110m=round(ck, 1),
                                 nearest_cell_land_share_lt_0_5=dict(cell=e.iloc[j].cell_id, km=round(float(dwat[j]), 1)),
                                 cci=cci_mix(lat, lon))

# ---------------------------------------------------------------- 3. Moon cells
from pyproj import CRS, Transformer  # noqa: E402

moon_sp = CRS.from_proj4(f"+proj=stere +lat_0=-90 +lon_0=0 +k=1 +R={R_MOON*1000} +units=m +no_defs")
geo = CRS.from_proj4(f"+proj=longlat +R={R_MOON*1000} +no_defs")
T = Transformer.from_crs(geo, moon_sp, always_xy=True)
reg = json.load(open(os.path.join(ENGINE_DATA, "artemis_iii_regions.geojson"), encoding="utf-8"))
from shapely.geometry import Polygon  # noqa: E402

regpolys = []
for f in reg["features"]:
    ring = np.array(f["geometry"]["coordinates"][0])
    x, y = T.transform(ring[:, 0], ring[:, 1])
    regpolys.append((f["properties"]["name"], Polygon(np.c_[x, y]).buffer(0)))


def cell_poly(lat, lon, n=40):
    la0, la1, lo0, lo1 = lat - 0.5, lat + 0.5, lon - 0.5, lon + 0.5
    lons = np.r_[np.linspace(lo0, lo1, n), np.full(n, lo1), np.linspace(lo1, lo0, n), np.full(n, lo0)]
    lats = np.r_[np.full(n, la0), np.linspace(la0, la1, n), np.full(n, la1), np.linspace(la1, la0, n)]
    x, y = T.transform(lons, lats)
    return Polygon(np.c_[x, y]).buffer(0)


iau = pd.read_csv(os.path.join(ENGINE_DATA, "iau_moon_nomenclature.csv"))
iau = iau[iau["type"] != "Satellite Feature"].copy()
iau["lon"] = ((iau["center_lon_e360"] + 180) % 360) - 180
moon_mean_elev = float((m.elevation_m * np.cos(np.radians(m.lat_deg))).sum() / np.cos(np.radians(m.lat_deg)).sum())
for mis, x in top["missions"].items():
    for p in x["pairs"]:
        cid = p["moon_cell_id"]
        if cid in res["moon"]:
            res["moon"][cid]["uses"].append(f"{mis}#{p['rank']}")
            continue
        r = mi.loc[cid]
        lat, lon = float(r.lat_deg), float(r.lon_deg)
        cp = cell_poly(lat, lon)
        inter = [n for n, pg in regpolys if pg.intersects(cp)]
        contains_centre = [n for n, pg in regpolys if pg.contains(Point(*T.transform(lon, lat)))]
        share = {n: round(pg.intersection(cp).area / cp.area, 3) for n, pg in regpolys if pg.intersects(cp)}
        d = haversine_km(lat, lon, iau["center_lat"].values, iau["lon"].values, R_MOON)
        k = np.argsort(d)[:3]
        zone = {"rover: lat <= -75": bool(lat <= -75.0),
                "solar: |lat| <= 30 and elevation <= -1200 m": bool(abs(lat) <= 30 and r.elevation_m <= -1200),
                "lunar_base: cell intersects the nine regions": bool(inter)}
        res["moon"][cid] = dict(uses=[f"{mis}#{p['rank']}"], lat=lat, lon=lon, elevation_m=float(r.elevation_m),
                                elevation_rel_m=round(float(r.elevation_m) - moon_mean_elev, 1),
                                slope_iso_deg=float(r.slope_iso_deg), roughness_m=float(r.roughness_m),
                                tmin_k=float(r.tmin_k), tmax_k=float(r.tmax_k), lst_diurnal_amp_k=float(r.lst_diurnal_amp_k),
                                temp_k=float(r.temp_k), irradiance_kwh_m2_day=float(r.irradiance_kwh_m2_day), illum_frac=float(r.illum_frac),
                                illum_frac_level=r.illum_frac_level, zone_rules=zone, nasa_regions_intersecting_cell=inter,
                                nasa_region_share_of_cell=share, nasa_region_containing_centre=contains_centre,
                                audio_feature=p["moon_place"].get("nearest_named_feature"), audio_feature_km=p["moon_place"].get("distance_km"),
                                audio_region_code=p["moon_place"].get("lunar_region_code"),
                                audio_nasa_regions=p["moon_place"].get("nasa_candidate_regions_intersected"),
                                nearest_iau=[(iau.iloc[i]["name"], iau.iloc[i]["type"], round(float(d[i]), 1), round(float(iau.iloc[i]["diameter_km"]), 1)) for i in k])
p = dump("p6_pairs.json", res)
print(json.dumps(res, indent=1, default=float, ensure_ascii=False)[:20000])
