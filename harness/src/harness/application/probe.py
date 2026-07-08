"""Interactive single-prompt probe — send one prompt through the chain and emit a live event
per stage, so a console or a dashboard can show status in real time and exactly what was utilized.

The chain for one prompt:
    plan -> target invoke -> evidence capture -> detectors -> judge quorum -> aggregate -> gate

`on_event(stage, payload)` is called as each stage completes (the same callback drives the console
renderer and the served dashboard's SSE stream). Provider-independent: mock offline or a real
model via `--provider litellm`. The gate stays deterministic (A1) — no LLM decides.
"""
from __future__ import annotations

from dataclasses import asdict
from typing import Any, Callable, Dict, List, Optional

from ..domain.aggregate import aggregate
from ..domain.contracts import Finding, SEVERITY_ORDER
from ..domain.gate import gate_decision
from .judge import run_judge

# a broad default battery for an arbitrary prompt (what gets "utilized")
DEFAULT_LENSES = ["goal_integrity", "tool_safety", "data_leakage", "safety", "policy_compliance"]
DEFAULT_DETECTORS = ["secret", "cpni", "tool", "toxicity"]


def run_probe(
    prompt: str,
    *,
    adapter: Any,
    detectors: Dict[str, Callable],
    cfg: dict,
    store: Any,
    system_prompt: str,
    judge_adapter: Any = None,
    lenses: Optional[List[str]] = None,
    detector_names: Optional[List[str]] = None,
    on_event: Callable[[str, dict], None] = lambda s, d: None,
) -> dict:
    lenses = lenses or DEFAULT_LENSES
    detector_names = [d for d in (detector_names or DEFAULT_DETECTORS) if d in detectors]
    judge = judge_adapter or adapter
    real = getattr(judge, "name", "") == "litellm"

    # 1 — plan: announce what WILL be utilized
    on_event("plan", {
        "prompt": prompt,
        "provider": getattr(adapter, "name", "?"),
        "judge": getattr(judge, "name", "?"),
        "judge_independent": judge is not adapter,
        "lenses": lenses, "detectors": detector_names, "quorum_n": cfg["QUORUM_N"],
    })

    # 2 — target invoke
    on_event("target_start", {"model": getattr(adapter, "name", "?")})
    resp = adapter.invoke("target", prompt, system=system_prompt)
    on_event("target", {"response": resp["text"], "model": resp.get("model", {}),
                        "tokens": resp.get("tokens", {})})

    # 3 — evidence capture (chain of custody)
    t = store.capture_turn("HR-PROBE", "target", "asset-under-test", resp["text"],
                           getattr(adapter, "name", "?"), model=resp.get("model"), tokens=resp.get("tokens"))
    on_event("evidence", {"hash": t["output_hash"], "uri": t["output_uri"]})

    # 4 — detectors (deterministic real-content floor)
    hits = []
    for name in detector_names:
        sev, span = detectors[name](resp["text"])
        hits.append((sev, span))
        on_event("detector", {"name": name, "hit": sev is not None, "severity": sev, "span": span})

    # 5 — judge quorum (each verdict streamed as it lands)
    vlist = []
    for j in range(cfg["QUORUM_N"]):
        lens = lenses[j % len(lenses)]
        v = run_judge(lens, {"attack": prompt, "label": None, "category": ""}, resp["text"], judge, cfg["SEED"] + j)
        vlist.append(v)
        on_event("judge", {"index": j + 1, **v})

    # 6 — aggregate (C3: detectors floor the judge)
    succeeded, severity, confidence, det_pos = aggregate(vlist, hits)
    on_event("aggregate", {"succeeded": succeeded, "severity": severity,
                           "confidence": confidence, "detector_positive": det_pos})

    # 7 — deterministic gate over this single candidate (control plane, no LLM)
    findings: List[Finding] = []
    if succeeded:
        findings.append(Finding(
            id="F-PROBE-1", source="probe", severity=severity, category="probe.single_prompt",
            title="Interactive probe finding", description="Single-prompt probe result",
            blocking=SEVERITY_ORDER[severity] >= SEVERITY_ORDER[cfg["FAIL_ON_SEVERITY"]],
            policy_rule="POL-PROBE", evidence_uri=t["output_uri"], recommendation="Review; add guardrail.",
            harness="PROBE", standards={}, basis=("detector(real-content)" if det_pos
                                                  else ("llm-judge(real)" if real else "simulated-judge(offline)"))))
    gate = gate_decision("allow", [{"status": "completed"}], findings, True)
    on_event("gate", {"decision": gate.decision, "matched_rule": gate.matched_rule,
                      "rationale": gate.rationale})

    return {
        "prompt": prompt, "response": resp["text"],
        "provider": getattr(adapter, "name", "?"), "judge": getattr(judge, "name", "?"),
        "evidence_basis": ("real (LLM judge)" if real else "simulated (offline)"),
        "detectors": [{"name": n, "hit": h[0] is not None, "severity": h[0], "span": h[1]}
                      for n, h in zip(detector_names, hits)],
        "verdicts": vlist,
        "aggregate": {"succeeded": succeeded, "severity": severity, "confidence": confidence,
                      "detector_positive": det_pos},
        "gate": asdict(gate),
        "evidence": {"hash": t["output_hash"], "uri": t["output_uri"]},
        "findings": [asdict(f) for f in findings],
    }
