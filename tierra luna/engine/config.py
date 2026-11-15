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
DATASETS_PATH = os.path.join(ENGINE_DIR, "datasets.json")
PROVENANCE_PATH = os.path.join(ENGINE_DIR, "provenance.json")

if PROJECT_DIR not in sys.path:  # mission_scoring.py lives next to the package
    sys.path.insert(0, PROJECT_DIR)

import mission_scoring  # noqa: E402  (team module, used unchanged)

BODIES = ("EARTH", "MOON")

# Settings that depend on the input table. They are NOT in engine_config.json: they
# come from the dataset descriptor (engine/datasets.json) chosen at load time.
DATASET_SETTINGS = ("inputs", "input_csv", "grid", "provenance", "column_aliases", "column_overrides",
                    "variables", "comparability", "bundle_format", "bundle_version", "output_dir",
                    "earth_land_cells", "earth_ocean_fill", "region_max_place_km", "export_columns",
                    "lunar_named_sites", "credits", "mission_notes", "similarity_columns", "similarity_excluded",
                    "lunar_info_columns")


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
    mission_config: Setting
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
    similarity_comparability: Setting
    explain_helps_n: Setting
    explain_hurts_n: Setting
    coordinate_tolerance_deg: Setting
    earth_country_polygons: Setting
    not_used_by_engine_why: Setting
    missing_data_reason: Setting
    binary_encoding: Setting
    first_view_budget_bytes: Setting
    mission_threshold_status: Setting
    similarity_rule: Setting
    similarity_rule_options: Setting
    repo_similarity: Setting
    similarity_zones: Setting
    twin_tie_rule: Setting
    detail_tile_rows: Setting
    approved_texts: Optional[Setting] = None
    # filled from the dataset descriptor (engine/datasets.json)
    dataset: Optional[Setting] = None
    inputs: Optional[Setting] = None
    input_csv: Optional[Setting] = None
    grid: Optional[Setting] = None
    provenance: Optional[Setting] = None
    column_aliases: Optional[Setting] = None
    column_overrides: Optional[Setting] = None
    variables: Optional[Setting] = None
    comparability: Optional[Setting] = None
    bundle_format: Optional[Setting] = None
    bundle_version: Optional[Setting] = None
    output_dir: Optional[Setting] = None
    earth_land_cells: Optional[Setting] = None
    earth_ocean_fill: Optional[Setting] = None
    region_max_place_km: Optional[Setting] = None
    export_columns: Optional[Setting] = None
    lunar_named_sites: Optional[Setting] = None
    credits: Optional[Setting] = None
    mission_notes: Optional[Setting] = None
    similarity_columns: Optional[Setting] = None
    similarity_excluded: Optional[Setting] = None
    lunar_info_columns: Optional[Setting] = None

    def v(self, name: str) -> Any:
        """Return the value of a setting (deep copy, so callers cannot mutate config)."""
        s = getattr(self, name)
        if s is None:
            raise KeyError(f"setting {name!r} is not set (dataset settings come from engine/datasets.json)")
        return copy.deepcopy(s.value)

    @property
    def dataset_id(self) -> str:
        """Id of the dataset descriptor these settings were loaded with."""
        return str(self.v("dataset"))


def load_datasets(path: Optional[str] = None) -> Dict:
    """Load engine/datasets.json (dataset descriptors)."""
    with open(path or DATASETS_PATH, encoding="utf-8") as fh:
        return json.load(fh)


def dataset_ids(path: Optional[str] = None) -> List[str]:
    """Ids of the available dataset descriptors, in file order."""
    return list(load_datasets(path)["datasets"].keys())


def default_dataset(path: Optional[str] = None) -> str:
    """The dataset used when none is named (engine/datasets.json 'default_dataset')."""
    return str(load_datasets(path)["default_dataset"]["value"])


