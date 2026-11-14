"""Machine check of the bundle against docs/DATA_CONTRACT.md (pydantic models plus
cross-file consistency checks). Used by the tests; the app team can run it too:

    python -c "from engine.contract import validate_bundle_dir as v; print(v('../app/public/data/v1'))"
"""
from __future__ import annotations

import hashlib
import json
import os
from typing import Any, Dict, List, Literal, Optional, Union

from pydantic import BaseModel, ConfigDict, model_validator

Num = Optional[float]


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class FileEntry(_Strict):
    name: str
    bytes: int
    sha256: str


class Manifest(_Strict):
    bundle_version: str
    engine_version: str
    build_time: str
    input: Dict[str, Any]
    config_sha256: Dict[str, str]
    grid: Dict[str, Any]
    counts: Dict[str, Any]
    files: List[FileEntry]
    credits: List[str]


class Gate(_Strict):
    variable: str
    origin: Literal["common", "mission"]
    applies_to: List[Literal["EARTH", "MOON"]]
    min: Num
    max: Num
    max_from: Optional[str]
    allow: Optional[List[str]]
    exclude: Optional[List[str]]
    source: Optional[str]


class Weighted(_Strict):
    variable: str
    kind: Literal["numeric", "categorical"]
    label: str
    unit: str
    weight: float
    bad: Num
    good: Num
    map: Optional[Dict[str, float]]
    default: Num
    why: Optional[str]
    in_similarity: bool
    similarity_exclusion: Optional[str]


class Mission(_Strict):
    id: str
    title: str
    description: Optional[str]
    author: Optional[str]
    provisional: bool
    provisional_note: Optional[str]
    frozen_at: Optional[str]
    on_missing_gate: str
    require_present: List[str]
    gates: List[Gate]
    weighted_variables: List[Weighted]
    reason_codes: List[str]
    pass_counts: Dict[Literal["EARTH", "MOON"], int]
    ranked_count: int
    passing_without_twin: int
    top_failure_reasons: Dict[Literal["EARTH", "EARTH_LAND", "MOON"], List[Dict[str, Union[str, int]]]]
    mix_factor: float
    similarity_scales: Dict[str, Dict[str, Any]]
    confidence_counts: Dict[Literal["high", "medium", "low"], int]
    excluded_from_similarity: Dict[str, str]
    known_limitations: List[str]
    facts: Dict[str, Any]
    not_used_by_engine: Dict[str, Any]


class MissionsFile(_Strict):
    bundle_version: str
    config_version: Optional[str]
    config_note: Optional[str]
    twin_rule: str
    missions: List[Mission]


class BodyProv(_Strict):
    level: Literal["MEASURED", "DERIVED", "MODELLED", "UNDOCUMENTED"]
    audit_level: str
    caveat: str
    claimed_source: str
    code: str
    resolution_km: float
    level_note: Optional[str] = None
    valid_min: Num
    valid_max: Num


class Variable(_Strict):
    name: str
    label: str
    unit: str
    kind: Literal["numeric", "categorical"]
    description: str
    categories: Optional[List[str]]
    range_source: str
    comparable_across_bodies: bool
    comparability_note: str
    bodies: Dict[Literal["EARTH", "MOON"], BodyProv]


class VariablesFile(_Strict):
    levels: Dict[str, str]
    variables: List[Variable]


class Passing(_Strict):
    id: List[int]
    u: Dict[str, List[Num]]
    suitability: List[Num]
    missing_n: List[int]
    twin: List[Optional[int]]
    sim: Dict[str, List[Num]]
    similarity: List[Num]
    final: List[Num]
    rank: List[Optional[int]]
    confidence: List[Optional[Literal["high", "medium", "low"]]]
    confidence_score: List[Num]

    @model_validator(mode="after")
    def _aligned(self) -> "Passing":
        n = len(self.id)
        arrays = [self.suitability, self.missing_n, self.twin, self.similarity, self.final, self.rank,
                  self.confidence, self.confidence_score, *self.u.values(), *self.sim.values()]
        if any(len(a) != n for a in arrays):
            raise ValueError("passing arrays are not aligned with passing.id")
        return self


