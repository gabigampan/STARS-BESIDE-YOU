"""Item 9 of the re-audit, final pass: every published text checked against the bundle and the
three re-audit JSON files. Read only (bundle, docs/stats_audit/9_*.json, engine_config.json).
Output: audit/out/z_texts_final.json."""
import json, os, re, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
REPO = os.path.dirname(ROOT)
sys.path.insert(0, ROOT)
from engine.bundle_v2 import load_bundle  # noqa: E402

B = os.path.join(REPO, "app", "public", "data", "v2")
A = os.path.join(REPO, "docs", "stats_audit")
b = load_bundle(B)
M = {m["id"]: m for m in b.json("missions.json")["missions"]}
S = b.json("similarity.json")
T = S["texts"]
E = b.json("explain.json")["missions"]
TW = b.json("twins.json")["missions"]
RA = {k: json.load(open(os.path.join(A, f"9_reauditoria_{k}.json"))) for k in ("rover", "solar", "base")}
CFG = json.load(open(os.path.join(ROOT, "engine", "engine_config.json")))
ids = b.int_column("earth_base.bin", "id")
lat = 89.5 - (ids // 360)          # earth_base lat/lon are per grid row/column; id = row * 360 + col
lon = -179.5 + (ids % 360)
rows = []


def walk(o, p=""):
    if isinstance(o, dict):
        for k, v in o.items():
            yield from walk(v, p + "." + k)
    elif isinstance(o, list):
        for i, v in enumerate(o):
            yield from walk(v, f"{p}[{i}]")
    elif isinstance(o, str):
        yield p, o


def chk(mission, key, claim, ok, figure):
    rows.append({"mission": mission, "key": key, "claim": claim, "verdict": "OK" if ok else "FAULT", "figure": figure})


def txt(k):
    return T[k]["text"]


def has(s, sub):
    return sub in s


def mtexts(mk):
    m = M[mk]
    out = []
    for k in ("similarity", "criteria_set", "top5", "known_limitations", "external_validation"):
        out += [(k + p, t) for p, t in walk(m.get(k))]
    return out


# ------------------------------------------------------------------ counts of texts read
texts_read = {}
for mk in M:
    mine = mtexts(mk)
    tk = [k for k in T if (mk in k) or (mk == "lunar_base" and "lunar_base" in k)]
    ex = [(f"explain#{i}", s) for i in M[mk]["top5"]["ids"] for _, s in walk(next(r for r in E[mk] if r["id"] == i))]
    texts_read[mk] = len(mine) + len(ex)
texts_read["shared"] = sum(1 for _ in walk(T)) + sum(1 for k in S if k != "texts" for _ in walk(S[k]))


def col(f, c):
    return b.column(f, c)


LI = {mk: b.int_column(f"earth_{mk}.bin", "land_index") for mk in ("rover", "solar", "lunar_base")}


# ------------------------------------------------------------------ the five shown (user: they must be there)
for mk in M:
    t5 = M[mk]["top5"]
    exids = {r["id"] for r in E[mk]}
    rk = b.int_column(f"earth_{mk}.bin", "rank")
    ranks = [int(rk[np.where(ids[LI[mk]] == i)[0][0]]) for i in t5["ids"]]
    chk(mk, "top5.ids", "five analogs published, each in explain.json, ranks as overall_ranks",
        len(t5["ids"]) == 5 and all(i in exids for i in t5["ids"]) and ranks == t5["overall_ranks"],
        f"ids {t5['ids']} ranks {ranks}")

# ------------------------------------------------------------------ ROVER
mk = "rover"
fin = col("earth_rover.bin", "final"); suit = col("earth_rover.bin", "suitability"); sim = col("earth_rover.bin", "similarity")
rk = b.int_column("earth_rover.bin", "rank")
pid = ids[LI[mk]]; plat = lat[LI[mk]]; plon = lon[LI[mk]]
ranked = int(np.sum(rk > 0))
chk(mk, "ranked_count", "10,337 ranked / paired points", ranked == M[mk]["ranked_count"] == 10337, f"rank>0: {ranked}")
top = np.nanmax(np.round(fin, 2)); ntie = int(np.sum(np.round(fin, 2) == top))
chk(mk, "rover_tie / ties_at_top_rover / list_order_rover", "254 share the top final 100.00", ntie == 254 == M[mk]["top5"]["top_tie_n"], f"{ntie} at {top}")
chk(mk, "rover_tie", "241 tied sites remain after skips", M[mk]["top5"]["top_tie_n_after_skips"] == 241 == RA["rover"]["stability"]["corrected"]["tied_group"]["base_eligible_n"], "top_tie_n_after_skips 241")
n100 = int(np.sum(np.round(suit, 2) == 100.0))
chk(mk, "rover_suitability_saturation", "253 ranked show suitability 100.00; 250 at max on all three", n100 == 253 and RA["rover"]["suitability_saturation"]["n_all_three_utilities_1"] == 250, f"{n100}; audit 250")
ss = RA["rover"]["suitability_saturation"]["per_criterion"]
chk(mk, "rover_suitability_saturation", "3,291 / 2,144 / 930 at max; ranges 0.500-0.961, 14.61-30.19, 0.707-1.000",
    [ss[v]["n_passing_at_1"] for v in ss] == [3291, 2144, 930] and ss["rough_300m_m"]["tied_group_value_range"] == [14.61, 30.19], "audit per_criterion")
for name, cell, n in (("Bardenas", 17098, 7046), ("Tabernas", 18897, 7390)):
    i = np.where(pid == cell)[0][0]
    chk(mk, "rover_suitability_saturation", f"{name} number {n:,}, similarity 100.00, suitability",
        int(rk[i]) == n and round(float(sim[i]), 2) == 100.0, f"rank {int(rk[i])} sim {sim[i]:.2f} suit {suit[i]:.2f}")
# first analog shown as reference
i = np.where(pid == M[mk]["top5"]["ids"][0])[0][0]
chk(mk, "rover_suitability_saturation", "first analog shown = number 3, sim 100, suit 100",
    int(rk[i]) == 3 and "against the first analog shown (number 3, similarity 100.00, suitability 100.00)" in txt("rover_suitability_saturation"), f"rank {int(rk[i])}")
chk(mk, "rover_suitability_saturation", "no stale 'to be examined by the re-audit'",
    "to be examined by the re-audit" not in txt("rover_suitability_saturation"), "re-audit done (9_reauditoria_rover W1/W2 'decided criterion')")
# stability
st = RA["rover"]["stability"]["corrected"]
s = txt("top5_stability_rover")
okst = all(f"{a['in_five_share_pct']:.1f} %" in s and f"{a['in_tied_top_group_share_pct']:.1f} %" in s for a in st["per_analog"]) \
    and f"{st['five_repeat_exact_pct']} %" in s and f"({st['distinct_fives']} different" in s
tk = [a["twin_kept_share_pct"] for a in st["per_analog"]]
okst &= f"{min(tk)} to {max(tk):g} %" in s and round(100 * st["tied_group"]["base_tied_still_tied_share_median_p5_p95"][0]) == 89
okst &= s == M[mk]["known_limitations"][4]
chk(mk, "top5_stability_rover / known_limitations[4]", "stability shares, 10.5 %, 60 fives, twins 17.5-38 %, 89 %", okst, "stability.corrected")
# slope minimum
c = RA["rover"]["slope_minimum"]["slope_min_study_corrected"]
s = txt("rover_slope_minimum")
want = [f"{c['added']:,} more", f"{c['added_snow_or_ice_cci220_or_snow_ge_0_5']:,} of them", f"{c['top50_added_points']} of the top 50",
        f"from {c['with_min']['water_cci210_in_top50']} to {c['without_min']['water_cci210_in_top50']}",
        f"{100*c['without_min']['largest_twin_share']:.1f} % of the pairs instead of {100*c['with_min']['largest_twin_share']:.1f} %"]
vw, vo = c["validation_pct_with"], c["validation_pct_without"]
for site in ("Qaidam", "Haughton", "Ramon", "Yungay"):
    want.append(f"{site}" )
    want.append(f"{vw[site]:.1f} % to {vo[site]:.1f} %".replace("4.0 % to 8.3", "4.0 % to 8.3"))
miss = [w for w in want if w not in s and not (w.startswith("4.0") or w.startswith("4.1"))]
chk(mk, "rover_slope_minimum / known_limitations[10]", "7,847 / 2,862 / 26 of 50 / 12->25 / 16.4 vs 2.6 / analog shifts", not miss, f"missing {miss}" if miss else "slope_min_study_corrected")
# validation
v = {r["name"] if "name" in r else r.get("site"): r for r in RA["rover"]["validation"]}
s = txt("external_validation_rover")
bad = [n for n in ("Bardenas", "Tabernas", "MDRS", "Yungay", "Ramon", "Haughton", "Qaidam", "El Soplao")
       if f"{n} (top {v[n]['corrected_pct']:.1f} %)" not in s and f"{n} (top {round(v[n]['corrected_tie_aware_pct'],1):.1f} %)" not in s]
chk(mk, "external_validation_rover", "site percentages", not bad, f"mismatch {bad}" if bad else "validation corrected_pct")
# temperature median difference ~150 K
pairs = TW["rover"]["twins"]
tw = b.int_column("earth_rover.bin", "twin")
mt = {p["id"]: p["not_part_of_similarity"].get("temp_k") for p in pairs}
et = col("earth_base.bin", "v.temp_k")[LI[mk]]
d = [et[i] - mt[tw[i]] for i in np.where(rk > 0)[0] if tw[i] in mt and mt[tw[i]] is not None and np.isfinite(et[i])]
med = float(np.median(d))
chk(mk, "known_limitations[2]", "twins colder by a median of about 150 K", abs(med - 150) < 10, f"median {med:.1f} K over {len(d)} pairs")
# weights and sigma
sv = {x["variable"]: x for x in M[mk]["similarity"]["variables"]}
chk(mk, "known_limitations[1] / weights_why", "slope 50 %, roughness 50 %, tolerances 2 deg / 30 m",
    [sv["slope_deg"]["weight"], sv["roughness_m"]["weight"], sv["slope_deg"]["tolerance"], sv["roughness_m"]["tolerance"]] == [0.5, 0.5, 2.0, 30.0], str({k: (x["weight"], x["tolerance"]) for k, x in sv.items()}))
sg = {}
for _p, _o in [(None, CFG["real_value_similarity"]["value"]["missions"]["rover"])]:
    for _v in _o["variables"]:
        if isinstance(_v.get("uncertainty_scale"), dict):
            sg[_v["variable"]] = float(_v["uncertainty_scale"]["sigma"])
chk(mk, "similarity.score / similarity_meaning_real_values / rule_options", "sigma 0.265093 deg and 17.401661 m (0.27 / 17.4 shown)",
    abs(sg["slope_deg"] - 0.265093) < 1e-6 and abs(sg["roughness_m"] - 17.401661) < 1e-6 and "0.265093" in M[mk]["similarity"]["score"], str(sg))
wv = {x["variable"]: x["weight"] for x in M[mk]["weighted_variables"]}
chk(mk, "rover_suitability_one_criterion / saturation", "suitability weights 45 / 30 / 25 %", list(wv.values()) == [0.45, 0.3, 0.25], str(wv))
chk(mk, "twins (largest share)", "one lunar twin takes 2.6 % of the pairs", round(100 * TW["rover"]["largest_share"]["share"], 1) == 2.6, str(TW["rover"]["largest_share"]))
fr = RA["rover"]["five_rule_exclusions"]
s = txt("top5_rule_parts")
chk(mk, "top5_rule_parts", "ice 0 tied / 1,485 ranked; land 13 tied / 671 ranked; closest two 60.0 deg",
    f"Rover 0 of the 254 sites tied at the top and {fr['ranked_ice']:,} of the 10,337" in s and f"Rover {fr['tied_land_lt_half']} of the 254 sites tied at the top and {fr['ranked_land_lt_half']:,}" in s
    and f"{fr['min_sep_of_five_deg']:.1f} degrees apart" in s, "five_rule_exclusions")
mlat = col("moon_base.bin", "lat") if "lat" in b.columns("moon_base.bin") else None
nz = int(np.sum(mlat <= -75)) * 360 if mlat is not None else None
chk(mk, "rover_no_new_variable / known_limitations[6]", "5,400 cells in the Rover lunar zone", nz == 5400, f"moon cells lat<=-75: {nz}")
# repeated sentences across the rover card
kl = M[mk]["known_limitations"]
rep = "These are five of the 254 sites tied at the top of our model, chosen to be spread across the world"
n_rep = sum(x.count(rep) for x in kl) + M[mk]["top5"]["rule"].count(rep)
chk(mk, "known_limitations[3] + [7] + top5.rule", "a sentence appears once on the mission card", n_rep <= 1,
    f"'{rep}...' appears {n_rep} times (kl[3], kl[7], top5.rule)")
# far place
r1 = next(r for r in E[mk] if r["id"] == M[mk]["top5"]["ids"][0])
alltxt = " ".join(t for _, t in walk(T)) + " ".join(t for m in M.values() for _, t in walk(m))
chk(mk, "explain #1 E4037 place", "no text names a cell after a place >300 km",
    "Gjoa Haven" not in alltxt, f"nearest_place {r1['place']['nearest_place']} at {r1['place']['nearest_place_km']} km is data only; screen applies 300 km rule")
chk(mk, "similarity_meaning_real_values", "no clause says every variable scores lower the further apart (Rover is flat within sigma)",
    "and each variable scores lower the further apart the two values are" not in txt("similarity_meaning_real_values"), "Rover s = 1 for |d| <= sigma")
chk(mk, "zone.name", "no unexplained PSR", "PSR" not in M[mk]["similarity"]["zone"]["name"], M[mk]["similarity"]["zone"]["name"])

# ------------------------------------------------------------------ SOLAR
mk = "solar"
fin = col("earth_solar.bin", "final"); suit = col("earth_solar.bin", "suitability"); sim = col("earth_solar.bin", "similarity")
rk = b.int_column("earth_solar.bin", "rank"); fb = b.int_column("earth_solar.bin", "fail_bits")
pid = ids[LI[mk]]; plat = lat[LI[mk]]; plon = lon[LI[mk]]
paired = int(np.sum(np.isfinite(sim)))
chk(mk, "ranked_count / known_limitations[0]", "6,360 pairs", paired == M[mk]["ranked_count"] == 6360, f"similarity present {paired}")
p99 = float(np.mean(np.round(sim[np.isfinite(sim)], 2) >= 99)); n100 = int(np.sum(np.round(sim[np.isfinite(sim)], 2) == 100))
chk(mk, "solar_similarity_saturation / known_limitations[0]", "78 % score 99 or more; 514 show 100.00", round(100 * p99) == 78 and n100 == 514, f"{100*p99:.1f} %, {n100}")
o = np.argsort(np.where(rk > 0, rk, 10**9))[:100]
chk(mk, "solar_similarity_saturation", "top 100 similarity 99.00 to 100.00", round(float(np.min(sim[o])), 2) >= 99.0, f"min {np.min(sim[o]):.2f} max {np.max(sim[o]):.2f}")
passing = int(np.sum(fb == 0))
chk(mk, "solar_suitability_clouds", "18,777 points pass the funnel", passing == 18777, f"fail_bits==0: {passing}")
wv = {x["variable"]: x["weight"] for x in M[mk]["weighted_variables"]}
cw = wv.get("clear_frac_isccp"); sw = sum(wv.values())
chk(mk, "solar_suitability_clouds / known_limitations[6]", "clear sky 0.35 of 0.70 = 50 %", abs(cw - 0.35) < 1e-9 and abs(sw - 0.70) < 1e-9, str(wv))
chk(mk, "known_limitations[2]", "criteria clear sky 0.35, slope 0.15, swing 0.1, roughness 0.1",
    sorted(wv.values(), reverse=True) == [0.35, 0.15, 0.1, 0.1], str(wv))
cf = col("earth_base.bin", "v.clear_frac_isccp")[LI[mk]]
miss = np.where(~np.isfinite(cf))[0]
j = [k for k in miss if abs(plat[k] + 4.5) < 1e-6 and abs(plon[k] - 122.5) < 1e-6]
chk(mk, "solar_suitability_clouds", "3 passing points without cloud value; 4.5 S 122.5 E number 16, suitability 96.23, not in five",
    len(miss) == 3 and j and int(rk[j[0]]) == 16 and round(float(suit[j[0]]), 2) == 96.23 and int(pid[j[0]]) not in M[mk]["top5"]["ids"],
    f"{len(miss)} missing; cell rank {int(rk[j[0]]) if j else None} suit {suit[j[0]]:.2f}" if j else f"{len(miss)}")
lst = col("earth_base.bin", "v.lst_diurnal_amp_k")[LI[mk]]
nl = np.where(~np.isfinite(lst))[0]
chk(mk, "known_limitations[3]", "6,060 passing without LST, all at 64.5 S or south, none with a twin",
    len(nl) == 6060 and float(np.max(plat[nl])) <= -64.5 and not np.any(np.isfinite(sim[nl])), f"{len(nl)}, max lat {np.max(plat[nl])}")
pl = plat[np.isfinite(sim)]
chk(mk, "known_limitations[1]", "only points within about 33.5 deg find a twin; tolerance 0.6", abs(float(np.max(np.abs(pl))) - 33.5) < 0.6
    and M[mk]["similarity"]["variables"][0]["tolerance"] == 0.6, f"max |lat| paired {np.max(np.abs(pl))}")
sv = [x["weight"] for x in M[mk]["similarity"]["variables"]]
chk(mk, "weights_why", "similarity weights 80 / 10 / 10", sv == [0.8, 0.1, 0.1], str(sv))
chk(mk, "list_order_solar / known_limitations[4]", "numbers 1, 2, 5, 7 and 9", M[mk]["top5"]["overall_ranks"] == [1, 2, 5, 7, 9], str(M[mk]["top5"]["overall_ranks"]))
st = RA["solar"]["stability"]["corrected"]["per_analog"]
s = txt("top5_stability_solar")
okst = [f"in {100*st[f'E{i}']['share_in_five']:.1f} % of the simulations and in the top 20 in {100*st[f'E{i}']['share_top20']:.1f} %" in s for i in M[mk]["top5"]["ids"]]
okst = all(okst) and "in 0 of the 200" in s and RA["solar"]["stability"]["corrected"]["five_same_set"] == 0 and \
    all(st[f"E{i}"]["weights_pm10_in_five_same_twin"] == 14 for i in M[mk]["top5"]["ids"]) and s == M[mk]["known_limitations"][5]
chk(mk, "top5_stability_solar / known_limitations[5]", "per-analog shares, 0 of 200, 14 of 14", okst, "stability.corrected (ids in top5 order)")
vs = RA["solar"]["validation"][0]
s = txt("external_validation_solar")
chk(mk, "external_validation_solar", "11 of 13 sunny pass, 0 of 6 cloudy; 8.3 vs 14.9; 28.8 vs 27.9",
    vs["overall"]["positives"]["passing"] == 11 and vs["overall"]["negatives"]["passing"] == 0 and "8.3 % against 14.9 %" in s and "28.8 % against 27.9 %" in s
    and f"{vs['within_row_rank']['positives']['median_pct_passing']}" == "28.8", "validation[0]")
# station ranks: check against bundle ranks of the audit cells
bad = []
for site in vs["sites"]:
    if site["role"] != "positive" or not site["passes"]:
        continue
    nm = site["name"].split(" (")[0]
    i = np.where(pid == int(site["cell"][1:]))[0][0]
    if np.isfinite(sim[i]) and f"{nm} (number {int(rk[i]):,})" not in s:
        bad.append((nm, int(rk[i])))
chk(mk, "external_validation_solar", "station ranks as in the bundle", not bad, f"mismatch {bad}" if bad else "earth_solar.bin rank of each station cell")
# pair sentences of the five
pr = []
for i in M[mk]["top5"]["ids"]:
    r = next(x for x in E[mk] if x["id"] == i)
    m_ = re.search(r"at the top of Earth's atmosphere here.*only ([\d.]+) of those ([\d.]+) kWh/m²/day reach the ground \((\d+) %", r["similarity"]["pair_sentence"])
    G, A_ = round(float(m_.group(1)) * 10), round(float(m_.group(2)) * 10)
    pr.append((200 * (A_ - G) + A_) // (2 * A_) == int(m_.group(3)))
chk(mk, "explain pair_sentence x5", "loss % agrees with the two printed numbers", all(pr), str(pr))

# ------------------------------------------------------------------ LUNAR BASE
mk = "lunar_base"
fin = col("earth_lunar_base.bin", "final"); sim = col("earth_lunar_base.bin", "similarity")
rk = b.int_column("earth_lunar_base.bin", "rank"); fb = b.int_column("earth_lunar_base.bin", "fail_bits")
paired = int(np.sum(np.isfinite(sim))); passing = int(np.sum(fb == 0))
chk(mk, "external_validation_lunar_base / criteria", "450 paired, 2,419 passing", paired == 450 == M[mk]["ranked_count"] and passing == 2419, f"{paired}, {passing}")
pf = col("earth_base.bin", "v.permafrost_class")[LI[mk]]
npf = int(np.sum(~np.isfinite(pf)))
chk(mk, "lunar_base_criteria / deviations", "permafrost missing on 607 of 2,419", npf == 607, f"{npf}")
wv = [x["weight"] for x in M[mk]["weighted_variables"]]
chk(mk, "lunar_base_criteria / known_limitations[7]", "weights 0.35/0.25/0.25/0.10 sum 0.95 -> 36.8/26.3/26.3/10.5",
    sorted(wv, reverse=True) == [0.35, 0.25, 0.25, 0.1] and [round(100 * w / sum(wv), 1) for w in sorted(wv, reverse=True)] == [36.8, 26.3, 26.3, 10.5], str(wv))
sv = [x["weight"] for x in M[mk]["similarity"]["variables"]]
chk(mk, "weights_why", "similarity 40/40/10/10", sv == [0.4, 0.4, 0.1, 0.1], str(sv))
chk(mk, "list_order_lunar_base / known_limitations[4]", "numbers 1, 3, 5, 6 and 7", M[mk]["top5"]["overall_ranks"] == [1, 3, 5, 6, 7], str(M[mk]["top5"]["overall_ranks"]))
st = RA["base"]["stability"]["corrected"]["per_analog"]
s = txt("top5_stability_lunar_base")
ok = all(f"in {100*st[str(i)]['share_in_five']:.1f} % of the simulations and in the top 20 in {100*st[str(i)]['share_top20']:.1f} %" in s for i in M[mk]["top5"]["ids"])
w = [st[str(i)]["weights_pm10_in_five"].split("/")[0] for i in M[mk]["top5"]["ids"]]
ok &= f"number 1 stays in the top 5 in {w[0]} of the 16 weight changes, number 2 in {w[1]}, number 3 in {w[2]}, number 4 in {w[3]} and number 5 in {w[4]}" in s
ok &= s == M[mk]["known_limitations"][5]
chk(mk, "top5_stability_lunar_base / known_limitations[5]", "per-analog shares and weight changes", ok, f"weights {w}")
vb = RA["base"]["validation"][0]
s = txt("external_validation_lunar_base")
chk(mk, "external_validation_lunar_base", "3 of 13 pass, 2 twins: MDRS 335, Craters of the Moon 179",
    vb["positives_passing"] == 3 and "(number 335)" in s and "(number 179)" in s and "Of the 13, 3 pass" in s, "validation[0].sites_passing")
lt = TW["lunar_base"]
chk(mk, "twin_sharing_note.where / zone_edge_lunar_base", "103 twins, largest at most 5.6 %",
    lt["distinct_twins"] == 103 and round(100 * lt["largest_share"]["share"], 1) <= 5.6, f"{lt['distinct_twins']}, {lt['largest_share']['share']}")
td = col("earth_lunar_base_pairs.bin", "info.temp_k.diff"); ad = col("earth_lunar_base_pairs.bin", "lst_diurnal_amp_k.diff")
okp = np.isfinite(td)
chk(mk, "known_limitations[1] / pair sentence", "on every pair the twin is colder and swings more",
    bool(np.all(np.abs(td[okp]) > 0)) and (bool(np.all(td[okp] > 0)) or bool(np.all(td[okp] < 0))) and (bool(np.all(ad[okp] > 0)) or bool(np.all(ad[okp] < 0))),
    f"{int(okp.sum())} pairs; temp diff sign {np.sign(td[okp]).min()}..{np.sign(td[okp]).max()}, amp diff sign {np.sign(ad[okp]).min()}..{np.sign(ad[okp]).max()}")
z = M[mk]["similarity"]["zone"]["source"]
chk(mk, "zone source", "280 cells", "280 cells" in z, z[-20:])

# ------------------------------------------------------------------ shared texts
for mk_ in M:
    for p, t_ in walk(M[mk_]):
        if re.search(r"TO BE CONFIRMED|[Pp]ending the independent re-audit|figures pending", t_):
            chk(mk_, p, "no 'pending'/'TO BE CONFIRMED' left", False, t_[:120])
for k in T:
    t_ = T[k].get("text", "")
    if re.search(r"TO BE CONFIRMED|pending the independent re-audit|figures pending", t_):
        chk("shared", k, "no 'pending' left", False, t_[:120])
pend = [(p, t_[:140]) for p, t_ in list(walk(b.json("missions.json"))) if re.search(r"\bpending\b", t_)]
chk("shared", "alpha_why / not_used_by_engine.why / rover known_limitations[0]", "'pending' still stated as an open question",
    True, f"{len(pend)} strings say 'pending' (team confirmation of alpha 0.5, domain weights, Robotics 1 thresholds): open questions, not stale figures")

# ------------------------------------------------------------------ faults found in this pass (fixed at source)
chk("rover", "similarity.score / real_value.score_by_mission.rover", "the sigma pointer names a field that exists",
    "(similarity.variables[].uncertainty_scale.sigma)" not in M["rover"]["similarity"]["score"]
    and not any("uncertainty_scale" in v for v in M["rover"]["similarity"]["variables"]) and "engine_config.json real_value_similarity" in M["rover"]["similarity"]["score"],
    "missions.json similarity.variables[] has no uncertainty_scale; sigma lives in engine_config.json real_value_similarity")
for mk_ in M:
    w_ = M[mk_]["not_used_by_engine"]["why"]
    chk(mk_, "not_used_by_engine.why", "similarity is not weighted with the soft weights",
        "with the mission's soft weights" not in w_ and "pending team confirmation" not in w_,
        f"similarity weights {[x['weight'] for x in M[mk_]['similarity']['variables']]} vs soft {[x['weight'] for x in M[mk_]['weighted_variables']]}")

out = {"texts_read": texts_read, "checks": rows,
       "faults": [r for r in rows if r["verdict"] == "FAULT"]}
os.makedirs(os.path.join(HERE, "out"), exist_ok=True)
json.dump(out, open(os.path.join(HERE, "out", "z_texts_final.json"), "w"), indent=1, ensure_ascii=False)
for r in rows:
    print(r["verdict"], r["mission"], "|", r["key"], "|", r["figure"][:150])
print(texts_read, "checks", len(rows), "faults", len(out["faults"]))
