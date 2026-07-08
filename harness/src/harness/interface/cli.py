"""CLI — the entry point. Wires config + adapters into the application and prints results.

    harness run        run the full assurance chain, print the report (+ optional bundle/dashboard)
    harness verify     run + the invariant acceptance suite; exit non-zero on any failure
    harness dashboard  build a self-contained HTML dashboard (open/serve locally)
    harness info       show config sources, invariants, and the harness registry

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
    return ov


def _load_json(path: Optional[str], default: dict) -> dict:
    if not path:
        return default
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _assemble(args):
    ctx = factory.build_context(config_dir=args.config, overrides=_overrides(args))
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


def cmd_run(args) -> int:
    ctx, bundle = _assemble(args)
    if args.json:
        print(json.dumps(_serializable(bundle), indent=2, default=str))
    else:
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
    ctx = factory.build_context(config_dir=args.config, overrides=_overrides(args))
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


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="harness", description="Enterprise AI Assurance Harness (MVP)")
    p.add_argument("--version", action="version", version=f"enterprise-harness {__version__}")
    sub = p.add_subparsers(dest="command", required=True)

    def common(sp):
        sp.add_argument("--config", help="config directory (default: <repo>/config)")
        sp.add_argument("--provider", choices=["mock", "litellm"], help="model provider (default: config)")
        sp.add_argument("--profile", choices=["vulnerable", "hardened"], help="mock target profile")
        sp.add_argument("--presidio", action="store_true", help="use Presidio PII/CPNI detectors")
        sp.add_argument("--detoxify", action="store_true", help="add the Detoxify toxicity detector")
        sp.add_argument("--driver", choices=["builtin", "inspect", "overlay", "pyrit", "garak", "nemo"],
                        help="harness driver (B3 seam)")
        sp.add_argument("--pack", choices=["foundational", "advanced", "all"],
                        help="harness pack (default: foundational)")
        sp.add_argument("--usecase", help="path to a use-case JSON (overrides the default)")
        sp.add_argument("--asset", help="path to an asset JSON (overrides the default)")

    r = sub.add_parser("run", help="run the assurance chain")
    common(r)
    r.add_argument("--json", action="store_true", help="print the full bundle as JSON")
    r.add_argument("--out", help="write the bundle JSON to this path")
    r.add_argument("--html", help="also write an HTML dashboard for this run")
    r.add_argument("--open", action="store_true", help="open the HTML dashboard in a browser")
    r.add_argument("--repeat", type=int, default=1, metavar="N",
                   help="run N times and report finding stability (Jaccard); quantifies determinism")
    r.set_defaults(func=cmd_run)

    v = sub.add_parser("verify", help="run + invariant acceptance suite (CI gate)")
    common(v)
    v.set_defaults(func=cmd_verify)

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
