#!/bin/bash
# Voice notification wrapper — calls system TTS (say/espeak) with consistent settings

set -euo pipefail

MESSAGE="${1:-}"
VOICE="Daniel"  # Preferred: natural/realistic human voice (male)
VOLUME="0.7"    # 70% volume per user preference
SILENT=false

# Parse options
while [[ $# -gt 1 ]]; do
    case "$2" in
        --voice)
            VOICE="$3"
            shift 2
            ;;
        --volume)
            VOLUME="$3"
            shift 2
            ;;
        --silent)
            SILENT=true
            shift
            ;;
        *)
            shift
            ;;
    esac
done

if [ -z "$MESSAGE" ]; then
    echo "Usage: voice-notify.sh 'message' [--voice VOICE] [--volume LEVEL] [--silent]"
    exit 1
fi

if [ "$SILENT" = true ]; then
    exit 0
fi

# Detect OS and use appropriate TTS
if command -v say &> /dev/null; then
    # macOS: use built-in 'say' command
    say -v "$VOICE" "$MESSAGE" 2>/dev/null || true
elif command -v espeak &> /dev/null; then
    # Linux: use espeak
    espeak -a "$VOLUME" "$MESSAGE" 2>/dev/null || true
else
    # Fallback: silent
    : # Do nothing
fi
