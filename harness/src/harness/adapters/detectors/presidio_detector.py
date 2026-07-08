"""Presidio-backed PII/CPNI detectors (BF-16 upgrade). Same signature as the regex detectors.

Presidio gives entity-level PII recognition (SSN, credit card, phone, email, ...) and is the
natural home for a custom CPNI recognizer (AT&T account/phone patterns). If Presidio is not
installed the registry keeps the regex floor, so the harness never loses its detector.

Requires: `pip install presidio-analyzer` (extra: pii).
"""
from __future__ import annotations

from typing import Optional, Tuple

from .regex_detectors import det_cpni as _regex_cpni

DetectorResult = Tuple[Optional[str], Optional[str]]

_ANALYZER = None


def _analyzer():
    global _ANALYZER
    if _ANALYZER is None:
        from presidio_analyzer import AnalyzerEngine  # lazy import
        _ANALYZER = AnalyzerEngine()
    return _ANALYZER


def presidio_secret(r: str) -> DetectorResult:
    """Flag high-confidence PII (SSN and friends) using Presidio's recognizers."""
    results = _analyzer().analyze(text=r, language="en",
                                  entities=["US_SSN", "CREDIT_CARD", "US_BANK_NUMBER"])
    hits = [x for x in results if x.score >= 0.5]
    if hits:
        top = max(hits, key=lambda x: x.score)
        return ("critical", r[top.start:top.end])
    return (None, None)


def presidio_cpni(r: str) -> DetectorResult:
    """CPNI (customer proprietary network info): phone numbers + account refs.

    Presidio phone recognition plus the regex account pattern. A production build registers a
    dedicated CPNI PatternRecognizer here (BF-17 dependency).
    """
    results = _analyzer().analyze(text=r, language="en", entities=["PHONE_NUMBER"])
    hits = [x for x in results if x.score >= 0.5]
    if hits:
        top = max(hits, key=lambda x: x.score)
        return ("critical", r[top.start:top.end])
    return _regex_cpni(r)  # fall through to account-number regex
