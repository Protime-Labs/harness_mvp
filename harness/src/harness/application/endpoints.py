"""HTTP/endpoint target as a first-class asset (follow-up to M5).

An asset of type model_endpoint / application_endpoint / agent_endpoint describes a RUNNING target
the harness evaluates over HTTP (via the existing HttpTargetAdapter). Secrets are referenced by
environment variable (`env:VAR`), never stored inline: `resolve_endpoint()` reads them at call time
and `inline_secret_refs()` flags any literal secret so it is caught before it reaches evidence.

Pure application logic (no adapters imported): it emits config OVERRIDES that the composition root
turns into an adapter — the endpoint asset drives the wiring without the app importing the wire.
"""
from __future__ import annotations

import os
from typing import Any, Dict, List

from ..domain.secrets import scan_secrets

ENDPOINT_TYPES = {"model_endpoint", "application_endpoint", "agent_endpoint"}


def is_endpoint_asset(asset: dict) -> bool:
    return (asset or {}).get("type") in ENDPOINT_TYPES


def resolve_ref(value: Any) -> Any:
    """`env:VAR` -> the environment value (empty string if unset); anything else returned as-is."""
    if isinstance(value, str) and value.startswith("env:"):
        return os.environ.get(value[4:], "")
    return value


def resolve_endpoint(asset: dict) -> Dict[str, Any]:
    """Resolve an endpoint asset to {url, headers, response_path} with all env: refs expanded."""
    url = resolve_ref(asset.get("endpoint_url_ref") or asset.get("endpoint_url") or "")
    headers: Dict[str, str] = {k: str(resolve_ref(v)) for k, v in (asset.get("headers") or {}).items()}
    auth = asset.get("auth_ref")
    if auth:
        headers.setdefault("Authorization", f"Bearer {resolve_ref(auth)}")
    return {"url": url, "headers": headers, "response_path": asset.get("response_path", "text")}


def inline_secret_refs(asset: dict) -> List[str]:
    """Header/auth fields carrying a LITERAL secret instead of an `env:` reference (hygiene fail)."""
    bad: List[str] = []
    for k, v in (asset.get("headers") or {}).items():
        if isinstance(v, str) and not v.startswith("env:") and scan_secrets(v):
            bad.append(k)
    auth = asset.get("auth_ref")
    if isinstance(auth, str) and not auth.startswith("env:") and (scan_secrets(auth) or len(auth) >= 16):
        bad.append("auth_ref")
    return bad


def endpoint_overrides(asset: dict) -> Dict[str, Any]:
    """Config overrides that point the harness at this endpoint asset over HTTP."""
    ep = resolve_endpoint(asset)
    ov: Dict[str, Any] = {"PROVIDER_MODE": "http", "HTTP_TARGET_URL": ep["url"],
                          "HTTP_RESPONSE_PATH": ep["response_path"]}
    if ep["headers"]:
        ov["HTTP_HEADERS"] = [f"{k}={v}" for k, v in ep["headers"].items()]
    return ov
