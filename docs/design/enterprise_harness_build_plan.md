# Enterprise AI Harness Platform — Build Plan

Prepared for Ivan Avelancio Jr.  
Date: 2026-07-07  
Source of truth: recently checked-in `docs/enterprise_harness.md` from `remedyblockchain/Bluey` commit `ef9211af` (`Add detailed design document for Enterprise AI Harness MVP`)  
Output: practical build sequence derived from that design document only.

---

## 1. What the Source Document Is Really Specifying

The checked-in `enterprise_harness.md` is not just an eval harness. It describes a **provider-independent enterprise AI assurance platform** with two major planes:

### Control Plane
Owns decisions, state, metadata, policy, approvals, orchestration, audit, RBAC, and API contracts.

Core responsibilities:
- Discover AI assets.
- Track provenance and lineage.
- Quarantine and scan assets.
- Normalize model/tool/agent metadata.
- Intake business use cases.
- Contextualize risk.
- Select required harnesses.
- Orchestrate evaluation runs.
- Make CI/CD gate decisions.
- Trigger remediation.
- Preserve governance/audit evidence.

### Data Plane
Owns execution and evidence capture.

Core responsibilities:
- Run scanner containers.
- Run harness containers.
- Provision isolated environments.
- Invoke models/agents through provider adapters.
- Execute mock tools and synthetic targets.
- Capture traces, telemetry, findings, artifacts, metrics, and reports.
- Support runtime replay off the critical production path.

### Practical Interpretation
The platform should be built in layers, but the MVP should not attempt all 20 layers at full enterprise scale. The right first version is a **vertical slice** that proves the full asset-to-gate workflow with a small number of asset types, harnesses, policies, and reports.

---

## 2. MVP North Star

Build a working platform slice where Ivan can:

1. Register or discover an AI asset.
2. Attach it to a use case.
3. Run quarantine checks.
4. Normalize its model/tool/agent metadata.
5. Generate a risk context.
6. Select required harnesses.
7. Execute harness runs in an isolated local environment.
8. Store traces and evidence.
9. Produce a gate decision: `approve`, `warn`, `block`, or `manual_review`.
10. Generate an executive/technical report.

The MVP should prove the system with these asset types first:

- Prompt
- Agent config
- Tool schema
- RAG dataset/index metadata
- Model endpoint reference

Avoid starting with full Kubernetes, Kafka, Temporal, enterprise IAM, or SIEM integrations until the core loop works locally.

---

## 3. Recommended MVP Architecture

Use a modular monorepo with API + worker + runner + UI/reporting.

```text
enterprise-ai-harness/
  README.md
  SAFETY.md
  pyproject.toml
  Makefile
  .env.example

  apps/
    api/                      # FastAPI control-plane API
    worker/                   # background orchestration worker
    cli/                      # harnessctl CLI
    dashboard/                # Streamlit or lightweight admin UI

  packages/
    common/                   # schemas, enums, shared utilities
    policy/                   # contextualization + gate rules
    discovery/                # connectors and asset registration
    quarantine/               # scanners and finding normalization
    normalization/            # provider/model/tool/agent mappings
    registry/                 # harness registry
    selector/                 # harness selection engine
    orchestration/            # run planner + state machine
    runner/                   # data-plane runner contract
    adapters/                 # provider adapters
    evidence/                 # artifact store + reports
    remediation/              # ticket/notify/retest actions
    telemetry/                # runtime trace + replay

  harnesses/
    prompt_injection/
    tool_misuse/
    sensitive_disclosure/
    rag_poisoning/

  scanners/
    secrets_scan/
    prompt_scan/
    tool_schema_scan/
    rag_policy_scan/

  scenarios/
    prompt_injection/
    tool_misuse/
    sensitive_disclosure/
    rag_poisoning/

  db/
    migrations/
    seed/

  reports/
    templates/
    output/

  tests/
```

### MVP Runtime Choices

