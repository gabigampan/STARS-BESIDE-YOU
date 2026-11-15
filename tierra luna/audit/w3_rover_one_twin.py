"""w3: why the five Rover pairs share one lunar twin (question 3), and option (b) 'each lunar cell
is the twin of at most one of the listed top 5' (not applied; weights/tolerances unchanged).

    python "tierra luna/audit/w3_rover_one_twin.py"

Writes audit/out/w3_rover_one_twin.json.
"""
import numpy as np
from w_common import audio_top5, base_run, compare_tracks, dump, earth_name, latlon, mission_bundle_ranked, moon_name
import p2_model


def main():
    r = base_run("rover")
    sp = r["spec"]
    zi = r["zone"]
    Mz = r["Mcmp_zone"]
    out = {"zone_cells": int(len(zi)), "bounds": dict(zip(sp["vars"], sp["bound"].tolist())), "cells": []}
    for k, eid, mid in audio_top5()["rover"]:
        cid = int(eid[1:])
        i = int(np.searchsorted(r["ids"], cid))
        d, ok, sim, s = p2_model.pair_matrix(r["cmp_earth"][i], Mz, sp)
        fin = np.isfinite(d)
        within = fin & (np.nan_to_num(d, nan=np.inf) <= sp["bound"][None, :])
        fails = np.where(sp["key"][None, :], ~within, fin & ~within)
        by_var = {v: int(fails[:, q].sum()) for q, v in enumerate(sp["vars"])}
        only = {v: int((fails[:, q] & (fails.sum(1) == 1)).sum()) for q, v in enumerate(sp["vars"])}
        missing_key = int((~fin[:, sp["key"]]).any(1).sum())
        o = np.lexsort((zi, -sim))[:3]
        best3 = [{"moon_id": f"M{zi[t]}", "lat_lon": latlon(int(zi[t])), "feature": moon_name(int(zi[t])), "similarity": round(float(sim[t]), 2),
                  "passes_filter": bool(ok[t]), "diff": {v: round(float(d[t, q]), 3) for q, v in enumerate(sp["vars"])}} for t in o]
        okidx = np.flatnonzero(ok)
        passing_list = sorted([(round(float(sim[t]), 3), f"M{zi[t]}") for t in okidx], reverse=True)[:5]
        rec = {"track": k, "earth_id": eid, "earth_values": dict(zip(sp["vars"], np.round(r["cmp_earth"][i], 3).tolist())),
               "zone_cells_passing_filter": int(ok.sum()), "fails_by_variable": by_var, "fails_only_this_variable": only,
               "key_value_missing_in_zone": missing_key, "best3_ignoring_filter": best3, "best_passing": passing_list}
        out["cells"].append(rec)
        print(k, eid, "pass", int(ok.sum()), "fails", by_var, "only", only, "missing", missing_key)
        for b in best3:
            print("    ", b["moon_id"], b["feature"]["feature"], b["similarity"], b["passes_filter"], b["diff"])
        print("    passing:", passing_list)
    # the twin's own values
    t = 59895
    out["twin_M59895_values"] = {v: float(r["mv"][v][t]) for v in sp["vars"]}
    # option (b): distinct twins in the top 5
    b = mission_bundle_ranked("rover")
    used, top = set(), []
    for i in range(len(b["id"])):
        if b["twin"][i] in used:
            continue
        used.add(int(b["twin"][i]))
        tw = int(b["twin"][i]); ml, mo = latlon(tw)
        top.append({"rank": len(top) + 1, "current_rank": int(b["rank"][i]), "earth_id": f"E{b['id'][i]}", "lat": b["lat"][i], "lon": b["lon"][i],
                    "earth_place": earth_name(b["id"][i]), "moon_id": f"M{tw}", "moon_lat": ml, "moon_lon": mo, "moon_feature": moon_name(tw),
                    "similarity": round(b["sim"][i], 2), "suitability": round(b["suit"][i], 2), "final": round(b["final"][i], 2)})
        if len(top) == 5:
            break
    tr, broken = compare_tracks("rover", top)
    out["option_b_distinct_twins"] = {"top": top, "tracks": tr, "tracks_broken": broken}
    for x in top:
        print("b", x["rank"], x["current_rank"], x["earth_id"], x["earth_place"]["place"], x["moon_id"], x["moon_feature"]["feature"], x["similarity"], x["suitability"], x["final"])
    print("broken", broken)
    dump(out, "w3_rover_one_twin.json")


if __name__ == "__main__":
    main()
