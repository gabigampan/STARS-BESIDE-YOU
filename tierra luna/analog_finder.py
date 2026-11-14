import copy
import json
import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from mission_filters import TEMPLATE as MISSION_TEMPLATE, apply_missions, load_cfg as load_mission_cfg
from rover_preset import (
    DEFAULT_GRAVITY as ROVER_DEFAULT_GRAVITY,
    PRESET_CONFIG as ROVER_PRESET_CONFIG,
    ROVER_SPEC,
    _json_safe as rover_json_safe,
    build_rover_preset,
    merge_into_presets,
)

MISSION_FILTERS_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "mission_filters.json"
)
PRESETS_JSON_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "data", "presets", "presets.json"
)


def get_mission_config(path: Optional[str] = None) -> Dict:
    p = path or MISSION_FILTERS_PATH
    if os.path.exists(p):
        return load_mission_cfg(p)
    return copy.deepcopy(MISSION_TEMPLATE)


def get_rover_preset_bundle(author: str = "Robotics 1 - Mobility Team") -> Dict:
    preset = build_rover_preset(
        ROVER_SPEC,
        ROVER_PRESET_CONFIG,
        ROVER_DEFAULT_GRAVITY,
        author=author,
        freeze=True,
        allow_unverified=True,
    )
    bundle = rover_json_safe(
        {
            "rover_spec": ROVER_SPEC,
            "preset_config": ROVER_PRESET_CONFIG,
            "gravity": ROVER_DEFAULT_GRAVITY,
            "preset": preset,
        }
    )
    try:
        merge_into_presets(Path(PRESETS_JSON_PATH), preset, name="rover", refreeze=True)
    except Exception:
        pass
    return bundle


ANALOG_FEATURES = [
    "elevation_rel_m",
    "slope_deg",
    "roughness_m",
    "temp_k",
    "rock_or_bare_frac",
    "sar_sigma0_db",
]

DEFAULT_WEIGHTS: Dict[str, float] = {
    "elevation_rel_m": 0.15,
    "slope_deg": 0.25,
    "roughness_m": 0.20,
    "temp_k": 0.15,
    "rock_or_bare_frac": 0.15,
    "sar_sigma0_db": 0.10,
}

EARTH_LANDMARKS = [
    ("Atacama Desert & Altiplano (Chile)", -23.5, -68.5),
    ("McMurdo Dry Valleys (Antarctica)", -77.5, 162.0),
    ("East Antarctic Polar Plateau", -80.0, 75.0),
    ("West Antarctic Ice Sheet & Mountains", -80.0, -110.0),
    ("Queen Maud Land Massifs (Antarctica)", -72.0, 10.0),
    ("Askja Volcanic Highlands (Iceland)", 64.8, -17.5),
    ("Mauna Kea Volcanic Slopes (Hawaii)", 19.8, -155.5),
    ("Devon Island Haughton Crater (Arctic Canada)", 75.0, -82.0),
    ("Baffin & Ellesmere Arctic Shield (Canada)", 70.0, -72.0),
    ("Brooks Range & North Slope (Alaska)", 68.0, -150.0),
    ("Canadian Shield Craton (Quebec/Labrador)", 54.0, -68.0),
    ("Craters of the Moon & Snake River Plain (Idaho, USA)", 43.4, -113.5),
    ("Meteor Crater & Colorado Plateau (Arizona, USA)", 35.0, -111.0),
    ("Sierra Madre & Mexican Volcanic Belt", 24.0, -104.0),
    ("High Andes Volcanic Zone (Peru/Bolivia)", -16.0, -70.0),
    ("Patagonian Steppe & Southern Andes (Argentina)", -47.0, -70.0),
    ("Guiana Shield Highlands (South America)", 5.0, -62.0),
    ("Brazilian Central Plateau", -15.0, -48.0),
    ("Greenland Interior Ice Sheet & Nunataks", 72.0, -40.0),
    ("Scandinavian Caledonides (Norway/Sweden)", 63.0, 12.0),
    ("Pyrenees & Iberian Highland Zone (Spain)", 40.5, -1.5),
    ("European Alps & Central Massifs", 46.5, 10.0),
    ("Mount Etna & Apennine Belt (Italy)", 37.7, 15.0),
    ("Anatolian Plateau & Cappadocia (Turkey)", 38.5, 34.5),
    ("Teide & Lanzarote Volcanic Field (Canary Islands)", 28.3, -16.6),
    ("Atlas Mountains & Anti-Atlas (Morocco)", 31.5, -6.0),
    ("Hoggar Mountains (Algeria)", 23.5, 5.5),
    ("Tibesti Volcanic Massif (Central Sahara)", 21.0, 18.0),
    ("Eastern Sahara & Nubian Desert (Egypt/Sudan)", 22.0, 30.0),
    ("Afar & East African Rift (Ethiopia)", 11.5, 41.0),
    ("East African Plateau & Kilimanjaro", -3.0, 36.0),
    ("Namib Desert & Southern African Escarpment", -24.0, 16.0),
    ("Drakensberg & Karoo Basin (South Africa)", -30.0, 26.0),
    ("Arabian Harrat Lava Fields", 24.0, 42.0),
    ("Lut Desert & Iranian Plateau (Iran)", 31.0, 58.0),
    ("Caucasus & Armenian Volcanic Highlands", 41.5, 44.5),
    ("Ural Mountains Belt", 60.0, 59.5),
    ("Pamir & Tian Shan Mountains (Central Asia)", 40.0, 74.0),
    ("Tibetan Plateau & Kunlun (China)", 33.5, 86.0),
    ("Himalayan & Karakoram Range", 29.0, 84.0),
    ("Taklamakan & Tarim Basin", 39.0, 83.0),
    ("Gobi Desert & Altai Range (Mongolia)", 44.0, 102.0),
    ("Central Siberian Traps & Putorana Plateau", 68.0, 95.0),
    ("Verkhoyansk & Chersky Range (NE Siberia)", 65.0, 138.0),
    ("Kamchatka Volcanic Belt (Russia)", 56.0, 160.0),
    ("Deccan Basalt Traps (India)", 19.0, 75.0),
    ("Pilbara Craton & Western Outback (Australia)", -22.5, 120.0),
    ("Central Australian Arid Ranges (MacDonnell)", -24.0, 134.0),
]


