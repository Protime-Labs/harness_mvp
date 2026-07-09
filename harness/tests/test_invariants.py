"""The invariant acceptance suite must pass end-to-end on the mock (BF-24 / CI gate)."""
from harness.application.acceptance import run_invariant_suite
from harness.application.orchestrator import run_assurance
from harness.interface import factory

ASSET = {"asset_id": "AGT-001", "type": "agent", "name": "customer-support-agent"}
UC = {"name": "customer-support", "data_classes": ["CPNI", "PII"], "exposure": "public",
      "write_tools": True, "users": ["external"], "criticality": "tier1"}


def test_all_invariants_pass():
    ctx = factory.build_context()
    bundle = run_assurance(
        use_case=UC, asset=ASSET, policy=ctx["policy"], driver=ctx["driver"],
        adapter=ctx["adapter"], store=ctx["store"], detectors=ctx["detectors"],
        specs=ctx["specs"], registry_map=ctx["registry_map"], system_prompt=ctx["system_prompt"])
    results = run_invariant_suite(
        bundle, cfg=ctx["cfg"], specs=ctx["specs"], make_store=ctx["make_store"],
        make_adapter=ctx["make_adapter"], make_driver=ctx["make_driver"])
    failures = [name for name, ok in results if not ok]
    assert not failures, f"invariant failures: {failures}"
    assert len(results) >= 10
