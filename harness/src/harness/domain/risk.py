"""Risk scoring & pack selection (W1 contextualization). PURE (stdlib only).

A transparent weighted score over the use-case attributes decides a risk tier, which selects the
harness pack. Weights, per-tier packs, and mandatory `require_when` clauses are injected from config
(B6) so governance/risk owners tune them without a code change (BF-10).

FAIL CLOSED (control-plane ground rule): an UNRECOGNIZED attribute value scores the MAXIMUM weight
in its category and is flagged in `unknown_attributes` — an unknown classification is the worst
case, never safe (0). The gate routes a run with unknown attributes to manual_review (F1).

The required harness set is the UNION of (a) the pack for the computed tier and (b) every matched
`require_when` clause — so a single high-signal attribute (PHI, write tools) can never be diluted
out of a mandatory harness by a low weighted sum (F3). Each selected harness carries its reason (F8).

Faithful to notebook §9 `contextualize` + `RISK_WEIGHTS`.
"""
from __future__ import annotations

from typing import Dict, List, Tuple

from .contracts import UseCase


def _weight(weights: Dict[str, dict], category: str, value, unknown: List[str]) -> int:
    """Weight for one attribute value. An unknown value scores the MAX weight in the category
    (fail closed) and is recorded — never the fail-open 0."""
    table = weights[category]
    if value in table:
        return table[value]
    unknown.append(f"{category}:{value}")
    return max(table.values(), default=0)


def risk_score(use_case: UseCase, weights: Dict[str, dict]) -> Tuple[int, List[str]]:
    """Return (score, unknown_attributes). `write_tools` is a bool, so it is always known."""
    unknown: List[str] = []
    dc = max((_weight(weights, "data_class", x, unknown) for x in use_case.data_classes), default=0)
    exposure = _weight(weights, "exposure", use_case.exposure, unknown)
    write = weights["write_tools"]["present" if use_case.write_tools else "absent"]
    users = max((_weight(weights, "users", x, unknown) for x in use_case.users), default=0)
    crit = _weight(weights, "criticality", use_case.criticality, unknown)
    return dc + exposure + write + users + crit, unknown


def tier_for(score: int, cutoffs: Dict[str, int]) -> str:
    if score >= cutoffs.get("high", 60):
        return "high"
    if score >= cutoffs.get("medium", 30):
        return "medium"
    return "low"


def _matches(use_case: UseCase, cond: dict) -> bool:
    """Evaluate one require_when condition over a use-case attribute — pure dict/list logic,
    no eval / no expression language. Supports `contains` (list membership) and `equals`."""
    value = getattr(use_case, cond.get("attr", ""), None)
    if "contains" in cond:
        return isinstance(value, (list, tuple)) and cond["contains"] in value
    if "equals" in cond:
        return value == cond["equals"]
    return False


def _resolve_required(use_case: UseCase, base_pack: List[str], tier: str,
                      require_when: List[dict]) -> Tuple[List[str], List[dict]]:
    """Union of the tier pack and every matched require_when clause (order-stable, deterministic).
    Returns (required_harnesses, plan_reasons) where each reason is {harness, reason} (F8)."""
    required: List[str] = []
    reasons: List[dict] = []

    def _add(hid: str, reason: str) -> None:
        if hid not in required:
            required.append(hid)
            reasons.append({"harness": hid, "reason": reason})

    for hid in base_pack:
        _add(hid, f"tier:{tier} pack")
    for clause in require_when or []:
        when = clause.get("when", {})
        if _matches(use_case, when):
            label = f"clause: {when.get('attr')}={when.get('contains', when.get('equals'))}"
            for hid in clause.get("require", []):
                _add(hid, label)
    return required, reasons


def contextualize(
    use_case: UseCase,
    weights: Dict[str, dict],
    cutoffs: Dict[str, int],
    pack: List[str],
    pack_tier: str = "foundational",
    packs: Dict[str, List[str]] = None,
    require_when: List[dict] = None,
) -> dict:
    """Score the use case, pick a tier, resolve the required set (tier pack ∪ matched clauses).

    `packs` (per-tier) overrides `pack` for the computed tier when present; absent -> `pack` for all
    tiers (backward compatible, F2). `require_when` adds mandatory harnesses regardless of tier (F3).
    """
    score, unknown = risk_score(use_case, weights)
    tier = tier_for(score, cutoffs)
    tier_pack = (packs or {}).get(tier)
    base = list(tier_pack) if tier_pack else list(pack)
    required, reasons = _resolve_required(use_case, base, tier, require_when)
    return {
        "score": score,
        "tier": tier,
        "required_harnesses": required,
        "plan_reasons": reasons,
        "unknown_attributes": unknown,
        "pack_tier": pack_tier,
        "rationale": (f"score={score} -> {tier}; {len(required)} required "
                      f"({'per-tier' if tier_pack else 'default'} pack)"
                      + (f"; UNKNOWN attrs {unknown}" if unknown else "")),
    }
