"""HTTP target adapter (B2) for real enterprise apps and agents.

This adapter lets the harness assess an already-running application endpoint instead of a
provider model directly. It POSTs a small JSON envelope and extracts the response text from a
configurable JSON path. If the endpoint returns plain text, the raw body is used.
"""
from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any, Dict, Iterable


def _path_get(obj: Any, path: str) -> Any:
    cur = obj
    for part in (p for p in path.split(".") if p):
        if isinstance(cur, dict):
            cur = cur.get(part)
        elif isinstance(cur, list) and part.isdigit():
            cur = cur[int(part)]
        else:
            return None
    return cur


class HttpTargetAdapter:
    name = "http"

    def __init__(
        self,
        url: str,
        *,
        response_path: str = "text",
        timeout_s: int = 30,
        headers: Dict[str, str] | None = None,
    ):
        if not url:
            raise ValueError("HTTP target mode requires HTTP_TARGET_URL or --target-url.")
        self.url = url
        self.response_path = response_path or "text"
        self.timeout_s = int(timeout_s or 30)
        self.headers = headers or {}

    def invoke(self, role: str, prompt: str, system: str = "", **kw: Any) -> Dict[str, Any]:
        payload = {
            "role": role,
            "prompt": prompt,
            "system": system,
            "metadata": {"source": "enterprise-harness", **kw},
        }
        body = json.dumps(payload).encode("utf-8")
        headers = {"Content-Type": "application/json", "Accept": "application/json, text/plain"}
        headers.update(self.headers)
        req = urllib.request.Request(self.url, data=body, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=self.timeout_s) as resp:
                raw = resp.read().decode("utf-8", errors="replace")
                ctype = resp.headers.get("content-type", "")
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"HTTP target returned {exc.code}: {detail[:500]}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"HTTP target unavailable: {exc.reason}") from exc

        text = raw
        model_meta: Dict[str, Any] = {"provider": "http", "url": self.url, "response_path": self.response_path}
        if "json" in ctype.lower():
            try:
                data = json.loads(raw)
                picked = _path_get(data, self.response_path)
                if picked is None:
                    picked = (
                        data.get("text")
                        or data.get("response")
                        or data.get("output")
                        or data.get("message")
                    )
                if picked is None:
                    text = raw
                elif isinstance(picked, str):
                    text = picked
                else:
                    text = json.dumps(picked, sort_keys=True)
                model_meta["response_keys"] = list(data.keys()) if isinstance(data, dict) else []
            except Exception:
                text = raw

        return {
            "text": text or "",
            "tokens": {"in": 0, "out": 0},
            "cost_usd": 0.0,
            "model": model_meta,
        }


def parse_headers(items: Iterable[str] | None) -> Dict[str, str]:
    out: Dict[str, str] = {}
    for item in items or []:
        if "=" not in item:
            raise ValueError(f"Header must be KEY=VALUE, got {item!r}")
        k, v = item.split("=", 1)
        out[k.strip()] = v.strip()
    return out
