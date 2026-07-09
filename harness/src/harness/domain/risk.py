"""Risk scoring & pack selection (W1 contextualization). PURE.

A transparent weighted score over the use-case attributes decides a risk tier, which
selects the harness pack. Weights are injected (from config, B6) so governance/risk owners
tune the number without a code change (BF-10).

Faithful to notebook §9 `contextualize` + `RISK_WEIGHTS`.
"""
from __future__ import annotations

from typing import Dict, List

from .contracts import UseCase


def risk_score(use_case: UseCase, weights: Dict[str, dict]) -> int:
    dc = max((weights["data_class"].get(x, 0) for x in use_case.data_classes), default=0)
    exposure = weights["exposure"].get(use_case.exposure, 0)
    write = weights["write_tools"]["present" if use_case.write_tools else "absent"]
    users = max((weights["users"].get(x, 0) for x in use_case.users), default=0)
    crit = weights["criticality"].get(use_case.criticality, 0)
    return dc + exposure + write + users + crit


def tier_for(score: int, cutoffs: Dict[str, int]) -> str:
    if score >= cutoffs.get("high", 60):
        return "high"
    if score >= cutoffs.get("medium", 30):
        return "medium"
    return "low"


def contextualize(
    use_case: UseCase,
    weights: Dict[str, dict],
    cutoffs: Dict[str, int],
    pack: List[str],
    pack_tier: str = "foundational",
) -> dict:
    """Score the use case, pick a tier, return the required harness pack + rationale."""
    score = risk_score(use_case, weights)
    tier = tier_for(score, cutoffs)
    return {
        "score": score,
        "tier": tier,
        "required_harnesses": list(pack),
        "pack_tier": pack_tier,
        "rationale": f"score={score} -> {tier}; {pack_tier.capitalize()} pack",
    }
