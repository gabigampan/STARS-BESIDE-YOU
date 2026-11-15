"""ra_rover_texts (item 9): collect every Rover text of the bundle with its 'show' field and the numbers it states,
so that each figure can be checked against out/ra_rover_audit.json.

    python ra_rover_texts.py [bundle folder]
Reads similarity.json texts, missions.json (rover), explain.json (rover part), variables.json (entries naming rover),
twins.json (rover part, headline only). Writes out/ra_rover_texts.json.
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
BDIR = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else os.path.join(HERE, "..", "..", "app", "public", "data", "v2")
NUM = re.compile(r"(?<![\w.])[-+]?\d[\d,]*(?:\.\d+)?\s?%?")


def walk(o, path, out, want=lambda p, s: True):
    if isinstance(o, dict):
        for k, v in o.items():
            walk(v, path + [str(k)], out, want)
    elif isinstance(o, list):
        for i, v in enumerate(o):
            walk(v, path + [str(i)], out, want)
    elif isinstance(o, str) and len(o) > 25 and want(path, o):
        out.append({"path": "/".join(path), "text": o, "numbers": NUM.findall(o)})


res = {}
sim = json.load(open(os.path.join(BDIR, "similarity.json"), encoding="utf-8"))
texts = []
for k, v in sim.get("texts", {}).items():
    blob = json.dumps(v, ensure_ascii=False).lower()
    if "rover" in k.lower() or "rover" in blob or k in ("numbers_without_effect", "deviations_from_team"):
        texts.append({"key": k, "show": v.get("show") if isinstance(v, dict) else None, "status": v.get("status") if isinstance(v, dict) else None,
                      "missions": v.get("missions") if isinstance(v, dict) else None, "content": v})
res["similarity_texts"] = texts
ms = json.load(open(os.path.join(BDIR, "missions.json"), encoding="utf-8"))
rv = [x for x in ms["missions"] if x["id"] == "rover"][0]
res["missions_rover_strings"] = []
walk(rv, ["missions", "rover"], res["missions_rover_strings"])
res["missions_rover_top5"] = rv.get("top5")
res["missions_rover_similarity"] = rv.get("similarity")
ex = json.load(open(os.path.join(BDIR, "explain.json"), encoding="utf-8"))
exr = ex.get("missions", {}).get("rover") if isinstance(ex.get("missions"), dict) else None
if exr is None and isinstance(ex, dict):
    exr = {k: v for k, v in ex.items() if "rover" in k.lower()} or ex.get("rover")
res["explain_rover_strings"] = []
walk(exr, ["explain", "rover"], res["explain_rover_strings"])
var = json.load(open(os.path.join(BDIR, "variables.json"), encoding="utf-8"))
res["variables_rover_strings"] = []
walk(var, ["variables"], res["variables_rover_strings"], want=lambda p, s: "rover" in s.lower() or any("rover" in x.lower() for x in p))
json.dump(res, open(os.path.join(HERE, "out", "ra_rover_texts.json"), "w"), indent=1, ensure_ascii=False)
for t in texts:
    print("##", t["key"], "| show:", t["show"], "| status:", t["status"])
    c = t["content"]
    print("   ", (c.get("text") if isinstance(c, dict) else c) if not isinstance(c, dict) or "text" in c else json.dumps(c, ensure_ascii=False)[:800])
print("missions.json rover strings:", len(res["missions_rover_strings"]), "| explain:", len(res["explain_rover_strings"]), "| variables:", len(res["variables_rover_strings"]))
print("top5:", json.dumps(res["missions_rover_top5"], ensure_ascii=False)[:1500])
