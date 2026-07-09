"""HTTP/endpoint target as a registered asset: env-ref resolution + inline-secret hygiene."""
from harness.application.endpoints import (endpoint_overrides, inline_secret_refs,
                                           is_endpoint_asset, resolve_endpoint)


def test_is_endpoint_asset():
    assert is_endpoint_asset({"type": "application_endpoint"})
    assert is_endpoint_asset({"type": "model_endpoint"})
    assert not is_endpoint_asset({"type": "agent"})


def test_resolve_endpoint_expands_env_refs(monkeypatch):
    monkeypatch.setenv("TARGET_URL", "http://127.0.0.1:8765/evaluate")
    monkeypatch.setenv("TARGET_TOKEN", "s3cr3t-value-abcdefgh")
    asset = {"type": "application_endpoint", "endpoint_url_ref": "env:TARGET_URL",
             "auth_ref": "env:TARGET_TOKEN", "response_path": "output"}
    ep = resolve_endpoint(asset)
    assert ep["url"] == "http://127.0.0.1:8765/evaluate"
    assert ep["headers"]["Authorization"] == "Bearer s3cr3t-value-abcdefgh"
    assert ep["response_path"] == "output"


def test_env_ref_asset_has_no_inline_secrets():
    asset = {"type": "application_endpoint", "endpoint_url_ref": "env:TARGET_URL",
             "auth_ref": "env:TARGET_TOKEN", "headers": {"X-Client": "harness"}}
    assert inline_secret_refs(asset) == []


def test_inline_literal_secret_is_flagged():
    asset = {"type": "application_endpoint", "endpoint_url_ref": "http://x",
             "auth_ref": "AKIAIOSFODNN7EXAMPLE"}
    assert "auth_ref" in inline_secret_refs(asset)


def test_endpoint_overrides_target_http(monkeypatch):
    monkeypatch.setenv("TARGET_URL", "http://x/evaluate")
    ov = endpoint_overrides({"type": "application_endpoint", "endpoint_url_ref": "env:TARGET_URL",
                             "headers": {"X-Client": "harness"}})
    assert ov["PROVIDER_MODE"] == "http" and ov["HTTP_TARGET_URL"] == "http://x/evaluate"
    assert "X-Client=harness" in ov["HTTP_HEADERS"]
