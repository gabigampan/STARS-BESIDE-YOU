"""Point A (reviewer 5): the complete inventory of every number of the model.

Two parts, both written to out/inventory.csv:
  1. ANNOTATED rows: every number that can act on a result or is shown to the user, with its value
     and unit, its origin class (measured / computation / literature / design), the origin as
     recorded in the repository, where it is read in the code (file:line, found by searching the
     code for the key), the measured effect of removing or perturbing it (from
     out/p5_sensitivity_<mission>.csv, written by p5_sensitivity.py) and a flag with a proposal.
  2. AUTO rows: every other numeric leaf of mission_scoring.json, engine/engine_config.json and
     engine/datasets.json (real_1deg) not covered by part 1, with its path, the code lines that read
     its key, and the rule that classes it (dead configuration, display, numerical, other mission).
Nothing is computed here that the other p5 scripts do not compute; this script only joins.
Run (after p5_sensitivity.py and p5_shown_numbers.py):
  <python> "tierra luna/audit/p5_inventory.py"
"""
from __future__ import annotations

import csv
import glob
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from p5_common import OUT, REPO, TL  # noqa: E402

CODE_DIRS = [os.path.join(TL, "engine"), os.path.join(TL, "real_data")]
CODE_FILES = sorted(glob.glob(os.path.join(TL, "engine", "*.py"))) + [os.path.join(TL, "mission_scoring.py")] + \
    sorted(glob.glob(os.path.join(TL, "real_data", "*.py"))) + sorted(glob.glob(os.path.join(TL, "tests", "*.py")))
_SRC = {f: open(f, encoding="utf-8").read().splitlines() for f in CODE_FILES}


def uses(*keys, limit=4):
    """file:line of code lines that read one of the keys (quoted key, or bare identifier)."""
    hits = []
    for f, lines in _SRC.items():
        for i, ln in enumerate(lines):
            s = ln.strip()
            if s.startswith("#") or s.startswith('"""'):
                continue
            for k in keys:
                if (f'"{k}"' in ln or f"'{k}'" in ln or re.search(rf"\b{re.escape(k)}\b\s*[=\[(,)]", ln)) and "why" not in ln[:12]:
                    hits.append(f"{os.path.relpath(f, REPO)}:{i + 1}")
                    break
            if len(hits) >= limit:
                return "; ".join(hits)
    return "; ".join(hits) if hits else "NOT READ BY ANY CODE (searched engine/, mission_scoring.py, real_data/, tests/)"


def load_sens():
    S = {}
    for f in glob.glob(os.path.join(OUT, "p5_sensitivity_*.csv")):
        for r in csv.DictReader(open(f, encoding="utf-8")):
            S[(r["mission"], r["id"])] = r
    return S


SENS = load_sens()


def eff(mission, *ids):
    out = []
    for i in ids:
        r = SENS.get((mission, i))
        if r is None:
            out.append(f"{mission}:{i}: not run")
            continue
        out.append(f"{mission}:{i}: in+{r['entered']}/out-{r['left']}, pairs +{r['pairs_gained']}/-{r['pairs_lost']}, "
                   f"twin changed {r['twin_changed']}, top5 kept {r['top5_kept']}/5{' same order' if r['top5_same_order'] == 'True' else ''}, "
                   f"top50 kept {r['top50_kept']}/50")
    return " | ".join(out)


def effp(mission, prefix):
    ids = sorted(i for (m, i) in SENS if m == mission and i.startswith(prefix))
    return eff(mission, *ids) if ids else f"{mission}:{prefix}*: not run"


MS = "tierra luna/mission_scoring.json"
EC = "tierra luna/engine/engine_config.json"
DS = "tierra luna/engine/datasets.json"
RV = "real_value_similarity.value.missions"
ROWS = []


def row(rid, value, unit, category, origin_class, origin, file_path, used, effect, flag="", proposal="", changes_design=""):
    ROWS.append({"id": rid, "value": value, "unit": unit, "category": category, "origin_class": origin_class,
                 "origin": origin, "defined_in": file_path, "used_at": used, "effect_measured": effect,
                 "flag": flag, "proposal": proposal, "correction_changes_design": changes_design})


