"""Point 1 (input data): recompute elevation, slope and roughness of a handful of cells on each
body DIRECTLY from the raw downloads, with code written for this audit (no builder import),
and compare with the tables. Also checks that well-known lunar features and Earth places
fall in the cell the tables give them, and the grid/id convention.

    <venv>/bin/python "tierra luna/audit/p1_raw_cells.py"

Deterministic. Writes out/p1_raw_cells.csv, out/p1_named_places.csv, out/p1_raw_cells.json.

Raw files read (scratchpad realdata/, sha256 in the builders' manifests):
  Earth  earth_raw/etopo/ETOPO_2022_v1_60s_N90W180_surface.nc  (ETOPO 2022 v1, 60 arc-second)
         earth_raw/cci/cci_lc_2020_*.tif                         (ESA CCI LC 2020, 1/360 deg) -> land mask
  Moon   moon/ldem_16.img + ldem_16.lbl                          (LOLA LDEM_16, 16 px/deg)

Definitions re-implemented from the text of docs/REAL_DATA.md section 2 (not from the code):
  elevation = cos(lat)-weighted mean of the pixels in the cell (Earth: land pixels only, a 60"
              pixel is land when >= 18 of its 6x6 CCI pixels are neither 210 (water) nor 0 (no data));
  slope_iso = cos(lat)-weighted mean of atan(hypot(dz/dx, dz/dy)) with central differences,
              north-south over +-1 pixel, east-west over +-max(1, 1/cos lat) pixels (linear interp.);
  slope     = same with east-west over +-1 pixel;
  roughness = sqrt(mean squared height difference) of pairs one pixel (dy metres) apart: north-south
              (pixel, the one south of it) and east-west (pixel, the point 1/cos(lat) pixels east).
"""
from __future__ import annotations

import json
import math
import os
import sys

import numpy as np
import pandas as pd

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import p1_common as C  # noqa: E402

ETOPO = os.path.join(C.RAW, "earth_raw", "etopo", "ETOPO_2022_v1_60s_N90W180_surface.nc")
CCI_DIR = os.path.join(C.RAW, "earth_raw", "cci")
LDEM = os.path.join(C.RAW, "moon", "ldem_16.img")
LDEM_LBL = os.path.join(C.RAW, "moon", "ldem_16.lbl")
R_E_RELIEF_M = 6371008.8   # radius REAL_DATA.md sec. 2 states for the Earth relief metrics
R_M_M = 1737400.0          # LDEM_16 label A_AXIS_RADIUS

# cells to recompute: the number-1 pair of each mission + others (ids from docs/AUDIO_TOP5.json
# and a dateline cell); reasons in the report
EARTH_CELLS = {17566: "rover #1", 38464: "solar #1", 17538: "lunar_base #1", 23945: "rover #2",
               18280: "rover #4", 21054: "lunar_base #4", 38465: "solar #5"}
MOON_CELLS = {59895: "rover #1-5 twin", 24296: "solar #1 twin", 63528: "lunar_base #1 twin",
              63841: "lunar_base #2 twin", 40854: "solar #3 twin", 24761: "solar #4 twin",
              32040: "dateline test (0.5 N, 179.5 W)"}


# ------------------------------------------------------------------ Earth
def etopo_window(r0, r1, c0, c1):
    """North-up ETOPO pixel rows r0..r1-1 (row 0 = 89.99167 N), cols c0..c1-1 (periodic)."""
    import netCDF4
    ds = netCDF4.Dataset(ETOPO)
    z = ds.variables["z"]
    lat = ds.variables["lat"]
    assert float(lat[0]) < float(lat[-1])            # ascending: nc row k = north-up row 10799-k
    rows = np.arange(r0, r1)
    nck = 10799 - rows
    cols = np.arange(c0, c1) % 21600
    blk = np.ma.filled(z[nck.min():nck.max() + 1, :].astype(np.float64), np.nan)[::-1]   # north-up
    out = blk[:, cols]
    ds.close()
    return out


