"""Point 3, rounding detail: recompute the published similarity of every paired point from the
bundle's own scores s.<v> with the contract formula (sum in the order of
missions.json similarity.variables, Python round to 2 decimals) and compare with the stored value.

    python "tierra luna/audit/p2_contract_sum.py"      -> audit/out/p2_contract_sum.json
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from p2_common import BUNDLE, dump, jload, mission_bundle  # noqa: E402

out = {}
mj = {x["id"]: x for x in jload(os.path.join(BUNDLE, "missions.json"))["missions"]}
for mi in ("rover", "solar", "lunar_base"):
    base, eb, pr, ids = mission_bundle(mi)
    vs = [(v["variable"], v["weight"]) for v in mj[mi]["similarity"]["variables"]]
    paired = np.isfinite(eb["twin"]) & (eb["twin"] >= 0)
    bad, n = [], 0
    for i in np.flatnonzero(paired):
        num = den = 0.0
        for v, w in vs:
            s = eb[f"s.{v}"][i]
            if np.isfinite(s):
                num += w * s
                den += w
        sim = float(100.0 * num / den)   # Python float: Python round (np.float64 would round like numpy)
        n += 1
        if round(sim, 2) != eb["similarity"][i]:
            bad.append({"earth_id": int(ids[i]), "recomputed": sim, "stored": float(eb["similarity"][i])})
    out[mi] = {"paired": n, "different": len(bad), "examples": bad[:10]}
    print(mi, n, len(bad))
dump(out, "p2_contract_sum.json")
