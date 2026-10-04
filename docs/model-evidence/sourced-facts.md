# Sourced model facts

Retrieved 2026-10-03 from Anthropic's official documentation. Every figure below was read from
the page named in the Source column on that date; nothing is inferred or taken from memory.
`unknown` means the official page does not state it. Prices are USD per million tokens (MTok).
Machine-readable copies live in `config/models.yaml` under `models.<id>.facts` and are validated
by `python3 scripts/models.py check`.

Primary sources:

- Model pages: `https://platform.claude.com/docs/en/models/<slug>/overview` (per-model)
- Models overview: `https://platform.claude.com/docs/en/about-claude/models/overview`
- Pricing: `https://platform.claude.com/docs/en/about-claude/pricing`

| Model | Input | Output | Cache read | 5m write | 1h write | Context | Max output | Reliable cutoff | Source (model page slug) |
|---|---|---|---|---|---|---|---|---|---|
| claude-haiku-4.5 | $1 | $5 | $0.10 | $1.25 | $2 | 200K | 64K | Feb 2025 | overview + pricing (no per-model page fetched) |
| claude-sonnet-4.5 | $3 | $15 | $0.30 | $3.75 | $6 | 200K | 64K | Jan 2025 | sonnet-4-5 |
| claude-sonnet-4.6 | $3 | $15 | $0.30 | $3.75 | $6 | 1M | 128K | Aug 2025 | sonnet-4-6 |
| claude-sonnet-5 | $2 | $10 | $0.20 | $2.50 | $4 | 1M | 128K | Jan 2026 | sonnet-5 |
| claude-sonnet-5.5 | $2 | $10 | $0.20 | $2.50 | $4 | 1M | 128K | Jun 2026 | sonnet-5-5 |
| claude-opus-4.6 | $5 | $25 | $0.50 | $6.25 | $10 | 1M | 128K | May 2025 | opus-4-6 |
| claude-opus-4.7 | $5 | $25 | $0.50 | $6.25 | $10 | 1M | 128K | Jan 2026 | opus-4-7 |
| claude-opus-4.8 | $5 | $25 | $0.50 | $6.25 | $10 | 1M | 128K | Jan 2026 | opus-4-8 |
| claude-opus-5 | $5 | $25 | $0.50 | $6.25 | $10 | 1M | 128K | May 2026 | opus-5 |
| claude-opus-5.5 | $4 | $20 | $0.20 | $5 | $8 | 1M | 128K | Jun 2026 | opus-5-5 |
| claude-fable-5 | $10 | $50 | $1 | $12.50 | $20 | 1M | 128K | Jan 2026 | fable-5 |

The pages print "1M tokens" / "200K tokens" / "128K tokens" / "64K tokens". The registry stores these as
1,000,000 / 200,000 / 128,000 / 64,000. The page does not say whether K is 1000 or 1024; the Claude
CLI's own `modelUsage` for claude-sonnet-5-5 reports `contextWindow: 1000000` and
`maxOutputTokens: 128000`, consistent with the decimal reading (a CLI report, not an official doc).

## Tokenizer (official statement, pricing page)

"Claude 4.7 and later models and Claude Mythos Preview use a newer tokenizer ... approximately 30%
more tokens for the same text. The exact increase depends on the content and workload shape.
Claude Sonnet 4.6 and earlier models use the previous tokenizer."
The pages fetched say nothing about a tokenizer change between Sonnet 5 and Sonnet 5.5, or between
Opus 5 and Opus 5.5: unknown from official text, so it is measured in
`sonnet-opus-5-5-measurement.md`.

## Differences from what the repo previously asserted

| Previous claim | Where | Official page says |
|---|---|---|
| Sonnet 5 "Same $3/$15 per MTok as Sonnet 4.6" | SPEC.md before b88ed9e; `config/orchestration.yaml` comment | Sonnet 5 is $2/$10. Pricing page footnote: the $2/$10 was introductory pricing, is now standard, and the scheduled rise to $3/$15 on 2026-09-01 will not occur. |
| Opus 4.6 max output 64K | SPEC.md before b88ed9e | 128K |
| "Sonnet 5.5 price and tokenizer are not asserted" | SPEC-2026-010 changelog | Price $2/$10 (cache read $0.20), 1M context, 128K output, cutoff Jun 2026 (sonnet-5-5 page) |
| Opus 5.5 unverified | registry | $4/$20, cache read $0.20 (0.05x), 1M / 128K, cutoff Jun 2026, released 2026-09-22 |

Other official facts worth recording: Sonnet 4.5 is marked **Deprecated** (retires 2026-11-30) on its
model page while the registry status is `supported`; the API ID shown there is the dated
`claude-sonnet-4-5-20250929` (alias `claude-sonnet-4-5`). Haiku 4.5's dated API ID is
`claude-haiku-4-5-20251001` (alias `claude-haiku-4-5`).

Pin retirement commitments from the models overview: Opus 5.5 not sooner than 2027-09-22, Sonnet 5.5
not sooner than 2027-09-28, Haiku 4.5 not sooner than 2026-10-15.
