"""r1: terrain candidates computed with the SAME definition on Earth (ETOPO 2022 60s) and Moon (LOLA LDEM_16).

Per 1-degree cell (cell_id = row*360 + col, row 0 = 89.5 N, col 0 = -179.5 E):
  steep_frac_{5,10,15}: area-weighted share of the cell's DEM pixels whose isotropic slope
      (same pixel slope as slope_iso_deg: baseline ~3.7 km Earth / ~3.8 km Moon) exceeds 5/10/15 deg
  rough2_m: RMS height difference at a metric lag of TWO DEM pixels (Earth 3.71 km, Moon 3.79 km),
      both directions, east-west at 2/cos(lat) pixels (linear interpolation), as roughness_m at one pixel
  hurst_h: log2(rough2_m / roughness_m) -- deviogram scaling exponent between the two lags
  check columns slope_iso_chk, rough1_chk: re-computation of the table's slope_iso_deg / roughness_m
Reads only the raw files already on disk; deterministic; writes research/out/r1_dem_<body>.npz.
"""
import math, sys, os
import numpy as np

RAWD = "/tmp/claude-0/-home-user-NASA/7228bb30-9725-52d9-8d71-762c955fd0bd/scratchpad/stars/realdata"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")
NR, NC = 180, 360
TH = (5.0, 10.0, 15.0)


def interp_row(zrow, lag):
    W = zrow.size
    xs = np.arange(W, dtype=np.float64)
    xq = xs + lag
    x0 = np.floor(xq); f = xq - x0
    i0 = x0.astype(np.int64) % W; i1 = (i0 + 1) % W
    return zrow[i0] * (1 - f) + zrow[i1] * f, i0, i1, f


def earth():
    import netCDF4
    R = 6371.0088
    land60 = np.load(RAWD + "/earth_cache/land60.npy", mmap_mode="r")
    ds = netCDF4.Dataset(RAWD + "/earth_raw/etopo/ETOPO_2022_v1_60s_N90W180_surface.nc")
    zv = ds.variables["z"]
    W = 21600
    dlam = math.radians(1 / 60); dy = R * dlam * 1000.0
    res = {k: np.full(NR * NC, np.nan) for k in ("steep_frac_5", "steep_frac_10", "steep_frac_15",
                                                 "rough2_m", "slope_iso_chk", "rough1_chk")}

    def rows(i0, i1):
        out = np.full((i1 - i0, W), np.nan); a, b = max(i0, 0), min(i1, 10800)
        blk = np.ma.filled(zv[10799 - (b - 1):10799 - a + 1, :].astype(np.float64), np.nan)[::-1]
        out[a - i0:b - i0] = blk
        L = np.zeros((i1 - i0, W), bool); L[a - i0:b - i0] = land60[a:b] >= 18
        return out, L

    pc = lambda a: a.reshape(a.shape[0], NC, 60).transpose(1, 0, 2).reshape(NC, -1)
    for r in range(NR):
        i0 = r * 60
        z, L = rows(i0 - 2, i0 + 62)          # two halo rows each side (lag-2 pairs)
        lat = 90.0 - (np.arange(i0 - 2, i0 + 62) + 0.5) / 60.0
        cl = np.cos(np.radians(lat)); dx = R * cl * dlam * 1000.0
        c = slice(2, 62)
        dzdy = (z[1:-3] - z[3:-1]) / (2 * dy)                # rows 2..61 centred
        okns = L[c] & L[1:-3] & L[3:-1]
        sl = np.full((60, W), np.nan); dE1 = np.full((60, W), np.nan); dE2 = np.full((60, W), np.nan)
        for k in range(60):
            kk = k + 2; zr, lr = z[kk], L[kk]
            s = max(1.0, 1.0 / cl[kk])
            zp, a0, a1, f = interp_row(zr, s); okp = lr[a0] & (lr[a1] | (f == 0))
            zm, b0, b1, g = interp_row(zr, -s); okm = lr[b0] & (lr[b1] | (g == 0))
            dzdx = (zp - zm) / (2 * s * dx[kk])
            ok = okns[k] & okp & okm & np.isfinite(dzdy[k])
            sl[k] = np.where(ok, np.degrees(np.arctan(np.hypot(dzdx, dzdy[k]))), np.nan)
            for lagpx, arr in ((1.0, dE1), (2.0, dE2)):
                zl, c0, c1, h = interp_row(zr, lagpx / cl[kk]); okl = lr[c0] & (lr[c1] | (h == 0))
                arr[k] = np.where(lr & okl, zl - zr, np.nan)
        w = pc(np.repeat(cl[c][:, None], W, 1))
        S = pc(sl); okS = np.isfinite(S)
        den = np.where(okS, w, 0).sum(1)
        cells = slice(r * NC, (r + 1) * NC)
        with np.errstate(invalid="ignore", divide="ignore"):
            res["slope_iso_chk"][cells] = np.where(den > 0, np.where(okS, S * w, 0).sum(1) / den, np.nan)
            for t in TH:
                res[f"steep_frac_{int(t)}"][cells] = np.where(den > 0, np.where(okS & (S > t), w, 0).sum(1) / den, np.nan)
            dS1 = np.where(L[c] & L[3:-1], z[3:-1] - z[c], np.nan)
            dS2 = np.where(L[c] & L[4:], z[4:] - z[c], np.nan)
            for name, e_, s_ in (("rough1_chk", dE1, dS1), ("rough2_m", dE2, dS2)):
                sq = np.concatenate([pc(e_), pc(s_)], 1) ** 2
                n = np.isfinite(sq).sum(1)
                res[name][cells] = np.where(n > 0, np.sqrt(np.nansum(sq, 1) / np.maximum(n, 1)), np.nan)
        if r % 30 == 0:
            print("earth row", r, flush=True)
    np.savez_compressed(OUT + "/r1_dem_earth.npz", **res)


