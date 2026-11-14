"""Independent re-computation of Moon cells from raw downloads (does not import the builders)."""
import glob, math, os, sys, zipfile
import numpy as np, pandas as pd, rasterio
from pyproj import Transformer, CRS

M = "/tmp/claude-0/-home-user-NASA/7228bb30-9725-52d9-8d71-762c955fd0bd/scratchpad/stars/realdata/moon"
G = "/tmp/claude-0/-home-user-NASA/7228bb30-9725-52d9-8d71-762c955fd0bd/scratchpad/stars/realdata/verify_gcp"
TAB = sys.argv[1] if len(sys.argv) > 1 else "/home/user/stars-beside-you/tierra luna/output_real/moon_real_1deg.csv"
R = 1737400.0
df = pd.read_csv(TAB, keep_default_na=False, na_values=[""])

# gazetteer straight from the zip (own reader)
import geopandas as gpd
zpath = M + "/MOON_nomenclature_center_pts.zip"
shp = [n for n in zipfile.ZipFile(zpath).namelist() if n.endswith(".shp")][0]
gz = gpd.read_file(f"zip://{zpath}!{shp}")
want = ["Tycho", "Copernicus", "Mons Huygens", "Shackleton", "Aristarchus", "Plato", "Tsiolkovskiy", "Mons Hadley",
        "Statio Tranquillitatis", "Korolev", "Hertzsprung", "Mons Pico", "Cabeus", "Peary", "Hermite", "Mons Malapert",
        "Apollo", "Orientale"]
cells = []
for nm in want:
    h = gz[gz["clean_name"] == nm]
    if h.empty:
        h = gz[gz["clean_name"].str.contains(nm, regex=False)]
    if h.empty:
        print("not in gazetteer", nm); continue
    h = h.iloc[0]
    lat, lon = float(h.center_lat), float(h.center_lon)
    lon = (lon + 180) % 360 - 180
    cells.append((nm, int(math.floor(90 - lat)), int(math.floor(lon + 180)) % 360, lat, lon, float(h.diameter)))
rng = np.random.default_rng(1969)
for b0 in range(-90, 90, 10):
    rr = rng.integers(90 - b0 - 10, 90 - b0, size=2)
    for r in rr:
        cells.append((f"rand{b0}", int(r), int(rng.integers(0, 360)), np.nan, np.nan, np.nan))

# LDEM_16
dn = np.fromfile(M + "/ldem_16.img", dtype="<i2").reshape(2880, 5760)
Z = dn * 0.5
ppd = 16
def lola_block(r, c, halo):
    """north-up block for the cell with a halo; columns in 0..360 east from the product."""
    lon_w = -180 + c
    j0 = int(round(((lon_w % 360)) * ppd)) - halo
    i0 = r * ppd - halo
    rows = np.arange(i0, i0 + ppd + 2 * halo)
    cols = np.arange(j0, j0 + ppd + 2 * halo) % 5760
    out = np.empty((rows.size, cols.size))
    for k, i in enumerate(rows):
        if i < 0:       # across the north pole
            out[k] = Z[-i - 1, (cols + 2880) % 5760]
        elif i >= 2880:
            out[k] = Z[2 * 2880 - i - 1, (cols + 2880) % 5760]
        else:
            out[k] = Z[i, cols]
    lat = 90 - (rows + 0.5) / ppd
    return out, lat, rows

rock = np.fromfile(M + "/dgdr_ra_avg_cyl_032_img.img", dtype="<i2").reshape(3840, 11520)
ill = {p: rasterio.open(f"{M}/AVGVISIB_{p}_240M_201608.TIF") for p in ("65S", "65N")}

