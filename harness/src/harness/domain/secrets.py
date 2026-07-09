"""Deterministic secret scanning for the quarantine front door (A1: no LLM, pure stdlib regex).

Detects common credential shapes (cloud keys, private-key blocks, provider tokens, inline
`key=value` secrets) in asset content. Emits REDACTED matches only — the raw secret is never
returned, logged, or stored; callers get a masked snippet plus a content fingerprint (hash of the
raw match) so the same leak can be correlated across runs without ever exposing it.

Regex-only by design (no entropy heuristics) to keep it deterministic and false-positive-averse:
a quarantine block must be defensible. A production build swaps in gitleaks/entropy behind the same
`scan_secrets` shape.
"""
from __future__ import annotations

import re
from typing import List, NamedTuple

from .contracts import sha256_hex


class SecretHit(NamedTuple):
    kind: str          # what pattern matched (e.g. "aws_access_key_id")
    redacted: str      # masked snippet safe to store/display
    fingerprint: str   # sha256 of the raw match — correlate without exposing


# (kind, pattern). Ordered specific -> generic; each match is de-duplicated by fingerprint.
_PATTERNS = [
    ("aws_access_key_id", re.compile(r"\bA(?:KIA|SIA)[0-9A-Z]{16}\b")),
    ("aws_secret_access_key",
     re.compile(r"(?i)aws_secret_access_key\s*[=:]\s*['\"]?([A-Za-z0-9/+=]{40})")),
    ("private_key_block",
     re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |DSA |PGP )?PRIVATE KEY-----")),
    ("openai_api_key", re.compile(r"\bsk-[A-Za-z0-9]{20,}\b")),
    ("slack_token", re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b")),
    ("github_token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{36,}\b")),
    ("google_api_key", re.compile(r"\bAIza[0-9A-Za-z_\-]{35}\b")),
    ("bearer_token", re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._\-]{20,}")),
    ("inline_credential",
     re.compile(r"(?i)\b(?:api[_-]?key|secret|token|password|passwd)\b\s*[=:]\s*['\"]?([A-Za-z0-9._\-/+=]{12,})")),
]


def _redact(raw: str) -> str:
    s = raw.strip().strip("'\"")
    if len(s) <= 8:
        return "*" * len(s)
    return (s[:4] + "*" * (len(s) - 8) + s[-4:])[:48]


def scan_secrets(text: str) -> List[SecretHit]:
    """Return redacted secret hits found in `text` (empty list when clean)."""
    hits: List[SecretHit] = []
    seen: set[str] = set()
    for kind, rx in _PATTERNS:
        for m in rx.finditer(text or ""):
            raw = m.group(0)
            fp = sha256_hex(raw)
            if fp in seen:
                continue
            seen.add(fp)
            hits.append(SecretHit(kind=kind, redacted=_redact(raw), fingerprint=fp))
    return hits
