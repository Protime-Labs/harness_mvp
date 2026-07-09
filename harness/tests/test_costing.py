"""Real-provider cost accounting: fallback pricing, unknown -> None, runner flags unknown cost."""
from harness.adapters.evidence import FileEvidenceStore
from harness.adapters.model.litellm_adapter import LiteLLMAdapter
from harness.adapters.model.mock_adapter import MockAdapter
from harness.application.runner import BuiltinDriver
from harness.domain.contracts import HarnessSpec, Scenario


def test_cost_fallback_pricing_used_when_litellm_cannot_price():
    a = LiteLLMAdapter("gateway/custom", pricing={"gateway/custom": {"in_per_1k": 1.0, "out_per_1k": 2.0}})
    # completion_cost can't price a bare {} response -> fallback pricing: 1000/1k*1 + 500/1k*2 = 2.0
    assert a._cost(response={}, tokens={"in": 1000, "out": 500}) == 2.0


def test_cost_unknown_returns_none_without_pricing():
    a = LiteLLMAdapter("gateway/unpriced")
    assert a._cost(response={}, tokens={"in": 10, "out": 10}) is None


class _NoCostMock:
    """Mock target whose price is undeterminable (a custom gateway LiteLLM can't price)."""
    name = "mock"

    def __init__(self):
        self._m = MockAdapter(seed=42, profile="vulnerable")

    def invoke(self, role, prompt, system="", **kw):
        r = self._m.invoke(role, prompt, system=system, **kw)
        r["cost_usd"] = None
        return r


def test_runner_flags_unknown_cost_without_crashing():
    spec = HarnessSpec(id="HT.1", name="t", category="test", lenses=["policy_compliance"],
                       detectors=[], scenarios=[Scenario(id="s1", title="t", category="c", attack="hello")])
    cfg = {"BUDGET": {"max_turns": 100, "max_tokens": 200_000, "max_cost_usd": 5.0, "max_wall_clock_s": 600},
           "QUORUM_N": 1, "QUORUM_RULE": "majority", "SEED": 42, "FAIL_ON_SEVERITY": "high"}
    driver = BuiltinDriver(detectors={}, system_prompt="sys", judge_adapter=None)
    result, *_ = driver.run(spec, _NoCostMock(), FileEvidenceStore(), cfg)
    assert result["metrics"]["cost_known"] is False
    assert result["status"] == "completed"   # an undetermined cost is not a budget breach
