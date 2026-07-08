"""NVIDIA NeMo Guardrails as a DRIVER (B3 seam) — guarded, model-bound.

NeMo Guardrails is a *guardrail runtime*: its rails need a live LLM to evaluate input/output
against Colang flows. It therefore cannot run in the pure-offline mock lab — it requires the
package (`pip install -e ".[guardrails]"`) AND a real provider (`--provider litellm`).

When both prerequisites are met, this driver builds an `LLMRails` app around the configured
model, runs each scenario through it, and scores the guarded output with OUR judge quorum +
detectors into canonical `Finding`s (the gate stays ours). Otherwise it raises an actionable
error rather than pretending to run — that honesty is why the capability inventory keeps NeMo
as `installable`, not `available`, until a live model is wired.
"""
from __future__ import annotations

from typing import Any, Callable, Dict


class NemoGuardrailsDriver:
    name = "nemo"

    def __init__(self, detectors: Dict[str, Callable], system_prompt: str, judge_adapter: Any = None):
        self.detectors = detectors
        self.system_prompt = system_prompt
        self.judge_adapter = judge_adapter

    def run(self, spec, adapter, store, cfg):
        try:
            import nemoguardrails  # noqa: F401
        except Exception as exc:
            raise RuntimeError(
                "NeMo Guardrails not installed. `pip install -e \".[guardrails]\"`. It is a guardrail "
                "runtime and needs a live LLM, so it does not run against the offline mock."
            ) from exc
        if getattr(adapter, "name", "") != "litellm":
            raise RuntimeError(
                "NeMo Guardrails requires a live model. Re-run with `--provider litellm` (and a key). "
                "Integration recipe: build LLMRails(RailsConfig) over the configured model, call "
                "rails.generate() per scenario, then score the guarded output with the shared judge "
                "quorum + detectors (see pyrit_driver.py for the scoring pattern) into canonical Findings."
            )
        # A live-model implementation plugs in here (kept out of the offline prototype path):
        raise NotImplementedError(
            "NeMo live-model driver not enabled in this lab build. Implement LLMRails generation +"
            " shared scoring against ports.model_port to complete it."
        )
