"""Honest limits as bundle texts, with figures computed from the data at build time
(decision of 2026-11-15 11:23 CET, point 4: keep and state honestly).

Every template lives in engine_config ``limit_texts``; this module only computes the
named figures (``facts``) and fills ``{placeholders}``. A template whose figures are
missing is never shipped with empty figures: the stability text falls back to its
``pending`` sentence (engine_config ``top5_stability``). No mission is named in code:
which missions a text applies to, the ice and water rules, the benchmark and the zone
regions are all configuration.
"""
from __future__ import annotations

import csv
import math
import re
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from engine.config import EngineConfig, resolve_path
from engine.gates import GateResult


# ----------------------------------------------------------------------------- formatting
def fmt_int(n: int) -> str:
    return f"{int(n):,}"


def fmt_pct(x: float, d: int = 1) -> str:
    return f"{x:.{d}f}"


def ordinal_list(items: List[str]) -> str:
    """'a', 'a and b', 'a, b and c'."""
    if not items:
        return ""
    return items[0] if len(items) == 1 else ", ".join(items[:-1]) + " and " + items[-1]


def fill(template: str, values: Dict[str, Any]) -> str:
    out = template
    for k, v in values.items():
        out = out.replace("{" + k + "}", str(v))
    left = re.findall(r"\{[a-z0-9_]+\}", out)
    if left:
        raise KeyError(f"unfilled placeholders {left} in {template[:60]!r}")
    return out


# ----------------------------------------------------------------------------- cell classes
def cell_classes(earth: pd.DataFrame, rules: Dict[str, Any]) -> Dict[str, np.ndarray]:
    """Boolean masks of the configured surface classes (engine_config limit_facts.cell_classes):
    each rule is a list of conditions joined by OR: {column, equals} or {column, at_least}."""
    out = {}
    for name, rule in rules.items():
        m = np.zeros(len(earth), dtype=bool)
        for c in rule["any_of"]:
            if c["column"] not in earth.columns:   # a table without the column: no cell is counted
                continue
            s = earth[c["column"]]
            if "equals" in c:
                if isinstance(c["equals"], str):
                    m |= (s.astype(str).str.strip().str.lower() == c["equals"].lower()).to_numpy()
                else:
                    m |= (pd.to_numeric(s, errors="coerce").to_numpy(dtype=np.float64) == float(c["equals"]))
            elif "at_least" in c:
                m |= np.nan_to_num(pd.to_numeric(s, errors="coerce").to_numpy(dtype=np.float64), nan=-np.inf) >= float(c["at_least"])
            else:
                raise ValueError(f"cell class {name}: unknown condition {c}")
        out[name] = m
    return out


# ----------------------------------------------------------------------------- external validation
def benchmark_sites(cfg: Dict[str, Any], grid) -> List[Dict[str, Any]]:
    """Sites of the benchmark CSV whose coordinates are not flagged unverified (the
    auditor's rule, engine_config external_validation.unverified_rule)."""
    rule = cfg["unverified_rule"]
    with open(resolve_path(cfg["benchmark_csv"]), encoding="utf-8", newline="") as fh:
        rows = list(csv.DictReader(fh))
    out = []
    for r in rows:
        cq = (r.get("coord_quality") or "").lower()
        ss = r.get("source_status") or ""
        bad = (rule["coord_quality_contains"] in cq or ss.upper().startswith(rule["source_status_starts_with"])
               or bool(re.search(rule["source_status_regex"], ss, re.I)))
        lat, lon = float(r["lat"]), float(r["lon"])
        row = min(int(math.floor(90.0 - lat)), grid.rows - 1)
        col = min(int(math.floor(lon + 180.0)), grid.cols - 1)
        out.append({"id": r["id"], "name": r["name"], "lat": lat, "lon": lon, "verified": not bad,
                    "cell": int(grid.cell_id(row, col))})
    return out


def _norm(name: str) -> str:
    for a, b in (("í", "i"), ("á", "a"), ("é", "e"), ("ó", "o"), ("ú", "u"), ("-", " ")):
        name = name.replace(a, b)
    return name.lower().strip()


