"""Validation of the cell table with pydantic: one schema per body.

Checks coordinate ranges, grid consistency, physically valid ranges per variable
(from provenance.json, itself from the audit data dictionary) and category
vocabularies. Nothing is fixed: failures are returned in a validity report.
A missing value (null) is valid here; missing data is handled by the gates
(eliminated) and by the soft score (renormalised and flagged).
"""
from __future__ import annotations

import math
from typing import Any, Dict, List, Literal, Optional, Tuple, Type

import numpy as np
import pandas as pd
from pydantic import BaseModel, ConfigDict, Field, ValidationError, create_model, model_validator

from engine.config import BODIES
from engine import provenance
from engine.dataset import Grid


def _grid_base(coord_tol_deg: float, grid: Grid) -> Type[BaseModel]:
    """Grid position and coordinates, with the grid-consistency check (dataset grid,
    configured coordinate tolerance)."""

    class _GridCell(BaseModel):
        model_config = ConfigDict(extra="ignore")
        id: int = Field(ge=0, lt=grid.rows * grid.cols)
        row: int = Field(ge=0, lt=grid.rows)
        col: int = Field(ge=0, lt=grid.cols)
        lat_deg: float = Field(ge=-90.0, le=90.0)
        lon_deg: float = Field(ge=-180.0, le=180.0)

        @model_validator(mode="after")
        def _grid_consistent(self) -> "_GridCell":
            exp_lat = float(grid.lat_center(self.row))
            exp_lon = float(grid.lon_center(self.col))
            if abs(self.lat_deg - exp_lat) > coord_tol_deg:
                raise ValueError(f"lat_deg {self.lat_deg} does not match row {self.row} (expected {exp_lat})")
            if abs(self.lon_deg - exp_lon) > coord_tol_deg:
                raise ValueError(f"lon_deg {self.lon_deg} does not match col {self.col} (expected {exp_lon})")
            if self.id != self.row * grid.cols + self.col:
                raise ValueError(f"id {self.id} is not row*{grid.cols}+col")
            return self

    return _GridCell


def _default_coord_tol() -> float:
    from engine.config import load_engine_config
    return float(load_engine_config().v("coordinate_tolerance_deg"))


def _grid_for(grid: Optional[Grid]) -> Grid:
    """The grid to validate against: the one given, else that of the default dataset."""
    if grid is not None:
        return grid
    from engine.config import load_engine_config
    from engine.dataset import grid_of
    return grid_of(load_engine_config())


def build_cell_model(body: str, reg: Optional[Dict] = None,
                     coord_tol_deg: Optional[float] = None, grid: Optional[Grid] = None) -> Type[BaseModel]:
    """Create the pydantic model of one cell of ``body`` from the provenance registry.
    ``coord_tol_deg`` defaults to engine_config.json coordinate_tolerance_deg; ``grid``
    to the default dataset's grid."""
    reg = reg or provenance.load_registry()
    tol = _default_coord_tol() if coord_tol_deg is None else float(coord_tol_deg)
    grid = _grid_for(grid)
    fields: Dict[str, Tuple[Any, Any]] = {}
    for var in provenance.variables(reg):
        entry = reg["variables"][var]
        if entry["kind"] == "categorical":
            cats = tuple(entry["categories"])
            fields[var] = (Optional[Literal[cats]], None)  # type: ignore[valid-type]
        else:
            b = entry["bodies"][body]
            constraints: Dict[str, float] = {}
            if b.get("valid_min") is not None:
                constraints["ge"] = float(b["valid_min"])
            if b.get("valid_max") is not None:
                constraints["le"] = float(b["valid_max"])
            fields[var] = (Optional[float], Field(default=None, allow_inf_nan=False, **constraints))
    return create_model(f"{body.title()}Cell", __base__=_grid_base(tol, grid), **fields)  # type: ignore[call-overload]


def _record(row: Dict[str, Any]) -> Dict[str, Any]:
    """Convert pandas missing markers to None (missing stays missing, never 0)."""
    out = {}
    for k, v in row.items():
        if v is None or (isinstance(v, float) and math.isnan(v)):
            out[k] = None
        elif isinstance(v, (np.floating,)):
            out[k] = None if np.isnan(v) else float(v)
        elif isinstance(v, (np.integer,)):
            out[k] = int(v)
        else:
            out[k] = v
    return out


def validate_body(df: pd.DataFrame, body: str, reg: Optional[Dict] = None,
                  coord_tol_deg: Optional[float] = None, grid: Optional[Grid] = None) -> Dict[str, Any]:
    """Validate every record of one body. Returns a report; never alters ``df``.

    Report: {"body", "records", "failing_records", "field_failures": {field: n},
             "failures": [{"id", "field", "value", "reason"}], "duplicate_ids": [...]}
    """
    reg = reg or provenance.load_registry()
    model = build_cell_model(body, reg, coord_tol_deg, grid)
    failures: List[Dict[str, Any]] = []
    field_counts: Dict[str, int] = {}
    failing_ids = set()
    cols = ["id", "row", "col", "lat_deg", "lon_deg"] + provenance.variables(reg)
    for rec in df[cols].to_dict(orient="records"):
        rec = _record(rec)
        try:
            model.model_validate(rec)
        except ValidationError as exc:
            for err in exc.errors():
                fld = ".".join(str(x) for x in err["loc"]) or "record"
                failures.append({"id": rec["id"], "field": fld, "value": rec.get(fld), "reason": err["msg"]})
                field_counts[fld] = field_counts.get(fld, 0) + 1
                failing_ids.add(rec["id"])
    dup = df["id"][df["id"].duplicated()].astype(int).tolist()
    return {
        "body": body,
        "records": int(len(df)),
        "failing_records": len(failing_ids),
        "field_failures": dict(sorted(field_counts.items())),
        "failures": sorted(failures, key=lambda f: (f["id"], f["field"])),
        "duplicate_ids": sorted(dup),
    }


def validate_table(cells: Dict[str, pd.DataFrame], reg: Optional[Dict] = None,
                   coord_tol_deg: Optional[float] = None, grid: Optional[Grid] = None) -> Dict[str, Any]:
    """Validate both bodies; returns {"bodies": {body: report}, "valid": bool}."""
    reg = reg or provenance.load_registry()
    tol = _default_coord_tol() if coord_tol_deg is None else coord_tol_deg
    grid = _grid_for(grid)
    reports = {b: validate_body(cells[b], b, reg, tol, grid) for b in BODIES}
    ok = all(r["failing_records"] == 0 and not r["duplicate_ids"] for r in reports.values())
    return {"valid": ok, "bodies": reports}


def invalid_fields_by_id(report: Dict[str, Any]) -> Dict[int, List[str]]:
    """Map cell id -> fields that failed validation (for per-cell flags)."""
    out: Dict[int, List[str]] = {}
    for f in report["failures"]:
        out.setdefault(int(f["id"]), []).append(f["field"])
    return out
