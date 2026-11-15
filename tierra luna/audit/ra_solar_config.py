"""Re-audit Solar panels, items 1 and 9 (machine part).

    python -I ra_solar_config.py [bundle folder]

Item 1: the effective Solar configuration of each criteria set (own reader: ra_solar_common.load_params_set),
the full list of differences corrected vs audited_morning and vs the team's mission_scoring.json,
weight sums, and whether every soft deviation from mission_scoring.json is listed in the set's
mission_scoring_deviations with a reason and a source.
Item 9: every Solar text of the bundle (similarity.json texts with 'show', missions.json solar entry,
explain.json, variables.json entries used by Solar), with every number found in each text, and a scan
for left-overs of the earlier rule (terms of the removed criteria) and unsupported superlatives.
Writes out/ra_solar_config.json and out/ra_solar_texts.json.
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ra_solar_common as R  # noqa: E402


def flat(d, pre=""):
    out = {}
    if isinstance(d, dict):
        for k, v in d.items():
            if k in ("why", "source", "tolerance_set_by", "weights_why", "label", "name"):
                continue
            out.update(flat(v, pre + "." + str(k) if pre else str(k)))
    elif isinstance(d, list):
        for i, v in enumerate(d):
            key = v.get("variable", i) if isinstance(v, dict) else i
            out.update(flat(v, "%s[%s]" % (pre, key)))
    else:
        out[pre] = d
    return out


def eff(set_name):
    P, ec, name, sd = R.load_params_set(set_name)
    m = P["missions"]["solar"]
    return {"require_present": m["require_present"], "gates": m["gates"], "common_gates": P["common_gates"], "soft": m["soft"],
            "sim": m["sim"], "top5": P["top5"], "alpha": P["alpha"], "mult": P["mult"], "score_decimals": P["score_decimals"]}, sd


def main():
    bdir = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else R.BUNDLE
    a, sda = eff("corrected")
    b, sdb = eff("audited_morning")
    fa, fb = flat(a), flat(b)
    diff = [{"key": k, "audited_morning": fb.get(k), "corrected": fa.get(k)} for k in sorted(set(fa) | set(fb)) if fa.get(k) != fb.get(k)]
    ms = json.load(open(os.path.join(R.TL, "mission_scoring.json"), encoding="utf-8"))["missions"]["solar"]
    team_soft = {k: {kk: vv for kk, vv in v.items() if kk in ("weight", "bad", "good")} for k, v in ms["soft"].items()}
    listed = {d["criterion"]: d for d in sda.get("mission_scoring_deviations", [])}
    dev = []
    for k in sorted(set(team_soft) | set(a["soft"])):
        t, o = team_soft.get(k), a["soft"].get(k)
        if t != ({kk: vv for kk, vv in o.items() if kk in ("weight", "bad", "good")} if o else None):
            d = listed.get(k)
            dev.append({"criterion": k, "team": t, "corrected": o, "listed": d is not None,
                        "has_reason": bool(d and d.get("reason")), "has_source": bool(d and d.get("source"))})
    gates_team = {k: {kk: vv for kk, vv in v.items() if kk in ("min", "max", "exclude", "allow")} for k, v in ms["gates"].items()}
    res = {"corrected": a, "audited_morning": b,
           "weights_sum": {"corrected_soft": round(sum(v["weight"] for v in a["soft"].values()), 6),
                           "corrected_sim": round(sum(x["weight"] for x in a["sim"]["variables"]), 6),
                           "morning_soft": round(sum(v["weight"] for v in b["soft"].values()), 6)},
           "differences_corrected_vs_morning": diff, "soft_deviations_from_mission_scoring": dev,
           "unlisted_soft_deviations": [d["criterion"] for d in dev if not (d["listed"] and d["has_reason"] and d["has_source"])],
           "gates_equal_mission_scoring": a["gates"] == gates_team, "require_present_equal": a["require_present"] == ms["require_present"],
           "zone_unchanged": a["sim"]["zone"] == b["sim"]["zone"], "sim_variables_unchanged": a["sim"]["variables"] == b["sim"]["variables"]}
    R.jdump(res, "ra_solar_config.json")
    print(json.dumps({k: v for k, v in res.items() if k not in ("corrected", "audited_morning")}, indent=1, default=str))
    # ---------------- texts
    txt = []

    def walk(o, path, src):
        if isinstance(o, dict):
            for k, v in o.items():
                walk(v, path + "." + str(k), src)
        elif isinstance(o, list):
            for i, v in enumerate(o):
                walk(v, "%s[%d]" % (path, i), src)
        elif isinstance(o, str) and len(o) > 25:
            txt.append({"file": src, "path": path, "text": o, "numbers": re.findall(r"-?\d[\d,]*\.?\d*", o)})
    ms_b = json.load(open(os.path.join(bdir, "missions.json"), encoding="utf-8"))
    walk([x for x in ms_b["missions"] if x["id"] == "solar"][0], "missions.solar", "missions.json")
    sj = json.load(open(os.path.join(bdir, "similarity.json"), encoding="utf-8"))
    for k, v in (sj.get("texts") or {}).items():
        if "solar" in k.lower() or (isinstance(v, dict) and "solar" in json.dumps(v).lower()) or "panel" in json.dumps(v).lower():
            walk(v, "similarity.texts." + k, "similarity.json")
    for k, v in sj.items():
        if k != "texts" and "solar" in json.dumps(v).lower():
            walk(v, "similarity." + k, "similarity.json")
    for fn in ("explain.json", "variables.json"):
        j = json.load(open(os.path.join(bdir, fn), encoding="utf-8"))
        s = json.dumps(j)
        if isinstance(j, dict):
            for k, v in j.items():
                if "solar" in k.lower() or "solar" in json.dumps(v).lower() or "clear_frac" in json.dumps(v):
                    walk(v, fn + "." + k, fn)
    flags = re.compile(r"sun_elev|sun_low|low sun|maximum sun|Sun elevation|WorldClim|irradiance.*(weight|criterion)|\bbest\b|the most|highest irradiance|cloud|clear", re.I)
    for t in txt:
        t["flag_terms"] = sorted(set(m.group(0) for m in flags.finditer(t["text"])))
    R.jdump(txt, "ra_solar_texts.json")
    print("texts", len(txt), "flagged", sum(bool(t["flag_terms"]) for t in txt))


if __name__ == "__main__":
    main()
