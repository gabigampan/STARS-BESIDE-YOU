"""w2: minimum separation between Earth cell centres in the top 5 (question 2), not applied.
Greedy by rank: keep the best, skip any cell within the separation of one already kept.
Separations: 2 degrees of great circle (= 222.4 km on R = 6371 km), 500 km, 1000 km.
Uses the ranking of the shipped bundle (identical to the in-memory recompute, see w0).

    python "tierra luna/audit/w2_separation.py"

Writes audit/out/w2_separation.json.
"""
import numpy as np
from w_common import MISSIONS, R_EARTH, compare_tracks, dump, earth_name, gc_km, latlon, moon_name, mission_bundle_ranked

SEPS = {"2deg_222.4km": float(np.radians(2.0) * R_EARTH), "500km": 500.0, "1000km": 1000.0}


def main():
    out = {}
    for mi in MISSIONS:
        r = mission_bundle_ranked(mi)
        out[mi] = {}
        for name, km in SEPS.items():
            kept = []
            for i in range(len(r["id"])):
                if all(gc_km(r["lat"][i], r["lon"][i], r["lat"][j], r["lon"][j], R_EARTH) >= km for j in kept):
                    kept.append(i)
                if len(kept) == 5:
                    break
            top = []
            for k, i in enumerate(kept, 1):
                t = int(r["twin"][i]); ml, mo = latlon(t)
                top.append({"rank": k, "current_rank": int(r["rank"][i]), "earth_id": f"E{r['id'][i]}", "lat": r["lat"][i],
                            "lon": r["lon"][i], "earth_place": earth_name(r["id"][i]), "moon_id": f"M{t}", "moon_lat": ml,
                            "moon_lon": mo, "moon_feature": moon_name(t), "similarity": round(r["sim"][i], 2),
                            "suitability": round(r["suit"][i], 2), "final": round(r["final"][i], 2)})
            tr, broken = compare_tracks(mi, top)
            out[mi][name] = {"separation_km": km, "top": top, "tracks": tr, "tracks_broken": broken}
            print(mi, name, [(t["current_rank"], t["earth_id"], t["earth_place"]["place"], t["moon_id"], t["final"]) for t in top], "broken", broken)
    dump(out, "w2_separation.json")


if __name__ == "__main__":
    main()
