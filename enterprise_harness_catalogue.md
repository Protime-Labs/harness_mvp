# Enterprise Harness Catalogue & Reference Architecture (v1)

**Owner:** Ivan Avelancio Jr. · **Customer context:** AT&T · **Source of truth for the harness layer.**
**Transcribed from:** `Harness_vis4.jpg` / `Enterprise_harness_platform_arch_v2.drawio` (verbatim titles + outputs).
**Classifies:** all 20 baseline harnesses (5 categories × 4) **+ H1.5 Bias & Fairness** (Test, added Phase-1 per AT&T decision — closes HTML-review F2) = **21** — by a formal schema, with dependencies, workflow binding, and packaging — the registry seed for `harness_definitions`.
**Companions:** `enterprise_harness_architecture_v3.md` (planes/invariants), `_agentic_workflows.md` (W-workflows), `_visuals_correlation.md` (why this exists).

> **How this is articulated (the method).** A catalogue of 20 harnesses is only useful if every entry is described the *same way* and its place in the system is unambiguous. So this doc is built in four moves: **(1) a classification schema** (§2 — the dimensions every harness is tagged by), **(2) 20 classified spec cards** (§4), **(3) a dependency DAG + workflow binding** (§5–§6 — the process order and which gate each feeds), and **(4) cross-cutting matrices** (§7–§9 — capability coverage, controls coverage, pack composition). This is the reference architecture for the harness layer; it slots beneath the platform reference architecture in `architecture_v3.md`.

---

## 1. Terminology (locked, per `_visuals_correlation.md §3`)

- **Harness Category** = one of the 5 in the catalogue (Test / Exposure / Remediation / Resilience / Governance). *Never* "Layer" — that word is reserved for the 20 **Platform Layers** (§6.1–§6.20).
- **Harness (runner)** = an executable module honoring the run contract (R3): `run_config.json` → `result.json` + evidence.
- **Harness Pack** = a *tiered, tagged configuration* of one or more runners (Foundational / Advanced Capability / AT&T Context). The Pack is what the Registry catalogs and the Selector picks; the runner is what executes.
- **Gate** = a deterministic decision instance (W8) with fixed vocabulary (approve/warn/block/manual_review). The named gates (Security Pass, Eval Pass, Approval Gate, Pipeline Gate) are instances.

---

## 2. Classification schema (the dimensions every harness is tagged by)

| Dimension | Allowed values |
|---|---|
| **Category** | Test · Exposure · Remediation · Resilience · Governance |
| **Execution type** | `benchmark` (dataset scoring) · `adversarial-agentic` (attacker agent) · `scanner` (deterministic scan) · `fault-injection` (chaos/degradation) · `action-verify` (apply+verify a change) · `policy-attest` (map to controls / aggregate evidence) |
| **Plane** | `data` (executes against a target) · `control-verify` (verifies a control-plane behavior) |
| **Target under test** | model · agent · RAG · tool/MCP · runtime-infra · control-plane · remediation-action |
| **Driver** (test input) | dataset · attacker-agent(PyRIT/Garak/Promptfoo) · fault-injector · IaC-applier · evidence-aggregator · none |
| **Scorer** | LLM-judge-quorum · deterministic-detector(Presidio/Ragas/regex/secret) · metric(RTO/RPO/SLO/cost) · control-map · human(HITL) |
| **Pack tier (primary)** | Foundational · Advanced Capability · AT&T Context |
| **Blocking capable** | yes / no |
| **Determinism class** | `deterministic` · `bounded-agentic` (A7/C5) |
| **Feeds gate** | Security Pass · Eval Pass · Approval Gate · Pipeline Gate |
| **MVP phase** | 1 (MVP) · 2 · 3 |

**Canonical ID:** `H<category>.<n>` → `H1.1 … H5.4`.

---

## 3. Dependency taxonomy (what "dependencies" means per harness)

Each card's **Depends on** lists, in order: **frameworks** → **platform layers (§6.x)** → **data** (scenario/ground-truth/benchmark) → **upstream harnesses** (DAG edges) → **upstream gate**. A harness cannot be selected (W2) unless its dependencies are satisfiable; unmet deps produce a **skip rationale** (R5).

