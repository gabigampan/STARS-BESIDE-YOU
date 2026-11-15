"""Point 9 (document side): every statement of the listed documents about the shared facts,
with file and line, against the shipped bundle read with the auditor's own reader.

Run:  <venv python> "tierra luna/audit/p4_docs_coherence.py"
Writes (deterministic, sorted):
  tierra luna/audit/out/p4_docs_hits.csv        every matching line: fact, file, line, marked_superseded, text
  tierra luna/audit/out/p4_docs_summary.json    truth from the bundle + hit counts + unmarked leftovers
Reads only; never writes outside tierra luna/audit/out/. Does not import the engine.
"""
from __future__ import annotations

import csv
import glob
import json
import os
import re
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from p4_common import OUT, REPO, Bundle, load_tables  # noqa: E402

DOCS = [
    "docs/DECISIONS.md", "ASSUMPTIONS.md", "docs/DATA_CONTRACT.md", "docs/ANALOG_PRINCIPLE.md",
    "docs/LUNAR_BASE_PROPOSAL.md", "docs/MISSION_ZONES.md", "tierra luna/engine/mission_zone_texts.json",
    "docs/AUDIO_TOP5.json", "app/public/audio/transcripts.json",
]
BUNDLE_TEXTS = ["missions.json", "similarity.json", "variables.json", "explain.json", "mission_zones.json"]

# Fact patterns. Each is (fact id, regex). Case-insensitive.
FACTS = [
    # counts
    ("count.rover.passing", r"\b10[,. ]?337\b"), ("count.rover.paired", r"\b10[,. ]?192\b"),
    ("count.rover.unpaired", r"\b145\b(?=[^0-9]{0,40}(unpaired|without|no twin|sin (gemelo|par)))"),
    ("count.rover.twins", r"\b401\b"),
    ("count.solar.passing", r"\b18[,. ]?777\b"), ("count.solar.paired", r"\b6[,. ]?360\b"),
    ("count.solar.unpaired", r"\b12[,. ]?417\b"), ("count.solar.twins", r"\b1[,. ]?704\b"),
    ("count.base.passing", r"\b2[,. ]?419\b"), ("count.base.paired", r"\b450\b"),
    ("count.base.unpaired", r"\b1[,. ]?969\b"), ("count.base.twins", r"\b103\b"),
    ("count.base.zone280", r"\b280\b"),
    # stale counts seen in earlier methods (any 4-5 digit count next to the mission words is listed by fact 'count.other')
    # number 1 pairs
    ("top1.rover", r"Bayinbaolige|E17566|\b17566\b"), ("top1.solar", r"Huxley|E38464|\b38464\b"),
    ("top1.base", r"Aheqi|Mons Malapert|E17538|\b17538\b"),
    ("top1.rover.moon", r"Casatus"),
    # method
    ("weights.rover", r"slope[^.\n]{0,40}40 ?%|40 ?%[^.\n]{0,40}slope|pendiente[^.\n]{0,30}40"),
    ("tol.rover.slope", r"2 ?(deg|degrees|°|grados)\b[^.\n]{0,30}(toler|slope|pendiente)|toleran[^.\n]{0,40}\b2 ?(deg|°)"),
    ("tol.rover.rough", r"\b30 ?m\b"), ("tol.rover.erel", r"\b500 ?m\b"),
    ("tol.solar.irr", r"\b0[.,]6 ?kWh"), ("weights.solar", r"\b80 ?%"),
    ("tol.base.pct", r"10 percentile|10 puntos|10 points|10 pp\b|tolerance 10\b"),
    ("bounds.base", r"\b4 ?(deg|°|grados)\b|\b60 ?m\b"),
    ("zone.rover", r"75 ?(°|deg|degrees|grados)? ?S\b|lat(itude)? ?<= ?-75|75S"),
    ("zone.solar", r"-1[,.]?200 ?m|1[,.]200 m|30 ?(°|deg|degrees|grados)[^.\n]{0,40}(equator|ecuador)"),
    ("zone.solar.old", r"solar[^.\n]{0,80}(south pole|polo sur|coldest part of the Moon|polar zone)"),
    ("rule.real_value", r"real_value_tolerance"), ("rule.base", r"percentile_and_real_tolerance"),
    ("rule.old.zone_twin", r"zone_twin"), ("rule.old.zscore", r"z-?scores?|zscore|puntuaci[oó]n z"),
    ("rule.old.pooled", r"pooled_percentile_range|pooled (robust )?(physical )?range|max\(0, ?1 ?- ?\|"),
    ("final.mix", r"0[.,]5 ?(x|×|\*) ?(similarity|similitud)|alpha 0[.,]5|half similarity|mitad similitud"),
    ("cell.size", r"1[- ]degree|1 ?°|1-deg|1 grado|un grado|1deg"),
    ("cell.size.other", r"\b(2|0[.,]5|0[.,]25)[- ]degree|\b2 ?° cell|2-degree cell|celda de 2"),
    ("levels", r"MEASURED|DERIVED|MODELLED|ASSUMED|MEDIDO|DERIVADO|MODELADO"),
    ("artemis.III", r"Artemis III"), ("artemis.IV", r"Artemis IV"),
    ("similarity.meaning", r"similarity (means|is|=)|similitud (significa|es|=)"),
]
MARK = re.compile(r"supersed|earlier|replaced|former|histor|no longer|retired|withdrawn|obsolete|previous|old rule|"
                  r"was replaced|until|anterior|antes|sustitu|reemplaz|obsolet|ya no|descartad|abandon|retirad|"
                  r"before the|pre-|legacy|kept for the record|not used|no se usa|unused|deprecated|"
                  r"desde el|historical|histórico|historico|v1|rev(ision)? [1-5]\b", re.I)


