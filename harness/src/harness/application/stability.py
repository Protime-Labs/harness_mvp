"""Stability / determinism check (B7). Run the core N times and measure how consistent the
findings are via Jaccard overlap. Mock is deterministic (A7) -> 1.0; a real model is "bounded"
-> may be < 1.0. This quantifies the `determinism_class` claim for real runs.
"""
from __future__ import annotations

from typing import List, Set, Tuple


def finding_key_set(bundle: dict) -> Set[Tuple[str, str, str]]:
    """Identity of a finding for stability: (harness, category, severity)."""
    return {(f.get("harness", ""), f.get("category", ""), f.get("severity", ""))
            for f in bundle.get("findings", [])}


def jaccard(a: Set, b: Set) -> float:
    if not a and not b:
        return 1.0
    return round(len(a & b) / len(a | b), 3)


def stability_from_sets(sets: List[Set]) -> dict:
    base = sets[0]
    scores = [jaccard(base, s) for s in sets[1:]] or [1.0]
    mean = round(sum(scores) / len(scores), 3)
    return {
        "runs": len(sets),
        "mean_jaccard": mean,
        "stable": mean >= 0.99,
        "class": "deterministic" if mean == 1.0 else "bounded",
        "finding_counts": [len(s) for s in sets],
    }
