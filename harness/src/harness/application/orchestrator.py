"""W0 — orchestration. The end-to-end assurance run over the injected components.

    contextualize (W1) -> select (W2) -> run each harness (W3/B3) with judge quorum (W7)
      -> governance (H5.1) -> gate (W8/B5) -> calibrate (C1) -> replay (Mode-A) -> remediate (W9)

Everything concrete (model adapter, evidence store, detectors, driver, specs, policy) is
INJECTED by the composition root (interface/), so this function is provider-independent and
runs identically on the mock or a real provider. Returns one bundle dict + the live objects a
caller needs for reporting/tests.
"""
from __future__ import annotations

from dataclasses import asdict
from typing import Any, Callable, Dict, List

from ..domain.contracts import Finding
from ..domain.gate import gate_decision
from .calibration import calibrate
from .judge_calibration import calibrate_judge
from .contextualize import contextualize
from .governance import run_governance_finding_lifecycle
from .readiness import assess_enterprise_readiness
from .quarantine import screen_asset
from .remediation import remediate
from .replay import replay_mode_a
from .selection import coverage_complete, select


def run_assurance(
    *,
    use_case: dict,
    asset: dict,
    policy: dict,                 # {config, risk_weights, risk_cutoffs, foundational_pack, ...}
    driver: Any,                  # a HarnessDriver (BuiltinDriver / overlay / pyrit)
    adapter: Any,                 # target ModelPort
    store: Any,                   # EvidencePort
    detectors: Dict[str, Callable],
    specs: Dict[str, Any],        # {harness_id: HarnessSpec}
    registry_map: Dict[str, dict],
    system_prompt: str,
    judge_adapter: Any = None,    # independent judge ModelPort (A4/BF-20); None => mock/self
) -> Dict[str, Any]:
    cfg = policy["config"]

    # W? quarantine (security front door) — a real gate input, not a hard-coded string
    quarantine = screen_asset(asset, cfg)

    # W1 contextualize -> W2 select
    ctx = contextualize(use_case, policy)
    plan, skipped = select(ctx["required_harnesses"], registry_map)
    # The selected plan is authoritative: run the plan's attack harnesses (governance harnesses are
    # verified by H5.1, not executed as attacks), NOT cfg["PHASE1_ATTACK"] directly.
    attack_ids = [p["harness"] for p in plan if not p.get("governance")]

    # W3 run each attack harness (driver honors the run contract; judge quorum inside)
    results: Dict[str, dict] = {}
    all_turns: List[dict] = []
    all_verdicts: List[dict] = []
    all_manifest: List[dict] = []
    all_findings: List[Finding] = []
    for hid in attack_ids:
        r, t, v, m, f = driver.run(specs[hid], adapter, store, cfg)
        results[hid] = r
        all_turns += t
        all_verdicts += v
        all_manifest += m
        all_findings += f

    # H5.1 governance self-check (verifies the others; does NOT decide the gate)
    gov = run_governance_finding_lifecycle(all_findings, all_verdicts, store)

    # C1 calibration per harness (scenario-based; meaningful vs a KNOWN-vulnerable target like the mock)
    cal = {hid: calibrate(specs[hid], adapter, system_prompt, cfg, detectors, judge_adapter=judge_adapter)
           for hid in attack_ids}
    # DR-11 verdict-level judge calibration (target-independent; the real-path gate-eligibility basis)
    judge_cal = calibrate_judge(judge_adapter or adapter, cfg, detectors)

    # W8 gate — the single deterministic decision (control plane, no LLM). Coverage fails closed when
    # a required harness was skipped (unimplemented/unregistered) or did not complete (A8).
    required_ran = coverage_complete(results, attack_ids, skipped)
    gate = gate_decision(quarantine["decision"], list(results.values()), all_findings, required_ran,
                         evaluator_status=judge_cal)

    # Mode-A replay (C4) — reproduce findings + gate from evidence alone
    harness_detectors = {hid: specs[hid].detectors for hid in attack_ids}
    orig = sorted((f.id, f.severity, f.category) for f in all_findings)
    replay_findings, replay_gate = replay_mode_a(
        all_manifest, all_verdicts, store, detectors, harness_detectors, evaluator_status=judge_cal,
        fail_on_severity=cfg["FAIL_ON_SEVERITY"])
    replay_ok = (orig == replay_findings) and (gate.decision == replay_gate.decision)

    # W9 remediation (advisory)
    remediation = remediate(all_findings)

    # self-describing run config (audit + dashboard inputs)
    is_real = cfg["PROVIDER_MODE"] in ("litellm", "http")
    if cfg["PROVIDER_MODE"] == "litellm":
        target_model = cfg["LITELLM_MODEL"]
    elif cfg["PROVIDER_MODE"] == "http":
        target_model = cfg.get("HTTP_TARGET_URL") or "http-target"
    else:
        target_model = "mock-1"
    judge_models = list(cfg.get("JUDGE_MODELS") or []) or [cfg["JUDGE_MODEL"]]
    judge_model = ("offline sim (content=real, semantic=simulated)" if cfg.get("OFFLINE_JUDGE") or not is_real
                   else ", ".join(judge_models))
    run_config = {
        "provider_mode": cfg["PROVIDER_MODE"],
        "target_model": target_model,
        "judge_model": judge_model,
        "quorum_n": cfg["QUORUM_N"], "quorum_rule": cfg["QUORUM_RULE"],
        "fail_on_severity": cfg["FAIL_ON_SEVERITY"], "seed": cfg["SEED"],
        "budget": cfg["BUDGET"], "use_presidio": cfg.get("USE_PRESIDIO", False),
    }
    readiness = assess_enterprise_readiness(
        policy,
        store=store,
        detectors=detectors,
        driver_name=getattr(driver, "name", None),
        specs=specs,
    )

    return {
        "asset": asset,
        "use_case": use_case,
        "run_config": run_config,
        "context": ctx,
        "plan": plan,
        "skipped": skipped,
        "quarantine": quarantine,
        "harness_results": results,
        "governance": gov,
        "gate": asdict(gate),
        "enterprise_readiness": readiness,
        "calibration": cal,
        "judge_calibration": judge_cal,
        "replay": {"ok": replay_ok, "findings": replay_findings, "gate": asdict(replay_gate)},
        "remediation": remediation,
        "findings": [asdict(f) for f in all_findings],
        "evidence_root": store.root,
        # live objects for reporting / the acceptance suite (not serialized):
        "_findings": all_findings,
        "_verdicts": all_verdicts,
        "_manifest": all_manifest,
    }
