"""M3 — persist a replayable run bundle to disk, and validate (replay) it after the process exits.

`run_assurance` returns a LIVE bundle (dicts + evidence files in a temp store). `write_run_bundle`
turns that into a self-contained, portable `runs/RUN-.../` directory:

    runs/RUN-.../
      run_config.json          gate_decision.json     findings.json
      evidence_manifest.json   replay_manifest.json   policy_manifest.json
      scenario_manifest.json   result_bundle.json     evidence/<per-turn input+output>.txt

`validate_run_bundle` reconstructs the findings and the gate from disk ALONE — no live objects, no
model calls — by re-reading each stored response, re-hashing it (chain of custody), re-running the
SAME deterministic detectors + stored verdicts, re-aggregating, and re-gating (reusing the in-memory
`replay_mode_a`). Tampering with any evidence file breaks its hash and fails validation (C4/R6/A3).
"""
from __future__ import annotations

import json
import os
import shutil
from typing import Any, Dict, List

from ..domain.contracts import sha256_hex
from .replay import replay_mode_a


def _write_json(path: str, obj: Any) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, default=str)


def _rel(*parts: str) -> str:
    return "/".join(parts)  # bundle-relative paths are POSIX-style for portability


def write_run_bundle(bundle: dict, store: Any, policy: dict, specs: dict, out_dir: str) -> str:
    """Write the full run bundle to `out_dir` and return it. `specs` supplies per-harness detectors
    + scenario provenance; `policy` supplies the resolved config for the policy manifest."""
    cfg = policy["config"]
    run_id = os.path.basename(os.path.normpath(out_dir)) or "RUN"
    ev_dir = os.path.join(out_dir, "evidence")
    os.makedirs(ev_dir, exist_ok=True)

    # 1 — copy every turn's evidence into the bundle; map old temp uri -> bundle-relative path
    uri_map: Dict[str, str] = {}
    artifacts: List[dict] = []
    for t in bundle.get("_turns", []):
        for uri_key, hash_key, kind in (("output_uri", "output_hash", "response"),
                                        ("input_uri", "input_hash", "input")):
            uri = t.get(uri_key)
            if not uri or not os.path.exists(uri):
                continue
            base = os.path.basename(uri)
            shutil.copyfile(uri, os.path.join(ev_dir, base))
            rel = _rel("evidence", base)
            uri_map[uri] = rel
            artifacts.append({
                "artifact_id": t["turn_id"], "harness_run_id": t["harness_run_id"], "role": t["role"],
                "type": kind if uri_key == "output_uri" else "prompt", "rel_path": rel,
                "sha256": t.get(hash_key), "model": t.get("model"), "tokens": t.get("tokens"),
                "ts": t.get("ts"),
            })

    # 2 — replay manifest: per-candidate target response + its detectors, verdicts, control inputs
    manifest = bundle.get("_manifest", [])
    harness_detectors = {hid: list(specs[hid].detectors) for hid in {m["harness"] for m in manifest}}
    candidates = [{
        "harness": m["harness"], "scenario_id": m["scenario_id"], "cand": m["cand"],
        "index": m["index"], "category": m["category"], "title": m.get("title", ""),
        "target_rel_path": uri_map.get(m["target_uri"], ""), "target_hash": m["target_hash"],
        "detectors": harness_detectors.get(m["harness"], []),
    } for m in manifest]

    replay_manifest = {
        "$schema": "harness/replay-manifest/v1", "run_id": run_id,
        "fail_on_severity": cfg["FAIL_ON_SEVERITY"],
        "quarantine_decision": (bundle.get("quarantine") or {}).get("decision", "allow"),
        "evaluator_status": bundle.get("judge_calibration"),
        "cost_status": bundle.get("_cost_status"),
        "context_status": bundle.get("_context_status"),
        "policy_hash": (bundle.get("gate") or {}).get("policy_hash", ""),
        "use_presidio": bool(cfg.get("USE_PRESIDIO")), "use_detoxify": bool(cfg.get("USE_DETOXIFY")),
        "candidates": candidates, "verdicts": bundle.get("_verdicts", []),
        "expected_gate": bundle.get("gate"),
    }

    # 3 — provenance manifests (tamper-evident policy + scenario corpus)
    evidence_manifest = {"$schema": "harness/evidence-manifest/v1", "run_id": run_id, "artifacts": artifacts}
    policy_manifest = {
        "$schema": "harness/policy-manifest/v1", "run_id": run_id,
        "config_hash": sha256_hex(cfg), "sources": policy.get("sources", []),
        "fail_on_severity": cfg["FAIL_ON_SEVERITY"], "seed": cfg["SEED"], "quorum_n": cfg["QUORUM_N"],
        "use_presidio": bool(cfg.get("USE_PRESIDIO")), "use_detoxify": bool(cfg.get("USE_DETOXIFY")),
    }
    scenario_manifest = {
        "$schema": "harness/scenario-manifest/v1", "run_id": run_id,
        "source": policy.get("scenario_path") or "built-in/config suite",
        "harnesses": {hid: {"scenario_count": len(s.scenarios),
                            "scenario_ids": [sc.id for sc in s.scenarios],
                            "hash": sha256_hex([[sc.id, sc.attack] for sc in s.scenarios])}
                      for hid, s in specs.items()},
    }

    # 4 — write everything (result_bundle.json is the serializable bundle for report/dashboard reuse)
    _write_json(os.path.join(out_dir, "run_config.json"), bundle.get("run_config", {}))
    _write_json(os.path.join(out_dir, "gate_decision.json"), bundle.get("gate", {}))
    _write_json(os.path.join(out_dir, "findings.json"), bundle.get("findings", []))
    _write_json(os.path.join(out_dir, "evidence_manifest.json"), evidence_manifest)
    _write_json(os.path.join(out_dir, "replay_manifest.json"), replay_manifest)
    _write_json(os.path.join(out_dir, "policy_manifest.json"), policy_manifest)
    _write_json(os.path.join(out_dir, "scenario_manifest.json"), scenario_manifest)
    _write_json(os.path.join(out_dir, "result_bundle.json"),
                {k: v for k, v in bundle.items() if not k.startswith("_")})
    return out_dir


