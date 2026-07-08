"""Real provider via LiteLLM (C2, BF-15) — a ModelPort implementation over 100+ providers.

Same interface as MockAdapter, so NO harness code changes when you swap it in. This is the
concrete B2 seam for real models (Anthropic, OpenAI, Azure, Bedrock, Databricks, a local
gateway, or the AT&T Model Router fronting any of them).

Judge independence (A4/BF-20) is enforced by the application, not here: the runner is given a
separate judge adapter whose model MUST differ from the target's.

Requires: `pip install litellm` and a provider key in the environment. Never hard-code keys.
"""
from __future__ import annotations

from typing import Any, Dict


class LiteLLMAdapter:
    name = "litellm"

    def __init__(self, model: str, temperature: float = 0.0):
        self.model = model
        self.temperature = temperature

    def invoke(self, role: str, prompt: str, system: str = "", **kw: Any) -> Dict[str, Any]:
        import litellm  # imported lazily so the core stays install-free

        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        r = litellm.completion(model=self.model, temperature=self.temperature, messages=messages)
        u = r.get("usage", {}) or {}  # litellm ModelResponse supports dict-style access
        return {
            "text": r["choices"][0]["message"]["content"],
            "tokens": {"in": u.get("prompt_tokens", 0), "out": u.get("completion_tokens", 0)},
            "cost_usd": 0.0,
            "model": {"provider": "litellm", "model": self.model, "temperature": self.temperature},
        }
