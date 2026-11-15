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


BUNDLE = os.path.join(HERE, "..", "public", "data", "v2")


def check_pair_values(sc):
    """Lunar base card: every number of scenario.pair_values must equal the shipped bundle
    (explain.json, the item of that rank), the ids must be the scenario's cells and the
    population sizes those of missions.json."""
    pv = sc.get("pair_values")
    if not pv:
        return []
    if sc.get("preview") or pv.get("preview"):
        print("PREVIEW scenario: pair not checked against the bundle (stills and terrain only; render.js refuses a full render)")
        return []
    if pv.get("mission") == "solar":
        return check_pair_values_solar(sc, pv)
    ex = json.load(open(os.path.join(BUNDLE, "explain.json")))
    its = [x for x in ex["missions"]["lunar_base"] if x["id"] == pv["earth_id"]]
    if not its:
        raise SystemExit("PAIR MISMATCH: E%d is not in explain.json missions.lunar_base" % pv["earth_id"])
    it = its[0]
    sim = it["similarity"]
    out = []

    def eq(name, a, b):
        ok = (a == b) if (isinstance(a, str) or a is None or b is None) else abs(float(a) - float(b)) < 1e-9
        out.append(dict(item=name, scenario=a, bundle=b, ok=ok))
        if not ok:
            raise SystemExit("PAIR MISMATCH %s: scenario %s bundle %s" % (name, a, b))
    # the pair's true place: overall rank (explain.json) and position among the five shown (missions.json top5)
    eq("rank (overall)", pv["rank"], it["rank"])
    t5 = ([m for m in json.load(open(os.path.join(BUNDLE, "missions.json")))["missions"] if m.get("id") == "lunar_base"][0].get("top5") or {})
    ids = t5.get("ids") or []
    pos = ids.index(pv["earth_id"]) + 1 if pv["earth_id"] in ids else None
    eq("position among the five shown (missions.json top5.ids)", pv.get("top5_position"), pos)
    if pos is not None:
        eq("top5 overall rank", it["rank"], t5["overall_ranks"][pos - 1])
        want = "Earth analog and lunar twin: lunar base, analog %d of the five shown" % pos
    else:
        want = "Earth analog and lunar twin: one of the Lunar base analog pairs (overall rank %d)" % it["rank"]
    eq("card title", sc["card"]["title"], want)
    for k in ("suitability", "similarity", "final"):
        if ("%s" % pv[k]) not in sc["card"]["subtitle"]:
            raise SystemExit("PAIR MISMATCH card subtitle does not show %s %s" % (k, pv[k]))
    eq("earth_id", pv["earth_id"], it["id"]); eq("moon_id", pv["moon_id"], sim["twin"]["id"])
    eq("earth cell", sc["earth_site"]["cell_id"], "E%d" % it["id"]); eq("moon cell", sc["site"]["cell_id"], "M%d" % sim["twin"]["id"])
    for k in ("suitability", "final"):
        eq(k, pv[k], it[k])
    eq("similarity", pv["similarity"], sim["value"])
    eq("pair_sentence", pv["pair_sentence"], sim["pair_sentence"])
    for v in sim["variables"]:
        d = pv["variables"][v["variable"]]
        eq(v["variable"] + ".earth", d["earth"], v["earth_real"]); eq(v["variable"] + ".moon", d["moon"], v["moon_real"])
        eq(v["variable"] + ".diff", d["diff"], v["difference_real"])
        if v["scale"] == "percentile_within_population":
            eq(v["variable"] + ".earth_pct", d["earth_pct"], v["earth"]); eq(v["variable"] + ".moon_pct", d["moon_pct"], v["moon"])
            eq(v["variable"] + ".diff_pct", d["diff_pct"], v["difference"])
    for k, d in sim["not_part_of_similarity"].items():
        for s in ("earth", "moon", "difference"):
            eq("info.%s.%s" % (k, s), pv["not_part_of_similarity"][k][s], d[s])
    eq("place.nearest", sc["earth_site"]["nearest_place"], it["place"]["nearest_place"])
    eq("place.nearest_km", sc["earth_site"]["nearest_place_km"], it["place"]["nearest_place_km"])
    eq("place.region", sc["earth_site"]["name"], "%s, %s" % (it["place"]["region"], it["place"]["country"]))
    eq("feature", sc["site"]["place_ref"]["feature"], sim["twin"]["feature"])
    eq("feature_km", sc["site"]["place_ref"]["distance_km"], sim["twin"]["feature_km"])
    ms = json.load(open(os.path.join(BUNDLE, "missions.json")))
    lb = [m for m in ms["missions"] if m.get("id") == "lunar_base"][0]["similarity"]
    eq("population EARTH", pv["populations"]["earth_points"], lb["populations"]["EARTH"]["cells"])
    eq("population MOON", pv["populations"]["moon_cells"], lb["populations"]["MOON"]["cells"])
    eq("zone name", sc["site"]["zone"]["name"], lb["zone"]["name"])
    return out