def external_validation(res, earth_ids: np.ndarray, cfg: Dict[str, Any], mcfg: Dict[str, Any], grid) -> Dict[str, Any]:
    """Rank percentile (100 * (rank - 0.5) / ranked points, 0 = best) of the named sites of
    one mission, matched by name as rover_preset.validate_rover_ranking does."""
    import importlib

    mod = importlib.import_module(mcfg["names_module"])
    sites = [s for s in benchmark_sites(cfg, grid) if s["verified"]]
    n = int((res.rank > 0).sum())
    out = {}
    for role, attr in (("positives", mcfg["positives"]), ("mismatches", mcfg["mismatches"])):
        rows = []
        for name in getattr(mod, attr):
            hit = next((s for s in sites if _norm(name) in _norm(s["name"])), None)
            if hit is None:
                rows.append({"name": name, "benchmark_id": None, "verified_coordinates": False})
                continue
            i = int(np.searchsorted(earth_ids, hit["cell"]))
            ok = i < len(earth_ids) and earth_ids[i] == hit["cell"]
            rk = int(res.rank[i]) if ok else 0
            rows.append({"name": name, "benchmark_id": hit["id"], "benchmark_name": hit["name"], "cell": hit["cell"],
                         "verified_coordinates": True, "passes_funnel": bool(ok and res.earth_gates.passed[i]),
                         "fail": list(res.earth_gates.reasons[i]) if ok else [],
                         "rank": rk or None, "rank_percentile": round(100.0 * (rk - 0.5) / n, 1) if rk > 0 else None})
        out[role] = rows
    out["ranked_points"] = n
    return out


# ----------------------------------------------------------------------------- lunar zone regions
def twin_region_shares(moon: pd.DataFrame, twin_ids: List[int], cfg: Dict[str, Any], radius_km: float) -> Dict[int, Dict[str, Any]]:
    """For each lunar cell id: the configured region it shares most area with and that share
    of the cell (south-polar Lambert azimuthal equal-area projection on the body sphere,
    cell square densified along the parallels; the auditor's method,
    docs/stats_audit/7_efecto_decisiones_pendientes.md P1)."""
    import json as _json

    from shapely.geometry import Polygon, shape
    from shapely.ops import transform

    r_m = radius_km * 1000.0
    pole = float(cfg["projection_pole_lat"])

    def laea(lon, lat):
        lon = np.radians(np.asarray(lon, float))
        colat = np.radians(np.asarray(lat, float) - pole) if pole < 0 else np.radians(pole - np.asarray(lat, float))
        rho = 2 * r_m * np.sin(colat / 2)
        return rho * np.sin(lon), rho * np.cos(lon)

    with open(resolve_path(cfg["regions_file"]), encoding="utf-8") as fh:
        g = _json.load(fh)
    regions = [(f["properties"]["name"], transform(lambda x, y, z=None: laea(x, y), shape(f["geometry"])))
               for f in g["features"]]
    half = float(cfg["cell_deg"]) / 2.0
    k = int(cfg["densify_points"])
    out = {}
    for cid in twin_ids:
        la, lo = float(moon["lat_deg"].iat[cid]), float(moon["lon_deg"].iat[cid])
        lons = np.linspace(lo - half, lo + half, k)
        top = np.column_stack(laea(lons, np.full(k, la + half)))
        bot = np.column_stack(laea(lons[::-1], np.full(k, la - half)))
        cp = Polygon(np.vstack([top, bot]))
        best = None
        for name, poly in regions:
            if not poly.intersects(cp):
                continue
            sh = poly.intersection(cp).area / cp.area
            if best is None or sh > best[1]:
                best = (name, sh)
        if best is None:
            out[cid] = {"region": None, "share_of_cell": 0.0, "phrase": None, "text": None}
            continue
        phrase = cfg["phrase_in"] if best[1] >= float(cfg["in_min_share"]) else cfg["phrase_edge"]
        out[cid] = {"region": best[0], "share_of_cell": round(float(best[1]), int(cfg["share_decimals"])),
                    "phrase": phrase, "text": cfg["text"].replace("{phrase}", phrase).replace("{region}", best[0])}
    return out


# ----------------------------------------------------------------------------- facts per mission
def gates_without_effect(g: GateResult, land: np.ndarray, gate_vars: List[str]) -> Dict[str, int]:
    """Per gate variable: Earth land cells that fail ONLY that gate (removing the gate would
    add exactly these cells; 0 = the gate excludes no cell at this resolution)."""
    out = {v: 0 for v in gate_vars}
    for i in np.flatnonzero(land):
        r = g.reasons[i]
        if not r:
            continue
        vs = {c.rsplit(":", 1)[0] for c in r}
        if len(vs) == 1:
            v = next(iter(vs))
            if v in out:
                out[v] += 1
    return out


