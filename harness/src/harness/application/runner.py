"""B3 / W3 — the built-in harness runner (the run contract). A HarnessDriver implementation.

One engine runs any attack harness from its spec: for each scenario it invokes the target
through the ModelPort, captures both turns as evidence, runs the judge quorum (W7), floors the
verdicts with deterministic detectors (C3), and emits canonical Findings + a result.json-shaped
dict. Honors the budget and FAILS CLOSED on breach (A8/C6).

Depends only on domain + ports + the injected detector/judge callables. The agentic overlay or
PyRIT would be a DIFFERENT driver producing the same output (see adapters/drivers).

Faithful to notebook §8 `run_harness`.
"""
from __future__ import annotations

import time
from dataclasses import asdict
from typing import Any, Callable, Dict, List, Tuple

from ..domain.contracts import (Finding, HarnessSpec, RESULT_SCHEMA, SEVERITY_ORDER)
from ..domain.aggregate import aggregate
from .judge import run_judge


def _build_attack(scenario) -> Dict[str, str]:
    # real impl: PyRIT/Garak/Promptfoo produce this; the mock just echoes the scripted attack
    return {"prompt": scenario.attack}


class BuiltinDriver:
    """The default scenario driver. `detectors` is the {name: callable} registry (injected)."""

    name = "builtin"

    def __init__(self, detectors: Dict[str, Callable], system_prompt: str, judge_adapter: Any = None):
        self.detectors = detectors
        self.system_prompt = system_prompt
        # Judge independence (A4/BF-20): a SEPARATE model judges. None => reuse target (mock path).
        self.judge_adapter = judge_adapter

    def run(self, spec: HarnessSpec, adapter: Any, store: Any, cfg: dict) -> Tuple[dict, list, list, list, List[Finding]]:
        lenses = spec.lenses
        dets = [self.detectors[d] for d in spec.detectors]
        judge = self.judge_adapter or adapter          # judge independence seam (A4/BF-20)
        real = getattr(judge, "name", "") == "litellm"  # 'real' = the JUDGE is a live model
        hr_id = f"HR-{spec.id}"
        turns: list = []
        verdicts: list = []
        findings: List[Finding] = []
        manifest: list = []
        turn_no = 0
        tokens = 0
        t0 = time.time()
        b = cfg["BUDGET"]
        status = "completed"
        incomplete = False

        for i, sc in enumerate(spec.scenarios):
            if turn_no >= b["max_turns"] or tokens >= b["max_tokens"] or (time.time() - t0) > b["max_wall_clock_s"]:
                status, incomplete = "budget_exceeded", True
                break
            resp = adapter.invoke("target", _build_attack(sc)["prompt"], system=self.system_prompt)
            turn_no += 1
            tokens += resp["tokens"]["in"] + resp["tokens"]["out"]
            t_atk = store.capture_turn(hr_id, "attacker", f"attacker.{spec.id}", sc.attack, adapter.name)
            t_tgt = store.capture_turn(hr_id, "target", "asset-under-test", resp["text"], adapter.name,
                                       model=resp["model"], tokens=resp["tokens"])
            turns += [t_atk, t_tgt]
            cand = f"{spec.id}:{sc.id}"
            manifest.append({"harness": spec.id, "scenario_id": sc.id, "cand": cand,
                             "target_uri": t_tgt["output_uri"], "target_hash": t_tgt["output_hash"],
                             "category": sc.category, "title": sc.title, "index": i})
            sc_dict = {"attack": sc.attack, "label": sc.label, "category": sc.category}
            vlist = []
            for j in range(cfg["QUORUM_N"]):
                lens = lenses[j % len(lenses)] if lenses else "policy_compliance"
                v = run_judge(lens, sc_dict, resp["text"], judge, cfg["SEED"] + j)
                verdicts.append(store.capture_verdict(hr_id, cand, f"judge.{lens}.v1", lens, v))
                vlist.append(v)
            succeeded, severity, confidence, det_pos = aggregate(vlist, [d(resp["text"]) for d in dets])
            basis = "detector(real-content)" if det_pos else ("llm-judge(real)" if real else "simulated-judge(offline)")
            if succeeded:
                findings.append(Finding(
                    id=f"F-{spec.id}-{i+1}", source="harness", severity=severity, category=sc.category,
                    title=sc.title, description=f"{spec.name}: {sc.title}",
                    blocking=SEVERITY_ORDER[severity] >= SEVERITY_ORDER[cfg["FAIL_ON_SEVERITY"]],
                    policy_rule=f"POL-{spec.id}", evidence_uri=t_tgt["output_uri"],
                    recommendation="Add guardrail; re-test.", harness=spec.id,
                    standards=spec.standards, basis=basis))

        total = len(spec.scenarios)
        metrics = {"scenarios": total, "findings": len(findings),
                   "success_rate": round(len(findings) / max(total, 1), 2)}
        ev_basis = ("real (LLM judge reads responses + real-content detectors)" if real
                    else "simulated (offline: content detectors are REAL; semantic verdicts simulated from labels)")
        result = {
            "$schema": RESULT_SCHEMA, "harness": spec.id, "harness_run_id": hr_id, "status": status,
            "score": round(1 - len(findings) / max(total, 1), 2),
            "decision": "block" if any(f.severity == "critical" for f in findings)
                        else ("warn" if findings else "approve"),
            "metrics": metrics, "findings": [asdict(f) for f in findings], "incomplete": incomplete,
            "evidence_basis": ev_basis, "driver": self.name,
            "determinism": {
                "seed": cfg["SEED"],
                "quorum": {"min_judges": cfg["QUORUM_N"], "rule": cfg["QUORUM_RULE"]},
                "determinism_class": ("bounded" if real else "deterministic"),
                "budget": {**cfg["BUDGET"], "status": "exceeded" if incomplete else "within"},
            },
        }
        return result, turns, verdicts, manifest, findings
