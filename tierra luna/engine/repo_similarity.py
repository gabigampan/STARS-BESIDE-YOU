"""The repository's own Earth-Moon similarity (analog_finder.py), reused exactly.

The formula is that of ``analog_finder.compute_analog_ranking`` (team code, read at
git ref main and in the team's newer local copy; both are identical in these
functions):

1. Each body is normalised on its own with ``analog_finder.normalize_planetary_features``
   (called here, not copied): per variable, the median and a robust scale
   (IQR / 1.349, else the standard deviation, else 1) of that body's cells;
   ``z = clip((value - median) / scale, -4, 4)``, rounded to 4 decimals.
   Earth cells are those with ``elevation_m > 0`` (the function's land filter); the
   Moon uses every cell.
2. Variables and weights: ``analog_finder.ANALOG_FEATURES`` and ``DEFAULT_WEIGHTS``
   (imported). A variable is active when its weight is positive and it has values on
   both bodies (the function's rule), and it is not excluded by the dataset (team
   lead decision: rock_or_bare_frac on the real tables). Active weights are divided by
   their sum (``norm_w``), which redistributes an excluded weight in proportion.
3. Distance to a lunar target: ``d = sqrt(sum_v norm_w[v] * (z_earth[v] - z_target[v])^2)``
   and ``similarity_pct = 100 * exp(-decay * d)`` with the function's decay (0.45, in
   engine_config.json ``repo_similarity``), rounded with ``numpy.round`` to 2 decimals
   as the function does.

Two targets (engine_config ``similarity_rule``):

* ``repo_global_mean``: the target is the mean z profile of every lunar cell (the
  function's default target zone "Global Lunar Surface Mean"), rounded to 4
  decimals; one similarity per Earth cell, the same for every mission, no twin.
* ``zone_twin``: the target is the single lunar cell of the mission's zone with the
  smallest distance (the twin); ties go to the lowest lunar id.

One departure, forced by the rule that a missing value is never 0: the repository
sets the z-score of a missing value to 0 (the median). Here a missing value keeps a
missing z, the variable drops out of that pair's distance, and the remaining
``norm_w`` are renormalised (``d^2 = sum(norm_w * diff^2) / sum(norm_w present)``).
With every value present the arithmetic is exactly the repository's (no division).
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd


def repo_module():
    """The team's analog_finder module (imported lazily: it pulls in its own deps)."""
    import analog_finder  # noqa: WPS433  (team module next to the engine package)
    return analog_finder


def repo_features_and_weights() -> Tuple[List[str], Dict[str, float]]:
    """ANALOG_FEATURES and DEFAULT_WEIGHTS of analog_finder, as the repository defines them."""
    af = repo_module()
    return list(af.ANALOG_FEATURES), {k: float(v) for k, v in af.DEFAULT_WEIGHTS.items()}


@dataclass(frozen=True)
class BodyNorm:
    """Per-body normalisation of the similarity variables."""

    z: Dict[str, np.ndarray]            # per variable, aligned with the body's rows; NaN = missing or outside the population
    values: Dict[str, np.ndarray]       # the absolute values read (NaN = missing)
    stats: Dict[str, Dict]              # analog_finder's stats plus n, iqr_scale, std, distinct values
    population: np.ndarray              # bool: rows normalised (Earth: elevation_m > 0; Moon: all)


