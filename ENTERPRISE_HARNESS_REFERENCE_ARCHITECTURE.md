# Enterprise AI Assurance Harness — Reference Architecture

**Purpose.** Your personal build reference. It maps the established requirements (invariants,
base layers, workflows, backfill register) onto a **functional prototype** you can run today
(`harness/`), and gives the **build direction** to grow it to enterprise scale. Everything here
is implemented and proven: the code in `harness/` runs offline, blocks on a vulnerable target,
approves a hardened one, replays from evidence, and passes a 10-check invariant suite.

**How to use it.** Read §1–§3 for the mental model, §4–§8 for the architecture you build
*against*, §9–§10 for configuration and the staged build path, §11 for enterprise scale. Each
section cites the code module and the source doc so you can trace any decision.

**Status of the prototype (`harness/`):**

```
run:     vulnerable -> BLOCK (8 findings)   hardened -> APPROVE (0 findings)
verify:  10/10 invariants PASS              tests: 12 passed
replay:  Mode-A reproduces findings + gate from evidence alone (no model)
```

---

## 1. The mental model (read this first)

Two planes, one hard rule between them.

- **Data plane (agentic, non-deterministic).** Agents *generate* attacks and *judge* responses.
  LLMs live here. Output is evidence and opinions.
- **Control plane (deterministic policy).** Rules *decide*: risk tier, harness selection, the
  gate, budgets. **No LLM, no model call, ever.** Output is a decision you can defend in an audit.

> **Keystone invariant A1:** *Agents generate & judge (data plane); deterministic policy decides
> (control plane). No LLM in the gate/risk path.* Every other design choice serves this.

The whole platform is: **take an AI asset → run adversarial harnesses (data plane) → aggregate
their findings deterministically → emit one gate decision (control plane) → keep replayable
evidence for the audit.**

---

## 2. What "good" looks like (the properties the architecture buys you)

| Property | Why it matters | Where it's enforced |
|---|---|---|
| **Provider independence** (R2) | swap mock ↔ real ↔ Janus with no core change | `ports/model_port.py` |
| **Deterministic decisions** (A1/R9) | the gate is auditable, not a model's mood | `domain/gate.py` (no LLM) |
| **Evidence replay** (C4/R6) | reconstruct any verdict from stored evidence | `application/replay.py` |
| **Judge independence** (A4/BF-20) | the judge model ≠ the target model | `interface/factory.py` |
| **Detectors floor the judge** (C3) | hard signals beat soft opinions | `domain/aggregate.py` |
| **Fail closed** (A8) | a budget breach blocks, never silently passes | `application/runner.py` + gate |
| **Honest coverage** (evidence_basis) | "real" vs "simulated" is labeled per finding | `application/runner.py` |

If a change would break any of these, it's a **contract change** (needs sign-off), not a tweak.

---

## 3. Clean / hexagonal architecture

Dependencies point **inward**; the domain is pure. This is what makes the framework evolve by
*implementing a seam* instead of rewriting the core.

```
                       ┌─────────────────────────────────────────────┐
                       │  interface/  (composition root)              │
                       │  cli.py · factory.py · report.py             │
                       │  — the ONLY layer that imports adapters —    │
                       └───────────────┬─────────────────────────────┘
                                       │ wires concrete plugs into
                                       ▼
     ┌───────────────────────────────────────────────────────────────────┐
     │  application/   the workflows W0–W9                                 │
     │  orchestrator · contextualize · selection · runner · judge ·       │
     │  governance · replay · calibration · remediation · acceptance      │
     └───────────────┬───────────────────────────────┬───────────────────┘
             depends │                       depends  │
                     ▼                                ▼
        ┌────────────────────────┐        ┌───────────────────────────────┐
        │  domain/  (PURE)       │◄───────│  ports/  (the seams)          │
        │  contracts (B0)        │  used  │  ModelPort     (B2)           │
        │  invariants (B1)       │  by    │  EvidencePort  (B4)           │
        │  gate (B5) · risk      │        │  Detector                     │
        │  aggregate · patterns  │        │  HarnessDriver (B3)           │
        └────────────────────────┘        └───────────────┬───────────────┘
                                                implements │
                                                           ▼
                       ┌───────────────────────────────────────────────────┐
                       │  adapters/  (concrete plugs)                       │
                       │  model: mock · litellm                            │
                       │  detectors: regex · presidio                      │
                       │  evidence: file                                   │
                       │  drivers: builtin · overlay(stub) · pyrit(stub)   │
                       │  config: defaults · loader                        │
                       └───────────────────────────────────────────────────┘
```

