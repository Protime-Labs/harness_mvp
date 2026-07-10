"""W1 risk contextualization — fail-closed unknown attributes (F1), per-tier packs (F2),
require_when clauses + A11 monotonicity (F3)."""
from harness.domain.contracts import UseCase
from harness.domain.risk import contextualize, risk_score

WEIGHTS = {
    "data_class": {"CPNI": 32, "PII": 30, "PHI": 35, "confidential": 20, "public": 0},
    "exposure": {"public": 25, "internal": 5},
    "write_tools": {"present": 20, "absent": 0},
    "users": {"external": 15, "internal": 0},
    "criticality": {"tier1": 15, "tier3": 5},
}
CUT = {"high": 60, "medium": 30}
PACKS = {"low": ["H1.2"], "medium": ["H1.2", "H2.1"], "high": ["H2.1", "H1.2", "H1.3", "H2.3", "H5.1"]}
REQUIRE = [
    {"when": {"attr": "data_classes", "contains": "PHI"}, "require": ["H1.3"]},
    {"when": {"attr": "write_tools", "equals": True}, "require": ["H2.1"]},
]


# ---- F1: unknown attributes fail closed ----------------------------------------------------
def test_unknown_attribute_scores_max_not_zero():
    score, unknown = risk_score(UseCase("x", ["biometrik"], "public", False, ["internal"], "tier3"), WEIGHTS)
    assert "data_class:biometrik" in unknown          # flagged
    assert score == 35 + 25 + 0 + 0 + 5               # max data_class (35) applied, not fail-open 0


def test_known_attributes_have_no_unknowns():
    r = contextualize(UseCase("x", ["CPNI"], "public", True, ["external"], "tier1"), WEIGHTS, CUT, ["H2.1"])
    assert r["unknown_attributes"] == []


# ---- F2: risk tier drives selection --------------------------------------------------------
def test_tier_selects_different_packs():
    lo = contextualize(UseCase("l", ["public"], "internal", False, ["internal"], "tier3"),
                       WEIGHTS, CUT, ["fallback"], packs=PACKS)
    hi = contextualize(UseCase("h", ["CPNI"], "public", True, ["external"], "tier1"),
                       WEIGHTS, CUT, ["fallback"], packs=PACKS)
    assert lo["tier"] == "low" and set(lo["required_harnesses"]) == {"H1.2"}
    assert hi["tier"] == "high" and "H2.3" in hi["required_harnesses"]


def test_missing_packs_falls_back_to_foundational_pack():
    r = contextualize(UseCase("x", ["public"], "internal", False, ["internal"], "tier3"),
                      WEIGHTS, CUT, ["H2.1", "H1.2"])  # no packs -> fallback for all tiers
    assert r["required_harnesses"] == ["H2.1", "H1.2"]


# ---- F3: require_when clauses + reasons -----------------------------------------------------
def test_phi_still_requires_privacy_harness_via_clause():
    # PHI + low-everything-else: the tier pack has no H1.3; the PHI clause forces it in (dilution-proof).
    packs = {"low": ["H1.2"], "medium": ["H1.2"], "high": ["H2.1"]}
    r = contextualize(UseCase("phi", ["PHI"], "internal", False, ["internal"], "tier3"),
                      WEIGHTS, CUT, ["fallback"], packs=packs, require_when=REQUIRE)
    assert "H1.3" not in packs[r["tier"]]              # not in the tier pack ...
    assert "H1.3" in r["required_harnesses"]           # ... but required, via the clause
    reasons = {x["harness"]: x["reason"] for x in r["plan_reasons"]}
    assert reasons["H1.3"].startswith("clause:")       # F8: carries its selection reason


def test_require_when_write_tools_clause():
    r = contextualize(UseCase("w", ["public"], "internal", True, ["internal"], "tier3"),
                      WEIGHTS, CUT, ["H1.2"], require_when=REQUIRE)
    assert "H2.1" in r["required_harnesses"]


# ---- Req 2: trust escalation (second negotiation axis) -------------------------------------
ESC = {"high": [], "moderate": ["H1.2"], "low": ["H1.2", "H1.4"], "untrusted": ["H1.2", "H1.4", "H2.2"]}


def test_untrusted_model_escalates_harnesses():
    r = contextualize(UseCase("x", ["public"], "internal", False, ["internal"], "tier3"),
                      WEIGHTS, CUT, ["H5.1"], trust="untrusted", trust_escalation=ESC)
    assert {"H1.2", "H1.4", "H2.2"} <= set(r["required_harnesses"]) and r["trust"] == "untrusted"
    reasons = {x["harness"]: x["reason"] for x in r["plan_reasons"]}
    assert "trust" in reasons["H2.2"]


def test_high_trust_adds_no_escalation():
    r = contextualize(UseCase("x", ["public"], "internal", False, ["internal"], "tier3"),
                      WEIGHTS, CUT, ["H5.1"], trust="high", trust_escalation=ESC)
    assert set(r["required_harnesses"]) == {"H5.1"}


def test_trust_axis_is_monotonic():
    uc = UseCase("x", ["public"], "internal", False, ["internal"], "tier3")
    hi = set(contextualize(uc, WEIGHTS, CUT, ["H5.1"], trust="high", trust_escalation=ESC)["required_harnesses"])
    for t in ("moderate", "low", "untrusted"):
        assert hi <= set(contextualize(uc, WEIGHTS, CUT, ["H5.1"], trust=t, trust_escalation=ESC)["required_harnesses"])
