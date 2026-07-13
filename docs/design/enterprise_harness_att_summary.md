# AT&T AI Harness Platform — One-Page Summary & Golden Controls Map

**Owner:** Ivan Avelancio Jr. · **Audience:** AT&T CSO / AI governance · **Status:** MVP Foundational core proven (offline, replayable).

## What it is
A **CSO-owned AI assurance fabric** for open-source and frontier models: **discover → secure → customize → deploy → evolve.** It discovers AI assets, secures them at an agentic front door, runs required **harness packs**, preserves hashed evidence, and **gates unsafe changes before production** — with every gate decision deterministic and auditable (no LLM decides the gate).

## The harness model — 5 categories × 4 = 20 harnesses, sold as tiered Packs
| Category | Verifies | Pack tiers |
|---|---|---|
| **Test** | model quality, adversarial robustness, safety, hallucination | Foundational |
| **Exposure** | prompt-injection/tool-abuse, cyber misuse, **PII/CPNI leakage**, business impact | Foundational + Advanced + AT&T Context |
| **Remediation** | safe fixes, IaC/playbook closure, rollback, blast-radius | AT&T Context |
| **Resilience** | control-failure/degraded-ops, failover/RTO-RPO, agent heartbeat, cost/SLO | Advanced |
| **Governance** | finding lifecycle/evidence, auditability, **Golden-Controls compliance**, HITL model-risk gate | AT&T Context |

**Packs** compose per model + use-case: **Foundational** (every model) ∪ **Advanced Capability** (cyber/agentic/availability) ∪ **AT&T Context** (Golden Controls, CPNI, business rules, approved playbooks).

## Golden Controls coverage (harness → control domain)
> AT&T supplies the Golden Controls catalogue (IDs + text). Below maps each control **domain** to the harness that produces its evidence; the **H5.3 Policy Compliance / Golden Controls** harness rolls all of it into a control-coverage + gap report.

| Golden Control domain | Harness(es) | What it proves | MVP |
|---|---|---|---|
| Identity & access, least privilege | Security Agent (front door), **H3.1** | only approved, privileged-checked actions | P3 |
| Logging & audit trail | **H5.2** | complete model/tool/agent trace + reviewer view | P2 |
| Data policy / **CPNI** handling | **H2.3** | no PII/CPNI/secret leakage (Presidio + CPNI recognizer) | **✅ MVP** |
| Network egress / fail-safe | **H4.1**, front door | fail-closed guardrails, evidence store, egress | P3 |
| Change management | **H3.2 / H3.3 / H3.4** | approved IaC, rollback, blast-radius before change | P3 |
| Availability / DR (RTO/RPO) | **H4.2** | failover + fallback model + recovery targets | P3 |
| Model risk & approval | **H5.4**, **H1.1** | HITL high-risk gate, model scorecard | P2 |
| Acceptable use / harm | **H1.3** | blocks harmful/unsafe output | **✅ MVP** |
| Tool & agent governance | **H2.1**, **H4.3** | no tool-abuse; agent auto-stop/heartbeat | **✅ MVP** (H2.1) |
| Evidence / finding lifecycle | **H5.1** | immutable finding record + verdict + evidence pack | **✅ MVP** |
| Cost / SLO guardrails | **H4.4** | budget caps, rate limits, cost-aware routing | P2 |
| **Policy compliance (roll-up)** | **H5.3** | maps ALL findings → Golden Controls + ISO 42001 gap report | P2 |

Cross-tagged to **OWASP LLM Top 10 · MITRE ATLAS · NIST AI RMF · ISO 42001** for auditors.

## What's proven today (pre-scaffolding)
An **operable Colab notebook** runs the **Foundational core** — H2.1 Prompt-Injection/Tool-Abuse, H1.2 Adversarial, H1.3 Safety, H2.3 Data/CPNI, H5.1 Finding-Lifecycle — fully **offline (mock target, no keys), deterministic, and replayable from evidence**. It produces 8 standards-tagged findings across 4 harnesses, a deterministic **`block`** gate, per-harness judge calibration, and a 10-check invariant acceptance suite (all pass). This is the assurance loop end-to-end before any production build.

## How it plugs into AT&T
Provider-independent (LiteLLM one-path); sources include **Hosted LLM, Databricks, Anthropic, Prisma AIRS, Open-Source, Internal AIRS, Janus**; authoring via **Harness Studio** (Python/TS/Java SDK); CI/CD gate + runtime telemetry feed the **Evolve** loop. No production coupling in MVP (synthetic data, isolated mock, deny-egress).

## Three asks from AT&T (unblock the AT&T Context packs)
1. **Golden Controls catalogue** — control IDs + text, so H5.3 maps to real IDs (today it maps to domains).
2. **Janus / Internal AIRS / Prisma AIRS** — confirm each as source vs. scanner vs. router (integration targets).
3. **Model Router** — does AT&T have one (Prisma AIRS / Databricks) to integrate, or do we build it (H4.2 depends on it)?

*Detail: `enterprise_harness_catalogue.md` (20 harnesses classified) · `enterprise_harness_architecture_v3.md` (platform) · `enterprise_harness_mvp_colab.ipynb` (operable proof).*
