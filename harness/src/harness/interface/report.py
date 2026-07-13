"""Human-readable report rendering (§6.18). Pure formatting over an assurance bundle."""
from __future__ import annotations

from typing import Any, Dict


def render_report(bundle: Dict[str, Any], specs: Dict[str, Any]) -> str:
    ctx = bundle["context"]
    gate = bundle["gate"]
    gov = bundle["governance"]
    first = next(iter(bundle["harness_results"].values()), {})
    L = [
        f"# Enterprise AI Assurance Report — {bundle['asset'].get('name', 'asset')}",
        f"**Gate:** `{gate['decision'].upper()}` · rule `{gate['matched_rule']}` · {gate['rationale']}",
        f"**Risk tier:** {ctx['tier']} ({ctx['score']}) · **Pack:** {ctx['pack_tier']}",
        f"**Evidence basis:** {first.get('evidence_basis', 'n/a')}",
        f"**Replay (Mode-A):** {'PASS' if bundle['replay']['ok'] else 'FAIL'}",
        "",
        "## Harnesses",
    ]
    for hid, r in bundle["harness_results"].items():
        name = specs[hid].name if hid in specs else hid
        L.append(f"- **{hid}** {name}: {r['status']}, {r['metrics']['findings']} finding(s), decision `{r['decision']}`")
    L.append(f"- **H5.1** governance: {gov['metrics']['complete']}/{gov['metrics']['checked']} findings lifecycle-complete")

    sc = bundle.get("scorecard")
    if sc:
        s = sc["summary"]
        L += ["", f"## Scorecard — vulnerability × criteria (profile: {sc['profile']})",
              f"**{s['pass']} pass · {s['warn']} warn · {s['fail']} fail · {s['not_tested']} not-tested** · "
              f"declared trust **{sc.get('declared_trust') or 'n/a'}**"
              + ("  ·  (!) declared-high yet a blocking finding" if sc.get("trusted_but_failing") else "")]
        _tag = {"pass": "PASS", "warn": "WARN", "fail": "FAIL", "not_tested": "n/a"}
        for r in sc["rows"]:
            _std = f" [{r['std']}]" if r.get("std") else ""
            L.append(f"- `{r['criterion']}` {r['title']}{_std}: **{_tag[r['status']]}** "
                     f"({', '.join(r['harnesses'])})")

    L += ["", "## Findings (aggregate)"]
    if not bundle["findings"]:
        L.append("- (none)")
    for f in bundle["findings"]:
        L.append(f"- **[{f['severity']}]** `{f['category']}` ({f['harness']}) · basis: {f['basis']} "
                 f"· owasp {f['standards'].get('owasp_llm')}")

    L += ["", "## Calibration (scenario · vs the live target)", *[
        f"- {h}: P={c['precision']} R={c['recall']} A={c['accuracy']} eligible={c['gate_eligible']}"
        for h, c in bundle["calibration"].items()]]
    jc = bundle.get("judge_calibration")
    if jc:
        L += ["", "## Judge calibration (verdict-level · target-independent, DR-11)",
              f"- P={jc['precision']} R={jc['recall']} A={jc['accuracy']} "
              f"eligible={jc['gate_eligible']} · n={jc['n']} · basis: {jc['basis']}"]

    if bundle.get("plan"):
        L += ["", "## Selection plan (why each harness is required)",
              *[f"- {p['harness']} -> {p.get('reason') or 'selected'}" for p in bundle["plan"]]]
    if bundle["skipped"]:
        L += ["", "## Skipped (coverage honesty)",
              *[f"- {s['harness']} -> {s['reason']}" for s in bundle["skipped"]]]
    return "\n".join(L)
