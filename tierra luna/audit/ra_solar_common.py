"""Re-audit of Solar panels (audit 9): common library.

Independent code path: reuses the first auditors' implementation (audit/p5_common.py: funnel,
suitability, real-value similarity, pair filter, twin search, final, rank), adapted to the
corrected rules here:
  * criteria sets of engine_config.json criteria_sets (engine_patch by dotted path + the
    mission_scoring_deviations of each set applied to the team's mission_scoring.json soft block);
  * the supplementary column clear_frac_isccp joined by cell id from
    real_data/supplement/earth_cloud_isccp_1deg.csv;
  * the five-selection rules by_rank / min_separation / rank_with_skips (ice, water, 2 degrees).
Nothing of tierra luna/engine is imported. Reads tables, the three configuration files and a bundle
folder (for comparison only).
"""
from __future__ import annotations

import copy
import json
import math
import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
TL = os.path.dirname(HERE)
REPO = os.path.dirname(TL)
OUT = os.path.join(HERE, "out")
sys.path.insert(0, HERE)
import p5_common as C  # noqa: E402

BUNDLE = os.path.join(REPO, "app", "public", "data", "v2")
SUPP = os.path.join(TL, "real_data", "supplement", "earth_cloud_isccp_1deg.csv")
R_EARTH = 6371.0


# ------------------------------------------------------------------ config with criteria sets
def _ec():
    return json.load(open(os.path.join(TL, "engine", "engine_config.json"), encoding="utf-8"))


def _set_path(ec, dotted, value):
    parts = dotted.split(".")
    node = ec[parts[0]]
    node = node["value"] if isinstance(node, dict) and "value" in node else node
    for p in parts[1:-1]:
        node = node[p]
    node[parts[-1]] = copy.deepcopy(value)


def criteria_set(mission="solar", name=None, ec=None):
    ec = ec or _ec()
    cs = ec["criteria_sets"]["value"]
    name = name or cs["selected"][mission]
    return name, cs["missions"][mission]["sets"][name]


def load_params_set(set_name=None, mission="solar"):
    """p5_common.load_params with the criteria set applied (engine patch and soft deviations).
    Returns (P, ec_patched, set_name, set_def)."""
    ec = _ec()
    name, sd = criteria_set(mission, set_name, ec)
    for k, v in (sd.get("engine_patch") or {}).items():
        _set_path(ec, k, v)
    P = C.load_params()
    rv = ec["real_value_similarity"]["value"]
    for m in C.MISSIONS:
        P["missions"][m]["sim"] = copy.deepcopy(rv["missions"][m])
    soft = P["missions"][mission]["soft"]
    for d in sd.get("mission_scoring_deviations") or []:
        c = d["criterion"]
        if d.get("ours") is None:
            soft.pop(c, None)
        else:
            soft[c] = {k: v for k, v in d["ours"].items() if k in ("weight", "bad", "good", "map", "default")}
    P["top5"] = copy.deepcopy(ec["top5_selection"]["value"]["missions"][mission])
    P["top5_count"] = int(ec["top5_selection"]["value"].get("count", 5))
    return P, ec, name, sd


# ------------------------------------------------------------------ data
_T = {}


def tables(P):
    if "T" not in _T:
        T = C.load_tables(P)
        sup = pd.read_csv(SUPP)
        sup["id"] = sup["row"].astype(int) * 360 + sup["col"].astype(int)
        assert (sup["cell_id"] == "E" + sup["id"].astype(str)).all()
        m = sup.set_index("id")
        E = T["EARTH"]
        E["clear_frac_isccp"] = m["clear_frac_isccp"].reindex(E["id"]).to_numpy()
        E["cloud_frac_isccp"] = m["cloud_frac_isccp"].reindex(E["id"]).to_numpy()
        E["n_months_isccp"] = m["n_months_isccp"].reindex(E["id"]).to_numpy()
        raw = pd.read_csv(os.path.join(TL, "output_real", "earth_real_1deg.csv"), low_memory=False)
        raw["id"] = raw["row"].astype(int) * 360 + raw["col"].astype(int)
        raw = raw.sort_values("id").reset_index(drop=True)
        assert (raw["id"].to_numpy() == E["id"].to_numpy()).all()
        for c in ("snow_ice_frac", "mask_fraction", "lc_dominant_cci_code", "bare_frac", "elevation_all_m"):
            E["__" + c] = raw[c].to_numpy()
        _T["T"] = T
        _T["D"] = C.derived(T, P)
    return _T["T"], _T["D"]


