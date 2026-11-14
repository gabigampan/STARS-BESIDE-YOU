#!/usr/bin/env python3
"""
mission_filters.py - Sistema de filtros (gates) por misión/propósito.
Solo biblioteca estándar de Python 3.10+.

IDEA
  Cada misión (rover, solar, thermal, ice...) tiene su propio juego de filtros en un
  archivo de configuración JSON. El programa lee las celdas de la Tierra (CSV), aplica
  los filtros de las misiones elegidas y marca qué celdas pasan.
  Añadir una misión nueva = añadir una entrada al JSON, sin tocar el código.

REGLAS DEL PLAN QUE CUMPLE
  - Un número sin referencia no entra: límite con valor y `source` vacío -> error.
  - Un límite en null no se aplica.
  - Dato ausente nunca es 0: en un filtro numérico la celda se queda (o se descarta
    con --on-missing drop); en `require_present` sin dato = no pasa.
  - Cada misión se congela por separado (frozen_at + author) antes de mirar ningún ranking:
    Robótica 1 congela `rover`, Robótica 2 congela `solar` y `thermal`.

TIPOS DE FILTRO (dentro de "gates", una entrada por columna)
  numérico:    {"min": 3.0, "max": null, "source": "..."}
  categórico:  {"allow": ["arena","roca"], "exclude": ["ninguno"], "source": "..."}

USO
  python mission_filters.py init   mission_filters.json
  python mission_filters.py check  mission_filters.json
  python mission_filters.py apply  mission_filters.json earth_cells.csv --missions solar,thermal --out resultado.csv
  python mission_filters.py freeze mission_filters.json --missions solar,thermal --author "Nombre"
  python mission_filters.py selftest
"""
import argparse
import copy
import csv
import json
import sys
from datetime import datetime, timezone

# ------------------------------------------------------------------ plantilla
TEMPLATE = {
    "version": "v0-template",
    "mask_min": 0.3,          # plan: mask_fraction >= 0.3 (si el CSV trae esa columna)
    "missions": {
        "rover": {
            "description": "Movilidad (la rellena Robótica 1)",
            "gates": {
                "slope_300m_deg": {"min": None, "max": None, "source": ""},
                "rough_300m_m":   {"min": None, "max": None, "source": ""},
            },
            "require_present": [],
            "weights": {"relieve": None, "material": None, "termico": None, "luz": None, "agua": None},
            "weights_note": "",
            "frozen_at": None,
            "author": "",
        },
        "solar": {
            "description": "Energía e iluminación (Robótica 2)",
            "gates": {
                "irradiance_kwh_m2_day": {"min": None, "max": None, "source": ""},
                "sun_elev_max_deg":      {"min": None, "max": None, "source": ""},
                "sun_low_frac_0_5deg":   {"min": None, "max": None, "source": ""},
            },
            "require_present": [],
            "weights": {"relieve": None, "material": None, "termico": None, "luz": None, "agua": None},
            "weights_note": "",
            "frozen_at": None,
            "author": "",
        },
        "thermal": {
            "description": "Entorno térmico (Robótica 2)",
            "gates": {
                "lst_diurnal_amp_k": {"min": None, "max": None, "source": ""},
            },
            "require_present": ["thermal_inertia_class"],
            "weights": {"relieve": None, "material": None, "termico": None, "luz": None, "agua": None},
            "weights_note": "",
            "frozen_at": None,
            "author": "",
        },
        "ice": {
            "description": "Perforación y prospección de hielo (solo si sobra tiempo)",
            "gates": {
                "permafrost_class": {"exclude": ["ninguno", "none"], "source": "plan fase 1, parte 3"},
            },
            "require_present": ["permafrost_class"],
            "weights": {"relieve": None, "material": None, "termico": None, "luz": None, "agua": None},
            "weights_note": "",
            "frozen_at": None,
            "author": "",
        },
    },
}

NUMERIC_KEYS = ("min", "max")
CATEG_KEYS = ("allow", "exclude")


# ------------------------------------------------------------------ utilidades
def to_float(x):
    """'' / 'nan' / None -> None (sin dato, nunca 0)."""
    if x is None:
        return None
    if isinstance(x, (int, float)):
        return None if x != x else float(x)
    s = str(x).strip()
    if s == "" or s.lower() in ("nan", "none", "null", "na"):
        return None
    try:
        return float(s)
    except ValueError:
        return None


def has_value(x):
    return x is not None and str(x).strip().lower() not in ("", "nan", "none", "null", "na")


def gate_active(g):
    return any(g.get(k) is not None for k in NUMERIC_KEYS) or any(g.get(k) for k in CATEG_KEYS)