def assign_earth_region_names(lats: np.ndarray, lons: np.ndarray) -> List[str]:
    names = []
    for lat, lon in zip(lats, lons):
        best_name = f"Global Cell ({lat:.1f}°, {lon:.1f}°)"
        best_d = 999.0
        for lname, llat, llon in EARTH_LANDMARKS:
            d = float(np.hypot(lat - llat, (lon - llon) * np.cos(np.radians(lat))))
            if d < best_d:
                best_d = d
                best_name = lname if d < 18.0 else f"{lname} Sector ({lat:.1f}°, {lon:.1f}°)"
        names.append(best_name)
    return names


def normalize_planetary_features(
    df: pd.DataFrame, features: List[str] = ANALOG_FEATURES
) -> Tuple[pd.DataFrame, Dict[str, Dict[str, float]]]:
    norm_df = df.copy()
    stats: Dict[str, Dict[str, float]] = {}

    for feat in features:
        vals = pd.to_numeric(norm_df[feat], errors="coerce").to_numpy(dtype=np.float64)
        finite = vals[np.isfinite(vals)]
        if finite.size == 0:
            stats[feat] = {"mean": 0.0, "std": 1.0, "min": 0.0, "max": 1.0, "valid": False}
            norm_df[f"{feat}_z"] = 0.0
            norm_df[f"{feat}_norm"] = 0.5
            continue

        med = float(np.median(finite))
        q25, q75 = np.percentile(finite, [25.0, 75.0])
        iqr_scale = float((q75 - q25) / 1.349)
        std = float(np.std(finite))
        scale = iqr_scale if iqr_scale > 1e-6 else (std if std > 1e-6 else 1.0)
        vmin, vmax = float(np.min(finite)), float(np.max(finite))
        span = max(vmax - vmin, 1e-6)

        z = np.where(np.isfinite(vals), (vals - med) / scale, 0.0)
        z = np.clip(z, -4.0, 4.0)
        minmax = np.where(np.isfinite(vals), (vals - vmin) / span, 0.5)

        norm_df[f"{feat}_z"] = np.round(z, 4)
        norm_df[f"{feat}_norm"] = np.round(minmax, 4)
        stats[feat] = {
            "mean": round(float(np.mean(finite)), 4),
            "median": round(med, 4),
            "std": round(scale, 4),
            "min": round(vmin, 4),
            "max": round(vmax, 4),
            "valid": True,
        }

    return norm_df, stats


