"""Build output_real/earth_real_1deg.csv from keyless, open Earth products.

One command (downloads what is missing, then aggregates; deterministic):

    <venv>/bin/python real_data/build_earth.py            # full build
    <venv>/bin/python real_data/build_earth.py --no-download   # use files already on disk

Grid (shared with the Moon table): 1-degree cells, 180 rows x 360 cols, row 0 at the
north (centre latitude 89.5), col 0 at the west (centre longitude -179.5), longitudes
-180..180 east-positive. cell_id = "E" + str(row*360 + col).

Sources (details, URLs, licences: provenance_earth.csv; files and sha256: manifest_earth.csv):
  ETOPO 2022 v1 60 arc-second surface elevation (NOAA NCEI)        -> relief
  ESA CCI / C3S Land Cover 2020 v2.1.1, 300 m (Planetary Computer)  -> land share, cover classes
  OpenLandMap MODIS MOD11A2 LST climatology 2000-2017, 1 km (Zenodo) -> LST, diurnal amplitude
  WorldClim 2.1, 10 arc-minute, 1970-2000 (UC Davis)               -> tmin, wind, rain, insolation
  Obu et al. permafrost probability, 1 km (PANGAEA)                 -> permafrost class
  Exact formula with the IAU 2006 obliquity                         -> sun geometry
Intermediate 1-degree arrays are cached as .npz next to the raw files (not in the repo).
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd
import rasterio
from rasterio.windows import Window

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import earth_sources as S  # noqa: E402

ROOT = HERE.parent
OUT_CSV = ROOT / "output_real" / "earth_real_1deg.csv"
RAW = S.DEFAULT_RAW
CACHE = RAW.parent / "earth_cache"

NR, NC = 180, 360
NCELL = NR * NC
R_EARTH_KM = 6371.0088          # IUGG mean radius, used for the spherical relief metrics
WGS84_A, WGS84_INVF = 6378.137, 298.257223563
OBLIQUITY_EARTH_DEG = 84381.406 / 3600.0   # IAU 2006 mean obliquity at J2000 (IERS Conventions 2010, ch. 5, text after eq. 5.22)

# ESA CCI LCCS legend codes
CCI_WATER = 210
CCI_SNOW_ICE = 220
CCI_BARE = (200, 201, 202)
CCI_SPARSE = (150, 151, 152, 153)
CLASS_MAP_FILE = HERE / "class_mappings.json"


# ---------------------------------------------------------------- grid helpers
def cell_centres():
    rows, cols = np.divmod(np.arange(NCELL), NC)
    return rows, cols, 89.5 - rows, -179.5 + cols


def meridian_arc_km(lat1_deg: float, lat2_deg: float) -> float:
    """Length of the WGS84 meridian between two latitudes (numerical integration)."""
    f = 1.0 / WGS84_INVF
    e2 = f * (2 - f)
    phi = np.radians(np.linspace(lat1_deg, lat2_deg, 2001))
    m = WGS84_A * (1 - e2) / (1 - e2 * np.sin(phi) ** 2) ** 1.5
    return float(abs(np.trapezoid(m, phi)))


def pixel_cell_index(lat_centres: np.ndarray, lon_centres: np.ndarray):
    """Map pixel-centre coordinates to (row, col) of the 1-degree grid (-1 if outside)."""
    r = np.floor(90.0 - lat_centres).astype(np.int64)
    c = np.floor(lon_centres + 180.0).astype(np.int64)
    c = np.where(c == NC, NC - 1, c)
    r = np.where((r < 0) | (r >= NR), -1, r)
    return r, c


def geo_axes(transform, height, width):
    """Pixel-centre latitude (per row) and longitude (per column) of a north-up raster."""
    lat = transform.f + transform.e * (np.arange(height) + 0.5)
    lon = transform.c + transform.a * (np.arange(width) + 0.5)
    return lat, lon


class Accum:
    """Per-cell running sums for means over valid pixels."""

    def __init__(self):
        self.s = np.zeros(NCELL)
        self.n = np.zeros(NCELL)

    def add(self, cell_idx: np.ndarray, values: np.ndarray):
        ok = np.isfinite(values) & (cell_idx >= 0)
        self.s += np.bincount(cell_idx[ok], weights=values[ok], minlength=NCELL)
        self.n += np.bincount(cell_idx[ok], minlength=NCELL)

    def mean(self):
        with np.errstate(invalid="ignore", divide="ignore"):
            return np.where(self.n > 0, self.s / np.maximum(self.n, 1), np.nan)


def aggregate_geographic(path: str, transform_values, band: int = 1, rows_per_block: int = 1200):
    """Mean of transform_values(raw_block) over each 1-degree cell for a lat/lon raster."""
    acc = Accum()
    with rasterio.open(path) as src:
        lat, lon = geo_axes(src.transform, src.height, src.width)
        _, ccol = pixel_cell_index(np.zeros_like(lon), lon)
        for r0 in range(0, src.height, rows_per_block):
            h = min(rows_per_block, src.height - r0)
            raw = src.read(band, window=Window(0, r0, src.width, h))
            vals = transform_values(raw, src.nodata)
            rr, _ = pixel_cell_index(lat[r0:r0 + h], np.zeros(h))
            idx = np.where(rr[:, None] >= 0, rr[:, None] * NC + ccol[None, :], -1)
            acc.add(idx.ravel(), vals.ravel().astype(np.float64))
    return acc


def cached(name: str):
    def deco(fn):
        def wrapper(*a, **k):
            CACHE.mkdir(parents=True, exist_ok=True)
            p = CACHE / f"{name}.npz"
            if p.exists():
                return dict(np.load(p, allow_pickle=False))
            res = fn(*a, **k)
            np.savez_compressed(p, **res)
            return res
        return wrapper
    return deco


# ---------------------------------------------------------------- land cover (ESA CCI)
@cached("cci")
def stage_cci(download: bool):
    """Class counts per 1-degree cell and land share per ETOPO 60" pixel (6x6 CCI pixels)."""
    counts = np.zeros((NCELL, 256), dtype=np.int64)
    land60 = np.zeros((10800, 21600), dtype=np.uint8)   # north-up, ETOPO pixel grid
    for tile in S.CCI_TILES:
        p = RAW / "cci" / f"cci_lc_2020_{tile}.tif"
        if download:
            S.fetch_cci_tile(tile, p)
        with rasterio.open(p) as src:
            t = src.transform
            assert abs(t.a - 1 / 360) < 1e-9 and src.width == 16200
            row0_60 = int(round((90.0 - t.f) * 60))
            col0_60 = int(round((t.c + 180.0) * 60))
            lat, lon = geo_axes(t, src.height, src.width)
            _, ccol = pixel_cell_index(np.zeros_like(lon), lon)
            for r0 in range(0, src.height, 1800):          # 5-degree blocks
                a = src.read(1, window=Window(0, r0, src.width, 1800))
                rr, _ = pixel_cell_index(lat[r0:r0 + 1800], np.zeros(1800))
                idx = (rr[:, None] * NC + ccol[None, :]) * 256 + a.astype(np.int64)
                counts += np.bincount(idx.ravel(), minlength=NCELL * 256).reshape(NCELL, 256)
                land = ((a != CCI_WATER) & (a != 0)).reshape(300, 6, 2700, 6).sum(axis=(1, 3))
                rs = row0_60 + r0 // 6
                land60[rs:rs + 300, col0_60:col0_60 + 2700] = land.astype(np.uint8)
        print(f"  cci {tile} done", flush=True)
    np.save(CACHE / "land60.npy", land60)
    return {"counts": counts}