def run(P, mission="solar", cache=None):
    T, D = tables(P)
    return C.run_mission(T, D, mission, P, cache=cache)


# ------------------------------------------------------------------ the five
def ang_deg(la1, lo1, la2, lo2):
    a1, o1, a2, o2 = map(math.radians, (la1, lo1, la2, lo2))
    c = math.sin(a1) * math.sin(a2) + math.cos(a1) * math.cos(a2) * math.cos(o1 - o2)
    return math.degrees(math.acos(max(-1.0, min(1.0, c))))


def _skip(E, idx, skips):
    why = []
    for nm, s in (skips or {}).items():
        if not s.get("enabled", True):
            continue
        x = E["__" + s["column"]].iloc[idx] if ("__" + s["column"]) in E else E[s["column"]].iloc[idx]
        x = float(x) if pd.notna(x) else float("nan")
        op = s["op"]
        hit = (x >= s["value"]) if op == ">=" else (x < s["value"]) if op == "<" else (x > s["value"]) if op == ">" else (x <= s["value"])
        if hit:
            why.append(nm)
    return why


def five(r, P, k=None, with_skipped=False):
    """Indices q (into r arrays) of the five, by the rule P['top5']."""
    T, _ = tables(P)
    E = T["EARTH"]
    k = k or P.get("top5_count", 5)
    rule = P["top5"].get("rule", "by_rank")
    sep = float(P["top5"].get("min_separation_deg", 0) or 0)
    o = np.argsort(np.where(r["rank"] > 0, r["rank"], 10 ** 9), kind="stable")
    o = o[r["rank"][o] > 0]
    pos = {int(i): j for j, i in enumerate(E["id"].to_numpy())}
    lat, lon = E["lat"].to_numpy(), E["lon"].to_numpy()
    kept, skipped = [], []
    for q in o:
        i = pos[int(r["pass_ids"][q])]
        why = []
        if rule == "rank_with_skips":
            why = _skip(E, i, P["top5"].get("skips"))
        if rule in ("min_separation", "rank_with_skips") and sep > 0:
            near = [int(r["pass_ids"][kq]) for kq in kept if ang_deg(lat[i], lon[i], lat[pos[int(r["pass_ids"][kq])]], lon[pos[int(r["pass_ids"][kq])]]) < sep]
            if near:
                why.append("within %.1f deg of E%d" % (sep, near[0]))
        if rule not in ("by_rank", "min_separation", "rank_with_skips"):
            raise ValueError(rule)
        if why:
            skipped.append((int(r["pass_ids"][q]), int(r["rank"][q]), why))
        else:
            kept.append(q)
        if len(kept) == k:
            break
    return (kept, skipped) if with_skipped else kept


# ------------------------------------------------------------------ bundle
def bundle_cols(bdir, fname):
    man = json.load(open(os.path.join(bdir, "manifest.json"), encoding="utf-8"))
    ent = [f for f in man["files"] if f["name"] == fname][0]
    raw = open(os.path.join(bdir, fname), "rb").read()
    out = {}
    for c in ent["columns"]:
        dt = "<f4" if c["type"] == "float32" else "<i4"
        a = np.frombuffer(raw, dtype=dt, count=c["length"], offset=c["offset"])
        if c["type"] == "int32":
            miss = a == -2147483648
            a = a.astype(np.float64)
            if c.get("divisor"):
                a = a / float(c["divisor"])
            a[miss] = np.nan
        else:
            a = a.astype(np.float64)
        out[c["name"]] = a
    return out


def bundle_solar(bdir=BUNDLE):
    base = bundle_cols(bdir, "earth_base.bin")
    mb = bundle_cols(bdir, "earth_solar.bin")
    ids = base["id"][mb["land_index"].astype(int)].astype(int)
    out = {"ids": ids, "base": base, **mb}
    try:
        out["pairs"] = bundle_cols(bdir, "earth_solar_pairs.bin")
    except Exception:
        out["pairs"] = None
    ms = json.load(open(os.path.join(bdir, "missions.json"), encoding="utf-8"))
    out["mdef"] = [x for x in ms["missions"] if x["id"] == "solar"][0]
    return out


def bundle_five(B):
    t = B["mdef"].get("top5")
    return t


def jdump(obj, name):
    os.makedirs(OUT, exist_ok=True)
    p = os.path.join(OUT, name)
    json.dump(obj, open(p, "w", encoding="utf-8"), indent=1, ensure_ascii=False, default=lambda o: o.item() if hasattr(o, "item") else str(o))
    return p
