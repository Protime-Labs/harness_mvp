# Original Architecture — Constraints & Image-Item Traceability

**Purpose:** cite the **actual tracked items** in the earliest architecture images, and show, item-by-item, **what the reference architecture drew** and **what the Colab mock v1 notebook implemented** to account for them — and where they remain constraints.
**Sources cited:**
- **Images (earliest pictures):** `Harness_vis1.jpg` (Visual Architecture), `Harness_vis2.jpg` (E2E Workflow), `Harness_vis3/4.jpg` (Harness Catalogue) — all from `Enterprise_harness_platform_arch_v2.drawio` (labels quoted «verbatim» from that file).
- **Reference architecture:** `Enterprise_harness_v1_reference_architecture.drawio` (RA p1–p4).
- **Mock v1 notebook:** `enterprise_harness_mvp_colab.ipynb` (NB §sections).

Status legend: ✅ implemented in mock v1 · 🟡 partial / manual / stub · ⛔ drawn in RA but **not** in mock v1 (design-only).

---

## 1. Constraints shortlist (with the specific citation each derives from)

| # | Constraint | Cited from | How RA + mock v1 account for it |
|---|---|---|---|
| 1 | **Undefined config contracts (G1–G14)** — runner I/O, Finding, risk weights, gate rules never defined | `enterprise_harness.md` §6.10/6.13; §5 empty figure | mock v1 **defines them concretely**: `result.json`, `Finding` (NB §2), gate precedence (NB §11), risk weights (NB §9) |
| 2 | **Enterprise infra prescribed *as MVP*** — K8s/Temporal/Kafka/ClickHouse | `enterprise_harness.md` §6.9/6.11/6.14/6.20 | mock v1 runs **stdlib-only, offline** (NB §0); RA marks them `DEFER` |
| 3 | **20-layer breadth vs. unverifiable on-prem stack** | `enterprise_harness.md` §6.1–6.20 | RA = forward-deployed **slice**; mock v1 = 5 harnesses, no connectors |
| 4 | **No "trust the evaluation" mechanism** (independence/quorum/calibration/stability unspecified) | `enterprise_harness.md` Exec Summary ("validates/evidence") | mock v1 **adds** quorum + detector-floor (NB §7), calibration (NB §15), replay (NB §16) |
| 5 | **Provider independence under-mechanized** (open capability vocab, no single-adapter mandate) | `enterprise_harness.md` §6.4/6.12 | mock v1 = one adapter path (NB §3/§20); RA = LiteLLM single I/O seam |
| 6 | **Internal incompleteness** — empty data-model figure, `TBD` MVP plan | `enterprise_harness.md` §5, §8 | resolved in `_design.md`/`_mvp_plan.md`; mock v1 makes it runnable |
| 7 | **No cost/budget model; "no prod coupling" vs "continuous monitoring"** | `enterprise_harness.md` §6.14/6.17 + Exec Summary | mock v1 **budget fail-closed** (NB §8) ≈ vis1 «Auto-stop»; monitoring deferred |
| 8 | **External/customer deps undefined** — «Prisma AIRS», «Janus», «Internal AIRS», «Model Router», «Harness Studio», «Golden Controls» | **vis1** (all drawn, none defined in the doc) | RA draws them (p1); mock v1 stubs (pack tier, golden_control_domains) — **blocked on AT&T inputs** |
| 9 | **Determinism vs. real models** (`bounded`, not identical) | implied by agentic design | mock v1 `determinism_class` + real-run `bounded` label (NB §8) |
| 10 | **Missing authorized-use / SAFETY boundary (G14)** | absent from `enterprise_harness.md` | mock v1 SAFETY posture (NB §0): synthetic-only, no prod creds, deny egress |

---

## 2. Image-item traceability — `Harness_vis1` (Visual Architecture)

Subtitle cited: «CSO-owned assurance fabric for open-source and frontier models: discover → secure → customize → deploy → evolve.»