**The rule, stated once:** `domain` imports only the standard library. `application` imports
`domain` + `ports` (never `adapters`). `adapters` implement `ports`. `interface` is the only
place concrete classes are chosen and wired. Break this and the guarantees in §2 leak.

---

## 4. Base layers B0–B6 → code

The base layers from `enterprise_harness_base_layers_and_accountability.md` are the stable
foundation. Here is exactly where each one lives in the prototype.

| # | Base layer | Module(s) | Seam it exposes |
|---|---|---|---|
| **B0** | Contracts & schemas | `domain/contracts.py` (Finding, TurnRecord, Verdict, GateDecision, RunConfig keys, `RESULT_SCHEMA`) | everything speaks these |
| **B1** | Plane boundary + invariants | `domain/invariants.py` + the purity of `domain/gate.py` | the rules every component obeys |
| **B2** | Model-I/O adapter | `ports/model_port.py` ← `adapters/model/*` | **Janus, providers, Model Router** |
| **B3** | Harness runner + run contract | `ports/driver_port.py` ← `application/runner.py` (`BuiltinDriver`) | **agentic overlay, PyRIT/Garak** |
| **B4** | Evidence store + replay | `ports/evidence_port.py` ← `adapters/evidence/file_evidence.py`; `application/replay.py` | audit, remediation, SIEM |
| **B5** | Deterministic gate | `domain/gate.py` | CI/CD, deployment |
| **B6** | Policy/config | `config/*.yaml` + `adapters/config/{defaults,loader}.py` | domain owners tune here |

**Rule of the base:** a B0/B1 change is a versioned contract change; a component change is
*filling a seam* (B2–B5) or *tuning config* (B6). That is what lets you integrate Janus and the
agentic overlay later without touching the core.

---

## 5. The seams — interface specs + how to fill them

This is the heart of "a framework that evolves and integrates with the other components." Each
seam is a Protocol in `ports/`; you satisfy it and wire it in `interface/factory.py`.

### 5.1 B2 — `ModelPort` (model I/O) — where Janus / providers / Model Router plug in
```python
class ModelPort(Protocol):
    name: str
    def invoke(self, role, prompt, system="", **kw) -> dict:
        # returns {"text": str, "tokens": {"in","out"}, "cost_usd": float, "model": {...}}
```
- **Ships:** `MockAdapter` (offline), `LiteLLMAdapter` (100+ real providers).
- **To integrate Janus:** implement `ModelPort` over Janus's API (or wrap it behind LiteLLM if
  it's OpenAI-compatible). Emit provenance in `model` for evidence. Nothing else changes.
- **To integrate the AT&T Model Router:** put it *in front* of the adapter (route → provider);
  still one `invoke` path. Judge independence (A4) is enforced separately in the factory.

### 5.2 B3 — `HarnessDriver` (run contract) — where the agentic overlay / PyRIT plug in
```python
class HarnessDriver(Protocol):
    name: str
    def run(self, spec, adapter, store, cfg) -> (result, turns, verdicts, manifest, findings)
```
- **Ships:** `BuiltinDriver` — iterates a fixed scenario set, quorum-judges, detector-floors.
- **Agentic overlay** (`adapters/drivers/overlay_driver.py`, stub): runs an *attacker agent* that
  reads the transcript and generates adaptive multi-turn attacks — but returns the **same
  5-tuple**, so the gate and quorum are unchanged.
- **PyRIT/Garak** (`adapters/drivers/pyrit_driver.py`, stub): wrap the engine's prompts through
  *our* `ModelPort` (keeps provider-independence + evidence), map its scores to canonical
  `Finding`s. One driver per engine; the orchestrator treats them identically.

