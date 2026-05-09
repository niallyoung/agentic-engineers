# TTS Research & Implementation Plan

**Status: ⏸️ PAUSED** (started 2026-04-25)

---

## Phase: High-Quality TTS Voice Implementation

### Overview

Research and implement high-quality text-to-speech models for custom voice synthesis. Build on existing voice preference (robotic/melodic OR natural/realistic human) to replace/enhance macOS `say` command with local TTS inference.

### Prerequisites Completed ✅

- [x] Voice preference pattern identified (robotic/melodic vs. natural/realistic)
- [x] 10 voices selected from macOS options
- [x] Voice selection documented (VOICE-SELECTION.md)
- [x] Voice preference documented (VOICE-PREFERENCE.md)
- [x] Architecture clarified (voice-notify for interactive console only)
- [x] Cron jobs configured (no voice alerts, logs/reports instead)

---

## Phase 1: Research & Model Selection (2-3 days)

### Task 1.1: Evaluate Lightweight TTS Models for MacBook

**Goal:** Identify 3-5 models that run efficiently on Intel CPU/limited GPU

**Models to evaluate:**
- [ ] **Kokoro** (82M params)
  - Setup: `pip install kokoro-onnx`
  - Test on MacBook for latency/quality
  - Rating: quality vs. speed vs. resource use
  
- [ ] **Kyutai Pocket TTS** (100M params)
  - Released Jan 2026
  - CPU-native performance
  - Real-time capability
  
- [ ] **CosyVoice2-0.5B** (500M params)
  - Lightweight variant
  - Voice cloning capability
  - Ultra-low latency
  
- [ ] **XTTS-v2 (Coqui)** (~1B params, optional GPU)
  - Voice cloning: 6-second reference sample
  - Multilingual support
  - Test CPU vs. GPU performance
  
- [ ] **OpenVoice** (~1B params)
  - Advanced: granular style control
  - Emotion, accent, rhythm customization
  - If GPU available, premium quality

**Deliverable:** Comparison table (model, params, speed, quality, voice-clone capability, resource usage)

### Task 1.2: Evaluate Voice Cloning Capabilities

**Goal:** Identify best approach to create custom Builder/Samantha voices from recordings

**Research:**
- [ ] XTTS-v2: Record 6-second reference → clone workflow
- [ ] OpenVoice: Reference audio + style transfer
- [ ] Fish Audio S2 Pro: 10-30 second samples, no fine-tuning needed
- [ ] Qwen3-TTS: Reference audio + transcript workflow

**Deliverable:** Voice cloning workflow for each model (input requirements, quality, limitations)

### Task 1.3: Research Personality Control Options

**Goal:** How to add emotion, accent, speech mannerisms to synthesized voices

**Models with personality control:**
- [ ] **Fish Audio S2 Pro:** Open-ended prosody (`[whisper]`, `[excited]`, `[British accent]`)
- [ ] **Mistral Voxtral TTS:** Emotion steering, captures accents/inflections
- [ ] **OpenVoice:** Style extraction from reference audio

**Deliverable:** Personality control matrix (which model supports what features)

### Task 1.4: Popular Culture Voice Implementation (Optional)

**Goal:** Assess feasibility of character voices for special alerts

**Research:**
- [ ] FakeYou: 2000+ characters available
- [ ] Vidnoz AI: Celebrity voice library
- [ ] ElevenLabs: Character voices
- [ ] Legal considerations: California, Tennessee, EU protect voice as "personality right"

**Deliverable:** Assessment of character voice options + legal constraints

---

## Phase 2: Local Deployment (1-2 weeks)

### Task 2.1: Set Up Kokoro Locally

- [ ] Install: `pip install kokoro-onnx`
- [ ] Benchmark: latency on Intel MacBook CPU
- [ ] Compare quality: Kokoro vs. macOS `say`
- [ ] Create test script: `test-kokoro.sh`

**Deliverable:** Kokoro running locally with latency/quality benchmarks

### Task 2.2: Implement XTTS-v2 Voice Cloning

