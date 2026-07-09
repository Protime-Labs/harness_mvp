"""CLI — the entry point. Wires config + adapters into the application and prints results.

    harness run          run the full assurance chain, print the report (+ optional bundle/dashboard)
    harness verify       run + the invariant acceptance suite; exit non-zero on any failure
    harness validate-run replay a persisted run bundle from disk (chain-of-custody)
    harness dashboard    build a self-contained HTML dashboard (open/serve locally)
    harness info         show config sources, invariants, and the harness registry

Provider is offline mock by default (zero installs). `--provider litellm` swaps in a real model
(needs `pip install litellm` + a key); the harness code is unchanged.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Dict, Optional

from .. import __version__
from ..domain.invariants import INVARIANTS
from ..application.acceptance import run_invariant_suite
from ..application.orchestrator import run_assurance
from ..application.readiness import assess_enterprise_readiness
from ..registry import load_harnesses
from . import factory
from .report import render_report

# Default asset + use-case (the AT&T customer-support agent, notebook §13). Override via --usecase.
DEFAULT_ASSET = {"asset_id": "AGT-001", "type": "agent", "name": "att-customer-support-agent"}
DEFAULT_USE_CASE = {"name": "att-customer-support", "data_classes": ["CPNI", "PII"], "exposure": "public",
                    "write_tools": True, "users": ["external"], "criticality": "tier1"}


def _overrides(args) -> dict:
    ov: dict = {}
    if args.provider:
        ov["PROVIDER_MODE"] = args.provider
    if args.profile:
        ov["TARGET_PROFILE"] = args.profile
    if getattr(args, "presidio", False):
        ov["USE_PRESIDIO"] = True
    if getattr(args, "detoxify", False):
        ov["USE_DETOXIFY"] = True
    if getattr(args, "driver", None):
        ov["DRIVER"] = args.driver
    if getattr(args, "pack", None):
        ov["PACK"] = args.pack
    if getattr(args, "target_url", None):
        ov["HTTP_TARGET_URL"] = args.target_url
    if getattr(args, "response_path", None):
        ov["HTTP_RESPONSE_PATH"] = args.response_path
    if getattr(args, "target_header", None):
        ov["HTTP_HEADERS"] = args.target_header
    if getattr(args, "offline_judge", False):
        ov["OFFLINE_JUDGE"] = True
    return ov


def _load_json(path: Optional[str], default: dict) -> dict:
    if not path:
        return default
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _assemble(args):
    ctx = factory.build_context(
        config_dir=args.config,
        overrides=_overrides(args),
        scenario_path=getattr(args, "scenarios", None),
    )
    use_case = _load_json(getattr(args, "usecase", None), DEFAULT_USE_CASE)
    asset = _load_json(getattr(args, "asset", None), DEFAULT_ASSET)
    bundle = run_assurance(
        use_case=use_case, asset=asset, policy=ctx["policy"], driver=ctx["driver"],
        adapter=ctx["adapter"], store=ctx["store"], detectors=ctx["detectors"],
        specs=ctx["specs"], registry_map=ctx["registry_map"], system_prompt=ctx["system_prompt"],
        judge_adapter=ctx["judge_adapter"],
    )
    return ctx, bundle


def _serializable(bundle: dict) -> dict:
    return {k: v for k, v in bundle.items() if not k.startswith("_")}


def _names(config_dir: Optional[str]) -> Dict[str, str]:
    return {hid: s.name for hid, s in load_harnesses(config_dir).items()}


def _scenario_count(ctx: dict) -> int:
    return sum(len(s.scenarios) for hid, s in ctx["specs"].items() if hid in ctx["cfg"]["PHASE1_ATTACK"])


def _print_preflight(ctx: dict, bundle: dict) -> None:
    cfg = ctx["cfg"]
    rc = bundle.get("run_config", {})
    print("ENVIRONMENT READINESS")
    print(f"  target provider : {rc.get('provider_mode')} ({rc.get('target_model')})")
    print(f"  judge           : {rc.get('judge_model')}")
    print(f"  driver          : {cfg.get('DRIVER')}")
    print(f"  detectors       : {', '.join(sorted(ctx['detectors'].keys()))}")
    print(f"  scenarios       : {_scenario_count(ctx)}" +
          (f" from {ctx['scenario_path']}" if ctx.get("scenario_path") else " from built-in/config suite"))
    print(f"  evidence store  : {bundle.get('evidence_root')}")
    print(f"  enterprise deps : {', '.join(bundle.get('enterprise_readiness', {}).get('missing', [])) or 'none missing'}")
    print("\nRUN PLAN")
    print(f"  use case        : {bundle['use_case'].get('name')}")
    print(f"  risk tier       : {bundle['context'].get('tier')} ({bundle['context'].get('score')})")
    print(f"  pack            : {bundle['context'].get('pack_tier')}")
    print(f"  harnesses       : {', '.join(bundle['harness_results'].keys())}")
    b = cfg.get("BUDGET", {})
    print(f"  budget          : turns={b.get('max_turns')} tokens={b.get('max_tokens')} "
          f"cost=${b.get('max_cost_usd')} time={b.get('max_wall_clock_s')}s")
    print("")


def cmd_run(args) -> int:
    ctx, bundle = _assemble(args)
    if args.json:
        print(json.dumps(_serializable(bundle), indent=2, default=str))
    else:
        _print_preflight(ctx, bundle)
        print(render_report(bundle, ctx["specs"]))
        print(f"\nEVIDENCE: {bundle['evidence_root']}")
    if getattr(args, "repeat", None) and args.repeat > 1:
        from ..application.stability import finding_key_set, stability_from_sets
        sets = [finding_key_set(bundle)]
        for _ in range(args.repeat - 1):
            sets.append(finding_key_set(_assemble(args)[1]))
        st = stability_from_sets(sets)
        print(f"\nSTABILITY: {st['runs']} runs · mean Jaccard {st['mean_jaccard']} · "
              f"{st['class']} · finding counts {st['finding_counts']}")
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(_serializable(bundle), f, indent=2, default=str)
        print(f"WROTE:    {args.out}")
    if getattr(args, "bundle", None):
        from ..application.bundle import write_run_bundle
        path = write_run_bundle(bundle, ctx["store"], ctx["policy"], ctx["specs"], args.bundle)
        print(f"BUNDLE:   {path}   (validate: harness validate-run {path})")
    if getattr(args, "html", None):
        from .dashboard import write_dashboard, open_in_browser
        from .capabilities import probe
        path = write_dashboard([bundle], _names(args.config), args.html, capabilities=probe())
        print(f"DASHBOARD:{path}")
        if getattr(args, "open", False):
            open_in_browser(path)
    return 0


def cmd_dashboard(args) -> int:
    from .dashboard import write_dashboard, open_in_browser, serve
    from .capabilities import probe
    bundles, labels = [], []
    if args.in_:
        for p in args.in_:
            with open(p, "r", encoding="utf-8") as f:
                bundles.append(json.load(f))
            labels.append(os.path.splitext(os.path.basename(p))[0])
    else:
        _, bundle = _assemble(args)        # fresh run (respects --provider/--profile)
        bundles.append(bundle)
        labels.append((bundle.get("run_config", {}) or {}).get("provider_mode", "run"))
    out = args.out or "harness_dashboard.html"
    path = write_dashboard(bundles, _names(args.config), out, capabilities=probe(), labels=labels)
    print(f"WROTE: {path}")
    if args.serve is not None:
        serve(os.path.dirname(path) or ".", os.path.basename(path), port=args.serve or 8000)
    elif args.open:
        open_in_browser(path)
        print("opened in your browser")
    return 0


def cmd_plugins(args) -> int:
    from .capabilities import probe, summarize
    caps = probe()
    s = summarize(caps)
    print(f"enterprise-harness plugins & dependencies  "
          f"({s['lab_runnable']}/{s['total']} runnable in the lab)\n")
    group = None
    for c in caps:
        if c["group"] != group:
            group = c["group"]
            print(f"\n{group}")
        extra = f"  pip install -e '.[{c['extra']}]'" if c.get("extra") and c["status"] == "installable" else ""
        key = ""
        if c.get("env") is not None:
            key = "  [key in env]" if c.get("key_present") else "  [no key in this process env]"
        print(f"  {c['id']:16s} {c['status']:12s} {c['name']}{extra}{key}")
    print(f"\nlab-runnable = available | installable | stub   (enterprise deps are stubbed, not wired)")
    return 0


def cmd_verify(args) -> int:
    ctx, bundle = _assemble(args)
    if not getattr(args, "json", False):
        _print_preflight(ctx, bundle)
    print(render_report(bundle, ctx["specs"]))
    print("\n" + "=" * 52)
    print(f"{'INVARIANT CHECK':38s} RESULT")
    print("-" * 52)
    results = run_invariant_suite(
        bundle, cfg=ctx["cfg"], specs=ctx["specs"], make_store=ctx["make_store"],
        make_adapter=ctx["make_adapter"], make_driver=ctx["make_driver"],
    )
    ok_all = True
    for name, ok in results:
        ok_all = ok_all and ok
        print(f"{name:38s} {'PASS' if ok else 'FAIL'}")
    print("-" * 52)
    print("OVERALL:", "ALL PASS" if ok_all else "FAILURES PRESENT")
    return 0 if ok_all else 1


_VERDICT_TAG = {"approve": "PASS", "warn": "WARN", "block": "FAIL", "manual_review": "REVIEW"}


def _print_probe_event(stage: str, d: dict) -> None:
    if stage == "plan":
        ind = "independent" if d["judge_independent"] else "self (offline sim for semantic lenses)"
        print(f"\nCHAIN PLAN")
        print(f"  provider : {d['provider']}   judge: {d['judge']} ({ind})")
        print(f"  detectors: {', '.join(d['detectors'])}")
        print(f"  lenses   : {', '.join(d['lenses'])}   quorum: {d['quorum_n']}")
        print(f"\n  prompt   : {d['prompt']}")
        print("-" * 60)
    elif stage == "target_start":
        print(f"-> invoking target ({d['model']}) ...")
    elif stage == "target":
        txt = d["response"].replace("\n", " ")
        print(f"   target responded: {txt[:100]}{'...' if len(txt) > 100 else ''}")
    elif stage == "evidence":
        print(f"   evidence captured: {d['hash'][:23]}...")
    elif stage == "detector":
        tag = f"HIT  {d['severity']}: {d['span']!r}" if d["hit"] else "----  (no hit)"
        print(f"   [detector] {d['name']:9s} {tag}")
    elif stage == "judge":
        v = "FAIL" if d["attack_succeeded"] else "ok"
        print(f"   [judge {d['index']}] {d['lens']:18s} {v:4s} conf={d['confidence']}  {d['rationale'][:60]}")
    elif stage == "aggregate":
        floor = " (detector-floored)" if d["detector_positive"] else ""
        print("-" * 60)
        print(f"AGGREGATE: succeeded={d['succeeded']} severity={d['severity']}{floor}")
    elif stage == "gate":
        print(f"GATE     : {_VERDICT_TAG.get(d['decision'], d['decision'].upper())}  "
              f"[{d['decision']}]  rule {d['matched_rule']}  {d['rationale']}")


def cmd_probe(args) -> int:
    if args.serve is not None:
        from .probe_server import serve_probe
        serve_probe(port=args.serve or 8000, config_dir=args.config, overrides=_overrides(args))
        return 0
    if not args.prompt:
        print("Provide --prompt \"your text\"  (or --serve [PORT] for the interactive dashboard)")
        return 2
    from ..application.probe import run_probe
    ctx = factory.build_context(
        config_dir=args.config,
        overrides=_overrides(args),
        scenario_path=getattr(args, "scenarios", None),
    )
    lenses = detector_names = None
    if args.harness:
        spec = ctx["specs"][args.harness]
        lenses = spec.lenses or None
        detector_names = spec.detectors or None
    result = run_probe(
        args.prompt, adapter=ctx["adapter"], detectors=ctx["detectors"], cfg=ctx["cfg"],
        store=ctx["store"], system_prompt=ctx["system_prompt"], judge_adapter=ctx["judge_adapter"],
        lenses=lenses, detector_names=detector_names, on_event=_print_probe_event,
    )
    if args.json:
        print("\n" + json.dumps(result, indent=2, default=str))
    return 0


def cmd_validate_run(args) -> int:
    from ..application.bundle import validate_run_bundle
    rep = validate_run_bundle(args.path)
    tag = "PASS" if rep["ok"] else "FAIL"
    print(f"VALIDATE-RUN [{tag}]  run={rep['run_id']}  candidates={rep['candidates']}")
    print(f"  expected gate : {rep['expected_gate']}")
    print(f"  replayed gate : {rep['replayed_gate']}")
    if rep["tamper"]:
        print(f"  chain-of-custody: FAILED — {rep['tamper']}")
    else:
        print(f"  chain-of-custody: OK (every stored response re-hashed)")
    return 0 if rep["ok"] else 1


def cmd_info(args) -> int:
    policy = factory.load_policy(config_dir=args.config)
    print(f"enterprise-harness v{__version__}")
    print("\nConfig sources (last wins):", " -> ".join(policy["sources"]))
    print("PyYAML available:", policy["yaml_available"])
    print("Provider mode:   ", policy["config"]["PROVIDER_MODE"])
    print("Quorum N:        ", policy["config"]["QUORUM_N"])
    print("Fail-on severity:", policy["config"]["FAIL_ON_SEVERITY"])
    print("\nInvariants (constitution):")
    for inv in INVARIANTS.values():
        print(f"  {inv.id:4s} {inv.statement}")
    from ..adapters.config.defaults import REGISTRY
    print("\nRegistry (implemented in MVP core):")
    for hid, d in REGISTRY.items():
        flag = "impl" if d.get("implemented") else "phase2/3"
        print(f"  {hid:6s} {flag}")
    return 0


def cmd_doctor(args) -> int:
    from .capabilities import probe, summarize
    try:
        ctx = factory.build_context(
            config_dir=args.config,
            overrides=_overrides(args),
            scenario_path=getattr(args, "scenarios", None),
        )
        error = None
    except Exception as exc:
        ctx, error = None, exc
    caps = probe()
    s = summarize(caps)
    print(f"enterprise-harness doctor v{__version__}")
    print(f"capabilities     : {s['available']} available / {s['installable']} installable / "
          f"{s['stub']} stub / {s['enterprise']} enterprise")
    if error:
        print(f"composition      : FAIL - {error}")
        return 1
    cfg = ctx["cfg"]
    print("composition      : PASS")
    print(f"provider         : {cfg['PROVIDER_MODE']}")
    if cfg["PROVIDER_MODE"] == "http":
        print(f"http target      : {'configured' if cfg.get('HTTP_TARGET_URL') else 'missing'}")
    elif cfg["PROVIDER_MODE"] == "litellm":
        keys = ["ANTHROPIC_API_KEY", "OPENAI_API_KEY", "AZURE_API_KEY", "AWS_ACCESS_KEY_ID"]
        print(f"provider key     : {'present' if any(os.environ.get(k) for k in keys) else 'missing'}")
    print(f"judge panel      : {', '.join(getattr(j, 'model', 'offline-sim') if j else 'offline-sim' for j in ctx['judge_adapters'])}")
    print(f"detectors        : {', '.join(sorted(ctx['detectors']))}")
    print(f"scenario source  : {ctx.get('scenario_path') or 'built-in/config suite'}")
    print(f"scenario count   : {_scenario_count(ctx)}")
    print(f"evidence store   : {type(ctx['store']).__name__}")
    readiness = assess_enterprise_readiness(
        ctx["policy"],
        scenario_path=ctx.get("scenario_path"),
        store=ctx["store"],
        detectors=ctx["detectors"],
        driver_name=getattr(ctx["driver"], "name", None),
        specs=ctx["specs"],
    )
    print(f"enterprise ready : {'yes' if not readiness['missing'] else 'no'}")
    for item in readiness["missing"]:
        print(f"  missing        : {item}")
    return 0 if not readiness["hard_blockers"] else 1


def cmd_demo_target(args) -> int:
    from .demo_target import serve_demo_target
    serve_demo_target(port=args.serve, profile=args.profile, open_browser=args.open)
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="harness", description="Enterprise AI Assurance Harness (MVP)")
    p.add_argument("--version", action="version", version=f"enterprise-harness {__version__}")
    sub = p.add_subparsers(dest="command", required=True)

    def common(sp):
        sp.add_argument("--config", help="config directory (default: <repo>/config)")
        sp.add_argument("--provider", choices=["mock", "litellm", "http"], help="model provider (default: config)")
        sp.add_argument("--profile", choices=["vulnerable", "hardened"], help="mock target profile")
        sp.add_argument("--presidio", action="store_true", help="use Presidio PII/CPNI detectors")
        sp.add_argument("--detoxify", action="store_true", help="add the Detoxify toxicity detector")
        sp.add_argument("--driver", choices=["builtin", "inspect", "overlay", "pyrit", "garak", "nemo"],
                        help="harness driver (B3 seam)")
        sp.add_argument("--pack", choices=["foundational", "advanced", "all"],
                        help="harness pack (default: foundational)")
        sp.add_argument("--usecase", help="path to a use-case JSON (overrides the default)")
        sp.add_argument("--asset", help="path to an asset JSON (overrides the default)")
        sp.add_argument("--scenarios", help="JSON/JSONL/CSV scenario corpus keyed by harness")
        sp.add_argument("--target-url", help="HTTP target URL for --provider http")
        sp.add_argument("--response-path", help="JSON response path for --provider http (default: text)")
        sp.add_argument("--target-header", action="append", metavar="KEY=VALUE",
                        help="HTTP header for --provider http (repeatable)")
        sp.add_argument("--offline-judge", action="store_true",
                        help="demo-only: simulate semantic judge when no real judge key is available")

    r = sub.add_parser("run", help="run the assurance chain")
    common(r)
    r.add_argument("--json", action="store_true", help="print the full bundle as JSON")
    r.add_argument("--out", help="write the bundle JSON to this single file")
    r.add_argument("--bundle", metavar="DIR",
                   help="write a replayable run bundle directory (e.g. runs/RUN-demo) for validate-run")
    r.add_argument("--html", help="also write an HTML dashboard for this run")
    r.add_argument("--open", action="store_true", help="open the HTML dashboard in a browser")
    r.add_argument("--repeat", type=int, default=1, metavar="N",
                   help="run N times and report finding stability (Jaccard); quantifies determinism")
    r.set_defaults(func=cmd_run)

    v = sub.add_parser("verify", help="run + invariant acceptance suite (CI gate)")
    common(v)
    v.set_defaults(func=cmd_verify)

    vr = sub.add_parser("validate-run", help="replay a persisted run bundle from disk (chain-of-custody)")
    vr.add_argument("path", help="path to a runs/RUN-.../ bundle directory (or its replay_manifest.json)")
    vr.set_defaults(func=cmd_validate_run)

    d = sub.add_parser("dashboard", help="build a self-contained HTML dashboard (open/serve locally)")
    common(d)
    d.add_argument("--in", dest="in_", action="append",
                   help="bundle/result JSON to load (repeatable). Omit to run fresh.")
    d.add_argument("--out", help="output HTML path (default: harness_dashboard.html)")
    d.add_argument("--open", action="store_true", help="open the file in a browser")
    d.add_argument("--serve", nargs="?", type=int, const=8000, default=None,
                   metavar="PORT", help="serve on localhost (default port 8000) and open")
    d.set_defaults(func=cmd_dashboard)

    pl = sub.add_parser("plugins", help="inventory plugins/dependencies runnable in the lab")
    pl.set_defaults(func=cmd_plugins)

    doc = sub.add_parser("doctor", help="preflight the environment and enterprise readiness")
    common(doc)
    doc.set_defaults(func=cmd_doctor)

    tgt = sub.add_parser("demo-target", help="serve a local HTTP target at /evaluate for demos")
    tgt.add_argument("--serve", type=int, default=8000, metavar="PORT",
                     help="port to bind (default: 8000)")
    tgt.add_argument("--profile", choices=["vulnerable", "hardened"], default="vulnerable",
                     help="demo target behavior")
    tgt.add_argument("--open", action="store_true", help="open /evaluate in a browser")
    tgt.set_defaults(func=cmd_demo_target)

    pr = sub.add_parser("probe", help="send one prompt through the chain with live indicators")
    common(pr)
    pr.add_argument("--prompt", help="the prompt to send through the chain")
    pr.add_argument("--harness", help="use a specific harness's lenses+detectors (default: full battery)")
    pr.add_argument("--json", action="store_true", help="print the full probe result as JSON")
    pr.add_argument("--serve", nargs="?", type=int, const=8000, default=None, metavar="PORT",
                    help="launch the interactive probe dashboard on localhost (default 8000)")
    pr.set_defaults(func=cmd_probe)

    i = sub.add_parser("info", help="show config, invariants, registry")
    i.add_argument("--config", help="config directory (default: <repo>/config)")
    i.set_defaults(func=cmd_info)
    return p


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
