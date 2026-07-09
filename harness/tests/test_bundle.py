"""M3 — persisted run bundle replays from disk after the process exits; tampering fails (C4)."""
import os

from harness.application.bundle import validate_run_bundle, write_run_bundle
from harness.application.orchestrator import run_assurance
from harness.interface import factory

ASSET = {"asset_id": "AGT-001", "type": "agent", "name": "att-customer-support-agent"}
UC = {"name": "att-customer-support", "data_classes": ["CPNI", "PII"], "exposure": "public",
      "write_tools": True, "users": ["external"], "criticality": "tier1"}

MANIFESTS = ["run_config.json", "gate_decision.json", "findings.json", "evidence_manifest.json",
             "replay_manifest.json", "policy_manifest.json", "scenario_manifest.json", "result_bundle.json"]


def _run():
    ctx = factory.build_context()
    b = run_assurance(
        use_case=UC, asset=ASSET, policy=ctx["policy"], driver=ctx["driver"], adapter=ctx["adapter"],
        store=ctx["store"], detectors=ctx["detectors"], specs=ctx["specs"],
        registry_map=ctx["registry_map"], system_prompt=ctx["system_prompt"])
    return ctx, b


def test_bundle_persists_and_replays_from_disk(tmp_path):
    ctx, b = _run()
    out = write_run_bundle(b, ctx["store"], ctx["policy"], ctx["specs"], str(tmp_path / "RUN-test"))
    for name in MANIFESTS:
        assert os.path.exists(os.path.join(out, name)), name
    # every target turn also persisted its input (both sides of the chain)
    assert any(f.endswith(".target.input.txt") for f in os.listdir(os.path.join(out, "evidence")))

    rep = validate_run_bundle(out)
    assert rep["ok"] is True
    assert rep["replayed_gate"] == rep["expected_gate"] == "block"
    assert rep["candidates"] > 0 and rep["tamper"] is None


def test_validate_accepts_replay_manifest_path(tmp_path):
    ctx, b = _run()
    out = write_run_bundle(b, ctx["store"], ctx["policy"], ctx["specs"], str(tmp_path / "RUN-2"))
    rep = validate_run_bundle(os.path.join(out, "replay_manifest.json"))
    assert rep["ok"] is True


def test_tampered_evidence_fails_validation(tmp_path):
    ctx, b = _run()
    out = write_run_bundle(b, ctx["store"], ctx["policy"], ctx["specs"], str(tmp_path / "RUN-tamper"))
    ev = os.path.join(out, "evidence")
    target = next(f for f in os.listdir(ev) if f.endswith(".target.txt"))
    with open(os.path.join(ev, target), "a", encoding="utf-8") as f:
        f.write("TAMPERED")
    rep = validate_run_bundle(out)
    assert rep["ok"] is False and rep["tamper"] is not None
