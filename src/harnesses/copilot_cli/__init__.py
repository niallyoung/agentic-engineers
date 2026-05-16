"""
Copilot CLI harness utilities.

Provides streaming output support for render-copilot.sh.
"""
from .streaming import StreamingRenderer, StreamEvent

__all__ = ["StreamingRenderer", "StreamEvent"]
