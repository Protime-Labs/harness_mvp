"""Unit tests for the pure control-plane domain: gate precedence, aggregation, risk scoring."""
from harness.domain.aggregate import aggregate
from harness.domain.contracts import Finding, GATE_VOCAB
from harness.domain.gate import gate_decision
from harness.domain.risk import contextualize
from harness.domain.contracts import UseCase


def _f(sev, *, blocking=True, basis="llm-judge(real)"):
    """A finding. `blocking` is what the runner computes from FAIL_ON_SEVERITY; `basis` says whether
    it is detector-derived (deterministic) or judge-derived."""
    return Finding(id="F", source="harness", severity=sev, category="c", title="t", description="d",
                   blocking=blocking, policy_rule="P", evidence_uri="", recommendation="", basis=basis)


def test_gate_vocab_only():
    for args in [("allow", [], [], True), ("block", [], [], True)]:
        assert gate_decision(*args).decision in GATE_VOCAB


def test_gate_precedence():
    # 1 quarantine hard block overrides everything (even a clean run)
    assert gate_decision("block", [], [], True).decision == "block"
    # 2 required coverage missing -> fail closed
    assert gate_decision("allow", [], [], False).decision == "block"
    # 3 a blocking harness reported failed
    assert gate_decision("allow", [{"status": "failed"}], [], True).decision == "block"
    # 8 default -> approve
    assert gate_decision("allow", [], [], True).decision == "approve"


def test_gate_honors_fail_on_severity():
    # FAIL_ON_SEVERITY=high => a high finding is blocking => BLOCK (previously only warned).
    assert gate_decision("allow", [], [_f("high", blocking=True)], True).decision == "block"
    # FAIL_ON_SEVERITY=critical => a high finding is non-blocking => WARN.
    assert gate_decision("allow", [], [_f("high", blocking=False)], True).decision == "warn"
    # A non-blocking low finding => APPROVE.
    assert gate_decision("allow", [], [_f("low", blocking=False)], True).decision == "approve"
    # Any blocking finding blocks regardless of severity label.
    assert gate_decision("allow", [], [_f("critical", blocking=True)], True).decision == "block"


def test_detector_critical_blocks_even_when_evaluator_ineligible():
    # C3: a deterministic detector-based blocking finding blocks even when the judge is uncalibrated.
    ineligible = {"gate_eligible": False}
    d = gate_decision("allow", [], [_f("critical", basis="detector(real-content)")], True,
                      evaluator_status=ineligible)
    assert d.decision == "block" and d.matched_rule == "4.detector_blocking_finding"


def test_judge_only_finding_manual_reviews_when_evaluator_ineligible():
    ineligible = {"gate_eligible": False}
    # A judge-derived blocking finding + uncalibrated judge => human review, not a silent block.
    assert gate_decision("allow", [], [_f("critical", basis="llm-judge(real)")], True,
                         evaluator_status=ineligible).decision == "manual_review"
    # No findings + uncalibrated judge => manual_review (cannot trust an 'all clear').
    assert gate_decision("allow", [], [], True, evaluator_status=ineligible).decision == "manual_review"


def test_eligible_evaluator_lets_judge_finding_block():
    eligible = {"gate_eligible": True}
    assert gate_decision("allow", [], [_f("critical", basis="llm-judge(real)")], True,
                         evaluator_status=eligible).decision == "block"


def test_cost_unknown_on_governed_run_manual_reviews():
    unknown = {"governed": True, "known": False}
    d = gate_decision("allow", [], [], True, cost_status=unknown)
    assert d.decision == "manual_review" and d.matched_rule == "6b.cost_unknown"


def test_cost_unknown_never_overrides_a_real_block():
    unknown = {"governed": True, "known": False}
    # a deterministic detector block still BLOCKS despite an undetermined cost
    assert gate_decision("allow", [], [_f("critical", basis="detector(real-content)")], True,
                         cost_status=unknown).decision == "block"


def test_cost_known_or_ungoverned_has_no_gate_effect():
    assert gate_decision("allow", [], [], True,
                         cost_status={"governed": True, "known": True}).decision == "approve"
    assert gate_decision("allow", [], [], True,
                         cost_status={"governed": False, "known": False}).decision == "approve"


def test_unknown_risk_attributes_route_manual_review():
    cs = {"unknown_attributes": ["data_class:biometrik"]}
    d = gate_decision("allow", [], [], True, context_status=cs)
    assert d.decision == "manual_review" and d.matched_rule == "2b.unknown_risk_attributes"
    # no unknowns -> no effect
    assert gate_decision("allow", [], [], True, context_status={"unknown_attributes": []}).decision == "approve"
    # coverage failure still outranks it (fail closed first)
    assert gate_decision("allow", [], [], False, context_status=cs).decision == "block"


def test_declaration_mismatch_routes_manual_review():
    cs = {"declaration_mismatch": True}
    d = gate_decision("allow", [], [], True, context_status=cs)
    assert d.decision == "manual_review" and d.matched_rule == "6a.declaration_mismatch"
    # a real block still wins (ordered after the block rules)
    assert gate_decision("allow", [], [_f("critical", basis="detector(real-content)")], True,
                         context_status=cs).decision == "block"


def test_no_llm_tokens_in_gate():
    banned = {"invoke", "completion", "judge", "aggregate"}
    assert banned.isdisjoint(set(gate_decision.__code__.co_names))


def test_detector_floors_judge():
    # all judges say 'no', but a detector hit forces success (C3)
    verdicts = [{"attack_succeeded": False, "confidence": 0.9, "severity": "info"}]
    succ, sev, conf, det = aggregate(verdicts, [("critical", "123-45-6789")])
    assert succ is True and sev == "critical" and det is True


def test_majority_without_detector():
    v = [{"attack_succeeded": True, "confidence": 0.8, "severity": "high"},
         {"attack_succeeded": True, "confidence": 0.6, "severity": "high"},
         {"attack_succeeded": False, "confidence": 0.5, "severity": "info"}]
    succ, sev, conf, det = aggregate(v, [(None, None)])
    assert succ is True and sev == "high" and det is False


def test_risk_tiers():
    weights = {
        "data_class": {"CPNI": 32, "public": 0}, "exposure": {"public": 25, "internal": 5},
        "write_tools": {"present": 20, "absent": 0}, "users": {"external": 15, "internal": 0},
        "criticality": {"tier1": 15, "tier3": 5},
    }
    hi = contextualize(UseCase("a", ["CPNI"], "public", True, ["external"], "tier1"),
                       weights, {"high": 60, "medium": 30}, ["H2.1"])
    lo = contextualize(UseCase("b", ["public"], "internal", False, ["internal"], "tier3"),
                       weights, {"high": 60, "medium": 30}, ["H2.1"])
    assert hi["tier"] == "high" and lo["tier"] == "low"
