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

from ..domain.contracts import Finding, SEVERITY_ORDER
from ..domain.gate import gate_decision
from .scorecard import build_scorecard, resolve_profile
from .calibration import calibrate
from .judge_calibration import calibrate_judge
from .contextualize import contextualize
from .governance import run_governance_finding_lifecycle
from .readiness import assess_enterprise_readiness, assess_mvp_readiness
from .quarantine import screen_asset
from .remediation import remediate
from .replay import replay_mode_a
from .selection import coverage_complete, select


def _build_run_config(cfg: dict, scenario_source: str = "built-in/config suite") -> dict:
    """Self-describing run config (audit + dashboard inputs). Depends only on cfg."""
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
    return {
        "provider_mode": cfg["PROVIDER_MODE"],
        "target_model": target_model,
        "judge_model": judge_model,
        "quorum_n": cfg["QUORUM_N"], "quorum_rule": cfg["QUORUM_RULE"],
        "fail_on_severity": cfg["FAIL_ON_SEVERITY"], "seed": cfg["SEED"],
        "budget": cfg["BUDGET"], "use_presidio": cfg.get("USE_PRESIDIO", False),
        "scenario_source": scenario_source,
    }


def _cost_governed(cfg: dict) -> bool:
    """A run is cost-governed when it hits a real provider AND a finite positive cost cap is set."""
    if cfg["PROVIDER_MODE"] not in ("litellm", "http"):
        return False
    mc = cfg["BUDGET"].get("max_cost_usd")
    try:
        return mc is not None and 0 < float(mc) < float("inf")
    except (TypeError, ValueError):
        return False