def build_lunar_reference_zones(moon_norm_df: pd.DataFrame) -> Dict[str, Dict[str, float]]:
    lat = moon_norm_df["lat_deg"]
    lon = moon_norm_df["lon_deg"]
    zones: Dict[str, pd.Series] = {
        "Global Lunar Surface Mean (-90° to +90°)": pd.Series(True, index=moon_norm_df.index),
        "South Pole PSR & Shackleton Rim (75°S–90°S)": lat <= -75.0,
        "South Pole-Aitken Basin (-53°S, 169°W)": (
            (lat <= -30.0) & (lat >= -75.0) & (np.abs(lon) >= 135.0)
        ),
        "Tycho & Southern Rocky Craters (35°S–55°S, 30°W–0°)": (
            (lat >= -55.0) & (lat <= -35.0) & (lon >= -30.0) & (lon <= 5.0)
        ),
        "Mare Tranquillitatis & Equatorial Maria": (
            (np.abs(lat) <= 30.0) & (moon_norm_df["elevation_m"] <= -1200.0)
        ),
        "Steep Crater Walls & Massifs (Top 20% Slope)": (
            moon_norm_df["slope_deg"] >= moon_norm_df["slope_deg"].quantile(0.80)
        ),
        "Lunar Farside Highlands (> +2000 m)": (
            moon_norm_df["elevation_m"] >= moon_norm_df["elevation_m"].quantile(0.80)
        ),
    }

    profiles: Dict[str, Dict[str, float]] = {}
    for name, mask in zones.items():
        sub = moon_norm_df[mask] if mask.any() else moon_norm_df
        prof: Dict[str, float] = {}
        for feat in ANALOG_FEATURES:
            prof[f"{feat}_z"] = round(float(sub[f"{feat}_z"].mean()), 4)
            prof[f"{feat}_norm"] = round(float(sub[f"{feat}_norm"].mean()), 4)
            prof[feat] = (
                round(float(sub[feat].dropna().mean()), 4)
                if sub[feat].notna().any()
                else 0.0
            )
        prof["pixel_count"] = int(len(sub))
        profiles[name] = prof

    return profiles


def map_domain_weights_to_features(domain_weights: Dict[str, float]) -> Dict[str, float]:
    relieve = float(domain_weights.get("relieve", 0.2))
    material = float(domain_weights.get("material", 0.2))
    termico = float(domain_weights.get("termico", 0.2))
    luz = float(domain_weights.get("luz", 0.2))
    agua = float(domain_weights.get("agua", 0.2))
    raw = {
        "slope_deg": relieve * 0.45 + luz * 0.15,
        "roughness_m": relieve * 0.35 + material * 0.20,
        "elevation_rel_m": relieve * 0.20 + luz * 0.35 + agua * 0.20,
        "temp_k": termico * 0.80 + luz * 0.35 + agua * 0.45,
        "rock_or_bare_frac": material * 0.55 + termico * 0.20 + luz * 0.15,
        "sar_sigma0_db": material * 0.25 + agua * 0.35,
    }
    total = sum(raw.values()) or 1.0
    return {k: v / total for k, v in raw.items()}


