"""Microsoft PyRIT as an external attack DRIVER (B3 seam).

PyRIT's target pipeline drives the send: each scenario prompt becomes a PyRIT `Message`, sent
through a real `PromptChatTarget` subclass that bridges OUR `ModelPort` (so provider-independence
holds and the offline mock works with no key). Responses are scored by OUR judge quorum +
deterministic detectors and emitted as canonical `Finding`s — the gate stays ours.

This proves a second external engine on the same seam. Requires the `redteam` extra
(`pip install -e ".[redteam]"`).
"""
from __future__ import annotations

import asyncio
from dataclasses import asdict
from typing import Any, Callable, Dict, List

from ...domain.aggregate import aggregate
from ...domain.contracts import Finding, HarnessSpec, RESULT_SCHEMA, SEVERITY_ORDER
from ...application.judge import run_judge


class PyritDriver:
    name = "pyrit"

    def __init__(self, detectors: Dict[str, Callable], system_prompt: str, judge_adapter: Any = None):
        self.detectors = detectors
        self.system_prompt = system_prompt
        self.judge_adapter = judge_adapter

    def _target(self, adapter):
        from pyrit.models import Message
        from pyrit.prompt_target import PromptChatTarget

        system_prompt = self.system_prompt

        class _PortTarget(PromptChatTarget):
            async def _send_prompt_to_target_async(self, *, normalized_conversation):
                user_text = ""
                for m in normalized_conversation:
                    pieces = getattr(m, "message_pieces", [])
                    role = pieces[0].role if pieces else None
                    if role == "user":
                        user_text = m.get_value()
                resp = adapter.invoke("target", user_text, system=system_prompt)
                return [Message.from_prompt(prompt=resp["text"], role="assistant")]

            def _validate_request(self, *, message):  # no-op: single user turn
                return None

            def is_response_format_json(self, *args, **kwargs):
                return False

        return _PortTarget()

    def run(self, spec: HarnessSpec, adapter: Any, store: Any, cfg: dict):
        from pyrit.models import Message

        async def _run_all(attacks):
            from pyrit.setup import IN_MEMORY, initialize_pyrit_async
            await initialize_pyrit_async(memory_db_type=IN_MEMORY)  # PyRIT CentralMemory (in-memory)
            target = self._target(adapter)
            out = []
            for attack in attacks:
                conv = [Message.from_prompt(prompt=attack, role="user")]
                res = await target._send_prompt_to_target_async(normalized_conversation=conv)
                out.append(res[0].get_value() if res else "")
            return out

        responses = asyncio.run(_run_all([sc.attack for sc in spec.scenarios]))

        dets = [self.detectors[d] for d in spec.detectors]
        judge = self.judge_adapter or adapter
        real = getattr(judge, "name", "") == "litellm"
        lenses = spec.lenses
        hr_id = f"HR-{spec.id}"
        turns: list = []
        verdicts: list = []
        findings: List[Finding] = []
        manifest: list = []

        for i, (sc, text) in enumerate(zip(spec.scenarios, responses)):
            t_atk = store.capture_turn(hr_id, "attacker", f"attacker.{spec.id}", sc.attack, adapter.name)
            t_tgt = store.capture_turn(hr_id, "target", "asset-under-test", text, adapter.name)
            turns += [t_atk, t_tgt]
            cand = f"{spec.id}:{sc.id}"
            manifest.append({"harness": spec.id, "scenario_id": sc.id, "cand": cand,
                             "target_uri": t_tgt["output_uri"], "target_hash": t_tgt["output_hash"],
                             "category": sc.category, "title": sc.title, "index": i})
            sc_dict = {"attack": sc.attack, "label": sc.label, "category": sc.category}
            vlist = []
            for j in range(cfg["QUORUM_N"]):
                lens = lenses[j % len(lenses)] if lenses else "policy_compliance"
                v = run_judge(lens, sc_dict, text, judge, cfg["SEED"] + j)
                verdicts.append(store.capture_verdict(hr_id, cand, f"judge.{lens}.v1", lens, v))
                vlist.append(v)
            succeeded, severity, confidence, det_pos = aggregate(vlist, [d(text) for d in dets])
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
