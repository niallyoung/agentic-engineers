#!/usr/bin/env python3
"""tests/test_model_evidence.py - structured, validated evidence in config/models.yaml.

Each model may carry sourced `facts` (price, context, max output, knowledge cutoff) and a
`cli_accepted` record (real Claude CLI acceptance). Facts are only legal next to a complete
`verified` date + https `source`; nulls stay legal. Rules are enforced by `scripts/models.py check`.
Mutations run against a temp copy, never the real tree.
"""

import datetime
import importlib.util
import re
import shutil
import sys
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("ae_models_evidence", REPO_ROOT / "scripts" / "models.py")
models = importlib.util.module_from_spec(_spec)
sys.modules["ae_models_evidence"] = models
_spec.loader.exec_module(models)

COPY_PATHS = ["config/models.yaml", "config/FRAMEWORK-MANIFEST.yaml", "src/AGENTS.md",
              "src/agents", ".githooks/LOCKED_MODELS.sh", ".agents_verification_sha", "docs/MODELS.md"]
TODAY = datetime.date(2026, 10, 3)
URL = "https://platform.claude.com/docs/en/models/sonnet-5-5/overview"
GOOD_FACTS = {
    "price_per_mtok": {"input": 2, "output": 10, "cache_read": 0.2, "cache_write_5m": 2.5, "cache_write_1h": 4},
    "context_tokens": 1000000,
    "max_output_tokens": 128000,
    "knowledge_cutoff": "2026-06",
}


def make_tree(tmp_path):
    for rel in COPY_PATHS:
        src, dst = REPO_ROOT / rel, tmp_path / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(src, dst) if src.is_dir() else shutil.copy2(src, dst)
    return tmp_path


def mutate(root, fn):
    path = Path(root) / "config" / "models.yaml"
    reg = yaml.safe_load(path.read_text())
    fn(reg)
    path.write_text(yaml.safe_dump(reg, sort_keys=False))


def errors_for(root):
    errors, _ = models.check(root)
    return [e for e in errors if "facts" in e or "cli_accepted" in e or "verified" in e or "source" in e]


@pytest.fixture(scope="module")
def reg():
    return models.load_registry()


class TestRealRegistryEvidence:
    def test_real_registry_has_no_evidence_errors(self):
        errors, _ = models.check()
        assert errors == []

    def test_every_model_with_facts_has_verified_and_https_source(self, reg):
        for mid, m in reg["models"].items():
            if m.get("facts"):
                assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(m.get("verified"))), mid
                assert str(m.get("source")).startswith("https://"), mid

    @pytest.mark.parametrize("mid", ["claude-sonnet-5.5", "claude-opus-5.5"])
    def test_pinned_55_models_are_sourced(self, reg, mid):
        m = reg["models"][mid]
        assert m["facts"]["price_per_mtok"]["input"] > 0
        assert m["facts"]["context_tokens"] and m["facts"]["max_output_tokens"]
        assert m["verified"] and m["source"]

    def test_every_role_pin_has_cli_acceptance(self, reg):
        pins = {cfg["model"] for cfg in reg["roles"].values()}
        for mid in pins:
            acc = reg["models"][mid].get("cli_accepted")
            assert acc, f"{mid}: role pin without cli_accepted evidence"
            assert acc["modelusage_key"] == reg["models"][mid]["ids"]["claude"]

    def test_sonnet_4_6_cli_acceptance_recorded(self, reg):
        assert reg["models"]["claude-sonnet-4.6"]["cli_accepted"]["modelusage_key"] == "claude-sonnet-4-6"


