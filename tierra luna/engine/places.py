"""Computed place names (no hand-made labels).

Earth: for every land cell,
* country: the Natural Earth 1:110m admin-0 polygon that contains the cell centre
  (label_rule "natural_earth_polygon"); when that polygon has no ISO code (France and
  Norway in NE 110m) the name comes from the polygon and the code is the polygon's
  commonest GeoNames country code (one code per polygon; "natural_earth_polygon_geonames_code"); a centre outside every polygon (coasts and
  small islands at 110m) falls back to the nearest populated place in GeoNames
  cities1000 (offline, reverse_geocoder; label_rule "nearest_geonames_place");
* country name: the ISO 3166 table of the IANA time zone database (tzdata), or the
  polygon's own ADMIN name when the code is missing or not in that table;
* region: the nearest GeoNames place's first-level region, only when that place is
  in the same country and within engine_config region_max_place_km; else null;
* cells at or south of the configured latitude (Antarctic Treaty area) are labelled
  Antarctica (label_rule "antarctic_treaty_area").
A 222 km cell can span several countries: the label is that of the cell centre.

Moon: for every cell, the nearest IAU-named feature (great-circle distance on the
1737.4 km sphere) from an offline extract of the USGS/IAU Gazetteer of Planetary
Nomenclature. The gazetteer uses longitudes 0-360 positive east; they are converted
to -180..180 (lon - 360 when lon > 180) to match the grid.
"""
from __future__ import annotations

import csv
import importlib.resources
import json
import math
import os
from typing import Dict, List, Optional

import numpy as np
import pandas as pd
from scipy.spatial import cKDTree

GAZETTEER_COLUMNS = ["name", "type", "code", "diameter_km", "center_lat", "center_lon_e360", "approval", "link"]


# ----------------------------------------------------------------------------- shared
def to_unit_vectors(lat_deg: np.ndarray, lon_deg: np.ndarray) -> np.ndarray:
    """Points on the unit sphere (for nearest-neighbour search by chord distance)."""
    la = np.radians(np.asarray(lat_deg, dtype=np.float64))
    lo = np.radians(np.asarray(lon_deg, dtype=np.float64))
    return np.column_stack([np.cos(la) * np.cos(lo), np.cos(la) * np.sin(lo), np.sin(la)])


def great_circle_km(lat1, lon1, lat2, lon2, radius_km: float) -> np.ndarray:
    """Haversine distance in km."""
    p1, p2 = np.radians(lat1), np.radians(lat2)
    dp = p2 - p1
    dl = np.radians(np.asarray(lon2) - np.asarray(lon1))
    a = np.sin(dp / 2) ** 2 + np.cos(p1) * np.cos(p2) * np.sin(dl / 2) ** 2
    return 2.0 * radius_km * np.arcsin(np.sqrt(np.clip(a, 0.0, 1.0)))


def lon_east360_to_180(lon: np.ndarray) -> np.ndarray:
    """0..360 positive-east longitude to -180..180 positive-east."""
    lon = np.asarray(lon, dtype=np.float64)
    return np.where(lon > 180.0, lon - 360.0, lon)


# ----------------------------------------------------------------------------- Moon
def extract_gazetteer(shp_path: str, out_csv: str) -> int:
    """Write the offline CSV extract of the IAU lunar gazetteer shapefile. Returns rows."""
    import geopandas as gpd  # only needed for this one-off extraction

    g = gpd.read_file(shp_path)
    df = pd.DataFrame({
        "name": g["clean_name"].astype(str),
        "type": g["type"].astype(str),
        "code": g["code"].astype(str),
        "diameter_km": pd.to_numeric(g["diameter"], errors="coerce"),
        "center_lat": pd.to_numeric(g["center_lat"], errors="coerce"),
        "center_lon_e360": pd.to_numeric(g["center_lon"], errors="coerce"),
        "approval": g["approval"].astype(str),
        "link": g["link"].astype(str),
    })
    df = df.sort_values(["name", "center_lat", "center_lon_e360"], kind="mergesort").reset_index(drop=True)
    os.makedirs(os.path.dirname(out_csv), exist_ok=True)
    df.to_csv(out_csv, index=False, quoting=csv.QUOTE_MINIMAL, lineterminator="\n")
    return len(df)