def cci_land_window(r0, r1, c0, c1):
    """Land flag per 60" pixel (>= 18 of 36 CCI pixels neither 210 nor 0)."""
    import glob
    import rasterio
    from rasterio.windows import Window
    land = np.zeros((r1 - r0, c1 - c0), dtype=bool)
    lat_top = 90.0 - r0 / 60.0
    lat_bot = 90.0 - r1 / 60.0
    lon_w = -180.0 + c0 / 60.0
    lon_e = -180.0 + c1 / 60.0
    for p in sorted(glob.glob(os.path.join(CCI_DIR, "cci_lc_2020_*.tif"))):
        with rasterio.open(p) as src:
            t = src.transform
            b_top, b_left = t.f, t.c
            b_bot, b_right = t.f + t.e * src.height, t.c + t.a * src.width
            top, bot = min(lat_top, b_top), max(lat_bot, b_bot)
            lw, le = max(lon_w, b_left), min(lon_e, b_right)
            if top <= bot or le <= lw:
                continue
            rr0 = int(round((b_top - top) * 360)); rr1 = int(round((b_top - bot) * 360))
            cc0 = int(round((lw - b_left) * 360)); cc1 = int(round((le - b_left) * 360))
            a = src.read(1, window=Window(cc0, rr0, cc1 - cc0, rr1 - rr0))
            ok = (a != 210) & (a != 0)
            cnt = ok.reshape(a.shape[0] // 6, 6, a.shape[1] // 6, 6).sum(axis=(1, 3))
            pr0 = int(round((lat_top - top) * 60)); pc0 = int(round((lw - lon_w) * 60))
            land[pr0:pr0 + cnt.shape[0], pc0:pc0 + cnt.shape[1]] = cnt >= 18
    return land


def interp_row(row, x):
    """Linear interpolation of a 1-D array at fractional positions x (no wrap needed here)."""
    x0 = np.floor(x).astype(int)
    f = x - x0
    return row[x0] * (1 - f) + row[x0 + 1] * f, x0, f


def earth_cell(cid):
    r, c = divmod(cid, 360)
    halo = 64                                         # > max lag 1/cos(lat) pixels at |lat| < 60
    pr0, pc0 = r * 60, c * 60
    z = etopo_window(pr0 - 1, pr0 + 61, pc0 - halo, pc0 + 60 + halo)
    L = cci_land_window(pr0 - 1, pr0 + 61, pc0 - halo, pc0 + 60 + halo)
    lat_rows = 90.0 - (np.arange(pr0 - 1, pr0 + 61) + 0.5) / 60.0
    dlam = math.radians(1 / 60)
    dy = R_E_RELIEF_M * dlam
    els, w_el, sl, sli, w_sl, w_sli, sq = [], [], [], [], [], [], []
    for k in range(1, 61):
        cl = math.cos(math.radians(lat_rows[k]))
        dx = dy * cl
        for j in range(halo, halo + 60):
            w = cl
            if L[k, j]:
                els.append(z[k, j]); w_el.append(w)
            # NS gradient
            okns = L[k, j] and L[k - 1, j] and L[k + 1, j]
            dzdy = (z[k - 1, j] - z[k + 1, j]) / (2 * dy)
            # literal slope
            if okns and L[k, j - 1] and L[k, j + 1]:
                dzdx = (z[k, j + 1] - z[k, j - 1]) / (2 * dx)
                sl.append(math.degrees(math.atan(math.hypot(dzdx, dzdy)))); w_sl.append(w)
            # isotropic slope
            s = max(1.0, 1.0 / cl)
            xp, xm = j + s, j - s
            ip, im = int(math.floor(xp)), int(math.floor(xm))
            fp, fm = xp - ip, xm - im
            okp = L[k, ip] and (L[k, ip + 1] or fp == 0)
            okm = L[k, im] and (L[k, im + 1] or fm == 0)
            if okns and okp and okm:
                zp = z[k, ip] * (1 - fp) + z[k, ip + 1] * fp
                zm = z[k, im] * (1 - fm) + z[k, im + 1] * fm
                dzdx = (zp - zm) / (2 * s * dx)
                sli.append(math.degrees(math.atan(math.hypot(dzdx, dzdy)))); w_sli.append(w)
            # roughness pairs
            lag = 1.0 / cl
            xl = j + lag
            il = int(math.floor(xl)); fl = xl - il
            if L[k, j] and L[k, il] and (L[k, il + 1] or fl == 0):
                zl = z[k, il] * (1 - fl) + z[k, il + 1] * fl
                sq.append((zl - z[k, j]) ** 2)
            if L[k, j] and L[k + 1, j]:
                sq.append((z[k + 1, j] - z[k, j]) ** 2)
    wm = lambda v, w: float(np.dot(v, w) / np.sum(w)) if len(v) else float("nan")
    return {"elev": wm(els, w_el), "slope": wm(sl, w_sl), "slope_iso": wm(sli, w_sli),
            "rough": float(math.sqrt(np.mean(sq))) if sq else float("nan"),
            "n_land_px": len(els), "n_slope_px": len(sl)}


# ------------------------------------------------------------------ Moon
def ldem():
    lbl = open(LDEM_LBL, encoding="latin-1").read()
    def val(key):
        import re
        return re.search(rf"^\s*{key}\s*=\s*([^\s<]+)", lbl, re.M).group(1)
    lines, samples, scale = int(val("LINES")), int(val("LINE_SAMPLES")), float(val("SCALING_FACTOR"))
    assert val("WESTERNMOST_LONGITUDE") == "0" and val("POSITIVE_LONGITUDE_DIRECTION").strip('"') == "EAST"
    dn = np.memmap(LDEM, dtype="<i2", mode="r", shape=(lines, samples))
    return dn, scale, {"LINES": lines, "LINE_SAMPLES": samples, "SCALING_FACTOR": scale,
                       "MAP_RESOLUTION": val("MAP_RESOLUTION"), "WESTERNMOST_LONGITUDE": 0,
                       "A_AXIS_RADIUS_km": val("A_AXIS_RADIUS")}


def moon_cell(cid, dn, scale):
    r, c = divmod(cid, 360)
    lat_c, lon_c = 89.5 - r, -179.5 + c
    ppd = 16
    dy = R_M_M * math.radians(1 / ppd)
    lon360_w = (lon_c - 0.5) % 360.0                  # west edge of the cell in 0..360 east
    j0 = int(round(lon360_w * ppd))                   # first source sample of the cell
    i0 = r * ppd
    def Z(i, j):
        return float(dn[i, j % 5760]) * scale
    def Zi(i, x):                                     # linear interpolation along a row, periodic
        x0 = math.floor(x); f = x - x0
        return Z(i, x0) * (1 - f) + Z(i, x0 + 1) * f
    els, w_el, sl, sli, sq = [], [], [], [], []
    for a in range(ppd):
        i = i0 + a
        lat = 90.0 - (i + 0.5) / ppd
        cl = math.cos(math.radians(lat))
        dx = dy * cl
        for b in range(ppd):
            j = j0 + b
            z = Z(i, j)
            els.append(z); w_el.append(cl)
            dzdy = (Z(i - 1, j) - Z(i + 1, j)) / (2 * dy)   # no pole rows in the chosen cells
            dzdx = (Z(i, j + 1) - Z(i, j - 1)) / (2 * dx)
            sl.append(math.degrees(math.atan(math.hypot(dzdx, dzdy))))
            s = max(1.0, 1.0 / cl)
            dzdx_i = (Zi(i, j + s) - Zi(i, j - s)) / (2 * s * dx)
            sli.append(math.degrees(math.atan(math.hypot(dzdx_i, dzdy))))
            sq.append((Z(i + 1, j) - z) ** 2)
            sq.append((Zi(i, j + 1.0 / cl) - z) ** 2)
    w = np.array(w_el)
    return {"elev": float(np.dot(els, w) / w.sum()), "slope": float(np.dot(sl, w) / w.sum()),
            "slope_iso": float(np.dot(sli, w) / w.sum()), "rough": float(math.sqrt(np.mean(sq))),
            "first_sample_lon360_centre": (j0 + 0.5) / ppd}


# ------------------------------------------------------------------ named places
LUNAR_FEATURES = ["Tycho", "Copernicus", "Plato", "Aristarchus", "Shackleton", "Casatus", "Huxley",
                  "Mons Malapert"]
EARTH_PLACES = [("Tamanrasset", "DZ"), ("Tinghir", "MA"), ("Derby", "AU"), ("Kununurra", "AU"),
                ("Maintirano", "MG"), ("Aheqi", "CN")]


def named_places(moon_tab, dn, scale, b):
    rows = []
    iau = pd.read_csv(C.IAU_CSV)
    sites = pd.read_csv(os.path.join(C.TL, "real_data", "lunar_named_sites.csv"))
    for name in LUNAR_FEATURES:
        f = iau[(iau["name"] == name) & (iau["type"] != "Satellite Feature")].iloc[0]
        lon = f["center_lon_e360"] - 360.0 if f["center_lon_e360"] > 180 else f["center_lon_e360"]
        cid = int(C.cell_id(f["center_lat"], lon))
        clat, clon = C.cell_centre(cid)
        row = moon_tab.iloc[cid]
        s = sites[sites["iau_name"] == name]
        # physical check: for a crater wider than 2 cells, the centre cell is lower than the mean of
        # the cells whose centre lies 0.8-1.2 crater radii away (the rim ring)
        ring = None
        if f["type"].startswith("Crater") and f["diameter_km"] > 60:
            lat_all, lon_all = moon_tab["lat_deg"].to_numpy(), moon_tab["lon_deg"].to_numpy()
            d = C.gc_km(f["center_lat"], lon, lat_all, lon_all, C.R_MOON_KM)
            rad = f["diameter_km"] / 2
            sel = (d >= 0.8 * rad) & (d <= 1.2 * rad)
            ring = float(moon_tab["elevation_m"].to_numpy()[sel].mean())
        rows.append({"body": "MOON", "name": name, "type": f["type"], "src_lat": f["center_lat"],
                     "src_lon_e180": round(lon, 4), "diameter_km": f["diameter_km"], "own_cell": f"M{cid}",
                     "cell_lat": clat, "cell_lon": clon, "table_lat": row["lat_deg"], "table_lon": row["lon_deg"],
                     "inside": abs(f["center_lat"] - row["lat_deg"]) <= 0.5 and abs(lon - row["lon_deg"]) <= 0.5,
                     "named_sites_cell": s["cell_id"].iloc[0] if len(s) else None,
                     "cell_elev_m": row["elevation_m"], "rim_ring_mean_elev_m": ring})
    gn = pd.read_csv(C.RG_CSV, keep_default_na=False, dtype={"name": str, "cc": str})
    ids = b.col("earth_base.bin", "id").astype(int)
    pos = {int(v): k for k, v in enumerate(ids)}
    pdetail = b.json("place_detail.json")
    npl = b.col("earth_place_detail.bin", "nearest_place")
    npkm = b.col("earth_place_detail.bin", "nearest_place_km")
    earth_tab = pd.read_csv(C.EARTH_CSV, usecols=["cell_id", "lat_deg", "lon_deg", "mask_fraction"])
    for name, cc in EARTH_PLACES:
        g = gn[(gn["name"] == name) & (gn["cc"] == cc)]
        g = g.iloc[0]
        la, lo = float(g["lat"]), float(g["lon"])
        cid = int(C.cell_id(la, lo))
        row = earth_tab.iloc[cid]
        k = pos.get(cid)
        rows.append({"body": "EARTH", "name": name, "type": f"GeoNames cities1000 ({cc})", "src_lat": la,
                     "src_lon_e180": lo, "own_cell": f"E{cid}", "cell_lat": row["lat_deg"], "cell_lon": row["lon_deg"],
                     "table_lat": row["lat_deg"], "table_lon": row["lon_deg"],
                     "inside": abs(la - row["lat_deg"]) <= 0.5 and abs(lo - row["lon_deg"]) <= 0.5,
                     "bundle_nearest_place_of_cell": pdetail["nearest_places"][int(npl[k])] if k is not None else None,
                     "bundle_km": float(npkm[k]) if k is not None else None,
                     "own_km_place_to_centre": float(C.gc_km(la, lo, row["lat_deg"], row["lon_deg"], C.R_EARTH_KM)),
                     "table_mask_fraction": row["mask_fraction"]})
    return rows


def main():
    e, m = C.load_tables()
    b = C.Bundle()
    out = []
    # grid / id convention on both tables
    grid = {}
    for name, t, pre in (("EARTH", e, "E"), ("MOON", m, "M")):
        rows, cols = np.divmod(np.arange(64800), 360)
        grid[name] = {
            "rows": int(len(t)), "unique_ids": int(t["cell_id"].nunique()),
            "id_formula_ok": bool((t["cell_id"] == [f"{pre}{i}" for i in range(64800)]).all()),
            "lat_is_89.5_minus_row": bool(np.allclose(t["lat_deg"], 89.5 - t["row"])),
            "lon_is_-179.5_plus_col": bool(np.allclose(t["lon_deg"], -179.5 + t["col"])),
            "row_col_match_id": bool(((t["row"] * 360 + t["col"]) == np.arange(64800)).all()),
            "lat_range": [float(t["lat_deg"].min()), float(t["lat_deg"].max())],
            "lon_range": [float(t["lon_deg"].min()), float(t["lon_deg"].max())],
            "cell_km_range": [float(t["cell_km"].min()), float(t["cell_km"].max())],
        }
    # bundle id -> centre (the web's convention), from manifest grid if present
    grid["bundle_manifest_grid"] = b.manifest.get("grid")

    for cid, why in EARTH_CELLS.items():
        r = earth_cell(cid)
        t = e.iloc[cid]
        out.append({"body": "EARTH", "cell": f"E{cid}", "why": why, "lat": t["lat_deg"], "lon": t["lon_deg"],
                    "mask_fraction": t["mask_fraction"],
                    "elev_own": r["elev"], "elev_table": t["elevation_m"],
                    "slope_own": r["slope"], "slope_table": t["slope_deg"],
                    "slope_iso_own": r["slope_iso"], "slope_iso_table": t["slope_iso_deg"],
                    "rough_own": r["rough"], "rough_table": t["roughness_m"],
                    "n_land_px_own": r["n_land_px"], "n_land_px_table": t["n_dem_land_px"]})
    dn, scale, lbl = ldem()
    for cid, why in MOON_CELLS.items():
        r = moon_cell(cid, dn, scale)
        t = m.iloc[cid]
        out.append({"body": "MOON", "cell": f"M{cid}", "why": why, "lat": t["lat_deg"], "lon": t["lon_deg"],
                    "elev_own": r["elev"], "elev_table": t["elevation_m"],
                    "slope_own": r["slope"], "slope_table": t["slope_deg"],
                    "slope_iso_own": r["slope_iso"], "slope_iso_table": t["slope_iso_deg"],
                    "rough_own": r["rough"], "rough_table": t["roughness_m"]})
    df = pd.DataFrame(out)
    for v in ("elev", "slope", "slope_iso", "rough"):
        df[f"d_{v}"] = df[f"{v}_own"] - df[f"{v}_table"]
    df.to_csv(os.path.join(C.OUT, "p1_raw_cells.csv"), index=False, float_format="%.4f")
    places = pd.DataFrame(named_places(m, dn, scale, b))
    places.to_csv(os.path.join(C.OUT, "p1_named_places.csv"), index=False)
    summ = {"grid": grid, "ldem_label": lbl,
            "max_abs_diff": {body: {v: float(df[df.body == body][f"d_{v}"].abs().max())
                                    for v in ("elev", "slope", "slope_iso", "rough")} for body in ("EARTH", "MOON")},
            "named_places_all_inside": bool(places["inside"].all())}
    C.write_json("p1_raw_cells.json", summ)
    pd.set_option("display.width", 250)
    print(df.round(3).to_string())
    print(places.to_string())
    print(json.dumps(summ, indent=1, default=C._default))


if __name__ == "__main__":
    main()