# ---------------------------------------------------------------- relief (ETOPO 2022)
@cached("etopo_v2")   # v2: area-weighted means, isotropic roughness lag, slope_iso (verification fixes)
def stage_etopo(download: bool):
    import netCDF4
    p = RAW / "etopo" / "ETOPO_2022_v1_60s_N90W180_surface.nc"
    if download:
        S.fetch(S.ETOPO_URL, p)
    land60 = np.load(CACHE / "land60.npy")              # 0..36 CCI land pixels per 60" pixel
    ds = netCDF4.Dataset(p)
    zvar = ds.variables["z"]
    lat_nc = ds.variables["lat"][:]
    assert lat_nc[0] < lat_nc[-1] and zvar.shape == (10800, 21600)
    dlam = math.radians(1 / 60)
    dy_km = R_EARTH_KM * dlam
    out = {k: np.full(NCELL, np.nan) for k in
           ("elev_all", "elev_land", "slope_mean", "slope_p90", "slope_iso_mean", "slope_iso_p90",
            "rough", "n_land", "n_slope")}

    def read_rows(i0, i1):
        """North-up rows i0..i1-1 (row 0 = northernmost); NaN outside the grid."""
        res = np.full((i1 - i0, 21600), np.nan, dtype=np.float64)
        a, b = max(i0, 0), min(i1, 10800)
        if b > a:
            # north-up row i is netCDF row 10799 - i
            blk = zvar[10799 - (b - 1):10799 - a + 1, :]
            blk = np.ma.filled(blk.astype(np.float64), np.nan)[::-1]
            res[a - i0:b - i0] = blk
        return res

    def read_land(i0, i1):
        res = np.zeros((i1 - i0, 21600), dtype=bool)
        a, b = max(i0, 0), min(i1, 10800)
        res[a - i0:b - i0] = land60[a:b] >= 18            # >= 50 % CCI land
        return res

    W = 21600
    xs = np.arange(W, dtype=np.float64)

    def shifted(zrow, lrow, lag):
        """z and land validity at x + lag pixels along a periodic row (linear interpolation)."""
        xq = xs + lag
        x0 = np.floor(xq)
        f = xq - x0
        i0 = x0.astype(np.int64) % W
        i1 = (i0 + 1) % W
        val = zrow[i0] * (1.0 - f) + zrow[i1] * f
        ok = lrow[i0] & (lrow[i1] | (f == 0.0))
        return val, ok

    def per_cell(a):
        """(60, 21600) pixel array -> (360, 3600) cell-major array."""
        return a.reshape(60, NC, 60).transpose(1, 0, 2).reshape(NC, 3600)

    def wmean(vals, wts):
        ok = np.isfinite(vals)
        num = np.where(ok, vals * wts, 0.0).sum(1)
        den = np.where(ok, wts, 0.0).sum(1)
        with np.errstate(invalid="ignore", divide="ignore"):
            return np.where(den > 0, num / den, np.nan), ok.sum(1)

    for r in range(NR):
        i0 = r * 60
        z = read_rows(i0 - 1, i0 + 61)                    # one halo row on each side
        L = read_land(i0 - 1, i0 + 61)
        lat_rows = 90.0 - (np.arange(i0 - 1, i0 + 61) + 0.5) / 60.0
        coslat = np.cos(np.radians(lat_rows))
        dx_km = R_EARTH_KM * coslat * dlam
        zc, Lc = z[1:-1], L[1:-1]
        wts = per_cell(np.repeat(coslat[1:-1, None], W, axis=1))   # area weight of each pixel (cos lat)
        cells = slice(r * NC, (r + 1) * NC)
        # mean elevation (area-weighted, as for the Moon), all pixels (incl. bathymetry) and land pixels
        out["elev_all"][cells], _ = wmean(per_cell(zc), wts)
        out["elev_land"][cells], nl = wmean(per_cell(np.where(Lc, zc, np.nan)), wts)
        out["n_land"][cells] = nl
        # slope by central differences on the sphere (metres / metres), common Earth/Moon definition
        zE, zW = np.roll(z, -1, axis=1), np.roll(z, 1, axis=1)     # longitude wraps
        LE, LW = np.roll(L, -1, axis=1), np.roll(L, 1, axis=1)
        dzdx = (zE[1:-1] - zW[1:-1]) / (2 * dx_km[1:-1, None] * 1000.0)
        dzdy = (z[:-2] - z[2:]) / (2 * dy_km * 1000.0)
        okns = Lc & L[:-2] & L[2:] & np.isfinite(dzdy)
        ok = okns & LE[1:-1] & LW[1:-1] & np.isfinite(dzdx)
        slope = np.where(ok, np.degrees(np.arctan(np.hypot(dzdx, dzdy))), np.nan)
        sl = per_cell(slope)
        sm, ns = wmean(sl, wts)                                    # area-weighted mean, as for the Moon
        has = ns > 0
        sp = np.full(NC, np.nan)
        if has.any():
            sp[has] = np.nanpercentile(sl[has], 90, axis=1)         # unweighted percentile, as for the Moon
        out["slope_mean"][cells], out["slope_p90"][cells], out["n_slope"][cells] = sm, sp, ns
        # isotropic companion slope: east-west lag s = max(1, 1/cos(lat)) pixels, so the east-west
        # baseline never falls below the north-south one (same definition as the Moon's slope_iso_deg)
        dzdx_iso = np.full(zc.shape, np.nan)
        ok_iso = np.zeros(zc.shape, dtype=bool)
        # roughness: RMS height difference at a metric lag of one DEM pixel (dy) in both directions;
        # east-west pairs are taken 1/cos(lat) pixels apart along the row (linear interpolation),
        # as in the Moon table, so the deviogram baseline is the same everywhere
        dE = np.full(zc.shape, np.nan)
        for k in range(60):
            zrow, lrow = z[k + 1], L[k + 1]
            s = max(1.0, 1.0 / coslat[k + 1])
            zp, okp = shifted(zrow, lrow, s)
            zm, okm = shifted(zrow, lrow, -s)
            dzdx_iso[k] = (zp - zm) / (2.0 * s * dx_km[k + 1] * 1000.0)
            ok_iso[k] = okp & okm
            lag = 1.0 / coslat[k + 1]
            zl, okl = shifted(zrow, lrow, lag)
            dE[k] = np.where(lrow & okl, zl - zrow, np.nan)
        ok_iso &= okns
        slope_iso = np.where(ok_iso, np.degrees(np.arctan(np.hypot(dzdx_iso, dzdy))), np.nan)
        sli = per_cell(slope_iso)
        smi, nsi = wmean(sli, wts)
        spi = np.full(NC, np.nan)
        if (nsi > 0).any():
            spi[nsi > 0] = np.nanpercentile(sli[nsi > 0], 90, axis=1)
        out["slope_iso_mean"][cells], out["slope_iso_p90"][cells] = smi, spi
        dS = np.where(Lc & L[2:], z[2:] - zc, np.nan)               # south neighbour pairs (dy apart)
        sq = np.concatenate([per_cell(dE), per_cell(dS)], axis=1) ** 2
        npair = np.isfinite(sq).sum(1)
        with np.errstate(invalid="ignore"):
            out["rough"][cells] = np.where(npair > 0, np.sqrt(np.nansum(sq, 1) / np.maximum(npair, 1)), np.nan)
        if r % 30 == 0:
            print(f"  etopo row {r}", flush=True)
    ds.close()
    return out


