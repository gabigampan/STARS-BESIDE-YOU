"""Build the repository-similarity context of a dataset: columns, exclusions, zones.

Reads engine_config ``repo_similarity`` and ``similarity_zones`` and the dataset's
``similarity_columns`` and ``similarity_excluded``; resolves each mission's lunar
zone (zone_twin rule). The lunar_base zone is the set of lunar cells that intersect
NASA's Artemis III candidate landing regions when a verified outline file exists,
otherwise the configured fallback (the code's south-pole zone, never the global mean).
"""
from __future__ import annotations

import json
import os
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from engine.config import EngineConfig, resolve_path
from engine.repo_similarity import RepoContext, build_context, zone_mask


def similarity_columns(engine_cfg: EngineConfig) -> Dict[str, Dict[str, Optional[str]]]:
    """{variable: {EARTH: column or None, MOON: column or None}} (notes dropped)."""
    return {v: {b: e.get(b) for b in ("EARTH", "MOON")} for v, e in engine_cfg.v("similarity_columns").items()}


def load_region_cells(path: str, flag: str, moon: pd.DataFrame, cell_deg: float) -> Tuple[Optional[np.ndarray], str, List[str]]:
    """(mask of lunar cells intersecting the regions, status text, region names).

    The file is a GeoJSON FeatureCollection in planetocentric degrees (longitude
    -180..180 east-positive) whose top-level ``flag`` member is true. A cell is in
    the zone when its 1-cell square (centre +- cell_deg / 2) intersects a region.
    Returns (None, reason, []) when the file is absent or not verified.
    """
    if not os.path.exists(path):
        return None, f"no outline file at {path}", []
    with open(path, encoding="utf-8") as fh:
        gj = json.load(fh)
    if gj.get(flag) is not True:
        return None, f"{path} is not marked '{flag}': true", []
    from shapely.geometry import box, shape
    from shapely.strtree import STRtree

    geoms = [shape(f["geometry"]) for f in gj["features"]]
    names = [str(f.get("properties", {}).get("name", f"region {k + 1}")) for k, f in enumerate(gj["features"])]
    tree = STRtree(geoms)
    lat = moon["lat_deg"].to_numpy(dtype=np.float64)
    lon = moon["lon_deg"].to_numpy(dtype=np.float64)
    h = cell_deg / 2.0
    mask = np.zeros(len(moon), dtype=bool)
    lo, hi = min(g.bounds[1] for g in geoms), max(g.bounds[3] for g in geoms)
    for i in np.flatnonzero((lat + h >= lo) & (lat - h <= hi)):
        b = box(lon[i] - h, lat[i] - h, lon[i] + h, lat[i] + h)
        if any(geoms[k].intersects(b) for k in tree.query(b)):
            mask[i] = True
    return mask, f"verified region footprints read from {path} (union of each region's 1 km USGS grid squares: an upper bound of the region)", names


def resolve_zones(moon: pd.DataFrame, engine_cfg: EngineConfig, missions: List[str]) -> Dict[str, Dict]:
    """{mission: {name, kind, source, used, reason, cells, mask}} for the zone_twin rule."""
    zones_cfg = engine_cfg.v("similarity_zones")
    cell_deg = float(engine_cfg.v("grid")["cell_deg"])
    out: Dict[str, Dict] = {}
    for m in missions:
        z = zones_cfg[m]
        if z["kind"] == "artemis_regions":
            mask, status, names = load_region_cells(resolve_path(z["regions_file"]), z["verified_flag"], moon, cell_deg)
            status = status.replace(resolve_path(z["regions_file"]), z["regions_file"])
            if mask is not None and mask.any():
                out[m] = {"name": z["name"], "kind": "artemis_regions", "source": z["source"], "regions": names,
                          "used": "artemis_regions", "reason": status, "mask": mask, "cells": int(mask.sum())}
                continue
            fb = z["fallback"]
            out[m] = {"name": fb["name"], "kind": fb["kind"], "lat_max": fb.get("lat_max"), "source": fb["source"],
                      "used": "fallback_south_pole",
                      "reason": f"Artemis III region outlines not available ({status}); the configured fallback, the code's south-pole zone, is used (never the global mean).",
                      "mask": zone_mask(moon, fb)}
        else:
            out[m] = {"name": z["name"], "kind": z["kind"], "lat_max": z.get("lat_max"), "source": z["source"],
                      "used": z["kind"], "reason": "configured zone", "mask": zone_mask(moon, z)}
        out[m]["cells"] = int(out[m]["mask"].sum())
    return out


def build_repo_context(earth: pd.DataFrame, moon: pd.DataFrame, engine_cfg: EngineConfig,
                       missions: List[str]) -> RepoContext:
    """Normalise both bodies with the repository's function and resolve the zones."""
    from engine.config import similarity_rule

    ctx = build_context(earth, moon, similarity_rule(engine_cfg), engine_cfg.v("repo_similarity"),
                        similarity_columns(engine_cfg), engine_cfg.v("similarity_excluded"))
    ctx.zones = resolve_zones(moon, engine_cfg, missions)
    return ctx
