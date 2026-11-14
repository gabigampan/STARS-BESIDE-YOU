"""Dataset descriptors: grid, input tables, column aliases and the provenance registry.

A dataset (engine/datasets.json) says which files hold the cells, the grid they are
on, where each variable's level and source come from, and which real column a
mission variable is read from. The modules downstream (gates, suitability,
similarity, pairing, confidence, export) only see:

* one frame per body, sorted by ``id = row * cols + col``, whose columns named after
  the mission variables hold the values of the aliased real columns (the "mission
  view"), plus the untouched real columns;
* a registry with the same structure for every dataset: per variable a label, unit,
  kind, comparability and, per body, the level, source, caveat and resolution.

Nothing here types a threshold, a weight or a data value: levels and sources are
read from the provenance files, aliases from column_aliases.json, the grid from the
descriptor.
"""
from __future__ import annotations

import csv
import json
import math
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from engine import provenance
from engine.config import BODIES, EngineConfig, resolve_path, sha256_file

LEVELS_WITH_NO_DATA = provenance.LEVELS + ("NO_DATA",)
COMPARABILITY_STATUSES = ("comparable", "comparable_with_caveat", "not_comparable")
GRID_KEYS = ("id", "row", "col", "lat_deg", "lon_deg")


# ----------------------------------------------------------------------------- grid
@dataclass(frozen=True)
class Grid:
    """Regular latitude-longitude grid, row 0 at the north, column 0 at the west."""

    rows: int
    cols: int
    cell_deg: float

    @property
    def cells(self) -> int:
        return self.rows * self.cols

    def cell_id(self, row, col):
        """id = row * cols + col (works on scalars and arrays)."""
        return np.asarray(row, dtype=np.int64) * self.cols + np.asarray(col, dtype=np.int64)

    def lat_center(self, row):
        return 90.0 - (np.asarray(row, dtype=np.float64) + 0.5) * self.cell_deg

    def lon_center(self, col):
        return -180.0 + (np.asarray(col, dtype=np.float64) + 0.5) * self.cell_deg

    def row_col_of(self, lat: float, lon: float) -> Tuple[int, int]:
        """Cell containing a point (lat -90..90, lon any; -180..180 east-positive after wrapping).
        A point on a cell edge belongs to the cell to its south / east; lat = -90 to the last row."""
        if not (-90.0 <= lat <= 90.0) or not math.isfinite(lon):
            raise ValueError(f"coordinates out of range: {lat}, {lon}")
        lon = ((lon + 180.0) % 360.0) - 180.0
        row = min(int(math.floor((90.0 - lat) / self.cell_deg)), self.rows - 1)
        col = min(int(math.floor((lon + 180.0) / self.cell_deg)), self.cols - 1)
        return row, col

    def cell_ns_km(self, radius_km: float) -> float:
        """North-south size of a cell on a sphere (2*pi*R*cell_deg/360)."""
        return 2.0 * math.pi * radius_km * self.cell_deg / 360.0

    def describe(self, radii: Dict[str, float], decimals: int) -> Dict:
        return {
            "rows": self.rows, "cols": self.cols, "cell_deg": self.cell_deg,
            "cell_id": f"row * {self.cols} + col",
            "lat_center": f"90 - (row + 0.5) * {self.cell_deg}",
            "lon_center": f"-180 + (col + 0.5) * {self.cell_deg} (positive east, -180..180)",
            "row0": "north", "col0": "west",
            "bodies": {b: {"radius_km": radii[b], "cell_ns_km": round(self.cell_ns_km(radii[b]), decimals),
                           "cell_ew_km_at_equator": round(self.cell_ns_km(radii[b]), decimals),
                           "cell_ew_km_rule": "cell_ns_km * cos(latitude)"} for b in BODIES},
        }


def grid_of(engine_cfg: EngineConfig) -> Grid:
    g = engine_cfg.v("grid")
    return Grid(rows=int(g["rows"]), cols=int(g["cols"]), cell_deg=float(g["cell_deg"]))


# ----------------------------------------------------------------------------- tables
def split_bodies(df: pd.DataFrame, grid: Grid) -> Dict[str, pd.DataFrame]:
    """Split a table by body, add ``id = row * cols + col`` and sort by id. Values are
    not changed; empty strings and NaN stay missing."""
    out: Dict[str, pd.DataFrame] = {}
    body_col = df["body"].astype(str).str.upper()
    for body in BODIES:
        part = df[body_col == body].copy()
        part["id"] = grid.cell_id(part["row"].astype(int), part["col"].astype(int)).astype(int)
        part = part.sort_values("id", kind="mergesort").reset_index(drop=True)
        out[body] = part
    return out


