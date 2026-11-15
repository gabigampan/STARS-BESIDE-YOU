"""Command line. Run from the "tierra luna" directory.

    python -m engine build      [--dataset ID] [--out DIR] [--build-time TEXT] [--input CSV] [--similarity-rule RULE]
    python -m engine validate   [--dataset ID]
    python -m engine report     [--dataset ID] [--benchmark CSV] [--top N] [--out JSON]
    python -m engine datasets
    python -m engine gazetteer  --shp MOON_nomenclature_center_pts.shp [--zip MOON_nomenclature_center_pts.zip]
    python -m engine artemis    --grids <folder of the USGS Artemis III 1 km region grids>

Datasets are defined in engine/datasets.json. The default (real_1deg) writes the v2
bundle the app ships to app/public/data/v2; legacy_2deg writes the v1 JSON bundle to
build/legacy_2deg (not shipped), for before-and-after comparison.
"""
from __future__ import annotations

import argparse
import json
import os
from typing import List, Optional

from engine.config import SIMILARITY_RULES, ENGINE_DIR, dataset_ids, default_dataset, load_datasets, load_engine_config, resolve_path


def _cmd_build(a: argparse.Namespace) -> int:
    from engine.build import build_and_write

    b = build_and_write(out_dir=a.out, dataset=a.dataset, input_csv=a.input, build_time=a.build_time,
                        similarity_rule=a.similarity_rule)
    m = b["manifest"]
    print(f"dataset {b['engine_cfg'].dataset_id}: bundle {m['bundle_version']} -> {b['out_dir']}")
    total = 0
    for f in m["files"]:
        total += f["bytes"]
        print(f"  {f['name']:26s} {f['bytes']:>10,d} B  {f['sha256'][:12]}  {f.get('load', '')}")
    total += len(b["files"]["manifest.json"])
    print(f"  manifest.json              {len(b['files']['manifest.json']):>10,d} B")
    print(f"  total {total:,d} B")
    if "sizes" in m:
        fv = m["sizes"]["first_view_bytes_without_manifest"] + len(b["files"]["manifest.json"])
        print(f"  first view (with manifest) {fv:,d} B; budget {m['sizes']['budget']}")
    for mid, c in m["counts"]["missions"].items():
        print(f"  {mid:8s} pass EARTH {c['pass_EARTH']:6d}  MOON {c['pass_MOON']:6d}  ranked {c['ranked_EARTH']:6d}")
    print(f"  validity: {'OK' if b['validity']['valid'] else 'FAILURES (see validity.json)'}")
    return 0


def _cmd_validate(a: argparse.Namespace) -> int:
    from engine import schema
    from engine.dataset import load_dataset

    ecfg = load_engine_config(dataset=a.dataset)
    ds = load_dataset(ecfg)
    rep = schema.validate_table(ds.cells, ds.reg, float(ecfg.v("coordinate_tolerance_deg")), ds.grid)
    for b, r in rep["bodies"].items():
        print(f"{b}: {r['records']} records, {r['failing_records']} failing, fields {r['field_failures']}")
    return 0 if rep["valid"] else 1


def _cmd_report(a: argparse.Namespace) -> int:
    from engine.build import compute
    from engine.report import run_report

    c = compute(a.dataset)
    rep = run_report(c, a.benchmark, a.top)
    text = json.dumps(rep, ensure_ascii=False, indent=1)
    if a.out:
        with open(a.out, "w", encoding="utf-8") as fh:
            fh.write(text + "\n")
        print(f"report -> {a.out}")
    else:
        print(text)
    return 0


def _cmd_datasets(a: argparse.Namespace) -> int:
    d = load_datasets()
    for k, v in d["datasets"].items():
        mark = " (default)" if k == d["default_dataset"]["value"] else ""
        print(f"{k}{mark}: {v['title']}")
    return 0


def _cmd_gazetteer(a: argparse.Namespace) -> int:
    from engine.places import extract_gazetteer, write_gazetteer_source

    ecfg = load_engine_config()
    out_csv = resolve_path(ecfg.v("lunar_gazetteer_csv"))
    n = extract_gazetteer(a.shp, out_csv)
    write_gazetteer_source(os.path.join(ENGINE_DIR, "data", "iau_source.json"), a.shp, a.zip, n)
    print(f"wrote {out_csv} ({n} features)")
    return 0


def _cmd_artemis(a: argparse.Namespace) -> int:
    from engine.artemis import write_regions

    ecfg = load_engine_config()
    out = resolve_path(ecfg.v("similarity_zones")["lunar_base"]["regions_file"])
    n = write_regions(a.grids, out)
    print(f"wrote {out} ({n} regions)")
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    p = argparse.ArgumentParser(prog="python -m engine", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    ids = dataset_ids()
    dflt = default_dataset()
    b = sub.add_parser("build", help="compute everything and write the static bundle")
    b.add_argument("--dataset", choices=ids, default=dflt)
    b.add_argument("--input", default=None, help="replace a one-file dataset's input CSV")
    b.add_argument("--out", default=None, help="output folder (default: the dataset's output_dir)")
    b.add_argument("--build-time", default=None, help="text stored as build_time (default: input sha256)")
    b.add_argument("--similarity-rule", default=None, choices=SIMILARITY_RULES,
                   help="override engine_config similarity_rule for this build only (e.g. a zone_twin preview to --out)")
    v = sub.add_parser("validate", help="validate the dataset's cell tables against the schema")
    v.add_argument("--dataset", choices=ids, default=dflt)
    r = sub.add_parser("report", help="counts, failure reasons, distributions, top cells and benchmark sites")
    r.add_argument("--dataset", choices=ids, default=dflt)
    r.add_argument("--benchmark", default=None, help="CSV of analog sites (id, name, lat, lon, ...)")
    r.add_argument("--top", type=int, default=15)
    r.add_argument("--out", default=None)
    sub.add_parser("datasets", help="list the dataset descriptors")
    g = sub.add_parser("gazetteer", help="extract the IAU lunar gazetteer to engine/data")
    g.add_argument("--shp", required=True)
    g.add_argument("--zip", default=None)
    ar = sub.add_parser("artemis", help="convert the USGS Artemis III region grids to engine/data GeoJSON")
    ar.add_argument("--grids", required=True, help="folder with one sub-folder per region holding *_1km_S_Grid.shp")
    a = p.parse_args(argv)
    return {"build": _cmd_build, "validate": _cmd_validate, "report": _cmd_report, "datasets": _cmd_datasets,
            "gazetteer": _cmd_gazetteer, "artemis": _cmd_artemis}[a.cmd](a)