### 5.3 `Detector` (deterministic floor) — where Presidio / scanners plug in
```python
Detector = Callable[[str], tuple[Optional[str], Optional[str]]]   # (severity|None, span|None)
```
- **Ships:** regex SSN/account/action detectors (real content analysis, C3 floor).
- **Presidio** (`adapters/detectors/presidio_detector.py`): same signature, entity-level PII +
  a CPNI recognizer. Toggle with `USE_PRESIDIO: true`; degrades to regex if not installed.
- **External scanners:** emit the canonical `Finding` directly (coarser, at the B0 layer).

### 5.4 B4 — `EvidencePort` (chain of custody) — where audit / SIEM read
```python
class EvidencePort(Protocol):
    root: str
    def capture_turn(...) -> dict     # content-hashed turn record
    def capture_verdict(...) -> dict
    def read(uri) -> str              # re-read for replay + hash re-verify
```
- **Ships:** `FileEvidenceStore`. **Enterprise:** swap for S3/WORM or an append-only DB behind
  the same port; Mode-A replay and the gate don't notice.

### 5.5 B6 — configuration (the tuning surface)
The `config/*.yaml` files override baked-in defaults when PyYAML is installed. This is the whole
"how do I provide a value" mechanism: **edit the owned YAML, no code change.** (§9.)

---

## 6. The workflows W0–W9 → code

Faithful to `enterprise_harness_agentic_workflows.md`. The prototype implements the Foundational
core; the rest are seams.

| Workflow | Role | Module | Plane |
|---|---|---|---|
| **W0** Orchestration | run the whole chain | `application/orchestrator.py` | control |
| **W1** Contextualization | use case → risk tier → pack | `application/contextualize.py` + `domain/risk.py` | control |
| **W2** Selection | pack → plan + skip rationale | `application/selection.py` | control |
| **W3** Harness run | attacker → target → judge | `application/runner.py` (B3) | data |
| **W7** Judge quorum | N isolated diverse judges | `application/judge.py` | data |
| **W8** Gate | one deterministic decision | `domain/gate.py` (B5) | control |
| **W9** Remediation | findings → prioritized advice | `application/remediation.py` | data (advisory) |
| **H5.1** Governance | verify the other findings | `application/governance.py` | control-verify |
| **W-A/W-B** Source/Security agents | onboarding, quarantine front door | *seam* (`Finding` schema) | data |
| **W-C** Harness challenge (bake-off) | onboard/compare a candidate harness | *seam* (`HarnessDriver`) | data |

Supporting: **calibration** (`application/calibration.py`, C1), **replay** (`application/replay.py`,
C4), **acceptance** (`application/acceptance.py`, the invariant CI gate).

---

## 7. The invariants (the constitution) — and how each is proved

`domain/invariants.py` holds the statements; `harness verify` proves them on a live run.

| ID | Guarantee | Proof (acceptance check) |
|---|---|---|
| **A1** | no LLM in the gate | banned tokens absent from `gate_decision.__code__` |
| **R2/A2** | one model path | all calls go through `ModelPort` (structural) |
| **A4** | isolated + independent judge | tool-less judge; factory enforces judge≠target |
| **A5** | quorum of N | every candidate has exactly `QUORUM_N` verdicts |
| **C3** | detectors floor the judge | SSN + CPNI criticals present despite judge votes |
| **A7** | determinism | full re-run yields identical findings |
| **A8** | fail closed | `max_turns=1` → `budget_exceeded` → gate `block` |
| **C4** | evidence replay | replay reproduces findings + gate, hashes match |
| **A9/C1** | calibrated judges | P/R/A vs ground truth ≥ thresholds → gate-eligible |
| **R9** | valid decision | gate ∈ {approve, warn, block, manual_review} |

**These are your regression gate.** Wire `harness verify` into CI; a red check means a base-layer
guarantee broke.

---

## 8. The run contract (the swap seam schema)

