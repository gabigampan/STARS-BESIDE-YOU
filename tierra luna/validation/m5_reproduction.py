"""Metric 5: reproduction of the counts the team declared (solar 5,192, thermal 2,613,
both 1,986) on the legacy table and on the shipped dataset, recomputed twice: with the
team module (mission_scoring.evaluate, unchanged) and with this script's own gate code
(independent of both the team module and the engine).

Configurations (read, never written):
  committed  : mission_scoring.json at commit 618bc45 (git show; on_missing_gate 'keep'),
               the state the audit and the declared counts refer to;
  current    : mission_scoring.json in the working tree (on_missing_gate 'drop';
               lunar_base = an exact copy of thermal).
"""
from __future__ import annotations

import json
import os
import subprocess
from typing import Dict, List

import numpy as np
import pandas as pd

from common import LEGACY_CSV, MISSION_CONFIG, REPO, context, write_csv
import mission_scoring  # noqa: E402

DECLARED = {"solar": 5192, "thermal": 2613, "both": 1986}


def committed_config() -> Dict:
    txt = subprocess.run(["git", "-C", REPO, "show", "618bc45:tierra luna/mission_scoring.json"],
                         capture_output=True, text=True, check=True).stdout
    return json.loads(txt)


def own_gates(df: pd.DataFrame, cfg: Dict, mission: str, common: bool = True) -> np.ndarray:
    """Independent pass flags: common gates, require_present, mission gates; a missing
    value in a gate passes only when on_missing_gate is 'keep'."""
    keep = cfg.get("on_missing_gate", "drop") == "keep"
    m = cfg["missions"][mission]
    gates = dict(cfg.get("common_gates", {})) if common else {}
    gates.update(m.get("gates", {}))
    ok = np.ones(len(df), dtype=bool)
    for col in m.get("require_present", []):
        s = df[col]
        ok &= ~(s.isna() | s.astype(str).str.strip().str.lower().isin(["", "nan", "none"])).to_numpy()
    for col, g in gates.items():
        s = df[col]
        if "min" in g or "max" in g:
            v = pd.to_numeric(s, errors="coerce").to_numpy(float)
            miss = ~np.isfinite(v)
            p = np.ones(len(df), bool)
            if g.get("min") is not None:
                p &= v >= g["min"]
            if g.get("max") is not None:
                p &= v <= g["max"]
        else:
            t = s.astype(str).str.strip().str.lower().to_numpy()
            miss = s.isna().to_numpy() | (t == "nan") | (t == "")
            p = np.ones(len(df), bool)
            if g.get("exclude"):
                p &= ~np.isin(t, [x.lower() for x in g["exclude"]])
            if g.get("allow"):
                p &= np.isin(t, [x.lower() for x in g["allow"]])
        ok &= np.where(miss, keep, p)
    return ok


def counts(df: pd.DataFrame, cfg: Dict, thermal_key: str) -> Dict[str, Dict[str, int]]:
    res = mission_scoring.evaluate(df, ["solar", thermal_key], cfg)
    ts, tt = res["pass_solar"].to_numpy(bool), res[f"pass_{thermal_key}"].to_numpy(bool)
    os_, ot = own_gates(df, cfg, "solar"), own_gates(df, cfg, thermal_key)
    return {"team_module": {"solar": int(ts.sum()), "thermal": int(tt.sum()), "both": int((ts & tt).sum())},
            "own_code": {"solar": int(os_.sum()), "thermal": int(ot.sum()), "both": int((os_ & ot).sum())}}


def missing_effect(df: pd.DataFrame, cfg: Dict, mission: str) -> int:
    """Cells that pass only because a gated value is missing and the rule is 'keep'."""
    c2 = json.loads(json.dumps(cfg))
    c2["on_missing_gate"] = "drop"
    return int((own_gates(df, cfg, mission) & ~own_gates(df, c2, mission)).sum())


