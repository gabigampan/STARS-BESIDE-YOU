"""Research 3 (Lunar base): double counting, permafrost, thermal-swing gate.
Measures options IN MEMORY with the auditor library p5_common, run against a snapshot of the
inputs at commit 42d8bba (configuration, tables) so that edits made today by other agents do not
leak in. Deterministic. Run:
  python3 "tierra luna/research/r3_base_lunar.py" <snapshot_dir>
where <snapshot_dir> holds "tierra luna/{engine,mission_scoring.json,real_data/column_aliases.json,
output_real}" extracted with `git archive 42d8bba` plus the audit/*.py files (see report).
Output: tierra luna/research/out/r3_base_lunar.json
"""
import copy, json, os, sys
import numpy as np
import pandas as pd

SNAP = sys.argv[1]
sys.path.insert(0, os.path.join(SNAP, "tierra luna", "audit"))
import p5_common as C  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
OUTD = os.path.join(HERE, "out"); os.makedirs(OUTD, exist_ok=True)
M = "lunar_base"

P0 = C.load_params(); T0 = C.load_tables(P0); D0 = C.derived(T0, P0)
RAW = pd.read_csv(os.path.join(SNAP, "tierra luna", "output_real", "earth_real_1deg.csv"), low_memory=False)
RAW["id"] = RAW["row"].astype(int) * 360 + RAW["col"].astype(int)
RAW = RAW.set_index("id").sort_index()

ANALOGS = [  # analog_benchmark.csv ids, cold / polar / high-mountain / habitat
    "MA06", "MA07", "MA08", "MA09", "MA19", "OP01", "OP02", "MO05"]
B = pd.read_csv(os.path.join(os.path.dirname(HERE), "data", "benchmark", "analog_benchmark.csv"))
B = B[B["id"].isin(ANALOGS)]


def cell_of(lat, lon):
    r = int(np.floor(90 - lat)); c = int(np.floor(lon + 180))
    return min(r, 179) * 360 + min(c, 359)


def run(P, T=T0, D=D0):
    return C.run_mission(T, D, M, P)


def summary(r, base_top50=None, T=T0):
    E = T["EARTH"].set_index("id")
    o = np.argsort(np.where(r["rank"] > 0, r["rank"], 10 ** 9), kind="stable")
    o = o[r["rank"][o] > 0]
    top = []
    for i in o[:5]:
        eid = int(r["pass_ids"][i])
        top.append({"earth_id": eid, "lat": float(E.loc[eid, "lat"]), "lon": float(E.loc[eid, "lon"]),
                    "twin": int(r["twin"][i]), "sim": round(float(r["sim"][i]), 2),
                    "suit": round(float(r["suit"][i]), 2), "final": float(r["final_pub"][i]),
                    "amp_k": float(RAW.loc[eid, "lst_diurnal_amp_k"]),
                    "amp_max_k": float(RAW.loc[eid, "lst_diurnal_amp_max_k"]),
                    "tmin_c": float(RAW.loc[eid, "tmin_c"]),
                    "lc": int(RAW.loc[eid, "lc_dominant_cci_code"]) if np.isfinite(RAW.loc[eid, "lc_dominant_cci_code"]) else None})
    top50 = [int(r["pass_ids"][i]) for i in o[:50]]
    paired = r["twin"] >= 0
    s = r["suit"][paired]
    out = {"pass": int(r["passed"].sum()), "paired": int(paired.sum()),
           "distinct_twins": int(len(set(r["twin"][paired].tolist()))),
           "suit_paired_p5_p50_p95": [round(float(x), 2) for x in np.percentile(s, [5, 50, 95])] if len(s) else None,
           "suit_paired_sd": round(float(np.std(s)), 2) if len(s) else None,
           "top5": top, "top50": top50}
    if base_top50 is not None:
        out["top50_overlap_with_today"] = len(set(top50) & set(base_top50))
        out["top5_overlap_with_today"] = len(set(top50[:5]) & set(base_top50[:5]))
    # analogs
    pos = {int(e): k for k, e in enumerate(r["pass_ids"])}
    an = []
    for _, a in B.iterrows():
        cid = cell_of(a["lat"], a["lon"])
        k = pos.get(cid)
        an.append({"id": a["id"], "name": a["name"], "cell": cid,
                   "passes": k is not None,
                   "paired": bool(k is not None and r["twin"][k] >= 0),
                   "rank": int(r["rank"][k]) if k is not None and r["rank"][k] > 0 else None,
                   "of": int((r["rank"] > 0).sum())})
    out["analogs"] = an
    return out


