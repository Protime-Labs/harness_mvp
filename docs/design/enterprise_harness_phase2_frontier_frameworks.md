# Phase-2 Frontier Harness Frameworks — Evaluation, Dependencies, Alignment & Best-of-Each

**Owner:** Ivan Avelancio Jr. · **As of:** July 2026 · **Type:** evaluation for Phase-2 adoption (no changes to other docs).
**Question answered:** review the frontier harness frameworks from **Cisco, NVIDIA, Microsoft, Anthropic** as a Phase-2 approach — what dependencies must be in place, are they aligned by purpose/use-case, and how do we challenge them and use the best of each.
**Maps to:** `enterprise_harness_catalogue.md §10` (Phase 2 = H1.1, H1.4, H2.2, H2.4, H4.4, H5.2–H5.4) — but these frameworks also **upgrade the Phase-1 attack engines** from our MVP stubs to real red-team tooling.

> **One-line thesis:** the four vendors' frameworks split cleanly into **three purpose classes** — *offline attack/audit generators* (adopt as data-plane drivers behind our run contract), *runtime guardrails* (integrate as inline backends **and** as targets our resilience harnesses test), and *full commercial platforms* (Cisco/Azure — which **overlap our control plane**, so integrate-or-benchmark, don't blindly rebuild under). "Best of each" = **compose the open drivers behind one run contract and let our platform be the neutral referee + gate**, not pick a single winner.

---

## 1. The frameworks (what they are, purpose, intended use case)

### Anthropic — **Petri** (+ **Bloom**), Claude Agent SDK, MCP
- **What:** Petri is an open-source **automated alignment-auditing** toolbox (Oct 2025; now donated to open source). An **auditor model** simulates many alignment-relevant scenarios against a target, and a **judge model** scores the transcripts for misaligned behaviors — deception, sycophancy, harmful cooperation. **Bloom** (Dec 2025) generates *targeted* behavioral evals (Petri explores broadly; Bloom drills deep). Built on **Inspect AI**.
- **Purpose / use case:** safety/alignment **research auditing** at scale — surfacing *behavioral* tendencies, not just single-prompt jailbreaks. Adopted by UK AI Security Institute.
- **Access:** open source (MIT-class), provider-independent via Inspect. Needs capable auditor+judge models (cost).
- **Fit:** its **auditor → target → judge** shape is *exactly* our attacker → target → judge-quorum (W3/W7). Most novel contribution: **autonomous multi-scenario behavioral auditing**.

### NVIDIA — **Garak** (scanner) + **NeMo Guardrails** (runtime)
- **What:** **Garak** is the open-source **LLM vulnerability scanner** — 50+ probe modules (prompt injection, jailbreak, hallucination, data leakage, toxicity, misinformation), 23 generator backends (OpenAI/Anthropic/HF/local). v0.15.0 (May 2026) added a **multi-turn GOAT probe**, an **Agent-breaker probe** (tests tools available to LLM agents), system-prompt-extraction, and a refusal detector. **NeMo Guardrails** = programmable **runtime** rails (Colang) — input/output/jailbreak/topical rails.
- **Purpose / use case:** *"Garak finds the holes offline; guardrails enforce policy at request time."* Garak can also **measure a guardrail's protection rate**.
- **Access:** both open source (Apache-2.0), provider-independent; NeMo can use local safety models (GPU/NIM optional).
- **Fit:** Garak = fast **breadth** scanner (data plane); NeMo = **inline guardrail** (off the deep-harness path) **and** a test target for our resilience harness.

