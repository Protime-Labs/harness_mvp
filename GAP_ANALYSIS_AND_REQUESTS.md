# Gap Analysis & Request Register — Original Architecture → v0.2 Prototype

**Subject:** Enterprise AI Assurance Harness
**Baseline (design):** the design corpus (`enterprise_harness_*.md`, `ENTERPRISE_HARNESS_REFERENCE_ARCHITECTURE.md`, base-layer + backfill registers)
**Delivered (prototype):** `origin/main` @ `v0.2.0-mvp` — M1–M5 + vendor-neutral + endpoint assets
**Status of prototype:** 58 tests pass · `harness verify` 10/10 invariants · both DoD flows demonstrated
**Purpose:** the decisions, sign-offs, and data to *request* from the architecture/enterprise owners to take the prototype from a proven core to an enterprise MVP.

---

## 0. Executive summary

The prototype delivers the **deterministic assurance core and a local control-plane spine** — proven, replayable, and honest about its own limits. It maps 1:1 onto the design's base layers **B0–B6** and enforces the load-bearing invariants (A1 no-LLM-in-gate, C3 detector-floor, A8 fail-closed, C4 replay, A9 calibration-gating, A4 judge independence).

**The gap is not the architecture — the clean/hexagonal shape is correct and matches the spec.** The gap is five concrete things, in priority order:

| # | Gap class | Nature | Who closes it |
|---|---|---|---|
| 1 | **Owner sign-offs** on provisional config (risk weights, judge thresholds, budgets, harness set) | Decision | Internal owners (governance/eval/platform/red-team) |
| 2 | **AT&T-supplied data & seams** (Golden Controls catalogue, Model Router, Janus identity, scanner front-door) | Decision + data + integration | AT&T |
| 3 | **Judge ground-truth calibration set** (80 labeled samples) — the top pre-build data task | Data | Eval/design |
| 4 | **Persistence & catalogue breadth** (7 of 20 slice-1 tables; 10 of 20 harnesses) | Build | Platform team |
| 5 | **Enterprise integration + scale-out** (WORM, SIEM, RBAC, event bus, K8s/Temporal/Kafka) | Integration (mostly explicit non-goals for MVP) | Platform + AT&T infra |

**One line:** *going enterprise is a controlled sequence of owner sign-offs and seam bindings — not a rewrite.*

---

## 1. Coverage map — the 20 platform layers (§6.1–6.20)

Legend: ✅ delivered · 🟨 partial · 🔶 stub-by-design (seam ready, dependency absent) · ⬜ deferred

| # | Layer | Design MVP depth | Prototype | Gap → what closes it |
|---|---|---|---|---|
| 6.1 | Discovery | LITE | 🟨 | Manual `asset-register` only (M4). Needs GitHub/K8s/registry connectors (deferred). |
| 6.2 | Provenance & Lineage | FULL | 🟨 | `asset_versions` content-hash ✅; **`provenance_records` + `asset_lineage` edges missing**. |
| 6.3 | Quarantine & Security | FULL (1 scanner) | 🟨 | Local **secrets** scanner + short-circuit (M2) ✅; needs the real scanner front-door (SBOM/malware/license/SAST) — **DR-09**. |
| 6.4 | Provider-Agnostic Normalization | FULL (static) | 🟨 | Endpoint-asset normalization (M5) ✅; **model/tool/agent capability records + 15-tag enum (G8) missing**. |
| 6.5 | Use-Case Intake | FULL | ✅ | `usecase-create` + schema. `use_case_data_classes/users/controls` child tables not split out. |
| 6.6 | Contextualization | FULL (YAML) | ✅ | Risk weights → tier → pack (config-driven). Rules are weights, not `contextualization_rules` (G5). |
| 6.7 | Harness Registry | FULL | 🟨 | In-code `REGISTRY` + YAML specs ✅; **not a versioned registry service** (`harness_versions/approvals/compatibility`). |
| 6.8 | Selection & Policy | FULL | ✅ | Plan + skip rationale + `coverage_complete` fail-closed (M1). |
| 6.9 | Orchestration | LITE | ✅ | In-process sequential (`orchestrator`). Temporal/Argo deferred by design. |
| 6.10 | Harness Runner | FULL | ✅ | `BuiltinDriver` (B3) + quorum + detectors + budget. |
| 6.11 | Runtime Environment | LITE | 🟨 | Temp-dir evidence; **no explicit isolation/egress-policy record** (`runtime_environments`, network-deny). |
| 6.12 | Provider Adapter | FULL (mock first) | ✅ | Mock + LiteLLM (real cost, M2) + HTTP. |
| 6.13 | Evidence Store | FULL | ✅ | File-backed, input+output hashed (M3). WORM is the enterprise target (🔶). |
| 6.14 | Observability & Analytics | DEFER | ⬜ | Dashboard + report only (by design). |
| 6.15 | CI/CD Gate | FULL | ✅ | Deterministic gate (M1). **Missing W8 rules 5–6: expired-waiver, unapproved-provider** (see §4). |
| 6.16 | Remediation Automation | LITE | ✅ | Advisory records (W9). Destructive actions deferred (A10). |
| 6.17 | Runtime Telemetry & Replay | DEFER | 🟨 | **Mode-A replay from disk ✅** (M3, exceeds LITE); runtime traces / Mode-B deferred. |
| 6.18 | Governance & Audit | FULL (audit) | ✅ | H5.1 self-check + `audit_events` append-only (M4). |
| 6.19 | RBAC & IAM | DEFER | ⬜ | Config stub URLs only (`RBAC_PROVIDER_URL`). |
| 6.20 | Event Bus | LITE | ✅ | `event_outbox` in-process (M4). Kafka deferred. |