def annotated():
    ms = json.load(open(os.path.join(TL, "mission_scoring.json"), encoding="utf-8"))
    ec = json.load(open(os.path.join(TL, "engine", "engine_config.json"), encoding="utf-8"))
    R3 = "docs/sources/R3_threshold_sources.md line 17: 'pure design choices: no source can confirm or refute them'"
    # ---------------- common gates
    row("common_gate.elevation_m.min", 1.0, "m", "common gate (Earth only)", "design",
        "mission_scoring.json common_gates.elevation_m.why: 'solo tierra firme (descarta oceano, que el modelo fija en -250 m)'; "
        "Earth only by engine_config gate_body_applicability", f"{MS} common_gates.elevation_m.min",
        uses("elevation_m") + "; mission_scoring.py:52-59",
        " | ".join(effp(m, "common_gate.elevation_m") for m in ("rover", "solar", "lunar_base")),
        "STATED REASON DOES NOT APPLY to the real table: there the ocean is empty (NaN), not -250 m; the gate removes real land below 1 m "
        "(depressions) that mask_fraction already accepts as land",
        "design question: keep (with the reason rewritten) or drop; the effect of dropping is the 'drop' line", "yes")
    row("common_gate.mask_fraction.min", 0.3, "fraction of land in the cell", "common gate", "design", R3,
        f"{MS} common_gates.mask_fraction.min", uses("mask_fraction") + "; mission_scoring.py:52-59",
        " | ".join(effp(m, "common_gate.mask_fraction") for m in ("rover", "solar", "lunar_base")),
        "no source (design); on the Moon mask_fraction = 1 everywhere so it removes no lunar cell; removes no lunar_base Earth point",
        "justify as the team's land-share threshold (design) or drop; dropping is a design change", "yes")
    # ---------------- per-mission funnel
    src_gate = {
        ("rover", "slope_300m_deg", "max"): ("literature", "NASA VIPER requirement 'Slopes up to 15 deg (reqt)', NTRS 20240013903 p.4 (docs/sources/R1 line 42; rover_preset.py line 168); rover-scale capability applied to a 3.7 km DEM slope (R1 line 87, column_aliases caveat)", "baseline mismatch: a 15 deg slope over 3.7 km is far steeper terrain than 15 deg at wheel scale"),
        ("rover", "slope_300m_deg", "min"): ("design", "none recorded; R3 line 75: 'Removes flat terrain, which is unusual for a rover gate; ask why'", "NO DEFENSIBLE ORIGIN"),
        ("rover", "rough_300m_m", "min"): ("design", "gate source text 'LRO LOLA & CNSA Yutu/VIPER topographic hazard envelope (5-650 m)', but R3 line 74: 'None found ... Design choice'; rover_preset.py line 215 'no gate until Robotics 1 sets one'", "NO DEFENSIBLE ORIGIN (the cited envelope is not found in docs/sources)"),
        ("rover", "rough_300m_m", "max"): ("design", "as the minimum (R3 line 74)", "NO DEFENSIBLE ORIGIN"),
        ("solar", "irradiance_kwh_m2_day", "min"): ("design", "mission_scoring.json: 'diseno: por debajo, la generacion no compensa'; R3 line 63: unit inferred, value a design choice", "design value, not validated (mission_scoring note)"),
        ("solar", "slope_deg", "max"): ("design", "'diseno: terreno practicamente plano'; R3 line 65: contradicted as an Earth siting value (federal 5 % = 2.9 deg)", "design value contradicted for Earth siting (R3)"),
        ("solar", "sun_elev_max_deg", "min"): ("design", "'diseno: sol siempre rasante = sombras permanentes'", "design value"),
        ("solar", "sun_low_frac_0_5deg", "max"): ("design", "'diseno: demasiado tiempo con sol a <5 grados'; " + R3, "design value"),
        ("lunar_base", "lst_diurnal_amp_k", "min"): ("design", "'diseno: sin ciclo termico fuerte no hay ensayo util'; R3 line 70: design choice", "design value"),
        ("lunar_base", "tmin_c", "max"): ("design", "'diseno: hace falta frio real para estresar el equipo'; " + R3, "design value"),
    }
    for m in ("rover", "solar", "lunar_base"):
        b = ms["missions"][m]
        for v in b["require_present"]:
            row(f"{m}.require_present.{v}", "present", "-", "required variable", "design",
                "mission_scoring.json require_present (team block)", f"{MS} missions.{m}.require_present",
                "mission_scoring.py:81-90; engine/gates.py:100", effp(m, f"require_present.{v}"),
                "", "")
        for g, spec in b["gates"].items():
            for k in ("min", "max"):
                if spec.get(k) is None:
                    continue
                oc, org, fl = src_gate.get((m, g, k), ("design", spec.get("source", ""), "design value"))
                row(f"{m}.gate.{g}.{k}", spec[k], unit_of(g), "hard filter", oc, org, f"{MS} missions.{m}.gates.{g}.{k}",
                    "mission_scoring.py:52-59; engine/gates.py:63-72", eff(m, f"gate.{g}.{k}.drop", f"gate.{g}.{k}x0.9", f"gate.{g}.{k}x1.1"),
                    fl, "design question if the flag is an origin problem: give the source or record the decision; do not change the value", "yes")
            if spec.get("exclude"):
                row(f"{m}.gate.{g}.exclude", "|".join(spec["exclude"]), "category", "hard filter", "design", spec.get("source", ""),
                    f"{MS} missions.{m}.gates.{g}.exclude", "mission_scoring.py:67-68; engine/gates.py:75-80", eff(m, f"gate.{g}.drop"),
                    "", "")
        for v, s in b["soft"].items():
            row(f"{m}.soft.{v}.weight", s["weight"], "share of suitability (sum " + f"{sum(x['weight'] for x in b['soft'].values()):g})", "suitability weight", "design",
                (b.get("provisional", "") + " " if m == "rover" else "") + f"why: '{s.get('why', '')}'; " + (R3 if m != "rover" else "rover block 'provisional' (Robotics 1)"),
                f"{MS} missions.{m}.soft.{v}.weight", "mission_scoring.py:119-135; engine/suitability.py:79-110",
                eff(m, f"soft.{v}.weight0", f"soft.{v}.weight x0.9", f"soft.{v}.weight x1.1"),
                "provisional / not validated (mission_scoring note)", "")
            if "map" in s:
                for cat, u in s["map"].items():
                    row(f"{m}.soft.{v}.map.{cat}", u, "utility 0-1", "utility class table", "design",
                        f"why: '{s.get('why', '')}'", f"{MS} missions.{m}.soft.{v}.map.{cat}", "mission_scoring.py:103-108",
                        eff(m, f"soft.{v}.map.{cat}-0.1"), "", "")
                row(f"{m}.soft.{v}.default", s.get("default"), "utility 0-1", "utility default", "design", "mission_scoring.json default",
                    f"{MS} missions.{m}.soft.{v}.default", "mission_scoring.py:108", eff(m, f"soft.{v}.default0.4"),
                    "check: a class absent from the map gets it", "")
            else:
                for k in ("bad", "good"):
                    row(f"{m}.soft.{v}.{k}", s[k], unit_of(v), f"utility '{k}' end", "design", f"why: '{s.get('why', '')}'",
                        f"{MS} missions.{m}.soft.{v}.{k}", "mission_scoring.py:111-114",
                        eff(m, f"soft.{v}.{k}x0.9", f"soft.{v}.{k}x1.1"), "provisional / not validated", "")
        sim = ec["real_value_similarity"]["value"]["missions"][m]
        for q, x in enumerate(sim["variables"]):
            v = x["variable"]
            oc = "literature (illustrative)" if "illustrative" in x["tolerance_set_by"] else "design"
            row(f"{m}.sim.{v}.weight", x["weight"], "share of similarity", f"similarity weight ({x['role']})", "design",
                sim.get("weights_why", ""), f"{EC} {RV}.{m}.variables[{q}].weight",
                "engine/real_similarity.py:206-219; engine/pairing.py:80",
                eff(m, f"sim.{v}.weight0", f"sim.{v}.removed", f"sim.{v}.weight x0.9", f"sim.{v}.weight x1.1"), "", "", "yes")
            row(f"{m}.sim.{v}.tolerance", x["tolerance"], x["unit"], f"tolerance ({x['role']}); filter bound = {x['tolerance'] * (1 if x['role'] == 'key' else 2):g}",
                oc, x["tolerance_set_by"], f"{EC} {RV}.{m}.variables[{q}].tolerance", "engine/real_similarity.py:206-219, 327",
                eff(m, f"sim.{v}.tolerance x0.9", f"sim.{v}.tolerance x1.1"),
                "ILLUSTRATIVE (rover_preset.py 'ILUSTRATIVO - set by Robotics 1')" if "illustrative" in x["tolerance_set_by"] else "",
                "justify with Robotics 1 or keep labelled illustrative (it is: DECISIONS.md line 46)" if "illustrative" in x["tolerance_set_by"] else "", "yes")
        z = sim["zone"]
        if z["kind"] == "lat_max":
            row(f"{m}.zone.lat_max", z["lat_max"], "deg latitude", "lunar zone", "design", z["source"] + "; " + z.get("why", "") +
                "; DECISIONS.md line 26 (justified by NASA plans, not by the data)", f"{EC} {RV}.{m}.zone.lat_max",
                uses("lat_max"), effp(m, "zone."), "", "", "yes")
        elif z["kind"] == "abs_lat_max_elevation_max":
            row(f"{m}.zone.abs_lat_max", z["abs_lat_max"], "deg |latitude|", "lunar zone", "design", z["source"] + "; DECISIONS.md lines 27-28",
                f"{EC} {RV}.{m}.zone.abs_lat_max", uses("abs_lat_max"), effp(m, "zone.abs_lat_max"), "", "", "yes")
            row(f"{m}.zone.elevation_max_m", z["elevation_max_m"], "m above 1737.4 km sphere", "lunar zone", "design", z["source"],
                f"{EC} {RV}.{m}.zone.elevation_max_m", uses("elevation_max_m"), effp(m, "zone.elevation_max_m"), "", "", "yes")
        else:
            row(f"{m}.zone.footprint", 280, "lunar 1-degree cells", "lunar zone", "measured + computation",
                "USGS navigational grids (McClernan 2024, DOI 10.5066/P1MEQ6UK) of NASA's nine regions; cells whose square intersects a region "
                "(engine/data/artemis_iii_regions.geojson); DECISIONS.md line 25", f"{EC} similarity_zones.lunar_base",
                "engine/artemis.py; engine/lunar_regions.py", effp(m, "zone."), "upper bound of the regions (union of 1 km squares, square-intersects rule)", "", "yes")
            row(f"{m}.population.EARTH", 2419, "Earth points", "percentile population", "computation", "points passing the Lunar base funnel (DECISIONS.md line 25)",
                f"{EC} {RV}.{m}.populations.EARTH", "engine/real_similarity.py:65", "changes with every funnel threshold: see lunar_base.gate.* rows", "", "")
            row(f"{m}.population.MOON", 280, "lunar cells", "percentile population", "computation", "the zone's cells with a value",
                f"{EC} {RV}.{m}.populations.MOON", "engine/real_similarity.py:65", effp(m, "zone."), "", "")
            row(f"{m}.percentile.midrank", "100*(rank-0.5)/n, ties averaged", "percentile points", "percentile rule", "design",
                sim["percentile"]["why"], f"{EC} {RV}.{m}.percentile.formula", "engine/real_similarity.py:65-88",
                effp(m, "percentile_rule"), "", "")
    rv = ec["real_value_similarity"]["value"]
    for role, val in rv["filter_bound_multiplier"].items():
        eff_all = " | ".join(effp(m, f"mult.{role}") for m in ("rover", "solar", "lunar_base"))
        row(f"filter_bound_multiplier.{role}", val, "x tolerance", "pair filter", "design",
            "team decision 2026-11-15 morning (DECISIONS.md line 45); Lunar base 08:55 (line 25)", f"{EC} real_value_similarity.value.filter_bound_multiplier.{role}",
            "engine/real_similarity.py:219; engine/export_v2.py:292,300", eff_all, "", "", "yes")
    row("mix_factor(alpha)", ec["mix_factor"]["value"], "-", "final score", "design",
        "mission_scoring.combine_with_similarity default (mission_scoring.py:207); ASSUMPTIONS.md 0.2 'pending team confirmation'; DECISIONS.md line 45",
        f"{EC} mix_factor", "engine/pipeline.py:160-164", " | ".join(effp(m, "alpha=") for m in ("rover", "solar", "lunar_base")), "", "", "yes")
    # ---------------- constants and derived values
    toa = ec["toa_insolation"]["value"]
    srcs = {"solar_constant_w_m2": "literature: NSSDC Moon fact sheet 'Solar irradiance (W/m2) 1361.0' (real_data/provenance_moon.csv irradiance row; build_moon.py:57)",
            "obliquity_deg": "literature: NSSDC Earth fact sheet (DECISIONS.md line 48); NOTE the Earth builder uses 84381.406/3600 = 23.4393 deg (IAU 2006, build_earth.py:50) for the same quantity",
            "eccentricity": "literature: NSSDC Earth fact sheet (DECISIONS.md line 48)",
            "sun_longitude_at_perihelion_deg": "literature + computation: Earth longitude of perihelion 102.9 + 180 (ASSUMPTIONS.md line 152); only shifts the seasons",
            "hours_per_day": "conversion factor W -> kWh/day (24 h)",
            "mean_anomaly_samples": "numerical: time steps of the annual mean", "kepler_iterations": "numerical: fixed-point iterations of Kepler's equation"}
    for k, v in toa.items():
        if k == "reference_values_kwh_m2_day":
            row("toa_insolation.reference_values", json.dumps(v), "kWh/m2/day at 0/30/45/60 deg", "test reference", "computation",
                "the checker's figures (docs/ANALOG_PRINCIPLE.md 'Comprobacion' 1); my own integration over the true anomaly gives 9.9739/8.7651/7.3667/5.6717",
                f"{EC} toa_insolation.reference_values_kwh_m2_day", "engine/export_v2.py:819 (exported); tests/test_real_value_similarity.py",
                "none on any result (check value only)", "", "")
            continue
        e = eff("solar", f"toa.{k}x1.01") if k in ("solar_constant_w_m2", "obliquity_deg", "eccentricity", "sun_longitude_at_perihelion_deg", "hours_per_day") else \
            "numerical parameter: my independent integration (true-anomaly route, 20,000 steps) agrees to <5e-4 kWh/m2/day at 0/30/45/60 deg, so the result does not depend on it"
        row(f"toa_insolation.{k}", v, "", "constant (solar key variable, Earth side)", srcs[k].split(":")[0], srcs[k],
            f"{EC} toa_insolation.{k}", "engine/real_similarity.py:90-118", e,
            "inconsistent with build_earth.py (23.4393)" if k == "obliquity_deg" else "", "use one obliquity value in both places (effect below 1e-3 kWh/m2/day)" if k == "obliquity_deg" else "")
    row("moon.irradiance_kwh_m2_day (S0, 24 h, flat horizon)", "1361 W/m2 x mean max(0,sin h) x 24/1000", "kWh/m2/day", "derived lunar column (solar key, Moon side)",
        "computation", "build_moon.py:476-507 (Sun geometry, circular orbit, obliquity 1.54 deg PIA13720, 720 x 2880 grid); provenance_moon.csv",
        "tierra luna/output_real/moon_real_1deg.csv irradiance_kwh_m2_day", "build_moon.py:625", eff("solar", "moon_irradiance x1.01", "S0 both bodies x1.01"),
        "Moon uses a circular orbit, Earth an eccentric one (difference below 0.02 %)", "")
    for b, mu in (("EARTH", 695.9244), ("MOON", -248.3894)):
        row(f"body_mean_elevation.{b}", round(mu, 1), "m", "constant (rover secondary variable)", "computation",
            "cos(latitude)-weighted mean of elevation_m over the body's cells with data (DECISIONS.md line 47); recomputed by p5_baseline.py: "
            f"{mu:.4f}", f"{EC} real_value_similarity.variables.elevation_rel_m", "engine/real_similarity.py:123-130",
            eff("rover", f"body_mean.{b}x1.01", "body_mean.unweighted"), "", "")
    row("celsius_to_kelvin.offset_k", 273.15, "K", "conversion factor", "literature (definition of the kelvin)", "engine_config real_value_similarity.variables.tmin_k",
        f"{EC} real_value_similarity.value.variables.tmin_k.sources.*.offset_k", "engine/real_similarity.py:161", eff("lunar_base", "kelvin_offset x1.01"),
        "NO EFFECT ON ANY RESULT by construction (same offset on both sides; percentiles are invariant); needed for the K shown in the pair table", "keep (display unit)")
    row("lunar_day_earth_days", ec["lunar_day_earth_days"]["value"], "Earth days", "constant shown in text", "literature", "NSSDC Moon fact sheet synodic period 29.53 (build_moon.py:59)",
        f"{EC} lunar_day_earth_days", "engine/export_v2.py:794 ({lunar_day} in texts.solar_limitation, shown as 29.5)", "none on any result (text only)", "", "")
    row("body_radius_km", json.dumps(ec["body_radius_km"]["value"]), "km", "constant (distances shown)", "literature", "IUGG/NSSDC mean radii",
        f"{EC} body_radius_km", uses("body_radius_km"), "none on pairing or ranking (only the km distances to named places/features shown)",
        "the Earth builder uses 6371.0088 (build_earth.py:48) for the relief metrics: two values of one constant, effect <0.0002 %", "")
    # ---------------- rounding
    dec = ec["export_decimals"]["value"]
    row("export_decimals.utility", dec["utility"], "decimals", "rounding (Python round, binary float)", "design", "engine_config export_decimals; engine/suitability.py:9-16",
        f"{EC} export_decimals.utility", "engine/suitability.py:77-79", " | ".join(effp(m, "utility_decimals") for m in ("rover", "solar", "lunar_base")), "", "")
    row("real_value_similarity.score_decimals", rv["score_decimals"], "decimals", "rounding of per-variable scores", "design", "engine_config",
        f"{EC} real_value_similarity.value.score_decimals", "engine/real_similarity.py:223,327", " | ".join(effp(m, "score_decimals") for m in ("rover", "solar", "lunar_base")),
        "6-decimal scores saturate: a difference below 0.001 x tolerance scores 1.000000 (exp(-0.5 x 0.001^2) = 0.9999995 rounds up)", "")
    row("export_decimals.score (final, rank key)", dec["score"], "decimals", "rounding of the final; the rank sorts the 2-decimal final, ties by lowest id", "design",
        "engine/pipeline.py:4-7", f"{EC} export_decimals.score", "engine/pipeline.py:164", " | ".join(effp(m, "final_decimals") for m in ("rover", "solar", "lunar_base")),
        "rank ties at 2 decimals are broken by the Earth id, not by the unrounded score", "")
    row("display rounding", "half up (half away from zero) on the shortest float32 decimal", "-", "rounding of displayed values", "design",
        "engine/display.py:1-30 (contract revision 6)", "tierra luna/engine/display.py", "engine/display.py:56-64; app/src (same rule)",
        "display only; the rank key uses Python round on binary floats (half-even on exact ties): the two rules can differ only on an exact half", "")
    # ---------------- confidence
    conf = ec["confidence"]["value"]
    for k in ("level_scores", "high_min", "medium_min", "high_max_cell_km"):
        row(f"confidence.{k}", json.dumps(conf[k]), "-", "confidence label shown per pair", "design", "engine_config confidence (no source recorded)",
            f"{EC} confidence.{k}", "engine/confidence.py:24-58",
            "no effect on pairs or ranking; bundle: rover 10,192 'medium', solar 6,360 'medium', lunar_base 450 'low' (missions.json confidence_counts): ONE label per mission",
            "NO DEFENSIBLE ORIGIN for the level scores; 'high' is unreachable on 1-degree cells (high_max_cell_km 1.0 < 30-111 km); the per-pair label carries no per-pair information",
            "show it once per mission (it is a property of the data levels, not of the pair) or record the origin of the numbers")


