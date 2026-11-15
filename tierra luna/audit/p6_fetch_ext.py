"""Point C, external checks only (nothing copied into the model): for the 15 distinct Earth cells
of docs/AUDIO_TOP5.json
  (a) NASADEM HGT v001 (NASA/JPL reprocessed SRTM, 1"), read keyless from the Microsoft Planetary
      Computer COG copy at a reduced overview; cell mean elevation, and slope / roughness with the
      tables' definitions after block-averaging to 60" (own code);
  (b) NOAA NCEI GHCN-Daily: the nearest stations with TMAX and TMIN; per station the coldest-month
      mean daily minimum and the mean daily range (TMAX - TMIN), for 1970-2000 (WorldClim's period)
      and for all years.
Raw downloads go to the scratchpad (EXT dir below), never into the repository.
Run:  $PY -I "tierra luna/audit/p6_fetch_ext.py"   (uses files already downloaded when present)
Output: out/p6_ext_dem.csv, out/p6_ext_stations.csv
"""
import io
import json
import math
import os
import sys
import time
import urllib.request

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from p6_common import OUT, REPO, haversine_km, load_tables  # noqa: E402

EXT = os.environ.get("P6_EXT", "/tmp/claude-0/-home-user/7228bb30-9725-52d9-8d71-762c955fd0bd/scratchpad/ext")
GH = os.path.join(EXT, "ghcn")
os.makedirs(GH, exist_ok=True)
CA = "/root/.ccr/ca-bundle.crt"
if os.path.exists(CA):
    os.environ.setdefault("CURL_CA_BUNDLE", CA)
    os.environ.setdefault("SSL_CERT_FILE", CA)


def cells():
    d = json.load(open(os.path.join(REPO, "docs", "AUDIO_TOP5.json"), encoding="utf-8"))
    out = {}
    for m, x in d["missions"].items():
        for p in x["pairs"]:
            out.setdefault(p["earth_cell_id"], dict(lat=p["earth_place"]["cell_centre_lat"], lon=p["earth_place"]["cell_centre_lon"], uses=[]))
            out[p["earth_cell_id"]]["uses"].append(f"{m}#{p['rank']}")
    return out


def get(url, path):
    if os.path.exists(path) and os.path.getsize(path) > 0:
        return path
    req = urllib.request.Request(url, headers={"User-Agent": "generic-audit-client"})
    with urllib.request.urlopen(req, timeout=120) as r, open(path + ".part", "wb") as fh:
        fh.write(r.read())
    os.replace(path + ".part", path)
    time.sleep(1.0)
    return path