**Net:** every FULL/LITE layer is present at least partially; the material gaps are **6.2 provenance/lineage**, **6.3 full scanner front-door**, **6.4 capability normalization**, and **6.7 registry-as-service**.

---

## 2. Invariant coverage

| Invariant | Guarantee | Enforced? | Evidence in prototype |
|---|---|---|---|
| **A1** | No LLM in gate/risk path | ✅ | `gate.py` + bytecode assertion + import lint (`test_boundaries`) |
| **R2/A2** | Provider independence | ✅ | `ModelPort`; import lint bans provider SDKs outside adapters/model |
| **A3/R6** | Evidence = hashed chain of custody | ✅ | `file_evidence` (input+output), `evidence_manifest`, `validate-run` |
| **A4** | Judge isolated + independent (judge ≠ target) | ✅ | `factory` enforces judge≠target; BF-20 |
| **A5** | Findings ≥ high need N independent judges | ✅ | quorum in `runner`; `aggregate` |
| **C3** | Detector floors the judge | ✅ | `aggregate` + gate rule 4 (`detector_blocking_finding`, M1) |
| **A7/C5** | Determinism pinned + disclosed | ✅ | seed/`determinism_class`; `stability` (Jaccard) |
| **A8/C6** | Budgets enforced, fail-closed | ✅ | `runner` (turns/tokens/**cost**/wall-clock, M2) |
| **A9/C1** | Miscalibrated judge cannot gate | ✅ *(mechanism)* | `judge_calibration` → gate rule 5. **Uses 9 fixed fixtures, not the real 80-sample GT set (C1/G15) — data gap, §6.** |
| **C4** | Mode-A replay | ✅ | `replay` + `validate-run` from disk; tamper fails |
| **R9** | Fixed decision vocabulary | ✅ | `GATE_VOCAB` |
| **C2** | Adapter-boundary import lint | ✅ | `test_boundaries` (M5) |
| **R5** | Explainable selection + skip rationale | ✅ | `selection` |
| **R8** | Transactional outbox | 🟨 | `event_outbox` rows written; no relay/consumer yet |
| **A10** | HITL for irreversible remediation | 🟨 | advisory only; no waiver/approval workflow (G13) |
| **G12** | `tenant_id` on every table from day one | ⬜ | **Not present — schema decision to make now (§7)** |

---

## 3. Data-model gap — slice-1 table set (20 tables)

Prototype persists **7 of the 20** slice-1 tables (M4):

| ✅ In prototype (7) | ⬜ Deferred (13) |
|---|---|
| `assets`, `asset_versions`, `use_cases`, `evaluation_runs`, `gate_decisions`, `audit_events`, `event_outbox` | `provenance_records`, `use_case_assets`, `use_case_data_classes`, `use_case_users`, `security_findings`, `contextualization_results`, `harness_definitions`, `harness_execution_plans`, `harness_execution_plan_items`, `harness_selection_decisions`, `harness_runs`, `findings`, `evidence_artifacts` |

