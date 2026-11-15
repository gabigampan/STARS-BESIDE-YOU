"""ra_rover_common: independent Rover model for the re-audit (audit 9).

Own code path, not the engine: built on the first audit's independent implementation
(audit/p5_common.py: tables, column resolution, funnel, suitability, derived values),
adapted here to the corrected Rover rules:
  * similarity variables and weights read from engine_config.json real_value_similarity.missions.rover
    (or from the engine_patch of a criteria set, e.g. 'audited_morning');
  * per-variable score  s = exp(-0.5*(d/tol)^2)                 (no uncertainty_scale, morning)
                        s = exp(-0.5*max(0, d/sigma - 1)^2)      (uncertainty_scale.sigma, corrected)
  * pair filter: key |d| <= tol, secondary |d| <= 2 tol (filter_bound_multiplier);
  * twin: highest weighted score (full precision); ties -> smallest sum (d/sigma)^2 (corrected) ->
    lowest lunar id (zone cells are id-sorted, so first index);
  * published per-variable score rounded to score_decimals, similarity = 100*sum w s, final = a*sim+(1-a)*suit,
    published to 2 decimals; rank by published final, ties by Earth id;
  * the five: 'by_rank', 'min_separation', 'rank_with_skips', 'spread_within_top_tie'.
Nothing of tierra luna/engine is imported. The bundle is read only for comparison.
"""
from __future__ import annotations

import copy
import json
import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import p5_common as C  # noqa: E402

TL, REPO, OUT = C.TL, C.REPO, C.OUT
SCRATCH_BUNDLE_MORNING = os.environ.get("RA_MORNING_BUNDLE", "")
R_EARTH = 6371.0


def load_config():
    return json.load(open(os.path.join(TL, "engine", "engine_config.json"), encoding="utf-8"))


def params(criteria: str = "corrected"):
    """p5 parameters + Rover similarity block and top-5 rule of the requested criteria set."""
    P = C.load_params()
    ec = load_config()
    top5 = copy.deepcopy(ec["top5_selection"]["value"]["missions"]["rover"])
    cs = ec.get("criteria_sets", {}).get("value", {}).get("missions", {}).get("rover", {}).get("sets", {})
    if criteria in cs:
        patch = cs[criteria].get("engine_patch", {})
        if "real_value_similarity.missions.rover" in patch:
            P["missions"]["rover"]["sim"] = copy.deepcopy(patch["real_value_similarity.missions.rover"])
        if "top5_selection.missions.rover" in patch:
            top5 = copy.deepcopy(patch["top5_selection.missions.rover"])
    elif criteria != "corrected":
        raise KeyError(criteria)
    P["rover_top5"] = top5
    P["criteria"] = criteria
    P["sep_deg_default"] = 2.0
    return P


def tables(P):
    T = C.load_tables(P)
    raw = pd.read_csv(os.path.join(TL, "output_real", "earth_real_1deg.csv"), low_memory=False)
    raw["id"] = raw["row"].astype(int) * 360 + raw["col"].astype(int)
    raw = raw.sort_values("id").reset_index(drop=True)
    for c in ("snow_ice_frac", "mask_fraction", "lc_dominant_cci_code", "bare_frac", "rock_or_bare_frac", "elevation_m"):
        T["EARTH"]["raw_" + c] = raw[c].to_numpy()
    return T


def derived_rover(T, P):
    """Only what Rover needs (slope, roughness, relative elevation); same definitions as p5_common.derived."""
    d = {}
    for v in ("slope_deg", "roughness_m"):
        d[v] = {b: pd.to_numeric(T[b][v], errors="coerce").to_numpy(float) for b in T}
    d["elevation_rel_m"] = {}
    for b in T:
        x = pd.to_numeric(T[b]["elevation_m"], errors="coerce").to_numpy(float)
        mu = C.body_mean(x, T[b]["lat"].to_numpy(float), "coslat")
        d["elevation_rel_m"][b] = x - mu
    return d


