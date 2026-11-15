"""Re-audit Solar panels, item 8: the five places.

    python -I ra_solar_five.py [criteria set=corrected] [bundle folder=app/public/data/v2]

For each of the five (own recomputation, shipped rule): land share, snow/ice share, dominant land
cover (CCI 210 = water), bare share, an own 1-degree distance to the sea (great-circle distance from
the cell centre to the nearest cell centre with land share 0; resolution about 111 km, labelled so),
the nearest GeoNames place by brute-force haversine over the engine's place data (reverse_geocoder
rg_cities1000.csv) compared with the bundle's earth_place_detail, the lunar twin's latitude and
elevation against the zone, and every pairwise separation. Also lists the points skipped before the
fifth and whether a recognised site (validation_sites_solar.csv, 3x3 block) was among them.
Writes out/ra_solar_five_<set>.json.
"""
import csv
import json
import math
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ra_solar_common as R  # noqa: E402

RE = 6371.0


def hav(la1, lo1, la2, lo2):
    p1, p2 = np.radians(la1), np.radians(la2)
    dp = p2 - p1
    dl = np.radians(np.asarray(lo2) - lo1)
    a = np.sin(dp / 2) ** 2 + np.cos(p1) * np.cos(p2) * np.sin(dl / 2) ** 2
    return 2 * RE * np.arcsin(np.sqrt(np.clip(a, 0, 1)))


def main():
    set_name = sys.argv[1] if len(sys.argv) > 1 else "corrected"
    bdir = os.path.abspath(sys.argv[2]) if len(sys.argv) > 2 else R.BUNDLE
    P, _, _, _ = R.load_params_set(set_name)
    T, D = R.tables(P)
    E, M = T["EARTH"], T["MOON"]
    r = R.run(P)
    kept, skipped = R.five(r, P, with_skipped=True)
    import reverse_geocoder
    rg = pd.read_csv(os.path.join(os.path.dirname(reverse_geocoder.__file__), "rg_cities1000.csv"))
    pos = {int(i): j for j, i in enumerate(E["id"].to_numpy())}
    mpos = {int(i): j for j, i in enumerate(M["id"].to_numpy())}
    lat, lon = E["lat"].to_numpy(float), E["lon"].to_numpy(float)
    sea = (E["__mask_fraction"].to_numpy(float) == 0)
    # bundle place detail
    base = R.bundle_cols(bdir, "earth_base.bin")
    pdb = R.bundle_cols(bdir, "earth_place_detail.bin")
    pdj = json.load(open(os.path.join(bdir, "place_detail.json"), encoding="utf-8"))
    names = pdj["nearest_places"]
    land_ids = base["id"].astype(int)
    lpos = {int(i): k for k, i in enumerate(land_ids)}
    zone = P["missions"]["solar"]["sim"]["zone"]
    melev = pd.to_numeric(M[zone["elevation_column"]], errors="coerce").to_numpy(float)
    out = []
    for qq in kept:
        e = int(r["pass_ids"][qq])
        j = pos[e]
        d = hav(lat[j], lon[j], rg["lat"].to_numpy(float), rg["lon"].to_numpy(float))
        k = int(np.argmin(d))
        ds = hav(lat[j], lon[j], lat[sea], lon[sea])
        t = int(r["twin"][qq])
        mj = mpos[t]
        li = lpos.get(e)
        bname = None if li is None or not np.isfinite(pdb["nearest_place"][li]) else names[int(pdb["nearest_place"][li])]
        bkm = None if li is None else float(pdb["nearest_place_km"][li])
        x = {"earth": "E%d" % e, "lat": float(lat[j]), "lon": float(lon[j]), "rank": int(r["rank"][qq]), "final": float(r["final_pub"][qq]),
             "land_share": round(float(E["__mask_fraction"].iloc[j]), 4), "snow_ice_frac": None if pd.isna(E["__snow_ice_frac"].iloc[j]) else round(float(E["__snow_ice_frac"].iloc[j]), 4),
             "lc_dominant_cci_code": None if pd.isna(E["__lc_dominant_cci_code"].iloc[j]) else int(E["__lc_dominant_cci_code"].iloc[j]),
             "bare_frac": None if pd.isna(E["__bare_frac"].iloc[j]) else round(float(E["__bare_frac"].iloc[j]), 3),
             "clear_frac_isccp": round(float(E["clear_frac_isccp"].iloc[j]), 3),
             "dist_to_all_sea_cell_centre_km_1deg": round(float(ds.min()), 0),
             "nearest_place_own": "%s (%s)" % (rg["name"].iloc[k], rg["cc"].iloc[k]), "nearest_km_own": round(float(d[k]), 1),
             "nearest_place_bundle": bname, "nearest_km_bundle": None if bkm is None else round(bkm, 1),
             "country_bundle": None if li is None else int(base["country"][li]),
             "twin": "M%d" % t, "twin_lat": float(M["lat"].iloc[mj]), "twin_lon": float(M["lon"].iloc[mj]), "twin_elev_m": round(float(melev[mj]), 1),
             "twin_in_zone": bool(abs(float(M["lat"].iloc[mj])) <= zone["abs_lat_max"] and melev[mj] <= zone["elevation_max_m"])}
        x["place_match"] = (bname == rg["name"].iloc[k]) and (bkm is not None and abs(bkm - d[k]) < 0.15)
        out.append(x)
    sep = []
    for a in range(len(out)):
        for b in range(a + 1, len(out)):
            sep.append({"pair": [out[a]["earth"], out[b]["earth"]], "deg": round(R.ang_deg(out[a]["lat"], out[a]["lon"], out[b]["lat"], out[b]["lon"]), 2)})
    # recognised sites among skipped (3x3 block)
    rows = [ln for ln in open(os.path.join(R.TL, "data", "benchmark", "validation_sites_solar.csv"), encoding="utf-8") if not ln.startswith("#")]
    sites = list(csv.DictReader(rows))
    blk = {}
    for s in sites:
        rr, cc = int(math.floor(90 - float(s["lat"]))), int(math.floor(float(s["lon"]) + 180))
        for dr in (-1, 0, 1):
            for dc in (-1, 0, 1):
                blk[(rr + dr) * 360 + (cc + dc) % 360] = s["site_id"] + " " + s["name"]
    sk = [{"earth": "E%d" % e, "rank": rk, "why": w, "recognised_site_3x3": blk.get(e)} for e, rk, w in skipped]
    res = {"criteria_set": set_name, "five": out, "separations_deg": sep, "min_separation_deg": min(x["deg"] for x in sep),
           "skipped_before_fifth": sk, "recognised_site_skipped": [x for x in sk if x["recognised_site_3x3"]],
           "dist_note": "distance to the centre of the nearest 1-degree cell with land share 0: an own approximation at grid resolution, not a coastline distance"}
    p = R.jdump(res, "ra_solar_five_%s.json" % set_name)
    for x in out:
        print(x)
    print(sep)
    print(sk)
    print("wrote", p)


if __name__ == "__main__":
    main()
