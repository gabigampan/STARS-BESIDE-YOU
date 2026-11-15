"""Artemis III candidate landing regions: from the USGS navigational grids to GeoJSON.

Source: McClernan, M.T., 2024, Down Selected Artemis III Candidate Landing Site
Navigational Grids, U.S. Geological Survey data release, doi 10.5066/P1MEQ6UK
(CC0). NASA announced the nine regions on 2024-10-28 (release 24-136). The exact
outline file listed on the item is not published (HTTP 403, docs/SIMILARITY_PROPOSAL.md),
so each region's footprint is the union of its 1 km grid squares, an upper bound of the
region (the proposal agent verified the grids: projection, units, centres against the
IAU gazetteer).

    python -m engine artemis --grids <dir with one folder per region holding *_1km_S_Grid.shp>

writes engine/data/artemis_iii_regions.geojson: one Polygon per region in
planetocentric degrees (IAU_2015:30100, longitude -180..180 east-positive), with the
source DOI, the licence, the sha256 of every shapefile read and ``"verified": true``.
The engine then selects the lunar cells whose 1-degree (or 2-degree) square intersects
a region (engine/similarity_context.py). Deterministic.
"""
from __future__ import annotations

import glob
import hashlib
import json
import os
from typing import Dict, List

SOURCE = {
    "title": "Down Selected Artemis III Candidate Landing Site Navigational Grids",
    "originator": "McClernan, M.T. (USGS Astrogeology Science Center)",
    "doi": "10.5066/P1MEQ6UK",
    "licence": "CC0 1.0 (Creative Commons Zero v1.0 Universal)",
    "nasa_announcement": "NASA release 24-136, 2024-10-28: nine candidate Artemis III landing regions near the lunar south pole",
    "footprint_rule": "union of each region's 1 km grid squares (the exact outline file is not published), so a footprint is an upper bound of the region",
}
GEOGRAPHIC_CRS = "IAU_2015:30100"


def _sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def regions_geojson(grids_dir: str, decimals: int = 6) -> Dict:
    """Read every '<region>/*_1km_S_Grid.shp' and return the GeoJSON object."""
    import geopandas as gpd
    import pyproj
    from shapely.geometry import mapping
    from shapely.ops import transform, unary_union

    geo = pyproj.CRS(GEOGRAPHIC_CRS)
    feats: List[Dict] = []
    files = []
    for shp in sorted(glob.glob(os.path.join(grids_dir, "*", "*_1km_S_Grid.shp"))):
        name = os.path.basename(os.path.dirname(shp))
        crs = pyproj.CRS.from_wkt(open(shp[:-4] + ".prj", encoding="utf-8").read())
        g = gpd.read_file(shp, engine="pyogrio").set_crs(crs, allow_override=True)
        reg = unary_union(g.geometry.buffer(0))
        tr = pyproj.Transformer.from_crs(crs, geo, always_xy=True)
        ll = transform(lambda x, y, z=None: tr.transform(x, y), reg)
        if ll.geom_type != "Polygon":
            raise ValueError(f"{name}: footprint is not one polygon")
        lons = [p[0] for p in ll.exterior.coords]
        if max(lons) - min(lons) > 180:
            raise ValueError(f"{name}: footprint crosses the antimeridian; split it before use")
        geom = json.loads(json.dumps(mapping(ll)))
        geom["coordinates"] = [[[round(x, decimals), round(y, decimals)] for x, y in ring] for ring in geom["coordinates"]]
        feats.append({"type": "Feature",
                      "properties": {"name": name.replace("_", " "), "grid_squares_1km": int(len(g)),
                                     "projected_crs": crs.name},
                      "geometry": geom})
        for ext in (".shp", ".shx", ".dbf", ".prj"):
            files.append({"file": os.path.basename(shp[:-4] + ext), "sha256": _sha256(shp[:-4] + ext)})
    if len(feats) != 9:
        raise ValueError(f"expected the nine NASA regions, found {len(feats)}")
    return {"type": "FeatureCollection", "verified": True, "crs_note": f"{GEOGRAPHIC_CRS}: planetocentric degrees, longitude -180..180 east-positive",
            "source": SOURCE, "files_read": files, "features": feats}


def write_regions(grids_dir: str, out_path: str) -> int:
    obj = regions_geojson(grids_dir)
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(obj, fh, ensure_ascii=False, separators=(",", ":"), sort_keys=False)
        fh.write("\n")
    return len(obj["features"])
