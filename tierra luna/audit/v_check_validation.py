"""Independent check of docs/VALIDATION.md headline figures (reads bundle by DATA_CONTRACT rev 8; no engine import)."""
import json, csv, os, sys
import numpy as np
R = "/home/user/stars-beside-you"; B = R + "/app/public/data/v2"; V = R + "/tierra luna/validation/out"
man = json.load(open(B + "/manifest.json")); mi = json.load(open(B + "/missions.json"))
zones = json.load(open(B + "/mission_zones.json"))
I32 = -2147483648
def load(name):
    f = [x for x in man["files"] if x["name"] == name][0]; raw = open(B + "/" + name, "rb").read(); out = {}
    for c in f["columns"]:
        dt = "<f4" if c["type"] == "float32" else "<i4"
        out[c["name"]] = np.frombuffer(raw, dtype=dt, count=c["length"], offset=c["offset"])
    return out
eb = load("earth_base.bin"); mb = load("moon_base.bin")
reg_codes = [r["code"] for r in zones["regions"]]
res = {"missions": {}}
for m in mi["missions"]:
    k = m["id"]; e = load(f"earth_{k}.bin"); mm = load(f"moon_{k}.bin")
    li = e["land_index"]; rank = e["rank"]; tw = e["twin"]
    paired = rank != I32; twins = np.unique(tw[tw != I32])
    zone = set(zones["mission_zone_regions"][k])
    twin_in_zone = all(reg_codes[mb["region"][t]] in zone for t in twins)
    tc = mm.get("twin_count")
    top = []
    for cid in m["top5"]["ids"]:
        pos = np.where(eb["id"][li] == cid)[0]
        assert len(pos) == 1; p = pos[0]; L = li[p]
        row, col = cid // 360, cid % 360  # earth id = row*360+col (contract: cell_id rule)
        lat, lon = float(eb["lat"][row]), float(eb["lon"][col])
        assert int(eb["id"][L]) == cid
        inside = (89 - row <= lat <= 90 - row) and (-180 + col <= lon <= -179 + col)
        t = int(tw[p]); tz = reg_codes[mb["region"][t]] if t != I32 else None
        
        top.append({"id": int(cid), "rank": int(rank[p]), "lat": lat, "lon": lon, "inside_cell": bool(inside),
                    "twin": t, "twin_region": tz, "twin_in_zone": tz in zone})
    res["missions"][k] = {"passing": int(len(rank)), "paired": int(paired.sum()), "distinct_twins": int(len(twins)),
        "all_twins_in_zone": bool(twin_in_zone), "missions_json_ranked_count": m["ranked_count"],
        "missions_json_passing_without_similarity": m["passing_without_similarity"],
        "twin_count_sum_moon": int(tc[tc != I32].sum()) if tc is not None else None,
        "ranks_1_to_N": bool(np.array_equal(np.sort(rank[paired]), np.arange(1, paired.sum() + 1))),
        "top5": top}
tj = json.load(open(B + "/twins.json"))
res["twins_json_counts"] = {k: len(v["twins"]) for k, v in tj["missions"].items()}
res["twins_json_ids_equal_bin"] = {k: sorted(int(x.get("moon_index", x.get("index", x.get("id", -1)))) for x in v["twins"]) == [int(t) for t in np.unique(load(f"earth_{k}.bin")["twin"][load(f"earth_{k}.bin")["twin"] != I32])] for k, v in tj["missions"].items()}
res["twins_json_row_keys"] = {k: list(v["twins"][0].keys())[:8] for k, v in tj["missions"].items()}
def rows(n): return list(csv.DictReader(open(f"{V}/{n}.csv")))
m6 = {r["mission"]: r for r in rows("m6_coordinates_summary")}
res["m6_distinct_twins"] = {k: int(v["distinct_twins"]) for k, v in m6.items()}
res["m6_ranked_points"] = {k: int(v["ranked_points_checked"]) for k, v in m6.items()}
res["validity_records"] = sum(int(r["records"]) for r in rows("m2_validity_by_table"))
res["validity_failing"] = sum(int(r["failing_records"]) for r in rows("m2_validity_by_table"))
os.makedirs(R + "/tierra luna/audit/out", exist_ok=True)
json.dump(res, open(R + "/tierra luna/audit/out/v_check_validation.json", "w"), indent=1)
print(json.dumps(res, indent=1))
