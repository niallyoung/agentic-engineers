#!/bin/bash
# Interactive voice voter — cycle through ALL voices, wait for y/n on each

set -euo pipefail

VOICE_SCRIPT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/voice-notify.sh"

echo "╔═══════════════════════════════════════════════════════╗"
echo "║      Cycle All Voices — Vote Y/N on Each One         ║"
echo "╚═══════════════════════════════════════════════════════╝"
echo ""
echo "Testing message:"
echo "  \"Model Engineer ready. Route low complexity tasks to Engineer.\""
echo ""
echo "Instructions:"
echo "  y = YES (add to favorites)"
echo "  n = NO (skip)"
echo ""

# All English voices
VOICES=(
    "Albert" "Daniel" "Eddy" "Fred" "Junior" "Ralph" "Reed" "Rocko"
    "Flo" "Grandma" "Karen" "Kathy" "Samantha" "Sandy" "Shelley"
    "Bad News" "Bahh" "Bells" "Boing" "Bubbles" "Cellos" "Good News" "Grandpa" "Jester" "Organ" "Superstar" "Trinoids" "Whisper" "Wobble" "Zarvox"
)

FAVORITES=()
TOTAL=${#VOICES[@]}
COUNT=0

for voice in "${VOICES[@]}"; do
    COUNT=$((COUNT + 1))
    echo ""
    echo "═══════════════════════════════════════════════════════"
    echo "[$COUNT/$TOTAL] 🎤 Testing: $voice"
    echo "───────────────────────────────────────────────────"

    # Play the voice
    bash "$VOICE_SCRIPT" "Model Engineer ready. Route low complexity tasks to Engineer." --voice "$voice" 2>/dev/null

    # Wait for user input
    echo ""
    while true; do
        read -p "Keep this voice? (y/n): " choice
        case "$choice" in
            y|Y)
                echo "✅ Added: $voice"
                FAVORITES+=("$voice")
                break
                ;;
            n|N)
                echo "❌ Skipped"
                break
                ;;
            *)
                echo "Please enter 'y' or 'n'"
                ;;
        esac
    done
done

echo ""
echo "═══════════════════════════════════════════════════════"
echo ""
echo "✅ FINAL SELECTION (${#FAVORITES[@]} voices):"
echo ""

if [ ${#FAVORITES[@]} -eq 0 ]; then
    echo "No voices selected."
    exit 0
fi

for i in "${!FAVORITES[@]}"; do
    num=$((i + 1))
    echo "$num. ${FAVORITES[$i]}"
done

echo ""
echo "Update voice-notify to use these voices:"
for voice in "${FAVORITES[@]}"; do
    echo "  bash voice-notify.sh \"message\" --voice \"$voice\""
done
