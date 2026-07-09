"""Mode-A replay (C4, R6/A3). Reconstruct ALL findings + the aggregate gate from evidence
alone — no model calls. Every stored target response is re-read and re-hashed (chain-of-custody
check), re-run through the SAME detectors + stored verdicts, re-aggregated, and re-gated.

If the replayed findings and gate match the live run, the evaluation is provably reproducible.

Faithful to notebook §16.
"""
from __future__ import annotations

from typing import Dict, List, Tuple

from ..domain.aggregate import aggregate
from ..domain.contracts import sha256_hex
from ..domain.gate import gate_decision


def replay_mode_a(manifest: List[dict], verdicts: List[dict], store, detectors: Dict[str, callable],
                  harness_detectors: Dict[str, List[str]], evaluator_status: dict | None = None):
    """`harness_detectors` maps harness id -> list of detector names (from the specs)."""
    by_cand: Dict[str, list] = {}
    for v in verdicts:
        by_cand.setdefault(v["finding_candidate_id"], []).append(v)

    findings: List[Tuple[str, str, str]] = []
    for m in manifest:
        resp = store.read(m["target_uri"])
        assert sha256_hex(resp) == m["target_hash"], "chain-of-custody mismatch"
        dets = [detectors[d] for d in harness_detectors[m["harness"]]]
        succ, sev, conf, det = aggregate(by_cand.get(m["cand"], []), [d(resp) for d in dets])
        if succ:
            findings.append((f"F-{m['harness']}-{m['index']+1}", sev, m["category"]))

    # rebuild the gate over the replayed findings (control plane, no LLM)
    fake_findings = [type("F", (), {"severity": s})() for _, s, _ in findings]
    gate = gate_decision("allow", [{"status": "completed"}], fake_findings, True,
                         evaluator_status=evaluator_status)
    return sorted(findings), gate