def run() -> Dict:
    legacy = pd.read_csv(LEGACY_CSV, low_memory=False)
    le = legacy[legacy["body"] == "EARTH"].reset_index(drop=True)
    com = committed_config()
    with open(MISSION_CONFIG, encoding="utf-8") as fh:
        cur = json.load(fh)
    rows = []
    out = {"declared": DECLARED, "legacy_earth_cells": int(len(le))}
    for label, cfg, tk in (("committed_618bc45", com, "thermal"), ("current", cur, "lunar_base")):
        r = counts(le, cfg, tk)
        for k, v in r.items():
            rows.append({"table": "legacy_2deg (output_py/earth_moon_harmonized_clean.csv, EARTH rows)", "config": label,
                         "on_missing_gate": cfg.get("on_missing_gate"), "method": k, **v})
        out[f"legacy_{label}"] = r
        out[f"legacy_{label}_kept_by_missing"] = {m: missing_effect(le, cfg, m) for m in ("solar", tk)}
    # shipped dataset: the engine's own pass flags and this script's recount on the engine's table
    c = context()
    earth = c["cells"]["EARTH"]
    ps, pt = c["results"]["solar"].earth_gates.passed, c["results"]["lunar_base"].earth_gates.passed
    rows.append({"table": "real_1deg (shipped)", "config": "current", "on_missing_gate": cur.get("on_missing_gate"),
                 "method": "engine", "solar": int(ps.sum()), "thermal": int(pt.sum()), "both": int((ps & pt).sum())})
    os_, ot = own_gates(earth, cur, "solar"), own_gates(earth, cur, "lunar_base")
    rows.append({"table": "real_1deg (shipped)", "config": "current", "on_missing_gate": cur.get("on_missing_gate"),
                 "method": "own_code", "solar": int(os_.sum()), "thermal": int(ot.sum()), "both": int((os_ & ot).sum())})
    os2, ot2 = own_gates(earth, com, "solar"), own_gates(earth, com, "thermal")
    rows.append({"table": "real_1deg (shipped)", "config": "committed_618bc45", "on_missing_gate": com.get("on_missing_gate"),
                 "method": "own_code", "solar": int(os2.sum()), "thermal": int(ot2.sum()), "both": int((os2 & ot2).sum())})
    t = pd.DataFrame(rows)
    write_csv(t, "m5_reproduction.csv")
    # why the shipped numbers differ: reasons among real land cells for each mission
    why = []
    for m in ("solar", "lunar_base"):
        res = c["results"][m]
        land = c["land"]
        from collections import Counter
        cnt = Counter()
        for i in np.flatnonzero(land & ~res.earth_gates.passed):
            for r in res.earth_gates.reasons[i]:
                cnt[r] += 1
        for r, n in sorted(cnt.items(), key=lambda kv: (-kv[1], kv[0])):
            why.append({"mission": m, "reason": r, "land_cells_failing": n})
    write_csv(pd.DataFrame(why), "m5_shipped_failure_reasons.csv")
    # the two thermal gates on each table, over its land cells (legacy: elevation_m >= 1)
    lland = pd.to_numeric(le["elevation_m"], errors="coerce").to_numpy(float) >= 1
    gates = []
    for tab, df, lmask in (("legacy_2deg", le, lland), ("real_1deg", earth, c["land"])):
        amp = pd.to_numeric(df["lst_diurnal_amp_k"], errors="coerce").to_numpy(float)[lmask]
        tmin = pd.to_numeric(df["tmin_c"], errors="coerce").to_numpy(float)[lmask]
        irr = pd.to_numeric(df["irradiance_kwh_m2_day"], errors="coerce").to_numpy(float)[lmask]
        n = int(lmask.sum())
        gates.append({"table": tab, "land_cells": n,
                      "amp_ge_15_pct": round(100 * float(np.sum(amp >= 15)) / n, 2),
                      "amp_missing_pct": round(100 * float(np.sum(~np.isfinite(amp))) / n, 2),
                      "amp_min": float(np.nanmin(amp)), "amp_max": float(np.nanmax(amp)),
                      "tmin_le_5_pct": round(100 * float(np.sum(tmin <= 5)) / n, 2),
                      "irr_ge_2_5_pct": round(100 * float(np.sum(irr >= 2.5)) / n, 2)})
    write_csv(pd.DataFrame(gates), "m5_gate_shares.csv")
    out["gate_shares"] = gates
    out["table"] = t.to_dict("records")
    out["legacy_grid"] = {"rows": 90, "cols": 180, "cell_deg": 2.0}
    out["shipped_land_cells"] = int(c["land"].sum())
    out["legacy_land_cells_elevation_ge_1"] = int((pd.to_numeric(le["elevation_m"], errors="coerce") >= 1).sum())
    return out


if __name__ == "__main__":
    print(json.dumps(run(), indent=1, default=str))