# ---------------------------------------------------------------- LST (OpenLandMap MOD11A2)
def _lst_kelvin(raw, nodata):
    v = raw.astype(np.float64)
    v[(raw == nodata) | (raw <= 0)] = np.nan
    return v * 0.02                                  # MOD11A2 scale factor (K)


def _lst_diff_k(raw, nodata):
    v = raw.astype(np.float64)
    v[raw == nodata] = np.nan
    return v * 0.02


@cached("lst")
def stage_lst(download: bool):
    out = {}
    paths = {}
    for st in ("day", "night"):
        p = RAW / "lst" / f"clm_lst_mod11a2.annual.{st}_m.tif"
        if download:
            S.fetch(S.LST_URL.format(period="annual", stat=st), p)
        paths[st] = p
    # annual mean LST = mean of the day (~10:30) and night (~22:30) climatologies, where both exist
    acc_t, acc_a = Accum(), Accum()
    with rasterio.open(paths["day"]) as sd, rasterio.open(paths["night"]) as sn:
        assert sd.transform == sn.transform and sd.shape == sn.shape
        lat, lon = geo_axes(sd.transform, sd.height, sd.width)
        _, ccol = pixel_cell_index(np.zeros_like(lon), lon)
        for r0 in range(0, sd.height, 1200):
            h = min(1200, sd.height - r0)
            w = Window(0, r0, sd.width, h)
            d = _lst_kelvin(sd.read(1, window=w), sd.nodata)
            n = _lst_kelvin(sn.read(1, window=w), sn.nodata)
            rr, _ = pixel_cell_index(lat[r0:r0 + h], np.zeros(h))
            idx = np.where(rr[:, None] >= 0, rr[:, None] * NC + ccol[None, :], -1).ravel()
            both = np.isfinite(d) & np.isfinite(n)
            acc_t.add(idx, np.where(both, 0.5 * (d + n), np.nan).ravel())
            acc_a.add(idx, np.where(both, d - n, np.nan).ravel())
    out["lst_mean_k"], out["lst_amp_annual_k"], out["lst_npix"] = acc_t.mean(), acc_a.mean(), acc_t.n
    # monthly day-minus-night climatologies: streamed one at a time, deleted after use
    monthly = []
    for m in S.MONTHS:
        cache_m = CACHE / f"lst_daynight_{m}.npy"
        if cache_m.exists():
            monthly.append(np.load(cache_m))
            continue
        p = RAW / "lst" / f"clm_lst_mod11a2.{m}.daynight_m.tif"
        S.fetch(S.LST_URL.format(period=m, stat="daynight"), p, keep=False)
        acc = aggregate_geographic(str(p), _lst_diff_k)
        np.save(cache_m, acc.mean())
        monthly.append(acc.mean())
        p.unlink()
        S.mark_deleted(p.name)
        print(f"  lst daynight {m} done", flush=True)
    mon = np.vstack(monthly)
    with np.errstate(invalid="ignore"):
        out["lst_amp_max_k"] = np.nanmax(np.where(np.isfinite(mon), mon, -np.inf), axis=0)
    out["lst_amp_max_k"][~np.isfinite(out["lst_amp_max_k"])] = np.nan
    out["lst_amp_argmax_month"] = np.where(np.isfinite(out["lst_amp_max_k"]),
                                           np.argmax(np.where(np.isfinite(mon), mon, -np.inf), axis=0) + 1, 0)
    out["lst_amp_monthly_k"] = mon
    return out


