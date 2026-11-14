import hashlib
import os
import re
from typing import Dict

import numpy as np
import requests
from scipy.ndimage import map_coordinates, zoom

MOON_RADIUS_M = 1737400.0
CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "cache")
TIMEOUT_S = 180


def _is_url(p: str) -> bool:
    return p.lower().startswith(("http://", "https://"))


def _swap_ext(p: str, ext: str) -> str:
    return os.path.splitext(p)[0] + ext


def _read_text(p: str) -> str:
    if _is_url(p):
        os.makedirs(CACHE_DIR, exist_ok=True)
        cache = os.path.join(CACHE_DIR, os.path.basename(p))
        if not os.path.exists(cache):
            r = requests.get(p, timeout=TIMEOUT_S)
            r.raise_for_status()
            open(cache, "wb").write(r.content)
        p = cache
    return open(p, "r", errors="ignore").read()


def parse_pds3_label(text: str, name: str = "") -> Dict[str, float]:
    def grab(key, default=None):
        m = re.search(rf"^\s*{key}\s*=\s*\"?([-+0-9.eE]+)", text, re.M)
        return float(m.group(1)) if m else default

    if "LSB_INTEGER" not in text or int(grab("SAMPLE_BITS", 16)) != 16:
        raise ValueError(f"{name}: only 16-bit LSB_INTEGER PDS3 images are supported")
    return {
        "lines": int(grab("LINES")),
        "samples": int(grab("LINE_SAMPLES")),
        "scale": grab("SCALING_FACTOR", 1.0),
        "offset": grab("OFFSET", 0.0),
        "missing": grab("MISSING_CONSTANT", -32768.0),
        "ppd": grab("MAP_RESOLUTION"),
        "lat_max": grab("MAXIMUM_LATITUDE", 90.0),
        "lat_min": grab("MINIMUM_LATITUDE", -90.0),
    }


def _read_rows(img: str, r0: int, r1: int, samples: int, lines: int) -> np.ndarray:
    row_bytes = samples * 2
    if not _is_url(img):
        mm = np.memmap(img, dtype="<i2", mode="r", shape=(lines, samples))
        return np.asarray(mm[r0:r1, :])

    os.makedirs(CACHE_DIR, exist_ok=True)
    full_local = os.path.join(CACHE_DIR, os.path.basename(img))
    if os.path.exists(full_local) and os.path.getsize(full_local) == lines * row_bytes:
        mm = np.memmap(full_local, dtype="<i2", mode="r", shape=(lines, samples))
        return np.asarray(mm[r0:r1, :])

    tag = hashlib.md5(img.encode()).hexdigest()[:8]
    cache = os.path.join(CACHE_DIR, f"{os.path.basename(img)}.{tag}.rows_{r0}_{r1}.bin")
    if not os.path.exists(cache):
        print(
            f"[PDS] Downloading rows {r0}-{r1} of {os.path.basename(img)} "
            f"({(r1 - r0) * row_bytes / 1e6:.1f} MB)..."
        )
        hdr = {"Range": f"bytes={r0 * row_bytes}-{r1 * row_bytes - 1}"}
        r = requests.get(img, headers=hdr, timeout=TIMEOUT_S)
        if r.status_code != 206 or len(r.content) != (r1 - r0) * row_bytes:
            raise IOError(f"Unexpected HTTP response ({r.status_code}, {len(r.content)} bytes)")
        open(cache + ".part", "wb").write(r.content)
        os.replace(cache + ".part", cache)
    return np.fromfile(cache, dtype="<i2").reshape(r1 - r0, samples)


def read_pds_global(
    path: str,
    shape: tuple,
    use_offset: bool = False,
) -> np.ndarray:
    lbl = path if path.lower().endswith(".lbl") else _swap_ext(path, ".lbl")
    img = path if path.lower().endswith(".img") else _swap_ext(path, ".img")
    if not _is_url(lbl) and not os.path.exists(lbl):
        lbl = _swap_ext(path, ".LBL")
    info = parse_pds3_label(_read_text(lbl), os.path.basename(lbl))

    raw = _read_rows(img, 0, info["lines"], info["samples"], info["lines"]).astype(np.float32)
    valid = raw != info["missing"]
    scaled = np.where(
        valid,
        raw * info["scale"] + (info["offset"] if use_offset else 0.0),
        np.nan,
    ).astype(np.float32)

    scaled = np.roll(scaled, shift=info["samples"] // 2, axis=1)

    h, w = shape
    zy = h / scaled.shape[0]
    zx = w / scaled.shape[1]
    if np.isnan(scaled).any():
        med = float(np.nanmedian(scaled))
        filled = np.where(np.isfinite(scaled), scaled, med)
        out = zoom(filled, (zy, zx), order=1).astype(np.float32)
    else:
        out = zoom(scaled, (zy, zx), order=1).astype(np.float32)
    return out


def read_pds_window(
    path: str,
    center_lat: float,
    center_lon: float,
    shape: tuple,
    res_m: float,
    use_offset: bool = False,
) -> np.ndarray:
    lbl = path if path.lower().endswith(".lbl") else _swap_ext(path, ".lbl")
    img = path if path.lower().endswith(".img") else _swap_ext(path, ".img")
    if not _is_url(lbl) and not os.path.exists(lbl):
        lbl = _swap_ext(path, ".LBL")
    info = parse_pds3_label(_read_text(lbl), os.path.basename(lbl))

    h, w = shape
    ppd = info["ppd"]
    y_m = ((h / 2.0 - 0.5) - np.arange(h)) * res_m
    x_m = (np.arange(w) - w / 2.0 + 0.5) * res_m
    deg_per_m = 180.0 / (np.pi * MOON_RADIUS_M)
    lat = center_lat + y_m * deg_per_m
    if lat.max() > info["lat_max"] or lat.min() < info["lat_min"]:
        raise ValueError(
            f"{os.path.basename(img)} covers {info['lat_min']}..{info['lat_max']} deg latitude; "
            f"requested window ({lat.min():.2f}..{lat.max():.2f} deg) is out of bounds."
        )
    coslat = np.cos(np.radians(lat))[:, None]
    lon = (center_lon + x_m[None, :] * deg_per_m / coslat) % 360.0

    rows = (info["lat_max"] - np.broadcast_to(lat[:, None], (h, w))) * ppd - 0.5
    cols = lon * ppd - 0.5

    r0 = max(int(np.floor(rows.min())) - 1, 0)
    r1 = min(int(np.ceil(rows.max())) + 2, info["lines"])
    ref = cols[h // 2, w // 2]
    n = info["samples"]
    cols_u = ((cols - ref + n / 2) % n) - n / 2 + ref
    c0 = int(np.floor(cols_u.min())) - 1
    c1 = int(np.ceil(cols_u.max())) + 2
    col_idx = np.arange(c0, c1) % n

    block = _read_rows(img, r0, r1, n, info["lines"])
    sub = block[:, col_idx].astype(np.float32)
    valid = (sub != info["missing"]).astype(np.float32)
    sub = np.where(valid > 0, sub * info["scale"] + (info["offset"] if use_offset else 0.0), 0.0)

    coords = [rows - r0, cols_u - c0]
    val = map_coordinates(sub, coords, order=1, mode="nearest")
    wgt = map_coordinates(valid, coords, order=1, mode="nearest")
    return np.where(wgt > 0.999, val, np.nan).astype(np.float32)
