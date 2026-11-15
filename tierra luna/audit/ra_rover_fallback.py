"""ra_rover_fallback (item 3): build Rover with criteria set 'audited_morning' in my own code path and compare
cell by cell with the bundle of this morning (git show a493514:app/public/data/v2, extracted to a folder).
    python ra_rover_fallback.py <morning bundle folder>
Writes out/ra_rover_fallback.json."""
import json, os, sys, time
import numpy as np
import ra_rover_common as R

bdir = sys.argv[1]
t0 = time.time()
P = R.params("audited_morning"); T = R.tables(P); D = R.derived_rover(T, P)
r = R.run(T, D, P)
B = R.bundle_rover(bdir)
cmp = R.compare(r, B)
f_mine = R.five_ids(r, P)
f_b = [int(x) for x in B["mission"].get("top5", {}).get("ids", [])] if isinstance(B["mission"].get("top5"), dict) else None
order = np.argsort(np.where(np.isfinite(B["rank"]), B["rank"], 1e9))[:5]
f_b_rank = [int(B["ids"][k]) for k in order]
res = {"criteria": "audited_morning", "bundle": bdir, "compare": cmp, "five_mine": f_mine, "five_bundle_by_rank": f_b_rank,
       "five_bundle_missions_json": f_b, "five_equal": f_mine == f_b_rank, "n_paired_mine": int((r["rank"] > 0).sum()),
       "difference_table": R.diff_table(r), "seconds": round(time.time() - t0)}
json.dump(res, open(os.path.join(R.OUT, "ra_rover_fallback.json"), "w"), indent=1)
print(json.dumps(res, indent=1))