| Area | MVP Choice | Later Enterprise Choice |
|---|---|---|
| API | FastAPI | Same or split services |
| DB | PostgreSQL preferred, SQLite acceptable for prototype | PostgreSQL + object storage |
| Object artifacts | Local filesystem | S3/MinIO/Azure Blob/GCS |
| Events | DB outbox table | Kafka/Pulsar/cloud pubsub |
| Workflow | Simple DB-backed worker/state machine | Temporal or Argo Workflows |
| Isolation | Local subprocess/container | Kubernetes namespaces/jobs |
| Dashboard | Streamlit | React/admin portal + Grafana/BI |
| Reports | Jinja2 Markdown/HTML | PDF packages + evidence bundles |
| Auth | Local roles/config | Enterprise IdP / OIDC / SSO |

---

## 4. Build Order: Vertical Slice First

The source document lists 20 layers. Build them in dependency order, but only to MVP depth.

## Phase 1 — Foundation and Schemas

**Goal:** Create the canonical data contracts that every layer uses.

Build:

1. `Asset`
2. `AssetVersion`
3. `UseCase`
4. `RiskContext`
5. `HarnessDefinition`
6. `HarnessExecutionPlan`
7. `EvaluationRun`
8. `HarnessRun`
9. `Finding`
10. `EvidenceArtifact`
11. `GateDecision`
12. `AuditEvent`

First database tables:

```text
assets
asset_versions
use_cases
use_case_assets
quarantine_jobs
security_findings
normalized_models
normalized_tools
normalized_agents
contextualization_results
harness_definitions
harness_execution_plans
harness_execution_plan_items
evaluation_runs
harness_runs
findings
evidence_artifacts
gate_decisions
audit_events
event_outbox
```

Build APIs:

```text
POST /api/v1/assets
GET  /api/v1/assets/{asset_id}
POST /api/v1/assets/{asset_id}/versions
POST /api/v1/use-cases
POST /api/v1/use-cases/{id}/assets
POST /api/v1/evaluations/runs
GET  /api/v1/evaluations/runs/{run_id}
GET  /api/v1/findings?run_id={run_id}
```

Done when:
- You can create an asset, create a version, attach it to a use case, and persist state.

---

## Phase 2 — Discovery Layer

**Goal:** Register AI assets from code or manual input.

Build first:

1. Manual asset registration API.
2. GitHub repo scanner for files matching:
   - `*.prompt.*`
   - `prompts/**`
   - `agents/**`
   - `tools/**`
   - `rag/**`
   - deployment manifests containing model/provider references.
3. Deterministic asset keys.
4. SHA-256 content/config hash.
5. Discovery findings for missing owner, missing metadata, write-capable tool, unapproved provider, public endpoint.

Defer:
- Kubernetes discovery.
- Runtime endpoint discovery.
- Artifact registry connector.

Done when:
- A GitHub scan creates `assets`, `asset_versions`, and `discovery_findings`.

---

## Phase 3 — Provenance and Lineage

**Goal:** Know where every AI asset came from and what depends on it.

Build first:

1. Immutable provenance record per asset version:
   - source URI
   - repo
   - commit SHA
   - file path
   - content hash
   - owner
   - license/SBOM URI if present
2. Simple lineage links:
   - agent uses model
   - agent uses tool
   - agent uses prompt
   - RAG pipeline uses dataset/index
3. Impact query:

```text
GET /api/v1/provenance/assets/{asset_id}/lineage
```

Defer:
- Materialized lineage graph.
- Advanced dependency inference.

Done when:
- You can answer: “if this tool/prompt/model changes, which use cases are affected?”

---

## Phase 4 — Quarantine and Security Layer

**Goal:** Block obviously unsafe assets before harness execution.

Build first scanners:

1. Secrets scanner.
2. Prompt-injection-pattern scanner.
3. Tool schema risk scanner.
4. RAG data policy scanner.
5. Provider approval scanner.

Normalize all scanner output into:

```text
security_findings
- severity
- category
- title
- description
- blocking_flag
- policy_rule
- evidence_uri
```

Quarantine decisions:

```text
allow
allow_with_warning
block
manual_review
```

Done when:
- Asset versions can be quarantined before harness selection.
- A finding can block an evaluation or require manual review.

---

## Phase 5 — Provider-Agnostic Normalization

**Goal:** Convert messy provider/agent/tool metadata into a common schema.

Build static mappings first:

### Normalized Model Fields
- provider
- model name
- context window
- supports tools
- supports vision
- supports structured output
- supports streaming
- region
- data retention class
- cost class
- risk class

### Normalized Tool Fields
- tool name
- input schema
- output schema
- read/write classification
- side-effect class
- auth requirement
- external network requirement
- risk class

### Normalized Agent Fields
- framework
- model references
- prompt references
- memory enabled
- RAG enabled
- tools attached
- runtime mode

Done when:
- Harnesses can be selected by capabilities instead of provider-specific names.

---

## Phase 6 — Use Case Intake and Contextualization

**Goal:** Convert business context into risk and required tests.

Build intake fields:

- owner
- business unit
- purpose
- asset links
- data classes: public/internal/confidential/PII/PHI/PCI/legal-sensitive
- users: internal/external/privileged/customer/partner
- criticality
- exposure: internal/private/public
- regulatory domain
- write-capable tools present
- human approval controls

Build contextualization rules as YAML first:

```yaml
- id: RULE-PII-001
  if:
    data_class: PII
  require_harnesses:
    - sensitive_disclosure
    - prompt_injection
  approvals:
    - security_reviewer
  risk_tier: high
```

Risk outputs:

- risk score
- risk tier
- required harnesses
- required approvals
- blocking policies
- rationale

Done when:
- A use case automatically produces required harnesses and approval requirements.

---

## Phase 7 — Harness Registry

**Goal:** Maintain approved harnesses as versioned, replaceable modules.

Build harness definition schema:

```json
{
  "name": "prompt_injection_baseline",
  "version": "0.1.0",
  "type": "behavioral_eval",
  "supported_asset_types": ["prompt", "agent", "rag_pipeline"],
  "supported_capabilities": ["chat", "tools", "rag"],
  "blocking_capable": true,
  "input_schema_uri": "...",
  "output_schema_uri": "...",
  "runner": "python_module_or_container",
  "status": "approved"
}
```

MVP harnesses:

1. Prompt Injection Baseline
2. Tool Misuse Baseline
3. Sensitive Disclosure Baseline
4. RAG Poisoning Baseline

Done when:
- Approved harnesses can be registered and selected without changing orchestrator code.

---

## Phase 8 — Harness Selection and Policy

**Goal:** Create deterministic, explainable execution plans.

Selection inputs:

- use case risk context
- normalized model/tool/agent capabilities
- quarantine decision
- harness registry
- enterprise policy

Execution plan output:

```text
harness_execution_plan
  item 1: prompt_injection_baseline, required=true, blocking=true
  item 2: sensitive_disclosure_baseline, required=true, blocking=true
  item 3: tool_misuse_baseline, required=true, blocking=false
```

Store skipped rationale:

- harness incompatible
- not required by policy
- asset type unsupported
- provider capability absent

Done when:
- The platform can explain why each harness was selected or skipped.

---

## Phase 9 — Evaluation Orchestration

**Goal:** Run selected harnesses reliably and persist results.

MVP orchestration:

1. Create `evaluation_run` from approved plan.
2. Create one `harness_run` per plan item.
3. Execute sequentially first.
4. Add status transitions:
   - pending
   - running
   - completed
   - failed
   - canceled
5. Aggregate final score and decision.
6. Write events to `event_outbox`.

Defer:
- Temporal.
- Argo Workflows.
- Parallel execution.
- Distributed retries.

Done when:
- One API call runs a full plan and returns aggregated decision.

---

## Phase 10 — Harness Runner Contract

**Goal:** Standardize how every harness executes.

Use the source document’s standard files:

```text
/input/run_config.json
/output/result.json
/output/evidence/*
```

### `run_config.json`

Must include:

- run ID
- harness ID/version
- asset version references
- target endpoint or local mock target
- normalized model/tool/agent metadata
- scenario set
- policy config
- output directory

### `result.json`

Must include:

- status
- score
- decision
- metrics
- findings
- evidence artifacts
- trace URI

MVP runner options:

1. Python module runner first.
2. Container runner second.
3. Kubernetes job runner later.

Done when:
- Any harness can be swapped in if it honors the same input/output contract.

---

