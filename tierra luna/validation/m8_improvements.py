"""Metric 8: improvements the measurements suggest, each with its effect measured in
memory. Proposals that would change a team threshold, weight or tolerance are marked
TEAM SETTING (proposal only, for the team lead); the others change no team setting.
Nothing here is applied to the project.
"""
from __future__ import annotations

import copy
import json
import os
from typing import Dict, List

import numpy as np
import pandas as pd

from common import BENCHMARK, MISSIONS, OUT, context, run_mission_variant, write_csv
from m3_external import precision_recall, rover_preset_check, site_table


def bench(c: Dict, mission: str, new_res=None, include_unverified: bool = False) -> Dict:
    """Benchmark result of one mission (D1 main definition and the rover_preset check)."""
    c2 = dict(c)
    c2["results"] = dict(c["results"])
    if new_res is not None:
        c2["results"][mission] = new_res
    sites = pd.read_csv(BENCHMARK)
    t = site_table(c2, sites)
    if include_unverified:
        t = t.assign(unverified="")
    pr = precision_recall(t)
    g = pr[(pr["mission"] == mission) & (pr["definition"] == "D1_top25")].iloc[0]
    out = {"recall_D1": g["recall_pct"], "precision_D1": g["precision_pct"],
           "recovered_pos": g["recovered_positive_ids"], "recovered_neg": g["recovered_negative_ids"]}
    if mission == "rover":
        rv = rover_preset_check(c2, t)
        x = rv[(rv["score"] == "final") & (rv["scope"] == "verified_coordinates_only")].iloc[0]
        out["rover_preset_ok"] = bool(x["ok"])
        out["rover_preset_problems"] = x["problems"]
    return out


def summary(base, new) -> Dict:
    bp, np_ = base.earth_gates.passed, new.earth_gates.passed
    bt, nt = base.twin_id >= 0, new.twin_id >= 0
    return {"funnel_pass": f"{int(bp.sum())} -> {int(np_.sum())}", "pairs": f"{int(bt.sum())} -> {int(nt.sum())}",
            "cells_entering": int((np_ & ~bp).sum()), "pairs_gained": int((nt & ~bt).sum()), "pairs_lost": int((bt & ~nt).sum())}


