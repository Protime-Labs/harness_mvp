# Correlation to the Original Architecture & Requirements

**Question:** how does the current framework (the real-runtime **truth notebook** + the design set) correlate to the **earliest checked-in** architecture and pictures?
**Baseline (git-verified):**
- **Original documents** — `enterprise_harness.md` (the detailed design + requirements), with `enterprise_harness_design.md`, `_mvp_plan.md`, `_build_plan.md` — all in the **first commit `137cae2` "Seed_MVP"**.
- **Original pictures** — `Enterprise_harness_platform_arch_v2.drawio` (`86c4d39`) and `Harness_vis1–4.jpg` (`94849a1`).
- **Current framework under review** — `enterprise_harness_truth_runtime_colab.ipynb` (+ the v3/catalogue/spec design docs).

---

## 1. Fidelity verdict

**Faithful to the original's *shape and invariants*, a deliberate *subset* of its *scope*, and *extended* on the one thing the original left implicit — proving the evaluation itself is true.**

- The original (`enterprise_harness.md`) specifies a **20-layer, provider-independent platform** that *discovers → validates → evaluates → gates → monitors*, split into a **control plane** (decisions) and **data plane** (execution/evidence).
- The truth notebook implements the **evaluate → gate → evidence core** (~10 of the 20 layers) with the control/data split intact, and **adds the assurance apparatus** (independence, quorum, calibration, stability) that the original *assumed* ("validates") but never specified.
- It does **not** implement the platform's breadth (discovery connectors, quarantine scanners, RBAC, event bus, runtime telemetry ingestion, and the pictures' Harness Studio / Model Router / front-door agents) — those remain design-only.

Legend: ✅ implemented · 🟡 partial / manual / stub · ⛔ gap (design-only, not built) · 🆕 added beyond the original.

---

## 2. Traceability — original 20 layers (`enterprise_harness.md §6`) → current

| Original layer | Current framework component | Status |
|---|---|---|
| 6.1 Discovery | `TARGET`/asset provided as input (Section 3); manual, no connectors | 🟡 |
| 6.2 Provenance & Lineage | evidence hashing captures asset + turns (Section 8); no lineage graph | 🟡 |
| 6.3 Quarantine & Security | — (design: W-B Security Agent) | ⛔ |
| 6.4 Provider-Agnostic Normalization | `invoke_model` normalizes provider I/O (Section 5); capability tags in catalogue | 🟡 |
| 6.5 Use Case Intake | `USE_CASE` input (Section 3) | ✅ |
| 6.6 Contextualization | `contextualize()` → risk tier (Section 12) | ✅ |
| 6.7 Harness Registry | `SCENARIOS` + catalogue as the source; no registry *service* | 🟡 |
| 6.8 Harness Selection & Policy | runs the provided scenario set; deterministic selection is design-only | 🟡 |
| 6.9 Evaluation Orchestration | `run_evaluation()` / `_harness_pass` (sequential) | ✅ LITE |
| 6.10 Harness Runner | the run chain honoring the run contract | ✅ |
| 6.11 Runtime Environment | process isolation; synthetic inputs; no sandbox/egress control | 🟡 |
| 6.12 Provider Adapter | `invoke_model` (anthropic/openai/litellm), role-based target/judge | ✅ |
| 6.13 Evidence Store | `EvidenceStore` + content-hash + Mode-A replay (Section 8) | ✅ |
| 6.14 Observability & Analytics | coverage/diversity + cost/latency/SLO + calibration + stability (Sections 9–11) | ✅ **extended** |
| 6.15 CI/CD Gate | `gate_decision` deterministic, fixed vocabulary (Section 12) | ✅ |
| 6.16 Remediation Automation | `recommendation` on each Finding; no ticketing/rollback | 🟡 |
| 6.17 Runtime Telemetry & Replay | Mode-A **replay** present (Section 8); production telemetry ingestion absent | 🟡 |
| 6.18 Governance & Audit | `audit_bundle` chain-of-custody (Section 13) | ✅ |
| 6.19 RBAC & IAM | — | ⛔ |
| 6.20 Event Bus | — | ⛔ |

**Coverage:** ~8 layers ✅, ~7 🟡, ~3 ⛔ — i.e. the **evaluate/gate/evidence/governance core is implemented**; the discovery/quarantine/IAM/eventing periphery is not.

---

## 3. Traceability — original 10-step end-to-end workflow → current run chain

Original spine (`enterprise_harness.md §4`): **Discover → Provenance → Quarantine → Normalize → Contextualize → Select → Orchestrate/Run → Evidence → Gate → Remediate.**

Truth-notebook chain (Section 14): *(asset input)* → **Contextualize → Run (adapter→target→judge quorum + detectors) → Findings → Calibrate/Stability → Gate → Evidence/Replay → Audit → Report.**

| Original step | In current chain? |
|---|---|
| Discover / Provenance / Quarantine / Normalize (steps 1–4) | 🟡/⛔ — asset supplied manually; no scanners |
| Contextualize (5) | ✅ |
| Select (6) | 🟡 — runs supplied scenarios |
| Orchestrate / Run (7) | ✅ (the core) |
| Evidence (8) | ✅ + replay |
| Gate (9) | ✅ deterministic |
| Remediate (10) | 🟡 — recommendation text only |

**The current chain is the original's *steps 5–9* implemented faithfully, with 1–4 as manual input and 10 as advisory.**

