#!/usr/bin/env python3
"""
mission_scoring.py - Filtros por mision en dos niveles.

  1) FILTROS DUROS (gates): si una celda terrestre incumple uno, la zona analoga se
     DESCARTA para esa mision (pass_<m> = 0 y se anota el motivo en fail_<m>).
  2) FILTROS BLANDOS (soft): las celdas que sobreviven reciben una puntuacion 0-100,
     media ponderada de utilidades 0-1 por variable. Cada mision pondera distinto.

Todo (umbrales, pesos, misiones) vive en mission_scoring.json. Anadir una mision =
anadir una entrada al JSON. La mision 'rover' queda como hueco ('external': true)
para quien la defina: basta rellenar 'gates' y 'soft' con el mismo esquema.

Esquema de un gate:   {"min": x, "max": y, "allow": [...], "exclude": [...]}
Esquema de un soft:   {"weight": w, "bad": a, "good": b}          (numerico, lineal, recortado a [0,1])
                      {"weight": w, "map": {"clase": u}, "default": u0}   (categorico)

Dato ausente: nunca se trata como 0.
  - gate: la celda se descarta (on_missing_gate="drop") o se conserva ("keep").
  - soft: esa variable se ignora y los pesos restantes se renormalizan
          (coverage_<m> indica la fraccion del peso con dato).

USO
  python mission_scoring.py run --cells output_py/earth_moon_harmonized_clean.csv \
         --missions solar,thermal --out output_py/mission_scores.csv
  python mission_scoring.py selftest
"""
import argparse
import json
import os
import sys
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mission_scoring.json")


def load_config(path: Optional[str] = None) -> Dict:
    with open(path or CONFIG_PATH, encoding="utf-8") as fh:
        return json.load(fh)


# --------------------------------------------------------------------- gates
def _gate_mask(df: pd.DataFrame, col: str, g: Dict, on_missing: str):
    """Devuelve (pasa: bool array, motivo: array de str) para un gate."""
    n = len(df)
    if col not in df.columns:
        raise KeyError(f"El gate usa la columna '{col}' que no existe en los datos")
    s = df[col]
    if "min" in g or "max" in g:
        v = pd.to_numeric(s, errors="coerce").to_numpy(dtype=np.float64)
        missing = ~np.isfinite(v)
        ok = np.ones(n, dtype=bool)
        if g.get("min") is not None:
            ok &= v >= g["min"]
        if g.get("max") is not None:
            ok &= v <= g["max"]
        label = f"{col} fuera de [{g.get('min', '-inf')}, {g.get('max', 'inf')}]"
    else:
        v = s.astype(str).str.strip().str.lower().to_numpy()
        missing = s.isna().to_numpy() | (v == "nan") | (v == "")
        ok = np.ones(n, dtype=bool)
        if g.get("allow"):
            ok &= np.isin(v, [a.lower() for a in g["allow"]])
        if g.get("exclude"):
            ok &= ~np.isin(v, [e.lower() for e in g["exclude"]])
        label = f"{col} no permitido"
    ok = np.where(missing, on_missing == "keep", ok)
    reason = np.where(missing & ~ok, f"{col} sin dato", np.where(~ok, label, ""))
    return ok, reason


def apply_gates(df: pd.DataFrame, gates: Dict[str, Dict], require_present: List[str],
                on_missing: str = "drop"):
    n = len(df)
    passed = np.ones(n, dtype=bool)
    reasons: List[List[str]] = [[] for _ in range(n)]
    cols_failed: List[List[str]] = [[] for _ in range(n)]
    for col in require_present:
        if col not in df.columns:
            raise KeyError(f"require_present usa '{col}' que no existe en los datos")
        s = df[col]
        absent = s.isna() | s.astype(str).str.strip().str.lower().isin(["", "nan", "none"])
        for i in np.flatnonzero(absent.to_numpy()):
            reasons[i].append(f"{col} sin dato")
            cols_failed[i].append(f"{col}:missing")
        passed &= ~absent.to_numpy()
    for col, g in gates.items():
        ok, why = _gate_mask(df, col, g, on_missing)
        passed &= ok
        for i in np.flatnonzero(~ok):
            reasons[i].append(why[i])
            cols_failed[i].append(col)
    return (passed, ["; ".join(dict.fromkeys(r)) for r in reasons],
            ["|".join(dict.fromkeys(c)) for c in cols_failed])


