"""Configuration loading for the engine.

Two configuration files drive every number the engine uses:

* ``mission_scoring.json`` (team file, read through ``mission_scoring.load_config``):
  every gate threshold, soft weight, utility bound (bad/good), category table and
  tolerance. The engine never types or changes any of these values.
* ``engine/engine_config.json`` (this package): engine-only settings such as the
  body applicability of common gates, the similarity scale rule, the mix factor,
  the confidence rule and export rounding. Every setting is an object with a
  ``value`` and a ``why``; the loader refuses a setting without a reason.
"""
from __future__ import annotations

import copy
import hashlib
import json
import os
import sys
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, field_validator

ENGINE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(ENGINE_DIR)  # ".../tierra luna"
ENGINE_CONFIG_PATH = os.path.join(ENGINE_DIR, "engine_config.json")
PROVENANCE_PATH = os.path.join(ENGINE_DIR, "provenance.json")

if PROJECT_DIR not in sys.path:  # mission_scoring.py lives next to the package
    sys.path.insert(0, PROJECT_DIR)

import mission_scoring  # noqa: E402  (team module, used unchanged)

BODIES = ("EARTH", "MOON")
GRID_ROWS = 90
GRID_COLS = 180
CELL_DEG = 2.0


class Setting(BaseModel):
    """One engine setting: its value and the reason it has that value."""

    model_config = ConfigDict(extra="forbid")
    value: Any
    why: str

    @field_validator("why")
    @classmethod
    def _why_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("every engine setting needs a non-empty 'why'")
        return v


class EngineConfig(BaseModel):
    """Typed view of engine_config.json. Each field is a :class:`Setting`."""

    model_config = ConfigDict(extra="forbid")
    engine_version: Setting
    bundle_version: Setting
    input_csv: Setting
    mission_config: Setting
    output_dir: Setting
    missions: Setting
    gate_body_applicability: Setting
    on_invalid_value: Setting
    similarity_scale: Setting
    similarity_zero_scale: Setting
    mix_factor: Setting
    pairing_chunk_rows: Setting
    confidence: Setting
    explain_top_n: Setting
    top_failure_reasons_n: Setting
    body_radius_km: Setting
    lunar_gazetteer_csv: Setting
    lunar_feature_exclude_types: Setting
    antarctic_label_lat_max: Setting
    export_decimals: Setting
    mission_titles: Setting
    credits: Setting
    similarity_comparability: Setting
    explain_helps_n: Setting
    explain_hurts_n: Setting
    coordinate_tolerance_deg: Setting
    earth_ocean_fill: Setting
    region_max_place_km: Setting
    earth_country_polygons: Setting
    not_used_by_engine_why: Setting
    mission_notes: Setting

    def v(self, name: str) -> Any:
        """Return the value of a setting (deep copy, so callers cannot mutate config)."""
        return copy.deepcopy(getattr(self, name).value)


def load_engine_config(path: Optional[str] = None) -> EngineConfig:
    """Load and validate engine_config.json."""
    with open(path or ENGINE_CONFIG_PATH, encoding="utf-8") as fh:
        raw = json.load(fh)
    raw = {k: v for k, v in raw.items() if not k.startswith("_")}
    return EngineConfig.model_validate(raw)


def resolve_path(p: str) -> str:
    """Resolve a config path relative to the project directory ("tierra luna")."""
    return p if os.path.isabs(p) else os.path.normpath(os.path.join(PROJECT_DIR, p))


def load_mission_config(path: Optional[str] = None, engine_cfg: Optional[EngineConfig] = None) -> Dict:
    """Load mission_scoring.json through the team module (no value is altered)."""
    if path is None:
        ecfg = engine_cfg or load_engine_config()
        path = resolve_path(ecfg.v("mission_config"))
    return mission_scoring.load_config(path)


def mission_ids(mission_cfg: Dict, engine_cfg: EngineConfig) -> List[str]:
    """Missions to build, in the configured order, restricted to missions defined in the JSON."""
    defined = mission_scoring.mission_names(mission_cfg)
    wanted = engine_cfg.v("missions")
    missing = [m for m in wanted if m not in defined]
    if missing:
        raise KeyError(f"engine_config lists missions not defined in mission_scoring.json: {missing}")
    return list(wanted)


def gate_applies(variable: str, body: str, engine_cfg: EngineConfig) -> bool:
    """True when a common gate on ``variable`` applies to ``body`` (default: all bodies)."""
    table = engine_cfg.v("gate_body_applicability")
    if variable not in table:
        return True
    return body in table[variable]["bodies"]


def body_mission_config(mission_cfg: Dict, body: str, engine_cfg: EngineConfig) -> Dict:
    """Copy of the mission config whose common gates are those applicable to ``body``.

    Only the *applicability* of a common gate changes; thresholds are copied verbatim.
    Mission gates are never removed.
    """
    cfg = copy.deepcopy(mission_cfg)
    cfg["common_gates"] = {
        col: g for col, g in cfg.get("common_gates", {}).items() if gate_applies(col, body, engine_cfg)
    }
    return cfg


def sha256_file(path: str) -> str:
    """Hex sha256 of a file."""
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_bytes(data: bytes) -> str:
    """Hex sha256 of a byte string."""
    return hashlib.sha256(data).hexdigest()
