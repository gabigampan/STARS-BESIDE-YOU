"""Metric 1: data coverage by provenance level (MEASURED / DERIVED / MODELLED) and missing share.

Levels come from the team's provenance files (real_data/provenance_earth.csv and
provenance_moon.csv) for table columns, and from the engine's registry (the same files
read through engine/dataset.py with the column aliases) for mission variables. A level is
never inferred from a column name. Missing values stay missing and are counted apart.
"""
from __future__ import annotations

from typing import Dict, List

import numpy as np
import pandas as pd

from common import (LEVELS, MISSIONS, PROV_EARTH, PROV_MOON, context, pct, write_csv)

ID_COLUMNS = {"body", "row", "col", "cell_id", "lat_deg", "lon_deg", "id"}

# Level of each pairing variable per side: the provenance level of the quantity the
# engine compares (engine_config real_value_similarity.variables.<v>.sources).
PAIRING_LEVELS = {
    "slope_deg": {"EARTH": "DERIVED", "MOON": "DERIVED"},          # slope_iso_deg on both (column_overrides)
    "roughness_m": {"EARTH": "DERIVED", "MOON": "DERIVED"},
    "elevation_rel_m": {"EARTH": "DERIVED", "MOON": "DERIVED"},    # elevation_m minus body mean (DERIVED in engine_config)
    "irradiance_toa_kwh_m2_day": {"EARTH": "DERIVED", "MOON": "DERIVED"},  # Earth: latitude formula; Moon: lunar table irradiance
    "tmin_k": {"EARTH": "MODELLED", "MOON": "MEASURED"},           # Earth WorldClim tmin_c; Moon Diviner tmin_k (via tmin_c + 273.15)
    "lst_diurnal_amp_k": {"EARTH": "DERIVED", "MOON": "DERIVED"},
}


def provenance_levels(path: str) -> Dict[str, str]:
    """{column: level} from a provenance csv ('a / b / c' rows give every column the level)."""
    p = pd.read_csv(path)
    out: Dict[str, str] = {}
    for _, r in p.iterrows():
        lev = str(r["level"]).strip()
        if lev.lower() in ("", "nan"):
            continue
        lev = "NO_DATA" if lev.lower().startswith("no data") else lev.split()[0].upper()
        for v in str(r["variable"]).split("/"):
            out[v.strip()] = lev
    return out


def by_body_variable(c: Dict) -> pd.DataFrame:
    """One row per (body, column): level, population, present, missing share."""
    rows = []
    land = c["land"]
    tables = {"EARTH": (c["dataset"].cells["EARTH"], land, PROV_EARTH),
              "MOON": (c["dataset"].cells["MOON"], np.ones(len(c["cells"]["MOON"]), bool), PROV_MOON)}
    import os
    from common import REAL_DIR
    raw = {"EARTH": pd.read_csv(os.path.join(REAL_DIR, "earth_real_1deg.csv"), low_memory=False),
           "MOON": pd.read_csv(os.path.join(REAL_DIR, "moon_real_1deg.csv"), low_memory=False)}
    for body, (_, pop, prov_path) in tables.items():
        lv = provenance_levels(prov_path)
        df = raw[body]
        # population: Earth land cells as the engine defines them, every lunar cell
        ids = df["row"].to_numpy() * 360 + df["col"].to_numpy()
        popmask = pop[np.searchsorted(c["cells"][body]["id"].to_numpy(), ids)]
        for col in df.columns:
            if col in ID_COLUMNS:
                continue
            s = df.loc[popmask, col]
            txt = s.astype(str).str.strip().str.lower()
            present = int((s.notna() & ~txt.isin(["", "nan", "none"])).sum())
            n = int(popmask.sum())
            rows.append({"body": body, "column": col, "level": lv.get(col, "NOT_IN_PROVENANCE"),
                         "population": n, "present": present, "missing": n - present,
                         "missing_pct": pct(n - present, n)})
    return pd.DataFrame(rows)


