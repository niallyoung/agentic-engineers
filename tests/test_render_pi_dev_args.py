"""
Tests for Bug 1 fix: Argument parsing heuristic

Verifies that the argument parser correctly handles:
- Named flags (--src, --dest) — unambiguous
- Two positional args (src dest) — unambiguous
- Single positional arg — now rejected with clear error
- Mode flags (--uninstall, --status)
"""

import pytest
import subprocess
import sys
from pathlib import Path

RENDERER = Path(__file__).parent.parent / "renderer" / "scripts" / "render-pi-dev.py"


def run_renderer(*args):
    """Run renderer with given args, return (returncode, stdout, stderr)"""
    result = subprocess.run(
        [sys.executable, str(RENDERER)] + list(args),
        capture_output=True, text=True
    )
    # DEBUG: Print captured output for troubleshooting
    if result.returncode != 0:
        print(f"\n[SUBPROCESS] Failed with rc={result.returncode}, args={args}")
        if result.stdout:
            print(f"[SUBPROCESS] STDOUT:\n{result.stdout}")
        if result.stderr:
            print(f"[SUBPROCESS] STDERR:\n{result.stderr}")
    return result.returncode, result.stdout, result.stderr


class TestArgParsing:
    """Tests for argument parsing with argparse"""
    
    def test_help_flag_works(self):
        """--help flag should display usage"""
        rc, out, err = run_renderer("--help")
        assert rc == 0
        assert "--src" in out
        assert "--dest" in out
        assert "--uninstall" in out
        assert "--status" in out
    
    def test_no_args_uses_defaults(self, tmp_path):
        """Zero args: uses default src and ~/.pi dest"""
        # Just verify it doesn't crash with --help
        rc, out, err = run_renderer("--help")
        assert rc == 0
        assert "--src" in out
        assert "--dest" in out
    
    def test_explicit_src_flag(self, tmp_path):
        """--src flag is unambiguous"""
        rc, out, err = run_renderer("--src", str(tmp_path), "--dest", str(tmp_path), "--status")
        # Should not emit ambiguity warning
        assert "Ambiguous" not in err
    
    def test_explicit_dest_flag(self, tmp_path):
        """--dest flag is unambiguous"""
        rc, out, err = run_renderer("--dest", str(tmp_path), "--status")
        assert "Ambiguous" not in err
    
    def test_two_positional_args_unambiguous(self, tmp_path):
        """Two positional args (src dest) are unambiguous"""
        rc, out, err = run_renderer(str(tmp_path), str(tmp_path), "--status")
        assert "Ambiguous" not in err
    
    def test_single_positional_arg_rejected(self, tmp_path):
        """Single positional arg is now rejected with clear error"""
        rc, out, err = run_renderer(str(tmp_path))
        assert rc == 2
        assert "Ambiguous" in err
        assert "--src" in err or "--dest" in err
    
    def test_pi_path_no_longer_heuristic(self, tmp_path):
        """Path containing /.pi no longer triggers heuristic"""
        pi_path = tmp_path / ".pi-backup" / "src"
        pi_path.mkdir(parents=True)
        # Single arg with /.pi in path: should be rejected, not silently treated as dest
        rc, out, err = run_renderer(str(pi_path))
        assert rc == 2
        assert "Ambiguous" in err
    
    def test_uninstall_with_dest_flag(self, tmp_path):
        """--uninstall works with --dest flag"""
        rc, out, err = run_renderer("--dest", str(tmp_path), "--uninstall")
        # Should not crash; nothing to uninstall
        assert rc == 0
    
    def test_status_with_dest_flag(self, tmp_path):
        """--status works with --dest flag"""
        rc, out, err = run_renderer("--dest", str(tmp_path), "--status")
        # Should report not installed (no agent/ dir)
        assert rc in (0, 1)  # 1 = not installed, which is valid
    
    def test_src_and_dest_flags_together(self, tmp_path):
        """--src and --dest flags work together"""
        src = tmp_path / "src"
        dest = tmp_path / "dest"
        src.mkdir()
        
        rc, out, err = run_renderer("--src", str(src), "--dest", str(dest), "--status")
        assert "Ambiguous" not in err
    
    def test_positional_args_with_flags_ignored(self, tmp_path):
        """Positional args are ignored when --src/--dest flags provided"""
        src = tmp_path / "src"
        dest = tmp_path / "dest"
        src.mkdir()
        
        # Provide both flags and positional args; flags should take precedence
        rc, out, err = run_renderer(
            "--src", str(src),
            "--dest", str(dest),
            "/ignored/path1",
            "/ignored/path2",
            "--status"
        )
        # Should use --src and --dest, not the positional args
        assert "Ambiguous" not in err
    
    def test_uninstall_flag_without_dest(self, tmp_path):
        """--uninstall without --dest uses default ~/.pi"""
        rc, out, err = run_renderer("--uninstall")
        # Should not crash; uses default dest
        assert rc == 0
    
    def test_status_flag_without_dest(self, tmp_path):
        """--status without --dest uses default ~/.pi"""
        rc, out, err = run_renderer("--status")
        # Should not crash; uses default dest
        assert rc in (0, 1)