def normalise_body(values: Dict[str, np.ndarray], population: np.ndarray) -> BodyNorm:
    """Run analog_finder.normalize_planetary_features on the population rows.

    ``values``: {repository variable: float array over all rows of the body} (NaN =
    missing; a variable absent from the dataset is all NaN). Rows outside the
    population get a missing z; a missing value keeps a missing z (the repository
    would give it 0).
    """
    af = repo_module()
    feats = list(values)
    n = len(population)
    idx = np.flatnonzero(population)
    frame = pd.DataFrame({f: np.asarray(values[f], dtype=np.float64)[idx] for f in feats})
    norm, stats = af.normalize_planetary_features(frame, feats)
    out_z: Dict[str, np.ndarray] = {}
    out_stats: Dict[str, Dict] = {}
    for f in feats:
        v = np.asarray(values[f], dtype=np.float64)
        z = np.full(n, np.nan)
        zz = norm[f"{f}_z"].to_numpy(dtype=np.float64)
        z[idx] = np.where(np.isfinite(v[idx]), zz, np.nan)
        out_z[f] = z
        fin = v[idx][np.isfinite(v[idx])]
        extra: Dict = {"n": int(fin.size)}
        if fin.size:
            q25, q75 = np.percentile(fin, [25.0, 75.0])
            extra.update({"iqr": float(q75 - q25), "std_dev": float(np.std(fin)),
                          "distinct_values": int(np.unique(fin).size)})
        else:
            extra.update({"iqr": None, "std_dev": None, "distinct_values": 0})
        out_stats[f] = {**stats[f], **extra}
    return BodyNorm(z=out_z, values={f: np.asarray(values[f], dtype=np.float64) for f in feats},
                    stats=out_stats, population=np.asarray(population, dtype=bool))


def variation_report(stats: Dict[str, Dict], threshold: float) -> Dict[str, str]:
    """Variation class of each variable on one body, with the repository's own scale
    threshold (``normalize_planetary_features`` falls back when a scale is <= 1e-6):

    * ``no_data``: no value;
    * ``zero``: interquartile range and standard deviation both <= threshold (every
      value equal); the repository would give every cell z = 0 and still count the
      variable;
    * ``near_zero``: interquartile range <= threshold but standard deviation above it
      (at least half the cells share one value; the repository falls back to the std);
    * ``ok``: otherwise.
    """
    out: Dict[str, str] = {}
    for f, s in stats.items():
        if not s.get("valid") or s.get("n", 0) == 0:
            out[f] = "no_data"
        elif s["iqr"] <= threshold and s["std_dev"] <= threshold:
            out[f] = "zero"
        elif s["iqr"] <= threshold:
            out[f] = "near_zero"
        else:
            out[f] = "ok"
    return out


def active_weights(features: Sequence[str], weights: Dict[str, float], earth: BodyNorm, moon: BodyNorm,
                   excluded: Sequence[str]) -> Tuple[List[str], Dict[str, float]]:
    """(active variables in repository order, norm_w) by the repository's rule plus the
    dataset's exclusions: weight > 0, valid on both bodies, not excluded. norm_w = w / sum(w)."""
    act = [f for f in features if weights.get(f, 0.0) > 0 and earth.stats[f]["valid"] and moon.stats[f]["valid"]
           and f not in excluded]
    total = sum(weights[f] for f in act) or 1.0
    return act, {f: weights[f] / total for f in act}


def target_mean_profile(moon: BodyNorm, features: Sequence[str]) -> Dict[str, Dict[str, Optional[float]]]:
    """The "Global Lunar Surface Mean" target: per variable the mean z of every lunar
    cell (rounded to 4 decimals, as build_lunar_reference_zones) and the mean value."""
    out: Dict[str, Dict[str, Optional[float]]] = {}
    for f in features:
        z = moon.z[f][moon.population]
        z = z[np.isfinite(z)]
        v = moon.values[f][moon.population]
        v = v[np.isfinite(v)]
        out[f] = {"z": round(float(z.mean()), 4) if z.size else None,
                  "value": round(float(v.mean()), 4) if v.size else None}
    return out