# --------------------------------------------------------------------- soft
def utility(series: pd.Series, spec: Dict) -> np.ndarray:
    """Utilidad 0-1 (NaN si no hay dato)."""
    if "map" in spec:
        m = {k.lower(): float(v) for k, v in spec["map"].items()}
        txt = series.astype(str).str.strip().str.lower()
        u = txt.map(m).astype(float)
        u = u.where(~(series.isna() | txt.isin(["", "nan"])), np.nan)
        u = u.where(~(u.isna() & series.notna() & ~txt.isin(["", "nan"])), float(spec.get("default", 0.5)))
        return u.to_numpy(dtype=np.float64)
    v = pd.to_numeric(series, errors="coerce").to_numpy(dtype=np.float64)
    bad, good = float(spec["bad"]), float(spec["good"])
    if bad == good:
        raise ValueError("'bad' y 'good' no pueden ser iguales")
    return np.clip((v - bad) / (good - bad), 0.0, 1.0)  # NaN se propaga


def apply_soft(df: pd.DataFrame, soft: Dict[str, Dict], weights: Optional[Dict[str, float]] = None):
    """Devuelve (score 0-100, coverage 0-1, DataFrame de utilidades por variable)."""
    w = {c: float(s["weight"]) for c, s in soft.items()}
    if weights:
        w.update({c: float(x) for c, x in weights.items() if c in w})
    num = np.zeros(len(df))
    den = np.zeros(len(df))
    utils = {}
    for col, spec in soft.items():
        if col not in df.columns:
            raise KeyError(f"El criterio blando usa '{col}' que no existe en los datos")
        u = utility(df[col], spec)
        utils[col] = u
        ok = np.isfinite(u)
        num += np.where(ok, w[col] * u, 0.0)
        den += np.where(ok, w[col], 0.0)
    total_w = sum(w.values()) or 1.0
    score = np.where(den > 0, 100.0 * num / np.where(den > 0, den, 1.0), np.nan)
    return score, den / total_w, pd.DataFrame(utils, index=df.index)


# ------------------------------------------------------------- orquestacion
def score_mission(df: pd.DataFrame, name: str, cfg: Dict,
                  weights: Optional[Dict[str, float]] = None) -> pd.DataFrame:
    m = cfg["missions"][name]
    if m.get("external") and not m.get("gates") and not m.get("soft"):
        raise ValueError(f"La mision '{name}' es externa y aun no esta definida en el JSON")
    gates = {**cfg.get("common_gates", {}), **m.get("gates", {})}
    gates = {c: {k: v for k, v in g.items() if k != "why"} for c, g in gates.items()}
    passed, why, failcols = apply_gates(df, gates, m.get("require_present", []),
                                        cfg.get("on_missing_gate", "drop"))
    score, cov, utils = apply_soft(df, m.get("soft", {}), weights)
    out = pd.DataFrame(index=df.index)
    out[f"pass_{name}"] = passed.astype(int)
    out[f"fail_{name}"] = why
    out[f"failcols_{name}"] = failcols
    out[f"score_{name}"] = np.where(passed, np.round(score, 2), np.nan)
    out[f"coverage_{name}"] = np.round(cov, 3)
    for c in utils.columns:
        out[f"u_{name}_{c}"] = np.round(utils[c], 3)
    return out


def evaluate(df: pd.DataFrame, missions: List[str], cfg: Optional[Dict] = None,
             weights: Optional[Dict[str, Dict[str, float]]] = None) -> pd.DataFrame:
    cfg = cfg or load_config()
    res = df.copy()
    for name in missions:
        res = pd.concat([res, score_mission(df, name, cfg, (weights or {}).get(name))], axis=1)
    cols = [f"pass_{m}" for m in missions]
    res["pass_all"] = res[cols].all(axis=1).astype(int)
    return res


def mission_names(cfg: Dict) -> List[str]:
    """Misiones definidas (se omiten las 'external' que aun no tienen gates ni soft)."""
    return [k for k, m in cfg["missions"].items()
            if not (m.get("external") and not m.get("gates") and not m.get("soft"))]


def build_stats(res: pd.DataFrame, missions: List[str]) -> Dict:
    """Auditoria: {mision: {pass, fail_by:{columna: n}}, '_all': n}."""
    stats: Dict = {}
    for m in missions:
        counts: Dict[str, int] = {}
        for cell in res[f"failcols_{m}"]:
            for c in filter(None, str(cell).split("|")):
                counts[c] = counts.get(c, 0) + 1
        stats[m] = {"pass": int(res[f"pass_{m}"].sum()), "fail_by": counts}
    stats["_all"] = int(res["pass_all"].sum())
    return stats


