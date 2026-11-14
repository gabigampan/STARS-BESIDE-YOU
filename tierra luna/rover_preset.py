# AI-assisted (Claude, Anthropic). Declared in docs/AI_USE.md.
"""
rover_preset.py

Physics checks and `rover` preset builder for the analog finder.

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
  python rover_preset.py --presets data/presets/presets.json \
      --author "Robotics 1" --freeze           # write the frozen preset
  Options: --rover <json> --config <json> --gravity <json>
           --allow-unverified --refreeze

In code:
  import rover_preset as rp
  preset = rp.build_rover_preset(rp.ROVER_SPEC, rp.PRESET_CONFIG,
                                 rp.DEFAULT_GRAVITY, author="Robotics 1")
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
    "max_speed_mps":          {"value": 0.20, "unit": "m/s", "source": "ESTIMADO (~0.8 km/h) - replace from project DB", "status": "VERIFICAR"},
    "max_operational_slope_deg": {"value": 15, "unit": "deg", "source": "ESTIMADO - replace from project DB", "status": "VERIFICAR"},
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
    "tolerances": {
        "slope_300m_deg": {"scale": 5.0,  "unit": "deg", "source": "ILUSTRATIVO - set by Robotics 1"},
        "rough_300m_m":   {"scale": 10.0, "unit": "m",   "source": "ILUSTRATIVO - set by Robotics 1"},
    },
    "gates": {
        "slope_300m_deg": {"min": None, "max_from": "max_operational_slope_deg"},
        "rough_300m_m":   {"min": None, "max": None, "source": "no gate until Robotics 1 sets one"},
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
# Preset builder
# --------------------------------------------------------------------------
class PresetError(ValueError):
    pass


def _resolve_gates(config: dict, rover: dict, tip_min: float, issues: list) -> dict:
    gates = {}
    for feature, g in (config.get("gates") or {}).items():
        gate = {"min": g.get("min"), "max": g.get("max"), "source": g.get("source", "")}
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
        gates[feature] = gate
    return gates


def build_rover_preset(rover: dict, config: dict, gravity: dict, author: str,
                       freeze: bool = False, allow_unverified: bool = False) -> dict:
    issues: list[str] = []

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

    # Tolerances {feature: {scale, unit, source}}.
    tolerances = {}
    for feat, t in (config.get("tolerances") or {}).items():
        if float(t["scale"]) <= 0:
            raise PresetError(f"tolerance {feat}: scale must be > 0")
        tolerances[feat] = {"scale": float(t["scale"]), "unit": t.get("unit"),
                            "source": t.get("source", "")}
        if is_unverified({"source": t.get("source", "")}):
            issues.append(f"tolerance {feat}: source missing or illustrative")

    gates = _resolve_gates(config, rover, tip["min_deg"], issues)

    if freeze and issues and not allow_unverified:
        raise PresetError("cannot freeze, unresolved items:\n  - " + "\n  - ".join(issues))

    physics = transfer_physics(rover, gravity)
    preset = {
        "weights": weights,
        "weight_sources": weight_sources,
        "tolerances": tolerances,
        "gates": gates,
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
        "transfer_card": transfer_card(tip, physics),
        "notes": [
            "Gates act on slope averaged over the baseline in the feature name; "
            "local slopes inside a cell are steeper. Prefer a p90 slope column "
            "for the gate when it exists.",
            "No slip, sinkage, traction or maximum climbable slope is predicted "
            "for the Moon or Mars.",
        ],
    }
    if config.get("workable_days"):
        preset["workable_days"] = config["workable_days"]
    return preset


def transfer_card(tip: dict, physics: dict) -> list[dict]:
    moon, mars = physics.get("moon", {}), physics.get("mars", {})
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
        {"level": "B", "item": "Energy per km", "value": None, "unit": None,
         "note": "range only, about +/-30 % (Apollo 15 LRV, Costes et al. 1972)"},
        {"level": "B", "item": "Slip", "value": None, "unit": None,
         "note": "granular scaling, cohesionless sand only; a lightened rover "
                 "at 1 g is optimistic (arXiv 2405.11001)"},
        {"level": "C", "item": "Traction and sinkage on target, thermal control, "
                               "dust adhesion, radiation on electronics",
         "value": None, "unit": None, "note": "declared limit, no prediction"},
    ]


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
    cfg["gates"] = {"slope_300m_deg": {"max": 80, "source": "x"}}
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
    args = ap.parse_args(argv)
    if args.selftest:
        return selftest()

    gravity = dict(DEFAULT_GRAVITY)
    if args.gravity:
        gravity.update(_load(args.gravity))

    try:
        rover = _load(args.rover) if args.rover else ROVER_SPEC
        config = _load(args.config) if args.config else PRESET_CONFIG
        preset = build_rover_preset(rover, config, gravity,
                                    args.author, args.freeze, args.allow_unverified)
        if args.presets:
            merge_into_presets(Path(args.presets), preset, refreeze=args.refreeze)
    except PresetError as e:
        print(f"ERROR: {e}")
        return 1

    ref = preset["rover_reference"]
    print(f"Rover: {ref['name']}  mass {ref['mass_kg']} kg  CG {ref['cg_m']} m")
    print(f"Min static tip-over: {ref['static_tipover']['min_deg']} deg")
    for row in preset["transfer_card"]:
        if row["level"] == "A":
            print(f"  [A] {row['item']}: {row['value']} {row['unit'] or ''}")
    if preset["unverified"]:
        print("Unverified items:")
        for i in preset["unverified"]:
            print(f"  - {i}")
    print("Frozen at:", preset["frozen_at"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