| Zone | Tracked item (cited «label») | Reference architecture (RA) | Colab mock v1 (NB) | Status |
|---|---|---|---|---|
| **Sources** | «Hosted LLM · Databricks · Anthropic · Prisma AIRS · Open Source · AT&T · Janus / Agentic · Internal AIRS» | p1 SOURCES band | `PROVIDER_MODE` + adapter (§3); real path §20 (Anthropic/Bedrock/OpenAI-compat) | 🟡 |
| **Agents** | «Source Agent» (discover harnesses) | p1 Control Plane → Discovery+Provenance | — | ⛔ |
| **Agents** | «Security Agent» + «Gate: Safe to move downstream» + «parallel security scan» | p1 "Security Agent / Quarantine → ⟦Security Pass⟧" | — | ⛔ |
| **Customize** | «Harness Studio (UI + SDK/API)» · Python · TypeScript · Java | RA reconciliation note (v3 §11); not a p1 box | authoring = edit `HARNESSES` dict (§5) | 🟡 |
| **Platform Core** | «Intake» | p1 Contextualization | `use_case` intake (§13) + `contextualize` (§9) | ✅ |
| **Platform Core** | «Quarantine» | p1 Security Agent/Quarantine | — | ⛔ |
| **Platform Core** | «Evaluation Lab» | p1 DATA PLANE | harness runner + judges (§5–§8, §13) | ✅ |
| **Platform Core** | «AT&T Context» | p1 "Contextualization + Golden Controls + CPNI" | `data_classes:["CPNI","PII"]` + `golden_control_domains` (§9,§5) | 🟡 |
| **Platform Core** | «Harness Registry (approved packs + evidence)» | p2 Registry (W-C) | `REGISTRY` dict + implemented flags (§10) | 🟡 |
| **Platform Core** | «Harness Pack (baseline + capability + context)» | p1 category boxes + pack tiers | `FOUNDATIONAL_PACK` + `pack_tier` (§9) | 🟡 |
| **Delivery** | «Model Router» | p1 "AT&T MODEL ROUTER (AT&T-owned)" | folded into adapter (no separate router) | 🟡 |
| **Delivery** | «Harness Selector» | p1 Control Plane → Selection | `select()` (§10) | ✅ |
| **Delivery** | «CI/CD» | p1 "CI/CD Gate" | gate (§11) + acceptance suite (§18) | 🟡 |
| **Delivery** | «Remediate + Retest» + «retest» edge | p1 Remediation | `Finding.recommendation` (§8) | 🟡 |
| **Delivery** | «Runtime» | p1 Runtime | execute path (§13) | 🟡 |
| **Delivery** | «Evidence + Telemetry (findings, drift, threat updates)» | p1 Evidence + Delivery band | EvidenceStore (§4) + replay (§16) + export (§21) | 🟡 (evidence ✅, drift/threat ⛔) |
| **Unified CP** | «Identity» | p1 Unified Control Plane | — (roles noted only) | ⛔ |
| **Unified CP** | «Golden Controls» | p1 Unified CP + Contextualization | `standards.golden_control_domains` (§5) | 🟡 |
| **Unified CP** | «Policy» | p1 Unified CP + Gate | gate `policy_version` (§11) | ✅ |
| **Unified CP** | «Audit» | p1 Unified CP | H5.1 governance + hashing (§12,§4) | ✅ |
| **Unified CP** | «HITL» | p1 Unified CP | gate `manual_review` vocab (§11) | 🟡 |
| **Unified CP** | «Auto-stop» | p1 Unified CP | budget fail-closed → `budget_exceeded` (§8) | 🟡 |
| **Feedback** | «Feedback Loop: Review → Correct → Evolve» + «update pack» edge | p1 "EVOLVE ↺" | testing matrix / re-run (§19) | 🟡 |

---

## 3. Image-item traceability — `Harness_vis2` (End-to-End Workflow)

Legend cited: «Fixed gates» vs «Agentic loops».

| Step (cited «label») | Gate (cited) | Reference architecture | Colab mock v1 | Status |
|---|---|---|---|---|
| 1 «Request / Model (use case or router)» | — | p1 Sources + Router | `use_case` (§13) | 🟡 |
| 2 «Source Agent (discover harnesses)» | «Source Allowed» | p1 Discovery / W-A | — | ⛔ |
| 3 «Security Agent (secure before move)» | «Security Pass» | p1 Security Agent / W-B; «Secure: SBOM·secrets·malware·license·policy·sandbox» | — | ⛔ |
| 4 «Studio UI/SDK (customize harness)» | — | Harness Studio (noted) | edit `HARNESSES` (§5) | 🟡 |
| 5 «Sandbox Eval (test + evidence)» | «Eval Pass» | p1 DATA PLANE | §5–§8, §13 (the eval) | ✅ |
| 6 «Context + Registry (approve + catalog)» | «Approval Gate» | p1 Contextualization + p2 Registry | `contextualize` (§9) + `REGISTRY`/`select` (§10) | 🟡 |
| 7 «Deploy Harness (CI/CD + runtime)» | «Pipeline Gate» | p1 Delivery | gate (§11) + suite (§18) | 🟡 |
| 8 «Observe + Feedback (review/correct/evolve)» | — | p1 EVOLVE | matrix + report (§17,§19) | 🟡 |
| **«Fixed gates» vs «Agentic loops»** (the core principle) | — | RA invariant A1 (agents generate/judge; policy decides) | deterministic gate (§11) vs LLM judges (§7) | ✅ |

