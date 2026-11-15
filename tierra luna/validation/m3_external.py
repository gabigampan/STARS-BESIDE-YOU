"""Metric 3: external agreement with documented analog sites.

Sites: data/benchmark/analog_benchmark.csv (44 rows, each with its source URL). A site
is USABLE only when its coordinate is not flagged as unverified in that file (rule
UNVERIFIED below). Labels per mission come from keywords in the file's own columns
(rule LABELS below), never from memory. A site's cell is the 1-degree cell containing
its coordinate. Everything is read from the engine's own computation of the shipped
dataset (engine.build.compute), which equals the shipped bundle cell by cell (checked
in metric 2 for ranks, finals and twins).
"""
from __future__ import annotations

from typing import Dict, List

import numpy as np
import pandas as pd

from common import BENCHMARK, MISSIONS, cell_of, context, write_csv

DEFINITIONS = {
    "D1_top25": "passes the funnel, has a lunar twin, and ranks in the top 25 % of the mission's ranked list (main definition)",
    "D2_top10": "passes the funnel, has a twin, ranks in the top 10 %",
    "D3_top50": "passes the funnel, has a twin, ranks in the top 50 %",
    "D4_paired": "passes the funnel and has a twin (any rank)",
    "D5_funnel": "passes the funnel (twin and rank ignored)",
    "D6_suit25": "passes the funnel and its suitability is in the top 25 % of the funnel survivors (pairing ignored)",
}


def unverified(r: pd.Series) -> str:
    """Reason the coordinate is unverified, or '' (rule UNVERIFIED)."""
    cq, st = str(r["coord_quality"]).lower(), str(r["source_status"])
    if "from memory" in cq:
        return "coord_quality says 'from memory'"
    if st.upper().startswith("FROM MEMORY"):
        return "source_status is FROM MEMORY"
    if "location FROM MEMORY" in st:
        return "source_status: location FROM MEMORY"
    return ""


def labels(r: pd.Series) -> Dict[str, str]:
    """Rule LABELS: 'positive', 'negative', 'ambiguous' or '' per mission, from keywords.
    rover +: 'rover', 'mobility' or 'traverse' in analog_type, analog_property_for or tested_there;
    rover -: benchmark_role ops_only_exclude, or 'mobility'/'rover' in not_analog_for.
    lunar_base +: 'cold' in analog_type or analog_property_for; -: 'cold' in not_analog_for.
    solar +: 'solar', 'sun', 'illumination', 'irradiance' or 'power' anywhere in those columns."""
    pos_txt = " ".join(str(r[c]) for c in ("analog_type", "analog_property_for", "tested_there")).lower()
    neg_txt = str(r["not_analog_for"]).lower()
    out = {}
    rp = any(k in pos_txt for k in ("rover", "mobility", "traverse"))
    rn = r["benchmark_role"] == "ops_only_exclude" or any(k in neg_txt for k in ("mobility", "rover"))
    out["rover"] = "ambiguous" if rp and rn else ("positive" if rp else ("negative" if rn else ""))
    lp = "cold" in (str(r["analog_type"]) + " " + str(r["analog_property_for"])).lower()
    ln = "cold" in neg_txt
    out["lunar_base"] = "ambiguous" if lp and ln else ("positive" if lp else ("negative" if ln else ""))
    sp = any(k in pos_txt + " " + neg_txt for k in ("solar", " sun", "illumination", "irradiance", "power"))
    out["solar"] = "positive" if sp else ""
    return out


def site_table(c: Dict, sites: pd.DataFrame) -> pd.DataFrame:
    earth = c["cells"]["EARTH"]
    land = c["land"]
    rows = []
    for _, s in sites.iterrows():
        cid = cell_of(float(s["lat"]), float(s["lon"]))
        base = {"id": s["id"], "name": s["name"], "lat": s["lat"], "lon": s["lon"], "cell": f"E{cid}",
                "cell_lat": float(earth["lat_deg"].iat[cid]), "cell_lon": float(earth["lon_deg"].iat[cid]),
                "unverified": unverified(s), "source_url": s["source_url"], "land_cell": bool(land[cid]),
                "mask_fraction": earth["mask_fraction"].iat[cid], "elevation_m": earth["elevation_m"].iat[cid],
                "slope_deg": earth["slope_deg"].iat[cid], "roughness_m": earth["roughness_m"].iat[cid],
                "rock_or_bare_frac": earth["rock_or_bare_frac"].iat[cid], "tmin_c": earth["tmin_c"].iat[cid],
                "lst_diurnal_amp_k": earth["lst_diurnal_amp_k"].iat[cid],
                "irradiance_kwh_m2_day": earth["irradiance_kwh_m2_day"].iat[cid]}
        lab = labels(s)
        for m in MISSIONS:
            res = c["results"][m]
            passed = bool(res.earth_gates.passed[cid])
            n_rank = int((res.rank > 0).sum())
            sp = res.earth_suit.score
            passers = np.flatnonzero(res.earth_gates.passed)
            rec = dict(base, mission=m, label=lab[m], passes_funnel=passed,
                       funnel_reasons="; ".join(res.earth_gates.reasons[cid]) if not passed else "",
                       suitability=float(sp[cid]) if passed else np.nan,
                       suitability_top_pct=(100.0 * float((sp[passers] > sp[cid]).sum() + 1) / len(passers)) if passed else np.nan,
                       twin=f"M{int(res.twin_id[cid])}" if res.twin_id[cid] >= 0 else "",
                       similarity=float(res.similarity_pct[cid]) if res.twin_id[cid] >= 0 else np.nan,
                       final=float(res.final_published[cid]) if res.rank[cid] > 0 else np.nan,
                       rank=int(res.rank[cid]) if res.rank[cid] > 0 else np.nan, ranked_total=n_rank,
                       rank_top_pct=100.0 * int(res.rank[cid]) / n_rank if res.rank[cid] > 0 else np.nan)
            nk = res.extra["real"]["nopair_kind"][cid]
            kinds = res.extra["real"].get("nopair_kinds") or ["key_value_missing_on_earth", "no_zone_cell_within_bound", "no_joint_match"]
            if passed and res.twin_id[cid] < 0 and nk >= 0:
                var = res.extra["real"]["nopair_var"][cid]
                rec["no_twin_reason"] = f"{kinds[nk]} ({res.sim_vars[var] if var >= 0 else '-'}, gap {res.extra['real']['nopair_gap'][cid]:.3g})"
            else:
                rec["no_twin_reason"] = ""
            rows.append(rec)
    return pd.DataFrame(rows)


