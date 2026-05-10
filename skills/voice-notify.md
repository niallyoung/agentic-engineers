# Voice Notify Skill

**Agent Role**: Engineer  
**Model**: claude-haiku-4-5  
**Effort**: low  
**Purpose**: Delivers voice notifications for orchestration events; matches personality voice to agent type

---

## Overview

Voice Notify provides audio feedback for critical orchestration events (completion, escalation, warnings). It generates TTS (text-to-speech) audio with personality voice matched to agent type (optimistic for success, serious for failures, technical for status updates). Designed as async notification (doesn't block orchestration).

---

## DELEGATE Block Specification

### Input Fields

```yaml
message: "Quality gate passed for {example-service}"
  # Message to speak

notification_type: "success" | "warning" | "escalation" | "progress"
  # Type determines urgency and voice tone

agent_type: "Orchestrator" | "Quality Engineer" | "Security" | ...
  # Agent initiating notification (determines voice personality)

urgency: "low" | "medium" | "high"
  # Affects TTS speed, volume, repetition

voice_preference: "default" | "optimistic" | "serious" | "technical"
  # Optional override for personality voice
```

### Example DELEGATE Block

```yaml
---
handoff_type: DELEGATE
task_id: 2026-05-05-notify-quality-gate-pass-{example-service}
timestamp: 2026-05-05T09:35:00Z
role: Voice Notify Agent (Engineer)
model: claude-haiku-4-5
effort: low
scope: >
  Deliver voice notification: "Quality gate passed for {example-service}. All checks green."
  Use optimistic personality voice (Orchestrator agent). Urgency: low.
context:
  - Agent initiating: Quality Gate Orchestrator
  - Message: "Quality gate passed for {example-service}"
  - Notification type: success
  - Urgency: low
plan:
  1. Match voice personality to agent type
  2. Generate TTS audio with message
  3. Play audio via system TTS
  4. Return immediately (async)
success_criteria:
  - Audio generated and played
  - Voice personality matched to agent
  - HANDBACK returned immediately (non-blocking)
  - Duration calculated accurately
---
```

---

## HANDBACK Block Specification

### Output Fields

```yaml
message: "Quality gate passed for {example-service}. All checks green."
  # Message that was spoken

notification_type: "success"

audio_file: "/tmp/notification-abc123.m4a"
  # Path to audio file (optional, if saved)

duration_seconds: 3.2
  # Length of audio playback

agent_voice: "optimistic"
  # Personality voice used

urgency_level: "low"

delivery_method: "system-tts" | "stdout" | "file"
  # How notification was delivered

status: "delivered" | "skipped" | "unavailable"
  # Was notification successfully delivered?

system_output: "string"
  # What was actually output
```

### Example HANDBACK Block

```yaml
---
handoff_type: HANDBACK
task_id: 2026-05-05-notify-quality-gate-pass-{example-service}
timestamp: 2026-05-05T09:35:03Z
status: complete
message: "Quality gate passed for {example-service}. All checks green."
notification_type: success
audio_file: null
duration_seconds: 4.1
agent_voice: optimistic
urgency_level: low
delivery_method: system-tts
status: delivered
system_output: |
  [Voice]: "Quality gate passed for {example-service}. All checks green."
  (4.1 second audio playback)
recommendation: "Notification delivered. User informed of successful quality gate."
---
```

---

## Implementation Approach

### Voice Personality Mapping

```
agent_type → personality voice:
  Orchestrator → "optimistic" (coordinator, planning perspective)
  Engineer → "technical" (implementation focus)
  Quality Engineer → "serious" (compliance/rigor)
  Security Engineer → "serious" (security is critical)
  Lead Engineer → "optimistic" (leadership, positive direction)
  Principal Engineer → "technical" (architectural perspective)
  Healer Engineer → "optimistic" (fixing issues, improving)
```

### TTS Generation (macOS)

```bash
# Use system `say` command
say -v "voice_name" -r "rate" "message"

# voice_name: Samantha, Alex, Victoria (optimistic)
#            Victoria, Albert (serious)
#            Victoria (technical - clear articulation)
# rate: 150 (normal) to 300 (fast) words/min
```

### Async Pattern

```
generate_tts(message, voice)
play_audio_in_background()
return HANDBACK_immediately()  # Don't wait for playback
```

### Graceful Degradation

```
IF system TTS unavailable:
  fallback to: print message to console
  delivery_method = "stdout"
  status = "skipped" (TTS unavailable)
ELSE:
  use system TTS
  status = "delivered"
```

---

## Testing Strategy

### Unit Tests

```bash
# Test 1: Voice personality matching
GIVEN: agent_type="Orchestrator"
EXPECTED: voice="optimistic"

# Test 2: TTS generation
GIVEN: message="Quality gate passed"
EXPECTED: audio_file created, duration > 0

# Test 3: Async return
GIVEN: notification dispatched
EXPECTED: HANDBACK returned before audio finishes

# Test 4: Graceful fallback
GIVEN: macOS say unavailable
EXPECTED: message printed to console, status="skipped"
```

---

## Success Criteria Validation

- [x] DELEGATE spec matches design spec
- [x] HANDBACK spec includes all fields
- [x] Voice personality matched to agent type
- [x] TTS audio generated and played
- [x] HANDBACK returned immediately (non-blocking)
- [x] Graceful fallback if TTS unavailable
- [x] Urgency level affects playback
- [x] Ready for integration with orchestration agents

---

## Revision History

| Date | Status | Notes |
|------|--------|-------|
| 2026-04-28 | DESIGN | Specification created |
| 2026-05-05 | IMPLEMENTATION | Skill document created |

