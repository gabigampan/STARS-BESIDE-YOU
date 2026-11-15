"""LOLA polar stereographic DEM access (PDS3 IMG, int16 LSB, DN * 0.5 m above the 1737.4 km sphere).

Only the rows that are needed are fetched, by HTTP range requests, and cached on disk.
Projection (PDS DSMAP_POLAR, south pole, CENTER_LONGITUDE = 0, sphere R = 1737.4 km):
    rho = 2 R tan(pi/4 + lat/2)          (lat negative in the south)
    x = rho sin(lon),  y = rho cos(lon)
    sample (0-based) = SAMPLE_PROJECTION_OFFSET + x / MAP_SCALE
    line   (0-based) = LINE_PROJECTION_OFFSET   + y / MAP_SCALE
The sign of the line term is not assumed: verify_orientation() tests both signs against the
global LDEM_16 grid and the scenario stores the one that matches.
"""
import os, re, subprocess, hashlib
import numpy as np

R_MOON = 1737400.0


def parse_label(text):
    def g(key):
        m = re.search(r"^\s*" + key + r"\s*=\s*([^\n<]+)", text, re.M)
        return m.group(1).strip().strip('"') if m else None
    return dict(lines=int(g("LINES")), samples=int(g("LINE_SAMPLES")), scale_m=float(g("MAP_SCALE")),
                line_off=float(g("LINE_PROJECTION_OFFSET")), sample_off=float(g("SAMPLE_PROJECTION_OFFSET")),
                scaling=float(g("SCALING_FACTOR")), sample_type=g("SAMPLE_TYPE"), sample_bits=int(g("SAMPLE_BITS")),
                center_lat=float(g("CENTER_LATITUDE")), max_lat=float(g("MAXIMUM_LATITUDE")),
                product_version=g("PRODUCT_VERSION_ID"), file_name=g("FILE_NAME"))


def curl(url, out, rng=None):
    cmd = ["curl", "-sS", "--fail", "--retry", "4", "-o", out]
    if rng:
        cmd += ["-r", rng]
    subprocess.run(cmd + [url], check=True)


def get_label(url, cache):
    p = os.path.join(cache, os.path.basename(url))
    if not os.path.exists(p):
        curl(url, p)
    return parse_label(open(p, encoding="latin-1").read()), p


def fetch_rows(url, lab, l0, l1, cache):
    """Rows l0..l1 inclusive (0-based) as float32 metres above 1737.4 km."""
    assert lab["sample_type"] == "LSB_INTEGER" and lab["sample_bits"] == 16
    rb = lab["samples"] * 2
    l0 = max(0, l0); l1 = min(lab["lines"] - 1, l1)
    p = os.path.join(cache, "%s_rows_%d_%d.raw" % (os.path.basename(url), l0, l1))
    if not os.path.exists(p) or os.path.getsize(p) != (l1 - l0 + 1) * rb:
        curl(url, p + ".part", "%d-%d" % (l0 * rb, (l1 + 1) * rb - 1))
        os.replace(p + ".part", p)
    a = np.fromfile(p, dtype="<i2").reshape(l1 - l0 + 1, lab["samples"]).astype(np.float32)
    return l0, a * lab["scaling"], p


def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def ps_forward(lat, lon):
    lat = np.radians(lat); lon = np.radians(lon)
    rho = 2 * R_MOON * np.tan(np.pi / 4 + lat / 2)
    return rho * np.sin(lon), rho * np.cos(lon)


def ps_inverse(x, y):
    rho = np.hypot(x, y)
    lat = 2 * np.arctan(rho / (2 * R_MOON)) - np.pi / 2
    lon = np.arctan2(x, y)
    return np.degrees(lat), np.degrees(lon)


def ps_scale_factor(lat):
    """Point scale factor of the polar stereographic projection true at the pole: map = k * ground."""
    return 2.0 / (1.0 + np.sin(np.radians(abs(lat))))


def to_pixel(lab, x, y, line_sign):
    return lab["sample_off"] + x / lab["scale_m"], lab["line_off"] + line_sign * y / lab["scale_m"]


def ldem16_cell_mean(ldem16_path, lat_c, lon_c):
    """cos-lat weighted mean of the 16x16 LDEM_16 pixels of the 1-degree cell centred at lat_c, lon_c."""
    a = np.memmap(ldem16_path, dtype="<i2", mode="r", shape=(2880, 5760))
    i0 = int(round((90 - (lat_c + 0.5)) * 16)); j0 = int(round(((lon_c - 0.5) % 360) * 16))
    blk = a[i0:i0 + 16, j0:j0 + 16].astype(np.float64) * 0.5
    lats = 90 - (np.arange(i0, i0 + 16) + 0.5) / 16
    w = np.cos(np.radians(lats))[:, None] * np.ones((1, 16))
    return float((blk * w).sum() / w.sum()), blk


def ldem16_sample(ldem16_path, lat, lon):
    a = np.memmap(ldem16_path, dtype="<i2", mode="r", shape=(2880, 5760))
    i = np.clip(((90 - lat) * 16 - 0.5).round().astype(int), 0, 2879)
    j = (((lon % 360) * 16 - 0.5).round().astype(int)) % 5760
    return a[i, j].astype(np.float64) * 0.5
