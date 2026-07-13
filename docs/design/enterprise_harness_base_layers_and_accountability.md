# Harness Base Layers & Architect Accountability (prelim → complete)

**Audience:** the 3 architects establishing the harness base. **Assumption:** the **agentic overlay** and **Janus** are **not built**; other components (AT&T Golden Controls, Model Router, scanners) are also pending. **Goal:** a base that runs today and **evolves by filling seams**, not by rework.

> **The governing move:** build **stable base layers + explicit seams**, and **stub everything that isn't built** (Janus, agentic overlay, scanners). The framework then evolves by *implementing seams*, and you hold accountability over *ownership of uncertainty*, not over answers you don't have yet. Most base layers are already **prototyped in `enterprise_harness_mvp_colab.ipynb`** — the architects' job is to ratify them, define the seams, and own the open items.

---

## 1. The base layers (the architecture points to establish)

These are the **stable foundation** — they must not change often, because everything (including Janus + the overlay) integrates through them.

| # | Base layer | What it is (the "point") | Seam it exposes | Prototyped? |
|---|---|---|---|---|
| **B0** | **Contracts & schemas** | `run_config` → `result.json` + evidence; canonical `Finding`; `agent_turn`; event envelope | *everything speaks these* | ✅ NB §2 (ratify + version) |
| **B1** | **Plane boundary + invariants** | control (decides) vs data (executes); *agents generate/judge, policy decides* (A1); provider-independence (R2) | the rules every component obeys | ✅ conceptual (adopt as law) |
| **B2** | **Adapter / model-I/O seam** | one `invoke(role,prompt,system,model)→response` path | **← Janus, providers, Model Router plug here** | ✅ NB §3/§20 |
| **B3** | **Harness runner + run contract** | the execution shape: attacker → target → judge; honors B0 | **← drivers plug here (agentic overlay, PyRIT/Garak, built-ins)** | ✅ NB §8 |
| **B4** | **Evidence store + replay** | content-hashed chain of custody; reconstruct findings from evidence | **← audit, remediation, SIEM read here** | ✅ NB §4/§16 |
| **B5** | **Deterministic gate** | the single decision point (approve/warn/block/manual_review); no LLM | **← CI/CD, deployment consume here** | ✅ NB §11 |
| **B6** | **Policy/config layer** | externalized weights, thresholds, quorum, budgets, rules | **← domain owners tune here (no code change)** | 🟨 partly (move inline → `config/*.yaml`) |

**Rule of the base:** a base layer changes **only** by a versioned contract change (B0/B1); a component change is *filling a seam* (B2–B5) or *tuning config* (B6). This is what lets the framework evolve without breaking the base.

---

## 2. Seams for the not-yet-built components (define now, fill later)

You don't build Janus/the overlay — you define the **interface** they plug into, so their teams build to it and you stub until they arrive.

| Not-yet-built | Plugs into seam | Interface it must satisfy | Stub until then |
|---|---|---|---|
| **Janus** (role TBD) | B2 adapter | expose `invoke(...)→{text,tokens,model,...}` **or** a documented API we adapt; emit telemetry in the B0 event envelope | mock source (NB §3) |
| **Agentic overlay** | B3 run contract | consume the transcript / produce adaptive attacks; emit `result.json` + `Finding[]` (B0) | built-in scenario driver (NB §5/§6) |
| **Model Router** (AT&T) | B2 adapter (in front) | route model choice; pass through to the adapter | adapter picks the model directly |
| **Security/quarantine scanners** | B0 finding schema | emit normalized `Finding[]` + a decision | none (gap; front door deferred) |
| **Golden Controls** | B6 config + B0 standards | a control catalogue (IDs+text) mapped to finding categories | `golden_control_domains` placeholder tags |

**The point:** every future component becomes a *seam implementation*, not an architecture change. Define the 5 interfaces above and the base is "integration-ready" for things that don't exist yet.

---

## 3. Who provides what — the 3-architect split (to begin work)

| Architect | Owns (base layers) | Provides to begin |
|---|---|---|
| **A1 — Contracts & Control Plane** | B0 schemas, B1 invariants, B5 gate, B6 config | the versioned schemas (`contracts/*.json`), the invariant list, the gate precedence, and `config/*.yaml` skeletons |
| **A2 — Data Plane & Integration** | B2 adapter, B3 runner, the 5 seams | the adapter + runner interfaces, the **seam specs** (one-pager each), and working stubs so the chain runs end-to-end today |
| **A3 — Assurance & Governance** | B4 evidence/replay, calibration/independence/stability, standards/Golden-Controls mapping, scanner seam | the evidence schema, the truth apparatus, the standards mapping, and the security/quarantine seam |

