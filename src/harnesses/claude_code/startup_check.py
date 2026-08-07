"""
Startup Verification Script for Claude Code Harness

Auto-runs during harness initialization to perform quick health checks on all
agents. Reports any missing or broken agents and caches results for performance.

Usage:
    from src.harnesses.claude_code.startup_check import StartupChecker
    checker = StartupChecker()
    status = checker.run_check()
    print(f"Startup check: {status}")
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional
from datetime import datetime, timedelta
import hashlib

from src.harnesses.claude_code.agent_verifier import AgentVerifier, CompatibilityReport


class StartupChecker:
    """Performs quick health checks during harness startup."""
    
    def __init__(
        self,
        repo_root: Optional[Path] = None,
        cache_dir: Optional[Path] = None,
        cache_ttl_seconds: int = 3600,
    ) -> None:
        """Initialize the startup checker.
        
        Args:
            repo_root: Path to repository root.
            cache_dir: Directory to store cache files. Defaults to ~/.cache/agentic-engineers/
            cache_ttl_seconds: Cache time-to-live in seconds (default: 1 hour).
        """
        if repo_root is None:
            repo_root = Path.cwd()
        
        self.repo_root = repo_root
        self.verifier = AgentVerifier(repo_root=repo_root)
        
        if cache_dir is None:
            cache_dir = Path.home() / ".cache" / "agentic-engineers"
        
        self.cache_dir = cache_dir
        self.cache_ttl_seconds = cache_ttl_seconds
        self.cache_file = cache_dir / "agent_verification_cache.json"
    
    def _get_cache_key(self) -> str:
        """Get cache key for current agent definitions.
        
        Returns:
            SHA256 hash of agent files.
        """
        return self.verifier.get_verification_cache_key()
    
    def _read_cache(self) -> Optional[dict]:
        """Read cached verification results.
        
        Returns:
            Cached report dict if valid, None otherwise.
        """
        if not self.cache_file.exists():
            return None
        
        try:
            cache_data = json.loads(self.cache_file.read_text(encoding="utf-8"))
            
            # Check cache validity
            timestamp_str = cache_data.get("cached_at")
            if not timestamp_str:
                return None
            
            cached_at = datetime.fromisoformat(timestamp_str)
            age_seconds = (datetime.utcnow() - cached_at).total_seconds()
            
            if age_seconds > self.cache_ttl_seconds:
                return None  # Cache expired
            
            # Verify cache key matches
            if cache_data.get("cache_key") != self._get_cache_key():
                return None  # Cache invalidated by file changes
            
            return cache_data.get("report")
        
        except Exception:
            return None  # Cache read failed
    
    def _write_cache(self, report: CompatibilityReport) -> None:
        """Write verification results to cache.
        
        Args:
            report: CompatibilityReport to cache.
        """
        try:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            
            cache_data = {
                "cached_at": datetime.utcnow().isoformat(),
                "cache_key": self._get_cache_key(),
                "report": report.to_dict(),
            }
            
            self.cache_file.write_text(
                json.dumps(cache_data, indent=2),
                encoding="utf-8",
            )
        except Exception:
            pass  # Silently fail cache writes
    
    def run_check(self, use_cache: bool = True) -> dict[str, bool | str]:
        """Run startup health check.
        
        Args:
            use_cache: Whether to use cached results if valid.
            
        Returns:
            Status dict with keys:
              - success: bool — all agents passed verification
              - agents_checked: int — number of agents verified
              - agents_failed: int — number of failures
              - cache_hit: bool — whether cache was used
              - message: str — human-readable summary
        """
        # Try to use cache
        if use_cache:
            cached_report = self._read_cache()
            if cached_report:
                return self._report_to_status(cached_report, cache_hit=True)
        
        # Run full verification
        report = self.verifier.verify_all_agents()
        self._write_cache(report)
        
        return self._report_to_status(report.to_dict(), cache_hit=False)
    
    def _report_to_status(
        self,
        report_dict: dict,
        cache_hit: bool = False,
    ) -> dict[str, bool | str]:
        """Convert report dict to status dict.
        
        Args:
            report_dict: Report dictionary from CompatibilityReport.to_dict().
            cache_hit: Whether this result came from cache.
            
        Returns:
            Status dictionary.
        """
        total = report_dict.get("total_agents", 0)
        failing = report_dict.get("failing", 0)
        
        success = failing == 0
        
        if success:
            message = f"✅ All {total} agents available and verified"
        else:
            message = f"❌ {failing}/{total} agent(s) failed verification"
        
        if cache_hit:
            message += " (cached)"
        
        return {
            "success": success,
            "agents_checked": total,
            "agents_failed": failing,
            "cache_hit": cache_hit,
            "message": message,
        }
    
    def clear_cache(self) -> None:
        """Clear the verification cache."""
        if self.cache_file.exists():
            self.cache_file.unlink()
    
    def get_quick_status(self) -> str:
        """Get a quick status string (suitable for logs).
        
        Returns:
            One-line status message.
        """
        status = self.run_check(use_cache=True)
        return status["message"]


def initialize_harness_check() -> bool:
    """Initialize harness with agent verification check.
    
    This is called automatically by the Claude Code harness during startup.
    
    Returns:
        True if all agents are available, False if any failures.
    """
    checker = StartupChecker()
    status = checker.run_check()
    
    if not status["success"]:
        print(f"⚠️  Agent startup check failed: {status['message']}")
        return False
    
    return True


def main() -> int:
    """Command-line entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Claude Code harness startup check")
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=None,
        help="Repository root path",
    )
    parser.add_argument(
        "--clear-cache",
        action="store_true",
        help="Clear verification cache and exit",
    )
    
    args = parser.parse_args()
    
    checker = StartupChecker(repo_root=args.repo_root)
    
    if args.clear_cache:
        checker.clear_cache()
        print("✅ Cache cleared")
        return 0
    
    status = checker.run_check()
    print(status["message"])
    
    return 0 if status["success"] else 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