def run() -> Dict:
    c = context()
    earth = c["cells"]["EARTH"]
    props: List[Dict] = []

    # P1 (TEAM SETTING): rover minimum slope 0.5 deg and roughness 5 m, written for a 300 m
    # baseline, removed (the data have 3.7 km slope and 1.85 km roughness baselines).
    mc = copy.deepcopy(c["mission_cfg"])
    mc["missions"]["rover"]["gates"]["slope_300m_deg"].pop("min")
    mc["missions"]["rover"]["gates"]["rough_300m_m"].pop("min")
    new = run_mission_variant(c, "rover", mission_cfg=mc)
    props.append({"id": "P1", "mission": "rover", "kind": "TEAM SETTING (threshold)",
                  "change": "drop the rover gates slope_300m_deg >= 0.5 and rough_300m_m >= 5 (keep the maxima)",
                  "why": "minimums written for a 300 m baseline; the table's slope is at 3.7 km and roughness at 1.85 km (column_aliases.json caveat); they remove Dhofar (AMADEE-18) and Concordia",
                  **summary(c["results"]["rover"], new), **{f"bench_{k}": v for k, v in bench(c, "rover", new).items()}})

    # P2 (TEAM SETTING): rover rock_or_bare_frac weight 0.25 -> 0 (renormalised)
    from engine.suitability import evaluate_suitability, round_like_export
    from engine.pipeline import rank_scores
    import mission_scoring
    base = c["results"]["rover"]
    w = {v: float(s["weight"]) for v, s in c["mission_cfg"]["missions"]["rover"]["soft"].items()}
    w["rock_or_bare_frac"] = 0.0
    es = evaluate_suitability(earth, "EARTH", "rover", c["mission_cfg"], c["engine_cfg"], weights=w)
    fin = mission_scoring.combine_with_similarity(pd.DataFrame({"similarity_pct": base.similarity_pct, "score_rover": es.score}),
                                                  "rover", alpha=base.alpha).to_numpy(float)
    fin = np.where(base.earth_gates.passed & (base.twin_id >= 0), fin, np.nan)
    new2 = copy.copy(base)
    new2.earth_suit = es
    new2.final_published = round_like_export(fin, 2)
    new2.rank = rank_scores(new2.final_published, earth["id"].to_numpy())
    b_ids = np.flatnonzero(base.rank > 0)
    top50b = set(b_ids[np.argsort(base.rank[b_ids])][:50])
    top50n = set(b_ids[np.argsort(new2.rank[b_ids])][:50])
    props.append({"id": "P2", "mission": "rover", "kind": "TEAM SETTING (weight)",
                  "change": "rover soft weight of rock_or_bare_frac 0.25 -> 0 (slope and roughness renormalised to 0.6 / 0.4)",
                  "why": "a 1-degree land-cover share is near 0 at Bardenas (0.018), Tabernas, Death Valley: the cell is mostly vegetated even where the test site is bare",
                  "funnel_pass": "unchanged", "pairs": "unchanged", "top50_overlap_with_base": len(top50b & top50n),
                  **{f"bench_{k}": v for k, v in bench(c, "rover", new2).items()}})

    # P3 (no team setting): Earth cells with a negative MODIS day-minus-night amplitude
    amp = pd.to_numeric(earth["lst_diurnal_amp_k"], errors="coerce").to_numpy(float)
    neg = np.isfinite(amp) & (amp < 0)
    rec = {"id": "P3", "mission": "solar, lunar_base", "kind": "no team setting (data validity flag)",
           "change": "mark lst_diurnal_amp_k < 0 as invalid (missing) on Earth, as the schema of section 2 does",
           "why": f"{int(neg.sum())} Earth cells have a negative amplitude (min {np.nanmin(amp):.2f} K); an amplitude below 0 is not physical for this variable's use as a thermal-cycling stress"}
    for m in ("solar", "lunar_base"):
        r = c["results"][m]
        rec[f"{m}_passing_with_negative_amp"] = int((neg & r.earth_gates.passed).sum())
        rec[f"{m}_ranked_with_negative_amp"] = int((neg & (r.rank > 0)).sum())
    props.append(rec)

    # P4 (no team setting): the one Earth cell below the lowest dry land
    elev = pd.to_numeric(earth["elevation_m"], errors="coerce").to_numpy(float)
    low = np.flatnonzero(np.isfinite(elev) & (elev < -430))
    props.append({"id": "P4", "mission": "all", "kind": "no team setting (data validity flag)",
                  "change": "mark Earth elevation_m below -430 m as invalid",
                  "why": "cells " + ", ".join(f"E{int(earth['id'].iat[i])} ({elev[i]:.1f} m, land {earth['mask_fraction'].iat[i]:.4f})" for i in low),
                  **{f"{m}_passes": int(sum(c['results'][m].earth_gates.passed[i] for i in low)) for m in MISSIONS}})

    # P5 (no team setting): verify the 15 benchmark coordinates flagged as unverified
    for m in ("rover", "lunar_base"):
        a = bench(c, m)
        b = bench(c, m, include_unverified=True)
        props.append({"id": "P5", "mission": m, "kind": "no team setting (benchmark)",
                      "change": "verify the coordinates flagged FROM MEMORY in the benchmark so those sites can be counted",
                      "why": "15 of 44 sites are left out today; the effect below counts them as if their coordinates were confirmed (an upper bound of what verification can change)",
                      "bench_recall_D1_now": a["recall_D1"], "bench_precision_D1_now": a["precision_D1"],
                      "bench_recall_D1_if_verified": b["recall_D1"], "bench_precision_D1_if_verified": b["precision_D1"]})

    # P6 (TEAM SETTING): lunar_base amplitude gate 15 K vs the cold benchmark sites
    for f in (0.9, 0.0):
        mc = copy.deepcopy(c["mission_cfg"])
        for k in ("lunar_base", "thermal"):
            mc["missions"][k]["gates"]["lst_diurnal_amp_k"]["min"] = 15.0 * f
        new = run_mission_variant(c, "lunar_base", mission_cfg=mc)
        props.append({"id": "P6", "mission": "lunar_base", "kind": "TEAM SETTING (threshold)",
                      "change": f"lunar_base gate lst_diurnal_amp_k >= {15.0 * f:g} K (today 15 K)",
                      "why": "every cold benchmark site fails this gate or has no amplitude; the Earth amplitude is MODIS 10:30 minus 22:30, which understates the daily range (column_aliases.json caveat)",
                      **summary(c["results"]["lunar_base"], new), **{f"bench_{k}": v for k, v in bench(c, "lunar_base", new).items()}})

    # P7, P8 (TEAM SETTING): tolerance changes read from metric 4 (not recomputed here)
    p = os.path.join(OUT, "m4_sensitivity_tolerances.csv")
    if os.path.exists(p):
        tol = pd.read_csv(p)
        for m, var in (("lunar_base", "tmin_k"), ("lunar_base", "lst_diurnal_amp_k"), ("solar", "irradiance_toa_kwh_m2_day")):
            g = tol[(tol.mission == m) & (tol.variable == var) & (tol.factor == 1.2)]
            if len(g):
                g = g.iloc[0]
                props.append({"id": "P7" if m == "lunar_base" else "P8", "mission": m, "kind": "TEAM SETTING (tolerance)",
                              "change": f"{var} tolerance x1.2 ({g.value_from:g} -> {g.value_to:g})",
                              "why": "share of passing points with a twin is low (lunar_base 18.6 %, solar 33.9 %); effect taken from metric 4",
                              "pairs": f"{int(g.pairs_base)} -> {int(g.pairs_new)}", "pairs_gained": int(g.pairs_gained),
                              "pairs_lost": int(g.pairs_lost), "number1_same": bool(g.number1_same)})
    df = pd.DataFrame(props)
    write_csv(df, "m8_improvements.csv")
    return {"proposals": df.to_dict("records")}


if __name__ == "__main__":
    print(json.dumps(run(), indent=1, default=str))
