# V1 Reference Architecture — Review (findings register)

**Reviews:** `Enterprise_harness_v1_reference_architecture.drawio` (+ `.md`) against R1–R9 / A1–A10, the catalogue, and the doc set.
**Type:** review only — no files changed. **Verdict:** **structurally sound, ship-worthy as a reference — but resolve 3 High findings before it drives a build**, and it currently over-states V1 scope.

---

## Strengths (keep)
- **Plane separation holds in the picture** — control plane (deterministic gate) is visually distinct from the data plane (swappable drivers behind the Run Contract). R1/R3/A1 are legible, not just asserted.
- **The Challenge/bake-off page is the best addition** — it operationalizes "integrate the best of each" as a gated pipeline (Base → Spec → Challenge → Registry → Select → Gate). That's the right lane discipline.
- **Frontier integration modes are correctly separated** — driver / detector / guardrail / platform / substrate. Nothing bypasses the adapter (R2/A2).
- **Lean** — 3 pages; not over-engineered on the surface.

---

## Findings

| # | Sev | Finding | Fix |
|---|---|---|---|
| **V1-F1** | **High** | **"Forward-deployed inside AT&T" ⟂ "synthetic-only in V1."** A forward-deployed harness implies operating against *real* AT&T assets; synthetic-only means it can't. The transition mock → **bounded real model** (C5 `bounded` class, isolated/read-only/no-egress) is undefined. Either V1 delivers little (never touches a real model) or "synthetic-only" is wrong and the A6/egress posture changes. | Split V1 into **V1a (synthetic mock)** → **V1b (bounded real, isolated, C5 stability-checked)**; show the `bounded` determinism class + Jaccard stability gate in the forward-deployed context. |
| **V1-F2** | **High** | **Cisco overlap is unresolved and understated.** The diagram shows Cisco as a dashed backend feeding H5.3. But if AT&T already runs Cisco AI Defense (Discover/Detect/Protect), our control plane **substantially overlaps** it. The dashed line hides a make-or-break positioning decision. | Decide and draw it explicitly: **are we the governance/orchestration layer *above* Cisco (consume its findings via the Run Contract) or a competing platform?** Recommended: orchestrate-above; run Option-D benchmark to confirm. |
| **V1-F3** | **Med** | **The bake-off pipeline is not a named workflow.** Page 2 introduces a real process that isn't assigned a W-number and doesn't appear in `agentic_workflows.md` (which stops at W-A/W-B). It floats outside the taxonomy → no owner, no traceability. | Name it **W-C (Harness Onboarding / Challenge)** and add it to the workflow doc + coverage matrix. |
| **V1-F4** | **Med** | **Model Router ambiguity — ours vs AT&T's.** The seam collapses "Model Router / LiteLLM," but `architecture_v3 §11` defines the Router as *distinct* from the adapter and lists AT&T sources (Prisma AIRS/Databricks/Internal). Forward-deployed, the router is likely **AT&T's existing infra**, not ours — and H4.2 failover depends on it. | Separate the two boxes: **adapter = ours (harness I/O, R2/A2)** vs **Model Router = AT&T's app routing** (integration boundary). State which is in V1. |
| **V1-F5** | **Med** | **No visual V1 vs Phase-2/3 boundary.** One canvas mixes V1 (Cat 1–2, mock, PyRIT/Garak) with Phase-2/3 (Cat 3–5, guardrails, Cisco, resilience). E.g. NeMo/Content-Safety guardrails are drawn in the V1 data plane, but their harness (H4.1) is **Phase 3**. This over-states V1 and works against "don't over-engineer." | Shade/boundary what is **in V1** vs **deferred**; grey out Phase 2/3 elements. |
| **V1-F6** | **Med** | **Bias & Fairness gap still open** (carried from the HTML review, F2). The reference tool has a Bias & Fairness pillar (68 prompts); our catalogue and the V1 architecture have **no counterpart** — a real coverage gap for an AT&T (fairness/regulatory exposure). | Add planned harness **H1.5 Bias & Fairness** to the catalogue (Test category) and show it in the roadmap. |
| **V1-F7** | **Low-Med** | **Egress-deny ⟂ "threat updates / evolve."** How do new attack corpora (Garak/PyRIT/Petri updates, Cisco threat intel) enter a default-deny-egress environment, and how does governance evidence leave? Undefined. | Add a **controlled one-way ingress** (signed pack updates) and an **evidence-export** path to the diagram. |
| **V1-F8** | **Low** | **Adapter is a single choke.** LiteLLM as the sole I/O path is a control strength but also holds all creds and is a single point of failure/leak forward-deployed. | Note HA + secret-handling posture (SDK in-proc for V1a; hardened proxy later). No redesign. |
| **V1-F9** | **Low** | **Operating roles (RBAC) undefined for forward-deployment.** Who at AT&T runs the bake-off, approves waivers, owns gate overrides? RBAC is DEFER, but forward-deploy forces a minimal operate-vs-govern role map. | Add a minimal role map (operator / security reviewer / model owner / auditor). |

