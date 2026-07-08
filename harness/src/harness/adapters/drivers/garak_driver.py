"""NVIDIA Garak as a DRIVER (B3 seam) — guarded, target-bound.

Garak is a vulnerability *scanner* driven from the CLI against a generator (a served model
endpoint). It has no clean offline embedding against the mock, so this driver requires the
package (`pip install -e ".[redteam]"`) AND a reachable target endpoint.

Integration recipe (documented, not run in the offline prototype): expose the asset-under-test
as an HTTP endpoint (or a Garak `rest`/`function` generator that calls our ModelPort), run the
chosen Garak probes as a subprocess, parse Garak's JSONL report, and map each hit to a canonical
`Finding`. Until a served target is wired this raises an actionable error — which is why the
inventory keeps Garak `installable`, not `available`.
"""
from __future__ import annotations

from typing import Any, Callable, Dict


class GarakDriver:
    name = "garak"

    def __init__(self, detectors: Dict[str, Callable], system_prompt: str, judge_adapter: Any = None):
        self.detectors = detectors
        self.system_prompt = system_prompt
        self.judge_adapter = judge_adapter

    def run(self, spec, adapter, store, cfg):
        try:
            import garak  # noqa: F401
        except Exception as exc:
            raise RuntimeError(
                "Garak not installed. `pip install -e \".[redteam]\"`. Garak is a CLI scanner that "
                "probes a served target, so it does not run against the offline mock."
            ) from exc
        raise RuntimeError(
            "Garak needs a served target. Recipe: expose the asset via a `rest`/`function` generator "
            "that calls ports.model_port, run `garak --model_type ... --probes ...` as a subprocess, "
            "parse the JSONL report, and map hits to canonical Findings."
        )
