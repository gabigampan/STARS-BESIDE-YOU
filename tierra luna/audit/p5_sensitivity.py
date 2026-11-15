"""Point A (reviewer 5): measured effect of removing or perturbing every number of the model.

Runs the auditor's own implementation (p5_common, verified against the shipped bundle by
p5_baseline.py: 0 twin, 0 rank and 0.00 score differences in the three missions) with ONE
number removed or perturbed at a time, and counts against the unperturbed run:
  Earth points entering / leaving the funnel, pairs gained / lost / with another twin,
  and the overlap of the top 5 and top 50 pairs (Earth id, twin id) and their order.
Deterministic. Run:
  <python> "tierra luna/audit/p5_sensitivity.py" [mission ...]
Outputs: out/p5_sensitivity_<mission>.csv (one row per perturbation); with --part START STOP
(to split a mission over processes) out/p5_sensitivity_<mission>_partSTART.csv; p5_inventory.py
reads all of them.
"""
from __future__ import annotations

import copy
import csv
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from p5_common import (MISSIONS, OUT, derived, load_params, load_tables, run_mission, top_pairs)  # noqa: E402


# ------------------------------------------------------------------ perturbation builders
def _set(path_fn):
    def f(P):
        Q = copy.deepcopy(P)
        path_fn(Q)
        return Q
    return f


