"""Markdown tables for docs/VALIDATION.md, written from validation/out/*.csv to
validation/out/tables.md (so the numbers in the document can be regenerated and diffed).

    cd "tierra luna" && python validation/report_tables.py
"""
from __future__ import annotations

import os

import numpy as np
import pandas as pd

from common import MISSIONS, OUT

SHORT = {"slope_300m_deg:below_min": "slope < 0.5", "rough_300m_m:below_min": "rough < 5",
         "mask_fraction:below_min": "land < 30 %", "thermal_inertia_class:excluded": "class agua",
         "tmin_c:above_max": "tmin > 5 C", "lst_diurnal_amp_k:below_min": "amp < 15 K",
         "lst_diurnal_amp_k:missing": "amp missing", "irradiance_kwh_m2_day:below_min": "irr < 2.5",
         "elevation_m:below_min": "elev < 1", "elevation_m:missing": "elev missing",
         "slope_300m_deg:missing": "slope missing", "rough_300m_m:missing": "rough missing",
         "slope_deg:missing": "slope missing", "tmin_c:missing": "tmin missing"}


def md(df: pd.DataFrame) -> str:
    cols = list(df.columns)
    lines = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    for _, r in df.iterrows():
        lines.append("| " + " | ".join("" if (isinstance(v, float) and np.isnan(v)) else str(v) for v in r.values) + " |")
    return "\n".join(lines)


def site_cell(r) -> str:
    if not r["passes_funnel"]:
        rs = [SHORT.get(x.strip(), x.strip()) for x in str(r["funnel_reasons"]).split(";")]
        return "out: " + ", ".join(rs)
    if not isinstance(r["twin"], str) or not r["twin"]:
        kind = str(r["no_twin_reason"]).split(" (")[0].replace("no_cell_meets_", "no cell: ").replace("_", " ")
        return f"suit {r['suitability']:.1f}, no twin ({kind})"
    return f"suit {r['suitability']:.1f}, final {r['final']:.2f}, top {r['rank_top_pct']:.1f} %"


def main() -> None:
    out = []
    t = pd.read_csv(os.path.join(OUT, "m3_benchmark_sites.csv"))
    u = t[t["unverified"].isna()]
    rows = []
    for sid, g in u.groupby("id", sort=False):
        g = g.set_index("mission")
        r0 = g.iloc[0]
        rec = {"site": f"{sid} {r0['name']}", "cell": r0["cell"], "land": f"{r0['mask_fraction']:.2f}"}
        for m in MISSIONS:
            lab = g.loc[m, "label"]
            rec[m] = (f"[{lab}] " if isinstance(lab, str) and lab else "") + site_cell(g.loc[m])
        rows.append(rec)
    out.append("## Benchmark sites (usable)\n\n" + md(pd.DataFrame(rows)))
    ex = t[t["unverified"].notna() & (t["mission"] == "rover")][["id", "name", "unverified"]]
    out.append("## Benchmark sites left out\n\n" + md(ex))
    pr = pd.read_csv(os.path.join(OUT, "m3_precision_recall.csv"))
    out.append("## Precision and recall\n\n" + md(pr[pr["positives"] > 0].drop(columns=["recovered_negative_ids"])))
    for name in ("m4_sensitivity_weights.csv", "m4_sensitivity_thresholds.csv", "m4_sensitivity_tolerances.csv",
                 "m4_sensitivity_summary.csv", "m7_global.csv", "m8_improvements.csv", "m6_coordinates_summary.csv",
                 "m1_coverage_by_mission.csv", "m1_coverage_per_ranked_point.csv", "m2_validity_by_table.csv",
                 "m2_validity_by_kind.csv", "m5_reproduction.csv"):
        p = os.path.join(OUT, name)
        if os.path.exists(p):
            d = pd.read_csv(p)
            for c in d.columns:
                if d[c].dtype == float:
                    d[c] = d[c].round(3)
            out.append(f"## {name}\n\n" + md(d))
    with open(os.path.join(OUT, "tables.md"), "w", encoding="utf-8") as fh:
        fh.write("\n\n".join(out) + "\n")
    print("wrote validation/out/tables.md")


if __name__ == "__main__":
    main()
