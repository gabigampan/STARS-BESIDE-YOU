"""Metric 3b: precision and recall on the three external site lists of the corrected model.

Lists (read, never edited):
  * Rover: the positive and negative names of rover_preset.py (MOBILITY_POSITIVES,
    MOBILITY_MISMATCHES, the lists validate_rover_ranking uses), located through the team
    benchmark data/benchmark/analog_benchmark.csv (cell, verified or not) as metric 3 does;
    the site's place in the ranking comes from m3_benchmark_sites.csv (run m3 first).
  * Solar panels: data/benchmark/validation_sites_solar.csv (research r4).
  * Lunar base: data/benchmark/validation_sites_lunar_base.csv (research r4).
For the two r4 lists the ranking of each site is computed by research/r4_rank_sites.py
on the shipped bundle (imported; its output is redirected to validation/out/).

Definitions (stated in docs/VALIDATION.md section 3):
  predicted positive under T = the site's 1-degree cell passes the funnel, has a lunar
  twin, and its published rank is within the best T % of the ranked list;
  recall    = predicted-positive positives / all positives of the list;
  precision = predicted-positive positives / all predicted-positive sites of the list
              (positives + negatives; the rest of the ranking is unlabelled and not counted);
  T = 25 % (main), 10 %, 50 %, and "paired" (any rank).
Deterministic. Writes only validation/out/.
"""
from __future__ import annotations

import importlib.util
import json
import os
from typing import Dict, List

import numpy as np
import pandas as pd

from common import BUNDLE, HERE, OUT, PROJECT, write_csv

THRESHOLDS = (("top10", 10.0), ("top25", 25.0), ("top50", 50.0), ("paired", 100.0))


def _r4_sites() -> pd.DataFrame:
    spec = importlib.util.spec_from_file_location("r4_rank_sites", os.path.join(PROJECT, "research", "r4_rank_sites.py"))
    r4 = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(r4)
    r4.HERE = os.path.join(OUT, "r4")          # r4 writes <HERE>/out/...: redirect into validation/out/r4/out
    import sys
    argv = sys.argv
    sys.argv = ["r4_rank_sites.py", BUNDLE, "shipped"]
    try:
        import contextlib, io
        with contextlib.redirect_stdout(io.StringIO()):
            r4.main()
    finally:
        sys.argv = argv
    with open(os.path.join(OUT, "r4", "out", "r4_rank_sites_shipped.json"), encoding="utf-8") as fh:
        rep = json.load(fh)
    rows = []
    for m, d in rep["missions"].items():
        n_ranked = d["ranked_with_twin"]
        for s in d["sites"]:
            paired = bool(s.get("twin"))
            rank = s.get("rank")
            rows.append({"mission": m, "list": f"validation_sites_{m}.csv", "site_id": s["site_id"], "name": s["name"],
                         "role": s["role"], "cell": f"E{s['cell']}", "passes_funnel": bool(s["passes"]), "paired": paired,
                         "rank": rank, "ranked_total": n_ranked,
                         "rank_top_pct": round(100.0 * rank / n_ranked, 2) if paired and rank else np.nan,
                         "rank_pct_within_lat_row": s.get("rank_pct_within_lat_row"),
                         "reasons": "; ".join(s.get("reasons") or [])})
    return pd.DataFrame(rows)


def _rover_sites() -> pd.DataFrame:
    import rover_preset
    t = pd.read_csv(os.path.join(OUT, "m3_benchmark_sites.csv"), keep_default_na=False, na_values=[""])
    t = t[t["mission"] == "rover"]
    rows = []
    for role, names in (("positive", rover_preset.MOBILITY_POSITIVES), ("negative", rover_preset.MOBILITY_MISMATCHES)):
        for nm in names:
            key = nm.lower().replace("-", " ")
            hit = t[t["name"].str.lower().str.replace("-", " ").str.contains(key, regex=False)]
            if hit.empty:
                rows.append({"mission": "rover", "list": "rover_preset.py", "site_id": "", "name": nm, "role": role,
                             "cell": "", "passes_funnel": False, "paired": False, "rank": np.nan, "ranked_total": np.nan,
                             "rank_top_pct": np.nan, "unverified": "not in benchmark", "reasons": "not located"})
                continue
            r = hit.iloc[0]
            paired = isinstance(r["twin"], str) and r["twin"] != ""
            rows.append({"mission": "rover", "list": "rover_preset.py", "site_id": r["id"], "name": nm, "role": role,
                         "cell": r["cell"], "passes_funnel": bool(r["passes_funnel"]), "paired": paired,
                         "rank": r["rank"] if paired else np.nan, "ranked_total": r["ranked_total"],
                         "rank_top_pct": float(r["rank_top_pct"]) if paired else np.nan,
                         "unverified": r["unverified"] if isinstance(r["unverified"], str) else "",
                         "reasons": r["funnel_reasons"] if isinstance(r["funnel_reasons"], str) else ""})
    return pd.DataFrame(rows)


def precision_recall(sites: pd.DataFrame) -> pd.DataFrame:
    out: List[Dict] = []
    for (m, lst), g0 in sites.groupby(["mission", "list"], sort=False):
        scopes = [("all", g0)]
        if "unverified" in g0 and g0["unverified"].fillna("").astype(bool).any():
            scopes.append(("verified_only", g0[g0["unverified"].fillna("") == ""]))
        for scope, g in scopes:
            pos, neg = g[g["role"] == "positive"], g[g["role"] == "negative"]
            for tname, tv in THRESHOLDS:
                def pred(x):
                    return x["paired"] & (x["rank_top_pct"].fillna(1e9) <= tv)
                tp, fp = int(pred(pos).sum()), int(pred(neg).sum())
                out.append({"mission": m, "list": lst, "scope": scope, "threshold": tname,
                            "positives": len(pos), "negatives": len(neg),
                            "positives_passing_funnel": int(pos["passes_funnel"].sum()),
                            "negatives_passing_funnel": int(neg["passes_funnel"].sum()),
                            "true_positives": tp, "false_positives": fp,
                            "recall_pct": round(100.0 * tp / len(pos), 1) if len(pos) else np.nan,
                            "precision_pct": round(100.0 * tp / (tp + fp), 1) if (tp + fp) else np.nan,
                            "recovered": " ".join(pos.loc[pred(pos), "name"].astype(str)),
                            "false_alarms": " ".join(neg.loc[pred(neg), "name"].astype(str))})
    return pd.DataFrame(out)


def run() -> Dict:
    sites = pd.concat([_rover_sites(), _r4_sites()], ignore_index=True)
    write_csv(sites, "m9_external_sites.csv")
    pr = precision_recall(sites)
    write_csv(pr, "m9_precision_recall.csv")
    return {"precision_recall": pr.to_dict("records")}


if __name__ == "__main__":
    import sys
    sys.path.insert(0, HERE)
    print(json.dumps(run(), indent=1, default=str)[:4000])
