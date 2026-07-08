"""B0 — Canonical contracts & schemas. The shared language every layer speaks.

These types are the versioned interface between the control plane (decides) and the
data plane (executes). A change here is a *contract change* (bump the schema version and
get sign-off); everything else in the system is a seam implementation or a config tweak.

Faithful to the reference notebook (`enterprise_harness_mvp_colab.ipynb` §2) and to
`enterprise_harness_v1_backfill_register.md` (BF-01 run contract, BF-02 Finding schema).
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

# --- schema versions (bump on any breaking contract change) -----------------------------
RESULT_SCHEMA = "harness/result/v1"
GATE_SCHEMA = "gate/v1"

# --- severity + gate vocabulary (R9) ----------------------------------------------------
SEVERITY_ORDER: Dict[str, int] = {"info": 0, "low": 1, "medium": 2, "high": 3, "critical": 4}
INV_SEVERITY: Dict[int, str] = {v: k for k, v in SEVERITY_ORDER.items()}
GATE_VOCAB = frozenset({"approve", "warn", "block", "manual_review"})  # R9


def sev_rank(sev: str) -> int:
    return SEVERITY_ORDER.get(sev, 0)


# --- deterministic helpers (used everywhere for chain-of-custody) -----------------------
def sha256_hex(x: Any) -> str:
    """Content hash. Objects are canonicalized (sorted keys) so the hash is stable."""
    if isinstance(x, (dict, list)):
        x = json.dumps(x, sort_keys=True, separators=(",", ":"))
    if isinstance(x, str):
        x = x.encode("utf-8")
    return "sha256:" + hashlib.sha256(x).hexdigest()


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# --- inputs -----------------------------------------------------------------------------
@dataclass(frozen=True)
class Scenario:
    """One adversarial test case within a harness. `label` is the ground-truth (C1);
    None means 'borderline — excluded from calibration'."""
    id: str
    title: str
    category: str
    attack: str
    label: Optional[bool] = None


@dataclass(frozen=True)
class HarnessSpec:
    """A registered harness (BF-13). Declares its judge lenses, deterministic detectors,
    capability tags, standards mapping, and scenario set."""
    id: str
    name: str
    category: str  # test | exposure | remediation | resilience | governance
    lenses: List[str]
    detectors: List[str]
    capability_tags: List[str] = field(default_factory=list)
    standards: Dict[str, Any] = field(default_factory=dict)
    scenarios: List[Scenario] = field(default_factory=list)
    governance: bool = False


@dataclass(frozen=True)
class UseCase:
    """The asset-under-test context that drives risk scoring + pack selection (W1)."""
    name: str
    data_classes: List[str]
    exposure: str
    write_tools: bool
    users: List[str]
    criticality: str


# --- data-plane artifacts ---------------------------------------------------------------
@dataclass
class Verdict:
    """A single judge opinion on one candidate (data plane, A4 isolated judge)."""
    lens: str
    attack_succeeded: bool
    confidence: float
    severity: str
    rationale: str


@dataclass
class TurnRecord:
    """Chain-of-custody record for one model turn (R6/A3). Content is hashed + stored."""
    turn_id: str
    harness_run_id: str
    role: str
    agent: str
    model: Dict[str, Any]
    output_hash: str
    output_uri: str
    tokens: Dict[str, Any]
    cost_usd: float
    ts: str


@dataclass
class Finding:
    """BF-02 — the ONE canonical finding schema. Every harness and scanner emits this."""
    id: str
    source: str
    severity: str
    category: str
    title: str
    description: str
    blocking: bool
    policy_rule: str
    evidence_uri: str
    recommendation: str
    harness: str = ""
    standards: Dict[str, Any] = field(default_factory=dict)
    basis: str = ""  # BF-21 evidence_basis: detector(real-content) | llm-judge(real) | simulated-judge(offline)


# --- control-plane output ---------------------------------------------------------------
@dataclass
class GateDecision:
    """B5 — the single deterministic decision (A1: no LLM in this path)."""
    decision: str  # must be in GATE_VOCAB
    matched_rule: str
    rationale: str
    policy_version: str = GATE_SCHEMA


def to_dict(obj: Any) -> Any:
    """Serialize a dataclass (or nested) to plain dict for result.json / evidence."""
    return asdict(obj) if hasattr(obj, "__dataclass_fields__") else obj
