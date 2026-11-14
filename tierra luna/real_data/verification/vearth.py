"""Independent re-computation of Earth cells from raw downloads (does not import the builders)."""
import glob, json, math, sys, zipfile
import numpy as np, pandas as pd, rasterio, netCDF4
from rasterio.windows import from_bounds, Window
from pyproj import Transformer

RAW = "/tmp/claude-0/-home-user-NASA/7228bb30-9725-52d9-8d71-762c955fd0bd/scratchpad/stars/realdata/earth_raw"
TAB = sys.argv[1] if len(sys.argv) > 1 else "/home/user/stars-beside-you/tierra luna/output_real/earth_real_1deg.csv"
CM = json.load(open("/home/user/stars-beside-you/tierra luna/real_data/class_mappings.json"))["EARTH"]["thermal_inertia_class_from_esa_cci_lccs"]["classes"]
R = 6371.0088e3
df = pd.read_csv(TAB, keep_default_na=False, na_values=[""])

named = {"Everest": (27.9881, 86.925), "Sahara": (25.3, 10.6), "Atacama Yungay": (-24.08, -69.92), "Tibet": (33.8, 86.6),
         "Death Valley": (36.25, -116.83), "Dome C": (-75.1, 123.33), "Manaus": (-3.1, -60.0), "Iceland": (64.7, -18.2),
         "Tabernas": (37.05, -2.4), "Haughton": (75.4, -89.8), "Mauna Kea": (19.82, -155.47), "Hanksville": (38.37, -110.71),
         "Yakutsk": (62.03, 129.73), "Longyearbyen": (78.22, 15.65), "Mont Blanc": (45.83, 6.865), "Kilimanjaro": (-3.07, 37.35),
         "Aconcagua": (-32.65, -70.01), "Dead Sea": (31.5, 35.5), "Amazon west": (-5.5, -70.5), "Dry Valleys": (-77.5, 162.5)}
cells = []
for nm, (la, lo) in named.items():
    r, c = int(math.floor(90 - la)), int(math.floor(lo + 180))
    cells.append((nm, r, c))
rng = np.random.default_rng(20261114)
land = df[(df.mask_fraction >= 0.5)]
for b0 in range(-90, 90, 15):
    sub = land[(land.lat_deg >= b0) & (land.lat_deg < b0 + 15)]
    if len(sub) == 0:
        continue
    for i in rng.choice(len(sub), size=min(3, len(sub)), replace=False):
        x = sub.iloc[i]
        cells.append((f"rand{b0}", int(x.row), int(x.col)))
cells.append(("ocean", 89, 29))

# ---- CCI mosaic reader
tiles = []
for p in sorted(glob.glob(RAW + "/cci/*.tif")):
    with rasterio.open(p) as s:
        tiles.append((p, s.bounds))
def read_cci(w, s_, e, n):
    res = 1 / 360
    H, W = int(round((n - s_) / res)), int(round((e - w) / res))
    out = np.zeros((H, W), np.uint8)
    for p, b in tiles:
        # handle wrap by shifting longitudes
        for shift in (-360, 0, 360):
            bw, be = b.left + shift, b.right + shift
            ww, ee, ss, nn = max(w, bw), min(e, be), max(s_, b.bottom), min(n, b.top)
            if ww >= ee or ss >= nn:
                continue
            with rasterio.open(p) as src:
                c0 = int(round((ww - bw) / res)); c1 = int(round((ee - bw) / res))
                r0 = int(round((b.top - nn) / res)); r1 = int(round((b.top - ss) / res))
                a = src.read(1, window=Window(c0, r0, c1 - c0, r1 - r0))
            oc = int(round((ww - w) / res)); orr = int(round((n - nn) / res))
            out[orr:orr + a.shape[0], oc:oc + a.shape[1]] = a
    return out

etopo = netCDF4.Dataset(RAW + "/etopo/ETOPO_2022_v1_60s_N90W180_surface.nc")
Z = etopo.variables["z"]
def read_etopo(r, c, hx=1):
    """north-up block with a one-pixel halo in latitude and hx pixels in longitude for cell (r, c)."""
    lat_s = 90 - r - 1
    i0 = int(round((lat_s + 90) * 60)) - 1          # netCDF row of the southern halo
    j0 = c * 60 - hx
    rows = np.arange(i0, i0 + 62)
    cols = np.arange(j0, j0 + 60 + 2 * hx) % 21600
    blk = np.full((62, cols.size), np.nan)
    okr = (rows >= 0) & (rows < 10800)
    sub = np.ma.filled(Z[rows[okr].min():rows[okr].max() + 1, :].astype(float), np.nan)[:, cols]
    blk[okr] = sub
    return blk[::-1]  # north-up

day = rasterio.open(RAW + "/lst/clm_lst_mod11a2.annual.day_m.tif")
night = rasterio.open(RAW + "/lst/clm_lst_mod11a2.annual.night_m.tif")
def wc(var):
    return [rasterio.open(f"zip://{RAW}/worldclim/wc2.1_10m_{var}.zip!wc2.1_10m_{var}_{m:02d}.tif") for m in range(1, 13)]
