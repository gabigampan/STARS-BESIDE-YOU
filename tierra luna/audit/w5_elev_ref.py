"""w5: Earth reference of elevation_rel_m for Rover (question 5), not applied.
 (a) as now: mean over land cells weighted by cos(latitude);
 (b) weighted by cos(latitude) x mask_fraction (land fraction);
 (c) sea level (0 m).
The lunar reference (Moon body mean) is unchanged. Full Rover pairing recomputed.

    python "tierra luna/audit/w5_elev_ref.py"

Writes audit/out/w5_elev_ref.json.
"""
import numpy as np
from w_common import base_run, compare_tracks, dump, load, run, summary
import p2_model


def main():
    eng, ms, e, m = load()
    el = p2_model.num(e, "elevation_m")
    mf = p2_model.num(e, "mask_fraction")
    w = np.cos(np.radians(e["lat_deg"].to_numpy(float)))
    land = np.isfinite(el) & (np.nan_to_num(mf) > 0)
    ref_a = p2_model.cos_mean(np.where(land, el, np.nan), e["lat_deg"].to_numpy(float))
    ref_b = float(np.sum((el * w * mf)[land]) / np.sum((w * mf)[land]))
    out = {"ref_a_m": ref_a, "ref_b_m": ref_b, "ref_c_m": 0.0}
    print(out)
    for name, ref in {"a_cos_lat": None, "b_cos_lat_x_land_fraction": ref_b, "c_sea_level": 0.0}.items():
        r = base_run("rover") if ref is None else run("rover", earth_elev_mean=ref)
        s = summary(r)
        s["earth_reference_m"] = r["derived_notes"]["elevation_body_mean"]["EARTH"]
        s["tracks"], s["tracks_broken"] = compare_tracks("rover", s["top"], r)
        out[name] = s
        print(name, "ref", round(s["earth_reference_m"], 1), "pass", s["passing"], "paired", s["paired"], "twins", s["distinct_twins"], "broken", s["tracks_broken"])
        for t in s["top"]:
            print("   ", t["rank"], t["earth_id"], t["earth_place"]["place"], t["moon_id"], t["moon_feature"]["feature"], t["similarity"], t["suitability"], t["final"])
        for tr in s["tracks"]:
            print("      ", tr)
    dump(out, "w5_elev_ref.json")


if __name__ == "__main__":
    main()
