"""CLI — the entry point. Wires config + adapters into the application and prints results.

    harness run      run the full assurance chain, print the report (+ optional bundle json)
    harness verify   run + the invariant acceptance suite; exit non-zero on any failure
    harness info     show config sources, invariants, and the harness registry

Provider is offline mock by default (zero installs). `--provider litellm` swaps in a real model
(needs `pip install litellm` + a key); the harness code is unchanged.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import asdict
from typing import Optional

from .. import __version__
from ..domain.invariants import INVARIANTS
from ..application.acceptance import run_invariant_suite
from ..application.orchestrator import run_assurance
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
    )
    return ctx, bundle


def cmd_run(args) -> int:
    ctx, bundle = _assemble(args)
    if args.json:
        serializable = {k: v for k, v in bundle.items() if not k.startswith("_")}
        print(json.dumps(serializable, indent=2, default=str))
    else:
        print(render_report(bundle, ctx["specs"]))
        print(f"\nEVIDENCE: {bundle['evidence_root']}")
    if args.out:
        serializable = {k: v for k, v in bundle.items() if not k.startswith("_")}
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(serializable, f, indent=2, default=str)
        print(f"WROTE:    {args.out}")
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
        sp.add_argument("--usecase", help="path to a use-case JSON (overrides the default)")
        sp.add_argument("--asset", help="path to an asset JSON (overrides the default)")

    r = sub.add_parser("run", help="run the assurance chain")
    common(r)
    r.add_argument("--json", action="store_true", help="print the full bundle as JSON")
    r.add_argument("--out", help="write the bundle JSON to this path")
    r.set_defaults(func=cmd_run)

    v = sub.add_parser("verify", help="run + invariant acceptance suite (CI gate)")
    common(v)
    v.set_defaults(func=cmd_verify)

    i = sub.add_parser("info", help="show config, invariants, registry")
    i.add_argument("--config", help="config directory (default: <repo>/config)")
    i.set_defaults(func=cmd_info)
    return p


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
