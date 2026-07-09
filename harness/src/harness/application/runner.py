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

    def __init__(self, detectors: Dict[str, Callable], system_prompt: str, judge_adapter: Any = None,
                 judge_adapters: Any = None):
        self.detectors = detectors
        self.system_prompt = system_prompt
        # Judge independence (A4/BF-20): a SEPARATE model judges. None => reuse target (mock path).
        # A panel (judge_adapters) enables a DIVERSE-model quorum (B7): one model per quorum index.
        self.judge_panel = list(judge_adapters) if judge_adapters else [judge_adapter]

    def run(self, spec: HarnessSpec, adapter: Any, store: Any, cfg: dict) -> Tuple[dict, list, list, list, List[Finding]]:
        lenses = spec.lenses
        dets = [self.detectors[d] for d in spec.detectors]
        panel = self.judge_panel                        # diverse judge quorum (one model per index)
        real = any(getattr(j, "name", "") == "litellm" for j in panel if j is not None)
        hr_id = f"HR-{spec.id}"
        turns: list = []
        verdicts: list = []
        findings: List[Finding] = []
        manifest: list = []
        turn_no = 0
        tokens = 0
        cost_usd = 0.0
        cost_known = True   # flips false if any turn's price can't be determined (real-provider path)
        t0 = time.time()
        b = cfg["BUDGET"]
        status = "completed"
        incomplete = False
        budget_reason = None

        def _cost_capacity_exhausted() -> bool:
            max_cost = float(b.get("max_cost_usd", float("inf")))
            if max_cost <= 0:
                return cost_usd > 0
            return cost_usd >= max_cost

        def _cost_breached() -> bool:
            return cost_usd > float(b.get("max_cost_usd", float("inf")))

        def _budget_reason(require_next_capacity: bool = True):
            if turn_no >= b["max_turns"]:
                return "max_turns"
            if tokens >= b["max_tokens"]:
                return "max_tokens"
            if _cost_breached() or (require_next_capacity and _cost_capacity_exhausted()):
                return "max_cost_usd"
            if (time.time() - t0) > b["max_wall_clock_s"]:
                return "max_wall_clock_s"
            return None

        for i, sc in enumerate(spec.scenarios):
            budget_reason = _budget_reason()
            if budget_reason:
                status, incomplete = "budget_exceeded", True
                break
            resp = adapter.invoke("target", _build_attack(sc)["prompt"], system=self.system_prompt)
            turn_no += 1
            tokens += resp["tokens"]["in"] + resp["tokens"]["out"]
            turn_cost = resp.get("cost_usd", 0.0)
            if turn_cost is None:
                cost_known = False          # price unavailable -> budget can't be verified (gate reviews)
            else:
                cost_usd += turn_cost
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
                judge = panel[j % len(panel)] or adapter   # rotate judge model across the quorum
                v = run_judge(lens, sc_dict, resp["text"], judge, cfg["SEED"] + j)
                jname = getattr(judge, "model", None) or getattr(judge, "name", "judge")
                verdicts.append(store.capture_verdict(hr_id, cand, f"judge.{lens}.{jname}", lens, v))
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
            budget_reason = _budget_reason(require_next_capacity=i < len(spec.scenarios) - 1)
            if budget_reason and (i < len(spec.scenarios) - 1 or _cost_breached()):
                status, incomplete = "budget_exceeded", True
                break

        total = len(spec.scenarios)
        metrics = {"scenarios": total, "findings": len(findings),
                   "success_rate": round(len(findings) / max(total, 1), 2),
                   "tokens": tokens, "cost_usd": round(cost_usd, 4), "cost_known": cost_known,
                   "latency_s": round(time.time() - t0, 3),
                   "budget_reason": budget_reason if incomplete else None,
                   "judges": [getattr(j, "model", None) or getattr(j, "name", "sim") for j in panel]}
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
                "budget": {**cfg["BUDGET"], "status": "exceeded" if incomplete else "within",
                           "reason": budget_reason if incomplete else None},
            },
        }
        return result, turns, verdicts, manifest, findings
