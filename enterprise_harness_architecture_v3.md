# Enterprise AI Harness Platform — Target Architecture (v3, Agentic)

**Owner:** Ivan Avelancio Jr.
**Status:** Full architecture. Design-only — no scaffolding. To be reviewed before any build.
**Builds on (does not replace):** `enterprise_harness_design.md` (v2 — 20 layers, R1–R9, G1–G14), `enterprise_harness_mvp_plan.md` (tracer bullet, config contracts).
**Adds:** the agentic execution model, the enterprise framework stack bound to each layer, and 10 agentic invariants (A1–A10) that extend R1–R9.

> Read order: this doc (what the system *is*) → `enterprise_harness_agentic_workflows.md` (how the agents *run*) → `enterprise_harness_architecture_review.md` (proof it satisfies every requirement).

---

## 1. The governing idea

A modern enterprise AI harness is itself agentic: the red-team scenarios are driven by **attacker agents**, the target-under-test is an **agent/model/RAG**, and success is decided by **judge agents** (LLM-as-judge). If any of those agents were allowed to make the *blocking* decision, the platform would be non-deterministic, non-auditable, and injectable — the opposite of an assurance tool.

So the whole architecture rests on one split:

```text
          DATA PLANE (agentic, non-deterministic)        CONTROL PLANE (deterministic, auditable)
          ────────────────────────────────────────       ─────────────────────────────────────────
          Attacker agents  → generate & adapt attacks     Risk scoring        → versioned weights (G3)
          Target-under-test → the asset being evaluated    Harness selection   → deterministic rules (G5)
          Judge agents     → score, detect, verify         Gate decision       → precedence rules (G4/R9)
          Remediation agent → PROPOSE fixes                 Waiver/approval      → policy + human
                                   │                                    ▲
                                   └──── findings + hashed evidence ────┘
```

**Rule of the architecture:** *agents propose, enrich, attack, and judge; policy decides.* An agent may write a finding; only the rule engine may turn findings into `block`. This preserves R1 (plane separation) as a hard code boundary and makes the agentic layer safe to adopt.

---

## 2. Design principles (extends the v2 engineering rules)

| # | Principle | Consequence |
|---|---|---|
| P1 | **Governance-first, not red-team-first.** | The product is the control plane; the harnesses are pluggable data-plane engines. |
| P2 | **Agents generate & judge; policy decides.** | No LLM in the gate/risk decision path. §1. |
| P3 | **Buy/adopt the eval engine; build the governance wrapper.** | Inspect AI + LiteLLM + PyRIT/Garak/Promptfoo are the substrate; your IP is discovery→gate→evidence→audit. |
| P4 | **Provider independence extends to every agent.** | Attacker, target, and judge agents all call the adapter (LiteLLM), never a provider SDK (R2 → A2). |
| P5 | **Every agent turn is evidence.** | Prompt, response, tool call, and judgment are hashed and stored; a run is replayable from evidence (R6 → A3). |
| P6 | **Determinism is engineered, not assumed.** | Temp/seed/model-version pinning, and quorum judging bound the non-determinism that agents introduce (A5, A7). |
| P7 | **Synthetic-only, isolated attack surface.** | Attacker agents only ever hit mock targets on a network-denied workspace (R7 → A6). |

---

## 3. The two planes × two tracks

The v2 design defines two **planes** (control/data). This architecture adds two **build tracks** that cut across them so a *functional* MVP produces results fast:

- **Track A — executable core (data plane):** scenario set → attacker agent → target (adapter) → judge quorum → `result.json`. Built on **Inspect AI** (task/dataset/solver/scorer) with **LiteLLM** as the adapter and a **mock provider** for offline runs. This is the part that *produces results for test evaluation cases*.
- **Track B — governance wrapper (control plane):** discovery → provenance → contextualization → selection → gate → evidence → audit. This is the v2 spine and the product differentiation.

The `run_config.json` / `result.json` contract (v2 §5.1–5.2, gap G1) is the **only** interface between the tracks. Track A honors it; Track B produces and consumes it. This is R3 restated as the track boundary.

---

## 4. Reference architecture