---

## 4. Traceability — control/data plane (`enterprise_harness.md §3`) → current

| Original plane | Owns | Current realization | Status |
|---|---|---|---|
| **Control plane** | decisions, policy, contextualization, gate, audit | `contextualize`, `gate_decision` (no LLM), `audit_bundle` | ✅ |
| **Data plane** | execution, model calls, evidence | `invoke_model`, judge quorum, detectors, `EvidenceStore` | ✅ |

The original's **architectural invariant** — "harnesses never make policy decisions; the control plane never calls a provider SDK directly" — holds exactly: the gate is deterministic (no model), and every model call is in the data-plane adapter.

---

## 5. Traceability — earliest pictures (`Harness_vis1–4` + `.drawio`) → current

| Picture zone | Current realization | Status |
|---|---|---|
| **vis1 Sources** (Hosted LLM / Anthropic / Bedrock / …) | `TARGET`/`JUDGE` provider+model inputs (Section 3) | ✅ |
| **vis1 Agents** (Source Agent, Security Agent, Gate) | Gate ✅ (deterministic); Source/Security agents ⛔ | 🟡 |
| **vis1 Platform Core** (Intake, Quarantine, Evaluation Lab, AT&T Context, Registry, Pack) | Intake ✅, Evaluation Lab ✅, AT&T Context 🟡 (USE_CASE+standards), Registry/Pack 🟡 (SCENARIOS), Quarantine ⛔ | 🟡 |
| **vis1 Customize — Harness Studio (UI+SDK)** | — | ⛔ |
| **vis1 Delivery+Runtime** (Model Router, Selector, CI/CD, Runtime, Evidence+Telemetry, Remediate) | Adapter≈Router ✅, CI/CD gate ✅, Evidence+cost ✅, Remediate 🟡, Selector 🟡 | 🟡 |
| **vis1 Unified Control Plane** (Identity, Golden Controls, Policy, Audit, HITL, Auto-stop) | Policy/Gate ✅, Audit ✅, HITL via `manual_review` 🟡, Golden Controls via standards 🟡, Identity/Auto-stop ⛔ | 🟡 |
| **vis2 E2E workflow** (Request→Source→Security→Studio→Sandbox Eval→Context+Registry→Deploy→Observe) | Sandbox-Eval + Context + Observe ✅; Source/Security/Studio ⛔ | 🟡 |
| **vis3/vis4 5-category harness catalogue** (Test/Exposure/Remediation/Resilience/Governance × 4) | the notebook is **category-agnostic** — it runs whatever `SCENARIOS`/`lenses` you supply; the catalogue is the reference for *what* to load | 🟡 (by design) |

---

## 6. What the current framework ADDS beyond the original (🆕) — and which requirement it fulfills

The original's Executive Summary demands the platform **"validates"** assets and preserves **"evidence"** — but `enterprise_harness.md` never specifies *how to make the evaluation itself trustworthy*. The truth notebook makes that explicit:

| Added control | Fulfills the original's implicit requirement… |
|---|---|
| **Independence** (judge ≠ target model) | credible "validation" (not self-grading) |
| **Judge quorum + neutral re-judge** | robust "validation" verdicts |
| **Deterministic detectors floor the judge** | evidence that is fact, not opinion |
| **Calibration** (P/R/F1 vs labeled data) | a *measured*, trustworthy evaluator |
| **Stability / Jaccard** | reproducible results (the point of "evidence") |
| **Mode-A replay + audit chain-of-custody** | the §6.13/§6.18 "chain of custody" made verifiable |
| **`evidence_basis = real`** | the original's "evidence" is genuine, not synthetic |

These are the concrete realization of the original's stated goal — *"discover, validate, evaluate, gate, preserve evidence"* — for the **validate/evaluate/evidence** portion.

---

## 7. Honest gaps — original required, current framework does not yet cover

- **Discovery connectors, deduplication, asset-key** (§6.1) — manual input only.
- **Quarantine scanners** (§6.3) — the "Security Agent" / "Secure" step in vis1/vis2.
- **RBAC/IAM** (§6.19) and **Event Bus** (§6.20).
- **Runtime telemetry ingestion + shadow eval** (§6.17) — only off-path replay exists.
- **Harness Studio, Model Router, Source/Security front-door agents** (pictures) — design-only.
- **Continuous monitoring** (Exec Summary "monitors") — the notebook is point-in-time.

These are exactly the layers the v2/v3 docs already mark `LITE`/`DEFER` — so the current framework is **consistent with the planned MVP scope**, not a silent divergence.

---

## 8. Verdict

The current framework is a **faithful, invariant-preserving implementation of the original architecture's evaluate/gate/evidence core** (control/data plane split intact, provider-independent, deterministic gate, hashed evidence), **scoped down** to that core rather than the full 20-layer platform, and **strengthened** with the assurance apparatus that turns the original's word *"validates"* into something measurable and true. Where it stops (discovery, quarantine, IAM, eventing, Studio, Model Router, continuous monitoring) matches the deferrals already recorded in the design set — so it correlates cleanly to the original as a **deliberate vertical slice**, not a drift.

*Reference: `enterprise_harness.md` §3/§4/§6 (original) · `Harness_vis1–4` + `.drawio` (original pictures) · `enterprise_harness_truth_runtime_colab.ipynb` (current).*