def recovered(t: pd.DataFrame, d: str) -> pd.Series:
    p, tw = t["passes_funnel"], t["twin"] != ""
    rk = t["rank_top_pct"]
    if d == "D1_top25":
        return p & tw & (rk <= 25)
    if d == "D2_top10":
        return p & tw & (rk <= 10)
    if d == "D3_top50":
        return p & tw & (rk <= 50)
    if d == "D4_paired":
        return p & tw
    if d == "D5_funnel":
        return p
    if d == "D6_suit25":
        return p & (t["suitability_top_pct"] <= 25)
    raise KeyError(d)


def precision_recall(t: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for m in MISSIONS:
        g = t[(t["mission"] == m) & (t["unverified"] == "")]
        pos, neg = g[g["label"] == "positive"], g[g["label"] == "negative"]
        for d in DEFINITIONS:
            rp, rn = recovered(pos, d), recovered(neg, d)
            tp, fp = int(rp.sum()), int(rn.sum())
            rows.append({"mission": m, "definition": d, "positives": len(pos), "negatives": len(neg),
                         "recovered_positives": tp, "recovered_negatives": fp,
                         "recall_pct": round(100.0 * tp / len(pos), 1) if len(pos) else np.nan,
                         "precision_pct": round(100.0 * tp / (tp + fp), 1) if (tp + fp) else np.nan,
                         "negatives_rejected_pct": round(100.0 * (len(neg) - fp) / len(neg), 1) if len(neg) else np.nan,
                         "recovered_positive_ids": " ".join(pos.loc[rp, "id"]), "recovered_negative_ids": " ".join(neg.loc[rn, "id"])})
    return pd.DataFrame(rows)


def rover_preset_check(c: Dict, t: pd.DataFrame) -> pd.DataFrame:
    """rover_preset.validate_rover_ranking on the shipped rover result, as it is."""
    import rover_preset
    g = t[t["mission"] == "rover"].set_index("name")
    out = []
    for score_col in ("final", "suitability"):
        for scope in ("all_named_sites", "verified_coordinates_only"):
            sc = {}
            for name, r in g.iterrows():
                if scope == "verified_coordinates_only" and r["unverified"]:
                    continue
                v = r[score_col]
                sc[name] = None if not np.isfinite(v) else float(v)
            rep = rover_preset.validate_rover_ranking(sc)
            for kind in ("positives", "mismatches"):
                for site, (v, p) in rep[kind].items():
                    hit = [n for n in g.index if site.lower().replace("-", " ") in n.lower().replace("-", " ")]
                    r = g.loc[hit[0]] if hit else None
                    out.append({"score": score_col, "scope": scope, "role": kind, "site": site,
                                "benchmark_id": r["id"] if r is not None else "", "cell": r["cell"] if r is not None else "",
                                "unverified": r["unverified"] if r is not None else "",
                                "score_value": v, "percentile_among_sites": p,
                                "passes_funnel": r["passes_funnel"] if r is not None else "",
                                "funnel_reasons": r["funnel_reasons"] if r is not None else "",
                                "twin": r["twin"] if r is not None else "", "no_twin_reason": r["no_twin_reason"] if r is not None else "",
                                "slope_deg": r["slope_deg"] if r is not None else np.nan,
                                "roughness_m": r["roughness_m"] if r is not None else np.nan,
                                "rock_or_bare_frac": r["rock_or_bare_frac"] if r is not None else np.nan,
                                "median_positive": rep["median_positive"], "ok": rep["ok"], "problems": " | ".join(rep["problems"])})
    return pd.DataFrame(out)


def run() -> Dict:
    c = context()
    sites = pd.read_csv(BENCHMARK)
    t = site_table(c, sites)
    write_csv(t, "m3_benchmark_sites.csv")
    pr = precision_recall(t)
    write_csv(pr, "m3_precision_recall.csv")
    rv = rover_preset_check(c, t)
    write_csv(rv, "m3_rover_preset_check.csv")
    usable = t[(t["mission"] == "rover") & (t["unverified"] == "")]
    lab = t[t["unverified"] == ""].groupby(["mission", "label"]).size().reset_index(name="sites")
    return {"sites_total": int(len(sites)), "usable": int(len(usable)),
            "excluded": t.loc[(t["mission"] == "rover") & (t["unverified"] != ""), ["id", "unverified"]].to_dict("records"),
            "labels": lab.to_dict("records"), "precision_recall": pr.drop(columns=["recovered_positive_ids", "recovered_negative_ids"]).to_dict("records"),
            "rover_preset": rv.groupby(["score", "scope"]).agg(ok=("ok", "first"), problems=("problems", "first")).reset_index().to_dict("records"),
            "definitions": DEFINITIONS}


if __name__ == "__main__":
    import json
    print(json.dumps(run(), indent=1, default=str))
