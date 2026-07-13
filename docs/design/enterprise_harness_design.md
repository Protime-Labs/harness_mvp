# Enterprise AI Harness Platform — Design Document (v2)

**Owner:** Ivan Avelancio Jr.
**Status:** Rewritten and consolidated from `enterprise_harness.md` (source design) and `enterprise_harness_build_plan.md` (derived plan).
**Supersedes:** `enterprise_harness.md`, `enterprise_harness_build_plan.md`, `enterprise_harness_build_plan (1).md`.

> This rewrite fixes three defects in the source: (1) the Core Data Model (§5) was an empty figure reference, (2) the MVP Build Plan (§8) was `TBD`, and (3) several "Implementation Notes" prescribed Kubernetes / Temporal / Kafka *as MVP*, which are enterprise-scale, not MVP-scale. Those are corrected here and expanded in the companion **`enterprise_harness_mvp_plan.md`**.

---

## 1. Executive Summary

A **provider-independent enterprise AI assurance platform** that continuously discovers, validates, evaluates, gates, and monitors AI assets — models, agents, prompts, RAG pipelines, tools, MCP servers, datasets, deployment manifests, and runtime endpoints.

The platform separates concerns into two planes:

- **Control plane** — decisions and state: lifecycle, policy, selection, approvals, orchestration, audit, API contracts.
- **Data plane** — execution and evidence: isolated workspaces, scanners, harness runners, provider adapters, model/agent invocation, telemetry, evidence artifacts.

The commercial positioning is **governance-first AI deployment assurance**, not a red-team tool:

> "Provider-independent AI deployment assurance: discover AI assets, validate risk, run required harnesses, preserve evidence, and gate unsafe changes before they reach production."

This maps directly to security, audit, compliance, SDLC governance, and model-risk management — the enterprise buying centers.

---

## 2. Architecture Overview

Four zones: enterprise **sources** → **control plane** (decides) → **data plane** (executes) → enterprise **outputs**.

```text
  SOURCES                CONTROL PLANE               DATA PLANE                 OUTPUTS
  ───────                ─────────────               ──────────                 ───────
  GitHub / CI       →    Discovery                                              Gate decisions
  Kubernetes        →    Provenance/Lineage    ┌──→  Scanner containers    →    PR annotations
  Model catalog     →    Quarantine policy     │     Harness runners       →    Reports (exec/tech)
  Artifact registry →    Normalization         │     Provider adapters     →    Evidence bundles
  Runtime telemetry →    Contextualization     │     Mock tools/targets    →    Tickets/notifications
                         Harness selection ────┘     Fault injection       →    Audit trail
                         Orchestration              Evidence capture
                         CI/CD gate            ←──── Findings/traces/metrics
                         Governance/Audit/RBAC
```

| Plane | Owns | Example components |
|---|---|---|
| **Control** | State, policy, metadata, orchestration, approvals, audit | Control-plane API, policy engine, harness registry, orchestrator, RBAC/IAM, metadata store |
| **Data** | Execution, scanning, evaluation, traces, evidence | Scanner containers, harness runner, provider-adapter layer, fault injection, evidence store |

**Architectural invariant:** even when the MVP runs both planes in one process, the *code boundary* between them is preserved. Harnesses (data plane) never make policy decisions; the control plane never invokes a provider SDK directly.

---

## 3. End-to-End Workflow (the canonical order of operations)

This 10-step pipeline is the backbone. Every feature is built *along* it, not layer-by-layer in isolation. The data handoff between steps forces the ordering.

```text
1.  Discover / receive an asset version         →  §6.1  Discovery
2.  Record provenance, ownership, hash, lineage →  §6.2  Provenance
3.  Quarantine scan → allow/warn/block/manual   →  §6.3  Quarantine
4.  Normalize model/tool/agent capabilities     →  §6.4  Normalization
5.  Contextualize use case → risk + required    →  §6.6  Contextualization
6.  Select required + blocking harnesses        →  §6.8  Selection
7.  Provision isolated env, run harnesses       →  §6.9–6.12  Orchestration/Runner/Env/Adapter
8.  Persist findings, traces, evidence          →  §6.13 Evidence
9.  CI/CD gate → approve/warn/block/manual       →  §6.15 Gate
10. Remediate → ticket / notify / retest         →  §6.16 Remediation
```