---

## 4. The 20 harnesses — classified spec cards

### Category 1 — Test Harnesses (baseline quality; runs first)

#### H1.1 — Model Behavior & Capability Benchmark · Foundational · Phase 2
**Class:** Test · `benchmark` · data · target: model · driver: dataset · scorer: metric+thresholds · blocking:no · `deterministic` · gate: Eval Pass.
**Tests (verbatim):** baseline quality across reasoning, coding, multimodal, tool-use, latency, throughput, cost, open-weight compatibility.
**Outputs (verbatim):** scorecard, pass/fail thresholds, model compatibility matrix.
**Capabilities:** extended reasoning, coding, multimodal, tool use/MCP, reliability, latency, throughput, open-weight availability.
**Depends on:** Inspect AI + LiteLLM (Model Router); §6.4/6.10/6.12/6.13; benchmark dataset; upstream gate: Security Pass.
**Controls:** NIST AI RMF Measure; (no direct OWASP) · Golden(model-risk).
**Invariants:** A2, A3, A7, A8.

#### H1.2 — Adversarial Robustness & Red-Team Scenario · Foundational · **Phase 1**
**Class:** Test · `adversarial-agentic` · data · target: model/agent · driver: PyRIT/Garak · scorer: LLM-judge-quorum · blocking:yes · `bounded-agentic` · gate: Eval Pass.
**Tests:** jailbreaks, refusal-bypass, stress prompts, malformed inputs, adversarial scenario suites.
**Outputs:** adversarial risk score, exploit examples, mitigation notes.
**Capabilities:** adversarial robustness, agentic behavior, reliability.
**Depends on:** Inspect, LiteLLM, PyRIT/Garak; §6.10/6.11/6.12/6.13; scenarios + ground-truth (C1); gate: Security Pass. **Shares the MVP Colab substrate.**
**Controls:** OWASP LLM01/LLM05 · ATLAS: Jailbreak, Prompt Injection · Golden(model-risk).
**Invariants:** A2–A8.

#### H1.3 — Safety / Policy / Harm Evaluation · Foundational · **Phase 1**
**Class:** Test · `adversarial-agentic`+`scanner` · data · target: model/agent · driver: attacker-agent · scorer: LLM-judge-quorum + policy-classifier (Llama Guard) · blocking:yes · `bounded-agentic` · gate: Eval Pass.
**Tests:** unsafe output, harmful instructions, policy conformance, protected-class sensitivity, controlled-content boundaries.
**Outputs:** safety verdict, blocked categories, evidence artifacts.
**Capabilities:** reliability, adversarial robustness, security controls.
**Depends on:** Inspect, LiteLLM, Llama Guard/NeMo Guardrails; §6.10/6.13; safety scenario set; gate: Security Pass.
**Controls:** OWASP LLM05/LLM09 · Golden(data-policy, acceptable-use).
**Invariants:** A4, A5, A9 (judge calibration), A3.

#### H1.4 — Hallucination & Grounding · Foundational · Phase 2
**Class:** Test · `adversarial-agentic` · data · target: model/RAG · driver: dataset+attacker · scorer: Ragas + LLM-judge · blocking:no · `bounded-agentic` · gate: Eval Pass.
**Tests:** factuality, grounded answers, citation quality, RAG support, uncertainty handling, answer consistency.
**Outputs:** grounding score, source-mismatch findings, regression set.
**Capabilities:** hallucination resistance, reliability.
**Depends on:** Inspect, LiteLLM, **Ragas**; §6.10/6.13; grounding dataset + RAG mock index; gate: Security Pass.
**Controls:** OWASP LLM09 (Misinformation) · Golden(model-risk).
**Invariants:** A3, A5, A9.

