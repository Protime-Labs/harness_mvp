"""Capability / plugin inventory — what this lab can actually run, per seam.

The harness is built so every real component plugs into a seam (B2 model, B3 driver, B4
evidence, the detector seam, B6 config). This module enumerates ALL of them and probes the
environment to resolve each into a lab-realistic status:

  available   — usable right now (built-in, or an optional package that is installed)
  installable — a LOCAL pip dependency that just isn't installed yet (`pip install ...[extra]`)
  stub        — seam defined, implementation not built yet (buildable in the lab)
  enterprise  — needs an enterprise dependency NOT wired into the lab (Janus, Model Router,
                Golden Controls catalogue, WORM store) — intentionally disconnected

The point: the lab runs everything that is built-in / pip-installable / buildable, and keeps
the enterprise dependencies clearly separated as stubs — a realistic environment you can
experiment in without touching production systems.
"""
from __future__ import annotations

import importlib.util
import os
from typing import Dict, List

# group -> ordered plugin catalogue. `module` is probed with find_spec (no import side effects).
CATALOGUE = [
    # --- Model providers (B2 / ModelPort) ---
    {"group": "Model providers (B2 · ModelPort)", "id": "mock", "name": "Mock target (offline, scripted)",
     "seam": "ModelPort", "kind": "builtin", "cite": "adapters/model/mock_adapter.py"},
    {"group": "Model providers (B2 · ModelPort)", "id": "litellm", "name": "LiteLLM — 100+ real providers",
     "seam": "ModelPort", "kind": "optional-pip", "extra": "providers", "module": "litellm",
     "env": ["ANTHROPIC_API_KEY", "OPENAI_API_KEY", "AZURE_API_KEY"], "cite": "adapters/model/litellm_adapter.py"},
    {"group": "Model providers (B2 · ModelPort)", "id": "janus", "name": "Janus (role TBD)",
     "seam": "ModelPort", "kind": "enterprise", "cite": "DR-05 · base-layers seam B2"},
    {"group": "Model providers (B2 · ModelPort)", "id": "model_router", "name": "AT&T Model Router",
     "seam": "ModelPort", "kind": "enterprise", "cite": "DR-08 · fronts the adapter"},

    # --- Detectors (Detector seam · C3 floor) ---
    {"group": "Detectors (Detector seam · C3 floor)", "id": "regex", "name": "Regex SSN / account / action",
     "seam": "Detector", "kind": "builtin", "cite": "adapters/detectors/regex_detectors.py"},
    {"group": "Detectors (Detector seam · C3 floor)", "id": "presidio", "name": "Presidio PII/CPNI",
     "seam": "Detector", "kind": "optional-pip", "extra": "pii", "module": "presidio_analyzer",
     "cite": "adapters/detectors/presidio_detector.py"},
    {"group": "Detectors (Detector seam · C3 floor)", "id": "scanners", "name": "Quarantine scanners",
     "seam": "Finding", "kind": "enterprise", "cite": "DR-09 · security front door"},

    # --- Harness drivers (B3 / HarnessDriver) ---
    {"group": "Harness drivers (B3 · HarnessDriver)", "id": "builtin", "name": "Built-in scenario driver",
     "seam": "HarnessDriver", "kind": "builtin", "cite": "application/runner.py"},
    {"group": "Harness drivers (B3 · HarnessDriver)", "id": "agentic_overlay", "name": "Agentic overlay (adaptive)",
     "seam": "HarnessDriver", "kind": "stub", "cite": "DR-06 · adapters/drivers/overlay_driver.py"},
    {"group": "Harness drivers (B3 · HarnessDriver)", "id": "pyrit", "name": "Microsoft PyRIT",
     "seam": "HarnessDriver", "kind": "optional-pip", "extra": "redteam", "module": "pyrit",
     "cite": "adapters/drivers/pyrit_driver.py"},
    {"group": "Harness drivers (B3 · HarnessDriver)", "id": "garak", "name": "NVIDIA Garak probes",
     "seam": "HarnessDriver", "kind": "optional-pip", "extra": "redteam", "module": "garak",
     "cite": "driver seam (same pattern as PyRIT)"},

    # --- Evidence (B4 / EvidencePort) ---
    {"group": "Evidence store (B4 · EvidencePort)", "id": "file", "name": "File store (content-hashed)",
     "seam": "EvidencePort", "kind": "builtin", "cite": "adapters/evidence/file_evidence.py"},
    {"group": "Evidence store (B4 · EvidencePort)", "id": "worm", "name": "S3 / WORM durable store",
     "seam": "EvidencePort", "kind": "enterprise", "cite": "Iter 4 · same port"},

    # --- Config & standards (B6) ---
    {"group": "Config & standards (B6)", "id": "yaml", "name": "YAML policy overrides",
     "seam": "config", "kind": "optional-pip", "extra": "config", "module": "yaml",
     "cite": "adapters/config/loader.py"},
    {"group": "Config & standards (B6)", "id": "golden_controls", "name": "AT&T Golden Controls catalogue",
     "seam": "config/B0", "kind": "enterprise", "cite": "DR-07 · config/golden_controls.yaml"},
]

_STATUS = {"builtin": "available", "stub": "stub", "enterprise": "enterprise"}


def _installed(module: str) -> bool:
    try:
        return importlib.util.find_spec(module) is not None
    except (ImportError, ValueError):
        return False


def probe() -> List[dict]:
    """Resolve each catalogue entry against the current environment."""
    out = []
    for raw in CATALOGUE:
        c = dict(raw)
        kind = c["kind"]
        if kind == "optional-pip":
            c["status"] = "available" if (c.get("module") and _installed(c["module"])) else "installable"
        else:
            c["status"] = _STATUS.get(kind, "unknown")
        # lab-runnable = anything that isn't gated on an enterprise dependency
        c["lab"] = c["status"] in ("available", "installable", "stub")
        if c.get("env"):
            c["key_present"] = any(os.environ.get(e) for e in c["env"])
        out.append(c)
    return out


def summarize(caps: List[dict]) -> Dict[str, int]:
    s = {"available": 0, "installable": 0, "stub": 0, "enterprise": 0}
    for c in caps:
        s[c["status"]] = s.get(c["status"], 0) + 1
    s["lab_runnable"] = sum(1 for c in caps if c["lab"])
    s["total"] = len(caps)
    return s
