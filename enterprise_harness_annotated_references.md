# Enterprise AI Harness (`enterprise_harness.md`) — Annotated References for Team Review

**Owner:** Ivan Avelancio Jr.
**Type:** Companion / annotation document. **The original `enterprise_harness.md` is left intact and unmodified** — this file only *adds* reference items keyed to its sections.
**Purpose:** give the reviewing team, per section, external references and industry frameworks that **support** each architectural decision, and any that **contradict / create tension** with it (including internal inconsistencies), so the original can be reviewed on the evidence.

### How to use this document
1. Open `enterprise_harness.md` and this file side by side.
2. For each section, read the ✅ supportive and ⚠️ contradictory bullets, then answer the 🔎 review question.
3. Many tensions are already resolved in the follow-on docs — see cross-refs. This doc surfaces *why*, with citations.

### Legend
- ✅ **Supportive** — an external standard/framework/practice that backs the design.
- ⚠️ **Contradictory / tension** — a reference or practice that challenges the design, or an internal inconsistency to resolve.
- 🔎 **Review question** — a decision for the team.

### Verification note
Reference **names, maintainers, and standard identifiers** below are given for the team to look up current versions/URLs. Treat version numbers as "confirm latest." No URLs are asserted here.

---

## Top-of-scan: five recurring themes (before section detail)

**Strongly supported by industry practice (keep):**
- Control-plane / data-plane separation, provider independence, evidence chain-of-custody, off-critical-path runtime replay, explainable/deterministic harness selection. These align with NIST AI RMF, ISO/IEC 42001, OWASP LLM Top 10, and mainstream platform architecture.

**Systemic tension the team should decide first:**
- ⚠️ **"Implementation Notes" repeatedly prescribe enterprise-scale infra *as MVP*** — Kubernetes (§6.11), Temporal/Argo (§6.9), Kafka/Pulsar (§6.20), ClickHouse/Pinot/BigQuery (§6.14). This contradicts an MVP posture and is the single biggest review item. *Already corrected in `enterprise_harness_design.md` (v2) and `enterprise_harness_mvp_plan.md`, which downgrade these to `DEFER`.*
- ⚠️ **Under-specified config contracts** (runner I/O, finding schema, risk weights, gate aggregation) — the design specifies entities/APIs but not the JSON/YAML the system reads/writes. *Tracked as gaps G1–G14 in v2 §7 and resolved in the MVP plan + `enterprise_harness_spec_addendum_C1-C6.md`.*
- ⚠️ **Static prompt-injection "pattern" scanning (§6.3) is a semantic problem, not a regex problem** — see §6.3 below.

---

## §1 Executive Summary — "provider-independent enterprise AI assurance platform"
- ✅ **NIST AI RMF 1.0** and **NIST AI 600-1 (Generative AI Profile)** frame exactly this lifecycle (Govern/Map/Measure/Manage) — the platform is a Measure/Manage engine.
- ✅ **ISO/IEC 42001:2023** (AI management systems) and **ISO/IEC 23894:2023** (AI risk management) give the governance vocabulary this positioning sells into.
- ✅ **EU AI Act (Reg. (EU) 2024/1689)** high-risk obligations (risk management, logging, technical documentation) map to discover→gate→evidence.
- ✅ For regulated buyers: **SR 11-7** (US Federal Reserve model-risk-management guidance) legitimizes the "model risk management" framing.
- 🔎 Which framework is the **primary compliance anchor** for the first customer segment (NIST AI RMF vs ISO 42001 vs EU AI Act)? It drives the contextualization control-map.

## §2 Architecture Overview / §3 Control & Data Plane
- ✅ Control-plane/data-plane split is standard in security and data platforms (e.g., service-mesh and policy-engine architectures); it's what keeps decisions auditable.
- ✅ **OPA (Open Policy Agent) / Rego** is the canonical "policy engine in the control plane" reference.
- ⚠️ Tension the team should name: in an **agentic** harness, attacker/judge **agents** live in the data plane but their *outputs* influence decisions. Guardrail: *agents generate/judge; policy decides.* *See `enterprise_harness_architecture_v3.md §1` (invariant A1).*
- 🔎 Is the plane boundary enforced as a **code boundary** (import rules / package split), or only conceptually? Recommend the former.

