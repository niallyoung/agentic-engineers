"""
local_model_runtime.py — Local Model Runtime support (COST-004, Phase 1+2)

Detects a running local Ollama instance, lists locally-available models, and
routes tasks to a zero-cost local model when a suitable one is available,
falling back to a cloud provider otherwise.

Strategic goal (COST-004): local models cost $0 per token, so routing
Haiku-class work to a local runtime delivers up to ~95% cost reduction for
users running on their own hardware.

Design decisions:
- Stdlib only (urllib) — no new runtime dependencies. The HTTP fetcher is
  injectable (`http_get_json`) so the suite never touches the network.
- Availability is discovered live from Ollama's `/api/tags` endpoint; the
  registered zero-cost model catalogue is read from src/config/providers.yaml
  (the `ollama` provider added for COST-002).
- Cost accounting for any local model is always 0.0. Cloud fallback cost is
  computed from providers.yaml per-1M-token rates when token counts are given.
- Fallback is graceful: when Ollama is down, no suitable local model exists, or
  a quality floor cannot be met locally, route to cloud (unless disallowed).

Usage:
    from scripts.local_model_runtime import LocalModelRuntime

    rt = LocalModelRuntime()
    if rt.is_available():
        decision = rt.route("code_review", input_tokens=4000, output_tokens=1500)
        print(decision.provider, decision.model, decision.estimated_cost)
"""
from __future__ import annotations

import json
import logging
import os
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

try:
    import yaml
except Exception:  # pragma: no cover - yaml is a project dependency
    yaml = None  # type: ignore

logger = logging.getLogger(__name__)

DEFAULT_HOST = "http://localhost:11434"

# Quality rank [0-100] per local model family. Higher = more capable.
# Conservative heuristic ordering of popular Ollama families.
_FAMILY_QUALITY: Dict[str, int] = {
    "llama3.1": 85,
    "llama3": 80,
    "codellama": 78,
    "mistral": 75,
    "phi3": 65,
}
_DEFAULT_FAMILY_QUALITY = 60

# Preferred family order per task type (best-fit first).
_GENERAL_PREF = ["llama3.1", "llama3", "mistral", "phi3"]
_CODE_PREF = ["codellama", "llama3.1", "llama3"]
_TASK_FAMILY_PREF: Dict[str, List[str]] = {
    "code": _CODE_PREF,
    "code_review": _CODE_PREF,
    "implementation": _CODE_PREF,
    "general": _GENERAL_PREF,
    "documentation": ["llama3.1", "llama3", "mistral"],
    "summarization": ["llama3.1", "mistral", "phi3"],
}

# Default cloud fallback target (cheap, capable).
_DEFAULT_CLOUD_PROVIDER = "anthropic"
_DEFAULT_CLOUD_MODEL = "claude-haiku-4.5"


class LocalModelUnavailableError(RuntimeError):
    """Raised when no local model can serve a request and fallback is disabled."""


@dataclass
class LocalModel:
    """A model available from the local Ollama runtime."""

    name: str
    family: str
    size_bytes: Optional[int] = None
    parameter_size: Optional[str] = None
    quality_rank: int = _DEFAULT_FAMILY_QUALITY
    cost_per_1m: float = 0.0

    @property
    def size_gb(self) -> Optional[float]:
        if self.size_bytes is None:
            return None
        return round(self.size_bytes / 1e9, 2)


@dataclass
class RoutingDecision:
    """Outcome of a routing request: local model or cloud fallback."""

    provider: str
    model: Optional[str]
    estimated_cost: float
    used_fallback: bool
    local_available: bool
    reason: str
    candidates: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "provider": self.provider,
            "model": self.model,
            "estimated_cost": self.estimated_cost,
            "used_fallback": self.used_fallback,
            "local_available": self.local_available,
            "reason": self.reason,
            "candidates": self.candidates,
        }


