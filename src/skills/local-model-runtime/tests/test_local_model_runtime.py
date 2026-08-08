"""
test_local_model_runtime.py — test suite for COST-004 (LocalModelRuntime).

Covers host resolution, Ollama detection, model listing/parsing, best-fit
local selection per task type, quality-floor handling, local-vs-cloud routing,
graceful fallback, cloud cost estimation, and the CLI. The HTTP layer is fully
mocked, so no live Ollama instance or network access is required.
"""
from __future__ import annotations

import io
import json
import sys
from contextlib import redirect_stdout
from pathlib import Path

import pytest

_SKILL_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(_SKILL_ROOT))

from scripts.local_model_runtime import (  # noqa: E402
    DEFAULT_HOST,
    LocalModel,
    LocalModelRuntime,
    LocalModelUnavailableError,
    RoutingDecision,
    main,
)

# --------------------------------------------------------------------------
# Fakes / fixtures
# --------------------------------------------------------------------------

TAGS_RESPONSE = {
    "models": [
        {"name": "llama3.1:latest", "size": 4_700_000_000,
         "details": {"parameter_size": "8B"}},
        {"name": "codellama:latest", "size": 3_800_000_000,
         "details": {"parameter_size": "7B"}},
        {"name": "phi3:latest", "size": 2_200_000_000,
         "details": {"parameter_size": "3.8B"}},
    ]
}


def make_fetcher(response=None, raise_exc=None):
    """Build an injectable http_get_json that returns canned JSON or raises."""
    calls = {"urls": []}

    def _fetch(url):
        calls["urls"].append(url)
        if raise_exc is not None:
            raise raise_exc
        return response

    _fetch.calls = calls
    return _fetch


@pytest.fixture
def up_runtime():
    """Runtime with a reachable Ollama returning TAGS_RESPONSE."""
    return LocalModelRuntime(http_get_json=make_fetcher(response=TAGS_RESPONSE))


@pytest.fixture
def down_runtime():
    """Runtime with an unreachable Ollama (fetcher raises)."""
    return LocalModelRuntime(
        http_get_json=make_fetcher(raise_exc=ConnectionError("refused"))
    )


# --------------------------------------------------------------------------
# Host resolution
# --------------------------------------------------------------------------

def test_default_host(monkeypatch):
    monkeypatch.delenv("OLLAMA_HOST", raising=False)
    rt = LocalModelRuntime(http_get_json=make_fetcher(response=TAGS_RESPONSE))
    assert rt.host == DEFAULT_HOST


def test_host_from_env(monkeypatch):
    monkeypatch.setenv("OLLAMA_HOST", "remote-box:11434")
    rt = LocalModelRuntime(http_get_json=make_fetcher(response=TAGS_RESPONSE))
    assert rt.host == "http://remote-box:11434"


def test_host_explicit_overrides_env(monkeypatch):
    monkeypatch.setenv("OLLAMA_HOST", "remote-box:11434")
    rt = LocalModelRuntime(
        host="http://localhost:9999/",
        http_get_json=make_fetcher(response=TAGS_RESPONSE),
    )
    assert rt.host == "http://localhost:9999"


# --------------------------------------------------------------------------
# Availability
# --------------------------------------------------------------------------

def test_is_available_true(up_runtime):
    assert up_runtime.is_available() is True


def test_is_available_false(down_runtime):
    assert down_runtime.is_available() is False


def test_is_available_hits_tags_endpoint(up_runtime):
    up_runtime.is_available()
    assert up_runtime._http_get_json.calls["urls"][-1].endswith("/api/tags")


# --------------------------------------------------------------------------
# Listing
# --------------------------------------------------------------------------

def test_list_models_parses(up_runtime):
    models = up_runtime.list_models()
    assert {m.name for m in models} == {
        "llama3.1:latest", "codellama:latest", "phi3:latest"
    }


def test_list_models_family_and_size(up_runtime):
    by_name = {m.name: m for m in up_runtime.list_models()}
    assert by_name["llama3.1:latest"].family == "llama3.1"
    assert by_name["llama3.1:latest"].size_gb == 4.7
    assert by_name["llama3.1:latest"].parameter_size == "8B"


def test_list_models_quality_rank(up_runtime):
    by_name = {m.name: m for m in up_runtime.list_models()}
    assert by_name["llama3.1:latest"].quality_rank == 85
    assert by_name["phi3:latest"].quality_rank == 65


def test_list_models_empty_when_unavailable(down_runtime):
    assert down_runtime.list_models() == []


def test_unknown_family_default_rank():
    rt = LocalModelRuntime(
        http_get_json=make_fetcher(
            response={"models": [{"name": "exotic-model:latest", "size": 1}]}
        )
    )
    assert rt.list_models()[0].quality_rank == 60


# --------------------------------------------------------------------------
# Selection
# --------------------------------------------------------------------------

def test_select_general_prefers_highest_quality(up_runtime):
    chosen = up_runtime.select_model("general")
    assert chosen.name == "llama3.1:latest"


def test_select_code_prefers_codellama(up_runtime):
    chosen = up_runtime.select_model("code_review")
    assert chosen.name == "codellama:latest"


def test_select_none_when_unavailable(down_runtime):
    assert down_runtime.select_model("general") is None


