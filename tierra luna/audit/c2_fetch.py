"""Point C on the NEW fifteen (missions.json top5 ids, values from explain.json). Check only: nothing
external is copied into the model, the tables, the bundle or the web.
Reuses part 6 code: p6_fetch_ext.nasadem / station_stats / stations (NASADEM HGT v001 via Planetary
Computer COG, GHCN-Daily), the Global Solar Atlas point query of p6_power_gsa, and the ESA CCI 2020
raw-tile mix and Natural Earth 110m test of p6_pairs. Added: Copernicus DEM GLO-30 (AWS open
bucket, keyless) for cells north of NASADEM's 60 N limit; slope/roughness also at the 12" read
(~370 m, nearest to the Rover's 300 m variables).
Run:  $PY -I "tierra luna/audit/c2_fetch.py"     Output: out/c2_sites.csv, out/c2_stations.csv, out/c2_gsa.csv
"""
import glob
import json
import math
import os
import sys
import urllib.request

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from p6_common import BUNDLE, ENGINE_DATA, OUT, haversine_km, load_tables  # noqa: E402
import p6_fetch_ext as P  # noqa: E402

EXT = P.EXT
RAW = "/tmp/claude-0/-home-user-NASA/7228bb30-9725-52d9-8d71-762c955fd0bd/scratchpad/stars/realdata/earth_raw/cci"


def sites():
    m = json.load(open(os.path.join(BUNDLE, "missions.json")))
    ex = json.load(open(os.path.join(BUNDLE, "explain.json")))["missions"]
    out = []
    for v in m["missions"]:
        L = {x["id"]: x for x in ex[v["id"]]}
        for r, i in enumerate(v["top5"]["ids"], 1):
            x = L[i]
            d = dict(mission=v["id"], rank=r, cell=f"E{i}", lat=x["lat"], lon=x["lon"], country=x["place"]["country"],
                     place=x["place"]["nearest_place"])
            for b in x["breakdown"]:
                d["bundle_" + b["variable"]] = b["value"]
            for s in x["similarity"]["variables"]:
                d.setdefault("bundle_" + s["variable"], s["earth"])
            out.append(d)
    return out


def dem_grid(lat, lon):
    """12" (300x300) cos-weighted grid for the 1-degree cell; NASADEM, else Copernicus GLO-30."""
    import rasterio
    la, lo = math.floor(lat), math.floor(lon)
    if -56 <= la < 60:
        r = P.nasadem(lat, lon)
        name = r["tile"]
        return np.load(os.path.join(EXT, "nasadem", name + "_ovr.npy")), "NASADEM_HGT v001 (" + name + ")", r
    t = f"Copernicus_DSM_COG_10_{'N' if la >= 0 else 'S'}{abs(la):02d}_00_{'E' if lo >= 0 else 'W'}{abs(lo):03d}_00_DEM"
    cache = os.path.join(EXT, "copdem", t + "_ovr.npy")
    os.makedirs(os.path.dirname(cache), exist_ok=True)
    if not os.path.exists(cache):
        url = f"https://copernicus-dem-30m.s3.amazonaws.com/{t}/{t}.tif"
        with rasterio.Env(GDAL_HTTP_TIMEOUT=60, AWS_NO_SIGN_REQUEST="YES"):
            with rasterio.open("/vsicurl/" + url) as ds:
                a = ds.read(1, out_shape=(300, 300), resampling=rasterio.enums.Resampling.average).astype(float)
        np.save(cache, a)
    return np.load(cache), "Copernicus DEM GLO-30 (" + t + ")", None


def terrain(a, lat, px_per_deg):
    """Slope (deg, mean, cos-weighted) and RMS neighbour difference (m) at the grid's own spacing."""
    n = a.shape[0]
    R = 6371008.8
    dy = R * math.radians(1 / px_per_deg)
    blat = lat + 0.5 - (np.arange(n) + 0.5) / n
    dx = dy * np.cos(np.radians(blat))[:, None]
    gy = (a[:-2, 1:-1] - a[2:, 1:-1]) / (2 * dy)
    gx = (a[1:-1, 2:] - a[1:-1, :-2]) / (2 * dx[1:-1])
    s = np.degrees(np.arctan(np.hypot(gx, gy)))
    w = np.cos(np.radians(blat[1:-1]))[:, None] * np.ones_like(s)
    ok = np.isfinite(s)
    d = np.concatenate([(a[1:] - a[:-1]).ravel(), (a[:, 1:] - a[:, :-1]).ravel()])
    return float((s * w)[ok].sum() / w[ok].sum()), float(np.sqrt(np.nanmean(d ** 2))), float(np.nanmax(a) - np.nanmin(a))


