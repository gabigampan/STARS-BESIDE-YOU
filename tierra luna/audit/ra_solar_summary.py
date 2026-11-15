"""Re-audit Solar panels: machine-readable summary docs/stats_audit/9_reauditoria_solar.json from the outputs.

    python -I ra_solar_summary.py <commit audited> <verdicts json file>
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")
REPO = os.path.dirname(os.path.dirname(HERE))


def J(n):
    p = os.path.join(OUT, n)
    return json.load(open(p, encoding="utf-8")) if os.path.exists(p) else None


def main():
    commit = sys.argv[1]
    v = json.load(open(sys.argv[2], encoding="utf-8"))
    mc_c, mc_m = J("ra_solar_mc_corrected.json"), J("ra_solar_mc_audited_morning.json")
    rob_c, rob_m = J("ra_solar_robustness_corrected.json"), J("ra_solar_robustness_audited_morning.json")
    val = J("ra_solar_validation.json")
    rc = J("ra_solar_recompute_final_corrected.json")

    def stab(mc, rob):
        if not mc:
            return None
        return {"runs": mc["runs"], "five_exact_same_order": mc["five_exact_same_order"], "five_same_set": mc["five_same_set"],
                "points_within_of_fifth_baseline": mc["baseline_points_within_of_fifth"], "points_within_of_fifth_runs_median": {k: x["median"] for k, x in mc["points_within_of_fifth_runs"].items()},
                "per_analog": {e: {**x, "weights_pm10_in_five": rob["per_analog"][e]["in_five"] if rob else None,
                                   "weights_pm10_in_five_same_twin": rob["per_analog"][e]["in_five_with_same_twin"] if rob else None,
                                   "weights_pm10_of": rob["per_analog"][e]["of"] if rob else None} for e, x in mc["per_analog"].items()},
                "sigma": mc["sigma"], "sigma_isccp_illustrative": mc["sigma_isccp_illustrative"]}
    out = {"mission": "solar", "commit_audited": commit, "verdicts": v["verdicts"], "overall": v["overall"],
           "stability": {"corrected": stab(mc_c, rob_c), "audited_morning": stab(mc_m, rob_m)},
           "validation": [{"criteria_set": s, "passing": val[s]["passing"], "overall": val[s]["overall"], "within_row_rank": val[s]["within_row_rank"],
                           "within_row_suitability": val[s]["within_row_suitability"],
                           "sites": [{k: x[k] for k in ("site_id", "role", "name", "cell", "passes", "rank_pct", "rank_pct_within_row", "suit_pct_within_row", "twin")} for x in val[s]["sites"]]}
                          for s in ("corrected", "audited_morning")],
           "difference_table": rc["difference_table"] if rc else None,
           "faults": v["faults"]}
    p = os.path.join(REPO, "docs", "stats_audit", "9_reauditoria_solar.json")
    json.dump(out, open(p, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print("wrote", p)


if __name__ == "__main__":
    main()
