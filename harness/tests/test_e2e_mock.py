"""End-to-end mock run: the whole chain, offline, deterministic."""
from harness.application.orchestrator import run_assurance
from harness.interface import factory

ASSET = {"asset_id": "AGT-001", "type": "agent", "name": "att-customer-support-agent"}
UC = {"name": "att-customer-support", "data_classes": ["CPNI", "PII"], "exposure": "public",
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


def test_governance_complete():
    _, b = _run("vulnerable")
    m = b["governance"]["metrics"]
    assert m["complete"] == m["checked"] and m["checked"] > 0


def test_determinism_same_findings_twice():
    _, a = _run("vulnerable")
    _, b = _run("vulnerable")
    ka = sorted((f["id"], f["severity"]) for f in a["findings"])
    kb = sorted((f["id"], f["severity"]) for f in b["findings"])
    assert ka == kb