def stability_sentence(mid: str, top5_ids: List[int], cfg: Dict[str, Any]) -> Dict[str, Any]:
    """The stability text of one mission: the audited figures when every one is present and
    they describe the five shown, else the pending sentence (never empty figures)."""
    e = (cfg["missions"] or {}).get(mid) or {}
    need = ("ids", "in_top5_share", "in_top20_share", "simulations", "weights_pm10_survivors", "source")
    ok = e.get("status") == "audited" and all(e.get(k) is not None for k in need)
    ok = ok and list(e["ids"]) == list(top5_ids) and len(e["in_top5_share"]) == len(top5_ids) == len(e["in_top20_share"])
    if not ok:
        reason = ("figures not filled" if e.get("status") != "audited" else
                  "the audited five differ from the five shown" if e.get("ids") and list(e["ids"]) != list(top5_ids)
                  else "a figure is missing")
        return {"text": cfg["pending_sentence"], "status": "pending", "reason": reason, "source": None}
    per = [cfg["per_analog"].replace("{n}", str(k + 1)).replace("{top5}", fmt_pct(a)).replace("{top20}", fmt_pct(b))
           for k, (a, b) in enumerate(zip(e["in_top5_share"], e["in_top20_share"]))]
    text = fill(cfg["sentence"], {"simulations": fmt_int(e["simulations"]), "per_analog": "; ".join(per),
                                  "survivors": e["weights_pm10_survivors"], "count": len(top5_ids)})
    return {"text": text, "status": "audited", "reason": None, "source": e["source"]}


def _plain(var: str, names: Dict[str, str]) -> str:
    """Plain-words name of a column or criterion for a sentence a user reads."""
    return names.get(var, var.replace("_", " "))


def _reasons(codes: List[str], mission_cfg: Dict[str, Any], mid: str, names: Optional[Dict[str, str]] = None) -> str:
    """Gate failures in plain words ('slope (degrees) outside 0.5 to 15')."""
    names = names or {}
    out = []
    m = mission_cfg["missions"][mid]
    for c in codes:
        var, kind = c.rsplit(":", 1)
        g = m.get("gates", {}).get(var, mission_cfg.get("common_gates", {}).get(var, {}))
        if kind == "missing":
            out.append(f"no value of {_plain(var, names)}")
        elif kind in ("below_min", "above_max"):
            lo, hi = g.get("min"), g.get("max")
            rng = (f"{lo:g} to {hi:g}" if lo is not None and hi is not None else
                   f"at least {lo:g}" if lo is not None else f"at most {hi:g}")
            out.append(f"{_plain(var, names)} outside {rng}")
        else:
            out.append(f"{_plain(var, names)} not allowed")
    return ", ".join(out)


