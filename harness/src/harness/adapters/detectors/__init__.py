"""Detectors — deterministic content analyzers that floor the judge (C3).

Default: regex detectors (zero installs). Upgrade: Presidio for PII/CPNI behind the same
signature. `build_detectors(names, use_presidio=...)` returns the callables the runner needs.
"""
from __future__ import annotations

from typing import Dict, List

from ...ports.detector_port import Detector
from .regex_detectors import REGEX_DETECTORS, is_refusal  # noqa: F401


def _toxicity_noop(_r: str):
    """Fallback when Detoxify is off/absent: no deterministic toxicity signal."""
    return (None, None)


def build_detectors(use_presidio: bool = False, use_detoxify: bool = False) -> Dict[str, Detector]:
    """Return the detector registry {name: callable}.

    secret/cpni upgrade to Presidio when asked; `toxicity` is always present (real Detoxify when
    enabled+installed, else a no-op so a harness listing it degrades to its judge).
    """
    detectors: Dict[str, Detector] = dict(REGEX_DETECTORS)
    if use_presidio:
        try:
            from .presidio_detector import presidio_secret, presidio_cpni
            detectors["secret"] = presidio_secret
            detectors["cpni"] = presidio_cpni
        except Exception:
            # Presidio not installed -> keep the regex floor (graceful degrade, logged by caller).
            pass
    if use_detoxify:
        try:
            from .detoxify_detector import detoxify_toxicity
            detectors["toxicity"] = detoxify_toxicity
        except Exception:
            detectors["toxicity"] = _toxicity_noop
    else:
        detectors["toxicity"] = _toxicity_noop
    return detectors
