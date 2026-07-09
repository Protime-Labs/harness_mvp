"""M4 — minimal SQLite control-plane state (stdlib sqlite3; local-first, no server, no ORM).

Persists the run lifecycle so evaluations are first-class RECORDS, not just live dicts: assets and
their content-hashed versions, use cases, evaluation runs, gate decisions, an append-only audit
trail, and an in-process event outbox. Seven schema-versioned tables to start — grow per feature,
do not big-bang the full catalogue.

Design notes:
- Deterministic IDs (content hashes / row counts), so the same input yields the same key and
  re-registering identical content creates NO duplicate version (idempotent registration).
- Plain parameterized SQL (injection-safe); each write is a transaction. This is a persistence
  SEAM the harness core never imports — the control plane wraps AROUND the pure evaluation core.
"""
from __future__ import annotations

import json
import sqlite3
from typing import Any, Dict, List, Optional

from ..domain.contracts import now_iso, sha256_hex

SCHEMA_VERSION = "harness/db/v1"
DEFAULT_DB = "harness_state.db"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS schema_meta (version TEXT PRIMARY KEY, created_at TEXT);
CREATE TABLE IF NOT EXISTS assets (
  asset_key TEXT PRIMARY KEY, name TEXT, type TEXT, owner TEXT, created_at TEXT);
CREATE TABLE IF NOT EXISTS asset_versions (
  asset_version_id TEXT PRIMARY KEY, asset_key TEXT, version_no INTEGER,
  content_hash TEXT, content_json TEXT, created_at TEXT,
  UNIQUE(asset_key, content_hash));
CREATE TABLE IF NOT EXISTS use_cases (
  use_case_id TEXT PRIMARY KEY, name TEXT, content_json TEXT, created_at TEXT);
CREATE TABLE IF NOT EXISTS evaluation_runs (
  run_id TEXT PRIMARY KEY, asset_version_id TEXT, use_case_id TEXT, status TEXT,
  gate_decision TEXT, bundle_dir TEXT, created_at TEXT, updated_at TEXT);
CREATE TABLE IF NOT EXISTS gate_decisions (
  gate_id TEXT PRIMARY KEY, run_id TEXT, decision TEXT, matched_rule TEXT,
  rationale TEXT, policy_version TEXT, created_at TEXT);
CREATE TABLE IF NOT EXISTS audit_events (
  event_id TEXT PRIMARY KEY, run_id TEXT, kind TEXT, detail TEXT, ts TEXT);
CREATE TABLE IF NOT EXISTS event_outbox (
  event_id TEXT PRIMARY KEY, event_type TEXT, resource_id TEXT, payload_json TEXT,
  status TEXT, created_at TEXT);