## §4 End-to-End Workflow (10 steps)
- ✅ The discover→provenance→scan→normalize→contextualize→select→run→evidence→gate→remediate order matches **DevSecOps "shift-left" + supply-chain** pipelines (SLSA, in-toto).
- ⚠️ The source numbers the **provider adapter 12th (§6.12)** but it is a **step-7 dependency** (can't run a harness without it). Internal ordering tension. *Flagged in v2 §3.*
- 🔎 Should the canonical workflow diagram be redrawn to show the adapter as a step-7 dependency?

## §5 Core Data Model Overview
- ⚠️ **Internal defect:** this section is an **empty figure reference** — there is no actual entity model in the source. *Resolved in v2 §4 (explicit entity relationships).*
- ✅ For the lineage entities: **W3C PROV**, **OpenLineage**, and **CycloneDX ML-BOM / AI-BOM** are the reference models for asset/data/model provenance graphs.
- 🔎 Adopt an existing lineage vocabulary (OpenLineage/PROV) or keep bespoke adjacency rows? (Adjacency is fine for MVP; align field names to PROV for later interop.)

## §6.1 Discovery
- ✅ Content-hash change detection + canonical keys is standard; **SPDX / CycloneDX** (incl. **AI-BOM**) and **SLSA provenance** back the "know what exists + where it came from" goal.
- ✅ **Model Cards** (Mitchell et al.) and **Datasheets for Datasets** (Gebru et al.) are the reference metadata artifacts to attach at discovery.
- ⚠️ Source suggests starting with **GitHub + K8s + model catalog + artifact registry + CI/CD webhook** connectors — broad for an MVP. *v2 reduces to manual registration + SHA-256 first.*
- 🔎 Which **one** connector is the MVP source of truth (recommend Git)?

## §6.2 Provenance & Lineage
- ✅ Immutable per-version records align with **in-toto attestations** and **SLSA**; "adjacency rows now, graph DB only if needed" is sound **YAGNI**.
- ✅ **Sigstore/cosign** for signing provenance/attestations if integrity guarantees are needed.
- 🔎 Do any customers require **cryptographically signed** provenance (Sigstore) in MVP, or is hashing sufficient?

## §6.3 Quarantine & Security  ⚠️ (highest-scrutiny section)
- ✅ Static/supply-chain scanners have mature tools: **gitleaks / TruffleHog** (secrets), **Semgrep** (SAST), **Trivy** (vulns/containers), **Checkov / tfsec** (IaC), **Syft** (SBOM).
- ✅ Model-artifact scanning is a real, distinct vector: **ModelScan / Protect AI Guardian**, **picklescan** (malicious pickle/deserialization in model files) — more relevant than generic "malware" AV.
- ✅ AI-specific scanning maps to **OWASP LLM Top 10 (2025)** (LLM01 Prompt Injection, LLM03 Supply Chain, LLM05 Improper Output Handling) and **MITRE ATLAS** techniques.
- ⚠️ **Prompt injection is semantic, not a regex.** A static "prompt-injection-pattern scanner" (§6.3) has high false-negatives — injection resistance is a **behavioral** property best measured by a *harness*, not a static scan. Published bypasses of pattern filters support this. *v2/v3 move injection assurance to the behavioral harness (W3); keep static scan only as a cheap pre-filter.*
- ⚠️ "Malware scanner" for AI assets should be scoped to **model-file deserialization**, not framed as generic AV.
- 🔎 Agree to treat static injection scanning as advisory-only and rely on the behavioral harness for the blocking signal?

## §6.4 Provider-Agnostic Normalization
- ✅ The **OpenAI-compatible API** is the de-facto normalization surface; **LiteLLM** already normalizes 100+ providers to it. **OpenTelemetry GenAI semantic conventions** normalize the *observability* fields.
- ⚠️ Source's capability vocabulary is **open-ended** (feature names listed, not enumerated) — filters can't match reliably across providers (gap G8). *Close to a fixed enum.*
- 🔎 Adopt LiteLLM's model-metadata schema as the normalization baseline rather than inventing one?

## §6.5 Use Case Intake
- ✅ Maps to **NIST AI RMF "Map"** (context) and **EU AI Act risk categories**; data-class taxonomy (PII/PHI/PCI) aligns with **GDPR / HIPAA / PCI-DSS** scoping.
- 🔎 Should intake capture the **EU AI Act risk category** explicitly as a field (drives obligations)?

## §6.6 Contextualization
- ✅ **OPA/Rego** (policy-as-code) is the reference for versioned, auditable rules; **NIST AI RMF** and **EU AI Act** define the risk-tier logic; **FAIR** offers a risk-quantification model if weighted scoring proves too coarse.
- ⚠️ "Transparent weighted score" is specified **without weights** (gap G3); naive additive scoring can be **non-monotonic / gameable**. *v2 §5.4 + addendum define the weight table + tier thresholds; keep rationale per factor.*
- 🔎 Is a linear weighted score sufficient, or do high-severity single factors need hard floors (e.g., PII ⇒ minimum "high")? (v2 uses `risk_tier_floor`.)

## §6.7 Harness Registry
- ✅ Versioned, approved, swappable modules with I/O schemas matches **OCI artifacts + Sigstore signing** and **MLflow Model Registry** patterns.
- ⚠️ Input/output schema URIs are **placeholders** (gap G6) — registry can't validate a harness without the runner contract (G1).
- 🔎 Should harness images be **signed** (cosign) as a registry admission requirement?

## §6.8 Harness Selection & Policy
- ✅ Deterministic + explainable selection is directly supported by **audit/EU AI Act explainability** expectations; **OPA** can express the filter rules.
- ✅ Storing **skip rationale** is a genuine differentiator vs. generic eval tools.
- 🔎 None major — confirm skip-rationale is mandatory (v2 makes it so).

## §6.9 Evaluation Orchestration
- ✅ **Temporal** / **Argo Workflows** are the correct *scale* choices for durable, restart-surviving workflows.
- ⚠️ Source lists them as **Implementation Notes (i.e., MVP)** — over-engineered for a first slice. *v2 corrects to a DB-backed sequential worker + status machine for MVP; Temporal deferred.*
- 🔎 Define the **trigger to adopt Temporal** (first real parallel/durable-retry need) rather than adopting it upfront.

## §6.10 Harness Runner
- ✅ The `/input/run_config.json` → `/output/result.json` + `/output/evidence/*` contract mirrors **Inspect AI eval logs**, **OpenAI Evals**, and the sandbox-file convention — a proven pattern.
- ⚠️ **The contract is named but never defined (gap G1)** — the highest-priority blocker; nothing can be written against an undefined contract. *Resolved: v2 §5.1–5.2 + addendum.*
- 🔎 Adopt **Inspect AI** as the runner substrate (honoring this contract) vs. hand-rolling? (Recommended: adopt.)

## §6.11 Runtime Environment
- ✅ Isolation references: **K8s NetworkPolicy default-deny**, ephemeral namespaces, **seccomp**, and stronger sandboxes **gVisor / Firecracker microVMs**; **E2B / Modal** sandboxes for agent code.
- ⚠️ "Use **Kubernetes namespaces for MVP**" contradicts MVP scope. *v2: local temp dir / subprocess, egress off; Docker/Podman next; K8s deferred.*
- ⚠️ Counter-tension the team must weigh: if the harness ever executes **genuinely untrusted model/agent code**, subprocess isolation is insufficient — gVisor/microVM becomes necessary earlier than "later." MVP mitigates by running only **mock targets + synthetic data** (no untrusted code execution).
- 🔎 Will MVP ever load untrusted model *weights/code*, or only call models via API? (If only API, local isolation is adequate.)

## §6.12 Provider Adapter
- ✅ **LiteLLM** (SDK + proxy), **OpenRouter**, **Vercel AI SDK** are the reference provider-abstraction layers; LiteLLM proxy also supplies the **rate-limit / token / cost accounting** the source's `adapter_*` tables require.
- ⚠️ Building bespoke adapters per provider (implied) duplicates LiteLLM. *v2/v3: make LiteLLM the default implementation behind the adapter interface.*
- 🔎 LiteLLM **SDK vs proxy** for MVP? (Addendum default: SDK first, proxy at widening.)

## §6.13 Evidence Store
- ✅ Content-hashed artifacts + immutable metadata align with **content-addressed storage** and **S3 Object Lock (WORM)**; **OpenTelemetry GenAI** traces are audit-grade evidence; **Presidio** for redaction.
- ⚠️ The **Finding schema differs between §6.3 (quarantine) and §6.13 (evidence)** (gap G2) — findings can't be normalized/aggregated. *Resolved: single canonical Finding (v2 §5.3).*
- ⚠️ Retention/redaction "by data class" is **undefined** (gap G9) — a compliance risk for PII/PHI.
- 🔎 Confirm a single Finding schema and a retention/redaction matrix before build.

## §6.14 Observability & Analytics
- ✅ **OpenTelemetry GenAI semantic conventions** + **Langfuse** / **Arize Phoenix** / **Braintrust** are the reference LLM-eval-ops stack; regression-vs-baseline is standard.
- ⚠️ "Use **ClickHouse, Pinot, BigQuery, or Postgres** initially" over-specifies analytics infra for an MVP that the doc itself marks lower priority. *v2: DEFER; run-summary only.*
- 🔎 Defer analytics DB choice until there's data volume to justify it?

## §6.15 CI/CD Gate
- ✅ Policy gates map to **OPA / Conftest**, **DevSecOps shift-left**, and native **GitHub Actions / GitLab CI** integration; OWASP-based blocking criteria are defensible.
- ⚠️ Long-running harnesses **cannot block a PR synchronously** — the source's "async with callback" path is the correct one; the "sync for small checks" option needs a strict time budget. (Design note, not a defect.)
- 🔎 Define the **max synchronous gate latency** before falling back to async-with-callback.

## §6.16 Remediation Automation
- ✅ Maps to **SOAR** playbook patterns; human-in-the-loop for destructive actions is best practice.
- ⚠️ Automated **rollback / disable-tool / endpoint changes** are high-blast-radius; auto-executing them is risky. *v2/v3 defer destructive automation and require human approval (invariant A10).*
- 🔎 Confirm destructive remediation stays **human-approved** through MVP and beyond.

## §6.17 Runtime Telemetry & Replay / §7 Runtime Telemetry Architecture
- ✅ Keeping the **full harness off the synchronous request path** and doing shadow/replay off-path is the correct, widely-used pattern; **OpenTelemetry** + **Langfuse/Phoenix** support it; inline **guardrails** (NeMo Guardrails, Llama Guard, Lakera) may stay on-path.
- ⚠️ "**Sample aggressively** and redact" — uniform sampling can **miss rare safety failures**. For safety-critical events, bias sampling toward anomalies (importance/stratified sampling), or rare failures go unobserved.
- 🔎 Define a **sampling policy that over-samples flagged/anomalous traces**, not just uniform sampling.

## §6.18 Governance & Audit
- ✅ Immutable audit maps to **append-only + hash-chaining** logs; obligations map to **EU AI Act (record-keeping/logging, technical documentation)**, **ISO 42001**, **NIST AI RMF "Govern"**; **Model Cards** as the reporting artifact.
- 🔎 Do audit events need **tamper-evidence** (hash chain / signed) for the target compliance regime?

## §6.19 RBAC & IAM
- ✅ **OIDC / OAuth2 / SCIM** + enterprise IdP are the reference; **separation of duties** (waiver approver ≠ requester) is a standard control.
- ⚠️ "Local roles in config" is fine for MVP, but **SoD on waiver approval / gate override / evidence access** should be enforced (or at least logged as high-sensitivity) from day one — the source says as much; make sure it isn't dropped in MVP.
- 🔎 Which three actions are "high-sensitivity" from day one? (Recommend: waiver approval, gate override, evidence access.)

## §6.20 Event Bus
- ✅ **Transactional Outbox pattern** (microservices.io / Chris Richardson) is exactly right; **CloudEvents (CNCF)** is the reference **event envelope** (resolves undefined event payloads, gap G10); **Kafka / Pulsar** at scale.
- ⚠️ "Use Kafka, Pulsar, or cloud pub/sub" as an Implementation Note reads as MVP; the *pattern* (outbox) is what's required first. *v2: outbox + in-process consumer for MVP; broker deferred.*
- 🔎 Adopt **CloudEvents** as the envelope schema now (cheap, standards-based)?

## §8 MVP Build Plan
- ⚠️ **Internal defect:** the source §8 is **`TBD` / empty**. *Fully resolved in `enterprise_harness_mvp_plan.md` (tracer bullet, scope table, 30/60/90-day path) and the C1–C6 addendum.*
- ✅ The vertical-slice / **tracer-bullet** approach (thinnest complete thread before widening) is the industry-standard way to de-risk a multi-layer platform.
- 🔎 None — direct the team to the companion MVP plan + addendum.

---

## Consolidated reference index (for the team to pull URLs/versions)

**Governance & risk standards:** NIST AI RMF 1.0; NIST AI 600-1 (GenAI Profile); ISO/IEC 42001:2023; ISO/IEC 23894:2023; EU AI Act (Reg. (EU) 2024/1689); SR 11-7 (model risk); GDPR / HIPAA / PCI-DSS (data-class scoping).

**AI security taxonomies:** OWASP Top 10 for LLM Applications (2025); MITRE ATLAS.

**Supply chain & provenance:** SLSA; in-toto; Sigstore/cosign; CycloneDX (incl. ML-BOM/AI-BOM); SPDX; Syft; OpenLineage; W3C PROV; Model Cards; Datasheets for Datasets.

**Scanners:** gitleaks; TruffleHog; Semgrep; Trivy; Checkov; tfsec; ModelScan / Protect AI Guardian; picklescan.

**Eval / harness engines:** Inspect AI (UK AI Security Institute); Promptfoo; DeepEval / DeepTeam (Confident AI); OpenAI Evals.

**Red-team:** PyRIT (Microsoft); garak (NVIDIA); DeepTeam; Promptfoo red-team.

**Provider abstraction:** LiteLLM (BerriAI); OpenRouter; Vercel AI SDK; OpenAI-compatible API standard.

**Guardrails / detectors:** NeMo Guardrails (NVIDIA); Llama Guard (Meta); Guardrails AI; Lakera Guard; Presidio (Microsoft, PII); Ragas (RAG eval).

**Observability / evidence:** OpenTelemetry GenAI semantic conventions; Langfuse; Arize Phoenix; Braintrust.

**Policy / orchestration / events / isolation:** OPA/Rego; Conftest; Temporal; Argo Workflows; CloudEvents (CNCF); Transactional Outbox pattern; Kafka; Pulsar; gVisor; Firecracker; E2B; Kubernetes NetworkPolicy.

**Frontier-native enterprise services (optional backends):** AWS Bedrock (Guardrails/Evaluations); Google Vertex AI (Gen AI Evaluation, Model Armor); Azure AI Foundry (Evaluations, AI Red Teaming Agent); OpenAI Evals API; Anthropic Claude Agent SDK + MCP.

---

## Cross-references (where tensions are already resolved)
- `enterprise_harness_design.md` (v2) — fixes the empty §5 data model, the `TBD` §8, and downgrades K8s/Temporal/Kafka/ClickHouse from MVP; defines R1–R9 and gaps G1–G14.
- `enterprise_harness_mvp_plan.md` — tracer-bullet MVP + config-contract schemas (G1–G14).
- `enterprise_harness_architecture_v3.md` / `_agentic_workflows.md` / `_architecture_review.md` — the agentic execution model (A1–A10) and the framework stack bound to each layer.
- `enterprise_harness_spec_addendum_C1-C6.md` — resolves the final build-blocking conditions.

*This annotation file adds review context only; `enterprise_harness.md` remains the untouched source of record.*
