"""Deterministic secret scanner: detects credentials, never emits the raw secret."""
from harness.domain.secrets import scan_secrets


def test_detects_and_redacts_aws_key():
    hits = scan_secrets("cfg: AKIAIOSFODNN7EXAMPLE ;")
    assert [h.kind for h in hits] == ["aws_access_key_id"]
    h = hits[0]
    assert "AKIAIOSFODNN7EXAMPLE" not in h.redacted        # raw secret never surfaced
    assert h.redacted.startswith("AKIA") and h.redacted.endswith("MPLE")
    assert h.fingerprint.startswith("sha256:")


def test_detects_private_key_and_inline_credential():
    assert any(h.kind == "private_key_block"
               for h in scan_secrets("-----BEGIN RSA PRIVATE KEY-----\n..."))
    assert any(h.kind == "inline_credential"
               for h in scan_secrets("api_key = 'abcd1234efgh5678'"))


def test_clean_text_has_no_hits():
    assert scan_secrets("customer-support-agent AGT-001 agent") == []
    assert scan_secrets("") == []


def test_duplicate_secret_deduped_by_fingerprint():
    hits = scan_secrets("AKIAIOSFODNN7EXAMPLE and again AKIAIOSFODNN7EXAMPLE")
    assert len(hits) == 1
