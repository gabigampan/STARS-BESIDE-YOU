"""w6: the common gate elevation_m >= 1 (question 6), not applied. Option: replace it by
'elevation_m has a value'. All three missions recomputed (Lunar base compares Earth percentiles
within the passing population, so its Earth population changes too).

    python "tierra luna/audit/w6_gate_elev.py"

Writes audit/out/w6_gate_elev.json.
"""
import copy
import numpy as np
from w_common import MISSIONS, base_run, compare_tracks, dump, load, row, ranked, run, summary
import p2_model


def main():
    eng, ms, e, m = load()
    orig_gates = p2_model.gates_earth
    ms2 = copy.deepcopy(ms)
    g = ms2["common_gates"]["elevation_m"]
    g["min"] = -np.inf          # 'has a value' (np.isfinite stays in the rule)

    def gate_fn(e_, mission, ms_):
        return orig_gates(e_, mission, ms2)

    el = p2_model.num(e, "elevation_m")
    mf = p2_model.num(e, "mask_fraction")
    out = {"land_cells_elev_below_1": int(((np.nan_to_num(mf) > 0) & np.isfinite(el) & (el < 1)).sum()),
           "of_which_mask_ge_0.3": int(((np.nan_to_num(mf) >= 0.3) & np.isfinite(el) & (el < 1)).sum())}
    print(out)
    for mi in MISSIONS:
        r0 = base_run(mi)
        r1 = run(mi, gate_fn=gate_fn)
        new = np.setdiff1d(r1["ids"], r0["ids"])
        idx = np.searchsorted(r1["ids"], new)
        got = idx[r1["twin"][idx] >= 0]
        s1 = summary(r1)
        s1["tracks"], s1["tracks_broken"] = compare_tracks(mi, s1["top"], r1)
        o50 = ranked(r1)[:50]
        new_in_50 = [row(r1, i) for i in o50 if r1["ids"][i] in set(new.tolist())]
        best_new = sorted([int(r1["rank"][i]) for i in got])[:5]
        # did the old cells' ranks/twins in the top 50 change?
        top50_old = [(row(r0, i)["earth_id"], row(r0, i)["moon_id"]) for i in ranked(r0)[:50]]
        top50_new = [(row(r1, i)["earth_id"], row(r1, i)["moon_id"]) for i in o50]
        out[mi] = {"passing_now": int(len(r0["ids"])), "passing_option": s1["passing"], "extra_passing": int(len(new)),
                   "extra_paired": int(len(got)), "paired_option": s1["paired"], "distinct_twins_option": s1["distinct_twins"],
                   "best_ranks_of_new": best_new, "new_in_top50": new_in_50, "top50_identical": top50_old == top50_new,
                   "top5": s1["top"], "tracks_broken": s1["tracks_broken"]}
        print(mi, {k: v for k, v in out[mi].items() if k not in ("top5",)})
    dump(out, "w6_gate_elev.json")


if __name__ == "__main__":
    main()