def unit_of(v):
    return {"slope_300m_deg": "deg", "slope_deg": "deg", "rough_300m_m": "m", "roughness_m": "m", "irradiance_kwh_m2_day": "kWh/m2/day",
            "sun_elev_max_deg": "deg", "sun_low_frac_0_5deg": "fraction of daylight", "lst_diurnal_amp_k": "K", "tmin_c": "degC",
            "rock_or_bare_frac": "fraction", "temp_k": "K"}.get(v, "")


# ---------------- automatic part
AUTO_RULES = [
    (r"^ms\.missions\.(thermal|ice)\.", "component block, not an offered mission: thermal is copied into lunar_base (engine/config.py check_components refuses drift); ice is evaluated per Earth point and shown as information only, never changes the ranking (ASSUMPTIONS.md 0.1)", "no effect on pairs or ranking", "keep as component (documented) or move out of the shipped config"),
    (r"^ms\.missions\.\w+\.weights\.", "domain weights relieve/material/termico/luz/agua: engine_config not_used_by_engine_why says the engine does not read them (engine/config.py check_components only compares lunar_base with thermal); the mission_scoring note says the web's 'Use Weights' button uses them, but app/src has no reference to them (grep relieve|luz: 0 hits)", "NOT READ BY THE ENGINE NOR BY THE WEB", "DEAD CONFIGURATION: remove from the shipped config (or move to a documented 'not used' block) and correct the note in mission_scoring.json"),
    (r"^ms\.missions\.rover\.tolerances\.", "old 300 m rover tolerances (5 deg, 10 m): not_used_by_engine_why; the shipped tolerances are engine_config real_value_similarity", "NOT READ BY THE ENGINE", "DEAD CONFIGURATION: remove, or mark 'superseded by real_value_similarity'"),
    (r"^ms\.missions\.rover\.workable_days\.", "Phase-1 workable-days defaults: not_used_by_engine_why ('not read by mission_scoring.py')", "NOT READ BY THE ENGINE", "DEAD CONFIGURATION: remove"),
    (r"^ec\.repo_similarity\.", "parameters of the repo_global_mean / zone_twin rules (z-score, decay 0.45): no shipped mission uses them since 2026-11-15 08:55", "no effect on the shipped bundle", "keep only as the --similarity-rule alternative (documented) or remove"),
    (r"^ec\.similarity_scale\.", "pooled 5-95 percentile scale of the physical_pooled rule: not the shipped rule", "no effect on the shipped bundle", "alternative rule only"),
    (r"^ec\.real_value_similarity\.value\.reference_tolerances_not_used\.", "temperature 10 K, amplitude 5 K: 'Reference values only; no mission uses them' (DECISIONS.md line 56)", "no effect", "DEAD CONFIGURATION: remove or keep under its own 'not used' label (it has one)"),
    (r"^ec\.similarity_zones\.(rover|solar)\.", "zone_twin-era zone of rover/solar; the shipped rule reads real_value_similarity zones (same -75 for rover)", "no effect on the shipped bundle (solar reads the maria zone)", "solar entry is stale (-75 here, maria in real_value_similarity): mark or remove"),
    (r"^ec\.similarity_zones\.lunar_base\.fallback", "fallback zone if the regions file is missing", "used only without the regions file; measured as zone.fallback_lat_max-75", ""),
    (r"^ec\.(export_decimals|binary_encoding)\.", "published precision of each exported value", "display/storage precision; the rank key is the 2-decimal final (see annotated rows)", ""),
    (r"^ec\.(pairing_chunk_rows|detail_tile_rows|first_view_budget_bytes)", "performance / file-size setting", "no effect on any value (chunking is exact)", ""),
    (r"^ec\.(explain_top_n|top_failure_reasons_n|explain_helps_n|explain_hurts_n)", "how many items the explain files list", "no effect on pairs or ranking (display only)", ""),
    (r"^ec\.coordinate_tolerance_deg", "schema check of grid coordinates", "check only", ""),
    (r"^ec\.antarctic_label_lat_max", "place label rule (Antarctica south of -60)", "label only", ""),
    (r"^ec\.lunar_regions\.", "region codes A-F of mission_zones.json (|lon| > 90 = far side)", "labels and zone-contrast texts only", ""),
    (r"^ec\.engine_version", "version string", "none", ""),
    (r"^ec\.approved_texts\..*\.(decimals|subtract)$", "display decimals / offset of a placeholder of an approved web text (shown value)", "display only; the filled texts are checked by the engine tests and explain.json", ""),
    (r"^ec\.approved_texts\..*\.decision$", "number of the team decision that approved the text", "label only", ""),
    (r"^ec\.toa_insolation\.", "see annotated rows", "", ""),
    (r"^ec\.real_value_similarity\.", "see annotated rows", "", ""),
    (r"^ec\.confidence\.", "see annotated rows", "", ""),
    (r"^ec\.(mix_factor|lunar_day_earth_days|body_radius_km)", "see annotated rows", "", ""),
    (r"^ds\..*region_max_place_km", "farthest distance at which a populated place names an Earth cell (111.2 km = one degree)", "place names only", ""),
    (r"^ds\..*grid\.", "grid geometry 180 x 360, 1 degree", "structural", ""),
    (r"^ms\.common_gates\.|^ms\.missions\.(rover|solar|lunar_base)\.(gates|soft|require_present)", "see annotated rows", "", ""),
    (r"^ms\.missions\.\w+\.frozen_at", "timestamp", "none", ""),
]


