# Secondary Review — `LLM-Safety-Suite-Harness.html` Alignment Analysis

**Reviewer:** Ivan Avelancio Jr. (via analysis) · **Type:** evaluation & findings only — **no files changed**, recommendations are proposals.
**Artifact reviewed:** `LLM-Safety-Suite-Harness.html` (287 KB, self-contained doc + D3 evidence charts). Provenance in the file: **"Project Glasswing Phase-2"**, backing the paper *"Mutator-Target Co-Adaptation Confounds Quality-Diversity Red-Teaming of Frontier LLMs."*
**Evaluated against:** our produced solution — `architecture_v3.md` (R1–R9, A1–A10), `catalogue.md` (5 categories × 4 = 20 harnesses), `spec_addendum_C1-C6.md`, `mvp_colab.ipynb`, `att_summary.md`.

---

## 1. Executive verdict

**The tool is a production-grade implementation of our *data-plane harness engine* for Harness Categories 1–2 — strongly aligned in intent and mechanics, a strict subset in scope, and net-additive on capability.** It independently validates our core loop (**Attacks → Judges → Reports → Evolves** ≈ W3→W7→evidence→W9), is vendor-neutral (R2/A2), and is evidence- and human-in-the-loop-first (A3/A10). It does **not** implement our **control plane** (deterministic gate, contextualization, selection, provenance, quarantine) or **Categories 3–5** (Remediation/Resilience/Governance), and carries **no AT&T/Golden-Controls context**.

It also brings **five capabilities our design should absorb** (chiefly QD/MAP-Elites evolutionary attack generation) and **exposes one real gap in our catalogue** (a dedicated **Bias & Fairness** harness). Its own research caveat — *mutator–target co-adaptation confounds results* — **empirically validates our independence invariants (A2 / decision D1)**.

**Alignment scorecard (tool vs our solution):**

| Our layer | Coverage in the tool | Verdict |
|---|---|---|
| Provider independence (R2/A2) | any backend via `config.yaml`; one-line retarget; anthropic/openai_compat/**bedrock**/bedrock_mantle | ✅ Full |
| Attacker → target → judge loop (W3/W7) | full, plus an evolutionary variant | ✅ Full (+superset) |
| LLM-as-judge + structured verdict (W7) | verdict/confidence/reasoning + per-prompt rubric | ✅ Full (richer rubric) |
| Evidence & audit (R6/A3) | every response + judge reasoning → CSV; multi-seed; re-judge | 🟡 Partial (no hash-chain/replay) |
| Human-in-the-loop (A10) | "human-in-the-loop by design"; override; borderline triage | ✅ Full |
| Determinism (A7/C5) | multi-seed reproducibility runs; QD seeds | 🟡 Partial (LLM judge nondeterminism acknowledged) |
| Deterministic detector floor (C3) | **canary token → instant FAIL** | 🟡 Partial (canary only; no PII/CPNI) |
| Judge robustness (A5 quorum) | single judge at decision + **neutral re-judge** (sequential) | 🟡 Partial (no simultaneous quorum) |
| Standards tagging | OWASP LLM Top 10 (2025) + coverage heatmap | ✅ Full (OWASP); ⛔ no ATLAS/ISO/Golden |
| Deterministic gate, fixed vocab (R9/A1) | risk LOW/MED/HIGH + pass-rate; no approve/warn/block/manual_review | ⛔ Absent |
| Control/data-plane separation (R1) | all data plane | ⛔ Absent |
| Contextualization / Selection / Provenance / Quarantine | — | ⛔ Absent |
| Categories 3–5 (Remediation/Resilience/Governance harnesses) | — | ⛔ Absent |
| AT&T Golden Controls / CPNI | — (Bedrock backend hints at enterprise) | ⛔ Absent |
| **Bias & Fairness** pillar | **present (68 prompts)** | 🔺 **Tool exceeds our catalogue** |

---

## 2. What the tool is (grounded facts)

- **Purpose:** turn LLM red-teaming from "a one-off art project" into a *repeatable, measurable, vendor-neutral engineering discipline* — versioned CSV, diff-able results, HTML evidence report.
- **Two modes:** **Static Prompt Sweep** (`run.py`) → pass-rate + LOW/MED/HIGH risk + per-pillar/category breakdown; **QD Evolutionary Search / MAP-Elites** (`run_qd.py`) → maps the *variety* of failure modes.
- **Library:** 415 prompts across **4 fixed pillars** — Adversarial Safety **265**, Bias & Fairness **68**, Hallucination **39**, Capability & Robustness **43**; severity mix 80 Critical / 132 High / 191 Medium / 12 Low. Prompt schema: `attack text, pillar, category, sub-category, technique, severity, optional system prompt, per-prompt judge rubric`.
- **Judge:** a *separate* LLM; input = pillar + rubric + attack + response → `{verdict PASS/FAIL, confidence HIGH/MED/LOW, reasoning}`. **Special cases:** API hard refusal → SKIP (=PASS); **CANARY token leaked → instant FAIL**; parse failure → one retry. Verdicts: PASS/FAIL/SKIP/UNKNOWN.
- **QD pipeline:** Seed prompts (151) → Mutator (new attacks) → Target → Judge (harm+category) → **MAP-Elites 15×15 grid** → best attacks fed back to mutator. Metrics: **Coverage** (% grid explored), **Diversity** (cells with harm≥0.5), **QD-Score** (Σ harm), **Peak** (max harm); behavioral-landscape heatmap (compliance × harm-category).
- **Backends:** `config.yaml` target/judge/mutator; types `anthropic | openai_compat | bedrock | bedrock_mantle`; models incl. Claude Opus 4.6 / Sonnet 4.6 / "Mythos".
- **Tooling:** `run.py`, `run_qd.py`, `rejudge.py` (re-judge with a different/neutral model), Streamlit dashboard. `--dry-run`/`--quick` offline smoke modes.
- **Evidence:** real runs — Mythos 96.3% pass, Opus 4.6 95.9% pass; multi-seed (1/2/3) reproducibility; mutator ablation; **neutral re-judge (Sonnet 4.6)**; OWASP coverage heatmap. Responsible-use statement (defensive tool; prompts test refusal, not harm instructions).

