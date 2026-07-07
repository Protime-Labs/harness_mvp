# V1 Reference Architecture — Forward-Deployed (companion to the .drawio)

**Owner:** Ivan Avelancio Jr. · **Diagram:** `Enterprise_harness_v1_reference_architecture.drawio` (3 pages).
**Open with:** draw.io / diagrams.net · the VS Code *Draw.io Integration* extension · or feed the XML to the **drawio-mcp** `create_diagram` tool (it consumes native mxGraphModel XML — [server README](https://github.com/jgraph/drawio-mcp/blob/main/mcp-app-server/README.md)).
**Scope:** V1 = base-functionality testing + meeting specification + the challenge (bake-off) to integrate harnesses into the **correct lane / layer**, with frontier-vendor integration where applicable. Lean, aligned to R1–R9 / A1–A10 — not over-engineered.
**Decisions locked:** (1) **orchestrate-above Cisco** — consumed behind the Run Contract; our gate authoritative. (2) **AT&T-owned Model Router**; our adapter is a separate harness-I/O path. (3) **V1a synthetic → V1b bounded-real** (isolated · read-only · no-egress · C5 stability). (4) **H1.5 Bias & Fairness** in Phase-1. The bake-off pipeline is workflow **W-C**.

## The three pages
1. **V1 Reference Architecture (Forward-Deployed)** — the forward-deployed boundary (runs inside AT&T, provider-independent, **V1a synthetic → V1b bounded-real**, default-deny egress); the **AT&T-owned Model Router** feeding our separate **Adapter / LiteLLM** harness-I/O seam; the **Control Plane** (deterministic: discovery→quarantine→contextualization→selection→**gate**→evidence→remediation) beside the **Data Plane** (agentic, swappable drivers behind the **Run Contract R3**); frontier drivers/guardrails; and the **Frontier Platform Integration** band (Cisco / Azure / Anthropic).
2. **Harness Integration — Challenge Pipeline** — how any harness earns its place: **Base Functionality Test → Meets Specification → Challenge (bake-off) → Registry → Selection → Deterministic Gate**, with an EVOLVE/re-challenge loop. Every gate is deterministic.
3. **Frontier Vendor Integration Map** — where each vendor plugs in (mode · lane · harnesses).

## The V1 story (what the diagram encodes)
- **Base functionality testing** — a candidate harness must *run* and honor the **Run Contract (R3)**: read `run_config.json`, emit `result.json` + evidence. Proven offline first (dry-run / `--quick`, no API — A6/A8).
- **Meeting specification** — schema-valid `run_config` / `result` / `finding`; canonical Findings (G2); standards + Golden-Control tags. Gate: *Spec Pass*.
- **Challenging to integrate** — the **bake-off** (Option A meta-eval + Option C ensemble): run every candidate behind the *same* Run Contract against the *same* C1 ground-truth + judge quorum, scored on recall · precision · coverage · cost · reproducibility · independence. Best-of-each wins its lane. Independence controls (A2/D1) prevent the co-adaptation confound.
- **Correct lane / layer** — decisions live in the **Control Plane** (deterministic gate, R9/A1); execution and vendor drivers live in the **Data Plane** behind the seam; guardrails are **inline + test target**, never a harness verdict; commercial platforms are **integrate-or-benchmark**, never allowed to bypass the gate.
- **Forward-deployed** — the whole control+data plane is designed to run *inside the AT&T environment*: provider-independent (nothing bypasses the adapter), **V1a synthetic → V1b bounded-real** (isolated · read-only · no-egress · C5 stability-checked), default-deny egress with signed one-way pack ingress + evidence export.

## Frontier-vendor integration (where applicable)
| Vendor | Framework(s) | Mode | Lane | Harnesses |
|---|---|---|---|---|
| **Anthropic** | Petri / Bloom · Claude Agent SDK + MCP | driver · substrate | Data | H1.3, agentic, H2.4 |
| **NVIDIA** | Garak · NeMo Guardrails · Aegis | driver · guardrail | Data / inline | H1.2, H2.1, H2.3, H4.1 |
| **Microsoft** | PyRIT · Azure Foundry RT Agent · Content Safety · Presidio | driver · backend · guardrail · detector | Data / inline | H2.1, H1.2, H2.2, H2.3 |
| **Cisco** | AI Defense (Discover/Detect/Protect) | platform (**orchestrate-above** — behind Run Contract) | driver + control-map backend | H5.3 + continuous |
| **Ours (glue)** | LiteLLM · Inspect AI · Glasswing MAP-Elites | adapter · substrate · driver | both | — |

**Integration rules:** drivers plug behind the Run Contract and are compared by the **W-C bake-off**; guardrails are inline *and* tested; **platforms orchestrate-above** (Cisco consumed behind the Run Contract; our gate authoritative); provider- and model-independence (R2/A2, D1) are preserved throughout.

*Detail: `enterprise_harness_phase2_frontier_frameworks.md` (vendor evaluation) · `enterprise_harness_catalogue.md` (20 harnesses) · `enterprise_harness_architecture_v3.md` (planes/invariants).*
