# Enterprise AI Assurance Harness — functional MVP prototype

A **provider-independent, evidence-replayable AI assurance harness** built on clean/hexagonal
architecture. It runs adversarial harnesses against an AI asset (agent/model), judges the
results with an independent quorum, and produces **one deterministic gate decision**
(`approve | warn | block | manual_review`) — with **no LLM anywhere in the decision path**.

It runs **offline on the standard library alone** (mock provider, no keys, no network) and
swaps to real models (LiteLLM), real PII detection (Presidio), and external red-team engines
(PyRIT/Garak) by **filling a seam** — never by rewriting the core.

> This package is the code companion to `../ENTERPRISE_HARNESS_REFERENCE_ARCHITECTURE.md`
> (the reference architecture) and the operable proof `../enterprise_harness_mvp_colab.ipynb`.

---

## Quickstart (zero installs)

```bash
cd harness

# 1) run the assurance chain against the mock target (offline, deterministic)
PYTHONPATH=src python -m harness run

# 2) run + the invariant acceptance suite (the platform's own CI gate)
PYTHONPATH=src python -m harness verify

# 3) inspect config resolution, invariants, and the harness registry
PYTHONPATH=src python -m harness info

# 4) build a self-contained HTML dashboard and open/serve it locally
PYTHONPATH=src python -m harness dashboard --open                         # fresh mock run -> open
PYTHONPATH=src python -m harness dashboard --serve 8000                   # serve on localhost + open
PYTHONPATH=src python -m harness dashboard --in a.json --in b.json        # compare saved bundles
PYTHONPATH=src python -m harness run --provider litellm --html dash.html --open

# 5) inventory every plugin/dependency and what the LAB can run
PYTHONPATH=src python -m harness plugins

# programmatic use
python examples/run_mock.py

# tests
python -m pytest -q
```

Expected: the **vulnerable** mock profile yields 8 findings and gate **BLOCK**; the
**hardened** profile (`--profile hardened`) yields 0 findings and **APPROVE**; Mode-A replay
reproduces both from evidence alone; the 10-check invariant suite is **ALL PASS**.

Install as a package (optional):

```bash
pip install -e .                 # core (stdlib only)
pip install -e ".[all]"          # + litellm, presidio, pyyaml, pytest
harness verify                   # console-script entry point
```

---

## Architecture (clean / hexagonal)

Dependencies point **inward**. The domain knows nothing about models, files, or frameworks.

```
 interface/  ── composition root (CLI, factory) ── wires adapters into the application
      │
      ▼
 application/ ── the workflows W0–W9 (orchestrate, run, judge, govern, replay, calibrate)
      │  depends on ▼            ▲ implements
   domain/ ◄────────────────── ports/ ◄──────────── adapters/
   B0 contracts, B1 invariants,  the seams:          concrete plugs:
   B5 gate, risk, aggregate      ModelPort (B2)      mock / LiteLLM
   (PURE — stdlib only)          EvidencePort (B4)   regex / Presidio
                                 Detector            file evidence
                                 HarnessDriver (B3)  builtin / overlay / pyrit
```

| Layer | Package | Contains | May import |
|---|---|---|---|
| **Domain** | `harness.domain` | contracts (B0), invariants (B1), gate (B5), risk, aggregate, patterns | stdlib only |
| **Ports** | `harness.ports` | `ModelPort`, `EvidencePort`, `Detector`, `HarnessDriver` | domain |
| **Application** | `harness.application` | orchestrator (W0), contextualize (W1), selection (W2), runner (B3/W3), judge (W7), governance (H5.1), replay, calibration, remediation (W9), acceptance | domain, ports |
| **Adapters** | `harness.adapters` | mock/LiteLLM models, regex/Presidio detectors, file evidence, drivers, config | domain, ports |
| **Registry** | `harness.registry` | harness specs + implementation status | domain |
| **Interface** | `harness.interface` | CLI, factory (composition root), report | everything |

The dependency rule is enforced in code: the gate (`domain/gate.py`) imports nothing that can
reach a model, and the acceptance suite proves it (`A1 no-LLM in gate`).

---

## The seams (how it evolves without rework)

| Seam | Port | Ships | Plug in later |
|---|---|---|---|
| **B2 model I/O** | `ports/model_port.py` | `MockAdapter` | `LiteLLMAdapter`, **Janus**, AT&T **Model Router** |
| **B4 evidence** | `ports/evidence_port.py` | `FileEvidenceStore` | S3/WORM, append-only DB, SIEM export |
| **Detector** | `ports/detector_port.py` | regex SSN/acct/action | **Presidio** (+CPNI recognizer), scanners |
| **B3 run contract** | `ports/driver_port.py` | `BuiltinDriver` (scenarios) | **agentic overlay**, **PyRIT**, Garak, Promptfoo |
| **B6 config** | `config/*.yaml` | baked defaults | owner-tuned YAML (risk, quorum, budgets, controls) |

Every not-yet-built component (Janus, the agentic overlay, the Model Router) becomes a **seam
implementation**, not an architecture change. The unbuilt drivers raise a clear
`NotImplementedError` documenting the exact contract to satisfy (`adapters/drivers/*`).

