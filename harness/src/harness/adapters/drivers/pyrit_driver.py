"""STUB — Microsoft PyRIT as an external attack engine (B3 seam, redteam extra).

PyRIT (Python Risk Identification Tool) orchestrates automated multi-turn attacks. To adopt
it as a driver: wrap PyRIT's orchestrator so its prompts flow through OUR ModelPort (keeping
provider-independence and evidence capture), then normalize PyRIT's results into the canonical
Finding + run-contract output. The gate/quorum never change — PyRIT is just another way to
generate the attacker turns.

Garak and Promptfoo would follow the same pattern (one driver each).
"""
from __future__ import annotations

from typing import Any

from ...domain.contracts import HarnessSpec


class PyritDriver:
    name = "pyrit"

    def run(self, spec: HarnessSpec, adapter: Any, store: Any, cfg: Any):
        raise NotImplementedError(
            "PyRIT driver not wired. Install `pyrit` (extra: redteam), route its PromptTarget"
            " through ports.model_port.ModelPort, capture turns via ports.evidence_port, and map"
            " PyRIT scores to canonical Findings. Return the run-contract 5-tuple."
        )