def perturbations(P, m):
    """List of (id, group, description, kind, fn). kind 'P' -> fn(P) returns new P;
    kind 'D' -> fn(P) returns (new P, dtag) where derived values must be recomputed."""
    out = []
    add = lambda pid, grp, desc, fn, kind="P": out.append((pid, grp, desc, kind, fn))
    # common gates
    for g, spec in P["common_gates"].items():
        add(f"common_gate.{g}.drop", "common_gate", f"drop common gate {g}",
            _set(lambda Q, g=g: Q["common_gates"].pop(g)))
        for k in ("min", "max"):
            if spec.get(k) is not None:
                for fac in (0.9, 1.1):
                    add(f"common_gate.{g}.{k}x{fac}", "common_gate", f"common gate {g} {k} {spec[k]} x{fac}",
                        _set(lambda Q, g=g, k=k, fac=fac: Q["common_gates"][g].__setitem__(k, Q["common_gates"][g][k] * fac)))
    mm = P["missions"][m]
    for v in mm["require_present"]:
        add(f"require_present.{v}.drop", "require_present", f"drop require_present {v}",
            _set(lambda Q, v=v: Q["missions"][m]["require_present"].remove(v)))
    for g, spec in mm["gates"].items():
        add(f"gate.{g}.drop", "gate", f"drop gate {g}", _set(lambda Q, g=g: Q["missions"][m]["gates"].pop(g)))
        for k in ("min", "max"):
            if spec.get(k) is not None:
                add(f"gate.{g}.{k}.drop", "gate", f"drop {k} of gate {g}",
                    _set(lambda Q, g=g, k=k: Q["missions"][m]["gates"][g].pop(k)))
                for fac in (0.9, 1.1):
                    add(f"gate.{g}.{k}x{fac}", "gate", f"gate {g} {k} {spec[k]} x{fac}",
                        _set(lambda Q, g=g, k=k, fac=fac: Q["missions"][m]["gates"][g].__setitem__(k, Q["missions"][m]["gates"][g][k] * fac)))
    for v, s in mm["soft"].items():
        add(f"soft.{v}.weight0", "soft_weight", f"suitability weight of {v} ({s['weight']}) -> 0",
            _set(lambda Q, v=v: Q["missions"][m]["soft"][v].__setitem__("weight", 0.0)))
        for fac in (0.9, 1.1):
            add(f"soft.{v}.weight x{fac}", "soft_weight", f"suitability weight of {v} x{fac}",
                _set(lambda Q, v=v, fac=fac: Q["missions"][m]["soft"][v].__setitem__("weight", Q["missions"][m]["soft"][v]["weight"] * fac)))
        if "map" in s:
            add(f"soft.{v}.default0.4", "soft_utility", f"default utility of {v} 0.5 -> 0.4",
                _set(lambda Q, v=v: Q["missions"][m]["soft"][v].__setitem__("default", 0.4)))
            for cat in s["map"]:
                add(f"soft.{v}.map.{cat}-0.1", "soft_utility", f"utility of {v}={cat} {s['map'][cat]} -0.1",
                    _set(lambda Q, v=v, cat=cat: Q["missions"][m]["soft"][v]["map"].__setitem__(cat, Q["missions"][m]["soft"][v]["map"][cat] - 0.1)))
        else:
            for k in ("bad", "good"):
                for fac in (0.9, 1.1):
                    add(f"soft.{v}.{k}x{fac}", "soft_utility", f"{k} of {v} ({s[k]}) x{fac}",
                        _set(lambda Q, v=v, k=k, fac=fac: Q["missions"][m]["soft"][v].__setitem__(k, Q["missions"][m]["soft"][v][k] * fac)))
    sim = mm["sim"]
    for q, x in enumerate(sim["variables"]):
        v = x["variable"]
        add(f"sim.{v}.weight0", "sim_weight", f"similarity weight of {v} ({x['weight']}) -> 0, still in the pair filter",
            _set(lambda Q, q=q: Q["missions"][m]["sim"]["variables"][q].__setitem__("weight", 0.0)))
        add(f"sim.{v}.removed", "sim_weight", f"{v} removed from similarity AND pair filter",
            _set(lambda Q, q=q: Q["missions"][m]["sim"]["variables"][q].__setitem__("_removed", True)))
        for fac in (0.9, 1.1):
            add(f"sim.{v}.weight x{fac}", "sim_weight", f"similarity weight of {v} x{fac}",
                _set(lambda Q, q=q, fac=fac: Q["missions"][m]["sim"]["variables"][q].__setitem__("weight", Q["missions"][m]["sim"]["variables"][q]["weight"] * fac)))
            add(f"sim.{v}.tolerance x{fac}", "tolerance", f"tolerance of {v} ({x['tolerance']}) x{fac}",
                _set(lambda Q, q=q, fac=fac: Q["missions"][m]["sim"]["variables"][q].__setitem__("tolerance", Q["missions"][m]["sim"]["variables"][q]["tolerance"] * fac)))
    for role in ("key", "secondary"):
        for fac in (0.9, 1.1):
            add(f"mult.{role}x{fac}", "filter_bound", f"filter multiplier {role} ({P['mult'][role]}) x{fac}",
                _set(lambda Q, role=role, fac=fac: Q["mult"].__setitem__(role, Q["mult"][role] * fac)))
    z = sim["zone"]
    if z["kind"] == "lat_max":
        for val in (z["lat_max"] * 0.9, z["lat_max"] * 1.1, z["lat_max"] + 1, z["lat_max"] - 1):
            add(f"zone.lat_max={val:g}", "zone", f"zone latitude limit {z['lat_max']} -> {val:g}",
                _set(lambda Q, val=val: Q["missions"][m]["sim"]["zone"].__setitem__("lat_max", val)))
    if z["kind"] == "abs_lat_max_elevation_max":
        for val in (z["abs_lat_max"] * 0.9, z["abs_lat_max"] * 1.1):
            add(f"zone.abs_lat_max={val:g}", "zone", f"zone |lat| limit {z['abs_lat_max']} -> {val:g}",
                _set(lambda Q, val=val: Q["missions"][m]["sim"]["zone"].__setitem__("abs_lat_max", val)))
        for val in (z["elevation_max_m"] * 0.9, z["elevation_max_m"] * 1.1):
            add(f"zone.elevation_max_m={val:g}", "zone", f"zone elevation limit {z['elevation_max_m']} -> {val:g}",
                _set(lambda Q, val=val: Q["missions"][m]["sim"]["zone"].__setitem__("elevation_max_m", val)))
    if z["kind"] == "similarity_zone":
        fb = P["zones_cfg"]["lunar_base"]["fallback"]
        add("zone.fallback_lat_max-75", "zone", "Lunar base zone replaced by its configured fallback (lat <= -75)",
            _set(lambda Q: Q["missions"][m]["sim"].__setitem__("zone", {"kind": "lat_max", "lat_max": fb["lat_max"]})))
        for rule in ("rank_over_n", "weibull"):
            add(f"percentile_rule={rule}", "percentile_rule", f"mid-rank rule -> {rule}",
                _set(lambda Q, rule=rule: Q.__setitem__("percentile_rule", rule)))
    for a in (0.45, 0.55, 0.0, 1.0):
        add(f"alpha={a}", "alpha", f"alpha 0.5 -> {a}", _set(lambda Q, a=a: Q.__setitem__("alpha", a)))
    add("utility_decimals=None", "rounding", "utilities not rounded to 6 decimals",
        _set(lambda Q: Q.__setitem__("utility_decimals", None)))
    add("score_decimals=12", "rounding", "per-variable scores rounded to 12 instead of 6 decimals",
        _set(lambda Q: Q.__setitem__("score_decimals", 12)))
    add("final_decimals=12", "rounding", "rank on the final score at 12 decimals instead of 2",
        _set(lambda Q: Q.__setitem__("final_decimals", 12)))
    # constants that act through the derived values
    names = [x["variable"] for x in sim["variables"]]
    if "irradiance_toa_kwh_m2_day" in names:
        for k in ("solar_constant_w_m2", "obliquity_deg", "eccentricity", "sun_longitude_at_perihelion_deg", "hours_per_day"):
            add(f"toa.{k}x1.01", "constant", f"TOA constant {k} ({P['toa'][k]}) x1.01",
                (lambda Q0, k=k: (_set(lambda Q: Q["toa"].__setitem__(k, Q["toa"][k] * 1.01))(Q0), f"toa_{k}")), "D")
        add("moon_irradiance x1.01", "constant", "lunar irradiance column x1.01 (= lunar S0 or day factor +1 %)",
            (lambda Q0: (copy.deepcopy(Q0), "moon_irr")), "D")
        add("S0 both bodies x1.01", "constant", "solar constant x1.01 on BOTH sides (Earth TOA and the lunar column, which uses the same 1361 W/m2)",
            (lambda Q0: (_set(lambda Q: Q["toa"].__setitem__("solar_constant_w_m2", Q["toa"]["solar_constant_w_m2"] * 1.01))(Q0), "s0_both")), "D")
    if "elevation_rel_m" in names:
        for b in ("EARTH", "MOON"):
            add(f"body_mean.{b}x1.01", "constant", f"{b} mean elevation x1.01",
                (lambda Q0, b=b: (_set(lambda Q: Q["body_mean_scale"].__setitem__(b, 1.01))(Q0), f"bm_{b}")), "D")
        add("body_mean.unweighted", "constant", "body mean elevation without cos(lat) weight",
            (lambda Q0: (_set(lambda Q: Q.__setitem__("body_mean_weighting", "none"))(Q0), "bm_none")), "D")
    if "tmin_k" in names:
        add("kelvin_offset x1.01", "constant", "273.15 K offset x1.01 (both bodies)",
            (lambda Q0: (_set(lambda Q: Q.__setitem__("kelvin_offset", Q["kelvin_offset"] * 1.01))(Q0), "kelvin")), "D")
    return out


