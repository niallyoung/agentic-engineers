#!/bin/bash
# Setup llama.cpp TTS for voice notifications
# Installs TTS engine for high-quality voice synthesis

set -euo pipefail

echo "╔════════════════════════════════════════════════════════════╗"
echo "║       ERS Voice Notifications — TTS Setup                 ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

TTS_DIR="$HOME/.local/share/{service-name}"
TTS_SERVER_PORT=8000

# Check if llama.cpp is already installed
if command -v llama-cli &> /dev/null; then
    echo "✅ llama.cpp is already installed"
    LLAMA_PATH=$(which llama-cli)
else
    echo "📦 Installing llama.cpp..."
    if [ "$(uname)" = "Darwin" ]; then
        # macOS: use Homebrew
        if command -v brew &> /dev/null; then
            brew install llama.cpp
        else
            echo "⚠️  Homebrew not found. Please install llama.cpp manually:"
            echo "   https://github.com/ggerganov/llama.cpp"
            exit 1
        fi
    else
        echo "⚠️  Automatic installation not supported on this platform."
        echo "   Please install llama.cpp manually: https://github.com/ggerganov/llama.cpp"
        exit 1
    fi
fi

echo ""
echo "Setting up TTS models..."

# Create TTS directory
mkdir -p "$TTS_DIR"

# For now, we'll use system TTS (macOS say, Linux espeak)
# llama.cpp TTS setup would go here when needed

echo ""
echo "═════════════════════════════════════════════════════════════"
echo ""
echo "Voice Notifications are configured to use:"
echo "  • macOS: Built-in 'say' command (voices: Builder, Victoria, Samantha, Alex)"
echo "  • Linux: espeak (if installed)"
echo ""
echo "To enable high-quality llama.cpp TTS:"
echo "  1. Download a TTS model: https://huggingface.co/models?library=llama.cpp&search=tts"
echo "  2. Place model in: $TTS_DIR/"
echo "  3. Update voice-notify.sh to use --voice llama-builder"
echo ""
echo "Current voice options:"
echo "  say -v '?' | grep -i voice  # List available voices on macOS"
echo ""
echo "Test voice notification:"
echo "  ./agentic-agents/scripts/voice-notify.sh 'Testing voice notification.' --volume 0.7"
echo ""
