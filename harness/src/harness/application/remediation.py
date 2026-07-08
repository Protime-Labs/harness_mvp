"""W9 — remediation (advisory, deterministic). Turn confirmed findings into prioritized,
category-keyed remediation guidance. This is DATA-PLANE advice; it never changes the gate.

A production build routes these to the guardrail/policy owners and re-tests (the resilience
harnesses) after a fix.
"""
from __future__ import annotations

from typing import Dict, List

from ..domain.contracts import Finding, sev_rank

_PLAYBOOK = {
    "prompt_injection": "Add an instruction-hierarchy guard + tool-call allowlist; re-test H2.1.",
    "sensitive_disclosure": "Strip internal notes from context; add a system-prompt-leak guard; re-test H2.1.",
    "data_leakage": "Enforce a PII/CPNI egress filter (Presidio) on responses; re-test H2.3.",
    "safety": "Attach a safety classifier (Llama Guard / NeMo) pre-response; re-test H1.3.",
    "adversarial": "Add jailbreak-resistant system framing + refusal reinforcement; re-test H1.2.",
}


def remediate(findings: List[Finding]) -> List[dict]:
    out = []
    for f in sorted(findings, key=lambda x: -sev_rank(x.severity)):
        key = f.category.split(".")[0]
        out.append({
            "finding_id": f.id, "severity": f.severity, "category": f.category, "harness": f.harness,
            "priority": "P1" if f.severity in ("critical", "high") else "P2",
            "action": _PLAYBOOK.get(key, "Review with the control owner; add a targeted guardrail; re-test."),
            "standards": f.standards, "evidence_uri": f.evidence_uri,
        })
    return out
