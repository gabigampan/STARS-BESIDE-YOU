"""Concatenate the Earth and Moon real-data tables and count mission readiness.

    <venv>/bin/python -I real_data/build_combined.py

Inputs : output_real/earth_real_1deg.csv, output_real/moon_real_1deg.csv,
         mission_scoring.json (gates, soft criteria, workable_days), real_data/column_aliases.json
Outputs: output_real/earth_moon_real_1deg.csv  (team column order first, where names coincide)
         real_data/mission_readiness.json       (cells with every needed variable present, per mission and body)
Deterministic; no downloads. slope_300m_deg / rough_300m_m are NOT written (see column_aliases.json).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
OUT = ROOT / "output_real"

# Column order of the team's harmonised table (output_py/earth_moon_harmonized_clean.csv)
TEAM_ORDER = ["body", "row", "col", "x_m", "y_m", "lat_deg", "lon_deg", "resolution_m", "source", "elevation_m",
              "elevation_rel_m", "slope_deg", "roughness_m", "temp_k", "rock_or_bare_frac", "sar_sigma0_db",
              "mask_fraction", "slope_300m_deg", "rough_300m_m", "irradiance_kwh_m2_day", "sun_elev_max_deg",
              "sun_low_frac_0_5deg", "lst_diurnal_amp_k", "thermal_inertia_class", "permafrost_class",
              "rain_mm_day", "wind_max_ms", "tmin_c"]
NOT_WRITTEN = {"slope_300m_deg", "rough_300m_m"}


def read(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, keep_default_na=False, na_values=[""], low_memory=False)


def present(series: pd.Series) -> pd.Series:
    if series.dtype == object or str(series.dtype).startswith("str"):
        return series.notna() & (series.astype(str).str.len() > 0)
    return series.notna()


def main() -> int:
    earth = read(OUT / "earth_real_1deg.csv")
    moon = read(OUT / "moon_real_1deg.csv")
    lead = [c for c in TEAM_ORDER if (c in earth.columns or c in moon.columns) and c not in NOT_WRITTEN]
    lead += ["cell_id", "cell_km"]
    rest = [c for c in earth.columns if c not in lead] + [c for c in moon.columns if c not in lead and c not in earth.columns]
    both = pd.concat([earth, moon], ignore_index=True)[lead + rest]
    both.to_csv(OUT / "earth_moon_real_1deg.csv", index=False, na_rep="", float_format="%.6g")

    ms = json.loads((ROOT / "mission_scoring.json").read_text())
    aliases = json.loads((HERE / "column_aliases.json").read_text())
    common = list(ms.get("common_gates", {}))
    report = {"_note": ("Cells where every variable a mission needs is present (non-empty). 'needed' = common gates + "
                        "require_present + gates + soft criteria, mission names mapped to real columns with "
                        "column_aliases.json. 'with_workable_days' also needs rain_mm_day, wind_max_ms and tmin_c "
                        "(rover workable_days). 'soft_defaults_allowed' does not require soft criteria that have a 'default' "
                        "utility in mission_scoring.json (e.g. permafrost_class in the thermal mission). Earth counts are over land cells (mask_fraction > 0); Moon over all "
                        "cells. 'pass_gates' applies min/max/exclude gates literally (on_missing_gate = drop), "
                        "for information only: the engine's own implementation decides."),
              "earth_land_cells": int((earth.mask_fraction > 0).sum()), "moon_cells": int(len(moon)), "missions": {}}
    for mission, spec in ms["missions"].items():
        needed = list(dict.fromkeys(common + spec.get("require_present", []) + list(spec.get("gates", {}))
                                    + list(spec.get("soft", {}))))
        extra = []
        if "workable_days" in spec:
            extra = [v for v in ("rain_mm_day", "wind_max_ms", "tmin_c") if v not in needed]
        rec = {"needed_mission_names": needed, "workable_days_extra": extra}
        for body, df, key in (("EARTH", earth, "EARTH"), ("MOON", moon, "MOON")):
            base = (df.mask_fraction > 0) if body == "EARTH" else pd.Series(True, index=df.index)
            colmap = {v: aliases[key].get(v, {}).get("column", v) for v in needed + extra}
            ok = base.copy()
            missing_by_var = {}
            for v in needed:
                c = colmap[v]
                p = present(df[c]) if c in df.columns else pd.Series(False, index=df.index)
                missing_by_var[f"{v}->{c}"] = int((base & ~p).sum())
                ok &= p
            # soft criteria that declare a 'default' utility tolerate a missing value in the engine's schema
            ok_def = base.copy()
            for v in needed:
                if "default" in spec.get("soft", {}).get(v, {}) and v not in spec.get("gates", {}) \
                        and v not in spec.get("require_present", []):
                    continue
                c = colmap[v]
                ok_def &= present(df[c]) if c in df.columns else False
            ok_wd = ok.copy()
            for v in extra:
                c = colmap[v]
                ok_wd &= present(df[c]) if c in df.columns else False
            # literal gate pass (information only)
            gate_ok = ok_def.copy()
            gates = dict(ms.get("common_gates", {}))
            gates.update(spec.get("gates", {}))
            for v, g in gates.items():
                c = colmap.get(v, v)
                if c not in df.columns:
                    gate_ok &= False
                    continue
                s = df[c]
                if "min" in g:
                    gate_ok &= pd.to_numeric(s, errors="coerce") >= g["min"]
                if "max" in g:
                    gate_ok &= pd.to_numeric(s, errors="coerce") <= g["max"]
                if "exclude" in g:
                    gate_ok &= present(s) & ~s.isin(g["exclude"])
            rec[body] = {"columns_used": colmap, "cells_all_needed_present": int(ok.sum()),
                         "cells_all_needed_present_with_workable_days": int(ok_wd.sum()),
                         "cells_present_soft_defaults_allowed": int(ok_def.sum()),
                         "cells_missing_each_variable": missing_by_var,
                         "cells_passing_all_gates_literal": int(gate_ok.sum())}
        report["missions"][mission] = rec
    (HERE / "mission_readiness.json").write_text(json.dumps(report, indent=1))
    for m, r in report["missions"].items():
        print(f"{m:8s} EARTH present {r['EARTH']['cells_all_needed_present']:6d} (+workable {r['EARTH']['cells_all_needed_present_with_workable_days']:6d}) "
              f"dflt {r['EARTH']['cells_present_soft_defaults_allowed']:6d} gates {r['EARTH']['cells_passing_all_gates_literal']:6d} | MOON present {r['MOON']['cells_all_needed_present']:6d} "
              f"(+workable {r['MOON']['cells_all_needed_present_with_workable_days']:6d}) dflt {r['MOON']['cells_present_soft_defaults_allowed']:6d} gates {r['MOON']['cells_passing_all_gates_literal']:6d}")
    print(f"wrote {OUT / 'earth_moon_real_1deg.csv'} rows={len(both)} cols={both.shape[1]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