def sim_spec(P):
    vs = [v for v in P["missions"]["rover"]["sim"]["variables"] if float(v.get("weight", 0)) > 0]
    names = [v["variable"] for v in vs]
    w = np.array([float(v["weight"]) for v in vs])
    tol = np.array([float(v["tolerance"]) for v in vs])
    role = [v["role"] for v in vs]
    bound = tol * np.array([P["mult"][r] for r in role])
    sig = [v.get("uncertainty_scale", {}).get("sigma") for v in vs]
    has_sig = all(s is not None for s in sig)
    sig = np.array([float(s) for s in sig]) if has_sig else None
    return dict(names=names, w=w, tol=tol, role=role, bound=bound, sig=sig)


def _score(d, S):
    if S["sig"] is not None:
        return np.exp(-0.5 * np.maximum(0.0, d / S["sig"] - 1.0) ** 2)
    return np.exp(-0.5 * (d / S["tol"]) ** 2)


def run(T, D, P, chunk=160, weights=None, suit_weights=None):
    """Full Rover model. weights: optional override of similarity weights (same order as sim_spec names);
    suit_weights: optional dict {soft variable: weight}."""
    E, M = T["EARTH"], T["MOON"]
    S = sim_spec(P)
    if weights is not None:
        S["w"] = np.asarray(weights, float)
    Pm = P
    if suit_weights is not None:
        Pm = copy.deepcopy(P)
        for k, v in suit_weights.items():
            Pm["missions"]["rover"]["soft"][k]["weight"] = float(v)
    passed = C.gate_pass(E, "EARTH", "rover", Pm)
    suit, utils = C.suitability(E, "rover", Pm, passed)
    zone = C.zone_mask(M, "rover", Pm)
    zi = np.flatnonzero(zone)
    pi = np.flatnonzero(passed)
    ev = np.column_stack([D[v]["EARTH"][pi] for v in S["names"]])
    mv = np.column_stack([D[v]["MOON"][zi] for v in S["names"]])
    n = len(pi)
    key = np.array([r == "key" for r in S["role"]])
    tw = np.full(n, -1)
    wsum = S["w"].sum()
    for a in range(0, n, chunk):
        b = min(n, a + chunk)
        d = np.abs(ev[a:b, None, :] - mv[None, :, :])
        fin = np.isfinite(d)
        dd = np.where(fin, d, np.inf)
        ok = np.all(np.where(key, fin & (dd <= S["bound"]), ~fin | (dd <= S["bound"])), axis=2)
        sc = _score(np.where(fin, d, 0.0), S)
        wq = np.where(fin, S["w"], 0.0)
        s = (sc * wq).sum(axis=2) / np.maximum(wq.sum(axis=2), 1e-300)
        s = np.where(ok, s, -np.inf)
        mx = s.max(axis=1)
        if S["sig"] is not None:
            z2 = (np.where(fin, d / S["sig"], 0) ** 2).sum(axis=2)
            z2 = np.where(ok & (s >= mx[:, None]), z2, np.inf)
            j = np.argmin(z2, axis=1)
        else:
            j = np.argmax(s, axis=1)
        tw[a:b] = np.where(np.isfinite(mx), j, -1)
    has = tw >= 0
    mvt = np.where(has[:, None], mv[np.maximum(tw, 0)], np.nan)
    diff = np.abs(ev - mvt)
    fin = np.isfinite(diff)
    sfull = _score(np.where(fin, diff, 0.0), S)
    sfull = np.where(fin, sfull, np.nan)
    sc6 = np.rint(sfull * 10 ** P["score_decimals"]) / 10 ** P["score_decimals"]
    wq = np.where(fin, S["w"], 0.0)
    den = wq.sum(axis=1)
    sc6z, sfz = np.nan_to_num(sc6), np.nan_to_num(sfull)
    sim = np.where(has & (den > 0), 100 * (sc6z * wq).sum(axis=1) / np.where(den > 0, den, 1), np.nan)
    sim_full = np.where(has & (den > 0), 100 * (sfz * wq).sum(axis=1) / np.where(den > 0, den, 1), np.nan)
    a = P["alpha"]
    fsc = a * sim + (1 - a) * suit[pi]
    pub = C.pyround(fsc, P["final_decimals"])
    ids = E["id"].to_numpy()[pi]
    okr = np.isfinite(pub)
    order = np.lexsort((ids, -np.where(okr, pub, -np.inf)))
    order = order[okr[order]]
    rank = np.zeros(n, dtype=int)
    rank[order] = np.arange(1, len(order) + 1)
    return {"passed": passed, "pi": pi, "ids": ids, "suit": suit[pi], "sim": sim, "sim_full": sim_full, "final": fsc,
            "final_pub": pub, "rank": rank, "twin": np.where(has, M["id"].to_numpy()[zi][np.maximum(tw, 0)], -1),
            "scores": sc6, "ev": ev, "mvt": mvt, "diff": diff, "names": S["names"], "zone_n": int(zone.sum()),
            "utils": {k: v[pi] for k, v in utils.items()}, "lat": E["lat"].to_numpy()[pi], "lon": E["lon"].to_numpy()[pi],
            "snow": T["EARTH"]["raw_snow_ice_frac"].to_numpy(float)[pi], "land": T["EARTH"]["raw_mask_fraction"].to_numpy(float)[pi]}


