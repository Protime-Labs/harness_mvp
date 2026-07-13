# Pilot Scope & Explainability Audit

**Date:** 2026-07-13 · **Reviewer:** critical second-look over everything built this cycle
**Question asked:** what in the current codebase, docs, or analysis **modifies the harness's intent**,
**does too much for a mock pilot**, or is **unexplainable within the primitives** (A1, B0–B6, the
Finding/GateDecision contracts, the control/data-plane split)?

This is a candid self-review, including where recent work over-reached. The recommendation column
distinguishes **fixed now** (safe corrections applied), **needs your call** (feature removals), and
**label** (keep, but scope honestly).

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
| **A1** | **`--mode operations` claims to be an inline runtime guardrail.** | The design corpus lists *"runtime inline harness on the request path"* as an **explicit non-goal** (`design/enterprise_harness_architecture_v3.md §10`). The extended-arch doc describes operations mode as "inline guardrail · no hot-path judge · low latency · gate allow/block inline" — repositioning the harness as a *different product* (a runtime guardrail). | **Needs your call:** remove the mode, or demote it to a named criteria profile (see A2). |
| **A2** | **…and it doesn't do any of that.** `MODE` is read in exactly one place — `scorecard.resolve_profile` — so `--mode operations` only **narrows the scorecard's criteria list**. The run is byte-identical to `assurance` (same harnesses, same judge quorum, offline). | A flag that advertises a capability the code doesn't have is worse than no flag. | **Needs your call:** if kept, rename to `--criteria operations` and delete every inline/latency/hot-path claim. |

### B — Unexplainable within the primitives

| # | Finding | Why it's a problem | Recommendation |
|---|---|---|---|
| **B1** | **"Observed trust" is a fabricated metric.** `scorecard._observed_trust` invents an ordinal (`any fail→low, warn→moderate, all pass→high`) with no basis in any primitive, then gate rule **`6c.trust_downgrade`** compares it to the model's *declared* inherent trust (a governance input) to route to `manual_review`. | The gate already blocks on findings deterministically (rules 4/6). B1 adds a second, weaker, **heuristic** path that can't be justified by A1/C3/the Finding schema — it dresses a made-up scale as a measurement and mixes a declared policy input with an inferred one. | **Needs your call:** drop `_observed_trust` + rule `6c`. If a "trusted model failed" signal is wanted, express it as a grounded fact — `declared_trust == high AND ≥1 blocking finding` — not a manufactured tier. |
| **B2** | **Criteria↔standard mapping overstates conformance.** `LLM05` is titled *"Unsafe Output / Harm"* (OWASP **LLM05:2025 is "Improper Output Handling"** — a different control; H1.3 tests harmful content, not output handling). `ATLAS-JB` is a **fabricated** technique id. `LLM09` folds in bias, which OWASP LLM09 (Misinformation) does not cover. | The scorecard asserts precise OWASP-LLM / MITRE-ATLAS coverage the harness does not have — a control claim that would not survive an audit. | **Fixed now:** corrected the OWASP ids/titles; reclassified H1.3/H1.5/H1.2 as safety/fairness/robustness (not OWASP-LLM), dropped the fake ATLAS id, added an explicit `std` per criterion. The mapping is now honest and governance-ownable. |

### C — Too much for a mock pilot

| # | Finding | Why it's a problem | Recommendation |
|---|---|---|---|
| **C1** | **Dynamic gate strictness (`gate_by_trust`).** The gate's fail-severity **and** judge quorum-N auto-vary by a *declared* model-trust tier. | The same target can `block` vs `warn` depending on a governance label, so the gate threshold is no longer one auditable decision — it's a per-run function of a soft input. That's platform machinery, not pilot-core. The *harness escalation* (more harnesses for lower trust) is fine — monotonic, explainable; the **gate-strictness** variation is the over-reach. | **Needs your call:** keep trust→harness escalation; drop (or make explicitly opt-in + logged) quorum-by-trust and severity-by-trust. |
| **C2** | **SQLite control plane + policy-hash drift are v0.2 platform, not pilot-core.** 7 tables, audit trail, outbox, `policy_hash` drift detection. | Clean and explicitly staged as "v0.2," but for a *mock pilot* the load-bearing artifacts are the deterministic gate + the replayable evidence bundle. Presenting a DB can imply production-readiness the pilot doesn't have. | **Label:** keep, but mark clearly as *v0.2 platform* everywhere; the pilot's story stays "deterministic decision + replay." |

### D — Documentation / analysis gaps

| # | Finding | Recommendation |
|---|---|---|
| **D1** | Root README stale (12 tests / 10 invariants / `dev-harness-mvp` branch / "Built for AT&T" — the code was scrubbed vendor-neutral; no mention of model switching, trust, or the scorecard). | **Fixed now:** refreshed to current state (93 tests · 11 invariants · `main` · vendor-neutral · new capabilities, honestly scoped). |
| **D2** | The extended-arch doc presents operations mode + trust reconciliation as built. | **Fixed now:** added honest caveats (operations = criteria profile only; observed-trust = heuristic) pending the A1/B1 decisions. |

---

## Recommended trims (net)

Ordered by confidence:

1. **Remove / demote `operations` mode** (A1/A2 — intent drift + unimplemented). *Highest confidence.*
2. **Remove `_observed_trust` + gate rule `6c`** (B1 — unexplainable); optionally replace with the grounded "declared-high-and-blocking-finding" note.
3. **Reconsider `gate_by_trust` dynamic strictness** (C1 — pilot over-reach); keep the harness escalation.
4. Everything else stays; the SQLite/policy-hash layer is **v0.2 platform**, labelled as such.

**Fixed in this pass** (safe, unambiguous): B2 taxonomy accuracy, D1 README refresh, D2 doc caveats.
**Awaiting your decision** (feature removals with test changes): A1/A2, B1, C1.

The net effect of the trims is a *smaller, more defensible* pilot: one deterministic gate on one
auditable policy, a scorecard that is an honest view over findings, and trust used only to widen
coverage (never to fabricate a metric or silently move the gate).