def to_web_cfg(cfg: Dict) -> Dict:
    """Formato que lee web/index.html: gates min/max/allow/exclude + source, mask_min, pesos de dominio."""
    mask_min = cfg.get("common_gates", {}).get("mask_fraction", {}).get("min")
    missions = {}
    for name in mission_names(cfg):
        m = cfg["missions"][name]
        gates = {}
        for col, g in m.get("gates", {}).items():
            gg = {k: v for k, v in g.items() if k != "why"}
            gg.setdefault("source", g.get("why", ""))
            gates[col] = gg
        missions[name] = {k: v for k, v in m.items() if k not in ("gates", "soft")}
        missions[name]["gates"] = gates
        missions[name]["soft"] = m.get("soft", {})
    return {"version": cfg.get("version", ""), "mask_min": mask_min, "missions": missions}


def combine_with_similarity(res: pd.DataFrame, mission: str, alpha: float = 0.5,
                            sim_col: str = "similarity_pct") -> pd.Series:
    """Mezcla opcional: alpha*similitud_con_la_Luna + (1-alpha)*puntuacion_de_mision.
    Las celdas descartadas por un gate duro quedan en NaN."""
    return alpha * res[sim_col] + (1.0 - alpha) * res[f"score_{mission}"]


# ----------------------------------------------------------------------- CLI
def selftest() -> None:
    cfg = {
        "on_missing_gate": "drop",
        "common_gates": {},
        "missions": {"t": {
            "require_present": [],
            "gates": {"a": {"min": 1.0}, "c": {"exclude": ["agua"]}},
            "soft": {
                "a": {"weight": 3, "bad": 1.0, "good": 5.0},
                "b": {"weight": 1, "bad": 10.0, "good": 0.0},
                "c": {"weight": 1, "map": {"roca": 1.0, "suelo": 0.5}, "default": 0.2},
            },
        }},
    }
    df = pd.DataFrame({
        "a": [5.0, 0.5, 3.0, np.nan, 5.0],
        "b": [0.0, 0.0, 5.0, 5.0, np.nan],
        "c": ["roca", "roca", "suelo", "suelo", "agua"],
    })
    r = score_mission(df, "t", cfg)
    assert list(r["pass_t"]) == [1, 0, 1, 0, 0], r["pass_t"].tolist()   # duro: a<1, a ausente, agua
    assert r.loc[0, "score_t"] == 100.0                                    # todo en 'good'
    assert np.isnan(r.loc[1, "score_t"])                                   # descartada -> sin puntuacion
    assert "a fuera de" in r.loc[1, "fail_t"] and "sin dato" in r.loc[3, "fail_t"]
    # fila 2: a=3 -> u=.5 (w3), b=5 -> u=.5 (w1), c=suelo -> .5 (w1) => 50
    assert abs(r.loc[2, "score_t"] - 50.0) < 1e-9
    # pesos sobreescritos en caliente
    r2 = score_mission(df, "t", cfg, {"a": 0.0})
    assert abs(r2.loc[2, "score_t"] - 50.0) < 1e-9
    # dato ausente en criterio blando: se renormaliza, no cuenta como 0 (fila 4 la descarta el gate, usamos otra)
    df2 = df.iloc[[0]].copy(); df2.loc[0, "b"] = np.nan
    r3 = score_mission(df2, "t", cfg)
    assert r3.loc[0, "score_t"] == 100.0 and abs(r3.loc[0, "coverage_t"] - 0.8) < 1e-9
    print("selftest OK (5 comprobaciones)")


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--cells", required=True, help="CSV con celdas (se usan solo las de body=EARTH si existe esa columna)")
    r.add_argument("--missions", default="solar,thermal")
    r.add_argument("--config", default=None)
    r.add_argument("--out", required=True)
    sub.add_parser("selftest")
    a = p.parse_args(argv)
    if a.cmd == "selftest":
        selftest()
        return 0
    cfg = load_config(a.config)
    df = pd.read_csv(a.cells)
    if "body" in df.columns:
        df = df[df["body"].str.upper() == "EARTH"].reset_index(drop=True)
    missions = [m.strip() for m in a.missions.split(",") if m.strip()]
    res = evaluate(df, missions, cfg)
    res.to_csv(a.out, index=False)
    for m in missions:
        n_ok = int(res[f"pass_{m}"].sum())
        print(f"{m}: {n_ok}/{len(res)} celdas pasan los filtros duros; "
              f"score medio {res[f'score_{m}'].mean():.1f}")
    print(f"pasan todas: {int(res['pass_all'].sum())}  ->  {a.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
