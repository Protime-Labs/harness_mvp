"""M5 — import-boundary lint: keep the hexagonal layers clean (architectural drift guard, §4.10).

Checks MODULE-LEVEL imports only; a deliberate lazy import inside a function is an allowed escape
hatch (e.g. bundle.validate_run_bundle building detectors on demand)."""
import ast
import pathlib

SRC = pathlib.Path(__file__).resolve().parents[1] / "src" / "harness"
PROVIDER_SDKS = {"litellm", "anthropic", "openai", "boto3", "google", "cohere", "mistralai", "vertexai"}


def _module_level_imports(pyfile):
    for node in ast.parse(pyfile.read_text(encoding="utf-8")).body:  # top-level only
        if isinstance(node, ast.Import):
            for a in node.names:
                yield a.name, 0
        elif isinstance(node, ast.ImportFrom):
            yield (node.module or ""), node.level


def _files(layer):
    return sorted((SRC / layer).rglob("*.py"))


def test_domain_imports_stdlib_or_domain_only():
    for py in _files("domain"):
        for mod, level in _module_level_imports(py):
            base = mod.split(".")[0]
            if level == 0:  # absolute -> must be stdlib, never a harness layer or provider SDK
                assert base not in {"harness", "adapters", "application", "ports", "interface", "storage"}, \
                    f"{py.name}: domain imports {mod}"
                assert base not in PROVIDER_SDKS, f"{py.name}: domain imports provider SDK {mod}"
            else:  # relative -> must stay within domain (level 1 sibling module)
                assert level == 1, f"{py.name}: domain reaches out of its package ({'.' * level}{mod})"


def test_application_and_ports_avoid_adapters_and_sdks():
    for layer in ("application", "ports"):
        for py in _files(layer):
            for mod, _level in _module_level_imports(py):
                base = mod.split(".")[0]
                assert base not in PROVIDER_SDKS, f"{py.name}: {layer} imports provider SDK {mod}"
                assert base != "adapters" and not mod.startswith("adapters"), \
                    f"{py.name}: {layer} imports adapters at module level ({mod}) — inject or lazy-import"
                assert base != "interface" and not mod.startswith("interface"), \
                    f"{py.name}: {layer} imports interface ({mod})"