Decisions to make before growing the schema (see §7):
- **Table-name generation to adopt:** slice-1 (`assets`, `gate_decisions`) vs design §5 (`discovered_assets`, `cicd_gate_decisions`). *Recommend slice-1 names — already in code.*
- **`tenant_id` (G12):** add to every table now (single-tenant runtime, multi-tenant schema) — cheap now, expensive later.
- **DDL:** no canonical DDL exists in the corpus; the M4 schema (`storage/repository.py`) is the de-facto first migration (`db/0001_core_tables.sql` equivalent).

---

## 4. Harness catalogue gap — 10 of 20

| Delivered (10, with scenarios) | Missing (10, catalogue-only) |
|---|---|
| **P1:** H2.1, H1.2, H1.3, H2.3, H5.1 · **Advanced:** H1.1, H1.4, H2.2, H2.4, H1.5 | H4.4 (declared, not impl) · **Cat 3 Remediation** H3.1–H3.4 (Phase 3) · **Cat 4 Resilience** H4.1–H4.3 · **Cat 5 Gov** H5.2–H5.4 · deeper H2.2 exploit-chain, H2.4 business-impact |

**Not built (drivers/harnesses named in design):** W6 **RAG-poisoning** harness (needs **Ragas**); **Garak** extraction probes and **Promptfoo** RBAC plugins (drivers are seams, not yet exercised).

**Gate precedence — two rules from the design's 9-rule W8 are absent** (worth an explicit decision):
- **Expired-waiver → block** (needs the waiver↔gate model, **G13**).
- **Unapproved provider/model/tool → block** (needs a provider/model approval list).
The prototype instead adds `detector_blocking_finding`, `evaluator_not_calibrated`, and `cost_unknown` rules (M1/M2) — arguably stronger, but the waiver + provider-approval rules should be added for parity.

---

## 5. REQUEST LIST — decisions & sign-offs to escalate

These come straight from the design's **Decision Register (DR-01–10)** and **Backfill Register (BF-10–19)**. *"The only failure is an element with no owner."*

### 5a. Internal owner sign-offs — provisional config (ship default, needs dated sign-off)

| ID | Request | Owner to confirm | Unblocks | Priority |
|---|---|---|---|---|
| **BF-10 / DR-03** | Ratify **risk weights + tier cutoffs** (`config/risk_weights.yaml`) | governance / risk | Contextualization tiering (W1) for AT&T context | High (wk 2) |
| **BF-11 / DR-04** | Ratify **judge calibration thresholds** (P≥0.90 / R≥0.80 / A≥0.85) | eval | Gate-eligibility (A9) validity | High (wk 3) |
| **BF-12 / C6** | Ratify **budget ceilings** (20 turns / 200k tok / $5 / 600 s) | platform | Real-provider cost governance (A8) | Medium |
| **BF-13** | Ratify **harness set + scenarios** (the 5→10 shipped) | red-team | Coverage claims; scenario corpus (G11) | High |
| **BF-14 / C5** | Ratify **determinism policy** (`deterministic` mock / `bounded` real, Jaccard ≥0.90) | eval | Honest A7 disclosure | Medium |

### 5b. AT&T / enterprise decisions — seams blocked on an external dependency

| ID | Request | Owner | Unblocks | Priority |
|---|---|---|---|---|
| **DR-08 / BF-18** | **Does AT&T have a Model Router?** If so, its interface | AT&T + adapter | B2 routing; H4.2 failover; removes "folded-into-adapter" stub | **Highest (wk-1 spike)** |
| **DR-05** | **Janus** — confirm its role (provider? router? agent runtime?) + invoke/telemetry seam | AT&T + Janus team | B2 real source; retire mock source | High (wk 2) |
| **DR-07 / BF-17** | **Golden Controls catalogue** — supply real control IDs + text | AT&T governance | `golden_controls.yaml` (currently `status: unresolved`); enterprise attestation | High (wk 4) |
| **DR-09** | **Scanner front-door** — which scanners (gitleaks/Trivy/Semgrep/ModelScan…) + output format | AT&T security | Full quarantine layer (6.3) beyond the local secrets floor | High (wk 2 spike) |
| **DR-10** | **Continuous-monitoring** scope vs "no production coupling" (R7) | architecture | 6.17 telemetry boundary | Medium (wk 4 spike) |
| — | **Prisma AIRS** — source vs scanner role | AT&T | normalization + routing | Medium |

---

## 6. DATA REQUIREMENTS — what the platform must be fed

