"""Point A (reviewer 5): inventory of every number SHOWN to the user, and whether each one can be
traced to a number of the model, the bundle or the file the text was generated from.

Sources scanned (strings only for JSON; every cue line for captions):
  * bundle texts: app/public/data/v2/{missions,similarity,mission_zones,explain,twins,places}.json
  * video captions: app/public/media/*/*.vtt; video scenarios: app/video-sim/scenarios/*.json
  * audio transcripts: app/public/audio/transcripts.json
Reference numbers are numeric leaves only (never numbers inside the scanned strings themselves).
Reference sets (a shown number is "traced" when it equals a reference number rounded to 0-4
decimals, or 100 x a reference fraction so rounded, or its absolute value):
  * bundle texts  -> every numeric leaf of the bundle JSON files + mission_scoring.json + engine_config.json
  * captions      -> every numeric leaf of the scenario of that video (+ the same config files)
  * transcripts   -> every numeric leaf of docs/AUDIO_TOP5.json (the file they were recorded from)
Spelled-out numbers ("one degree") are listed but only digits are traced.
Run: <python> "tierra luna/audit/p5_shown_numbers.py"
Outputs: out/p5_shown_numbers.csv (one row per number), out/p5_shown_numbers_summary.json
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

APP = os.path.join(REPO, "app")
NUM = re.compile(r"(?<![A-Za-z_\d])[-−]?\d{1,3}(?:[,.]\d{3})*(?:[.,]\d+)?|(?<![A-Za-z_\d])[-−]?\d+(?:[.,]\d+)?")
WORDS = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9,
         "ten": 10, "eleven": 11, "twelve": 12, "twenty": 20, "hundred": 100, "half": 0.5, "quarter": 0.25}
SKIP_KEYS = {"url", "source", "label_url", "link", "sha256", "doi", "file", "path", "files"}


def leaves(o, p=""):
    if isinstance(o, dict):
        for k, v in o.items():
            yield from leaves(v, f"{p}.{k}" if p else k)
    elif isinstance(o, list):
        for i, v in enumerate(o):
            yield from leaves(v, f"{p}[{i}]")
    else:
        yield p, o


def numeric_refs(objs, strings=True):
    out = set()
    for o in objs:
        for _, v in leaves(o):
            if isinstance(v, bool):
                continue
            if isinstance(v, (int, float)):
                out.add(float(v))
            elif isinstance(v, str) and strings:
                for t in NUM.findall(v):
                    x = parse(t, "en")
                    if x is not None:
                        out.add(x)
    return out


def parse(tok, lang):
    t = tok.replace("−", "-")
    if lang == "es":
        # Spanish: '.' thousands, ',' decimal
        if re.fullmatch(r"-?\d{1,3}(\.\d{3})+", t):
            t = t.replace(".", "")
        t = t.replace(",", ".")
    else:
        if re.fullmatch(r"-?\d{1,3}(,\d{3})+(\.\d+)?", t):
            t = t.replace(",", "")
        elif "," in t:
            return None
    try:
        return float(t)
    except ValueError:
        return None


def traced(x, refs):
    for r in refs:
        for d in range(0, 5):
            if abs(abs(x) - abs(round(r, d))) < 1e-9 or abs(abs(x) - abs(round(100 * r, d))) < 1e-9:
                return True
    return False


def scan_text(text, lang):
    for m in NUM.finditer(text):
        tok = m.group(0)
        if re.fullmatch(r"(19|20)\d\d", tok):           # years
            kind = "year"
        else:
            kind = "digits"
        yield tok, kind, text[max(0, m.start() - 45): m.end() + 45].replace("\n", " ")
    for w in re.finditer(r"\b(" + "|".join(WORDS) + r")\b", text, flags=re.I):
        yield w.group(0), "word", text[max(0, w.start() - 45): w.end() + 45].replace("\n", " ")


def main():
    ms = json.load(open(os.path.join(TL, "mission_scoring.json"), encoding="utf-8"))
    ec = json.load(open(os.path.join(TL, "engine", "engine_config.json"), encoding="utf-8"))
    bdir = os.path.join(APP, "public", "data", "v2")
    bfiles = ["missions.json", "similarity.json", "mission_zones.json", "explain.json", "twins.json", "places.json"]
    bundle = {f: json.load(open(os.path.join(bdir, f), encoding="utf-8")) for f in bfiles}
    rows = []
    cfg_refs = numeric_refs([ms, ec])
    bundle_refs = numeric_refs(list(bundle.values()), strings=False) | cfg_refs
    for f, o in bundle.items():
        for p, v in leaves(o):
            if not isinstance(v, str) or p.split(".")[-1] in SKIP_KEYS or v.startswith("http"):
                continue
            if f in ("twins.json", "places.json") and not re.search(r"\s", v):
                continue
            for tok, kind, ctx in scan_text(v, "en"):
                x = parse(tok, "en") if kind == "digits" else None
                rows.append({"where": f"bundle/{f}", "path": p, "token": tok, "kind": kind,
                             "traced": (traced(x, bundle_refs) if x is not None else ""), "context": ctx})
    for scen in sorted(glob.glob(os.path.join(APP, "video-sim", "scenarios", "*.json"))):
        name = os.path.basename(scen)[:-5]
        sc = json.load(open(scen, encoding="utf-8"))
        refs = numeric_refs([sc], strings=False) | cfg_refs
        for vtt in sorted(glob.glob(os.path.join(APP, "public", "media", name, "*.vtt"))):
            lang = "es" if vtt.endswith(".es.vtt") else "en"
            for i, line in enumerate(open(vtt, encoding="utf-8").read().splitlines()):
                if "-->" in line or re.fullmatch(r"\d+", line.strip()):
                    continue
                for tok, kind, ctx in scan_text(line, lang):
                    x = parse(tok, lang) if kind == "digits" else None
                    rows.append({"where": os.path.relpath(vtt, REPO), "path": f"line {i + 1}", "token": tok, "kind": kind,
                                 "traced": (traced(x, refs) if x is not None else ""), "context": ctx})
    for vtt in sorted(glob.glob(os.path.join(APP, "public", "media", "*", "*.vtt"))):
        name = os.path.basename(os.path.dirname(vtt))
        if os.path.exists(os.path.join(APP, "video-sim", "scenarios", name + ".json")):
            continue
        lang = "es" if vtt.endswith(".es.vtt") else "en"
        for i, line in enumerate(open(vtt, encoding="utf-8").read().splitlines()):
            if "-->" in line or re.fullmatch(r"\d+", line.strip()):
                continue
            for tok, kind, ctx in scan_text(line, lang):
                rows.append({"where": os.path.relpath(vtt, REPO), "path": f"line {i + 1}", "token": tok, "kind": kind,
                             "traced": "no scenario file", "context": ctx})
    top5 = json.load(open(os.path.join(REPO, "docs", "AUDIO_TOP5.json"), encoding="utf-8"))
    trefs = numeric_refs([top5], strings=False)
    tr = json.load(open(os.path.join(APP, "public", "audio", "transcripts.json"), encoding="utf-8"))
    for k, text in tr.items():
        for tok, kind, ctx in scan_text(text, "en"):
            x = parse(tok, "en") if kind == "digits" else None
            rows.append({"where": "app/public/audio/transcripts.json", "path": k, "token": tok, "kind": kind,
                         "traced": (traced(x, trefs) if x is not None else ""), "context": ctx})
    with open(os.path.join(OUT, "p5_shown_numbers.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    summ = {}
    for r in rows:
        key = r["where"] if not r["where"].startswith("app/public/media") else r["where"]
        s = summ.setdefault(key, {"numbers": 0, "digits": 0, "traced": 0, "not_traced": 0, "words": 0, "years": 0, "no_scenario": 0})
        s["numbers"] += 1
        if r["kind"] == "digits":
            s["digits"] += 1
            if r["traced"] is True:
                s["traced"] += 1
            elif r["traced"] is False:
                s["not_traced"] += 1
            else:
                s["no_scenario"] += 1
        elif r["kind"] == "word":
            s["words"] += 1
        else:
            s["years"] += 1
    nt = [r for r in rows if r["traced"] is False]
    json.dump({"per_file": summ, "not_traced": nt}, open(os.path.join(OUT, "p5_shown_numbers_summary.json"), "w", encoding="utf-8"),
              indent=1, ensure_ascii=False)
    for k, v in summ.items():
        print(k, v)
    print("not traced:", len(nt))


if __name__ == "__main__":
    main()
