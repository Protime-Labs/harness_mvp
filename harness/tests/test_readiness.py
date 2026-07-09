"""M5 — MVP vs enterprise readiness split; Golden Controls as an unresolved dependency record."""
from harness.application.readiness import assess_enterprise_readiness, assess_mvp_readiness
from harness.interface import factory


def test_mock_run_is_mvp_ready_but_not_enterprise_ready():
    ctx = factory.build_context()
    kw = dict(store=ctx["store"], detectors=ctx["detectors"],
              driver_name=getattr(ctx["driver"], "name", None), specs=ctx["specs"])
    mvp = assess_mvp_readiness(ctx["policy"], **kw)
    ent = assess_enterprise_readiness(ctx["policy"], **kw)
    assert mvp["ready"] is True                       # a fully-local run IS mvp-ready ...
    assert ent["missing"]                             # ... but not enterprise-ready
    assert mvp["enabled"]["quarantine_scanner"] == "local-regex-secrets"
    assert mvp["enabled"]["persistence"] == "sqlite (local)"


def test_golden_controls_reported_unresolved_not_fake_ids():
    policy = {"config": {"PROVIDER_MODE": "mock"},
              "golden_controls": {"status": "unresolved",
                                  "domains": {"cpni_handling": {"status": "unresolved"}}}}
    ent = assess_enterprise_readiness(policy)
    assert any("unresolved dependency record" in m for m in ent["missing"])
    assert "GC-TBD" not in str(policy["golden_controls"])   # no fake control ids


def test_http_inline_secret_header_is_flagged():
    policy = {"config": {"PROVIDER_MODE": "http", "HTTP_TARGET_URL": "http://target",
                         "HTTP_HEADERS": ["Authorization=Bearer sk-abcdefghij1234567890"]}}
    ent = assess_enterprise_readiness(policy)
    assert any("inline secret" in m for m in ent["missing"])