The stable interface between planes: a harness consumes config, emits a `result.json`-shaped dict
+ hashed evidence. Swapping the driver/provider changes *how* the result is produced, never its
shape. (BF-01/BF-02.)

**Input** — the run config keys (`config/*.yaml` → `cfg`): `SEED`, `PROVIDER_MODE`,
`QUORUM_N`, `FAIL_ON_SEVERITY`, `BUDGET`, `JUDGE_THRESHOLDS`, `PHASE1_ATTACK`.

**Output** — `result` per harness:
```json
{
  "$schema": "harness/result/v1",
  "harness": "H2.3", "harness_run_id": "HR-H2.3", "status": "completed",
  "score": 0.33, "decision": "block",
  "metrics": {"scenarios": 3, "findings": 2, "success_rate": 0.67},
  "findings": [ { "id": "F-H2.3-1", "severity": "critical", "category": "data_leakage.cpni",
                  "blocking": true, "evidence_uri": "…", "basis": "detector(real-content)",
                  "standards": {"owasp_llm": ["LLM02","LLM08"]} } ],
  "evidence_basis": "simulated (offline: content detectors REAL; semantic verdicts simulated)",
  "determinism": {"seed": 42, "quorum": {"min_judges": 3, "rule": "majority"},
                  "determinism_class": "deterministic", "budget": {"status": "within"}}
}
```

**Finding** (the one canonical schema, `domain/contracts.py::Finding`): `id · source · severity ·
category · title · description · blocking · policy_rule · evidence_uri · recommendation · harness
· standards · basis`. Every harness, judge, and scanner emits exactly this.

---

## 9. Configuration model (B6) — what to tune, who owns it

Resolution order (last wins): **Python defaults → `config/*.yaml` → CLI flags.** The harness runs
with zero config; YAML is the enterprise tuning surface.

| File | Tunes | Class | Owner |
|---|---|---|---|
| `config/risk_weights.yaml` | risk weights + tier cutoffs + pack | 🟨 PROVISIONAL (BF-10) | governance/risk |
| `config/quorum.yaml` | quorum N, calibration thresholds, target/judge models | 🟨 PROVISIONAL (BF-11) | eval |
| `config/budgets.yaml` | budget ceilings, seed, harness set, profile | 🟨 PROVISIONAL (BF-12) | platform |
| `config/harnesses.yaml` | scenario sets (add/override) | 🟨 PROVISIONAL (BF-13) | red-team |
| `config/golden_controls.yaml` | control catalogue mapping | 🟦 PLACEHOLDER (BF-17) | AT&T governance |

**The provisioning pattern:** a value ships as a working *default* so build proceeds today; the
**named owner's sign-off** (edit the YAML + record it in the decision register) is what makes it
real. That is how you hold accountability without knowing every answer up front.

---

## 10. Build direction — the staged path (dependency-gated)

Grow the prototype by **filling seams**, each stage gated by an acceptance test before the next.
This is the ladder that survives the reality that on-prem infra isn't verifiable yet.

| Stage | Goal | What you do | Acceptance gate (must pass before next) |
|---|---|---|---|
| **Iter 0 — offline** ✅ *done* | prove the shape | run `harness verify` on the mock | 10/10 invariants PASS; BLOCK on vulnerable, APPROVE on hardened |
| **Iter 1 — real model** | one real provider | `--provider litellm`, target=Haiku, judge=Sonnet; keys from env | judge independence enforced; findings carry `basis: llm-judge(real)`; calibration meaningful on a labeled GT set |
| **Iter 2 — real detector** | real PII/CPNI | `USE_PRESIDIO: true` + CPNI recognizer | Presidio flags SSN/CPNI; regex parity or better; no benign false-positive regressions |
| **Iter 3 — real driver** | adaptive attacks | implement `AgenticOverlayDriver` or `PyritDriver` against the B3 contract | same run-contract output; gate unchanged; evidence captured per turn |
| **Iter 4 — real evidence** | durable custody | swap `FileEvidenceStore` → S3/WORM behind `EvidencePort` | Mode-A replay still passes; hashes verify |
| **Iter 5 — real controls** | AT&T governance | fill `golden_controls.yaml` with real IDs+text; map to categories | every finding carries a real control ID; CPNI rules applied |
| **Iter 6 — integration** | Janus / Model Router | implement `ModelPort` over each; route in the factory | provider-independence holds; no core change; invariants still green |

