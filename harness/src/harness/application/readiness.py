"""Enterprise readiness assessment for the demo/prototype surface.

This is not part of the gate. It is operator-facing truth-in-labeling: which controls are
live in this run, which are still represented by seams/config, and which external enterprise
dependencies must be connected before the harness is production-grade.
"""
from __future__ import annotations

import os
from typing import Any, Callable, Dict


def _golden_controls_loaded(policy: dict) -> bool:
    controls = policy.get("golden_controls") or {}
    return bool(controls.get("domains") or controls.get("controls") or controls.get("catalogue"))


def _golden_controls_ready(policy: dict) -> bool:
    gc = policy.get("golden_controls") or {}
    if not _golden_controls_loaded(policy):
        return False
    if str(gc.get("status", "")).lower() == "unresolved":
        return False
    marker_text = str(gc).upper()
    return not any(m in marker_text for m in ("PLACEHOLDER", "TBD", "UNRESOLVED"))


def _store_name(store: Any) -> str:
    return type(store).__name__ if store is not None else ""


def assess_mvp_readiness(
    policy: dict,
    *,
    store: Any = None,
    detectors: Dict[str, Callable] | None = None,
    driver_name: str | None = None,
    specs: Dict[str, Any] | None = None,
) -> dict:
    """LOCAL readiness — the MVP substitutes that make a run real WITHOUT enterprise services.

    This is deliberately separate from `assess_enterprise_readiness`: a fully-local run (mock target,
    local secrets scanner, file evidence + replay, SQLite persistence, deterministic gate) is
    MVP-ready even though it is not enterprise-ready. Reporting one verdict would under-credit a
    legitimately complete local evaluation (§4.6)."""
    dets = sorted((detectors or {}).keys())
    missing: list[str] = []
    if not dets:
        missing.append("detector registry (deterministic content floor)")
    if store is None:
        missing.append("evidence store")
    if not driver_name:
        missing.append("harness driver")
    if not specs:
        missing.append("harness specs")
    enabled = {
        "quarantine_scanner": "local-regex-secrets",         # M2
        "evidence_store": _store_name(store) or "none",       # M0
        "replayable_bundle": True,                            # M3
        "deterministic_gate": True,                           # A1
        "persistence": "sqlite (local)",                      # M4
        "detectors": dets, "driver": driver_name or "unknown",
        "harness_count": len(specs or {}),
    }
    return {"ready": not missing, "missing": missing, "enabled": enabled}


def assess_enterprise_readiness(
    policy: dict,
    *,
    scenario_path: str | None = None,
    store: Any = None,
    detectors: Dict[str, Callable] | None = None,
    driver_name: str | None = None,
    specs: Dict[str, Any] | None = None,
) -> dict:
    cfg = policy["config"]
    provider = cfg.get("PROVIDER_MODE", "mock")
    scenario_path = scenario_path or policy.get("scenario_path")
    missing: list[str] = []
    hard: list[str] = []

    if provider == "mock":
        missing.append("real target provider (use --provider litellm or --provider http)")
    if provider == "http" and not cfg.get("HTTP_TARGET_URL"):
        missing.append("HTTP target URL")
        hard.append("HTTP target URL")
    if provider == "litellm":
        keys = ["ANTHROPIC_API_KEY", "OPENAI_API_KEY", "AZURE_API_KEY", "AWS_ACCESS_KEY_ID"]
        if not any(os.environ.get(k) for k in keys):
            missing.append("provider credentials in environment")
    if provider != "mock" and cfg.get("OFFLINE_JUDGE"):
        missing.append("real independent judge provider (offline judge enabled)")

    if not scenario_path:
        missing.append("external scenario corpus for the target environment")
    if not _golden_controls_loaded(policy):
        missing.append("Golden Controls catalogue")
    elif not _golden_controls_ready(policy):
        missing.append("production Golden Controls catalogue (current file is an unresolved dependency record)")
    # HTTP target must reference secrets by env var, never carry them inline (BF/§4.8)
    headers = cfg.get("HTTP_HEADERS")
    if provider == "http" and headers:
        from ..domain.secrets import scan_secrets
        if scan_secrets(str(headers)):
            missing.append("HTTP target headers contain inline secrets — use env-var references")
            hard.append("inline secret in HTTP target headers")
    if not cfg.get("MODEL_ROUTER_URL"):
        missing.append("model gateway/router policy enforcement")
    if not cfg.get("QUARANTINE_SCANNER_URL"):
        missing.append("quarantine scanners for prompt/document ingress")
    if "FileEvidenceStore" in _store_name(store):
        missing.append("WORM/append-only evidence backend")
    if not cfg.get("SIEM_EXPORT_URL"):
        missing.append("SIEM/SOAR export")
    if not cfg.get("WAIVER_WORKFLOW_URL"):
        missing.append("manual review / waiver workflow")
    if not cfg.get("RBAC_PROVIDER_URL"):
        missing.append("operator identity/RBAC integration")

    detector_names = sorted((detectors or {}).keys())
    enabled = {
        "provider_mode": provider,
        "real_target": provider != "mock" and not (provider == "http" and not cfg.get("HTTP_TARGET_URL")),
        "real_judge": provider != "mock" and not cfg.get("OFFLINE_JUDGE"),
        "scenario_source": scenario_path or "built-in/config suite",
        "golden_controls_loaded": _golden_controls_loaded(policy),
        "golden_controls_ready": _golden_controls_ready(policy),
        "evidence_store": _store_name(store) or "unknown",
        "driver": driver_name or "unknown",
        "detectors": detector_names,
        "harness_count": len(specs or {}),
    }
    return {
        "ready": not missing,
        "missing": missing,
        "hard_blockers": hard,
        "enabled": enabled,
    }
