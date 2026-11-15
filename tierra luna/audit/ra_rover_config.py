"""ra_rover_config (item 1): the Rover 'corrected' criteria set against the decisions, number by number.

    python ra_rover_config.py
Reads engine/engine_config.json, mission_scoring.json and the bundle missions.json (rover). Recomputes the two
uncertainty scales from their stated inputs (research 5 formula) with own code. Writes out/ra_rover_config.json.
"""
import json
import math
import os

import ra_rover_common as R

C = R.C
ec = R.load_config()
ms = json.load(open(os.path.join(C.TL, "mission_scoring.json"), encoding="utf-8"))
mis = json.load(open(os.path.join(C.BUNDLE, "missions.json"), encoding="utf-8"))
mr = [x for x in mis["missions"] if x["id"] == "rover"][0]
rv = ec["real_value_similarity"]["value"]
ro = rv["missions"]["rover"]
chk = []


def check(name, ok, got, want, note=""):
    chk.append({"check": name, "ok": bool(ok), "got": got, "want": want, "note": note})


vs = ro["variables"]
check("similarity variables are slope_deg and roughness_m only", [v["variable"] for v in vs] == ["slope_deg", "roughness_m"], [v["variable"] for v in vs], ["slope_deg", "roughness_m"], "11:23 decision 1")
check("weights 0.5 / 0.5, sum 1", [v["weight"] for v in vs] == [0.5, 0.5], [v["weight"] for v in vs], [0.5, 0.5])
check("both key", all(v["role"] == "key" for v in vs), [v["role"] for v in vs], ["key", "key"])
check("tolerances 2 deg and 30 m (unchanged)", [v["tolerance"] for v in vs] == [2.0, 30.0], [v["tolerance"] for v in vs], [2.0, 30.0])
check("key filter bound multiplier 1", rv["filter_bound_multiplier"]["key"] == 1.0, rv["filter_bound_multiplier"], {"key": 1.0})
check("elevation_rel_m out of similarity and filter", "elevation_rel_m" not in [v["variable"] for v in vs], None, None)
check("elevation_rel_m information row", "elevation_rel_m" in rv["info_differences"]["rover"] and "elevation_rel_m" in rv["info_in_pairs_file"]["rover"],
      [rv["info_differences"]["rover"], rv["info_in_pairs_file"]["rover"]], "contains elevation_rel_m")
morning_zone = ec["criteria_sets"]["value"]["missions"]["rover"]["sets"]["audited_morning"]["engine_patch"]["real_value_similarity.missions.rover"]["zone"]
check("zone unchanged (lat <= -75)", ro["zone"] == morning_zone and ro["zone"]["lat_max"] == -75.0, ro["zone"]["lat_max"], -75.0)
# uncertainty scale, own recomputation
SZE, SZM, DYE, DYM = 7.17, 10.0, 2 * math.pi * 6371.0e3 / 21600, 2 * math.pi * 1737.4e3 / 5760
s_slope = math.degrees(math.hypot(SZE / (math.sqrt(2) * 1853.0), SZM / (math.sqrt(2) * 1895.2)))
s_slope_exact_dy = math.degrees(math.hypot(SZE / (math.sqrt(2) * DYE), SZM / (math.sqrt(2) * DYM)))
s_rough = math.sqrt(2 * SZE ** 2 + 2 * SZM ** 2)
check("sigma slope = formula", abs(vs[0]["uncertainty_scale"]["sigma"] - s_slope) < 1e-6, vs[0]["uncertainty_scale"]["sigma"], round(s_slope, 6),
      f"pixel sizes from the radii: Earth 60 arc-second N-S {DYE:.1f} m, LDEM_16 {DYM:.1f} m -> {s_slope_exact_dy:.6f} deg")
check("sigma roughness = formula", abs(vs[1]["uncertainty_scale"]["sigma"] - s_rough) < 1e-6, vs[1]["uncertainty_scale"]["sigma"], round(s_rough, 6))
check("score form exp(-0.5 max(0, d/sigma - 1)^2)", all("max(0, |d| / sigma - 1)" in v["uncertainty_scale"]["score"] for v in vs), [v["uncertainty_scale"]["score"] for v in vs], "research 5 'Para implementar'")
t5 = ec["top5_selection"]["value"]["missions"]["rover"]
cs = ec["criteria_sets"]["value"]["missions"]["rover"]["sets"]["corrected"]["engine_patch"].get("top5_selection.missions.rover", t5)
check("five: spread_within_top_tie", cs["rule"] == "spread_within_top_tie", cs["rule"], "spread_within_top_tie")
check("five: min separation 2 deg", cs.get("min_separation_deg") == 2.0, cs.get("min_separation_deg"), 2.0)
check("five: ice skip snow_ice_frac >= 0.5", cs["skips"]["ice"]["enabled"] and cs["skips"]["ice"]["value"] == 0.5 and cs["skips"]["ice"]["op"] == ">=", cs["skips"]["ice"], ">= 0.5")
check("five: water skip mask_fraction < 0.5", cs["skips"]["water"]["enabled"] and cs["skips"]["water"]["value"] == 0.5 and cs["skips"]["water"]["op"] == "<", cs["skips"]["water"], "< 0.5",
      "brief: 'less than half land' is part of the order; config text says 'TO BE CONFIRMED by the team lead'")
# funnel / suitability = the team's file (no override)
mb = ms["missions"]["rover"]
gates_b = {g["variable"]: (g["min"], g["max"]) for g in mr["gates"] if g["origin"] == "mission"}
check("mission gates equal mission_scoring.json", all(gates_b[k] == (v.get("min"), v.get("max")) for k, v in mb["gates"].items()), gates_b, {k: (v.get("min"), v.get("max")) for k, v in mb["gates"].items()})
soft_b = {w["variable"]: (w["weight"], w["bad"], w["good"]) for w in mr["weighted_variables"]}
check("soft criteria equal mission_scoring.json", all(soft_b[k] == (v["weight"], v["bad"], v["good"]) for k, v in mb["soft"].items()), soft_b, {k: (v["weight"], v["bad"], v["good"]) for k, v in mb["soft"].items()})
check("soft weights sum 1", abs(sum(v["weight"] for v in mb["soft"].values()) - 1) < 1e-12, sum(v["weight"] for v in mb["soft"].values()), 1.0)
check("slope minimum 0.5 kept", mb["gates"]["slope_300m_deg"]["min"] == 0.5 and gates_b["slope_300m_deg"][0] == 0.5, gates_b["slope_300m_deg"], 0.5)
check("criteria set mission_scoring_deviations empty for rover", ec["criteria_sets"]["value"]["missions"]["rover"]["sets"]["corrected"]["mission_scoring_deviations"] == [], None, [])
check("selected criteria set rover = corrected", ec["criteria_sets"]["value"]["selected"]["rover"] == "corrected", ec["criteria_sets"]["value"]["selected"]["rover"], "corrected")
check("mix factor 0.5", float(ec["mix_factor"]["value"]) == 0.5, ec["mix_factor"]["value"], 0.5)
out = {"checks": chk, "all_ok": all(c["ok"] for c in chk), "corrected_set": ec["criteria_sets"]["value"]["missions"]["rover"]["sets"]["corrected"],
       "rover_similarity_block": ro, "top5_selection_rover_main": t5}
json.dump(out, open(os.path.join(R.OUT, "ra_rover_config.json"), "w"), indent=1, ensure_ascii=False)
for c in chk:
    print("OK " if c["ok"] else "NO ", c["check"], "|", json.dumps(c["got"], ensure_ascii=False)[:160], "|", c["note"])
print("all_ok", out["all_ok"])
