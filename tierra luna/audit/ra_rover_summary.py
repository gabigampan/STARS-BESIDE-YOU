"""ra_rover_summary: assemble docs/stats_audit/9_reauditoria_rover.json from the ra_rover_* outputs.
    python ra_rover_summary.py <commit audited>"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")
REPO = os.path.dirname(os.path.dirname(HERE))
L = lambda f: json.load(open(os.path.join(OUT, f), encoding="utf-8"))
A = L("ra_rover_audit.json"); CF = L("ra_rover_config.json"); W = L("ra_rover_weights.json")
MC = L("ra_rover_mc_corrected_first_audit.json"); MM = L("ra_rover_mc_audited_morning_first_audit.json")
V = json.load(open(os.path.join(HERE, "ra_rover_verdicts.json"), encoding="utf-8"))
for d in (MC, MM):
    d.pop("records", None)


def stab(mc, w):
    wp = {x["id"]: x for x in w["per_analog"]}
    return [{"id": "E%d" % a["id"], "twin": "M%d" % a["twin"], "in_five_share_pct": round(100 * a["in_five_share"], 1),
             "in_top20_share_pct_published_rank": round(100 * a["top20_share_rank"], 1),
             "in_top20_share_pct_tie_aware": round(100 * a["top20_share_tie_aware"], 1),
             "in_top50_share_pct_published_rank": round(100 * a["top50_share_rank"], 1),
             "in_top50_share_pct_tie_aware": round(100 * a["top50_share_tie_aware"], 1),
             "in_tied_top_group_share_pct": round(100 * a["tied_top_share"], 1), "twin_kept_share_pct": round(100 * a["twin_kept_share"], 1),
             "passes_funnel_share_pct": round(100 * a["passes_share"], 1),
             "weights_pm10_stays_in_five": f'{wp[a["id"]]["stays_in_five"]}/{wp[a["id"]]["of"]}',
             "weights_pm10_stays_in_five_and_keeps_twin": f'{wp[a["id"]]["stays_in_five_and_keeps_twin"]}/{wp[a["id"]]["of"]}'} for a in mc["per_analog"]]


S = {"mission": "rover", "commit_audited": sys.argv[1] if len(sys.argv) > 1 else None,
     "verdicts": V["verdicts"], "overall": V["overall"],
     "stability": {"simulations": MC["runs"], "seed": MC["seed"], "sigma_set": "first audit (audit/p3_montecarlo.py; docs/stats_audit/3 F.3)",
                   "corrected": {"five": ["E%d" % i for i in MC["base_five"]], "per_analog": stab(MC, W["corrected"]),
                                 "five_repeat_exact_pct": round(100 * MC["five_repeat_exact_share"], 1),
                                 "five_repeat_as_set_pct": round(100 * MC["five_repeat_as_set_share"], 1), "distinct_fives": MC["distinct_fives"],
                                 "tied_group": MC.get("tied_group"), "within_of_fifth_median": MC["within_of_fifth_median"],
                                 "within_of_fifth_p5_p95": MC["within_of_fifth_p5_p95"],
                                 "weights_pm10_same_five": f'{W["corrected"]["same_five_count"]}/{W["corrected"]["n_perturbations"]}'},
                   "morning": {"five": ["E%d" % i for i in MM["base_five"]], "per_analog": stab(MM, W["audited_morning"]),
                               "five_repeat_exact_pct": round(100 * MM["five_repeat_exact_share"], 1),
                               "five_repeat_as_set_pct": round(100 * MM["five_repeat_as_set_share"], 1), "distinct_fives": MM["distinct_fives"],
                               "within_of_fifth_median": MM["within_of_fifth_median"], "within_of_fifth_p5_p95": MM["within_of_fifth_p5_p95"],
                               "weights_pm10_same_five": f'{W["audited_morning"]["same_five_count"]}/{W["audited_morning"]["n_perturbations"]}'}},
     "validation": [{"site": x["name"], "role": x["role"], "cell": x.get("cell"), "unverified_coords": x.get("unverified_coords"),
                     "corrected_pct": x.get("pct"), "corrected_tie_aware_pct": x.get("tie_aware_pct"),
                     "morning_pct": next((y.get("pct") for y in A["validation_morning"]["sites"] if y["name"] == x["name"]), None)}
                    for x in A["validation_corrected"]["sites"]],
     "validation_summary": {"corrected_verified": A["validation_corrected"]["summary_verified_published_rank"],
                            "morning_verified": A["validation_morning"]["summary_verified_published_rank"],
                            "corrected_all": A["validation_corrected"]["summary_published_rank"],
                            "morning_all": A["validation_morning"]["summary_published_rank"]},
     "difference_table": A["difference_table_corrected"],
     "difference_table_morning": A["difference_table_morning"],
     "suitability_saturation": A["suitability_saturation"],
     "five_rule_exclusions": A["five_rule_exclusions"],
     "bardenas_tabernas": {k: {kk: v[kk] for kk in ("cell", "criterion_by_criterion", "suitability_check", "points_below_top_final", "n_ranked_better")} for k, v in A["bardenas_tabernas"].items()},
     "slope_minimum": {k: {kk: A[k][kk] for kk in A[k] if not kk.startswith("validation_tie")} for k in ("slope_min_study_rule_1123_tolerance_score", "slope_min_study_corrected")},
     "faults": V["faults"],
     "scripts": ["tierra luna/audit/ra_rover_common.py", "ra_rover_config.py", "ra_rover_audit.py", "ra_rover_fallback.py", "ra_rover_weights.py",
                 "ra_rover_mc.py", "ra_rover_texts.py", "ra_rover_summary.py"]}
json.dump(S, open(os.path.join(REPO, "docs", "stats_audit", "9_reauditoria_rover.json"), "w", encoding="utf-8"), indent=1, ensure_ascii=False)
print(json.dumps(S["stability"], indent=1)[:4000])
