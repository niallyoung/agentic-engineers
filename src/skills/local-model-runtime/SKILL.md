---
name: local-model-runtime
description: >
  Local Model Runtime support (COST-004) — detects a running local Ollama
  instance, lists locally-available models, and routes tasks to a zero-cost
  local model when a suitable one exists, falling back to a cloud provider
  otherwise. Strategic enabler of up to ~95% cost reduction.
version: "1.0.0"
dependencies:
  - skill: cost-aggregation
    optional: true
  - skill: model-selection
    optional: true
entry_points:
  - scripts/local_model_runtime.py
tests:
  - tests/test_local_model_runtime.py
coverage_minimum: 85
---

# COST-004: Local Model Runtime (Ollama)

Detects a local [Ollama](https://ollama.com) runtime, discovers which models are
pulled, and routes tasks to a **zero-cost** local model when one fits — otherwise
it falls back gracefully to a cloud provider. Local inference costs `$0` per
token, so routing Haiku-class work locally is the framework's primary lever for
long-term cost reduction.

This skill implements **Phase 1 (architecture/detection)** and **Phase 2
(minimal Ollama integration)** of COST-004. Phases for `llama.cpp`, Apple MLX,
and NVIDIA CUDA remain future work.

## API

### `LocalModelRuntime`

```python
from scripts.local_model_runtime import LocalModelRuntime

rt = LocalModelRuntime()            # host from $OLLAMA_HOST or localhost:11434
```

Constructor args:
- `host` (str, optional): Ollama base URL. Defaults to `$OLLAMA_HOST` or
  `http://localhost:11434`.
- `providers_yaml` (Path, optional): path to `src/config/providers.yaml`
  (the zero-cost `ollama` model catalogue + cloud fallback rates).
- `http_get_json` (callable, optional): injectable JSON fetcher (takes a full
  URL). Defaults to a `urllib`-based fetcher — **no third-party dependencies**.
  Injecting a fake makes the runtime fully testable offline.
- `timeout` (float): HTTP timeout for the default fetcher (seconds).

#### `is_available() -> bool`
True when a local Ollama answers on `/api/tags`.

#### `list_models() -> list[LocalModel]`
Models currently pulled locally, each with `name`, `family`, `size_gb`,
`parameter_size`, `quality_rank`, and `cost_per_1m` (always `0.0`).

#### `select_model(task_type="general", constraints=None) -> LocalModel | None`
Best-fit local model for a task. `constraints` supports `min_quality` (int,
0–100). Returns `None` when nothing is available or the quality floor can't be
met locally.

#### `route(task_type, input_tokens=0, output_tokens=0, constraints=None, allow_cloud_fallback=True) -> RoutingDecision`
Decide local vs cloud. Returns a `RoutingDecision` with `provider`, `model`,
`estimated_cost` (`0.0` for local; computed from `providers.yaml` rates for
cloud), `used_fallback`, `local_available`, `reason`, and `candidates`.
`constraints` may set `min_quality`, `cloud_provider`, and `cloud_model`. With
`allow_cloud_fallback=False`, raises `LocalModelUnavailableError` when no local
model fits.

#### `estimate_savings(cloud_provider, cloud_model, input_tokens, output_tokens) -> float`
USD saved by serving a task locally (`$0`) versus the named cloud model.

## CLI

```bash
python scripts/local_model_runtime.py status
python scripts/local_model_runtime.py list
python scripts/local_model_runtime.py route --task-type code_review \
    --input-tokens 4000 --output-tokens 1500 --min-quality 75
```

## Routing heuristic

- **Task → family preference:** code tasks prefer `codellama`, then
  `llama3.1`/`llama3`; general/doc tasks prefer `llama3.1` > `llama3` >
  `mistral` > `phi3`.
- **Quality ranks** are conservative per-family scores (`llama3.1`=85 …
  `phi3`=65; unknown families default to 60).
- **Fallback** triggers when Ollama is unreachable, no preferred/known model is
  pulled, or the best local model is below the requested `min_quality`.

## Testing

```bash
python3 -m pytest tests/test_local_model_runtime.py -q
```

30 tests, fully offline (HTTP layer mocked). No live Ollama required.