#### H1.5 — Bias & Fairness · Foundational · **Phase 1**  *(added per AT&T decision — closes HTML-review F2)*
**Class:** Test · `adversarial-agentic`+`benchmark` · data · target: model/agent · driver: fairness prompt set (Glasswing pillar / custom) · scorer: LLM-judge-quorum + protected-attribute rubric · blocking:yes · `bounded-agentic` · gate: Eval Pass.
**Tests:** stereotyping & unfair treatment across protected attributes — gender · race · religion · age · disability · orientation · political · loaded premises.
**Outputs:** fairness/bias score, disparate-treatment findings, evidence artifacts.
**Capabilities:** reliability, security controls, adversarial robustness.
**Depends on:** Inspect, LiteLLM; §6.10/6.13; bias scenario set + ground-truth (C1); gate: Security Pass.
**Controls:** OWASP LLM09 (partial) · Golden(fairness, protected-class) · EU AI Act (non-discrimination) · ISO 42001.
**Invariants:** A4, A5, A9, A3.

### Category 2 — Exposure Harnesses (find vulnerabilities; the MVP core)

#### H2.1 — Prompt-Injection & Tool-Abuse Exposure · Foundational · **Phase 1 (MVP tracer)**
**Class:** Exposure · `adversarial-agentic` · data · target: agent/tool-MCP · driver: PyRIT/Promptfoo · scorer: LLM-judge-quorum(goal_integrity, tool_safety) + tool side-effect log · blocking:yes · `bounded-agentic` · gate: Eval Pass.
**Tests:** direct/indirect prompt injection, MCP/tool boundary abuse, unauthorized tool invocation, agent instruction override.
**Outputs:** exposure chain, affected tool, required policy control.
**Capabilities:** prompt-injection resistance, tool use/MCP, agentic behavior.
**Depends on:** Inspect, LiteLLM, PyRIT/Promptfoo; §6.10/6.11/6.12/6.13; scenarios + ground-truth (C1); gate: Security Pass. **← implemented in `enterprise_harness_mvp_colab.ipynb` (W3/W4).**
**Controls:** OWASP LLM01/LLM06/LLM07 · ATLAS: Prompt Injection · Golden(tool-egress, change-mgmt).
**Invariants:** A2–A8.

#### H2.2 — Exploit Chain & Cyber Misuse · Advanced Capability (Cyber) · Phase 2
**Class:** Exposure · `adversarial-agentic` · data · target: model/agent · driver: PyRIT/Garak(cyber probes) · scorer: LLM-judge-quorum + kill-switch heuristic · blocking:yes · `bounded-agentic` · gate: Eval Pass.
**Tests:** model-assisted cyber capability misuse, exploit-chain generation, unsafe code-execution paths, dual-use escalation.
**Outputs:** cyber misuse score, chain graph, **kill-switch recommendation**.
**Capabilities:** cyber capabilities, coding, adversarial robustness.
**Depends on:** Inspect, LiteLLM, Garak/PyRIT; §6.10/6.11/6.13; cyber scenario set; upstream: H1.2 (adversarial baseline); gate: Security Pass.
**Controls:** OWASP LLM05 · ATLAS: dual-use / exfiltration · Golden(security-controls, auto-stop).
**Invariants:** A4, A5, A6, A8 (kill-switch = auto-stop).

#### H2.3 — Data Privacy & Leakage Exposure · Foundational (+AT&T Context for CPNI) · **Phase 1**
**Class:** Exposure · `adversarial-agentic`+`scanner` · data · target: model/RAG · driver: Garak(leak) · scorer: **Presidio (PII/CPNI, floors judges)** + LLM-judge(data_leakage) · blocking:yes · `bounded-agentic` · gate: Eval Pass.
**Tests:** PII/**CPNI**/secrets leakage, training/retention assumptions, RAG leakage, embeddings leakage, cross-context disclosure.
**Outputs:** data-exposure severity, data-class mapping, remediation action.
**Capabilities:** data privacy, security controls.
**Depends on:** Inspect, LiteLLM, **Presidio (+ CPNI recognizer)**; §6.10/6.13; synthetic PII/CPNI fixtures + ground-truth; gate: Security Pass. **← partly in the MVP Colab (`sensitive_disclosure`).**
**Controls:** OWASP LLM02/LLM07/LLM08 · Golden(data-policy, CPNI-handling).
**Invariants:** A4, A5, A9, G9 (redaction).

