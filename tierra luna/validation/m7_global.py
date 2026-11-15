"""Metric 7: one summary figure per mission, a weighted combination of metrics 1-6.

It is a SUMMARY OF CHECKS, NOT A PROBABILITY OF BEING RIGHT. Each component is a
0-100 score read from the tables of metrics 1-6 (validation/out/); the weights are
stated and justified in docs/VALIDATION.md section 7. A component that cannot be
measured for a mission (no benchmark site documented for it) is left out and the other
weights are renormalised; the figure without it is marked.
"""
from __future__ import annotations

import json
import os
from typing import Dict

import pandas as pd

from common import MISSIONS, OUT, write_csv

WEIGHTS = {"external_agreement": 0.25, "coverage": 0.20, "stability": 0.20,
           "validity": 0.15, "coordinates": 0.15, "reproduction": 0.05}


def _r(name):
    return pd.read_csv(os.path.join(OUT, name))


def components() -> pd.DataFrame:
    cov = _r("m1_coverage_by_mission.csv").set_index("mission")
    val = _r("m2_validity_by_table.csv").set_index("table")
    pr = _r("m3_precision_recall.csv")
    sw, st, so = _r("m4_sensitivity_weights.csv"), _r("m4_sensitivity_thresholds.csv"), _r("m4_sensitivity_tolerances.csv")
    co = _r("m6_coordinates_summary.csv").set_index("mission")
    rep = _r("m5_reproduction.csv")
    leg = rep[rep["table"].str.startswith("legacy")]
    declared = {"solar": 5192, "thermal": 2613, "both": 1986}
    hits = sum(int(r[k] == v) for _, r in leg.iterrows() for k, v in declared.items())
    reproduction = 100.0 * hits / (3 * len(leg))
    rows = []
    for m in MISSIONS:
        tabs = ["earth_real_1deg.csv", "moon_real_1deg.csv", "earth_base.bin", f"earth_{m}.bin", "moon_base.bin"]
        n = sum(val.loc[t, "records"] for t in tabs)
        bad = sum(val.loc[t, "failing_records"] for t in tabs)
        # external agreement = mean recall at the top 25 % over every site list measured for the
        # mission: the team benchmark (metric 3, D1) and the dedicated list of metric 3b (m9:
        # rover_preset.py, validation_sites_solar.csv, validation_sites_lunar_base.csv; scope "all")
        g = pr[(pr["mission"] == m) & (pr["definition"] == "D1_top25")].iloc[0]
        recalls = [float(g["recall_pct"])] if g["positives"] > 0 else []
        if os.path.exists(os.path.join(OUT, "m9_precision_recall.csv")):
            p9 = _r("m9_precision_recall.csv")
            h = p9[(p9["mission"] == m) & (p9["threshold"] == "top25") & (p9["scope"] == "all")]
            recalls += [float(x) for x in h["recall_pct"].dropna()]
        ext = sum(recalls) / len(recalls) if recalls else None
        k = 50
        ov = pd.concat([sw[sw.mission == m].top50_overlap, st[st.mission == m].top50_overlap, so[so.mission == m].top50_overlap])
        c = co.loc[m]
        good = c["country_agrees_centre_polygon"] + c["country_agrees_polygon_touching_cell"] + c["antarctic_label_lat_ok"]
        coord = 100.0 * good / c["ranked_points_checked"] * (c["twin_feature_name_agrees"] / c["distinct_twins"])
        comp = {"coverage": cov.loc[m, "MEASURED_pct"] + cov.loc[m, "DERIVED_pct"],
                "validity": 100.0 * (n - bad) / n, "external_agreement": ext,
                "stability": 100.0 * ov.mean() / k, "coordinates": coord, "reproduction": reproduction}
        used = {kk: w for kk, w in WEIGHTS.items() if comp[kk] is not None}
        tot = sum(used.values())
        fig = sum(comp[kk] * w for kk, w in used.items()) / tot
        no_ext = {kk: w for kk, w in WEIGHTS.items() if kk != "external_agreement"}
        fig_no_ext = sum(comp[kk] * w for kk, w in no_ext.items()) / sum(no_ext.values())
        rows.append({"mission": m, **{kk: (round(v, 2) if v is not None else None) for kk, v in comp.items()},
                     "global_figure": round(fig, 1), "external_measured": ext is not None,
                     "global_without_external": round(fig_no_ext, 1),
                     "lowest_component": min((kk for kk in comp if comp[kk] is not None), key=lambda kk: comp[kk])})
    return pd.DataFrame(rows)


def run() -> Dict:
    df = components()
    write_csv(df, "m7_global.csv")
    return {"weights": WEIGHTS, "table": df.to_dict("records")}


if __name__ == "__main__":
    print(json.dumps(run(), indent=1, default=str))
