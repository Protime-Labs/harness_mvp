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
    return MockAdapter(seed=cfg["SEED"], profile=cfg.get("TARGET_PROFILE", "vulnerable"))


def make_judge_adapter(cfg: dict):
    """Independent judge (A4/BF-20). Mock path judges with the same offline sim path (None).
    Real path REQUIRES judge model != target model."""
    if cfg["PROVIDER_MODE"] != "litellm":
        return None
    if cfg["JUDGE_MODEL"] == cfg["LITELLM_MODEL"]:
        raise ValueError(
            f"Judge independence violated (A4/BF-20): JUDGE_MODEL must differ from LITELLM_MODEL "
            f"(both = {cfg['JUDGE_MODEL']}). Set a different judge model in config/quorum.yaml."
        )
    from ..adapters.model.litellm_adapter import LiteLLMAdapter
    return LiteLLMAdapter(cfg["JUDGE_MODEL"])


def make_detectors(cfg: dict) -> Dict[str, Callable]:
    return build_detectors(use_presidio=cfg.get("USE_PRESIDIO", False),
                           use_detoxify=cfg.get("USE_DETOXIFY", False))


def make_store() -> Any:
    return FileEvidenceStore()


def make_driver(cfg: dict, detectors: Dict[str, Callable], judge_adapter=None) -> BuiltinDriver:
    return BuiltinDriver(detectors=detectors, system_prompt=SYSTEM_PROMPT, judge_adapter=judge_adapter)


def build_context(config_dir: Optional[str] = None, overrides: Optional[dict] = None) -> dict:
    """One call that assembles everything the orchestrator / acceptance suite needs."""
    policy = load_policy(config_dir, overrides)
    cfg = policy["config"]
    detectors = make_detectors(cfg)
    judge_adapter = make_judge_adapter(cfg)
    return {
        "policy": policy,
        "cfg": cfg,
        "specs": load_harnesses(config_dir),
        "registry_map": REGISTRY,
        "golden_control_domains": GOLDEN_CONTROL_DOMAINS,
        "detectors": detectors,
        "system_prompt": SYSTEM_PROMPT,
        "adapter": make_target_adapter(cfg),
        "judge_adapter": judge_adapter,
        "store": make_store(),
        "driver": make_driver(cfg, detectors, judge_adapter),
        # factories for the acceptance suite (fresh instances per re-run)
        "make_store": make_store,
        "make_adapter": lambda: make_target_adapter(cfg),
        "make_driver": lambda: make_driver(cfg, detectors, judge_adapter),
    }
