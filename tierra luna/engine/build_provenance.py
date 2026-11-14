"""Build engine/provenance.json from the audit data dictionary (A2_data_dictionary.csv).

Usage (from "tierra luna"):
    python -m engine.build_provenance --dictionary <path>/A2_data_dictionary.csv

The audit CSV supplies, per variable and body: unit, the audit's level, the claimed
source and what the code does (file:line). This module adds what the CSV does not
hold: the English label, a description, the physically valid range used by the
schema, the category vocabulary and a one-line caveat. The level is mapped from the
audit's level text, never from the column name:

    MEASURED...        -> MEASURED
    DERIVED...         -> DERIVED
    MODELLED...        -> MODELLED
    NOT DETERMINED...  -> UNDOCUMENTED   (cached array of undocumented origin)

provenance.json is committed, so the engine does not need the audit CSV at run time.
"""
from __future__ import annotations

import argparse
import json
import math
import os
from typing import Dict, List, Optional

import pandas as pd

from engine.config import BODIES, PROVENANCE_PATH, load_engine_config

# Variables of the harmonized table that carry physical meaning (metadata excluded).
VARIABLES: Dict[str, Dict] = {
    "elevation_m": {
        "label": "Elevation", "unit": "m", "kind": "numeric",
        "description": "Surface height. Earth: above sea level (ocean cells are a constant -250 m fill). Moon: above the 1737.4 km reference sphere.",
        "valid": {"EARTH": [-500.0, 9000.0], "MOON": [-9200.0, 10800.0]},
        "range_source": "config.py:80 (Earth) and config.py:90 (Moon), per the data dictionary; no external source cited",
        "caveat": {
            "EARTH": "Loaded from earth_global_real.npz of undocumented origin; land pattern matches real geography, ocean is a -250 m fill.",
            "MOON": "Exact 8x8 block mean of LOLA LDEM_4 (verified); a 2-degree cell hides all relief below about 61 km.",
        },
    },
    "elevation_rel_m": {
        "label": "Relative elevation", "unit": "m", "kind": "numeric",
        "description": "Elevation minus a mean (Earth: minus the land mean, ocean fixed at -1000 m; Moon: minus the global mean).",
        "valid": {"EARTH": [-6000.0, 6000.0], "MOON": [-9000.0, 9000.0]},
        "range_source": "config.py:81 and config.py:91 per the data dictionary; no external source cited",
        "caveat": {
            "EARTH": "Land = elevation_m - 1047.4 m; the ocean value -1000 m is inconsistent with the -250 m fill.",
            "MOON": "Elevation minus the global mean, exact; inherits the 2-degree block mean.",
        },
    },
    "slope_deg": {
        "label": "Slope", "unit": "deg", "kind": "numeric",
        "description": "Mean terrain slope of the cell.",
        "valid": {"EARTH": [0.0, 90.0], "MOON": [0.0, 90.0]},
        "range_source": "definition (0-90 degrees)",
        "caveat": {
            "EARTH": "Cached array; cannot be reproduced from its elevation (corr 0.60). Method unknown.",
            "MOON": "Cached array; neither the repo formula nor the 4-ppd LOLA gradient reproduces it. Method unknown.",
        },
    },
    "roughness_m": {
        "label": "Roughness", "unit": "m", "kind": "numeric",
        "description": "Spread of elevation inside the cell.",
        "valid": {"EARTH": [0.0, None], "MOON": [0.0, None]},
        "range_source": "definition (>= 0)",
        "caveat": {
            "EARTH": "Cached array, method undocumented; ocean is a 0.1 m fill. Labelled 'local 3x3 std' in code, which is not verified.",
            "MOON": "Standard deviation of the 64 LDEM_4 pixels (7.6 km each) in the cell, not a 3x3 std as labelled.",
        },
    },
    "temp_k": {
        "label": "Surface temperature", "unit": "K", "kind": "numeric",
        "description": "Surface temperature. Earth: described as a daytime land surface temperature. Moon: a night-time-like value.",
        "valid": {"EARTH": [180.0, 360.0], "MOON": [20.0, 420.0]},
        "range_source": "config.py:84 and config.py:94 per the data dictionary (> 0 K by definition)",
        "caveat": {
            "EARTH": "Cached array of undocumented origin; ocean is a constant 285 K.",
            "MOON": "Cached array; values reach +-89 deg although the cited Diviner products cover only 60 S-60 N. Source not determined.",
        },
    },
    "rock_or_bare_frac": {
        "label": "Rock or bare-ground fraction", "unit": "fraction", "kind": "numeric",
        "description": "Earth: fraction of bare ground. Moon: rock abundance.",
        "valid": {"EARTH": [0.0, 1.0], "MOON": [0.0, 1.0]},
        "range_source": "definition (0-1)",
        "caveat": {
            "EARTH": "Cached array of undocumented origin (claimed ASTER 1-NDVI); ocean is 0.",
            "MOON": "Cached array; values exist poleward of 60 deg where the cited Diviner product has none.",
        },
    },
    "sar_sigma0_db": {
        "label": "Radar backscatter", "unit": "dB", "kind": "numeric",
        "description": "Radar backscatter coefficient.",
        "valid": {"EARTH": [-35.0, 15.0], "MOON": [-35.0, 15.0]},
        "range_source": "config.py:85 and config.py:95 per the data dictionary; no external source cited",
        "caveat": {
            "EARTH": "Fits -18.29 + 7.97*rock + 0.452*slope with R2 0.99: behaves as a formula, not as radar data.",
            "MOON": "Exactly -19.2 + 45*rock + 0.22*slope: a formula; no lunar radar product is read.",
        },
    },
    "mask_fraction": {
        "label": "Mask fraction", "unit": "fraction", "kind": "numeric",
        "description": "Formula used by the common gate as 'cell with enough data'.",
        "valid": {"EARTH": [0.0, 1.0], "MOON": [0.0, 1.0]},
        "range_source": "definition (0-1)",
        "caveat": {
            "EARTH": "A formula on elevation (0 on ocean), not a data-coverage fraction.",
            "MOON": "Constant 1.0, not a data-coverage fraction.",
        },
    },
    "slope_300m_deg": {
        "label": "Slope (named 300 m baseline)", "unit": "deg", "kind": "numeric",
        "description": "Rover gate and soft variable. Despite the name it is a copy of slope_deg at 2-degree resolution.",
        "valid": {"EARTH": [0.0, 90.0], "MOON": [0.0, 90.0]},
        "range_source": "definition (0-90 degrees)",
        "caveat": {
            "EARTH": "Copy of slope_deg (2-degree cell), not a 300 m baseline slope.",
            "MOON": "Copy of slope_deg (2-degree cell), not a 300 m baseline slope; no LOLA product uses 300 m.",
        },
    },
    "rough_300m_m": {
        "label": "Roughness (named 300 m baseline)", "unit": "m", "kind": "numeric",
        "description": "Rover gate and soft variable. Despite the name it is a copy of roughness_m at 2-degree resolution.",
        "valid": {"EARTH": [0.0, None], "MOON": [0.0, None]},
        "range_source": "definition (>= 0)",
        "caveat": {
            "EARTH": "Copy of roughness_m (2-degree cell), not a 300 m baseline value.",
            "MOON": "Copy of roughness_m (std of 7.6 km pixels in a 2-degree cell), not a 300 m baseline value.",
        },
    },
    "irradiance_kwh_m2_day": {
        "label": "Solar irradiance", "unit": "kWh/m2/day", "kind": "numeric",
        "description": "Daily solar energy on a horizontal surface, from a fitted formula.",
        "valid": {"EARTH": [0.0, None], "MOON": [0.0, None]},
        "range_source": "definition (>= 0)",
        "caveat": {
            "EARTH": "Formula on latitude, bare fraction and elevation; no NASA POWER data was downloaded.",
            "MOON": "The same Earth-style atmospheric formula applied to the airless Moon.",
        },
    },
    "sun_elev_max_deg": {
        "label": "Maximum sun elevation", "unit": "deg", "kind": "numeric",
        "description": "Highest sun elevation over the year, from latitude.",
        "valid": {"EARTH": [0.0, 90.0], "MOON": [0.0, 90.0]},
        "range_source": "definition (0-90 degrees)",
        "caveat": {
            "EARTH": "90 - |lat| + 11.7 deg; the constant is about half Earth's 23.44 deg obliquity.",
            "MOON": "90 - |lat| + 1.54 deg (lunar axis tilt); geometry only, no topographic shading.",
        },
    },
    "sun_low_frac_0_5deg": {
        "label": "Low-sun fraction (0-5 deg)", "unit": "fraction", "kind": "numeric",
        "description": "Share of time with the sun between 0 and 5 degrees, from a fitted formula on latitude.",
        "valid": {"EARTH": [0.0, 1.0], "MOON": [0.0, 1.0]},
        "range_source": "definition (0-1)",
        "caveat": {
            "EARTH": "Invented fit on latitude, identical for both bodies.",
            "MOON": "Invented fit on latitude, identical to Earth; no horizon or polar-ridge illumination.",
        },
    },
    "lst_diurnal_amp_k": {
        "label": "Diurnal temperature amplitude", "unit": "K", "kind": "numeric",
        "description": "Day-night surface temperature swing.",
        "valid": {"EARTH": [0.0, None], "MOON": [0.0, None]},
        "range_source": "definition (>= 0)",
        "caveat": {
            "EARTH": "Formula 8 + 22*bare + 0.0022*elev (land, max 38.75 K), 2.5 K on ocean; not MODIS.",
            "MOON": "Formula 180*cos(lat)^0.35 (63-180 K): latitude only.",
        },
    },
    "thermal_inertia_class": {
        "label": "Thermal inertia class", "unit": "category", "kind": "categorical",
        "description": "Surface class from thresholds on bare fraction, roughness, slope and temperature.",
        "categories": ["suelo", "arena", "regolito", "roca", "hielo", "agua"],
        "range_source": "code categories (harmonizer_cleaner.py:268-274)",
        "caveat": {
            "EARTH": "Thresholds on modelled inputs; no thermal-inertia data is used.",
            "MOON": "Every lunar cell is 'suelo' because lunar rock never reaches the 0.22 threshold.",
        },
    },
    "permafrost_class": {
        "label": "Permafrost class", "unit": "category", "kind": "categorical",
        "description": "Permafrost continuity class from temperature thresholds (Earth) or latitude and temperature (Moon).",
        "categories": ["ninguno", "esporadico", "discontinuo", "continuo"],
        "range_source": "code categories (harmonizer_cleaner.py:276-284)",
        "caveat": {
            "EARTH": "Thresholds on temp_k and elevation; the cited IPA permafrost map was not used.",
            "MOON": "Thresholds on |lat| and temp_k; a label borrowed from Earth, not lunar ice data.",
        },
    },
    "rain_mm_day": {
        "label": "Rain", "unit": "mm/day", "kind": "numeric",
        "description": "Daily rain from a formula (Moon: constant 0).",
        "valid": {"EARTH": [0.0, None], "MOON": [0.0, None]},
        "range_source": "definition (>= 0)",
        "caveat": {
            "EARTH": "Formula on bare fraction and latitude; no source cited.",
            "MOON": "Constant 0 (physically right, but set by code).",
        },
    },
    "wind_max_ms": {
        "label": "Maximum wind", "unit": "m/s", "kind": "numeric",
        "description": "Maximum wind speed from a formula (Moon: constant 0).",
        "valid": {"EARTH": [0.0, None], "MOON": [0.0, None]},
        "range_source": "definition (>= 0)",
        "caveat": {
            "EARTH": "Formula on elevation and latitude; no source cited.",
            "MOON": "Constant 0 (physically right, but set by code).",
        },
    },
    "tmin_c": {
        "label": "Minimum temperature", "unit": "degC", "kind": "numeric",
        "description": "temp_k - 273.15 - 0.35 * diurnal amplitude.",
        "valid": {"EARTH": [-273.15, None], "MOON": [-273.15, None]},
        "range_source": "absolute zero",
        "caveat": {
            "EARTH": "Formula on temp_k and the modelled amplitude; not an observed minimum.",
            "MOON": "Subtracts up to 63 K from a night-time temp_k; not an observed minimum.",
        },
    },
}