# ---------------------------------------------------------------- WorldClim 2.1
DAYS_IN_MONTH = np.array([31, 28.25, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31])


def _wc_stack(var: str, download: bool) -> np.ndarray:
    z = RAW / "worldclim" / f"wc2.1_10m_{var}.zip"
    if download:
        S.fetch(S.WORLDCLIM_URL.format(var=var), z)
    arrs = []
    for m in range(1, 13):
        with rasterio.open(f"zip://{z}!wc2.1_10m_{var}_{m:02d}.tif") as src:
            assert src.shape == (1080, 2160) and abs(src.transform.a - 1 / 6) < 1e-9
            a = src.read(1).astype(np.float64)
            if src.nodata is not None:
                a[a == src.nodata] = np.nan
            a[~np.isfinite(a) | (np.abs(a) > 1e30)] = np.nan
            arrs.append(a)
    return np.stack(arrs)          # (12, 1080, 2160), north-up, origin -180/90


def _cell_mean_10m(a: np.ndarray) -> np.ndarray:
    b = a.reshape(NR, 6, NC, 6)
    n = np.isfinite(b).sum(axis=(1, 3))
    with np.errstate(invalid="ignore"):
        return np.where(n > 0, np.nansum(b, axis=(1, 3)) / np.maximum(n, 1), np.nan).ravel()


