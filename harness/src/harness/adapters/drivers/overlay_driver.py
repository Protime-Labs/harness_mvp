"""STUB — the agentic overlay driver (DR-06 / B3 seam).

When the agentic overlay is built it plugs in HERE: instead of iterating a fixed scenario
list, it runs an attacker AGENT that reads the target's transcript and generates ADAPTIVE
follow-up attacks (multi-turn). Whatever it does internally, it MUST emit the same run-contract
output as the BuiltinDriver, so the orchestrator and gate are unchanged.

Until then this raises a clear NotImplementedError; the orchestrator falls back to BuiltinDriver.
"""
from __future__ import annotations

from typing import Any

from ...domain.contracts import HarnessSpec


class AgenticOverlayDriver:
    name = "agentic-overlay"

    def __init__(self, max_turns_per_scenario: int = 4):
        self.max_turns_per_scenario = max_turns_per_scenario

    def run(self, spec: HarnessSpec, adapter: Any, store: Any, cfg: Any):
        raise NotImplementedError(
            "Agentic overlay not built (DR-06). Define the driver against ports.driver_port."
            " Contract: consume (spec, model_port, evidence_port, cfg); run an adaptive attacker"
            " agent; capture every turn as evidence; judge via the same quorum; return"
            " (result_dict, turns, verdicts, manifest, findings)."
        )
