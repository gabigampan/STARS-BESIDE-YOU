"""The six lunar regions of docs/MISSION_ZONES.md section 2 and the web's zone texts.

Every lunar cell gets exactly one region (engine_config ``lunar_regions``), evaluated in
the configured order, first match wins:

    A  the Lunar base zone (similarity_zones.lunar_base: the nine NASA regions, 280 cells)
    B  the Rover zone (latitude <= -75), not A
    C  the Rover latitude bound mirrored to the north (latitude >= 75)
    D  the Solar panels zone (|latitude| <= 30 and elevation <= -1,200 m)
    E  |longitude| > 90 (far side)
    F  the rest

The zone thresholds are read from the zone definitions already in engine_config (they are
not repeated). Each mission's zone is a union of regions (``mission_zone_regions``), checked
against the zone masks here. The texts shown for a cell outside a mission's zone come
verbatim from engine/mission_zone_texts.json (written by the zone-texts agent); when that
file is absent or incomplete the regions are exported without texts.
"""
from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from engine.config import EngineConfig, resolve_path


def _config_path(engine_cfg: EngineConfig, dotted: str) -> Dict[str, Any]:
    """The engine_config value at 'setting.key.key...' (e.g. real_value_similarity.missions.rover.zone)."""
    head, *rest = dotted.split(".")
    node = engine_cfg.v(head)
    for k in rest:
        node = node[k]
    return node


def zone_from_config(moon: pd.DataFrame, engine_cfg: EngineConfig, dotted: str) -> np.ndarray:
    """Mask of a zone named by its place in engine_config."""
    from engine.pipeline import real_zone_mask

    if dotted.startswith("similarity_zones."):
        key = dotted.split(".", 1)[1]
        return real_zone_mask(moon, {"kind": "similarity_zone", "similarity_zones_key": key}, engine_cfg)
    return real_zone_mask(moon, _config_path(engine_cfg, dotted), engine_cfg)


def region_codes(moon: pd.DataFrame, engine_cfg: EngineConfig) -> Tuple[np.ndarray, List[Dict[str, Any]]]:
    """(region index of every lunar cell, the region table in order)."""
    cfg = engine_cfg.v("lunar_regions")
    regs = cfg["regions"]
    lat = moon["lat_deg"].to_numpy(dtype=np.float64)
    lon = moon["lon_deg"].to_numpy(dtype=np.float64)
    out = np.full(len(moon), -1, dtype=np.int64)
    for k, r in enumerate(regs):
        if r["kind"] == "zone_of":
            m = zone_from_config(moon, engine_cfg, r["zone"])
        elif r["kind"] == "mirror_of":
            z = _config_path(engine_cfg, r["zone"])
            if z["kind"] != "lat_max":
                raise ValueError(f"region {r['code']}: only a lat_max zone can be mirrored")
            m = lat >= -float(z["lat_max"])
        elif r["kind"] == "abs_lon_greater_than":
            m = np.abs(lon) > float(r["abs_lon_gt"])
        elif r["kind"] == "rest":
            m = np.ones(len(moon), dtype=bool)
        else:
            raise ValueError(f"unknown region kind {r['kind']!r}")
        out[(out < 0) & m] = k
    if np.any(out < 0):
        raise ValueError("a lunar cell has no region")
    return out, regs


def check_mission_zones(moon: pd.DataFrame, engine_cfg: EngineConfig, codes: np.ndarray,
                        zone_masks: Dict[str, np.ndarray]) -> None:
    """Each mission's zone mask must be exactly the union of its configured regions."""
    cfg = engine_cfg.v("lunar_regions")
    idx = {r["code"]: k for k, r in enumerate(cfg["regions"])}
    for m, codes_m in cfg["mission_zone_regions"].items():
        if m not in zone_masks:
            continue
        want = np.isin(codes, [idx[c] for c in codes_m])
        if not np.array_equal(want, zone_masks[m]):
            raise ValueError(f"{m}: the zone is not exactly the regions {codes_m}")


def load_zone_texts(engine_cfg: EngineConfig) -> Tuple[Optional[Dict[str, Any]], str]:
    """(texts, status). texts is None when the file is absent, not valid JSON or lacks a
    required key; when it is complete every mission must have a text for every region
    outside its zone (else ValueError: the build fails)."""
    cfg = engine_cfg.v("lunar_regions")
    path = resolve_path(cfg["texts_file"])
    if not os.path.exists(path):
        return None, f"{cfg['texts_file']} is absent: regions exported without texts"
    try:
        with open(path, encoding="utf-8") as fh:
            t = json.load(fh)
    except (OSError, ValueError) as e:
        return None, f"{cfg['texts_file']} is not valid JSON ({type(e).__name__}): regions exported without texts"
    if not isinstance(t, dict):
        return None, f"{cfg['texts_file']} is not a JSON object: regions exported without texts"
    missing = [k for k in cfg["texts_required_keys"] if k not in t]
    if missing:
        return None, f"{cfg['texts_file']} is incomplete (no {', '.join(missing)}): regions exported without texts"
    codes = [r["code"] for r in cfg["regions"]]
    problems = []
    for m, inside in cfg["mission_zone_regions"].items():
        if not (t.get("zone_why") or {}).get(m):
            problems.append(f"zone_why.{m}")
        for c in codes:
            if c not in inside and not ((t.get("outside") or {}).get(m) or {}).get(c):
                problems.append(f"outside.{m}.{c}")
    for c in codes:
        if not (t.get("region_labels") or {}).get(c):
            problems.append(f"region_labels.{c}")
    if problems:
        raise ValueError(f"{cfg['texts_file']}: missing texts {problems}")
    return t, f"texts copied verbatim from {cfg['texts_file']}"


def mission_zones_json(moon: pd.DataFrame, engine_cfg: EngineConfig, codes: np.ndarray) -> Tuple[Dict[str, Any], str]:
    """mission_zones.json and the status line for the manifest."""
    cfg = engine_cfg.v("lunar_regions")
    texts, status = load_zone_texts(engine_cfg)
    labels = (texts or {}).get("region_labels") or {}
    regions = [{"code": r["code"], "label": labels.get(r["code"], r["fallback_label"]), "rule": r["rule"],
                "cells": int((codes == k).sum())} for k, r in enumerate(cfg["regions"])]
    out: Dict[str, Any] = {
        "consulted_on": (texts or {}).get("consulted_on"),
        "source_document": (texts or {}).get("source_document", cfg["source_document"]),
        "regions": regions,
        "mission_zone_regions": cfg["mission_zone_regions"],
        "region_column": "moon_base.bin 'region' (index into 'regions')",
        "texts": None if texts is None else {k: texts[k] for k in ("general_note", "zone_why", "outside")},
        "texts_status": status,
    }
    if texts is not None:
        for k in cfg["texts_copied_if_present"]:
            if k in texts:
                out[k] = texts[k]
        out["label_source"] = cfg["texts_file"]
    else:
        out["label_source"] = "engine_config lunar_regions fallback_label (docs/MISSION_ZONES.md section 2); the texts file was not usable"
    return out, status
