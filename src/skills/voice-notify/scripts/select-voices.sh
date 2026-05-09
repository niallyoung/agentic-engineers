#!/bin/bash
# Interactive voice selector — test all macOS voices and vote for favorites

set -euo pipefail

VOICE_SCRIPT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/voice-notify.sh"

echo "╔═══════════════════════════════════════════════════════╗"
echo "║        macOS Voice Selector — Vote for Favorites      ║"
echo "╚═══════════════════════════════════════════════════════╝"
echo ""
echo "Testing: \"Model Engineer ready. Route low complexity tasks to Engineer.\""
echo ""
echo "Vote for each voice:"
echo "  y = YES (add to favorites)"
echo "  n = NO (skip)"
echo "  s = SKIP (go to next)"
echo ""

# Get all English voices
VOICES=$(say -v '?' | grep -E "en_US|en_GB|en_AU" | awk '{print $1}' | sort -u)

FAVORITES=()

for voice in $VOICES; do
    echo "───────────────────────────────────────────────────"
    echo "🎤 Testing: $voice"

    # Play the voice
    bash "$VOICE_SCRIPT" "Model Engineer ready. Route low complexity tasks to Engineer." --voice "$voice" 2>/dev/null

    # Ask for feedback
    echo ""
    read -p "Keep this voice? (y/n/skip): " choice

    case "$choice" in
        y|Y)
            echo "✅ Added: $voice"
            FAVORITES+=("$voice")
            ;;
        n|N)
            echo "❌ Skipped"
            ;;
        *)
            echo "⏭️  Next"
            ;;
    esac

    echo ""
done

echo "═══════════════════════════════════════════════════════"
echo ""
echo "✅ Final Selection:"
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
echo "Update voice-notify.sh to use:"
for voice in "${FAVORITES[@]}"; do
    echo "  bash voice-notify.sh \"message\" --voice $voice"
done
