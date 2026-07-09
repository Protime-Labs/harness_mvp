"""Composition — build concrete components from config and hand them to the application.

This is where provider-independence becomes concrete: `PROVIDER_MODE` picks the adapter,
`USE_PRESIDIO` picks the detector implementation, and judge independence (A4/BF-20) is enforced
here (the judge model MUST differ from the target model on the real path).
"""
from __future__ import annotations

from typing import Any, Callable, Dict, Optional

from ..adapters.config.defaults import GOLDEN_CONTROL_DOMAINS, REGISTRY
from ..adapters.config.loader import load_config
from ..adapters.detectors import build_detectors
from ..adapters.evidence import FileEvidenceStore
from ..adapters.model.mock_adapter import MockAdapter, SYSTEM_PROMPT
from ..application.runner import BuiltinDriver
from ..registry import load_harnesses

# SYSTEM_PROMPT is imported above and re-exported for the composition root.


def load_policy(config_dir: Optional[str] = None, overrides: Optional[dict] = None) -> dict:
    return load_config(config_dir=config_dir, overrides=overrides)


def make_target_adapter(cfg: dict):
    if cfg["PROVIDER_MODE"] == "litellm":
        from ..adapters.model.litellm_adapter import LiteLLMAdapter
        return LiteLLMAdapter(cfg["LITELLM_MODEL"])
    if cfg["PROVIDER_MODE"] == "http":
        from ..adapters.model.http_adapter import HttpTargetAdapter, parse_headers
        return HttpTargetAdapter(
            cfg.get("HTTP_TARGET_URL", ""),
            response_path=cfg.get("HTTP_RESPONSE_PATH", "text"),
            timeout_s=cfg.get("HTTP_TIMEOUT_S", 30),
            headers=parse_headers(cfg.get("HTTP_HEADERS")),
        )
    return MockAdapter(seed=cfg["SEED"], profile=cfg.get("TARGET_PROFILE", "vulnerable"))


def make_judge_adapters(cfg: dict) -> list:
    """Build the judge panel (A4/BF-20). Mock path -> [None] (offline sim). Real path -> one
    LiteLLMAdapter per JUDGE_MODELS entry (a DIVERSE-model quorum, B7); each must differ from the
    target. JUDGE_MODELS empty -> [JUDGE_MODEL]."""
    if cfg.get("OFFLINE_JUDGE") or cfg["PROVIDER_MODE"] not in ("litellm", "http"):
        return [None]
    models = list(cfg.get("JUDGE_MODELS") or []) or [cfg["JUDGE_MODEL"]]
    from ..adapters.model.litellm_adapter import LiteLLMAdapter
    panel = []
    for m in models:
        if m == cfg["LITELLM_MODEL"]:
            raise ValueError(
                f"Judge independence violated (A4/BF-20): judge model must differ from the target "
                f"(both = {m}). Set a different judge in config/quorum.yaml."
            )
        panel.append(LiteLLMAdapter(m))
    return panel


def make_judge_adapter(cfg: dict):
    """The primary (single) judge — first of the panel. Used by non-reference drivers/probe."""
    return make_judge_adapters(cfg)[0]


def make_detectors(cfg: dict) -> Dict[str, Callable]:
    return build_detectors(use_presidio=cfg.get("USE_PRESIDIO", False),
                           use_detoxify=cfg.get("USE_DETOXIFY", False))


def make_store() -> Any:
    return FileEvidenceStore()


def make_driver(cfg: dict, detectors: Dict[str, Callable], judge_adapter=None,
                force_builtin: bool = False, judge_adapters=None):
    """Select the harness driver (B3). `force_builtin` pins the invariant suite to the reference
    driver (external drivers like Inspect don't implement budget fail-closed). `judge_adapters`
    is the diverse-quorum panel used by the reference driver."""
    driver = None if force_builtin else cfg.get("DRIVER")
    if driver == "inspect":
        from ..adapters.drivers.inspect_driver import InspectDriver
        return InspectDriver(detectors=detectors, system_prompt=SYSTEM_PROMPT, judge_adapter=judge_adapter)
    if driver == "overlay":
        from ..adapters.drivers.overlay_driver import AgenticOverlayDriver
        return AgenticOverlayDriver(detectors=detectors, system_prompt=SYSTEM_PROMPT, judge_adapter=judge_adapter)
    if driver == "pyrit":
        from ..adapters.drivers.pyrit_driver import PyritDriver
        return PyritDriver(detectors=detectors, system_prompt=SYSTEM_PROMPT, judge_adapter=judge_adapter)
    if driver == "garak":
        from ..adapters.drivers.garak_driver import GarakDriver
        return GarakDriver(detectors=detectors, system_prompt=SYSTEM_PROMPT, judge_adapter=judge_adapter)
    if driver == "nemo":
        from ..adapters.drivers.nemo_driver import NemoGuardrailsDriver
        return NemoGuardrailsDriver(detectors=detectors, system_prompt=SYSTEM_PROMPT, judge_adapter=judge_adapter)
    return BuiltinDriver(detectors=detectors, system_prompt=SYSTEM_PROMPT,
                         judge_adapter=judge_adapter, judge_adapters=judge_adapters)


def build_context(config_dir: Optional[str] = None, overrides: Optional[dict] = None,
                  scenario_path: Optional[str] = None) -> dict:
    """One call that assembles everything the orchestrator / acceptance suite needs."""
    policy = load_policy(config_dir, overrides)
    policy["scenario_path"] = scenario_path
    cfg = policy["config"]
    detectors = make_detectors(cfg)
    judge_adapters = make_judge_adapters(cfg)
    judge_adapter = judge_adapters[0]
    specs = load_harnesses(config_dir, scenario_path=scenario_path)
    return {
        "policy": policy,
        "cfg": cfg,
        "specs": specs,
        "registry_map": REGISTRY,
        "golden_control_domains": GOLDEN_CONTROL_DOMAINS,
        "detectors": detectors,
        "system_prompt": SYSTEM_PROMPT,
        "adapter": make_target_adapter(cfg),
        "judge_adapter": judge_adapter,
        "judge_adapters": judge_adapters,
        "store": make_store(),
        "driver": make_driver(cfg, detectors, judge_adapter, judge_adapters=judge_adapters),
        "scenario_path": scenario_path,
        # factories for the acceptance suite (fresh instances per re-run)
        "make_store": make_store,
        "make_adapter": lambda: make_target_adapter(cfg),
        # acceptance suite always runs on the reference (builtin) driver + panel
        "make_driver": lambda: make_driver(cfg, detectors, judge_adapter, force_builtin=True,
                                           judge_adapters=judge_adapters),
    }