### Microsoft — **PyRIT** + **Azure AI Foundry AI Red Teaming Agent** + Content Safety + Presidio
- **What:** **PyRIT** (Python Risk Identification Tool, open source, Azure/PyRIT) — orchestrated red teaming with **20+ attack strategies** incl. **encoding** (Base64/ROT13/Leetspeak/Unicode) and **Crescendo** (multi-turn escalation), converters, scorers, memory. The **AI Red Teaming Agent** in Azure AI Foundry wraps PyRIT + Foundry Risk & Safety Evaluations, reports **Attack Success Rate (ASR)** and **agentic risk categories** (prohibited actions, sensitive-data leakage, task adherence); runs in cloud **or locally via the Azure AI Evaluation SDK**. **Presidio** = PII; **Content Safety / Prompt Shields** = injection/groundedness guardrails.
- **Purpose / use case:** systematic **adversarial probing / shift-left** red teaming for models *and agents*, with cloud governance if you're on Azure.
- **Access:** PyRIT/Presidio open source (MIT); the Foundry agent/Content Safety are **Azure-commercial** (subscription), though the eval SDK runs the agent locally.
- **Fit:** PyRIT = best **orchestration depth** (multi-turn, agentic ASR) as a data-plane driver; Foundry agent = a cloud option if AT&T is Azure-centric.

