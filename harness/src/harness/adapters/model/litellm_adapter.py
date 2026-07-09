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

    def __init__(self, model: str, temperature: float = 0.0, pricing: Dict[str, Any] | None = None):
        self.model = model
        self.temperature = temperature
        # Optional fallback pricing for models LiteLLM can't price: {model: {in_per_1k, out_per_1k}}.
        self.pricing = pricing or {}

    def invoke(self, role: str, prompt: str, system: str = "", **kw: Any) -> Dict[str, Any]:
        import litellm  # imported lazily so the core stays install-free

        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        r = litellm.completion(model=self.model, temperature=self.temperature, messages=messages)
        u = r.get("usage", {}) or {}  # litellm ModelResponse supports dict-style access
        tokens = {"in": u.get("prompt_tokens", 0), "out": u.get("completion_tokens", 0)}
        return {
            "text": r["choices"][0]["message"]["content"],
            "tokens": tokens,
            "cost_usd": self._cost(r, tokens),
            "model": {"provider": "litellm", "model": self.model, "temperature": self.temperature},
        }

    def _cost(self, response: Any, tokens: Dict[str, int]):
        """USD for this call, or None when the model can't be priced (caller routes cost-governed
        runs to manual_review rather than silently assuming $0)."""
        # 1 — LiteLLM's built-in cost map (covers Anthropic/OpenAI/Azure/Bedrock/…)
        try:
            import litellm
            c = litellm.completion_cost(completion_response=response)
            if c and c > 0:
                return float(c)
        except Exception:
            pass
        # 2 — explicit fallback pricing for models LiteLLM doesn't know (e.g. a custom gateway)
        p = self.pricing.get(self.model)
        if p:
            return round(tokens["in"] / 1000 * p.get("in_per_1k", 0.0)
                         + tokens["out"] / 1000 * p.get("out_per_1k", 0.0), 6)
        # 3 — unknown price
        return None
