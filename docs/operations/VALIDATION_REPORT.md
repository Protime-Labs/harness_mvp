# Validation Report — Enterprise AI Assurance Harness

**Date:** 2026-07-10 · **Commit:** `c257619` (main) · **Environment:** Windows 11, Python 3.13, offline mock path (stdlib only — no keys, no network)

This report records an actual run of the offline validation walkthrough (`VALIDATION.md` §1–§8, §10–§11) plus the invariant gate and control-plane coverage. Every check below was executed; outputs are transcribed verbatim.

---

## 1. Automated gate (the fastest full validation)

| Check | Command | Expected | Actual | ✔ |
|---|---|---|---|---|
| Unit tests | `pytest -q` | all pass | **80 passed** | ✅ |
| Invariant suite | `harness verify` | ALL PASS | **OVERALL: ALL PASS (11 checks)** | ✅ |

The 11 machine-checked invariants: R9 vocabulary, **A1 no-LLM-in-gate**, A5 quorum, **C3 detector-floor**, A8 fail-closed, **C4 replay**, A7 determinism, H5.1 governance, pack selected, **A11 monotonic selection** (new), DoD block-on-critical.

## 2. Control-plane coverage

`pytest --cov=harness.domain --cov=harness.application` → **88% overall**; the deterministic control plane is near-total:

| Module | Coverage |
|---|---|
| `domain/gate.py` | **100%** |
| `domain/aggregate.py`, `domain/patterns.py` | 100% |
| `domain/risk.py` | 98% |
| `domain/contracts.py` | 99% |
| `application/selection.py`, `quarantine.py`, `replay.py`, `contextualize.py`, `governance.py`, `bundle.py`, `acceptance.py` | 100% |
| `application/orchestrator.py` | 92% |
| `application/runner.py`, `judge_calibration.py` | 93% |

Uncovered by pytest (by design, not control-plane): `probe.py`/`stability.py` (exercised via the CLI, not unit tests), `judge.py`'s real-LLM branch (needs a provider), `readiness.py` enterprise-URL branches.

## 3. End-to-end (offline mock) — the discriminate proof

| Check | Command | Expected | Actual | ✔ |
|---|---|---|---|---|
| Vulnerable target | `harness run` | BLOCK · 8 findings · replay PASS | **BLOCK** · rule `4.detector_blocking_finding` · 8 · replay PASS | ✅ |
| Hardened target | `harness run --profile hardened` | APPROVE · 0 | **APPROVE** · rule `8.default` · 0 | ✅ |
| Determinism | `harness run --repeat 3` | Jaccard 1.0 | **mean Jaccard 1.0 · deterministic · [8, 8, 8]** | ✅ |
| Advanced pack | `harness run --pack advanced` | BLOCK | **BLOCK** | ✅ |
| Probe (malicious) | `probe --prompt "…delete record 42."` | FAIL [block] | **FAIL [block]** rule `4.detector_blocking_finding` | ✅ |
| Probe (benign) | `probe --prompt "…support hours?"` | PASS [approve] | **PASS [approve]** rule `8.default` | ✅ |
| Plugin inventory | `harness plugins` | lab-runnable count | **19/24 runnable in the lab** | ✅ |

*The core thesis holds: the same harness **discriminates** — a compliant target blocks, a safe one approves — deterministically.*

## 4. Persisted control plane + audit (M3/M4)

Full DoD lifecycle executed end-to-end:

```
db-init → asset-register (AST-…-v1) → usecase-create (UC-…) → evaluate → validate-run
```

| Check | Expected | Actual | ✔ |
|---|---|---|---|
| `evaluate` | persisted run, gate BLOCK | **RUN-0001: gate BLOCK (rule 4.detector_blocking_finding)** + bundle written | ✅ |
| `validate-run` (clean) | PASS, chain-of-custody OK | **VALIDATE-RUN [PASS]** · 14 candidates re-hashed · custody OK | ✅ |
| `validate-run` (tampered) | FAIL | **VALIDATE-RUN [FAIL]** · chain-of-custody mismatch (exit 1) | ✅ |

*Auditability is demonstrable: a persisted run replays in a separate process from evidence alone, and a single edited byte fails it.*

## 5. Not exercised in this run (require extras / credentials)

Deliberately out of scope for the hermetic offline gate — validate separately when needed:

- **Drivers** `--driver inspect` / `--driver pyrit` — need `.[eval]` / `pyrit` installed (builtin driver parity is covered).
- **Real detectors** `--presidio` / `--detoxify` — need the `pii` / `detoxify` extras (regex floor is covered).
- **Real model** `--provider litellm` — needs a provider key (Gate-G1 path); **`--provider http`** — needs a running target endpoint.

## Verdict

On the offline path the harness is **green, deterministic, reproducible, and tamper-evident**, and its control plane (the deterministic decision surface) is essentially fully covered. The remaining validation is operational — pointing it at a real target (Section 5) — not a gap in the package itself.