class LocalModelRuntime:
    """Detect and route to a local Ollama runtime with cloud fallback."""

    def __init__(
        self,
        host: Optional[str] = None,
        providers_yaml: Optional[Path] = None,
        http_get_json: Optional[Callable[[str], Any]] = None,
        timeout: float = 2.0,
    ) -> None:
        """
        Args:
            host: Ollama base URL. Defaults to $OLLAMA_HOST or DEFAULT_HOST.
            providers_yaml: Path to providers.yaml. Defaults to the repo's
                src/config/providers.yaml (located by walking up parents).
            http_get_json: Injectable JSON fetcher taking a full URL and
                returning parsed JSON. Defaults to a urllib-based fetcher.
            timeout: HTTP timeout (seconds) for the default fetcher.
        """
        raw_host = host or os.environ.get("OLLAMA_HOST") or DEFAULT_HOST
        self.host = self._normalize_host(raw_host)
        self.timeout = timeout
        self._http_get_json = http_get_json or self._default_http_get_json
        self._providers_yaml = providers_yaml or self._find_providers_yaml()
        self._registered_models = self._load_registered_models()

    # ------------------------------------------------------------------ utils
    @staticmethod
    def _normalize_host(raw: str) -> str:
        host = raw.strip().rstrip("/")
        if not host.startswith("http://") and not host.startswith("https://"):
            host = "http://" + host
        return host

    def _default_http_get_json(self, url: str) -> Any:
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:  # nosec B310
            return json.loads(resp.read().decode("utf-8"))

    @staticmethod
    def _find_providers_yaml() -> Path:
        here = Path(__file__).resolve()
        for parent in here.parents:
            candidate = parent / "src" / "config" / "providers.yaml"
            if candidate.exists():
                return candidate
        return here.parents[4] / "src" / "config" / "providers.yaml"

    def _load_registered_models(self) -> List[str]:
        """Read the zero-cost ollama model catalogue from providers.yaml."""
        if yaml is None or not self._providers_yaml.exists():
            return list(_FAMILY_QUALITY.keys())
        try:
            with open(self._providers_yaml, "r", encoding="utf-8") as fh:
                data = yaml.safe_load(fh) or {}
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning("Failed to read providers.yaml: %s", exc)
            return list(_FAMILY_QUALITY.keys())
        ollama = (data.get("providers") or {}).get("ollama") or {}
        models = list((ollama.get("models") or {}).keys())
        return models or list(_FAMILY_QUALITY.keys())

    @staticmethod
    def _family_of(name: str) -> str:
        return name.split(":", 1)[0]

    @classmethod
    def _quality_for(cls, name: str) -> int:
        return _FAMILY_QUALITY.get(cls._family_of(name), _DEFAULT_FAMILY_QUALITY)

    # ------------------------------------------------------------- discovery
    def is_available(self) -> bool:
        """Return True if a local Ollama instance answers on the host."""
        try:
            self._http_get_json(f"{self.host}/api/tags")
            return True
        except Exception as exc:
            logger.debug("Ollama not available at %s: %s", self.host, exc)
            return False

    def list_models(self) -> List[LocalModel]:
        """List models the local Ollama instance currently has pulled."""
        try:
            data = self._http_get_json(f"{self.host}/api/tags")
        except Exception as exc:
            logger.debug("list_models failed: %s", exc)
            return []
        out: List[LocalModel] = []
        for entry in (data or {}).get("models", []) or []:
            name = entry.get("name") or entry.get("model")
            if not name:
                continue
            details = entry.get("details") or {}
            out.append(
                LocalModel(
                    name=name,
                    family=self._family_of(name),
                    size_bytes=entry.get("size"),
                    parameter_size=details.get("parameter_size"),
                    quality_rank=self._quality_for(name),
                )
            )
        return out

    # --------------------------------------------------------------- routing
    def select_model(
        self,
        task_type: str = "general",
        constraints: Optional[Dict[str, Any]] = None,
    ) -> Optional[LocalModel]:
        """
        Pick the best-fit locally-available model for a task, or None.

        Returns None when no local model is available or the best available
        model cannot meet a `min_quality` floor in `constraints`.
        """
        constraints = constraints or {}
        available = self.list_models()
        if not available:
            return None

        min_quality = constraints.get("min_quality", 0)
        by_name = {m.name: m for m in available}
        by_family: Dict[str, LocalModel] = {}
        for m in sorted(available, key=lambda x: x.quality_rank, reverse=True):
            by_family.setdefault(m.family, m)

        chosen: Optional[LocalModel] = None
        for fam in _TASK_FAMILY_PREF.get(task_type, _GENERAL_PREF):
            if fam in by_family:
                chosen = by_family[fam]
                break
        if chosen is None:
            # No preferred family pulled — fall back to highest-quality local.
            chosen = max(available, key=lambda x: x.quality_rank)

        if chosen.quality_rank < min_quality:
            logger.debug(
                "Best local model %s (q=%d) below min_quality=%d",
                chosen.name,
                chosen.quality_rank,
                min_quality,
            )
            return None
        return by_name.get(chosen.name, chosen)

    def route(
        self,
        task_type: str = "general",
        input_tokens: int = 0,
        output_tokens: int = 0,
        constraints: Optional[Dict[str, Any]] = None,
        allow_cloud_fallback: bool = True,
    ) -> RoutingDecision:
        """
        Decide whether to run a task on a local model or fall back to cloud.

        Args:
            task_type: Task category (e.g. "code_review", "general").
            input_tokens / output_tokens: Used to estimate cloud fallback cost.
            constraints: Optional dict. Recognised keys:
                - min_quality (int): minimum acceptable local quality rank.
                - cloud_provider (str) / cloud_model (str): fallback target.
            allow_cloud_fallback: If False, raise when no local model fits.
        """
        constraints = constraints or {}
        available = self.is_available()
        candidates = [m.name for m in self.list_models()] if available else []

        if available:
            local = self.select_model(task_type, constraints)
            if local is not None:
                return RoutingDecision(
                    provider="ollama",
                    model=local.name,
                    estimated_cost=0.0,
                    used_fallback=False,
                    local_available=True,
                    reason=f"Routed to local model {local.name} (cost $0).",
                    candidates=candidates,
                )
            fallback_reason = "No local model met the quality floor."
        else:
            fallback_reason = f"Ollama not reachable at {self.host}."

        if not allow_cloud_fallback:
            raise LocalModelUnavailableError(fallback_reason)

        provider = constraints.get("cloud_provider", _DEFAULT_CLOUD_PROVIDER)
        model = constraints.get("cloud_model", _DEFAULT_CLOUD_MODEL)
        cost = self._cloud_cost(provider, model, input_tokens, output_tokens)
        return RoutingDecision(
            provider=provider,
            model=model,
            estimated_cost=cost,
            used_fallback=True,
            local_available=available,
            reason=f"{fallback_reason} Falling back to {provider}/{model}.",
            candidates=candidates,
        )

    # ----------------------------------------------------------------- costs
    def _provider_rates(self, provider: str, model: str) -> Dict[str, float]:
        if yaml is None or not self._providers_yaml.exists():
            return {"input_per_1m": 0.0, "output_per_1m": 0.0}
        try:
            with open(self._providers_yaml, "r", encoding="utf-8") as fh:
                data = yaml.safe_load(fh) or {}
        except Exception:  # pragma: no cover - defensive
            return {"input_per_1m": 0.0, "output_per_1m": 0.0}
        pdata = (data.get("providers") or {}).get(provider) or {}
        models = pdata.get("models") or {}
        rates = models.get(model) or pdata.get("fallback") or {}
        return {
            "input_per_1m": float(rates.get("input_per_1m", 0.0)),
            "output_per_1m": float(rates.get("output_per_1m", 0.0)),
        }

    def _cloud_cost(
        self, provider: str, model: str, input_tokens: int, output_tokens: int
    ) -> float:
        rates = self._provider_rates(provider, model)
        cost = (input_tokens / 1_000_000.0) * rates["input_per_1m"] + (
            output_tokens / 1_000_000.0
        ) * rates["output_per_1m"]
        return round(cost, 6)

    def estimate_savings(
        self,
        cloud_provider: str = _DEFAULT_CLOUD_PROVIDER,
        cloud_model: str = _DEFAULT_CLOUD_MODEL,
        input_tokens: int = 0,
        output_tokens: int = 0,
    ) -> float:
        """USD saved by serving a task locally ($0) instead of on cloud."""
        return self._cloud_cost(
            cloud_provider, cloud_model, input_tokens, output_tokens
        )