def gc_deg(la1, lo1, la2, lo2):
    la1, lo1, la2, lo2 = map(np.radians, (la1, lo1, la2, lo2))
    c = np.sin(la1) * np.sin(la2) + np.cos(la1) * np.cos(la2) * np.cos(lo1 - lo2)
    return np.degrees(np.arccos(np.clip(c, -1, 1)))


def _skipped(r, rule):
    sk = rule.get("skips", {})
    bad = np.zeros(len(r["pi"]), dtype=bool)
    if sk.get("ice", {}).get("enabled"):
        v = float(sk["ice"]["value"])
        bad |= np.nan_to_num(r["snow"], nan=-1.0) >= v
    if sk.get("water", {}).get("enabled"):
        v = float(sk["water"]["value"])
        bad |= np.nan_to_num(r["land"], nan=1.0) < v
    return bad


def five(r, P, rule=None):
    """Returns (list of positions into r arrays, info dict)."""
    rule = rule or P["rover_top5"]
    kind = rule["rule"]
    order = np.argsort(np.where(r["rank"] > 0, r["rank"], 10 ** 9), kind="stable")
    order = order[r["rank"][order] > 0]
    sep = float(rule.get("min_separation_deg", P["sep_deg_default"]))
    if kind == "by_rank":
        return [int(k) for k in order[:5]], {"rule": kind}
    bad = _skipped(r, rule) if kind in ("rank_with_skips", "spread_within_top_tie") else np.zeros(len(r["pi"]), bool)

    def greedy(cands):
        out = []
        for k in cands:
            if bad[k]:
                continue
            if all(gc_deg(r["lat"][k], r["lon"][k], r["lat"][j], r["lon"][j]) >= sep for j in out):
                out.append(int(k))
            if len(out) == 5:
                break
        return out

    if kind in ("min_separation", "rank_with_skips"):
        return greedy(order), {"rule": kind}
    if kind == "spread_within_top_tie":
        top = np.nanmax(r["final_pub"])
        tied_all = np.flatnonzero(r["final_pub"] == top)
        tied = tied_all[~bad[tied_all]]
        info = {"rule": kind, "top": float(top), "tied_all": int(len(tied_all)), "tied_eligible": int(len(tied))}
        if len(tied) <= 5:
            info["fallback"] = rule.get("alternative_rule", "rank_with_skips")
            return greedy(order), info
        ids = r["ids"][tied]
        o = np.lexsort((ids, -r["sim_full"][tied]))
        ch = [int(o[0])]
        la, lo = r["lat"][tied], r["lon"][tied]
        dmin = gc_deg(la, lo, la[ch[0]], lo[ch[0]])
        while len(ch) < 5:
            c = np.lexsort((ids, -dmin))
            c = [x for x in c if x not in ch][0]
            ch.append(int(c))
            dmin = np.minimum(dmin, gc_deg(la, lo, la[c], lo[c]))
        sel = [int(tied[c]) for c in ch]
        info["min_sep_deg"] = float(min(gc_deg(r["lat"][a], r["lon"][a], r["lat"][b], r["lon"][b]) for a in sel for b in sel if a != b))
        return sel, info
    raise ValueError(kind)


