"""The invariant acceptance suite (external checks). Proves the load-bearing invariants against
a live run — this is the CI gate for the platform itself (BF-24).

Factories (`make_store`, `make_adapter`, `make_driver`) are injected so this application module
never imports a concrete adapter; the composition root supplies them. Each check maps to an
invariant in `domain.invariants`.

Faithful to notebook §18 `test_suite`.
"""
from __future__ import annotations

from collections import Counter
from typing import Any, Callable, Dict, List, Tuple

from ..domain.contracts import GATE_VOCAB, Finding
from ..domain.gate import gate_decision


def run_invariant_suite(
    bundle: dict,
    *,
    cfg: dict,
    specs: Dict[str, Any],
    make_store: Callable[[], Any],
    make_adapter: Callable[..., Any],
    make_driver: Callable[..., Any],
) -> List[Tuple[str, bool]]:
    findings: List[Finding] = bundle["_findings"]
    verdicts: List[dict] = bundle["_verdicts"]
    gate = bundle["gate"]
    plan = bundle["plan"]
    gov = bundle["governance"]

    T: List[Tuple[str, bool]] = []

    # R9 — gate emits a valid decision
    T.append(("R9 gate vocabulary", gate["decision"] in GATE_VOCAB))

    # A1 — no LLM tokens reachable in the gate function's code
    banned = {"invoke", "completion", "judge", "aggregate"}
    T.append(("A1 no-LLM in gate", banned.isdisjoint(set(gate_decision.__code__.co_names))))

    # A5 — every candidate judged by exactly QUORUM_N judges
    vc = Counter(v["finding_candidate_id"] for v in verdicts)
    T.append(("A5 quorum size (all harnesses)", len(vc) > 0 and all(c == cfg["QUORUM_N"] for c in vc.values())))

    # C3 — deterministic detectors floor the judge (H2.3 SSN + CPNI criticals exist)
    T.append(("C3 detector-floors-judge",
              any(f.category == "data_leakage.pii" for f in findings)
              and any(f.category == "data_leakage.cpni" for f in findings)))

    # A8 — fail closed on a budget breach (re-run one harness with max_turns=1)
    tight = dict(cfg); tight["BUDGET"] = {**cfg["BUDGET"], "max_turns": 1}
    s2, a2, d2 = make_store(), make_adapter(), make_driver()
    r2, *_ = d2.run(specs["H2.1"], a2, s2, tight)
    g2 = gate_decision("allow", [r2], [], r2["status"] == "completed")
    T.append(("A8 fail-closed on budget", r2["status"] == "budget_exceeded" and g2.decision == "block"))

    # C4 — Mode-A replay reproduced findings + gate
    T.append(("C4 evidence replay", bool(bundle["replay"]["ok"])))

    # A7 — deterministic re-run of the whole core
    s3, a3, d3 = make_store(), make_adapter(), make_driver()
    f3: List[Finding] = []
    for hid in cfg["PHASE1_ATTACK"]:
        _, _, _, _, ff = d3.run(specs[hid], a3, s3, cfg)
        f3 += ff
    T.append(("A7 deterministic re-run",
              sorted((f.id, f.severity) for f in f3) == sorted((f.id, f.severity) for f in findings)))

    # H5.1 — governance lifecycle completeness
    T.append(("H5.1 findings lifecycle-complete", gov["metrics"]["complete"] == gov["metrics"]["checked"]))

    # pack composition — every required (implemented) harness made it into the plan
    planned = set(p["harness"] for p in plan)
    T.append(("Foundational pack selected", planned == set(bundle["context"]["required_harnesses"])))

    # DoD — the vulnerable baseline blocks
    T.append(("DoD block-on-critical", gate["decision"] == "block"))
    return T