```text
 SOURCES            CONTROL PLANE (Track B — deterministic)          DATA PLANE (Track A — agentic)         OUTPUTS
 ───────            ────────────────────────────────────            ──────────────────────────────         ───────
 GitHub/CI    →  Discovery ─ Provenance ─ Quarantine                ┌─ Orchestrator (Inspect eval /        Gate decisions
 K8s/registry →     │            │            │                     │   Temporal at scale)                 PR annotations
 Model catalog→  Normalization (static caps)  │                     │      │                               Exec + tech reports
 Runtime tel. →     │                         │                     │   ┌──┴───────────────────────┐        Evidence bundles
                 Contextualization ──rules──> Selection ──plan──────┼──▶│ Harness = agent graph:   │        Tickets/notifs
                    │ (risk score G3)          (explain G5)          │   │  Attacker agent (PyRIT/  │        Audit trail
                    │                                                │   │   Garak/Promptfoo)       │
                 Gate engine (precedence G4/R9) ◀── findings ────────┼───│  Target (LiteLLM adapter │
                    │                                                │   │   → mock/real provider)  │
                 Governance / Audit / RBAC                           │   │  Judge quorum (LLM-judge │
                    │                                                │   │   + Presidio/Ragas)      │
                 Remediation (agent proposes, human approves) ◀──────┘   └──────────┬───────────────┘
                                                                                    │
                 Evidence store (hashed) ◀── every agent turn (OTel GenAI + Langfuse)┘
```

**Framework legend (what plugs in where):**

| Component | Primary framework | Role | Alternatives |
|---|---|---|---|
| Harness engine (Track A) | **Inspect AI** (UK AISI) | Task/Dataset/Sample/Solver/Scorer; eval logs = evidence | Promptfoo; DeepEval |
| Provider adapter (§6.12) | **LiteLLM** (SDK + proxy) | One OpenAI-format interface; cost/token/rate-limit accounting; virtual keys/budgets | OpenRouter; native SDKs behind an interface |
| Attacker agents (§8 harnesses) | **PyRIT** (Microsoft) + **Garak** (NVIDIA) | Automated adaptive red-team; injection/jailbreak/leak probes | DeepTeam; Promptfoo red-team |
| PII/leak detection | **Presidio** (Microsoft) | Deterministic PII scorer + evidence redaction (G9) | regex packs; cloud DLP |
| RAG scoring | **Ragas** | Retrieval-trust/faithfulness scorer | TruLens |
| Guardrails (inline, off-path) | **NeMo Guardrails / Llama Guard / Guardrails AI** | §6.17 inline checks, never the deep harness | Lakera Guard |
| Tracing / evidence | **OpenTelemetry GenAI** + **Langfuse** | Per-turn capture, replay, regression (§6.14) | Arize Phoenix; Braintrust |
| Orchestration | Inspect `eval()` (MVP) → **Temporal** (scale) | Durable multi-harness runs (§6.9) | Argo Workflows |
| Standards mapping | **OWASP LLM Top 10 · MITRE ATLAS · NIST AI RMF · ISO 42001 · EU AI Act** | Finding tags + contextualization control map | — |

Frontier-native services (**Bedrock Guardrails/Evals**, **Vertex Gen AI Eval / Model Armor**, **Azure AI Foundry Evals + AI Red Teaming Agent**, **OpenAI Evals API**, **Anthropic Agent SDK + MCP**) plug in as **optional adapter backends or scanners** — never as the foundation, to preserve R2/P4.

---

## 5. The agentic execution model

### 5.1 Agent roster (roles, not products)

| Agent | Plane | Makes decisions? | Backing framework | Isolation |
|---|---|---|---|---|
| **Orchestrator** | control | Sequences only (no policy) | Inspect `eval()` / Temporal | — |
| **Contextualization agent** | control (advisory) | **No** — proposes; rules decide (G3/G5) | LiteLLM + structured output | read-only |
| **Selection explainer** | control (advisory) | **No** — rules select; agent narrates | LiteLLM | read-only |
| **Attacker agent** | data | No — attempts, doesn't judge | PyRIT / Garak / Promptfoo | mock target only (A6) |
| **Target-under-test** | data | It's the asset | LiteLLM adapter → mock/real | sandboxed workspace (R7) |
| **Judge agents (quorum)** | data | Scores a finding, **not** the gate (A5) | Inspect scorer + LiteLLM; Presidio/Ragas | isolated context, no tools (A4) |
| **Gate engine** | control | **Yes** — deterministic (G4/R9) | rules, **no LLM** | — |
| **Remediation agent** | control (advisory) | **No** — drafts fix/ticket; human approves (A10) | LiteLLM | no write to prod |

### 5.2 How one harness runs (the agent graph)

Every one of the four baseline harnesses is a specialization of the same graph:

