"""W? — quarantine (the security front door). Produce a QuarantineDecision the gate consumes.

The gate takes `quarantine` as a real control-plane input (not a hard-coded argument). This module
screens the asset's own content with a deterministic local secrets scanner BEFORE any harness runs
or any prompt is sent to the target: a credential embedded in an asset config is refused at ingress.

Findings are canonical `Finding(source="scanner")` records carrying only REDACTED snippets + a
fingerprint (see `domain.secrets`) — the raw secret is never stored. Pure control plane, no LLM
(A1): a scanner is a deterministic detector, never a model in the gate path. `QUARANTINE_SCANNER_URL`
(config) is the enterprise ingress-scanner dependency that would augment this local floor.
"""
from __future__ import annotations

from dataclasses import asdict
from typing import Any, Dict, Iterator, List, Tuple

from ..domain.contracts import Finding
from ..domain.secrets import scan_secrets


def _iter_strings(obj: Any, path: str = "asset") -> Iterator[Tuple[str, str]]:
    """Yield (field_path, string) for every string value in the asset (recursively)."""
    if isinstance(obj, str):
        yield path, obj
    elif isinstance(obj, dict):
        for k, v in obj.items():
            yield from _iter_strings(v, f"{path}.{k}")
    elif isinstance(obj, (list, tuple)):
        for i, v in enumerate(obj):
            yield from _iter_strings(v, f"{path}[{i}]")


def screen_asset(asset: Dict[str, Any], cfg: dict) -> Dict[str, Any]:
    """Return a QuarantineDecision-shaped dict: {decision, findings, reason, scanner}.

    decision ∈ {allow, block} (gate vocabulary). A secret anywhere in asset content -> `block`
    (findings carry redacted evidence); otherwise `allow` with an honest note about the (not
    invoked) enterprise scanner. The object is recorded in the run bundle for audit.
    """
    findings: List[dict] = []
    for field, text in _iter_strings(asset or {}):
        for hit in scan_secrets(text):
            findings.append(asdict(Finding(
                id=f"Q-SECRET-{len(findings) + 1}",
                source="scanner",
                severity="critical",
                category="secret.exposed",
                title=f"{hit.kind} in asset content",
                description=f"A {hit.kind} was found in {field}: {hit.redacted} ({hit.fingerprint[:19]}…)",
                blocking=True,
                policy_rule="QUAR-SECRET",
                evidence_uri="",
                recommendation="Remove the secret from asset content and rotate the credential; "
                               "reference secrets by env var, never inline.",
                harness="quarantine",
                standards={"owasp_llm": ["LLM02"], "cwe": ["CWE-798"]},
                basis="detector(real-content)",
            )))

    if findings:
        return {
            "decision": "block",
            "findings": findings,
            "reason": f"{len(findings)} secret(s) detected in asset content by the local scanner",
            "scanner": "local-regex-secrets",
        }

    scanner_url = (cfg or {}).get("QUARANTINE_SCANNER_URL") or ""
    enterprise = ("enterprise ingress scanner not configured" if not scanner_url
                  else f"enterprise scanner {scanner_url} declared but not invoked from the offline core")
    return {
        "decision": "allow",
        "findings": [],
        "reason": f"clean: no secrets detected by the local scanner ({enterprise})",
        "scanner": "local-regex-secrets",
    }
