"""Metric 4: sensitivity of each mission to its team settings, computed in memory.

(a) each suitability weight x1.2 and x0.8, all weights then renormalised to their
    original sum (the suitability formula divides by the summed weight, so this is the
    same as changing only that weight); the pairing does not depend on weights, so only
    suitability, final and rank change;
(b) each numeric hard threshold (common gates and mission gates, min or max) x0.9 and
    x1.1; the whole mission is rerun through the engine (funnel, pairing, rank);
(c) each pairing tolerance x0.8 and x1.2 (its filter bound follows, bound = multiplier x
    tolerance); the whole mission is rerun.

Nothing is written outside validation/out/. Configuration variants are deep copies.
"""
from __future__ import annotations

import copy
import time
from typing import Dict, List

import numpy as np
import pandas as pd

from common import MISSIONS, context, run_mission_variant, spearman, write_csv
import mission_scoring  # noqa: E402 (common puts the project folder on sys.path)


def _ranked(res, ids):
    idx = np.flatnonzero(res.rank > 0)
    return idx[np.argsort(res.rank[idx])]


def compare(base, new, ids) -> Dict:
    """Overlap of the top 5 / top 50 and rank correlations of a variant against the base."""
    b, n = _ranked(base, ids), _ranked(new, ids)
    out = {}
    for k in (5, 50):
        out[f"top{k}_overlap"] = len(set(b[:k]) & set(n[:k]))
    # Spearman over the points ranked in both lists (their ranks in each list)
    common = np.intersect1d(b, n)
    out["spearman_all_common"] = spearman(base.rank[common], new.rank[common]) if len(common) > 2 else np.nan
    # Spearman over the base top 50 (their rank in the variant; unranked there -> after the last)
    b50 = b[:50]
    nr = np.where(new.rank[b50] > 0, new.rank[b50], len(n) + 1)
    out["spearman_base_top50"] = spearman(np.arange(1, len(b50) + 1), nr)
    out["number1_same"] = bool(len(b) and len(n) and b[0] == n[0] and base.twin_id[b[0]] == new.twin_id[n[0]])
    out["number1_new"] = f"E{int(ids[n[0]])}-M{int(new.twin_id[n[0]])}" if len(n) else ""
    return out


def weights_sensitivity(c: Dict) -> pd.DataFrame:
    from engine.suitability import evaluate_suitability, round_like_export
    from engine.pipeline import rank_scores
    earth = c["cells"]["EARTH"]
    ids = earth["id"].to_numpy()
    rows = []
    for m in MISSIONS:
        base = c["results"][m]
        alpha = float(base.alpha)
        soft = c["mission_cfg"]["missions"][m]["soft"]
        w0 = {v: float(s["weight"]) for v, s in soft.items()}
        tot = sum(w0.values())
        has_twin = base.twin_id >= 0
        # check: the base final is reproduced from the base suitability
        f0 = alpha * base.similarity_pct + (1 - alpha) * base.earth_suit.score
        assert np.allclose(np.where(has_twin, f0, np.nan), np.where(has_twin, base.final, np.nan), equal_nan=True)
        for v in soft:
            for f in (1.2, 0.8):
                w = dict(w0)
                w[v] *= f
                s = sum(w.values())
                w = {k: x * tot / s for k, x in w.items()}
                es = evaluate_suitability(earth, "EARTH", m, c["mission_cfg"], c["engine_cfg"], weights=w)
                frame = pd.DataFrame({"similarity_pct": base.similarity_pct, f"score_{m}": es.score})
                fin = mission_scoring.combine_with_similarity(frame, m, alpha=alpha).to_numpy(dtype=np.float64)
                fin = np.where(base.earth_gates.passed & has_twin, fin, np.nan)
                fp = round_like_export(fin, int(c["engine_cfg"].v("export_decimals")["score"]))
                new = copy.copy(base)
                new.rank = rank_scores(fp, ids)
                rec = {"mission": m, "change": "weight", "variable": v, "factor": f,
                       "value_from": w0[v], "value_to": round(w[v], 6),
                       "ranked": int((new.rank > 0).sum())}
                rec.update(compare(base, new, ids))
                rows.append(rec)
    return pd.DataFrame(rows)


def gate_variants(mcfg: Dict, m: str):
    """(where, variable, bound, value) of every numeric gate bound of a mission."""
    out = []
    for v, g in mcfg.get("common_gates", {}).items():
        for k in ("min", "max"):
            if isinstance(g.get(k), (int, float)):
                out.append(("common", v, k, float(g[k])))
    for v, g in mcfg["missions"][m].get("gates", {}).items():
        for k in ("min", "max"):
            if isinstance(g.get(k), (int, float)):
                out.append(("mission", v, k, float(g[k])))
    return out


