# Enterprise AI Harness Platform — Architecture Review & Requirements Traceability

**Owner:** Ivan Avelancio Jr.
**Reviews:** `enterprise_harness_architecture_v3.md` + `enterprise_harness_agentic_workflows.md`, against `enterprise_harness_design.md` (R1–R9, G1–G14, 20 layers) and `enterprise_harness_mvp_plan.md` (DoD).
**Verdict:** **Approve to build Track A, then Track B — with 6 conditions (C1–C6) resolved first.** No blocking architectural defect. The agentic model is sound *because* every decision remains deterministic.

---

## 1. Review method

Checked the v3 architecture and the 10 workflows against four rubrics:
1. **Requirement coverage** — every R1–R9, A1–A10, and G1–G14 traced to a component/workflow that satisfies it.
2. **Layer coverage** — all 20 v2 layers accounted for at declared depth.
3. **Failure-mode analysis** — new risks introduced specifically by the agentic design.
4. **Buildability** — can a functional MVP produce results for the test evaluation cases without the deferred enterprise infrastructure?

---

## 2. Executive verdict

**Strengths**
- The **"agents generate & judge; policy decides"** split (P2/A1) resolves the core tension of an agentic assurance tool: it stays auditable (R4), explainable (R5), and deterministic at the gate (R9) while using non-deterministic agents where they add value (attack generation, judging).
- **Adopting Inspect AI + LiteLLM + PyRIT/Garak/Promptfoo** collapses the highest-risk, least-specified part of the v2 plan (the harness runner + the four harnesses) onto mature, provider-independent substrate — turning months of bespoke eval-engine work into integration work.
- **Provider independence is preserved end-to-end**: extending R2 to A2 (every agent calls the adapter) means even the attacker and judge agents are provider-agnostic.
- **Evidence-as-replay (A3)** makes non-deterministic runs reproducible and audit-grade — the strongest answer to "how do you trust an agentic evaluator."

**Weaknesses / conditions to clear (C1–C6 in §6).** All are resolvable in design before scaffolding; none is architectural rework.

---

## 3. Requirements traceability — R1–R9 (v2)

| Req | Requirement | Satisfied by | Status |
|---|---|---|---|
| R1 | Control/data plane code boundary | §1 split; W8 gate has no LLM; agents confined to data plane | ✅ |
| R2 | Provider independence, no SDK in harnesses | LiteLLM adapter; extended to A2 (all agents) | ✅ |
| R3 | Standard runner contract (`run_config`/`result`/`evidence`) | Track boundary §3; Inspect honors G1 contract | ✅ |
| R4 | Everything versioned; provenance/audit immutable | rule versions on every decision; `run_determinism`; audit events | ✅ |
| R5 | Explainable selection (why ran/skipped) | W2 `harness_selection_decisions` (mandatory) + AG-SEL narrative | ✅ |
| R6 | Evidence = hashed chain of custody; findings link evidence | §7 `agent_turn`; every finding → `evidence_uri`; A3 | ✅ |
| R7 | No production coupling — isolation, synthetic, deny-egress | §5.3; A6; mock targets/tools/index in W4/W5/W6 | ✅ |
| R8 | Transactional outbox for events | W0 writes `event_outbox` | ✅ |
| R9 | Fixed decision vocabulary | W8 precedence engine; quarantine/gate enums unchanged | ✅ |

## 3b. Requirements traceability — A1–A10 (new, agentic)

| Req | Enforced by | Status | Note |
|---|---|---|---|
| A1 | Agents propose; W8 gate + W1 rules decide (no LLM) | ✅ | The keystone invariant. |
| A2 | LiteLLM for attacker/target/judge/ctx/remediation | ✅ | Verify no framework smuggles a native SDK (C2). |
| A3 | `agent_turn` + OTel/Langfuse; replay from evidence | ✅ | Replay fidelity to be proven in POC (C4). |
| A4 | Judge isolation: fresh context, no tools, structured-only | ✅ | Anti-judge-injection. |
| A5 | Quorum ≥N judges, diverse lenses, majority | ✅ | Set N + tie-break policy (C3). |
| A6 | Attacker → mock target only, synthetic, deny-egress | ✅ | Enforced by runtime env. |
| A7 | Pin model/version/temp/seed; record per run | ✅ | Real providers cap determinism — disclosed, not guaranteed (C5). |
| A8 | Per-run token/cost/turn/wall-clock ceilings; fail-safe | ✅ | Define default ceilings (C6). |
| A9 | Judge calibration vs labeled ground truth | ⚠️ | Requires a labeled scenario set — **C1**, the top pre-build task. |
| A10 | Human approves irreversible remediation | ✅ | Destructive actions deferred anyway. |

