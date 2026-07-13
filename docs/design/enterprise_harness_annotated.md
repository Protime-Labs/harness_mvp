# Enterprise AI Harness Platform MVP — Detailed Design (Annotated Reference-Architecture Baseline)

> **This is a faithful recreation of the original `enterprise_harness.md`, with every area in question or gap marked up** to seed the reference architecture. Structure and section numbering follow the original; callouts are added, nothing removed.
> **Companion diagram:** `Enterprise_harness_annotated_reference.drawio` (annotated vis1–4).
> **Markup legend:** ✅ **ANSWERED in v1** (backfilled — cites BF-## / NB §) · 🟨 **PROVISIONAL** (example value, tune) · 🔶 **EXTERNAL/AT&T INPUT** needed · ⛔ **GAP / NOT BUILT** (design-only) · ❓ **OPEN QUESTION**. Gap IDs `G#` = `enterprise_harness_design.md §7`; backfill IDs `BF-##` = `enterprise_harness_v1_backfill_register.md`.

## Table of Contents
1. Executive Summary · 2. Architecture Overview · 3. Control Plane and Data Plane · 4. End-to-End Workflow · 5. Core Data Model · 6. Layer-by-Layer Detailed Design (6.1–6.20) · 7. Runtime Telemetry and Replay · 8. MVP Build Plan

---

## 1. Executive Summary
A **provider-independent Enterprise AI Harness Platform** that continuously discovers, validates, evaluates, gates, and monitors AI models, agents, prompts, RAG systems, tools, MCP servers, datasets, deployment manifests, and runtime endpoints. It separates policy/orchestration (**control plane**) from execution/telemetry/evidence (**data plane**).

> ⛔ **GAP — "validates" is undefined.** The summary asserts the platform "validates" and preserves "evidence" but never specifies *how the evaluation itself is trustworthy*. ✅ **ANSWERED in v1:** judge independence (BF-20), quorum + detector-floor (BF-05, NB §7), calibration (BF-11, NB §15), `evidence_basis` (BF-21).
> ❓ **OPEN QUESTION — "monitors" (continuous) vs "no production coupling."** These two requirements conflict; the MVP resolves point-in-time only (runtime telemetry ingestion ⛔, §6.17).

## 2. Architecture Overview
Four zones: enterprise **sources** → **control plane** (decides) → **data plane** (executes) → enterprise **outputs**. (See annotated **vis1**.)

> 🔶 **AT&T INPUT — Sources.** `Prisma AIRS`, `Janus / Agentic`, `Internal AIRS` are drawn (vis1) but never defined in the doc — role (source vs scanner vs router) is unknown.

## 3. Control Plane and Data Plane
| Plane | Owns | Examples |
|---|---|---|
| **Control** | state, policy, metadata, orchestration, approvals, audit | Control-Plane API, policy engine, harness registry, orchestrator, RBAC/IAM |
| **Data** | execution, scanning, evaluation, traces, evidence | scanner/harness containers, provider adapters, fault injection, evidence store |

**Invariant:** harnesses (data plane) never make policy decisions; the control plane never calls a provider SDK directly.

> ✅ **ANSWERED in v1 — the invariant holds exactly** ("agents generate & judge; deterministic policy decides", A1): gate = NB §11 (no LLM); all model calls = adapter NB §3/§20. This is the vis2 «Fixed gates vs Agentic loops» principle realized.

## 4. End-to-End Workflow (10 steps)
Discover → Provenance → Quarantine → Normalize → Contextualize → Select → Orchestrate/Run → Evidence → Gate → Remediate. (See annotated **vis2**.)

> ⛔ **GAP — steps 1–4 front door.** Discovery connectors, Quarantine/Security scanners, Normalization are design-only in v1 (⛔). Steps 5–9 are built.
> ❓ **OPEN QUESTION — ordering.** The Provider Adapter is numbered 12th (§6.12) but is a step-7 dependency; build it with the runner.

## 5. Core Data Model
> ⛔ **GAP (internal defect) — this section is an empty figure reference in the original.** ✅ **ANSWERED:** entity model made explicit in `enterprise_harness_design.md §4`; the operative subset (Finding, result, evidence, gate) is implemented in NB §2.

---

## 6. Layer-by-Layer Detailed Design

### 6.1 Discovery
**Objective:** find/register AI assets; classify type; dedupe across code/CI/K8s/runtime; version on hash change; attach early risk hints.
**APIs:** `POST /discovery/sources`, `POST /discovery/runs`, `GET /assets`, `POST /discovery/events`. **Events:** `asset.discovered`, `asset.version.created`.
> ⛔ **GAP — connectors not built** (GitHub/K8s/registry/webhook). v1 uses **manual asset input** (NB §13 `use_case`/asset). 🔶 **AT&T INPUT** for connector targets.
> 🟨 **PROVISIONAL — asset-key (G7):** "canonical keys" defined as `hash(type + identity-fields)` in the addendum, not yet in v1.

### 6.2 Provenance & Lineage
**Objective:** immutable per-version record (source, commit, hash, owner, SBOM/license); parent/child lineage; blast-radius query.
**APIs:** `POST /provenance/records`, `GET /provenance/assets/{id}/lineage`.
> 🟨 **PARTIAL — hashing yes, lineage no.** v1 hashes turns/evidence (BF-06, NB §4) but has no lineage graph / blast-radius.

### 6.3 Quarantine & Security
**Objective:** block unsafe assets before harness execution; static + AI-specific scanners; normalize to a common finding schema; decide `allow/allow_with_warning/block/require_manual_review`.
**APIs:** `POST /quarantine/jobs`, `GET /quarantine/jobs/{id}/decision`.
> ⛔ **GAP — scanners not built** (SBOM/secrets/malware/license/policy/sandbox = vis1 «Security Agent», vis2 «Secure»). Design-only (W-B).
> ❓ **OPEN QUESTION — static prompt-injection scanning is a semantic problem;** a regex scanner has high false-negatives. v1 moves injection assurance to the behavioral harness (H2.1, NB §5).

### 6.4 Provider-Agnostic Normalization
**Objective:** map provider capabilities to normalized features (supports_tools/vision/streaming/structured_output, context window, region, cost/latency/risk class).
**APIs:** `POST /normalization/models`, `GET /adapters/providers/{provider}/features`.
> 🟨 **PARTIAL / G8 — capability vocabulary open-ended.** v1 carries `capability_tags` on each harness (NB §5) using the closed 15-tag enum (addendum C7), but no dynamic probing.

### 6.5 Use Case Intake
**Objective:** capture owner, business unit, purpose, assets, data classes, users, criticality, exposure, regulatory domain, controls.
**APIs:** `POST /use-cases`, `POST /use-cases/{id}/submit`.
> ✅ **ANSWERED in v1** — `USE_CASE` intake with data classes incl. **CPNI** (NB §13, §9).

### 6.6 Contextualization
**Objective:** use case → risk tier, required controls, required harnesses, required approvals; transparent weighted score.
**APIs:** `POST /contextualization/evaluate`.
> ⛔ **GAP (G3) — "transparent weighted score" with no weights.** ✅ **ANSWERED / 🟨 PROVISIONAL:** `RISK_WEIGHTS` + tier cutoffs (BF-10, NB §9) — tune with governance owner.

### 6.7 Harness Registry
**Objective:** catalog of approved, versioned, swappable harnesses; input/output schema URIs; blocking capability; approval history.
**APIs:** `POST /harnesses`, `POST /harnesses/{id}/approve`.
> 🟨 **PARTIAL (G6) — schema URIs are placeholders.** v1 = `REGISTRY` dict + Foundational pack (BF-19, NB §10/§9); no registry service, Advanced/AT&T-Context packs ⛔ 🔶.

### 6.8 Harness Selection & Policy
**Objective:** deterministic, explainable execution plan (required/optional/blocking) with **skip rationale**.
**APIs:** `POST /harness-selection/plans`, `GET .../{id}/explain`.
> ✅ **ANSWERED in v1** — `select()` with skip reasons (BF-07, NB §10).

### 6.9 Evaluation Orchestration
**Objective:** run approved plans; provisioning, ordering, retries, aggregation; survive restarts; apply final policy.
> ⛔ **OVER-SCOPED — original prescribes Temporal/Argo as MVP.** ✅ **ANSWERED:** v1 = sequential in-process runner (NB §13); Temporal deferred.

### 6.10 Harness Runner
**Objective:** execute a harness against a target via the **standard run contract** (`/input/run_config.json` → `/output/result.json` + evidence).
> ⛔ **GAP (G1) — the contract is named but never defined. HIGHEST PRIORITY.** ✅ **ANSWERED in v1** — concrete `result.json` + run flow (BF-01, NB §2/§8).

### 6.11 Runtime Environment
**Objective:** isolated, ephemeral execution; no prod secrets; synthetic data; restricted egress; quotas; teardown; fault injection.
> ⛔ **OVER-SCOPED — original prescribes K8s namespaces as MVP.** ✅ **ANSWERED:** v1 = process isolation + synthetic-only + deny-egress posture (BF-22, NB §0); Docker/K8s deferred.

### 6.12 Provider Adapter
**Objective:** hide provider API differences behind a normalized `ModelRequest`/`ToolRequest` → common `ModelResponse`.
> ✅ **ANSWERED in v1** — one `invoke(role,prompt,system)` path, mock + LiteLLM (BF-08, NB §3/§20). 🔶 **AT&T INPUT — «Model Router»** (vis1) is a distinct AT&T-owned concern, not the adapter.

### 6.13 Evidence Store
**Objective:** persist prompts, responses, tool calls, findings, metrics, reports; small metadata in DB, artifacts in object store; retention by data class; encryption/redaction.
> ⛔ **GAP (G2) — Finding schema inconsistent (§6.3 vs §6.13).** ✅ **ANSWERED:** single `Finding` (BF-02, NB §2) + hashed evidence + **Mode-A replay** (BF-06, NB §4/§16).
> ⛔ **GAP (G9) — retention/redaction unspecified.** 🔶 partly addressed (redaction noted); retention matrix pending.

### 6.14 Observability & Analytics
**Objective:** pass/fail, risk, regression, latency/cost, PII-leak trends; dashboards.
> ⛔ **OVER-SCOPED — ClickHouse/Pinot/BigQuery as MVP.** ✅ **ANSWERED (extended):** v1 = coverage/diversity + cost/SLO + calibration + stability (NB §11/§15; truth NB §10/§11); dashboards deferred.

### 6.15 CI/CD Gate
**Objective:** evaluate quarantine + blocking failures + risk + missing evidence → `approve/warn/block/require_manual_approval`; PR comments; sync or async.
> ⛔ **GAP (G4) — aggregation logic (N findings → 1 decision) undefined.** ✅ **ANSWERED:** precedence engine (BF-03) + wired vocabulary (BF-04), NB §11. 🟡 no actual CI integration yet.

### 6.16 Remediation Automation
**Objective:** map finding category/severity → playbooks (ticket, notify, rollback, disable tool, retest).
> 🟨 **PARTIAL** — v1 = `Finding.recommendation` text (NB §8). Destructive actions deferred (require A10 HITL).

### 6.17 Runtime Telemetry & Replay
**Objective:** sample production traces; shadow-evaluate/replay off the critical path; drift detection.
> 🟨 **PARTIAL** — v1 has **Mode-A replay** (NB §16) but **no production telemetry ingestion / drift** (vis1 «Evidence+Telemetry: drift · threat» ⛔).
> ❓ **OPEN QUESTION — sampling.** "Sample aggressively" can miss rare safety failures; bias sampling toward anomalies.

### 6.18 Governance & Audit
**Objective:** approval records, pass/fail reports, waiver history, immutable audit, evidence packages, chain of custody.
> ✅ **ANSWERED in v1** — H5.1 governance self-check (BF-23, NB §12) + audit bundle (truth NB §13). 🔶 **AT&T INPUT — «Golden Controls»** catalogue needed for full mapping.

### 6.19 RBAC & IAM
**Objective:** roles (developer, security reviewer, model owner, governance, admin, auditor, CI/CD SA); scoped permissions; authorization logging.
> ⛔ **GAP — not built.** v1 notes operator/reviewer/owner/auditor roles only. vis1 «Identity» ⛔.

### 6.20 Event Bus
**Objective:** durable lifecycle events; ordering by key; transactional outbox.
> ⛔ **OVER-SCOPED — Kafka/Pulsar as MVP.** ✅ pattern = transactional outbox (design). ❓ **OPEN — event payload schema (G10):** adopt CloudEvents envelope.

---

## 7. Runtime Telemetry and Replay Architecture
Keep the full harness **off** the synchronous request path; production apps emit sampled, redacted, replayable telemetry; inline guardrails may exist but deep scoring is off-path.
> ✅ **PRINCIPLE PRESERVED** (off-path replay, NB §16). ⛔ ingestion + shadow-eval against candidate models not built.

## 8. MVP Build Plan
> ⛔ **GAP (internal defect) — the original §8 is `TBD`.** ✅ **ANSWERED:** `enterprise_harness_mvp_plan.md` (tracer bullet + config contracts) and the operable `enterprise_harness_mvp_colab.ipynb` (5 harnesses, gate, replay). 🟨 the dependency-gated Phase-2 ladder = `enterprise_harness_phase2_integration_plan.md`.

---

## Annotated summary — where to focus the reference architecture

| Priority | Cluster | Items |
|---|---|---|
| **1 — resolve first** | ⛔ **Contracts** | G1 runner (BF-01) · G2 finding (BF-02) · G3 weights (BF-10) · G4 gate (BF-03) — mostly ✅ answered in v1; ratify them |
| **2 — re-scope** | ⛔ **Enterprise-as-MVP** | §6.9 Temporal · §6.11 K8s · §6.14 ClickHouse · §6.20 Kafka — ✅ v1 uses lean substitutes |
| **3 — build the front door** | ⛔ **Discover + Secure** | §6.1 connectors · §6.3 scanners (vis1 «Source/Security Agent», vis2 «Secure») — design-only |
| **4 — AT&T inputs** | 🔶 **External deps** | «Golden Controls» · «Model Router» · «Prisma AIRS/Janus/Internal AIRS» · «Harness Studio» — undefined in the original doc |
| **5 — breadth** | ⛔ **Catalogue** | 15 of 20 harnesses (Remediation + Resilience whole) not built |

*This annotated baseline + `Enterprise_harness_annotated_reference.drawio` are the starting reference architecture: every gap, question, and dependency is now visible and cited.*