class _BundleReader:
    """Minimal EvidencePort.read for replay: opens a persisted evidence file by absolute path."""

    def read(self, uri: str) -> str:
        with open(uri, encoding="utf-8") as f:
            return f.read()


def validate_run_bundle(path: str, current_policy_hash: str | None = None) -> dict:
    """Replay the gate from a persisted bundle (no live objects, no model calls). `path` is the
    bundle directory or its replay_manifest.json. Returns {ok, expected_gate, replayed_gate, ...};
    a tampered evidence file trips the chain-of-custody hash check and yields ok=False.

    F4: pass `current_policy_hash` (the policy in force now) to detect POLICY DRIFT — if it differs
    from the hash the bundle was decided under, the run is no longer reproducible under today's
    policy and `ok` is False."""
    from ..adapters.detectors import build_detectors  # lazy: keep the module-level layer graph clean

    bundle_dir = os.path.dirname(path) if path.endswith(".json") else path
    with open(os.path.join(bundle_dir, "replay_manifest.json"), encoding="utf-8") as f:
        rm = json.load(f)

    detectors = build_detectors(use_presidio=rm.get("use_presidio", False),
                                use_detoxify=rm.get("use_detoxify", False))
    manifest, harness_detectors = [], {}
    for c in rm["candidates"]:
        manifest.append({
            "harness": c["harness"], "cand": c["cand"], "category": c["category"], "index": c["index"],
            "target_uri": os.path.join(bundle_dir, *c["target_rel_path"].split("/")),
            "target_hash": c["target_hash"],
        })
        harness_detectors[c["harness"]] = c["detectors"]

    expected = (rm.get("expected_gate") or {}).get("decision")
    stored_hash = rm.get("policy_hash", "")
    policy_drift = current_policy_hash is not None and current_policy_hash != stored_hash
    tamper = None
    try:
        _findings, gate = replay_mode_a(
            manifest, rm.get("verdicts", []), _BundleReader(), detectors, harness_detectors,
            evaluator_status=rm.get("evaluator_status"), fail_on_severity=rm.get("fail_on_severity", "high"),
            cost_status=rm.get("cost_status"), quarantine=rm.get("quarantine_decision", "allow"),
            context_status=rm.get("context_status"), policy_hash=stored_hash)
        replayed = gate.decision
    except AssertionError as e:
        tamper, replayed = str(e), None

    return {
        "ok": tamper is None and replayed == expected and not policy_drift,
        "run_id": rm.get("run_id"), "candidates": len(rm.get("candidates", [])),
        "expected_gate": expected, "replayed_gate": replayed, "tamper": tamper,
        "policy_hash": stored_hash, "policy_drift": policy_drift,
    }