def input_paths(engine_cfg: EngineConfig) -> Dict[str, str]:
    """{"ALL" | body: absolute path} of the dataset's input tables."""
    return {k: resolve_path(p) for k, p in engine_cfg.v("inputs").items()}


def load_raw(engine_cfg: EngineConfig, paths: Optional[Dict[str, str]] = None) -> Dict[str, pd.DataFrame]:
    """Read the dataset's input table(s) into one frame per body, sorted by id."""
    paths = paths or input_paths(engine_cfg)
    grid = grid_of(engine_cfg)
    if "ALL" in paths:
        return split_bodies(pd.read_csv(paths["ALL"], keep_default_na=True), grid)
    out = {}
    for body in BODIES:
        df = pd.read_csv(paths[body], keep_default_na=True)
        if set(df["body"].astype(str).str.upper()) != {body}:
            raise ValueError(f"{paths[body]} must hold only {body} rows")
        out[body] = split_bodies(df, grid)[body]
    return out


def inputs_info(engine_cfg: EngineConfig, raw: Dict[str, pd.DataFrame],
                paths: Optional[Dict[str, str]] = None) -> List[Dict]:
    """[{key, file, sha256, rows}] of the input tables (for manifest.json)."""
    paths = paths or input_paths(engine_cfg)
    out = []
    for key, p in paths.items():
        rows = sum(len(raw[b]) for b in BODIES) if key == "ALL" else len(raw[key])
        out.append({"key": key, "file": p.replace("\\", "/").split("/")[-1], "sha256": sha256_file(p), "rows": int(rows)})
    return out


# ----------------------------------------------------------------------------- aliases
def load_aliases(engine_cfg: EngineConfig) -> Optional[Dict[str, Dict[str, Dict]]]:
    """{body: {mission variable: alias entry}} or None for an identity dataset."""
    p = engine_cfg.v("column_aliases")
    if p is None:
        return None
    with open(resolve_path(p), encoding="utf-8") as fh:
        raw = json.load(fh)
    return {b: {k: v for k, v in raw[b].items() if not k.startswith("_")} for b in BODIES}


def resolve_columns(variables: List[str], aliases: Optional[Dict], overrides: Dict[str, str]) -> Dict[str, Dict[str, Dict]]:
    """For every variable and body: {"column": real column read, "alias_column": the
    alias file's column, "override": bool}. Identity when there is no alias file.

    ``overrides`` maps a real column to the one actually read (engine setting
    column_overrides, e.g. slope_deg -> slope_iso_deg).
    """
    out: Dict[str, Dict[str, Dict]] = {}
    for v in variables:
        out[v] = {}
        for b in BODIES:
            if aliases is None:
                col = v
            else:
                if v not in aliases[b]:
                    raise KeyError(f"column_aliases.json has no {b} entry for {v}")
                col = aliases[b][v]["column"]
            real = overrides.get(col, col)
            out[v][b] = {"column": real, "alias_column": col, "override": real != col}
    return out


def mission_view(raw: pd.DataFrame, columns: Dict[str, Dict[str, Dict]], body: str) -> pd.DataFrame:
    """Frame whose mission-variable columns hold the aliased real columns' values.

    Identity entries keep the column; aliased ones are copied (values unchanged).
    Real columns stay available under their own names unless a mission variable has
    the same name (then the mission meaning wins, e.g. slope_deg := slope_iso_deg).
    """
    out = raw.copy()
    for v, per_body in columns.items():
        col = per_body[body]["column"]
        if col not in raw.columns:
            raise KeyError(f"{body}: column {col!r} (for {v}) is not in the input table")
        if col != v:
            out[v] = raw[col].to_numpy()
    return out


# ----------------------------------------------------------------------------- provenance
def normalise_level(text: str) -> Tuple[str, Optional[str]]:
    """Provenance level text -> (level, note). 'no data' -> NO_DATA; 'DERIVED (...)' ->
    DERIVED with the text as note. Unknown text raises: a level is never guessed."""
    t = (text or "").strip()
    if t.lower() == "no data":
        return "NO_DATA", None
    head = t.split(" ", 1)[0].upper()
    if head in provenance.LEVELS:
        return head, (t if t.upper() != head else None)
    raise ValueError(f"unknown provenance level {text!r}")


