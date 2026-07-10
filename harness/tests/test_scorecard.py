"""Req 2 — vulnerability × trust scorecard + trust reconciliation."""
from harness.adapters.config import defaults
from harness.application.scorecard import build_scorecard, resolve_profile

CRIT = defaults.CRITERIA


def _f(harness, blocking):
    return {"id": f"F-{harness}", "harness": harness, "severity": "critical", "blocking": blocking}


def test_scorecard_pass_warn_fail_nottested():
    ran = ["H2.1", "H2.3", "H2.2"]
    findings = [_f("H2.1", True), _f("H2.2", False)]         # H2.1 blocking, H2.2 advisory
    sc = build_scorecard(["LLM01", "LLM06", "LLM07"], CRIT, ran, findings, trust="high")
    rows = {r["criterion"]: r["status"] for r in sc["rows"]}
    assert rows["LLM01"] == "fail"                            # H2.1 blocking finding
    assert rows["LLM06"] == "warn"                            # H2.2 non-blocking finding
    assert rows["LLM07"] == "not_tested"                      # H2.4 not in the plan


def test_trust_reconciliation_flags_downgrade():
    sc = build_scorecard(["LLM01"], CRIT, ["H2.1"], [_f("H2.1", True)], trust="high")
    assert sc["observed_trust"] == "low" and sc["trust_downgrade"] is True


def test_trust_consistent_when_all_pass():
    sc = build_scorecard(["LLM01"], CRIT, ["H2.1"], [], trust="high")
    assert sc["observed_trust"] == "high" and sc["trust_downgrade"] is False


def test_resolve_profile_by_mode():
    name, ids = resolve_profile({"MODE": "operations"}, defaults.CRITERIA_PROFILES)
    assert name == "operations" and set(ids) == {"LLM01", "LLM02", "LLM06"}