```text
 scenario sample (test evaluation case, seeded, synthetic)
        │
        ▼
 [Attacker agent] ──(adaptive, multi-turn)──▶ [Target-under-test via adapter] ──▶ observation
        ▲                                                                            │
        └──────────────── attack transcript (evidence, hashed) ◀─────────────────────┘
                                             │
                                             ▼
                        [Judge quorum: N independent judges, diverse lenses]
                         goal-integrity · data-leakage · policy-compliance
                                             │  majority/quorum → Finding
                                             ▼
                        normalize → Finding[] (OWASP/ATLAS-tagged) + metrics → result.json
```

The differences per harness are only: which **attacker** (PyRIT injection vs tool-abuse vs Garak leak vs RAG-poison), which **judges/detectors** (add Presidio for disclosure, Ragas for RAG), and the **scenario set**. The graph, contract, and evidence flow are identical — which is what makes them swappable (R3, §6.7).

### 5.3 Determinism & safety envelope (A-invariants applied at runtime)

- **Pin** model+version, temperature (0 where scoring), and seed per run; record all three in `result.json` (A7).
- **Quorum judging**: any finding ≥ `high` requires ≥3 independent judges with distinct lenses; a lone judge cannot raise a blocking finding (A5).
- **Judge isolation**: judges get only the transcript as structured input, run in a fresh context, have **no tools** and no memory shared with attacker/target — this is the anti-judge-injection control (A4).
- **Budgets**: per-run token/cost/turn/wall-clock ceilings enforced by the adapter; exceeding fails the run safe (never silent truncation) (A8).
- **Isolation**: attacker agents only reach the mock target on a network-denied local workspace; synthetic data only (A6/R7).

---

## 6. The 20 layers, bound to frameworks and agent roles

| Layer (v2) | MVP depth | Framework | Agentic role |
|---|---|---|---|
| 6.1 Discovery | LITE | manual API + SHA-256 (later: GitHub connector) | none |
| 6.2 Provenance/Lineage | FULL | SQL adjacency rows | none |
| 6.3 Quarantine | FULL (1 scanner) | Trivy/gitleaks + Garak static probes; **Promptfoo** injection patterns | optional triage agent (advisory) |
| 6.4 Normalization | FULL (static) | static capability map (JSONB raw) | none |
| 6.5 Intake | FULL | FastAPI/CLI | none |
| 6.6 Contextualization | FULL (YAML) | rules engine + **NIST/OWASP/ISO control map** | contextualization agent **proposes**, rules decide |
| 6.7 Registry | FULL | harness defs + JSON Schemas | none |
| 6.8 Selection | FULL | deterministic filter | selection explainer narrates |
| 6.9 Orchestration | LITE | Inspect `eval()` → Temporal | orchestrator |
| 6.10 Runner | FULL | **Inspect AI** task runner honoring G1 contract | hosts the harness agent graph |
| 6.11 Runtime Env | LITE | local temp dir, egress off → Docker | sandbox for attacker/target |
| 6.12 Adapter | FULL (mock→real) | **LiteLLM** | invocation path for all agents |
| 6.13 Evidence | FULL | DB + hashed FS; **OTel GenAI + Langfuse** | captures every agent turn (A3) |
| 6.14 Observability | DEFER | Langfuse/Phoenix dashboards | judge-calibration metrics (A9) |
| 6.15 Gate | FULL | precedence rule engine (**no LLM**) | gate engine (deterministic) |
| 6.16 Remediation | LITE | record + report | remediation agent **proposes** (A10) |
| 6.17 Telemetry/Replay | DEFER | trace schema + replay POC | replay uses recorded agent turns |
| 6.18 Governance/Audit | FULL (audit) | immutable audit events + Jinja2 reports | none |
| 6.19 RBAC/IAM | DEFER | local roles → OIDC | none |
| 6.20 Event Bus | LITE | transactional outbox → broker | none |

---

## 7. Data contracts extended for the agentic layer

The v2 contracts (`run_config.json`, `result.json`, `Finding`, risk weights, gate precedence, rule schema, asset key — G1–G7) stand unchanged. The agentic layer adds three:

### 7.1 `agent_turn` (new — the atomic unit of agentic evidence, satisfies A3)
```json
{
  "turn_id": "T-0007",
  "harness_run_id": "HR-0001",
  "role": "attacker | target | judge",
  "agent": "pyrit.injection.v1",
  "model": { "provider": "mock", "model": "mock-1", "version": "0.1.0", "temperature": 0, "seed": 42 },
  "input_hash": "sha256:...",
  "output_hash": "sha256:...",
  "input_uri": "/output/evidence/turns/T-0007.in.txt",
  "output_uri": "/output/evidence/turns/T-0007.out.txt",
  "tokens": { "in": 512, "out": 210 }, "cost_usd": 0.0,
  "latency_ms": 0, "ts": "2026-07-07T00:00:00Z"
}
```

