"""M4 — SQLite control-plane: idempotent asset versioning + persisted run lifecycle."""
from harness.storage import repository as repo


def test_asset_versioning_is_idempotent(tmp_path):
    db = repo.init_db(str(tmp_path / "state.db"))
    conn = repo.connect(db)
    a1 = repo.register_asset(conn, {"name": "agent-x", "type": "agent", "cfg": 1}, owner="demo")
    a2 = repo.register_asset(conn, {"name": "agent-x", "type": "agent", "cfg": 1}, owner="demo")  # identical
    a3 = repo.register_asset(conn, {"name": "agent-x", "type": "agent", "cfg": 2}, owner="demo")  # changed
    assert a2["new_version"] is False and a1["asset_version_id"] == a2["asset_version_id"]
    assert a3["asset_key"] == a1["asset_key"] and a3["asset_version_id"] != a1["asset_version_id"]
    assert a3["new_version"] is True
    conn.close()


def test_run_lifecycle_persists_gate_audit_outbox(tmp_path):
    db = repo.init_db(str(tmp_path / "state.db"))
    conn = repo.connect(db)
    av = repo.register_asset(conn, {"name": "agent-y", "type": "agent"}, owner="demo")
    uc = repo.create_use_case(conn, {"name": "uc", "data_classes": ["PII"]})
    run_id = repo.create_run(conn, av["asset_version_id"], uc["use_case_id"])
    repo.complete_run(conn, run_id,
                      {"decision": "block", "matched_rule": "4.detector_blocking_finding",
                       "rationale": "r", "policy_version": "gate/v1"}, bundle_dir="runs/RUN-x")
    got = repo.get_run(conn, run_id)
    assert got["run"]["status"] == "completed" and got["run"]["gate_decision"] == "block"
    assert got["gate"]["decision"] == "block" and got["gate"]["matched_rule"] == "4.detector_blocking_finding"
    assert any(e["kind"] == "run.completed" for e in got["audit"])
    assert conn.execute("SELECT COUNT(*) c FROM event_outbox WHERE status='pending'").fetchone()["c"] == 1
    assert [r["run_id"] for r in repo.list_runs(conn)] == [run_id]
    conn.close()


def test_init_db_records_schema_version(tmp_path):
    db = repo.init_db(str(tmp_path / "state.db"))
    conn = repo.connect(db)
    v = conn.execute("SELECT version FROM schema_meta").fetchone()["version"]
    assert v == repo.SCHEMA_VERSION
    conn.close()


def test_full_evaluate_flow_persists_completed_run(tmp_path):
    """The DoD flow end-to-end: register -> create -> run -> evaluate -> persist gate + bundle."""
    from harness.application.bundle import write_run_bundle
    from harness.application.orchestrator import run_assurance
    from harness.interface import factory

    asset = {"asset_id": "AGT-001", "type": "agent", "name": "att-customer-support-agent"}
    uc = {"name": "att-customer-support", "data_classes": ["CPNI", "PII"], "exposure": "public",
          "write_tools": True, "users": ["external"], "criticality": "tier1"}

    conn = repo.connect(repo.init_db(str(tmp_path / "state.db")))
    av = repo.register_asset(conn, asset, owner="demo")
    ucr = repo.create_use_case(conn, uc)
    run_id = repo.create_run(conn, av["asset_version_id"], ucr["use_case_id"])

    ctx = factory.build_context()
    bundle = run_assurance(
        use_case=repo.get_use_case(conn, ucr["use_case_id"]),
        asset=repo.get_asset_version(conn, av["asset_version_id"]),
        policy=ctx["policy"], driver=ctx["driver"], adapter=ctx["adapter"], store=ctx["store"],
        detectors=ctx["detectors"], specs=ctx["specs"], registry_map=ctx["registry_map"],
        system_prompt=ctx["system_prompt"])
    bdir = str(tmp_path / "RUN")
    write_run_bundle(bundle, ctx["store"], ctx["policy"], ctx["specs"], bdir)
    repo.complete_run(conn, run_id, bundle["gate"], bundle_dir=bdir)

    got = repo.get_run(conn, run_id)
    assert got["run"]["status"] == "completed"
    assert got["run"]["gate_decision"] == "block" and got["run"]["bundle_dir"] == bdir
    assert got["gate"]["matched_rule"] == "4.detector_blocking_finding"
    conn.close()