| Data input | Owner | Format / location | Status | Blocked without it |
|---|---|---|---|---|
| **Judge ground-truth calibration set** (C1/G15) — 80 labeled samples (per harness: 8 clear + 2 borderline success, 8 + 2 refusal) | eval / design | `gt/<harness>/*.jsonl` | ⛔ **Top pre-build task.** Prototype uses **9 fixed fixtures** (target-independent mechanism), *not* the real GT set | Real A9 calibration → real gate-eligibility |
| **Golden Controls catalogue** (IDs + text) | AT&T governance | `config/golden_controls.yaml` | 🔶 `status: unresolved` (BF-17) | Enterprise control attestation |
| **Scenario corpus** (per-harness attack sets) | red-team | `config/harnesses.yaml` / `scenarios/*.jsonl,csv` | 🟨 built-in 5→10; loader + schema ✅ (M5) | Breadth + realism (G11) |
| **Synthetic PII/CPNI fixtures** (e.g. SSN `123-45-6789`) | red-team / eval | in mock + scenarios | ✅ present | Detector evidence (G11) |
| **Risk weights + tier cutoffs** | governance/risk | `config/risk_weights.yaml` | 🟨 provisional (BF-10) | Tiering |
| **Judge thresholds (P/R/A)** | eval | `config/quorum.yaml` | 🟨 provisional (BF-11) | Gating validity |
| **Budget ceilings** | platform | `config/budgets.yaml` | 🟨 provisional (BF-12) | Cost governance |
| **Model IDs + roles** (judge ≠ target family) | eval/platform | `config/quorum.yaml` | ✅ enforced (A4) | Independence |
| **Provider credentials** (ANTHROPIC/OPENAI/AWS) | operator | env (never stored) | operator-supplied | Real runs |
| **Model pricing / cost catalogue** | adapter/FinOps | `config/model_pricing.yaml` | 🟨 LiteLLM cost + fallback (M2); no full price catalogue | Cost accuracy on non-LiteLLM models |
| **Data-classification taxonomy** (…+ **CPNI**) | governance | `use_case_data_classes` | 🟨 CPNI present; taxonomy not formalized | Contextualization |
| **User-population taxonomy** | governance | `use_case_users` | 🟨 informal | Contextualization |
| **Contextualization rules** (versioned YAML/OPA, e.g. `RULE-PII-001`) | security + governance | `contextualization_rules.yaml` | ⬜ weights only (G5) | Rule-floored tiering |
| **Asset inventory / metadata** (discovery connectors) | AT&T | manual for MVP; key = `sha256(type+identity)` | 🟨 manual register ✅ (G7) | Auto-discovery |
| **Capability taxonomy** (closed 15-tag enum, G8) | normalization | code | ⬜ not enforced | Selection precision |
| **Fault-injection profiles** | platform | `fault_injection_profiles` | ⬜ | Resilience harnesses (Cat 4) |
| **Waiver policy** (waiver↔gate, G13) | governance/platform | — | ⬜ | Waiver gate rule |
| **SAFETY.md authorized-use boundary** (G14/BF-22) | design | `SAFETY.md` | verify present (synthetic-only, deny-egress, no prod creds) | Authorized-use posture |

---

## 7. Architectural decision points to ratify / resolve

### 7a. Ratify the DECIDED contracts (sign + version — no rework, just governance)
`DR-01` Finding schema · `DR-02` Run contract · `BF-01–09` (runner I/O, Finding, gate aggregation, vocabulary, judge quorum, evidence/replay, selection, adapter, standards tagging). **Ask:** formal ratification + a schema version stamp.

### 7b. Resolve the OPEN decisions
| Decision | Options | Recommendation |
|---|---|---|
| **Table-name generation** (`assets` vs `discovered_assets`; `gate_decisions` vs `cicd_gate_decisions`) | slice-1 names / design-§5 names | **slice-1** (in code) |
| **`tenant_id` from day one (G12)** | add now / retrofit later | **Add now** — single-tenant runtime, multi-tenant schema |
| **Waiver ↔ gate (G13)** + **provider-approval** gate rules | add W8 rules 5–6 / omit | **Add both** for design parity |
| **Mode-B replay (re-execution)** | build now / defer (C4) | **Defer** — Mode-A is MVP-mandatory and delivered |
| **Continuous monitoring (DR-10)** | on-path / off-path replay only | **Off-path only** — preserve R7 |
| **Cisco AI Defense / other platforms** | integrate / orchestrate-above | **Orchestrate-above** — our gate authoritative (ADR) |
| **Registry as service (6.7)** vs in-code | build service / keep code+YAML | Keep for MVP; service in enterprise phase |

