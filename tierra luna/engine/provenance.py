"""Provenance registry: data level, source, code location, resolution and caveat
for every variable and body (engine/provenance.json, built from the audit).

Levels are read from the registry only, never inferred from a column name.
"""
from __future__ import annotations

import json
from typing import Dict, List, Optional

from engine.config import BODIES, PROVENANCE_PATH

LEVELS = ("MEASURED", "DERIVED", "MODELLED", "UNDOCUMENTED")


def load_registry(path: Optional[str] = None) -> Dict:
    """Load and check the registry: every variable has a known level for both bodies."""
    with open(path or PROVENANCE_PATH, encoding="utf-8") as fh:
        reg = json.load(fh)
    for var, entry in reg["variables"].items():
        if not isinstance(entry.get("comparable_across_bodies"), bool) or not entry.get("comparability_note"):
            raise KeyError(f"provenance: {var} lacks comparable_across_bodies / comparability_note")
        for body in BODIES:
            b = entry["bodies"].get(body)
            if b is None:
                raise KeyError(f"provenance: {var} has no entry for {body}")
            if b["level"] not in LEVELS:
                raise ValueError(f"provenance: {var}/{body} has unknown level {b['level']!r}")
            for key in ("claimed_source", "code", "resolution_km", "caveat"):
                if key not in b:
                    raise KeyError(f"provenance: {var}/{body} lacks {key}")
    return reg


def variables(reg: Dict) -> List[str]:
    """Physical variables in registry order."""
    return list(reg["variables"].keys())


def level(reg: Dict, variable: str, body: str) -> str:
    """Data level of ``variable`` on ``body``."""
    return reg["variables"][variable]["bodies"][body]["level"]


def kind(reg: Dict, variable: str) -> str:
    """'numeric' or 'categorical'."""
    return reg["variables"][variable]["kind"]


def categorical_variables(reg: Dict) -> List[str]:
    """Variables whose values are category labels."""
    return [v for v in variables(reg) if kind(reg, v) == "categorical"]


def resolution_km(reg: Dict, variable: str, body: str) -> float:
    """True north-south cell size behind a variable on a body, in km."""
    return float(reg["variables"][variable]["bodies"][body]["resolution_km"])


def comparable(reg: Dict, variable: str) -> bool:
    """True when ``variable`` is the same physical quantity on both bodies (registry flag)."""
    return bool(reg["variables"][variable]["comparable_across_bodies"])


def comparability_note(reg: Dict, variable: str) -> str:
    """Why a variable is (or is not) comparable across bodies."""
    return str(reg["variables"][variable]["comparability_note"])
