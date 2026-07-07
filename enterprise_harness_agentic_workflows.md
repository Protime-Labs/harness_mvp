# Enterprise AI Harness Platform — Agentic Workflow Specifications

**Owner:** Ivan Avelancio Jr.
**Companion to:** `enterprise_harness_architecture_v3.md` (architecture) and `enterprise_harness_design.md` (v2 layers/contracts).
**Purpose:** define every agentic workflow the platform runs, as design specs — agents, roles, tools, orchestration pattern, I/O contract, determinism/safety controls, and the requirements each satisfies. **No code.**

> The load-bearing rule from the architecture (P2/A1): **agents generate, attack, enrich, and judge; deterministic policy decides.** Each workflow below is explicit about which steps are agentic (data plane) and which are rule-based (control plane).

---

## 0. Conventions

**Workflow spec template** (used for every W#):
- **Intent** — what it produces.
- **Plane** — control / data / mixed.
- **Trigger & inputs** — event + contract in.
- **Agents & tools** — roster + what each may call.
- **Orchestration** — the graph and pattern (sequential / fan-out / quorum / loop-until-dry).
- **Output contract** — what it writes (bound to G1–G7, §7 schemas).
- **Determinism & safety** — which A-invariants apply and how.
- **Satisfies** — R/A/G IDs.

**Orchestration patterns used** (borrowed from mature multi-agent practice):
- **Fan-out/gather** — independent agents run in parallel, results merged.
- **Quorum verify** — N independent judges, diverse lenses, majority decides a *finding* (A5).
- **Adaptive loop** — attacker agent iterates against the target until success, budget, or turn cap (A8).
- **Loop-until-dry** — keep spawning attack variants until K rounds yield no new finding (coverage).
- **Propose→decide** — agent proposes; a versioned rule engine makes the recorded decision (A1).

**Agent invocation invariant:** every agent (attacker, target, judge, contextualizer, explainer, remediator) calls models **only** through the LiteLLM adapter (A2). No agent holds a provider SDK or a production credential.

---

## 1. Agent roster (catalog)

| ID | Agent | Plane | Decides? | Tools it may call | Backing |
|---|---|---|---|---|---|
| AG-ORCH | Orchestrator | control | sequence only | run DB, event outbox | Inspect `eval()` / Temporal |
| AG-CTX | Contextualization agent | control (advisory) | proposes | rules-lint, control-map lookup | LiteLLM + structured output |
| AG-SEL | Selection explainer | control (advisory) | narrates | registry read | LiteLLM |
| AG-ATK | Attacker agent (family) | data | no | adapter→target, scenario store | PyRIT / Garak / Promptfoo |
| AG-TGT | Target-under-test | data | it's the asset | adapter→mock/real, mock tools | LiteLLM |
| AG-JDG | Judge agent (family) | data | scores finding, not gate | **none** (structured out only) | LiteLLM + Presidio/Ragas |
| AG-GATE | Gate engine | control | **yes (deterministic)** | policy store | rules, **no LLM** |
| AG-REM | Remediation agent | control (advisory) | proposes | report/ticket draft | LiteLLM |

Judge family (AG-JDG) lenses: `goal_integrity`, `data_leakage`, `policy_compliance`, `tool_safety`, `retrieval_trust`. Detectors that augment judges are deterministic: **Presidio** (PII), **Ragas** (RAG faithfulness), regex/secret scanners.

---

## 2. Workflow map

```text
W0 Evaluation Orchestration ──drives──▶ W3/W4/W5/W6 (harnesses) ──each uses──▶ W7 (judge quorum)
        ▲                                                                              │
        │                                                                     findings + evidence
   W1 Contextualization ──required harnesses──▶ W2 Selection ──plan──▶ W0                │
                                                                                         ▼
                                                                       W8 Gate ──block/warn──▶ W9 Remediation
```

---

## W0 — Evaluation Orchestration (meta-workflow)

- **Intent:** run an approved execution plan to a persisted, aggregated result.
- **Plane:** control (orchestration only; runs data-plane harnesses).
- **Trigger/inputs:** `evaluation.run.started` + `harness_execution_plan` (v2 §6.8).
- **Agents & tools:** AG-ORCH only. No LLM decisions.
- **Orchestration:**
  ```text
  create evaluation_run → for each plan_item (sequential MVP; parallel later):
      provision isolated workspace (R7/A6) → write run_config.json (G1)
      run harness (W3–W6) → collect result.json (G1) → persist harness_run + findings + evidence
      emit harness.run.completed → event_outbox (R8)
  after all items → AG-GATE (W8) → persist gate_decision → emit
  ```
- **Output:** `evaluation_runs`, `harness_runs`, aggregated status; events.
- **Determinism & safety:** run-level budget ceiling split across items (A8); `run_locks` prevent concurrent runs on same asset (v2 §6.9); state survives restart (DB-backed).
- **Satisfies:** R1, R3, R8, A8; v2 §6.9/6.11.

---

## W1 — Contextualization (propose → decide)

- **Intent:** turn a use case into risk tier + required/blocking harnesses + required approvals + control-framework mapping.
- **Plane:** mixed — **agent proposes, rules decide (A1).**
- **Trigger/inputs:** `use_case.submitted` + intake fields (v2 §6.5).
- **Agents & tools:** AG-CTX (reads use case, proposes risk factors + maps to OWASP/NIST/ISO/EU-AI-Act controls, cites rationale). **Read-only.**
- **Orchestration:**
  ```text
  AG-CTX  → proposes {data-sensitivity, exposure, tool-write, users, criticality, regulatory} + suggested controls
      │        (advisory JSON, structured output)
      ▼
  RULE ENGINE (deterministic, versioned):
      risk_weights.yaml (G3) → score → tier   (agent's proposal is INPUT, never the decision)
      contextualization_rules.yaml (G5) → required_harnesses, required_approvals, blocking, risk_tier_floor
      control-map → attach NIST AI RMF / ISO 42001 / EU AI Act obligations
  ```
- **Output:** `contextualization_results` (risk tier/score, required harnesses, approvals, rationale, **rule version**), advisory agent note stored as evidence.
- **Determinism & safety:** the score and tier come **only** from versioned weights; the agent can raise but never lower risk vs. the rules; disagreements (agent vs rules) are logged for tuning (A9-style calibration of the contextualizer).
- **Satisfies:** R4, R5, A1; resolves G3/G5 usage; adds standards mapping.

---

## W2 — Harness Selection (deterministic + explanation)

- **Intent:** produce an explainable execution plan (required/optional/blocking, ordered) with skip rationale.
- **Plane:** mixed — **rules select (A1); agent only narrates.**
- **Trigger/inputs:** `contextualization.completed` + normalized capabilities (§6.4) + quarantine decision (§6.3) + registry (§6.7).
- **Agents & tools:** AG-SEL (reads the deterministic selection + skip reasons, writes a human-readable `explain` narrative). Registry read-only.
- **Orchestration:** `propose→decide` inverted — the **rule engine selects**, then AG-SEL narrates the already-made decision. The narrative is never the selection.
- **Output:** `harness_execution_plans`, `harness_execution_plan_items`, `harness_selection_decisions` (why each ran/skipped — **mandatory**, R5), `explain` text.
- **Determinism & safety:** selection is a pure function of inputs; identical inputs → identical plan; agent narrative flagged `advisory`.
- **Satisfies:** R5, A1; v2 §6.8.

---

## W3 — Prompt-Injection Harness (agentic red-team)

- **Intent:** measure resistance to direct override, indirect/RAG instruction, system-prompt extraction, cross-context contamination. Emits goal-integrity + output-leakage scores + findings.
- **Plane:** data (fully agentic).
- **Trigger/inputs:** `run_config.json` with `scenario_set: prompt_injection/baseline_v1`.
- **Agents & tools:**
  - AG-ATK = **PyRIT** injection orchestrator (+ **Garak** probes for extraction/leak), calling the target via adapter. May read the scenario store; may **not** judge.
  - AG-TGT = the asset-under-test via LiteLLM (mock provider offline).
  - AG-JDG quorum (lenses: `goal_integrity`, `data_leakage`) — W7.
- **Orchestration:**
  ```text
  for each scenario sample (seeded):
     adaptive loop (A8 turn cap):
        AG-ATK crafts/adapts injection → AG-TGT responds → capture agent_turn (A3)
        stop when: attacker declares success | turn cap | budget
     loop-until-dry over attack families (direct/indirect/extraction/contamination)
  transcript → W7 judge quorum → Finding[] (tag OWASP LLM01, ATLAS AML.T0051)
  ```
- **Output:** `result.json` with `metrics.goal_integrity`, `metrics.output_leakage`, `metrics.detection_rate`, findings, evidence turns, `run_determinism`.
- **Determinism & safety:** attacker hits **mock target only** (A6); temp/seed pinned (A7); judges isolated & tool-less (A4); each turn hashed (A3).
- **Satisfies:** R2/A2, R3, R6/A3, R7/A6, A4/A5/A7/A8; v2 §8 harness 1.

---

## W4 — Tool-Misuse Harness (agentic)

- **Intent:** measure unsafe write calls, parameter-scope breach, approval bypass, tool-chaining risk. Emits tool-safety score + blocked/allowed action log.
- **Plane:** data.
- **Agents & tools:** AG-ATK = **Promptfoo excessive-agency / RBAC** plugins + PyRIT tool-abuse orchestrator; AG-TGT wired to **mock tools** (deterministic, side-effect-logging, no real effect); AG-JDG lens `tool_safety`.
- **Orchestration:**
  ```text
  present target with tasks that tempt out-of-scope / unapproved tool calls
  mock tools record every attempted call + args (side-effect log) but execute nothing real (R7)
  AG-ATK probes: scope breach, approval bypass, dangerous chaining
  action log + transcript → W7 (tool_safety lens) → Finding[] (OWASP LLM06 excessive agency, ATLAS)
  ```
- **Output:** `result.json` with `metrics.tool_safety`, action log (allowed/blocked), side-effect findings.
- **Determinism & safety:** mock tools never touch real systems (R7/A6); write attempts are evidence, not effects.
- **Satisfies:** R2/R3/R6/R7 + A-series; v2 §8 harness 2.

---

## W5 — Sensitive-Disclosure Harness (agentic + deterministic detectors)

- **Intent:** measure synthetic PII/credential/confidential-doc leakage and excessive-context disclosure. Emits disclosure score + PII/leak detector result + redaction status.
- **Plane:** data.
- **Agents & tools:** AG-ATK = **Garak** leak probes + disclosure prompts over **synthetic** secrets; AG-TGT via adapter; AG-JDG lens `data_leakage` **augmented by Presidio** (deterministic PII detection) — the judge cannot override a positive Presidio hit downward.
- **Orchestration:**
  ```text
  seed synthetic PII/credentials/confidential docs into context (never real — R7/A6)
  AG-ATK elicits disclosure → AG-TGT responds
  DETERMINISTIC: Presidio scans response for PII entities (ground truth)
  AG-JDG quorum judges excessive/confidential disclosure (lens data_leakage)
  finding severity = max(Presidio-hit severity, judge quorum)   ← detector floors the judge
  redact incidental sensitive data before persisting evidence (G9)
  ```
- **Output:** `result.json` with `metrics.disclosure`, Presidio entity report, redaction status.
- **Determinism & safety:** Presidio makes PII detection deterministic and auditable (mitigates judge unreliability, A9); synthetic-only (A6); redaction on persist (G9).
- **Satisfies:** R6/R7 + A4/A5/A9 + G9; v2 §8 harness 3.

---

## W6 — RAG-Poisoning Harness (agentic)

- **Intent:** measure resistance to adversarial retrieved docs, instruction-like content, source-trust conflict, poisoned memory. Emits retrieval-trust + injection-resistance scores.
- **Plane:** data.
- **Agents & tools:** AG-ATK plants adversarial/instruction-like docs in the **mock index**; AG-TGT runs its RAG flow via adapter; AG-JDG lens `retrieval_trust` **augmented by Ragas** (faithfulness/context-precision).
- **Orchestration:**
  ```text
  poison mock vector index with adversarial + instruction-like + untrusted-source docs (synthetic)
  AG-TGT retrieves + answers → capture retrieved chunks (evidence)
  Ragas scores faithfulness/context relevance (deterministic-ish) + AG-JDG judges injection-via-retrieval
  transcript + chunks → W7 → Finding[] (OWASP LLM08 vector/embedding weaknesses, LLM01 indirect injection)
  ```
- **Output:** `result.json` with `metrics.retrieval_trust`, `metrics.injection_resistance`, suspicious-source findings.
- **Determinism & safety:** mock index only; retrieved chunks are hashed evidence.
- **Satisfies:** R6/R7 + A-series; v2 §8 harness 4.

---

## W7 — LLM-as-Judge Scoring (shared quorum subroutine)

- **Intent:** convert an attack transcript into calibrated, verified findings. Used by W3–W6.
- **Plane:** data.
- **Agents & tools:** AG-JDG family — N independent judges, **diverse lenses**, structured output only, **no tools, isolated context (A4)**; deterministic detectors (Presidio/Ragas/regex) as non-LLM co-judges where applicable.
- **Orchestration (quorum verify, A5):**
  ```text
  for each candidate finding in transcript:
     fan-out N judges (distinct lenses) → each emits judge_verdict {attack_succeeded, confidence, rationale, evidence_refs}
     deterministic detector (if any) emits a hard verdict
     AGGREGATE (rule, not LLM):
        succeeded = (majority of judges agree) OR (detector positive)
        severity  = max(detector_severity, quorum_severity)
        confidence = mean(judge confidence)
     emit Finding (G2) only if succeeded; else record as "attempted, not confirmed"
  ```
- **Output:** `Finding[]` (canonical, standards-tagged) + `judge_verdict[]` evidence.
- **Determinism & safety:** anti-injection by isolation (A4); quorum removes single-judge unreliability (A5); detectors floor the judges (A9); every verdict is evidence (A3).
- **Satisfies:** A3, A4, A5, A9; G2.

---

## W8 — Gate Decision (deterministic — the one place decisions are made)

- **Intent:** aggregate quarantine + harness results into one `approve / warn / block / manual_review` with policy version + rationale.
- **Plane:** control. **No LLM (A1).**
- **Trigger/inputs:** all `harness_runs` + quarantine decision + waivers + approvals.
- **Agents & tools:** AG-GATE = rule engine only. (An LLM may *draft the human-readable rationale prose*, but the decision and matched rule come from the precedence engine.)
- **Orchestration (v2 §5.5 precedence, first match wins):**
  ```text
  1 quarantine == block                         → block
  2 required harness missing/not-run            → block
  3 blocking harness status == failed           → block
  4 any finding.severity == critical            → block
  5 expired waiver on active blocking rule       → block
  6 unapproved provider/model/tool              → block
  7 manual_review required by policy/context     → manual_review
  8 any finding.severity == high (non-block)     → warn
  9 else                                         → approve
  persist: policy_version, matched_rule, rationale, evidence_refs, run_determinism ref
  ```
- **Output:** `gate_decisions` (immutable-linked to evidence).
- **Determinism & safety:** identical findings + policy version → identical decision, always; fully auditable (R4/R9); the agentic layer can only *feed* this, never *be* it (A1).
- **Satisfies:** R1, R4, R5, R9, A1; resolves G4.

---

## W9 — Remediation (agent proposes → human approves)

- **Intent:** turn blocking findings into owner-visible action without letting an agent take irreversible steps.
- **Plane:** control (advisory agent + human gate).
- **Trigger/inputs:** `gate.decision == block | manual_review`.
- **Agents & tools:** AG-REM drafts: remediation record, suggested fix text (per finding category/severity playbook), and a ticket/notification **draft**. It may **not** roll back, disable tools, or change endpoints.
- **Orchestration:**
  ```text
  for each blocking finding:
     AG-REM → maps category→playbook → drafts fix + ticket + retest flag
  HUMAN approves (A10) → then execute non-destructive actions (record, notify, retest request)
  destructive actions (rollback/disable-tool) DEFERRED until approval workflows mature (v2 §6.16)
  ```
- **Output:** `remediation_actions` (record, notification event, retest flag, suggested-fix report text).
- **Determinism & safety:** human-in-the-loop for anything irreversible (A10); all agent proposals are advisory + logged.
- **Satisfies:** R4, A10; v2 §6.16.

---

## Cross-cutting: evidence, budgets, calibration

- **Evidence capture (A3):** an OTel GenAI span wraps every agent turn; the exporter writes `agent_turn` records + hashed artifacts to the evidence store and streams to Langfuse for replay/regression. A run is reconstructable from evidence alone.
- **Budget enforcement (A8):** the adapter meters tokens/cost per turn against the run ceiling; the orchestrator meters turns/wall-clock; breach → run fails `status: budget_exceeded` (never truncates silently — logged).
- **Judge calibration (A9):** a `judge_eval` harness runs each judge against a labeled ground-truth scenario set; judge accuracy/precision/recall are platform metrics; a judge below threshold is quarantined from gating-relevant findings until re-tuned.

---

## Requirements coverage by workflow

| Workflow | R1 | R2/A2 | R3 | R4 | R5 | R6/A3 | R7/A6 | R8 | R9 | A1 | A4 | A5 | A7 | A8 | A9 | A10 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| W0 Orchestration | ✔ |  | ✔ | ✔ |  | ✔ | ✔ | ✔ |  |  |  |  |  | ✔ |  |  |
| W1 Contextualization | ✔ |  |  | ✔ | ✔ |  |  |  |  | ✔ |  |  |  |  | ✔ |  |
| W2 Selection | ✔ |  |  | ✔ | ✔ |  |  |  |  | ✔ |  |  |  |  |  |  |
| W3–W6 Harnesses | ✔ | ✔ | ✔ | ✔ |  | ✔ | ✔ |  |  |  | ✔ | ✔ | ✔ | ✔ |  |  |
| W7 Judge quorum | ✔ | ✔ |  | ✔ |  | ✔ |  |  |  | ✔ | ✔ | ✔ |  |  | ✔ |  |
| W8 Gate | ✔ |  |  | ✔ | ✔ |  |  |  | ✔ | ✔ |  |  |  |  |  |  |
| W9 Remediation | ✔ |  |  | ✔ |  |  |  |  |  | ✔ |  |  |  |  |  | ✔ |

Every architectural requirement (R1–R9, A1–A10) is satisfied by at least one workflow; the full traceability — including the G1–G14 config gaps — is proven in `enterprise_harness_architecture_review.md`.