---

## 8. Enterprise-dependency register — the not-wired seams

| Dependency | Seam | Role | To wire it, need… | Serves |
|---|---|---|---|---|
| **Janus** | B2 | AT&T model source | role confirmation + invoke/telemetry seam (DR-05) | R2/A2 |
| **Model Router** | B2 (in front) | request routing | AT&T router interface (DR-08/BF-18) | H4.2 failover |
| **Prisma AIRS** | B2/scanner | runtime security | source-vs-scanner role | quarantine/routing |
| **Golden Controls** | B6+B0 | control anchor | catalogue IDs+text (DR-07/BF-17) | attestation |
| **Scanner front-door** | B0 Finding | SBOM/secrets/malware/license/SAST | scanner set + format (DR-09) | 6.3 / W-B |
| **WORM / append-only** | B4 | tamper-proof evidence | S3 Object Lock / append-only DB | R6/A3 |
| **SIEM/SOAR** (Wazuh/OpenSearch/Elastic) | B4 | security export | export interface (Days 61–90) | observability |
| **RBAC/IAM/OIDC/SSO** | 6.19 | identity | enterprise IdP | governance |
| **Kafka / Pulsar** | 6.20 | event bus | broker + consumers | R8 at scale |
| **Temporal / Argo** | 6.9 | durable orchestration | worker infra | orchestration at scale |
| **Kubernetes / Podman** | 6.11 | isolation | runtime infra | R7 |
| **Ragas** | Scorer | RAG faithfulness | wire for W6 RAG harness | H-RAG |

*(Kafka/Temporal/K8s/IAM/SIEM are explicit MVP **non-goals** — listed here for the enterprise roadmap, not as MVP blockers.)*

---

## 9. What the prototype delivers *beyond* the original design (net-new)

The assurance apparatus that was absent from the source design and is now built + tested:

- **BF-20** judge independence · **BF-21** `evidence_basis` (real vs simulated per finding) · **BF-22** SAFETY / authorized-use boundary · **BF-23** governance self-check harness (H5.1) · **BF-24** 10-check invariant acceptance suite.
- **M1** gate honors `Finding.blocking`; detector-critical floors the calibration gate (C3 correctness fix); plan-driven fail-closed coverage.
- **M2** deterministic secrets scanner + quarantine short-circuit; real LiteLLM cost + unknown-cost→manual_review.
- **M3** self-contained, replayable, **tamper-evident** run bundle (`validate-run` from disk).
- **M4** SQLite control-plane lifecycle (idempotent asset versioning, audit trail, outbox).
- **M5** MVP-vs-enterprise readiness split · unresolved Golden Controls record · import-boundary lint · HTTP-target-as-registered-asset (env-ref secrets).

---

## 10. Recommended unblock sequence (critical path)

1. **Ratify** decided contracts (DR-01/02, BF-01–09) + write/verify **SAFETY.md** (G14/BF-22).
2. **Commission the judge ground-truth set** (C1/G15) — the single highest-leverage data task; converts A9 from mechanism to real gating.
3. **Run the wk-1 AT&T spikes:** Model Router (DR-08), Janus role (DR-05), scanner front-door (DR-09) — these define the B2 + quarantine seams.
4. **Collect AT&T data:** Golden Controls catalogue (DR-07).
5. **Sign off provisional config** (BF-10–14).
6. **Grow persistence** to the full 20-table slice-1 (+ `tenant_id`) and add the waiver + provider-approval gate rules.
7. **Enterprise phases:** real scanner front-door → WORM evidence → SIEM/RBAC/event-bus → catalogue breadth (Cat 3/4 harnesses) → scale-out infra.

---

### Appendix — decision-register cross-reference
Invariant families: **R1–R9** platform · **A1–A10** agentic · **C1–C7** build conditions · **G1–G15** config/contract gaps. Decision records beyond DR-01–10: **ADR-1–6** (accepted), **Q1–Q4** (resolved), **D-1–9** reconciliation, **D1–D5** confirmed defaults, **V1-F1–F9** review findings. Backfill: **BF-01–24**. Source: design corpus at repo root.