#### H2.4 — Context & Business-Impact Validation · AT&T Context · Phase 2
**Class:** Exposure · `policy-attest` · control-verify · target: use-case/asset · driver: evidence-aggregator+rules · scorer: control-map(business-impact rules) · blocking:yes · `deterministic` · gate: Approval Gate.
**Tests:** use-case context, asset criticality, business impact, operational blast radius, safe routing decisions.
**Outputs:** business-impact tier, **model-router constraint**, compensating controls.
**Capabilities:** enterprise integration, reliability.
**Depends on:** rules engine (W1 contextualization), §6.2 lineage, §6.6; use-case intake; upstream: H2.1–H2.3 findings; gate: Eval Pass.
**Controls:** NIST AI RMF Map · Golden(business-impact, model-router).
**Invariants:** A1 (rules decide), A3.

### Category 3 — Remediation Harnesses (fix what Exposure found; heavy, Phase 3)

#### H3.1 — Safe Remediation Execution · AT&T Context · Phase 3
**Class:** Remediation · `action-verify` · data+control-verify · target: remediation-action · driver: none(applies approved fix) · scorer: control-map + **HITL** · blocking:yes · `deterministic` · gate: Approval Gate.
**Tests:** constrains automated fixes to approved actions, checks privileges, validates change preconditions, avoids unsafe self-remediation.
**Outputs:** approved fix path, action evidence, **human-approval requirement**.
**Capabilities:** security controls, enterprise integration.
**Depends on:** §6.16 remediation, §6.19 RBAC; approved-action catalogue; upstream: H2.1–H2.4 findings; gate: Approval Gate. **Requires A10 HITL.**
**Controls:** Golden(change-mgmt, least-privilege, HITL).
**Invariants:** A10, A1, A3.

#### H3.2 — IaC / Terraform / Playbook Remediation · AT&T Context · Phase 3
**Class:** Remediation · `action-verify` · control-verify · target: runtime-infra · driver: IaC-applier(Terraform/Ansible) · scorer: control-map(post-state) · blocking:yes · `deterministic` · gate: Approval Gate.
**Tests:** applies approved IaC, guardrail, network, IAM, logging, policy templates to close gaps.
**Outputs:** change record, control closure, rollback handle.
**Capabilities:** enterprise integration, security controls, deployment flexibility.
**Depends on:** Terraform/OPA, §6.11/6.16; IaC template library; upstream: H3.1 approval; gate: Approval Gate.
**Controls:** Golden(change-mgmt, network-egress, logging) · ISO 42001.
**Invariants:** A10, A3.

#### H3.3 — Rollback & Retest · Foundational · Phase 3
**Class:** Remediation · `action-verify` · data · target: model/agent/runtime · driver: none · scorer: metric(regression) + reruns prior harness · blocking:yes · `deterministic` · gate: Pipeline Gate.
**Tests:** rollback behavior, regression tests, after-action retest, before/after evidence capture.
**Outputs:** rollback success, retest verdict, evidence bundle.
**Capabilities:** reliability, deployment flexibility.
**Depends on:** §6.9/6.13/6.17; version/lineage (§6.2); upstream: H3.1/H3.2 applied change; gate: Approval Gate.
**Controls:** Golden(change-mgmt, rollback) · ISO 42001.
**Invariants:** A3, A7 (deterministic retest), C4 (replay).

#### H3.4 — Blast-Radius & Change-Risk · AT&T Context · Phase 3
**Class:** Remediation · `policy-attest` · control-verify · target: control-plane · driver: evidence-aggregator+lineage · scorer: control-map(risk) · blocking:yes · `deterministic` · gate: Approval Gate.
**Tests:** dependencies, impacted assets, tool permissions, data paths, downstream safety/regression impact.
**Outputs:** blast-radius report, risk-acceptance or remediation gate.
**Capabilities:** enterprise integration, security controls.
**Depends on:** §6.2 lineage (blast-radius query), §6.6; upstream: H2.4 business-impact; gate: Eval Pass.
**Controls:** Golden(change-mgmt, business-impact) · NIST Manage.
**Invariants:** A1, A3.

### Category 4 — Resilience Harnesses (runtime/infra failure behavior; Phase 3)