def auto():
    ms = json.load(open(os.path.join(TL, "mission_scoring.json"), encoding="utf-8"))
    ec = json.load(open(os.path.join(TL, "engine", "engine_config.json"), encoding="utf-8"))
    ds = json.load(open(os.path.join(TL, "engine", "datasets.json"), encoding="utf-8"))
    out = []

    def walk(o, p):
        if isinstance(o, dict):
            for k, v in o.items():
                if k in ("why", "text", "source", "note", "reason", "caveat"):
                    continue
                walk(v, f"{p}.{k}")
        elif isinstance(o, list):
            for i, v in enumerate(o):
                walk(v, f"{p}[{i}]")
        elif isinstance(o, (int, float)) and not isinstance(o, bool):
            out.append((p, o))

    walk(ms, "ms")
    walk(ec, "ec")
    walk(ds["datasets"]["real_1deg"], "ds.real_1deg")
    for p, v in out:
        clean = p.replace(".value.", ".").replace(".value", "")
        rule = next(((d, e, pr) for rx, d, e, pr in AUTO_RULES if re.search(rx, clean)), None)
        if rule and rule[0] == "see annotated rows":
            continue
        key = re.findall(r"[A-Za-z_][A-Za-z0-9_]*", clean.split(".")[-1])[0]
        ROWS.append({"id": "AUTO " + clean, "value": v, "unit": "", "category": "configuration leaf",
                     "origin_class": "", "origin": rule[0] if rule else "NOT CLASSIFIED: see used_at",
                     "defined_in": {"ms": MS, "ec": EC, "ds": DS}[clean.split(".")[0]], "used_at": uses(key, limit=2),
                     "effect_measured": rule[1] if rule else "", "flag": ("DEAD CONFIGURATION" if rule and "DEAD" in rule[2] else ""),
                     "proposal": rule[2] if rule else "", "correction_changes_design": "no" if rule and "DEAD" in rule[2] else ""})


