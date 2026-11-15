"""Re-audit of Lunar base (2026-11-15): common helpers.

Own code path: the funnel, suitability, percentile pairing, final and rank come from the first
auditor's independent implementation p5_common (no module of tierra luna/engine is imported),
adapted here to the criteria sets of engine_config.json `criteria_sets` (applied by this file,
not by engine/criteria.py) and to the top-5 rules of `top5_selection` (re-implemented here).
"""
from __future__ import annotations

import copy
import json
import math
import os
import sys
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import p5_common as C  # noqa: E402

TL = C.TL
REPO = C.REPO
OUT = C.OUT
M = "lunar_base"
R_EARTH_KM = 6371.0


def engine_config() -> Dict:
    return json.load(open(os.path.join(TL, "engine", "engine_config.json"), encoding="utf-8"))


def _set_path(obj: Dict, dotted: str, value):
    """engine_patch keys are dotted paths below each top-level block's 'value'."""
    parts = dotted.split(".")
    top = obj[parts[0]]
    node = top["value"] if isinstance(top, dict) and "value" in top else top
    for p in parts[1:-1]:
        node = node[p]
    node[parts[-1]] = copy.deepcopy(value)


def params_for_set(set_name: str):
    """(P, ec_patched, set_block): p5 parameters with the lunar_base criteria set applied."""
    ec = copy.deepcopy(engine_config())
    sb = ec["criteria_sets"]["value"]["missions"][M]["sets"][set_name]
    for k, v in sb.get("engine_patch", {}).items():
        _set_path(ec, k, v)
    P = C.load_params()
    P["missions"][M]["sim"] = copy.deepcopy(ec["real_value_similarity"]["value"]["missions"][M])
    soft = P["missions"][M]["soft"]
    for dev in sb.get("mission_scoring_deviations", []):
        crit = dev["criterion"]
        if dev.get("ours") is None:
            soft.pop(crit, None)
        else:
            soft[crit] = {kk: vv for kk, vv in dev["ours"].items() if kk in ("weight", "bad", "good", "map", "default")}
    P["_top5"] = copy.deepcopy(ec["top5_selection"]["value"]["missions"][M])
    P["_top5_count"] = int(ec["top5_selection"]["value"].get("count", 5))
    return P, ec, sb


def load_raw_earth() -> pd.DataFrame:
    raw = pd.read_csv(os.path.join(TL, "output_real", "earth_real_1deg.csv"), low_memory=False)
    raw["id"] = raw["row"].astype(int) * 360 + raw["col"].astype(int)
    return raw.sort_values("id").reset_index(drop=True)


def gc_deg(lat1, lon1, lat2, lon2) -> float:
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dl = math.radians(lon2 - lon1)
    c = math.sin(p1) * math.sin(p2) + math.cos(p1) * math.cos(p2) * math.cos(dl)
    return math.degrees(math.acos(max(-1.0, min(1.0, c))))


def ranked_order(r: Dict) -> np.ndarray:
    o = np.argsort(np.where(r["rank"] > 0, r["rank"], 10 ** 9), kind="stable")
    return o[r["rank"][o] > 0]


def select_five(r: Dict, P: Dict, E: pd.DataFrame, raw: pd.DataFrame, rule: Optional[Dict] = None,
                return_skips: bool = False):
    """The five by the configured rule: by_rank, or rank_with_skips (ice / water / separation)."""
    rule = rule or P["_top5"]
    k = P["_top5_count"]
    order = ranked_order(r)
    ids = r["pass_ids"]
    lat = E.set_index("id")["lat"]
    lon = E.set_index("id")["lon"]
    rawi = raw.set_index("id")
    kept: List[int] = []
    skipped = []
    for i in order:
        cid = int(ids[i])
        if rule["rule"] == "by_rank":
            kept.append(i)
        else:
            why = None
            for name, s in rule.get("skips", {}).items():
                if not s.get("enabled", True):
                    continue
                x = float(rawi.at[cid, s["column"]])
                bad = (x >= s["value"]) if s["op"] == ">=" else (x < s["value"]) if s["op"] == "<" else False
                if not np.isfinite(x):
                    bad = False
                if bad:
                    why = name
                    break
            if why is None and rule.get("min_separation_deg"):
                for j in kept:
                    if gc_deg(lat[cid], lon[cid], lat[int(ids[j])], lon[int(ids[j])]) < float(rule["min_separation_deg"]):
                        why = f"near {int(ids[j])}"
                        break
            if why is None:
                kept.append(i)
            else:
                skipped.append((cid, int(r["rank"][i]), why))
        if len(kept) == k:
            break
    out = [int(ids[i]) for i in kept]
    return (out, skipped) if return_skips else out


def bundle_mission_at(folder: str, m: str = M) -> Dict[str, np.ndarray]:
    old = C.BUNDLE
    C.BUNDLE = folder
    try:
        return C.bundle_mission(m)
    finally:
        C.BUNDLE = old


def compare(r: Dict, b: Dict) -> Dict:
    pos = {int(i): k for k, i in enumerate(r["pass_ids"])}
    same = set(map(int, b["ids"])) == set(pos)
    idx = np.array([pos.get(int(i), -1) for i in b["ids"]])
    ok = idx >= 0
    idx2 = idx[ok]
    tw_b = np.where(np.isfinite(b["twin"]), b["twin"], -1).astype(int)[ok]
    rk_b = np.where(np.isfinite(b["rank"]), b["rank"], 0).astype(int)[ok]

    def mx(a, c):
        f = np.isfinite(a) & np.isfinite(c)
        nan_mismatch = int((np.isfinite(a) != np.isfinite(c)).sum())
        return (float(np.max(np.abs(a[f] - c[f]))) if f.any() else None), nan_mismatch

    s_suit = mx(C.pyround(r["suit"][idx2], 2), b["suitability"][ok])
    s_sim = mx(C.pyround(r["sim"][idx2], 2), b["similarity"][ok])
    s_fin = mx(r["final_pub"][idx2], b["final"][ok])
    return {"pass_mine": int(len(r["pass_ids"])), "pass_bundle": int(len(b["ids"])), "same_pass_set": bool(same),
            "paired_mine": int((r["twin"] >= 0).sum()), "paired_bundle": int((tw_b >= 0).sum()),
            "twin_mismatch": int((r["twin"][idx2] != tw_b).sum()), "rank_mismatch": int((r["rank"][idx2] != rk_b).sum()),
            "max_diff_suitability": s_suit[0], "nan_mismatch_suitability": s_suit[1],
            "max_diff_similarity": s_sim[0], "nan_mismatch_similarity": s_sim[1],
            "max_diff_final": s_fin[0], "nan_mismatch_final": s_fin[1]}


def bundle_top5(folder: str, m: str = M):
    mj = json.load(open(os.path.join(folder, "missions.json"), encoding="utf-8"))
    for x in mj["missions"]:
        if x.get("id") == m or x.get("mission") == m:
            return x.get("top5")
    return None


def run(set_name: str, T=None, D=None, P=None):
    if P is None:
        P, _, _ = params_for_set(set_name)
    if T is None:
        T = C.load_tables(P)
    if D is None:
        D = C.derived(T, P)
    return C.run_mission(T, D, M, P), P, T, D


def dump(obj, name: str):
    os.makedirs(OUT, exist_ok=True)
    p = os.path.join(OUT, name)
    json.dump(obj, open(p, "w", encoding="utf-8"), indent=1, ensure_ascii=False, default=float)
    return p
