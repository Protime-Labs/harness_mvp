"""B4 — the evidence seam. Content-hashed chain of custody + replay source (R6/A3).

Audit, remediation, SIEM export, and Mode-A replay all READ through this port. A file-backed
implementation ships in adapters/evidence; an S3/WORM or database-backed store can replace it
without touching the application.
"""
from __future__ import annotations

from typing import Any, Dict, Optional, Protocol, runtime_checkable


@runtime_checkable
class EvidencePort(Protocol):
    root: str

    def capture_turn(self, hr_id: str, role: str, agent: str, text: str,
                     adapter_name: str, model: Optional[dict] = None,
                     tokens: Optional[dict] = None) -> Dict[str, Any]:
        """Persist a model turn; return a TurnRecord dict (turn_id, output_hash, output_uri, ...)."""
        ...

    def capture_verdict(self, hr_id: str, cand_id: str, judge_name: str,
                        lens: str, v: dict) -> Dict[str, Any]:
        """Persist a judge verdict; return a verdict record (verdict_id, ...)."""
        ...

    def read(self, uri: str) -> str:
        """Read back stored content by uri (logs the access for audit)."""
        ...