# --------------------------------------------------------------------- CLI
def main(argv: Optional[List[str]] = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(
        prog="local-model-runtime",
        description="Detect and route to a local Ollama runtime (COST-004).",
    )
    parser.add_argument("--host", default=None, help="Ollama base URL")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("status", help="Report whether Ollama is reachable")
    sub.add_parser("list", help="List locally-available models")
    route_p = sub.add_parser("route", help="Show routing decision for a task")
    route_p.add_argument("--task-type", default="general")
    route_p.add_argument("--input-tokens", type=int, default=0)
    route_p.add_argument("--output-tokens", type=int, default=0)
    route_p.add_argument("--min-quality", type=int, default=0)
    route_p.add_argument("--no-fallback", action="store_true")

    args = parser.parse_args(argv)
    rt = LocalModelRuntime(host=args.host)

    if args.command == "status":
        print(json.dumps({"host": rt.host, "available": rt.is_available()}, indent=2))
        return 0
    if args.command == "list":
        models = [
            {"name": m.name, "family": m.family, "size_gb": m.size_gb,
             "quality_rank": m.quality_rank, "cost_per_1m": m.cost_per_1m}
            for m in rt.list_models()
        ]
        print(json.dumps({"models": models}, indent=2))
        return 0
    if args.command == "route":
        try:
            decision = rt.route(
                task_type=args.task_type,
                input_tokens=args.input_tokens,
                output_tokens=args.output_tokens,
                constraints={"min_quality": args.min_quality},
                allow_cloud_fallback=not args.no_fallback,
            )
        except LocalModelUnavailableError as exc:
            print(json.dumps({"error": str(exc)}, indent=2))
            return 1
        print(json.dumps(decision.to_dict(), indent=2))
        return 0
    return 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
