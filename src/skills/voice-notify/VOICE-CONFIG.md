---
name: voice-config
description: Voice notification configuration for agentic-engineers
---

## Selected Voice Palette

### Primary Alert Voice
**Daniel** — Professional male voice, neutral tone
- Used for: Main agent status updates, critical alerts
- Agents: TokenAdvisor, Model Engineer, A/B Testing, Daily Summary
- Rationale: Natural/realistic human voice, trustworthy, clear information delivery

### Secondary Voice
**Samantha** — High-quality intelligent female voice
- Used for: Detailed updates, recommendations, follow-ups
- Agents: Can rotate or emphasize specific information
- Rationale: Natural/realistic human voice, professional, high-quality

### Not Selected
- ❌ Builder (deep but less natural)
- ❌ Victoria (professional but not as engaging)
- ❌ Alex (too casual for operational alerts)

## Voice Assignment by Agent

| Agent | Primary | Secondary |
|-------|---------|-----------|
| TokenAdvisor | Daniel | Samantha (for escalation) |
| Model Engineer | Daniel | Samantha (for recommendations) |
| A/B Testing | Daniel | Samantha (for results) |
| Daily Summary | Daniel | Samantha (for details) |
| Metrics ETL | Silent | N/A |

## Implementation

Update .cron files to use:
```bash
bash voice-notify.sh "message" --voice Daniel    # Default male
# or
bash voice-notify.sh "message" --voice Samantha  # Secondary female
```

## Voice Testing

Test any voice interactively:
```bash
bash skills/voice-notify/scripts/voice-notify.sh "Your message" --voice Daniel
bash skills/voice-notify/scripts/voice-notify.sh "Your message" --voice Samantha
```

## Future TTS Enhancement

When llama.cpp TTS models are added:
- `llama-builder` — Custom Builder voice (high quality)
- `llama-female` — Custom female voice from recordings
