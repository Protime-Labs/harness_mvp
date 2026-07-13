# Extended Architecture — the Control Plane as a Negotiator

**Subject:** Enterprise AI Assurance Harness · **Status:** design for two extended requirements
1. **Switch models via the console/API** (implemented — Req 1).
2. **Trust-tiered vulnerability results** — the control plane *negotiates* which harnesses run and which safety criteria apply, and emits a **vulnerability × criteria** scorecard (designed here — Req 2; the original two-*mode* framing was trimmed — see the resolution note below).

> **✓ Trimmed — see [PILOT_SCOPE_AUDIT.md](PILOT_SCOPE_AUDIT.md).** Three over-reaches flagged in the audit were removed, so read §4–§5 below with these corrections:
> - **"operations mode" removed.** `operations` is now only a selectable `--criteria` profile (a scorecard criteria subset), never a mode — there is no inline runtime guardrail (that stays a non-goal). §4 keeps the original two-mode draft as a struck-through record.
> - **"observed trust" + gate rule `6c` removed.** The scorecard no longer infers a trust tier; it echoes the *declared* trust and flags the grounded `trusted_but_failing` case (declared-high + a blocking finding), which does **not** gate. §5's "trust reconciliation" is now that flag.
> - **gate-by-trust dynamic strictness removed.** Trust escalates the *harness set* only (monotonic, A11) — never the gate threshold or quorum-N.

---

## 0. Positioning — the control plane is not just a gate

Today the control plane *decides* (the deterministic gate) and *selects* (risk-tier packs + `require_when` clauses). The extension makes it **negotiate**: it takes three inputs and deterministically resolves the whole test posture.

```
        WHAT is under test            WHY it's used                HOW it's scored
      ┌────────────────────┐      ┌──────────────────┐        ┌──────────────────────┐
      │ model INHERENT      │      │ use-case RISK     │        │ CRITERIA PROFILE      │
      │ TRUST (Req 1)       │      │ TIER (F1–F3)      │        │ assurance | ops | cpni│
      │ untrusted…high      │      │ low | med | high  │        │ (scorecard scope only)│
      └─────────┬──────────┘      └────────┬─────────┘        └───────────┬──────────┘
                └───────────────┬──────────┴──────────────────────────────┘
                                ▼   NEGOTIATION  (deterministic · no LLM · A1)
                ┌───────────────────────────────────────────────────────────┐
                │     harness plan (trust + risk)   ·   criteria profile      │
                └───────────────────────────────────────────────────────────┘
                                ▼
                DATA PLANE runs the plan → findings → GATE → SCORECARD (vuln × criteria)
```

The keystone (A1) is preserved: **negotiation is control-plane policy — pure, config-driven, deterministic. No model call decides what to test or whether it passed.** The models are only ever the *target* and the *judges* (data plane).

---

## 1. Req 1 — model switching via the console/API (implemented)

A **model registry** (`config/models.yaml` + `defaults.MODEL_REGISTRY`) makes models first-class and selectable through the LiteLLM `ModelPort` seam (B2). Each entry carries a governance-assigned **inherent-trust** tier.

```
harness models                                   # list ids · trust · roles · key-present
harness run --provider litellm --model haiku --judge-model sonnet   # switch target + judge (A4: judge ≠ target)
harness probe --serve 8000 --model gpt4o          # live probe against a switched model
```

- `--model` accepts a **registry alias** (`haiku`) *or* a **raw LiteLLM id** (`openai/gpt-4o-mini`) — unknown aliases fail loud (never silent).
- Selecting a registry model **carries its `inherent_trust`** into the run (`INHERENT_TRUST` config), which is the first input to negotiation (Req 2).
- A4 judge-independence is still enforced in the composition root: the judge model must differ from the target.

| id | inherent_trust | roles | model |
|---|---|---|---|
| `haiku` | high | target, judge | `anthropic/claude-haiku-4-5-…` |
| `sonnet` | high | judge, target | `anthropic/claude-sonnet-4-5` |
| `gpt4o` | moderate | target, judge | `openai/gpt-4o` |
| `oss-local` | untrusted | target | `ollama/llama3` |