def body_shares(t: pd.DataFrame) -> pd.DataFrame:
    """Share of all (cell x column) slots by level and missing, per body, over the value
    columns that carry a provenance level (bookkeeping columns such as pixel counts and
    cell_km are excluded: they describe the grid, not the ground)."""
    rows = []
    skip_prefix = ("n_", "cell_km", "temp_n_subcells", "illum_frac_level", "lst_diurnal_amp_max_month")
    for body, g in t.groupby("body"):
        g = g[~g["column"].str.startswith(skip_prefix)]
        g = g[g["level"].isin(LEVELS + ("NO_DATA",))]
        slots = int(g["population"].sum())
        rec = {"body": body, "columns": int(len(g)), "slots": slots}
        for lev in LEVELS:
            rec[f"{lev}_pct"] = pct(int(g.loc[g["level"] == lev, "present"].sum()), slots)
        rec["NO_DATA_columns"] = int((g["level"] == "NO_DATA").sum())
        rec["missing_pct"] = pct(int(g["missing"].sum()), slots)
        rows.append(rec)
    return pd.DataFrame(rows)


def mission_variables(c: Dict, m: str) -> Dict[str, List[str]]:
    mcfg = c["mission_cfg"]
    mm = mcfg["missions"][m]
    funnel = list(dict.fromkeys(list(mcfg.get("common_gates", {})) + list(mm.get("require_present", [])) +
                                list(mm.get("gates", {})) + list(mm.get("soft", {}))))
    pairing = [v["variable"] for v in c["engine_cfg"].v("real_value_similarity")["missions"][m]["variables"]]
    return {"funnel": funnel, "pairing": pairing}


def per_mission(c: Dict):
    from engine import provenance
    reg = c["registry"]
    earth = c["cells"]["EARTH"]
    summary, points_rows, var_rows = [], [], []
    for m in MISSIONS:
        res = c["results"][m]
        mv = mission_variables(c, m)
        ranked = np.flatnonzero(res.rank > 0)
        twin_pos = np.searchsorted(c["cells"]["MOON"]["id"].to_numpy(), res.twin_id[ranked])
        dv = res.extra["real"]["derived"].values
        # slots: (variable, side) -> (level, present mask over ranked points)
        slots = []
        for v in mv["funnel"]:
            lev = provenance.level(reg, v, "EARTH")
            s = earth[v]
            txt = s.astype(str).str.strip().str.lower()
            present = (s.notna() & ~txt.isin(["", "nan", "none"])).to_numpy()[ranked]
            slots.append((f"funnel:{v}:EARTH", lev, present))
        for v in mv["pairing"]:
            e = np.asarray(dv[v]["EARTH"], dtype=float)[ranked]
            mo = np.asarray(dv[v]["MOON"], dtype=float)[twin_pos]
            slots.append((f"pairing:{v}:EARTH", PAIRING_LEVELS[v]["EARTH"], np.isfinite(e)))
            slots.append((f"pairing:{v}:MOON", PAIRING_LEVELS[v]["MOON"], np.isfinite(mo)))
        n = len(ranked)
        tot = len(slots) * n
        rec = {"mission": m, "ranked_points": n, "slots_per_point": len(slots), "slots": tot}
        per_point = {lev: np.zeros(n) for lev in LEVELS + ("MISSING",)}
        for name, lev, present in slots:
            key = lev if lev in LEVELS else "MODELLED"
            per_point[key] += present
            per_point["MISSING"] += ~present
            var_rows.append({"mission": m, "slot": name, "level": lev, "ranked_points": n,
                             "present": int(present.sum()), "missing": int((~present).sum())})
        for lev in LEVELS + ("MISSING",):
            rec[f"{lev}_pct"] = pct(float(per_point[lev].sum()), tot)
        summary.append(rec)
        for lev in LEVELS + ("MISSING",):
            share = 100.0 * per_point[lev] / len(slots)
            q = np.percentile(share, [0, 10, 50, 90, 100]) if n else [np.nan] * 5
            points_rows.append({"mission": m, "level": lev, "min_pct": q[0], "p10_pct": q[1], "median_pct": q[2],
                                "p90_pct": q[3], "max_pct": q[4],
                                "points_with_any": int((per_point[lev] > 0).sum())})
    return pd.DataFrame(summary), pd.DataFrame(points_rows), pd.DataFrame(var_rows)


def run() -> Dict:
    c = context()
    t = by_body_variable(c)
    write_csv(t, "m1_coverage_by_body_variable.csv")
    b = body_shares(t)
    write_csv(b, "m1_coverage_by_body.csv")
    s, p, v = per_mission(c)
    write_csv(s, "m1_coverage_by_mission.csv")
    write_csv(p, "m1_coverage_per_ranked_point.csv")
    write_csv(v, "m1_coverage_mission_slots.csv")
    return {"by_body": b.to_dict("records"), "by_mission": s.to_dict("records"),
            "per_point": p.to_dict("records")}


if __name__ == "__main__":
    import json
    print(json.dumps(run(), indent=1, default=str))