def cci_mix(lat, lon):
    import rasterio
    for t in glob.glob(os.path.join(RAW, "*.tif")):
        with rasterio.open(t) as ds:
            b = ds.bounds
            if b.left <= lon < b.right and b.bottom <= lat < b.top:
                a = ds.read(1, window=rasterio.windows.from_bounds(lon - 0.5, lat - 0.5, lon + 0.5, lat + 0.5, ds.transform))
                v, c = np.unique(a, return_counts=True)
                d = dict(zip(v.tolist(), c.tolist())); tot = c.sum()
                sh = lambda codes: round(sum(d.get(k, 0) for k in codes) / tot, 4)
                top = max(d.items(), key=lambda kv: kv[1])
                return dict(cci_water_210=sh([210]), cci_snowice_220=sh([220]), cci_bare_200_202=sh([200, 201, 202]),
                            cci_sparse_150_153=sh([150, 151, 152, 153]), cci_top_class=int(top[0]), cci_top_share=round(top[1] / tot, 3))
    return dict(cci_note="no local CCI tile")


def main():
    from shapely.geometry import Point, shape
    from shapely.ops import unary_union
    ne = json.load(open(os.path.join(ENGINE_DATA, "ne_110m_admin_0_countries.geojson"), encoding="utf-8"))
    land = unary_union([shape(f["geometry"]) for f in ne["features"]])
    e, _ = load_tables()
    ei = e.set_index("cell_id")
    st = P.stations()
    rows, strows, gsa = [], [], []
    for s in sites():
        cid, lat, lon = s["cell"], s["lat"], s["lon"]
        r = dict(s)
        if cid in ei.index:
            t = ei.loc[cid]
            for k in ("mask_fraction", "snow_ice_frac", "bare_frac", "rock_or_bare_frac", "slope_deg", "slope_iso_deg", "roughness_m",
                      "tmin_c", "lst_diurnal_amp_k", "irradiance_kwh_m2_day", "elevation_m"):
                if k in t.index:
                    r["table_" + k] = t[k]
        r["ne110m_centre_on_land"] = bool(land.contains(Point(lon, lat)))
        r.update(cci_mix(lat, lon))
        try:
            a, src, _ = dem_grid(lat, lon)
            ok = np.isfinite(a) & (a > -1000)
            a = np.where(ok, a, np.nan)
            r["dem_source"] = src
            r["dem_valid_frac"] = round(float(ok.mean()), 4)
            r["dem_mean_m"] = round(float(np.nanmean(a)), 1)
            s12, r12, relief = terrain(a, lat, 300)
            b = a.reshape(60, 5, 60, 5).mean(axis=(1, 3))
            s60, r60, _ = terrain(b, lat, 60)
            r.update(dem_slope_12s_deg=round(s12, 3), dem_rms_12s_m=round(r12, 2), dem_slope_60s_deg=round(s60, 3),
                     dem_rms_60s_m=round(r60, 2), dem_relief_m=round(relief, 0))
        except Exception as ex:
            r["dem_source"] = "not reached: " + str(ex)[:150]
        rows.append(r)
        if s["mission"] == "lunar_base":
            dist = haversine_km(lat, lon, st.lat.values, st.lon.values, 6371.0088)
            cand = st.assign(km=dist)
            cand = cand[(cand.km <= 250) & (cand.y1 >= 1990) & (cand.y1 - cand.y0 >= 10)].nsmallest(2, "km")
            for _, c in cand.iterrows():
                try:
                    ss = P.station_stats(c["id"])
                except Exception as ex:
                    strows.append(dict(cell=cid, station=c["id"], error=str(ex)[:150])); continue
                for tag in ("1970_2000", "all"):
                    strows.append(dict(cell=cid, station=c["id"], name=c["name"], st_elev_m=c.elev, km=round(float(c.km), 1), period=tag,
                                       **(ss.get(tag) or {}), bundle_tmin_c=s.get("bundle_tmin_c"), bundle_lst_amp_k=s.get("bundle_lst_diurnal_amp_k"),
                                       dem_mean_m=r.get("dem_mean_m")))
        if s["mission"] in ("solar", "lunar_base"):
            p = os.path.join(EXT, "gsa", f"{cid}.json")
            try:
                P.get(f"https://api.globalsolaratlas.info/data/lta?loc={lat},{lon}", p)
                d = json.load(open(p)); a = d["annual"]["data"]; meta = d["annual"]["metadata"]["layers"]["GHI"]
                gday = a["GHI"] / 365.25
                mod = s.get("bundle_irradiance_kwh_m2_day", r.get("table_irradiance_kwh_m2_day"))
                gsa.append(dict(cell=cid, mission=s["mission"], lat=lat, lon=lon, gsa_ghi_kwh_m2_day=round(gday, 3), gsa_version=meta.get("version"),
                                gsa_period_to=meta["period"].get("to"), model_ground_kwh_m2_day=mod,
                                rel_diff_pct=round(100 * (float(mod) - gday) / gday, 1) if mod is not None and mod == mod else None))
            except Exception as ex:
                gsa.append(dict(cell=cid, error="not reached: " + str(ex)[:150]))
        print(cid, r.get("dem_source"), r.get("dem_slope_12s_deg"), flush=True)
    pd.DataFrame(rows).to_csv(os.path.join(OUT, "c2_sites.csv"), index=False)
    pd.DataFrame(strows).to_csv(os.path.join(OUT, "c2_stations.csv"), index=False)
    pd.DataFrame(gsa).to_csv(os.path.join(OUT, "c2_gsa.csv"), index=False)


if __name__ == "__main__":
    main()
