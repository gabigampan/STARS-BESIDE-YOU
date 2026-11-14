"""Command line.

    python -m engine build      [--input CSV] [--out DIR] [--build-time TEXT]
    python -m engine validate   [--input CSV]
    python -m engine gazetteer  --shp MOON_nomenclature_center_pts.shp [--zip MOON_nomenclature_center_pts.zip]

Run from the "tierra luna" directory.
"""
from __future__ import annotations

import argparse
import json
import os
from typing import List, Optional

from engine.config import ENGINE_DIR, load_engine_config, resolve_path


def _cmd_build(a: argparse.Namespace) -> int:
    from engine.build import build_and_write

    b = build_and_write(out_dir=a.out, input_csv=a.input, build_time=a.build_time)
    m = b["manifest"]
    print(f"bundle {m['bundle_version']} -> {b['out_dir']}")
    for f in m["files"]:
        print(f"  {f['name']:24s} {f['bytes']:>10,d} B  {f['sha256'][:12]}")
    total = sum(f["bytes"] for f in m["files"]) + len(b["files"]["manifest.json"])
    print(f"  total {total:,d} B")
    for mid, c in m["counts"]["missions"].items():
        print(f"  {mid:8s} pass EARTH {c['pass_EARTH']:5d}  MOON {c['pass_MOON']:5d}  ranked {c['ranked_EARTH']:5d}")
    print(f"  validity: {'OK' if b['objects']['validity.json']['valid'] else 'FAILURES (see validity.json)'}")
    return 0


def _cmd_validate(a: argparse.Namespace) -> int:
    from engine import provenance, schema
    from engine.table import load_cells

    ecfg = load_engine_config()
    cells = load_cells(a.input or resolve_path(ecfg.v("input_csv")))
    rep = schema.validate_table(cells, provenance.load_registry())
    for b, r in rep["bodies"].items():
        print(f"{b}: {r['records']} records, {r['failing_records']} failing, fields {r['field_failures']}")
    return 0 if rep["valid"] else 1


def _cmd_gazetteer(a: argparse.Namespace) -> int:
    from engine.places import extract_gazetteer, write_gazetteer_source

    ecfg = load_engine_config()
    out_csv = resolve_path(ecfg.v("lunar_gazetteer_csv"))
    n = extract_gazetteer(a.shp, out_csv)
    write_gazetteer_source(os.path.join(ENGINE_DIR, "data", "iau_source.json"), a.shp, a.zip, n)
    print(f"wrote {out_csv} ({n} features)")
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    p = argparse.ArgumentParser(prog="python -m engine", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build", help="compute everything and write the static bundle")
    b.add_argument("--input", default=None)
    b.add_argument("--out", default=None)
    b.add_argument("--build-time", default=None, help="text stored as build_time (default: input sha256)")
    v = sub.add_parser("validate", help="validate the cell table against the schema")
    v.add_argument("--input", default=None)
    g = sub.add_parser("gazetteer", help="extract the IAU lunar gazetteer to engine/data")
    g.add_argument("--shp", required=True)
    g.add_argument("--zip", default=None)
    a = p.parse_args(argv)
    return {"build": _cmd_build, "validate": _cmd_validate, "gazetteer": _cmd_gazetteer}[a.cmd](a)
