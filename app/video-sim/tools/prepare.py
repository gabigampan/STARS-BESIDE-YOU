"""Prepare the terrain and the checks for one scenario.

usage: python3 -I tools/prepare.py scenarios/solar.json --work <work_dir>

1. Reads the two 1-degree tables and checks every value copied into the scenario's
   table_values against the row with that cell_id (and that the id matches the coordinates).
2. Fetches only the needed rows of the two LOLA polar DEM products (HTTP range requests).
3. Verifies the georeferencing: the cell mean of the polar product over the 1-degree cell is
   compared with the table's elevation_m and with the global LDEM_16 grid.
4. Resamples the DEM onto a local east/north grid centred on the site, at the product's true
   ground spacing at that latitude (no upsampling), with the Moon's curvature applied.
5. Computes horizon angles (terrain + curvature) on the grids, for N azimuths, and a fine horizon
   profile at the object's location; the page uses them for hard terrain shadows and for the
   'Sun blocked by terrain' test.
6. Writes a shaded-relief PNG rendered directly from the elevation patch (for the visual check).
"""
import sys, os, json, csv, math, argparse, time
from multiprocessing import Pool
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dem as D

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TABLES = os.path.join(HERE, "..", "..", "tierra luna", "output_real")
LDEM16_DEFAULT = "/tmp/claude-0/-home-user-NASA/7228bb30-9725-52d9-8d71-762c955fd0bd/scratchpad/stars/realdata/moon/ldem_16.img"
R = D.R_MOON


def read_row(path, cell_id):
    with open(path, newline="") as f:
        for r in csv.DictReader(f):
            if r["cell_id"] == cell_id:
                return r
    raise SystemExit("cell %s not in %s" % (cell_id, path))


def check_tables(sc):
    out = []
    for body, key, fname in (("moon", "site", "moon_real_1deg.csv"), ("earth", "earth_site", "earth_real_1deg.csv")):
        s = sc[key]
        row = read_row(os.path.join(TABLES, fname), s["cell_id"])
        if abs(float(row["lat_deg"]) - s["lat_deg"]) > 1e-6 or abs(float(row["lon_deg"]) - s["lon_deg"]) > 1e-6:
            raise SystemExit("cell id %s does not match coordinates %s,%s" % (s["cell_id"], s["lat_deg"], s["lon_deg"]))
        for var, v in sc["table_values"][body].items():
            tv = row[var]
            ok = (str(v["value"]) == tv) if isinstance(v["value"], str) else (tv != "" and abs(float(tv) - float(v["value"])) < 1e-9)
            out.append(dict(body=body, cell=s["cell_id"], var=var, scenario=v["value"], table=tv, ok=ok))
            if not ok:
                raise SystemExit("MISMATCH %s %s: scenario %s table %s" % (s["cell_id"], var, v["value"], tv))
    return out


def dest(lat, lon, e, n):
    """local east/north metres (azimuthal equidistant about the site) -> lat, lon (deg)."""
    p = math.radians(lat)
    A = np.arctan2(e, n); th = np.hypot(e, n) / R
    la = np.arcsin(np.sin(p) * np.cos(th) + np.cos(p) * np.sin(th) * np.cos(A))
    lo = math.radians(lon) + np.arctan2(np.sin(A) * np.sin(th) * np.cos(p), np.cos(th) - np.sin(p) * np.sin(la))
    return np.degrees(la), (np.degrees(lo) + 180) % 360 - 180


def bilinear(a, r, c):
    r0 = np.floor(r).astype(np.int64); c0 = np.floor(c).astype(np.int64)
    fr = r - r0; fc = c - c0
    r0 = np.clip(r0, 0, a.shape[0] - 2); c0 = np.clip(c0, 0, a.shape[1] - 2)
    return (a[r0, c0] * (1 - fr) * (1 - fc) + a[r0 + 1, c0] * fr * (1 - fc)
            + a[r0, c0 + 1] * (1 - fr) * fc + a[r0 + 1, c0 + 1] * fr * fc)


