"""Inspect AI as an external harness DRIVER (B3 seam). Proves the run contract with a
different engine underneath.

Inspect owns the dataset + generation loop (each scenario becomes an Inspect `Sample`, run via
the `generate()` solver). Model calls are routed through OUR `ModelPort` via a custom Inspect
`ModelAPI` bridge — so provider-independence (R2) holds and the offline mock works with no key.
The platform's assurance apparatus stays authoritative: we capture evidence, run OUR judge
quorum + deterministic detectors, aggregate, and emit the canonical `Finding` + result contract.

Result: swapping `--driver inspect` for the built-in driver yields the SAME gate decision from
the same evidence — the whole point of the B3 seam. Requires the `eval` extra:
`pip install -e ".[eval]"`.
"""
from __future__ import annotations

import os
from dataclasses import asdict
from typing import Any, Callable, Dict, List

from ...domain.aggregate import aggregate
from ...domain.contracts import Finding, HarnessSpec, RESULT_SCHEMA, SEVERITY_ORDER
from ...application.judge import run_judge


def _bridge_model(adapter):
    """Wrap our ModelPort as an Inspect Model so Inspect's generate() calls flow through it."""
    from inspect_ai.model import GenerateConfig, Model, ModelAPI, ModelOutput
    from inspect_ai._util.registry import RegistryInfo, set_registry_info

    provider = getattr(adapter, "name", "port")

    class _PortModelAPI(ModelAPI):
        def __init__(self):
            super().__init__(model_name=f"harness-{provider}")
            self._adapter = adapter

        async def generate(self, input, tools, tool_choice, config):
            system, prompt = "", ""
            for m in input:
                role = getattr(m, "role", "")
                text = getattr(m, "text", None)
                if text is None:
                    text = str(getattr(m, "content", ""))
                if role == "system":
                    system = text
                elif role == "user":
                    prompt = text
            resp = self._adapter.invoke("target", prompt, system=system)
            return ModelOutput.from_content(model=self.model_name, content=resp["text"])

    api = _PortModelAPI()
    # attach Inspect registry info so eval() can name/resolve this custom provider
    set_registry_info(api, RegistryInfo(type="modelapi", name=f"harness/{provider}", metadata={}))
    return Model(api, GenerateConfig())


class InspectDriver:
    name = "inspect"

    def __init__(self, detectors: Dict[str, Callable], system_prompt: str, judge_adapter: Any = None):
        self.detectors = detectors
        self.system_prompt = system_prompt
        self.judge_adapter = judge_adapter

    def run(self, spec: HarnessSpec, adapter: Any, store: Any, cfg: dict):
        from inspect_ai import Task, eval as inspect_eval
        from inspect_ai.dataset import Sample
        from inspect_ai.solver import generate, system_message

        dets = [self.detectors[d] for d in spec.detectors]
        judge = self.judge_adapter or adapter
        real = getattr(judge, "name", "") == "litellm"
        hr_id = f"HR-{spec.id}"

        samples = [Sample(input=sc.attack, id=sc.id,
                          metadata={"category": sc.category, "title": sc.title,
                                    "label": sc.label, "index": i})
                   for i, sc in enumerate(spec.scenarios)]
        task = Task(dataset=samples, solver=[system_message(self.system_prompt), generate()])
        model = _bridge_model(adapter)
        log_dir = os.path.join(store.root, "inspect_logs")

        logs = inspect_eval(task, model=model, display="none", log_dir=log_dir, score=False)
        log = logs[0]

        turns: list = []
        verdicts: list = []
        findings: List[Finding] = []
        manifest: list = []

        recs = sorted(log.samples or [], key=lambda s: (s.metadata or {}).get("index", 0))
        for s in recs:
            meta = s.metadata or {}
            i = meta.get("index", 0)
            text = s.output.completion if s.output else ""
            t_atk = store.capture_turn(hr_id, "attacker", f"attacker.{spec.id}", str(s.input), adapter.name)
            t_tgt = store.capture_turn(hr_id, "target", "asset-under-test", text, adapter.name)
            turns += [t_atk, t_tgt]
            cand = f"{spec.id}:{s.id}"
            manifest.append({"harness": spec.id, "scenario_id": s.id, "cand": cand,
                             "target_uri": t_tgt["output_uri"], "target_hash": t_tgt["output_hash"],
                             "category": meta.get("category", ""), "title": meta.get("title", ""), "index": i})
            sc_dict = {"attack": str(s.input), "label": meta.get("label"), "category": meta.get("category", "")}
            vlist = []
            for j in range(cfg["QUORUM_N"]):
                lens = spec.lenses[j % len(spec.lenses)] if spec.lenses else "policy_compliance"
                v = run_judge(lens, sc_dict, text, judge, cfg["SEED"] + j)
                verdicts.append(store.capture_verdict(hr_id, cand, f"judge.{lens}.v1", lens, v))
                vlist.append(v)
            succeeded, severity, confidence, det_pos = aggregate(vlist, [d(text) for d in dets])
            basis = "detector(real-content)" if det_pos else ("llm-judge(real)" if real else "simulated-judge(offline)")
            if succeeded:
                findings.append(Finding(
                    id=f"F-{spec.id}-{i+1}", source="harness", severity=severity,
                    category=meta.get("category", ""), title=meta.get("title", ""),
                    description=f"{spec.name}: {meta.get('title', '')}",
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
            "$schema": RESULT_SCHEMA, "harness": spec.id, "harness_run_id": hr_id, "status": "completed",
            "score": round(1 - len(findings) / max(total, 1), 2),
            "decision": "block" if any(f.severity == "critical" for f in findings)
                        else ("warn" if findings else "approve"),
            "metrics": metrics, "findings": [asdict(f) for f in findings], "incomplete": False,
            "evidence_basis": ev_basis, "driver": self.name,
            "determinism": {"seed": cfg["SEED"], "quorum": {"min_judges": cfg["QUORUM_N"], "rule": cfg["QUORUM_RULE"]},
                            "determinism_class": ("bounded" if real else "deterministic"),
                            "budget": {**cfg["BUDGET"], "status": "within"}},
        }
        return result, turns, verdicts, manifest, findings