---

## 4. Image-item traceability — `Harness_vis3/4` (Harness Catalogue)

Packaging model cited: «Foundational · Advanced Capability · AT&T Context Pack». Five categories cited: «Layer 1 Test · Layer 2 Exposure · Layer 3 Remediation · Layer 4 Resilience · Layer 5 Governance».

**Categories:** RA p1 draws all five (Cat 3–5 greyed = Phase 2/3). Mock v1 touches **3 of 5** (Test, Exposure, Governance); Remediation + Resilience ⛔.

**The 20 catalogued harnesses (vis4 exact titles) → mock v1:** mock v1 implements **5 of 20**, each a direct match to a cited catalogue title:

| vis4 catalogue harness (cited «title») | mock v1 harness (NB §5) | Status |
|---|---|---|
| Layer 2 #1 «Prompt-Injection & Tool-Abuse Exposure Harness» | `H2.1` | ✅ |
| Layer 1 #2 «Adversarial Robustness & Red-Team Scenario Harness» | `H1.2` | ✅ |
| Layer 1 #3 «Safety / Policy / Harm Evaluation Harness» | `H1.3` | ✅ |
| Layer 2 #3 «Data Privacy & Leakage Exposure Harness» | `H2.3` | ✅ |
| Layer 5 #1 «Finding Lifecycle / Evidence / Verdict Harness» | `H5.1` | ✅ |
| the other 15 (L1#1,#4 · L2#2,#4 · L3#1–4 · L4#1–4 · L5#2–4) | — | ⛔ (catalogue + RA only) |

**Capability tags** (cited: «Extended reasoning … Open-weight availability», 15) → mock v1 carries `capability_tags` on each of the 5 harnesses (NB §5). ✅ (for those 5).
**Packaging tiers** → mock v1 = **Foundational only** (`pack_tier:"foundational"`, §9); Advanced/AT&T-Context ⛔.
**vis3 flow «Registry → Selector → CI/CD + Runtime» + feedback** → NB §10 `select` → §11 gate → §13 run; ✅ (LITE).

---

## 5. Rollup — what accounted for the images, and what remains a constraint

**Fully accounted for in mock v1 (✅):** Intake/Contextualization, Evaluation Lab, Harness Selector, Policy/Gate, Audit, the «Fixed gates vs Agentic loops» principle (A1), and 5 catalogue harnesses by exact title.

**Partial / stubbed (🟡):** Sources (adapter, mock target), AT&T Context (CPNI + Golden-Control *domains*), Registry/Pack (dicts), Model Router (folded into adapter), Remediate/Retest (recommendation text), Evidence+Telemetry (evidence ✅ / drift+threat ⛔), HITL (`manual_review`), Auto-stop (budget fail-closed), Feedback (re-run matrix), Harness Studio (edit-the-dict).

**Drawn in RA but not in mock v1 (⛔ — the live constraints):** «Source Agent», «Security Agent»/«Quarantine»/«Secure» scanners, «Identity», drift/threat telemetry, 15 of 20 catalogue harnesses, and the external/customer items «Prisma AIRS»/«Janus»/«Internal AIRS»/full «Golden Controls» — i.e., constraints **#3** (breadth) and **#8** (AT&T-supplied deps) above.

**Net:** the mock v1 notebook is a **faithful realization of the images' *evaluate → gate → evidence* spine and the «agentic loops vs fixed gates» principle**, with the *secure/discover front-door*, *governance breadth*, and *AT&T-specific integrations* remaining the tracked, cited constraints to close.

*Cite key: image labels «…» are verbatim from `Enterprise_harness_platform_arch_v2.drawio`; RA p# = `Enterprise_harness_v1_reference_architecture.drawio`; NB § = `enterprise_harness_mvp_colab.ipynb`.*
