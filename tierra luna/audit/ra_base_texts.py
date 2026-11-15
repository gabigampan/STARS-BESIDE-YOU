"""Re-audit Lunar base, item 9: print every Lunar base note of the bundle (similarity.json texts with
their show field, missions.json lunar_base known_limitations, top5, external_validation, weighted
variables) and check the figures they contain against my own outputs (out/ra_base_*.json).
Run: python "tierra luna/audit/ra_base_texts.py" -> out/ra_base_texts.json"""
import json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ra_base_common as R
import p5_common as C

B = C.BUNDLE
sim = json.load(open(os.path.join(B, "similarity.json"), encoding="utf-8"))
mj = json.load(open(os.path.join(B, "missions.json"), encoding="utf-8"))
lb = [x for x in mj["missions"] if x["id"] == R.M][0]
mc = json.load(open(os.path.join(R.OUT, "ra_base_mc_corrected.json"), encoding="utf-8"))["summary"]
texts = {k: v for k, v in sim["texts"].items()
         if "lunar_base" in (v.get("missions") or []) or "lunar_base" in k or k in ("deviations_from_team", "numbers_without_effect")}
checks = []


def has(name, s, needle):
    checks.append({"text": name, "needle": needle, "found": needle in s})


ev = texts.get("external_validation_lunar_base", {}).get("text", "")
checks.append({"text": "external_validation_lunar_base", "needle": "no longer says passing sites have no twin", "found": "have no twin" not in ev})
for n in ("13.8", "7.4", "0.615"):
    has("external_validation_lunar_base", ev, n)
st = texts.get("top5_stability_lunar_base", {}).get("text", "")
checks.append({"text": "top5_stability_lunar_base", "needle": "not pending", "found": "pending" not in st.lower()})
for e in mc["share_in_five"]:
    for k in ("share_in_five", "share_top20"):
        v = mc[k][e] * 100
        cands = {f"{v:.1f}", f"{v:.0f}", f"{v:g}"}
        checks.append({"text": "top5_stability_lunar_base", "needle": f"E{e} {k} {v:.1f}", "found": any(c in st for c in cands)})
wv = {x["variable"]: x for x in lb["weighted_variables"]}
checks.append({"text": "weighted_variables", "needle": "weights", "values": {k: x["weight"] for k, x in wv.items()}})
checks.append({"text": "weighted_variables", "needle": "tmin_c also_in_similarity", "value": wv["tmin_c"].get("also_in_similarity")})
for k, v in texts.items():
    print("==", k, v.get("show"), "|", (v.get("text") or json.dumps(v.get("variants"), ensure_ascii=False))[:1200])
print("== known_limitations")
for t in lb["known_limitations"]:
    print("-", t[:1200])
print("== external_validation", json.dumps(lb.get("external_validation"), ensure_ascii=False)[:1500])
print("== top5", json.dumps(lb.get("top5"), ensure_ascii=False)[:800])
for c in checks:
    print("CHECK", c)
R.dump({"texts": texts, "known_limitations": lb["known_limitations"], "external_validation": lb.get("external_validation"),
        "checks": checks}, "ra_base_texts.json")