def load_engine_config(path: Optional[str] = None, dataset: Optional[str] = None,
                       datasets_path: Optional[str] = None) -> EngineConfig:
    """Load engine_config.json and overlay the settings of one dataset descriptor.

    ``dataset`` defaults to datasets.json 'default_dataset'. Every descriptor must set
    every dataset setting (DATASET_SETTINGS), each with a value and a why.
    """
    with open(path or ENGINE_CONFIG_PATH, encoding="utf-8") as fh:
        raw = json.load(fh)
    raw = {k: v for k, v in raw.items() if not k.startswith("_")}
    clash = sorted(set(raw) & set(DATASET_SETTINGS))
    if clash:
        raise ValueError(f"engine_config.json must not hold dataset settings (they belong in datasets.json): {clash}")
    ds_all = load_datasets(datasets_path)
    ds_id = dataset or str(ds_all["default_dataset"]["value"])
    if ds_id not in ds_all["datasets"]:
        raise KeyError(f"unknown dataset {ds_id!r}; known: {list(ds_all['datasets'])}")
    desc = ds_all["datasets"][ds_id]
    missing = [k for k in DATASET_SETTINGS if k not in desc["settings"]]
    if missing:
        raise KeyError(f"dataset {ds_id!r} lacks settings {missing}")
    raw.update({k: desc["settings"][k] for k in DATASET_SETTINGS})
    raw["dataset"] = {"value": ds_id, "why": desc["why"]}
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


SIMILARITY_RULES = ("repo_global_mean", "zone_twin", "physical_pooled")
# Fields of a mission block that define its filters and scores (a component copy must match them all).
MISSION_DEFINITION_KEYS = ("require_present", "gates", "soft", "weights")


def mission_ids(mission_cfg: Dict, engine_cfg: EngineConfig) -> List[str]:
    """Missions to build (the offered missions), in the configured order.

    Every listed mission must be defined in the JSON, the JSON's own
    ``offered_missions`` (when present) must list the same missions, and every
    mission with ``components.core`` must be an exact copy of its core block
    (:func:`check_components`).
    """
    defined = mission_scoring.mission_names(mission_cfg)
    wanted = engine_cfg.v("missions")
    missing = [m for m in wanted if m not in defined]
    if missing:
        raise KeyError(f"engine_config lists missions not defined in mission_scoring.json: {missing}")
    offered = mission_cfg.get("offered_missions")
    if offered is not None and list(offered) != list(wanted):
        raise ValueError(f"mission_scoring.json offered_missions {offered} differs from engine_config missions {wanted}")
    check_components(mission_cfg, wanted)
    return list(wanted)


def mission_components(mission_cfg: Dict, mission: str) -> Dict[str, Any]:
    """{"core": id or None, "info": [ids]} of a mission (mission_scoring.json 'components')."""
    c = mission_cfg["missions"][mission].get("components") or {}
    return {"core": c.get("core"), "info": list(c.get("info", []))}


def check_components(mission_cfg: Dict, missions: List[str]) -> None:
    """A mission with a core component must equal that block on every definition field
    (require_present, gates, soft, weights); info components must be defined."""
    for m in missions:
        comp = mission_components(mission_cfg, m)
        for c in ([comp["core"]] if comp["core"] else []) + comp["info"]:
            if c not in mission_cfg["missions"]:
                raise KeyError(f"{m}: component {c!r} is not defined in mission_scoring.json")
        if comp["core"]:
            a, b = mission_cfg["missions"][m], mission_cfg["missions"][comp["core"]]
            diff = [k for k in MISSION_DEFINITION_KEYS if a.get(k) != b.get(k)]
            if diff:
                raise ValueError(f"{m} must be an exact copy of {comp['core']}; differs in {diff}")


def similarity_rule(engine_cfg: EngineConfig) -> str:
    """The active similarity rule (engine_config similarity_rule)."""
    r = str(engine_cfg.v("similarity_rule"))
    if r not in SIMILARITY_RULES:
        raise ValueError(f"unknown similarity_rule {r!r}; known: {SIMILARITY_RULES}")
    return r


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