def gate_reasons(P, T=T0):
    """Why each analog fails the funnel (per gate, Earth)."""
    E = T["EARTH"].set_index("id")
    mm = P["missions"][M]
    res = []
    for _, a in B.iterrows():
        cid = cell_of(a["lat"], a["lon"])
        row = RAW.loc[cid]
        why = []
        if not (row["elevation_m"] >= 1): why.append(f"elevation_m={row['elevation_m']} (<1, land gate)")
        if not (row["mask_fraction"] >= 0.3): why.append(f"mask_fraction={row['mask_fraction']} (<0.3)")
        for v in mm["require_present"]:
            val = E.loc[cid, v]
            if pd.isna(val) or str(val).strip().lower() in ("", "nan"): why.append(f"{v} missing")
        g = mm["gates"]
        amp = row["lst_diurnal_amp_k"]
        if np.isfinite(amp) and "lst_diurnal_amp_k" in g and amp < g["lst_diurnal_amp_k"].get("min", -1e9):
            why.append(f"amp {amp} K < {g['lst_diurnal_amp_k']['min']}")
        if np.isfinite(row["tmin_c"]) and row["tmin_c"] > 5: why.append(f"tmin {row['tmin_c']} C > 5")
        if str(row["thermal_inertia_class"]).lower() == "agua": why.append("dominant class agua")
        res.append({"id": a["id"], "name": a["name"], "lat": a["lat"], "lon": a["lon"], "cell": cid,
                    "cell_lat": float(row["lat_deg"]), "cell_lon": float(row["lon_deg"]),
                    "amp_k": None if not np.isfinite(amp) else float(amp),
                    "amp_max_k": None if not np.isfinite(row["lst_diurnal_amp_max_k"]) else float(row["lst_diurnal_amp_max_k"]),
                    "amp_max_month": None if not np.isfinite(row["lst_diurnal_amp_max_month"]) else int(row["lst_diurnal_amp_max_month"]),
                    "tmin_c": None if not np.isfinite(row["tmin_c"]) else float(row["tmin_c"]),
                    "temp_k": None if not np.isfinite(row["temp_k"]) else float(row["temp_k"]),
                    "n_lst_px": int(row["n_lst_px"]), "elev": float(row["elevation_m"]) if np.isfinite(row["elevation_m"]) else None,
                    "mask": float(row["mask_fraction"]), "class": row["thermal_inertia_class"],
                    "rock_or_bare": float(row["rock_or_bare_frac"]) if np.isfinite(row["rock_or_bare_frac"]) else None,
                    "permafrost": row["permafrost_class"], "lc": row["lc_dominant_cci_code"],
                    "fails_today": why})
    return res


def soft(P, var, **kw):
    P = copy.deepcopy(P)
    s = P["missions"][M]["soft"]
    for k, v in kw.items():
        if k == "drop":
            s.pop(var, None)
        else:
            s[var][k] = v
    return P


def gate(P, var, **kw):
    P = copy.deepcopy(P)
    g = P["missions"][M]["gates"]
    if kw.get("drop"):
        g.pop(var, None)
    else:
        g[var] = kw
    return P


def with_amp_max(scope):
    """Earth swing = warmest-month mean day-minus-night LST (lst_diurnal_amp_max_k, MOD11A2 monthly
    climatology, already in the table) instead of the annual mean day-minus-night. scope 'gate_suit'
    changes only the funnel and the suitability (T); 'all' also the pairing percentile (D)."""
    T = {b: df.copy() for b, df in T0.items()}
    T["EARTH"]["lst_diurnal_amp_k"] = RAW.loc[T["EARTH"]["id"].to_numpy(), "lst_diurnal_amp_max_k"].to_numpy()
    D = dict(D0)
    if scope == "all":
        D = copy.copy(D0)
        D["lst_diurnal_amp_k"] = {"EARTH": pd.to_numeric(T["EARTH"]["lst_diurnal_amp_k"]).to_numpy(float),
                                  "MOON": D0["lst_diurnal_amp_k"]["MOON"]}
    return T, D