def compute_mission_optimality_scores(
    earth_norm: pd.DataFrame,
    lunar_zones: Dict[str, Dict[str, float]],
    mission_cfg: Dict,
) -> pd.DataFrame:
    df = earth_norm.copy()
    missions = mission_cfg.get("missions", {})
    default_target = list(lunar_zones.values())[0]
    polar_target = lunar_zones.get(
        "South Pole PSR & Shackleton Rim (75°S–90°S)", default_target
    )
    rocky_target = lunar_zones.get(
        "Tycho & Southern Rocky Craters (35°S–55°S, 30°W–0°)", default_target
    )

    mission_targets = {
        "rover": rocky_target,
        "solar": polar_target,
        "thermal": default_target,
        "ice": polar_target,
    }

    for m_name, m_obj in missions.items():
        fw = map_domain_weights_to_features(m_obj.get("weights", {}))
        t_prof = mission_targets.get(m_name, default_target)
        sq = np.zeros(len(df), dtype=np.float64)
        for feat in ANALOG_FEATURES:
            diff = df[f"{feat}_z"].to_numpy(dtype=np.float64) - t_prof[f"{feat}_z"]
            sq += fw[feat] * (diff ** 2)
        analog_sim = 100.0 * np.exp(-0.45 * np.sqrt(sq))

        if m_name == "rover":
            s300 = df["slope_300m_deg"].to_numpy(dtype=np.float64)
            r300 = df["rough_300m_m"].to_numpy(dtype=np.float64)
            rock = df["rock_or_bare_frac"].to_numpy(dtype=np.float64)
            tols = m_obj.get("tolerances") or ROVER_PRESET_CONFIG.get("tolerances", {})
            slope_tol = float(tols.get("slope_300m_deg", {}).get("scale", 5.0))
            rough_tol = float(tols.get("rough_300m_m", {}).get("scale", 10.0))
            t_slope = float(t_prof.get("slope_deg", 3.5))
            t_rough = float(t_prof.get("roughness_m", 60.0))
            slope_q = np.exp(-0.5 * ((s300 - t_slope) / max(slope_tol, 0.5)) ** 2)
            rough_q = np.exp(-0.5 * ((r300 - t_rough) / max(rough_tol * 12.0, 5.0)) ** 2)
            gate_q = 100.0 * (0.45 * slope_q + 0.30 * rough_q + 0.25 * np.clip(rock, 0.0, 1.0))
        elif m_name == "solar":
            irr = df["irradiance_kwh_m2_day"].to_numpy(dtype=np.float64)
            slow = df["sun_low_frac_0_5deg"].to_numpy(dtype=np.float64)
            smax = df["sun_elev_max_deg"].to_numpy(dtype=np.float64)
            irr_q = np.clip((irr - 1.8) / (8.5 - 1.8), 0.0, 1.0)
            low_q = np.clip((slow - 0.025) / 0.18, 0.0, 1.0)
            elev_q = np.clip(1.0 - np.abs(smax - 35.0) / 50.0, 0.0, 1.0)
            gate_q = 100.0 * (0.45 * irr_q + 0.35 * low_q + 0.20 * elev_q)
        elif m_name == "thermal":
            damp = df["lst_diurnal_amp_k"].to_numpy(dtype=np.float64)
            rock = df["rock_or_bare_frac"].to_numpy(dtype=np.float64)
            tic = df["thermal_inertia_class"].astype(str).to_numpy()
            amp_q = np.clip((damp - 16.0) / 28.0, 0.0, 1.0)
            tic_q = np.where(np.isin(tic, ["roca", "hielo"]), 1.0, np.where(tic == "regolito", 0.85, 0.7))
            gate_q = 100.0 * (0.50 * amp_q + 0.25 * tic_q + 0.25 * np.clip(rock, 0.0, 1.0))
        elif m_name == "ice":
            temp = df["temp_k"].to_numpy(dtype=np.float64)
            pfc = df["permafrost_class"].astype(str).to_numpy()
            cold_q = np.clip((280.0 - temp) / 60.0, 0.0, 1.0)
            pfc_q = np.where(
                pfc == "continuo",
                1.0,
                np.where(pfc == "discontinuo", 0.85, np.where(pfc == "esporadico", 0.70, 0.55)),
            )
            gate_q = 100.0 * (0.55 * cold_q + 0.45 * pfc_q)
        else:
            gate_q = analog_sim

        pass_mask = df[f"pass_{m_name}"].to_numpy(dtype=np.float64) > 0
        combined = 0.65 * analog_sim + 0.35 * gate_q
        # A cell that fails any hard filter of this mission has no score for it and
        # cannot be ranked for it (team lead's rule; replaces the old x0.35 penalty).
        score = np.where(pass_mask, combined, np.nan)
        df[f"score_{m_name}"] = np.round(score, 2)

    m_cols = [f"score_{m}" for m in missions.keys()]
    pass_all_mask = df["pass_all"].to_numpy(dtype=np.float64) > 0
    mean_all = df[m_cols].mean(axis=1).to_numpy(dtype=np.float64)
    # Same rule for the combined score: only cells passing every mission get one.
    df["score_all"] = np.round(np.where(pass_all_mask, mean_all, np.nan), 2)
    return df


