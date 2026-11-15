"""Point 2 (grid): true cell sizes on both bodies at the latitudes of the 15 audio pairs, the
physical baselines of slope and roughness, and every statement of cell size / resolution in the
web, the bundle and the documents (grep, file and line).

    <venv>/bin/python "tierra luna/audit/p1_grid.py"

Deterministic. Writes out/p1_grid_sizes.csv, out/p1_grid_statements.csv, out/p1_grid.json.
Sizes: sphere of the stated radius (Earth 6371.0 km as the bundle, also the WGS84 meridian arc of
the table's cell_km; Moon 1737.4 km), N-S = 2 pi R / 360, E-W at the cell centre = N-S cos(lat),
area = R^2 * dlon * (sin(lat_n) - sin(lat_s)).
"""
from __future__ import annotations

import json
import math
import os
import re
import sys

import numpy as np
import pandas as pd

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import p1_common as C  # noqa: E402

PATTERNS = [
    r"\b1(?:\.0)?[- ]?(?:degree|deg)\b", r"1\s?°", r"one[- ]degree", r"2[- ]degree",
    r"\b(?:110|111|111\.\d+|110\.\d+|30|30\.3\d*|222|222\.4|83|83\.\d|55|55\.6|7\.1|7\.07|1\.3\d?)\s?(?:km|kilomet)",
    r"\bresolution\b", r"cell[ _]size", r"cell_ns_km|cell_ew_km|cell_km", r"km (?:wide|across|square|on a side)",
    r"\bresoluci[oó]n\b", r"tama[nñ]o de (?:la )?celda", r"\bceldas? de \d",
]
RX = re.compile("|".join(f"(?:{p})" for p in PATTERNS), re.I)
SCAN = [("app/src", (".ts", ".js", ".css", ".html", ".json")), ("app/index.html", None),
        ("app/public/audio/transcripts.json", None), ("app/public/data/v2", (".json",)),
        ("docs", (".md", ".json", ".csv")), ("ASSUMPTIONS.md", None), ("README.md", None),
        ("app/README.md", None), ("tierra luna/engine", (".json", ".py")),
        ("tierra luna/tools/make_audio_top5.py", None), ("tierra luna/real_data", (".md", ".json", ".csv"))]
SKIP = ("docs/stats_audit", "node_modules", "/dist/", "audit_evidence")


def files():
    for path, exts in SCAN:
        p = os.path.join(C.REPO, path)
        if os.path.isfile(p):
            yield p
            continue
        for root, _, fs in os.walk(p):
            if any(s in root for s in SKIP):
                continue
            for f in sorted(fs):
                if exts is None or f.endswith(exts):
                    yield os.path.join(root, f)


def statements():
    rows = []
    for p in files():
        rel = os.path.relpath(p, C.REPO)
        try:
            text = open(p, encoding="utf-8").read()
        except Exception:
            continue
        for ln, line in enumerate(text.splitlines(), 1):
            for mt in RX.finditer(line):
                a, z = max(0, mt.start() - 110), min(len(line), mt.end() + 110)
                rows.append({"file": rel, "line": ln, "col": mt.start() + 1, "match": mt.group(0),
                             "context": line[a:z].replace("\n", " ")})
    return pd.DataFrame(rows)


def sizes():
    top = C.jload(os.path.join(C.REPO, "docs", "AUDIO_TOP5.json"))
    e = pd.read_csv(C.EARTH_CSV, usecols=["cell_id", "lat_deg", "cell_km"])
    out = []
    for mi, blk in top["missions"].items():
        for p in blk["pairs"]:
            for body, cid, R in (("EARTH", int(p["earth_cell_id"][1:]), C.R_EARTH_KM),
                                 ("MOON", int(p["moon_cell_id"][1:]), C.R_MOON_KM)):
                lat, _ = C.cell_centre(cid)
                lat = float(lat)
                ns = 2 * math.pi * R / 360.0
                ew = ns * math.cos(math.radians(lat))
                area = R * R * math.radians(1.0) * (math.sin(math.radians(lat + 0.5)) - math.sin(math.radians(lat - 0.5)))
                out.append({"mission": mi, "rank": p["rank"], "body": body, "cell": f"{body[0]}{cid}", "lat": lat,
                            "ns_km": ns, "ew_km": ew, "area_km2": area,
                            "table_cell_km": float(e.iloc[cid]["cell_km"]) if body == "EARTH" else 30.323})
    df = pd.DataFrame(out)
    piv = df.pivot_table(index=["mission", "rank"], columns="body", values=["ew_km", "area_km2", "lat"])
    piv.columns = [f"{a}_{b}" for a, b in piv.columns]
    piv["area_ratio_earth_over_moon"] = piv["area_km2_EARTH"] / piv["area_km2_MOON"]
    piv["ew_ratio"] = piv["ew_km_EARTH"] / piv["ew_km_MOON"]
    return df, piv.reset_index()


def main():
    df, piv = sizes()
    df.to_csv(os.path.join(C.OUT, "p1_grid_sizes.csv"), index=False, float_format="%.3f")
    st = statements()
    st.to_csv(os.path.join(C.OUT, "p1_grid_statements.csv"), index=False)
    dy_e = 6371.0088 * math.radians(1 / 60)
    dy_m = 1737.4 * math.radians(1 / 16)
    res = {
        "ns_km": {"EARTH_sphere_6371": 2 * math.pi * 6371.0 / 360, "MOON_sphere_1737.4": 2 * math.pi * 1737.4 / 360},
        "baselines_km": {"EARTH_pixel_dy": dy_e, "EARTH_slope_iso_baseline": 2 * dy_e, "EARTH_roughness_lag": dy_e,
                         "MOON_pixel_dy": dy_m, "MOON_slope_iso_baseline": 2 * dy_m, "MOON_roughness_lag": dy_m,
                         "ratio_moon_over_earth": dy_m / dy_e},
        "pixels_per_cell": {"EARTH": 60 * 60, "MOON": 16 * 16},
        "pairs": piv.round(3).to_dict("records"),
        "area_ratio_range": [float(piv["area_ratio_earth_over_moon"].min()), float(piv["area_ratio_earth_over_moon"].max())],
        "statements_found": int(len(st)),
        "statements_by_file": st.groupby("file").size().to_dict(),
    }
    C.write_json("p1_grid.json", res)
    pd.set_option("display.width", 250)
    print(piv.round(2).to_string())
    print(json.dumps({k: v for k, v in res.items() if k != "pairs"}, indent=1, default=C._default))


if __name__ == "__main__":
    main()