def main():
    rep = {"snapshot": SNAP}
    r0 = run(P0)
    base = summary(r0)
    b50 = base["top50"]
    rep["baseline"] = base
    rep["analog_cells"] = gate_reasons(P0)

    # 1. double counting -------------------------------------------------------------
    E = RAW
    pas = r0["pass_ids"]
    ti = pd.Series(r0["utils"]["thermal_inertia_class"]); rb = pd.Series(r0["utils"]["rock_or_bare_frac"])
    rep["dc_spearman_utils_passing"] = round(float(ti.corr(rb, method="spearman")), 3)
    lc = E.loc[pas, "lc_dominant_cci_code"]
    rep["dc_passing_by_dominant_class"] = {str(int(k)): int(v) for k, v in lc.value_counts().items()}
    rep["dc_passing_urban190"] = int((lc == 190).sum())
    opts = {
        "DC1_keep_class_weight_0.25": soft(soft(P0, "rock_or_bare_frac", drop=True), "thermal_inertia_class", weight=0.25),
        "DC2_keep_rockbare_weight_0.25": soft(soft(P0, "thermal_inertia_class", drop=True), "rock_or_bare_frac", weight=0.25),
        "DC3_drop_rockbare_no_redistribution": soft(P0, "rock_or_bare_frac", drop=True),
    }
    # urban fix on top of DC2: 190 is mapped to 'roca' only in the class criterion; DC2 removes it.
    P_u = copy.deepcopy(opts["DC1_keep_class_weight_0.25"])
    rep["urban_note"] = "rock_or_bare_frac codes 150-153,200-202 do not include 190; only thermal_inertia_class maps 190 to roca"
    # 2. permafrost ---------------------------------------------------------------------
    opts["PF0_permafrost_weight0"] = soft(P0, "permafrost_class", drop=True)
    pf = E.loc[pas, "permafrost_class"]
    rep["pf_passing_counts"] = {str(k): int(v) for k, v in pf.fillna("MISSING").value_counts().items()}
    # 3. gate ---------------------------------------------------------------------------
    opts["G_nogate_soft_bad15"] = gate(P0, "lst_diurnal_amp_k", drop=True)
    Pg = gate(P0, "lst_diurnal_amp_k", drop=True)
    Pg["missions"][M]["soft"]["lst_diurnal_amp_k"]["bad"] = 0.0
    opts["G_nogate_soft_bad0"] = Pg
    for g in (10.0, 5.0):
        opts[f"G_gate_{int(g)}K"] = gate(P0, "lst_diurnal_amp_k", min=g)
    # combined recommendation candidates
    Pr = soft(soft(soft(P0, "rock_or_bare_frac", drop=True), "thermal_inertia_class", weight=0.25), "permafrost_class", drop=True)
    opts["R_DC1_PF0"] = Pr
    Pr2 = copy.deepcopy(soft(soft(P0, "thermal_inertia_class", drop=True), "rock_or_bare_frac", weight=0.25))
    Pr2 = soft(Pr2, "permafrost_class", drop=True)
    Pr2["missions"][M]["require_present"] = [v for v in Pr2["missions"][M]["require_present"] if v != "thermal_inertia_class"]
    opts["R_DC2_PF0_classgate_kept"] = Pr2  # agua exclusion gate kept, class not a weighted criterion
    for k, P in opts.items():
        rep[k] = summary(run(P), b50)
        print(k, rep[k]["pass"], rep[k]["paired"], rep[k]["top50_overlap_with_today"], [t["earth_id"] for t in rep[k]["top5"]], flush=True)
    # swing definition: warmest-month day-night (already in table)
    for scope in ("gate_suit", "all"):
        T, D = with_amp_max(scope)
        for nm, P in (("today", P0), ("R_DC1_PF0", Pr)):
            k = f"AMPMAX_{scope}_{nm}"
            rep[k] = summary(C.run_mission(T, D, M, P), b50, T)
            print(k, rep[k]["pass"], rep[k]["paired"], rep[k]["top50_overlap_with_today"], [t["earth_id"] for t in rep[k]["top5"]], flush=True)
    # where the gate sits: distribution of the swing among cells passing every other filter
    Pn = gate(P0, "lst_diurnal_amp_k", drop=True)
    pn = C.gate_pass(T0["EARTH"], "EARTH", M, Pn)
    a = pd.to_numeric(T0["EARTH"]["lst_diurnal_amp_k"], errors="coerce").to_numpy()[pn]
    rep["swing_without_gate"] = {"n": int(pn.sum()), "share_below_15K": round(float((a < 15).mean()), 3),
                                 "pct": {str(q): round(float(np.percentile(a, q)), 2) for q in (5, 25, 50, 75, 95)}}
    mz = C.zone_mask(T0["MOON"], M, P0)
    am = D0["lst_diurnal_amp_k"]["MOON"][mz]; tm = D0["tmin_k"]["MOON"][mz]
    rep["moon_zone_swing_k"] = {str(q): round(float(np.nanpercentile(am, q)), 1) for q in (5, 50, 95)}
    rep["moon_zone_tmin_k"] = {str(q): round(float(np.nanpercentile(tm, q)), 1) for q in (5, 50, 95)}
    json.dump(rep, open(os.path.join(OUTD, "r3_base_lunar.json"), "w"), indent=1, default=str)


if __name__ == "__main__":
    main()