---

## Swapping in a real provider (LiteLLM + independent judge)

```bash
pip install litellm
export ANTHROPIC_API_KEY=...        # never commit a key
# target = Haiku, judge = Sonnet  (judge independence A4/BF-20 is enforced)
PYTHONPATH=src python -m harness run --provider litellm
```

Set the target/judge models in `config/quorum.yaml`. The harness code does not change —
only the adapter behind `ModelPort`. If `JUDGE_MODEL == LITELLM_MODEL`, the factory refuses to
run (judge independence violated).

---

## Dashboard & lab capabilities

`harness dashboard` renders a **self-contained HTML** view (no server, no network, no build
step): the gate verdict as a **PASS / WARN / FAIL** badge, the **inputs** that produced it
(use case + run config), per-harness **signals**, findings feedback, calibration meters, and a
**Plugins & dependencies** panel. Double-click the file, `--open` it, or `--serve` it. A
"Load bundle…" control reads any local `result.json` with the browser FileReader, so you can
drop in your own runs — built for testing and experimentation.

The **plugin inventory** is the lab-vs-enterprise model made explicit. `harness plugins` (and the
dashboard panel) classify every seam implementation:

| Status | Meaning | Examples |
|---|---|---|
| **available** | runs now (built-in, or a wired package that is installed) | mock, LiteLLM, regex, **Presidio**, **Detoxify**, **Inspect AI**, file evidence, YAML, HTML dashboard, JSON bundle |
| **installable** | a local `pip install` away (adapter may still be a stub) | PyRIT/Garak `.[redteam]`, NeMo Guardrails `.[guardrails]` |
| **stub** | seam defined, buildable in the lab | agentic overlay, Ollama, Llama Guard, Promptfoo |
| **enterprise** | needs an enterprise dependency **not wired** into the lab | Janus, Model Router, Golden Controls, WORM store |

Real plugins wire in behind their seams and degrade gracefully if absent:
- **Detectors** — `--presidio` (PII/CPNI, augments the regex floor), `--detoxify` (toxicity floor for H1.3).
- **Drivers (B3)** — `--driver {builtin,overlay,inspect,pyrit,nemo,garak}`. Each honors the same run
  contract, so the gate is unchanged:
  - `builtin` — the scenario driver (reference; the invariant suite is pinned to it).
  - `overlay` — **agentic overlay**: adaptive, multi-turn escalation; finds issues the single-shot
    pass misses (e.g. 11 findings vs 8 on the mock). No external dep.
  - `inspect` — **Inspect AI** owns the dataset + generation loop via a `ModelPort` bridge.
  - `pyrit` — **Microsoft PyRIT**'s target pipeline drives the send via a bridged `PromptChatTarget`.
  - `nemo` / `garak` — real adapters that are **model-bound** (NeMo needs a live LLM; Garak a served
    target), so they stay `installable` and raise an actionable error offline rather than fake a run.

  `inspect`, `pyrit`, and `builtin` all yield the **same** gate (BLOCK, 8 findings, replay PASS) on
  the mock — different engines, one decision. That is the point of the B3 seam.

**lab-runnable = available | installable | stub.** The enterprise dependencies stay stubbed and
clearly separated — a realistic environment you can experiment in without touching production
systems. Anything installable becomes available the moment you `pip install` its extra; anything
enterprise becomes available the moment its adapter implements the seam it already has.

---

## What each invariant guarantees (proved by `harness verify`)

`R9` valid gate vocabulary · `A1` no LLM in the gate · `A5` full judge quorum ·
`C3` deterministic detectors floor the judge · `A8` budgets fail closed ·
`C4` Mode-A replay reproduces findings + gate from evidence · `A7` deterministic re-run ·
`H5.1` every finding is lifecycle-complete · Foundational pack selected · block-on-critical.

See `harness.domain.invariants` for the full statements and citations.

---

## Layout

```
harness/
├── pyproject.toml            packaging + optional extras (providers/pii/config/redteam)
├── conftest.py               makes src/ importable for tests
├── config/                   B6 — externalized policy (YAML overrides the baked defaults)
│   ├── risk_weights.yaml     BF-10 risk model         (owner: governance/risk)
│   ├── quorum.yaml           BF-11 quorum+calibration (owner: eval)
│   ├── budgets.yaml          BF-12 budgets+determinism(owner: platform)
│   ├── harnesses.yaml        BF-13 scenario override  (owner: red-team)
│   └── golden_controls.yaml  BF-17 controls PLACEHOLDER(owner: AT&T governance)
├── examples/run_mock.py      minimal programmatic run
├── src/harness/
│   ├── domain/               B0/B1/B5 + risk + aggregate + patterns  (PURE)
│   ├── ports/                the four seams
│   ├── application/          W0–W9 + acceptance
│   ├── adapters/             model / detectors / evidence / drivers / config
│   ├── registry/             harness specs + status
│   └── interface/            cli + factory + report
└── tests/                    gate, e2e-mock, invariants (12 tests)
```