**Shared, signed by all three:** B1 invariants (they're the constitution) and the B0 contracts (the shared language). Everything else has a single owner.

---

## 4. What to ask for, and how to provide it (the elicitation mechanism)

The backfill classes tell you exactly *who to ask and how they answer*. Turn each open item into an **owned ask**:

| Item (example) | Class | **Ask (what you request)** | From whom | **How provided (artifact)** |
|---|---|---|---|---|
| Risk weights + tiers (BF-10) | 🟨 provisional | "confirm/adjust these weights + cutoffs for AT&T risk appetite" | risk/governance owner | edit `config/risk_weights.yaml` + sign-off in the register |
| Judge thresholds (BF-11) | 🟨 provisional | "confirm the precision/recall bar + supply labeled ground truth" | eval owner | `config/quorum.yaml` + a labeled GT set |
| Budgets/SLO (BF-12) | 🟨 provisional | "confirm cost/latency/turn ceilings" | platform owner | `config/budgets.yaml` |
| Golden Controls (BF-17) | 🔶 placeholder | "the control catalogue (IDs+text) + CPNI rules" | AT&T governance | `config/golden_controls.yaml` mapping |
| **Janus** | 🔶 placeholder | "what *is* Janus — provider? router? agent runtime? — and its invoke/telemetry interface" | Janus team | an interface spec implementing the **B2 seam** |
| **Model Router** | 🔶 placeholder | "does AT&T have a router; its API" | AT&T platform | router API spec → B2 adapter |
| Scanners | 🔶 placeholder | "which scanners + their finding format" | security team | scanner adapters emitting the **B0 Finding** |

**How to *provide* any value (the pattern):** externalize it into a **`config/*.yaml` owned file**, never hardcode. A provisional default lets build proceed today; the **named owner's sign-off** (recorded in the register) is what makes it real. That's the whole "how do I provide them" — a config file + an owner + a dated sign-off.

---

## 5. Accountability without knowing all the questions (the crux)

You cannot enumerate every question up front — and you don't need to. **Make *ownership of uncertainty* the unit of accountability, not answers.**

- Every architecture element is a row in a **living decision register** with: `id · description · STATE · OWNER · default/stub · the ASK · target date`.
- **Four states, and `Unknown` is first-class and valid:**
  - 🟩 **Decided** — ratified, in a versioned contract/config.
  - 🟨 **Provisional** — default in `config/`, owner assigned, review date set.
  - 🔶 **Placeholder** — seam defined, dependency ticket on the external team.
  - ⬜ **Unknown** — *we don't know yet* — **owner assigned, spike scheduled**.
- **The only failure is an element with no owner.** You are not accountable for *knowing the answer*; you are accountable for *owning the item and moving it*.
- **Definition of Done per state** (this is how "done" is measured without the answer): Unknown→owner+spike · Provisional→default+owner+review-date · Placeholder→seam+dependency-ticket · Decided→versioned+signed.
- **Cadence:** a weekly architecture review walks the register; every Unknown must have *moved* (owner ran a spike → proposed a default → became Provisional; or raised a dependency → became Placeholder). You review **movement and ownership**, not correctness of answers you can't have yet.

> **In one line:** you hold accountability by making sure **every uncertainty has an owner and a state**, and a weekly review that forces movement — `Unknown → Question → Provisional/Placeholder → Decided`. The register *is* the "what to ask": each Provisional is a tuning ask, each Placeholder is a dependency ask, each Unknown is a spike.

---

## 6. How to complete the prelim → "base established"

**Exit criteria (Definition of Done for the base):**
1. **B0 contracts versioned + signed** by all three (the shared language is frozen-ish).
2. **B1 invariants adopted** as the constitution (agents judge; policy decides; provider-independent).
3. **The 5 seams specified** (one-pager each) so Janus/overlay/router/scanners/Golden-Controls know what to build against.
4. **B2–B5 running end-to-end on stubs** (the v1 notebook already does this — ratify it as the reference implementation).
5. **All provisional values externalized to `config/*.yaml`** with named owners.
6. **The living decision register stood up**, every open item owned and stated, weekly review scheduled.

When those six are true, the base is *established*: it runs today, it's integration-ready for the unbuilt components, and every open question is owned and moving — which is exactly how you "complete this and hold accountability without knowing what to ask."

---

## 7. Starter decision register (extend this)

| ID | Element | State | Owner | Default/stub | The ASK | Due |
|---|---|---|---|---|---|---|
| DR-01 | `Finding` schema (B0) | 🟩 Decided | A1 | NB §2 | ratify + version | — |
| DR-02 | Run contract (B0) | 🟩 Decided | A1 | NB §8 | ratify + version | — |
| DR-03 | Risk weights (B6) | 🟨 Provisional | A3 + risk owner | `config/risk_weights.yaml` | confirm for AT&T | wk 2 |
| DR-04 | Judge thresholds (B6) | 🟨 Provisional | A3 + eval owner | NB §15 defaults | confirm + GT set | wk 3 |
| DR-05 | Janus interface (B2 seam) | 🔶 Placeholder | A2 + Janus team | mock source | define invoke/telemetry seam | wk 2 |
| DR-06 | Agentic-overlay driver (B3 seam) | 🔶 Placeholder | A2 + overlay team | built-in driver | define driver seam | wk 3 |
| DR-07 | Golden Controls (B6/B0) | 🔶 Placeholder | A3 + AT&T gov | domain tags | catalogue IDs+text | wk 4 |
| DR-08 | Model Router (B2) | ⬜ Unknown | A2 | adapter-direct | does AT&T have one? | wk 1 spike |
| DR-09 | Scanner front door (B0) | ⬜ Unknown | A3 + security | none | which scanners + format | wk 2 spike |
| DR-10 | Continuous monitoring (§6.17) | ⬜ Unknown | A1 | off-path replay | scope vs "no prod coupling" | wk 4 spike |

*Cite key: base layers B0–B6; NB § = `enterprise_harness_mvp_colab.ipynb`; BF-## = `enterprise_harness_v1_backfill_register.md`; gaps G# = `enterprise_harness_design.md §7`.*