# ------------------------------------------------------------------ validación
def validate(cfg, strict=False, only=None):
    problems = []
    if not cfg.get("missions"):
        problems.append("No hay misiones definidas.")
    for name, m in cfg.get("missions", {}).items():
        if only and name not in only:
            continue
        for col, g in m.get("gates", {}).items():
            if gate_active(g) and not str(g.get("source", "")).strip():
                problems.append(f"{name}.{col}: tiene límite pero no `source` (no entra).")
            if g.get("min") is not None and g.get("max") is not None and g["min"] > g["max"]:
                problems.append(f"{name}.{col}: min > max.")
        w = m.get("weights", {})
        if strict and w and all(v is None for v in w.values()):
            problems.append(f"{name}: faltan los pesos.")
        if w and any(v is not None for v in w.values()):
            if any(v is None for v in w.values()):
                problems.append(f"{name}: pesos incompletos.")
            elif abs(sum(w.values()) - 1.0) > 1e-6:
                problems.append(f"{name}: los pesos deben sumar 1 (suman {sum(w.values()):.3f}).")
            if not str(m.get("weights_note", "")).strip():
                problems.append(f"{name}: falta la línea de justificación de los pesos.")
    return problems


# ------------------------------------------------------------------ evaluación
def failed_gates(cell, mission, mask_min=None, on_missing="keep"):
    """Lista de motivos por los que la celda NO pasa (vacía = pasa)."""
    fails = []
    mf = to_float(cell.get("mask_fraction"))
    if mask_min is not None and mf is not None and mf < mask_min:
        fails.append("mask_fraction")
    for col in mission.get("require_present", []):
        if not has_value(cell.get(col)):
            fails.append(f"{col}:sin_dato")
    for col, g in mission.get("gates", {}).items():
        if not gate_active(g):
            continue
        raw = cell.get(col)
        if g.get("allow") or g.get("exclude"):          # categórico
            if not has_value(raw):
                if on_missing == "drop":
                    fails.append(f"{col}:sin_dato")
                continue
            v = str(raw).strip().lower()
            if g.get("allow") and v not in [str(a).lower() for a in g["allow"]]:
                fails.append(col)
            elif g.get("exclude") and v in [str(a).lower() for a in g["exclude"]]:
                fails.append(col)
        else:                                            # numérico
            v = to_float(raw)
            if v is None:
                if on_missing == "drop":
                    fails.append(f"{col}:sin_dato")
                continue
            if (g.get("min") is not None and v < g["min"]) or (g.get("max") is not None and v > g["max"]):
                fails.append(col)
    return fails


def apply_missions(rows, cfg, missions, on_missing="keep"):
    """Devuelve (filas con flags, estadísticas)."""
    unknown = [m for m in missions if m not in cfg["missions"]]
    if unknown:
        raise SystemExit(f"Misión desconocida: {unknown}. Disponibles: {list(cfg['missions'])}")
    mask_min = cfg.get("mask_min")
    stats = {m: {"pass": 0, "fail_by": {}} for m in missions}
    stats["_all"] = 0
    out = []
    for r in rows:
        r = dict(r)
        ok_all = True
        for m in missions:
            fails = failed_gates(r, cfg["missions"][m], mask_min, on_missing)
            r[f"pass_{m}"] = int(not fails)
            if fails:
                ok_all = False
                for f in fails:
                    stats[m]["fail_by"][f] = stats[m]["fail_by"].get(f, 0) + 1
            else:
                stats[m]["pass"] += 1
        r["pass_all"] = int(ok_all)
        stats["_all"] += ok_all
        out.append(r)
    return out, stats


# ------------------------------------------------------------------ comandos
def load_cfg(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def save_cfg(cfg, path):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)


def cmd_init(a):
    save_cfg(TEMPLATE, a.config)
    print(f"Plantilla escrita en {a.config}. Rellena min/max/source y pesos.")


def cmd_check(a):
    problems = validate(load_cfg(a.config), strict=a.strict)
    for p in problems:
        print("[PROBLEMA]", p)
    print("OK: sin problemas." if not problems else f"{len(problems)} problema(s).")
    return 1 if problems else 0