**Dependency reality (why the order can't change):**
- Step 6 (selection) requires **all three** of: step 4 normalized capabilities, step 5 required-harness list, step 3 quarantine decision.
- Step 9 (gate) consumes step 3 (quarantine block), step 6 (missing required harness), and step 8 (critical finding / blocking failure).
- Step 7 cannot run a harness without the **provider adapter (§6.12)** — which the source numbers 12th but is a step-7 dependency. Build it with the runner, not after.

---

## 4. Core Data Model

> The source §5 referenced an empty figure. This is the entity model made explicit.

**Asset lifecycle & provenance**
```text
assets (1) ──< (N) asset_versions
asset_versions (1) ── (1) provenance_records          # immutable: source URI, commit SHA, hash, owner, license/SBOM
asset_versions (N) ──< (N) asset_lineage              # adjacency rows: agent→model, agent→tool, agent→prompt, rag→index
asset_versions (1) ──< (N) asset_approvals
```

**Use case & risk**
```text
use_cases (1) ──< (N) use_case_assets ──> asset_versions
use_cases (1) ──< (N) use_case_data_classes           # public/internal/confidential/PII/PHI/PCI/legal
use_cases (1) ──< (N) use_case_users                  # internal/external/privileged/partner/customer
use_cases (1) ──< (N) use_case_controls               # declared guardrails/approvals/filters
use_cases (1) ── (1) contextualization_results        # risk tier/score, required harnesses, approvals, rationale
contextualization_rules (N)                           # versioned YAML/OPA rules
```

**Quarantine**
```text
asset_versions (1) ──< (N) quarantine_jobs
quarantine_jobs (1) ──< (N) scanner_runs ──> scanner_definitions
quarantine_jobs (1) ──< (N) security_findings         # normalized: severity, category, blocking_flag, policy_rule, evidence_uri
quarantine_jobs (1) ── (1) quarantine_policy_decisions
quarantine_jobs (1) ──< (N) quarantine_waivers        # approver + expiration
```

**Normalization**
```text
normalized_models / normalized_tools / normalized_agents   # provider-independent capability records
provider_adapters                                          # adapter version + feature map
```

**Selection → execution → evidence**
```text
harness_definitions (1) ──< (N) harness_versions           # only "approved" versions selectable for blocking
harness_execution_plans (1) ──< (N) harness_execution_plan_items ──> harness_definitions
harness_execution_plans (1) ──< (N) harness_selection_decisions   # WHY selected/skipped  (mandatory)
evaluation_runs (1) ──< (N) harness_runs ──> plan_items
harness_runs (1) ──< (N) findings
harness_runs (1) ──< (N) evidence_artifacts               # SHA-256 hashed, retention class
harness_runs (1) ──< (N) harness_run_metrics
evaluation_runs (1) ── (1) gate_decisions                 # approve/warn/block/manual + policy version + rationale
```

**Cross-cutting**
```text
audit_events        # immutable, stored separately from mutable tables
event_outbox        # transactional outbox → in-process consumer (MVP) → broker (later)
remediation_actions # ticket/notify/retest records
```

---

## 5. Layer-by-Layer Design (20 layers, with MVP depth)

Each layer: **objective**, key **tables**, key **APIs**, and **MVP depth** (`FULL` / `LITE` / `DEFER`).

### 6.1 Discovery — `LITE`
Find and register AI assets; classify type; dedupe across code/CI/K8s/runtime; version only on hash change; attach early risk hints (missing owner, write-capable tool, external provider, PII source, public endpoint).
Tables: `discovery_sources, discovery_runs, discovered_assets, discovered_asset_versions, asset_source_bindings, discovery_findings`.
APIs: `POST /discovery/sources`, `POST /discovery/runs`, `GET /assets`, `POST /discovery/events`.
**MVP:** manual registration API + SHA-256 hashing only. Defer GitHub/K8s/registry/webhook connectors.

### 6.2 Provenance & Lineage — `FULL`
Immutable per-version record (source URI, commit SHA, content hash, SBOM/license, owner, approval status); parent/child lineage; impact/blast-radius query.
Tables: `provenance_records, asset_lineage, asset_approvals, asset_lineage_snapshots`.
APIs: `POST /provenance/records`, `GET /provenance/assets/{id}/lineage`, `GET /provenance/versions/{id}/dependencies`.
**MVP:** adjacency rows (no graph DB); answer "if this changes, which use cases are affected?"

### 6.3 Quarantine & Security — `FULL (1 scanner first)`
Materialize version in isolated workspace; run static + AI-specific scanners; normalize to common finding schema; decide `allow / allow_with_warning / block / require_manual_review`; support waivers with expiration.
Tables: `quarantine_jobs, scanner_definitions, scanner_runs, security_findings, quarantine_policy_decisions, quarantine_waivers, quarantine_evidence_artifacts`.
APIs: `POST /quarantine/jobs`, `GET /quarantine/jobs/{id}/findings`, `GET /quarantine/jobs/{id}/decision`, `POST /quarantine/waivers`.
**MVP:** secrets scanner first; then prompt-injection-pattern, tool-schema-risk, RAG-policy, provider-approval scanners.

### 6.4 Provider-Agnostic Normalization — `FULL (static)`
Map provider capabilities into normalized features (`supports_tools/vision/streaming/structured_output`, context window, region, retention class, cost/latency/risk class). Enables capability-based harness selection.
Tables: `normalized_models, normalized_tools, normalized_agents, provider_adapters, normalization_probes`.
APIs: `POST /normalization/models`, `GET /adapters/providers/{provider}/features`.
**MVP:** static catalog mappings; keep raw provider metadata in JSONB. Defer dynamic probing.

### 6.5 Use Case Intake — `FULL`
Capture owner, business unit, purpose, assets, data classes, user population, criticality, exposure, regulatory domain, controls. Draft → submitted → approved.
Tables: `use_cases, use_case_assets, use_case_data_classes, use_case_users, use_case_controls`.
APIs: `POST /use-cases`, `POST /use-cases/{id}/assets`, `POST /use-cases/{id}/submit`.
**MVP:** manual API/CLI payload. Defer auto-linking from discovery.

### 6.6 Contextualization — `FULL (YAML)`
Convert use case → risk profile, required controls, required harnesses, required approvals. Versioned, auditable rules; transparent weighted score; distinguishes advisory vs blocking.
Tables: `contextualization_results, contextualization_rules, risk_factor_results, approval_requirements`.
APIs: `POST /contextualization/evaluate`, `POST /contextualization/rules`.
**MVP:** YAML rules + documented weighted-score formula (see gaps §7).

### 6.7 Harness Registry — `FULL`
Catalog of approved, versioned, swappable harnesses (type, supported asset types/capabilities, container image, input/output schema URIs, blocking capability, status, approval history). Only `approved` versions run in blocking gates. Add harnesses without changing the orchestrator.
Tables: `harness_definitions, harness_versions, harness_approvals, harness_compatibility, harness_test_suites`.
APIs: `POST /harnesses`, `POST /harnesses/{id}/approve`, `POST /harnesses/{id}/deprecate`.
**MVP:** register 4 baseline harnesses with validated schemas.

### 6.8 Harness Selection & Policy — `FULL`
Consume contextualization + normalized capabilities + quarantine decision + registry + policy; filter by asset type/capability/status/risk tier; produce ordered plan (required/optional/blocking); **store skip rationale**.
Tables: `harness_execution_plans, harness_execution_plan_items, harness_selection_decisions, plan_approvals`.
APIs: `POST /harness-selection/plans`, `GET /harness-selection/plans/{id}/explain`.
**MVP:** deterministic + fully explainable. Skip rationale is mandatory, not optional.

### 6.9 Evaluation Orchestration — `LITE`
Create runs from approved plans; manage provisioning, ordering, parallelism, retries, timeouts, aggregation, evidence upload; survive process restarts; apply final policy.
Tables: `evaluation_runs, harness_runs, workflow_steps, run_locks`.
APIs: `POST /evaluations/runs`, `POST /evaluations/runs/{id}/cancel`.
**MVP:** DB-backed **sequential** worker + status transitions (`pending/running/completed/failed/canceled`) + `run_locks`. **Corrected from source:** Temporal/Argo are *deferred*, not MVP.

### 6.10 Harness Runner — `FULL`
Execute a harness against a target using the **standard run contract**; inject config/policy/target/schemas/datasets/output dir; enforce quotas/timeout; collect result JSON + evidence + metrics + traces; normalize findings.
Tables: `harness_run_results, harness_run_logs, harness_run_metrics, harness_run_artifacts`.
APIs: `POST /runner/execute`, `POST /runner/runs/{id}/cancel`.
**MVP:** Python-module runner honoring `/input/run_config.json` → `/output/result.json` + `/output/evidence/*`. This contract is load-bearing — do not shortcut it. (Schemas defined in MVP plan.)

### 6.11 Runtime Environment — `LITE`
Isolated, ephemeral execution: no prod secrets, synthetic data, restricted egress, per-run quotas, timeouts, audit, auto-teardown, mock APIs/tools, fault injection.
Tables: `runtime_environments, evaluation_environment_bindings, environment_resources, fault_injection_profiles`.
APIs: `POST /environments/{id}/provision`, `POST /environments/{id}/teardown`.
**MVP:** local temp dir per run, egress off by default. **Corrected from source:** K8s namespaces are *deferred*; subprocess/local isolation satisfies the "no prod coupling" requirement at a fraction of the cost. Docker/Podman next.

### 6.12 Provider Adapter — `FULL (mock first)`
Hide provider API differences (chat, tools, structured output, streaming, embeddings, MCP, retries, token/cost accounting) behind a normalized `ModelRequest`/`ToolRequest` → common `ModelResponse`.
Tables: `provider_adapters, adapter_invocations, adapter_rate_limits, adapter_feature_maps`.
APIs: `POST /adapters/invoke`, `POST /adapters/invoke-with-tools`, `GET /adapters/providers`.
**MVP:** mock adapter (deterministic, offline) → then one OpenAI-compatible + one Anthropic-compatible adapter. Harnesses call the adapter, never a provider SDK.

### 6.13 Evidence Store — `FULL`
Persist prompts, responses, tool calls, retrieved chunks, scanner/harness logs, findings, metrics, reports, policy decisions, traces. Small metadata in DB, large artifacts in object store; retention by data class; encryption/redaction/access control.
Tables: `evidence_artifacts, findings, evidence_access_log, evidence_retention_policies`.
APIs: `POST /evidence/artifacts`, `GET /evidence/runs/{id}`, `GET /findings?run_id={id}`.
**MVP:** DB metadata + local filesystem under content-hashed paths; every finding links to an evidence URI.

### 6.14 Observability & Analytics — `DEFER`
Pass/fail trends, risk trends, regression vs baseline, latency/cost, PII-leak rate; dashboards by use case/model/harness/BU.
Tables: `evaluation_metrics, risk_snapshots, regression_results, dashboard_views`.
**MVP:** basic run-summary only. Full analytics post-MVP.

### 6.15 CI/CD Gate — `FULL`
Evaluate quarantine result, blocking harness failures, risk score, missing evidence, policy violations, expired waivers, unapproved model, missing approval → `approve / warn / block / require_manual_approval`; PR comments; sync or async-with-callback.
Tables: `cicd_gate_decisions, cicd_callbacks, deployment_approvals`.
APIs: `POST /cicd/gate/evaluate`, `POST /cicd/gate/callback`.
**MVP:** `harnessctl` CLI + explicit, auditable blocking criteria + GitHub Actions example.

### 6.16 Remediation Automation — `LITE`
Map finding category/severity → playbook actions: create ticket, notify, fail pipeline, roll back, disable tool, require approval, retest, open incident.
Tables: `remediation_actions, remediation_playbooks, remediation_action_attempts, remediation_targets`.
APIs: `POST /remediation/actions`, `POST /remediation/actions/{id}/retry`.
**MVP:** local remediation record + notification event + retest flag + suggested-fix report text. Defer Jira/ServiceNow/Slack and all destructive actions (rollback/disable-tool) until approval workflows mature.

### 6.17 Runtime Telemetry & Replay — `DEFER`
Sample production traces (prompt/response/model/tools/retrieval/latency/cost/policy); shadow-evaluate and replay against candidate models off the critical path; drift detection.
Tables: `runtime_traces, runtime_trace_events, replay_runs, drift_findings`.
APIs: `POST /runtime/traces`, `POST /runtime/replay`.
**MVP:** define the trace schema + a replay POC only. **Design constraint:** full harness stays *off* the synchronous request path; inline guardrails may exist but deep scoring is off-path.

### 6.18 Governance & Audit — `FULL (audit only)`
Approval records, pass/fail reports, policy violations, waiver history, immutable audit trail, evidence packages, executive summaries; full chain of custody discovery→gate.
Tables: `audit_events, governance_reports, approval_records, waiver_history`.
APIs: `GET /audit/events`, `POST /governance/reports`, `GET /governance/use-cases/{id}/evidence`.
**MVP:** immutable audit events + Jinja2 report generation. Retain audit events independently of operational tables.

### 6.19 RBAC & IAM — `DEFER`
Roles (developer, security reviewer, model owner, governance reviewer, admin, auditor, CI/CD service account); scoped permissions; authorization logging.
Tables: `principals, role_assignments, permission_definitions, authorization_logs`.
**MVP:** local roles in config. Enterprise IdP / OIDC / SSO later. Treat waiver approval, gate override, evidence access as high-sensitivity from day one (even if only logged).

### 6.20 Event Bus — `LITE`
Durable lifecycle events decouple components; ordering by resource key; feeds analytics/notifications/automation.
Tables: `event_outbox, event_log, event_subscriptions, dead_letter_events`.
APIs: `POST /events`, `POST /events/subscriptions`.
**MVP:** transactional `event_outbox` + in-process consumer. **Corrected from source:** Kafka/Pulsar are *deferred*; the outbox *pattern* is what's required.

---

## 6. Cross-Cutting Requirements (product invariants)

These survive into the smallest MVP because they are the differentiators. Drop them and it's a generic eval script.

| # | Invariant | Enforced by |
|---|---|---|
| R1 | Control/data plane separation (code boundary) | §2 |
| R2 | Provider independence — capability-based, no provider SDK in harnesses | §6.4, §6.12 |
| R3 | Standard runner contract (`run_config.json`/`result.json`/`evidence/*`) | §6.10 |
| R4 | Everything versioned; provenance/audit immutable | §6.2, §6.18 |
| R5 | Explainable selection — store why each harness ran or was skipped | §6.8 |
| R6 | Evidence = hashed chain of custody; findings link to evidence | §6.13, §6.18 |
| R7 | No production coupling — isolation, synthetic data, default-deny egress | §6.11 |
| R8 | Transactional outbox for events | §6.20 |
| R9 | Fixed decision vocabulary — quarantine `allow/allow_with_warning/block/manual_review`; gate `approve/warn/block/require_manual_approval` | §4, §6.3, §6.15 |

**Engineering rules:** everything versioned; everything explainable; no provider lock-in; no production coupling in MVP; artifacts are evidence (hash + link); blocking must be auditable (policy version + rationale); don't overbuild orchestration; reports before dashboards.

---

## 7. Configuration Gaps & Open Questions

The source fully specifies *entities and APIs* but leaves the **configuration contracts** — the actual JSON/YAML the platform reads and writes — undefined. These are the true blockers to implementation. Each is resolved with a concrete schema in `enterprise_harness_mvp_plan.md §5`.

| # | Gap | Impact | Resolution |
|---|---|---|---|
| G1 | **Runner contract has no schema.** `run_config.json`/`result.json` are named (§6.10) but never defined. | Nothing can run — harnesses can't be written against an undefined contract. | Concrete JSON Schemas (MVP plan §5.1–5.2). **Highest priority.** |
| G2 | **Finding schema is inconsistent** across quarantine (§6.3) and evidence (§6.13). | Findings can't be normalized or aggregated. | Single canonical `Finding` schema (MVP plan §5.3). |
| G3 | **Risk scoring formula undefined.** "Transparent weighted score" (§6.6) with no weights. | Risk tier is non-deterministic; can't be tuned or audited. | Documented weight table + tier thresholds (MVP plan §5.4). |
| G4 | **Gate aggregation logic undefined.** How do N harness scores/decisions → one gate decision? | The core output is unspecified. | Explicit precedence rules (MVP plan §5.5). |
| G5 | **Contextualization rule schema is informal.** One YAML example, no formal fields/operators. | Rules can't be validated or version-controlled safely. | Rule schema + operator set (MVP plan §5.6). |
| G6 | **Harness definition input/output schema URIs are placeholders** (§6.7). | Registry can't validate what a harness consumes/produces. | Bind to G1 contract + per-harness scenario schema. |
| G7 | **Deterministic asset-key algorithm unspecified** ("canonical keys", §6.1). | Dedup (§6.1) and change-detection can't be implemented. | Define key = `hash(type + normalized-identity-fields)` (MVP plan §5.7). |
| G8 | **Normalized capability vocabulary is open-ended.** Feature names listed but not enumerated. | Selection filters can't match reliably across providers. | Closed enum of capability flags + classes. |
| G9 | **Evidence retention/redaction policy unspecified.** Retention "by data class" but no classes→durations map, no redaction rules. | PII/PHI handling is undefined — a compliance risk. | Retention matrix + redaction pass before persist. |
| G10 | **Event payload schemas undefined.** Event *names* listed (§6.20) but no payloads. | Consumers can't be built against events. | Envelope schema `{event, resource_id, version, ts, payload_hash, payload}`. |
| G11 | **Synthetic-data / mock-target spec missing.** §6.11 requires synthetic data; none defined. | Harnesses have nothing safe to run against. | Fixture sets per harness (seeded, deterministic). |
| G12 | **Multi-tenancy / scoping undefined for MVP.** Object-store prefixes "by tenant" (§6.13) but no tenant model. | Rework later if bolted on. | Single-tenant MVP, but carry a `tenant_id` column from day one. |
| G13 | **Waiver ↔ gate interaction underspecified.** Expired waiver blocks (§6.15) but lifecycle/review flow is thin. | Governance ambiguity. | Waiver states + expiry check in gate engine. |
| G14 | **No SAFETY.md / authorized-use boundary.** Platform runs injection/jailbreak scenarios. | Legal/operational exposure without documented authorization + synthetic-only constraint. | Ship `SAFETY.md` in the repo root (MVP plan §7). |

---

## 8. MVP Build Plan (summary — full plan in companion doc)

The source §8 was `TBD`. The MVP is a **vertical slice (tracer bullet)** through the full §3 workflow — one asset, one scanner, one harness, mock adapter, one gate, one report — proving all nine invariants (R1–R9) end-to-end before widening.

**MVP Definition of Done:** a registered agent asset with a PII + write-capable-tool use case is contextualized to high risk; selection produces an *explainable* plan requiring prompt-injection; the harness runs in isolation against the mock adapter; findings + hashed evidence persist; the gate returns `block`; `harnessctl` emits executive + technical reports with every finding linked to evidence; all safety constraints documented.

See **`enterprise_harness_mvp_plan.md`** for scope table, config-contract schemas (resolving §7 gaps), build sequence, repo layout, and the 30/60/90-day widening path.