WC = {v: wc(v) for v in ("tmin", "prec", "wind", "srad")}
DAYS = np.array([31, 28.25, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31])

pf_src = {}
for name, epsg in (("UiO_PEX_PERPROB_5.0_20181128_2000_2016_NH", 3995), ("UiO_PEX_PERPROB_5.0_20181205_2000_2017_ANT", 3031)):
    pf_src[epsg] = rasterio.open(f"zip://{RAW}/permafrost/{name}.zip!{name}.tif")
def permafrost(r, c):
    lat_n, lon_w = 90 - r, -180 + c
    vals = []
    for epsg, src in pf_src.items():
        if (epsg == 3995 and lat_n < 20) or (epsg == 3031 and lat_n > -50):
            continue
        fwd = Transformer.from_crs(4326, epsg, always_xy=True); inv = Transformer.from_crs(epsg, 4326, always_xy=True)
        la, lo = np.meshgrid(np.linspace(lat_n - 1, lat_n, 41), np.linspace(lon_w, lon_w + 1, 41))
        x, y = fwd.transform(lo.ravel(), la.ravel())
        win = from_bounds(min(x) - 2000, min(y) - 2000, max(x) + 2000, max(y) + 2000, src.transform).round_offsets().round_lengths()
        a = src.read(1, window=win, boundless=True, fill_value=-9)
        t = src.window_transform(win)
        jj, ii = np.meshgrid(np.arange(a.shape[1]), np.arange(a.shape[0]))
        xs, ys = t.c + t.a * (jj + 0.5), t.f + t.e * (ii + 0.5)
        plo, pla = inv.transform(xs.ravel(), ys.ravel())
        plo, pla = np.asarray(plo), np.asarray(pla)
        inside = (pla >= lat_n - 1) & (pla < lat_n) & (plo >= lon_w) & (plo < lon_w + 1)
        v = a.ravel()[inside]
        vals.append(v[(v >= 0) & (v <= 1)])
    v = np.concatenate(vals) if vals else np.array([])
    return (float(v.mean()) if v.size else np.nan), v.size

def pfclass(f):
    if not np.isfinite(f): return ""
    return "continuo" if f >= 0.9 else "discontinuo" if f >= 0.5 else "esporadico" if f >= 0.01 else "ninguno"

def window_mean(src, r, c, fn):
    lat_n, lon_w = 90 - r, -180 + c
    win = from_bounds(lon_w, lat_n - 1, lon_w + 1, lat_n, src.transform).round_offsets().round_lengths()
    return src.read(1, window=win, boundless=True, fill_value=src.nodata if src.nodata is not None else 0)

