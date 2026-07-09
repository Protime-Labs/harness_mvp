"""Config loader (B6). Baked-in defaults, optionally overridden by YAML.

Resolution order (last wins):
  1. Python defaults (`defaults.py`) — always available, zero installs.
  2. `config/*.yaml` next to the repo (if PyYAML is installed AND the file exists).
  3. explicit overrides passed by the caller (CLI flags).

This is the whole "how do I provide a value" mechanism: edit the owned YAML file, the loader
merges it, and no code changes. Without PyYAML the harness still runs on the defaults.
"""
from __future__ import annotations

import copy
import os
from typing import Any, Dict, Optional

from . import defaults

try:  # optional dependency (extra: config)
    import yaml  # type: ignore
    _HAS_YAML = True
except Exception:  # pragma: no cover
    _HAS_YAML = False


def _deep_merge(base: dict, override: dict) -> dict:
    out = copy.deepcopy(base)
    for k, v in (override or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = copy.deepcopy(v)
    return out


def _default_config_dir() -> str:
    # <repo>/config  (this file is <repo>/src/harness/adapters/config/loader.py)
    here = os.path.dirname(os.path.abspath(__file__))
    return os.path.normpath(os.path.join(here, "..", "..", "..", "..", "config"))


def _load_yaml(path: str) -> dict:
    if not (_HAS_YAML and os.path.exists(path)):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def load_config(config_dir: Optional[str] = None, overrides: Optional[dict] = None) -> Dict[str, Any]:
    """Return the merged runtime config dict + the risk/pack policy, with provenance."""
    cfg_dir = config_dir or _default_config_dir()
    sources = ["python-defaults"]

    cfg = copy.deepcopy(defaults.DEFAULT_CONFIG)
    weights = copy.deepcopy(defaults.RISK_WEIGHTS)
    cutoffs = copy.deepcopy(defaults.RISK_CUTOFFS)
    pack = list(defaults.FOUNDATIONAL_PACK)
    golden_controls = {"domains": {}}

    if _HAS_YAML:
        y_budgets = _load_yaml(os.path.join(cfg_dir, "budgets.yaml"))
        y_quorum = _load_yaml(os.path.join(cfg_dir, "quorum.yaml"))
        y_risk = _load_yaml(os.path.join(cfg_dir, "risk_weights.yaml"))
        y_controls = _load_yaml(os.path.join(cfg_dir, "golden_controls.yaml"))
        if y_budgets:
            cfg = _deep_merge(cfg, y_budgets); sources.append("budgets.yaml")
        if y_quorum:
            cfg = _deep_merge(cfg, y_quorum); sources.append("quorum.yaml")
        if y_risk:
            weights = _deep_merge(weights, y_risk.get("weights", {}))
            cutoffs = _deep_merge(cutoffs, y_risk.get("cutoffs", {}))
            pack = y_risk.get("foundational_pack", pack)
            sources.append("risk_weights.yaml")
        if y_controls:
            golden_controls = y_controls
            sources.append("golden_controls.yaml")

    if overrides:
        cfg = _deep_merge(cfg, overrides)
        sources.append("cli-overrides")

    # pack selection (B6): a non-foundational pack sets the required harnesses + the attack set.
    selected = cfg.get("PACK", "foundational")
    if selected in defaults.PACKS and selected != "foundational":
        pack = list(defaults.PACKS[selected])
        cfg["PHASE1_ATTACK"] = [h for h in pack if h not in defaults.GOVERNANCE_HARNESSES]
        sources.append(f"pack:{selected}")

    return {
        "config": cfg,
        "risk_weights": weights,
        "risk_cutoffs": cutoffs,
        "foundational_pack": pack,
        "golden_controls": golden_controls,
        "sources": sources,
        "yaml_available": _HAS_YAML,
    }