---

## 3. Component-to-architecture mapping

| Tool component | Our architecture element | Our doc |
|---|---|---|
| Static sweep (`run.py`) | harness runner honoring a run contract (W3, §6.10) | catalogue H2.1/H1.2/H1.3 |
| QD search (`run_qd.py`, MAP-Elites) | **attacker-agent driver** (advanced), + coverage metrics | §6.4/6.14, A-series |
| Judge LLM + rubric + confidence | W7 LLM-as-judge (single) | agentic_workflows W7 |
| Canary → instant FAIL | deterministic detector floor (C3.3) | spec_addendum C3 |
| `rejudge.py` (neutral model) | cross-model judge check (D1) | review §8 D1 |
| Results CSV + reasoning + override | evidence store + HITL (A3/A10) | §6.13, A10 |
| `config.yaml` target/judge/mutator | provider adapter / Model Router (R2/A2) | §6.12, v3 §11 |
| Pillars/categories/severity/technique | scenario + Finding schema (G2) | spec_addendum |
| OWASP LLM tagging + heatmap | standards mapping | catalogue §8 |
| risk LOW/MED/HIGH, pass-rate | *(no equivalent gate)* — we add W8 deterministic gate | **gap in tool** |

---

## 4. Pillar → our 20-harness catalogue

| Tool pillar (count) | Sub-categories | Maps to our harness(es) | Note |
|---|---|---|---|
| Adversarial Safety (265) | prompt injection, jailbreaks, data exfiltration, malware, persona hijacking, system-prompt leakage | **H2.1** (injection/tool), **H1.2** (jailbreak), **H2.3** (exfiltration/leakage), **H2.2** (malware/cyber), **H1.3** (harm) | ✅ strong overlap |
| Hallucination (39) | fake entities, false premises, sycophancy, citation fabrication | **H1.4** Hallucination & Grounding | ✅ aligned |
| Capability & Robustness (43) | format adherence, multi-step reasoning, instruction hierarchy, multilingual, **over-refusal calibration** | **H1.1** Benchmark, **H1.2** | 🟡 our H1.1 lacks explicit **over-refusal calibration** |
| **Bias & Fairness (68)** | gender, race, religion, age, disability, orientation, political, loaded premises | **— none —** | 🔺 **Catalogue gap: no dedicated Bias/Fairness harness** (only "protected-class sensitivity" folded into H1.3) |

---

## 5. Capabilities to absorb from the tool (ranked; proposals only)

1. **QD / MAP-Elites evolutionary attacker (highest value).** A closed loop (seed→mutate→target→judge→archive→re-attack) that maps the *diversity* of failure modes, not just pass-rate. Superior to our static scenario sets + "loop-until-dry." **Slot:** an Advanced-Capability attacker driver for H1.2/H2.1/H2.2, plus **Coverage/Diversity/QD-Score/Peak** as observability metrics (§6.14) — answers "did we test enough variety."
2. **Per-prompt judge rubric.** Each attack scored against its own bespoke failure bar. **Slot:** refine W7 judge inputs (complements, not replaces, the quorum).
3. **Over-refusal calibration** (false-accept + false-reject). **Slot:** add to H1.1 — critical for AT&T (an over-refusing support agent is a real business cost).
4. **Neutral re-judge with a different model (`rejudge.py`).** A cheap cross-model bias check. **Slot:** complements our simultaneous quorum (A5) with a sequential cross-model pass; aligns with D1.
5. **Canary-token deterministic FAIL.** A detector-floor primitive. **Slot:** add to our C3 detector family alongside Presidio/secret/CPNI.

---

## 6. Where our solution is stronger (the tool does not cover)

