"""B2 — the model-I/O seam. The ONE path every model call goes through (R2/A2).

Janus, any LiteLLM-backed provider, and the AT&T Model Router all plug in HERE by
implementing this Protocol. The application never imports a concrete provider — it depends
only on `ModelPort`, so swapping mock -> real -> Janus is a wiring change, not a code change.
"""
from __future__ import annotations

from typing import Any, Dict, Protocol, runtime_checkable


@runtime_checkable
class ModelPort(Protocol):
    """A provider-independent model interface.

    Implementations MUST expose a stable `name` and a single `invoke` method. `role` is one
    of {"target", "attacker", "judge"} so an adapter can route or shape the call if needed.
    """

    name: str

    def invoke(self, role: str, prompt: str, system: str = "", **kw: Any) -> Dict[str, Any]:
        """Return a dict with at least:
            {
              "text":  str,                     # the model output
              "tokens": {"in": int, "out": int},
              "cost_usd": float,
              "model": {"provider": str, "model": str, ...},  # provenance for evidence
            }
        """
        ...