**Gate discipline:** each iteration must keep `harness verify` green. The invariant suite is the
contract that lets you change everything underneath without regressing the guarantees.

---

## 11. Enterprise scale — how each layer grows

| Concern | MVP prototype | Enterprise-scale build |
|---|---|---|
| **Providers** | mock, LiteLLM | LiteLLM/Model-Router gateway; per-provider rate limits, retries, cost caps |
| **Concurrency** | in-process, per-harness | queue + workers; one harness-run per task; budgets per run |
| **Evidence** | file, temp dir | S3/WORM or append-only DB; retention + legal hold; SIEM export |
| **Config** | YAML files | config service / GitOps; per-tenant policy; signed policy versions |
| **Registry** | Python dict + YAML | registry service; harness packs (Foundational/Advanced/AT&T-Context); W-C bake-off to onboard |
| **Judges** | quorum of 3 | diverse-model quorum; per-domain rubrics; drift monitoring on calibration |
| **Gate** | in-process function | same pure function, invoked as a service; policy-as-code with version pinning |
| **Standards** | OWASP tags | OWASP-LLM + MITRE ATLAS + NIST AI RMF + ISO 42001 + AT&T Golden Controls mapping |
| **Frontier vendors** | (seams) | Cisco AI Defense *orchestrate-above*; NVIDIA Garak/NeMo, MS PyRIT, Anthropic Petri as **drivers**; Inspect AI as an eval substrate |

**Frontier vendor integration principle:** vendors plug in at the **driver seam (B3)** or the
**detector seam**, never above the gate. You keep *best-of-each* (PyRIT's attack orchestration,
Garak's probes, Presidio's PII, Inspect's harness ergonomics) while the deterministic gate and
canonical evidence remain yours. The bake-off (W-C) is how you decide which driver wins per
capability — a feature-fit comparison, not a product lock-in.

---

## 12. Directory map + commands

```
harness/                       the functional prototype (this is what you build against)
  src/harness/{domain,ports,application,adapters,registry,interface}/
  config/*.yaml                B6 tuning surface
  tests/                       gate · e2e-mock · invariants
  examples/run_mock.py
  README.md                    quickstart + layout

# run
PYTHONPATH=src python -m harness run       # assurance chain (report)
PYTHONPATH=src python -m harness verify     # + invariant acceptance suite (CI gate)
PYTHONPATH=src python -m harness info       # config sources, invariants, registry
python -m pytest -q                         # 12 tests
```

---

## 13. Traceability to the corpus

| This document | Established requirement |
|---|---|
| Planes + A1 | `enterprise_harness_architecture_v3.md` (A1–A10), keystone invariant |
| Base layers B0–B6 | `enterprise_harness_base_layers_and_accountability.md` |
| Seams / not-yet-built | same, §2 (Janus, overlay, router, scanners, Golden Controls) |
| Workflows W0–W9, W-A/B/C | `enterprise_harness_agentic_workflows.md` |
| Backfill classes BF-## | `enterprise_harness_v1_backfill_register.md` |
| Invariants R#/A#/C# | `enterprise_harness_design.md`, `..._spec_addendum_C1-C6.md` |
| Harness catalogue + packs | `enterprise_harness_catalogue.md` |
| Operable proof | `enterprise_harness_mvp_colab.ipynb` (this code is its clean-architecture form) |
| Frontier vendor map | `enterprise_harness_phase2_frontier_frameworks.md` |
| Reference diagrams | `Enterprise_harness_v1_reference_architecture.drawio` |

**One-line summary.** The prototype is the notebook's proof, refactored into clean architecture
so it can *grow*: the domain is pure and invariant-guarded, the seams are explicit, and every
not-yet-built component (Janus, the agentic overlay, the Model Router, real scanners, Golden
Controls) has a defined interface to build against and a stub to run until it arrives.
