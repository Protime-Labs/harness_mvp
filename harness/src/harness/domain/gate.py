"""B5 — the deterministic gate. The ONE decision point (W8, G4/R9).

A1 / KEYSTONE INVARIANT: no LLM, no model call, no agent runs in this function. It is
pure control-plane policy over the aggregate of findings. First matching rule wins
(fixed precedence). Fails CLOSED: a required harness that did not complete => block.

This module imports NOTHING that could reach a model. The acceptance suite proves it by
inspecting `gate_decision.__code__.co_names` for banned tokens (A1 machine check).

Faithful to notebook §11 `gate_decision`.
"""
from __future__ import annotations

from typing import Iterable, List

from .contracts import GATE_SCHEMA, GateDecision, Finding


def gate_decision(
    quarantine: str,
    harness_results: Iterable[dict],
    findings: List[Finding],
    required_ran: bool,
    evaluator_status: dict | None = None,
    cost_status: dict | None = None,
) -> GateDecision:
    """Aggregate every harness finding into one decision. First matching rule wins.

    A finding's `blocking` flag (computed from the configured FAIL_ON_SEVERITY threshold) is the
    control-plane signal for "this severity gates" — the gate honors it rather than hard-coding a
    severity. A finding's `basis` says whether it came from a deterministic detector or a judge:
    deterministic detector evidence is judge-independent (C3 floor), so a detector-based blocking
    finding blocks REGARDLESS of judge calibration; a judge-derived finding does not gate while the
    evaluator is below its calibration threshold (A9/C1) — it routes to human review instead.

    Attributes are read defensively (`getattr`) so any finding-like object (e.g. the replay
    reconstruction) is accepted as long as it carries `severity`; missing `blocking`/`basis`
    degrade safely to non-blocking / non-detector.
    """

    def out(dec: str, rule: str, why: str) -> GateDecision:
        return GateDecision(decision=dec, matched_rule=rule, rationale=why, policy_version=GATE_SCHEMA)

    # 1 — quarantine hard block (security front door, when present)
    if quarantine == "block":
        return out("block", "1.quarantine_block", "Quarantine blocked ingress.")
    # 2 — required coverage missing (skipped or did not complete) -> fail closed (A8)
    if not required_ran:
        return out("block", "2.required_harness_not_run",
                   "A required harness did not run/complete (A8 fail-closed).")
    # 3 — a blocking harness reported failed status
    if any(r.get("status") == "failed" for r in harness_results):
        return out("block", "3.blocking_harness_failed", "A blocking harness failed.")
    # 4 — a DETERMINISTIC detector produced a blocking finding. This evidence is judge-independent,
    #     so it blocks regardless of judge calibration (C3 floor; ordered ahead of rule 5).
    if any(getattr(f, "blocking", False) and getattr(f, "basis", "").startswith("detector")
           for f in findings):
        return out("block", "4.detector_blocking_finding",
                   "Deterministic detector produced a blocking finding (C3 floor).")
    # 5 — evaluator below its calibration threshold -> judge-derived results cannot gate; the only
    #     blocking findings that could remain are judge-derived, so route to human review (A9/C1).
    if evaluator_status and evaluator_status.get("gate_eligible") is False:
        return out("manual_review", "5.evaluator_not_calibrated",
                   "Evaluator calibration below threshold; routing judge-derived result to review.")
    # 6 — any blocking finding (judge-derived, evaluator calibrated) honors FAIL_ON_SEVERITY
    if any(getattr(f, "blocking", False) for f in findings):
        return out("block", "6.blocking_finding",
                   "Finding at or above the configured fail-severity threshold.")
    # 6b — cost could not be determined on a cost-governed run: the budget is unassured, so we
    #      cannot silently approve (ordered AFTER every block rule — a real block always wins).
    if cost_status and cost_status.get("governed") and cost_status.get("known") is False:
        return out("manual_review", "6b.cost_unknown",
                   "Run cost could not be determined on a cost-governed run.")
    # 7 — a high (non-blocking) finding -> warn (advisory)
    if any(getattr(f, "severity", "") == "high" for f in findings):
        return out("warn", "7.high_finding", "High-severity advisory finding.")
    # 8 — default
    return out("approve", "8.default", "No blocking conditions.")
