"""Re-audit Lunar base, item 8 (and the gate distance of the brief): the five shown in the bundle.
For each: land share, snow and ice share, dominant CCI class, distance to the nearest water-dominated
cell of the table (mask_fraction < 0.5; a coast proxy from the table's own columns), amplitude above the
15 K gate and tmin below the 5 C gate; the named place against my own great-circle nearest over the
engine's place file (reverse_geocoder rg_cities1000.csv, data only); lunar twin inside the 280-cell zone;
pairwise separations; the points skipped by the rule before the fifth, and whether any is a recognised site.
Run: python "tierra luna/audit/ra_base_places.py" [bundle_folder] -> out/ra_base_places.json"""
import json, math, os, sys
import numpy as np
import pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ra_base_common as R
import p5_common as C

BUNDLE = sys.argv[1] if len(sys.argv) > 1 else C.BUNDLE


def hav_km(lat1, lon1, lat2, lon2):
    p1, p2 = np.radians(lat1), np.radians(lat2)
    a = np.sin((p2 - p1) / 2) ** 2 + np.cos(p1) * np.cos(p2) * np.sin(np.radians(lon2 - lon1) / 2) ** 2
    return 2 * R.R_EARTH_KM * np.arcsin(np.sqrt(np.clip(a, 0, 1)))


def main():
    import reverse_geocoder
    cities = pd.read_csv(os.path.join(os.path.dirname(reverse_geocoder.__file__), "rg_cities1000.csv"), dtype=str, keep_default_na=False)
    clat, clon = cities["lat"].astype(float).to_numpy(), cities["lon"].astype(float).to_numpy()
    raw = R.load_raw_earth().set_index("id")
    wet = raw[raw["mask_fraction"] < 0.5]
    mj = json.load(open(os.path.join(BUNDLE, "missions.json"), encoding="utf-8"))
    lb = [x for x in mj["missions"] if x["id"] == R.M][0]
    five = [int(i) for i in lb["top5"]["ids"]]
    man = json.load(open(os.path.join(BUNDLE, "manifest.json"), encoding="utf-8"))
    C.BUNDLE = BUNDLE
    base = C.bundle_columns("earth_base.bin")
    pdb = C.bundle_columns("earth_place_detail.bin")
    pdj = json.load(open(os.path.join(BUNDLE, "place_detail.json"), encoding="utf-8"))
    bm = R.bundle_mission_at(BUNDLE)
    bpos = {int(i): k for k, i in enumerate(bm["ids"])}
    lidx = {int(i): k for k, i in enumerate(base["id"].astype(int))}
    P, _, _ = R.params_for_set("corrected")
    T = C.load_tables(P)
    zone = set(T["MOON"]["id"][C.zone_mask(T["MOON"], R.M, P)].astype(int))
    rows = []
    for e in five:
        rw = raw.loc[e]
        lat, lon = float(rw["lat_deg"]), float(rw["lon_deg"])
        d = hav_km(lat, lon, clat, clon)
        j = int(np.argmin(d))
        li = lidx[e]
        npl = pdb["nearest_place"][li]
        name_b = pdj["nearest_places"][int(npl)] if np.isfinite(npl) else None
        k = bpos[e]
        tw = int(bm["twin"][k])
        rows.append({"earth": e, "lat": lat, "lon": lon, "rank": int(bm["rank"][k]), "final": float(bm["final"][k]),
                     "mask_fraction": float(rw["mask_fraction"]), "snow_ice_frac": float(rw["snow_ice_frac"]),
                     "bare_frac": float(rw["bare_frac"]), "rock_or_bare_frac": float(rw["rock_or_bare_frac"]),
                     "lc_dominant_cci_code": int(rw["lc_dominant_cci_code"]), "thermal_inertia_class": rw["thermal_inertia_class"],
                     "km_to_water_dominated_cell": round(float(hav_km(lat, lon, wet["lat_deg"].to_numpy(), wet["lon_deg"].to_numpy()).min()), 1),
                     "amp_k": float(rw["lst_diurnal_amp_k"]), "amp_above_gate_k": round(float(rw["lst_diurnal_amp_k"]) - 15.0, 2),
                     "tmin_c": float(rw["tmin_c"]), "tmin_below_gate_c": round(5.0 - float(rw["tmin_c"]), 2),
                     "place_bundle": name_b, "place_km_bundle": float(pdb["nearest_place_km"][li]),
                     "place_mine": cities["name"][j], "place_km_mine": round(float(d[j]), 1),
                     "place_same": name_b == cities["name"][j], "twin": tw, "twin_in_zone": tw in zone})
    sep = [[round(R.gc_deg(a["lat"], a["lon"], b["lat"], b["lon"]), 2) for b in rows] for a in rows]
    min_sep = min(sep[i][j] for i in range(5) for j in range(5) if i < j)
    rep = {"bundle": BUNDLE, "five": rows, "pairwise_deg": sep, "min_separation_deg": min_sep}
    for x in rows:
        print(json.dumps(x, ensure_ascii=False))
    print("min separation", min_sep)
    print(R.dump(rep, "ra_base_places.json"))


if __name__ == "__main__":
    main()