## 3c. Config-gap resolution — G1–G14 (v2 §7)

| Gap | Resolution in v3 | Status |
|---|---|---|
| G1 runner contract | v2 §5.1/5.2 unchanged; Inspect adapts to it | ✅ |
| G2 finding schema | canonical `Finding` + `standards` tags (OWASP/ATLAS/NIST) | ✅ enhanced |
| G3 risk formula | v2 `risk_weights.yaml`; agent proposes, weights decide | ✅ |
| G4 gate aggregation | W8 precedence engine | ✅ |
| G5 contextualization rules | v2 rule schema + control-map | ✅ |
| G6 harness I/O schema URIs | bound to G1 + per-harness scenario schema | ✅ |
| G7 asset key | v2 §5.7 unchanged | ✅ |
| G8 capability vocabulary | closed enum (still to enumerate — minor) | ⚠️ small |
| G9 evidence retention/redaction | Presidio redaction on persist (W5) + retention matrix | ✅ |
| G10 event payload schema | envelope `{event,resource_id,version,ts,payload_hash,payload}` | ✅ |
| G11 synthetic data / mock targets | seeded fixtures per harness (W3–W6); mock provider/tools/index | ✅ |
| G12 multi-tenancy | single-tenant runtime, `tenant_id` column from day one | ✅ |
| G13 waiver ↔ gate | expired-waiver rule in W8 | ✅ |
| G14 SAFETY.md | still required as first repo file (unchanged) | ⚠️ pending write |

**New gap surfaced by the agentic design:**
| G15 | **Judge ground-truth / calibration set undefined.** Without labeled attack-success examples, judge accuracy (A9) can't be measured and quorum thresholds are guesses. | Define a small labeled scenario set per harness (known-success + known-refusal). **This is C1.** |

---

## 4. Layer coverage (all 20 accounted for)

Every v2 layer maps to a component + framework + agentic role in `architecture_v3.md §6`. No layer is dropped; DEFER layers (6.14 Observability, 6.17 Telemetry/Replay, 6.19 RBAC) match the v2 MVP depth. Agentic additions (judge calibration in 6.14, replay from agent turns in 6.17) *reuse* deferred layers without pulling them forward.

---

## 5. Risk register (agentic-specific)

| # | Risk | Likelihood × Impact | Mitigation | Residual |
|---|---|---|---|---|
| K1 | **Judge is itself prompt-injectable** (transcript contains attacker text). | Med × High | A4 isolation: judge gets structured transcript, no tools, fresh context; deterministic detectors floor judges (Presidio/Ragas). | Low |
| K2 | **Single judge unreliable / hallucinated finding.** | High × Med | A5 quorum, diverse lenses, majority; detector co-judge. | Low |
| K3 | **Non-determinism → flaky gate.** | Med × High | Gate is rule-based (A1); findings feed it; determinism pinned (A7); flaky *findings* surfaced by re-run variance metric. | Low–Med |
| K4 | **Attacker agent cost/token blow-up.** | Med × Med | A8 budgets fail-safe; loop-until-dry has round cap; mock provider is free offline. | Low |
| K5 | **Framework smuggles a provider SDK / breaks R2.** | Low × High | A2 audit: all model I/O through adapter; CI check that harness deps don't import provider SDKs. | Low |
| K6 | **Real attacker payloads leak into logs / are reused unsafely.** | Med × High | SAFETY.md (G14); synthetic-only (A6); redaction on persist (G9); network-deny. | Low |
| K7 | **Judge calibration drift over model upgrades.** | Med × Med | A9 periodic calibration vs ground truth; pin judge model+version (A7); alert on accuracy drop. | Med |
| K8 | **Over-trust in agentic contextualizer lowering risk.** | Low × High | A1: agent can only raise, never lower, vs rules; rule floor (`risk_tier_floor`). | Low |
| K9 | **Vendor lock to Inspect/LiteLLM.** | Low × Med | Both Apache-2.0, self-hostable; the G1 contract is the abstraction — engine is swappable (Promptfoo fallback). | Low |

No risk is un-mitigable at the architecture level; K3 and K7 carry a residual that observability (6.14) manages over time.

---

## 6. Conditions to clear before scaffolding (C1–C6)

