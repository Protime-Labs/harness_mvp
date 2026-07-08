"""C1 / A9 — judge calibration. Quorum vs clear-cut ground truth per harness -> P/R/A ->
gate-eligibility. Borderline scenarios (label None) are excluded from the ground-truth set.

OFFLINE CAVEAT (honest): for content harnesses (H2.1/H2.3) calibration is meaningful (detectors
analyse real content). For semantic harnesses (H1.2/H1.3) the offline verdict is SIMULATED from
the label, so calibration is trivially perfect and NOT meaningful until a real judge is used.

Faithful to notebook §15.
"""
from __future__ import annotations

from typing import Callable, Dict, List

from ..domain.aggregate import aggregate
from ..domain.contracts import HarnessSpec
from .judge import run_judge


def _quorum(spec: HarnessSpec, sc, text: str, cfg: dict, adapter, detectors: Dict[str, Callable]):
    lenses = spec.lenses
    dets = [detectors[d] for d in spec.detectors]
    sc_dict = {"attack": sc.attack, "label": sc.label, "category": sc.category}
    vs = [run_judge(lenses[j % len(lenses)] if lenses else "policy_compliance", sc_dict, text, adapter, cfg["SEED"] + j)
          for j in range(cfg["QUORUM_N"])]
    return aggregate(vs, [d(text) for d in dets])


def calibrate(spec: HarnessSpec, adapter, store_system_prompt: str, cfg: dict,
              detectors: Dict[str, Callable]) -> dict:
    tp = fp = tn = fn = 0
    for sc in spec.scenarios:
        if sc.label is None:  # skip borderline (no GT label)
            continue
        text = adapter.invoke("target", sc.attack, system=store_system_prompt)["text"]
        succ, *_ = _quorum(spec, sc, text, cfg, adapter, detectors)
        if succ and sc.label:
            tp += 1
        elif succ and not sc.label:
            fp += 1
        elif not succ and not sc.label:
            tn += 1
        else:
            fn += 1
    n = tp + fp + tn + fn
    prec = tp / (tp + fp) if tp + fp else 1.0
    rec = tp / (tp + fn) if tp + fn else 1.0
    acc = (tp + tn) / n if n else 1.0
    th = cfg["JUDGE_THRESHOLDS"]
    return {
        "precision": round(prec, 2), "recall": round(rec, 2), "accuracy": round(acc, 2),
        "gate_eligible": prec >= th["precision"] and rec >= th["recall"] and acc >= th["accuracy"],
    }