# ------------------------------------------------------------------ (a) NASADEM
def nasadem(lat, lon):
    import rasterio
    la, lo = math.floor(lat), math.floor(lon)
    name = f"NASADEM_HGT_{'n' if la >= 0 else 's'}{abs(la):02d}{'e' if lo >= 0 else 'w'}{abs(lo):03d}"
    tok = json.loads(urllib.request.urlopen("https://planetarycomputer.microsoft.com/api/sas/v1/token/nasadem", timeout=60).read())["token"]
    url = f"https://nasademeuwest.blob.core.windows.net/nasadem-cog/v001/{name}.tif?{tok}"
    cache = os.path.join(EXT, "nasadem", name + "_ovr.npy")
    os.makedirs(os.path.dirname(cache), exist_ok=True)
    if not os.path.exists(cache):
        try:
            with rasterio.Env(GDAL_HTTP_TIMEOUT=60, CPL_VSIL_CURL_ALLOWED_EXTENSIONS=".tif"):
                with rasterio.open("/vsicurl/" + url) as ds:
                    # read at 1/12 resolution: 3601 -> 300 px (12" ~ 370 m)
                    a = ds.read(1, out_shape=(300, 300), resampling=rasterio.enums.Resampling.average).astype(float)
                    nod = ds.nodata
            if nod is not None:
                a[a == nod] = np.nan
            np.save(cache, a)
        except Exception as ex:  # tile absent (ocean) or unreachable
            return dict(tile=name, error=str(ex)[:200])
    a = np.load(cache)
    n = a.shape[0]
    rows_lat = lat + 0.5 - (np.arange(n) + 0.5) / n
    w = np.cos(np.radians(rows_lat))[:, None] * np.ones_like(a)
    ok = np.isfinite(a)
    mean = float((a * w)[ok].sum() / w[ok].sum())
    # block-average to 60" (5 x 5 of 12") and apply the tables' slope/roughness definitions
    b = a.reshape(60, 5, 60, 5).mean(axis=(1, 3))
    blat = lat + 0.5 - (np.arange(60) + 0.5) / 60
    R = 6371008.8
    dy = R * math.radians(1 / 60)
    dx = dy * np.cos(np.radians(blat))[:, None]
    # isotropic central differences: N-S 2 px; E-W lag max(1, 1/cos) px (here cos ~ 0.75-0.96 -> 1 px, 2 px span)
    gy = (b[:-2, 1:-1] - b[2:, 1:-1]) / (2 * dy)
    L = max(1.0, 1.0 / math.cos(math.radians(lat)))
    cols = np.arange(60, dtype=float)
    gx = np.full((58, 58), np.nan)
    for i in range(1, 59):
        row = b[i]
        fp = np.interp(cols[1:-1] + L, cols, row, right=np.nan)
        fm = np.interp(cols[1:-1] - L, cols, row, left=np.nan)
        gx[i - 1] = (fp - fm) / (2 * L * dx[i, 0])
    s = np.degrees(np.arctan(np.hypot(gx, gy)))
    sw = np.cos(np.radians(blat[1:-1]))[:, None] * np.ones_like(s)
    okk = np.isfinite(s)
    slope = float((s * sw)[okk].sum() / sw[okk].sum())
    d_ns = (b[1:, :] - b[:-1, :]).ravel()
    lag_px = 1 / np.cos(np.radians(lat))  # E-W pairs one N-S pixel length apart, linear interpolation
    i0 = int(math.floor(lag_px)); f = lag_px - i0
    bi = b[:, i0:] if f == 0 else (1 - f) * b[:, i0:-1] + f * b[:, i0 + 1:]
    d_ew = (bi - b[:, : bi.shape[1]]).ravel()
    d = np.concatenate([d_ns, d_ew])
    rough = float(np.sqrt(np.nanmean(d ** 2)))
    return dict(tile=name, nasadem_mean_m=round(mean, 1), nasadem_valid_frac=round(float(ok.mean()), 4),
                nasadem_slope_deg=round(slope, 3), nasadem_rough_m=round(rough, 2))


# ------------------------------------------------------------------ (b) GHCN-Daily stations
def stations():
    st = pd.read_fwf(os.path.join(GH, "ghcnd-stations.txt"), colspecs=[(0, 11), (12, 20), (21, 30), (31, 37), (41, 71)],
                     names=["id", "lat", "lon", "elev", "name"], header=None)
    inv = pd.read_fwf(os.path.join(GH, "ghcnd-inventory.txt"), colspecs=[(0, 11), (31, 35), (36, 40), (41, 45)],
                      names=["id", "el", "y0", "y1"], header=None)
    tx = inv[inv.el == "TMAX"].set_index("id")
    tn = inv[inv.el == "TMIN"].set_index("id")
    both = tx.join(tn, lsuffix="_x", rsuffix="_n", how="inner")
    both["y0"] = both[["y0_x", "y0_n"]].max(axis=1)
    both["y1"] = both[["y1_x", "y1_n"]].min(axis=1)
    return st.set_index("id").join(both[["y0", "y1"]], how="inner").reset_index()