def load_lunar_features(csv_path: str, exclude_types: List[str]) -> pd.DataFrame:
    """Gazetteer features with lon converted to -180..180, excluded types removed,
    sorted by name then position (stable ids for ties)."""
    df = pd.read_csv(csv_path)
    df = df[~df["type"].isin(exclude_types)].copy()
    df = df[np.isfinite(df["center_lat"]) & np.isfinite(df["center_lon_e360"])]
    df["lon"] = lon_east360_to_180(df["center_lon_e360"].to_numpy())
    df["lat"] = df["center_lat"].astype(float)
    df = df.sort_values(["name", "lat", "lon"], kind="mergesort").reset_index(drop=True)
    return df


def nearest_lunar_feature(lat: np.ndarray, lon: np.ndarray, features: pd.DataFrame,
                          radius_km: float) -> Dict[str, list]:
    """Nearest named feature to each point: name, type, diameter_km, distance_km."""
    tree = cKDTree(to_unit_vectors(features["lat"].to_numpy(), features["lon"].to_numpy()))
    _, idx = tree.query(to_unit_vectors(lat, lon), k=1)
    f = features.iloc[idx]
    dist = great_circle_km(np.asarray(lat), np.asarray(lon), f["lat"].to_numpy(), f["lon"].to_numpy(), radius_km)
    return {
        "index": [int(i) for i in np.asarray(idx).reshape(-1)],
        "name": f["name"].tolist(),
        "type": f["type"].tolist(),
        "diameter_km": [None if not np.isfinite(d) else float(d) for d in f["diameter_km"].to_numpy(dtype=float)],
        "distance_km": dist.tolist(),
    }


# ----------------------------------------------------------------------------- Earth
def iso3166_names() -> Dict[str, str]:
    """ISO 3166 alpha-2 -> English short name from the IANA tz table iso3166.tab."""
    text: Optional[str] = None
    try:
        text = importlib.resources.files("tzdata").joinpath("zoneinfo/iso3166.tab").read_text(encoding="utf-8")
    except (ModuleNotFoundError, FileNotFoundError):
        for p in ("/usr/share/zoneinfo/iso3166.tab",):
            if os.path.exists(p):
                text = open(p, encoding="utf-8").read()
    names: Dict[str, str] = {}
    for line in (text or "").splitlines():
        if not line or line.startswith("#"):
            continue
        parts = line.split("\t")
        if len(parts) >= 2:
            names[parts[0].strip()] = parts[1].strip()
    return names


def load_country_polygons(geojson_path: str) -> List[Dict]:
    """Natural Earth admin-0 polygons: [{"code": ISO_A2 or None, "name": ADMIN, "geom": shapely}]
    in file order (the order breaks ties deterministically)."""
    from shapely.geometry import shape

    with open(geojson_path, encoding="utf-8") as fh:
        gj = json.load(fh)
    out = []
    for f in gj["features"]:
        p = f["properties"]
        code = str(p.get("ISO_A2") or "").strip()
        out.append({"code": code if len(code) == 2 and code.isalpha() else None,
                    "name": p.get("ADMIN"), "geom": shape(f["geometry"])})
    return out


def polygon_country(lat: np.ndarray, lon: np.ndarray, polygons: List[Dict]) -> List[Optional[int]]:
    """Index of the first polygon (file order) that contains each point, or None."""
    from shapely import STRtree, points

    geoms = [p["geom"] for p in polygons]
    tree = STRtree(geoms)
    pts = points(np.asarray(lon, dtype=np.float64), np.asarray(lat, dtype=np.float64))
    pt_idx, poly_idx = tree.query(pts, predicate="within")
    best: Dict[int, int] = {}
    for a, b in zip(pt_idx.tolist(), poly_idx.tolist()):
        best[a] = min(b, best.get(a, b))
    return [best.get(i) for i in range(len(pts))]


def polygon_codes_from_places(poly_of: List[Optional[int]], place_codes: List[Optional[str]],
                              polygons: List[Dict]) -> Dict[int, str]:
    """{polygon index: code} for polygons without an ISO code: the commonest GeoNames
    country code of the nearest places of the cells inside the polygon (ties: the
    alphabetically first code). One code per polygon, so its name and code agree on
    every cell (NE 110m France and Norway have no ISO_A2)."""
    counts: Dict[int, Dict[str, int]] = {}
    for pk, cc in zip(poly_of, place_codes):
        if pk is None or polygons[pk]["code"] or not cc:
            continue
        counts.setdefault(pk, {})
        counts[pk][cc] = counts[pk].get(cc, 0) + 1
    return {pk: sorted(c.items(), key=lambda kv: (-kv[1], kv[0]))[0][0] for pk, c in counts.items()}