def _f32_tenths(x):
    """similarity.json texts.solar_limitation display rule: the stored float32 written with 1 decimal,
    half up, as an integer of tenths (6.177 -> 62)."""
    sh = "%.12f" % float(str(np.float32(x)))
    i = sh.index(".")
    return int(sh[:i]) * 10 + int(sh[i + 1]) + (1 if int(sh[i + 2]) >= 5 else 0)


def check_pair_values_solar(sc, pv):
    """Solar panels card: every number of scenario.pair_values (and every card level) must equal the
    shipped bundle: explain.json missions.solar item of that rank, missions.json (zone, similarity
    variables and their levels), mission_zones.json (zone label), similarity.json (display rule of the
    share lost) and variables.json (levels)."""
    ex = json.load(open(os.path.join(BUNDLE, "explain.json")))
    ms0 = [x for x in json.load(open(os.path.join(BUNDLE, "missions.json")))["missions"] if x.get("id") == "solar"][0]
    top5 = (ms0.get("top5") or {}).get("ids")
    first = top5[0] if top5 else [x for x in ex["missions"]["solar"] if x["rank"] == 1][0]["id"]
    if pv["earth_id"] != first:
        raise SystemExit("PAIR MISMATCH: the scenario's Earth point E%d is not the first Solar panels analog of the bundle (E%d, %s); rerun tools/solar_pair.py"
                         % (pv["earth_id"], first, "missions.json top5.ids[0]" if top5 else "explain.json rank 1"))
    it = [x for x in ex["missions"]["solar"] if x["id"] == first][0]
    sim = it["similarity"]
    out = [dict(item="first analog", scenario=pv["earth_id"], bundle=first, ok=True)]
    eq0 = lambda n, x, y: None
    pos = top5.index(first) + 1 if top5 and first in top5 else None
    if pv.get("top5_position") != pos:
        raise SystemExit("PAIR MISMATCH position among the five shown: scenario %s bundle %s" % (pv.get("top5_position"), pos))
    if pos and ms0["top5"]["overall_ranks"][pos - 1] != it["rank"]:
        raise SystemExit("PAIR MISMATCH top5 overall rank")
    want = ("Earth analog and lunar twin: solar panels, analog %d of the five shown" % pos) if pos else \
        ("Earth analog and lunar twin: one of the Solar panels analog pairs (overall rank %d)" % it["rank"])
    if sc["card"]["title"] != want:
        raise SystemExit("PAIR MISMATCH card title: %r, expected %r" % (sc["card"]["title"], want))
    for k, v in (("rank", it["rank"]), ("suitability", it["suitability"]), ("similarity", sim["value"]), ("final", it["final"])):
        if ("%s" % v) not in sc["card"]["subtitle"]:
            raise SystemExit("PAIR MISMATCH card subtitle does not show %s %s" % (k, v))
    out.append(dict(item="position/title/subtitle", scenario=pos, bundle=pos, ok=True))

    def eq(name, a, b):
        ok = (a == b) if (isinstance(a, str) or a is None or b is None) else abs(float(a) - float(b)) < 1e-9
        out.append(dict(item=name, scenario=a, bundle=b, ok=ok))
        if not ok:
            raise SystemExit("PAIR MISMATCH %s: scenario %s bundle %s" % (name, a, b))
    eq("earth_id", pv["earth_id"], it["id"]); eq("moon_id", pv["moon_id"], sim["twin"]["id"])
    eq("earth cell", sc["earth_site"]["cell_id"], "E%d" % it["id"]); eq("moon cell", sc["site"]["cell_id"], "M%d" % sim["twin"]["id"])
    eq("earth lat", sc["earth_site"]["lat_deg"], it["lat"]); eq("earth lon", sc["earth_site"]["lon_deg"], it["lon"])
    eq("moon lat", sc["site"]["lat_deg"], sim["twin"]["lat"]); eq("moon lon", sc["site"]["lon_deg"], sim["twin"]["lon"])
    for k in ("suitability", "final", "rank"):
        eq(k, pv[k], it[k])
    eq("similarity", pv["similarity"], sim["value"]); eq("rule", pv["rule"], sim["rule"])
    eq("pair_sentence", pv["pair_sentence"], sim["pair_sentence"])
    if len(pv["variables"]) != len(sim["variables"]):
        raise SystemExit("PAIR MISMATCH: number of similarity variables")
    for v in sim["variables"]:
        d = pv["variables"][v["variable"]]
        for s_ in ("earth", "moon", "difference", "tolerance", "role", "weight"):
            eq(v["variable"] + "." + s_, d[s_], v[s_])
    for k, d in sim["not_part_of_similarity"].items():
        for s_ in ("earth", "moon", "difference"):
            eq("info.%s.%s" % (k, s_), pv["not_part_of_similarity"][k][s_], d[s_])
    for k in ("ground_kwh_m2_day", "toa_kwh_m2_day", "lost_share"):
        eq("atmosphere." + k, pv["atmosphere"][k], sim["atmosphere"][k])
    # share lost, as displayed (similarity.json texts.solar_limitation.placeholders.loss_pct.formula)
    A = _f32_tenths(sim["atmosphere"]["toa_kwh_m2_day"]); G = _f32_tenths(sim["atmosphere"]["ground_kwh_m2_day"])
    eq("displayed toa (tenths)", pv["atmosphere"]["toa_display"], "%d.%d" % divmod(A, 10))
    eq("displayed ground (tenths)", pv["atmosphere"]["ground_display"], "%d.%d" % divmod(G, 10))
    eq("displayed share lost %", pv["atmosphere"]["loss_pct_display"], (200 * (A - G) + A) // (2 * A))
    simj = json.load(open(os.path.join(BUNDLE, "similarity.json")))
    eq("loss rule", pv["atmosphere"]["loss_rule"], simj["texts"]["solar_limitation"]["placeholders"]["loss_pct"]["rule"])
    eq("saturation note", pv["saturation_note"], simj["texts"]["solar_similarity_saturation"]["text"])
    eq("lunar day (Earth days)", pv["synodic_days_bundle"], simj["real_value"]["lunar_day_earth_days"])
    # place names
    eq("place.nearest", sc["earth_site"]["nearest_place"], it["place"]["nearest_place"])
    eq("place.nearest_km", sc["earth_site"]["nearest_place_km"], it["place"]["nearest_place_km"])
    eq("place.country", sc["earth_site"]["name"], ", ".join(x for x in (it["place"]["region"], it["place"]["country"]) if x))
    eq("feature", sc["site"]["place_ref"]["feature"], sim["twin"]["feature"])
    eq("feature_km", sc["site"]["place_ref"]["distance_km"], sim["twin"]["feature_km"])
    # zone: missions.json rule and mission_zones.json label of the mission's region
    ms = json.load(open(os.path.join(BUNDLE, "missions.json")))
    m = [x for x in ms["missions"] if x.get("id") == "solar"][0]
    z = m["similarity"]["zone"]
    eq("zone abs_lat_max", sc["site"]["zone"]["abs_lat_max"], z["abs_lat_max"]); eq("zone elevation_max_m", sc["site"]["zone"]["elevation_max_m"], z["elevation_max_m"])
    eq("zone cells", sc["site"]["zone"]["cells"], z["cells"])
    mz = json.load(open(os.path.join(BUNDLE, "mission_zones.json")))
    code = mz["mission_zone_regions"]["solar"]
    eq("zone code", sc["site"]["zone"]["region_code"], code[0] if len(code) == 1 else None)
    eq("zone name", sc["site"]["zone"]["name"], [r for r in mz["regions"] if r["code"] == code[0]][0]["label"])
    if not (abs(sc["site"]["lat_deg"]) <= z["abs_lat_max"] and sc["table_values"]["moon"]["elevation_m"]["value"] <= z["elevation_max_m"]):
        raise SystemExit("lunar cell outside the Solar panels zone")
    # levels: similarity variables from missions.json sides, the rest from variables.json
    vj = {v["name"]: v for v in json.load(open(os.path.join(BUNDLE, "variables.json")))["variables"]}
    simv = {v["variable"]: v for v in m["similarity"]["variables"]}
    for var, lv in pv["levels"].items():
        for b, L in lv.items():
            src = simv[var]["sides"][b.upper()]["level"] if var in simv else vj[var]["bodies"][b.upper()]["level"]
            eq("level %s.%s" % (var, b), L, src)
    eq("population EARTH", pv["populations"]["earth_paired"], m["similarity"]["paired_count"])
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


_CYL = {}


def sample_product(spec, lab, lat, lon, line_sign, cache):
    if lab.get("projection") == "simple_cylindrical":     # one local file (memory map); spec["file"] in the cache
        path = os.path.join(cache, spec["file"])
        if path not in _CYL:
            _CYL[path] = D.cyl_open(path, lab)
        a = _CYL[path]
        s, l = D.cyl_pixel(lab, lat, lon)
        assert s.min() >= 0 and s.max() < lab["samples"] - 1 and l.min() >= 0 and l.max() < lab["lines"] - 1, "patch leaves the product"
        r0, r1 = int(np.floor(l.min())), int(np.ceil(l.max())) + 1
        c0, c1 = int(np.floor(s.min())), int(np.ceil(s.max())) + 1
        blk = np.asarray(a[r0:r1 + 1, c0:c1 + 1], dtype=np.float64) * lab["scaling"] * lab["to_m"]
        if not np.isfinite(blk).all() or np.abs(blk).max() > 20000:
            raise SystemExit("invalid heights in %s rows %d-%d" % (spec["file"], r0, r1))
        return bilinear(blk, l - r0, s - c0), path, (r0, r1)
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
    ap.add_argument("--checks-only", action="store_true", help="table and bundle checks only, no terrain")
    a = ap.parse_args()
    sc = json.load(open(a.scenario))
    work = os.path.join(a.work, sc["name"]); cache = os.path.join(a.work, "cache")
    os.makedirs(work, exist_ok=True); os.makedirs(cache, exist_ok=True)
    t0 = time.time()
    checks = {"tables": check_tables(sc)}
    print("table values: %d checked, all equal" % len(checks["tables"]))
    checks["pair_values"] = check_pair_values(sc)
    if checks["pair_values"]:
        print("pair values: %d checked against the bundle, all equal" % len(checks["pair_values"]))
    if a.checks_only:
        return

    lat, lon = sc["site"]["lat_deg"], sc["site"]["lon_deg"]
    k = float(D.ps_scale_factor(lat))
    specs = sc["dem"]
    labs = {}
    for key in ("near", "far"):
        if specs[key].get("projection") == "simple_cylindrical":
            lp = os.path.join(cache, os.path.basename(specs[key]["label"]))
            if not os.path.exists(lp):
                D.curl(specs[key]["label"], lp)
            labs[key] = D.parse_cyl_label(open(lp, encoding="latin-1").read())
            k = 1.0   # simple cylindrical: MAP_SCALE is the true north-south spacing; east-west it is finer (x cos lat)
        else:
            labs[key], lp = D.get_label(specs[key]["label"], cache)
    near_step = labs["near"]["scale_m"] / k * specs["near"].get("native_step_px", 1)
    far_native = labs["far"]["scale_m"] / k * specs["far"].get("native_step_px", 1)
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
        i = int(round((ev["az_mean_deg"] if "az_mean_deg" in ev else (ev["az_min_deg"] + ev["az_max_deg"]) / 2) / 0.5)) % n_obj
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