LEVELS = ("MEASURED", "DERIVED", "MODELLED", "UNDOCUMENTED")

# Strength order used to cap a DERIVED level at the level of its input: a stated
# formula on an undocumented or modelled value is no better than that value.
LEVEL_STRENGTH = {"MEASURED": 3, "DERIVED": 2, "UNDOCUMENTED": 1, "MODELLED": 0}

# Variable -> the variable it is computed from (A2 section 2a: elevation_rel_m =
# elevation_m - mean; lunar roughness_m = std of LDEM_4 pixels; rough_300m_m copies
# roughness_m). Inputs come earlier in VARIABLES, so their level is already final.
DERIVED_FROM: Dict[str, str] = {
    "elevation_rel_m": "elevation_m",
    "roughness_m": "elevation_m",
    "rough_300m_m": "roughness_m",
}

# Whether a variable is the same physical quantity on both bodies. A variable marked
# False is left out of the Earth-Moon similarity (engine_config similarity_comparability)
# but still counts in suitability. The reason is exported with the variable.
COMPARABILITY: Dict[str, Dict] = {
    "rock_or_bare_frac": {"comparable": False, "reason": "Different quantities: bare-ground fraction on Earth (0-0.98) and rock abundance on the Moon (0.0015-0.046) (A2 section 2a). Their similarity measured how vegetated an Earth cell is."},
    "irradiance_kwh_m2_day": {"comparable": False, "reason": "The lunar value is the Earth atmospheric formula fed with rock abundance where Earth uses bare-ground fraction (A2 sections 2c and 3); it is not a lunar irradiance, and its similarity tracked Earth bare fraction."},
    "thermal_inertia_class": {"comparable": False, "reason": "Classes are thresholds on rock_or_bare_frac, a different quantity on each body; every lunar cell is 'suelo' (A2 section 3)."},
    "permafrost_class": {"comparable": False, "reason": "Permafrost is ground at or below 0 deg C for two years and has no lunar equivalent by definition (R3, ice row and F17); the lunar label is a latitude and temperature threshold."},
    "temp_k": {"comparable": True, "reason": "Same quantity name on both bodies, but Earth is described as a daytime land surface temperature and the Moon as a night-time-like value (A2 section 3), so the comparison mixes times of day. Kept, with this caveat, because the ice and thermal missions have no other temperature."},
    "lst_diurnal_amp_k": {"comparable": True, "reason": "Same quantity on both bodies, but both are MODELLED formulas and the lunar one (latitude only, 63-180 K) is contradicted by Diviner (R2 section 3, R3 F10 and F12)."},
    "tmin_c": {"comparable": True, "reason": "Same formula on both bodies (temp_k - 273.15 - 0.35 * amplitude); it inherits the caveats of temp_k and lst_diurnal_amp_k."},
    "slope_deg": {"comparable": True, "reason": "Same quantity name, but measured over different areas: a 2-degree cell is about 222 km on Earth and 61 km on the Moon, and the methods behind the cached arrays differ or are undocumented (A2 sections 2a and 3). Kept, with this caveat."},
    "roughness_m": {"comparable": True, "reason": "Same quantity name, but measured over different areas: a 2-degree cell is about 222 km on Earth and 61 km on the Moon, and the methods behind the cached arrays differ or are undocumented (A2 sections 2a and 3). Kept, with this caveat."},
    "slope_300m_deg": {"comparable": True, "reason": "Same quantity name, but measured over different areas: a 2-degree cell is about 222 km on Earth and 61 km on the Moon, and the methods behind the cached arrays differ or are undocumented (A2 sections 2a and 3). Kept, with this caveat."},
    "rough_300m_m": {"comparable": True, "reason": "Same quantity name, but measured over different areas: a 2-degree cell is about 222 km on Earth and 61 km on the Moon, and the methods behind the cached arrays differ or are undocumented (A2 sections 2a and 3). Kept, with this caveat."},
}
DEFAULT_COMPARABILITY = {"comparable": True, "reason": "Same physical quantity on both bodies; see each body's level and caveat for how far the values can be trusted."}