out = []
for nm, r, c in cells:
    lat_c, lon_c = 89.5 - r, -179.5 + c
    rec = {"name": nm, "row": r, "col": c, "lat": lat_c, "lon": lon_c}
    # CCI with a 6-pixel (1 arc-min) halo
    h = 1 / 60
    poleward = abs(lat_c) + 0.5 + h
    hx = int(min(10740, math.ceil(1 / max(math.cos(math.radians(min(poleward, 89.9999))), 1e-9)) + 2))
    cci = read_cci(lon_c - 0.5 - hx * h, lat_c - 0.5 - h, lon_c + 0.5 + hx * h, lat_c + 0.5 + h)
    core = cci[6:-6, 6 * hx:-6 * hx]
    nod = (core == 0).sum(); water = (core == 210).sum(); landpx = core.size - nod - water
    rec["mask_fraction"] = landpx / (core.size - nod) if core.size - nod else np.nan
    if landpx:
        rec["rock_or_bare_frac"] = np.isin(core, [150, 151, 152, 153, 200, 201, 202]).sum() / landpx
    cats = {}
    for code, n in zip(*np.unique(core[core > 0], return_counts=True)):
        cat = CM[str(int(code))]["category"]; cats[cat] = cats.get(cat, 0) + n
    order = ["roca", "regolito", "arena", "suelo", "hielo", "agua"]
    rec["thermal_inertia_class"] = max(order, key=lambda k: (cats.get(k, 0), -order.index(k))) if cats else ""
    land60w = ((cci != 210) & (cci != 0)).reshape(62, 6, 60 + 2 * hx, 6).sum(axis=(1, 3)) >= 18
    zw = read_etopo(r, c, hx)
    Lw = land60w & np.isfinite(zw)
    z, L = zw[:, hx - 1:hx + 61], Lw[:, hx - 1:hx + 61]
    lat_px = lat_c + 0.5 + h - (np.arange(62) + 0.5) * h
    w = np.cos(np.radians(lat_px))[:, None] * np.ones((1, 62))
    zc, Lc, wc_ = z[1:-1, 1:-1], L[1:-1, 1:-1], w[1:-1, 1:-1]
    if Lc.any():
        rec["elevation_m"] = zc[Lc].mean()
        rec["elevation_m_coslat"] = (zc[Lc] * wc_[Lc]).sum() / wc_[Lc].sum()
        dy = R * math.radians(h); dx = dy * np.cos(np.radians(lat_px))[1:-1, None]
        dzdx = (z[1:-1, 2:] - z[1:-1, :-2]) / (2 * dx)
        dzdy = (z[:-2, 1:-1] - z[2:, 1:-1]) / (2 * dy)
        ok = Lc & L[1:-1, 2:] & L[1:-1, :-2] & L[:-2, 1:-1] & L[2:, 1:-1]
        s = np.degrees(np.arctan(np.hypot(dzdx, dzdy)))[ok]
        if s.size:
            rec["slope_deg"] = s.mean(); rec["slope_p90_deg"] = np.percentile(s, 90)
            rec["slope_deg_coslat"] = (s * wc_[ok]).sum() / wc_[ok].sum()
        dE = (z[1:-1, 2:] - zc)[Lc & L[1:-1, 2:]]
        dS = (z[2:, 1:-1] - zc)[Lc & L[2:, 1:-1]]
        d = np.concatenate([dE, dS])
        rec["roughness_m"] = math.sqrt((d ** 2).mean()) if d.size else np.nan
        rec["roughness_ns_only"] = math.sqrt((dS ** 2).mean()) if dS.size else np.nan
        # isotropic: E-W pair at metric lag dy, i.e. 1/cos(lat) pixels, linear interpolation
        sqs, sis, wis = [d_ ** 2 for d_ in [dS]], [], []
        for k in range(60):
            la = lat_px[k + 1]; lag = 1 / math.cos(math.radians(la)); s_ = max(1.0, lag)
            jj = np.arange(hx, hx + 60).astype(float)
            def at(x):
                x0 = np.floor(x).astype(int); f = x - x0
                v = zw[k + 1, x0] * (1 - f) + zw[k + 1, x0 + 1] * f
                ok = Lw[k + 1, x0] & (Lw[k + 1, x0 + 1] | (f == 0))
                return v, ok
            ctr = zw[k + 1, hx:hx + 60]; lc = Lw[k + 1, hx:hx + 60]
            v, ok = at(jj + lag)
            sqs.append(((v - ctr) ** 2)[lc & ok])
            vp, okp = at(jj + s_); vm, okm = at(jj - s_)
            gx = (vp - vm) / (2 * s_ * dy * math.cos(math.radians(la)))
            gy = (zw[k, hx:hx + 60] - zw[k + 2, hx:hx + 60]) / (2 * dy)
            okk = lc & okp & okm & Lw[k, hx:hx + 60] & Lw[k + 2, hx:hx + 60]
            sis.append(np.degrees(np.arctan(np.hypot(gx, gy)))[okk]); wis.append(np.full(okk.sum(), math.cos(math.radians(la))))
        q = np.concatenate(sqs); rec["roughness_iso"] = math.sqrt(q.mean()) if q.size else np.nan
        si = np.concatenate(sis); wi = np.concatenate(wis)
        if si.size:
            rec["slope_iso_deg"] = (si * wi).sum() / wi.sum(); rec["slope_iso_p90_deg"] = np.percentile(si, 90)
    # LST
    dd = window_mean(day, r, c, None).astype(float); nn = window_mean(night, r, c, None).astype(float)
    okl = (dd > 0) & (nn > 0) & (dd != day.nodata) & (nn != night.nodata)
    if okl.any():
        rec["temp_k"] = (0.5 * (dd + nn) * 0.02)[okl].mean(); rec["lst_diurnal_amp_k"] = ((dd - nn) * 0.02)[okl].mean()
    # WorldClim
    st = {}
    for v, srcs in WC.items():
        arr = []
        for s_ in srcs:
            a = window_mean(s_, r, c, None).astype(float)
            a[(a == s_.nodata) | (np.abs(a) > 1e30)] = np.nan
            arr.append(a)
        st[v] = np.stack(arr)
    if np.isfinite(st["tmin"]).any():
        rec["tmin_c"] = np.nanmean(np.min(st["tmin"], axis=0))
        rec["rain_mm_day"] = np.nanmean(np.sum(st["prec"], axis=0) / 365.25)
        rec["wind_max_ms"] = np.nanmean(np.max(st["wind"], axis=0))
        rec["irradiance_kwh_m2_day"] = np.nanmean(np.sum(st["srad"] * DAYS[:, None, None], axis=0) / 365.25 / 3600)
    if abs(lat_c) > 17:
        f, n = permafrost(r, c)
        rec["permafrost_area_frac"] = f; rec["permafrost_class"] = pfclass(f); rec["n_pf"] = n
    out.append(rec)
    print(nm, r, c, flush=True)
mine = pd.DataFrame(out)
mine.to_csv("/tmp/claude-0/-home-user-NASA/7228bb30-9725-52d9-8d71-762c955fd0bd/scratchpad/verify/earth_mine2.csv", index=False)
