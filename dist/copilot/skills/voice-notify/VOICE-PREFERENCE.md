---
name: voice-preference
description: Voice selection preferences for future TTS and voice model decisions
---

# Voice Preference Profile

## Identified Preference Pattern

User prefers **ONE OF TWO CATEGORIES**:

### Category A: Robotic/Melodic/Synthetic Voices
Distinctive, character-driven, musical quality. Preferred for special alerts and personality.

**Selected Favorites:**
- Bad News (ominous, dramatic)
- Cellos (musical, instrument-like)
- Good News (upbeat, synthetic)
- Organ (mechanical, unique)
- Zarvox (futuristic, alien-like)

**Why:** Immediately recognizable, no ambiguity, entertaining, personality-driven

### Category B: Natural/Realistic Human Voices
High-quality, professional, authentic human speech. Preferred for routine operations and professional communication.

**Selected Favorites:**
- Daniel (professional male, neutral)
- Fred (clear male, reliable)
- Ralph (distinctive male, strong)
- Karen (professional female, warm)
- Samantha (intelligent female, high-quality)

**Why:** Trustworthy, clear information delivery, professional tone, no novelty distraction

## What Was NOT Selected

**Middle-ground casual/quirky voices:** Excluded (Albert, Eddy, Junior, Reed, Rocko, Flo, Grandma, Kathy, Sandy, Shelley, Bahh, Bells, Boing, Bubbles, Grandpa, Jester, Superstar, Trinoids, Whisper, Wobble)

Reason: Neither clearly robotic/melodic NOR natural/realistic. Uncanny valley territory.

## Application to Future Voice Work

### For TTS Model Selection
- **Prefer models that deliver:** Robotic/synthetic OR natural/human (not in-between)
- **Avoid models that:** Sound vaguely human but unconvincing, uncanny valley quality

### For Voice Cloning
- **Robotic route:** Use speech synthesis models with clear prosody control
  - Fish Audio S2 Pro (open-ended descriptions: `[excited]`, `[robotic]`)
  - Kokoro (clear, synthetic quality)
  - Kyutai (clean, digital tone)
  
- **Human route:** Use high-fidelity cloning models
  - XTTS-v2 (preserves speaker characteristics)
  - OpenVoice (captures natural speech patterns)
  - Voxtral TTS (emotion control while maintaining naturalism)

### For Agent Personalities
- **TokenAdvisor:** Natural/realistic (data analyst personality)
- **Model Engineer:** Natural/realistic (strategist personality)
- **A/B Testing:** Could use either (scientist personality — robotic for objectivity, or natural for credibility)
- **Daily Summary:** Natural/realistic (reporter personality)
- **Special alerts:** Robotic/melodic for emphasis

## Technical Implications

When evaluating TTS models:
- ✅ Robotic/synthetic: Rate high on prosody control, distinctiveness, clarity
- ✅ Natural/human: Rate high on speaker similarity, emotional nuance, authenticity
- ❌ Avoid: Uncanny valley (almost human but clearly artificial)

Document this preference in TTS model evaluation rubric.
