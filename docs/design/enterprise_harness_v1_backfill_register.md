# v1 Backfill Register — what the notebook answered that the original architecture did not

**For:** the build team. **Answers:** what the mock **v1 Colab notebook** (`enterprise_harness_mvp_colab.ipynb`, "NB") concretely decided that the **original architecture** (`enterprise_harness.md`) left absent, undefined, inconsistent, or abstract — and **how settled each decision is**.

> **How to read / articulate this (the method).** Every row states three things: (1) the **original state** — *not represented* (absent), *undefined* (named but not specified), *inconsistent*, or *abstract*; (2) the **v1 backfill** — the concrete answer and where it lives; (3) a **build class** that tells the team exactly how to treat it:
> - 🟩 **DECIDED** — concrete and correct; **build against it, don't re-open** without a spec change.
> - 🟨 **PROVISIONAL** — a working *example value*; **tune with the owner** before production (it runs, but the number/rule is a placeholder).
> - 🟦 **PLACEHOLDER** — a **stub standing in for a real dependency**; **blocked** until the real thing is supplied.
>
> In standups/PRs, cite the **Backfill ID** and its class. A 🟩 is settled; a 🟨 needs an owner sign-off; a 🟦 is a dependency ticket. Nothing here silently changes the original spec — it *fills* it, and this register is the audit trail of "not represented → backfilled."

---

## A. DECIDED backfills 🟩 — the original *named but never defined*; build against these

| ID | Item | Original state (cited) | v1 backfill (location) |
|---|---|---|---|
| BF-01 | **Runner I/O contract** (`run_config.json` → `result.json`) | undefined — named in §6.10, never specified (gap **G1**) | concrete `result.json` (harness, status, score, decision, metrics, findings, evidence, determinism) — **NB §2, §8** |
| BF-02 | **Canonical `Finding` schema** | inconsistent between §6.3 and §6.13 (gap **G2**) | one dataclass: id·severity·category·title·description·blocking·evidence_uri·recommendation·basis·standards — **NB §2** |
| BF-03 | **Gate aggregation** (N findings → 1 decision) | undefined — §6.15 gives outcomes, not the rule (gap **G4**) | first-match precedence: required-not-run→block · critical→block · high→warn · else approve — **NB §11** |
| BF-04 | **Decision vocabulary, wired** | listed but not implemented | deterministic `approve/warn/block/manual_review` + `policy_version` — **NB §11** |
| BF-05 | **Judge / scoring mechanism** | abstract — §6.10 "runner" never says *how* a harness scores behavior | LLM-judge + N-lens **quorum** + **detector-floors-judge** aggregation — **NB §7** |
| BF-06 | **Evidence chain-of-custody + replay** | §6.13 says "hash artifacts"; no reconstruction mechanism | content-hashed turns + **Mode-A replay** (rebuild findings+gate from evidence, no model) — **NB §4, §16** |
| BF-07 | **Selection + skip rationale** | abstract — §6.8 | `select()` produces plan + explicit skip reasons — **NB §10** |
| BF-08 | **Provider adapter interface** | abstract ModelRequest/Response — §6.12 | one `invoke(role,prompt,system)→{text,tokens,model}` path (mock + LiteLLM) — **NB §3, §20** |
| BF-09 | **Standards tagging on findings** | not in the original | every harness/finding tagged OWASP-LLM (+ATLAS) — **NB §5** |

---

## B. PROVISIONAL backfills 🟨 — working *example values*; an owner must tune before production

| ID | Item | Original state | v1 backfill (location) | Owner to confirm |
|---|---|---|---|---|
| BF-10 | **Risk-scoring weights + tiers** | "transparent weighted score", no weights (gap **G3**) | `RISK_WEIGHTS` (data_class/exposure/write_tools/users/criticality) + tier cutoffs — **NB §9** | governance/risk |
| BF-11 | **Judge calibration thresholds** | not in the original | precision ≥0.90 / recall ≥0.80 / accuracy ≥0.85 → gate-eligibility — **NB §15** | eval owner |
| BF-12 | **Budget ceilings + fail-closed** | no cost model (implements vis1 «Auto-stop») | max turns/tokens/cost/wall-clock; breach→`budget_exceeded`→block — **NB §8** | platform owner |
| BF-13 | **Harness set + scenarios** | §6.7 registry abstract | 5 harnesses with scenario sets, lenses, detectors — **NB §5** | red-team owner |
| BF-14 | **Determinism policy** | reproducibility of LLM eval never addressed | `determinism_class` (deterministic mock / bounded real) + stability check | eval owner |

