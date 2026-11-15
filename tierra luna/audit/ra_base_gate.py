"""Re-audit Lunar base: the 15 K swing gate, own figures. Corrected set with and without the gate
(utility unchanged, 15-35 K), the head of the ranking without it, and the swings of the polar stations.
Run: python "tierra luna/audit/ra_base_gate.py" -> out/ra_base_gate.json"""
import copy, json, os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ra_base_common as R
import p5_common as C

raw = R.load_raw_earth().set_index("id")
rep = {}
for label, gmin in (("gate_15K", 15.0), ("no_gate", None), ("gate_10K", 10.0), ("gate_5K", 5.0)):
    P, _, _ = R.params_for_set("corrected")
    g = P["missions"][R.M]["gates"]
    if gmin is None:
        g.pop("lst_diurnal_amp_k")
    else:
        g["lst_diurnal_amp_k"] = {"min": gmin}
    T = C.load_tables(P); D = C.derived(T, P)
    r = C.run_mission(T, D, R.M, P)
    o = R.ranked_order(r)[:10]
    head = [{"rank": int(r["rank"][i]), "earth": int(r["pass_ids"][i]), "lat": float(raw.loc[int(r["pass_ids"][i]), "lat_deg"]),
             "lon": float(raw.loc[int(r["pass_ids"][i]), "lon_deg"]), "amp_k": float(raw.loc[int(r["pass_ids"][i]), "lst_diurnal_amp_k"]),
             "similarity": round(float(r["sim"][i]), 2), "final": float(r["final_pub"][i])} for i in o]
    pa = np.array([raw.loc[int(c), "lst_diurnal_amp_k"] for c in r["pass_ids"]])
    rep[label] = {"passed": int(r["passed"].sum()), "paired": int((r["twin"] >= 0).sum()),
                  "share_passing_below_15K": round(float((pa < 15).mean()), 3), "median_amp_passing": round(float(np.nanmedian(pa)), 2),
                  "head": head}
    print(label, rep[label]["passed"], rep[label]["paired"], rep[label]["share_passing_below_15K"], rep[label]["median_amp_passing"])
    for h in head[:5]:
        print("   ", h)
st = {"Haughton E5130": 5130, "Svalbard E3793": 3793, "Kangerlussuaq E8049": 8049, "Axel Heiberg E3689": 3689,
      "McMurdo E60462": 60462, "Concordia E59703": 59703, "Askja E8803": 8803}
rep["stations"] = {k: {"amp_k": (None if not np.isfinite(raw.loc[v, "lst_diurnal_amp_k"]) else round(float(raw.loc[v, "lst_diurnal_amp_k"]), 2)),
                       "amp_max_month_k": (None if not np.isfinite(raw.loc[v, "lst_diurnal_amp_max_k"]) else round(float(raw.loc[v, "lst_diurnal_amp_max_k"]), 2))}
                   for k, v in st.items()}
print(rep["stations"])
print(R.dump(rep, "ra_base_gate.json"))
