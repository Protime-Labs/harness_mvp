"""W? — quarantine (the security front door). Produce a QuarantineDecision the gate consumes.

This is the seam that turns "quarantine" from a hard-coded gate argument into a real control-plane
input. In the MVP core there is no ingress scanner wired yet (that is the next milestone: a local
redacted secrets scanner over asset content), so this returns an explicit `allow` WITH the reason
that no scanner is configured — honest, not silently permissive. When a scanner is added it emits
canonical `Finding(source="scanner")` records here and can raise the decision to `block`.

Pure control plane, no LLM (A1): a scanner is a deterministic detector, never a model in the gate
path. `QUARANTINE_SCANNER_URL` (config) is the enterprise dependency that would back a real scan.
"""
from __future__ import annotations

from typing import Any, Dict, List


def screen_asset(asset: Dict[str, Any], cfg: dict) -> Dict[str, Any]:
    """Return a QuarantineDecision-shaped dict: {decision, findings, reason, scanner}.

    decision ∈ {allow, warn, block, manual_review} (gate vocabulary). For now the MVP core has no
    scanner, so the decision is `allow` with a truthful reason; the object is recorded in the run
    bundle for audit and threaded into the deterministic gate as its quarantine input.
    """
    scanner_url = (cfg or {}).get("QUARANTINE_SCANNER_URL") or ""
    findings: List[dict] = []
    if not scanner_url:
        return {
            "decision": "allow",
            "findings": findings,
            "reason": "no quarantine scanner configured (QUARANTINE_SCANNER_URL unset); "
                      "ingress not screened in the MVP core",
            "scanner": None,
        }
    # An enterprise scanner is declared but not invoked from the offline core; surface it honestly
    # rather than pretending a scan ran.
    return {
        "decision": "allow",
        "findings": findings,
        "reason": f"quarantine scanner declared ({scanner_url}) but not invoked from the offline core",
        "scanner": scanner_url,
    }