# ----------------------------------------------------------------------------- the build step
def build_limits(ds, results: Dict[str, Any], mission_cfg: Dict[str, Any], engine_cfg: EngineConfig,
                 land: np.ndarray) -> Dict[str, Any]:
    """Everything the decision of 2026-11-15 11:23 CET adds to the bundle: the five shown
    per mission (missions.json top5), the texts of engine_config limit_texts filled with
    figures computed here, the external validation per mission and the region share of
    the twins of the missions configured in twin_zone_regions."""
    from engine import top5 as t5

    earth, moon = ds.cells["EARTH"], ds.cells["MOON"]
    ids = earth["id"].to_numpy()
    lat, lon = earth["lat_deg"].to_numpy(dtype=np.float64), earth["lon_deg"].to_numpy(dtype=np.float64)
    radii = engine_cfg.v("body_radius_km")
    sel = engine_cfg.v("top5_selection")
    stab = engine_cfg.v("top5_stability")
    lf = engine_cfg.v("limit_facts")
    lt = engine_cfg.v("limit_texts")
    ev_cfg = engine_cfg.v("external_validation")
    tz = engine_cfg.v("twin_zone_regions")
    classes = cell_classes(earth, lf["cell_classes"])
    names = lt.get("plain_names", {})
    alpha = float(engine_cfg.v("mix_factor"))
    texts: Dict[str, Any] = {}
    top5: Dict[str, Any] = {}
    rows5: Dict[str, List[int]] = {}
    ext: Dict[str, Any] = {}
    region_share: Dict[str, Dict[int, Dict[str, Any]]] = {}
    for mid, res in results.items():
        rule = {"count": sel["count"], **sel["missions"][mid], "sentence": sel["sentences"][sel["missions"][mid]["rule"]]}
        cols = {sk["column"]: pd.to_numeric(earth[sk["column"]], errors="coerce").to_numpy(dtype=np.float64)
                for sk in (rule.get("skips") or {}).values()}
        rows = t5.select(res.rank, lat, lon, rule, cols, res.final_published, res.similarity_pct, ids)
        rows5[mid] = rows
        top5[mid] = t5.top5_block(rule, rows, ids, res.rank, float(radii[sel["radius_body"]]), int(sel["km_decimals"]))
        tied = t5.top_tie(res.rank, res.final_published)
        skipm = t5.skip_mask(rule, cols, len(ids))
        top5[mid].update({
            "rule_id": rule["rule"],
            "skips": {k: {"enabled": bool(v.get("enabled")), "column": v["column"], "op": v["op"], "value": v["value"]}
                      for k, v in (rule.get("skips") or {}).items()},
            "top_tie_n": int(len(tied)), "top_tie_n_after_skips": int((~skipm[tied]).sum()),
            "alternative_rule": rule.get("alternative_rule"),
        })
        top5[mid]["rule"] = top5[mid]["rule"].replace("{tied_n}", fmt_int(top5[mid]["top_tie_n_after_skips"])).replace(
            "{tied_all_n}", fmt_int(top5[mid]["top_tie_n"])).replace("{min_pair_deg}", _min_pair_deg(rows, lat, lon))
        alt = rule.get("alternative_rule")
        if alt:
            arule = {"count": sel["count"], **sel["missions"][mid], "rule": alt, "sentence": sel["sentences"][alt]}
            arows = t5.select(res.rank, lat, lon, arule, cols, res.final_published, res.similarity_pct, ids)
            top5[mid]["alternative"] = {"rule_id": alt, "ids": [int(ids[i]) for i in arows],
                                        "overall_ranks": [int(res.rank[i]) for i in arows],
                                        "rule": t5.top5_block(arule, arows, ids, res.rank, float(radii[sel["radius_body"]]),
                                                              int(sel["km_decimals"]))["rule"]}
        # (a) order and wording of the five
        t = lt["list_order"]
        five = (t.get("five_sentences") or {}).get(rule["rule"], "These are five of the highest-scoring analogs in our model, not a proven best.")
        if rule["rule"] == "spread_within_top_tie" and top5[mid]["top_tie_n_after_skips"] <= int(rule["count"]):
            five = t["five_sentences"]["rank_with_skips"]
        five = five.replace("{tied_n}", fmt_int(top5[mid]["top_tie_n"])).replace(
            "{deg}", f"{float(rule.get('min_separation_deg') or 0):g}").replace(
            "{ranks}", ordinal_list([str(int(res.rank[i])) for i in rows]))
        texts[f"list_order_{mid}"] = {"missions": [mid], "show": t["show"], "decision": t["decision"],
                                      "text": fill(t["text"], {"alpha_pct": f"{100 * alpha:g}", "rest_pct": f"{100 * (1 - alpha):g}",
                                                               "five_sentence": five})}
        # (b) stability
        s = stability_sentence(mid, top5[mid]["ids"], stab)
        texts[f"top5_stability_{mid}"] = {"missions": [mid], "show": stab["show"], "decision": stab["decision"],
                                          "text": s["text"], "status": s["status"], "status_reason": s["reason"],
                                          "source": s["source"]}
        # (e) external validation
        mv = ev_cfg["missions"].get(mid)
        if mv and mv.get("names_module"):
            ev = external_validation(res, ids, ev_cfg, mv, ds.grid)
            ext[mid] = ev
            pos = []
            for r in ev["positives"]:
                if not r["verified_coordinates"]:
                    continue
                if r["rank"]:
                    pos.append(mv["ranked_item"].replace("{name}", r["name"]).replace("{pct}", fmt_pct(r["rank_percentile"])))
                else:
                    pos.append(mv["unranked_item"].replace("{name}", r["name"]).replace(
                        "{reasons}", _reasons(r["fail"], mission_cfg, mid, names) or "not paired"))
            mis = []
            for r in ev["mismatches"]:
                if not r["verified_coordinates"]:
                    continue
                mis.append(mv["ranked_item"].replace("{name}", r["name"]).replace("{pct}", fmt_pct(r["rank_percentile"]))
                           if r["rank"] else mv["unranked_item"].replace("{name}", r["name"]).replace(
                               "{reasons}", _reasons(r["fail"], mission_cfg, mid, names)))
            unver = [r["name"] for r in ev["positives"] + ev["mismatches"] if not r["verified_coordinates"]]
            texts[f"external_validation_{mid}"] = {
                "missions": [mid], "show": ev_cfg["show"], "decision": ev_cfg["decision"], "source": mv["source"],
                "text": fill(mv["text"], {"positives": ordinal_list(pos), "mismatches": ordinal_list(mis),
                                          "unverified": ordinal_list(unver), "ranked": fmt_int(ev["ranked_points"])})}
        elif mv:
            texts[f"external_validation_{mid}"] = {"missions": [mid], "show": ev_cfg["show"], "decision": ev_cfg["decision"],
                                                   "source": mv["source"], "text": mv["text"]}
        # (h) region of each twin
        if mid in tz:
            cfg = tz[mid]
            tw = sorted({int(x) for x in res.twin_id[res.rank > 0] if x >= 0})
            region_share[mid] = twin_region_shares(moon, tw, cfg, float(radii["MOON"]))
    # (d) surface classes in the ranking, per configured mission
    for key, t in lt.items():
        if t.get("kind") != "surface_classes":
            continue
        for mid in t["missions"]:
            res = results[mid]
            rk = res.rank
            ranked = rk > 0
            shown = set(rows5[mid])
            vals: Dict[str, Any] = {"ranked_n": fmt_int(ranked.sum()), "top_n": t["top_n"]}
            for cname in t["classes"]:
                m = classes[cname] & ranked
                best = int(rk[m].min()) if m.any() else None
                in_top = int((m & (rk <= int(t["top_n"]))).sum())
                in5 = sum(1 for i in shown if classes[cname][i])
                vals[f"{cname}_n"] = fmt_int(m.sum())
                vals[f"{cname}_best"] = fmt_int(best) if best else "none"
                vals[f"{cname}_top"] = fmt_int(in_top)
                vals[f"{cname}_shown"] = fmt_int(in5)
                vals[f"{cname}_shown_ids"] = ", ".join(f"E{ids[i]} (number {int(rk[i])})" for i in rows5[mid] if classes[cname][i]) or "none"
            texts[f"{key}_{mid}"] = {"missions": [mid], "show": t["show"], "decision": t["decision"], "source": t["source"],
                                     "text": fill(t["text"], vals), "figures": vals}
    # ties at the head of the ranking (the fragility of the five)
    t = lt.get("ties_at_top")
    if t:
        sd = int(engine_cfg.v("export_decimals")["score"])
        for mid, res in results.items():
            rk = res.rank
            if not (rk == 1).any():
                continue
            top = float(res.final_published[rk == 1][0])
            tied = int(np.sum((rk > 0) & (res.final_published == top)))
            if tied >= int(t["min_tied"]):
                vals = {"tied_n": fmt_int(tied), "score": f"{top:.{sd}f}"}
                texts[f"ties_at_top_{mid}"] = {"missions": [mid], "show": t["show"], "decision": t["decision"],
                                               "source": t["source"], "text": fill(t["text"], vals), "figures": vals}
    # (f) the common elevation gate on Earth land below sea level
    t = lt["gate_elevation_land"]
    el = pd.to_numeric(earth[t["elevation_column"]], errors="coerce").to_numpy(dtype=np.float64)
    mf = pd.to_numeric(earth[t["land_share_column"]], errors="coerce").to_numpy(dtype=np.float64)
    gmin = float(mission_cfg["common_gates"][t["gate"]]["min"])
    lmin = float(mission_cfg["common_gates"][t["land_share_gate"]]["min"])
    below = np.isfinite(el) & (el < gmin)
    vals = {"below_n": fmt_int(below.sum()), "below_land_n": fmt_int((below & (np.nan_to_num(mf, nan=-1) >= lmin)).sum()),
            "gate_min": f"{gmin:g}", "land_min_pct": f"{100 * lmin:g}"}
    texts["gate_elevation_land"] = {"show": t["show"], "decision": t["decision"], "source": t["source"],
                                    "text": fill(t["text"], vals), "figures": vals}
    # (g) numbers without effect at this resolution
    t = lt["numbers_without_effect"]
    titles = engine_cfg.v("mission_titles_short")
    inert = []
    for mid, res in results.items():
        m = mission_cfg["missions"][mid]
        gvars = list(dict.fromkeys(list(mission_cfg.get("common_gates", {})) + list(m.get("gates", {}))))
        only = {}
        for i in np.flatnonzero(land):
            r = res.earth_gates.reasons[i]
            if r and len({c.rsplit(":", 1)[0] for c in r}) == 1:
                for c in set(r):
                    only[c] = only.get(c, 0) + 1
        parts = []
        for v in gvars:
            g = m.get("gates", {}).get(v, mission_cfg.get("common_gates", {}).get(v, {}))
            for bound, kind in (("min", "below_min"), ("max", "above_max")):
                if g.get(bound) is not None and only.get(f"{v}:{kind}", 0) == 0:
                    parts.append(f"{_plain(v, names)} {'at least' if bound == 'min' else 'at most'} {g[bound]:g}")
            for bound, kind in (("allow", "not_allowed"), ("exclude", "excluded")):
                if g.get(bound) and only.get(f"{v}:{kind}", 0) == 0:
                    parts.append(f"{_plain(v, names)} {'in' if bound == 'allow' else 'not in'} {', '.join(g[bound])}")
        if parts:
            inert.append(f"{titles.get(mid, mid)}: {', '.join(parts)}")
    unread = []
    for mid in results:
        m = mission_cfg["missions"][mid]
        keys = [k for k in t["unread_keys"] if m.get(k)]
        if keys:
            unread.append(f"{titles.get(mid, mid)}: {', '.join(t['unread_labels'][k] for k in keys)}")
    vals = {"inert_gates": "; ".join(inert) or "none", "unread_values": "; ".join(unread) or "none"}
    texts["numbers_without_effect"] = {"show": t["show"], "decision": t["decision"], "source": t["source"],
                                       "text": fill(t["text"], vals), "figures": vals}
    # (h) the zone rule of the twins' regions
    for mid, shares in region_share.items():
        t = lt["zone_edge"]
        edge = sum(1 for s in shares.values() if s["phrase"] == tz[mid]["phrase_edge"])
        if "real" not in results[mid].extra:
            continue
        zc = int(results[mid].extra["real"]["zone_cells"])
        vals = {"zone_cells": fmt_int(zc), "edge_n": fmt_int(edge), "twins_n": fmt_int(len(shares)),
                "in_min_pct": f"{100 * float(tz[mid]['in_min_share']):g}"}
        texts[f"zone_edge_{mid}"] = {"missions": [mid], "show": t["show"], "decision": t["decision"], "source": t["source"],
                                     "text": fill(t["text"], vals), "figures": vals}
    # (i) texts of the decisions of 11:28, 11:36 and 11:51 CET (kind 'static' or 'computed:<name>')
    applied = ((engine_cfg.v("criteria_sets") or {}).get("applied", {}) if engine_cfg.criteria_sets is not None else {})
    for key, t in lt.items():
        kind = t.get("kind") or ""
        if not (kind == "static" or kind.startswith("computed:")):
            continue
        mids = [m for m in t.get("missions", list(results)) if m in results]
        if t.get("missions") and not mids:
            continue
        if t.get("criteria_set") and any((applied.get(m) or {}).get("set") != t["criteria_set"] for m in mids):
            continue  # the text describes a criteria set this build does not use
        vals = _computed_figures(kind.split(":", 1)[1], t, results, earth, mission_cfg, engine_cfg, top5, applied, rows5) \
            if kind.startswith("computed:") else {}
        if vals is None:
            continue
        texts[key] = {**({"missions": mids} if t.get("missions") else {}), "show": t["show"], "decision": t["decision"],
                      "source": t["source"], "text": fill(t["text"], vals), "figures": vals}
    return {"texts": texts, "top5": top5, "top5_rows": rows5, "external_validation": ext, "region_share": region_share}


