"""w4: ice in the Rover ranking (question 4). (a) as now; (b) hard filter excluding
thermal_inertia_class 'hielo'; (c) hard filter excluding snow_ice_frac >= 0.5. Rover compares real
values only (no percentile population), so removing Earth cells changes neither the lunar zone nor
any twin: the ranking of the remaining cells is the current one with the removed cells taken out.

    python "tierra luna/audit/w4_ice.py"

Writes audit/out/w4_ice.json.
"""
import numpy as np
from w_common import compare_tracks, dump, earth_name, latlon, load, mission_bundle_ranked, moon_name


def main():
    eng, ms, e, m = load()
    sc = [v["scale"] if "scale" in v else "real" for v in eng["real_value_similarity"]["value"]["missions"]["rover"]["variables"]]
    b = mission_bundle_ranked("rover")
    tic = e["thermal_inertia_class"].astype(object).to_numpy()
    snow = np.asarray(e["snow_ice_frac"], float)
    hielo = tic[b["id"]] == "hielo"
    sn = np.nan_to_num(snow[b["id"]], nan=-1) >= 0.5
    either = hielo | sn
    out = {"rover_scales": sc, "ranked": int(len(b["id"])), "hielo": int(hielo.sum()), "snow_ge_0.5": int(sn.sum()),
           "either": int(either.sum()), "both": int((hielo & sn).sum()),
           "best_rank_hielo": int(b["rank"][hielo].min()) if hielo.any() else None,
           "best_rank_snow": int(b["rank"][sn].min()) if sn.any() else None}
    for name, drop in {"b_no_hielo": hielo, "c_no_snow_ge_0.5": sn}.items():
        keep = np.flatnonzero(~drop)
        top50_now = list(b["id"][:50])
        top50_new = list(b["id"][keep[:50]])
        out[name] = {"paired_after": int(len(keep)), "distinct_twins_after": int(len(np.unique(b["twin"][keep]))),
                     "distinct_twins_now": int(len(np.unique(b["twin"]))),
                     "top5_same": top50_now[:5] == top50_new[:5], "top50_same": top50_now == top50_new,
                     "ranks_of_removed_in_top100": [int(x) for x in b["rank"][drop] if x <= 100]}
        print(name, out[name])
    print({k: v for k, v in out.items() if not isinstance(v, dict)})
    dump(out, "w4_ice.json")


if __name__ == "__main__":
    main()