def read_provenance_csv(path: str, body: str) -> Dict[str, Dict[str, str]]:
    """{column: row} of a builder's provenance CSV (rows for ``body`` only)."""
    out: Dict[str, Dict[str, str]] = {}
    with open(path, encoding="utf-8", newline="") as fh:
        for r in csv.DictReader(fh):
            if r.get("body", "").strip().upper() != body:
                continue
            out[r["variable"].strip()] = {k: (v or "").strip() for k, v in r.items()}
    return out


_KM = re.compile(r"(\d+(?:\.\d+)?)\s*km")
_ISO = re.compile(r"(\d+(?:\.\d+)?)\s*km in both directions")


def baseline_km(text: Optional[str]) -> Optional[float]:
    """First '<number> km' in a baseline text, or None."""
    m = _KM.search(text or "")
    return float(m.group(1)) if m else None


def override_baseline(row: Dict[str, str]) -> str:
    """True baseline of an isotropic-baseline column, read from its provenance row
    ('<x> km in both directions' in the formula or caveats). Raises when absent."""
    for key in ("formula", "caveats"):
        m = _ISO.search(row.get(key, ""))
        if m:
            return f"{m.group(1)} km in both directions"
    raise ValueError(f"no isotropic baseline stated in the provenance row of {row.get('variable')}")


def _registry_from_csv(engine_cfg: EngineConfig, raw: Dict[str, pd.DataFrame]) -> Dict:
    """Registry of a dataset whose provenance is in the builders' CSV files."""
    pcfg = engine_cfg.v("provenance")
    rows = {b: read_provenance_csv(resolve_path(pcfg[b]), b) for b in BODIES}
    aliases = load_aliases(engine_cfg)
    meta = engine_cfg.v("variables")
    comp = engine_cfg.v("comparability")
    overrides = engine_cfg.v("column_overrides")
    variables = list(meta.keys())
    for v in set(aliases["EARTH"]) | set(aliases["MOON"]):
        if v not in meta:
            raise KeyError(f"column_aliases.json names {v} but datasets.json 'variables' does not describe it")
    columns = resolve_columns(variables, aliases, overrides)
    radii = engine_cfg.v("body_radius_km")
    grid = grid_of(engine_cfg)
    reg: Dict = {"levels": dict(_LEVEL_TEXT), "variables": {}}
    for v in variables:
        if v not in comp:
            raise KeyError(f"datasets.json comparability has no row for {v}")
        c = comp[v]
        if c["status"] not in COMPARABILITY_STATUSES or not c.get("reason"):
            raise ValueError(f"comparability of {v}: bad status or no reason")
        m = meta[v]
        entry: Dict = {"label": m["label"], "unit": m["unit"], "kind": m["kind"], "description": m["description"],
                       "range_source": "not validated: the provenance files give no physically valid ranges",
                       "comparable_across_bodies": c["status"] != "not_comparable",
                       "comparability": c["status"], "comparability_note": c["reason"], "bodies": {}}
        if m["kind"] == "categorical":
            cats = set()
            for b in BODIES:
                col = columns[v][b]["column"]
                s = raw[b][col]
                t = s.astype(str).str.strip()
                cats |= set(t[~(s.isna() | t.str.lower().isin(["", "nan"]))])
            entry["categories"] = sorted(cats)
        for b in BODIES:
            cinfo = columns[v][b]
            col = cinfo["column"]
            if col not in rows[b]:
                raise KeyError(f"{b}: provenance file has no row for column {col} (variable {v})")
            r = rows[b][col]
            lvl, note = normalise_level(r["level"])
            vals = raw[b][col]
            has_any = bool((vals.notna() & ~vals.astype(str).str.strip().str.lower().isin(["", "nan"])).any())
            if lvl == "NO_DATA" and has_any:
                raise ValueError(f"{b}/{col}: provenance says 'no data' but the table has values")
            al = aliases[b][v]
            if cinfo["override"]:
                tb = override_baseline(r)
            else:  # this alias's baseline, else that of another alias entry for the same column
                tb = al.get("true_baseline_km") or next(
                    (a.get("true_baseline_km") for a in aliases[b].values()
                     if a.get("column") == cinfo["alias_column"] and a.get("true_baseline_km")), None)
            entry["bodies"][b] = {
                "level": lvl, "audit_level": r["level"], "level_note": note,
                "column": col, "alias_column": cinfo["alias_column"], "column_override": cinfo["override"],
                "caveat": al.get("caveat") or "",
                "provenance_caveat": r.get("caveats", ""),
                "claimed_source": " ".join(x for x in (r.get("product", ""), r.get("version", "")) if x),
                "product": r.get("product", ""), "version": r.get("version", ""), "url": r.get("url", ""),
                "licence_credit": r.get("licence_credit", ""),
                "native_resolution": r.get("native_resolution", ""),
                "aggregation": r.get("aggregation_to_cell", r.get("aggregation", "")),
                "formula": r.get("formula", ""),
                "true_baseline": tb, "true_baseline_km": baseline_km(tb),
                "code": f"{pcfg[b]} row '{col}'",
                "resolution_km": grid.cell_ns_km(radii[b]),
                "has_data": has_any,
                "valid_min": None, "valid_max": None,
            }
        reg["variables"][v] = entry
    reg["columns"] = columns
    return reg


