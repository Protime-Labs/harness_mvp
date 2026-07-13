"""Req 2 — vulnerability × criteria scorecard + the grounded trusted_but_failing flag."""
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


def test_trusted_but_failing_is_grounded_not_inferred():
    # declared high + a blocking finding -> grounded flag; NO fabricated "observed trust"
    sc = build_scorecard(["LLM01"], CRIT, ["H2.1"], [_f("H2.1", True)], trust="high")
    assert sc["trusted_but_failing"] is True and "observed_trust" not in sc
    # declared high + clean -> not flagged
    assert build_scorecard(["LLM01"], CRIT, ["H2.1"], [], trust="high")["trusted_but_failing"] is False
    # only declared-HIGH trips it (a low-trust failing model is expected, not a surprise)
    assert build_scorecard(["LLM01"], CRIT, ["H2.1"], [_f("H2.1", True)], trust="low")["trusted_but_failing"] is False


def test_resolve_profile_by_criteria():
    name, ids = resolve_profile({"CRITERIA_PROFILE": "operations"}, defaults.CRITERIA_PROFILES)
    assert name == "operations" and set(ids) == {"LLM01", "LLM02", "LLM06"}
    assert resolve_profile({}, defaults.CRITERIA_PROFILES)[0] == "assurance"   # default