def sq_distance(ez: Dict[str, np.ndarray], tz: Dict[str, np.ndarray], norm_w: Dict[str, float]) -> np.ndarray:
    """Weighted squared distance, broadcasting ``ez[v]`` against ``tz[v]``.

    Sums run in the order of ``norm_w`` (the repository's feature order). Where every
    variable is present the result is ``sum(norm_w * diff^2)`` exactly as the
    repository computes it; otherwise the present weights are renormalised. NaN when
    no variable is present.
    """
    sq = None
    wsum = None
    full = None
    for f, w in norm_w.items():
        diff = np.asarray(ez[f], dtype=np.float64) - np.asarray(tz[f], dtype=np.float64)
        ok = np.isfinite(diff)
        part = np.where(ok, w * np.where(ok, diff, 0.0) ** 2, 0.0)
        wp = np.where(ok, w, 0.0)
        sq = part if sq is None else sq + part
        wsum = wp if wsum is None else wsum + wp
        full = ok if full is None else (full & ok)
    if sq is None:
        raise ValueError("no active similarity variable")
    renorm = np.where(wsum > 0, sq / np.where(wsum > 0, wsum, 1.0), np.nan)
    return np.where(full, sq, renorm)


def similarity_from_sq(sq: np.ndarray, decay: float) -> np.ndarray:
    """100 * exp(-decay * sqrt(sq)), rounded with numpy.round to 2 decimals (as the
    repository publishes similarity_pct). NaN stays NaN."""
    sim = 100.0 * np.exp(-decay * np.sqrt(np.asarray(sq, dtype=np.float64)))
    return np.round(sim, 2)


def best_twins(ez: Dict[str, np.ndarray], mz: Dict[str, np.ndarray], norm_w: Dict[str, float],
               zone_ids: np.ndarray, chunk_rows: int) -> Tuple[np.ndarray, np.ndarray]:
    """(twin id, squared distance) of every Earth row: the zone cell with the smallest
    distance; ties go to the lowest id (``zone_ids`` strictly increasing; argmin keeps
    the first minimum). ``mz[v]`` holds the zone cells' z. -1 and NaN when no zone
    cell shares a present variable with the Earth row."""
    zone_ids = np.asarray(zone_ids)
    if zone_ids.size and np.any(np.diff(zone_ids) <= 0):
        raise ValueError("zone ids must be strictly increasing")
    n = len(next(iter(ez.values())))
    twin = np.full(n, -1, dtype=np.int64)
    best = np.full(n, np.nan)
    if n == 0 or zone_ids.size == 0:
        return twin, best
    for start in range(0, n, chunk_rows):
        stop = min(start + chunk_rows, n)
        sq = sq_distance({f: ez[f][start:stop, None] for f in norm_w}, {f: mz[f][None, :] for f in norm_w}, norm_w)
        filled = np.where(np.isfinite(sq), sq, np.inf)
        k = np.argmin(filled, axis=1)
        val = filled[np.arange(stop - start), k]
        has = np.isfinite(val)
        twin[start:stop] = np.where(has, zone_ids[k], -1)
        best[start:stop] = np.where(has, val, np.nan)
    return twin, best


@dataclass
class RepoContext:
    """Everything the repository similarity needs, computed once per build."""

    rule: str
    features: List[str]                 # ANALOG_FEATURES
    weights: Dict[str, float]           # DEFAULT_WEIGHTS
    columns: Dict[str, Dict[str, Optional[str]]]  # variable -> body -> column read (None = no column)
    excluded: Dict[str, str]            # variable -> reason (dataset decision)
    active: List[str]
    norm_w: Dict[str, float]
    decay: float
    earth: BodyNorm
    moon: BodyNorm
    variation: Dict[str, Dict[str, str]]  # body -> variable -> class
    target: Dict[str, Dict[str, Optional[float]]]
    global_sq: np.ndarray               # Earth rows: squared distance to the global mean target
    global_similarity: np.ndarray       # Earth rows: published similarity to the global mean target
    zones: Dict[str, Dict] = field(default_factory=dict)  # mission -> zone description and mask


def earth_population(earth: pd.DataFrame, rule: Dict) -> np.ndarray:
    """Earth rows normalised by the repository (``elevation_m > 0`` in compute_analog_ranking)."""
    v = pd.to_numeric(earth[rule["variable"]], errors="coerce").to_numpy(dtype=np.float64)
    return np.isfinite(v) & (v > float(rule["greater_than"]))