def builders():
    """Module constants of the table builders (real_data/*.py): NAME = number."""
    for f in ("build_moon.py", "build_earth.py"):
        lines = _SRC[os.path.join(TL, "real_data", f)]
        for i, ln in enumerate(lines):
            m = re.match(r"^([A-Z][A-Z0-9_]+)\s*=\s*([-0-9.e/ ()*+]+?)\s*(#\s*(.*))?$", ln)
            if not m:
                continue
            name, val, com = m.group(1), m.group(2).strip(), (m.group(4) or "")
            if not com:   # nearest comment line just above (section header or legend note)
                for j in range(i - 1, max(-1, i - 4), -1):
                    t = lines[j].strip()
                    if t.startswith("#") and len(t.strip("#- ")) > 3:
                        com = "(comment above) " + t.strip("# ")
                        break
            if name in ("NR", "NC", "NCELL", "NROWS", "NCOLS"):
                continue
            ROWS.append({"id": f"BUILDER {f}:{name}", "value": val, "unit": "", "category": "table builder constant",
                         "origin_class": "literature" if re.search(r"fact sheet|IAU|IUGG|PIA|IERS|label|legend", com) else ("design" if com else "NOT RECORDED"),
                         "origin": com or "no comment in the code", "defined_in": f"tierra luna/real_data/{f}:{i + 1}",
                         "used_at": uses(name, limit=3), "effect_measured": "acts through the tables; not perturbed (needs a rebuild from the raw downloads)",
                         "flag": ("" if not com.startswith("(comment above) 3.") and com and not (name == "RA_MIN_VALID_FRAC") else "NO ORIGIN RECORDED (the comment above is a section title)") if com else "NO ORIGIN RECORDED",
                         "proposal": "" if (com and name != "RA_MIN_VALID_FRAC") else "add the source or the reason in a comment (acts only on the information column rock_abundance_frac, never on a result)" if name == "RA_MIN_VALID_FRAC" else "add the source or the reason in a comment",
                         "correction_changes_design": ""})


