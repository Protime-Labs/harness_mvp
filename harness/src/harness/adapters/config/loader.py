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
from ...domain.contracts import SEVERITY_ORDER, sha256_hex  # adapter -> domain (allowed)

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


# F5 — governance YAML must not degrade silently: unknown top-level keys are a misconfiguration.
_CONFIG_YAMLS = ("risk_weights.yaml", "quorum.yaml", "budgets.yaml", "golden_controls.yaml", "model_pricing.yaml")
_ALLOWED_KEYS = {
    "risk_weights.yaml": {"weights", "cutoffs", "foundational_pack", "packs", "require_when"},
    "golden_controls.yaml": {"schema", "status", "external_dependency", "note", "domains", "controls", "catalogue"},
    "model_pricing.yaml": {"schema", "models"},
    # budgets.yaml + quorum.yaml merge into CONFIG -> validated against DEFAULT_CONFIG keys below.
}


def _check_keys(fname: str, data: dict, allowed) -> None:
    unknown = set(data or {}) - set(allowed)
    if unknown:
        raise ValueError(f"{fname}: unknown top-level key(s) {sorted(unknown)}; "
                         f"allowed {sorted(allowed)} (STRICT_CONFIG — check for a typo).")


# F6 — a runtime override may only TIGHTEN governance-owned policy (lower budget, wider pack, lower
# fail-severity). A loosening override is an audit hole: under strict mode it raises; otherwise it is
# recorded in `sources` provenance so it lands in the bundle. Only these keys are policy-classified.
_PACK_RANK = {"foundational": 1, "advanced": 2, "all": 2}


def _policy_override_changes(cfg: dict, overrides: dict) -> list:
    """Return [{key, from, to, direction}] for policy-tightenable override keys (direction in
    {tighten, loosen})."""
    changes = []
    if "FAIL_ON_SEVERITY" in overrides:
        old, new = cfg.get("FAIL_ON_SEVERITY"), overrides["FAIL_ON_SEVERITY"]
        if new != old:  # lower severity rank = stricter (blocks on less) = tighten
            d = "tighten" if SEVERITY_ORDER.get(new, 9) < SEVERITY_ORDER.get(old, 9) else "loosen"
            changes.append({"key": "FAIL_ON_SEVERITY", "from": old, "to": new, "direction": d})
    if isinstance(overrides.get("BUDGET"), dict):
        old_b = cfg.get("BUDGET", {}) or {}
        for k, nv in overrides["BUDGET"].items():
            ov = old_b.get(k)
            if ov is None or nv == ov:
                continue  # a HIGHER budget allows more = loosen; lower = tighten
            changes.append({"key": f"BUDGET.{k}", "from": ov, "to": nv,
                            "direction": "loosen" if nv > ov else "tighten"})
    if "PACK" in overrides:
        old, new = cfg.get("PACK"), overrides["PACK"]
        if new != old:  # a wider pack (more harnesses) = stricter = tighten
            d = "tighten" if _PACK_RANK.get(new, 0) >= _PACK_RANK.get(old, 0) else "loosen"
            changes.append({"key": "PACK", "from": old, "to": new, "direction": d})
    return changes


