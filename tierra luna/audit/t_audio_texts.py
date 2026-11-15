"""Independent check of the 19 audio texts (app/public/audio/transcripts.json) against the bundle and tables.

Written by the independent checker (docs/stats_audit/10_textos_audio.md). It does NOT import the writer's
generator (tierra luna/tools/make_audio_top5.py). It reads app/public/data/v2 by docs/DATA_CONTRACT.md
(revision 8), the Earth table (snow_ice_frac), GeoNames cities1000 (reverse_geocoder copy), the engine's IAU
file and NASA's region footprints. Output: tierra luna/audit/out/t_audio_texts.json (facts, expected spoken
figures, every check and its result).

Run: <venv>/python "tierra luna/audit/t_audio_texts.py" [--transcripts PATH]
"""
import argparse
import csv
import json
import math
import os
import re
import sys
from decimal import Decimal, ROUND_HALF_UP

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
B = os.path.join(REPO, "app", "public", "data", "v2")
OUT = os.path.join(HERE, "out", "t_audio_texts.json")
R_E, R_M = 6371.0, 1737.4
# The web names the nearest populated place only within this distance (read from the web, not from the generator);
# beyond it a track says the country (and region) and the coordinates, and does not mention the place.
_DP = os.path.join(REPO, "app", "src", "flow", "detailPanel.ts")
with open(_DP, encoding="utf-8") as _fh:
    _m = __import__("re").search(r"const NEAREST_PLACE_MAX_KM = (\d+(?:\.\d+)?);", _fh.read())
if not _m:
    raise SystemExit(f"NEAREST_PLACE_MAX_KM not found in {_DP}")
NEAREST_PLACE_MAX_KM = float(_m.group(1))

RESULTS = []


def ok(cond, what, detail=""):
    RESULTS.append({"ok": bool(cond), "check": what, "detail": str(detail)})
    return bool(cond)


def J(name):
    with open(os.path.join(B, name), encoding="utf-8") as fh:
        return json.load(fh)


MAN = J("manifest.json")
FILES = {f["name"]: f for f in MAN["files"]}
_cache = {}


def col(fname, cname):
    if fname not in _cache:
        with open(os.path.join(B, fname), "rb") as fh:
            _cache[fname] = fh.read()
    c = next(c for c in FILES[fname]["columns"] if c["name"] == cname)
    a = np.frombuffer(_cache[fname], dtype="<f4" if c["type"] == "float32" else "<i4", count=c["length"], offset=c["offset"])
    if c["type"] == "int32":
        if c.get("divisor"):
            out = np.where(a == -2147483648, np.nan, a / c["divisor"])
            return out
        return a.astype(np.int64)
    return a


# ---------------------------------------------------------------- display rules (app/src/flow/dom.ts)
def half_up(x, d):
    """toFixed / Intl on the exact binary value: half up on the exact decimal expansion."""
    q = Decimal(1).scaleb(-d)
    return Decimal(float(x)).quantize(q, rounding=ROUND_HALF_UP)


def strip(dec):
    s = format(dec, "f")
    if "." in s:
        s = s.rstrip("0").rstrip(".")
    return s


def num(v, d):          # dom.ts num(): up to d decimals, trailing zeros dropped
    return strip(half_up(v, d))


def fixed(v, d):        # dom.ts fixed(): exactly d decimals
    return format(half_up(v, d), "f")


def value_text(v, unit):   # dom.ts valueText (number part only)
    if unit == "percentile points":
        return fixed(v, 1)
    a = abs(float(v))
    d = 3 if unit == "fraction 0-1" else 1 if a >= 100 else 2 if a >= 10 else 3
    return num(v, d)


def f32_display_tenth(raw):   # contract: shortest round-trip decimal of the float32, then 1 decimal half up
    s = np.format_float_positional(np.float32(raw), unique=True)
    return Decimal(s).quantize(Decimal("0.1"), ROUND_HALF_UP)


def gc_deg(lat1, lon1, lat2, lon2):
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dl = math.radians(lon2 - lon1)
    c = math.sin(p1) * math.sin(p2) + math.cos(p1) * math.cos(p2) * math.cos(dl)
    return math.degrees(math.acos(max(-1.0, min(1.0, c))))