## Phase 11 — Runtime Environment

**Goal:** Keep evaluation isolated and safe.

MVP:

- Local temporary working directory per run.
- No production credentials.
- Synthetic data only.
- Network disabled by default unless explicitly needed.
- Mock APIs and mock tools.
- Automatic cleanup.

Next:

- Docker/Podman per harness run.

Later:

- Kubernetes namespace per evaluation run.
- Default-deny egress.
- Explicit allowlist for approved provider endpoints.
- Resource quotas and teardown controller.

Done when:
- Harness execution cannot touch production systems by accident.

---

## Phase 12 — Provider Adapter Layer

**Goal:** Hide provider differences from harnesses.

MVP adapter interface:

```python
class ProviderAdapter:
    def invoke(self, request: ModelRequest) -> ModelResponse: ...
    def invoke_with_tools(self, request: ToolModelRequest) -> ModelResponse: ...
```

Common response schema:

- text
- structured output
- tool calls
- token usage
- latency
- provider metadata URI
- safety metadata
- raw payload URI

Start with:

1. Mock provider adapter.
2. OpenAI-compatible adapter.
3. Anthropic-compatible adapter if needed.

Done when:
- Harnesses call the common adapter, not provider APIs directly.

---

## Phase 13 — Evidence Store and Reports

**Goal:** Preserve audit-quality proof.

MVP evidence:

- prompts
- responses
- tool calls
- retrieved chunks
- scanner logs
- harness logs
- findings
- metrics
- policy decisions
- final reports

Store:

- metadata in DB
- artifacts on local filesystem under content-hashed paths

Report types:

1. Executive risk report.
2. Technical findings report.
3. Gate decision report.
4. Evidence bundle index.

Done when:
- A run produces a report and every finding links back to evidence.

---

## Phase 14 — CI/CD Gate

**Goal:** Make the platform useful in developer pipelines.

Build `harnessctl` CLI:

```bash
harnessctl register-asset --path ./agents/customer-support-agent.yaml
harnessctl evaluate --use-case customer-support --commit $GITHUB_SHA
harnessctl gate --run-id RUN-123
```

Gate decisions:

- `approve`
- `warn`
- `block`
- `manual_review`

Blocking criteria:

- quarantine block
- missing required harness
- blocking harness failure
- critical finding
- expired waiver
- missing approval
- unapproved provider/model/tool

Done when:
- A GitHub Actions job can fail on unsafe AI asset changes.

---

## Phase 15 — Remediation Automation

**Goal:** Turn failures into action.

MVP actions:

1. Create local remediation record.
2. Emit notification event.
3. Mark retest required.
4. Generate suggested remediation text in report.

Next integrations:

- Jira
- ServiceNow
- Slack/Teams
- GitHub PR comments

Defer high-risk automation:

- rollback
- disable tools
- production endpoint changes

Done when:
- Every blocking finding creates an owner-visible remediation item.

---

## Phase 16 — Runtime Telemetry and Replay

**Goal:** Evaluate production behavior off-path without slowing live requests.

MVP:

- Define normalized runtime trace schema.
- Accept trace POSTs:

```text
POST /api/v1/runtime/traces
```

- Store sampled traces with redaction.
- Replay a trace against a candidate model or policy.

Important source direction:
- Keep full harness outside synchronous runtime path.
- Inline guardrails may exist, but deep scoring happens off-path.

Done when:
- A captured runtime trace can be replayed against a candidate model/config and compared to baseline.

---

## Phase 17 — Governance, Audit, RBAC, Event Bus

**Goal:** Add enterprise controls after the core loop works.

MVP governance:

- Immutable audit events.
- Local role definitions.
- Approval records.
- Waiver records.
- Report generation.

MVP event bus:

- Transactional `event_outbox` table.
- Worker consumes outbox and dispatches internal handlers.

Later:

- OIDC/SSO.
- Enterprise IdP groups.
- Kafka/Pulsar/cloud pubsub.
- Fine-grained resource authorization.

Done when:
- Sensitive actions are auditable: waiver, approval, gate override, evidence access.

---

## 5. 30-Day Practical Build Plan

## Week 1 — Control Plane Skeleton

