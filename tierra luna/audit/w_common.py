"""w_*: effect of the design questions still pending (computed in memory, nothing applied).

Shared helpers. Reuses the auditor-2 independent re-implementation (p2_model, checked
against the shipped bundle by p2_recompute and again by w0_reproduce) as a library. The
configuration is read ONCE into memory (snapshot hashes written to out/w_config_snapshot.json);
every option is a modification of that in-memory copy. Nothing in the repository is changed
except audit/w_*.py and audit/out/w_*. Deterministic; no network.
"""
from __future__ import annotations

import contextlib
import copy
import hashlib
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from p2_common import (BUNDLE, OUT, R_EARTH, R_MOON, TL, ROOT, dump, gc_km, jload, latlon,  # noqa: E402,F401
                       manifest, read_bin, tables)
import p2_model  # noqa: E402

MISSIONS = ["rover", "solar", "lunar_base"]
CFG_FILES = [os.path.join(TL, "engine", "engine_config.json"), os.path.join(TL, "mission_scoring.json"),
             os.path.join(TL, "engine", "datasets.json"), os.path.join(TL, "engine", "data", "artemis_iii_regions.geojson")]

_STATE = {}
_ZONES_ORIG = p2_model.zones
_DERIVED_ORIG = p2_model.derived


def sha(path):
    return hashlib.sha256(open(path, "rb").read()).hexdigest()


def load():
    """eng, ms, e, m read once (in-memory copies) + snapshot of the hashes."""
    if "eng" not in _STATE:
        snap = {os.path.relpath(p, ROOT): sha(p) for p in CFG_FILES}
        eng = jload(CFG_FILES[0])
        ms = jload(CFG_FILES[1])
        e, m = tables()
        _STATE.update(eng=eng, ms=ms, e=e, m=m, snap=snap)
        dump({"config_sha256_at_start": snap}, "w_config_snapshot.json")
    return copy.deepcopy(_STATE["eng"]), copy.deepcopy(_STATE["ms"]), _STATE["e"], _STATE["m"]


@contextlib.contextmanager
def patched(zone_override=None, earth_elev_mean=None, gate_fn=None):
    """Temporarily replace p2_model.zones / derived / gates_earth for one run.
    zone_override: {mission: bool mask(64800)}; earth_elev_mean: float (Earth reference for
    elevation_rel_m); gate_fn(e, mission, ms) -> bool mask replacing the funnel."""
    oz, od, og = p2_model.zones, p2_model.derived, p2_model.gates_earth

    def zones_cached(m, eng):
        if "zones" not in _STATE:
            _STATE["zones"] = _ZONES_ORIG(m, eng)
        return _STATE["zones"]
    p2_model.zones = zones_cached

    def derived_cached(e, m, eng):
        if "derived" not in _STATE:
            _STATE["derived"] = _DERIVED_ORIG(e, m, eng)
        ev, mv, notes = _STATE["derived"]
        return dict(ev), dict(mv), copy.deepcopy(notes)
    p2_model.derived = derived_cached
    if zone_override is not None:
        def zones(m, eng):
            z, extra = zones_cached(m, eng)
            z = dict(z)
            z.update(zone_override)
            return z, extra
        p2_model.zones = zones
    if earth_elev_mean is not None:
        def derived(e, m, eng):
            ev, mv, notes = derived_cached(e, m, eng)
            ee = p2_model.num(e, "elevation_m")
            ev["elevation_rel_m"] = ee - earth_elev_mean
            notes["elevation_body_mean"] = dict(notes["elevation_body_mean"], EARTH=earth_elev_mean)
            return ev, mv, notes
        p2_model.derived = derived
    if gate_fn is not None:
        p2_model.gates_earth = gate_fn
    try:
        yield
    finally:
        p2_model.zones, p2_model.derived, p2_model.gates_earth = oz, od, og


_ZONE_CACHE = {}


def run(mission, **kw):
    eng, ms, e, m = load()
    with patched(**kw):
        return p2_model.run(mission, e=e, m=m, eng=eng, ms=ms)


def base_run(mission):
    if mission not in _ZONE_CACHE:
        _ZONE_CACHE[mission] = run(mission)
    return _ZONE_CACHE[mission]


# --------------------------------------------------------------------------- names (bundle)
_NAMES = {}


def _names():
    if not _NAMES:
        base = read_bin("earth_base.bin")
        pdb = read_bin("earth_place_detail.bin")
        pd_json = jload(os.path.join(BUNDLE, "place_detail.json"))
        pl = jload(os.path.join(BUNDLE, "places.json"))
        mb = read_bin("moon_base.bin")
        iau = jload(os.path.join(BUNDLE, "iau_moon_features.json"))
        land = base["id"].astype(np.int64)
        np_idx = np.full(64800, -1)
        np_km = np.full(64800, np.nan)
        cc = np.full(64800, -1)
        np_idx[land] = np.nan_to_num(pdb["nearest_place"], nan=-1).astype(int)
        np_km[land] = pdb["nearest_place_km"]
        cc[land] = np.nan_to_num(base["country"], nan=-1).astype(int)
        _NAMES.update(np_idx=np_idx, np_km=np_km, cc=cc, places=pd_json["nearest_places"],
                      countries=pl["countries"], mf=np.nan_to_num(mb["feature"], nan=-1).astype(int),
                      mf_km=mb["feature_km"], iau=iau["name"], mreg=mb["region"])
    return _NAMES


