"""Harness drivers — HarnessDriver implementations (B3 run-contract seam).

  - BuiltinDriver          the scenario driver (application/runner) — ships, runs offline.
  - AgenticOverlayDriver   STUB for the not-yet-built agentic overlay (adaptive attacks).
  - PyritDriver            STUB sketch for Microsoft PyRIT as an external attack engine.

Every driver honors the same contract, so the orchestrator treats them identically.
"""
from .overlay_driver import AgenticOverlayDriver  # noqa: F401
from .pyrit_driver import PyritDriver  # noqa: F401
from .garak_driver import GarakDriver  # noqa: F401
from .nemo_driver import NemoGuardrailsDriver  # noqa: F401