class TestFactsValidation:
    def test_null_facts_accepted(self, tmp_path):
        root = make_tree(tmp_path)
        def fn(r):
            for m in r["models"].values():
                m["facts"] = None
                m["cli_accepted"] = None
                m["verified"] = None
                m["source"] = None
        mutate(root, fn)
        assert errors_for(root) == []

    def test_facts_without_source_rejected(self, tmp_path):
        root = make_tree(tmp_path)
        def fn(r):
            m = r["models"]["claude-fable-5"]
            m["facts"], m["verified"], m["source"] = GOOD_FACTS, None, None
        mutate(root, fn)
        assert any("claude-fable-5" in e and "facts" in e for e in errors_for(root))

    def test_facts_with_verified_but_no_source_rejected(self, tmp_path):
        root = make_tree(tmp_path)
        def fn(r):
            m = r["models"]["claude-fable-5"]
            m["facts"], m["verified"], m["source"] = GOOD_FACTS, TODAY, None
        mutate(root, fn)
        assert errors_for(root)

    def test_facts_with_http_source_rejected(self, tmp_path):
        root = make_tree(tmp_path)
        def fn(r):
            m = r["models"]["claude-fable-5"]
            m["facts"], m["verified"], m["source"] = GOOD_FACTS, TODAY, "http://example.com/x"
        mutate(root, fn)
        assert any("claude-fable-5" in e for e in errors_for(root))

    def test_facts_with_non_iso_verified_rejected(self, tmp_path):
        root = make_tree(tmp_path)
        def fn(r):
            m = r["models"]["claude-fable-5"]
            m["facts"], m["verified"], m["source"] = GOOD_FACTS, "yesterday", URL
        mutate(root, fn)
        assert any("claude-fable-5" in e for e in errors_for(root))

    def test_sourced_facts_accepted(self, tmp_path):
        root = make_tree(tmp_path)
        def fn(r):
            m = r["models"]["claude-fable-5"]
            m["facts"], m["verified"], m["source"] = GOOD_FACTS, TODAY, URL
        mutate(root, fn)
        assert errors_for(root) == []

    @pytest.mark.parametrize("bad", [
        {"price_per_mtok": {"input": 2}},                                   # output missing
        {"price_per_mtok": {"input": -1, "output": 10}},                    # negative
        {"price_per_mtok": {"input": "two", "output": 10}},                 # not a number
        {"price_per_mtok": {"input": 2, "output": 10, "bogus": 1}},         # unknown price key
        {"context_tokens": 0},
        {"context_tokens": "1M"},
        {"max_output_tokens": -5},
        {"knowledge_cutoff": "June 2026"},
        {"knowledge_cutoff": "2026-13"},
        {"unknown_fact": 1},
    ])
    def test_malformed_facts_rejected(self, tmp_path, bad):
        root = make_tree(tmp_path)
        def fn(r):
            m = r["models"]["claude-fable-5"]
            m["facts"], m["verified"], m["source"] = bad, TODAY, URL
        mutate(root, fn)
        assert any("claude-fable-5" in e and "facts" in e for e in errors_for(root)), bad

    def test_facts_must_be_a_mapping(self, tmp_path):
        root = make_tree(tmp_path)
        def fn(r):
            m = r["models"]["claude-fable-5"]
            m["facts"], m["verified"], m["source"] = ["input", 10], TODAY, URL
        mutate(root, fn)
        assert any("claude-fable-5" in e and "facts" in e for e in errors_for(root))


class TestCliAcceptedValidation:
    def test_wrong_modelusage_key_rejected(self, tmp_path):
        root = make_tree(tmp_path)
        mutate(root, lambda r: r["models"]["claude-fable-5"].update(
            cli_accepted={"date": TODAY, "modelusage_key": "claude-opus-5"}))
        assert any("claude-fable-5" in e and "cli_accepted" in e for e in errors_for(root))

    def test_bad_date_rejected(self, tmp_path):
        root = make_tree(tmp_path)
        mutate(root, lambda r: r["models"]["claude-fable-5"].update(
            cli_accepted={"date": "soon", "modelusage_key": "claude-fable-5"}))
        assert any("cli_accepted" in e for e in errors_for(root))

    def test_future_date_rejected(self, tmp_path):
        root = make_tree(tmp_path)
        mutate(root, lambda r: r["models"]["claude-fable-5"].update(
            cli_accepted={"date": datetime.date.today() + datetime.timedelta(days=30), "modelusage_key": "claude-fable-5"}))
        assert any("cli_accepted" in e for e in errors_for(root))

    def test_missing_key_rejected(self, tmp_path):
        root = make_tree(tmp_path)
        mutate(root, lambda r: r["models"]["claude-fable-5"].update(cli_accepted={"date": TODAY}))
        assert any("cli_accepted" in e for e in errors_for(root))

    def test_valid_record_accepted(self, tmp_path):
        root = make_tree(tmp_path)
        mutate(root, lambda r: r["models"]["claude-fable-5"].update(
            cli_accepted={"date": TODAY, "modelusage_key": "claude-fable-5"}))
        assert errors_for(root) == []
