"""p3_percentile_unc (point F.3): how much the Lunar base percentiles move when the
underlying temperatures carry their documented uncertainty.
Populations: Earth = points passing the Lunar base funnel (2,419); Moon = the 280 cells
of the nine NASA regions. 200 draws, seed fixed, same sigmas as p3_montecarlo (Earth tmin
1.39 K, Earth amplitude sqrt(2) K, Moon tmin 1 K, Moon amplitude sqrt(2) K); the funnel is
held fixed here so that only the percentile arithmetic is measured.
Output: out/p3_percentile_unc.json. Run: python p3_percentile_unc.py"""
import numpy as np

from p3_common import dump, funnel, load_params, load_tables, lunar_base_zone_ids, midrank_pct, num

SIG = {("EARTH", "tmin_c"): 1.39, ("EARTH", "lst_diurnal_amp_k"): 2 ** 0.5,
       ("MOON", "tmin_c"): 1.0, ("MOON", "lst_diurnal_amp_k"): 2 ** 0.5}


def main():
    P = load_params()
    T = load_tables(P)
    pi = np.flatnonzero(funnel(T["EARTH"], "EARTH", "lunar_base", P))
    zpos = np.searchsorted(T["MOON"]["id"].to_numpy(), lunar_base_zone_ids())
    rng = np.random.default_rng(20261115)
    out = {"earth_population": int(len(pi)), "moon_population": int(len(zpos)),
           "one_rank_step_points": {"EARTH": round(100 / len(pi), 4), "MOON": round(100 / len(zpos), 4)}}
    for (body, c), s in SIG.items():
        v = num(T[body], c)[pi if body == "EARTH" else zpos]
        p0 = midrank_pct(v)
        sh = []
        for _ in range(200):
            sh.append(np.abs(midrank_pct(v + rng.standard_normal(v.size) * s) - p0))
        sh = np.array(sh)
        rng_v = np.nanquantile(v, [0.05, 0.5, 0.95])
        out[f"{body}:{c}"] = {"sigma": round(s, 3), "value_q05_q50_q95": [round(float(x), 2) for x in rng_v],
                              "abs_percentile_shift_median": round(float(np.nanmedian(sh)), 2),
                              "abs_percentile_shift_p90": round(float(np.nanquantile(sh, 0.9)), 2),
                              "share_shift_gt_5": round(float(np.nanmean(sh > 5)), 3),
                              "share_shift_gt_10": round(float(np.nanmean(sh > 10)), 3)}
        print(body, c, out[f"{body}:{c}"])
    print(dump("p3_percentile_unc.json", out))


if __name__ == "__main__":
    main()