def moon():
    R = 1737400.0
    lbl = open(RAWD + "/moon/ldem_16.lbl").read()
    sc = float([l for l in lbl.splitlines() if "SCALING_FACTOR" in l][0].split("=")[1].split("<")[0])
    lines, samples, ppd = 2880, 5760, 16
    z = np.fromfile(RAWD + "/moon/ldem_16.img", dtype="<i2").reshape(lines, samples).astype(np.float64) * sc
    z = np.roll(z, -samples // 2, axis=1)
    lat = 90.0 - (np.arange(lines) + 0.5) / ppd
    dy = R * math.radians(1 / ppd); cl = np.cos(np.radians(lat)); dx = dy * cl
    half = samples // 2
    z_n = np.vstack([np.roll(z[0:1], half, 1), z[:-1]]); z_s = np.vstack([z[1:], np.roll(z[-1:], half, 1)])
    dzdy = (z_n - z_s) / (2 * dy)
    xs = np.arange(samples, dtype=np.float64); sl = np.empty_like(z)
    ew1 = np.empty_like(z); ew2 = np.empty_like(z)
    for i in range(lines):
        zi = z[i]; xp, fp = np.r_[xs, samples], np.r_[zi, zi[0]]
        lag = max(1.0, 1.0 / cl[i])
        dzdx = (np.interp(xs + lag, xp, fp, period=samples) - np.interp(xs - lag, xp, fp, period=samples)) / (2 * lag * dx[i])
        sl[i] = np.degrees(np.arctan(np.hypot(dzdx, dzdy[i])))
        ew1[i] = (np.interp(xs + 1.0 / cl[i], xp, fp, period=samples) - zi) ** 2
        ew2[i] = (np.interp(xs + 2.0 / cl[i], xp, fp, period=samples) - zi) ** 2
    ns1 = (z_s - z) ** 2; ns1[-1] = np.nan
    ns2 = np.full_like(z, np.nan); ns2[:-2] = (z[2:] - z[:-2]) ** 2
    k = ppd
    blk = lambda a: a.reshape(NR, k, NC, k)
    w = np.repeat(cl[:, None], samples, 1)
    wsum = blk(w).sum((1, 3))
    res = {"slope_iso_chk": (blk(sl * w).sum((1, 3)) / wsum).ravel()}
    for t in TH:
        res[f"steep_frac_{int(t)}"] = (blk(np.where(sl > t, w, 0)).sum((1, 3)) / wsum).ravel()
    for name, e_, s_ in (("rough1_chk", ew1, ns1), ("rough2_m", ew2, ns2)):
        num = np.nansum(blk(e_), (1, 3)) + np.nansum(blk(s_), (1, 3))
        n = np.isfinite(blk(e_)).sum((1, 3)) + np.isfinite(blk(s_)).sum((1, 3))
        res[name] = np.sqrt(num / n).ravel()
    np.savez_compressed(OUT + "/r1_dem_moon.npz", **res)


if __name__ == "__main__":
    {"earth": earth, "moon": moon}[sys.argv[1]]()
