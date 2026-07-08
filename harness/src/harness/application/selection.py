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