Deliverables:

- Repo structure.
- FastAPI app.
- DB migrations.
- Core schemas.
- Asset/version/use-case APIs.
- Manual asset registration.
- Basic audit event writing.

End-of-week demo:

- Register an agent asset.
- Create asset version.
- Attach to use case.
- View persisted metadata.

---

## Week 2 — Quarantine, Normalization, Contextualization

Deliverables:

- Secrets/prompt/tool/RAG scanners.
- Normalized finding schema.
- Static provider/model/tool normalization.
- Use case intake fields.
- YAML contextualization rules.
- Risk score and risk tier output.

End-of-week demo:

- Register a use case with a write-capable tool and PII.
- System marks it high risk.
- System requires prompt injection, tool misuse, and sensitive disclosure harnesses.

---

## Week 3 — Harness Registry, Selection, Runner

Deliverables:

- Harness registry.
- Four MVP harness definitions.
- Harness selection engine.
- Evaluation run orchestration.
- Standard runner contract.
- Local isolated workspace per run.
- JSON result collection.

End-of-week demo:

- One API call creates a harness plan.
- Another API call executes it.
- Results are persisted as harness runs/findings/evidence.

---

## Week 4 — Gate, Evidence, Reports, CLI

Deliverables:

- Gate decision engine.
- Evidence artifact store.
- Jinja2 report generation.
- `harnessctl` CLI.
- GitHub Actions example.
- Basic dashboard or run summary page.

End-of-week demo:

- Run an evaluation from CLI.
- Produce a `block` decision due to critical finding.
- Generate executive and technical reports.
- Show evidence links and remediation items.

---

## 6. 90-Day Expansion Plan

## Days 31–60

Add:

- GitHub discovery connector.
- Containerized harness runner.
- Docker/Podman isolation.
- Promptfoo adapter as one harness implementation.
- DeepEval/DeepTeam comparison path.
- GitHub PR comments.
- Waivers with expiration.
- Manual approval workflow.
- Streamlit dashboard.

## Days 61–90

Add:

- Kubernetes namespace execution option.
- Wazuh/OpenSearch/Elastic event emission.
- Runtime telemetry ingestion.
- Replay against candidate models.
- Regression analytics.
- OIDC/SSO planning.
- Jira/ServiceNow remediation integration.
- Evidence package export.

---

## 7. Build Priority by Source Layer

| Source Layer | MVP Priority | Build Depth |
|---|---:|---|
| Discovery | High | Manual + GitHub file scan |
| Provenance/Lineage | High | Source/hash/owner + simple graph |
| Quarantine/Security | High | Basic scanners + block/warn/review |
| Provider Normalization | High | Static mappings |
| Use Case Intake | High | API + simple UI/CLI payload |
| Contextualization | High | YAML rules + weighted risk |
| Harness Registry | High | Versioned definitions |
| Harness Selection | High | Deterministic plan + explainability |
| Evaluation Orchestration | High | DB-backed sequential worker |
| Harness Runner | High | Standard local contract |
| Runtime Environment | Medium | Local temp dir, then container |
| Provider Adapter | Medium | Mock + 1 real provider-compatible adapter |
| Evidence Store | High | Local artifacts + DB metadata |
| Observability/Analytics | Medium | Basic metrics/trends |
| CI/CD Gate | High | CLI + GitHub Actions |
| Remediation | Medium | Records + report text first |
| Runtime Telemetry/Replay | Medium | Trace schema + replay POC |
| Governance/Audit | High | Audit events + reports |
| RBAC/IAM | Low initially | Local roles, enterprise later |
| Event Bus | Medium | DB outbox first |

---

## 8. First Harnesses to Implement

### 1. Prompt Injection Baseline
Tests:
- direct instruction override
- indirect RAG instruction
- system prompt extraction attempt
- cross-context contamination

Outputs:
- goal integrity score
- output leakage score
- detection result
- findings

### 2. Tool Misuse Baseline
Tests:
- unsafe write-capable tool call
- parameter scope breach
- approval bypass attempt
- tool chaining risk

Outputs:
- tool safety score
- blocked/allowed action log
- side-effect risk finding