| # | Condition | Why it blocks a *correct* build | Effort |
|---|---|---|---|
| **C1** | **Author the judge ground-truth set** (per harness: N known-success + N known-refusal, labeled). | Without it, A9 calibration and A5 quorum thresholds are unmeasurable — the harness could report confident-but-wrong results. Resolves new gap G15. | S (design) |
| **C2** | **Confirm the adapter boundary** — pick LiteLLM SDK-vs-proxy for MVP and verify PyRIT/Garak/Inspect can all be pointed at it (no native SDK path). | Protects R2/A2/K5. | S |
| **C3** | **Fix quorum params** — N judges, lens set, tie-break, and the detector-floors-judge rule. | Determines finding reliability (A5). | S |
| **C4** | **Prove replay** — POC that a run reconstructs from `agent_turn` evidence alone. | Validates A3/R6, the audit story. | M |
| **C5** | **Determinism policy for real providers** — document that temp/seed pinning bounds but doesn't guarantee determinism; define acceptable variance. | Sets honest expectations (A7); avoids false "reproducible" claims. | S |
| **C6** | **Default budget ceilings** — tokens/cost/turns/wall-clock per harness run. | Prevents K4; makes A8 concrete. | S |

All six are **design decisions**, resolvable in a short spec pass — none requires code. That is why the review approves *design-complete, build-ready* rather than *build-now*.

---

## 7. Architecture Decision Records (concise)

- **ADR-1: Agents generate & judge; policy decides.** *Accepted.* Alternative (LLM makes gate calls) rejected — breaks R4/R5/R9.
- **ADR-2: Adopt Inspect AI as the harness substrate.** *Accepted.* Alternatives Promptfoo-only (weaker task/scoring model) and build-from-scratch (months, duplicative) rejected; Promptfoo kept as red-team plugin source + fallback engine.
- **ADR-3: LiteLLM as the single model I/O path.** *Accepted.* Gives R2 + cost/rate accounting free; native SDKs rejected as harness dependencies.
- **ADR-4: Multi-judge quorum + deterministic detectors, not single LLM judge.** *Accepted.* Single-judge rejected (K1/K2).
- **ADR-5: Standards tags on every finding (OWASP LLM / ATLAS / NIST).** *Accepted.* Cheap now, load-bearing for enterprise buyers; retrofitting rejected as expensive.
- **ADR-6: Track A before Track B.** *Accepted.* Produces results for the test evaluation cases first (the "functional MVP" ask); governance wrapper built around a working core.

---

## 8. Open decisions for Ivan (need a call before/with the build spec)

1. **Judge model policy (C1/C3/K7):** should judges use a *different* provider/model family than the target-under-test (reduces correlated blind spots) — and are you willing to spend real tokens on judging in MVP, or judge with the mock/offline path first?
2. **MVP adapter form (C2):** LiteLLM **SDK** (simplest, in-process) vs **proxy** (gets you keys/budgets/rate-limits but adds a service). I recommend **SDK for the tracer bullet, proxy at Track B widening.**
3. **First real provider (post-mock):** Anthropic (Claude Agent SDK + MCP aligns with your MCP-server asset type) vs an OpenAI-compatible endpoint. I recommend **Anthropic first** given the MCP asset story.
4. **Orchestration jump point:** stay on Inspect `eval()` / sequential worker until when — number of harnesses, or first real parallel/durable need — before introducing Temporal?
5. **Standards scope for MVP:** OWASP LLM Top 10 tagging is cheap; do you also want NIST AI RMF / ISO 42001 / EU AI Act obligation mapping in the MVP contextualization, or defer to Track B?

---

## 9. Recommended path (design-complete → build)

1. **Resolve C1–C6** as a one-page spec addendum (design, ~half a day).
2. **Write SAFETY.md + the three contracts + two config YAMLs** (G14 + G1–G5) — still the first artifacts, per v2 §12.
3. **Track A tracer bullet:** Inspect AI task + LiteLLM mock provider + one prompt-injection scenario set (with its C1 ground-truth) + judge quorum → emits a spec-compliant `result.json`. *This is the first functional harness producing results for a test evaluation case.*
4. **Track B wrap:** contextualization → selection → gate → evidence → reports around the working core.
5. Widen per v2 §10 (real adapter, more harnesses, Docker, CI gate).

**Definition of Done (unchanged from v2 §11) + agentic addenda:** the four harnesses run as agent graphs against the mock adapter; judges quorum-verify; every finding is standards-tagged and evidence-linked; a run replays from evidence (A3); the gate decision is deterministic and rule-versioned. When `harnessctl evaluate` drives one scenario to a `block` with a replayable evidence trail, the agentic architecture is proven.
