"""F4 — gate policy provenance: policy_hash is stable and content-sensitive."""
from harness.adapters.config.loader import load_config


def test_policy_hash_stable_across_identical_loads():
    a = load_config()["policy_hash"]
    b = load_config()["policy_hash"]
    assert a == b and a.startswith("sha256:")


def test_policy_hash_changes_when_a_policy_value_changes():
    base = load_config()["policy_hash"]
    # tightening overrides (F6-safe) that ARE part of the hashed policy set change the hash
    assert load_config(overrides={"FAIL_ON_SEVERITY": "medium"})["policy_hash"] != base
    assert load_config(overrides={"BUDGET": {"max_cost_usd": 1.0}})["policy_hash"] != base


def test_gate_carries_policy_hash():
    from harness.domain.gate import gate_decision
    d = gate_decision("allow", [], [], True, policy_hash="sha256:abc")
    assert d.policy_hash == "sha256:abc"