### 3. Sensitive Disclosure Baseline
Tests:
- synthetic PII leakage
- synthetic credential leakage
- confidential document leakage
- excessive context disclosure

Outputs:
- disclosure score
- leaked token/PII detector result
- evidence redaction status

### 4. RAG Poisoning Baseline
Tests:
- adversarial document retrieved
- instruction-like retrieved content
- source trust conflict
- poisoned memory/reference

Outputs:
- retrieval trust score
- injection resistance score
- suspicious source finding

---

## 9. Engineering Rules

1. **Everything versioned.** Assets, harnesses, policies, rules, reports, and findings need version identity.
2. **Everything explainable.** Store why a harness was selected, skipped, passed, failed, or blocked.
3. **No provider lock-in.** Harnesses use normalized interfaces, not direct provider SDKs.
4. **No production coupling in MVP.** Use mocks, synthetic data, local execution, and explicit allowlists.
5. **Artifacts are evidence.** Hash them, store them, link findings to them.
6. **Blocking must be auditable.** Every gate decision needs policy version + rationale.
7. **Do not overbuild orchestration first.** Sequential worker beats premature Temporal/Kubernetes complexity.
8. **Reports before dashboards.** Reports prove business value faster than UI polish.

---

## 10. Immediate Next Steps for Ivan

1. Create a dedicated repo or branch for the platform implementation.
2. Start with FastAPI + PostgreSQL + SQLAlchemy/Alembic or SQLModel.
3. Build core schemas and database migrations first.
4. Implement manual asset registration before GitHub/Kubernetes discovery.
5. Implement four MVP harnesses as local Python modules before containers.
6. Add the runner contract early: `/input/run_config.json` and `/output/result.json`.
7. Generate the first report before building full dashboard.
8. Add CI/CD gate once one evaluation run can produce a stable decision.

Recommended first command sequence:

```bash
mkdir enterprise-ai-harness
cd enterprise-ai-harness
python -m venv .venv
source .venv/bin/activate
pip install fastapi uvicorn pydantic sqlalchemy alembic psycopg2-binary pyyaml jinja2 pytest rich typer
mkdir -p apps/{api,worker,cli,dashboard}
mkdir -p packages/{common,policy,discovery,quarantine,normalization,registry,selector,orchestration,runner,adapters,evidence,remediation,telemetry}
mkdir -p harnesses/{prompt_injection,tool_misuse,sensitive_disclosure,rag_poisoning}
mkdir -p scanners/{secrets_scan,prompt_scan,tool_schema_scan,rag_policy_scan}
mkdir -p scenarios reports/templates reports/output db/migrations tests
```

Then build in this order:

1. `packages/common/schemas.py`
2. `db/migrations/0001_core_tables.sql`
3. `apps/api/main.py`
4. `packages/discovery/manual_registration.py`
5. `packages/quarantine/scanners.py`
6. `packages/policy/contextualization.py`
7. `packages/registry/harness_registry.py`
8. `packages/selector/selection.py`
9. `packages/orchestration/evaluation_worker.py`
10. `packages/runner/local_runner.py`
11. `packages/evidence/report_builder.py`
12. `apps/cli/harnessctl.py`

---

## 11. MVP Definition of Done

The MVP is done when:

- A prompt/agent/tool/RAG asset can be registered.
- Asset provenance and version hashes are stored.
- Quarantine scanners run and produce normalized findings.
- A use case can be created and risk-contextualized.
- Harness selection creates an explainable execution plan.
- Four baseline harnesses can run locally.
- Evidence artifacts and traces are persisted.
- Gate decision returns approve/warn/block/manual_review.
- Report generation produces executive + technical output.
- CLI can run an evaluation from a pipeline.
- All safety constraints are documented and enforced.

---

## 12. Strategic Recommendation

The best commercial path is to build this as a **governance-first AI assurance platform**, not merely a red-team tool.

Positioning:

> “Provider-independent AI deployment assurance: discover AI assets, validate risk, run required harnesses, preserve evidence, and gate unsafe changes before they reach production.”

That aligns better with enterprise buyers than “AI red-team harness” alone because it maps directly to security, audit, compliance, SDLC governance, and model-risk management.