def sun_analytic(lat, eps, n=200000):
    """Year means by the closed-form day length per declination (independent of the builders' 2-D quadrature)."""
    L = (np.arange(n) + 0.5) * 2 * np.pi / n
    d = np.arcsin(np.sin(np.radians(eps)) * np.sin(L))
    phi = np.radians(lat)
    def H(alt):
        x = (np.sin(np.radians(alt)) - np.sin(phi) * np.sin(d)) / (np.cos(phi) * np.cos(d))
        return np.arccos(np.clip(x, -1, 1))       # half-day arc above altitude alt
    H0, H5 = H(0.0), H(5.0)
    # mean of max(0, sin h) over a day = (H0 sinphi sind + cosphi cosd sinH0)/pi
    msp = (H0 * np.sin(phi) * np.sin(d) + np.cos(phi) * np.cos(d) * np.sin(H0)) / np.pi
    return {"low": (H0 - H5).sum() / H0.sum() if H0.sum() else np.nan, "day": (H0 / np.pi).mean(), "msp": msp.mean(),
            "msd": msp.sum() / (H0 / np.pi).sum() if H0.sum() else np.nan,
            "disc": (H(-0.2666) / np.pi).mean(), "elmax": 90 - max(0, abs(lat) - eps)}

# GCP bands downloaded again for this check
gcp = {}
for f in sorted(glob.glob(G + "/*.tab")):
    t = pd.read_csv(f, header=None, skiprows=1, skipinitialspace=True, usecols=[0, 1, 2, 10], names=["clon", "clat", "ltim", "tbol"])
    gcp[os.path.basename(f)] = t
def gcp_cell(lat_c, lon_c):
    rows = []
    for name, t in gcp.items():
        s = t[(t.clat > lat_c - 0.5) & (t.clat < lat_c + 0.5) & (t.clon > lon_c - 0.5) & (t.clon < lon_c + 0.5)]
        if len(s): rows.append(s)
    if not rows: return None
    s = pd.concat(rows)
    s = s[s.tbol > 0]
    res = {"mean": [], "max": [], "min": [], "w": [], "raw_mean": []}
    for (la, lo), g in s.groupby(["clat", "clon"]):
        g = g.sort_values("ltim")
        lt = (np.rint((g.ltim.values - 0.125) / 0.25) + 0.5) * 0.25; tb = g.tbol.values
        if len(lt) < 40: continue
        gaps = np.diff(np.r_[lt, lt[0] + 24])
        if round(gaps.max() / 0.25) - 1 > 12: continue
        x = (np.arange(96) + 0.5) * 0.25
        full = np.interp(x, lt, tb, period=24)
        res["mean"].append(full.mean()); res["max"].append(full.max()); res["min"].append(full.min())
        res["raw_mean"].append(tb.mean()); res["w"].append(math.cos(math.radians(la)))
    if not res["w"]: return None
    w = np.array(res["w"])
    return {k: float((np.array(v) * w).sum() / w.sum()) for k, v in res.items() if k != "w"} | {"nsub": len(w)}

