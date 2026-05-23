# TTS Research — High-Quality Models, Voice Cloning & Personality Voices

## Executive Summary

**For your MacBook (Intel CPU, limited GPU):** Recommend **Kokoro (82M params)** or **Kyutai Pocket TTS (100M params)** as primary models. Both run efficiently on CPU with real-time performance.

**For custom Builder/Samantha voices:** Use **XTTS-v2** or **OpenVoice** for voice cloning from 6-30 second audio samples.

**For personality/accent control:** **Fish Audio S2 Pro** or **Mistral Voxtral TTS** support natural-language prosody control (e.g., `[whisper]`, `[excited]`, `[accent: British]`).

---

## Part 1: High-Quality Models (MacBook Optimized)

### Tier 1: Recommended for Local Deployment

| Model | Parameters | Speed | Quality | Voice Clone | Personality |
|-------|-----------|-------|---------|-------------|------------|
| **Kokoro** | 82M | RTF 0.03 (10s in 0.3s) | ⭐⭐⭐⭐ | No | Limited |
| **Kyutai Pocket TTS** | 100M | Real-time CPU | ⭐⭐⭐⭐ | No | Limited |
| **CosyVoice2-0.5B** | 500M | Ultra-low latency | ⭐⭐⭐⭐ | Yes (lite) | Limited |

**Why:** All run comfortably on Intel CPU without GPU. Kokoro has **44% win rate on TTS Arena V2** (beats competitors in head-to-head tests).

### Tier 2: If You Have GPU Available

| Model | Parameters | Speed | Quality | Voice Clone | Personality |
|-------|-----------|-------|---------|-------------|------------|
| **Voxtral TTS** | ~1.5B | 90ms first-audio | ⭐⭐⭐⭐⭐ | Yes | Yes (emotion control) |
| **Fish Audio S2 Pro** | 4B | Fast | ⭐⭐⭐⭐⭐ | Yes | Yes (open-ended prosody) |
| **XTTS-v2 (Coqui)** | ~1B | Real-time | ⭐⭐⭐⭐ | Yes | Limited |
| **OpenVoice** | ~1B | Real-time | ⭐⭐⭐⭐ | Yes (advanced) | Yes (emotion, accent, rhythm) |

**Why:** Better quality but require GPU for fast inference. OpenVoice has **granular control over style** (emotion, accent, rhythm, pauses, intonation).

### Tier 3: Highest Quality (Not MacBook-Friendly)

| Model | Use Case |
|-------|----------|
| **Higgs Audio V2** | Top trending on HF; 10M hours training; expressive multi-speaker |
| **VibeVoice** | Long-form (90 min); multi-speaker dialogue |
| **Dia2** | Dialogue-focused; multi-speaker conversations |

**Issue:** Too large for local MacBook. Consider cloud API instead.

---

## Part 2: Voice Cloning — Custom Builder/Samantha Voices

### Best Options for Your Use Case

**XTTS-v2 (Coqui) — Recommended**
- **Input:** Just 6-second audio sample + text
- **No fine-tuning required**
- **Language support:** Multilingual
- **MacBook:** Runs on CPU (slower) or GPU (fast)
- **Setup:** `pip install TTS` + load model from HuggingFace
- **Quality:** ⭐⭐⭐⭐

**OpenVoice — Advanced Option**
- **Input:** Short audio reference (varies)
- **Granular control:** Emotion, accent, rhythm, pauses, intonation
- **Quality:** ⭐⭐⭐⭐⭐ (best for personality)
- **MacBook:** Can run, but slow on CPU

**Fish Audio S2 Pro**
- **Input:** 10-30 second reference
- **Special feature:** Open-ended prosody via text descriptions
  - `[whisper in small voice]` — Whisper effect
  - `[pitch up]` — Raise pitch
  - `[excited and fast]` — Emotion + speed
- **Languages:** 80+
- **MacBook:** Requires GPU for reasonable speed

**Qwen3-TTS — Practical Option**
- **Input:** Reference audio + transcript
- **Language:** Chinese + English
- **Easy integration:** Straightforward API
- **MacBook:** Good CPU performance

### Workflow: Creating Custom Builder/Samantha Voices

```bash
# 1. Collect reference audio
#    - Find a 6-30 second clip of Builder (deep male) voice
#    - Find a 6-30 second clip of Samantha (female) voice
#    - Trim silence, normalize audio

# 2. Clone voice with XTTS-v2
from TTS.api import TTS
tts = TTS(model_name="tts_models/multilingual/multi-speaker/xtts_v2")
tts.speaker_wav = "builder_reference.wav"
tts.tts("Your message here", language="en")

# 3. Deploy to voice-notify.sh
#    Replace macOS 'say' calls with local TTS inference
```

---

## Part 3: Personality & Character Voices

### What's Possible Now (2026)

**Emotion & Prosody Control:**
- Mistral **Voxtral TTS:** Supports emotion-steering for lifelike interactions
  - Capture: accent, inflections, intonations, disfluencies
  - Control: neutral or emotive, casual or formal, natural or robotic
  - Latency: 90ms to first audio (excellent)

**Fish Audio S2 Pro — Open-Ended Prosody**
```
Example descriptions:
  "Excited and energetic"
  "Whisper in a small voice"
  "Sad, slow, dramatic"
  "British accent, formal"
  "Southern drawl, casual"
```
Works with any natural language description at specific word positions.

