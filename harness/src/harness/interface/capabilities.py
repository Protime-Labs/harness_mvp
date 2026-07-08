"""Capability / plugin inventory — what this lab can actually run, per seam.

The harness is built so every real component plugs into a seam (B2 model, B3 driver, B4
evidence, the detector seam, B6 config, reporting). This module enumerates ALL of them and
probes the environment to resolve each into a lab-realistic status:

  available   — usable right now (built-in, or a WIRED optional package that is installed)
  installable — a LOCAL pip/npm dependency you can add (`pip install ...[extra]`); if its
                adapter is still a stub, the meta says so (package installs; wiring is the step)
  stub        — seam defined, implementation not built yet (buildable in the lab)
  enterprise  — needs an enterprise dependency NOT wired into the lab (Janus, Model Router,
                Golden Controls catalogue, WORM store) — intentionally disconnected

`wired` marks whether an adapter that actually uses the dependency exists yet. A wired+installed
optional dep is `available`; a not-yet-wired optional dep stays `installable` (the package is a
pip away, but someone still writes the ~30-line adapter against the seam).
"""
from __future__ import annotations

import importlib.util
import os
from typing import Dict, List

# group -> ordered plugin catalogue. `modules` are probed with find_spec (no import side effects).
CATALOGUE = [
    # --- Model providers (B2 · ModelPort) ---
    {"group": "Model providers (B2 · ModelPort)", "id": "mock", "name": "Mock target (offline, scripted)",
     "seam": "ModelPort", "kind": "builtin", "wired": True, "cite": "adapters/model/mock_adapter.py"},
    {"group": "Model providers (B2 · ModelPort)", "id": "litellm", "name": "LiteLLM — 100+ real providers",
     "seam": "ModelPort", "kind": "optional-pip", "wired": True, "extra": "providers", "modules": ["litellm"],
     "env": ["ANTHROPIC_API_KEY", "OPENAI_API_KEY", "AZURE_API_KEY"], "cite": "adapters/model/litellm_adapter.py"},
    {"group": "Model providers (B2 · ModelPort)", "id": "ollama", "name": "Ollama local models (via LiteLLM)",
     "seam": "ModelPort", "kind": "stub", "wired": False, "cite": "local runtime + pulled model; route via LiteLLM"},
    {"group": "Model providers (B2 · ModelPort)", "id": "janus", "name": "Janus (role TBD)",
     "seam": "ModelPort", "kind": "enterprise", "wired": False, "cite": "DR-05 · base-layers seam B2"},
    {"group": "Model providers (B2 · ModelPort)", "id": "model_router", "name": "AT&T Model Router",
     "seam": "ModelPort", "kind": "enterprise", "wired": False, "cite": "DR-08 · fronts the adapter"},

    # --- Detectors (Detector seam · C3 floor) ---
    {"group": "Detectors (Detector seam · C3 floor)", "id": "regex", "name": "Regex SSN / account / action",
     "seam": "Detector", "kind": "builtin", "wired": True, "cite": "adapters/detectors/regex_detectors.py"},
    {"group": "Detectors (Detector seam · C3 floor)", "id": "presidio", "name": "Presidio PII/CPNI (spaCy)",
     "seam": "Detector", "kind": "optional-pip", "wired": True, "extra": "pii",
     "modules": ["presidio_analyzer", "en_core_web_sm"], "cite": "adapters/detectors/presidio_detector.py"},
    {"group": "Detectors (Detector seam · C3 floor)", "id": "detoxify", "name": "Detoxify toxicity classifier",
     "seam": "Detector", "kind": "optional-pip", "wired": True, "extra": "toxicity", "modules": ["detoxify"],
     "cite": "adapters/detectors/detoxify_detector.py"},
    {"group": "Detectors (Detector seam · C3 floor)", "id": "llama_guard", "name": "Llama Guard safety classifier",
     "seam": "Detector/ModelPort", "kind": "stub", "wired": False, "cite": "safety classifier via a ModelPort"},
    {"group": "Detectors (Detector seam · C3 floor)", "id": "scanners", "name": "Quarantine scanners",
     "seam": "Finding", "kind": "enterprise", "wired": False, "cite": "DR-09 · security front door"},

    # --- Harness drivers (B3 · HarnessDriver) ---
    {"group": "Harness drivers (B3 · HarnessDriver)", "id": "builtin", "name": "Built-in scenario driver",
     "seam": "HarnessDriver", "kind": "builtin", "wired": True, "cite": "application/runner.py"},
    {"group": "Harness drivers (B3 · HarnessDriver)", "id": "agentic_overlay", "name": "Agentic overlay (adaptive)",
     "seam": "HarnessDriver", "kind": "stub", "wired": False, "cite": "DR-06 · adapters/drivers/overlay_driver.py"},
    {"group": "Harness drivers (B3 · HarnessDriver)", "id": "pyrit", "name": "Microsoft PyRIT",
     "seam": "HarnessDriver", "kind": "optional-pip", "wired": False, "extra": "redteam", "modules": ["pyrit"],
     "cite": "adapters/drivers/pyrit_driver.py (stub)"},
    {"group": "Harness drivers (B3 · HarnessDriver)", "id": "garak", "name": "NVIDIA Garak probes",
     "seam": "HarnessDriver", "kind": "optional-pip", "wired": False, "extra": "redteam", "modules": ["garak"],
     "cite": "driver seam (same pattern as PyRIT)"},
    {"group": "Harness drivers (B3 · HarnessDriver)", "id": "inspect_ai", "name": "Inspect AI eval substrate",
     "seam": "HarnessDriver", "kind": "optional-pip", "wired": False, "extra": "eval", "modules": ["inspect_ai"],
     "cite": "wrap Inspect tasks as a driver"},
    {"group": "Harness drivers (B3 · HarnessDriver)", "id": "nemo_guardrails", "name": "NVIDIA NeMo Guardrails",
     "seam": "HarnessDriver", "kind": "optional-pip", "wired": False, "extra": "guardrails", "modules": ["nemoguardrails"],
     "cite": "guardrail eval as a driver"},
    {"group": "Harness drivers (B3 · HarnessDriver)", "id": "promptfoo", "name": "Promptfoo (node)",
     "seam": "HarnessDriver", "kind": "stub", "wired": False, "cite": "npm i -g promptfoo; wrap as a driver"},

    # --- Evidence store (B4 · EvidencePort) ---
    {"group": "Evidence store (B4 · EvidencePort)", "id": "file", "name": "File store (content-hashed)",
     "seam": "EvidencePort", "kind": "builtin", "wired": True, "cite": "adapters/evidence/file_evidence.py"},
    {"group": "Evidence store (B4 · EvidencePort)", "id": "worm", "name": "S3 / WORM durable store",
     "seam": "EvidencePort", "kind": "enterprise", "wired": False, "cite": "Iter 4 · same port"},

    # --- Reporting & export ---
    {"group": "Reporting & export", "id": "html_dashboard", "name": "HTML dashboard (self-contained)",
     "seam": "reporting", "kind": "builtin", "wired": True, "cite": "interface/dashboard.py"},
    {"group": "Reporting & export", "id": "json_bundle", "name": "JSON result bundle (audit)",
     "seam": "reporting", "kind": "builtin", "wired": True, "cite": "run --out / result.json"},

    # --- Config & standards (B6) ---
    {"group": "Config & standards (B6)", "id": "yaml", "name": "YAML policy overrides",
     "seam": "config", "kind": "optional-pip", "wired": True, "extra": "config", "modules": ["yaml"],
     "cite": "adapters/config/loader.py"},
    {"group": "Config & standards (B6)", "id": "golden_controls", "name": "AT&T Golden Controls catalogue",
     "seam": "config/B0", "kind": "enterprise", "wired": False, "cite": "DR-07 · config/golden_controls.yaml"},
]

_STATUS = {"builtin": "available", "stub": "stub", "enterprise": "enterprise"}


def _installed(modules) -> bool:
    if isinstance(modules, str):
        modules = [modules]
    try:
        return all(importlib.util.find_spec(m) is not None for m in (modules or []))
    except (ImportError, ValueError):
        return False


def probe() -> List[dict]:
    """Resolve each catalogue entry against the current environment."""
    out = []
    for raw in CATALOGUE:
        c = dict(raw)
        kind = c["kind"]
        if kind == "optional-pip":
            inst = _installed(c.get("modules"))
            c["pkg_installed"] = inst
            if c.get("wired", True):
                c["status"] = "available" if inst else "installable"
            else:
                # package is a pip away, but the adapter is still a stub -> installable, not available
                c["status"] = "installable"
        else:
            c["status"] = _STATUS.get(kind, "unknown")
        # lab-runnable = anything not gated on an enterprise dependency
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