def iter_text_lines(path):
    """(line_no, text, heading) for a text file; JSON files are read as text lines too."""
    head = ""
    with open(path, encoding="utf-8") as fh:
        for i, line in enumerate(fh, 1):
            s = line.rstrip("\n")
            if s.startswith("#"):
                head = s.strip()
            yield i, s, head


def iter_json_strings(obj, path="$"):
    if isinstance(obj, dict):
        for k in obj:
            yield from iter_json_strings(obj[k], f"{path}.{k}")
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from iter_json_strings(v, f"{path}[{i}]")
    elif isinstance(obj, str):
        yield path, obj


def main() -> None:
    os.makedirs(OUT, exist_ok=True)
    B = Bundle()
    rows = []
    files = [os.path.join(REPO, d) for d in DOCS]
    files += sorted(glob.glob(os.path.join(REPO, "app/public/media/*/README.md")))
    files += sorted(glob.glob(os.path.join(REPO, "app/public/media/*/*.vtt")))
    pats = [(f, re.compile(p, re.I)) for f, p in FACTS]
    for path in files:
        rel = os.path.relpath(path, REPO)
        for ln, s, head in iter_text_lines(path):
            for fid, rx in pats:
                m = rx.search(s)
                if m:
                    a, b = max(0, m.start() - 160), min(len(s), m.end() + 160)
                    rows.append({"fact": fid, "file": rel, "where": str(ln),
                                 "marked": bool(MARK.search(s) or MARK.search(head)),
                                 "heading": head[:100], "text": s[a:b].replace("\t", " ")})
    for name in BUNDLE_TEXTS:
        obj = B.json(name)
        for jp, s in iter_json_strings(obj):
            for fid, rx in pats:
                m = rx.search(s)
                if m:
                    a, b = max(0, m.start() - 160), min(len(s), m.end() + 160)
                    rows.append({"fact": fid, "file": "app/public/data/v2/" + name, "where": jp,
                                 "marked": bool(MARK.search(s)), "heading": "", "text": s[a:b]})
    rows.sort(key=lambda r: (r["fact"], r["file"], r["where"].zfill(8)))
    with open(os.path.join(OUT, "p4_docs_hits.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["fact", "file", "where", "marked", "heading", "text"])
        w.writeheader()
        w.writerows(rows)

    # ---------------- truth from the bundle (own reader) and the tables
    truth = {}
    base_ids = B.col("earth_base.bin", "id").astype(int)
    for mid, f in [("rover", "earth_rover.bin"), ("solar", "earth_solar.bin"), ("lunar_base", "earth_lunar_base.bin")]:
        tw = B.col(f, "twin")
        rk = B.col(f, "rank")
        li = B.col(f, "land_index").astype(int)
        ids = base_ids[li]
        paired = ~np.isnan(tw)
        top = int(ids[np.where(rk == 1)[0][0]])
        truth[mid] = {"passing": int(ids.size), "paired": int(paired.sum()), "unpaired": int((~paired).sum()),
                      "distinct_twins": int(np.unique(tw[paired]).size), "top1_earth": top,
                      "top1_moon": int(tw[np.where(rk == 1)[0][0]])}
    ms = B.json("missions.json")
    truth["missions_json"] = [{"id": m["id"], "name": m.get("name"), "label": m.get("label"),
                               "similarity_rule": m["similarity"].get("rule"),
                               "variables": [(v["variable"], v["role"], v["weight"], v["tolerance"], v.get("bound"))
                                             for v in m["similarity"]["variables"]],
                               "zone": m["similarity"].get("zone") or m.get("zone")} for m in ms["missions"]]
    man = B.manifest
    truth["manifest"] = {k: man.get(k) for k in ("contract_revision", "engine_version", "dataset", "bundle_version")}
    truth["grid"] = man.get("grid")
    # thermal facts for "nowhere on Earth is as cold as the Moon"
    E, M = load_tables()
    reg = B.col("moon_base.bin", "region")
    codes = [r["code"] for r in B.json("mission_zones.json")["regions"]]
    zoneA = np.array([codes[int(i)] == "A" for i in reg])
    e_tmin_k = E["tmin_c"].values + 273.15
    e_land = E["mask_fraction"].values > 0
    truth["thermal"] = {
        "earth_tmin_k_min_land": float(np.nanmin(e_tmin_k[e_land])),
        "moon_zoneA_tmin_k_max": float(np.nanmax(M["tmin_k"].values[zoneA])),
        "moon_zoneA_tmin_k_min": float(np.nanmin(M["tmin_k"].values[zoneA])),
        "moon_all_tmin_k_max": float(np.nanmax(M["tmin_k"].values)),
        "earth_cells_colder_than_warmest_zoneA_cell": int(np.sum(e_tmin_k[e_land] <= np.nanmax(M["tmin_k"].values[zoneA]))),
    }
    summ = {"truth": truth, "hits_per_fact": {}, "unmarked_leftovers": []}
    for r in rows:
        summ["hits_per_fact"].setdefault(r["fact"], 0)
        summ["hits_per_fact"][r["fact"]] += 1
        if r["fact"] in ("rule.old.zone_twin", "rule.old.zscore", "rule.old.pooled", "zone.solar.old", "artemis.III",
                         "cell.size.other") and not r["marked"]:
            summ["unmarked_leftovers"].append([r["fact"], r["file"], r["where"], r["text"][:260]])
    with open(os.path.join(OUT, "p4_docs_summary.json"), "w", encoding="utf-8") as fh:
        json.dump(summ, fh, indent=1, ensure_ascii=False, sort_keys=True)
    print(json.dumps(truth, indent=1, ensure_ascii=False)[:4000])
    print("hits", len(rows), "unmarked leftovers", len(summ["unmarked_leftovers"]))


if __name__ == "__main__":
    main()