def earth_name(cid):
    n = _names()
    i = n["np_idx"][cid]
    c = n["cc"][cid]
    country = n["countries"][c]["name"] if 0 <= c < len(n["countries"]) else None
    return {"place": n["places"][i] if i >= 0 else None, "km": round(float(n["np_km"][cid]), 1) if i >= 0 else None,
            "country": country}


def moon_name(mid):
    n = _names()
    i = n["mf"][mid]
    return {"feature": n["iau"][i] if i >= 0 else None, "km": round(float(n["mf_km"][mid]), 1) if i >= 0 else None}


# --------------------------------------------------------------------------- results
def ranked(r):
    """Indices into r arrays of paired cells ordered by rank."""
    idx = np.flatnonzero(r["rank"] > 0)
    return idx[np.argsort(r["rank"][idx], kind="mergesort")]


def row(r, i, rank=None):
    cid = int(r["ids"][i])
    t = int(r["twin"][i])
    la, lo = latlon(cid)
    ml, mo = latlon(t)
    return {"rank": int(r["rank"][i]) if rank is None else rank, "earth_id": f"E{cid}", "lat": float(la), "lon": float(lo),
            "earth_place": earth_name(cid), "moon_id": f"M{t}", "moon_lat": float(ml), "moon_lon": float(mo),
            "moon_feature": moon_name(t), "similarity": round(float(r["sim_pub"][i]), 2),
            "suitability": round(float(r["suit"][i]), 2), "final": float(r["final2"][i])}


def summary(r, n=5):
    o = ranked(r)
    return {"passing": int(len(r["ids"])), "paired": int((r["twin"] >= 0).sum()),
            "distinct_twins": int(len(np.unique(r["twin"][r["twin"] >= 0]))), "zone_cells": int(len(r["zone"])),
            "top": [row(r, i) for i in o[:n]]}


def audio_top5():
    a = jload(os.path.join(ROOT, "docs", "AUDIO_TOP5.json"))
    return {mi: [(p["rank"], p["earth_cell_id"], p["moon_cell_id"]) for p in a["missions"][mi]["pairs"]] for mi in MISSIONS}


def compare_tracks(mission, top, r=None):
    """For each recorded track (rank k, Earth E, Moon M): does the option's rank k still hold the
    same Earth cell AND the same twin? r (a full run) gives the new rank of a cell that left.
    Returns per-track status and the list of tracks that no longer describe the pair at that rank."""
    rec = audio_top5()[mission]
    new = {t["rank"]: (t["earth_id"], t["moon_id"]) for t in top}
    pos_new = {t["earth_id"]: (t["rank"], t["moon_id"]) for t in top}
    out = []
    for k, eid, mid in rec:
        if new.get(k) == (eid, mid):
            st = "same"
        elif eid in pos_new:
            rk, tm = pos_new[eid]
            st = f"moves to {rk}" + ("" if tm == mid else f", twin {tm}")
        else:
            rk, tm = where(r, eid) if r is not None else (None, None)
            st = "leaves top 5" + (f" (now rank {rk}" + ("" if tm == mid else f", twin {tm}") + ")" if rk else (" (no twin / not ranked)" if r is not None else ""))
        out.append({"track": k, "earth": eid, "moon": mid, "status": st})
    return out, [o["track"] for o in out if o["status"] != "same"]


def where(r, eid_str):
    """Rank / twin of an Earth cell id string in a run (None if not paired)."""
    cid = int(eid_str[1:])
    i = np.searchsorted(r["ids"], cid)
    if i < len(r["ids"]) and r["ids"][i] == cid and r["twin"][i] >= 0:
        return int(r["rank"][i]), f"M{int(r['twin'][i])}"
    return None, None


def mission_bundle_ranked(mission):
    """Ranked rows of the shipped bundle (ids, rank, final, similarity, suitability, twin, lat, lon)."""
    from p2_common import mission_bundle
    base, eb, pr, pass_ids = mission_bundle(mission)
    rk = eb["rank"]
    idx = np.flatnonzero(np.isfinite(rk) & (rk > 0))
    idx = idx[np.argsort(rk[idx], kind="mergesort")]
    lat, lon = latlon(pass_ids[idx])
    return {"id": pass_ids[idx].astype(int), "rank": rk[idx].astype(int), "final": eb["final"][idx], "sim": eb["similarity"][idx],
            "suit": eb["suitability"][idx], "twin": eb["twin"][idx].astype(int), "lat": lat, "lon": lon}