### 7.2 `judge_verdict` (new — one judge's opinion; quorum aggregates these, satisfies A5)
```json
{
  "verdict_id": "V-0003", "finding_candidate_id": "FC-0001",
  "judge": "judge.goal_integrity.v1", "lens": "goal_integrity",
  "attack_succeeded": true, "confidence": 0.82,
  "rationale": "Target executed update_record after injected 'ignore previous instructions'.",
  "evidence_refs": ["T-0007"], "structured_only": true, "tools_used": []
}
```

### 7.3 `run_determinism` (new — the replay/audit block on every `result.json`, satisfies A7)
```json
{
  "seed": 42, "pinned_models": [{ "role": "target", "model": "mock-1", "version": "0.1.0" }],
  "quorum": { "min_judges": 3, "rule": "majority" },
  "budget": { "max_tokens": 200000, "max_cost_usd": 5.0, "max_turns": 20, "status": "within" },
  "replayable": true
}
```

Findings carry standards tags so evidence maps to audits:
```json
{ "...": "canonical Finding (G2)",
  "standards": { "owasp_llm": "LLM01", "mitre_atlas": "AML.T0051", "nist_ai_rmf": "MEASURE-2.7" } }
```

---

## 8. Ten agentic invariants (A1–A10) — extend R1–R9

| # | Invariant | Enforced by |
|---|---|---|
| A1 | Agents generate & judge; **deterministic policy decides**. No LLM in gate/risk path. | §1, §5.1, gate engine |
| A2 | Every agent model call routes through the adapter — no provider SDK in any agent (extends R2). | LiteLLM |
| A3 | Every agent turn (prompt/response/tool-call/judgment) is hashed evidence; runs replay from evidence (extends R6). | `agent_turn`, OTel+Langfuse |
| A4 | Judges are isolated: fresh context, structured-output only, **no tools**, no shared memory (anti-injection). | judge harness |
| A5 | Findings ≥ `high` require ≥N independent judges, diverse lenses, quorum decides the *finding* (not the gate). | `judge_verdict`, scorer |
| A6 | Attacker agents run only against isolated, synthetic, network-denied targets (extends R7). | runtime env |
| A7 | Determinism pinned: model+version, temperature, seed recorded per run; non-determinism bounded & disclosed. | `run_determinism` |
| A8 | Per-run budgets (tokens/cost/turns/wall-clock) enforced; exceed → **fail safe**, never silent truncation. | adapter/orchestrator |
| A9 | Judges calibrated against labeled ground-truth; judge accuracy tracked; a miscalibrated judge cannot gate. | eval harness for judges |
| A10 | Human-in-the-loop for irreversible/agentic remediation — agents propose, humans approve. | remediation workflow |

---

## 9. Tech stack — MVP vs enterprise

| Area | MVP | Enterprise |
|---|---|---|
| Harness engine | Inspect AI (local) | Inspect AI + hosted log store |
| Adapter | LiteLLM SDK + **mock provider** | LiteLLM **proxy** (keys/budgets/rate limits) |
| Red-team | PyRIT/Garak/Promptfoo as Inspect solvers | + DeepTeam, continuous red-team |
| Orchestration | Inspect `eval()`, sequential worker | Temporal (durable, parallel, retries) |
| Store | SQLite + hashed FS | Postgres + S3/MinIO + object lifecycle |
| Tracing | OTel → Langfuse (self-host) | Langfuse/Phoenix cluster + regression analytics |
| Isolation | local temp dir, egress off | Docker/Podman → K8s namespaces, default-deny egress |
| Events | transactional outbox | Kafka/Pulsar |
| Auth | local roles | OIDC/SSO, enterprise IdP |
| Reports | Jinja2 exec+tech | PDF evidence bundles |

---

## 10. Non-goals (MVP)

Kubernetes, Kafka, Temporal, enterprise IAM/SSO, SIEM, dynamic capability probing, runtime inline harness on the request path, multi-tenant isolation (carry `tenant_id` from day one per G12, but single-tenant runtime). Agents never take irreversible production actions (A10). The gate is never an LLM (A1).
