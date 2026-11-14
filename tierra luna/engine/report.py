"""Run report: per mission and body, what passed, why the rest failed, how the scores
are distributed, the top Earth cells and where known analog sites fall.

Pure functions on a computed build (engine.build.compute / build_bundle). The
benchmark site list is an input file (CSV with at least id, name, lat, lon); it is
never copied into code.
"""
from __future__ import annotations

import csv
from typing import Any, Dict, List, Optional

import numpy as np

from engine.dataset import Grid
from engine.export import rnd
from engine.export_v2 import missing_summary, quantiles
from engine.gates import top_reasons
from engine.pipeline import MissionResult


def read_sites(path: str) -> List[Dict[str, str]]:
    """Rows of a benchmark CSV (id, name, lat, lon, ...), in file order."""
    with open(path, encoding="utf-8", newline="") as fh:
        rows = list(csv.DictReader(fh))
    for r in rows:
        if not all(k in r for k in ("id", "name", "lat", "lon")):
            raise KeyError("benchmark CSV needs id, name, lat and lon columns")
    return rows


def site_cell(lat: float, lon: float, grid: Grid) -> Dict[str, Any]:
    """Grid cell containing a point: row, col, id and the cell centre."""
    row, col = grid.row_col_of(lat, lon)
    return {"row": row, "col": col, "id": int(grid.cell_id(row, col)),
            "lat_center": float(grid.lat_center(row)), "lon_center": float(grid.lon_center(col))}


def benchmark_lookup(sites: List[Dict[str, str]], results: Dict[str, MissionResult], earth_ids: np.ndarray,
                     grid: Grid, land: np.ndarray, earth_places: Dict[str, list]) -> List[Dict[str, Any]]:
    """For each site: its Earth cell, land flag, place label and, per mission, pass,
    failure reasons, rank (null when not ranked), number ranked, final and suitability."""
    pos = {int(i): k for k, i in enumerate(earth_ids)}
    out = []
    for s in sites:
        lat, lon = float(s["lat"]), float(s["lon"])
        cell = site_cell(lat, lon, grid)
        k = pos.get(cell["id"])
        item: Dict[str, Any] = {"site_id": s["id"], "name": s["name"], "lat": lat, "lon": lon,
                                "target_body": s.get("target_body"), "cell": cell,
                                "land_cell": bool(land[k]) if k is not None else False,
                                "country_code": earth_places["country_code"][k] if k is not None else None,
                                "missions": {}}
        for mid, r in results.items():
            if k is None:
                item["missions"][mid] = {"pass": False, "fail": ["cell not in table"], "rank": None}
                continue
            n_ranked = int((r.rank > 0).sum())
            item["missions"][mid] = {
                "pass": bool(r.earth_gates.passed[k]), "fail": list(r.earth_gates.reasons[k]),
                "rank": int(r.rank[k]) if r.rank[k] > 0 else None, "ranked_of": n_ranked,
                "rank_percentile": rnd(100.0 * r.rank[k] / n_ranked, 1) if r.rank[k] > 0 else None,
                "final": rnd(r.final_published[k], 2), "suitability": rnd(r.earth_suit.score[k], 2),
                "similarity": rnd(r.similarity_pct[k], 2), "twin": int(r.twin_id[k]) if r.twin_id[k] >= 0 else None,
            }
        out.append(item)
    return out


def top_cells(res: MissionResult, earth, moon, earth_places: Dict[str, list], moon_feat: Dict[str, list],
              n: int) -> List[Dict[str, Any]]:
    """The ``n`` best-ranked Earth cells with place, twin and scores."""
    order = [i for i in np.argsort(np.where(res.rank > 0, res.rank, np.iinfo(np.int64).max), kind="mergesort")
             if res.rank[i] > 0][:n]
    mpos = {int(i): p for p, i in enumerate(moon["id"])}
    out = []
    for i in order:
        tp = mpos[int(res.twin_id[i])]
        out.append({
            "rank": int(res.rank[i]), "id": int(earth["id"].iat[i]),
            "lat": float(earth["lat_deg"].iat[i]), "lon": float(earth["lon_deg"].iat[i]),
            "country": earth_places["country"][i], "country_code": earth_places["country_code"][i],
            "region": earth_places["region"][i], "nearest_place": earth_places["nearest_place"][i],
            "twin_id": int(res.twin_id[i]), "twin_lat": float(moon["lat_deg"].iat[tp]),
            "twin_lon": float(moon["lon_deg"].iat[tp]), "twin_feature": moon_feat["name"][tp],
            "twin_feature_km": rnd(moon_feat["distance_km"][tp], 1),
            "suitability": rnd(res.earth_suit.score[i], 2), "similarity": rnd(res.similarity_pct[i], 2),
            "final": rnd(res.final_published[i], 2), "confidence": res.confidence[i],
            "confidence_score": rnd(res.confidence_score[i], 3), "missing_n": int(res.earth_suit.missing_n[i]),
        })
    return out


def mission_report(res: MissionResult, earth, moon, land: np.ndarray, earth_places: Dict[str, list],
                   moon_feat: Dict[str, list], n_top: int, n_reasons: int, missing_suffix: str) -> Dict[str, Any]:
    """Counts, failure reasons, twins, distributions and the top cells of one mission."""
    from engine.export import _subset

    land_g = _subset(res.earth_gates, land)
    ranked = res.rank > 0
    passing = res.earth_gates.passed
    tw = res.twin_id[res.twin_id >= 0]
    return {
        "pass": {"EARTH": int(passing.sum()), "EARTH_land_cells": int(land.sum()),
                 "MOON": int(res.moon_gates.passed.sum()), "MOON_cells": int(len(moon))},
        "failure_reasons": {"EARTH_LAND": top_reasons(land_g, n_reasons), "MOON": top_reasons(res.moon_gates, n_reasons)},
        "missing_data": {"EARTH_LAND": missing_summary(land_g, missing_suffix),
                         "MOON": missing_summary(res.moon_gates, missing_suffix)},
        "ranked": int(ranked.sum()),
        "distinct_twins": int(len(np.unique(tw))),
        "similarity_variables": list(res.sim_vars),
        "excluded_from_similarity": dict(res.sim_excluded),
        "distributions": {
            "suitability": quantiles(res.earth_suit.score[passing], 2),
            "similarity": quantiles(res.similarity_pct[ranked], 2),
            "final": quantiles(res.final_published[ranked], 2),
            "confidence_score": quantiles(res.confidence_score[ranked], 3),
        },
        "confidence_counts": {k: int(sum(1 for c in res.confidence if c == k)) for k in ("high", "medium", "low")},
        "top": top_cells(res, earth, moon, earth_places, moon_feat, n_top),
    }


def run_report(c: Dict, benchmark_csv: Optional[str], n_top: int) -> Dict[str, Any]:
    """Full report on a computed build ``c`` (engine.build.compute output)."""
    ecfg = c["engine_cfg"]
    earth, moon = c["cells"]["EARTH"], c["cells"]["MOON"]
    suffix = ecfg.v("missing_data_reason")["code_suffix"]
    rep: Dict[str, Any] = {"dataset": ecfg.dataset_id, "missions": {}}
    for mid, res in c["results"].items():
        rep["missions"][mid] = mission_report(res, earth, moon, c["land"], c["earth_places"], c["moon_features"],
                                              n_top, int(ecfg.v("top_failure_reasons_n")), suffix)
    if benchmark_csv:
        rep["benchmark"] = benchmark_lookup(read_sites(benchmark_csv), c["results"], earth["id"].to_numpy(),
                                            c["dataset"].grid, c["land"], c["earth_places"])
    return rep
