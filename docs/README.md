# docs — documentation hive

All project documentation, organized by purpose. **New here? Start with
[operations/RUNBOOK.md](operations/RUNBOOK.md).**

## architecture/ — current architecture + diagrams
- [ENTERPRISE_HARNESS_REFERENCE_ARCHITECTURE.md](architecture/ENTERPRISE_HARNESS_REFERENCE_ARCHITECTURE.md) — the seam-interface build reference (base layers, invariants, growth ladder)
- [CONTROL_PLANE_EXTENDED_ARCHITECTURE.md](architecture/CONTROL_PLANE_EXTENDED_ARCHITECTURE.md) — the control plane as a **negotiator**: model switching, inherent trust, criteria profiles, two modes, vuln×trust scorecard
- [GAP_ANALYSIS_AND_REQUESTS.md](architecture/GAP_ANALYSIS_AND_REQUESTS.md) — original architecture → prototype gap analysis + request/decision register
- **Diagrams** (draw.io / pdf): `Enterprise_Harness_Architecture.drawio` (6-page system), `Control_Plane_Negotiation.drawio`, `Agentic_System_Framework_Governance.drawio` (+ `.pdf`), and the v1/annotated/platform-v2 references.

## operations/ — how to run + validate
- [RUNBOOK.md](operations/RUNBOOK.md) — **operate the harness**: launch the consoles, run assessments, switch models, choose a posture (mode/trust/criteria), read the scorecard, persist + replay, tune governance config
- [VALIDATION.md](operations/VALIDATION.md) — step-by-step acceptance walkthrough (with expected outputs + checklist)
- [VALIDATION_REPORT.md](operations/VALIDATION_REPORT.md) — dated record of an actual validation run

## design/ — the original design corpus
The source design / spec / review corpus the prototype was built from. Good entry points:
- `enterprise_harness_design.md` (platform invariants R1–R9) · `enterprise_harness_architecture_v3.md` (agentic invariants A1–A10) · `enterprise_harness_agentic_workflows.md` (workflows W0–W9)
- `enterprise_harness_catalogue.md` (the harness catalogue + packs) · `enterprise_harness_base_layers_and_accountability.md` (base layers B0–B6 + the DR decision register) · `enterprise_harness_v1_backfill_register.md` (BF-01..24) · `enterprise_harness_spec_addendum_C1-C6.md`
- `enterprise_harness_mvp_plan.md` (tracer/slice-1 + table set) · reviews, correlations, phase-2 plans, and two reference notebooks (`*_colab.ipynb`).

---
*Package quickstart lives with the code: [../harness/README.md](../harness/README.md). Repo landing page: [../README.md](../README.md).*
