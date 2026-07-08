"""The detector seam. A deterministic content detector (no LLM) that floors the judge (C3).

A Detector reads the ACTUAL model response and returns a hard signal. Regex detectors ship
by default; Presidio (PII/CPNI) plugs in behind the same signature. Real scanners emit the
canonical Finding directly (a coarser integration at the B0 layer).
"""
from __future__ import annotations

from typing import Optional, Protocol, Tuple, runtime_checkable

# (severity | None, matched_span | None)  -- None severity means "no hit"
DetectorResult = Tuple[Optional[str], Optional[str]]


@runtime_checkable
class Detector(Protocol):
    def __call__(self, response: str) -> DetectorResult:
        ...
