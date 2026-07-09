"""Scenario corpus loads against its contract and fails fast on a malformed row (§4.9)."""
import json

import pytest

from harness.registry import load_harnesses


def _write(path, rows):
    path.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
    return str(path)


def test_valid_external_corpus_loads(tmp_path):
    p = _write(tmp_path / "corpus.jsonl",
               [{"harness": "HX.1", "id": "S1", "category": "test.cat", "attack": "do X", "label": True}])
    suite = load_harnesses(scenario_path=p)
    assert "HX.1" in suite and suite["HX.1"].scenarios[0].id == "S1"


def test_missing_attack_fails_fast(tmp_path):
    p = _write(tmp_path / "bad.jsonl", [{"harness": "HX.1", "id": "S1", "category": "c"}])
    with pytest.raises(ValueError):
        load_harnesses(scenario_path=p)


def test_missing_harness_fails_fast(tmp_path):
    p = _write(tmp_path / "bad2.jsonl", [{"id": "S1", "category": "c", "attack": "x"}])
    with pytest.raises(ValueError):
        load_harnesses(scenario_path=p)