- [ ] Record 6-second reference clips
  - [ ] Builder voice (deep male) sample
  - [ ] Samantha voice (female) sample
- [ ] Clone using XTTS-v2
- [ ] Test synthesized voice quality
- [ ] Create cloning workflow script

**Deliverable:** Custom Builder + Samantha voices from XTTS-v2

### Task 2.3: Integrate with voice-notify.sh

- [ ] Update `voice-notify.sh` to detect local TTS availability
- [ ] Fallback: macOS `say` if TTS unavailable
- [ ] Priority: Kokoro → OpenVoice → XTTS-v2 → macOS `say`
- [ ] Test with all 10 selected voices

**Deliverable:** Enhanced voice-notify.sh with TTS fallback chain

---

## Phase 3: Personality & Polish (2-3 weeks)

### Task 3.1: Add Emotion/Accent Control

- [ ] Integrate OpenVoice for style customization
- [ ] OR Fish Audio S2 Pro for open-ended prosody
- [ ] Define agent personalities:
  - [ ] TokenAdvisor: analytical, precise
  - [ ] Model Engineer: thoughtful, strategic
  - [ ] A/B Testing: objective, scientific
  - [ ] Daily Summary: engaging, reporter-like

**Deliverable:** Personality-driven voice variations per agent

### Task 3.2: Optimize for MacBook Performance

- [ ] Profile TTS inference time
- [ ] Optimize model loading
- [ ] Cache synthesized voices (if repeated)
- [ ] Measure system resource usage during synthesis

**Deliverable:** Performance-optimized TTS pipeline

### Task 3.3: Documentation & User Guide

- [ ] Document: Model selection, installation, usage
- [ ] Troubleshooting guide
- [ ] Voice preference application guide
- [ ] Upgrade path (Kokoro → OpenVoice when GPU available)

**Deliverable:** TTS-SETUP.md + implementation guide

---

## Phase 4: Integration & Testing (1 week)

### Task 4.1: Manual Agent Invocation with TTS

- [ ] Test with TokenAdvisor manual run
- [ ] Test with Model Engineer manual run
- [ ] Test with A/B Testing manual run
- [ ] Verify voice quality and latency

### Task 4.2: Interactive Console Experience

- [ ] Verify voice-notify works during live agent work
- [ ] Test with all 10 selected voices
- [ ] Verify personality variations work correctly

### Task 4.3: Regression Testing

- [ ] Confirm macOS `say` still works as fallback
- [ ] Verify cron jobs still output to logs (voice-notify not in cron)
- [ ] Confirm no impact on automation framework

**Deliverable:** All tests passing, TTS ready for live use

---

## Research References

**Models:**
- [HuggingFace TTS Models](https://huggingface.co/models?pipeline_tag=text-to-speech)
- [TTS Arena Benchmarking](https://huggingface.co/blog/arena-tts)
- [XTTS-v2 (Coqui)](https://huggingface.co/coqui/XTTS-v2)
- [OpenVoice](https://huggingface.co/myshell-ai/OpenVoice)

**Lightweight Models:**
- [Kokoro](https://github.com/thewh1teagle/kokoro-onnx)
- [Kyutai Pocket TTS](https://kyutai.org/tts)
- [Fish Audio S2 Pro](https://fish.audio/)
- [Mistral Voxtral TTS](https://mistral.ai/news/voxtral-tts/)

**Voice Preferences Applied:**
- Category A (Robotic/Melodic): Bad News, Cellos, Good News, Organ, Zarvox
- Category B (Natural/Realistic): Daniel, Fred, Ralph, Karen, Samantha

---

## Notes

- **Voice Preference:** Filter all TTS models through preference (avoid uncanny valley)
- **MacBook Constraints:** Optimize for CPU, no GPU assumption
- **Architecture:** Keep voice-notify for interactive use, not cron jobs
- **Fallback:** Always maintain macOS `say` as safety net
- **Testing:** Test on actual MacBook before declaring "ready"

---

**Resume when:** Ready to implement high-quality local TTS
**Last Updated:** 2026-04-25