def sample_product(spec, lab, lat, lon, line_sign, cache):
    x, y = D.ps_forward(lat, lon)
    s, l = D.to_pixel(lab, x, y, line_sign)
    l0, a, raw = D.fetch_rows(spec["url"], lab, int(np.floor(l.min())) - 2, int(np.ceil(l.max())) + 2, cache)
    assert s.min() >= 0 and s.max() < lab["samples"] - 1, "patch leaves the product"
    return bilinear(a, l - l0, s), raw, (l0, l0 + a.shape[0] - 1)


def build_grid(sc, spec, lab, half, step_m, h0, cache):
    n = int(round(half / step_m))
    ax = np.arange(-n, n + 1) * step_m
    E, N = np.meshgrid(ax, ax)                       # row index = north, col = east
    la, lo = dest(sc["site"]["lat_deg"], sc["site"]["lon_deg"], E, N)
    h, raw, rows = sample_product(spec, lab, la, lo, sc["dem"]["line_sign"], cache)
    th = np.hypot(E, N) / R
    base = h0 if h0 is not None else float(h[n, n])
    z = (R + h) * np.cos(th) - (R + base)               # height in the site's tangent frame, curvature applied
    return dict(ax=ax, step=step_m, n=2 * n + 1, h=h, z=z.astype(np.float32), raw=raw, rows=rows, h0=base, la=la, lo=lo)


# ---------------------------------------------------------------- horizons
G = {}


def _init(grids):
    G.update(grids)


def zsample(e, n):
    """height (site frame) at local coords from the finest grid that contains the point; nan outside."""
    out = np.full(e.shape, np.nan, dtype=np.float64)
    for g in (G["far"], G["near"]):   # near overrides far
        h = g["half"]; st = g["step"]
        inside = (np.abs(e) < h - st) & (np.abs(n) < h - st)
        if inside.any():
            c = (e[inside] + h) / st; r = (n[inside] + h) / st
            out[inside] = bilinear(g["z"], r, c)
    return out


def horizon_for_az(args):
    az, pe, pn, pz, dmin = args
    s, c = math.sin(math.radians(az)), math.cos(math.radians(az))
    best = np.full(pe.shape, -90.0)
    d = dmin
    fine = G["near"]["step"]; dmax = G["far"]["half"] * 1.45
    while d < dmax:
        zq = zsample(pe + d * s, pn + d * c)
        ang = np.degrees(np.arctan2(zq - pz, d))
        ok = ~np.isnan(ang)
        best[ok] = np.maximum(best[ok], ang[ok])
        d += max(fine * 0.9, 0.025 * d) if d < G["near"]["half"] * 1.5 else max(G["far"]["step"] * 0.9, 0.025 * d)
    return best


def horizon_map(points_e, points_n, points_z, n_az, dmin, pool):
    azs = [i * 360.0 / n_az for i in range(n_az)]
    res = pool.map(horizon_for_az, [(a, points_e, points_n, points_z, dmin) for a in azs])
    return np.stack(res).astype(np.float32), azs


def hillshade(z, step, az_deg, el_deg):
    gy, gx = np.gradient(z.astype(np.float64), step)       # rows = north
    nx, ny, nz = -gx, -gy, np.ones_like(z, dtype=np.float64)
    norm = np.sqrt(nx * nx + ny * ny + 1)
    a, e = math.radians(az_deg), math.radians(el_deg)
    sx, sy, sz = math.sin(a) * math.cos(e), math.cos(a) * math.cos(e), math.sin(e)
    return np.clip((nx * sx + ny * sy + nz * sz) / norm, 0, 1)


