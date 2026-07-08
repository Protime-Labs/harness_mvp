"""Detectors — deterministic content analyzers that floor the judge (C3).

Default: regex detectors (zero installs). Upgrade: Presidio for PII/CPNI behind the same
signature. `build_detectors(names, use_presidio=...)` returns the callables the runner needs.
"""
from __future__ import annotations

from typing import Dict, List

from ...ports.detector_port import Detector
from .regex_detectors import REGEX_DETECTORS, is_refusal  # noqa: F401


def build_detectors(use_presidio: bool = False) -> Dict[str, Detector]:
    """Return the detector registry {name: callable}. secret/cpni upgrade to Presidio if asked."""
    detectors: Dict[str, Detector] = dict(REGEX_DETECTORS)
    if use_presidio:
        try:
            from .presidio_detector import presidio_secret, presidio_cpni
            detectors["secret"] = presidio_secret
            detectors["cpni"] = presidio_cpni
        except Exception:
            # Presidio not installed -> keep the regex floor (graceful degrade, logged by caller).
            pass
    return detectors
