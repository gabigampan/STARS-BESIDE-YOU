"""Re-audit Lunar base, item 6: Monte Carlo of input uncertainty, own code path (p5_common via
ra_base_common), with the sigma table of the first audit (p3_montecarlo.SIGMA, sources there and in
docs/stats_audit/3_robustez_validacion_ranking.md F.3). Each run: independent Gaussian noise per cell
on the inputs, then the whole chain again (funnel, suitability, percentiles within the perturbed
populations, twins, final, rank, the five by the set's own rule).
Run: python "tierra luna/audit/ra_base_montecarlo.py" SET [RUNS=200] [SEED=20261115]
 -> out/ra_base_mc_<SET>.json"""
import json, os, sys, time
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ra_base_common as R
import p5_common as C
from p3_montecarlo import SIGMA  # the first audit's documented uncertainties (only the table is reused)

# p3 column keys -> the p5 variable names (slope/roughness: the engine's columns after overrides)
COLS = {"elevation_m": "elevation_m", "slope": "slope_deg", "rough": "roughness_m", "tmin_c": "tmin_c",
        "irradiance_kwh_m2_day": "irradiance_kwh_m2_day", "lst_diurnal_amp_k": "lst_diurnal_amp_k",
        "rock_or_bare_frac": "rock_or_bare_frac"}


def perturb(T, rng):
    out = {}
    for body, df in T.items():
        d = df.copy()
        n = len(d)
        for (b, c), (kind, val, _) in SIGMA.items():
            if b != body or COLS[c] not in d.columns:
                continue
            e = rng.standard_normal(n) * val
            v = np.asarray(C.pd.to_numeric(d[COLS[c]], errors="coerce"), float)
            v = v * (1 + e) if kind == "rel" else v + e
            if c == "rock_or_bare_frac":
                v = np.clip(v, 0, 1)
            d[COLS[c]] = v
        out[body] = d
    return out


def near_fifth(r, five):
    pos = {int(i): k for k, i in enumerate(r["pass_ids"])}
    f5 = float(r["final_pub"][pos[five[-1]]])
    fp = r["final_pub"][np.isfinite(r["final_pub"])]
    return {str(t): int((np.abs(fp - f5) <= t).sum() - 1) for t in (0.1, 0.5, 1.0)}, f5


def main():
    set_name = sys.argv[1]
    runs = int(sys.argv[2]) if len(sys.argv) > 2 else 200
    seed = int(sys.argv[3]) if len(sys.argv) > 3 else 20261115
    P, _, _ = R.params_for_set(set_name)
    raw = R.load_raw_earth()
    T = C.load_tables(P); D = C.derived(T, P)
    r0 = C.run_mission(T, D, R.M, P)
    five0 = R.select_five(r0, P, T["EARTH"], raw)
    pos0 = {int(i): k for k, i in enumerate(r0["pass_ids"])}
    twin0 = {e: int(r0["twin"][pos0[e]]) for e in five0}
    near0, f50 = near_fifth(r0, five0)
    rng = np.random.default_rng(seed)
    rec = []
    t0 = time.time()
    for k in range(runs):
        Tp = perturb(T, rng)
        Dp = C.derived(Tp, P)
        r = C.run_mission(Tp, Dp, R.M, P)
        five = R.select_five(r, P, Tp["EARTH"], raw)
        pos = {int(i): j for j, i in enumerate(r["pass_ids"])}
        rk = {e: (int(r["rank"][pos[e]]) if e in pos else -2) for e in five0}   # -2 fails funnel, 0 no twin
        tw = {e: (int(r["twin"][pos[e]]) if e in pos else -2) for e in five0}
        nf, f5 = near_fifth(r, five)
        rec.append({"five": five, "rank": rk, "twin": tw, "near_fifth": nf, "final_fifth": f5,
                    "n_pass": int(r["passed"].sum()), "n_ranked": int((r["rank"] > 0).sum())})
        if (k + 1) % 25 == 0:
            print(set_name, k + 1, round(time.time() - t0), flush=True)
    def share(f):
        return {e: round(sum(f(x, e) for x in rec) / len(rec), 3) for e in five0}
    summ = {
        "set": set_name, "runs": runs, "seed": seed, "five": five0, "twins": twin0,
        "baseline_near_fifth": near0, "baseline_final_fifth": f50,
        "share_in_five": share(lambda x, e: e in x["five"]),
        "share_top20": share(lambda x, e: 0 < x["rank"][e] <= 20),
        "share_top50": share(lambda x, e: 0 < x["rank"][e] <= 50),
        "share_twin_kept": share(lambda x, e: x["twin"][e] == twin0[e]),
        "share_fails_funnel": share(lambda x, e: x["rank"][e] == -2),
        "five_identical_set": round(sum(set(x["five"]) == set(five0) for x in rec) / runs, 3),
        "five_identical_order": round(sum(x["five"] == five0 for x in rec) / runs, 3),
        "median_near_fifth": {t: float(np.median([x["near_fifth"][t] for x in rec])) for t in ("0.1", "0.5", "1.0")},
        "sigma": {f"{b}:{c}": v for (b, c), v in SIGMA.items()},
    }
    print(json.dumps({k: v for k, v in summ.items() if k != "sigma"}))
    R.dump({"summary": summ, "runs": rec}, f"ra_base_mc_{set_name}.json")


if __name__ == "__main__":
    main()