def build_optimal_mission_zones(
    earth_scored: pd.DataFrame,
    mission_cfg: Dict,
    top_zones_per_mission: int = 6,
    min_separation_deg: float = 14.0,
) -> Dict[str, List[Dict]]:
    missions_keys = list(mission_cfg.get("missions", {}).keys()) + ["all"]
    optimal_zones: Dict[str, List[Dict]] = {}

    for m_key in missions_keys:
        pass_col = "pass_all" if m_key == "all" else f"pass_{m_key}"
        score_col = "score_all" if m_key == "all" else f"score_{m_key}"

        passing = earth_scored[earth_scored[pass_col] == 1].copy()
        if passing.empty:
            optimal_zones[m_key] = []
            continue

        passing = passing.sort_values(score_col, ascending=False).reset_index(drop=True)
        selected_centers: List[Tuple[float, float]] = []
        zones_list: List[Dict] = []

        for _, row in passing.iterrows():
            lat = float(row["lat_deg"])
            lon = float(row["lon_deg"])
            too_close = False
            for clat, clon in selected_centers:
                dist = float(np.hypot(lat - clat, (lon - clon) * np.cos(np.radians(lat))))
                if dist < min_separation_deg:
                    too_close = True
                    break
            if too_close:
                continue

            selected_centers.append((lat, lon))
            d_all = np.hypot(
                passing["lat_deg"].to_numpy(dtype=np.float64) - lat,
                (passing["lon_deg"].to_numpy(dtype=np.float64) - lon) * np.cos(np.radians(lat)),
            )
            cluster = passing[d_all <= 8.5]
            lat_min = float(cluster["lat_deg"].min()) - 1.0
            lat_max = float(cluster["lat_deg"].max()) + 1.0
            lon_min = float(cluster["lon_deg"].min()) - 1.0
            lon_max = float(cluster["lon_deg"].max()) + 1.0

            m_meta = (
                mission_cfg["missions"][m_key]
                if m_key in mission_cfg.get("missions", {})
                else {
                    "description": "Combined All-Mission Hub (Rover + Solar + Thermal + Ice)",
                    "author": "Multi-Mission Integration Team",
                }
            )

            zones_list.append(
                {
                    "mission": m_key,
                    "zone_rank": len(zones_list) + 1,
                    "earth_region": str(row["earth_region"]),
                    "matched_lunar_zone": str(row["matched_lunar_zone"]),
                    "lat": round(lat, 2),
                    "lon": round(lon, 2),
                    "bbox": [
                        round(max(-85.0, lat_min), 2),
                        round(max(-180.0, lon_min), 2),
                        round(min(85.0, lat_max), 2),
                        round(min(180.0, lon_max), 2),
                    ],
                    "cluster_cells": int(len(cluster)),
                    "mission_score": round(float(row[score_col]), 2),
                    "similarity_pct": round(float(row["similarity_pct"]), 2),
                    "elevation_m": round(float(row["elevation_m"]), 1),
                    "slope_300m_deg": round(float(row["slope_300m_deg"]), 2),
                    "rough_300m_m": round(float(row["rough_300m_m"]), 1),
                    "temp_k": round(float(row["temp_k"]), 1),
                    "lst_diurnal_amp_k": round(float(row["lst_diurnal_amp_k"]), 1),
                    "irradiance_kwh_m2_day": round(float(row["irradiance_kwh_m2_day"]), 2),
                    "sun_elev_max_deg": round(float(row["sun_elev_max_deg"]), 1),
                    "sun_low_frac_0_5deg": round(float(row["sun_low_frac_0_5deg"]), 4),
                    "thermal_inertia_class": str(row["thermal_inertia_class"]),
                    "permafrost_class": str(row["permafrost_class"]),
                    "description": m_meta.get("description", ""),
                    "author": m_meta.get("author", ""),
                }
            )
            if len(zones_list) >= top_zones_per_mission:
                break

        optimal_zones[m_key] = zones_list

    return optimal_zones


def _apply_mission_scoring_gates(earth_df: pd.DataFrame, mission_names: List[str]) -> Tuple[pd.DataFrame, Dict]:
    """Set pass_<mission> and pass_all from mission_scoring.json through the engine's
    gate module (engine.gates.evaluate_gates, Earth body rules). Returns the frame and
    stats in the old {mission: {"pass", "fail_by": {column: n}}, "_all": n} format."""
    from engine.config import load_engine_config, load_mission_config
    from engine.gates import evaluate_gates

    ecfg = load_engine_config()
    mcfg = load_mission_config(engine_cfg=ecfg)
    df = earth_df.copy()
    stats: Dict = {}
    all_ok = np.ones(len(df), dtype=bool)
    for m_name in mission_names:
        if m_name not in mcfg["missions"]:
            raise KeyError(f"mission '{m_name}' is not defined in mission_scoring.json")
        g = evaluate_gates(df.reset_index(drop=True), "EARTH", m_name, mcfg, ecfg)
        df[f"pass_{m_name}"] = g.passed.astype(int)
        fail_by: Dict[str, int] = {}
        for reasons in g.reasons:
            for col in dict.fromkeys(code.split(":")[0] for code in reasons):
                fail_by[col] = fail_by.get(col, 0) + 1
        stats[m_name] = {"pass": int(g.passed.sum()), "fail_by": fail_by}
        all_ok &= g.passed
    df["pass_all"] = all_ok.astype(int)
    stats["_all"] = int(all_ok.sum())
    return df, stats