class CellMission(_Strict):
    reason_codes: List[str]
    pass_: List[Literal[0, 1]]
    fail: List[Optional[List[int]]]
    passing: Optional[Passing] = None
    twin_of_count: Optional[List[int]] = None

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    @classmethod
    def from_json(cls, d: Dict) -> "CellMission":
        d = dict(d)
        d["pass_"] = d.pop("pass")
        return cls.model_validate(d)


class CellsFile(_Strict):
    bundle_version: str
    body: Literal["EARTH", "MOON"]
    count: int
    id: List[int]
    lat: List[float]
    lon: List[float]
    land: Optional[List[Literal[0, 1]]] = None
    invalid_fields: Dict[str, List[str]]
    values: Dict[str, List[Union[float, str, None]]]
    ocean_fill: Optional[Dict[str, Any]] = None
    place: Optional[Dict[str, List[Any]]] = None
    feature: Optional[Dict[str, List[Any]]] = None
    missions: Dict[str, Dict[str, Any]]

    @model_validator(mode="after")
    def _lengths(self) -> "CellsFile":
        n = self.count
        cols = [self.id, self.lat, self.lon, *self.values.values()]
        if self.land is not None:
            cols.append(self.land)
        for grp in (self.place or {}, self.feature or {}):
            cols.extend(grp.values())
        if any(len(c) != n for c in cols):
            raise ValueError("a column does not have 'count' entries")
        if any(not -90 <= x <= 90 for x in self.lat) or any(not -180 <= x <= 180 for x in self.lon):
            raise ValueError("coordinates out of range")
        for mid, m in self.missions.items():
            cm = CellMission.from_json(m)
            if len(cm.pass_) != n or len(cm.fail) != n:
                raise ValueError(f"{mid}: pass/fail length")
            for p, f in zip(cm.pass_, cm.fail):
                if (p == 1) != (f is None):
                    raise ValueError(f"{mid}: a passing cell has reasons or a failing cell has none")
                if f is not None and any(not 0 <= i < len(cm.reason_codes) for i in f):
                    raise ValueError(f"{mid}: reason index out of range")
            if self.body == "EARTH":
                if cm.passing is None:
                    raise ValueError(f"{mid}: EARTH needs 'passing'")
                pos = {c: i for i, c in enumerate(self.id)}
                if any(cm.pass_[pos[c]] != 1 for c in cm.passing.id):
                    raise ValueError(f"{mid}: a gate-failed cell appears in 'passing'")
                if len(cm.passing.id) != sum(cm.pass_):
                    raise ValueError(f"{mid}: passing count mismatch")
            elif cm.twin_of_count is None or len(cm.twin_of_count) != n:
                raise ValueError(f"{mid}: MOON needs twin_of_count")
        return self


class ExplainVar(_Strict):
    variable: str
    earth: Union[float, str, None]
    moon: Union[float, str, None]
    difference: Num
    utility: Num
    similarity: Num
    weight: float
    suitability_weight: Num
    similarity_weight: Num
    suitability_points: Num
    similarity_points: Num
    final_points: Num
    lost_points: Num


class ExplainItem(_Strict):
    rank: int
    id: int
    lat: float
    lon: float
    place: Dict[str, Any]
    twin: Dict[str, Any]
    suitability: Num
    similarity: Num
    final: Num
    confidence: Optional[Literal["high", "medium", "low"]]
    confidence_score: Num
    missing_n: int
    variables: List[ExplainVar]
    helps_most: List[str]
    hurts_most: List[str]


class ExplainFile(_Strict):
    bundle_version: str
    top_n: int
    missions: Dict[str, List[ExplainItem]]


class IauFile(_Strict):
    credit: str
    source: Dict[str, Any]
    excluded_types: List[str]
    longitude_convention: str
    count: int
    name: List[str]
    type: List[str]
    lat: List[float]
    lon: List[float]
    diameter_km: List[Num]


