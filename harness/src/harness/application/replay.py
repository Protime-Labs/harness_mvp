"""Mode-A replay (C4, R6/A3). Reconstruct ALL findings + the aggregate gate from evidence
alone — no model calls. Every stored target response is re-read and re-hashed (chain-of-custody
check), re-run through the SAME detectors + stored verdicts, re-aggregated, and re-gated.

If the replayed findings and gate match the live run, the evaluation is provably reproducible.

Faithful to notebook §16.
"""
from __future__ import annotations

from typing import Dict, List, Tuple

from ..domain.aggregate import aggregate
from ..domain.contracts import sev_rank, sha256_hex
from ..domain.gate import gate_decision


def _replay_finding(severity: str, detector_positive: bool, fail_on_severity: str):
    """Reconstruct the finding attributes the gate reads (`severity`, `blocking`, `basis`) so the
    replayed gate sees the SAME inputs the live gate saw — otherwise the honored `blocking` flag
    and the detector/judge distinction would silently differ and replay could diverge (C4)."""
    return type("F", (), {
        "severity": severity,
        "blocking": sev_rank(severity) >= sev_rank(fail_on_severity),
        "basis": "detector(real-content)" if detector_positive else "llm-judge(real)",
    })()


def replay_mode_a(manifest: List[dict], verdicts: List[dict], store, detectors: Dict[str, callable],
                  harness_detectors: Dict[str, List[str]], evaluator_status: dict | None = None,
                  fail_on_severity: str = "high", cost_status: dict | None = None,
                  quarantine: str = "allow"):
    """`harness_detectors` maps harness id -> list of detector names (from the specs)."""
    by_cand: Dict[str, list] = {}
    for v in verdicts:
        by_cand.setdefault(v["finding_candidate_id"], []).append(v)

    findings: List[Tuple[str, str, str]] = []
    fake_findings = []
    for m in manifest:
        resp = store.read(m["target_uri"])
        assert sha256_hex(resp) == m["target_hash"], "chain-of-custody mismatch"
        dets = [detectors[d] for d in harness_detectors[m["harness"]]]
        succ, sev, conf, det = aggregate(by_cand.get(m["cand"], []), [d(resp) for d in dets])
        if succ:
            findings.append((f"F-{m['harness']}-{m['index']+1}", sev, m["category"]))
            fake_findings.append(_replay_finding(sev, det, fail_on_severity))

    # rebuild the gate over the replayed findings (control plane, no LLM). Run-level control inputs
    # (evaluator calibration, cost status) are supplied so the replayed decision matches the live one.
    gate = gate_decision(quarantine, [{"status": "completed"}], fake_findings, True,
                         evaluator_status=evaluator_status, cost_status=cost_status)
    return sorted(findings), gate
