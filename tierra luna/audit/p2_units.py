"""Point E (units, scales, formulas; saturation) and the team lead's table of differences.

    python "tierra luna/audit/p2_units.py"

Reads the tables, the configuration and the bundle (own decoder); the per-cell zone scans
use the auditor's own implementation (p2_model). Writes audit/out/p2_units.json and
audit/out/p2_table.csv. Deterministic; no network.
"""
from __future__ import annotations

import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from p2_common import OUT, configs, dump, mission_bundle, qtl, read_bin, tables  # noqa: E402
import p2_model  # noqa: E402

MISSIONS = ["rover", "solar", "lunar_base"]


def share(a, cond):
    a = a[np.isfinite(a)]
    return float(np.mean(cond(a))) if a.size else None


def main():
    eng, ms = configs()
    e, m = tables()
    out = {"saturation": {}, "units": {}, "table": []}
    rows = []
    ev, mv, notes = p2_model.derived(e, m, eng)
    zmask, _ = p2_model.zones(m, eng)
    for mi in MISSIONS:
        base, eb, pr, pass_ids = mission_bundle(mi)
        sp = p2_model.spec(eng, mi)
        paired = np.isfinite(eb["twin"]) & (eb["twin"] >= 0)
        sim2 = eb["similarity"][paired]
        rec = pd.read_csv(os.path.join(OUT, f"p2_pairs_{mi}.csv"))
        simf = rec["similarity_recomputed"].to_numpy()[paired]   # from 6-dp scores, unrounded
        sat = {"paired": int(paired.sum()), "quantiles_published": qtl(sim2, (0, 0.01, 0.1, 0.25, 0.5, 0.75, 0.9, 0.99, 1.0)),
               "share_ge_99": share(sim2, lambda a: a >= 99), "share_ge_99.9": share(sim2, lambda a: a >= 99.9),
               "share_ge_99.99": share(sim2, lambda a: a >= 99.99), "share_published_100.00": share(sim2, lambda a: a >= 100.0),
               "share_display_100.0_one_decimal": share(simf, lambda a: a >= 99.95),
               "share_display_100_integer": share(simf, lambda a: a >= 99.5),
               "count_ge_99": int(np.sum(sim2 >= 99)), "count_published_100.00": int(np.sum(sim2 >= 100.0)),
               "distinct_values_published_2dp": int(np.unique(sim2).size),
               "distinct_values_full_from_scores": int(np.unique(np.round(simf, 9)).size)}
        # real difference for a similarity of 99 / 99.9 / 99.99 (a) when only this variable differs,
        # (b) when every variable is at the same fraction r of its tolerance
        eq = {}
        for S in (99.0, 99.9, 99.99):
            r_all = float(np.sqrt(-2 * np.log(S / 100)))
            per = {}
            for q, v in enumerate(sp["vars"]):
                loss = (100 - S) / 100 / sp["w"][q]
                d_alone = float(sp["tau"][q] * np.sqrt(-2 * np.log(1 - loss))) if loss < 1 else None
                per[v] = {"only_this_variable_differs": d_alone, "all_variables_equal_fraction": r_all * float(sp["tau"][q]),
                          "unit": "percentile points" if sp["scale"][q] != "real" else {"slope_deg": "deg", "roughness_m": "m",
                                                                                        "elevation_rel_m": "m"}.get(v, "kWh/m2/day")}
            eq[f"S={S}"] = {"fraction_of_tolerance_when_equal": r_all, "per_variable": per}
        sat["real_difference_for_similarity"] = eq
        # selection effect: how many zone cells pass and how many of them score >= 99, per paired point
        zi = np.flatnonzero(zmask[mi])
        E = np.column_stack([ev[v] for v in sp["vars"]])
        Mz = np.column_stack([mv[v] for v in sp["vars"]])[zi]
        ids = pass_ids
        Ec = E[ids].copy()
        for q, sc in enumerate(sp["scale"]):
            if sc != "real":
                Ec[:, q] = p2_model.midrank(E[ids, q])
                Mz[:, q] = p2_model.midrank(Mz[:, q])
        npass, n99, med_pass = [], [], []
        for i in np.flatnonzero(paired):
            d, ok, sim, s = p2_model.pair_matrix(Ec[i], Mz, sp)
            npass.append(int(ok.sum()))
            n99.append(int(np.sum(ok & (sim >= 99))))
            med_pass.append(float(np.median(sim[ok])))
        npass, n99, med_pass = np.array(npass), np.array(n99), np.array(med_pass)
        sat["selection_effect"] = {"zone_cells": int(zi.size), "zone_cells_passing_filter_per_point": qtl(npass, (0, 0.1, 0.5, 0.9, 1.0)),
                                   "zone_cells_passing_with_similarity_ge_99_per_point": qtl(n99, (0, 0.1, 0.5, 0.9, 1.0)),
                                   "share_points_with_ge_10_cells_at_99": float(np.mean(n99 >= 10)),
                                   "median_similarity_of_the_passing_cells_per_point": qtl(med_pass, (0.1, 0.5, 0.9)),
                                   "best_minus_second_full": qtl(rec["best_minus_second"].to_numpy()[paired], (0.1, 0.5, 0.9))}
        # rounding: ties on the published similarity and final
        fin2 = eb["final"][paired]
        finf = rec["final_recomputed"].to_numpy()[paired]
        sat["rounding"] = {"similarity_rows_in_tie_groups_published": int(np.sum(pd.Series(sim2).duplicated(keep=False))),
                           "similarity_rows_in_tie_groups_full": int(np.sum(pd.Series(np.round(simf, 9)).duplicated(keep=False))),
                           "final_rows_in_tie_groups_published": int(np.sum(pd.Series(fin2).duplicated(keep=False))),
                           "final_rows_in_tie_groups_full": int(np.sum(pd.Series(np.round(finf, 9)).duplicated(keep=False)))}
        # top-5 / rank-6 unrounded finals (does rounding decide the 5th place?)
        rk = eb["rank"]
        top = [int(np.flatnonzero(rk == k)[0]) for k in range(1, 7)]
        sat["top6_final_full"] = [{"rank": k + 1, "earth_id": int(ids[p]), "final_published": float(eb["final"][p]),
                                   "final_full": float(rec["final_recomputed"].iloc[p]),
                                   "similarity_full": float(rec["similarity_recomputed"].iloc[p]),
                                   "suitability_full": float(rec["suitability_recomputed"].iloc[p])} for k, p in enumerate(top)]
        out["saturation"][mi] = sat
        # ---- the table: differences on the surviving pairs
        for q, v in enumerate(sp["vars"]):
            dreal = pr[f"{v}.diff"][paired]
            unit = {"slope_deg": "deg", "roughness_m": "m", "elevation_rel_m": "m", "irradiance_toa_kwh_m2_day": "kWh/m2/day",
                    "tmin_k": "K", "lst_diurnal_amp_k": "K"}[v]
            if sp["scale"][q] != "real":
                dp = pr[f"{v}.diff_pct"][paired]
                rows.append([mi, v, sp["role"][q], "percentile points", sp["tau"][q], sp["bound"][q],
                             np.median(dp), np.quantile(dp, 0.9), dp.max()])
                rows.append([mi, v + " (real)", sp["role"][q], unit, None, None, np.median(dreal), np.quantile(dreal, 0.9), dreal.max()])
            else:
                rows.append([mi, v, sp["role"][q], unit, sp["tau"][q], sp["bound"][q], np.median(dreal), np.quantile(dreal, 0.9), dreal.max()])
        # ---- units checks
        u = {}
        if mi == "lunar_base":
            te, tm = pr["tmin_k.earth"][paired], pr["tmin_k.moon"][paired]
            ae, am = pr["lst_diurnal_amp_k.earth"][paired], pr["lst_diurnal_amp_k.moon"][paired]
            me, mm = pr["info.temp_k.earth"][paired], pr["info.temp_k.moon"][paired]
            pe = pass_ids[paired]
            u["tmin_k_earth_equals_tmin_c_plus_273.15_max_abs"] = float(np.max(np.abs(te - (pd.to_numeric(e["tmin_c"]).to_numpy()[pe] + 273.15))))
            tw = eb["twin"][paired].astype(int)
            u["tmin_k_moon_equals_lunar_tmin_k_column_max_abs"] = float(np.max(np.abs(tm - pd.to_numeric(m["tmin_k"]).to_numpy()[tw])))
            u["moon_colder_tmin_all_pairs"] = bool(np.all(tm < te))
            u["moon_colder_mean_all_pairs"] = bool(np.all(mm < me))
            u["moon_larger_swing_all_pairs"] = bool(np.all(am > ae))
            u["tmin_k_diff_median_K"] = float(np.median(te - tm))
            u["earth_tmin_c_range_pairs"] = [float(np.min(te - 273.15)), float(np.max(te - 273.15))]
            u["moon_tmin_k_range_pairs"] = [float(np.min(tm)), float(np.max(tm))]
            u["earth_amp_range_pairs_K"] = [float(np.min(ae)), float(np.max(ae))]
            u["moon_amp_range_pairs_K"] = [float(np.min(am)), float(np.max(am))]
            # what a change of population would do: Earth percentile among ALL land cells with a value
            allv = pd.to_numeric(e["tmin_c"], errors="coerce").to_numpy() + 273.15
            land = np.isfinite(allv)
            pct_all = p2_model.midrank(np.where(land, allv, np.nan))
            pct_pop = pr["tmin_k.earth_pct"][paired]
            u["earth_tmin_pct_if_population_were_all_land_cells"] = {"cells": int(land.sum()),
                                                                    "pairs_median_shift_points": float(np.median(pct_all[pe] - pct_pop)),
                                                                    "pairs_share_shift_gt_10_points": float(np.mean(np.abs(pct_all[pe] - pct_pop) > 10))}
            alla = pd.to_numeric(e["lst_diurnal_amp_k"], errors="coerce").to_numpy()
            pa_all = p2_model.midrank(alla)
            u["earth_amp_pct_if_population_were_all_land_cells"] = {"cells": int(np.isfinite(alla).sum()),
                                                                   "pairs_median_shift_points": float(np.median(pa_all[pe] - pr["lst_diurnal_amp_k.earth_pct"][paired])),
                                                                   "pairs_share_shift_gt_10_points": float(np.mean(np.abs(pa_all[pe] - pr["lst_diurnal_amp_k.earth_pct"][paired]) > 10))}
            # Moon percentile if the population were the whole south-pole zone (lat <= -75) instead of the 280 cells
            sp_zone = np.flatnonzero(zmask["rover"])
            mt = pd.to_numeric(m["tmin_c"]).to_numpy() + 273.15
            pz = p2_model.midrank(mt[sp_zone])
            pos = np.searchsorted(sp_zone, tw)
            u["moon_tmin_pct_if_population_were_lat_le_-75"] = {"cells": int(sp_zone.size),
                                                               "pairs_median_shift_points": float(np.median(pz[pos] - pr["tmin_k.moon_pct"][paired]))}
        if mi == "solar":
            toa_e = pr["irradiance_toa_kwh_m2_day.earth"][paired]
            toa_m = pr["irradiance_toa_kwh_m2_day.moon"][paired]
            g = pr["atm.ground_kwh_m2_day"][paired]
            u["earth_toa_range_pairs_kwh"] = [float(toa_e.min()), float(toa_e.max())]
            u["moon_irr_range_pairs_kwh"] = [float(toa_m.min()), float(toa_m.max())]
            u["earth_ground_range_pairs_kwh"] = [float(np.nanmin(g)), float(np.nanmax(g))]
            u["lost_share_median"] = float(np.nanmedian(pr["atm.lost_share"][paired]))
            u["lost_share_check_max_abs"] = float(np.nanmax(np.abs(pr["atm.lost_share"][paired] - (1 - g / pr["atm.toa_kwh_m2_day"][paired]))))
            # daily-mean W/m2 equivalents (x 1000 / 24) of the tolerance and the values
            u["tolerance_0.6_kwh_in_w_m2_daily_mean"] = 0.6 * 1000 / 24
            u["moon_equator_row_irradiance_kwh_and_w_m2"] = [float(mv["irradiance_toa_kwh_m2_day"][89 * 360]), float(mv["irradiance_toa_kwh_m2_day"][89 * 360]) * 1000 / 24]
            u["moon_equator_S0_over_pi_kwh"] = 1361.0 / np.pi * 24 / 1000
            u["earth_toa_equator_kwh"] = float(ev["irradiance_toa_kwh_m2_day"][89 * 360])
            u["earth_toa_unique_values_on_pairs"] = int(np.unique(np.round(toa_e, 6)).size)
            u["earth_toa_unique_values_on_passing"] = int(np.unique(np.round(pr["irradiance_toa_kwh_m2_day.earth"], 6)).size)
            zi_s = np.flatnonzero(zmask["solar"])
            u["moon_zone_irradiance_unique_values"] = int(np.unique(mv["irradiance_toa_kwh_m2_day"][zi_s]).size)
        if mi == "rover":
            u["elevation_body_means_m"] = notes["elevation_body_mean"]
            u["earth_mean_cells"] = int(np.isfinite(pd.to_numeric(e["elevation_m"], errors="coerce")).sum())
            el = pd.to_numeric(e["elevation_m"], errors="coerce").to_numpy()
            u["earth_land_elev_min_max"] = [float(np.nanmin(el)), float(np.nanmax(el))]
        out["units"][mi] = u
        print(mi, "share>=99:", round(sat["share_ge_99"], 4), ">=99.99:", round(sat["share_ge_99.99"], 4),
              "pub 100:", sat["count_published_100.00"])
    # slope: degrees everywhere? compare slope_deg and slope_iso_deg columns, and percent-grade equivalents
    for body, df in (("EARTH", e), ("MOON", m)):
        a = pd.to_numeric(df["slope_iso_deg"], errors="coerce").to_numpy()
        out["units"][f"slope_iso_deg_{body}"] = {"min": float(np.nanmin(a)), "max": float(np.nanmax(a)), "median": float(np.nanmedian(a))}
        r_ = pd.to_numeric(df["roughness_m"], errors="coerce").to_numpy()
        out["units"][f"roughness_m_{body}"] = {"min": float(np.nanmin(r_)), "max": float(np.nanmax(r_)), "median": float(np.nanmedian(r_))}
    out["units"]["slope_2deg_as_percent_grade"] = float(100 * np.tan(np.radians(2.0)))
    out["units"]["slope_4deg_as_percent_grade"] = float(100 * np.tan(np.radians(4.0)))
    tab = pd.DataFrame(rows, columns=["mission", "variable", "role", "unit", "tolerance", "bound", "median", "p90", "max"])
    tab.to_csv(os.path.join(OUT, "p2_table.csv"), index=False, float_format="%.4f")
    out["table"] = tab.to_dict(orient="records")
    dump(out, "p2_units.json")
    print(tab.to_string())


if __name__ == "__main__":
    main()