def _declaration_mismatch(use_case: dict, findings) -> bool:
    """F7 (minimal hook) — declared vs observed reconciliation. A sensitive-data finding
    (data_leakage / sensitive_disclosure) in a use case that declared NO sensitive data class is a
    contradiction: the intake under-stated the asset's exposure, so the risk scoping is suspect and
    the gate routes to manual_review.

    DESIGN NOTE: the full treatment is a two-pass re-selection — re-run W1/W2 with the observed
    attributes merged into the declared ones and fail closed if coverage widened. That is out of
    scope here; this is the deterministic gate hook that surfaces the contradiction for a human.
    """
    declared = {str(d).upper() for d in (use_case.get("data_classes") or [])}
    if declared & {"PII", "CPNI", "PHI", "PCI"}:
        return False
    for f in findings:
        cat = getattr(f, "category", "") or ""
        if cat.startswith("data_leakage") or "sensitive_disclosure" in cat:
            return True
    return False


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
    cfg = dict(policy["config"])
    # Req 2 — gate-by-trust: a lower-trust asset gets a stricter gate (tighten-only, deterministic).
    _tr = cfg.get("INHERENT_TRUST")
    _gbt = (policy.get("gate_by_trust") or {}).get(_tr or "", {})
    if _gbt.get("fail_on_severity") and \
            SEVERITY_ORDER.get(_gbt["fail_on_severity"], 99) < SEVERITY_ORDER.get(cfg["FAIL_ON_SEVERITY"], 99):
        cfg["FAIL_ON_SEVERITY"] = _gbt["fail_on_severity"]

    # W? quarantine (security front door) — a real gate input, not a hard-coded string
    quarantine = screen_asset(asset, cfg)

    # W1 contextualize -> W2 select (each plan entry carries WHY it was required, F8)
    ctx = contextualize(use_case, policy)
    plan_reasons = {r["harness"]: r["reason"] for r in ctx.get("plan_reasons", [])}
    plan, skipped = select(ctx["required_harnesses"], registry_map, reasons=plan_reasons)
    # The selected plan is authoritative: run the plan's attack harnesses (governance harnesses are
    # verified by H5.1, not executed as attacks), NOT cfg["PHASE1_ATTACK"] directly.
    attack_ids = [p["harness"] for p in plan if not p.get("governance")]

    # Quarantine short-circuit: if ingress is blocked we do NOT invoke the target or run any harness
    # (fail-closed, and no prompts/billing against a quarantined asset). The gate blocks on the
    # quarantine decision (rule 1); the redacted scanner findings live in the bundle's quarantine object.
    if quarantine["decision"] == "block":
        gate = gate_decision("block", [], [], coverage_complete({}, attack_ids, skipped),
                             policy_hash=policy.get("policy_hash", ""))
        gov = run_governance_finding_lifecycle([], [], store)
        readiness = assess_enterprise_readiness(
            policy, store=store, detectors=detectors,
            driver_name=getattr(driver, "name", None), specs=specs)
        mvp_readiness = assess_mvp_readiness(
            policy, store=store, detectors=detectors,
            driver_name=getattr(driver, "name", None), specs=specs)
        return {
            "asset": asset, "use_case": use_case,
            "run_config": _build_run_config(cfg, policy.get("scenario_path") or "built-in/config suite"),
            "scorecard": build_scorecard(
                resolve_profile(cfg, policy.get("criteria_profiles", {}))[1], policy.get("criteria", {}),
                [], [], trust=cfg.get("INHERENT_TRUST"), mode=cfg.get("MODE", "assurance"),
                profile_name=resolve_profile(cfg, policy.get("criteria_profiles", {}))[0]),
            "context": ctx, "plan": plan, "skipped": skipped, "quarantine": quarantine,
            "harness_results": {}, "governance": gov, "gate": asdict(gate),
            "enterprise_readiness": readiness, "mvp_readiness": mvp_readiness, "calibration": {},
            "judge_calibration": {"gate_eligible": None, "n": 0,
                                  "basis": "not run (ingress quarantined before evaluation)"},
            "replay": {"ok": True, "findings": [], "gate": asdict(gate)},
            "remediation": remediate([]),
            "findings": [], "evidence_root": store.root,
            "_findings": [], "_verdicts": [], "_manifest": [],
            "_turns": [], "_cost_status": {"governed": _cost_governed(cfg), "known": True},
            "_context_status": {"unknown_attributes": [], "declaration_mismatch": False},
        }

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

    # Cost governance: on a cost-governed run, a turn whose price could not be determined leaves the
    # budget unassured -> the gate routes to manual_review (never a silent over-budget approve).
    cost_status = {"governed": _cost_governed(cfg),
                   "known": all(r["metrics"].get("cost_known", True) for r in results.values())}
    # Context integrity: unrecognized risk attributes (F1) + declared-vs-observed mismatch (F7).
    context_status = {
        "unknown_attributes": ctx.get("unknown_attributes", []),
        "declaration_mismatch": _declaration_mismatch(use_case, all_findings),
    }

    # W8 gate — the single deterministic decision (control plane, no LLM). Coverage fails closed when
    # a required harness was skipped (unimplemented/unregistered) or did not complete (A8).
    required_ran = coverage_complete(results, attack_ids, skipped)
    pol_hash = policy.get("policy_hash", "")
    gate = gate_decision(quarantine["decision"], list(results.values()), all_findings, required_ran,
                         evaluator_status=judge_cal, cost_status=cost_status,
                         context_status=context_status, policy_hash=pol_hash)

    # Mode-A replay (C4) — reproduce findings + gate from evidence alone
    harness_detectors = {hid: specs[hid].detectors for hid in attack_ids}
    orig = sorted((f.id, f.severity, f.category) for f in all_findings)
    replay_findings, replay_gate = replay_mode_a(
        all_manifest, all_verdicts, store, detectors, harness_detectors, evaluator_status=judge_cal,
        fail_on_severity=cfg["FAIL_ON_SEVERITY"], cost_status=cost_status,
        context_status=context_status, policy_hash=pol_hash)
    replay_ok = (orig == replay_findings) and (gate.decision == replay_gate.decision)

    # W9 remediation (advisory)
    remediation = remediate(all_findings)

    # self-describing run config (audit + dashboard inputs)
    run_config = _build_run_config(cfg, policy.get("scenario_path") or "built-in/config suite")
    readiness = assess_enterprise_readiness(
        policy,
        store=store,
        detectors=detectors,
        driver_name=getattr(driver, "name", None),
        specs=specs,
    )
    mvp_readiness = assess_mvp_readiness(
        policy, store=store, detectors=detectors,
        driver_name=getattr(driver, "name", None), specs=specs)

    # Req 2 — vulnerability × trust scorecard (a deterministic view of the findings the gate saw)
    findings_dicts = [asdict(f) for f in all_findings]
    _profile_name, _profile_ids = resolve_profile(cfg, policy.get("criteria_profiles", {}))
    scorecard = build_scorecard(_profile_ids, policy.get("criteria", {}), attack_ids, findings_dicts,
                                trust=cfg.get("INHERENT_TRUST"), mode=cfg.get("MODE", "assurance"),
                                profile_name=_profile_name)

    return {
        "asset": asset,
        "use_case": use_case,
        "run_config": run_config,
        "scorecard": scorecard,
        "context": ctx,
        "plan": plan,
        "skipped": skipped,
        "quarantine": quarantine,
        "harness_results": results,
        "governance": gov,
        "gate": asdict(gate),
        "enterprise_readiness": readiness,
        "mvp_readiness": mvp_readiness,
        "calibration": cal,
        "judge_calibration": judge_cal,
        "replay": {"ok": replay_ok, "findings": replay_findings, "gate": asdict(replay_gate)},
        "remediation": remediation,
        "findings": findings_dicts,
        "evidence_root": store.root,
        # live objects for reporting / the acceptance suite / bundle persistence (not serialized):
        "_findings": all_findings,
        "_verdicts": all_verdicts,
        "_manifest": all_manifest,
        "_turns": all_turns,
        "_cost_status": cost_status,
        "_context_status": context_status,
    }