def _cell_rows(earth: pd.DataFrame, sites: List[Dict[str, Any]], grid_deg: float = 1.0) -> List[Optional[int]]:
    """Row of the 1-degree Earth cell holding each site (lat, lon), or None."""
    ids = earth["id"].to_numpy()
    out = []
    for st in sites:
        r = int((90.0 - float(st["lat"])) // grid_deg)
        c = int((float(st["lon"]) + 180.0) // grid_deg)
        k = np.flatnonzero(ids == r * int(360 / grid_deg) + c)
        out.append(int(k[0]) if k.size else None)
    return out


def _computed_figures(name: str, t: Dict[str, Any], results: Dict[str, Any], earth: pd.DataFrame,
                      mission_cfg: Dict[str, Any], engine_cfg: EngineConfig, top5: Dict[str, Any],
                      applied: Dict[str, Any], rows5: Optional[Dict[str, List[int]]] = None) -> Optional[Dict[str, Any]]:
    """Figures of one computed limits text (recomputed at every build; never typed)."""
    if name == "soft_column_percentiles":  # p10 / p90 of a soft column over the mission's passing points
        res = results[t["mission"]]
        if t["column"] not in earth.columns or t["column"] not in res.earth_suit.utilities:
            return None
        ok = np.isfinite(res.earth_suit.score)
        v = pd.to_numeric(earth[t["column"]], errors="coerce").to_numpy(dtype=np.float64)[ok]
        fin = np.isfinite(v)
        return {"passing_n": fmt_int(ok.sum()), "missing_n": fmt_int((~fin).sum()),
                "p10": f"{np.percentile(v[fin], 10):.3f}", "p90": f"{np.percentile(v[fin], 90):.3f}"}
    if name == "site_values":  # a column at named sites (polar stations)
        if t["column"] not in earth.columns:
            return None
        rows = _cell_rows(earth, t["sites"])
        col = pd.to_numeric(earth[t["column"]], errors="coerce").to_numpy(dtype=np.float64)
        parts = []
        for st, k in zip(t["sites"], rows):
            v = col[k] if k is not None else np.nan
            parts.append(f"{st['name']} {v:.1f} {t['unit']}" if np.isfinite(v) else f"{st['name']} no value in the table")
        res = results[t["mission"]]
        gmin = float(mission_cfg["missions"][t["mission"]]["gates"][t["column"]]["min"])
        return {"sites": "; ".join(parts), "gate_min": f"{gmin:g}"}
    if name == "spearman_soft":  # Spearman between two utilities over the passing points
        res = results[t["mission"]]
        if any(x not in res.earth_suit.utilities for x in t["variables"]):
            return None
        a, b = (res.earth_suit.utilities[x] for x in t["variables"])
        ok = np.isfinite(a) & np.isfinite(b) & np.isfinite(res.earth_suit.score)
        ra = pd.Series(a[ok]).rank().to_numpy()
        rb = pd.Series(b[ok]).rank().to_numpy()
        rho = float(np.corrcoef(ra, rb)[0, 1])
        w = res.earth_suit.weights
        return {"rho": f"{rho:.2f}", "w1_pct": f"{100 * w[t['variables'][0]]:g}", "w2_pct": f"{100 * w[t['variables'][1]]:g}",
                "passing_n": fmt_int(ok.sum())}
    if name == "rover_tie":
        res = results[t["mission"]]
        tb = top5[t["mission"]]
        ranked = res.rank > 0
        best = float(res.final_published[ranked].max())
        return {"tied_n": fmt_int(tb["top_tie_n"]), "tied_kept_n": fmt_int(tb["top_tie_n_after_skips"]),
                "score": f"{best:.2f}", "ranked_n": fmt_int(ranked.sum()), "rule": tb["rule"]}
    if name == "suitability_saturation":  # criteria saturated by the points tied at the top
        mid = t["mission"]
        res = results[mid]
        names = engine_cfg.v("limit_texts").get("plain_names", {})
        U = res.earth_suit.utilities
        w = res.earth_suit.weights
        soft = mission_cfg["missions"][mid]["soft"]
        ranked = res.rank > 0
        tied = np.zeros(len(ranked), dtype=bool)
        tied[_top_tie_rows(res)] = True
        sat = {k: ranked & (np.asarray(u) >= 1.0 - 1e-9) for k, u in U.items()}
        allsat = np.logical_and.reduce(list(sat.values()))
        suit = np.asarray(res.earth_suit.score, dtype=np.float64)
        crit = "; ".join(f"{_plain(k, names)} {100 * w[k]:g} %, full marks at {soft[k]['good']:g} or "
                         f"{'less' if soft[k]['good'] < soft[k]['bad'] else 'more'}" for k in U)
        per = "; ".join(f"{_plain(k, names)} {fmt_int(sat[k].sum())}" for k in U)
        def rng(col, d):
            v = pd.to_numeric(earth[col], errors="coerce").to_numpy(dtype=np.float64)[tied]
            return f"{np.nanmin(v):.{d}f} to {np.nanmax(v):.{d}f}"
        cols = list(U)
        rows = _cell_rows(earth, t["sites"])
        j = int(min(np.flatnonzero(tied), key=lambda k: res.rank[k]))
        ids = earth["id"].to_numpy()
        def site(label, k):
            parts = []
            for c in cols:
                v = float(pd.to_numeric(earth[c], errors="coerce").iloc[k])
                u = float(U[c][k])
                parts.append(f"{_plain(c, names)} {v:.3g}, utility {u:.2f}, {100 * w[c] * (1 - u):.1f} points lost")
            return (f"{label} (cell E{int(ids[k])}, number {fmt_int(res.rank[k])}, similarity {res.similarity_pct[k]:.2f}, "
                    f"suitability {suit[k]:.2f}): " + "; ".join(parts))
        ex = [site(st["name"], k) for st, k in zip(t["sites"], rows) if k is not None and res.rank[k] > 0]
        ex.append(site("against the tied site " + f"number {int(res.rank[j])}", j))
        return {"tied_n": fmt_int(tied.sum()), "ranked_n": fmt_int(ranked.sum()), "sat_all_n": fmt_int((allsat & tied).sum()),
                "sat_all_ranked_n": fmt_int(allsat.sum()), "suit100_n": fmt_int((ranked & (np.round(suit, 2) >= 100.0)).sum()),
                "criteria": crit, "per_criterion": per,
                "slope_range": rng(cols[0], 3), "rough_range": rng(cols[1], 2), "bare_range": rng(cols[2], 3),
                "examples": "; ".join(ex)}
    if name == "top5_rule_parts":  # what each part of the five-selection rule removes
        sel = engine_cfg.v("top5_selection")
        titles = engine_cfg.v("mission_titles_short")
        lat = earth["lat_deg"].to_numpy(dtype=np.float64)
        lon = earth["lon_deg"].to_numpy(dtype=np.float64)
        parts = {"ice": [], "land": [], "sep": []}
        deg = None
        for mid, res in results.items():
            r = sel["missions"][mid]
            sk = r.get("skips") or {}
            ranked = res.rank > 0
            tied = np.zeros(len(ranked), dtype=bool)
            tied[_top_tie_rows(res)] = True
            def cnt(key):
                if key not in sk:
                    return None
                c = pd.to_numeric(earth[sk[key]["column"]], errors="coerce").to_numpy(dtype=np.float64)
                x = float(sk[key]["value"])
                m = np.isfinite(c) & ((c >= x) if sk[key]["op"] == ">=" else (c < x))
                return m
            for key, label in (("ice", "ice"), ("water", "land")):
                m = cnt(key)
                if m is None:
                    continue
                st = "" if sk[key].get("enabled") else " (switched off)"
                if r["rule"] == "spread_within_top_tie" and tied.sum() > int(sel["count"]):
                    parts[label].append(f"{titles.get(mid, mid)}{st} {fmt_int((m & tied).sum())} of the {fmt_int(tied.sum())} sites tied at the top "
                                        f"and {fmt_int((m & ranked).sum())} of the {fmt_int(ranked.sum())} ranked points")
                else:
                    parts[label].append(f"{titles.get(mid, mid)}{st} {fmt_int((m & ranked).sum())} of the {fmt_int(ranked.sum())} ranked points")
            if r.get("min_separation_deg") is not None:
                deg = float(r["min_separation_deg"])
            sel5 = (rows5 or {}).get(mid, [])
            if r["rule"] == "spread_within_top_tie" and tied.sum() > int(sel["count"]):
                parts["sep"].append(f"{titles.get(mid, mid)} none (the five are chosen as far apart as possible among the tied sites; "
                                    f"the closest two are {_min_pair_deg(sel5, lat, lon)} degrees apart)")
            elif sel5:
                last = max(int(res.rank[i]) for i in sel5)
                skip = np.zeros(len(ranked), dtype=bool)
                for key in ("ice", "water"):
                    m = cnt(key)
                    if m is not None and sk[key].get("enabled"):
                        skip |= m
                above = ranked & (res.rank <= last) & ~skip
                n_sep = int(above.sum()) - len(sel5)
                parts["sep"].append(f"{titles.get(mid, mid)} {fmt_int(n_sep)} points above the fifth one shown")
        return {k: "; ".join(v) or "none" for k, v in parts.items()} | {"deg": f"{deg:g}" if deg is not None else "2"}
    if name == "deviations_table":
        rows = []
        for mid, info in applied.items():
            for d in info["deviations"]:
                def show(x):
                    if x is None:
                        return "not used (weight 0)"
                    return ", ".join(f"{k} {x[k]:g}" if isinstance(x[k], (int, float)) else f"{k} {x[k]}"
                                     for k in ("weight", "bad", "good") if k in x) or "map " + ", ".join(
                        f"{k} {v:g}" for k, v in x.get("map", {}).items())
                rows.append(f"{engine_cfg.v('mission_titles_short').get(mid, mid)} | {d['criterion']} | {show(d['team'])} | "
                            f"{show(d['ours'])} | {d['reason']} | {d['source']}")
        if not rows:
            return None
        sets = "; ".join(f"{engine_cfg.v('mission_titles_short').get(m, m)}: {i['set']}" for m, i in applied.items())
        return {"rows": " || ".join(rows), "n": fmt_int(len(rows)), "sets": sets}
    raise ValueError(f"unknown computed limits text {name!r}")


def _top_tie_rows(res) -> np.ndarray:
    """Rows of ranked points whose published final equals the best one."""
    from engine import top5 as t5

    return t5.top_tie(res.rank, res.final_published)


def _min_pair_deg(rows: List[int], lat: np.ndarray, lon: np.ndarray) -> str:
    """Smallest great-circle angle between two of the five shown, 1 decimal."""
    from engine import top5 as t5

    if len(rows) < 2:
        return "n/a"
    d = [float(t5.central_angle_deg(float(lat[a]), float(lon[a]), lat[[b]], lon[[b]])[0])
         for k, a in enumerate(rows) for b in rows[k + 1:]]
    return f"{min(d):.1f}"
