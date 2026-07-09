"""Quarantine front door: a secret in asset content blocks ingress with a redacted finding."""
from harness.application.quarantine import screen_asset

CLEAN_ASSET = {"asset_id": "AGT-001", "type": "agent", "name": "att-customer-support-agent"}


def test_clean_asset_allows():
    q = screen_asset(CLEAN_ASSET, {})
    assert q["decision"] == "allow" and q["findings"] == []


def test_seeded_secret_blocks_with_redacted_finding():
    asset = {"asset_id": "AGT-002", "config": {"aws_key": "AKIAIOSFODNN7EXAMPLE"}}
    q = screen_asset(asset, {})
    assert q["decision"] == "block"
    assert len(q["findings"]) == 1
    f = q["findings"][0]
    assert f["source"] == "scanner" and f["severity"] == "critical" and f["blocking"] is True
    assert f["basis"].startswith("detector")
    # the raw secret must not leak into the finding anywhere (redaction is mandatory)
    assert "AKIAIOSFODNN7EXAMPLE" not in str(f)


def test_secret_nested_in_list_is_found():
    asset = {"asset_id": "AGT-003", "tools": [{"name": "t", "token": "xoxb-1234567890-abcdefghij"}]}
    assert screen_asset(asset, {})["decision"] == "block"