#### H4.1 — Control-Failure / Degraded-Ops · AT&T Context · Phase 3
**Class:** Resilience · `fault-injection` · control-verify · target: control-plane · driver: fault-injector · scorer: metric(fail-open/closed) · blocking:yes · `deterministic` · gate: Pipeline Gate.
**Tests:** fail-open/fail-closed behavior for guardrails, identity, logging, policy service, network egress, evidence store.
**Outputs:** degraded-mode verdict, fail-safe gaps, runbook updates.
**Capabilities:** security controls, reliability.
**Depends on:** chaos/fault-injection (§6.11), §6.13/6.19/6.20; runtime env (Docker/K8s); gate: Eval Pass.
**Controls:** Golden(fail-safe, availability) · ISO 42001.
**Invariants:** A8 (fail-closed), A3.

#### H4.2 — Failover & Recovery / RTO-RPO · Advanced Capability · Phase 3
**Class:** Resilience · `fault-injection` · data · target: runtime-infra/Model Router · driver: fault-injector · scorer: metric(RTO/RPO) · blocking:yes · `deterministic` · gate: Pipeline Gate.
**Tests:** provider/model/runtime failover, fallback-model selection, state recovery, RTO/RPO targets.
**Outputs:** recovery metrics, fallback route, model-availability score.
**Capabilities:** deployment flexibility, reliability, enterprise integration.
**Depends on:** **Model Router** (§6.12), §6.11; multi-provider adapters (LiteLLM); gate: Eval Pass.
**Controls:** Golden(availability, DR) · ISO 42001.
**Invariants:** A2, A3.

#### H4.3 — Agent Coordination / Heartbeat · Advanced Capability (Agentic) · Phase 3
**Class:** Resilience · `fault-injection` · data · target: agent · driver: fault-injector · scorer: metric(coordination health) · blocking:yes · `deterministic` · gate: Pipeline Gate.
**Tests:** *Cisco-style* agent heartbeat, watchdogs, stale-agent detection, auto-block, **auto-stop** behavior.
**Outputs:** coordination health score, blocked agent/task, heartbeat evidence.
**Capabilities:** agentic behavior, reliability, security controls.
**Depends on:** §6.11/6.20; agent runtime + heartbeat bus; upstream: H2.1 (agentic exposure); gate: Eval Pass.
**Controls:** Golden(auto-stop, agent-governance).
**Invariants:** A8 (auto-stop), A6, A3.

#### H4.4 — Latency / Throughput / Cost Budget · Foundational · Phase 2
**Class:** Resilience · `fault-injection` · data · target: model/runtime · driver: load-generator · scorer: metric(SLO/cost) · blocking:no · `deterministic` · gate: Pipeline Gate.
**Tests:** overload, budget caps, rate limits, token exhaustion, queueing, throttling, cost-aware routing.
**Outputs:** SLO report, cost guardrail, performance envelope.
**Capabilities:** latency, throughput, cost/latency, enterprise integration.
**Depends on:** **LiteLLM proxy** (budgets/rate-limits), §6.12/6.14; load profiles; gate: Eval Pass.
**Controls:** OWASP LLM10 (Unbounded Consumption) · Golden(cost, SLO).
**Invariants:** A8 (budgets/C6), A3.

### Category 5 — Governance Harnesses (verify governance; cheap — reuse evidence; Phase 2)

#### H5.1 — Finding Lifecycle / Evidence / Verdict · Foundational · **Phase 1**
**Class:** Governance · `policy-attest` · control-verify · target: control-plane · driver: evidence-aggregator · scorer: control-map(schema+lifecycle) · blocking:no · `deterministic` · gate: Approval Gate.
**Tests:** *Cisco-style* lifecycle for states, verdicts, severity, reproduction steps, evidence artifacts, artifact/agent fingerprints.
**Outputs:** immutable finding record, verdict, evidence package.
**Capabilities:** security controls, enterprise integration.
**Depends on:** Finding schema (G2), §6.13/6.18; **all upstream harness findings**; gate: Eval Pass. **← largely realized in the MVP Colab (Finding + verdict + evidence + Mode-A replay).**
**Controls:** Golden(evidence, audit) · ISO 42001.
**Invariants:** A3, A5 (verdict), C4 (replay).

