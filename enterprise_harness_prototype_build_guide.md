# Prototype Build Guide — Colab (APIs · Services · Operations)

**Purpose:** a followable build for the prototype in Google Colab, with clear definitions of the **APIs**, the **services to enable**, and the **operations** to run it in your prototype environment.
**Principle (from the dependency-gated MVP):** you do **not** need the on-prem infrastructure finished. Start at **Iteration 0** (zero dependencies), and add one *verified* dependency per iteration. Each iteration has a **"verify before you proceed"** gate.
**Artifact:** `enterprise_harness_mvp_colab.ipynb` (the notebook you'll run).

---

## 0. What you're building

The §2-shape loop from the conceptual design: **test cases → run (driver → target → judge) → evaluate → gate → iterate**, wrapped by the Run Contract so real pieces swap in later. At the end of this guide you can: run an evaluation, read results, add test cases, enable a real model, and export an evidence bundle.

**Iteration ladder (build order):**
| Iter | You enable | Dependency to verify first | Outcome |
|---|---|---|---|
| **0** | nothing (offline) | — | the full loop runs; scored findings + gate + replay |
| **1** | one real model | LiteLLM + provider key working | real behavior, `bounded` determinism |
| **2** | one real framework | Garak *or* PyRIT installs + reaches the adapter | real attack coverage vs mock baseline |
| **3** | persistence | Drive/DB reachable | durable evidence bundles |
| **4+** | 2nd framework · router · controls | those systems verified | *only now*: bake-off, more categories |

Do **not** skip ahead — if an iteration's dependency isn't verified, stay on the previous rung; it keeps delivering.

---

## 1. Iteration 0 — run offline (no APIs, no keys)

**Services required:** none. **APIs required:** none.

1. Open Colab → `File ▸ Upload notebook` → `enterprise_harness_mvp_colab.ipynb` (or open from GitHub via `colab.research.google.com/github`).
2. `Runtime ▸ Run all`.
3. Confirm you see: per-harness finding counts, `GATE: BLOCK`, `OVERALL: ALL PASS`, `Mode-A replay PASSED`.

**Verify-to-proceed gate (Iter 0 done):** the notebook runs end-to-end with zero installs and the invariant suite passes. If yes, the *loop* is proven and you can iterate on test cases immediately (Section 5).

---

## 2. The APIs & interfaces (clear definitions)

These are the contracts your prototype is built on. Everything else plugs into them.

### 2.1 Run Contract API (the seam)
**Input — `run_config.json`** (control plane → harness):
```
run_id, harness{id,version}, asset_versions[], target{mode,adapter,endpoint},
normalized{model,tools,agent}, scenario_set, policy{fail_on_severity}, constraints{network,timeout,synthetic_only}
```
**Output — `result.json`** (harness → control plane):
```
harness, status(completed|budget_exceeded|failed), score, decision(approve|warn|block|manual_review),
metrics{}, findings[Finding], evidence[{type,uri,sha256}], determinism{seed,quorum,budget,class}
```
**Finding** (canonical): `id, source, severity(critical|high|medium|low|info), category, title, description, blocking, policy_rule, evidence_uri, recommendation, standards{owasp_llm, golden_control_domains}`.

### 2.2 Adapter API (the single model I/O path — R2/A2)
```python
class ProviderAdapter:
    def invoke(self, role, prompt, system="") -> {
        "text": str,
        "tokens": {"in": int, "out": int},
        "cost_usd": float,
        "model": {"provider","model","version","temperature","seed"}
    }
```
Every attacker, target, and judge calls **only** this. In Iter 0 it's `MockAdapter`; in Iter 1 it's `LiteLLMAdapter`. Harness/judge/gate code never changes.

### 2.3 Internal component APIs (function contracts)
| Component | Signature | Returns |
|---|---|---|
| Harness runner | `run_harness(hid, adapter, store, cfg)` | `result, turns, verdicts, manifest, findings` |
| Judge | `judge(lens, response, seed)` | `{attack_succeeded, confidence, severity, rationale}` |
| Quorum aggregate | `aggregate(verdicts, detector_hits)` | `succeeded, severity, confidence, detector_positive` |
| Gate | `gate_decision(quarantine, results, findings, required_ran, cfg)` | `{decision, matched_rule, rationale, policy_version}` |
| Replay | `replay_mode_a(manifest, verdicts, store, cfg)` | `findings, gate` (from evidence only) |

### 2.4 Provider APIs (reached *through* the adapter, never directly)
- **Anthropic** — Messages API (`ANTHROPIC_API_KEY`).
- **OpenAI-compatible** — Chat Completions (`OPENAI_API_KEY` + optional `base_url`).
- **AWS Bedrock** — via AWS credentials + region; model access enabled in the Bedrock console.

---

## 3. Iteration 1 — enable one real model

**Goal:** swap the mock target for a real, isolated model. Nothing else changes (the seam does its job).

### 3.1 Services to enable
| Provider | Enable | Credential |
|---|---|---|
| Anthropic | create an API key at the Anthropic Console | `ANTHROPIC_API_KEY` |
| OpenAI-compatible | key from the provider | `OPENAI_API_KEY` (+ `base_url` if self-hosted) |
| AWS Bedrock | enable model access in Bedrock; IAM creds | `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_REGION` |

### 3.2 Steps (in a new Colab cell)
```python
!pip -q install litellm
import os
os.environ["ANTHROPIC_API_KEY"] = "..."      # or the provider you enabled
CONFIG["PROVIDER_MODE"] = "litellm"
CONFIG["LITELLM_MODEL"] = "anthropic/claude-sonnet-5"   # use your provider's current model id
#   OpenAI-compatible: "openai/<model>"  ·  Bedrock: "bedrock/us.anthropic.claude-..."
```
Then re-run the evaluation cells. The `LiteLLMAdapter` (already in the notebook) is picked up automatically.

### 3.3 Safety & operations for real-model runs
- Keep `synthetic_data_only = True`; the *inputs* stay synthetic even against a real model.
- Set `temperature=0` and record the model id/version (the notebook does).
- Mark the run **`bounded`** (not "reproducible"): re-run 3× and check finding-set stability (Jaccard ≥ 0.90). Unstable runs route to `manual_review`, never a silent pass.
- **Budget:** set `CONFIG["BUDGET"]` (tokens/cost/turns). Budget-exceeded fails **closed** (blocks) — by design.

**Verify-to-proceed gate (Iter 1 done):** a real model runs behind the adapter, produces findings, the run is stability-checked, and cost stayed within budget.

---

## 4. Iteration 2 — enable one real framework (driver)

**Goal:** replace the built-in attacker with a real red-team tool, still behind the Run Contract.

### 4.1 Services to enable
```python
!pip -q install garak        # NVIDIA scanner (breadth) — OR:
!pip -q install pyrit        # Microsoft orchestration (multi-turn depth)
```
Both call models through an OpenAI-compatible endpoint — point them at your adapter/provider (same key as Iter 1). Start with a **small probe set** to bound cost.

### 4.2 Integration rule
The framework is a **driver**: it generates attacks and calls the target via the adapter; the platform's **judge + gate stay ours**. You are *adding a driver*, not replacing the loop. Compare its findings to the Iter-0 mock baseline to see what it adds.

**Verify-to-proceed gate (Iter 2 done):** one real framework runs behind the contract, its findings normalize into our `Finding` schema, and it surfaces at least one issue the mock didn't.

*(Iter 3 persistence and Iter 4+ multi-framework/router/controls/bake-off are deferred until their dependencies are independently verified — see the conceptual design §8c.)*

---

## 5. Operations in your prototype environment

### 5.1 Run an evaluation
`Runtime ▸ Run all`, or run the sections in order. Section 13 drives the full Phase-1 core; the gate + reports print inline.

### 5.2 Add or edit test cases (the primary iteration action)
Edit the `HARNESSES` dict (Section 5 of the notebook): add a scenario `{id, title, category, attack, label}` under the relevant harness; add its expected behavior to the mock target (Section 3) if running offline. Re-run. **This is how you iterate** — more/better cases → better coverage.

### 5.3 Change behavior (the control panel)
Edit `CONFIG` (Section 1): `SEED`, `PROVIDER_MODE`, `QUORUM_N`, `FAIL_ON_SEVERITY`, `BUDGET`, `JUDGE_THRESHOLDS`, `PHASE1_ATTACK`. Re-run to see the effect (Section 19 is a matrix that sweeps these).

### 5.4 Read & export results
- Per-harness findings + calibration + gate print inline (Sections 14–18).
- Export the bundle (Section 21) — `att_foundational_bundle.json` (findings, gate, calibration, evidence root). In Colab, `files.download(path)` to save.

### 5.5 Troubleshooting
| Symptom | Cause | Fix |
|---|---|---|
| `NameError` mid-notebook | ran a cell out of order | `Runtime ▸ Run all` from the top |
| `AuthenticationError` (Iter 1+) | key not set / wrong provider | set the env var; match `LITELLM_MODEL` to the provider |
| `status: budget_exceeded` | ceiling hit (working as intended) | raise `BUDGET` or reduce scenarios |
| findings differ across runs (real model) | `bounded` nondeterminism | expected; rely on the stability check, not identity |
| calibration `gate_eligible: false` | judge unreliable | fix the rubric or change judge model before trusting verdicts |
| rate-limit errors | provider throttling | lower concurrency / add retries (LiteLLM handles most) |

### 5.6 Cost & safety controls (always on)
- **Cost:** `BUDGET.max_cost_usd` per harness; mock runs are $0. Start every real-model change with `--quick`-style small runs.
- **Safety:** synthetic inputs only; no production credentials in Colab; network stays effectively deny except the provider endpoint you enabled; redact incidental sensitive data before export.

---

## 6. Definition of Done (prototype)

- [ ] Iter 0 runs offline; invariant suite passes; gate reaches `BLOCK` on a critical finding.
- [ ] You can **add a test case** and see it change the results.
- [ ] Iter 1: a real model runs behind the adapter, stability-checked, within budget.
- [ ] Evidence bundle exports; a run **replays from evidence** (Mode A).
- [ ] Judges are **calibrated** (precision/recall thresholds met) before their verdicts are trusted.

---

## 7. From prototype → hardened (later, not now)

When you move off Colab (only after the on-prem dependencies are verified): swap local files for a real evidence store (Iter 3); put the adapter behind the **LiteLLM proxy** for keys/budgets; add a second framework and — *then* — the W-C bake-off; integrate the AT&T **Model Router** and **Golden Controls**; wire the CI/CD gate. Each is a separate, dependency-verified step. The prototype's job is only to prove the loop and let you iterate on test cases — which it does today with zero infrastructure.