def read_columns(df: pd.DataFrame, columns: Dict[str, Optional[str]], features: Sequence[str]) -> Dict[str, np.ndarray]:
    """{variable: float array}; a variable without a column is all missing."""
    out = {}
    for f in features:
        c = columns.get(f)
        if c is None:
            out[f] = np.full(len(df), np.nan)
        else:
            if c not in df.columns:
                raise KeyError(f"similarity column {c!r} (for {f}) is not in the table")
            out[f] = pd.to_numeric(df[c], errors="coerce").to_numpy(dtype=np.float64)
    return out


def build_context(earth: pd.DataFrame, moon: pd.DataFrame, rule: str, settings: Dict,
                  columns: Dict[str, Dict[str, Optional[str]]], excluded: Dict[str, str]) -> RepoContext:
    """Normalise both bodies, choose the active variables and compute the global-mean
    similarity of every Earth row. ``settings`` = engine_config ``repo_similarity``."""
    feats, weights = repo_features_and_weights()
    for f in feats:
        if f not in columns:
            raise KeyError(f"datasets.json similarity_columns has no entry for {f}")
    e_pop = earth_population(earth, settings["earth_population"])
    m_pop = np.ones(len(moon), dtype=bool)
    en = normalise_body(read_columns(earth, {f: columns[f]["EARTH"] for f in feats}, feats), e_pop)
    mn = normalise_body(read_columns(moon, {f: columns[f]["MOON"] for f in feats}, feats), m_pop)
    thr = float(settings["zero_variation_threshold"])
    variation = {"EARTH": variation_report(en.stats, thr), "MOON": variation_report(mn.stats, thr)}
    act, norm_w = active_weights(feats, weights, en, mn, list(excluded))
    target = target_mean_profile(mn, feats)
    decay = float(settings["decay"])
    tz = {f: np.float64(target[f]["z"]) for f in act}
    gsq = sq_distance({f: en.z[f] for f in act}, tz, norm_w)
    gsim = similarity_from_sq(gsq, decay)
    return RepoContext(rule=rule, features=feats, weights=weights, columns=columns, excluded=dict(excluded),
                       active=act, norm_w=norm_w, decay=decay, earth=en, moon=mn, variation=variation,
                       target=target, global_sq=gsq, global_similarity=gsim)


def zone_mask(moon: pd.DataFrame, zone: Dict) -> np.ndarray:
    """Lunar cells of a zone. ``lat_max``: centre latitude at or below the bound (the
    code's south-pole zone, lat <= -75); ``cell_ids``: an explicit list of cells."""
    if zone["kind"] == "lat_max":
        return moon["lat_deg"].to_numpy(dtype=np.float64) <= float(zone["lat_max"])
    if zone["kind"] == "cell_ids":
        ids = set(int(i) for i in zone["cell_ids"])
        return np.array([int(i) in ids for i in moon["id"].to_numpy()], dtype=bool)
    raise ValueError(f"unknown zone kind {zone['kind']!r}")


def zone_twins(ctx: RepoContext, earth_rows: np.ndarray, zone: np.ndarray, moon_ids: np.ndarray,
               chunk_rows: int) -> Tuple[np.ndarray, np.ndarray]:
    """(twin id, published similarity) for the given Earth rows against the zone cells."""
    zi = np.flatnonzero(zone)
    tw, sq = best_twins({f: ctx.earth.z[f][earth_rows] for f in ctx.active},
                        {f: ctx.moon.z[f][zi] for f in ctx.active}, ctx.norm_w, moon_ids[zi], chunk_rows)
    return tw, similarity_from_sq(sq, ctx.decay)


def published_similarity_check(sim: np.ndarray) -> None:
    """Published similarities are exact at 2 decimals (q / 100)."""
    ok = np.isfinite(sim)
    q = np.rint(sim[ok] * 100.0)
    if not np.array_equal(q / 100.0, sim[ok]):
        raise AssertionError("published similarity is not exact at 2 decimals")


def exp_similarity(sq: float, decay: float) -> float:
    """Scalar version of :func:`similarity_from_sq` (documentation and tests)."""
    return float(np.round(100.0 * math.exp(-decay * math.sqrt(sq)), 2))
