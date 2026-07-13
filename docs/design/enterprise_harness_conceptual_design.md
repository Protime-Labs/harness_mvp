# Harness Platform — Conceptual Design (understand the *why*)

**Purpose:** so you can *fully* understand the harness — what it is conceptually, the design decisions and their rationale, and how the pieces depend on each other. This is the "explain it to me" document, not a spec.
**Companions:** `enterprise_harness_architecture_v3.md` (full spec), `enterprise_harness_catalogue.md` (the 21 harnesses), `enterprise_harness_mvp_colab.ipynb` (the working MVP).

---

## 1. What an AI harness *is* (in one paragraph)

A software test harness runs your code against inputs and checks the output. An **AI harness** does the same for an AI asset (a model, agent, prompt, or RAG pipeline), but the "input" is an **attack or probe**, the "output" is **behavior**, and "checking" is a **judgement** — because there's no single correct answer, only *safe vs unsafe*, *aligned vs misaligned*. The harness's job is to **make an AI asset reveal how it behaves under pressure, decide whether that behavior is acceptable, and turn that into an auditable record.**

Everything else in this platform is scaffolding around that one idea.

---

## 2. The mental model: three primitives + one wrapper

Every harness, no matter the category, is the same shape:

```
        ┌──────────────────────── one harness run ────────────────────────┐
        │                                                                  │
  TEST CASE ──▶ [ DRIVER ] ──attack──▶ [ TARGET ] ──response──▶ [ JUDGE ] ──▶ FINDING
  (scenario)    (attacker/            (the asset             (did the attack
                 prober)               under test)            succeed? how bad?)
        │                                                                  │
        └──────────── everything above is the DATA PLANE ──────────────────┘
                                        │  finding + evidence
                                        ▼
                    [ POLICY / GATE ]  ← the CONTROL PLANE wrapper
                    turns findings into approve / warn / block / manual_review
```

- **Target** — the AI asset you're evaluating. In the MVP it's a *mock*; later it's a real model.
- **Driver** — what generates the attack/probe (a scenario file, or a red-team tool like PyRIT/Garak/Petri, or an evolutionary search).
- **Judge** — decides whether the target misbehaved. An LLM-as-judge, backed by deterministic detectors.
- **Policy / Gate** — the *only* thing that makes a decision. Deterministic, versioned, auditable.

If you remember nothing else, remember this shape. The 21 harnesses differ only in *which driver, which judge, which test cases* — the shape is fixed.

---

## 3. The one decision everything hangs on

> **Agents generate and judge (non-deterministic). Policy decides (deterministic). No LLM is ever in the gate or risk path.**