#### H5.2 — Auditability & Explainability · Foundational · Phase 2
**Class:** Governance · `policy-attest` · control-verify · target: control-plane · driver: evidence-aggregator(OTel/Langfuse) · scorer: control-map(trace completeness) · blocking:no · `deterministic` · gate: Approval Gate.
**Tests:** model/tool/agent traces, rationale, explainability artifacts, reviewer notes, end-to-end action history.
**Outputs:** audit trail, explanation bundle, reviewer view.
**Capabilities:** enterprise integration, reliability.
**Depends on:** OTel GenAI + Langfuse, §6.13/6.18; agent_turn evidence (A3); all upstream traces; gate: Eval Pass.
**Controls:** Golden(audit, explainability) · EU AI Act logging · ISO 42001.
**Invariants:** A3.

#### H5.3 — Policy Compliance / Golden Controls · AT&T Context · Phase 2
**Class:** Governance · `policy-attest` · control-verify · target: control-plane · driver: evidence-aggregator · scorer: **control-map → AT&T Golden Controls + ISO 42001** · blocking:yes · `deterministic` · gate: Approval Gate.
**Tests:** maps results to **AT&T Golden Controls**, ISO 42001, LLM/agentic threat models, data policy, security exceptions.
**Outputs:** control coverage, gap report, approval recommendation.
**Capabilities:** security controls, enterprise integration.
**Depends on:** OPA/Rego + Golden Controls catalogue (**AT&T to supply IDs**), §6.6/6.18; all upstream findings; gate: Eval Pass.
**Controls:** **Golden Controls (primary)** · ISO 42001 · OWASP LLM Top 10 (cross-tag) · MITRE ATLAS.
**Invariants:** A1, A3.

#### H5.4 — Human Approval & Model Risk Gate · AT&T Context · Phase 2
**Class:** Governance · `policy-attest`+`human` · control-verify · target: control-plane · driver: none · scorer: **HITL** + control-map(model-risk) · blocking:yes · `deterministic` · gate: **Approval Gate**.
**Tests:** HITL approval, exception workflows, risk acceptance, high-risk tool/model approval, compensating controls.
**Outputs:** approval record, conditional pass, expiration/retest date.
**Capabilities:** security controls, enterprise integration.
**Depends on:** §6.18/6.19, waiver/approval store (G13); upstream: H5.3 gap report; gate: Approval Gate. **This IS the Approval Gate for high-risk.**
**Controls:** Golden(model-risk, HITL, exception) · SR 11-7 (model risk).
**Invariants:** A10, A1, A3.

---

## 5. Harness dependency DAG & execution order (the process workflow)

```text
                    ┌─────────────── FRONT DOOR (agents; deterministic gates) ───────────────┐
  Request/Model ──▶ │ W-A Source Agent ──[Source Allowed]──▶ W-B Security Agent ──[Security Pass] │
                    └───────────────────────────────────────────────────────────┬────────────┘
                                                                                 ▼  SANDBOX EVAL
    ┌──────────────── run in parallel where independent ────────────────────────────────────┐
    │  Cat 1 TEST (H1.1 benchmark, H1.2 adversarial, H1.3 safety, H1.4 hallucination)         │
    │  Cat 2 EXPOSURE (H2.1 inj/tool, H2.2 exploit, H2.3 data/CPNI, H2.4 business-impact*)     │
    │  Cat 4 RESILIENCE (H4.1 control-fail, H4.2 failover, H4.3 heartbeat, H4.4 cost)          │
    └───────────────────────────────┬──────────────────────────────────────────────────────┘
                                     │ findings + evidence
                                     ▼
        Cat 3 REMEDIATION (needs findings): H3.4 blast-radius → H3.1 safe-exec → H3.2 IaC → H3.3 rollback/retest
                                     │ (H3.1/H3.2 require A10 HITL)
                                     ▼
        Cat 5 GOVERNANCE (consumes ALL evidence): H5.1 finding-lifecycle · H5.2 audit · H5.3 golden-controls
                                     │
                                     ▼  H5.4 Human Approval & Model Risk ──[Approval Gate]──▶
        Context + Registry ──[Pipeline Gate]──▶ Deploy ──▶ Observe/Feedback ──(evolve packs)──╮
        ▲───────────────────────────────────────────────────────────────────────────────────╯
```
*H2.4 depends on the H2.1–H2.3 findings; it feeds the Model Router constraint.