def bearing(lat1, lon1, lat2, lon2):
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dl = math.radians(lon2 - lon1)
    y = math.sin(dl) * math.cos(p2)
    x = math.cos(p1) * math.sin(p2) - math.sin(p1) * math.cos(p2) * math.cos(dl)
    return (math.degrees(math.atan2(y, x)) + 360) % 360


COMPASS = ["north", "northeast", "east", "southeast", "south", "southwest", "west", "northwest"]


def compass8(b):
    return COMPASS[int(((b + 22.5) % 360) // 45)]


def centre(cid):
    r, c = divmod(int(cid), 360)
    return 90 - (r + 0.5), -180 + (c + 0.5)


def say_int(n):
    return f"{int(n):,}"


# ---------------------------------------------------------------- load
missions = {m["id"]: m for m in J("missions.json")["missions"]}
explain = J("explain.json")["missions"]
twins = J("twins.json")["missions"]
places = J("places.json")
pdetail = J("place_detail.json")
iau = J("iau_moon_features.json")
sim_texts = J("similarity.json")["texts"]

land_ids = col("earth_base.bin", "id")
land_pos = {int(i): k for k, i in enumerate(land_ids)}
e_country = col("earth_base.bin", "country")
e_region = col("earth_base.bin", "region")
e_mask = col("earth_base.bin", "v.mask_fraction")
e_clear = col("earth_base.bin", "v.clear_frac_isccp")
np_idx = col("earth_place_detail.bin", "nearest_place")
np_km = col("earth_place_detail.bin", "nearest_place_km")
m_feat = col("moon_base.bin", "feature")
m_feat_km = col("moon_base.bin", "feature_km")

et = pd.read_csv(os.path.join(REPO, "tierra luna", "output_real", "earth_real_1deg.csv"), usecols=["cell_id", "snow_ice_frac", "mask_fraction"])
et_id = et["cell_id"].astype(str).str[1:].astype(int).values
ICE = dict(zip(et_id.tolist(), et["snow_ice_frac"].astype(float).tolist()))
TMASK = dict(zip(et_id.tolist(), et["mask_fraction"].astype(float).tolist()))
cl = pd.read_csv(os.path.join(REPO, "tierra luna", "real_data", "supplement", "earth_cloud_isccp_1deg.csv"))
CLEAR_TBL = dict(zip(cl["cell_id"].astype(str).str[1:].astype(int).tolist(), cl["clear_frac_isccp"].astype(float).tolist()))

import reverse_geocoder  # noqa: E402
GN = pd.read_csv(os.path.join(os.path.dirname(reverse_geocoder.__file__), "rg_cities1000.csv"), dtype=str, keep_default_na=False)
GN["latf"] = GN["lat"].astype(float)
GN["lonf"] = GN["lon"].astype(float)
with open(os.path.join(REPO, "tierra luna", "engine", "data", "iau_moon_nomenclature.csv"), encoding="utf-8") as fh:
    ENGINE_IAU = {r["name"]: r for r in csv.DictReader(fh)}

IAU_LAT = np.array(iau["lat"], float)
IAU_LON = np.array(iau["lon"], float)


def moon_nearest(lat, lon):
    p1, p2 = np.radians(lat), np.radians(IAU_LAT)
    c = np.sin(p1) * np.sin(p2) + np.cos(p1) * np.cos(p2) * np.cos(np.radians(IAU_LON - lon))
    d = np.degrees(np.arccos(np.clip(c, -1, 1))) * math.pi / 180 * R_M
    i = int(np.argmin(d))
    return i, float(d[i])


# ---------------------------------------------------------------- per mission facts
FACTS = {}
for mid in ("rover", "solar", "lunar_base"):
    mj = missions[mid]
    t5 = mj["top5"]
    ef, pf = f"earth_{mid}.bin", f"earth_{mid}_pairs.bin"
    li = col(ef, "land_index")
    ids = land_ids[li]
    pos = {int(i): k for k, i in enumerate(ids)}
    rank = col(ef, "rank")
    final = col(ef, "final")
    simv = col(ef, "similarity")
    suit = col(ef, "suitability")
    twin = col(ef, "twin")
    ex = {it["id"]: it for it in explain[mid]}
    tw = {t["id"]: t for t in twins[mid]["twins"]}

    # ---- rule of the five, recomputed
    ranked = [int(i) for i in ids[np.argsort(np.where(rank == -2147483648, 10**9, rank), kind="stable")] if rank[pos[int(i)]] != -2147483648]

    def skip(eid):
        if ICE[eid] >= 0.5:
            return "ice"
        if float(e_mask[land_pos[eid]]) < 0.5:
            return "water"
        return None

    fx = {"rule_id": t5["rule_id"]}
    if t5["rule_id"] == "rank_with_skips":
        kept, skipped = [], []
        for eid in ranked:
            r = int(rank[pos[eid]])
            why = skip(eid)
            if why is None and any(gc_deg(*centre(eid), *centre(k)) < 2.0 for k in kept):
                why = "within 2 degrees"
            if why:
                skipped.append((r, why))
            else:
                kept.append(eid)
            if len(kept) == 5:
                break
        fx["recomputed_ids"] = kept
        fx["skipped_before_fifth"] = skipped
        ok(kept == t5["ids"], f"{mid}: rule of the five recomputed gives the bundle's top5", (kept, t5["ids"]))
        ok([int(rank[pos[k]]) for k in kept] == t5["overall_ranks"], f"{mid}: overall ranks", t5["overall_ranks"])
        fx["highest_scoring_the_rule_allows"] = kept == t5["ids"]
    else:
        top = np.nanmax(final)
        tied = [int(i) for i in ids if final[pos[int(i)]] == top]
        kept_t = [e for e in tied if skip(e) is None]
        fx["top_final"] = float(top)
        fx["tied_n"] = len(tied)
        fx["tied_after_skips"] = len(kept_t)
        fx["skips"] = {"ice": sum(skip(e) == "ice" for e in tied), "water": sum(skip(e) == "water" for e in tied)}
        sims = sorted(set(float(simv[pos[e]]) for e in tied))
        suits = sorted(set(float(suit[pos[e]]) for e in tied))
        fx["tied_similarity_values"] = sims
        fx["tied_suitability_values"] = suits
        # first: highest similarity, ties by rank; then farthest point
        first = sorted(kept_t, key=lambda e: (-simv[pos[e]], rank[pos[e]]))[0]
        ch = [first]
        while len(ch) < 5:
            nxt = max(kept_t, key=lambda e: (min(gc_deg(*centre(e), *centre(c)) for c in ch), -rank[pos[e]]) if e not in ch else (-1, 0))
            ch.append(nxt)
        fx["recomputed_ids"] = ch
        mind = min(gc_deg(*centre(a), *centre(b)) for i, a in enumerate(ch) for b in ch[i + 1:])
        fx["closest_two_deg"] = mind
        ok(set(ch) == set(t5["ids"]), f"{mid}: spread-within-tie recomputed gives the bundle's five (as a set)", (ch, t5["ids"]))
        ok(ch == t5["ids"], f"{mid}: ... and in the bundle's order", (ch, t5["ids"]))
        ok(len(tied) == t5["top_tie_n"] and len(kept_t) == t5["top_tie_n_after_skips"], f"{mid}: tie counts", (len(tied), len(kept_t)))
        # how many paired sites have similarity 100.00 at all (to judge 'match equally well')
        fx["paired_with_similarity_100"] = int(np.sum(simv == 100.0))
        fx["tied_with_similarity_exactly_100"] = sum(simv[pos[e]] == 100.0 for e in tied)

    # ---- pairs
    pairs = []
    for n, eid in enumerate(t5["ids"], 1):
        p = pos[eid]
        k = land_pos[eid]
        it = ex[eid]
        mc = int(twin[p])
        lat, lon = centre(eid)
        mlat, mlon = centre(mc)
        P = {"number": n, "id": eid, "rank": int(rank[p]), "lat": lat, "lon": lon, "twin": mc}
        ok(it["rank"] == P["rank"] and it["similarity"]["twin"]["id"] == mc, f"{mid} #{n}: explain matches binary rank/twin")
        P["similarity"] = fixed(simv[p], 2)
        P["final"] = fixed(final[p], 2)
        P["suitability"] = fixed(suit[p], 2)
        ok(it["similarity"]["value"] == float(simv[p]) and it["final"] == float(final[p]), f"{mid} #{n}: explain scores = binary")
        # Earth place
        cname = places["countries"][int(e_country[k])]["name"]
        rname = None if e_region[k] == -2147483648 else places["regions"][int(e_region[k])]
        rname = rname["name"] if isinstance(rname, dict) else rname
        pname = pdetail["nearest_places"][int(np_idx[k])]
        km = float(np_km[k])
        ok(it["place"]["country"] == cname and it["place"]["region"] == rname and it["place"]["nearest_place"] == pname,
           f"{mid} #{n}: place names explain = binary", (cname, rname, pname))
        cand = GN[GN["name"] == pname].copy()
        cand["d"] = [gc_deg(lat, lon, a, b) * math.pi / 180 * R_E for a, b in zip(cand["latf"], cand["lonf"])]
        g = cand.sort_values("d").iloc[0]
        # is it the nearest cities1000 place at all?
        allg = GN.copy()
        dd = np.degrees(np.arccos(np.clip(np.sin(np.radians(lat)) * np.sin(np.radians(allg["latf"])) + np.cos(np.radians(lat)) * np.cos(np.radians(allg["latf"])) * np.cos(np.radians(allg["lonf"] - lon)), -1, 1))) * math.pi / 180 * R_E
        gi = int(np.argmin(dd.values))
        P["earth"] = {"country": cname, "region": rname, "place": pname, "place_cc": g["cc"], "place_admin1": g["admin1"],
                      "km_stored": km, "km_spoken": int(half_up(km, 0)), "km_on_screen": num(km, 0) if km <= NEAREST_PLACE_MAX_KM else None,
                      "km_recomputed": round(float(g["d"]), 2), "direction": compass8(bearing(g["latf"], g["lonf"], lat, lon)),
                      "bearing": round(bearing(g["latf"], g["lonf"], lat, lon), 1),
                      "nearest_cities1000": allg.iloc[gi]["name"], "nearest_cities1000_km": round(float(dd.values[gi]), 2)}
        ok(abs(float(g["d"]) - km) < 1.0, f"{mid} #{n}: Earth distance recomputed", (g["d"], km))
        ok(allg.iloc[gi]["name"] == pname, f"{mid} #{n}: {pname} is the nearest cities1000 place", allg.iloc[gi]["name"])
        # Moon feature
        fi = int(m_feat[mc])
        fname, ftype = iau["name"][fi], iau["type"][fi]
        fkm = float(m_feat_km[mc])
        ni, nd = moon_nearest(mlat, mlon)
        ok(ni == fi and abs(nd - fkm) < 0.5, f"{mid} #{n}: lunar feature is the nearest primary IAU feature, distance recomputed", (iau["name"][ni], nd, fkm))
        ok(fname in ENGINE_IAU, f"{mid} #{n}: '{fname}' written so in the engine's IAU file")
        ok(it["similarity"]["twin"]["feature"] == fname, f"{mid} #{n}: explain feature")
        P["moon"] = {"feature": fname, "type": ftype, "km_stored": fkm, "km_spoken": int(half_up(fkm, 0)), "km_on_screen": num(fkm, 1),
                     "twin_lat": mlat, "twin_lon": mlon}
        # values
        if mid == "rover":
            for v in ("slope_deg", "roughness_m"):
                u = "deg" if v == "slope_deg" else "m"
                P[v] = {"earth": value_text(col(pf, f"{v}.earth")[p], u), "moon": value_text(col(pf, f"{v}.moon")[p], u),
                        "diff": value_text(col(pf, f"{v}.diff")[p], u)}
            P["s"] = [float(col(ef, "s.slope_deg")[p]), float(col(ef, "s.roughness_m")[p])]
        if mid == "solar":
            A = f32_display_tenth(col(pf, "atm.toa_kwh_m2_day")[p])
            G = f32_display_tenth(col(pf, "atm.ground_kwh_m2_day")[p])
            Mo = f32_display_tenth(col(pf, "irradiance_toa_kwh_m2_day.moon")[p])
            Ai, Gi = int(A * 10), int(G * 10)
            P["toa_earth"], P["ground"], P["toa_moon"] = str(A), str(G), str(Mo)
            P["loss_pct"] = (200 * (Ai - Gi) + Ai) // (2 * Ai)
            P["clear"] = value_text(e_clear[k], "fraction 0-1")
            P["clear_raw"] = float(e_clear[k])
            ok(abs(CLEAR_TBL[eid] - float(e_clear[k])) < 1e-6, f"solar #{n}: clear-sky bundle = ISCCP table", (CLEAR_TBL[eid], e_clear[k]))
            P["pair_sentence"] = it["similarity"].get("pair_sentence")
            ok(f"{A}" in P["pair_sentence"] and f"{G}" in P["pair_sentence"] and f"{P['loss_pct']}" in P["pair_sentence"],
               f"solar #{n}: my figures appear in the bundle's pair sentence", P["pair_sentence"])
        if mid == "lunar_base":
            P["tmin_diff_K"] = value_text(col(pf, "tmin_k.diff")[p], "K")
            P["tmin_earth_K"] = float(col(pf, "tmin_k.earth")[p])
            P["tmin_moon_K"] = float(col(pf, "tmin_k.moon")[p])
            P["tmin_pct"] = [fixed(col(pf, "tmin_k.earth_pct")[p], 1), fixed(col(pf, "tmin_k.moon_pct")[p], 1)]
            P["amp_pct"] = [fixed(col(pf, "lst_diurnal_amp_k.earth_pct")[p], 1), fixed(col(pf, "lst_diurnal_amp_k.moon_pct")[p], 1)]
            P["amp_pct_diff"] = fixed(col(pf, "lst_diurnal_amp_k.diff_pct")[p], 1)
            P["slope"] = [value_text(col(pf, "slope_deg.earth")[p], "deg"), value_text(col(pf, "slope_deg.moon")[p], "deg"),
                          float(col(pf, "slope_deg.diff")[p])]
            P["rough"] = [value_text(col(pf, "roughness_m.earth")[p], "m"), value_text(col(pf, "roughness_m.moon")[p], "m"),
                          float(col(pf, "roughness_m.diff")[p])]
            nr = tw[mc]["nasa_region"]
            P["region"] = nr
            ok((nr["share_of_cell"] >= 0.5) == (nr["phrase"] == "in"), f"base #{n}: region phrase follows the 50 % rule", nr)
        pairs.append(P)
    FACTS[mid] = {"rule": fx, "pairs": pairs}

# ---------------------------------------------------------------- lunar_base region share, recomputed (independent)
try:
    from shapely.geometry import shape, Point
    from shapely.prepared import prep
    with open(os.path.join(REPO, "tierra luna", "engine", "data", "artemis_iii_regions.geojson"), encoding="utf-8") as fh:
        gj = json.load(fh)
    regs = {f["properties"]["name"]: prep(shape(f["geometry"])) for f in gj["features"]}
    for P in FACTS["lunar_base"]["pairs"]:
        lat0, lon0 = P["twin"] // 360, P["twin"] % 360
        la_c, lo_c = centre(P["twin"])
        N = 120
        tot = ins = 0.0
        g = regs[P["region"]["region"]]
        for i in range(N):
            la = la_c - 0.5 + (i + 0.5) / N
            w = math.cos(math.radians(la))
            for j in range(N):
                lo = lo_c - 0.5 + (j + 0.5) / N
                tot += w
                if g.contains(Point(lo, la)):
                    ins += w
        P["region_share_recomputed"] = round(ins / tot, 4)
        ok(abs(ins / tot - P["region"]["share_of_cell"]) < 0.02 and (ins / tot < 0.5) == (P["region"]["phrase"] == "at the edge of"),
           f"base #{P['number']}: share of the twin cell inside {P['region']['region']} recomputed", (round(ins / tot, 4), P["region"]["share_of_cell"]))
except Exception as exc:  # noqa
    ok(False, "region share recompute failed", exc)

# zone distances from the pole (for 'near the south pole')
mb_lat = col("moon_base.bin", "lat")
zone_far = {}
for mid in ("rover", "lunar_base"):
    tws = twins[mid]["twins"]
    zone_far[mid] = max((90 + t["lat"]) * math.pi / 180 * R_M for t in tws)
FACTS["twin_max_km_from_pole"] = zone_far

# ---------------------------------------------------------------- the texts
ap = argparse.ArgumentParser()
ap.add_argument("--transcripts", default=os.path.join(REPO, "app", "public", "audio", "transcripts.json"))
args = ap.parse_args()
with open(args.transcripts, encoding="utf-8") as fh:
    TX = json.load(fh)
NUMW = {1: "one", 2: "two", 3: "three", 4: "four", 5: "five"}
PREF = {"rover": "rover", "solar": "solar", "lunar_base": "base"}
TITLE = {"rover": "Rover", "solar": "Solar panels", "lunar_base": "Lunar base"}
TYPEW = {"Crater": "the crater {}", "Mons": "{}", "Rima": "{}, a lunar rille", "Catena": "{}, a chain of craters"}

for key, text in TX.items():
    w = len(text.split())
    ok(55 <= w <= 105, f"{key}: {w} words")
    low = text.lower()
    for bad in ("the five best", "the best", "best analog", "identical", "charge the same", "equally cold", "gently sloping", "proven"):
        ok(bad not in low, f"{key}: no '{bad}'")
    for m_ in re.finditer(r"\bnear\b ([^,.;:]*)", low):
        ok(False, f"{key}: 'near {m_.group(1)}' (rule 2: check the distance)")

rv = FACTS["rover"]["rule"]
for mid in ("rover", "solar", "lunar_base"):
    for P in FACTS[mid]["pairs"]:
        key = f"{PREF[mid]}_{P['number']}.mp3"
        t = TX[key]
        e, mo = P["earth"], P["moon"]
        ok(t.startswith(f"{TITLE[mid]}, analog {NUMW[P['number']]}."), f"{key}: opening")
        where = ", ".join(x for x in (e["region"], e["country"]) if x)
        ok(f"A site in {where}" in t, f"{key}: region/country '{where}'")
        if e["km_stored"] <= NEAREST_PLACE_MAX_KM:
            ok(f"about {say_int(e['km_spoken'])} kilometers {e['direction']} of {e['place']}" in t,
               f"{key}: Earth place '{say_int(e['km_spoken'])} km {e['direction']} of {e['place']}'", e)
        else:
            # farther than the screen names a place: country (and region), coordinates, and no place
            coords = (f"{num(abs(P['lat']), 1)} degrees {'north' if P['lat'] >= 0 else 'south'} and "
                      f"{num(abs(P['lon']), 1)} degrees {'east' if P['lon'] >= 0 else 'west'}")
            ok(t.split(". Its lunar twin")[0].endswith(f"A site in {where}, at {coords}"),
               f"{key}: place {e['km_stored']:.1f} km > {NEAREST_PLACE_MAX_KM:g} km: country/region and coordinates '{coords}' only", e)
            ok(not re.search(r"\b" + re.escape(e["place"]) + r"\b", t), f"{key}: the far place '{e['place']}' is not named", e)
            ok(not re.search(r"kilometers (north|south|east|west|northeast|northwest|southeast|southwest) of", t),
               f"{key}: no Earth distance to a place", e)
        ftw = TYPEW.get(mo["type"].split(",")[0], "{}").format(mo["feature"])
        ok(f"about {mo['km_spoken']} kilometers from {ftw}" in t, f"{key}: lunar feature '{mo['km_spoken']} km from {ftw}'", mo)
        if mid == "rover":
            s, r = P["slope_deg"], P["roughness_m"]
            ok(f"{s['earth']} degrees on Earth and {s['moon']} on the Moon" in t, f"{key}: slope {s}")
            ok(f"{r['earth']} meters on Earth and {r['moon']} on the Moon" in t, f"{key}: roughness {r}")
            ok(f"Similarity: {strip(Decimal(P['similarity']))} out of 100" in t or f"Similarity: {P['similarity']} out of 100" in t, f"{key}: similarity {P['similarity']}")
            ok(f"one of the {say_int(rv['tied_n'])} sites tied at the top" in t, f"{key}: tie count {rv['tied_n']}")
        if mid == "solar":
            if P["toa_earth"] == P["toa_moon"]:
                ok(f"both get {P['toa_earth']} kilowatt hours" in t, f"{key}: sunlight both {P['toa_earth']}")
            else:
                ok(f"the site gets {P['toa_earth']} kilowatt hours per square meter a day, and its twin {P['toa_moon']}" in t,
                   f"{key}: sunlight {P['toa_earth']} / {P['toa_moon']}")
            ok(f"only {P['ground']} of them reach the ground" in t, f"{key}: ground {P['ground']}")
            ok(f"{P['loss_pct']} percent is lost" in t, f"{key}: lost {P['loss_pct']}")
            ok(f"clear-sky fraction of {P['clear']}" in t, f"{key}: clear sky {P['clear']}")
            simsay = "over 99.99" if P["similarity"] == "100.00" else P["similarity"]
            ok(f"Similarity: {simsay} out of 100" in t, f"{key}: similarity {simsay}")
            fr = {"half": 0.5, "three fifths": 0.6, "two thirds": 2 / 3, "seven tenths": 0.7, "three quarters": 0.75, "four fifths": 0.8}
            m_ = re.search(r"see about ([a-z ]+?) of the sky", t)
            ok(m_ and abs(fr[m_.group(1)] - P["clear_raw"]) <= 0.02 and min(fr, key=lambda q: abs(fr[q] - P["clear_raw"])) == m_.group(1),
               f"{key}: plain fraction '{m_.group(1) if m_ else None}' for {P['clear']}")
        if mid == "lunar_base":
            ok(P["region"]["text"] in t, f"{key}: region phrase '{P['region']['text']}'")
            ok(f"{P['tmin_diff_K']} kelvin lower" in t, f"{key}: kelvin {P['tmin_diff_K']}")
            ok(P["tmin_moon_K"] < P["tmin_earth_K"], f"{key}: the Moon's coldest is lower")
            ok(f"percentile {P['tmin_pct'][0]} on Earth and {P['tmin_pct'][1]} on the Moon" in t, f"{key}: tmin pct {P['tmin_pct']}")
            ok(f"at {P['amp_pct'][0]} and {P['amp_pct'][1]}" in t, f"{key}: swing pct {P['amp_pct']}")
            if P["slope"][2] <= 2.0:
                ok(f"{P['slope'][0]} degrees on Earth and {P['slope'][1]} on the Moon" in t, f"{key}: slope {P['slope']}")
            else:
                ok("slope" not in t.lower(), f"{key}: no slope sentence (difference {P['slope'][2]:.3f} > tolerance 2)")
            ok(f"Similarity: {P['similarity']} out of 100" in t, f"{key}: similarity {P['similarity']}")

# intros
ok(f"five of the {say_int(rv['tied_n'])} sites tied at the top of our model, chosen to be spread across the world" in TX["m1_rover.mp3"], "m1_rover: tie sentence with N")
for k, mid in (("m2_solar.mp3", "solar"), ("m3_base.mp3", "lunar_base")):
    ok("five of the highest-scoring analogs in our model" in TX[k] and FACTS[mid]["rule"]["highest_scoring_the_rule_allows"], f"{k}: highest-scoring wording allowed")
    ok("half likeness and half suitability" in TX[k], f"{k}: order rule")
lb = missions["lunar_base"]["similarity"]["populations"]
ok(f"{say_int(lb['EARTH']['cells'])} candidates" in TX["m3_base.mp3"] and f"{lb['MOON']['cells']} lunar cells" in TX["m3_base.mp3"], "m3_base: populations")
ok("highest-scoring" not in TX["m1_rover.mp3"], "m1_rover: no 'highest-scoring'")

os.makedirs(os.path.dirname(OUT), exist_ok=True)


def _j(o):
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating,)):
        return float(o)
    if isinstance(o, (np.bool_,)):
        return bool(o)
    return str(o)


with open(OUT, "w", encoding="utf-8") as fh:
    json.dump({"facts": FACTS, "results": RESULTS}, fh, ensure_ascii=False, indent=1, default=_j)
bad = [r for r in RESULTS if not r["ok"]]
print(json.dumps(FACTS, ensure_ascii=False, indent=1, default=_j)[:200000])
print(f"\n{len(RESULTS)} checks, {len(bad)} failed")
for r in bad:
    print("FAIL:", r["check"], "|", r["detail"][:300])
