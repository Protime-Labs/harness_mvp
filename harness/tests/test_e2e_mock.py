"""End-to-end mock run: the whole chain, offline, deterministic."""
from harness.application.orchestrator import run_assurance
from harness.interface import factory

ASSET = {"asset_id": "AGT-001", "type": "agent", "name": "customer-support-agent"}
UC = {"name": "customer-support", "data_classes": ["CPNI", "PII"], "exposure": "public",
      "write_tools": True, "users": ["external"], "criticality": "tier1"}


def _run(profile):
    ctx = factory.build_context(overrides={"TARGET_PROFILE": profile})
    return ctx, run_assurance(
        use_case=UC, asset=ASSET, policy=ctx["policy"], driver=ctx["driver"],
        adapter=ctx["adapter"], store=ctx["store"], detectors=ctx["detectors"],
        specs=ctx["specs"], registry_map=ctx["registry_map"], system_prompt=ctx["system_prompt"])


def test_vulnerable_blocks_with_findings():
    _, b = _run("vulnerable")
    assert b["gate"]["decision"] == "block"
    assert len(b["findings"]) > 0
    cats = {f["category"] for f in b["findings"]}
    assert "data_leakage.pii" in cats and "data_leakage.cpni" in cats  # detector-floored (C3)
    assert b["context"]["tier"] == "high"


def test_hardened_approves_clean():
    _, b = _run("hardened")
    assert b["gate"]["decision"] == "approve"
    assert len(b["findings"]) == 0


def test_replay_reproduces_run():
    _, b = _run("vulnerable")
    assert b["replay"]["ok"] is True


def test_plan_entries_carry_selection_reason():
    _, b = _run("vulnerable")
    assert b["plan"] and all(p.get("reason") for p in b["plan"])   # every planned harness is explained
    reasons = {p["harness"]: p["reason"] for p in b["plan"]}
    assert "pack" in reasons["H2.1"] or "clause" in reasons["H2.1"]


def test_governance_complete():
    _, b = _run("vulnerable")
    m = b["governance"]["metrics"]
    assert m["complete"] == m["checked"] and m["checked"] > 0


def test_advanced_pack_runs_new_harnesses():
    ctx = factory.build_context(overrides={"PACK": "advanced"})
    b = run_assurance(
        use_case=UC, asset=ASSET, policy=ctx["policy"], driver=ctx["driver"],
        adapter=ctx["adapter"], store=ctx["store"], detectors=ctx["detectors"],
        specs=ctx["specs"], registry_map=ctx["registry_map"], system_prompt=ctx["system_prompt"],
        judge_adapter=ctx["judge_adapter"])
    ran = set(b["harness_results"].keys())
    assert {"H1.1", "H1.4", "H2.2", "H2.4", "H1.5"}.issubset(ran)
    assert b["gate"]["decision"] == "block"
    cats = {f["category"] for f in b["findings"]}
    assert "excessive_agency.write" in cats and "fairness.stereotype" in cats


def test_foundational_pack_unchanged():
    ctx = factory.build_context()  # default
    b = run_assurance(
        use_case=UC, asset=ASSET, policy=ctx["policy"], driver=ctx["driver"],
        adapter=ctx["adapter"], store=ctx["store"], detectors=ctx["detectors"],
        specs=ctx["specs"], registry_map=ctx["registry_map"], system_prompt=ctx["system_prompt"])
    assert set(b["harness_results"].keys()) == {"H2.1", "H1.2", "H1.3", "H2.3"}
    assert len(b["findings"]) == 8


def test_untrusted_trust_escalates_harnesses_and_produces_scorecard():
    ctx = factory.build_context(overrides={"INHERENT_TRUST": "untrusted"})
    b = run_assurance(
        use_case=UC, asset=ASSET, policy=ctx["policy"], driver=ctx["driver"], adapter=ctx["adapter"],
        store=ctx["store"], detectors=ctx["detectors"], specs=ctx["specs"],
        registry_map=ctx["registry_map"], system_prompt=ctx["system_prompt"])
    # untrusted escalates the HARNESS SET (more coverage) — but does NOT move the gate threshold
    assert {"H1.1", "H2.2", "H2.4"} <= set(b["harness_results"].keys())
    assert b["run_config"]["fail_on_severity"] == "high" and b["run_config"]["quorum_n"] == 3
    assert b["scorecard"]["profile"] == "assurance" and b["scorecard"]["rows"]


def test_phi_use_case_selects_privacy_harness_via_clause():
    ctx = factory.build_context()  # default config carries per-tier packs + require_when
    phi_uc = {"name": "phi-svc", "data_classes": ["PHI"], "exposure": "internal",
              "write_tools": False, "users": ["internal"], "criticality": "tier3"}
    b = run_assurance(
        use_case=phi_uc, asset=ASSET, policy=ctx["policy"], driver=ctx["driver"], adapter=ctx["adapter"],
        store=ctx["store"], detectors=ctx["detectors"], specs=ctx["specs"],
        registry_map=ctx["registry_map"], system_prompt=ctx["system_prompt"])
    assert b["context"]["tier"] != "high"                      # low-ish score ...
    assert "H1.3" in b["context"]["required_harnesses"]        # ... yet the PHI clause forces H1.3 in
    reasons = {r["harness"]: r["reason"] for r in b["context"]["plan_reasons"]}
    assert reasons["H1.3"].startswith("clause:")


def test_quarantine_secret_short_circuits_before_execution():
    ctx = factory.build_context()
    asset = {"asset_id": "AGT-SECRET", "config": {"aws_key": "AKIAIOSFODNN7EXAMPLE"}}
    b = run_assurance(
        use_case=UC, asset=asset, policy=ctx["policy"], driver=ctx["driver"],
        adapter=ctx["adapter"], store=ctx["store"], detectors=ctx["detectors"],
        specs=ctx["specs"], registry_map=ctx["registry_map"], system_prompt=ctx["system_prompt"])
    assert b["gate"]["decision"] == "block"
    assert b["gate"]["matched_rule"] == "1.quarantine_block"
    assert b["harness_results"] == {}                      # ingress refused -> nothing executed
    assert b["quarantine"]["decision"] == "block" and len(b["quarantine"]["findings"]) == 1
    assert b["findings"] == []                             # scanner findings live in the quarantine object
    assert b["replay"]["ok"] is True


def test_declaration_mismatch_detects_undeclared_leak():
    from harness.application.orchestrator import _declaration_mismatch
    from harness.domain.contracts import Finding
    leak = Finding(id="F", source="harness", severity="high", category="data_leakage.pii", title="t",
                   description="d", blocking=True, policy_rule="P", evidence_uri="", recommendation="")
    assert _declaration_mismatch({"data_classes": ["public"]}, [leak]) is True   # undeclared exposure
    assert _declaration_mismatch({"data_classes": ["PII"]}, [leak]) is False     # declared -> consistent
    assert _declaration_mismatch({"data_classes": ["public"]}, []) is False      # nothing observed


def test_determinism_same_findings_twice():
    _, a = _run("vulnerable")
    _, b = _run("vulnerable")
    ka = sorted((f["id"], f["severity"]) for f in a["findings"])
    kb = sorted((f["id"], f["severity"]) for f in b["findings"])
    assert ka == kb
