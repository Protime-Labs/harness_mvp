"""B3 — the run-contract seam. The execution shape: attacker -> target -> judge -> findings.

The built-in scenario driver ships in application/runner. The AGENTIC OVERLAY plugs in HERE
(it consumes the transcript and produces adaptive attacks); external red-team engines
(PyRIT, Garak, Promptfoo) plug in HERE too. Every driver, whatever its internals, MUST honor
the run contract: consume a HarnessSpec + ModelPort + EvidencePort + RunConfig, and emit a
result.json-shaped dict plus the canonical Finding list.
"""
from __future__ import annotations

from typing import Any, Dict, List, Protocol, Tuple, runtime_checkable

from ..domain.contracts import Finding, HarnessSpec

# (result_dict, turns, verdicts, manifest, findings)
DriverOutput = Tuple[Dict[str, Any], List[dict], List[dict], List[dict], List[Finding]]


@runtime_checkable
class HarnessDriver(Protocol):
    """Runs one harness end-to-end. `name` identifies the driver in evidence/provenance."""

    name: str

    def run(self, spec: HarnessSpec, adapter: Any, store: Any, cfg: Any) -> DriverOutput:
        ...
