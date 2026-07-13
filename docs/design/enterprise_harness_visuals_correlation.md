# Harness Visuals — Correlation & Alignment to Produced Content

**Owner:** Ivan Avelancio Jr.
**Inputs reviewed:** `Enterprise_harness_platform_arch_v2.drawio`, `Harness_vis1.jpg` (Visual Architecture), `Harness_vis2.jpg` (End-to-End Workflow — Updated), `Harness_vis3.jpg` (Harness Packs — 4 per Category), `Harness_vis4.jpg` (Harness Catalogue).
**Correlated against:** `enterprise_harness_architecture_v3.md`, `_agentic_workflows.md`, `_architecture_review.md`, `_spec_addendum_C1-C6.md`, `enterprise_harness_mvp_colab.ipynb`, and the v2 design/plan.
**Purpose:** extract what the visuals assert, map it to the produced docs, and reconcile the gaps into a single clear direction.

> **Headline:** the visuals and the text docs describe the **same platform** and agree on the hardest architectural call — *fixed (deterministic) gates vs. agentic loops*, which is exactly the produced docs' invariant **A1** ("agents generate & judge; policy decides"). But the visuals carry **five direction-setting facts the text docs do not**: (1) the customer is **AT&T**; (2) the harness set is a **5-category × 4 = 20 catalogue**, not 4; (3) there is a **Harness Studio** (UI + SDK/API, Python/TS/Java); (4) harnesses ship as **Packs** (Foundational / Advanced Capability / AT&T Context); (5) the front door is an **agentic Source Agent → Security Agent** pair with named fixed gates. These are additive, not contradictory — but they widen scope and must be folded into the direction.

---

## 1. What the visuals assert (extracted verbatim)

**Positioning (vis1):** "CSO-owned assurance fabric for open-source and frontier models: **discover → secure → customize → deploy → evolve**." Stakeholder note (vis2): "**Updated for Saeed**: Security Agent checkpoint, Harness Studio UI/SDK, and continuous feedback loop."

**Zones (vis1):**
- **Sources:** Hosted LLM*, Databricks, Anthropic, Prisma AIRS, Open Source, AT&T, Janus / Agentic, Internal AIRS. *(vis2 Discover adds **Cisco**.)*
- **Agents:** Source Agent 🔎 → Security Agent 🛡️ → **Gate ("Safe to move downstream")**, with a **parallel security scan** path.
- **Platform Core:** Intake → Quarantine · Evaluation Lab → AT&T Context · **Harness Registry** (approved packs + evidence) · **Harness Pack** (baseline + capability + context).
- **Customize:** **Harness Studio** — UI + SDK/API (Python · TypeScript · Java).
- **Delivery + Runtime:** **Model Router** → **Harness Selector** → CI/CD · Runtime · **Evidence + Telemetry** (findings, drift, threat updates) → **Remediate + Retest**.
- **Unified Control Plane:** Identity · **Golden Controls** · Policy · Audit · **HITL** · **Auto-stop**.
- **Feedback Loop:** Review → Correct → Evolve. Edge labels: *new source, new risk, update pack, update code, new version, retest*.

**Workflow (vis2) — 8 steps, alternating fixed gates ◇ and agentic loops:**
`1 Request/Model → 2 Source Agent ◇Source Allowed → 3 Security Agent ◇Security Pass → 4 Studio UI/SDK → 5 Sandbox Eval ◇Eval Pass → 6 Context+Registry ◇Approval Gate → 7 Deploy Harness ◇Pipeline Gate → 8 Observe+Feedback`, wrapped by **Continuous Feedback: Review → Course Correct → Evolve Harness Packs**.

**Catalogue (vis3/vis4) — 20 harnesses in 5 categories** (exact titles in §4). Capability taxonomy (15 tags): Extended reasoning · Cyber capabilities · Coding · Multimodal · Tool use/MCP · Agentic behavior · Reliability · Hallucination resistance · Adversarial robustness · Prompt-injection resistance · Data privacy · Security controls · Enterprise integration · Deployment flexibility · Open-weight availability.

**Packaging model (vis4):** every harness is tagged **Foundational** (common to all models), **Advanced Capability** (reasoning/cyber/coding/multimodal/tool/MCP/agentic), or **AT&T Context Pack** (embeds Golden Controls, data policy, business-impact rules, prior findings, approved remediation playbooks).

\* "Hostel LLM" in vis1 is a typo for **Hosted LLM** — fix in the diagram.

---

## 2. Correlation matrix (visual element → produced doc → status)

Status: ✅ aligned · 🟡 partial/needs reframing · 🆕 new in visuals (add to direction).