def five_ids(r, P, rule=None):
    return [int(r["ids"][k]) for k in five(r, P, rule)[0]]


# ------------------------------------------------------------------ bundle readers
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


def bundle_rover(bdir):
    base = bundle_cols(bdir, "earth_base.bin")
    mb = bundle_cols(bdir, "earth_rover.bin")
    ids = base["id"][mb["land_index"].astype(int)].astype(int)
    out = {"ids": ids, **mb}
    try:
        pr = bundle_cols(bdir, "earth_rover_pairs.bin")
        out["pairs"] = pr
    except (IndexError, KeyError):
        pass
    ms = json.load(open(os.path.join(bdir, "missions.json"), encoding="utf-8"))
    out["mission"] = [x for x in ms["missions"] if x["id"] == "rover"][0]
    return out


def compare(r, B):
    """Cell-by-cell comparison at published precision."""
    pos = {int(i): k for k, i in enumerate(r["ids"])}
    res = {"n_mine": int(len(r["ids"])), "n_bundle": int(len(B["ids"])),
           "same_passing_set": set(map(int, r["ids"])) == set(map(int, B["ids"]))}
    common = [(k, pos[int(i)]) for k, i in enumerate(B["ids"]) if int(i) in pos]
    bk = np.array([c[0] for c in common])
    mk = np.array([c[1] for c in common])

    def cmp(bv, mv, tol):
        bv, mv = np.asarray(bv, float), np.asarray(mv, float)
        both_nan = np.isnan(bv) & np.isnan(mv)
        dif = np.abs(np.nan_to_num(bv, nan=1e9) - np.nan_to_num(mv, nan=1e9))
        bad = ~both_nan & (dif > tol)
        nan_mis = int((np.isnan(bv) != np.isnan(mv)).sum())
        return {"mismatch": int(bad.sum()), "mismatch_beyond_one_last_digit": int((~both_nan & (dif > 2 * tol + 1e-9)).sum()),
                "nan_pattern_mismatch": nan_mis,
                "max_abs_diff": float(np.max(np.where(both_nan | (np.isnan(bv) != np.isnan(mv)), 0, dif))) if len(dif) else 0.0}

    res["suitability"] = cmp(B["suitability"][bk], C.pyround(r["suit"][mk], 2), 0.0051)
    res["similarity"] = cmp(B["similarity"][bk], C.pyround(r["sim"][mk], 2), 0.0051)
    res["final"] = cmp(B["final"][bk], r["final_pub"][mk], 0.0051)
    res["rank"] = cmp(B["rank"][bk], np.where(r["rank"][mk] > 0, r["rank"][mk], np.nan), 0)
    res["twin"] = cmp(B["twin"][bk], np.where(r["twin"][mk] >= 0, r["twin"][mk], np.nan), 0)
    for q, v in enumerate(r["names"]):
        col = "s." + v
        if col in B:
            res["score_" + v] = cmp(B[col][bk], r["scores"][mk, q], 1.01e-6)
    if "pairs" in B:
        pr = B["pairs"]
        for q, v in enumerate(r["names"]):
            for part, arr in (("earth", r["ev"][:, q]), ("moon", r["mvt"][:, q]), ("diff", r["diff"][:, q])):
                c = f"{v}.{part}"
                if c in pr and len(pr[c]) == len(B["ids"]):
                    res["pairs_" + c] = cmp(pr[c][bk], arr[mk].astype(np.float32).astype(float), 1e-3)
    return res


def diff_table(r):
    S_ok = r["twin"] >= 0
    out = []
    for q, v in enumerate(r["names"]):
        d = r["diff"][S_ok, q]
        out.append({"variable": v, "n_pairs": int(S_ok.sum()), "median": float(np.median(d)), "p90": float(np.percentile(d, 90)),
                    "max": float(np.max(d))})
    return out


def place_name_lookup():
    """Great-circle nearest place in the engine's place data (bundle places.json) for comparison with the bundle."""
    return json.load(open(os.path.join(C.BUNDLE, "places.json"), encoding="utf-8"))
