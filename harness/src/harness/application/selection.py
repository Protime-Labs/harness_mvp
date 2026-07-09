"""W2 — selection (R5). Turn the required pack into a run plan + explicit skip rationale.

An unimplemented / unregistered harness is skipped WITH a reason (never silently dropped),
so the report is honest about coverage.

Faithful to notebook §10 `select`.
"""
from __future__ import annotations

from typing import Dict, List, Tuple


def select(required: List[str], registry: Dict[str, dict]) -> Tuple[List[dict], List[dict]]:
    plan, skipped = [], []
    for h in required:
        d = registry.get(h)
        if not d:
            skipped.append({"harness": h, "reason": "not in registry"})
        elif not d.get("implemented"):
            skipped.append({"harness": h, "reason": "Phase 2/3 - not in MVP core"})
        else:
            plan.append({"harness": h, "governance": d.get("governance", False)})
    return plan, skipped


def coverage_complete(results: Dict[str, dict], attack_ids: List[str], skipped: List[dict]) -> bool:
    """Required-coverage check that feeds the gate's `required_ran` (A8 fail-closed).

    Coverage is complete only when NOTHING required was skipped (an unimplemented/unregistered
    required harness is a real coverage gap, never a silent pass) AND every planned attack harness
    actually completed. Any gap -> False -> the gate blocks (rule 2). This is what makes a skipped
    required harness gate-visible instead of invisibly absent.
    """
    if skipped:
        return False
    return all(results.get(h, {}).get("status") == "completed" for h in attack_ids)
