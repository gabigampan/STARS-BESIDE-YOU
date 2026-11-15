"""Re-audit Lunar base, item 5: each suitability weight and each similarity weight x0.9 and x1.1
(renormalised to the original sum), one at a time; for each of the five, in how many perturbations
it stays among the five (by the set's own rule) and keeps its twin.
Run: python "tierra luna/audit/ra_base_robustness.py" [set ...]  -> out/ra_base_robustness.json"""
import copy, json, os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ra_base_common as R
import p5_common as C


def one_set(set_name, raw):
    P0, _, _ = R.params_for_set(set_name)
    T = C.load_tables(P0); D = C.derived(T, P0)
    r0 = C.run_mission(T, D, R.M, P0)
    five0 = R.select_five(r0, P0, T["EARTH"], raw)
    pos0 = {int(i): k for k, i in enumerate(r0["pass_ids"])}
    twin0 = {e: int(r0["twin"][pos0[e]]) for e in five0}
    runs = []
    soft = P0["missions"][R.M]["soft"]
    simv = P0["missions"][R.M]["sim"]["variables"]
    jobs = [("suit", v) for v in soft] + [("sim", x["variable"]) for x in simv]
    for kind, v in jobs:
        for f in (0.9, 1.1):
            P = copy.deepcopy(P0)
            if kind == "suit":
                s = P["missions"][R.M]["soft"]
                tot = sum(float(x["weight"]) for x in s.values())
                s[v]["weight"] = float(s[v]["weight"]) * f
                k = tot / sum(float(x["weight"]) for x in s.values())
                for x in s.values():
                    x["weight"] = float(x["weight"]) * k
            else:
                vs = P["missions"][R.M]["sim"]["variables"]
                tot = sum(float(x["weight"]) for x in vs)
                for x in vs:
                    if x["variable"] == v:
                        x["weight"] = float(x["weight"]) * f
                k = tot / sum(float(x["weight"]) for x in vs)
                for x in vs:
                    x["weight"] = float(x["weight"]) * k
            r = C.run_mission(T, D, R.M, P)
            five = R.select_five(r, P, T["EARTH"], raw)
            pos = {int(i): k2 for k2, i in enumerate(r["pass_ids"])}
            runs.append({"kind": kind, "variable": v, "factor": f, "five": five,
                         "rank_of_base_five": {e: int(r["rank"][pos[e]]) for e in five0},
                         "twin_kept": {e: int(r["twin"][pos[e]]) == twin0[e] for e in five0}})
    per = {e: {"in_five": sum(e in x["five"] for x in runs), "twin_kept": sum(x["twin_kept"][e] for x in runs),
               "both": sum((e in x["five"]) and x["twin_kept"][e] for x in runs), "of": len(runs),
               "worst_rank": max(x["rank_of_base_five"][e] for x in runs)} for e in five0}
    return {"five": five0, "twins": twin0, "n_perturbations": len(runs),
            "five_identical_in": sum(x["five"] == five0 for x in runs), "per_analog": per, "runs": runs}


def main():
    sets = sys.argv[1:] or ["corrected", "audited_morning"]
    raw = R.load_raw_earth()
    rep = {s: one_set(s, raw) for s in sets}
    for s in sets:
        print(s, rep[s]["five"], rep[s]["five_identical_in"], "/", rep[s]["n_perturbations"], json.dumps(rep[s]["per_analog"]))
    print(R.dump(rep, "ra_base_robustness.json"))


if __name__ == "__main__":
    main()