def validate_bundle_dir(path: str) -> Dict[str, Any]:
    """Validate every file and the manifest hashes; raises on the first problem."""
    def load(n: str) -> Any:
        with open(os.path.join(path, n), encoding="utf-8") as fh:
            return json.load(fh)

    man = Manifest.model_validate(load("manifest.json"))
    for f in man.files:
        data = open(os.path.join(path, f.name), "rb").read()
        if len(data) != f.bytes or hashlib.sha256(data).hexdigest() != f.sha256:
            raise ValueError(f"manifest size/hash mismatch for {f.name}")
    missions = MissionsFile.model_validate(load("missions.json"))
    VariablesFile.model_validate(load("variables.json"))
    earth = CellsFile.model_validate(load("earth_cells.json"))
    moon = CellsFile.model_validate(load("moon_cells.json"))
    ExplainFile.model_validate(load("explain.json"))
    IauFile.model_validate(load("iau_moon_features.json"))
    for m in missions.missions:
        e = earth.missions[m.id]
        if sum(e["pass"]) != m.pass_counts["EARTH"] or sum(moon.missions[m.id]["pass"]) != m.pass_counts["MOON"]:
            raise ValueError(f"{m.id}: pass counts differ between missions.json and cells")
        moon_pass = {i for i, p in zip(moon.id, moon.missions[m.id]["pass"]) if p == 1}
        p = e["passing"]
        if any(t is not None and t not in moon_pass for t in p["twin"]):
            raise ValueError(f"{m.id}: a twin is a lunar cell that fails the mission")
        check_rank_rule(m.id, p["id"], p["final"], p["rank"])
        for t, f, r in zip(p["twin"], p["final"], p["rank"]):
            if t is None and (f is not None or r is not None):
                raise ValueError(f"{m.id}: a cell without a twin has a final score or a rank")
            if (f is None) != (r is None):
                raise ValueError(f"{m.id}: final and rank must both be null or both be set")
        if set(m.excluded_from_similarity) & set(p["sim"]):
            raise ValueError(f"{m.id}: a variable excluded from the similarity has similarities")
    check_ocean_fill(earth)
    return {"ok": True, "files": [f.name for f in man.files]}


def check_rank_rule(mission: str, ids: List[int], final: List[Optional[float]], rank: List[Optional[int]]) -> None:
    """The stored rank must be the contract rule applied to the stored final:
    final descending, ties by id ascending, starting at 1; null final = no rank."""
    scored = sorted((-f, i) for i, f in zip(ids, final) if f is not None)
    expected = {i: k + 1 for k, (_, i) in enumerate(scored)}
    for i, r in zip(ids, rank):
        if expected.get(i) != r:
            raise ValueError(f"{mission}: stored rank of cell {i} is {r}, the contract rule gives {expected.get(i)}")


def check_ocean_fill(earth: "CellsFile") -> None:
    """Fill variables must be null on every non-land Earth cell (null means missing)."""
    if earth.ocean_fill is None or earth.land is None:
        raise ValueError("earth_cells.json needs 'land' and 'ocean_fill'")
    for v in earth.ocean_fill["variables"]:
        col = earth.values[v]
        if any(col[i] is not None for i, l in enumerate(earth.land) if l == 0):
            raise ValueError(f"{v}: an ocean fill value is exported as data")


def check_values_match_input(cells_obj: Dict[str, Any], df: Any, variables: List[str]) -> None:
    """values[v][i] must be null exactly where the input value is missing (for cells
    that are not blanked as ocean fills). ``df`` is the body's table sorted by id."""
    import pandas as pd

    blanked = set()
    land = cells_obj.get("land")
    if cells_obj.get("ocean_fill") and land is not None:
        blanked = {(v, i) for v in cells_obj["ocean_fill"]["variables"] for i, l in enumerate(land) if l == 0}
    for v in variables:
        raw = df[v]
        miss = (raw.isna() | raw.astype(str).str.strip().str.lower().isin(["", "nan"])).to_numpy()
        for i, x in enumerate(cells_obj["values"][v]):
            if (v, i) in blanked:
                continue
            if bool(miss[i]) != (x is None):
                raise ValueError(f"{v}[{i}]: exported {x!r} but input missing={bool(miss[i])}")