def load_config(config_dir: Optional[str] = None, overrides: Optional[dict] = None) -> Dict[str, Any]:
    """Return the merged runtime config dict + the risk/pack policy, with provenance."""
    cfg_dir = config_dir or _default_config_dir()
    sources = ["python-defaults"]

    cfg = copy.deepcopy(defaults.DEFAULT_CONFIG)
    weights = copy.deepcopy(defaults.RISK_WEIGHTS)
    cutoffs = copy.deepcopy(defaults.RISK_CUTOFFS)
    pack = list(defaults.FOUNDATIONAL_PACK)
    packs_by_tier = copy.deepcopy(defaults.PACKS_BY_TIER)   # per-risk-tier packs (F2)
    require_when = copy.deepcopy(defaults.REQUIRE_WHEN)      # mandatory clauses (F3)
    golden_controls = {"domains": {}}

    # F5 — STRICT_CONFIG (default: true unless mock provider). Decided from the override/default
    # provider mode (YAML can't be read yet when PyYAML is missing — which is exactly the case to catch).
    provider_mode = (overrides or {}).get("PROVIDER_MODE") or cfg["PROVIDER_MODE"]
    _strict_flag = (overrides or {}).get("STRICT_CONFIG")
    strict = _strict_flag if _strict_flag is not None else (provider_mode != "mock")
    if strict and not _HAS_YAML:
        present = [f for f in _CONFIG_YAMLS if os.path.exists(os.path.join(cfg_dir, f))]
        if present:
            raise RuntimeError(
                f"STRICT_CONFIG: governance config present {present} but PyYAML is not installed, so it "
                f"would be silently ignored. Install pyyaml (`pip install -e '.[config]'`), or run in mock "
                f"mode / set STRICT_CONFIG=false to accept the baked-in defaults.")

    if _HAS_YAML:
        y_budgets = _load_yaml(os.path.join(cfg_dir, "budgets.yaml"))
        y_quorum = _load_yaml(os.path.join(cfg_dir, "quorum.yaml"))
        y_risk = _load_yaml(os.path.join(cfg_dir, "risk_weights.yaml"))
        y_controls = _load_yaml(os.path.join(cfg_dir, "golden_controls.yaml"))
        y_pricing = _load_yaml(os.path.join(cfg_dir, "model_pricing.yaml"))
        # validate top-level keys up front (a typo must fail, not silently merge into nothing)
        _check_keys("budgets.yaml", y_budgets, defaults.DEFAULT_CONFIG.keys())
        _check_keys("quorum.yaml", y_quorum, defaults.DEFAULT_CONFIG.keys())
        _check_keys("risk_weights.yaml", y_risk, _ALLOWED_KEYS["risk_weights.yaml"])
        _check_keys("golden_controls.yaml", y_controls, _ALLOWED_KEYS["golden_controls.yaml"])
        _check_keys("model_pricing.yaml", y_pricing, _ALLOWED_KEYS["model_pricing.yaml"])
        if y_budgets:
            cfg = _deep_merge(cfg, y_budgets); sources.append("budgets.yaml")
        if y_quorum:
            cfg = _deep_merge(cfg, y_quorum); sources.append("quorum.yaml")
        if y_pricing:
            cfg["MODEL_PRICING"] = _deep_merge(cfg.get("MODEL_PRICING", {}),
                                               y_pricing.get("models", y_pricing) or {})
            sources.append("model_pricing.yaml")
        if y_risk:
            weights = _deep_merge(weights, y_risk.get("weights", {}))
            cutoffs = _deep_merge(cutoffs, y_risk.get("cutoffs", {}))
            pack = y_risk.get("foundational_pack", pack)
            packs_by_tier = y_risk.get("packs", packs_by_tier)          # F2 (absent -> fallback)
            require_when = y_risk.get("require_when", require_when)      # F3
            sources.append("risk_weights.yaml")
        if y_controls:
            golden_controls = y_controls
            sources.append("golden_controls.yaml")

    if overrides:
        changes = _policy_override_changes(cfg, overrides)   # classify BEFORE applying (F6)
        loosenings = [c for c in changes if c["direction"] == "loosen"]
        if strict and loosenings:
            raise ValueError(
                f"STRICT_CONFIG: override(s) would LOOSEN governance policy {loosenings}. "
                f"A runtime override may only tighten policy (lower budget, wider pack, lower "
                f"fail-severity). Change the governance YAML instead, or drop strict mode.")
        cfg = _deep_merge(cfg, overrides)
        sources.append("cli-overrides")
        for c in changes:  # audit provenance -> bundle
            sources.append(f"override:{c['key']}:{c['from']}->{c['to']}({c['direction']})")

    # pack selection (B6): a non-foundational pack sets the required harnesses + the attack set.
    selected = cfg.get("PACK", "foundational")
    if selected in defaults.PACKS and selected != "foundational":
        pack = list(defaults.PACKS[selected])
        cfg["PHASE1_ATTACK"] = [h for h in pack if h not in defaults.GOVERNANCE_HARNESSES]
        packs_by_tier = None       # an explicit pack override wins over per-tier selection
        sources.append(f"pack:{selected}")

    # F5 — inverted risk cutoffs are a misconfiguration (fail closed, always checked).
    if not (cutoffs.get("high", 0) > cutoffs.get("medium", 0)):
        raise ValueError(f"risk cutoffs invalid: high ({cutoffs.get('high')}) must be greater than "
                         f"medium ({cutoffs.get('medium')}).")

    # F4 — content hash of the policy in force (drift detection). Canonical (sorted-key) JSON.
    policy_hash = sha256_hex({
        "weights": weights, "cutoffs": cutoffs, "packs": packs_by_tier, "require_when": require_when,
        "budget": cfg.get("BUDGET"), "quorum": {"n": cfg.get("QUORUM_N"), "rule": cfg.get("QUORUM_RULE")},
        "fail_on_severity": cfg.get("FAIL_ON_SEVERITY"),
    })

    return {
        "config": cfg,
        "risk_weights": weights,
        "risk_cutoffs": cutoffs,
        "foundational_pack": pack,
        "packs": packs_by_tier,
        "require_when": require_when,
        "policy_hash": policy_hash,
        "golden_controls": golden_controls,
        "sources": sources,
        "yaml_available": _HAS_YAML,
    }
