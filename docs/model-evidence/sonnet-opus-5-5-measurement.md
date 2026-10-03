# Sonnet 5 vs 5.5 and Opus 5 vs 5.5: spot measurement

Measured 2026-10-03 with the real `claude` CLI. This is a spot measurement (n = 2 per cell, two
fixed prompts, one effort level), not a benchmark. It answers two narrow questions: does the
tokenizer differ on identical input, and what did these runs cost. It does not rank quality.

## Method

- Same CLI, same account, same host, interleaved runs (prompt, then model, repeated twice).
- Per run: `claude -p "<prompt>" --model <id> --effort medium --tools "" --system-prompt "You are a concise engineering assistant." --max-turns 1 --no-session-persistence --disable-slash-commands --output-format json`
  from an empty scratch directory. Effort fixed at `medium` for all models because the defaults
  differ (Opus 5.5 `medium`, Opus 5 `high`, per the official model pages).
- Prompts: `ok` (2 characters, calibrates the fixed per-request overhead the CLI adds),
  `delegate` (736 characters, a routing-style DELEGATE-construction request), `review`
  (3,747 characters, about 1.4k prompt tokens: the real `_evidence_problems` function from
  `scripts/models.py` with a code-review instruction).
- Input tokens are `input_tokens + cache_creation_input_tokens + cache_read_input_tokens` from
  the JSON `usage` (the CLI splits input across those fields depending on cache state).
  "Prompt tokens" = total input minus the `ok` run's total for the same model, which removes the
  CLI's fixed overhead and leaves the tokens attributable to the prompt text.
- Cost columns: **list cost** = total input x list input price + output x list output price, with
  prices from `docs/model-evidence/sourced-facts.md` and no cache discount, so cache state does
  not distort the comparison. The CLI's own `total_cost_usd` is in the raw file but is not used for
  ratios: run 1 of a cell writes the 1h cache (2x input price) and run 2 reads it (0.1x), which
  swings it by about 3x between identical runs.
- Raw per-run numbers: `docs/model-evidence/measurement-raw-summary.json` (and the CLI JSON
  files, which are not committed). All 30 runs returned `is_error: false`.

## Tokenizer on identical input

Prompt tokens (total input minus the `ok` run), identical in both repetitions of every cell:

| Model | `delegate` | `review` | `ok` total (fixed overhead) |
|---|---|---|---|
| claude-sonnet-4-6 | 177 | 1,119 | 1,776 |
| claude-sonnet-5 | 262 | 1,399 | 2,492 |
| claude-sonnet-5-5 | 262 | 1,399 | 2,435 |
| claude-opus-5 | 262 | 1,399 | 2,422 |
| claude-opus-5-5 | 262 | 1,399 | 2,429 |

- 5.5 vs 5 (both families): ratio 1.000 on both prompts. No tokenizer difference observed. All four
  models give identical prompt-token counts, so Sonnet and Opus 5/5.5 share one tokenizer here.
- Sonnet 5 vs Sonnet 4.6: 1.48x (`delegate`, small input) and 1.25x (`review`). The official pricing
  page says "Claude 4.7 and later" use a tokenizer that produces "approximately 30% more tokens";
  the review prompt (1.25x) is consistent with that, the short prompt is a small-number effect.
- The fixed overhead differs a little by model (2,422 to 2,492; 1,776 for 4.6). It is whatever the
  CLI and API add around the request; its composition was not inspected.

## Output tokens, list cost and latency (mean of 2 runs)

Thinking tokens are included in output tokens. Ratios are 5.5 / 5.

| Prompt | Model | Output tokens | of which thinking | List cost (USD) | Wall (s) |
|---|---|---|---|---|---|
| delegate | sonnet-5 | 731 | 0 | 0.01282 | 13.3 |
| delegate | sonnet-5-5 | 954 | 0 | 0.01493 | 12.2 |
| delegate | opus-5 | 1,218 | 0 | 0.04388 | 20.7 |
| delegate | opus-5-5 | 1,015 (run 2 only, see note) | 37 | 0.03106 | 15.4 |
| review | sonnet-5 | 2,022 | 1,376 / 1,771 | 0.02801 | 29.0 |
| review | sonnet-5-5 | 486 | 0 / 0 | 0.01253 | 10.0 |
| review | opus-5 | 1,652 | 1,013 / 1,399 | 0.06039 | 27.1 |
| review | opus-5-5 | 1,242 | 750 / 713 | 0.04015 | 18.5 |

| Ratio (5.5 / 5) | delegate | review |
|---|---|---|
| Sonnet output tokens | 1.31 | 0.24 |
| Sonnet list cost | 1.16 | 0.45 |
| Opus output tokens | 0.83 | 0.75 |
| Opus list cost | 0.71 | 0.66 |

Note on opus-5-5 `delegate` run 1: the CLI reported 1,437 total input tokens, below its own
fixed overhead of 2,429, which cannot be right for that request (run 2 reported 2,691). It is
treated as a usage-reporting anomaly and excluded from the opus-5-5 `delegate` row.

## What this does and does not show

- Input side: 5.5 does not tokenize these prompts differently from 5. Prices are equal for Sonnet
  ($2/$10) and 20% lower for Opus 5.5 ($4/$20 vs $5/$25), so input cost per identical text is
  equal (Sonnet) or 0.8x (Opus).
- Output side: output tokens moved a lot and in both directions (Sonnet `delegate` +31%, Sonnet
  `review` -76%; Opus -17% and -25%). The Sonnet `review` change is mostly thinking: Sonnet 5 used
  1,376 and 1,771 thinking tokens, Sonnet 5.5 used 0 in both runs at the same `--effort medium`.
  Sonnet 4.6 on the same prompt used 2,306 and 4,033, so thinking volume varies widely between
  runs of the same model too.
- Variance: n = 2, and the two runs of a cell differ by up to 1.5x in output tokens (Sonnet 4.6
  `review` 2,547 vs 4,365). Differences smaller than about 1.5x in output tokens are within noise
  here. The Sonnet `review` (0.24x) and Opus `delegate` cost (0.71x) gaps exceed it; the others do
  not clearly.
- Limits: two prompts, one effort level, no quality grading, one host and day, CLI-reported usage.
  The CLI adds its own fixed overhead (about 2.4k tokens even with `--tools ""`); real orchestration
  sessions carry far more context, so absolute dollar figures here do not transfer, only the ratios
  of the same prompt across models do.

## Budget consequence (config/orchestration.yaml)

The old note said Sonnet 5 "keeps Sonnet 4.6's $3/$15 per MTok yet emits ~30% more tokens", so the
Sonnet roles would burn budget about 30% faster. The official pricing page states Sonnet 5 and 5.5
are $2/$10 (the $3/$15 step-up was cancelled), so the premise was wrong. Using only measured
tokens and sourced prices for identical input text, Sonnet 4.6 to Sonnet 5.5:

- Input cost ratio = token ratio x price ratio = (1.25 to 1.48) x (2/3) = 0.83 to 0.99.
- Output cost cannot be scaled from these runs (output tokens are behaviour-dependent and noisy).

No ratio here justifies raising or lowering `session_usd` / `daily_usd`, and 5 vs 5.5 shows no
tokenizer difference, so the budgets are left unchanged (5.00 / 20.00) and the note records why.
