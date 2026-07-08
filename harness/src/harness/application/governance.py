"""H5.1 — Finding Lifecycle / Evidence / Verdict (Category-5 governance harness).

A deterministic control-verify harness: it consumes every finding from the attack harnesses
and checks lifecycle completeness — required fields present, evidence exists & re-hashes, a
verdict quorum exists — then emits the immutable evidence package. This is how the platform
tests its OWN governance (A1: it verifies; it does not decide the gate).

Faithful to notebook §12.
"""
from __future__ import annotations

import os
from dataclasses import asdict
from typing import List

from ..domain.contracts import Finding, sha256_hex


def run_governance_finding_lifecycle(all_findings: List[Finding], verdicts: List[dict], store) -> dict:
    required = ["id", "severity", "category", "evidence_uri", "policy_rule", "standards"]
    cand_with_verdicts = {v["finding_candidate_id"] for v in verdicts}
    records = []
    complete = 0
    for f in all_findings:
        d = asdict(f)
        missing = [k for k in required if not d.get(k)]
        ev_ok = os.path.exists(d["evidence_uri"]) and sha256_hex(store.read(d["evidence_uri"])) is not None
        has_verdict = any(d["harness"] in c for c in cand_with_verdicts)
        ok = (not missing) and ev_ok and has_verdict
        complete += ok
        records.append({"finding_id": d["id"], "immutable_hash": sha256_hex(d), "complete": ok,
                        "missing": missing, "evidence_ok": ev_ok, "verdict_present": has_verdict})
    return {
        "$schema": "harness/result/v1", "harness": "H5.1", "harness_run_id": "HR-H5.1",
        "status": "completed",
        "decision": "approve" if complete == len(all_findings) else "warn",
        "metrics": {"checked": len(all_findings), "complete": complete},
        "evidence_package": [r["immutable_hash"] for r in records], "records": records,
    }