def compute_analog_ranking(
    moon_df: pd.DataFrame,
    earth_df: pd.DataFrame,
    weights: Optional[Dict[str, float]] = None,
    target_zone: str = "Global Lunar Surface Mean (-90° to +90°)",
    top_k: int = 50,
) -> Tuple[pd.DataFrame, pd.DataFrame, Dict]:
    w = dict(DEFAULT_WEIGHTS)
    if weights:
        w.update(weights)

    land_filter = earth_df["elevation_m"] > 0.0
    earth_land_df = earth_df[land_filter].copy() if land_filter.any() else earth_df.copy()

    moon_norm, moon_stats = normalize_planetary_features(moon_df)
    earth_norm, earth_stats = normalize_planetary_features(earth_land_df)
    lunar_zones = build_lunar_reference_zones(moon_norm)

    if target_zone not in lunar_zones:
        target_zone = list(lunar_zones.keys())[0]
    target_profile = lunar_zones[target_zone]

    active_feats = [
        f for f in ANALOG_FEATURES
        if w.get(f, 0.0) > 0 and moon_stats[f]["valid"] and earth_stats[f]["valid"]
    ]
    total_w = sum(w[f] for f in active_feats) or 1.0
    norm_w = {f: w[f] / total_w for f in active_feats}

    sq_dist = np.zeros(len(earth_norm), dtype=np.float64)
    for feat in active_feats:
        diff = earth_norm[f"{feat}_z"].to_numpy(dtype=np.float64) - target_profile[f"{feat}_z"]
        comp_sim = 100.0 * np.exp(-0.35 * (diff ** 2))
        earth_norm[f"sim_{feat}_pct"] = np.round(comp_sim, 2)
        sq_dist += norm_w[feat] * (diff ** 2)

    rms_dist = np.sqrt(sq_dist)
    similarity_pct = 100.0 * np.exp(-0.45 * rms_dist)
    earth_norm["similarity_pct"] = np.round(similarity_pct, 2)
    earth_norm["feature_distance"] = np.round(rms_dist, 4)

    zone_names = [z for z in lunar_zones.keys() if not z.startswith("Global Lunar Surface Mean")]
    zone_dists = []
    for zname in zone_names:
        zprof = lunar_zones[zname]
        zd = np.zeros(len(earth_norm), dtype=np.float64)
        for feat in active_feats:
            diff = earth_norm[f"{feat}_z"].to_numpy(dtype=np.float64) - zprof[f"{feat}_z"]
            zd += norm_w[feat] * (diff ** 2)
        zone_dists.append(zd)
    best_zone_idx = np.argmin(np.vstack(zone_dists), axis=0)
    earth_norm["matched_lunar_zone"] = [zone_names[i] for i in best_zone_idx]
    earth_norm["earth_region"] = assign_earth_region_names(
        earth_norm["lat_deg"].to_numpy(), earth_norm["lon_deg"].to_numpy()
    )

    mission_cfg = get_mission_config()
    rover_bundle = get_rover_preset_bundle()
    mission_names = list(mission_cfg.get("missions", {}).keys())

    if "rain_mm_day" not in earth_norm.columns:
        cos_lat = np.clip(np.cos(np.radians(earth_norm["lat_deg"].to_numpy(dtype=np.float64))), 0.05, 1.0)
        bare_v = np.clip(earth_norm["rock_or_bare_frac"].to_numpy(dtype=np.float64), 0.0, 1.0)
        elev_v = np.maximum(earth_norm["elevation_m"].to_numpy(dtype=np.float64), 0.0)
        lat_v = earth_norm["lat_deg"].to_numpy(dtype=np.float64)
        temp_v = earth_norm["temp_k"].to_numpy(dtype=np.float64)
        damp_v = earth_norm["lst_diurnal_amp_k"].to_numpy(dtype=np.float64)
        earth_norm["rain_mm_day"] = np.round(
            np.clip(4.2 * np.power(1.0 - bare_v, 1.8) * np.clip(cos_lat + 0.15, 0.2, 1.1), 0.01, 12.0), 2
        )
        earth_norm["wind_max_ms"] = np.round(
            np.clip(4.5 + 0.0012 * elev_v + 3.8 * np.power(np.abs(lat_v) / 90.0, 1.4), 2.5, 15.5), 2
        )
        earth_norm["tmin_c"] = np.round((temp_v - 273.15) - 0.35 * damp_v, 2)

    wd_cfg = ROVER_PRESET_CONFIG.get("workable_days", {})
    rain_max = float(wd_cfg.get("rain_mm_max", 1.0))
    wind_max = float(wd_cfg.get("wind_max_ms_max", 12.0))
    tmin_min = float(wd_cfg.get("tmin_c_min", -10.0))
    earth_norm["workable_rover"] = (
        (earth_norm["rain_mm_day"] <= rain_max)
        & (earth_norm["wind_max_ms"] <= wind_max)
        & (earth_norm["tmin_c"] >= tmin_min)
    ).astype(int)

    # Hard filters come from mission_scoring.json (the team's new filter system, which
    # replaces mission_filters.json), applied by the engine exactly as for the static
    # bundle, so this legacy output never scores or ranks a cell the engine eliminates.
    earth_norm, mission_stats = _apply_mission_scoring_gates(earth_norm, mission_names)

    earth_norm = compute_mission_optimality_scores(earth_norm, lunar_zones, mission_cfg)
    optimal_mission_zones = build_optimal_mission_zones(earth_norm, mission_cfg)

    # Only cells that pass every mission's hard filters are ranked (a gate-failed
    # cell cannot be ranked); ties keep the earlier row order (stable sort).
    ranked = (earth_norm[earth_norm["pass_all"] == 1]
              .sort_values("similarity_pct", ascending=False, kind="mergesort").reset_index(drop=True))
    ranked["rank"] = np.arange(1, len(ranked) + 1)

    mission_cols = [
        c for c in [
            "mask_fraction",
            "slope_300m_deg",
            "rough_300m_m",
            "irradiance_kwh_m2_day",
            "sun_elev_max_deg",
            "sun_low_frac_0_5deg",
            "lst_diurnal_amp_k",
            "thermal_inertia_class",
            "permafrost_class",
            "rain_mm_day",
            "wind_max_ms",
            "tmin_c",
            "workable_rover",
            *[f"pass_{m}" for m in mission_names],
            "pass_all",
            *[f"score_{m}" for m in mission_names],
            "score_all",
        ]
        if c in ranked.columns
    ]

    cols = [
        "rank",
        "similarity_pct",
        "feature_distance",
        "earth_region",
        "matched_lunar_zone",
        "row",
        "col",
        "lat_deg",
        "lon_deg",
        "x_m",
        "y_m",
        "elevation_m",
        *ANALOG_FEATURES,
        *[f"sim_{f}_pct" for f in active_feats],
        *mission_cols,
    ]
    top_ranking = ranked[cols].head(top_k).copy()

    metadata = {
        "weights_normalized": norm_w,
        "active_features": active_feats,
        "target_zone": target_zone,
        "lunar_zones": lunar_zones,
        "moon_stats": moon_stats,
        "earth_stats": earth_stats,
        "mission_filters": mission_cfg,
        "mission_stats": mission_stats,
        "optimal_mission_zones": optimal_mission_zones,
        "rover_preset": rover_bundle,
    }
    return top_ranking, earth_norm, metadata


