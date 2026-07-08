"""File-backed evidence store (R6/A3) — content-hashed chain of custody + replay source.

Every model turn is written to disk and hashed; findings reference the stored uri; Mode-A
replay reads back through `read()` and re-verifies the hash. A production build swaps this for
an S3/WORM or append-only DB store behind the same EvidencePort — no application change.

Faithful to notebook §4 `EvidenceStore`.
"""
from __future__ import annotations

import os
import tempfile
from typing import Any, Dict, List, Optional, Tuple

from ...domain.contracts import now_iso, sha256_hex


class FileEvidenceStore:
    def __init__(self, root: Optional[str] = None):
        self.root = root or tempfile.mkdtemp(prefix="harness_evidence_")
        os.makedirs(os.path.join(self.root, "turns"), exist_ok=True)
        self.turn_no = 0
        self.verdict_no = 0
        self.access_log: List[Tuple[str, str]] = []

    def _write(self, rel: str, text: str) -> str:
        path = os.path.join(self.root, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
        return path

    def capture_turn(self, hr_id: str, role: str, agent: str, text: str,
                     adapter_name: str, model: Optional[dict] = None,
                     tokens: Optional[dict] = None) -> Dict[str, Any]:
        self.turn_no += 1
        tid = f"T-{self.turn_no:04d}"
        path = self._write(f"turns/{tid}.{role}.txt", text)
        return {
            "turn_id": tid, "harness_run_id": hr_id, "role": role, "agent": agent,
            "model": model or {"provider": adapter_name}, "output_hash": sha256_hex(text),
            "output_uri": path, "tokens": tokens or {}, "cost_usd": 0.0, "ts": now_iso(),
        }

    def capture_verdict(self, hr_id: str, cand_id: str, judge_name: str,
                        lens: str, v: dict) -> Dict[str, Any]:
        self.verdict_no += 1
        return {
            "verdict_id": f"V-{self.verdict_no:04d}", "finding_candidate_id": cand_id,
            "judge": judge_name, "lens": lens, "attack_succeeded": v["attack_succeeded"],
            "confidence": v["confidence"], "severity": v["severity"],
            "rationale": v["rationale"], "evidence_refs": [],
        }

    def read(self, uri: str) -> str:
        self.access_log.append((uri, now_iso()))
        with open(uri, encoding="utf-8") as f:
            return f.read()
