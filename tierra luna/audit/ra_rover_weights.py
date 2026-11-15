"""ra_rover_weights (item 5): each suitability weight and each similarity weight of Rover changed by +10 % and
-10 %, one at a time, the weights renormalised to their original sum; own code path (ra_rover_common).

    python ra_rover_weights.py [CRITERIA ...]     (default: corrected audited_morning)

For each perturbation: the five shown (rule of the set), and for each of the five of the unperturbed model whether
it stays among the five, keeps its twin, stays in the tied top group, and its rank. Writes out/ra_rover_weights.json.
"""
import json
import os
import sys

import numpy as np

import ra_rover_common as R

crits = sys.argv[1:] or ["corrected", "audited_morning"]
res = {}
for crit in crits:
    P = R.params(crit)
    T = R.tables(P)
    D = R.derived_rover(T, P)
    r0 = R.run(T, D, P)
    f0, _ = R.five(r0, P)
    ids0 = [int(r0["ids"][k]) for k in f0]
    tw0 = [int(r0["twin"][k]) for k in f0]
    S = R.sim_spec(P)
    soft = {k: float(v["weight"]) for k, v in P["missions"]["rover"]["soft"].items()}
    runs = []
    cases = []
    for name in soft:
        for f in (1.1, 0.9):
            w = dict(soft); w[name] *= f
            tot = sum(w.values()); w = {k: v * sum(soft.values()) / tot for k, v in w.items()}
            cases.append(("suitability", name, f, {"suit_weights": w}))
    for q, name in enumerate(S["names"]):
        for f in (1.1, 0.9):
            w = S["w"].copy(); w[q] *= f; w = w * S["w"].sum() / w.sum()
            cases.append(("similarity", name, f, {"weights": w}))
    for kind, name, f, kw in cases:
        r = R.run(T, D, P, **kw)
        fk, info = R.five(r, P)
        five = [int(r["ids"][k]) for k in fk]
        pos = {int(i): k for k, i in enumerate(r["ids"])}
        top = np.nanmax(r["final_pub"])
        per = []
        for i, t in zip(ids0, tw0):
            k = pos[i]
            per.append({"id": i, "in_five": i in five, "twin_kept": int(r["twin"][k]) == t, "rank": int(r["rank"][k]),
                        "tied_top": bool(r["final_pub"][k] == top)})
        runs.append({"kind": kind, "variable": name, "factor": f,
                     "weights": {k: round(float(v), 6) for k, v in (kw.get("suit_weights") or dict(zip(S["names"], kw["weights"]))).items()},
                     "five": five, "same_five": five == ids0, "n_tied_top": int((r["final_pub"] == top).sum()), "info": info, "per_analog": per})
    n = len(runs)
    res[crit] = {"base_five": ids0, "base_twins": tw0, "n_perturbations": n, "runs": runs,
                 "per_analog": [{"id": i, "stays_in_five": sum(rr["per_analog"][q]["in_five"] for rr in runs),
                                 "keeps_twin": sum(rr["per_analog"][q]["twin_kept"] for rr in runs),
                                 "stays_in_five_and_keeps_twin": sum(rr["per_analog"][q]["in_five"] and rr["per_analog"][q]["twin_kept"] for rr in runs),
                                 "stays_tied_top": sum(rr["per_analog"][q]["tied_top"] for rr in runs),
                                 "of": n} for q, i in enumerate(ids0)],
                 "same_five_count": sum(rr["same_five"] for rr in runs)}
    print(crit, json.dumps({k: v for k, v in res[crit].items() if k != "runs"}))
    for rr in runs:
        print("  ", rr["kind"], rr["variable"], rr["factor"], rr["five"], rr["n_tied_top"])
json.dump(res, open(os.path.join(R.OUT, "ra_rover_weights.json"), "w"), indent=1, default=str)