**Ordering rules:** (1) nothing runs before **Security Pass** (R7/A6). (2) **Test + Exposure + Resilience** are independent → parallelizable. (3) **Remediation** consumes Exposure findings (edge: H2.* → H3.*). (4) **Governance** consumes *everything* and owns the **Approval Gate**. (5) The **Feedback loop** re-evolves packs (`new version`) → re-enters at Registry.

---

## 6. Workflow binding (harness → E2E step → gate → W-workflow)

| E2E step (vis2) | Gate | Harnesses active | W-workflow |
|---|---|---|---|
| 2 Source Agent | Source Allowed | — (discovery) | **W-A** |
| 3 Security Agent | Security Pass | quarantine scanners (SBOM/secrets/malware/license/policy/sandbox) | **W-B** |
| 4 Studio UI/SDK | — | (authoring; no eval) | Harness Studio |
| 5 Sandbox Eval | Eval Pass | **Cat 1, Cat 2, Cat 4** | W0→W3–W6, W7 |
| 6 Context + Registry | Approval Gate | **Cat 3, Cat 5** | W1, W2, W8, W9 |
| 7 Deploy Harness | Pipeline Gate | H3.3 retest, H4.* runtime checks | W0/W8 |
| 8 Observe + Feedback | — | telemetry/replay → evolve packs | §6.17, feedback |

---

## 7. Capability coverage matrix (15-tag taxonomy → covering harnesses)

| Capability tag | Covered by |
|---|---|
| Extended reasoning | H1.1 |
| Cyber capabilities | H2.2 |
| Coding | H1.1, H2.2 |
| Multimodal | H1.1 |
| Tool use / MCP | H2.1 |
| Agentic behavior | H1.2, H2.1, H4.3 |
| Reliability | H1.3, H1.4, H3.3, H4.1, H4.4, H5.2 |
| Hallucination resistance | H1.4 |
| Adversarial robustness | H1.2, H1.3, H2.2 |
| Prompt-injection resistance | H2.1 |
| Data privacy | H2.3 |
| Security controls | H1.3, H2.3, H3.*, H4.1, H4.3, H5.1, H5.3, H5.4 |
| Enterprise integration | H2.4, H3.2, H3.4, H4.2, H4.4, H5.* |
| Deployment flexibility | H3.2, H3.3, H4.2 |
| Open-weight availability | H1.1 |

Gaps to note: **Multimodal** and **Extended reasoning** are only covered by H1.1 — if AT&T needs deeper multimodal/reasoning assurance, add Advanced Capability variants of H1.1.

---

## 8. Standards & Golden Controls coverage (governance view)

- **OWASP LLM Top 10 (2025):** LLM01 → H2.1/H1.2; LLM02 → H2.3; LLM05 → H2.2/H1.3; LLM06 → H2.1; LLM07 → H2.3/H2.1; LLM08 → H2.3; LLM09 → H1.4/H1.3; LLM10 → H4.4. (LLM03 Supply-chain, LLM04 Poisoning → covered at the Security Agent front door, W-B.)
- **MITRE ATLAS:** offensive harnesses (H1.2, H2.1, H2.2, H2.3) carry ATLAS technique tags (Prompt Injection, Jailbreak, Exfiltration, dual-use). *Confirm exact AML.T IDs with the ATLAS matrix before publishing.*
- **ISO/IEC 42001 & EU AI Act:** governance harnesses (H5.*) produce the management-system + logging evidence.
- **AT&T Golden Controls (primary anchor):** mapped by **H5.3**. **AT&T must supply the Golden Controls catalogue (IDs + text);** until then H5.3 maps to control *domains*: identity, logging/audit, data-policy (**CPNI**), network-egress, change-mgmt, availability/fail-safe, model-risk, HITL, cost/SLO.