# ------------------------------------------------------------------ comparison
def compare(r0, r1):
    a0, a1 = set(r0["pass_ids"].tolist()), set(r1["pass_ids"].tolist())
    p0 = {int(i): int(t) for i, t in zip(r0["pass_ids"], r0["twin"]) if t >= 0}
    p1 = {int(i): int(t) for i, t in zip(r1["pass_ids"], r1["twin"]) if t >= 0}
    common = set(p0) & set(p1)
    t5_0, t5_1 = top_pairs(r0, 5), top_pairs(r1, 5)
    t50_0, t50_1 = top_pairs(r0, 50), top_pairs(r1, 50)
    return {
        "earth_pass": len(a1), "entered": len(a1 - a0), "left": len(a0 - a1),
        "paired": len(p1), "pairs_gained": len(set(p1) - set(p0)), "pairs_lost": len(set(p0) - set(p1)),
        "twin_changed": sum(1 for i in common if p0[i] != p1[i]),
        "top5_kept": len(set(t5_0) & set(t5_1)), "top5_same_order": t5_0 == t5_1,
        "top50_kept": len(set(t50_0) & set(t50_1)), "top50_same_order": t50_0 == t50_1,
        "top5_new": ";".join(f"{e}-{t}" for e, t in t5_1 if (e, t) not in set(t5_0)),
    }


def main(missions, start=0, stop=None, tag=""):
    """start/stop: run only perturbations [start, stop) of the list (to split a mission over several
    processes); rows are appended to the CSV as they are computed."""
    t0 = time.time()
    P0 = load_params()
    T = load_tables(P0)
    D0 = derived(T, P0)
    for m in missions:
        cache = {}
        base = run_mission(T, D0, m, P0, cache=cache)
        rows = []
        path = os.path.join(OUT, f"p5_sensitivity_{m}{tag}.csv")
        fh = open(path, "w", newline="", encoding="utf-8")
        wr = None
        for pid, grp, desc, kind, fn in perturbations(P0, m)[start:stop]:
            if kind == "P":
                Q, D, tag = fn(P0), D0, "base"
            else:
                Q, tag = fn(P0)
                D = derived(T, Q)
                if tag in ("moon_irr", "s0_both"):
                    D["irradiance_toa_kwh_m2_day"]["MOON"] = D["irradiance_toa_kwh_m2_day"]["MOON"] * 1.01
            r = run_mission(T, D, m, Q, cache=cache, dtag=tag)
            row = {"mission": m, "id": pid, "group": grp, "change": desc, **compare(base, r)}
            rows.append(row)
            if wr is None:
                wr = csv.DictWriter(fh, fieldnames=list(row.keys()))
                wr.writeheader()
            wr.writerow(row)
            fh.flush()
            print(m, pid, {k: row[k] for k in ("entered", "left", "pairs_gained", "pairs_lost", "twin_changed", "top5_kept", "top50_kept")}, flush=True)
        fh.close()
        print(m, "done", round(time.time() - t0, 1), "s", flush=True)


if __name__ == "__main__":
    # usage: p5_sensitivity.py [mission ...]   or   p5_sensitivity.py mission --part START STOP
    a = sys.argv[1:]
    if "--part" in a:
        k = a.index("--part")
        st, sp = int(a[k + 1]), int(a[k + 2])
        main(a[:k], st, sp, f"_part{st:03d}")
    else:
        main(a or list(MISSIONS))
