# Installation & Setup

agentic-engineers is now a standalone repository. Install it to `~/.agents/` for automatic detection by Claude CLI and future integrations.

## Quick Install

```bash
git clone git@github.com:{your-org}/agentic-engineers.git ~/git/ers/agentic-engineers
cd ~/git/ers/agentic-engineers
make install
```

This installs the framework to `~/.agents/agentic-engineers/`.

## Shell Integration

Add to `~/.zshrc` or `~/.bashrc`:

```bash
# Initialize agentic-engineers at session start
if [ -f "$HOME/.agents/agentic-engineers/setup/session-init.sh" ]; then
    source "$HOME/.agents/agentic-engineers/setup/session-init.sh"
fi
```

Then reload your shell:
```bash
source ~/.zshrc  # or ~/.bashrc
```

## Claude Code Integration

Claude Code will automatically discover `~/.agents/agentic-engineers/` when you:
1. Reference `SYSTEM.md` for bootstrap configuration
2. Load the framework via `setup/copilot-instructions.md`
3. Initialize the session with `setup/session-init.sh`

## Copilot CLI Integration

Add to your Copilot instructions or context:

```markdown
Framework location: ~/.agents/agentic-engineers/
Bootstrap: Read ~/.agents/agentic-engineers/SYSTEM.md
Initialize: bash ~/.agents/agentic-engineers/setup/session-init.sh
```

## Verification

Check installation:
```bash
ls ~/.agents/agentic-engineers/SYSTEM.md
# Should print: ~/.agents/agentic-engineers/SYSTEM.md
```

Initialize session tracking:
```bash
bash ~/.agents/agentic-engineers/setup/session-init.sh
```

## Uninstallation

Remove the framework:
```bash
make clean
```

Or manually:
```bash
rm -rf ~/.agents/agentic-engineers
```

## Development

To develop or modify the framework:

```bash
cd ~/git/ers/agentic-engineers
# Make changes
git commit -m "message"
git push origin main

# Reinstall to ~/.agents/
make install
```

## Support

For issues or questions, reference:
- `SYSTEM.md` — Framework overview and structure
- `README.md` — Detailed documentation
- `setup/STARTUP-INTEGRATION.md` — Integration details