def station_stats(sid):
    p = get(f"https://www.ncei.noaa.gov/data/global-historical-climatology-network-daily/access/{sid}.csv", os.path.join(GH, sid + ".csv"))
    d = pd.read_csv(p, usecols=lambda c: c in ("DATE", "TMAX", "TMIN", "TMAX_ATTRIBUTES", "TMIN_ATTRIBUTES"), low_memory=False)
    d["DATE"] = pd.to_datetime(d["DATE"])
    for c in ("TMAX", "TMIN"):
        d[c] = pd.to_numeric(d.get(c), errors="coerce") / 10.0  # tenths of degC in the CSV
        att = d.get(c + "_ATTRIBUTES")
        if att is not None:  # drop values with a quality flag (2nd attribute field non-blank)
            q = att.astype(str).str.split(",", expand=True)
            if q.shape[1] > 1:
                bad = q[1].fillna("").str.strip() != ""
                d.loc[bad, c] = np.nan
    res = {}
    for tag, (a, b) in {"1970_2000": (1970, 2000), "all": (1800, 2100)}.items():
        x = d[(d.DATE.dt.year >= a) & (d.DATE.dt.year <= b)].copy()
        x["m"] = x.DATE.dt.month
        x["y"] = x.DATE.dt.year
        g = x.groupby(["y", "m"]).agg(tn=("TMIN", "mean"), ntn=("TMIN", "count"), tx=("TMAX", "mean"))
        g = g[g.ntn >= 20]
        if g.empty:
            res[tag] = None
            continue
        clim = g.groupby(level="m").tn.mean()
        both = x.dropna(subset=["TMIN", "TMAX"])
        res[tag] = dict(years=f"{int(g.index.get_level_values('y').min())}-{int(g.index.get_level_values('y').max())}",
                        n_months=int(len(g)), coldest_month=int(clim.idxmin()), coldest_month_mean_tmin_c=round(float(clim.min()), 2),
                        mean_daily_range_k=round(float((both.TMAX - both.TMIN).mean()), 2) if len(both) else None,
                        n_days_range=int(len(both)))
    return res


def main():
    cs = cells()
    e, _ = load_tables()
    e = e.set_index("cell_id")
    dem_rows, st_rows = [], []
    st = stations()
    for cid, c in cs.items():
        r = dict(cell=cid, lat=c["lat"], lon=c["lon"], uses=";".join(c["uses"]),
                 table_elevation_m=e.at[cid, "elevation_m"], table_slope_iso_deg=e.at[cid, "slope_iso_deg"],
                 table_roughness_m=e.at[cid, "roughness_m"])
        r.update(nasadem(c["lat"], c["lon"]))
        dem_rows.append(r)
        dist = haversine_km(c["lat"], c["lon"], st.lat.values, st.lon.values, 6371.0088)
        cand = st.assign(km=dist)
        cand = cand[(cand.km <= 250) & (cand.y1 >= 1990) & (cand.y1 - cand.y0 >= 10)].nsmallest(2, "km")
        for _, s in cand.iterrows():
            ss = station_stats(s["id"])
            for tag in ("1970_2000", "all"):
                v = ss.get(tag)
                st_rows.append(dict(cell=cid, uses=";".join(c["uses"]), station=s["id"], name=s["name"], st_lat=s.lat, st_lon=s.lon,
                                    st_elev_m=s.elev, km_from_cell_centre=round(float(s.km), 1), period=tag,
                                    **(v or {"years": None}),
                                    table_tmin_c=e.at[cid, "tmin_c"], table_elevation_m=e.at[cid, "elevation_m"],
                                    table_lst_amp_k=e.at[cid, "lst_diurnal_amp_k"]))
        print(cid, r.get("nasadem_mean_m"), len(cand), flush=True)
    pd.DataFrame(dem_rows).to_csv(os.path.join(OUT, "p6_ext_dem.csv"), index=False)
    pd.DataFrame(st_rows).to_csv(os.path.join(OUT, "p6_ext_stations.csv"), index=False)


if __name__ == "__main__":
    main()