_LEVEL_TEXT = {
    "MEASURED": "A value from a named measured data product, aggregated to the cell.",
    "DERIVED": "A stated formula applied to measured values (e.g. slope from a DEM, amplitude from two temperatures, sun geometry).",
    "MODELLED": "A model, an interpolated climatology, an assumed mapping or a value set by definition; not a measurement of the cell.",
    "UNDOCUMENTED": "A cached array whose product, date and method are not documented.",
    "NO_DATA": "The variable has no data on this body (not applicable); its values are empty, never 0.",
}


def build_registry(engine_cfg: EngineConfig, raw: Dict[str, pd.DataFrame]) -> Dict:
    """Registry of the dataset (same structure for every dataset kind)."""
    pcfg = engine_cfg.v("provenance")
    if pcfg["kind"] == "registry":
        reg = provenance.load_registry(resolve_path(pcfg["path"]))
        for v, e in reg["variables"].items():
            e.setdefault("comparability", "comparable" if e["comparable_across_bodies"] else "not_comparable")
        reg["columns"] = resolve_columns(provenance.variables(reg), None, engine_cfg.v("column_overrides"))
        return reg
    if pcfg["kind"] == "csv":
        return _registry_from_csv(engine_cfg, raw)
    raise ValueError(f"unknown provenance kind {pcfg['kind']!r}")


def provenance_files(engine_cfg: EngineConfig) -> Dict[str, str]:
    """{name: absolute path} of the files the registry was read from (for hashes)."""
    pcfg = engine_cfg.v("provenance")
    out = {}
    if pcfg["kind"] == "registry":
        out[pcfg["path"].split("/")[-1]] = resolve_path(pcfg["path"])
    else:
        for b in BODIES:
            out[pcfg[b].split("/")[-1]] = resolve_path(pcfg[b])
    if engine_cfg.v("column_aliases"):
        out[engine_cfg.v("column_aliases").split("/")[-1]] = resolve_path(engine_cfg.v("column_aliases"))
    return out


# ----------------------------------------------------------------------------- dataset
@dataclass
class Dataset:
    """A loaded dataset: raw frames, mission-view frames, registry and grid."""

    id: str
    grid: Grid
    raw: Dict[str, pd.DataFrame]
    cells: Dict[str, pd.DataFrame]
    reg: Dict
    inputs: List[Dict] = field(default_factory=list)


def load_dataset(engine_cfg: EngineConfig, paths: Optional[Dict[str, str]] = None) -> Dataset:
    """Read the tables, build the registry and the mission-view frames."""
    raw = load_raw(engine_cfg, paths)
    reg = build_registry(engine_cfg, raw)
    cols = reg["columns"]
    cells = {b: mission_view(raw[b], cols, b) for b in BODIES}
    for b, df in cells.items():
        for k in GRID_KEYS:
            if k not in df.columns:
                raise KeyError(f"{b}: input lacks {k}")
    return Dataset(id=engine_cfg.dataset_id, grid=grid_of(engine_cfg), raw=raw, cells=cells, reg=reg,
                   inputs=inputs_info(engine_cfg, raw, paths))