---

## C. PLACEHOLDER backfills 🟦 — stubs for a real dependency; blocked until supplied

| ID | Item | Original / image state | v1 stub (location) | Real dependency (unblocks) |
|---|---|---|---|---|
| BF-15 | **Target model** | — | `MockAdapter` (scripted, offline) — **NB §3** | real provider via `LiteLLMAdapter`/key (§20) |
| BF-16 | **PII/CPNI detector** | — | regex SSN/account — **NB §7** | **Presidio** (+ CPNI recognizer) |
| BF-17 | **Golden Controls mapping** | vis1 «Golden Controls» drawn, never defined | `golden_control_domains` placeholder tags — **NB §5** | **AT&T Golden Controls catalogue** |
| BF-18 | **Model Router** | vis1 «Model Router» drawn, never defined | folded into the adapter — **NB §3** | AT&T-owned router (Prisma AIRS/Databricks) |
| BF-19 | **Registry / packs** | §6.7 + vis1 «Harness Registry/Pack» | `REGISTRY` dict + Foundational pack — **NB §10, §9** | real registry service + Advanced/AT&T-Context packs |

---

## D. NET-NEW backfills 🟩 — concepts *absent entirely* from the original (the assurance apparatus)

The original's Executive Summary says the platform *"validates"* and preserves *"evidence"* but never says **how to make the evaluation itself trustworthy**. v1 introduced the answer — these are new, decided, and load-bearing:

| ID | Item | v1 backfill (location) |
|---|---|---|
| BF-20 | **Judge independence** (judge ≠ target model) | enforced in the real path / truth notebook (§ real-provider; truth NB §3) |
| BF-21 | **`evidence_basis`** (real vs simulated, per finding `basis`) | stamped on every result + finding — **NB §8, §14** |
| BF-22 | **SAFETY / authorized-use boundary** (gap **G14**) | synthetic-only, no prod creds, deny-egress posture — **NB §0** |
| BF-23 | **Governance self-check (H5.1)** | Finding-Lifecycle/Evidence/Verdict harness verifies the others — **NB §12** |
| BF-24 | **Invariant acceptance suite** | 10 machine-checked invariants (R9/A1/A5/A8/C4/A7…) — **NB §18** |

---

## E. How to articulate this to the build team (one paragraph + a rule)

**Say it like this:** *"The original architecture (`enterprise_harness.md`) specified entities and APIs but left the operative contracts, the scoring/gate mechanics, and the trust apparatus unspecified. The v1 notebook backfilled them. Everything in Section A and D is **decided — build against it**; Section B is **provisional — an owner tunes the value, then build**; Section C is **placeholder — blocked on a named real dependency**. Cite the Backfill ID (BF-nn) in every PR/ticket so a reviewer instantly knows whether an item is settled, needs sign-off, or is waiting on an input."*

**The one rule that keeps this honest:** a 🟩 DECIDED item is only changed via a spec change (not in-line); a 🟨 PROVISIONAL item ships only after its **named owner** signs off the value; a 🟦 PLACEHOLDER item is a **dependency ticket** on the party that supplies the real thing (provider key, Presidio, AT&T Golden Controls / router). This register is the traceable record that every "not represented in the original" item was consciously **backfilled**, by whom class, and where it lives.

*Cite key: original = `enterprise_harness.md §…` / gap **G#** (from `enterprise_harness_design.md §7`); image labels «…» = `Enterprise_harness_platform_arch_v2.drawio`; NB § = `enterprise_harness_mvp_colab.ipynb`.*