def map_level(audit_level: str) -> str:
    """Map the audit's level text to one of the four registry levels."""
    t = str(audit_level).strip().upper()
    if t.startswith("MEASURED"):
        return "MEASURED"
    if t.startswith("DERIVED"):
        return "DERIVED"
    if t.startswith("MODELLED"):
        return "MODELLED"
    if t.startswith("NOT DETERMINED"):
        return "UNDOCUMENTED"
    raise ValueError(f"unknown audit level: {audit_level!r}")


def cell_size_km(radius_km: float, cell_deg: float = 2.0) -> float:
    """North-south size of a cell of ``cell_deg`` degrees on a sphere of ``radius_km``."""
    return 2.0 * math.pi * radius_km * cell_deg / 360.0


def build(dictionary_csv: str) -> Dict:
    """Return the provenance registry as a dict (see module docstring)."""
    ecfg = load_engine_config()
    radii = ecfg.v("body_radius_km")
    dd = pd.read_csv(dictionary_csv)
    out: Dict[str, Dict] = {}
    for var, spec in VARIABLES.items():
        entry = {
            "label": spec["label"], "unit": spec["unit"], "kind": spec["kind"],
            "description": spec["description"], "range_source": spec["range_source"],
            "bodies": {},
        }
        if spec["kind"] == "categorical":
            entry["categories"] = spec["categories"]
        comp = COMPARABILITY.get(var, DEFAULT_COMPARABILITY)
        entry["comparable_across_bodies"] = bool(comp["comparable"])
        entry["comparability_note"] = comp["reason"]
        for body in BODIES:
            rows = dd[(dd["variable"] == var) & (dd["body"] == body)]
            if len(rows) != 1:
                raise KeyError(f"data dictionary has {len(rows)} rows for {var}/{body}")
            r = rows.iloc[0]
            lvl = map_level(r["level"])
            src = DERIVED_FROM.get(var)
            capped_by = None
            if lvl == "DERIVED" and src is not None:
                src_lvl = out[src]["bodies"][body]["level"]
                if LEVEL_STRENGTH[src_lvl] < LEVEL_STRENGTH[lvl]:
                    lvl, capped_by = src_lvl, src
            b: Dict = {
                "level": lvl,
                "audit_level": str(r["level"]),
                "claimed_source": str(r["claimed_source"]),
                "code": str(r["what_code_does_file_line"]),
                "unit_in_dictionary": str(r["unit"]),
                "resolution_km": round(cell_size_km(radii[body]), 1),
                "resolution_note": "2-degree cell (90 x 180 grid); the CSV column resolution_m = 500 is wrong",
                "caveat": spec["caveat"][body],
            }
            if capped_by is not None:
                b["level_note"] = (f"The audit calls this DERIVED, but it is a formula on {capped_by}, whose level on "
                                   f"this body is {lvl}; a derived value cannot be stronger than its input.")
            if spec["kind"] == "numeric":
                lo, hi = spec["valid"][body]
                b["valid_min"] = lo
                b["valid_max"] = hi
            entry["bodies"][body] = b
        out[var] = entry
    return {
        "_note": "Built by engine/build_provenance.py from audit A2_data_dictionary.csv (and A2/A4 notes). Levels come from the audit, never from column names.",
        "levels": {
            "MEASURED": "Verified against a named data product in the repository.",
            "DERIVED": "A stated formula applied to a measured value (or a copy of a derived value). A formula on an UNDOCUMENTED or MODELLED value takes that weaker level.",
            "MODELLED": "A formula or constant invented in code; not data.",
            "UNDOCUMENTED": "A cached array whose product, date and method are not documented (the audit's 'NOT DETERMINED'). It may be real data, but it cannot be presented as measured.",
        },
        "variables": out,
    }


def main(argv: Optional[List[str]] = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--dictionary", required=True, help="path to A2_data_dictionary.csv")
    p.add_argument("--out", default=PROVENANCE_PATH)
    a = p.parse_args(argv)
    reg = build(a.dictionary)
    with open(a.out, "w", encoding="utf-8") as fh:
        json.dump(reg, fh, ensure_ascii=False, indent=1)
        fh.write("\n")
    print(f"wrote {a.out} ({len(reg['variables'])} variables)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
