"""Minimal programmatic use of the harness (offline mock). Run:  python examples/run_mock.py

Shows the composition-root pattern: build_context() wires the concrete adapters, then the
application orchestrator runs the provider-independent workflow.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from harness.application.orchestrator import run_assurance   # noqa: E402
from harness.interface import factory                         # noqa: E402
from harness.interface.report import render_report            # noqa: E402

ASSET = {"asset_id": "AGT-001", "type": "agent", "name": "customer-support-agent"}
USE_CASE = {"name": "customer-support", "data_classes": ["CPNI", "PII"], "exposure": "public",
            "write_tools": True, "users": ["external"], "criticality": "tier1"}


def main():
    ctx = factory.build_context()  # mock provider, defaults
    bundle = run_assurance(
        use_case=USE_CASE, asset=ASSET, policy=ctx["policy"], driver=ctx["driver"],
        adapter=ctx["adapter"], store=ctx["store"], detectors=ctx["detectors"],
        specs=ctx["specs"], registry_map=ctx["registry_map"], system_prompt=ctx["system_prompt"])
    print(render_report(bundle, ctx["specs"]))
    print(f"\nGATE: {bundle['gate']['decision'].upper()}  |  findings: {len(bundle['findings'])}"
          f"  |  replay: {'ok' if bundle['replay']['ok'] else 'FAIL'}")
    print(f"evidence: {bundle['evidence_root']}")


if __name__ == "__main__":
    main()