def export_web_bundle(
    moon_df: pd.DataFrame,
    earth_df: pd.DataFrame,
    out_dir: str = "output_py",
    web_dir: str = "web",
    stride: int = 2,
) -> Dict[str, str]:
    os.makedirs(out_dir, exist_ok=True)
    os.makedirs(web_dir, exist_ok=True)

    top_ranking, earth_scored, meta = compute_analog_ranking(moon_df, earth_df, top_k=100)
    ranking_csv_path = os.path.join(out_dir, "analog_ranking.csv")
    top_ranking.to_csv(ranking_csv_path, index=False)

    moon_norm, _ = normalize_planetary_features(moon_df)

    earth_sub = earth_scored[
        (earth_scored["row"] % stride == 0) & (earth_scored["col"] % stride == 0)
    ].copy()
    moon_sub = moon_norm[
        (moon_norm["row"] % stride == 0) & (moon_norm["col"] % stride == 0)
    ].copy()

    def _score_or_none(value) -> Optional[float]:
        # Gate-failed cells carry NaN scores; JSON gets null, never a number.
        v = float(value) if value is not None else float("nan")
        return round(v, 2) if np.isfinite(v) else None

    def pack_cells(df: pd.DataFrame, include_match: bool = False) -> List[Dict]:
        records = []
        for _, r in df.iterrows():
            item = {
                "r": int(r["row"]),
                "c": int(r["col"]),
                "lat": round(float(r["lat_deg"]), 4),
                "lon": round(float(r["lon_deg"]), 4),
                "elev": round(float(r["elevation_m"]), 1),
                "rel": round(float(r["elevation_rel_m"]), 1),
                "slope": round(float(r["slope_deg"]), 2),
                "rough": round(float(r["roughness_m"]), 2),
                "temp": round(float(r["temp_k"]), 2) if pd.notna(r["temp_k"]) else None,
                "rock": round(float(r["rock_or_bare_frac"]), 4) if pd.notna(r["rock_or_bare_frac"]) else None,
                "sar": round(float(r["sar_sigma0_db"]), 2) if pd.notna(r["sar_sigma0_db"]) else None,
                "z": [round(float(r[f"{f}_z"]), 3) for f in ANALOG_FEATURES],
                "mf": round(float(r.get("mask_fraction", 1.0)), 3),
                "s300": round(float(r.get("slope_300m_deg", r["slope_deg"])), 2),
                "r300": round(float(r.get("rough_300m_m", r["roughness_m"])), 1),
                "irr": round(float(r.get("irradiance_kwh_m2_day", 4.0)), 2),
                "smax": round(float(r.get("sun_elev_max_deg", 45.0)), 1),
                "slow": round(float(r.get("sun_low_frac_0_5deg", 0.05)), 4),
                "damp": round(float(r.get("lst_diurnal_amp_k", 20.0)), 1),
                "tic": str(r.get("thermal_inertia_class", "roca")),
                "pfc": str(r.get("permafrost_class", "ninguno")),
                "rain": round(float(r.get("rain_mm_day", 0.5)), 2),
                "wind": round(float(r.get("wind_max_ms", 6.0)), 2),
                "tmin": round(float(r.get("tmin_c", -5.0)), 1),
            }
            if include_match:
                item["zone"] = str(r["matched_lunar_zone"])
                item["reg"] = str(r["earth_region"])
                item["p_rov"] = int(r.get("pass_rover", 1))
                item["p_sol"] = int(r.get("pass_solar", 1))
                item["p_thm"] = int(r.get("pass_thermal", 1))
                item["p_ice"] = int(r.get("pass_ice", 1))
                item["p_all"] = int(r.get("pass_all", 1))
                item["wk_rov"] = int(r.get("workable_rover", 1))
                item["s_rov"] = _score_or_none(r.get("score_rover"))
                item["s_sol"] = _score_or_none(r.get("score_solar"))
                item["s_thm"] = _score_or_none(r.get("score_thermal"))
                item["s_ice"] = _score_or_none(r.get("score_ice"))
                item["s_all"] = _score_or_none(r.get("score_all"))
            records.append(item)
        return records

    opt_rows = []
    for m_List in meta["optimal_mission_zones"].values():
        opt_rows.extend(m_List)
    opt_csv_path = os.path.join(out_dir, "optimal_mission_zones.csv")
    if opt_rows:
        pd.DataFrame(opt_rows).to_csv(opt_csv_path, index=False)

    n_rows = int(earth_df["row"].max() + 1)
    n_cols = int(earth_df["col"].max() + 1)

    payload = {
        "grid": {
            "rows": n_rows,
            "cols": n_cols,
            "stride": stride,
            "dlat": round((180.0 / n_rows) * stride, 4),
            "dlon": round((360.0 / n_cols) * stride, 4),
            "resolution_m": float(earth_df["resolution_m"].iloc[0]),
        },
        "features": ANALOG_FEATURES,
        "default_weights": DEFAULT_WEIGHTS,
        "lunar_zones": meta["lunar_zones"],
        "moon_stats": meta["moon_stats"],
        "earth_stats": meta["earth_stats"],
        "mission_filters": meta["mission_filters"],
        "mission_stats": meta["mission_stats"],
        "optimal_mission_zones": meta["optimal_mission_zones"],
        "rover_preset": meta["rover_preset"],
        "earth_cells": pack_cells(earth_sub, include_match=True),
        "moon_cells": pack_cells(moon_sub, include_match=False),
    }

    json_path = os.path.join(out_dir, "analog_web_data.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(payload, f)

    js_path = os.path.join(web_dir, "analog_data.js")
    with open(js_path, "w", encoding="utf-8") as f:
        f.write("window.ANALOG_DATA = ")
        json.dump(payload, f)
        f.write(";\n")

    return {
        "ranking_csv": ranking_csv_path,
        "optimal_zones_csv": opt_csv_path,
        "web_json": json_path,
        "web_js": js_path,
    }


if __name__ == "__main__":
    moon_csv = os.path.join("output_py", "moon_lola_diviner_clean.csv")
    earth_csv = os.path.join("output_py", "earth_srtm_modis_aster_clean.csv")
    if os.path.exists(moon_csv) and os.path.exists(earth_csv):
        m_df = pd.read_csv(moon_csv)
        e_df = pd.read_csv(earth_csv)
        paths = export_web_bundle(m_df, e_df)
        print(f"[ANALOG] Exported ranking and web bundle: {paths}")