def cmd_apply(a):
    cfg = load_cfg(a.config)
    for p in validate(cfg):
        print("[AVISO]", p, file=sys.stderr)
    missions = [m.strip() for m in a.missions.split(",") if m.strip()]
    with open(a.cells, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fields = list(reader.fieldnames or [])
        rows = list(reader)
    out, st = apply_missions(rows, cfg, missions, a.on_missing)
    n = len(rows)
    print(f"Celdas leídas: {n}   (config {cfg.get('version')})")
    for m in missions:
        fz = cfg["missions"][m].get("frozen_at")
        print(f"  [{m}] " + (f"congelada {fz}" if fz else "SIN CONGELAR (no uses el ranking como resultado final)"))
    for m in missions:
        print(f"  {m}: pasan {st[m]['pass']} ({100 * st[m]['pass'] / n:.1f} %)" if n else f"  {m}: 0")
        for col, c in sorted(st[m]["fail_by"].items(), key=lambda kv: -kv[1]):
            print(f"      descarta por {col}: {c}")
    if len(missions) > 1:
        print(f"  TODAS ({'+'.join(missions)}): pasan {st['_all']}")
    if a.out:
        flag_cols = [f"pass_{m}" for m in missions] + ["pass_all"]
        keep = [r for r in out if r["pass_all"]] if a.only_pass else out
        with open(a.out, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=fields + flag_cols)
            w.writeheader()
            w.writerows(keep)
        print(f"Escrito {a.out} ({len(keep)} filas).")


def cmd_freeze(a):
    cfg = load_cfg(a.config)
    missions = [m.strip() for m in a.missions.split(",") if m.strip()]
    unknown = [m for m in missions if m not in cfg["missions"]]
    if unknown:
        raise SystemExit(f"Misión desconocida: {unknown}. Disponibles: {list(cfg['missions'])}")
    problems = validate(cfg, strict=True, only=missions)
    if problems:
        raise SystemExit("No se puede congelar:\n  - " + "\n  - ".join(problems))
    if not a.author.strip():
        raise SystemExit("Indica --author.")
    stamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    for m in missions:
        cfg["missions"][m]["frozen_at"] = stamp
        cfg["missions"][m]["author"] = a.author
    save_cfg(cfg, a.config)
    print(f"Congeladas {missions}: {stamp} por {a.author}")


def selftest(_=None):
    cfg = copy.deepcopy(TEMPLATE)
    rows = [
        {"cell_id": 1, "mask_fraction": 0.5, "irradiance_kwh_m2_day": 5, "lst_diurnal_amp_k": 30,
         "thermal_inertia_class": "arena", "permafrost_class": "ninguno"},
        {"cell_id": 2, "mask_fraction": 0.5, "irradiance_kwh_m2_day": 2, "lst_diurnal_amp_k": "",
         "thermal_inertia_class": "", "permafrost_class": "continuo"},
        {"cell_id": 3, "mask_fraction": 0.1, "irradiance_kwh_m2_day": 6, "lst_diurnal_amp_k": 20,
         "thermal_inertia_class": "roca", "permafrost_class": ""},
    ]
    # plantilla vacía: solar deja pasar salvo máscara; thermal exige inercia; ice exige permafrost
    out, st = apply_missions(rows, cfg, ["solar", "thermal", "ice"])
    assert [r["pass_solar"] for r in out] == [1, 1, 0]
    assert [r["pass_thermal"] for r in out] == [1, 0, 0]
    assert [r["pass_ice"] for r in out] == [0, 1, 0]   # 1: 'ninguno' excluido; 3: sin dato
    assert [r["pass_all"] for r in out] == [0, 0, 0]

    cfg["missions"]["solar"]["gates"]["irradiance_kwh_m2_day"].update(min=3.0, source="test")
    out, st = apply_missions(rows, cfg, ["solar"])
    assert [r["pass_solar"] for r in out] == [1, 0, 0]
    assert st["solar"]["fail_by"]["irradiance_kwh_m2_day"] == 1
    cfg["missions"]["thermal"]["gates"]["lst_diurnal_amp_k"].update(min=25.0, source="test")
    out, _ = apply_missions(rows, cfg, ["thermal"], on_missing="drop")
    assert out[0]["pass_thermal"] == 1 and out[1]["pass_thermal"] == 0
    cfg["missions"]["thermal"]["gates"]["thermal_inertia_class"] = {"allow": ["arena"], "source": "test"}
    out, _ = apply_missions(rows, cfg, ["thermal"])
    assert [r["pass_thermal"] for r in out] == [1, 0, 0]

    # validación y combinación
    cfg["missions"]["solar"]["gates"]["irradiance_kwh_m2_day"]["source"] = ""
    assert any("source" in p for p in validate(cfg))
    cfg["missions"]["solar"]["gates"]["irradiance_kwh_m2_day"]["source"] = "test"
    out, st = apply_missions(rows, cfg, ["solar", "thermal"])
    assert [r["pass_all"] for r in out] == [1, 0, 0] and st["_all"] == 1
    assert any("faltan los pesos" in p for p in validate(cfg, strict=True))
    cfg["missions"]["solar"]["weights"] = {"relieve": .1, "material": .1, "termico": .1, "luz": .5, "agua": .2}
    cfg["missions"]["solar"]["weights_note"] = "test"
    assert validate(cfg, strict=True, only=["solar"]) == []          # solar lista, aunque rover no
    assert validate(cfg, strict=True, only=["rover"]) != []
    print("selftest OK")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("init");  p.add_argument("config"); p.set_defaults(f=cmd_init)
    p = sub.add_parser("check"); p.add_argument("config"); p.add_argument("--strict", action="store_true"); p.set_defaults(f=cmd_check)
    p = sub.add_parser("apply")
    p.add_argument("config"); p.add_argument("cells")
    p.add_argument("--missions", required=True, help="p. ej. solar,thermal (se combinan con Y)")
    p.add_argument("--out"); p.add_argument("--only-pass", action="store_true")
    p.add_argument("--on-missing", choices=["keep", "drop"], default="keep")
    p.set_defaults(f=cmd_apply)
    p = sub.add_parser("freeze"); p.add_argument("config"); p.add_argument("--missions", required=True); p.add_argument("--author", required=True); p.set_defaults(f=cmd_freeze)
    p = sub.add_parser("selftest"); p.set_defaults(f=selftest)
    a = ap.parse_args()
    sys.exit(a.f(a) or 0)


if __name__ == "__main__":
    main()