**OpenVoice — Style Control**
- Capture from reference: emotion, accent, rhythm, pauses, intonation
- Apply to new text with same speaker's style
- Best for consistent character voices

### Popular Culture Character Voices

**Available Platforms (2026):**
- **FakeYou:** 2,000+ characters (Donald Trump, Elsa, Hulk, SpongeBob, Mickey, Shrek)
- **Vidnoz AI:** Celebrity voices, character presets
- **ElevenLabs:** Character voice library

**Legal Note:** California, Tennessee, and EU have laws protecting voice as "personality right." Using celebrity voices without consent may carry legal risks.

**Practical Alternative:** Clone your own voice or record personality-inflected phrases as reference audio, then use XTTS-v2/OpenVoice to generalize to new text.

### Accent & Speech Mannerisms

**Achievable with Modern Models:**

| Feature | Model | How |
|---------|-------|-----|
| British/Southern/Scottish accent | Fish Audio S2 Pro, OpenVoice | Text description or reference voice |
| Whisper, excitement, sadness | Voxtral TTS, OpenVoice | Emotion control parameter |
| Pauses, rhythm, disfluencies | OpenVoice, Voxtral TTS | Captured from reference audio |
| Speech pattern quirks | XTTS-v2 + training | Clone reference with quirks |

---

## Recommendation for agentic-engineers

### Phase 1: Launch Quickly (This Week)
**Use:** Kokoro (82M) + macOS `say` (current setup)
- ✅ Fast, lightweight, good quality
- ✅ No new dependencies
- ✅ Already configured with Builder + Samantha voices

### Phase 2: Add Local TTS (Next 2-4 Weeks)
**Use:** XTTS-v2 (voice cloning)
1. **Record reference audio:** 6-second clips of ideal "Builder" and "Samantha" voices
   - Can use existing voice actors, YouTubers, or your own voice
2. **Clone voices:** XTTS-v2 from HuggingFace
3. **Integrate with voice-notify.sh:** Replace `say` calls with local TTS inference
4. **Test on automation jobs:** Verify quality, latency, accent

### Phase 3: Add Personality (4-8 Weeks)
**Use:** OpenVoice or Fish Audio S2 Pro
- Add emotion/accent control to Builder and Samantha personas
- Example: Builder gets "confident, commanding" tone; Samantha gets "warm, empathetic" tone
- Use text descriptions to tweak emotion per message

### Phase 4: Custom Character Voices (Optional)
**If you want personality-driven alerts:**
- Create distinct personas for each agent
- TokenAdvisor: "data analyst" personality (precise, factual)
- Model Engineer: "strategist" personality (thoughtful, recommendations)
- A/B Testing: "scientist" personality (objective, statistical)
- Daily Summary: "reporter" personality (engaging, summary-focused)

---

## Installation Paths

### Option A: XTTS-v2 (Recommended for MacBook)
```bash
pip install TTS torch torchaudio

# Download model
from TTS.api import TTS
tts = TTS(model_name="tts_models/multilingual/multi-speaker/xtts_v2", gpu=False)

# Use speaker from reference
tts.speaker_wav = "builder_reference.wav"
wav = tts.tts("Message here", language="en", speaker_wav="builder_reference.wav")
```

### Option B: Kokoro (Simplest)
```bash
pip install kokoro-onnx

from kokoro import Kokoro
kokoro = Kokoro()
audio = kokoro.synthesize("Your message", voice="af_nova")  # or bf_emma, am_adam, etc.
```

### Option C: Fish Audio S2 Pro (Best Prosody)
```bash
# Via HuggingFace Transformers
from transformers import AutoProcessor, AutoModel

processor = AutoProcessor.from_pretrained("fishaudio/fish-speech-1.5")
model = AutoModel.from_pretrained("fishaudio/fish-speech-1.5")

# Supports [excited], [whisper], [British accent], etc.
```

---

## Next Steps

1. **This week:** Test Kokoro locally on your MacBook
   ```bash
   pip install kokoro-onnx
   # Run demo to compare with macOS say
   ```

2. **Next week:** Record 6-second reference clips
   - Find or record your ideal "Builder" voice (deep, confident male)
   - Find or record your ideal "Samantha" voice (warm, intelligent female)

3. **Following week:** Clone voices with XTTS-v2
   - Test quality vs. current macOS `say`
   - Benchmark latency on your MacBook

4. **Iterate:** Refine based on real-world usage in automation jobs

---

## Sources & References

- [HuggingFace Text-to-Speech Models](https://huggingface.co/models?pipeline_tag=text-to-speech)
- [The Best Open-Source TTS Models in 2026](https://www.bentoml.com/blog/exploring-the-world-of-open-source-text-to-speech-models)
- [TTS Arena: Community Benchmarking](https://huggingface.co/blog/arena-tts)
- [XTTS-v2 (Coqui)](https://huggingface.co/coqui/XTTS-v2)
- [OpenVoice](https://huggingface.co/myshell-ai/OpenVoice)
- [Qwen3-TTS](https://huggingface.co/Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice)
- [Fish Audio S2 Pro](https://fish.audio/)
- [Mistral Voxtral TTS](https://mistral.ai/news/voxtral-tts/)
- [Text to Speech with Emotion: Creator's Guide 2026](https://www.camb.ai/blog-post/text-to-speech-with-emotion)
- [Lightweight TTS for Edge Devices](https://www.siliconflow.com/articles/en/best-lightweight-TTS-models-for-chatbots)
