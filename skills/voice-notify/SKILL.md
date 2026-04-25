---
name: voice-notify
description: Voice notification integration layer providing consistent, brief audio alerts for lifecycle events across all automation agents. Use to emit status alerts via macOS say command or Linux espeak with configurable voices.
license: Proprietary
compatibility: macOS (say command) or Linux (espeak). Designed for agentic-engineers framework.
metadata:
  author: agentic-engineers
  version: "1.0"
  category: orchestration
  role: orchestrator
---

## Overview

Provides unified voice notifications for all automation agents, using short, consistent status phrases that agents can recognize and respond to.

**What it does:**
1. Emits brief audio alerts for agent completion
2. Uses consistent status phrases across all tools
3. Integrates with macOS `say` command or Linux `espeak`
4. Configurable voices and volume
5. Optional voice customization via llama.cpp TTS

## Invocation

### Basic Notification
```bash
scripts/voice-notify.sh "TokenAdvisor complete. Distribution healthy."
```

### With Voice Selection
```bash
scripts/voice-notify.sh "Model Engineer ready" --voice Builder --volume 0.7
```

### Silent Mode
```bash
scripts/voice-notify.sh "Message" --silent
```

## Voices

**Available (macOS):**
- `Daniel` (preferred) — Professional male voice, neutral tone
- `Samantha` (preferred) — High-quality female voice, intelligent
- `Builder` (default) — Deep, confident male voice
- `Victoria` — Professional female voice
- `Alex` — Casual male voice

**Future (llama.cpp TTS):**
- `llama-builder` — TTS-rendered Builder voice
- `llama-female` — TTS-rendered female voice (high quality)

## Phrase Design

All voice messages follow consistent format:

```
"[Tool name] [status]. [Metric change] [Direction] [Percentage]."
```

**Status phrases (reusable):**
- `"complete"` — Task finished, results ready
- `"in progress"` — Task started, monitoring active
- `"monitoring"` — Ongoing collection/analysis
- `"significant result"` — Statistical threshold met
- `"early stop: [reason]"` — Experiment concluded early
- `"ready"` — Analysis complete, ready for action

**Metric phrases:**
- `"Distribution healthy"` — All metrics OK
- `"Engineer over budget by X%"` — Role exceeds threshold
- `"Quality down X%, cost saved X%"` — Tradeoff summary
- `"Variant winning, p=0.03"` — A/B test result

## Configuration

System volume is controlled by the user, not by voice-notify.

Manual volume adjustment:
```bash
# macOS
osascript -e 'get volume settings'
osascript -e 'set volume output volume 70'
```

## Integration

Called by all automation agents:
- TokenAdvisor — Status + cost/quality summary
- Model Engineer — Routing recommendations
- A/B Testing Monitor — Test results and conclusions
- Metrics ETL — Silent (no voice)
- Daily Email Summary — Activity count

## Scripts

- `voice-notify.sh` — Main TTS wrapper
- `setup-tts.sh` — TTS configuration and environment setup
