#!/usr/bin/env python3
"""Build the 1-degree lunar real-data table for the Stars Beside You analog engine.

One command rebuilds everything (downloads only what is missing):

    python build_moon.py --raw-dir <scratch>/realdata/moon

Outputs
  ../output_real/moon_real_1deg.csv       64,800 cells, 1 degree, row 0 = north
  provenance_moon.csv                     one row per variable (level, product, URL, ...)
  manifest_moon.csv                       every downloaded file: URL, bytes, sha256
  lunar_named_sites.csv                   IAU features and the 1-degree cell they fall in
  checks_moon.json                        self-checks run at the end of the build
  column_aliases.json                     MOON section (merged, other bodies kept)

Rules followed (see README.md): no accounts, no keys, no Google Earth Engine, no NASA POWER;
one request per second per host; missing values are empty (NaN), never 0 or a fill value.
Deterministic: no random numbers, fixed quadrature grids, sorted outputs.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import math
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from urllib.parse import urlparse

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
REPO_DIR = HERE.parent  # ".../tierra luna"
OUT_DIR = REPO_DIR / "output_real"
DEFAULT_RAW = Path(
    "/tmp/claude-0/-home-user-NASA/7228bb30-9725-52d9-8d71-762c955fd0bd/scratchpad/stars/realdata/moon"
)

# ---------------------------------------------------------------------------
# Common grid (shared definition with the Earth table)
# ---------------------------------------------------------------------------
NROWS, NCOLS = 180, 360
ROW_LAT = 89.5 - np.arange(NROWS)          # centre latitude of each row
COL_LON = -179.5 + np.arange(NCOLS)        # centre longitude of each column

# ---------------------------------------------------------------------------
# Physical constants, each with its official source
# ---------------------------------------------------------------------------
MOON_RADIUS_M = 1737400.0   # reference sphere of LOLA/Diviner labels and NSSDC Moon fact sheet
MOON_OBLIQUITY_DEG = 1.54   # NASA Photojournal PIA13720: "tilted by only 1.54 deg"
SOLAR_CONSTANT_W_M2 = 1361.0  # NSSDC Moon fact sheet, "Solar irradiance (W/m2) 1361.0"
SUN_SEMIDIAMETER_DEG = 0.2666  # mean angular radius of the Sun at 1 au (959.6 arcsec)
SYNODIC_DAYS = 29.53        # NSSDC Moon fact sheet, synodic period

# Team lead decision (2026-11-14): permafrost_class is the label 'ninguno' (none) on every lunar
# cell, recorded in the provenance as a MODELLED label, not a measurement. The word is the
# team's own class name for "no permafrost" (mission_scoring.json permafrost maps and ice gate).
PERMAFROST_LABEL = "ninguno"

URL_PIA13720 = "https://science.nasa.gov/photojournal/south-pole-illumination-map"
URL_MOONFACT = "https://nssdc.gsfc.nasa.gov/planetary/factsheet/moonfact.html"
URL_MOONFACTS_REGOLITH = "https://science.nasa.gov/moon/facts/"

USER_AGENT = "Claude-User"  # on-demand, user-directed fetch; allowed by pds-geosciences robots.txt

PDSG = "https://pds-geosciences.wustl.edu"
LOLA_DIR = PDSG + "/lro/lro-l-lola-3-rdr-v1/lrolol_1xxx/data/lola_gdr/cylindrical/img"
DIV_DIR = PDSG + "/lro/urn-nasa-pds-lro_diviner_derived1"
GCP_BANDS = [
    "80n90n", "70n80n", "60n70n", "50n60n", "40n50n", "30n40n", "20n30n", "10n20n", "00n10n",
    "10s00s", "20s10s", "30s20s", "40s30s", "50s40s", "60s50s", "70s60s", "80s70s", "90s80s",
]
ILLUM_TIF = "https://pgda.gsfc.nasa.gov/data/MoonIllumination/AVGVISIB_{p}_240M_201608.TIF"
ILLUM_LBL = "https://imbrium.mit.edu/EXTRAS/ILLUMINATION/IMG/AVGVISIB_{p}_240M_201608.LBL"

SOURCES = {
    "ldem_16.img": LOLA_DIR + "/ldem_16.img",
    "ldem_16.lbl": LOLA_DIR + "/ldem_16.lbl",
    "ldem_4.img": LOLA_DIR + "/ldem_4.img",
    "ldem_4.lbl": LOLA_DIR + "/ldem_4.lbl",
    "dgdr_ra_avg_cyl_032_img.img": DIV_DIR + "/data_derived_gdr_l3/cylindrical/img/dgdr_ra_avg_cyl_032_img.img",
    "dgdr_ra_avg_cyl_032_img.lbl": DIV_DIR + "/data_derived_gdr_l3/cylindrical/img/dgdr_ra_avg_cyl_032_img.lbl",
    "dlre_gcp.fmt": DIV_DIR + "/label/dlre_gcp.fmt",
    "AVGVISIB_65S_240M_201608.TIF": ILLUM_TIF.format(p="65S"),
    "AVGVISIB_65N_240M_201608.TIF": ILLUM_TIF.format(p="65N"),
    "AVGVISIB_65S_240M_201608.LBL": ILLUM_LBL.format(p="65S"),
    "AVGVISIB_65N_240M_201608.LBL": ILLUM_LBL.format(p="65N"),
    "MOON_nomenclature_center_pts.zip":
        "https://asc-planetarynames-data.s3.us-west-2.amazonaws.com/MOON_nomenclature_center_pts.zip",
}
for _b in GCP_BANDS:
    SOURCES[f"global_cumul_avg_cyl_{_b}_002.lbl"] = f"{DIV_DIR}/data_derived_gcp/global_cumul_avg_cyl_{_b}_002.lbl"
    SOURCES[f"global_cumul_avg_cyl_{_b}_002.tab"] = f"{DIV_DIR}/data_derived_gcp/global_cumul_avg_cyl_{_b}_002.tab"


# ---------------------------------------------------------------------------
# Download with manifest and per-host rate limit
# ---------------------------------------------------------------------------
class Fetcher:
    """Downloads files with curl (uses the configured proxy), one request per second per host."""

    def __init__(self, raw_dir: Path):
        self.raw_dir = raw_dir
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        self.manifest_path = raw_dir / "manifest_moon_raw.json"
        self.manifest = json.loads(self.manifest_path.read_text()) if self.manifest_path.exists() else {}
        self._last = {}

    def _wait(self, host: str) -> None:
        last = self._last.get(host)
        if last is not None:
            delay = 1.05 - (time.monotonic() - last)
            if delay > 0:
                time.sleep(delay)
        self._last[host] = time.monotonic()

    @staticmethod
    def sha256(path: Path) -> str:
        h = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(1 << 22), b""):
                h.update(chunk)
        return h.hexdigest()

    def head(self, url: str) -> dict:
        host = urlparse(url).netloc
        self._wait(host)
        r = subprocess.run(["curl", "-sSIL", "-A", USER_AGENT, "--max-time", "60", url],
                           capture_output=True, text=True)
        status = re.findall(r"^HTTP/\S+\s+(\d+)", r.stdout, flags=re.M)
        length = re.findall(r"^content-length:\s*(\d+)", r.stdout, flags=re.M | re.I)
        ctype = re.findall(r"^content-type:\s*(\S+)", r.stdout, flags=re.M | re.I)
        return {"status": status[-1] if status else "error", "length": int(length[-1]) if length else None,
                "content_type": ctype[-1] if ctype else None}

    def get(self, name: str, used_for: str) -> Path:
        """Return the local path of a source file, downloading it (HEAD first) if needed."""
        url = SOURCES[name]
        dest = self.raw_dir / name
        if dest.exists() and name in self.manifest and dest.stat().st_size == self.manifest[name]["bytes"]:
            return dest
        head = self.head(url)
        if head["status"] != "200":
            raise RuntimeError(f"HEAD {url} -> {head}")
        if head["content_type"] and "html" in head["content_type"] and not name.endswith((".lbl", ".LBL", ".fmt")):
            raise RuntimeError(f"HEAD {url} returned HTML (soft 404?)")
        host = urlparse(url).netloc
        self._wait(host)
        tmp = dest.with_suffix(dest.suffix + ".part")
        subprocess.run(["curl", "-fsS", "-A", USER_AGENT, "--retry", "3", "--retry-delay", "5",
                        "-o", str(tmp), url], check=True)
        tmp.rename(dest)
        size = dest.stat().st_size
        if head["length"] is not None and size != head["length"]:
            raise RuntimeError(f"size mismatch for {url}: {size} vs {head['length']}")
        self.manifest[name] = {
            "file": name, "url": url, "bytes": size, "sha256": self.sha256(dest),
            "downloaded_utc": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "head_status": head["status"], "used_for": used_for, "kept_on_disk": "yes",
        }
        self.save()
        return dest

    def mark_deleted(self, name: str) -> None:
        if name in self.manifest:
            self.manifest[name]["kept_on_disk"] = "no (deleted after reduction; reduced cache kept)"
            self.save()

    def save(self) -> None:
        self.manifest_path.write_text(json.dumps(self.manifest, indent=1, sort_keys=True))


def parse_pds3_label(path: Path) -> dict:
    """Very small PDS3 label reader: KEY = VALUE pairs (first occurrence wins, units and quotes stripped)."""
    out = {}
    for line in Path(path).read_text(errors="replace").splitlines():
        m = re.match(r"^\s*([A-Z0-9_:^]+)\s*=\s*(.*?)\s*$", line)
        if m:
            val = m.group(2).split("<")[0].strip().strip('"')
            out.setdefault(m.group(1), val)
    return out


def area_weighted_block_mean(fine: np.ndarray, lat_fine: np.ndarray, k: int) -> np.ndarray:
    """Mean over k x k blocks of a (180k, 360k) array with cos(lat) pixel weights, NaN-aware."""
    w = np.cos(np.radians(lat_fine))[:, None] * np.ones((1, fine.shape[1]))
    valid = np.isfinite(fine)
    fw = np.where(valid, fine * w, 0.0)
    ww = np.where(valid, w, 0.0)
    nr, nc = fine.shape[0] // k, fine.shape[1] // k
    num = fw.reshape(nr, k, nc, k).sum(axis=(1, 3))
    den = ww.reshape(nr, k, nc, k).sum(axis=(1, 3))
    with np.errstate(invalid="ignore", divide="ignore"):
        return np.where(den > 0, num / den, np.nan)


# ---------------------------------------------------------------------------
# 1. LOLA LDEM_16: elevation, slope, roughness
# ---------------------------------------------------------------------------
def step_lola(fx: Fetcher, cache: Path) -> dict:
    cpath = cache / "lola_1deg.npz"
    img = fx.get("ldem_16.img", "elevation_m, slope_deg, slope_p90_deg, roughness_m")
    lbl = parse_pds3_label(fx.get("ldem_16.lbl", "label of LDEM_16 (scale, offset, layout)"))
    if cpath.exists():
        return dict(np.load(cpath))
    lines, samples = int(lbl["LINES"]), int(lbl["LINE_SAMPLES"])
    scale = float(lbl["SCALING_FACTOR"])
    ppd = int(float(lbl["MAP_RESOLUTION"]))
    assert (lines, samples, ppd) == (2880, 5760, 16), (lines, samples, ppd)
    assert lbl["SAMPLE_TYPE"] == "LSB_INTEGER" and lbl["SAMPLE_BITS"] == "16"
    assert float(lbl["WESTERNMOST_LONGITUDE"]) == 0.0 and float(lbl["EASTERNMOST_LONGITUDE"]) == 360.0
    dn = np.fromfile(img, dtype="<i2").reshape(lines, samples)
    # Height relative to the 1737.4 km sphere: HEIGHT = DN * SCALING_FACTOR (label NOTE).
    z = dn.astype(np.float64) * scale
    # Longitude 0..360 (sample j centre = (j+0.5)/16) -> -180..180: column k centre = -180 + (k+0.5)/16.
    z = np.roll(z, -samples // 2, axis=1)
    lat = 90.0 - (np.arange(lines) + 0.5) / ppd
    dy = MOON_RADIUS_M * math.radians(1.0 / ppd)               # north-south pixel spacing (m)
    coslat = np.cos(np.radians(lat))
    dx = dy * coslat                                            # east-west pixel spacing (m)

    # Neighbour rows across the pole: the pixel at the same latitude, longitude + 180 deg.
    half = samples // 2
    z_n = np.vstack([np.roll(z[0:1], half, axis=1), z[:-1]])   # row above (north neighbour)
    z_s = np.vstack([z[1:], np.roll(z[-1:], half, axis=1)])     # row below (south neighbour)
    dzdy = (z_n - z_s) / (2.0 * dy)
    dzdx = (np.roll(z, -1, axis=1) - np.roll(z, 1, axis=1)) / (2.0 * dx[:, None])
    slope = np.degrees(np.arctan(np.hypot(dzdx, dzdy)))

    # Roughness: RMS height difference at a lag of one DEM pixel (1/16 deg = dy metres).
    # North-south pairs are exactly dy apart. East-west pairs are taken at the same metric lag dy,
    # i.e. 1/cos(lat) pixels along the row (linear interpolation, periodic in longitude), so the
    # deviogram baseline is the same in both directions and at every latitude.
    sq_ns = (z_s - z) ** 2                                      # pair (i, i+1) assigned to row i
    sq_ns[-1] = np.nan                                          # last row pairs across the pole: skip
    sq_ew = np.empty_like(z)
    xs = np.arange(samples, dtype=np.float64)
    for i in range(lines):
        lag = 1.0 / coslat[i]
        zi = z[i]
        shifted = np.interp(xs + lag, np.r_[xs, samples], np.r_[zi, zi[0]], period=samples)
        sq_ew[i] = (shifted - zi) ** 2

    k = ppd
    elev = area_weighted_block_mean(z, lat, k)
    slope_mean = area_weighted_block_mean(slope, lat, k)
    blocks = slope.reshape(NROWS, k, NCOLS, k).transpose(0, 2, 1, 3).reshape(NROWS, NCOLS, k * k)
    slope_p90 = np.percentile(blocks, 90, axis=2)
    ns_sum = np.nansum(sq_ns.reshape(NROWS, k, NCOLS, k), axis=(1, 3))
    ns_cnt = np.isfinite(sq_ns).reshape(NROWS, k, NCOLS, k).sum(axis=(1, 3))
    ew_sum = sq_ew.reshape(NROWS, k, NCOLS, k).sum(axis=(1, 3))
    ew_cnt = np.full_like(ew_sum, k * k)
    rough = np.sqrt((ns_sum + ew_sum) / (ns_cnt + ew_cnt))
    valid = np.isfinite(z).reshape(NROWS, k, NCOLS, k).sum(axis=(1, 3))

    # Companion columns slope_iso_deg / slope_iso_p90_deg: east-west derivative over a lag of
    # max(1, 1/cos lat) pixels (linear interpolation), so the east-west baseline never drops below the
    # north-south one. Near the poles the literal 1-pixel east-west spacing falls to metres, far below
    # the true ~1.9 km resolution of LDEM_16, and the literal slope picks up interpolation noise.
    dzdx_iso = np.empty_like(z)
    for i in range(lines):
        lag = max(1.0, 1.0 / coslat[i])
        zi = z[i]
        xp, fp = np.r_[xs, samples], np.r_[zi, zi[0]]
        dzdx_iso[i] = (np.interp(xs + lag, xp, fp, period=samples)
                       - np.interp(xs - lag, xp, fp, period=samples)) / (2.0 * lag * dx[i])
    slope_iso_px = np.degrees(np.arctan(np.hypot(dzdx_iso, dzdy)))
    slope_iso = area_weighted_block_mean(slope_iso_px, lat, k)
    slope_iso_p90 = np.percentile(
        slope_iso_px.reshape(NROWS, k, NCOLS, k).transpose(0, 2, 1, 3).reshape(NROWS, NCOLS, k * k), 90, axis=2)

    out = {"elevation_m": elev, "slope_deg": slope_mean, "slope_p90_deg": slope_p90,
           "roughness_m": rough, "dem_valid_pixels": valid.astype(float), "slope_iso_deg": slope_iso,
           "slope_iso_p90_deg": slope_iso_p90,
           "dy_m": np.array(dy)}
    np.savez_compressed(cpath, **out)
    return out


# ---------------------------------------------------------------------------
# 2. Diviner Global Cumulative Products (GCP): bolometric temperature by local time
# ---------------------------------------------------------------------------
GCP_MIN_VALID = 40      # of 96 local-time bins (0.25 h each)
GCP_MAX_GAP = 12        # bins (3 h); longest observed gap in a sample of the files was 7 bins


def _reduce_gcp_file(tab: Path, lbl: dict) -> dict:
    """Return per-0.5-degree diurnal statistics of tbol for one 10-degree latitude band."""
    # Some GCP labels have MINIMUM/MAXIMUM_LATITUDE swapped (e.g. the 40s30s band): take the extremes.
    a, b = float(lbl["MINIMUM_LATITUDE"]), float(lbl["MAXIMUM_LATITUDE"])
    lat_min, lat_max = min(a, b), max(a, b)
    cols = ["clon", "clat", "ltim", "t3", "t4", "t5", "t6", "t7", "t8", "t9", "tbol"]
    df = pd.read_csv(tab, header=None, names=cols, skiprows=1, skipinitialspace=True,
                     usecols=["clon", "clat", "ltim", "tbol"], dtype=np.float64)
    assert len(df) == int(lbl.get("ROWS", 1382400)), len(df)
    ilon = np.rint((df.clon.values + 179.75) / 0.5).astype(int)
    ilat = np.rint((lat_max - 0.25 - df.clat.values) / 0.5).astype(int)   # 0 = northernmost
    ilt = np.rint((df.ltim.values - 0.125) / 0.25).astype(int)
    assert ilon.min() == 0 and ilon.max() == 719 and ilat.min() == 0 and ilat.max() == 19, (lat_min, lat_max)
    assert abs(df.clat.min() - (lat_min + 0.25)) < 1e-6 and abs(df.clat.max() - (lat_max - 0.25)) < 1e-6
    assert ilt.min() == 0 and ilt.max() == 95
    tb = np.full((20, 720, 96), np.nan)
    v = df.tbol.values
    v = np.where(v <= -9000, np.nan, v)        # -9999 = no observations (label)
    n_nonpos = int(np.sum(v <= 0))
    v = np.where(v <= 0, np.nan, v)           # a bolometric temperature must be positive
    tb[ilat, ilon, ilt] = v
    flat = tb.reshape(-1, 96)
    nvalid = np.isfinite(flat).sum(axis=1)
    tmean = np.full(flat.shape[0], np.nan)
    tmax = np.full(flat.shape[0], np.nan)
    tmin = np.full(flat.shape[0], np.nan)
    maxgap = np.full(flat.shape[0], 96)
    x = np.arange(96, dtype=float)
    for c in np.nonzero(nvalid >= GCP_MIN_VALID)[0]:
        row = flat[c]
        idx = np.nonzero(np.isfinite(row))[0]
        gap = int(np.diff(np.r_[idx, idx[0] + 96]).max() - 1)
        maxgap[c] = gap
        if gap > GCP_MAX_GAP:
            continue
        full = np.interp(x, idx.astype(float), row[idx], period=96)   # circular linear interpolation
        tmean[c], tmax[c], tmin[c] = full.mean(), full.max(), full.min()
    shape = (20, 720)
    lat_c = lat_max - 0.25 - 0.5 * np.arange(20)
    return {"lat_c": lat_c, "tmean": tmean.reshape(shape), "tmax": tmax.reshape(shape),
            "tmin": tmin.reshape(shape), "nvalid": nvalid.reshape(shape), "maxgap": maxgap.reshape(shape),
            "n_nonpos": np.array(n_nonpos), "lat_min": np.array(lat_min)}


def step_diviner_gcp(fx: Fetcher, cache: Path, keep_raw: bool) -> dict:
    fx.get("dlre_gcp.fmt", "column layout of the Diviner GCP tables")
    half = {"tmean": np.full((360, 720), np.nan), "tmax": np.full((360, 720), np.nan),
            "tmin": np.full((360, 720), np.nan), "nvalid": np.zeros((360, 720)),
            "maxgap": np.full((360, 720), 96.0)}
    n_nonpos = 0
    label_swaps = []
    for band in GCP_BANDS:
        cpath = cache / f"gcp_{band}.npz"
        lname, tname = f"global_cumul_avg_cyl_{band}_002.lbl", f"global_cumul_avg_cyl_{band}_002.tab"
        lbl = parse_pds3_label(fx.get(lname, "label of a Diviner GCP band"))
        if not cpath.exists():
            tab = fx.get(tname, "temp_k, lst_diurnal_amp_k, tmin_c (Diviner GCP tbol)")
            red = _reduce_gcp_file(tab, lbl)
            np.savez_compressed(cpath, **red)
            if not keep_raw:
                tab.unlink()
                fx.mark_deleted(tname)
        red = dict(np.load(cpath))
        top = max(float(lbl["MINIMUM_LATITUDE"]), float(lbl["MAXIMUM_LATITUDE"]))
        if float(lbl["MINIMUM_LATITUDE"]) > float(lbl["MAXIMUM_LATITUDE"]):
            label_swaps.append(band)
        r0 = int(round((90.0 - top) / 0.5))
        assert abs(float(red["lat_c"][0]) - (top - 0.25)) < 1e-9
        for key in half:
            half[key][r0:r0 + 20] = red[key]
        n_nonpos += int(red["n_nonpos"])
    # Half-degree grid columns already run from -179.75 (west) eastward: same order as the 1-degree grid.
    lat_half = 89.75 - 0.5 * np.arange(360)
    out = {}
    for key in ("tmean", "tmax", "tmin"):
        out[key] = area_weighted_block_mean(half[key], lat_half, 2)
    out["n_sub"] = np.isfinite(half["tmean"]).reshape(180, 2, 360, 2).sum(axis=(1, 3)).astype(float)
    out["n_nonpos"] = n_nonpos
    out["label_lat_swapped"] = label_swaps
    out["half_nvalid"] = half["nvalid"]
    out["half_maxgap"] = half["maxgap"]
    return out


# ---------------------------------------------------------------------------
# 3. Diviner rock abundance (Bandfield et al. 2011), 60S-60N, 32 px/deg
# ---------------------------------------------------------------------------
RA_MIN_VALID_FRAC = 0.5


def step_rock(fx: Fetcher, cache: Path) -> dict:
    cpath = cache / "rock_1deg.npz"
    img = fx.get("dgdr_ra_avg_cyl_032_img.img", "rock_abundance_frac")
    lbl = parse_pds3_label(fx.get("dgdr_ra_avg_cyl_032_img.lbl", "label of Diviner rock abundance"))
    if cpath.exists():
        return dict(np.load(cpath))
    lines, samples = int(lbl["LINES"]), int(lbl["LINE_SAMPLES"])
    ppd = int(float(lbl["MAP_RESOLUTION"]))
    lat_top, lat_bot = float(lbl["MAXIMUM_LATITUDE"]), float(lbl["MINIMUM_LATITUDE"])
    assert (lines, samples, ppd, lat_top, lat_bot) == (3840, 11520, 32, 60.0, -60.0)
    assert float(lbl["WESTERNMOST_LONGITUDE"]) == 0.0
    dn = np.fromfile(img, dtype="<i2").reshape(lines, samples)
    miss = int(lbl["MISSING_CONSTANT"])
    ra = np.where(dn == miss, np.nan, dn * float(lbl["SCALING_FACTOR"]) + float(lbl["OFFSET"]))
    ra = np.roll(ra, -samples // 2, axis=1)
    lat = lat_top - (np.arange(lines) + 0.5) / ppd
    band = area_weighted_block_mean(ra, lat, ppd)            # 120 x 360 cells
    frac = np.isfinite(ra).reshape(120, ppd, 360, ppd).mean(axis=(1, 3))
    band = np.where(frac >= RA_MIN_VALID_FRAC, band, np.nan)
    full = np.full((NROWS, NCOLS), np.nan)
    fvalid = np.zeros((NROWS, NCOLS))
    r0 = int(90 - lat_top)
    full[r0:r0 + 120] = band
    fvalid[r0:r0 + 120] = frac
    out = {"rock": full, "valid_frac": fvalid, "raw_max": np.array(np.nanmax(ra))}
    np.savez_compressed(cpath, **out)
    return out


# ---------------------------------------------------------------------------
# 4. LOLA polar average illumination (Mazarico et al. 2011), 65-90 N/S, 240 m
# ---------------------------------------------------------------------------
def step_illum(fx: Fetcher, cache: Path) -> dict:
    import rasterio

    cpath = cache / "illum_1deg.npz"
    paths = {p: fx.get(f"AVGVISIB_{p}_240M_201608.TIF", "illum_frac (polar, LOLA topographic simulation)") for p in ("65S", "65N")}
    labels = {p: parse_pds3_label(fx.get(f"AVGVISIB_{p}_240M_201608.LBL", "label of illumination map")) for p in ("65S", "65N")}
    if cpath.exists():
        return dict(np.load(cpath))
    num = np.zeros((NROWS, NCOLS))
    cnt = np.zeros((NROWS, NCOLS))
    info = {}
    for p, path in paths.items():
        lbl = labels[p]
        south = p.endswith("S")
        with rasterio.open(path) as src:
            a = src.read(1).astype(np.float64)
            nodata = src.nodata
            tr = src.transform
            scales, offsets = src.scales, src.offsets
            crs = src.crs.to_wkt() if src.crs else ""
        info[p] = {"dtype_max": float(np.nanmax(a)), "nodata": nodata, "scales": scales, "offsets": offsets}
        # Physical value: if the GeoTIFF still holds DN (max > 1.5), apply the label scaling.
        if nodata is not None:
            a = np.where(a == nodata, np.nan, a)
        if np.nanmax(a) > 1.5:
            a = a * float(lbl["SCALING_FACTOR"]) + float(lbl["OFFSET"])
        h, w = a.shape
        cols = np.arange(w) + 0.5
        rows = np.arange(h) + 0.5
        x = tr.c + tr.a * cols                     # map x (m) of pixel centres
        y = tr.f + tr.e * rows                     # map y (m)
        X, Y = np.meshgrid(x, y)
        rho = np.hypot(X, Y)
        # Spherical polar stereographic, true scale at the pole: rho = 2 R tan((90 - |lat|)/2).
        colat = 2.0 * np.degrees(np.arctan(rho / (2.0 * MOON_RADIUS_M)))
        if south:
            latp = -90.0 + colat
            lonp = np.degrees(np.arctan2(X, Y))    # centre longitude 0, south-pole aspect
        else:
            latp = 90.0 - colat
            lonp = np.degrees(np.arctan2(X, -Y))   # north-pole aspect
        ok = np.isfinite(a) & (np.abs(latp) >= 65.0)
        ri = np.clip(np.floor(90.0 - latp[ok]).astype(int), 0, NROWS - 1)
        ci = np.clip(np.floor(lonp[ok] + 180.0).astype(int), 0, NCOLS - 1)
        np.add.at(num, (ri, ci), a[ok])
        np.add.at(cnt, (ri, ci), 1.0)
        info[p]["crs"] = crs[:200]
        info[p]["pixels_used"] = int(ok.sum())
    with np.errstate(invalid="ignore", divide="ignore"):
        illum = np.where(cnt > 0, num / cnt, np.nan)
    # Only rows that lie entirely inside 65-90 degrees (centre |lat| >= 65.5).
    polar_rows = np.abs(ROW_LAT) >= 65.5
    illum[~polar_rows] = np.nan
    out = {"illum": illum, "pixels": cnt, "info": np.array(json.dumps(info, default=str))}
    np.savez_compressed(cpath, **out)
    return out


# ---------------------------------------------------------------------------
# 5. Sun geometry (exact formulas, numerical quadrature on fixed grids)
# ---------------------------------------------------------------------------
def sun_geometry(lat_deg: np.ndarray, obliquity_deg: float, n_season: int = 720, n_hour: int = 2880) -> dict:
    """Year-averaged Sun geometry for a horizontal surface on a sphere, Sun centre, no atmosphere.

    Solar declination over the year: sin(d) = sin(eps) sin(L), L uniform in [0, 360) (circular orbit).
    Elevation: sin(h) = sin(phi) sin(d) + cos(phi) cos(d) cos(H), hour angle H uniform in [0, 360).
    Returns, per latitude:
      sun_elev_max_deg  = 90 - max(0, |phi| - eps)                        (closed form)
      day_frac          = time fraction with h > 0 (Sun centre)
      disc_frac         = time fraction with h > -semi-diameter (any part of the disc visible)
      low_frac          = time with 0 < h < 5 deg divided by time with h > 0
      mean_sin_pos      = time mean of max(0, sin h)          (=> insolation / S0)
      mean_sin_day      = mean of sin h over the time with h > 0
    """
    eps = math.radians(obliquity_deg)
    L = (np.arange(n_season) + 0.5) * 2.0 * math.pi / n_season
    dec = np.arcsin(math.sin(eps) * np.sin(L))
    H = (np.arange(n_hour) + 0.5) * 2.0 * math.pi / n_hour
    cosH = np.cos(H)
    sin5 = math.sin(math.radians(5.0))
    sin_sd = math.sin(math.radians(-SUN_SEMIDIAMETER_DEG))
    res = {k: np.zeros(len(lat_deg)) for k in ("day_frac", "disc_frac", "low_frac", "mean_sin_pos", "mean_sin_day")}
    sd, cd = np.sin(dec)[:, None], np.cos(dec)[:, None]
    for i, phi in enumerate(np.radians(lat_deg)):
        s = math.sin(phi) * sd + math.cos(phi) * cd * cosH[None, :]
        up = s > 0
        n_up = up.sum()
        res["day_frac"][i] = n_up / s.size
        res["disc_frac"][i] = (s > sin_sd).sum() / s.size
        res["low_frac"][i] = ((s > 0) & (s < sin5)).sum() / n_up if n_up else np.nan
        res["mean_sin_pos"][i] = np.where(up, s, 0.0).mean()
        res["mean_sin_day"][i] = s[up].mean() if n_up else np.nan
    res["sun_elev_max_deg"] = 90.0 - np.maximum(0.0, np.abs(lat_deg) - obliquity_deg)
    return res


# ---------------------------------------------------------------------------
# 6. IAU named sites
# ---------------------------------------------------------------------------
NAMED_SITES = [
    # (IAU name, why it matters, note)
    ("Shackleton", "south-polar rim: highly illuminated rim, shadowed interior (solar/ice)", "crater centre; the lit rim and the PSR floor share the cell"),
    ("de Gerlache", "NASA candidate landing region 'de Gerlache Rim 2' (announced October 2024)", "crater centre, not the rim region"),
    ("Mons Malapert", "NASA candidate landing region 'Malapert Massif' (announced October 2024)", "massif centre; 'Malapert Massif' is an informal name"),
    ("Mons Mouton", "NASA candidate landing region 'Mons Mouton Plateau' (announced October 2024)", "mons centre"),
    ("Nobile", "NASA candidate landing regions 'Nobile Rim 1' and 'Nobile Rim 2' (announced October 2024)", "crater centre, not the rim regions"),
    ("Haworth", "NASA candidate landing region 'Haworth' (announced October 2024)", "crater centre"),
    ("Cabeus", "LCROSS impact crater, south-polar PSR (ice)", "crater centre"),
    ("Cabeus B", "NASA candidate landing region 'Peak near Cabeus B' (announced October 2024)", "satellite crater centre, not the peak"),
    ("Slater", "NASA candidate landing region 'Slater Plain' (announced October 2024)", "crater centre"),
    ("Tycho", "young rayed crater, rough rocky reference", "crater centre"),
    ("Statio Tranquillitatis", "Apollo 11 landing site", "IAU statio = landing site"),
    ("Surveyor", "Apollo 12 site (astronaut-named crater beside the LM)", "proxy for the landing point"),
    ("Cone", "Apollo 14 site (astronaut-named crater)", "proxy for the landing point"),
    ("Dune", "Apollo 15 site (astronaut-named crater)", "proxy for the landing point"),
    ("Flag", "Apollo 16 site (astronaut-named crater)", "proxy for the landing point"),
    ("Taurus Littrow Valley", "Apollo 17 site (astronaut-named valley)", "valley centre"),
    ("Statio Shiv Shakti", "Chandrayaan-3 landing site, high southern latitude", "IAU statio = landing site"),
]


def step_named_sites(fx: Fetcher, cache: Path) -> pd.DataFrame:
    import zipfile

    z = fx.get("MOON_nomenclature_center_pts.zip", "lunar_named_sites.csv (IAU names and coordinates)")
    dbf_cache = cache / "gazetteer_sites.csv"
    if not dbf_cache.exists():
        import geopandas as gpd

        exdir = cache / "gazetteer"
        exdir.mkdir(exist_ok=True)
        with zipfile.ZipFile(z) as zf:
            for m in zf.namelist():
                if m.lower().endswith((".shp", ".shx", ".dbf", ".prj", ".cpg")):
                    target = exdir / Path(m).name
                    target.write_bytes(zf.read(m))
        shp = next(exdir.glob("*.shp"))
        g = gpd.read_file(shp)
        names = [n for n, _, _ in NAMED_SITES]
        sel = g[g["clean_name"].isin(names)][["clean_name", "type", "center_lat", "center_lon", "diameter", "origin", "link"]]
        sel.to_csv(dbf_cache, index=False)
    return pd.read_csv(dbf_cache)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--raw-dir", type=Path, default=DEFAULT_RAW, help="where raw downloads and caches live")
    ap.add_argument("--keep-raw", action="store_true", help="keep the 18 Diviner GCP tables (2.8 GB)")
    args = ap.parse_args()
    raw = args.raw_dir
    cache = raw / "reduced"
    cache.mkdir(parents=True, exist_ok=True)
    fx = Fetcher(raw)

    print("[1/6] LOLA LDEM_16 relief", flush=True)
    lola = step_lola(fx, cache)
    print("[2/6] Diviner GCP temperatures", flush=True)
    gcp = step_diviner_gcp(fx, cache, args.keep_raw)
    print("[3/6] Diviner rock abundance", flush=True)
    rock = step_rock(fx, cache)
    print("[4/6] LOLA polar illumination", flush=True)
    ill = step_illum(fx, cache)
    print("[5/6] Sun geometry", flush=True)
    sg = sun_geometry(ROW_LAT, MOON_OBLIQUITY_DEG)

    # ---- assemble -----------------------------------------------------------
    rr, cc = np.meshgrid(np.arange(NROWS), np.arange(NCOLS), indexing="ij")
    lat2 = ROW_LAT[rr]
    cell_km = MOON_RADIUS_M * math.radians(1.0) / 1000.0

    illum_meas = ill["illum"]
    illum = np.where(np.isfinite(illum_meas), illum_meas, sg["disc_frac"][rr])
    # Mazarico AVGVISIB is a LOLA-team ray-traced simulation from measured LOLA topography, not a light measurement:
    # both cases are DERIVED; the level column says which method was used.
    illum_level = np.where(np.isfinite(illum_meas), "DERIVED_LOLA_TOPOGRAPHY", "DERIVED_FLAT_GEOMETRY")
    # Insolation on a horizontal surface, in kWh per m2 per 24-hour Earth day.
    #   geometric (DERIVED):  Q = S0 * <max(0, sin h)> * 24 / 1000
    #   with the LOLA topographic lit fraction f: Q = S0 * f * <sin h | Sun up> * 24 / 1000
    #   (f replaces the geometric daylight fraction, so night is not counted twice).
    q_geo = SOLAR_CONSTANT_W_M2 * sg["mean_sin_pos"][rr] * 24.0 / 1000.0
    q_meas = SOLAR_CONSTANT_W_M2 * illum_meas * sg["mean_sin_day"][rr] * 24.0 / 1000.0
    irr = np.where(np.isfinite(illum_meas), q_meas, q_geo)

    tmin_k = gcp["tmin"]
    cols = {
        "body": np.full(rr.shape, "MOON", dtype=object),
        "row": rr, "col": cc,
        "cell_id": np.char.add("M", (rr * NCOLS + cc).astype(str)),
        "lat_deg": lat2, "lon_deg": COL_LON[cc],
        "cell_km": np.full(rr.shape, round(cell_km, 3)),
        "elevation_m": np.round(lola["elevation_m"], 1),
        "slope_deg": np.round(lola["slope_deg"], 3),
        "slope_p90_deg": np.round(lola["slope_p90_deg"], 3),
        "slope_iso_deg": np.round(lola["slope_iso_deg"], 3),
        "slope_iso_p90_deg": np.round(lola["slope_iso_p90_deg"], 3),
        "roughness_m": np.round(lola["roughness_m"], 2),
        "mask_fraction": np.ones(rr.shape),
        "rock_or_bare_frac": np.ones(rr.shape),
        "rock_abundance_frac": np.round(rock["rock"], 4),
        "temp_k": np.round(gcp["tmean"], 2),
        "tmax_k": np.round(gcp["tmax"], 2),
        "tmin_k": np.round(tmin_k, 2),
        "lst_diurnal_amp_k": np.round(gcp["tmax"] - gcp["tmin"], 2),
        "tmin_c": np.round(tmin_k - 273.15, 2),
        "temp_n_subcells": gcp["n_sub"].astype(int),
        "illum_frac": np.round(illum, 4),
        "illum_frac_level": illum_level,
        "irradiance_kwh_m2_day": np.round(irr, 3),
        "sun_elev_max_deg": np.round(sg["sun_elev_max_deg"][rr], 3),
        "sun_low_frac_0_5deg": np.round(sg["low_frac"][rr], 4),
        "thermal_inertia_class": np.full(rr.shape, "regolito", dtype=object),
        # Team lead decision (2026-11-14): the label 'ninguno' on every cell, a MODELLED
        # label (no liquid water or seasonal thaw on the Moon), not a measurement.
        "permafrost_class": np.full(rr.shape, PERMAFROST_LABEL, dtype=object),
        "rain_mm_day": np.full(rr.shape, np.nan),
        "wind_max_ms": np.full(rr.shape, np.nan),
    }
    df = pd.DataFrame({k: np.asarray(v).ravel() for k, v in cols.items()})
    OUT_DIR.mkdir(exist_ok=True)
    out_csv = OUT_DIR / "moon_real_1deg.csv"
    df.to_csv(out_csv, index=False, na_rep="", float_format="%.6g")
    print(f"wrote {out_csv} ({len(df)} rows)", flush=True)

    # ---- named sites ------------------------------------------------------------
    print("[6/6] named sites, provenance, manifest, checks", flush=True)
    gz = step_named_sites(fx, cache)
    site_rows = []
    keep_cols = ["elevation_m", "slope_deg", "slope_p90_deg", "slope_iso_deg", "slope_iso_p90_deg", "roughness_m",
                 "rock_abundance_frac", "temp_k",
                 "tmax_k", "tmin_k", "lst_diurnal_amp_k", "illum_frac", "illum_frac_level",
                 "irradiance_kwh_m2_day", "sun_elev_max_deg", "sun_low_frac_0_5deg"]
    for name, why, note in NAMED_SITES:
        hit = gz[gz.clean_name == name]
        if hit.empty:
            site_rows.append({"iau_name": name, "why": why, "status": "not found in gazetteer"})
            continue
        h = hit.iloc[0]
        lon360 = float(h.center_lon)
        lon180 = ((lon360 + 180.0) % 360.0) - 180.0
        r = min(int(math.floor(90.0 - float(h.center_lat))), NROWS - 1)
        c = min(int(math.floor(lon180 + 180.0)), NCOLS - 1)
        cell = df.iloc[r * NCOLS + c]
        ew_km = cell_km * math.cos(math.radians(float(cell.lat_deg)))
        diam = float(h.diameter) if pd.notna(h.diameter) else 0.0
        if ew_km < 0.5 * cell_km:
            fit = (f"polar cell: {cell_km:.1f} km north-south by only {ew_km:.2f} km east-west, a strip that "
                   "cuts across rims, slopes and floors; the value averages lit and shadowed ground along it")
        elif diam < cell_km:
            fit = (f"feature ({diam:.1f} km) smaller than the {cell_km:.0f} x {ew_km:.0f} km cell: the value "
                   "averages it with its surroundings and cannot resolve it")
        else:
            fit = (f"feature ({diam:.0f} km) larger than the cell: the value describes only the part of it "
                   "inside the cell")
        rec = {"iau_name": name, "iau_type": h["type"], "why": why, "site_note": note,
               "lat_deg": float(h.center_lat), "lon_east_0_360": lon360, "lon_deg": round(lon180, 4),
               "diameter_km": h.diameter, "cell_id": cell.cell_id, "cell_row": r, "cell_col": c,
               "cell_lat_deg": cell.lat_deg, "cell_lon_deg": cell.lon_deg,
               "cell_ns_km": round(cell_km, 2), "cell_ew_km": round(ew_km, 3), "feature_vs_cell": fit,
               "gazetteer_link": h.link}
        for k in keep_cols:
            rec["cell_" + k] = cell[k]
        site_rows.append(rec)
    site_rows.append({
        "iau_name": "(none) 'Connecting Ridge' between Shackleton and de Gerlache", "iau_type": "informal name",
        "why": "most illuminated south-polar site in Glaser et al. 2014 (92.27 % at 2 m, 95.65 % at 10 m)",
        "site_note": "not an IAU name and no coordinates in the cited sources (R2 notes): no cell assigned. "
                     "It lies between the Shackleton and de Gerlache rows above; its sub-km ridge crest cannot "
                     "be seen in any 1-degree value (cell illum_frac is a strip average, ~0.06-0.15 here).",
    })
    sites = pd.DataFrame(site_rows)
    sites.to_csv(HERE / "lunar_named_sites.csv", index=False)

    # ---- manifest ---------------------------------------------------------------
    man = pd.DataFrame(sorted(fx.manifest.values(), key=lambda d: d["file"]))
    man = man[["file", "url", "bytes", "sha256", "downloaded_utc", "head_status", "used_for", "kept_on_disk"]]
    man.to_csv(HERE / "manifest_moon.csv", index=False)

    # ---- provenance, aliases, checks ----------------------------------------------
    write_provenance(sg, lola, gcp, rock, ill)
    write_aliases(float(lola["dy_m"]))
    ldem4 = (fx.get("ldem_4.img", "self-check only: elevation vs the committed 2-degree table"),
             parse_pds3_label(fx.get("ldem_4.lbl", "self-check only: LDEM_4 label")))
    checks = run_checks(df, lola, gcp, rock, ill, sg, ldem4)
    (HERE / "checks_moon.json").write_text(json.dumps(checks, indent=1, default=float))
    print(json.dumps(checks["summary"], indent=1, default=float))
    return 0


# ---------------------------------------------------------------------------
# Provenance
# ---------------------------------------------------------------------------
LIC_PDS = ("NASA PDS data: publicly released, no access restrictions; NASA-produced data are not subject "
           "to US copyright (licence string not stated on the product page). Credit: ")


def write_provenance(sg, lola, gcp, rock, ill) -> None:
    i_eq = int(np.argmin(np.abs(ROW_LAT - 0.5)))
    i_45 = int(np.argmin(np.abs(ROW_LAT - 45.5)))
    i_85 = int(np.argmin(np.abs(ROW_LAT - 85.5)))
    q = lambda i: SOLAR_CONSTANT_W_M2 * sg["mean_sin_pos"][i] * 0.024  # noqa: E731
    qd = lambda i: SOLAR_CONSTANT_W_M2 * sg["mean_sin_day"][i] * 0.024  # noqa: E731
    illum_85 = np.nanmedian(ill["illum"][i_85])
    lola_url = SOURCES["ldem_16.img"]
    lola_credit = ("LOLA team, LRO (Smith et al. 2010, GRL 37, L18204); product LDEM_16 V3.1, "
                   "LRO-L-LOLA-4-GDR-V1.0, PDS Geosciences Node")
    dy_km = float(lola["dy_m"]) / 1000.0
    gcp_url = DIV_DIR + "/data_derived_gcp/global_cumul_avg_cyl_{00n10n..90s80s}_002.tab (18 files)"
    gcp_credit = ("Diviner team, UCLA (Williams et al. 2017, Icarus 283:300-325); LRO-L-DLRE-5-GCP-V1.0, "
                  "product version 1 (files *_002), PDS Geosciences Node")
    gcp_common = (f"0.5 deg x 0.5 deg x 0.25 h local-time bins, all nadir data 2009-07-05..2015-04-01. Per 0.5 deg "
                  f"bin: -9999 and non-positive values dropped; bins with >= {GCP_MIN_VALID}/96 valid local times "
                  f"and longest gap <= {GCP_MAX_GAP} bins (3 h) are filled by circular linear interpolation in "
                  "local time; then the statistic over the 96 bins; then the cos-lat weighted mean of the "
                  "(up to 4) 0.5 deg bins in the 1 deg cell (count in temp_n_subcells)")
    gcp_cav = ("Bolometric BRIGHTNESS temperature of the surface (radiometric, ~skin), NOT air temperature and "
               "not kinetic temperature. Each local-time bin averages all seasons 2009-2015, so at high latitude "
               "the max/min of this averaged curve are smoother than the extremes of a single lunation; "
               "a 1 deg cell mixes lit and shadowed terrain near the poles.")
    ill_url = ILLUM_TIF.format(p="65S") + " ; " + ILLUM_TIF.format(p="65N") + " (labels: " + ILLUM_LBL.format(p="65S") + ")"
    rows = [
        dict(variable="cell_km", level="DERIVED", product="grid definition", version="", url=URL_MOONFACT,
             licence_credit="NSSDC Moon fact sheet (volumetric mean radius 1737.4 km)", native_resolution="",
             aggregation="", formula="R * 1 deg in radians = 1737.4 km * pi/180 = 30.323 km (north-south)",
             caveats="East-west width = cell_km * cos(lat): 0.26 km in the rows next to the poles."),
        dict(variable="elevation_m", level="MEASURED", product="LOLA LDEM_16 (gridded elevation, 16 px/deg)",
             version="V3.1 (2019-03-15)", url=lola_url, licence_credit=LIC_PDS + lola_credit,
             native_resolution="1/16 deg = 1895.2 m (north-south)",
             aggregation="cos-lat weighted mean of the 16x16 = 256 pixels in each cell",
             formula="height_m = DN * 0.5 (label SCALING_FACTOR), relative to the 1737.4 km sphere; "
                     "longitude 0..360 rolled to -180..180",
             caveats="Height above the 1737.4 km reference sphere, not above a geoid ('sea level' does not exist). "
                     "LDEM_16 is partly interpolated (GMT surface) where tracks are sparse."),
        dict(variable="slope_deg", level="DERIVED", product="from LOLA LDEM_16", version="V3.1", url=lola_url,
             licence_credit=LIC_PDS + lola_credit, native_resolution="1895.2 m pixel",
             aggregation="cos-lat weighted mean of the 256 pixel slopes",
             formula="slope = atan(hypot(dz/dx, dz/dy)); central differences; dy = R*dlat = 1895.2 m; "
                     "dx = dy*cos(lat) (one pixel east-west, true metric spacing, periodic in longitude); "
                     "across the pole the neighbour is the same-latitude pixel at longitude+180",
             caveats=f"Baseline: north-south 2 pixels = {2*dy_km:.2f} km; east-west 2 pixels = {2*dy_km:.2f} km x cos(lat), "
                     "i.e. shorter toward the poles (equal to the Earth definition). A km-scale slope is much "
                     "smaller than a rover-scale (metres) slope. NOT a 300 m slope."),
        dict(variable="slope_p90_deg", level="DERIVED", product="from LOLA LDEM_16", version="V3.1", url=lola_url,
             licence_credit=LIC_PDS + lola_credit, native_resolution="1895.2 m pixel",
             aggregation="90th percentile of the 256 pixel slopes (unweighted)",
             formula="as slope_deg, then numpy.percentile(..., 90)",
             caveats="Same baseline as slope_deg. Within ~2 deg of the poles the literal 1-pixel east-west "
                     "spacing is metres to tens of metres on a ~1.9 km DEM, which inflates the tail: use "
                     "slope_iso_p90_deg there."),
        dict(variable="slope_iso_deg", level="DERIVED", product="from LOLA LDEM_16", version="V3.1", url=lola_url,
             licence_credit=LIC_PDS + lola_credit, native_resolution="1895.2 m pixel",
             aggregation="cos-lat weighted mean of the 256 pixel slopes",
             formula="as slope_deg, but dz/dx = (z(x+s) - z(x-s)) / (2 s dx) with s = max(1, 1/cos(lat)) pixels "
                     "(linear interpolation along the row): east-west baseline = max(2 dx, 2 dy)",
             caveats=f"Baseline {2*dy_km:.2f} km in both directions at every latitude. Equal to slope_deg at the "
                     "equator; differs mainly poleward of ~85 deg. Not part of the common Earth-Moon "
                     "definition: provided because the literal definition is unreliable near the poles."),
        dict(variable="slope_iso_p90_deg", level="DERIVED", product="from LOLA LDEM_16", version="V3.1", url=lola_url,
             licence_credit=LIC_PDS + lola_credit, native_resolution="1895.2 m pixel",
             aggregation="90th percentile of the 256 pixel slopes (unweighted)",
             formula="as slope_iso_deg, then numpy.percentile(..., 90)", caveats="See slope_iso_deg."),
        dict(variable="roughness_m", level="DERIVED", product="from LOLA LDEM_16", version="V3.1", url=lola_url,
             licence_credit=LIC_PDS + lola_credit, native_resolution="1895.2 m pixel",
             aggregation="RMS over all north-south and east-west neighbour pairs whose first pixel is in the cell",
             formula=f"roughness = sqrt(mean((z(x+L) - z(x))^2)), lag L = one DEM pixel = {dy_km:.4f} km "
                     "(deviogram, Rosenburg et al. 2011, JGR 116, E02001). North-south pairs: adjacent rows. "
                     "East-west pairs: same metric lag L, i.e. 1/cos(lat) pixels along the row with linear "
                     "interpolation, so the lag is the same at every latitude.",
             caveats=f"Baseline {dy_km:.3f} km, not 300 m. Interpolation inside the DEM smooths the deviogram."),
        dict(variable="mask_fraction", level="MODELLED", product="definition", version="", url="",
             licence_credit="", native_resolution="cell", aggregation="none",
             formula="1 for every cell (the Moon has no oceans; LDEM_16 has 256/256 valid pixels in every cell)",
             caveats="Set by definition, not measured. The engine gate mask_fraction >= 0.3 passes everywhere."),
        dict(variable="rock_or_bare_frac", level="MODELLED", product="definition (no vegetation)", version="",
             url=URL_MOONFACTS_REGOLITH, licence_credit="NASA Science, Moon facts page",
             native_resolution="cell", aggregation="none",
             formula="1 for every cell: the team's variable means exposed (unvegetated) ground; the Moon has none",
             caveats="NOT rock abundance. Rock abundance is the separate column rock_abundance_frac."),
        dict(variable="rock_abundance_frac", level="MEASURED",
             product="Diviner rock abundance DGDR_RA_AVG_CYL_032 (Bandfield et al. 2011, JGR 116, E00H02)",
             version="V4.0 (calibration 4.0), data 2009-07-05..2010-11-30",
             url=SOURCES["dgdr_ra_avg_cyl_032_img.img"],
             licence_credit=LIC_PDS + "Diviner team (UCLA), Bandfield et al. 2011; LRO-L-DLRE-5-GDR-V1.0",
             native_resolution="1/32 deg (947.6 m)",
             aggregation=f"cos-lat weighted mean of valid pixels; empty if < {int(RA_MIN_VALID_FRAC*100)} % of the 1024 pixels are valid",
             formula="RA = DN * 0.001 + 0 (label); missing DN = -32768",
             caveats="Areal fraction of the surface covered by rocks larger than about 1 m (night-time thermal "
                     "method), 60S-60N only: empty poleward of 60 deg (no data, not zero). Not a bare-ground "
                     "fraction. A newer 128 px/deg version (2016 slope correction, 80S-80N, 1.9 GB) exists and was "
                     "not used here."),
        dict(variable="temp_k", level="DERIVED", product="Diviner Global Cumulative Products (GCP), column tbol",
             version="GCP v1, files *_002 (2016-05-27)", url=gcp_url, licence_credit=LIC_PDS + gcp_credit,
             native_resolution="0.5 deg, 0.25 h local time", aggregation=gcp_common + "; statistic = time mean",
             formula="temp_k = mean over the 96 local-time bins of the diurnal tbol curve, after circular linear "
                     "interpolation of empty bins (gaps of at most 12 bins = 3 h); labelled DERIVED, not MEASURED, "
                     "because of that gap filling", caveats=gcp_cav),
        dict(variable="tmax_k", level="MEASURED", product="Diviner GCP, tbol", version="GCP v1 (*_002)",
             url=gcp_url, licence_credit=LIC_PDS + gcp_credit, native_resolution="0.5 deg, 0.25 h",
             aggregation=gcp_common + "; statistic = max", formula="max over local time of tbol", caveats=gcp_cav),
        dict(variable="tmin_k", level="MEASURED", product="Diviner GCP, tbol", version="GCP v1 (*_002)",
             url=gcp_url, licence_credit=LIC_PDS + gcp_credit, native_resolution="0.5 deg, 0.25 h",
             aggregation=gcp_common + "; statistic = min", formula="min over local time of tbol", caveats=gcp_cav),
        dict(variable="lst_diurnal_amp_k", level="DERIVED", product="Diviner GCP, tbol", version="GCP v1 (*_002)",
             url=gcp_url, licence_credit=LIC_PDS + gcp_credit, native_resolution="0.5 deg, 0.25 h",
             aggregation=gcp_common, formula="tmax_k - tmin_k (cell means of the per-bin max and min)",
             caveats=gcp_cav + " Lunar 'LST' here is a bolometric brightness temperature."),
        dict(variable="tmin_c", level="DERIVED", product="Diviner GCP, tbol", version="GCP v1 (*_002)",
             url=gcp_url, licence_credit=LIC_PDS + gcp_credit, native_resolution="0.5 deg, 0.25 h",
             aggregation=gcp_common, formula="tmin_k - 273.15",
             caveats="SURFACE minimum (pre-dawn), not air temperature (there is no air). " + gcp_cav),
        dict(variable="temp_n_subcells", level="DERIVED", product="Diviner GCP", version="", url=gcp_url,
             licence_credit="", native_resolution="0.5 deg", aggregation="count",
             formula="number of 0.5 deg bins (0-4) that passed the coverage test", caveats="0 means temperatures empty"),
        dict(variable="illum_frac", level="DERIVED (illum_frac_level says how: DERIVED_LOLA_TOPOGRAPHY or DERIVED_FLAT_GEOMETRY)",
             product="LOLA average solar illumination AVGVISIB_65S/65N_240M_201608 (Mazarico et al. 2011, Icarus 211:1066)",
             version="V1.05 (2016-09-15), GeoTIFF conversion 2025-03-20 by PGDA", url=ill_url,
             licence_credit=LIC_PDS + "LOLA team / NASA GSFC PGDA (E. Mazarico); Mazarico et al. 2011",
             native_resolution="240 m polar stereographic (sphere 1737.4 km), 65-90 deg N and S",
             aggregation="mean of all 240 m pixels whose centre falls in the cell (polar-stereographic -> lat/lon "
                         "by the spherical formula rho = 2R tan((90-|lat|)/2)); only rows with |centre lat| >= 65.5",
             formula="DERIVED_LOLA_TOPOGRAPHY: label 'percentage of timesteps where each pixel was sunlit (by any fraction of the "
                     "solar disc)', hourly over ~18.6 yr, computed by the LOLA team by ray tracing over LOLA topography (a simulation from measured topography, not a measurement of light). DERIVED_FLAT_GEOMETRY (|lat| < 65): fraction of time the upper limb of "
                     f"the Sun is above a flat horizon, obliquity {MOON_OBLIQUITY_DEG} deg, semi-diameter "
                     f"{SUN_SEMIDIAMETER_DEG} deg, year-averaged (see sun formula)",
             caveats="Height above ground: the label states none; computed for the surface (0 m). Published "
                     "values at 2 m and 10 m (Glaser et al. 2014) are higher. The DERIVED values ignore "
                     "topographic shadowing (flat ground). A 1 deg cell (~30 km) averages lit ridges with "
                     "shadowed craters: the best sites (~0.9) do not appear at this resolution. At |lat| = 65 "
                     "the value jumps from ~0.50 (flat geometry) to ~0.44 (LOLA topography, with topographic shadowing): "
                     "the jump is the shadowing the flat-ground formula ignores, not an error."),
        dict(variable="irradiance_kwh_m2_day", level="DERIVED",
             product="solar constant (NSSDC Moon fact sheet) + exact geometry; LOLA topographic illum_frac where it exists (|lat| >= 65.5)",
             version="", url=URL_MOONFACT + " ; " + URL_PIA13720,
             licence_credit="NASA NSSDC fact sheet; NASA Photojournal PIA13720",
             native_resolution="cell centre latitude", aggregation="none",
             formula=("Horizontal surface, no atmosphere, Sun-Moon distance 1 au, per 24-hour Earth day. "
                      f"Geometric: Q = S0 * <max(0, sin h)> * 24/1000, S0 = {SOLAR_CONSTANT_W_M2} W/m2, "
                      "sin h = sin(lat) sin(d) + cos(lat) cos(d) cos(H), sin d = sin(eps) sin(L), "
                      "time mean over H and L uniform. Where the LOLA topographic illum_frac exists: Q = S0 * illum_frac * "
                      "<sin h | h > 0> * 24/1000 (the topographic lit fraction replaces the geometric daylight "
                      "fraction; multiplying the geometric Q by illum_frac would count the night twice). "
                      f"Results (cell centres): 0.5 deg (equator) {q(i_eq):.2f}, 45.5 deg {q(i_45):.2f}, 85.5 deg "
                      f"{q(i_85):.3f} kWh/m2/day (geometric); 85.5 deg with the median topographic illum_frac "
                      f"of that row {illum_85:.3f}: "
                      f"{SOLAR_CONSTANT_W_M2*illum_85*sg['mean_sin_day'][i_85]*0.024:.3f} kWh/m2/day "
                      f"(<sin h | h>0> at 85.5 deg = {sg['mean_sin_day'][i_85]:.4f})"),
             caveats="Horizontal panel. A vertical sun-tracking panel at the pole receives ~S0 whenever lit "
                     "(about 32.7 kWh/m2 per 24 h at illum_frac 1); the engine's thresholds were written for "
                     "horizontal Earth irradiance. Lunar day = 29.53 Earth days, so 'per day' is a long-run mean."),
        dict(variable="sun_elev_max_deg", level="DERIVED", product="exact geometry", version="",
             url=URL_PIA13720, licence_credit="NASA Photojournal PIA13720 (obliquity 1.54 deg)",
             native_resolution="cell centre latitude", aggregation="none",
             formula=f"90 - max(0, |lat| - eps), eps = {MOON_OBLIQUITY_DEG} deg (Sun centre, no refraction)",
             caveats="Flat horizon; local topography can raise or block the Sun."),
        dict(variable="sun_low_frac_0_5deg", level="DERIVED", product="exact geometry", version="",
             url=URL_PIA13720, licence_credit="NASA Photojournal PIA13720",
             native_resolution="cell centre latitude", aggregation="none",
             formula="(time with 0 < h < 5 deg) / (time with h > 0), year average; quadrature on 720 seasons x "
                     "2880 hour angles; sin h as for irradiance; Sun centre, no refraction",
             caveats="Equals 1 poleward of ~85 deg (the Sun never exceeds 5 deg)."),
        dict(variable="thermal_inertia_class", level="MODELLED", product="assumption", version="",
             url=URL_MOONFACTS_REGOLITH,
             licence_credit="NASA Science, Moon facts: 'Nearly the entire Moon is covered by ... lunar regolith'",
             native_resolution="global", aggregation="none", formula="'regolito' in every cell",
             caveats="Stated assumption. Rocky exposures (e.g. fresh crater walls, Tycho) exist locally; see "
                     "rock_abundance_frac. Regolith thermal inertia ~55 J m-2 K-1 s-1/2 (Hayne et al. 2017)."),
        dict(variable="permafrost_class", level="MODELLED", product="model label (team lead decision 2026-11-14)",
             version="", url=URL_MOONFACTS_REGOLITH, licence_credit="NASA Science, Moon facts page",
             native_resolution="global", aggregation="none",
             formula=f"'{PERMAFROST_LABEL}' in every cell (label set by definition)",
             caveats="MODELLED label, not a measurement: terrestrial permafrost (ground frozen for two or more "
                     "years, with seasonal thaw of liquid water) does not exist on the Moon, so every cell is "
                     f"labelled '{PERMAFROST_LABEL}' (none). It says nothing about lunar cold traps or buried ice; "
                     "the cold-trap analogue is tmin_k / tmax_k < 110 K, not estimated here."),
        dict(variable="rain_mm_day", level="no data", product="not applicable", version="", url="",
             licence_credit="", native_resolution="", aggregation="", formula="empty",
             caveats="No atmosphere, no precipitation. Empty, not 0 (the engine must treat it as not applicable)."),
        dict(variable="wind_max_ms", level="no data", product="not applicable", version="", url="",
             licence_credit="", native_resolution="", aggregation="", formula="empty",
             caveats="No atmosphere, no wind. Empty, not 0."),
        dict(variable="slope_300m_deg", level="no data", product="none", version="", url="", licence_credit="",
             native_resolution="", aggregation="", formula="not written",
             caveats="No global open product at a 300 m baseline. See column_aliases.json (stand-in: slope_deg)."),
        dict(variable="rough_300m_m", level="no data", product="none", version="", url="", licence_credit="",
             native_resolution="", aggregation="", formula="not written",
             caveats="No global open product at a 300 m baseline. See column_aliases.json (stand-in: roughness_m)."),
    ]
    prov = pd.DataFrame(rows)
    prov.insert(1, "body", "MOON")
    prov = prov[["variable", "body", "level", "product", "version", "url", "licence_credit", "native_resolution",
                 "aggregation", "formula", "caveats"]]
    prov.to_csv(HERE / "provenance_moon.csv", index=False)


def write_aliases(dy_m: float) -> None:
    path = HERE / "column_aliases.json"
    data = json.loads(path.read_text()) if path.exists() else {}
    base = f"{dy_m/1000:.3f} km"
    data["MOON"] = {
        "_note": "Mission variable name -> real column in output_real/moon_real_1deg.csv. Written by real_data/build_moon.py.",
        "slope_300m_deg": {"column": "slope_deg", "true_baseline_km": f"central differences over 2 pixels: {2*dy_m/1000:.2f} km north-south, {2*dy_m/1000:.2f} km x cos(lat) east-west",
                           "caveat": "Not a 300 m slope. km-baseline slopes are much gentler than rover-scale slopes; a 15 deg gate means something different here. slope_p90_deg is the steeper tail. Poleward of ~85 deg the literal 1-pixel east-west spacing shrinks to metres and inflates slope_deg/slope_p90_deg; slope_iso_deg/slope_iso_p90_deg (3.79 km baseline in both directions) are the reliable values there."},
        "rough_300m_m": {"column": "roughness_m", "true_baseline_km": base,
                         "caveat": "RMS height difference at one LOLA pixel (deviogram), not at 300 m. Values grow with baseline (Hurst exponent ~0.5-0.9), so it is larger than a 300 m roughness."},
        "slope_deg": {"column": "slope_deg", "true_baseline_km": f"{2*dy_m/1000:.2f} km", "caveat": "see slope_300m_deg"},
        "roughness_m": {"column": "roughness_m", "true_baseline_km": base, "caveat": "see rough_300m_m"},
        "rock_or_bare_frac": {"column": "rock_or_bare_frac", "true_baseline_km": "cell",
                              "caveat": "1 by definition (no vegetation). Measured rock abundance is rock_abundance_frac (60S-60N)."},
        "temp_k": {"column": "temp_k", "true_baseline_km": "0.5 deg bins averaged to 1 deg",
                   "caveat": "Diurnal mean surface bolometric brightness temperature, not air temperature."},
        "lst_diurnal_amp_k": {"column": "lst_diurnal_amp_k", "true_baseline_km": "0.5 deg", "caveat": "tmax_k - tmin_k of the season-averaged diurnal curve."},
        "tmin_c": {"column": "tmin_c", "true_baseline_km": "0.5 deg", "caveat": "Surface minimum, not air."},
        "irradiance_kwh_m2_day": {"column": "irradiance_kwh_m2_day", "true_baseline_km": "cell centre latitude",
                                  "caveat": "Horizontal surface, per 24 h, DERIVED; uses the LOLA topographic illum_frac (Mazarico 2011 simulation) at |lat| >= 65.5."},
        "sun_elev_max_deg": {"column": "sun_elev_max_deg", "true_baseline_km": "cell centre latitude", "caveat": "Exact geometry, flat horizon."},
        "sun_low_frac_0_5deg": {"column": "sun_low_frac_0_5deg", "true_baseline_km": "cell centre latitude", "caveat": "Exact geometry, flat horizon."},
        "mask_fraction": {"column": "mask_fraction", "true_baseline_km": "cell", "caveat": "1 by definition."},
        "elevation_m": {"column": "elevation_m", "true_baseline_km": "cell mean of 1.9 km pixels", "caveat": "Relative to the 1737.4 km sphere."},
        "thermal_inertia_class": {"column": "thermal_inertia_class", "true_baseline_km": "global", "caveat": "'regolito' everywhere, MODELLED assumption."},
        "permafrost_class": {"column": "permafrost_class", "true_baseline_km": "global",
                             "caveat": f"'{PERMAFROST_LABEL}' on every cell: a MODELLED label set by definition (no terrestrial-type permafrost on the Moon), not a measurement."},
        "rain_mm_day": {"column": "rain_mm_day", "true_baseline_km": "", "caveat": "Empty: not applicable (no atmosphere)."},
        "wind_max_ms": {"column": "wind_max_ms", "true_baseline_km": "", "caveat": "Empty: not applicable (no atmosphere)."},
    }
    path.write_text(json.dumps(data, indent=1, ensure_ascii=False))


# ---------------------------------------------------------------------------
# Self-checks
# ---------------------------------------------------------------------------
def run_checks(df, lola, gcp, rock, ill, sg, ldem4) -> dict:
    out = {}
    # 1. Elevation vs the committed 2-degree table (block mean of LDEM_4).
    ref_path = REPO_DIR / "output_py" / "moon_lola_diviner_clean.csv"
    if ref_path.exists():
        ref = pd.read_csv(ref_path, usecols=["lat_deg", "lon_deg", "elevation_m"])
        e1 = lola["elevation_m"]
        w = np.cos(np.radians(ROW_LAT))[:, None] * np.ones((1, NCOLS))
        e2 = (e1 * w).reshape(90, 2, 180, 2).sum(axis=(1, 3)) / w.reshape(90, 2, 180, 2).sum(axis=(1, 3))
        lat2 = 89.0 - 2.0 * np.arange(90)
        lon2 = -179.0 + 2.0 * np.arange(180)
        mine = pd.DataFrame({"lat_deg": np.repeat(lat2, 180), "lon_deg": np.tile(lon2, 90), "mine": e2.ravel()})
        m = ref.merge(mine, on=["lat_deg", "lon_deg"], how="inner")
        d = m.mine - m.elevation_m
        out["elevation_vs_committed_2deg"] = {
            "matched_cells": int(len(m)), "ref_cells": int(len(ref)),
            "mean_diff_m": float(d.mean()), "median_abs_diff_m": float(d.abs().median()),
            "p99_abs_diff_m": float(d.abs().quantile(0.99)), "max_abs_diff_m": float(d.abs().max()),
            "corr": float(np.corrcoef(m.mine, m.elevation_m)[0, 1]),
            "max_abs_diff_m_excluding_rows_at_|lat|=89": float(d[np.abs(m.lat_deg) < 89].abs().max()),
        }
        # Explain the residual: rebuild the committed table from LDEM_4 with and without area weights.
        img4, lbl4 = ldem4
        l4, s4 = int(lbl4["LINES"]), int(lbl4["LINE_SAMPLES"])
        z4 = np.roll(np.fromfile(img4, dtype="<i2").reshape(l4, s4) * float(lbl4["SCALING_FACTOR"]), -s4 // 2, axis=1)
        k4 = l4 // 90
        unw = z4.reshape(90, k4, 180, k4).mean(axis=(1, 3))
        lat4 = 90.0 - (np.arange(l4) + 0.5) / (l4 / 180.0)
        wtd = area_weighted_block_mean(z4, lat4, k4)
        refg = ref.sort_values(["lat_deg", "lon_deg"], ascending=[False, True]).elevation_m.values.reshape(90, 180)
        out["elevation_committed_table_explained"] = {
            "LDEM_4_version": lbl4.get("PRODUCT_VERSION_ID"),
            "committed_minus_unweighted_LDEM4_2deg_max_abs_m": float(np.abs(refg - unw).max()),
            "committed_minus_weighted_LDEM4_2deg_max_abs_m": float(np.abs(refg - wtd).max()),
            "this_table_minus_weighted_LDEM4_2deg_median_abs_m": float(np.median(np.abs(e2 - wtd))),
            "this_table_minus_weighted_LDEM4_2deg_max_abs_m": float(np.abs(e2 - wtd).max()),
            "reading": ("The committed table is an UNWEIGHTED block mean of LDEM_4. Toward the poles an unweighted "
                        "mean over-counts the small high-latitude pixels of each 2-degree cell, hence differences "
                        "of 100-1100 m poleward of ~73 deg (largest at -89). Below 80 deg the median difference "
                        "is ~9 m. Area-weighted, LDEM_4 (V3.0) and this LDEM_16 (V3.1) table agree to a "
                        "median of ~8 m."),
        }
    # 2. Temperatures vs the latitude profile in R2 (Diviner GCP sample, 8 strips per band).
    r2 = {  # band: (median max, median min, median amplitude)
        "0-10N": (391.8, 94.4, 297.7), "0-10S": (391.3, 94.6, 297.0), "20-30N": (379.4, 92.3, 286.5),
        "40-50N": (353.8, 87.6, 265.7), "60-70N": (307.3, 79.3, 228.1), "70-80N": (275.8, 71.5, 204.2),
        "70-80S": (275.4, 71.7, 204.1), "80-90N": (222.4, 55.4, 164.8), "80-90S": (229.3, 51.4, 175.7),
    }
    prof = {}
    for band, (rmax, rmin, ramp) in r2.items():
        lo, hi = [float(x) for x in band[:-1].split("-")]
        sign = 1 if band.endswith("N") else -1
        rows = np.nonzero((np.abs(ROW_LAT) > lo) & (np.abs(ROW_LAT) < hi) & (np.sign(ROW_LAT) == sign))[0]
        mx = np.nanmedian(gcp["tmax"][rows]); mn = np.nanmedian(gcp["tmin"][rows])
        amp = np.nanmedian((gcp["tmax"] - gcp["tmin"])[rows])
        prof[band] = {"this_max": round(float(mx), 1), "R2_max": rmax, "this_min": round(float(mn), 1), "R2_min": rmin,
                      "this_amp": round(float(amp), 1), "R2_amp": ramp}
    out["temperature_vs_R2_profile"] = prof
    # Published equatorial range: NSSDC fact sheet 95-390 K; Williams 2017 via Diviner team ~387-397 K, ~95 K.
    eq = np.abs(df.lat_deg) < 5
    out["equator_published_check"] = {"median_tmax_k_|lat|<5": float(df.tmax_k[eq].median()),
                                      "median_tmin_k_|lat|<5": float(df.tmin_k[eq].median()),
                                      "published": "95 K to 390 K (NSSDC Moon fact sheet); ~387-397 K noon, ~95 K pre-dawn (Williams et al. 2017)"}
    # 3. Ranges and empties.
    rng = {}
    for c in df.columns:
        if df[c].dtype.kind in "fi":
            rng[c] = {"min": float(df[c].min()) if df[c].notna().any() else None,
                      "max": float(df[c].max()) if df[c].notna().any() else None,
                      "empty": int(df[c].isna().sum())}
        else:
            rng[c] = {"values": sorted(map(str, df[c].dropna().unique()))[:8], "empty": int(df[c].isna().sum())}
    out["ranges"] = rng
    out["gcp_nonpositive_tbol_values_dropped"] = int(gcp["n_nonpos"])
    out["gcp_labels_with_swapped_min_max_latitude"] = list(gcp["label_lat_swapped"])
    out["gcp_halfdeg_bins_too_few_valid"] = int(np.sum(gcp["half_nvalid"] < GCP_MIN_VALID))
    out["gcp_halfdeg_bins_gap_too_long"] = int(np.sum((gcp["half_nvalid"] >= GCP_MIN_VALID) & (gcp["half_maxgap"] > GCP_MAX_GAP)))
    out["rock_raw_pixel_max"] = float(rock["raw_max"])
    out["illum_info"] = json.loads(str(ill["info"]))
    out["slope_literal_vs_isotropic_by_lat"] = {
        f"{lo}-{hi}": {"literal": round(float(np.nanmedian(lola["slope_deg"][(np.abs(ROW_LAT) >= lo) & (np.abs(ROW_LAT) < hi)])), 3),
                       "isotropic": round(float(np.nanmedian(lola["slope_iso_deg"][(np.abs(ROW_LAT) >= lo) & (np.abs(ROW_LAT) < hi)])), 3)}
        for lo, hi in [(0, 30), (30, 60), (60, 80), (80, 85), (85, 88), (88, 89), (89, 90)]}
    s = {}
    for lat in (0.5, 45.5, 60.5, 80.5, 85.5, 88.5, 89.5):
        i = int(np.argmin(np.abs(ROW_LAT - lat)))
        s[str(lat)] = {k: round(float(sg[k][i]), 5) for k in ("sun_elev_max_deg", "day_frac", "disc_frac", "low_frac", "mean_sin_pos", "mean_sin_day")}
        s[str(lat)]["irr_geo_kwh"] = round(float(SOLAR_CONSTANT_W_M2 * sg["mean_sin_pos"][i] * 0.024), 4)
    out["sun_geometry_samples"] = s
    out["summary"] = {
        "rows": int(len(df)), "elevation": out.get("elevation_vs_committed_2deg"),
        "empty_counts": {c: v["empty"] for c, v in rng.items() if v["empty"]},
        "temperature_profile": prof,
    }
    return out


if __name__ == "__main__":
    sys.exit(main())