def save_png(arr01, path):
    from PIL import Image
    img = (np.clip(arr01, 0, 1) * 255).astype(np.uint8)[::-1]   # north up
    Image.fromarray(img).save(path)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("scenario")
    ap.add_argument("--work", default=os.path.join(HERE, "build"))
    ap.add_argument("--ldem16", default=LDEM16_DEFAULT)
    a = ap.parse_args()
    sc = json.load(open(a.scenario))
    work = os.path.join(a.work, sc["name"]); cache = os.path.join(a.work, "cache")
    os.makedirs(work, exist_ok=True); os.makedirs(cache, exist_ok=True)
    t0 = time.time()
    checks = {"tables": check_tables(sc)}
    print("table values: %d checked, all equal" % len(checks["tables"]))

    lat, lon = sc["site"]["lat_deg"], sc["site"]["lon_deg"]
    k = float(D.ps_scale_factor(lat))
    specs = sc["dem"]
    labs = {}
    for key in ("near", "far"):
        labs[key], lp = D.get_label(specs[key]["label"], cache)
    near_step = labs["near"]["scale_m"] / k
    far_native = labs["far"]["scale_m"] / k
    print("true ground spacing at %.2f: near %.2f m/px, far %.2f m/px (k=%.5f)" % (lat, near_step, far_native, k))

    near = build_grid(sc, specs["near"], labs["near"], specs["near"]["half_extent_m"], near_step, None, cache)
    h0 = near["h0"]
    farN = build_grid(sc, specs["far"], labs["far"], specs["far"]["half_extent_m"], far_native, h0, cache)
    print("grids: near %d^2 far(native) %d^2  h0=%.1f m  %.0fs" % (near["n"], farN["n"], h0, time.time() - t0))

    # ---- georeference checks
    cl = lat + (np.arange(64) + 0.5) / 64 - 0.5
    co = lon + (np.arange(64) + 0.5) / 64 - 0.5
    CL, CO = np.meshgrid(cl, co, indexing="ij")
    hc, _, _ = sample_product(specs["far"], labs["far"], CL, CO, specs["line_sign"], cache)
    w = np.cos(np.radians(CL))
    cell_mean_far = float((hc * w).sum() / w.sum())
    l16, _ = D.ldem16_cell_mean(a.ldem16, lat, lon)
    tab = sc["table_values"]["moon"]["elevation_m"]["value"]
    # near vs far over the near patch (same points)
    nf = bilinear(farN["z"], (near["ax"][None, :] * 0 + near["ax"][:, None] + farN["ax"][-1]) / far_native,
                  (near["ax"][None, :] + farN["ax"][-1]) / far_native)
    d_nf = near["z"] - nf
    pts = dest(lat, lon, np.array([0.0]), np.array([0.0]))
    checks["georef"] = dict(
        site_ps_xy_m=[float(v) for v in D.ps_forward(lat, lon)],
        near_rows_fetched=near["rows"], far_rows_fetched=farN["rows"],
        true_m_per_px_near=near_step, true_m_per_px_far=far_native, ps_scale_factor=k,
        site_height_m=h0,
        cell_mean_far_product_m=cell_mean_far, cell_mean_ldem16_recomputed_m=l16, table_elevation_m=tab,
        diff_far_vs_table_m=cell_mean_far - tab, diff_ldem16_vs_table_m=l16 - tab,
        near_minus_far_over_near_patch_m=dict(mean=float(d_nf.mean()), rms=float(np.sqrt((d_nf ** 2).mean())), p99=float(np.percentile(np.abs(d_nf), 99))),
        centre_back_to_latlon=[float(pts[0][0]), float(pts[1][0])],
        near_relief_m=[float(near["h"].min()), float(near["h"].max())], far_relief_m=[float(farN["h"].min()), float(farN["h"].max())],
    )
    print(json.dumps(checks["georef"], indent=1))
    if abs(cell_mean_far - tab) > 150:
        raise SystemExit("georeference check failed: polar product cell mean differs from the table by > 150 m")

    # ---- render far grid (decimated, never upsampled)
    st = specs["far"]["render_step_px"]
    far = dict(z=farN["z"][::st, ::st].copy(), ax=farN["ax"][::st], step=far_native * st)
    far["n"] = far["z"].shape[0]
    grids = {"near": dict(z=near["z"].astype(np.float64), half=float(near["ax"][-1]), step=near_step),
             "far": dict(z=farN["z"].astype(np.float64), half=float(farN["ax"][-1]), step=far_native)}
    n_az = specs["horizon_azimuths"]
    with Pool(4, initializer=_init, initargs=(grids,)) as pool:
        _init(grids)
        E, N = np.meshgrid(near["ax"], near["ax"])
        hz_near, azs = horizon_map(E.ravel(), N.ravel(), near["z"].ravel().astype(np.float64) + 0.05, n_az, near_step * 0.7, pool)
        print("near horizons %.0fs" % (time.time() - t0))
        E2, N2 = np.meshgrid(far["ax"], far["ax"])
        hz_far, _ = horizon_map(E2.ravel(), N2.ravel(), far["z"].ravel().astype(np.float64) + 0.05, n_az, far["step"] * 0.7, pool)
        print("far horizons %.0fs" % (time.time() - t0))
        # object horizon profile (fine azimuths) at the object point and height above ground
        obj_h = sc.get("array", {}).get("hub_height_m", 2.0) if "array" in sc else 2.0
        oz = float(near["z"][near["n"] // 2, near["n"] // 2]) + obj_h
        n_obj = 720
        res = pool.map(horizon_for_az, [(i * 360.0 / n_obj, np.array([0.0]), np.array([0.0]), np.array([oz]), 1.0) for i in range(n_obj)])
        obj_hz = [float(r[0]) for r in res]
        # ground point (0.05 m) too
        res = pool.map(horizon_for_az, [(i * 360.0 / n_obj, np.array([0.0]), np.array([0.0]), np.array([oz - obj_h + 0.05]), 1.0) for i in range(n_obj)])
        gnd_hz = [float(r[0]) for r in res]
    print("object horizon %.0fs" % (time.time() - t0))

    # ---- Earth decision
    ev = sc.get("earth_visibility", {})
    earth = dict(draw=False)
    if ev.get("draw") == "auto":
        az = ev["az_mean_deg"]; i = az / 0.5
        i0 = int(math.floor(i)) % n_obj; i1 = (i0 + 1) % n_obj; f = i - math.floor(i)
        hz = obj_hz[i0] * (1 - f) + obj_hz[i1] * f
        earth = dict(draw=bool(ev["elev_mean_deg"] - 0.95 > hz), az_deg=az, elev_deg=ev["elev_mean_deg"], terrain_horizon_deg=hz,
                     note="Earth angular radius 0.95 deg; drawn only if the whole disc clears the real horizon at the mean position")
    elif ev:
        i = int(round(ev.get("az_mean_deg", (ev["az_min_deg"] + ev["az_max_deg"]) / 2) / 0.5)) % n_obj
        earth = dict(draw=False, terrain_horizon_at_earth_az_deg=obj_hz[i], elev_mean_deg=ev["elev_mean_deg"])
    checks["earth"] = earth
    print("earth:", earth)

    # ---- shaded relief (direct from the patch, sun from the north-west at 25 deg, north up)
    save_png(hillshade(near["z"], near_step, 315, 25), os.path.join(work, "hillshade_near.png"))
    save_png(hillshade(far["z"], far["step"], 315, 25), os.path.join(work, "hillshade_far.png"))

    # ---- write assets
    near["z"].astype("<f4").tofile(os.path.join(work, "near_z.f32"))
    far["z"].astype("<f4").tofile(os.path.join(work, "far_z.f32"))
    np.round(hz_near * 100).astype("<i2").tofile(os.path.join(work, "near_hz.i16"))
    np.round(hz_far * 100).astype("<i2").tofile(os.path.join(work, "far_hz.i16"))
    meta = dict(name=sc["name"], near=dict(n=near["n"], step=near_step, half=float(near["ax"][-1]), product=specs["near"]["product"], url=specs["near"]["url"], sha256_rows=D.sha256(near["raw"])),
                far=dict(n=far["n"], step=far["step"], half=float(far["ax"][-1]), native_step=far_native, product=specs["far"]["product"], url=specs["far"]["url"], sha256_rows=D.sha256(farN["raw"])),
                n_az=n_az, h0=h0, obj_hz=obj_hz, gnd_hz=gnd_hz, obj_hz_step_deg=0.5, obj_height_m=obj_h,
                earth=earth, checks=checks, prepare_seconds=time.time() - t0)
    json.dump(meta, open(os.path.join(work, "terrain.json"), "w"), indent=1)
    print("done in %.0fs -> %s" % (time.time() - t0, work))


if __name__ == "__main__":
    main()