@cached("worldclim")
def stage_worldclim(download: bool):
    tmin = _wc_stack("tmin", download)
    wind = _wc_stack("wind", download)
    prec = _wc_stack("prec", download)
    srad = _wc_stack("srad", download)
    with np.errstate(invalid="ignore"):
        tmin_px = np.min(tmin, axis=0)                     # coldest-month mean daily minimum, deg C
        wind_px = np.max(wind, axis=0)                     # windiest-month mean speed, m/s
        prec_px = np.sum(prec, axis=0) / 365.25            # annual total / days, mm/day
        srad_px = np.sum(srad * DAYS_IN_MONTH[:, None, None], axis=0) / 365.25 / 3600.0  # kWh m-2 day-1
    return {"tmin_c": _cell_mean_10m(tmin_px), "wind_max_ms": _cell_mean_10m(wind_px),
            "rain_mm_day": _cell_mean_10m(prec_px), "irr_kwh": _cell_mean_10m(srad_px),
            "wc_npix": np.isfinite(tmin_px).reshape(NR, 6, NC, 6).sum(axis=(1, 3)).ravel().astype(float)}


# ---------------------------------------------------------------- permafrost (Obu et al.)
def _permafrost_one(zpath: Path, epsg: int, acc: Accum, cov: np.ndarray):
    from pyproj import Transformer
    tif = [n for n in zipfile.ZipFile(zpath).namelist() if n.endswith(".tif")][0]
    tr = Transformer.from_crs(epsg, 4326, always_xy=True)
    with rasterio.open(f"zip://{zpath}!{tif}") as src:
        t = src.transform
        xs = t.c + t.a * (np.arange(src.width) + 0.5)
        for r0 in range(0, src.height, 400):
            h = min(400, src.height - r0)
            a = src.read(1, window=Window(0, r0, src.width, h)).astype(np.float64)
            valid = (a >= 0) & (a <= 1)
            if not valid.any():
                continue
            ys = t.f + t.e * (np.arange(r0, r0 + h) + 0.5)
            rr_, cc_ = np.nonzero(valid)
            lon, lat = tr.transform(xs[cc_], ys[rr_])
            r, c = pixel_cell_index(np.asarray(lat), np.asarray(lon))
            idx = np.where(r >= 0, r * NC + c, -1)
            acc.add(idx, a[rr_, cc_])
            cov[idx[idx >= 0]] = True