Why this is the keystone: an AI harness is *itself* built from AI (the attacker is an LLM, the judge is an LLM). If you let any LLM make the final block/approve decision, your assurance tool becomes:
- **non-reproducible** (same input, different verdict),
- **non-auditable** (can't explain the decision to a regulator),
- **injectable** (the attacker's text could manipulate the judge into passing).

So we draw a hard line: **LLMs *propose*, attack, and score; a versioned rule engine *decides*.** This single rule is what makes an agentic tool trustworthy enough to gate a production deployment.

---

## 4. Why two planes (control vs data)

| Plane | Owns | Property |
|---|---|---|
| **Control plane** | decisions, policy, gate, risk scoring, selection, audit | **deterministic, auditable** |
| **Data plane** | attackers, targets, judges, evidence capture | **agentic, swappable** |

They're separated as a *code boundary*, not just a diagram, for two reasons:
1. **Trust** — decisions stay deterministic even though execution is not (§3).
2. **Swappability** — you can replace any driver/model/framework in the data plane without touching the decision logic. That's what lets you start with a mock and swap in real tools later.

---

## 5. The Run Contract — the most important interface

Between the two planes sits one interface:

```
control plane  ──writes──▶  run_config.json   ──▶  [ harness runs ]  ──▶  result.json + evidence  ──reads──▶  control plane
```

This contract is the **seam**. Its value is not the JSON — it's what the seam *buys* you:
- **Any driver is swappable** — mock, PyRIT, Garak, Petri, even Cisco, all speak the same contract.
- **Dependencies are decoupled** — you can run with a *stub* behind the seam and swap the real thing in when it's ready. You never block on infrastructure you don't have yet.

This is the single most useful idea for an MVP where the on-prem stack is still being built: **build against the seam, run on stubs, swap as each dependency is verified.**

---

## 6. The lifecycle of one evaluation (conceptual walkthrough)

Follow one asset through the system:

1. **Discover** — an asset (agent config, prompt, model reference) is registered; we hash it and record who owns it.
2. **Secure** — quick scans (secrets, malicious files, policy) block obviously-unsafe assets *before* they run.
3. **Contextualize** — the *business* use case (PII/CPNI? write-capable tools? external users?) determines the **risk tier** and **which harnesses are required**. Rules decide, not an LLM.
4. **Select** — a deterministic, explainable plan: which harnesses run, and *why each was skipped* if not.
5. **Run** — each harness executes the §2 shape: driver → target → judge → finding.
6. **Judge** — findings above `high` need a **quorum** of independent judges plus deterministic detectors (a canary/PII hit *overrides* the LLM).
7. **Gate** — a rule engine aggregates all findings into one decision: `approve / warn / block / manual_review`, with the policy version and rationale recorded.
8. **Evidence** — every prompt, response, and judgement is hashed and stored so the whole run can be **replayed from evidence alone**.
9. **Remediate** — blocking findings become owner-visible items; an agent *proposes* fixes, a human *approves* anything irreversible.

Steps 1–4, 7–9 are control plane. Steps 5–6 are data plane. The Run Contract is between 4 and 5.

---

## 7. The invariants and *why they exist* (the design decisions)

The spec lists R1–R9 and A1–A10 tersely. Here's what each *prevents* — the rationale is the point:

| Invariant | Prevents… | So we require… |
|---|---|---|
| **R1** plane separation | LLMs quietly making decisions | control ≠ data as a code boundary |
| **R2 / A2** provider independence | vendor lock-in; a rewrite per model | *all* model I/O through one adapter |
| **R3** run contract | harnesses that can't be swapped | a fixed input/output file contract |
| **R6 / A3** evidence chain | "trust me, it failed" with no proof | hash every artifact; replay from evidence |
| **R9 / A1** fixed decision vocabulary + no-LLM gate | non-reproducible, unexplainable gates | deterministic rule engine, 4 outcomes |
| **A4** judge isolation | the attacker's text manipulating the judge | judges get structured input only, no tools |
| **A5** judge quorum | one unreliable/hallucinated verdict blocking a deploy | ≥3 diverse-lens judges for gating severity |
| **A7 / C5** determinism class | over-claiming "reproducible" to auditors | pin seed/model; label real runs `bounded` + stability-check |
| **A8 / C6** budgets, fail-closed | runaway token cost; silent partial runs passing | per-run ceilings; budget-exceeded ⇒ block |
| **A9** judge calibration | trusting a judge you never measured | score judges vs labeled ground truth |
| **A10** human-in-the-loop | an agent auto-rolling-back production | agents propose; humans approve irreversible actions |

Two derived design rules worth internalizing:
- **Detector floors the judge** — if a deterministic check (a leaked PII token, a canary) fires, the finding is confirmed regardless of what the LLM judge says. Ground truth beats opinion.
- **Fail closed** — running out of budget on a *required* harness is treated as "not run," which blocks. Incomplete coverage is never a clean bill.

---

## 8. Interdependencies — what depends on what

### 8a. Build-order dependencies (must exist before → can be built)
```
contracts/schemas ──▶ everything
adapter ──▶ harness runner, judges          (the model I/O path)
scenarios + ground-truth ──▶ harness runner, judge calibration
harness runner ──▶ orchestration
judge + detectors ──▶ harness runner
evidence store ──▶ harness runner, gate, replay
contextualization rules ──▶ selection
selection ──▶ orchestration
findings (from runner) + quarantine + context ──▶ gate
gate ──▶ reports, remediation
```
**Read it as:** you cannot build the gate before findings exist; you cannot produce findings before the runner; the runner needs the adapter + scenarios + judges; everything needs the contracts. **The contracts are the root — build them first.**

### 8b. Runtime data dependencies (what flows to what)
`test case → attack → response → verdict → finding → gate decision → report/remediation`, with **evidence captured at every arrow**.

### 8c. External dependencies (outside our control — the ones you can't verify yet)
| External thing | Who owns it | If not ready, use… |
|---|---|---|
| Real model endpoint | AT&T / provider | **mock adapter** (offline) |
| Model Router | AT&T infra | our adapter targets a model directly |
| PyRIT / Garak / Petri | vendors (OSS) | **built-in scenario driver** |
| Golden Controls catalogue | AT&T | control *domains* placeholder |
| Evidence store / DB | AT&T infra | local hashed files |
| Cisco / Azure platforms | vendors | omit (Phase 4+) |

**This table is the whole point of the dependency-gated MVP:** every external dependency has a stub, so nothing external blocks you.

---

## 9. Two things called "layer" (clear this up once)

- **Platform layers (§6.1–§6.20)** — the 20 architectural components (discovery, quarantine, runner, gate…). Vertical build structure.
- **Harness categories (5)** — Test · Exposure · Remediation · Resilience · Governance. The *kinds of harness* in the catalogue (H1.x–H5.x).

They are unrelated axes. When in doubt: "layer" = a platform component; "category" = a kind of test.

---

## 10. Where the MVP actually sits

The full picture above is the **target**. The **MVP** is §2's shape, run offline:

- **Target:** mock. **Driver:** built-in scenarios. **Judge:** LLM-judge simulated + detectors. **Gate:** the real rule engine.
- It needs **no infrastructure** — it runs in Colab with zero installs and still produces scored findings, a gate decision, and a replayable trail.
- Everything else (real models, real frameworks, Model Router, Cisco, forward-deploy, the bake-off) is added **one verified dependency at a time**, behind the Run Contract.

So the conceptual design and the MVP are the same shape — the MVP just has stubs where the target has integrations. That is by design, and it's why the seam matters.

---

## 11. Glossary

- **Harness** — a runnable test that drives a target, judges the behavior, and emits findings honoring the Run Contract.
- **Driver / attacker** — generates the probe (scenario file or red-team tool).
- **Target** — the asset under test (mock or real model/agent).
- **Judge** — LLM-as-judge that scores a transcript; runs as a **quorum** with deterministic **detectors**.
- **Detector** — a deterministic check (regex, PII, canary) that *floors* the judge.
- **Finding** — a normalized, standards-tagged record of a confirmed issue, linked to evidence.
- **Gate** — the deterministic rule engine; the only decision-maker (`approve/warn/block/manual_review`).
- **Run Contract** — the `run_config.json → result.json + evidence` seam between planes.
- **Evidence / replay** — hashed artifacts sufficient to reconstruct findings + gate decision with no model calls.
- **Quorum** — ≥3 independent, diverse-lens judges required for gating-severity findings.
- **Bounded (determinism)** — a real-model run: pinned but not byte-identical; stability-checked, never called "reproducible."