---

## 9. Pack composition model (how harnesses bundle per model + use-case)

Per the vis4 packaging model — each harness tagged Foundational / Advanced Capability / AT&T Context, then composed into a runnable pack by the Selector (W2):

| Pack | Contents | Applies to |
|---|---|---|
| **Foundational** (every model) | H1.1, H1.2, H1.3, H1.4, H2.1, H2.3, H3.3, H4.4, H5.1, H5.2 | all sources/models |
| **Advanced — Cyber** | + H2.2 | code/cyber-capable models |
| **Advanced — Agentic** | + H4.3, + H2.1(tool-abuse depth) | agents / MCP tools |
| **Advanced — Availability** | + H4.1, H4.2 | production-critical runtimes |
| **AT&T Context Pack** | + H2.4, H3.1, H3.2, H3.4, H5.3, H5.4, + CPNI recognizers in H2.3 | any AT&T production use-case |

**Selection rule (W2):** `pack = Foundational ∪ (Advanced by capability_tags of the asset) ∪ (AT&T Context if use_case.tenant == AT&T)`, filtered by satisfiable dependencies, with skip rationale for the rest (R5).

---

## 10. Phasing (maps to the MVP → widening path)

| Phase | Harnesses | Rationale |
|---|---|---|
| **Phase 1 (MVP)** | H2.1 (tracer, done) · H1.2 · H1.3 · H2.3 · **H1.5 Bias & Fairness** · H5.1 | all data-plane agentic/scanner + finding-lifecycle; **reuse the Colab substrate**; proves the full spine on the Foundational core |
| **Phase 2** | H1.1 · H1.4 · H2.2 · H2.4 · H4.4 · H5.2 · H5.3 · H5.4 | governance is cheap (reuses evidence/audit); adds capability benchmarks + cost/SLO; lights up the Approval Gate + Golden Controls |
| **Phase 3** | H3.1–H3.4 · H4.1 · H4.2 · H4.3 | heavy: needs action-execution (IaC/HITL), chaos/fault-injection, Model Router failover, real runtime (Docker/K8s) |

---

## 11. Registry seed schema (how this catalogue becomes data)

Each card populates one `harness_definitions` row. Extend the v2 registry (§6.7) with the reconciliation fields:

```json
{
  "id": "H2.1", "name": "Prompt-Injection & Tool-Abuse Exposure", "version": "0.1.0",
  "category": "exposure", "execution_type": "adversarial-agentic", "plane": "data",
  "target": ["agent", "tool_mcp"], "driver": ["pyrit", "promptfoo"],
  "scorer": ["llm_judge_quorum", "tool_side_effect_log"],
  "pack_tier": "foundational",
  "capability_tags": ["prompt_injection_resistance", "tool_use_mcp", "agentic_behavior"],
  "blocking_capable": true, "determinism_class": "bounded_agentic",
  "feeds_gate": "eval_pass", "mvp_phase": 1,
  "depends_on": { "frameworks": ["inspect_ai","litellm","pyrit"], "platform_layers": ["6.10","6.11","6.12","6.13"],
                  "data": ["scenarios/prompt_injection/baseline_v1","gt/prompt_injection"],
                  "upstream_harnesses": [], "upstream_gate": "security_pass" },
  "standards": { "owasp_llm": ["LLM01","LLM06","LLM07"], "mitre_atlas": ["prompt_injection"],
                 "golden_control_domains": ["tool_egress","change_mgmt"], "iso_42001": true },
  "input_schema_uri": "contracts/run_config.schema.json",
  "output_schema_uri": "contracts/result.schema.json",
  "status": "approved"
}
```

This row is what the Selector (W2) filters and the Registry (§6.7) approves. The 20 cards above are the seed set.

---

*This catalogue is the harness-layer reference architecture: a fixed classification schema, 20 classified entries, a dependency DAG bound to the workflow and its gates, and a pack model that composes them per model + use-case. It is the single source of truth the visuals implied; `harness_definitions` is seeded directly from §11.*