@cached("permafrost")
def stage_permafrost(download: bool):
    acc = Accum()
    cov = np.zeros(NCELL, dtype=bool)
    for url, name, epsg in ((S.PERMAFROST_NH_URL, "UiO_PEX_PERPROB_5.0_20181128_2000_2016_NH.zip", 3995),
                            (S.PERMAFROST_ANT_URL, "UiO_PEX_PERPROB_5.0_20181205_2000_2017_ANT.zip", 3031)):
        z = RAW / "permafrost" / name
        if download:
            S.fetch(url, z)
        _permafrost_one(z, epsg, acc, cov)
        print(f"  permafrost {name} done", flush=True)
    return {"pf_frac": acc.mean(), "pf_npix": acc.n}


# ---------------------------------------------------------------- sun geometry (formula)
def sun_geometry(lat_deg: np.ndarray, obliquity_deg: float, n_lambda: int = 1440, n_hour: int = 2880):
    """sun_elev_max_deg (exact) and sun_low_frac_0_5deg (numerical time integral).

    Declination over a year on a circular orbit: sin(dec) = sin(eps) * sin(L), L uniform in time.
    Elevation: sin(h) = sin(lat) sin(dec) + cos(lat) cos(dec) cos(H), H uniform in time.
    sun_elev_max = 90 - max(0, |lat| - eps) (noon Sun at the solstice; geometric, no refraction).
    sun_low_frac = time(0 < h <= 5 deg) / time(h > 0), Sun centre treated as a point.
    """
    eps = math.radians(obliquity_deg)
    L = (np.arange(n_lambda) + 0.5) * 2 * np.pi / n_lambda
    dec = np.arcsin(math.sin(eps) * np.sin(L))
    H = (np.arange(n_hour) + 0.5) * 2 * np.pi / n_hour
    sd, cd, cH = np.sin(dec)[:, None], np.cos(dec)[:, None], np.cos(H)[None, :]
    elev_max = 90.0 - np.maximum(0.0, np.abs(lat_deg) - obliquity_deg)
    low = np.full(lat_deg.shape, np.nan)
    for la in np.unique(lat_deg):
        phi = math.radians(la)
        h = np.degrees(np.arcsin(np.clip(math.sin(phi) * sd + math.cos(phi) * cd * cH, -1, 1)))
        up = (h > 0).sum()
        low[lat_deg == la] = ((h > 0) & (h <= 5.0)).sum() / up if up else np.nan
    return elev_max, low


# ---------------------------------------------------------------- assemble
def load_class_map():
    with open(CLASS_MAP_FILE) as f:
        cm = json.load(f)["EARTH"]["thermal_inertia_class_from_esa_cci_lccs"]["classes"]
    return {int(k): v["category"] for k, v in cm.items()}