def builders_extra():
    """Builder constants written as tuples or pairs (not caught by the NAME = number pattern)."""
    for name, val, org, line in (
            ("CCI_BARE", "(200, 201, 202)", "ESA CCI LCCS legend codes (bare areas); with CCI_SPARSE they make rock_or_bare_frac", "build_earth.py:55"),
            ("CCI_SPARSE", "(150, 151, 152, 153)", "ESA CCI LCCS legend codes (sparse vegetation < 15 %)", "build_earth.py:56"),
            ("WGS84_A, WGS84_INVF", "6378.137 km, 298.257223563", "WGS84 ellipsoid (meridian arc of the grid cells)", "build_earth.py:49")):
        ROWS.append({"id": f"BUILDER build_earth.py:{name}", "value": val, "unit": "", "category": "table builder constant",
                     "origin_class": "literature", "origin": org, "defined_in": f"tierra luna/real_data/{line}",
                     "used_at": uses(name.split(",")[0], limit=3), "effect_measured": "acts through the tables; not perturbed (needs a rebuild)",
                     "flag": "", "proposal": "", "correction_changes_design": ""})


def main():
    annotated()
    auto()
    builders()
    builders_extra()
    fields = ["id", "value", "unit", "category", "origin_class", "origin", "defined_in", "used_at", "effect_measured", "flag", "proposal",
              "correction_changes_design"]
    with open(os.path.join(OUT, "inventory.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        w.writerows(ROWS)
    n = len(ROWS)
    flagged = [r for r in ROWS if r["flag"]]
    print(f"{n} rows, {len(flagged)} flagged")
    for r in flagged:
        print(" -", r["id"], "|", r["flag"][:110])


if __name__ == "__main__":
    main()