def thresholds_sensitivity(c: Dict, log=print) -> pd.DataFrame:
    earth_ids = c["cells"]["EARTH"]["id"].to_numpy()
    rows = []
    for m in MISSIONS:
        base = c["results"][m]
        bpass = base.earth_gates.passed
        bpaired = (base.twin_id >= 0)
        for where, v, k, val in gate_variants(c["mission_cfg"], m):
            for f in (0.9, 1.1):
                mc = copy.deepcopy(c["mission_cfg"])
                if where == "common":
                    mc["common_gates"][v][k] = val * f
                else:
                    mc["missions"][m]["gates"][v][k] = val * f
                    core = (mc["missions"][m].get("components") or {}).get("core")
                    if core:  # lunar_base must stay an exact copy of its core block (engine check)
                        mc["missions"][core]["gates"][v][k] = val * f
                t = time.time()
                new = run_mission_variant(c, m, mission_cfg=mc)
                npass, npaired = new.earth_gates.passed, new.twin_id >= 0
                rec = {"mission": m, "change": "threshold", "variable": f"{where}:{v}:{k}", "factor": f,
                       "value_from": val, "value_to": round(val * f, 6),
                       "funnel_pass_base": int(bpass.sum()), "funnel_pass_new": int(npass.sum()),
                       "cells_entering": int((npass & ~bpass).sum()), "cells_leaving": int((bpass & ~npass).sum()),
                       "pairs_base": int(bpaired.sum()), "pairs_new": int(npaired.sum()),
                       "pairs_gained": int((npaired & ~bpaired).sum()), "pairs_lost": int((bpaired & ~npaired).sum()),
                       "twin_changed_on_kept_pairs": int((npaired & bpaired & (new.twin_id != base.twin_id)).sum())}
                rec.update(compare(base, new, earth_ids))
                rows.append(rec)
                log(f"  threshold {m} {v} {k} x{f}: {time.time() - t:.1f}s")
    return pd.DataFrame(rows)


def tolerance_sensitivity(c: Dict, log=print) -> pd.DataFrame:
    earth_ids = c["cells"]["EARTH"]["id"].to_numpy()
    rv0 = c["engine_cfg"].v("real_value_similarity")
    rows = []
    for m in MISSIONS:
        base = c["results"][m]
        bpaired = base.twin_id >= 0
        for q, var in enumerate(rv0["missions"][m]["variables"]):
            for f in (0.8, 1.2):
                rv = copy.deepcopy(rv0)
                rv["missions"][m]["variables"][q]["tolerance"] = float(var["tolerance"]) * f
                t = time.time()
                new = run_mission_variant(c, m, real_settings=rv)
                npaired = new.twin_id >= 0
                rec = {"mission": m, "change": "tolerance", "variable": var["variable"], "role": var["role"], "factor": f,
                       "value_from": float(var["tolerance"]), "value_to": round(float(var["tolerance"]) * f, 6),
                       "pairs_base": int(bpaired.sum()), "pairs_new": int(npaired.sum()),
                       "pairs_gained": int((npaired & ~bpaired).sum()), "pairs_lost": int((bpaired & ~npaired).sum()),
                       "twin_changed_on_kept_pairs": int((npaired & bpaired & (new.twin_id != base.twin_id)).sum())}
                rec.update(compare(base, new, earth_ids))
                rows.append(rec)
                log(f"  tolerance {m} {var['variable']} x{f}: {time.time() - t:.1f}s")
    return pd.DataFrame(rows)


def run(log=print) -> Dict:
    c = context()
    w = weights_sensitivity(c)
    write_csv(w, "m4_sensitivity_weights.csv")
    log("weights done")
    t = thresholds_sensitivity(c, log)
    write_csv(t, "m4_sensitivity_thresholds.csv")
    tol = tolerance_sensitivity(c, log)
    write_csv(tol, "m4_sensitivity_tolerances.csv")
    summ = []
    for m in MISSIONS:
        ww, tt, oo = w[w.mission == m], t[t.mission == m], tol[tol.mission == m]
        summ.append({"mission": m,
                     "weights_min_top5_overlap": int(ww.top5_overlap.min()), "weights_min_top50_overlap": int(ww.top50_overlap.min()),
                     "weights_min_spearman_all": float(ww.spearman_all_common.min()),
                     "weights_number1_changes": int((~ww.number1_same).sum()), "weights_variants": int(len(ww)),
                     "thresholds_max_entering": int(tt.cells_entering.max()), "thresholds_max_leaving": int(tt.cells_leaving.max()),
                     "thresholds_number1_changes": int((~tt.number1_same).sum()), "thresholds_variants": int(len(tt)),
                     "tolerances_max_gained": int(oo.pairs_gained.max()), "tolerances_max_lost": int(oo.pairs_lost.max()),
                     "tolerances_number1_changes": int((~oo.number1_same).sum()), "tolerances_variants": int(len(oo))})
    s = pd.DataFrame(summ)
    write_csv(s, "m4_sensitivity_summary.csv")
    return {"summary": s.to_dict("records")}


if __name__ == "__main__":
    import json
    print(json.dumps(run(), indent=1, default=str))