def earth_places(lat: np.ndarray, lon: np.ndarray, land: np.ndarray, antarctic_lat_max: float,
                 radius_km: float, polygons: Optional[List[Dict]] = None,
                 region_max_place_km: Optional[float] = None) -> Dict[str, list]:
    """Country code, country name, first-level region, nearest place and its distance
    for each Earth cell; null for non-land cells (rules in the module docstring)."""
    import reverse_geocoder as rg

    n = len(lat)
    out: Dict[str, list] = {k: [None] * n for k in
                            ("country_code", "country", "region", "nearest_place", "nearest_place_km", "label_rule")}
    names = iso3166_names()
    land_idx = np.flatnonzero(np.asarray(land, dtype=bool))
    if land_idx.size == 0:
        return out
    pts = [(float(lat[i]), float(lon[i])) for i in land_idx]
    hits = rg.search(pts, mode=1, verbose=False)  # single process: deterministic
    poly_of = polygon_country(np.asarray(lat)[land_idx], np.asarray(lon)[land_idx], polygons) if polygons else \
        [None] * len(land_idx)
    poly_code = polygon_codes_from_places(poly_of, [h["cc"] for h in hits], polygons) if polygons else {}
    for k, (i, h) in enumerate(zip(land_idx, hits)):
        d = float(great_circle_km(lat[i], lon[i], float(h["lat"]), float(h["lon"]), radius_km))
        out["nearest_place"][i] = h["name"]
        out["nearest_place_km"][i] = d
        if lat[i] <= antarctic_lat_max:
            out["country_code"][i] = "AQ"
            out["country"][i] = names.get("AQ", "Antarctica")
            out["region"][i] = None
            out["label_rule"][i] = "antarctic_treaty_area"
            continue
        pk = poly_of[k]
        if pk is not None and polygons[pk]["code"]:
            cc = polygons[pk]["code"]
            out["country_code"][i] = cc
            out["country"][i] = names.get(cc) or polygons[pk]["name"]
            out["label_rule"][i] = "natural_earth_polygon"
        elif pk is not None:  # polygon without an ISO code (e.g. France, Norway in NE 110m)
            # one code for the whole polygon (its commonest GeoNames code), so a French
            # cell whose nearest place is in Andorra is not labelled 'AD France'
            cc = poly_code.get(pk, h["cc"])
            out["country_code"][i] = cc
            out["country"][i] = polygons[pk]["name"]
            out["label_rule"][i] = "natural_earth_polygon_geonames_code"
        else:
            cc = h["cc"]
            out["country_code"][i] = cc
            out["country"][i] = names.get(cc)
            out["label_rule"][i] = "nearest_geonames_place"
        same_country = cc is not None and h["cc"] == cc
        near = region_max_place_km is None or d <= region_max_place_km
        out["region"][i] = (h["admin1"] or None) if (same_country and near) else None
    return out


def write_gazetteer_source(out_json: str, shp_path: str, zip_path: Optional[str], rows: int) -> None:
    """Record where the gazetteer extract came from."""
    from engine.config import sha256_file

    info = {
        "product": "USGS/IAU Gazetteer of Planetary Nomenclature, MOON_nomenclature_center_pts",
        "url": "https://asc-planetarynames-data.s3.us-west-2.amazonaws.com/MOON_nomenclature_center_pts.zip",
        "downloaded": "2026-11-14 (during the audit; Last-Modified 14 Nov 2026 per R4)",
        "zip_sha256": sha256_file(zip_path) if zip_path and os.path.exists(zip_path) else None,
        "shapefile": os.path.basename(shp_path),
        "rows": rows,
        "longitude_convention": "0-360 positive east in the source; converted to -180..180 by the engine",
        "sphere_radius_m": 1737400,
        "credit": "Gazetteer of Planetary Nomenclature, IAU WGPSN and USGS Astrogeology Science Center",
    }
    with open(out_json, "w", encoding="utf-8") as fh:
        json.dump(info, fh, indent=1)
        fh.write("\n")


def cell_size_km(radius_km: float, cell_deg: float) -> float:
    """North-south size of a cell (2*pi*R*deg/360)."""
    return 2.0 * math.pi * radius_km * cell_deg / 360.0
