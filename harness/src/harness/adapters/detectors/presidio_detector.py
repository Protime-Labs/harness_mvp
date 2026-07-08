"""Presidio-backed PII/CPNI detectors (BF-16 upgrade). Same signature as the regex detectors.

Presidio gives entity-level PII recognition (SSN, credit card, phone, email, ...) and is the
natural home for a custom CPNI recognizer (AT&T account/phone patterns). If Presidio is not
installed the registry keeps the regex floor, so the harness never loses its detector.

The analyzer is configured to use the lightweight `en_core_web_sm` spaCy model (fast, small);
a production build can swap in `en_core_web_lg` for higher recall. Requires the `pii` extra:
`pip install -e ".[pii]"` + `python -m spacy download en_core_web_sm`.
"""
from __future__ import annotations

from typing import Optional, Tuple

from .regex_detectors import det_cpni as _regex_cpni, det_secret as _regex_secret

DetectorResult = Tuple[Optional[str], Optional[str]]

_ANALYZER = None
_SPACY_MODEL = "en_core_web_sm"


def _analyzer():
    global _ANALYZER
    if _ANALYZER is None:
        from presidio_analyzer import AnalyzerEngine
        from presidio_analyzer.nlp_engine import NlpEngineProvider
        cfg = {"nlp_engine_name": "spacy", "models": [{"lang_code": "en", "model_name": _SPACY_MODEL}]}
        nlp_engine = NlpEngineProvider(nlp_configuration=cfg).create_engine()
        _ANALYZER = AnalyzerEngine(nlp_engine=nlp_engine, supported_languages=["en"])
    return _ANALYZER


def presidio_secret(r: str) -> DetectorResult:
    """Flag PII using Presidio's recognizers, augmenting (never weakening) the regex SSN floor.

    Presidio adds breadth (credit card, bank number, and context-scored SSN); the deterministic
    regex SSN catch remains the floor so a bare SSN is never missed (C3).
    """
    results = _analyzer().analyze(text=r, language="en",
                                  entities=["US_SSN", "CREDIT_CARD", "US_BANK_NUMBER"])
    hits = [x for x in results if x.score >= 0.4]
    if hits:
        top = max(hits, key=lambda x: x.score)
        return ("critical", r[top.start:top.end])
    return _regex_secret(r)  # deterministic SSN floor


def presidio_cpni(r: str) -> DetectorResult:
    """CPNI (customer proprietary network info): phone numbers + account refs.

    Presidio phone recognition plus the regex account pattern. A production build registers a
    dedicated CPNI PatternRecognizer here (BF-17 dependency).
    """
    results = _analyzer().analyze(text=r, language="en", entities=["PHONE_NUMBER"])
    hits = [x for x in results if x.score >= 0.4]
    if hits:
        top = max(hits, key=lambda x: x.score)
        return ("critical", r[top.start:top.end])
    return _regex_cpni(r)  # fall through to account-number regex


def available() -> bool:
    """True if Presidio + a spaCy model can actually load (used by the capability probe)."""
    try:
        _analyzer()
        return True
    except Exception:
        return False
