"""F5 — the config loader fails loudly instead of degrading silently."""
import pytest

from harness.adapters.config import loader


def _cfg(tmp_path, files):
    d = tmp_path / "cfg"
    d.mkdir()
    for name, content in files.items():
        (d / name).write_text(content, encoding="utf-8")
    return str(d)


def test_missing_pyyaml_with_config_present_raises_under_strict(monkeypatch, tmp_path):
    cfgdir = _cfg(tmp_path, {"risk_weights.yaml": "weights: {}\n"})
    monkeypatch.setattr(loader, "_HAS_YAML", False)
    with pytest.raises(RuntimeError):
        loader.load_config(config_dir=cfgdir, overrides={"PROVIDER_MODE": "litellm"})


def test_mock_mode_runs_with_zero_deps(monkeypatch, tmp_path):
    cfgdir = _cfg(tmp_path, {"risk_weights.yaml": "weights: {}\n"})
    monkeypatch.setattr(loader, "_HAS_YAML", False)   # PyYAML unavailable
    p = loader.load_config(config_dir=cfgdir, overrides={"PROVIDER_MODE": "mock"})
    assert p["config"]["PROVIDER_MODE"] == "mock" and p["policy_hash"].startswith("sha256:")


def test_unknown_top_level_key_typo_raises(tmp_path):
    if not loader._HAS_YAML:
        pytest.skip("needs pyyaml")
    cfgdir = _cfg(tmp_path, {"risk_weights.yaml": "cuttoffs:\n  high: 60\n  medium: 30\n"})  # typo
    with pytest.raises(ValueError):
        loader.load_config(config_dir=cfgdir)


def test_inverted_cutoffs_raise(tmp_path):
    if not loader._HAS_YAML:
        pytest.skip("needs pyyaml")
    cfgdir = _cfg(tmp_path, {"risk_weights.yaml": "cutoffs:\n  high: 30\n  medium: 60\n"})
    with pytest.raises(ValueError):
        loader.load_config(config_dir=cfgdir)


# ---- F6: overrides may only tighten policy --------------------------------------------------
def test_raising_budget_under_strict_raises():
    with pytest.raises(ValueError):  # litellm -> strict; +cost cap = loosen
        loader.load_config(overrides={"PROVIDER_MODE": "litellm", "BUDGET": {"max_cost_usd": 10.0}})


def test_lowering_budget_succeeds_and_is_recorded():
    p = loader.load_config(overrides={"BUDGET": {"max_cost_usd": 1.0}})  # mock -> not strict; tighten
    assert p["config"]["BUDGET"]["max_cost_usd"] == 1.0
    assert any("BUDGET.max_cost_usd" in s and "tighten" in s for s in p["sources"])


def test_loosening_override_recorded_when_not_strict():
    p = loader.load_config(overrides={"FAIL_ON_SEVERITY": "critical"})  # mock; high->critical = loosen
    assert any("FAIL_ON_SEVERITY" in s and "loosen" in s for s in p["sources"])
