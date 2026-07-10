"""B1 — the invariant registry (the constitution every component obeys).

These are *definitions* (id + statement + citation). The machine-checked acceptance suite
that proves them against a live run lives in `application/acceptance.py`. Keeping the
statements here — in the pure domain — makes them the single source of truth referenced by
docs, tests, and reviews.

Sources: architecture_v3.md (A1-A10), design.md (R1-R9), spec_addendum_C1-C6 (+C7).
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Invariant:
    id: str
    statement: str
    source: str


INVARIANTS = {
    "A1": Invariant("A1", "Agents generate & judge (data plane); deterministic policy decides "
                          "(control plane). No LLM in the gate/risk path.", "architecture_v3 §keystone"),
    "R2": Invariant("R2", "Provider independence: one model I/O path; harnesses never bind to a "
                          "concrete provider.", "design R2"),
    "A2": Invariant("A2", "A single adapter mediates every model call (role, prompt, system).", "architecture_v3 A2"),
    "A3": Invariant("A3", "Every model turn is captured as content-hashed evidence.", "architecture_v3 A3 / R6"),
    "A4": Invariant("A4", "Judges are isolated and tool-less; a judge takes no actions.", "architecture_v3 A4"),
    "A5": Invariant("A5", "Each candidate is judged by a quorum of N (odd) diverse lenses.", "architecture_v3 A5 / C3"),
    "C3": Invariant("C3", "Deterministic detectors floor the judge: a detector hit is success "
                          "regardless of the quorum vote.", "spec_addendum C3.3"),
    "A7": Invariant("A7", "Runs are deterministic under a fixed seed (mock) / bounded (real).", "architecture_v3 A7 / C5"),
    "A8": Invariant("A8", "Budgets fail closed: a breach stops the harness and blocks the gate.", "architecture_v3 A8 / C6"),
    "C4": Invariant("C4", "Mode-A replay reconstructs all findings + the gate from evidence alone, "
                          "with no model calls.", "spec_addendum C4"),
    "A9": Invariant("A9", "A judge quorum is gate-eligible only if it meets calibration thresholds "
                          "(precision/recall/accuracy).", "architecture_v3 A9 / C1"),
    "R9": Invariant("R9", "The gate emits exactly one of {approve, warn, block, manual_review}.", "design R9"),
    "A11": Invariant("A11", "Monotonic selection: escalating a risk attribute OR lowering inherent "
                            "trust never shrinks the required harness set (tier packs ∪ require_when ∪ "
                            "trust escalation).", "control-plane triage F3 + Req 2 trust axis"),
}
