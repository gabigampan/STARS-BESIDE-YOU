"""Named criteria sets per mission (engine_config ``criteria_sets``).

Decision of the team lead (2026-11-15, 11:28/11:36 CET, docs/DECISIONS.md): each mission
is published in the version that passes the independent re-audit. Every mission has two
named sets and a switch (``selected``):

* ``audited_morning``: the rule, weights, gates, filter and top-5 choice of commit
  42d8bba (the state audited in the morning);
* ``corrected``: everything decided since.

A set is applied at build time, as configuration only:

* ``engine_patch``: {dotted path inside an engine setting's value: replacement value}
  (e.g. ``real_value_similarity.missions.rover``); applied to a copy of the setting;
* ``mission_scoring_deviations``: a list of {criterion, team, ours, reason, source}: the
  soft criterion of mission_scoring.json is replaced by ``ours`` (``null`` removes it,
  i.e. weight 0) in a COPY of the team's config; the team's file is never edited, and the
  build checks that ``team`` still equals the team's file (a stale deviation fails).

No mission or variable is named in this module.
"""
from __future__ import annotations

import copy
from typing import Any, Dict, Optional, Tuple

from engine.config import EngineConfig, Setting


def _set_path(obj: Dict[str, Any], path: str, value: Any) -> None:
    head, *rest = path.split(".")
    if not rest:
        obj[head] = copy.deepcopy(value)
        return
    if head not in obj or not isinstance(obj[head], dict):
        raise KeyError(f"criteria set patch: no block {head!r} on the path {path!r}")
    _set_path(obj[head], ".".join(rest), value)


def selected_sets(engine_cfg: EngineConfig, override: Optional[Dict[str, str]] = None) -> Dict[str, str]:
    cs = engine_cfg.v("criteria_sets") if engine_cfg.criteria_sets is not None else None
    if not cs:
        return {}
    sel = dict(cs["selected"])
    sel.update(override or {})
    for m, name in sel.items():
        if name not in cs["missions"][m]["sets"]:
            raise KeyError(f"criteria set {name!r} is not defined for {m}")
    return sel


def apply_criteria_sets(engine_cfg: EngineConfig, mission_cfg: Dict[str, Any],
                        override: Optional[Dict[str, str]] = None) -> Tuple[EngineConfig, Dict[str, Any], Dict[str, Any]]:
    """(engine config, mission config, info) with the selected set of every mission applied.

    Returns copies; the inputs are untouched. ``override`` = {mission: set name} for one
    build (tests, the fallback to the audited state). ``info`` is what the bundle states:
    {mission: {"set": name, "deviations": [...]}}."""
    cs = engine_cfg.v("criteria_sets") if engine_cfg.criteria_sets is not None else None
    if not cs or engine_cfg.dataset_id not in cs["datasets"]:
        return engine_cfg, mission_cfg, {}
    sel = selected_sets(engine_cfg, override)
    ecfg = engine_cfg.model_copy(deep=True)
    mcfg = copy.deepcopy(mission_cfg)
    info: Dict[str, Any] = {}
    for mid, name in sel.items():
        s = cs["missions"][mid]["sets"][name]
        for path, value in (s.get("engine_patch") or {}).items():
            setting, *rest = path.split(".")
            st = getattr(ecfg, setting)
            if st is None:
                raise KeyError(f"criteria set patch names unknown setting {setting!r}")
            val = copy.deepcopy(st.value)
            if rest:
                _set_path(val, ".".join(rest), value)
            else:
                val = copy.deepcopy(value)
            setattr(ecfg, setting, Setting(value=val, why=st.why))
        devs = s.get("mission_scoring_deviations") or []
        targets = [mid]
        core = (mcfg["missions"][mid].get("components") or {}).get("core")
        if core:
            targets.append(core)  # a mission that is an exact copy of a component keeps being one
        for d in devs:
            crit = d["criterion"]
            team_now = mission_cfg["missions"][mid].get("soft", {}).get(crit)
            if team_now != d["team"]:
                raise ValueError(f"{mid}/{crit}: the deviation's 'team' value no longer equals mission_scoring.json")
            for t in targets:
                soft = mcfg["missions"][t].setdefault("soft", {})
                if d["ours"] is None:
                    soft.pop(crit, None)
                else:
                    soft[crit] = copy.deepcopy(d["ours"])
        info[mid] = {"set": name, "title": s.get("title", name), "deviations": copy.deepcopy(devs)}
    cv = copy.deepcopy(ecfg.criteria_sets.value)
    cv["applied"] = info
    ecfg.criteria_sets = Setting(value=cv, why=ecfg.criteria_sets.why)
    return ecfg, mcfg, info