"""


def _sid(prefix: str, *parts: str) -> str:
    """Deterministic id: prefix + first 12 hex of sha256(parts)."""
    return prefix + sha256_hex("|".join(parts)).split(":", 1)[1][:12]


def connect(db_path: str = DEFAULT_DB) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(db_path: str = DEFAULT_DB) -> str:
    conn = connect(db_path)
    with conn:
        conn.executescript(_SCHEMA)
        conn.execute("INSERT OR IGNORE INTO schema_meta(version, created_at) VALUES (?, ?)",
                     (SCHEMA_VERSION, now_iso()))
    conn.close()
    return db_path


def register_asset(conn: sqlite3.Connection, asset: dict, owner: str = "unknown") -> Dict[str, Any]:
    """Register an asset + a content-hashed version. Idempotent: identical content -> same version
    (no duplicate); changed content -> a new version under the same asset key."""
    name = asset.get("name") or asset.get("asset_id") or "asset"
    atype = asset.get("type", "unknown")
    asset_key = _sid("AST-", name, atype)
    content_hash = sha256_hex(asset)
    with conn:
        conn.execute("INSERT OR IGNORE INTO assets(asset_key,name,type,owner,created_at) VALUES(?,?,?,?,?)",
                     (asset_key, name, atype, owner, now_iso()))
        existing = conn.execute(
            "SELECT asset_version_id FROM asset_versions WHERE asset_key=? AND content_hash=?",
            (asset_key, content_hash)).fetchone()
        if existing:
            return {"asset_key": asset_key, "asset_version_id": existing["asset_version_id"],
                    "content_hash": content_hash, "new_version": False}
        version_no = conn.execute("SELECT COUNT(*) c FROM asset_versions WHERE asset_key=?",
                                  (asset_key,)).fetchone()["c"] + 1
        avid = f"{asset_key}-v{version_no}"
        conn.execute(
            "INSERT INTO asset_versions(asset_version_id,asset_key,version_no,content_hash,content_json,created_at)"
            " VALUES(?,?,?,?,?,?)",
            (avid, asset_key, version_no, content_hash, json.dumps(asset, sort_keys=True), now_iso()))
        _audit(conn, "", "asset.version_created", f"{avid} ({content_hash[:19]})")
    return {"asset_key": asset_key, "asset_version_id": avid, "content_hash": content_hash, "new_version": True}


def create_use_case(conn: sqlite3.Connection, uc: dict) -> Dict[str, Any]:
    ucid = _sid("UC-", json.dumps(uc, sort_keys=True))
    with conn:
        conn.execute("INSERT OR IGNORE INTO use_cases(use_case_id,name,content_json,created_at) VALUES(?,?,?,?)",
                     (ucid, uc.get("name", "usecase"), json.dumps(uc, sort_keys=True), now_iso()))
    return {"use_case_id": ucid}


def get_asset_version(conn: sqlite3.Connection, asset_version_id: str) -> Optional[dict]:
    row = conn.execute("SELECT content_json FROM asset_versions WHERE asset_version_id=?",
                       (asset_version_id,)).fetchone()
    return json.loads(row["content_json"]) if row else None


def get_use_case(conn: sqlite3.Connection, use_case_id: str) -> Optional[dict]:
    row = conn.execute("SELECT content_json FROM use_cases WHERE use_case_id=?", (use_case_id,)).fetchone()
    return json.loads(row["content_json"]) if row else None


def create_run(conn: sqlite3.Connection, asset_version_id: str, use_case_id: str) -> str:
    n = conn.execute("SELECT COUNT(*) c FROM evaluation_runs").fetchone()["c"]
    run_id = f"RUN-{n + 1:04d}"
    ts = now_iso()
    with conn:
        conn.execute(
            "INSERT INTO evaluation_runs(run_id,asset_version_id,use_case_id,status,created_at,updated_at)"
            " VALUES(?,?,?,?,?,?)", (run_id, asset_version_id, use_case_id, "pending", ts, ts))
        _audit(conn, run_id, "run.created", f"{asset_version_id} / {use_case_id}")
    return run_id


def complete_run(conn: sqlite3.Connection, run_id: str, gate: dict, bundle_dir: str = "") -> None:
    ts = now_iso()
    with conn:
        conn.execute(
            "INSERT OR REPLACE INTO gate_decisions"
            "(gate_id,run_id,decision,matched_rule,rationale,policy_version,created_at) VALUES(?,?,?,?,?,?,?)",
            (f"{run_id}-GATE", run_id, gate.get("decision"), gate.get("matched_rule"),
             gate.get("rationale"), gate.get("policy_version"), ts))
        conn.execute("UPDATE evaluation_runs SET status=?, gate_decision=?, bundle_dir=?, updated_at=? WHERE run_id=?",
                     ("completed", gate.get("decision"), bundle_dir, ts, run_id))
        _audit(conn, run_id, "run.completed", f"gate={gate.get('decision')} rule={gate.get('matched_rule')}")
        _outbox(conn, "evaluation.completed", run_id,
                {"run_id": run_id, "decision": gate.get("decision"), "bundle_dir": bundle_dir})


def get_run(conn: sqlite3.Connection, run_id: str) -> Optional[Dict[str, Any]]:
    row = conn.execute("SELECT * FROM evaluation_runs WHERE run_id=?", (run_id,)).fetchone()
    if not row:
        return None
    gate = conn.execute("SELECT * FROM gate_decisions WHERE run_id=?", (run_id,)).fetchone()
    events = conn.execute("SELECT kind,detail,ts FROM audit_events WHERE run_id=? ORDER BY ts", (run_id,)).fetchall()
    return {"run": dict(row), "gate": dict(gate) if gate else None,
            "audit": [dict(e) for e in events]}


def list_runs(conn: sqlite3.Connection) -> List[Dict[str, Any]]:
    rows = conn.execute("SELECT run_id,asset_version_id,use_case_id,status,gate_decision,created_at"
                        " FROM evaluation_runs ORDER BY created_at").fetchall()
    return [dict(r) for r in rows]


def _audit(conn: sqlite3.Connection, run_id: str, kind: str, detail: str) -> None:
    conn.execute("INSERT INTO audit_events(event_id,run_id,kind,detail,ts) VALUES(?,?,?,?,?)",
                 (_sid("EVT-", run_id, kind, detail, now_iso()), run_id, kind, detail, now_iso()))


def _outbox(conn: sqlite3.Connection, event_type: str, resource_id: str, payload: dict) -> None:
    conn.execute(
        "INSERT INTO event_outbox(event_id,event_type,resource_id,payload_json,status,created_at) VALUES(?,?,?,?,?,?)",
        (_sid("OBX-", event_type, resource_id, now_iso()), event_type, resource_id,
         json.dumps(payload, sort_keys=True), "pending", now_iso()))