*Trust is a **governance judgement**, not intrinsic — provisional (BF-style), owner-editable in `models.yaml`.*

---

## 2. Inherent trust — the second selection axis

Risk tier answers *"how much does a failure cost?"* (use-case exposure). **Inherent trust answers *"how much do we believe the asset before we test it?"*** — a frontier lab model with a safety track record starts trusted; an open-weight model of unknown provenance does not. The two are orthogonal and **both** shape the test posture:

| | low risk use-case | high risk use-case |
|---|---|---|
| **high trust model** | light | risk-tier pack |
| **untrusted model** | risk-tier pack + escalation | **full battery** (same gate) |

**Trust escalation** (config-driven, parallels per-tier packs / `require_when`): lower trust *adds* harnesses — it never subtracts, and it never moves the gate. This preserves **A11 monotonicity** on the new axis (dropping trust can only widen coverage). *(The `gate_by_trust` dynamic strictness originally sketched here was removed — see the resolution note at the top; the gate threshold is one governance decision, invariant across trust tiers.)*

```yaml
# config/trust_policy.yaml (Req 2)
trust_escalation:
  high:      []                                  # baseline: risk-tier pack only
  moderate:  [H1.2, H1.5]                         # + adversarial robustness, bias
  low:       [H1.2, H1.5, H1.4, H2.2]             # + hallucination, exploit-chain
  untrusted: [H1.1, H1.2, H1.3, H1.4, H1.5, H2.1, H2.2, H2.3, H2.4]   # full battery
```

`required = union(risk_tier_pack, require_when_clauses, trust_escalation[trust])` — a straight extension of the F2/F3 resolver, still pure and still monotonic.

---

## 3. Selectable safety criteria — anchored to known taxonomies

Findings already carry OWASP-LLM tags; the extension makes **criteria first-class and selectable**. A *criterion* binds a known-vulnerability id to the harness/detector that tests it and a pass/warn/fail threshold.

Each criterion carries an explicit `std` so the scorecard never overstates conformance: OWASP-LLM **2025** where the id is precise, otherwise the honest NIST/ATLAS bucket for safety/fairness/robustness (governance owns the map in `trust_policy.yaml`).

| Criterion | Standard (`std`) | Harness |
|---|---|---|
| **LLM01** Prompt Injection | OWASP LLM01:2025 | H2.1 |
| **LLM02** Sensitive Information Disclosure | OWASP LLM02:2025 | H2.3 |
| **LLM06** Excessive Agency | OWASP LLM06:2025 | H2.2 |
| **LLM07** System Prompt Leakage | OWASP LLM07:2025 | H2.4 |
| **LLM09** Misinformation | OWASP LLM09:2025 | H1.4 |
| **SAFETY** Unsafe / Harmful Content | NIST AI RMF (safety) | H1.3 |
| **FAIRNESS** Bias / Fairness | NIST AI RMF (fairness) | H1.5 |
| **ROBUST** Adversarial Robustness / Jailbreak | MITRE ATLAS (evasion) | H1.2 |

**Criteria profiles** make the scorecard's criteria set selectable (`--criteria <profile>`) — they narrow *what the scorecard reports on*, nothing else:

```yaml
criteria_profiles:
  operations:  [LLM01, LLM02, LLM06]                                        # a narrow, fast-signal subset
  assurance:   [LLM01, LLM02, LLM06, LLM07, LLM09, SAFETY, FAIRNESS, ROBUST]  # full board (default)
  cpni-strict: [LLM02, LLM07]                                              # a focused, regulator-facing profile
```

---

## 4. ~~Two operating modes~~ — trimmed (kept as a record)

> **✗ Not built — this was the over-reach the audit removed (A1/A2).** An early draft proposed an
> `operations` mode: an **inline runtime guardrail on live traffic** (on-path, low-latency, detector-floor
> only, block/allow inline) sitting beside the offline `assurance` red-team. It was cut for two reasons:
> a runtime inline harness on the request path is an **explicit non-goal** of the design
> (`design/enterprise_harness_architecture_v3.md §10`), and the code never implemented it — `--mode`
> only narrowed the scorecard's criteria list, so an `operations` run was byte-identical to `assurance`.
>
> **What remains:** the harness runs in one posture (offline assurance). `operations` lives on only as a
> **`--criteria operations` profile** — a narrow scorecard scope, not a runtime mode. If a true inline
> guardrail is ever wanted, it is a **separate product** with its own design, not a flag on this one.

