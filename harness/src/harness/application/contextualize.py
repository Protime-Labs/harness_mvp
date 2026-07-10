"""W1 — contextualization. Turn a use-case description into a risk tier + required pack.

Thin application wrapper over the pure `domain.risk` scorer, wiring in the config-driven
weights/cutoffs/pack (B6). Rules decide here — no LLM (A1).
"""
from __future__ import annotations

from typing import Dict

from ..domain.contracts import UseCase
from ..domain.risk import contextualize as _contextualize


def contextualize(use_case: dict, policy: Dict) -> dict:
    """`policy` = the loaded {risk_weights, risk_cutoffs, foundational_pack} bundle."""
    uc = UseCase(
        name=use_case["name"], data_classes=use_case["data_classes"], exposure=use_case["exposure"],
        write_tools=use_case["write_tools"], users=use_case["users"], criticality=use_case["criticality"],
    )
    return _contextualize(uc, policy["risk_weights"], policy["risk_cutoffs"], policy["foundational_pack"],
                          packs=policy.get("packs"), require_when=policy.get("require_when"),
                          trust=policy["config"].get("INHERENT_TRUST"),
                          trust_escalation=policy.get("trust_escalation"))
