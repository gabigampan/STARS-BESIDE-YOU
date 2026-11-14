# AI-assisted (Claude, Anthropic). Declared in docs/AI_USE.md.
"""
rover_preset.py  (version 3)

Physics checks and `rover` preset builder for the analog finder.

CHANGES IN VERSION 3 (nothing from versions 1 and 2 was removed):
  7. Abrasive wear: new level C row in the Test Transfer Card (wear of
     wheels, seals and bearings is tested on Earth, never predicted; rounded
     Earth sand is less abrasive than angular lunar regolith).
  8. Abrasivity excluded from the score on purpose, with the reason (no
     global layer of grain shape or hardness).
  9. Wear-test hint per site from its GLiM lithology class
     (wear_test_hint): volcanic and pyroclastic sites are flagged as better
     candidates for wear tests, loose sediments as optimistic. It is a flag
     for the site card, it does not change any score.

CHANGES IN VERSION 2 (nothing from version 1 was removed):
  1. Relief baseline: tolerances and gates are defined for 300 m (Earth
     Engine route) and 5 km (EarthEnv route). The baseline is chosen from the
     columns that really exist in earth_cells (pass them with --columns or
     available_columns=...), or forced with --baseline.
  2. Slope gate on the 90th percentile: if a p90 slope column exists
     (slope_300m_p90_deg / slope_5km_p90_deg), the gate uses it instead of the
     median, because a rover is stopped by the steepest stretches.
  3. Rock density excluded on purpose, with the reason written in the preset
     (Diviner rock abundance stops at 60 S; the Shackleton region is 84-90 S).
     Ground clearance goes to the Test Transfer Card as a rover property.
  4. Soft soil: new level C row in the Test Transfer Card (getting stuck or
     sinking is tested on Earth, never predicted), with the reason.
  5. Soil grain class: thermal_inertia_class added as a class feature of the
     rover preset (dust / sand / coarse_or_crust / rock), plus helpers to
     classify TES thermal inertia and to build the class similarity matrix.
  6. Ranking sanity check (--check-scores): Bardenas (BASEPROD site) and the
     other mobility analogs should rank high; operations-only sites low.
  Config format: tolerances and gates now live in "tolerances_common",
  "tolerances_by_baseline" and "gates_by_baseline". PRESET_CONFIG still has
  the version 1 "tolerances" key, because analog_finder.py reads it.

Self-contained: one Python file, no dependencies beyond the standard library.
Works for any rover (wheels, tracks, legs). The rover is described in the dict
ROVER_SPEC and the preset choices (weights, tolerances, gates) in PRESET_CONFIG,
both defined below. Nothing is downloaded: fill ROVER_SPEC from the project's
NASA database (or pass a JSON file with --rover / --config).

Conventions (same as the integration contract):
  - SI units, NaN for missing data (never 0).
  - Rover frame: x forward, y left, z up, origin on the ground at the centre
    of the contact footprint.
  - Every number that reaches presets.json needs a written `source`.

What this module does NOT do (plan, section 5): it never predicts slip,
sinkage, traction or maximum climbable slope on the Moon or Mars.

Usage:
  python rover_preset.py                       # print results
  python rover_preset.py --selftest            # run the built-in checks
  python rover_preset.py --columns slope_5km_deg,rough_5km_m,...
                                               # pick baseline from real columns
  python rover_preset.py --presets data/presets/presets.json \\
      --author "Robotics 1" --freeze           # write the frozen preset
  python rover_preset.py --check-scores scores.json
                                               # sanity check of the ranking
  Options: --rover <json> --config <json> --gravity <json>
           --baseline 300m|5km --allow-unverified --refreeze

In code:
  import rover_preset as rp
  preset = rp.build_rover_preset(rp.ROVER_SPEC, rp.PRESET_CONFIG,
                                 rp.DEFAULT_GRAVITY, author="Robotics 1",
                                 available_columns=list(earth_cells.columns))
  report = rp.validate_rover_ranking({"Bardenas": 81.0, "Rio Tinto": 22.0})
  hint = rp.wear_test_hint("vb")   # GLiM class of a named site
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import math
from pathlib import Path

NAN = float("nan")

# m/s^2. NASA Planetary Fact Sheet values used in the phase-1 plan.
# Override with --gravity <json> to read them from the project database.
DEFAULT_GRAVITY = {"earth": 9.81, "moon": 1.62, "mars": 3.73}

SECTORS = (
    "relief",
    "surface_material",
    "thermal_regime",
    "light_and_sky",
    "water_ice_aridity",
)

# Values with these sources/statuses cannot be frozen unless --allow-unverified.
PLACEHOLDER_SOURCES = {"", "PENDIENTE", "PENDING", "TODO"}
UNVERIFIED_MARKERS = {"VERIFICAR", "VERIFY", "ESTIMADO", "ESTIMATED",
                      "ILUSTRATIVO", "ILLUSTRATIVE"}

# Relief baselines in the contract. Feature names carry the baseline.
BASELINES = ("300m", "5km")

# Soil grain classes from thermal inertia (TES units, J m^-2 K^-1 s^-1/2).
# Indicative thresholds from the phase-1 plan, section 3.
TI_CLASSES = ("dust", "sand", "coarse_or_crust", "rock")
TI_THRESHOLDS = (150.0, 350.0, 600.0)

# Features left out of the rover score on purpose, with the reason.
EXCLUDED_FEATURES = [
    {"feature": "rock_abundance",
     "reason": "Diviner rock abundance only reaches 60 S; the Shackleton "
               "region (84-90 S) has no comparable rock data, so rock density "
               "cannot be compared at the lunar target.",
     "source": "Phase-1 plan, section 4 (limits found in testing)"},
    {"feature": "abrasivity",
     "reason": "Abrasiveness depends on grain shape and hardness; no global "
               "orbital layer measures it at 300 m or 5 km. Handled as a level C "
               "row of the Test Transfer Card and as a site flag "
               "(wear_test_hint), never as a score.",
     "source": "No dataset in the phase-1 data inventory"},
]

# Wear-test hint from GLiM lithology classes (16 classes, plan section 4).
# Volcanic and pyroclastic material can keep angular grains, closer to
# lunar regolith; loose sediments are usually rounded by wind or water.
# GLiM does not say how young or angular the material is: this is a hint
# to check in the field, not a measurement.
WEAR_GOOD_CLASSES = {"py": "pyroclastics", "vb": "basic volcanic",
                     "vi": "intermediate volcanic", "va": "acid volcanic"}
WEAR_OPTIMISTIC_CLASSES = {"su": "unconsolidated sediments",
                           "ss": "siliciclastic sedimentary",
                           "sm": "mixed sedimentary", "sc": "carbonate sedimentary",
                           "ev": "evaporites"}

# Ranking sanity check (phase-1 plan, section 5). Names as in the benchmark.
MOBILITY_POSITIVES = ("Bardenas", "Tabernas", "Dumont Dunes", "MDRS", "Yungay",
                      "Erfoud", "Dhofar", "Ramon", "Haughton", "Death Valley",
                      "Qaidam")
MOBILITY_MISMATCHES = ("Concordia", "NEEMO", "HI-SEAS", "Rio Tinto", "El Soplao")
BASEPROD_REF = ("BASEPROD rover dataset at Bardenas Reales, Gerdes et al., "
                "Scientific Data 11:1054 (2024), doi:10.1038/s41597-024-03881-1")


# --------------------------------------------------------------------------
# Rover description. Approximate VIPER reference.
# Replace every value with status "VERIFICAR" using the project NASA
# database before freezing. Fields: {"value", "unit", "source", "status"}.
# Optional keys: "mass_budget" (list of {"name", "mass_kg", "x_m", "y_m",
# "z_m", "source"}) and "contact_points_m" (list of [x, y]) for rovers
# that are not a 4-contact rectangle.
# --------------------------------------------------------------------------
ROVER_SPEC = {
    "name": "VIPER (approximation)",
    "locomotion": "wheels",
    "mass_kg":                {"value": 440,  "unit": "kg",  "source": "Phase-1 plan (VIPER, arXiv 2405.11001)", "status": "OK"},
    "cg_height_m":            {"value": 0.60, "unit": "m",   "source": "ESTIMADO - replace from project DB", "status": "VERIFICAR"},
    "cg_x_m":                 {"value": 0.0,  "unit": "m",   "source": "assumed centred", "status": "VERIFICAR"},
    "cg_y_m":                 {"value": 0.0,  "unit": "m",   "source": "assumed centred", "status": "VERIFICAR"},
    "wheelbase_m":            {"value": 1.30, "unit": "m",   "source": "ESTIMADO from ~1.5 m body length - replace from project DB", "status": "VERIFICAR"},
    "track_m":                {"value": 1.30, "unit": "m",   "source": "ESTIMADO from ~1.5 m body width - replace from project DB", "status": "VERIFICAR"},
    "n_contacts":             {"value": 4,    "unit": "-",   "source": "four wheels", "status": "OK"},
    "contact_patch_length_m": {"value": 0.10, "unit": "m",   "source": "ESTIMADO - replace from project DB", "status": "VERIFICAR"},
    "contact_patch_width_m":  {"value": 0.20, "unit": "m",   "source": "ESTIMADO wheel width - replace from project DB", "status": "VERIFICAR"},
    "ground_clearance_m":     {"value": None, "unit": "m",   "source": "", "status": "MISSING"},
    "max_speed_mps":          {"value": 0.20, "unit": "m/s", "source": "NASA VIPER Industry Day Technical Briefing, 13 Feb 2025, p.17 and p.47: 'Top Speed: 20cm/s (0.5MPH)' (docs/sources/R1_viper_rover_spec_sources.md)", "status": "OK"},
    "max_operational_slope_deg": {"value": 15, "unit": "deg", "source": "NASA requirement: 'Slopes up to 15 deg (reqt)', Bluethmann, VIPER Rover Overview and Mobility and Hardware, NTRS 20240013903, p.4 (rover-scale requirement, not a DEM-baseline slope; docs/sources/R1_viper_rover_spec_sources.md)", "status": "OK"},
}

# --------------------------------------------------------------------------
# Preset choices. Robotics 1 sets every number and source.
# Values marked ILUSTRATIVO only show the format and cannot be frozen.
# --------------------------------------------------------------------------
PRESET_CONFIG = {
    "weights": {
        "relief":            {"value": 0.35, "source": "ILUSTRATIVO - plan sec. 3 order only (relief and material weigh more)"},
        "surface_material":  {"value": 0.30, "source": "ILUSTRATIVO - plan sec. 3 order only"},
        "thermal_regime":    {"value": 0.10, "source": "ILUSTRATIVO"},
        "light_and_sky":     {"value": 0.10, "source": "ILUSTRATIVO"},
        "water_ice_aridity": {"value": 0.15, "source": "ILUSTRATIVO"},
    },
    # "auto": choose from the columns that exist in earth_cells.
    "baseline": "auto",
    # Gate on the p90 slope column when it exists.
    "gate_prefer_p90": True,
    # Features that do not depend on the relief baseline.
    "tolerances_common": {
        "thermal_inertia_class": {
            "type": "class", "classes": list(TI_CLASSES),
            "same": 1.0, "neighbour": 0.5,
            "unit": "class",
            "source": "ILUSTRATIVO - matrix values proposed in plan sec. 3; set by Robotics 1",
        },
    },
    "tolerances_by_baseline": {
        "300m": {
            "slope_300m_deg": {"scale": 5.0,  "unit": "deg", "source": "ILUSTRATIVO - set by Robotics 1"},
            "rough_300m_m":   {"scale": 10.0, "unit": "m",   "source": "ILUSTRATIVO - set by Robotics 1"},
        },
        "5km": {
            "slope_5km_deg": {"scale": 2.0,  "unit": "deg", "source": "ILUSTRATIVO - set by Robotics 1 (5 km slopes are much gentler)"},
            "rough_5km_m":   {"scale": 30.0, "unit": "m",   "source": "ILUSTRATIVO - set by Robotics 1 (check EarthEnv roughness definition, contract asks RMS)"},
        },
    },
    # Version 1 key kept for code that reads PRESET_CONFIG["tolerances"]
    # directly (analog_finder.py does). The builder uses the keys above.
    "tolerances": {
        "slope_300m_deg": {"scale": 5.0,  "unit": "deg", "source": "ILUSTRATIVO - set by Robotics 1"},
        "rough_300m_m":   {"scale": 10.0, "unit": "m",   "source": "ILUSTRATIVO - set by Robotics 1"},
    },
    "gates_by_baseline": {
        "300m": {
            "slope_300m_deg": {"min": None, "max_from": "max_operational_slope_deg"},
            "rough_300m_m":   {"min": None, "max": None, "source": "no gate until Robotics 1 sets one"},
        },
        "5km": {
            "slope_5km_deg": {"min": None, "max_from": "max_operational_slope_deg",
                              "note": "a 5 km mean hides local slopes even more; weak gate"},
            "rough_5km_m":   {"min": None, "max": None, "source": "no gate until Robotics 1 sets one"},
        },
    },
    "workable_days": {
        "rain_mm_max": 1, "wind_max_ms_max": 12, "tmin_c_min": -10,
        "source": "ILUSTRATIVO - phase-1 plan, model 1 defaults",
    },
}


# --------------------------------------------------------------------------
# Reading rover specs
# --------------------------------------------------------------------------
def _field(spec: dict, key: str) -> dict:
    """Return a field as {'value', 'unit', 'source', 'status'}."""
    raw = spec.get(key)
    if raw is None:
        return {"value": None, "unit": None, "source": "", "status": "MISSING"}
    if isinstance(raw, dict):
        return {
            "value": raw.get("value"),
            "unit": raw.get("unit"),
            "source": raw.get("source", ""),
            "status": raw.get("status", "OK"),
        }
    return {"value": raw, "unit": None, "source": "", "status": "OK"}


def value(spec: dict, key: str) -> float:
    v = _field(spec, key)["value"]
    return NAN if v is None else float(v)


def is_unverified(field: dict) -> bool:
    status = str(field.get("status", "")).upper()
    source = str(field.get("source", "")).strip().upper()
    return (
        status in UNVERIFIED_MARKERS
        or status == "MISSING"
        or source in PLACEHOLDER_SOURCES
        or any(source.startswith(m) for m in UNVERIFIED_MARKERS)
    )


def mass_properties(rover: dict) -> tuple[float, tuple[float, float, float]]:
    """Total mass and centre of gravity.

    If the rover has a `mass_budget` (list of subsystems with mass and
    position), mass and CG are computed from it. Otherwise `mass_kg` and
    `cg_x_m`, `cg_y_m`, `cg_height_m` are used directly.
    """
    budget = rover.get("mass_budget")
    if budget:
        m = sum(float(item["mass_kg"]) for item in budget)
        if m <= 0:
            return NAN, (NAN, NAN, NAN)
        cx = sum(float(i["mass_kg"]) * float(i.get("x_m", 0.0)) for i in budget) / m
        cy = sum(float(i["mass_kg"]) * float(i.get("y_m", 0.0)) for i in budget) / m
        cz = sum(float(i["mass_kg"]) * float(i["z_m"]) for i in budget) / m
        return m, (cx, cy, cz)
    cx = value(rover, "cg_x_m")
    cy = value(rover, "cg_y_m")
    return value(rover, "mass_kg"), (
        0.0 if math.isnan(cx) else cx,
        0.0 if math.isnan(cy) else cy,
        value(rover, "cg_height_m"),
    )


def contact_points(rover: dict) -> list[tuple[float, float]]:
    """Ground contact points (x, y). Explicit list, or a rectangle built
    from wheelbase and track for a 4-contact rover."""
    pts = rover.get("contact_points_m")
    if pts:
        return [(float(p[0]), float(p[1])) for p in pts]
    wb, tr = value(rover, "wheelbase_m"), value(rover, "track_m")
    if math.isnan(wb) or math.isnan(tr):
        return []
    return [(wb / 2, tr / 2), (-wb / 2, tr / 2), (-wb / 2, -tr / 2), (wb / 2, -tr / 2)]


# --------------------------------------------------------------------------
# Geometry and physics (level A unless stated)
# --------------------------------------------------------------------------
def _convex_hull(points: list[tuple[float, float]]) -> list[tuple[float, float]]:
    """Counter-clockwise convex hull (monotone chain)."""
    pts = sorted(set(points))
    if len(pts) < 3:
        return pts

    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])

    lower, upper = [], []
    for p in pts:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], p) <= 0:
            lower.pop()
        lower.append(p)
    for p in reversed(pts):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], p) <= 0:
            upper.pop()
        upper.append(p)
    return lower[:-1] + upper[:-1]


def _direction_label(angle_deg: float) -> str:
    a = (angle_deg + 360.0) % 360.0
    if a <= 45 or a > 315:
        return "forward"
    if a <= 135:
        return "left"
    if a <= 225:
        return "rearward"
    return "right"


def static_tipover(points: list[tuple[float, float]],
                   cg: tuple[float, float, float]) -> dict:
    """Static tip-over angle about each edge of the support polygon.

    angle = atan(d / h), d = horizontal distance from the CG projection to
    the edge, h = CG height. Independent of gravity, so it transfers exactly
    from Earth to the Moon or Mars (Test Transfer Card, level A).
    Dynamic effects, soft soil and suspension travel are not included.
    """
    hull = _convex_hull(points)
    h = cg[2]
    if len(hull) < 3 or math.isnan(h) or h <= 0:
        return {"min_deg": NAN, "edges": [], "stable": None,
                "note": "no data: needs >=3 contact points and a CG height"}
    edges, inside = [], True
    for i, p1 in enumerate(hull):
        p2 = hull[(i + 1) % len(hull)]
        ex, ey = p2[0] - p1[0], p2[1] - p1[1]
        length = math.hypot(ex, ey)
        # CCW hull: positive distance means the CG is inside.
        d = (ex * (cg[1] - p1[1]) - ey * (cg[0] - p1[0])) / length
        if d <= 0:
            inside = False
        normal_deg = math.degrees(math.atan2(-ex, ey))  # outward normal
        edges.append({
            "direction": _direction_label(normal_deg),
            "normal_deg": round(normal_deg, 1),
            "lever_arm_m": round(d, 4),
            "angle_deg": round(math.degrees(math.atan2(d, h)), 2) if d > 0 else 0.0,
        })
    return {
        "min_deg": min(e["angle_deg"] for e in edges),
        "edges": edges,
        "stable": inside,
        "note": "static, rigid, hard ground; independent of g",
    }


def weight_force_n(mass_kg: float, g: float) -> float:
    """Weight available on a tool or drill: m * g."""
    return mass_kg * g


def ground_pressure_pa(mass_kg: float, g: float, n_contacts: float,
                       patch_length_m: float, patch_width_m: float) -> float:
    """Mean static ground pressure, rigid contact patch."""
    area = n_contacts * patch_length_m * patch_width_m
    if any(math.isnan(x) for x in (area, mass_kg)) or area <= 0:
        return NAN
    return mass_kg * g / area


def earth_twin_mass_kg(mass_kg: float, g_target: float, g_earth: float) -> float:
    """Mass an Earth twin needs to load the ground as the real rover does
    on the target body (same weight, same footprint)."""
    return mass_kg * g_target / g_earth


def froude_test_speed(v_target_mps: float, g_target: float, g_earth: float) -> float:
    """Earth test speed that matches the Froude number v^2 / (g L)
    for the same rover size."""
    return v_target_mps * math.sqrt(g_earth / g_target)


def transfer_physics(rover: dict, gravity: dict, targets=("moon", "mars")) -> dict:
    mass, cg = mass_properties(rover)
    g_e = gravity["earth"]
    n = value(rover, "n_contacts")
    pl, pw = value(rover, "contact_patch_length_m"), value(rover, "contact_patch_width_m")
    v = value(rover, "max_speed_mps")
    out = {
        "earth": {
            "weight_n": round(weight_force_n(mass, g_e), 1),
            "ground_pressure_pa": round(ground_pressure_pa(mass, g_e, n, pl, pw), 1),
        }
    }
    for body in targets:
        g_t = gravity[body]
        out[body] = {
            "g_mps2": g_t,
            "weight_n": round(weight_force_n(mass, g_t), 1),
            "ground_pressure_pa": round(ground_pressure_pa(mass, g_t, n, pl, pw), 1),
            "earth_twin_mass_kg": round(earth_twin_mass_kg(mass, g_t, g_e), 1),
            "earth_load_ratio": round(g_e / g_t, 2),
            "froude_speed_factor": round(math.sqrt(g_e / g_t), 2),
            "earth_test_speed_mps": round(froude_test_speed(v, g_t, g_e), 3),
        }
    return out


# --------------------------------------------------------------------------
# Soil grain class (thermal inertia)
# --------------------------------------------------------------------------
def thermal_inertia_class(ti: float) -> str | None:
    """Classify a TES thermal inertia value (Mars) into a grain class.
    Jezero (TES 276) -> 'sand'. Earth uses apparent thermal inertia by
    percentile (Programmer 1); the lunar polar region has no product."""
    if ti is None or (isinstance(ti, float) and math.isnan(ti)):
        return None
    for limit, name in zip(TI_THRESHOLDS, TI_CLASSES):
        if ti < limit:
            return name
    return TI_CLASSES[-1]


def class_similarity_matrix(classes, same: float = 1.0,
                            neighbour: float = 0.5) -> dict:
    """M_f[class_c][class_T]: `same` on the diagonal, `neighbour` for adjacent
    classes in the ordered list, 0 otherwise (plan, section 3)."""
    m = {}
    for i, a in enumerate(classes):
        m[a] = {}
        for j, b in enumerate(classes):
            m[a][b] = same if i == j else (neighbour if abs(i - j) == 1 else 0.0)
    return m


# --------------------------------------------------------------------------
# Abrasive wear hint (site flag, not a score)
# --------------------------------------------------------------------------
def wear_test_hint(lithology_class: str | None) -> dict:
    """Return a wear-test hint for a site from its GLiM class code."""
    code = (lithology_class or "").strip().lower()
    if code in WEAR_GOOD_CLASSES:
        return {"hint": "candidate_for_wear_tests",
                "text": f"{WEAR_GOOD_CLASSES[code]}: may keep angular grains, "
                        "closer to lunar regolith for wear tests (check in the field)"}
    if code in WEAR_OPTIMISTIC_CLASSES:
        return {"hint": "optimistic_for_wear",
                "text": f"{WEAR_OPTIMISTIC_CLASSES[code]}: grains usually rounded, "
                        "wear tests here underestimate lunar abrasion"}
    return {"hint": "no_data",
            "text": "no wear hint for this lithology class"}


# --------------------------------------------------------------------------
# Relief baseline
# --------------------------------------------------------------------------
def choose_baseline(config: dict, available_columns=None, forced: str | None = None,
                    issues: list | None = None) -> str:
    """300m if its slope column exists, otherwise 5km. Without the column
    list it falls back to 300m and records a warning."""
    issues = issues if issues is not None else []
    choice = forced or config.get("baseline", "auto")
    if choice in BASELINES:
        if available_columns is not None and f"slope_{choice}_deg" not in available_columns:
            issues.append(f"baseline {choice} forced but slope_{choice}_deg is not in earth_cells")
        return choice
    if available_columns is None:
        issues.append("baseline not confirmed: pass the earth_cells columns "
                      "(--columns) so 300m/5km is chosen from real data")
        return "300m"
    if "slope_300m_deg" in available_columns:
        return "300m"
    if "slope_5km_deg" in available_columns:
        return "5km"
    issues.append("no slope column found in earth_cells; using 300m names")
    return "300m"


def p90_name(feature: str) -> str:
    """slope_300m_deg -> slope_300m_p90_deg."""
    head, _, unit = feature.rpartition("_")
    return f"{head}_p90_{unit}"


# --------------------------------------------------------------------------
# Preset builder
# --------------------------------------------------------------------------
class PresetError(ValueError):
    pass


def _resolve_gates(gates_cfg: dict, rover: dict, tip_min: float, issues: list,
                   available_columns=None, prefer_p90: bool = False) -> dict:
    gates = {}
    for feature, g in (gates_cfg or {}).items():
        gate = {"min": g.get("min"), "max": g.get("max"), "source": g.get("source", "")}
        if g.get("note"):
            gate["note"] = g["note"]
        if g.get("max_from"):
            f = _field(rover, g["max_from"])
            gate["max"] = f["value"]
            gate["source"] = f"rover.{g['max_from']}: {f['source']}"
            if is_unverified(f):
                issues.append(f"gate {feature}: rover field {g['max_from']} is not verified")
        elif str(gate["source"]).strip().upper() in PLACEHOLDER_SOURCES:
            issues.append(f"gate {feature}: missing source")
        if feature.startswith("slope") and gate["max"] is not None and not math.isnan(tip_min):
            if float(gate["max"]) >= tip_min:
                raise PresetError(
                    f"gate {feature} max {gate['max']} deg is not below the static "
                    f"tip-over angle {tip_min} deg")
        target_feature = feature
        if prefer_p90 and feature.startswith("slope"):
            p90 = p90_name(feature)
            if available_columns is not None and p90 in available_columns:
                target_feature = p90
                gate["applies_to"] = "p90 of the cell (steepest stretches)"
            else:
                gate["applies_to"] = "median of the cell"
                issues.append(f"gate {feature}: {p90} not available, gate uses the "
                              "median slope (permissive)")
        gates[target_feature] = gate
    return gates


def build_rover_preset(rover: dict, config: dict, gravity: dict, author: str,
                       freeze: bool = False, allow_unverified: bool = False,
                       available_columns=None, baseline: str | None = None) -> dict:
    issues: list[str] = []
    if available_columns is not None:
        available_columns = set(available_columns)
    base = choose_baseline(config, available_columns, baseline, issues)

    # Rover fields used by the physics.
    used = ["mass_kg", "cg_height_m", "wheelbase_m", "track_m", "n_contacts",
            "contact_patch_length_m", "contact_patch_width_m", "max_speed_mps"]
    if rover.get("mass_budget"):
        used = [u for u in used if u not in ("mass_kg", "cg_height_m")]
        for item in rover["mass_budget"]:
            if is_unverified(item):
                issues.append(f"mass_budget item '{item.get('name')}' is not verified")
    unverified = [k for k in used if k in rover and is_unverified(_field(rover, k))]
    issues += [f"rover field {k} is not verified" for k in unverified]

    mass, cg = mass_properties(rover)
    tip = static_tipover(contact_points(rover), cg)
    if tip["stable"] is False:
        raise PresetError("CG projection falls outside the support polygon")

    # Sector weights, normalised to sum 1.
    raw_w = config.get("weights") or {}
    unknown = set(raw_w) - set(SECTORS)
    if unknown:
        raise PresetError(f"unknown sectors in weights: {sorted(unknown)}")
    weights, weight_sources = {}, {}
    for k, w in raw_w.items():
        val = float(w["value"]) if isinstance(w, dict) else float(w)
        src = w.get("source", "") if isinstance(w, dict) else ""
        if val < 0:
            raise PresetError(f"negative weight for {k}")
        weights[k], weight_sources[k] = val, src
        if is_unverified({"source": src}):
            issues.append(f"weight {k}: source missing or illustrative")
    total = sum(weights.values())
    if total <= 0:
        raise PresetError("weights sum to 0")
    weights = {k: round(v / total, 4) for k, v in weights.items()}

    # Tolerances. Physical: {scale, unit, source}. Class: {type: class,
    # classes, matrix, source}. Version 1 key "tolerances" still accepted.
    if "tolerances_by_baseline" in config or "tolerances_common" in config:
        tol_cfg = dict(config.get("tolerances_common") or {})
        tol_cfg.update((config.get("tolerances_by_baseline") or {}).get(base, {}))
    else:
        tol_cfg = config.get("tolerances") or {}
    tolerances = {}
    for feat, t in tol_cfg.items():
        if t.get("type") == "class":
            classes = list(t["classes"])
            tolerances[feat] = {
                "type": "class", "classes": classes,
                "matrix": t.get("matrix") or class_similarity_matrix(
                    classes, float(t.get("same", 1.0)), float(t.get("neighbour", 0.5))),
                "unit": t.get("unit", "class"), "source": t.get("source", ""),
            }
        else:
            if float(t["scale"]) <= 0:
                raise PresetError(f"tolerance {feat}: scale must be > 0")
            tolerances[feat] = {"scale": float(t["scale"]), "unit": t.get("unit"),
                                "source": t.get("source", "")}
        if is_unverified({"source": t.get("source", "")}):
            issues.append(f"tolerance {feat}: source missing or illustrative")
        if available_columns is not None and feat not in available_columns:
            issues.append(f"tolerance {feat}: column not in earth_cells")

    if "gates_by_baseline" in config:
        gates_cfg = (config.get("gates_by_baseline") or {}).get(base, {})
    else:
        gates_cfg = config.get("gates") or {}
    gates = _resolve_gates(gates_cfg, rover, tip["min_deg"], issues,
                           available_columns, bool(config.get("gate_prefer_p90")))

    if freeze and issues and not allow_unverified:
        raise PresetError("cannot freeze, unresolved items:\n  - " + "\n  - ".join(issues))

    physics = transfer_physics(rover, gravity)
    preset = {
        "weights": weights,
        "weight_sources": weight_sources,
        "tolerances": tolerances,
        "gates": gates,
        "baseline": base,
        "excluded_features": EXCLUDED_FEATURES,
        "wear_test_flags": {
            "good_classes": WEAR_GOOD_CLASSES,
            "optimistic_classes": WEAR_OPTIMISTIC_CLASSES,
            "source": "GLiM lithology classes; hint only, not a score",
        },
        "frozen_at": _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds") if freeze else None,
        "author": author,
        "unverified": issues,
        "rover_reference": {
            "name": rover.get("name"),
            "locomotion": rover.get("locomotion"),
            "mass_kg": round(mass, 2),
            "cg_m": [round(c, 3) for c in cg],
            "static_tipover": tip,
            "physics": physics,
        },
        "transfer_card": transfer_card(tip, physics, rover),
        "notes": [
            "Gates act on slope averaged over the baseline in the feature name; "
            "local slopes inside a cell are steeper. Prefer a p90 slope column "
            "for the gate when it exists.",
            "No slip, sinkage, traction or maximum climbable slope is predicted "
            "for the Moon or Mars.",
            "Tolerances and gates are only valid for the baseline in their names; "
            "5 km slopes are much gentler than 300 m slopes.",
            "thermal_inertia_class has no product at the lunar south pole: it is "
            "NaN there and its weight is redistributed. Lunar polar regolith is "
            "always fine and loose, so soil class only discriminates for Mars.",
            "Loose-soil analog sites are wanted, not avoided: getting stuck on "
            "Earth is cheap, on the Moon it ends the mission.",
            "Abrasive wear is not scored. Use wear_test_hint() on each named "
            "site: volcanic/pyroclastic sites are better for wear tests, loose "
            "sediments give optimistic wear results.",
            "Before the pitch, check the ranking with validate_rover_ranking(): "
            "Bardenas must make sense for rover (" + BASEPROD_REF + ").",
        ],
    }
    if config.get("workable_days"):
        preset["workable_days"] = config["workable_days"]
    return preset


def transfer_card(tip: dict, physics: dict, rover: dict | None = None) -> list[dict]:
    moon, mars = physics.get("moon", {}), physics.get("mars", {})
    clearance = value(rover, "ground_clearance_m") if rover else NAN
    return [
        {"level": "A", "item": "Static tip-over angle (min)",
         "value": tip["min_deg"], "unit": "deg",
         "note": "independent of gravity"},
        {"level": "A", "item": "Weight on tool, Moon / Mars / Earth",
         "value": [moon.get("weight_n"), mars.get("weight_n"), physics["earth"]["weight_n"]],
         "unit": "N", "note": "m * g; an Earth test pushes harder than on the target"},
        {"level": "A", "item": "Earth twin mass for equal ground load, Moon / Mars",
         "value": [moon.get("earth_twin_mass_kg"), mars.get("earth_twin_mass_kg")],
         "unit": "kg", "note": "m * g_target / g_earth"},
        {"level": "A", "item": "Earth test speed (Froude), Moon / Mars",
         "value": [moon.get("earth_test_speed_mps"), mars.get("earth_test_speed_mps")],
         "unit": "m/s", "note": "v_target * sqrt(g_earth / g_target)"},
        {"level": "A", "item": "Ground clearance",
         "value": None if math.isnan(clearance) else clearance, "unit": "m",
         "note": "rover property, independent of g. Rock density is not scored: "
                 "no rock data at the lunar south pole (Diviner stops at 60 S)"},
        {"level": "B", "item": "Energy per km", "value": None, "unit": None,
         "note": "range only, about +/-30 % (Apollo 15 LRV, Costes et al. 1972)"},
        {"level": "B", "item": "Slip", "value": None, "unit": None,
         "note": "granular scaling, cohesionless sand only; a lightened rover "
                 "at 1 g is optimistic (arXiv 2405.11001)"},
        {"level": "C", "item": "Traction and sinkage on target, thermal control, "
                               "dust adhesion, radiation on electronics",
         "value": None, "unit": None, "note": "declared limit, no prediction"},
        {"level": "C", "item": "Getting stuck or sinking in loose soil",
         "value": None, "unit": None,
         "note": "tested on Earth, never predicted. On the Moon the soil itself "
                 "weighs less and grips less, so Earth sand holds the rover "
                 "better even with a lightened twin: VIPER twin slipped 42 % at "
                 "30 deg on Earth vs 85 % simulated on the Moon (arXiv "
                 "2405.11001). Every Earth result is optimistic."},
        {"level": "C", "item": "Abrasive wear of wheels, seals and bearings",
         "value": None, "unit": None,
         "note": "tested on Earth, never predicted. Lunar regolith has angular, "
                 "glassy grains not rounded by wind or water; Apollo dust wore "
                 "suits, seals and mechanisms within days. Rounded Earth sand "
                 "underestimates wear; young volcanic or pyroclastic ground is "
                 "closer (see wear_test_hint)."},
    ]


# --------------------------------------------------------------------------
# Ranking sanity check (plan, section 5)
# --------------------------------------------------------------------------
def _norm(name: str) -> str:
    for a, b in (("í", "i"), ("á", "a"), ("é", "e"), ("ó", "o"), ("ú", "u"), ("-", " ")):
        name = name.replace(a, b)
    return name.lower().strip()


def validate_rover_ranking(scores: dict, positives=MOBILITY_POSITIVES,
                           mismatches=MOBILITY_MISMATCHES) -> dict:
    """Quick check of rover scores for named sites ({site name: score 0-100}).
    It reports and never changes weights (they are frozen). The formal
    validation (AUC with bootstrap, controls) is done by the engine."""
    by_name = {_norm(k): float(v) for k, v in scores.items()
               if v is not None and not (isinstance(v, float) and math.isnan(v))}

    def find(name):
        key = _norm(name)
        for k, v in by_name.items():
            if key in k:
                return v
        return None

    pos = {p: find(p) for p in positives}
    neg = {n: find(n) for n in mismatches}
    pos_vals = sorted(v for v in pos.values() if v is not None)
    median_pos = pos_vals[len(pos_vals) // 2] if pos_vals else None
    all_vals = sorted(by_name.values())

    def pct(v):
        if v is None or not all_vals:
            return None
        return round(100.0 * sum(1 for x in all_vals if x < v) / len(all_vals), 1)

    problems = []
    bard = pos.get("Bardenas")
    if bard is None:
        problems.append("Bardenas has no score")
    elif median_pos is not None and bard < median_pos:
        problems.append("Bardenas scores below the median of mobility analogs; "
                        "review before the pitch (BASEPROD site)")
    for n, v in neg.items():
        if v is not None and median_pos is not None and v >= median_pos:
            problems.append(f"{n} (operations or mineralogy analog) scores as high "
                            "as the mobility analogs")
    return {
        "positives": {k: (v, pct(v)) for k, v in pos.items()},
        "mismatches": {k: (v, pct(v)) for k, v in neg.items()},
        "median_positive": median_pos,
        "problems": problems,
        "ok": not problems,
        "reference": BASEPROD_REF,
    }


# --------------------------------------------------------------------------
# presets.json
# --------------------------------------------------------------------------
def _json_safe(obj):
    """NaN/inf become null so the file stays valid JSON for the web."""
    if isinstance(obj, float) and not math.isfinite(obj):
        return None
    if isinstance(obj, dict):
        return {k: _json_safe(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_json_safe(v) for v in obj]
    return obj


def merge_into_presets(path: Path, preset: dict, name: str = "rover",
                       refreeze: bool = False) -> dict:
    """Write the preset into presets.json, keeping the other presets.
    A frozen preset is only replaced with refreeze=True (declare it)."""
    data = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    old = data.get(name)
    if old and old.get("frozen_at") and not refreeze:
        raise PresetError(f"'{name}' was frozen at {old['frozen_at']}; "
                          "use --refreeze and declare it")
    if old and old.get("frozen_at") and refreeze:
        preset.setdefault("refrozen_from", old["frozen_at"])
    data[name] = _json_safe(preset)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False, allow_nan=False),
                    encoding="utf-8")
    return data


def _load(path: str) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


# --------------------------------------------------------------------------
# Built-in checks (python rover_preset.py --selftest)
# --------------------------------------------------------------------------
def selftest() -> int:
    import copy
    import tempfile

    G = DEFAULT_GRAVITY
    checks = []

    def check(name, cond):
        checks.append((name, bool(cond)))

    check("Earth twin for VIPER is ~73 kg (plan)",
          abs(earth_twin_mass_kg(440, G["moon"], G["earth"]) - 72.66) < 0.05)
    check("Froude factor Moon 2.46",
          abs(froude_test_speed(1.0, G["moon"], G["earth"]) - 2.46) < 0.01)
    check("Froude factor Mars 1.62",
          abs(froude_test_speed(1.0, G["mars"], G["earth"]) - 1.62) < 0.01)

    sq = [(0.65, 0.65), (-0.65, 0.65), (-0.65, -0.65), (0.65, -0.65)]
    tip = static_tipover(sq, (0.0, 0.0, 0.6))
    check("Tip-over of a square footprint",
          abs(tip["min_deg"] - math.degrees(math.atan(0.65 / 0.6))) < 0.01 and tip["stable"])
    check("CG outside footprint is unstable",
          static_tipover(sq, (0.9, 0.0, 0.5))["stable"] is False)

    a = build_rover_preset(ROVER_SPEC, PRESET_CONFIG, G, "t")
    b = build_rover_preset(ROVER_SPEC, PRESET_CONFIG, {"earth": 9.81, "moon": 1.0, "mars": 2.0}, "t")
    check("Tip-over independent of gravity",
          a["rover_reference"]["static_tipover"] == b["rover_reference"]["static_tipover"])

    budget = dict(ROVER_SPEC, mass_budget=[
        {"name": "a", "mass_kg": 100, "z_m": 0.2, "source": "x"},
        {"name": "b", "mass_kg": 100, "z_m": 1.0, "source": "x"}])
    m, cg = mass_properties(budget)
    check("Mass budget gives mass and CG", m == 200 and abs(cg[2] - 0.6) < 1e-9)

    try:
        build_rover_preset(ROVER_SPEC, PRESET_CONFIG, G, "t", freeze=True)
        check("Freeze blocked while sources are illustrative", False)
    except PresetError:
        check("Freeze blocked while sources are illustrative", True)

    cfg = copy.deepcopy(PRESET_CONFIG)
    cfg["gates_by_baseline"] = {"300m": {"slope_300m_deg": {"max": 80, "source": "x"}}}
    try:
        build_rover_preset(ROVER_SPEC, cfg, G, "t")
        check("Slope gate above tip-over rejected", False)
    except PresetError:
        check("Slope gate above tip-over rejected", True)

    p = build_rover_preset(ROVER_SPEC, PRESET_CONFIG, G, "t", freeze=True, allow_unverified=True)
    with tempfile.TemporaryDirectory() as d:
        path = Path(d) / "presets.json"
        path.write_text(json.dumps({"solar": {"weights": {}}}))
        merge_into_presets(path, p)
        kept = "solar" in json.loads(path.read_text())
        try:
            merge_into_presets(path, p)
            blocked = False
        except PresetError:
            blocked = True
            merge_into_presets(path, p, refreeze=True)
        refrozen = "refrozen_from" in json.loads(path.read_text())["rover"]
        json.loads(path.read_text())  # must be valid JSON (no NaN)
    check("Other presets kept in presets.json", kept)
    check("Frozen preset not overwritten without --refreeze", blocked and refrozen)

    # Version 2 checks
    cols5 = ["slope_5km_deg", "rough_5km_m", "thermal_inertia_class"]
    p5 = build_rover_preset(ROVER_SPEC, PRESET_CONFIG, G, "t", available_columns=cols5)
    check("5 km baseline chosen when 300 m columns are missing",
          p5["baseline"] == "5km" and "slope_5km_deg" in p5["tolerances"]
          and "slope_300m_deg" not in p5["tolerances"])
    cols3 = ["slope_300m_deg", "slope_300m_p90_deg", "rough_300m_m", "thermal_inertia_class"]
    p3 = build_rover_preset(ROVER_SPEC, PRESET_CONFIG, G, "t", available_columns=cols3)
    check("Slope gate uses p90 when available",
          "slope_300m_p90_deg" in p3["gates"] and "slope_300m_deg" not in p3["gates"])
    check("Without p90 the gate stays on the median and warns",
          "slope_5km_deg" in p5["gates"] and any("p90" in i for i in p5["unverified"]))
    check("Jezero TES 276 is sand", thermal_inertia_class(276) == "sand")
    check("TI classes at the edges",
          thermal_inertia_class(100) == "dust" and thermal_inertia_class(700) == "rock")
    mtx = class_similarity_matrix(TI_CLASSES)
    check("Class matrix: same 1, neighbour 0.5, far 0",
          mtx["sand"]["sand"] == 1.0 and mtx["sand"]["dust"] == 0.5
          and mtx["dust"]["rock"] == 0.0)
    check("Thermal inertia class in the rover tolerances",
          a["tolerances"]["thermal_inertia_class"]["type"] == "class")
    items = [r["item"] for r in a["transfer_card"]]
    check("Transfer card has soft-soil and ground-clearance rows",
          "Getting stuck or sinking in loose soil" in items and "Ground clearance" in items)
    check("Rock density excluded with a reason",
          a["excluded_features"][0]["feature"] == "rock_abundance")
    v1 = {"weights": PRESET_CONFIG["weights"],
          "tolerances": {"slope_300m_deg": {"scale": 5, "unit": "deg", "source": "x"}},
          "gates": {"slope_300m_deg": {"max": 10, "source": "x"}}}
    pv1 = build_rover_preset(ROVER_SPEC, v1, G, "t")
    check("Version 1 config format still works",
          "slope_300m_deg" in pv1["tolerances"] and pv1["gates"]["slope_300m_deg"]["max"] == 10)
    good = {"Bardenas": 80, "Tabernas": 75, "Yungay": 70, "MDRS": 72,
            "Río Tinto": 20, "El Soplao": 15, "Paris": 5}
    bad = dict(good, **{"Bardenas": 30, "Río Tinto": 90})
    r_good, r_bad = validate_rover_ranking(good), validate_rover_ranking(bad)
    check("Ranking check passes a sensible ranking", r_good["ok"])
    check("Ranking check flags Bardenas low and Rio Tinto high",
          not r_bad["ok"] and len(r_bad["problems"]) == 2)

    # Version 3 checks
    check("Transfer card has the abrasive-wear row",
          "Abrasive wear of wheels, seals and bearings" in items)
    check("Abrasivity excluded with a reason",
          any(e["feature"] == "abrasivity" for e in a["excluded_features"]))
    check("Wear hint: basic volcanic is a candidate",
          wear_test_hint("vb")["hint"] == "candidate_for_wear_tests")
    check("Wear hint: loose sediments are optimistic",
          wear_test_hint("su")["hint"] == "optimistic_for_wear")
    check("Wear hint: unknown class gives no data",
          wear_test_hint(None)["hint"] == "no_data" and wear_test_hint("mt")["hint"] == "no_data")
    check("Wear flags stored in the preset", "wear_test_flags" in a)

    for name, ok in checks:
        print(("ok    " if ok else "FAIL  ") + name)
    failed = sum(1 for _, ok in checks if not ok)
    print(f"{len(checks) - failed}/{len(checks)} checks passed")
    return 1 if failed else 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Build the `rover` preset.")
    ap.add_argument("--rover", help="rover spec JSON (default: ROVER_SPEC)")
    ap.add_argument("--config", help="preset config JSON (default: PRESET_CONFIG)")
    ap.add_argument("--selftest", action="store_true", help="run built-in checks")
    ap.add_argument("--presets", help="presets.json to update (omit to only print)")
    ap.add_argument("--gravity", help="JSON {'earth':..,'moon':..,'mars':..}")
    ap.add_argument("--author", default="Robotics 1")
    ap.add_argument("--freeze", action="store_true")
    ap.add_argument("--refreeze", action="store_true")
    ap.add_argument("--allow-unverified", action="store_true")
    ap.add_argument("--baseline", choices=BASELINES, help="force 300m or 5km")
    ap.add_argument("--columns", help="comma-separated earth_cells columns")
    ap.add_argument("--check-scores", help="JSON {site name: rover score} to sanity-check")
    args = ap.parse_args(argv)
    if args.selftest:
        return selftest()
    if args.check_scores:
        report = validate_rover_ranking(_load(args.check_scores))
        for k, (v, pc) in report["positives"].items():
            print(f"  analog   {k:14s} score {v}  percentile {pc}")
        for k, (v, pc) in report["mismatches"].items():
            print(f"  mismatch {k:14s} score {v}  percentile {pc}")
        for prob in report["problems"]:
            print("PROBLEM:", prob)
        print("OK" if report["ok"] else "REVIEW BEFORE THE PITCH")
        return 0 if report["ok"] else 1
    columns = [c.strip() for c in args.columns.split(",")] if args.columns else None

    gravity = dict(DEFAULT_GRAVITY)
    if args.gravity:
        gravity.update(_load(args.gravity))

    try:
        rover = _load(args.rover) if args.rover else ROVER_SPEC
        config = _load(args.config) if args.config else PRESET_CONFIG
        preset = build_rover_preset(rover, config, gravity,
                                    args.author, args.freeze, args.allow_unverified,
                                    available_columns=columns, baseline=args.baseline)
        if args.presets:
            merge_into_presets(Path(args.presets), preset, refreeze=args.refreeze)
    except PresetError as e:
        print(f"ERROR: {e}")
        return 1

    ref = preset["rover_reference"]
    print(f"Rover: {ref['name']}  mass {ref['mass_kg']} kg  CG {ref['cg_m']} m")
    print(f"Relief baseline: {preset['baseline']}")
    print(f"Min static tip-over: {ref['static_tipover']['min_deg']} deg")
    for row in preset["transfer_card"]:
        if row["level"] == "A":
            shown = "no data" if row["value"] is None else f"{row['value']} {row['unit'] or ''}"
            print(f"  [A] {row['item']}: {shown}")
        else:
            print(f"  [{row['level']}] {row['item']}")
    if preset["unverified"]:
        print("Unverified items:")
        for i in preset["unverified"]:
            print(f"  - {i}")
    print("Frozen at:", preset["frozen_at"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
