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
from .contextualize import contextualize
from .governance import run_governance_finding_lifecycle
from .remediation import remediate
from .replay import replay_mode_a
from .selection import select


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
) -> Dict[str, Any]:
    cfg = policy["config"]

    # W1 contextualize -> W2 select
    ctx = contextualize(use_case, policy)
    plan, skipped = select(ctx["required_harnesses"], registry_map)

    # W3 run each attack harness (driver honors the run contract; judge quorum inside)
    results: Dict[str, dict] = {}
    all_turns: List[dict] = []
    all_verdicts: List[dict] = []
    all_manifest: List[dict] = []
    all_findings: List[Finding] = []
    for hid in cfg["PHASE1_ATTACK"]:
        r, t, v, m, f = driver.run(specs[hid], adapter, store, cfg)
        results[hid] = r
        all_turns += t
        all_verdicts += v
        all_manifest += m
        all_findings += f

    # H5.1 governance self-check (verifies the others; does NOT decide the gate)
    gov = run_governance_finding_lifecycle(all_findings, all_verdicts, store)

    # W8 gate — the single deterministic decision (control plane, no LLM)
    required_ran = all(results[h]["status"] == "completed" for h in cfg["PHASE1_ATTACK"])
    gate = gate_decision("allow", list(results.values()), all_findings, required_ran)

    # C1 calibration per harness
    cal = {hid: calibrate(specs[hid], adapter, system_prompt, cfg, detectors)
           for hid in cfg["PHASE1_ATTACK"]}

    # Mode-A replay (C4) — reproduce findings + gate from evidence alone
    harness_detectors = {hid: specs[hid].detectors for hid in cfg["PHASE1_ATTACK"]}
    orig = sorted((f.id, f.severity, f.category) for f in all_findings)
    replay_findings, replay_gate = replay_mode_a(all_manifest, all_verdicts, store, detectors, harness_detectors)
    replay_ok = (orig == replay_findings) and (gate.decision == replay_gate.decision)

    # W9 remediation (advisory)
    remediation = remediate(all_findings)

    return {
        "asset": asset,
        "context": ctx,
        "plan": plan,
        "skipped": skipped,
        "harness_results": results,
        "governance": gov,
        "gate": asdict(gate),
        "calibration": cal,
        "replay": {"ok": replay_ok, "findings": replay_findings, "gate": asdict(replay_gate)},
        "remediation": remediation,
        "findings": [asdict(f) for f in all_findings],
        "evidence_root": store.root,
        # live objects for reporting / the acceptance suite (not serialized):
        "_findings": all_findings,
        "_verdicts": all_verdicts,
        "_manifest": all_manifest,
    }
