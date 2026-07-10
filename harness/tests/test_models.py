"""Req 1 — model registry + console switching: aliases, raw ids, inherent trust."""
import pytest

from harness.adapters.config.loader import load_model_registry, resolve_model_ref


def test_registry_loads_with_trust_tiers():
    reg = load_model_registry()
    ids = {m["id"] for m in reg}
    assert {"haiku", "sonnet"} <= ids
    haiku = next(m for m in reg if m["id"] == "haiku")
    assert haiku["inherent_trust"] == "high" and "target" in haiku["roles"]
    oss = next(m for m in reg if m["id"] == "oss-local")
    assert oss["inherent_trust"] == "untrusted"


def test_resolve_alias_returns_model_and_trust():
    model, trust = resolve_model_ref("haiku", load_model_registry())
    assert model.startswith("anthropic/") and trust == "high"


def test_resolve_raw_litellm_id_passthrough():
    raw, trust = resolve_model_ref("openai/gpt-4o-mini", load_model_registry())
    assert raw == "openai/gpt-4o-mini" and trust is None


def test_resolve_unknown_alias_fails_loud():
    with pytest.raises(ValueError):
        resolve_model_ref("nonesuch", load_model_registry())