out = []
for nm, r, c, flat, flon, diam in cells:
    lat_c, lon_c = 89.5 - r, -179.5 + c
    rec = {"name": nm, "row": r, "col": c, "lat": lat_c, "lon": lon_c, "feat_lat": flat, "feat_lon": flon, "diam": diam}
    z, lat, rows = lola_block(r, c, 1)
    w = np.cos(np.radians(lat))[:, None] * np.ones((1, z.shape[1]))
    zc, wc = z[1:-1, 1:-1], w[1:-1, 1:-1]
    rec["elevation_m"] = (zc * wc).sum() / wc.sum()
    rec["elevation_unweighted"] = zc.mean()
    dy = R * math.radians(1 / ppd)
    dx = dy * np.cos(np.radians(lat[1:-1]))[:, None]
    dzdx = (z[1:-1, 2:] - z[1:-1, :-2]) / (2 * dx)
    dzdy = (z[:-2, 1:-1] - z[2:, 1:-1]) / (2 * dy)
    s = np.degrees(np.arctan(np.hypot(dzdx, dzdy)))
    rec["slope_deg"] = (s * wc).sum() / wc.sum(); rec["slope_p90_deg"] = np.percentile(s, 90)
    # roughness, isotropic metric lag dy: E-W at 1/cos(lat) pixels by linear interpolation along the full row
    sq = []
    for k in range(1, 1 + ppd):
        i = rows[k]
        row = Z[i]; j0 = int(round((lon_c - 0.5) % 360 * ppd))
        js = (np.arange(j0, j0 + ppd)) % 5760
        lag = 1 / math.cos(math.radians(lat[k]))
        xs = js + lag
        x0 = np.floor(xs).astype(int); f = xs - x0
        zz = row[x0 % 5760] * (1 - f) + row[(x0 + 1) % 5760] * f
        sq.append((zz - row[js]) ** 2)
        if i + 1 < 2880:
            sq.append((Z[i + 1, js] - row[js]) ** 2)
    sq = np.concatenate(sq)
    rec["roughness_m"] = math.sqrt(sq.mean())
    dE = (z[1:-1, 2:] - zc).ravel(); dS = (z[2:, 1:-1] - zc).ravel()
    rec["roughness_1px"] = math.sqrt(np.concatenate([dE, dS]) ** 2 .mean()) if False else math.sqrt((np.concatenate([dE, dS]) ** 2).mean())
    # rock abundance (60S-60N)
    if abs(lat_c) < 60:
        i0 = int(round((60 - (lat_c + 0.5)) * 32)); j0 = int(round(((lon_c - 0.5) % 360) * 32))
        blk = rock[i0:i0 + 32, j0:j0 + 32].astype(float)
        valid = blk != -32768
        latp = (lat_c + 0.5) - (np.arange(32) + 0.5) / 32
        ww = np.cos(np.radians(latp))[:, None] * np.ones((1, 32))
        if valid.mean() >= 0.5:
            rec["rock_abundance_frac"] = (blk * 0.001 * ww)[valid].sum() / ww[valid].sum()
    # illumination via pyproj with the files' own CRS: sample a fine lat/lon lattice, take unique pixels
    if abs(lat_c) >= 65.5:
        src = ill["65S" if lat_c < 0 else "65N"]
        tr = Transformer.from_crs(CRS.from_proj4(f"+proj=longlat +R={R} +no_defs"), src.crs, always_xy=True)
        la, lo = np.meshgrid(np.linspace(lat_c - 0.5 + 0.0005, lat_c + 0.5 - 0.0005, 400), np.linspace(lon_c - 0.5 + 0.0005, lon_c + 0.5 - 0.0005, 400))
        x, y = tr.transform(lo.ravel(), la.ravel())
        rr_, cc_ = rasterio.transform.rowcol(src.transform, x, y)
        pix = np.unique(np.c_[rr_, cc_], axis=0)
        a = src.read(1)
        v = a[pix[:, 0], pix[:, 1]].astype(float)
        v = v[v != src.nodata] * 4e-5
        rec["illum_frac"] = v.mean()
    sa = sun_analytic(lat_c, 1.54)
    rec["sun_elev_max_deg"] = sa["elmax"]; rec["sun_low_frac_0_5deg"] = sa["low"]
    illum_used = rec.get("illum_frac", sa["disc"])
    rec["irradiance_kwh_m2_day"] = (1361 * illum_used * sa["msd"] * 24 / 1000) if "illum_frac" in rec else 1361 * sa["msp"] * 24 / 1000
    g = gcp_cell(lat_c, lon_c) if gcp else None
    if g:
        rec["temp_k"], rec["tmax_k"], rec["tmin_k"], rec["temp_raw_mean"], rec["nsub"] = g["mean"], g["max"], g["min"], g["raw_mean"], g["nsub"]
        rec["lst_diurnal_amp_k"] = g["max"] - g["min"]
    out.append(rec)
    print(nm, r, c, flush=True)
pd.DataFrame(out).to_csv("/tmp/claude-0/-home-user-NASA/7228bb30-9725-52d9-8d71-762c955fd0bd/scratchpad/verify/moon_mine.csv", index=False)
