"""Re-audit Solar panels, item 5: one-at-a-time weight perturbations (+/-10 %, renormalised to sum 1).

    python -I ra_solar_robustness.py <criteria set>

Every suitability weight and every similarity weight, x1.1 and x0.9, the others rescaled so the
weights of that block sum to 1. For each of the baseline five: in how many perturbations it stays
among the five (shipped rule) and keeps its twin. Writes out/ra_solar_robustness_<set>.json.
"""
import copy
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ra_solar_common as R  # noqa: E402


def renorm(ws, k, f):
    w = dict(ws)
    w[k] = w[k] * f
    s = sum(w.values())
    return {kk: v / s for kk, v in w.items()}


def main():
    set_name = sys.argv[1]
    P0, _, _, _ = R.load_params_set(set_name)
    cache = {}
    r0 = R.run(P0, cache=cache)
    k5 = R.five(r0, P0)
    base = [(int(r0["pass_ids"][q]), int(r0["twin"][q])) for q in k5]
    runs = []
    soft = P0["missions"]["solar"]["soft"]
    sw = {k: float(v["weight"]) for k, v in soft.items()}
    simv = P0["missions"]["solar"]["sim"]["variables"]
    mw = {x["variable"]: float(x["weight"]) for x in simv}
    for blk, ws in (("suitability", sw), ("similarity", mw)):
        for k in ws:
            for f in (1.1, 0.9):
                P = copy.deepcopy(P0)
                nw = renorm(ws, k, f)
                if blk == "suitability":
                    for kk, v in nw.items():
                        P["missions"]["solar"]["soft"][kk]["weight"] = v
                else:
                    for x in P["missions"]["solar"]["sim"]["variables"]:
                        x["weight"] = nw[x["variable"]]
                r = R.run(P, cache=cache)
                kk5 = R.five(r, P)
                f5 = [(int(r["pass_ids"][q]), int(r["twin"][q])) for q in kk5]
                tw = {int(i): int(t) for i, t in zip(r["pass_ids"], r["twin"])}
                rk = {int(i): int(t) for i, t in zip(r["pass_ids"], r["rank"])}
                runs.append({"block": blk, "weight": k, "factor": f, "five": f5,
                             "base_ranks": {"E%d" % e: rk.get(e) for e, _ in base},
                             "base_keeps_twin": {"E%d" % e: tw.get(e) == t for e, t in base}})
                print(blk, k, f, [e for e, _ in f5])
    n = len(runs)
    per = {}
    for e, t in base:
        per["E%d" % e] = {"twin": "M%d" % t,
                          "in_five": sum(any(x[0] == e for x in rr["five"]) for rr in runs),
                          "keeps_twin": sum(rr["base_keeps_twin"]["E%d" % e] for rr in runs),
                          "in_five_with_same_twin": sum((e, t) in rr["five"] for rr in runs),
                          "worst_rank": max(rr["base_ranks"]["E%d" % e] or 10 ** 6 for rr in runs), "of": n}
    out = {"criteria_set": set_name, "baseline_five": [{"earth": "E%d" % e, "twin": "M%d" % t} for e, t in base],
           "perturbations": n, "per_analog": per, "five_identical": sum([x for x in rr["five"]] == base for rr in runs), "runs": runs}
    p = R.jdump(out, "ra_solar_robustness_%s.json" % set_name)
    print(per, "identical", out["five_identical"], "/", n)
    print("wrote", p)


if __name__ == "__main__":
    main()
