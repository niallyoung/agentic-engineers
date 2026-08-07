"""Claude Code harness integration for agentic-engineers framework."""

from src.harnesses.claude_code.agent_verifier import (
    AgentVerifier,
    AgentDefinition,
    VerificationResult,
    CompatibilityReport,
)
from src.harnesses.claude_code.startup_check import StartupChecker, initialize_harness_check
from src.harnesses.claude_code.idle_loop import ClaudeIdleLoop, IdleLoopConfig

__version__ = "1.0.0"
__all__ = [
    "AgentVerifier",
    "AgentDefinition",
    "VerificationResult",
    "CompatibilityReport",
    "StartupChecker",
    "initialize_harness_check",
    "ClaudeIdleLoop",
    "IdleLoopConfig",
]