---

## 5. Output — the vulnerability × criteria scorecard

The bundle gains a `scorecard`: per-criterion pass/warn/fail keyed to the known taxonomy, plus the model's **declared trust** and a grounded `trusted_but_failing` flag.

```
ASSURANCE SCORECARD — target: haiku (inherent trust: HIGH) · use-case: customer-support (risk: HIGH) · profile: assurance

  CRITERION                         HARNESS   STATUS   EVIDENCE
  LLM01 Prompt Injection            H2.1      PASS     T-0002 (refused)
  LLM02 Sensitive Disclosure        H2.3      PASS     T-0009 (refused)
  LLM06 Excessive Agency            H2.2      PASS     T-0011 (no tool call)
  LLM07 System-Prompt Leakage       H2.4      PASS     T-0013
  LLM09 Misinformation              H1.4      WARN     T-0021 (1 borderline)

  DECLARED TRUST: HIGH   ·   trusted_but_failing: no
  GATE: APPROVE  (policy_hash sha256:…)   [the gate is decided in the domain, not here]
```

`trusted_but_failing` is a **grounded** flag, not an inferred metric: it is true exactly when the model's *declared* trust is `high` **and** the run produced ≥1 blocking finding — i.e. "we assumed this asset was safe and a hard control fired." It is **informational**: it appears on the scorecard and dashboard but does **not** move the gate. (The earlier design fabricated an "observed trust" tier and gated on it via rule `6c`; both were removed — see the resolution note at the top and [PILOT_SCOPE_AUDIT.md](PILOT_SCOPE_AUDIT.md) B1.)

The scorecard is a **renderer over existing findings** — deterministic, no new evidence, and replayable from the M3 bundle. It reports; the domain gate decides.

---

## 6. What's implemented vs designed

| Piece | State |
|---|---|
| Model registry + `harness models` + `--model`/`--judge-model` switching + inherent-trust carry-through | ✅ implemented (Req 1) |
| Trust as the second negotiation axis; `INHERENT_TRUST` config | ✅ plumbed |
| Trust → **harness-set** escalation (monotonic, A11); union with risk pack + `require_when` | ✅ implemented |
| `config/trust_policy.yaml` (`trust_escalation` + `criteria` + `criteria_profiles`) | ✅ implemented |
| `--criteria <profile>` + `--trust` + `--model`/`--judge-model` flags | ✅ implemented |
| `scorecard` in the bundle + report/dashboard renderer (grounded `trusted_but_failing` flag) | ✅ implemented |
| ~~operations *mode*, `gate_by_trust`, observed-trust + gate rule 6c~~ | ✗ removed (audit A1/B1/C1) |

**What shipped for Req 2** (each stayed green, kept `verify` ALL PASS, stayed deterministic):
1. `trust_policy.yaml` + the resolver — `required = union(risk pack, require_when clauses, trust_escalation[trust])`; **A11** extended to cover the trust axis (lower trust only widens the set).
2. `criteria` map + `criteria_profiles` + `--criteria` — bind findings ↔ criteria (OWASP-LLM 2025 where precise; NIST/ATLAS for safety/fairness/robustness, each tagged with its `std`).
3. `scorecard` builder + the grounded `trusted_but_failing` flag + report/dashboard rendering — a **view over findings**, no new gate input.

*(Trimmed per the audit: operations *mode*, `gate_by_trust` dynamic strictness, and the observed-trust → gate-rule-6c path. The scorecard reports; it does not decide.)*

Everything above is a **straight extension of the F1–F8 machinery** (per-tier packs, `require_when`, policy provenance, explainable plans) — no rewrite, no new invariant violations, and the control plane stays the sole, deterministic decider.
