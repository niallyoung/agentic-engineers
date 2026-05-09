---
name: voice-selection
description: Final voice selection from comprehensive macOS voice voting
---

# Voice Selection Results

## Final Favorites (10 voices selected)

### Male Voices (3)
- **Daniel** — Professional, neutral tone
- **Fred** — Clear, reliable voice
- **Ralph** — Distinctive, strong voice

### Female Voices (2)
- **Karen** — Professional, warm tone
- **Samantha** — High-quality, intelligent voice

### Novelty/Fun Voices (5)
- **Bad News** — Ominous, dramatic delivery
- **Cellos** — Musical, unique tone
- **Good News** — Upbeat, positive delivery
- **Organ** — Mechanical, distinctive sound
- **Zarvox** — Futuristic, unique quality

## Voice Assignment by Agent

| Agent | Primary Voice | Secondary Voice | Notes |
|-------|--------------|-----------------|-------|
| TokenAdvisor | Daniel | Ralph | Cost/distribution alerts |
| Model Engineer | Daniel | Fred | Routing recommendations |
| A/B Testing | Daniel | Ralph | Experiment results |
| Daily Summary | Samantha | Karen | Activity reporting |
| Metrics ETL | Silent | N/A | No voice notifications |

## Optional: Fun Variants

For special cases or personality-driven alerts:
- **Success alerts:** Good News
- **Warning alerts:** Bad News
- **Special emphasis:** Cellos, Organ, Zarvox

## Implementation

Update .cron files to rotate through selection:
```bash
# Primary (professional)
bash voice-notify.sh "message" --voice Daniel

# Secondary (alternative professional)
bash voice-notify.sh "message" --voice Samantha

# Special events (fun)
bash voice-notify.sh "message" --voice "Good News"
```

## Test Command

Test any selected voice:
```bash
bash agentic-engineers/skills/voice-notify/scripts/voice-notify.sh "Your message" --voice Daniel
```