- **Deterministic gate with fixed vocabulary (R9/A1)** — the tool outputs risk levels/pass-rates, not `approve/warn/block/manual_review` with policy version + rationale. No gate = not a promotion control.
- **Control/data-plane separation (R1)** and the control plane itself: **contextualization (W1), selection with skip rationale (W2/R5), provenance/lineage (§6.2), quarantine front door (W-B)** — all absent.
- **Judge robustness at decision time:** our **quorum of ≥3 diverse lenses + broad deterministic detectors (Presidio/CPNI, not just canary)** vs. the tool's single judge (its re-judge is sequential/offline).
- **Hash-chained evidence + Mode-A replay (C4/A3):** the tool has rich CSV evidence but not reconstruct-findings-from-evidence with hash verification.
- **Categories 3–5:** no **Remediation, Resilience, or Governance-as-harness** — it evaluates, it does not remediate, test resilience, or attest controls.
- **AT&T context:** no Golden Controls / CPNI / Context packs (though the **Bedrock / bedrock_mantle** backend signals enterprise/AT&T readiness).
- **Synthetic-only isolation (R7/A6):** the tool is a **live** testing tool (it calls real provider APIs in real runs); our MVP posture is synthetic-mock-first. Different by design — theirs is a real-model evaluator, ours is a governance harness; both valid, but not the same safety envelope.

---

## 7. Their empirical caveat validates our invariants

The tool's own paper — *"Mutator-Target Co-Adaptation Confounds Quality-Diversity Red-Teaming of Frontier LLMs"* — reports that when the **mutator (attacker) and target are the same/related model, QD results are confounded** (mitigated via mutator ablation + neutral re-judge). This is direct empirical support for:
- **A2** (all agents provider-independent) and **decision D1** (judge/attacker should be a *different* model family than the target).
- A concrete **design risk to encode:** attacker, target, and judge must be independent models; record model identities per run (A7) and prefer cross-family judging.

---

## 8. Findings summary (ranked)

| # | Finding | Type | Severity |
|---|---|---|---|
| F1 | Tool is a strong, working implementation of our data-plane loop (Cat 1–2) — **directionally aligned**, validates the thesis | alignment ✅ | — |
| F2 | **Bias & Fairness pillar (68) has no counterpart in our 20-harness catalogue** | gap in **our** work | High |
| F3 | **QD/MAP-Elites** attacker + coverage/diversity metrics exceed our static approach | capability to absorb | High |
| F4 | Tool has **no deterministic gate / control plane / Categories 3–5** — cannot promote/govern on its own | scope gap in **tool** | High (for platform role) |
| F5 | **Over-refusal calibration** missing from our H1.1 | gap in our work | Medium |
| F6 | Judge robustness: tool single-judge; our quorum+detector-floor stronger — but adopt tool's **canary** + **neutral re-judge** | bidirectional | Medium |
| F7 | Mutator–target co-adaptation caveat validates A2/D1; encode independence as a hard rule | risk to encode | Medium |
| F8 | Tool is **live/real-model**; our MVP is synthetic-mock — reconcile safety envelope when integrating | integration note | Medium |
| F9 | No hash-chained evidence/replay (C4) in tool | gap in tool | Low |
| F10 | Bedrock/bedrock_mantle backend suggests AT&T/enterprise readiness — a fast integration path | opportunity | Low |

---

## 9. Integration thesis (report; not applied)

```text
        OUR CONTROL PLANE (add)                     THE TOOL (reuse as-is, Cat 1–2 data plane)
        ───────────────────────                     ──────────────────────────────────────────
  Discovery→Provenance→Quarantine (W-A/W-B)   ┐
  Contextualization (W1) → Selection (W2)     ├──▶  run.py / run_qd.py  (attacks + QD)
  Deterministic GATE (W8, R9)  ◀── findings ──┤     LLM judge + rubric + canary + rejudge
  Evidence hash-chain + Mode-A replay (C4)    │     CSV/JSON/HTML evidence, OWASP heatmap
  Golden Controls / CPNI / Cat 3–5 harnesses  ┘     + ADD Bias&Fairness, over-refusal
```
**Clean read:** the tool can serve as the **Phase-1/2 harness engine for Categories 1–2**, wrapped by our control plane. Flow *from* it into our design: QD/MAP-Elites, per-prompt rubrics, canary floor, neutral re-judge, over-refusal calibration. Flow *into* it from us: the deterministic gate, quorum + broad detectors, hash-replay, contextualization/selection, and Categories 3–5 + Golden Controls.

---

## 10. Recommendations (proposals — awaiting your go-ahead; nothing changed)

1. **Add a Bias & Fairness harness** to the catalogue (Test category, e.g. `H1.5`) — closes F2.
2. **Add over-refusal calibration** to H1.1 — closes F5.
3. **Adopt QD/MAP-Elites** as an Advanced-Capability attacker driver + add Coverage/Diversity/QD-Score/Peak to observability — F3.
4. **Fold canary-floor + neutral re-judge** into the C3/A5 judge design; keep our quorum as the decision mechanism — F6.
5. **Encode attacker/target/judge model-independence** as a hard rule (A2/D1) with per-run model identities — F7.
6. **Evaluate the tool as the concrete Cat 1–2 engine** behind our run contract (it already speaks Bedrock) — F1/F10.

**No catalogue, architecture, workflow, or notebook files were modified by this review.** These are findings and proposals only.