### Cisco — **AI Defense** (Robust Intelligence heritage)
- **What:** a **full-lifecycle commercial platform** — **Discover** (inventory models/datasets/agents across multicloud), **Detect** (**algorithmic red teaming** across **200+ risk subcategories**, single + adaptive multi-turn, multi-lingual, mapped to Cisco's AI Security & Safety Framework **plus OWASP, NIST, MITRE**), **Protect** (runtime guardrails/AI firewall). "Explorer Edition" brings **agentic red teaming** self-serve; ~20 min vs 7–15 weeks manual; expanding to AWS/Azure/GCP.
- **Purpose / use case:** turnkey **enterprise AI security across the lifecycle** — continuous validation + runtime protection.
- **Access:** **commercial** (Cisco Security Cloud subscription), closed, cloud/multicloud, possible inline network placement.
- **Fit:** **overlaps our control plane** (Discover/Detect/Protect ≈ our discovery→gate→remediate). Coopetition — integrate as a scanner/threat-feed/guardrail backend, or benchmark against.

---

## 2. Alignment by purpose & intended use case (direct verdict)

| Framework | Its purpose | Aligned with our purpose (governance-first, provider-independent assurance)? | Verdict / role |
|---|---|---|---|
| **PyRIT** (MS) | orchestrated red-team attack generation | ✅ yes — data-plane attacker | **Adopt as driver** (H2.1/H1.2/H2.2/agentic) |
| **Garak** (NV) | offline vuln scanning (breadth) | ✅ yes — data-plane scanner | **Adopt as driver** (H1.2/H2.1/H2.3/H2.2) |
| **Petri / Bloom** (Anthropic) | autonomous alignment/behavioral auditing | ✅ yes — extends judge/attacker with behavioral auditing | **Adopt as driver + new capability** (H1.3, agentic, H2.4) |
| **NeMo Guardrails** (NV) | runtime rails | 🟡 partial — it's a *guardrail*, not a harness | **Integrate as inline backend + test target** (H4.1, §6.17) |
| **Azure Content Safety / Prompt Shields** (MS) | runtime injection/groundedness guard | 🟡 partial — guardrail backend | **Integrate as backend + test target** |
| **Presidio** (MS) | PII detection | ✅ yes — deterministic detector (C3) | **Adopt as detector** (H2.3) |
| **Azure AI Foundry Red Teaming Agent** (MS) | cloud red-team + governance | 🟡 partial — Azure-coupled *platform* feature | **Integrate-as-backend if Azure-centric; else PyRIT direct** |
| **Cisco AI Defense** (Cisco) | full-lifecycle enterprise AI security platform | ⚠️ **overlaps our platform** (mission-aligned, scope-competing) | **Coopetition — integrate-as-backend or benchmark; strategic decision needed** |

**Answer to "are they aligned by purpose?":** the **open red-team/audit generators (PyRIT, Garak, Petri/Bloom) and Presidio are cleanly aligned** as data-plane components behind our run contract. **Runtime guardrails (NeMo, Content Safety) are complementary but a different purpose** (protect vs. assure) — we consume them as backends and *test* them. **Cisco AI Defense and (to a lesser degree) Azure AI Foundry are mission-aligned platforms that overlap our control plane** — the alignment question there is strategic (buy-vs-build / integrate-vs-benchmark), not technical.

---

## 3. Coverage → our harnesses (what each framework powers)

| Our harness (catalogue) | Best-fit frontier framework(s) | Phase |
|---|---|---|
| **H1.2** Adversarial Robustness | PyRIT (Crescendo/encoding) · Garak (jailbreak probes) · Glasswing QD | P1→upgrade |
| **H2.1** Prompt-Injection & Tool-Abuse | Garak (Agent-breaker/GOAT) · PyRIT (agentic ASR) | P1→upgrade |
| **H2.3** Data Privacy & Leakage | Garak (leakage) · **Presidio** (PII/CPNI floor) | P1→upgrade |
| **H1.3** Safety / Policy / Harm | **Petri/Bloom** (behavioral) · Garak (toxicity) · Llama Guard/NeMo | P1→upgrade |
| **H2.2** Cyber Misuse & Exploit Chain | PyRIT · Garak · (Meta CyberSecEval-class sets) | **P2** |
| **H1.1** Model Behavior & Capability Benchmark | Inspect evals · Azure Eval SDK · Cisco (200+ cat.) | **P2** |
| **H1.4** Hallucination & Grounding | Garak (hallucination) · Ragas · Petri (sycophancy) | **P2** |
| **H2.4** Context & Business-Impact | our rules + Petri (agentic misalignment context) | **P2** |
| **H4.1 / H4.4** Resilience / Cost | NeMo & Content Safety & Cisco Protect (as *targets*) · LiteLLM budgets | P2/P3 |
| **H5.2 / H5.3 / H5.4** Governance | Cisco/Azure control-mapping (OWASP/NIST/MITRE) · our gate | **P2** |
| Coverage/diversity metric | **Glasswing MAP-Elites** (repo) | P2 |
| Agentic tool/heartbeat (H4.3) | Garak Agent-breaker · Cisco agentic RT | P3 |

---

## 4. Dependencies that must be in place before adoption

| Framework | Infra / creds needed | Models needed | Skills | Effort | License / lock-in |
|---|---|---|---|---|---|
| **Garak** | Python; generator backend pointed at our adapter | any (target) | red-team | **Low** | Apache-2.0 · none |
| **PyRIT** | Python; a **memory store** (DuckDB local / Azure); endpoints via adapter | target + scorer | red-team + Python | **Low–Med** | MIT · none (Azure optional) |
| **Petri / Bloom** | Python; **Inspect AI**; MCP optional | **auditor + judge** models (capable, **≠ target family** — see §6) | eval engineering | **Med** (model cost) | MIT · none |
| **Presidio** | Python; spaCy models; CPNI custom recognizer | none | data/privacy | **Low** | MIT · none |
| **NeMo Guardrails** | Python; Colang configs; rails LLM; optional **GPU/NIM** for local safety models | rails/safety model | guardrail eng | **Med** | Apache-2.0 · low |
| **Azure AI Foundry RT Agent / Content Safety / Eval SDK** | **Azure subscription + Foundry project + region + creds** (Eval SDK can run locally) | any target | Azure | **Med–High** | Commercial · **Azure lock-in (partial)** |
| **Cisco AI Defense** | **Cisco Security Cloud contract**; multicloud connectors (AWS/Azure/GCP); possible inline placement for Protect | n/a (turnkey) | security ops + procurement | **High (procure) / Low (build)** | Commercial · **vendor lock-in** |

**Cross-cutting prerequisites (from our own architecture) that must exist first:** the **R3 run contract + LiteLLM adapter** (so every driver is swappable), the **C1 ground-truth + A5 judge quorum + C3 detectors** (so frameworks can be scored on equal footing), the **evidence store (A3)**, and **model-independence controls (A2/D1)** — attacker ≠ judge ≠ target model families.

---

## 5. Best-of-each (compose, don't choose)

Normalize all offline drivers behind our run contract and run them as an **ensemble**; our platform dedupes, judges, and gates:

| Capability | Winner | Why |
|---|---|---|
| Fast broad known-vuln coverage | **Garak** | 50+ probes, 23 backends, Agent-breaker/GOAT |
| Multi-turn orchestration depth (Crescendo, encoding, agentic ASR) | **PyRIT** | richest attacker strategies + agentic risk categories |
| Autonomous alignment/behavioral auditing (deception/sycophancy/misalignment) | **Petri + Bloom** | scenario-space auditing our stack lacks |
| Quality-diversity coverage metric | **Glasswing / MAP-Elites** (repo) | maps *variety* of failures, not just pass-rate |
| Runtime guardrail (inline + test target) | **NeMo Guardrails** / **Azure Prompt Shields** | programmable rails; measurable protection rate |
| PII / CPNI detection (detector floor) | **Presidio** | deterministic, extensible to CPNI |
| Turnkey enterprise breadth + continuous validation | **Cisco AI Defense** | 200+ categories, OWASP/NIST/MITRE, if buying > building |
| Eval substrate / scoring | **Inspect AI** (our base; Petri runs on it) | one scoring/log model across drivers |

**Composition rule:** the **union** of ensemble findings = coverage; the **intersection** = high-confidence; our **quorum + detectors** confirm; our **gate** decides. A framework earns its place only while it surfaces findings the others miss (loop-until-dry completeness critic).

---

## 6. Options to challenge & evaluate the harnesses (the bake-off)

Four complementary options — recommended combination is **A + C with B's controls, plus D for the commercial call**:

**Option A — Meta-evaluation with our platform as neutral referee (recommended core).**
Run each framework as a driver behind the **R3 run contract** against the **same synthetic targets + same C1 labeled ground-truth**, judged by the **same quorum (A5) + detectors (C3)** — the Glasswing *"identical prompt set + identical judge"* principle generalized to frameworks. Score each on a weighted rubric:

| Criterion | Metric |
|---|---|
| Recall | % of known ground-truth vulns found |
| Precision | 1 − false-positive rate (quorum-confirmed) |
| Coverage / Diversity | QD-score — unique failure niches found (MAP-Elites grid) |
| Novelty | findings no other framework surfaced |
| Cost / latency | tokens, $, wall-clock per run (A8 budget) |
| Reproducibility | finding-set variance across seeds (A7/C5) |
| Provider-independence | works behind our adapter without native SDK (A2) |
| Integration effort / license / maintenance cadence | qualitative |

**Option B — Cross-framework adversarial challenge (independence controls).**
- **Attacks-vs-guardrails matrix:** PyRIT/Garak/Petri attacks × NeMo/Content-Safety/Cisco guardrails → measures attack strength *and* guardrail efficacy at once.
- **Independence controls (mandatory, from the Glasswing/Anthropic caveat):** attacker ≠ judge ≠ target **model families**; **neutral re-judge** with a different model; **multi-seed + mutator ablation** — avoids the *mutator–target co-adaptation* confound that Anthropic/Glasswing documented.
- **Transfer test:** re-run one framework's confirmed findings under our judge — do they reproduce?

**Option C — Ensemble / redundancy ("use the best of each" literally).**
Run Garak (breadth) + PyRIT (depth) + Petri (alignment) + Glasswing (diversity) **in parallel** as drivers; dedupe to our canonical Finding schema; quorum verifies. Keep each framework while it adds unique findings; drop it after K dry rounds. This *composes* strengths instead of picking one.

**Option D — Buy-vs-build benchmark for the commercial platforms.**
Run **Cisco AI Defense** and **Azure Foundry RT Agent** against the *same* targets/ground-truth as the OSS ensemble; compare coverage/precision/cost/time-to-value → decide **integrate-as-backend** vs **build-with-OSS** for each. Directly tests whether turnkey 200+ categories beat our composed OSS stack (and whether Cisco's Discover/Detect/Protect should sit *under* or *beside* our control plane).

---

## 7. Recommended Phase-2 adoption plan

1. **Wire the seam first:** put PyRIT + Garak behind the R3 run contract + LiteLLM adapter (upgrades the MVP stubs for H1.2/H2.1/H2.3). Low dependency, immediate.
2. **Add Presidio** as the C3 detector floor for H2.3 (PII/**CPNI**).
3. **Add Petri/Bloom** (on Inspect) as the alignment-auditing driver for H1.3 + agentic behaviors — the genuinely new capability. Enforce attacker/judge/target independence (A2/D1).
4. **Adopt Glasswing MAP-Elites** for coverage/diversity metrics.
5. **Run the Option-A bake-off** to produce a scored, evidence-backed best-of-each per harness category.
6. **Guardrails (NeMo / Content Safety)** integrate as inline backends *and* become the targets for the H4.1 resilience harness.
7. **Commercial call (Option D):** benchmark **Cisco AI Defense** / **Azure Foundry** — likely **integrate Cisco as a continuous-validation + threat-feed backend and OWASP/NIST/MITRE control-mapping source (H5.3)** rather than adopt it as the platform, preserving provider-independence and our deterministic gate.

**Risks / watch-items:** (a) **co-adaptation confound** — enforce model independence or results are biased; (b) **Azure/Cisco lock-in** — keep everything behind the adapter/run-contract so a backend is swappable; (c) **cost** — Petri/agentic multi-turn burns tokens (A8 budgets mandatory); (d) **guardrails ≠ assurance** — don't let a NeMo/Content-Safety pass substitute for a harness verdict; (e) **platform overlap** — Cisco Discover/Detect/Protect competes with our control plane; decide integrate-vs-compete explicitly before procurement.

---

## Sources
- Anthropic Petri: [petri-open-source-auditing](https://www.anthropic.com/research/petri-open-source-auditing), [donating-open-source-petri](https://www.anthropic.com/research/donating-open-source-petri); Petri 2.0/3.0: [therift.ai](https://www.therift.ai/news-feed/anthropic-releases-petri-2-0-open-source-tool-for-automated-ai-alignment-audits), [meridianlabs.ai](https://meridianlabs.ai/blog/posts/introducing-petri-3/)
- Cisco AI Defense: [Cisco solution overview](https://www.cisco.com/c/en/us/products/collateral/security/ai-defense/ai-defense-so.html), [Explorer Edition (agentic red teaming)](https://blogs.cisco.com/ai/introducing-cisco-ai-defense-explorer), [data sheet](https://www.cisco.com/c/en/us/products/collateral/security/ai-defense/ai-defense-ds.html)
- Microsoft PyRIT / Foundry: [AI Red Teaming Agent (Learn)](https://learn.microsoft.com/en-us/azure/foundry/concepts/ai-red-teaming-agent), [run locally via Eval SDK](https://learn.microsoft.com/en-us/azure/foundry/how-to/develop/run-scans-ai-red-teaming-agent), [Azure/PyRIT](https://github.com/Azure/PyRIT), [preview announcement](https://devblogs.microsoft.com/foundry/ai-red-teaming-agent-preview/)
- NVIDIA garak / NeMo Guardrails: [NVIDIA/garak](https://github.com/NVIDIA/garak), [NeMo Guardrails](https://github.com/NVIDIA-NeMo/Guardrails), [LLM vulnerability scanning docs](https://docs.nvidia.com/nemo/guardrails/latest/evaluation/llm-vulnerability-scanning)

*Evaluation only — no catalogue/architecture/workflow/notebook files were modified.*