def pf_class(frac: np.ndarray) -> np.ndarray:
    out = np.full(frac.shape, "", dtype=object)
    f = frac
    out[np.isfinite(f) & (f < 0.01)] = "ninguno"
    out[np.isfinite(f) & (f >= 0.01)] = "esporadico"      # sporadic (10-50 %) and isolated (1-10 %)
    out[np.isfinite(f) & (f >= 0.5)] = "discontinuo"
    out[np.isfinite(f) & (f >= 0.9)] = "continuo"
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-download", action="store_true")
    args = ap.parse_args()
    dl = not args.no_download

    rows, cols, lat, lon = cell_centres()
    cci = stage_cci(dl)
    eto = stage_etopo(dl)
    lst = stage_lst(dl)
    wc = stage_worldclim(dl)
    pf = stage_permafrost(dl)

    counts = cci["counts"].astype(np.float64)
    total = counts.sum(1)
    water = counts[:, CCI_WATER]
    nod = counts[:, 0]
    landpx = total - water - nod
    with np.errstate(invalid="ignore", divide="ignore"):
        mask_fraction = np.where(total - nod > 0, landpx / (total - nod), np.nan)
        bare = counts[:, list(CCI_BARE)].sum(1)
        sparse = counts[:, list(CCI_SPARSE)].sum(1)
        rock_or_bare = np.where(landpx > 0, (bare + sparse) / np.maximum(landpx, 1), np.nan)
        bare_only = np.where(landpx > 0, bare / np.maximum(landpx, 1), np.nan)
        snow_ice = np.where(landpx > 0, counts[:, CCI_SNOW_ICE] / np.maximum(landpx, 1), np.nan)

    # thermal_inertia_class: category holding the largest share of the cell's CCI pixels
    cmap = load_class_map()
    cats = ["roca", "regolito", "arena", "suelo", "hielo", "agua"]
    catcounts = np.zeros((NCELL, len(cats)))
    for code, cat in cmap.items():
        catcounts[:, cats.index(cat)] += counts[:, code]
    ti = np.array(cats, dtype=object)[np.argmax(catcounts, axis=1)]
    ti[catcounts.sum(1) == 0] = ""
    dom_code = np.argmax(np.where(np.arange(256)[None, :] == 0, -1, counts), axis=1)
    dom_code = np.where(total - nod > 0, dom_code, 0)

    land = landpx > 0
    elev_max, low = sun_geometry(lat.astype(float), OBLIQUITY_EARTH_DEG)
    cell_km = np.array([meridian_arc_km(la - 0.5, la + 0.5) for la in 89.5 - np.arange(NR)])[rows]

    def landonly(a):
        return np.where(land, a, np.nan)

    pf_frac = pf["pf_frac"]
    df = pd.DataFrame({
        "body": "EARTH", "row": rows, "col": cols,
        "cell_id": ["E" + str(i) for i in range(NCELL)],
        "lat_deg": lat.astype(float), "lon_deg": lon.astype(float), "cell_km": np.round(cell_km, 3),
        "elevation_m": np.round(landonly(eto["elev_land"]), 1),
        "mask_fraction": np.round(mask_fraction, 4),
        "slope_deg": np.round(landonly(eto["slope_mean"]), 3),
        "slope_p90_deg": np.round(landonly(eto["slope_p90"]), 3),
        "slope_iso_deg": np.round(landonly(eto["slope_iso_mean"]), 3),
        "slope_iso_p90_deg": np.round(landonly(eto["slope_iso_p90"]), 3),
        "roughness_m": np.round(landonly(eto["rough"]), 2),
        "rock_or_bare_frac": np.round(landonly(rock_or_bare), 4),
        "temp_k": np.round(landonly(lst["lst_mean_k"]), 2),
        "lst_diurnal_amp_k": np.round(landonly(lst["lst_amp_annual_k"]), 2),
        "lst_diurnal_amp_max_k": np.round(landonly(lst["lst_amp_max_k"]), 2),
        "lst_diurnal_amp_max_month": np.where(land & (lst["lst_amp_argmax_month"] > 0), lst["lst_amp_argmax_month"], np.nan),
        "tmin_c": np.round(landonly(wc["tmin_c"]), 2),
        "irradiance_kwh_m2_day": np.round(landonly(wc["irr_kwh"]), 3),
        "sun_elev_max_deg": np.round(elev_max, 3),
        "sun_low_frac_0_5deg": np.round(low, 5),
        "thermal_inertia_class": ti,
        "permafrost_class": pf_class(landonly(pf_frac)),          # no class where CCI has no land
        "permafrost_area_frac": np.round(landonly(pf_frac), 4),
        "rain_mm_day": np.round(landonly(wc["rain_mm_day"]), 3),
        "wind_max_ms": np.round(landonly(wc["wind_max_ms"]), 2),
        # supporting columns
        "elevation_all_m": np.round(eto["elev_all"], 1),
        "bare_frac": np.round(landonly(bare_only), 4),
        "snow_ice_frac": np.round(landonly(snow_ice), 4),
        "lc_dominant_cci_code": np.where(dom_code > 0, dom_code, np.nan),
        "n_dem_land_px": eto["n_land"].astype(int),
        "n_dem_slope_px": eto["n_slope"].astype(int),
        "n_lst_px": lst["lst_npix"].astype(int),
        "n_worldclim_px": wc["wc_npix"].astype(int),
        "n_permafrost_px": pf["pf_npix"].astype(int),
    })
    # never 0-as-missing: integer-like supporting columns stay as written; classes empty = missing
    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT_CSV, index=False, float_format="%.6g", na_rep="")
    print(f"wrote {OUT_CSV} rows={len(df)}")


if __name__ == "__main__":
    main()