| Visual element | Where it lives in produced content | Status |
|---|---|---|
| Discover→secure→customize→deploy→evolve | v2 §3 10-step spine; W0–W9 | ✅ |
| Control plane / data plane; Unified Control Plane | v3 §1–§3; R1 | ✅ |
| **Fixed gates vs Agentic loops** | v3 **A1** (agents generate/judge; policy decides); W8 gate | ✅ **exact match** |
| Named gates: Source Allowed, Security Pass, Eval Pass, Approval Gate, Pipeline Gate | W8 precedence + R9 vocab (approve/warn/block/manual_review) | 🟡 map the 4-value vocab onto the 5 named gates |
| HITL, Auto-stop | v3 **A10** (human approves irreversible), **A8** (budget fail-safe / kill-switch) | ✅ |
| Golden Controls, Policy, Audit, Identity | contextualization control-map (D5); §6.18 audit; §6.19 IAM | 🟡 Golden Controls not yet the named anchor |
| Evidence + Telemetry (findings, drift, threat updates) | §6.13/§6.14; **A3** evidence-replay; agent_turn schema | ✅ |
| Harness Registry (approved packs + evidence) | §6.7 registry | ✅ |
| Model Router | — (I have Harness **Selector**, not Model Router) | 🆕 add |
| Harness Selector | W2 selection; §6.8 | ✅ |
| Remediate + Retest | W9 remediation; §6.16; retest flag | ✅ |
| Source Agent (discover harnesses) | §6.1 Discovery — but as a rule, not an agent | 🟡 promote to agent + fixed gate |
| Security Agent (secure before move) | §6.3 Quarantine — but as scanners, not an agent | 🟡 promote to agent + fixed gate |
| **Harness Studio (UI + SDK/API, Python/TS/Java)** | — (registry exists; no authoring surface) | 🆕 add product surface |
| **Harness Pack = baseline + capability + context; Foundational/Advanced/AT&T Context** | §6.7 has definitions/versions, no pack tiering | 🆕 add packaging model |
| **20-harness catalogue (5×4)** | 4 baseline harnesses (v3 §8) = subset of Layers 1–2 | 🟡 **biggest gap — expand/scope** |
| Capability taxonomy (15 tags) | §6.4 normalization capability flags (gap G8 "closed enum") | 🟡 adopt the 15 tags as the enum |
| Sources: Prisma AIRS, Databricks, Cisco, Janus, Internal AIRS | §6.12 adapter + §6.3 scanners | 🟡 name the integrations |
| CPNI (data class, vis4 Layer 2 #3) | G3 risk weights data_class set (PII/PHI/PCI/…) | 🆕 add CPNI (telecom-regulatory) |
| Sandbox Eval (test + evidence) | §6.11 isolation; **A6** synthetic mock only | ✅ |

**Net:** strong conceptual alignment; the produced content is **deeper** (agentic invariants A1–A10, config contracts G1–G14, MVP tracer, replay) while the visuals are **broader** (AT&T context, 20 harnesses, Studio, packs, Model Router).

---

## 3. Terminology reconciliation (do this first — it prevents confusion)

Two words collide across the two bodies of work:

| Term | Visuals mean… | Produced docs mean… | Resolution |
|---|---|---|---|
| **"Layer"** | one of **5 harness categories** (Test/Exposure/Remediation/Resilience/Governance) | one of the **20 platform layers** (§6.1–§6.20) | Call the visuals' the **"Harness Categories"**; keep "Platform Layers" for §6.x. Never say "Layer 3" unqualified. |
| **"Harness"** | a **Pack** (baseline+capability+context, tiered) | a runner module honoring the run contract (R3) | A **Harness Pack** is a *packaged, tiered configuration* of one or more **harness runners**. Pack = what's cataloged/sold; runner = what executes. |
| **"Gate"** | a named checkpoint (Security Pass, etc.) | the deterministic decision engine (W8) | The named gates are **instances** of the W8 engine with a fixed-vocab output. |

---

## 4. The 20-harness catalogue mapped to the produced 4 baseline harnesses

The produced content's four baseline harnesses are the **Test + Exposure** core. Harness Categories 3–5 (**Remediation, Resilience, Governance**) are **entirely new as harnesses** — the produced docs build those capabilities as *platform features*, but the visuals also want harnesses that **verify** them. That is the real scope delta.

| Cat. | # | Catalogue harness (exact) | Covered by produced content? |
|---|---|---|---|
| **1 Test** | 1 | Model Behavior & Capability Benchmark | 🆕 (new) |
| | 2 | Adversarial Robustness & Red-Team Scenario | 🟡 `prompt_injection_baseline` (partial) |
| | 3 | Safety / Policy / Harm Evaluation | 🟡 `sensitive_disclosure_baseline` (partial) |
| | 4 | Hallucination & Grounding | 🟡 `rag_poisoning_baseline` (partial) |
| **2 Exposure** | 1 | Prompt-Injection & Tool-Abuse Exposure | ✅ `prompt_injection_baseline` + `tool_misuse_baseline` (**the MVP tracer**) |
| | 2 | Exploit Chain & Cyber Misuse | 🆕 |
| | 3 | Data Privacy & Leakage Exposure (PII/**CPNI**/secrets) | 🟡 `sensitive_disclosure_baseline` |
| | 4 | Context & Business-Impact Validation | 🟡 W1 contextualization (as harness: new) |
| **3 Remediation** | 1–4 | Safe Remediation Exec · IaC/Playbook · Rollback & Retest · Blast-Radius | 🆕 all four (W9 is the *feature*, not the *test*) |
| **4 Resilience** | 1–4 | Control-Failure/Degraded-Ops · Failover/RTO-RPO · Agent Coordination/Heartbeat · Latency/Throughput/Cost | 🆕 all four (A8 budgets ≈ Cat4 #4 partial) |
| **5 Governance** | 1 | Finding Lifecycle / Evidence / Verdict | 🟡 Finding schema G2 + judge-quorum verdict (as harness: new) |
| | 2 | Auditability & Explainability | 🟡 §6.18 + A3 (as harness: new) |
| | 3 | Policy Compliance / **Golden Controls** (+ISO 42001) | 🟡 contextualization control-map (as harness: new) |
| | 4 | Human Approval & Model Risk Gate | 🟡 A10 + W8 manual_review (as harness: new) |

**Reading:** the MVP tracer bullet (the Colab notebook) squarely implements **Category 2, Harness #1** (Prompt-Injection & Tool-Abuse) with spillover into Cat 1 #2/#3 and Cat 2 #3. It remains the correct first slice — it just needs to be *named against the catalogue* so everyone sees where it sits in the 20.

---

## 5. Where the visuals validate the produced direction (keep)

- **Fixed gates vs Agentic loops (vis2 legend)** is the produced docs' central thesis (A1) drawn in a diagram — the deterministic gate/agentic-execution split is confirmed by the customer-facing design. Strong.
- **HITL + Auto-stop** confirm A10 (human-approved irreversible actions) and A8 (budget fail-safe / kill-switch); vis4 Cat 2 #2 even outputs a "kill-switch recommendation" and Cat 4 #3 tests "auto-stop." Direct evidence the invariants are right.
- **Evidence + Telemetry / Finding Lifecycle / Verdict** confirm the Finding schema (G2), evidence-as-replay (A3), and judge-verdict model (A5).
- **Sandbox Eval** confirms synthetic-mock isolation (A6/R7).
- **Continuous Feedback → Evolve Harness Packs** confirms the §6.17 telemetry/replay + remediation loop.

No visual contradicts an R- or A-invariant. The produced governance model is compatible as-is.

---

## 6. Gaps to reconcile into the direction (each with a recommendation)

**D-1 — Adopt the 20-harness catalogue as the target; keep 4 as the MVP.** *(biggest)*
Reframe v3 §8 and the mvp plan: the target is **5 Harness Categories × 4 = 20**; the MVP tracer is **Cat 2 #1**. Add Categories 3–5 (Remediation/Resilience/Governance) as *harnesses that test those capabilities*, distinct from the platform features that provide them. Phase: MVP = Cat 1–2 core; Phase 2 = Cat 5 (governance, cheap — reuses evidence/audit); Phase 3 = Cat 3–4 (remediation/resilience, heavier).

**D-2 — Promote Discovery/Quarantine to the agentic front door.** Add two workflows: **W-A Source Agent** (discover/register harnesses & models; fixed gate *Source Allowed* = §6.1) and **W-B Security Agent** (SBOM · secrets · malware · license · policy · sandbox; fixed gate *Security Pass* = §6.3, with the **parallel security scan** path). Keep A1: the *Agent* discovers/scans; the *gate* decision stays deterministic.

**D-3 — Add Harness Studio (UI + SDK/API).** New product surface over the registry: authoring in **Python/TypeScript/Java**, honoring the R3 run contract, emitting registrable Harness Packs. This is the "customize" zone and is MVP-relevant for Saeed's ask. Add to §6.7 and the repo layout.

**D-4 — Add the Pack packaging model to the registry schema.** Extend `harness_definitions` with a `pack_tier ∈ {foundational, advanced_capability, att_context}` and a `capability_tags[]` (the 15-tag taxonomy). AT&T Context Packs embed Golden Controls + data policy + business-impact rules + prior findings + approved remediation playbooks. This answers *how harnesses compose per model/use-case*.

**D-5 — Make AT&T Golden Controls the primary control anchor.** Resolves the produced open decision D5: contextualization maps findings to **Golden Controls + ISO 42001** first; OWASP LLM Top 10 / MITRE ATLAS / NIST AI RMF remain secondary cross-tags. Add a `golden_control_id` to the Finding `standards` block.

**D-6 — Add a Model Router distinct from the Harness Selector.** Model Router routes a request to a source model (Hosted/Databricks/Anthropic/Prisma AIRS/Open-Source/Internal); Harness Selector picks the packs. Both feed CI/CD + Runtime. Add Model Router to §6.12 (it's an adapter-adjacent routing concern).

**D-7 — Name the source/scanner integrations.** Map Sources to adapters/scanners: **Prisma AIRS** (Palo Alto AI Runtime Security — scanner + guarded source), **Databricks** (model source), **Anthropic** (frontier source), **Cisco** ("Cisco-style" heartbeat/finding-lifecycle patterns — Cat 4 #3, Cat 5 #1), **Janus / Internal AIRS** (internal agentic + runtime security — **confirm what these are with AT&T**). All still sit behind the LiteLLM one-path rule (C2) for model I/O.

**D-8 — Add CPNI to the data-class taxonomy.** Telecom-regulatory (Customer Proprietary Network Information). Add to `risk_weights.yaml` data_class (weight ≈ PII/PHI tier) and to the Data Privacy & Leakage harness detectors (Presidio custom recognizer). Compliance-material for AT&T.

**D-9 — Adopt the 15-tag capability taxonomy as the closed enum.** Resolves gap G8: normalization `capability_tags` = the vis4 columns. Harness selection filters on these; packs declare them.

---

## 7. Impact on the MVP notebook (Colab)

Still valid and correctly scoped — it is **Harness Category 2 #1 (Prompt-Injection & Tool-Abuse)**. Minimal reconciliations to align it with the visuals:
- Rename/label the harness `cat2_prompt_injection_tool_abuse` and tag it `pack_tier: foundational`, `capability_tags: [prompt-injection resistance, tool use/MCP, agentic behavior]`.
- Add `golden_control_id` and `cpni` to the finding/standards and data-class stubs (one-line each).
- Map the notebook's 5 named gate outcomes (approve/warn/block/manual_review) to the workflow's named gates (Eval Pass / Approval Gate).
No structural change — the invariant suite (A1/A5/A8/C4) is unaffected and the visuals *validate* it.

---

## 8. Recommended direction updates (per document)

| Doc | Change |
|---|---|
| `architecture_v3.md` | Add: AT&T context + CSO ownership; Harness Categories vs Platform Layers terminology (§3 here); Model Router; Harness Studio; Pack packaging model + capability enum. |
| `agentic_workflows.md` | Add W-A Source Agent + W-B Security Agent (front-door, fixed gates); note Cat 3–5 harnesses as future workflows. |
| `spec_addendum_C1-C6.md` | D5 → Golden Controls primary; add CPNI to C1 detectors + data classes; add `pack_tier`/`capability_tags` to the registry contract. |
| `mvp_colab.ipynb` | Section-8 labels → catalogue IDs; add `golden_control_id`/`cpni` stubs; map gate names. |
| new `harness_catalogue.md` | The 20-harness catalogue as the canonical registry seed (titles + outputs + tier + capability tags), transcribed from vis4. |
| the `.drawio` | Fix "Hostel LLM" → "Hosted LLM". |

---

## 9. Open questions for Ivan / Saeed (customer confirmations)

1. **Scope:** is the MVP the **Cat 1–2 core** (recommended), or must it show one harness per category (1 of each of the 5) for the AT&T demo?
2. **Harness Studio:** in-MVP authoring surface, or Phase 2? (Saeed's note implies it's wanted early.)
3. **Golden Controls:** confirm AT&T Golden Controls (+ISO 42001) as the primary anchor over OWASP/NIST.
4. **Janus / Internal AIRS / Prisma AIRS:** what exactly are these (platforms? scanners? sources?), and which are integration targets for MVP vs later?
5. **CPNI & data residency:** any AT&T-specific handling (residency, retention) beyond synthetic-only for MVP?
6. **Model Router:** does AT&T already have a router (e.g., via Prisma AIRS / Databricks) we integrate with, or do we build one?

---

*The visuals and the produced docs are two views of one platform. This file reconciles them: keep the agentic-invariant depth of the docs, adopt the catalogue/Studio/pack/AT&T breadth of the visuals, and disambiguate "layer/harness/gate." The MVP tracer remains the right first slice — now explicitly positioned as Catalogue Category 2, Harness #1.*
