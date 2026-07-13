# Pilot Scope & Explainability Audit

**Date:** 2026-07-13 · **Reviewer:** critical second-look over everything built this cycle
**Question asked:** what in the current codebase, docs, or analysis **modifies the harness's intent**,
**does too much for a mock pilot**, or is **unexplainable within the primitives** (A1, B0–B6, the
Finding/GateDecision contracts, the control/data-plane split)?

This is a candid self-review, including where recent work over-reached. The recommendation column
distinguishes **fixed now** (safe corrections applied), **needs your call** (feature removals), and
**label** (keep, but scope honestly).

> **✓ Update (2026-07-13) — all three trims are now applied.** The owner accepted the removals:
> **A1/A2** operations *mode* removed (`operations` survives only as a `--criteria` profile); **B1**
> `_observed_trust` + gate rule `6c` removed (replaced by the grounded `trusted_but_failing` flag);
> **C1** `gate_by_trust` dynamic strictness removed (trust escalates the harness set only, A11). The
> "needs your call" cells below are kept for the record and marked **Applied**. Suite is green
> (91 tests · `harness verify` ALL PASS); no dangling references remain.

---

## What is solid (well-grounded — no change)

The core maps cleanly onto the primitives and is appropriately scoped for a mock pilot:
deterministic gate (A1) · quarantine secrets scanner + short-circuit · Mode-A replay bundle + tamper
(C4) · risk-tier packs + `require_when` + coverage fail-closed (A11) · strict config + tighten-only
overrides (F5/F6) · explainable plans (F8) · model switching (Req 1) · the **scorecard as a view over
findings**. Keep all of it.

---

## Findings

### A — Modifies the harness's intent

| # | Finding | Why it's a problem | Recommendation |
|---|---|---|---|
| **A1** | **`--mode operations` claims to be an inline runtime guardrail.** | The design corpus lists *"runtime inline harness on the request path"* as an **explicit non-goal** (`design/enterprise_harness_architecture_v3.md §10`). The extended-arch doc described operations mode as "inline guardrail · no hot-path judge · low latency · gate allow/block inline" — repositioning the harness as a *different product* (a runtime guardrail). | **✅ Applied:** the mode is removed. `--mode` no longer exists; the inline/latency/hot-path claims are struck from the docs. |
| **A2** | **…and it doesn't do any of that.** `MODE` was read in exactly one place — `scorecard.resolve_profile` — so `--mode operations` only **narrowed the scorecard's criteria list**. The run was byte-identical to `assurance` (same harnesses, same judge quorum, offline). | A flag that advertises a capability the code doesn't have is worse than no flag. | **✅ Applied:** demoted to `--criteria operations` (a scorecard criteria subset). `MODE` config, the `--mode` flag, and `GATE_BY_TRUST` are gone. |

### B — Unexplainable within the primitives

| # | Finding | Why it's a problem | Recommendation |
|---|---|---|---|
| **B1** | **"Observed trust" is a fabricated metric.** `scorecard._observed_trust` invented an ordinal (`any fail→low, warn→moderate, all pass→high`) with no basis in any primitive, then gate rule **`6c.trust_downgrade`** compared it to the model's *declared* inherent trust (a governance input) to route to `manual_review`. | The gate already blocks on findings deterministically (rules 4/6). B1 added a second, weaker, **heuristic** path that couldn't be justified by A1/C3/the Finding schema — it dressed a made-up scale as a measurement and mixed a declared policy input with an inferred one. | **✅ Applied:** `_observed_trust` and gate rule `6c` are removed. The signal is now the grounded fact `trusted_but_failing = (declared_trust == "high" AND ≥1 blocking finding)` — surfaced on the scorecard, **not** gated on. |
| **B2** | **Criteria↔standard mapping overstates conformance.** `LLM05` is titled *"Unsafe Output / Harm"* (OWASP **LLM05:2025 is "Improper Output Handling"** — a different control; H1.3 tests harmful content, not output handling). `ATLAS-JB` is a **fabricated** technique id. `LLM09` folds in bias, which OWASP LLM09 (Misinformation) does not cover. | The scorecard asserts precise OWASP-LLM / MITRE-ATLAS coverage the harness does not have — a control claim that would not survive an audit. | **Fixed now:** corrected the OWASP ids/titles; reclassified H1.3/H1.5/H1.2 as safety/fairness/robustness (not OWASP-LLM), dropped the fake ATLAS id, added an explicit `std` per criterion. The mapping is now honest and governance-ownable. |

### C — Too much for a mock pilot

| # | Finding | Why it's a problem | Recommendation |
|---|---|---|---|
| **C1** | **Dynamic gate strictness (`gate_by_trust`).** The gate's fail-severity **and** judge quorum-N auto-varied by a *declared* model-trust tier. | The same target could `block` vs `warn` depending on a governance label, so the gate threshold was no longer one auditable decision — it was a per-run function of a soft input. That's platform machinery, not pilot-core. The *harness escalation* (more harnesses for lower trust) is fine — monotonic, explainable; the **gate-strictness** variation was the over-reach. | **✅ Applied:** `gate_by_trust` removed. Trust escalates the **harness set only** (monotonic, A11); the gate threshold and quorum-N are a single governance decision, invariant across trust tiers. |
| **C2** | **SQLite control plane + policy-hash drift are v0.2 platform, not pilot-core.** 7 tables, audit trail, outbox, `policy_hash` drift detection. | Clean and explicitly staged as "v0.2," but for a *mock pilot* the load-bearing artifacts are the deterministic gate + the replayable evidence bundle. Presenting a DB can imply production-readiness the pilot doesn't have. | **Label:** keep, but mark clearly as *v0.2 platform* everywhere; the pilot's story stays "deterministic decision + replay." |

### D — Documentation / analysis gaps

| # | Finding | Recommendation |
|---|---|---|
| **D1** | Root README stale (12 tests / 10 invariants / `dev-harness-mvp` branch / "Built for AT&T" — the code was scrubbed vendor-neutral; no mention of model switching, trust, or the scorecard). | **Fixed:** refreshed to current state (91 tests · 11 invariants · `main` · vendor-neutral · new capabilities, honestly scoped). |
| **D2** | The extended-arch doc presents operations mode + trust reconciliation as built. | **Fixed:** the caveats became a resolution note once the trims landed — operations is a criteria profile only; observed-trust/rule-6c and gate-by-trust are removed. |

---

## Recommended trims (net) — all applied

Ordered by confidence; every one is now **done**:

1. **Removed / demoted `operations` mode** (A1/A2 — intent drift + unimplemented). `operations` survives only as a `--criteria` profile. *Highest confidence.* ✅
2. **Removed `_observed_trust` + gate rule `6c`** (B1 — unexplainable); replaced with the grounded `trusted_but_failing` flag (declared-high **and** a blocking finding), informational only. ✅
3. **Removed `gate_by_trust` dynamic strictness** (C1 — pilot over-reach); kept the harness escalation. ✅
4. Everything else stays; the SQLite/policy-hash layer is **v0.2 platform**, labelled as such.

**Fixed earlier in the pass** (safe, unambiguous): B2 taxonomy accuracy, D1 README refresh, D2 doc caveats.
**Now applied** (the feature removals, with test changes): A1/A2, B1, C1 — 91 tests green, `verify` ALL PASS.

The net effect of the trims is a *smaller, more defensible* pilot: one deterministic gate on one
auditable policy, a scorecard that is an honest view over findings, and trust used only to widen
coverage (never to fabricate a metric or silently move the gate).
