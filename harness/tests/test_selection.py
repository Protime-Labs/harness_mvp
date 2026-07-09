"""W2 selection + coverage: a skipped required harness must be gate-visible (A8 fail-closed)."""
from harness.application.selection import coverage_complete, select


REGISTRY = {
    "H2.1": {"implemented": True},
    "H1.2": {"implemented": True},
    "H5.1": {"implemented": True, "governance": True},
    "H4.4": {"implemented": False},   # declared but not in the MVP core
}


def test_select_skips_unimplemented_and_unregistered_with_reason():
    plan, skipped = select(["H2.1", "H4.4", "H9.9", "H5.1"], REGISTRY)
    planned = {p["harness"] for p in plan}
    assert planned == {"H2.1", "H5.1"}
    reasons = {s["harness"]: s["reason"] for s in skipped}
    assert set(reasons) == {"H4.4", "H9.9"}          # both skipped, never silently dropped
    assert "not in registry" in reasons["H9.9"]


def test_coverage_complete_true_when_all_ran_and_nothing_skipped():
    results = {"H2.1": {"status": "completed"}, "H1.2": {"status": "completed"}}
    assert coverage_complete(results, ["H2.1", "H1.2"], skipped=[]) is True


def test_coverage_incomplete_when_a_required_harness_was_skipped():
    # Even though everything that ran completed, a skipped required harness is a coverage gap.
    results = {"H2.1": {"status": "completed"}}
    assert coverage_complete(results, ["H2.1"], skipped=[{"harness": "H4.4", "reason": "not in core"}]) is False


def test_coverage_incomplete_when_a_planned_harness_did_not_complete():
    results = {"H2.1": {"status": "completed"}, "H1.2": {"status": "budget_exceeded"}}
    assert coverage_complete(results, ["H2.1", "H1.2"], skipped=[]) is False