def test_select_respects_min_quality(up_runtime):
    # Highest available is llama3.1 (85); a floor above that yields None.
    assert up_runtime.select_model("general", {"min_quality": 90}) is None
    assert up_runtime.select_model("general", {"min_quality": 80}) is not None


def test_select_falls_back_to_best_when_no_preferred():
    # Only an unknown family is pulled; selection still returns it.
    rt = LocalModelRuntime(
        http_get_json=make_fetcher(
            response={"models": [{"name": "exotic:latest", "size": 1}]}
        )
    )
    chosen = rt.select_model("general")
    assert chosen.name == "exotic:latest"


# --------------------------------------------------------------------------
# Routing
# --------------------------------------------------------------------------

def test_route_uses_local_zero_cost(up_runtime):
    decision = up_runtime.route("general", input_tokens=5000, output_tokens=2000)
    assert isinstance(decision, RoutingDecision)
    assert decision.provider == "ollama"
    assert decision.model == "llama3.1:latest"
    assert decision.estimated_cost == 0.0
    assert decision.used_fallback is False
    assert decision.local_available is True


def test_route_falls_back_when_unavailable(down_runtime):
    decision = down_runtime.route("general", input_tokens=1000, output_tokens=1000)
    assert decision.used_fallback is True
    assert decision.local_available is False
    assert decision.provider == "anthropic"
    assert decision.model == "claude-haiku-4.5"


def test_route_fallback_when_quality_too_low(up_runtime):
    decision = up_runtime.route("general", constraints={"min_quality": 99})
    assert decision.used_fallback is True
    assert decision.local_available is True
    assert "quality" in decision.reason.lower()


def test_route_raises_when_no_fallback_and_unavailable(down_runtime):
    with pytest.raises(LocalModelUnavailableError):
        down_runtime.route("general", allow_cloud_fallback=False)


def test_route_respects_cloud_override(down_runtime):
    decision = down_runtime.route(
        "general",
        input_tokens=1_000_000,
        output_tokens=0,
        constraints={"cloud_provider": "openai", "cloud_model": "gpt-5-mini"},
    )
    assert decision.provider == "openai"
    assert decision.model == "gpt-5-mini"
    # gpt-5-mini input rate is 0.40/1M → 1M input tokens ≈ $0.40
    assert decision.estimated_cost == pytest.approx(0.40, abs=1e-6)


# --------------------------------------------------------------------------
# Costs / savings
# --------------------------------------------------------------------------

def test_cloud_cost_from_providers_yaml(up_runtime):
    # anthropic/claude-haiku-4.5 (src/config/providers.yaml): input 1.00/1M, output 5.00/1M
    cost = up_runtime._cloud_cost("anthropic", "claude-haiku-4.5", 1_000_000, 1_000_000)
    assert cost == pytest.approx(6.00, abs=1e-6)


def test_estimate_savings_equals_cloud_cost(up_runtime):
    savings = up_runtime.estimate_savings(
        "anthropic", "claude-haiku-4.5", 1_000_000, 0
    )
    assert savings == pytest.approx(1.00, abs=1e-6)


def test_local_model_cost_is_zero():
    m = LocalModel(name="llama3:latest", family="llama3")
    assert m.cost_per_1m == 0.0


def test_routing_decision_to_dict(up_runtime):
    d = up_runtime.route("general").to_dict()
    assert d["provider"] == "ollama"
    assert d["estimated_cost"] == 0.0
    assert "candidates" in d


# --------------------------------------------------------------------------
# Registered catalogue from providers.yaml
# --------------------------------------------------------------------------

def test_registered_models_loaded_from_yaml(up_runtime):
    # providers.yaml ships an ollama section with these families.
    fams = {m.split(":", 1)[0] for m in up_runtime._registered_models}
    assert "llama3.1" in fams or "llama3" in fams


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------

def _run_cli(monkeypatch, argv, response=None, raise_exc=None):
    fetcher = make_fetcher(response=response, raise_exc=raise_exc)
    orig_init = LocalModelRuntime.__init__

    def patched_init(self, host=None, providers_yaml=None,
                     http_get_json=None, timeout=2.0):
        orig_init(self, host=host, providers_yaml=providers_yaml,
                  http_get_json=fetcher, timeout=timeout)

    monkeypatch.setattr(LocalModelRuntime, "__init__", patched_init)
    buf = io.StringIO()
    with redirect_stdout(buf):
        code = main(argv)
    return code, buf.getvalue()


def test_cli_status_available(monkeypatch):
    code, out = _run_cli(monkeypatch, ["status"], response=TAGS_RESPONSE)
    assert code == 0
    assert json.loads(out)["available"] is True


def test_cli_list(monkeypatch):
    code, out = _run_cli(monkeypatch, ["list"], response=TAGS_RESPONSE)
    assert code == 0
    names = {m["name"] for m in json.loads(out)["models"]}
    assert "codellama:latest" in names


def test_cli_route_local(monkeypatch):
    code, out = _run_cli(
        monkeypatch, ["route", "--task-type", "code_review"], response=TAGS_RESPONSE
    )
    assert code == 0
    data = json.loads(out)
    assert data["provider"] == "ollama"
    assert data["model"] == "codellama:latest"


def test_cli_route_no_fallback_unavailable(monkeypatch):
    code, out = _run_cli(
        monkeypatch, ["route", "--no-fallback"], raise_exc=ConnectionError("x")
    )
    assert code == 1
    assert "error" in json.loads(out)