---

## Top 3 to resolve before this drives a build
1. **V1-F1** — define the synthetic → bounded-real transition (or the reference architecture promises something V1 can't do).
2. **V1-F2** — resolve the Cisco positioning; it changes what we build vs integrate.
3. **V1-F3** — name the bake-off **W-C** so the "challenge to integrate" story has an owner and a spec.

**Alignment verdict:** the V1 architecture is faithful to the invariants and to the frontier-integration model; its gaps are **scope-honesty** (F1/F5), **strategic positioning** (F2), and **traceability** (F3/F4) — not structural defects. Fixing F1–F3 makes it build-ready.

---

## Calibration & Consolidation (9 findings → 5 themes; overlap · naming · direction)

| Theme | Merges | Direction (default) | Status |
|---|---|---|---|
| **T1 · Scope / Phasing** | F1 + F5 | V1 states its target class + phase edge: **V1a synthetic → V1b bounded-real**; grey Phase 2/3 on the canvas | **decision Q2** |
| **T2 · Cisco positioning** | F2 | **Orchestrate-above** (consume Cisco behind the Run Contract); confirm via bake-off | **decision Q1** |
| **T3 · Naming / Traceability** | F3 + F4 | bake-off = **W-C** (fixed); **adapter (ours, harness I/O) ≠ Model Router (app routing)** shown as distinct boxes | **W-C FIXED**; router split pending Q3 |
| **T4 · Coverage** | F6 | add **H1.5 Bias & Fairness** (closes HTML-review F2) | **decision Q4** |
| **T5 · Forward-deploy ops** | F7 + F8 + F9 | **signed one-way pack ingress + evidence export**; SDK-in-proc adapter for V1a; roles = operator / security-reviewer / model-owner / auditor | defaulted (no decision needed) |

**Fixes applied this pass:** the bake-off is now the named workflow **W-C** (`enterprise_harness_agentic_workflows.md`); findings calibrated and de-overlapped above. **T5** is defaulted (low-risk). **T3 router split, T1 phase-split diagram, T4 H1.5** finalize once **Q1–Q4** are decided.

## Open decisions → final architecture (Q1–Q4)
Presented as options with a recommendation for each (see the accompanying question prompt). On answer, I finalize the diagram (V1a/V1b phase boundary, adapter/Router split, Cisco box) and the catalogue (H1.5) in one coherent pass.

- **RESOLVED (all recommended):** Q1 **orchestrate-above Cisco** · Q2 **V1a synthetic → V1b bounded-real** · Q3 **AT&T-owned Model Router** (adapter separate) · Q4 **H1.5 Bias & Fairness in Phase-1**.

**Finalized:** diagram regenerated (`Enterprise_harness_v1_reference_architecture.drawio` — adapter≠router, V1a/V1b + greyed Phase 2/3, Cisco orchestrate-above); **W-C** added to workflows; **H1.5** added to catalogue (§Category 1 + Phase-1). All F1–F9 themes now either fixed or defaulted (T5).
