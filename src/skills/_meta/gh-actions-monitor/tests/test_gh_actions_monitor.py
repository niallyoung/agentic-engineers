#!/usr/bin/env python3
"""
Tests for gh_actions_monitor.py

Tests adaptive polling intervals, log analysis, and report generation.
"""

import pytest
import json
import time
from unittest.mock import patch, MagicMock
from pathlib import Path
import tempfile
import sys

# Add scripts directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from gh_actions_monitor import GHActionsMonitor

class TestGHActionsMonitor:
    
    def test_adaptive_interval_active(self):
        """Test 30s interval when status changing."""
        monitor = GHActionsMonitor("123", "org/repo", "/tmp/test.md")
        monitor.status_unchanged_count = 0
        
        interval = monitor.get_adaptive_interval()
        assert interval == 30, "Active phase should use 30s interval"
    
    def test_adaptive_interval_stabilized(self):
        """Test 60s interval when status unchanged."""
        monitor = GHActionsMonitor("123", "org/repo", "/tmp/test.md")
        monitor.status_unchanged_count = 5  # 5+ unchanged checks = stabilized
        
        interval = monitor.get_adaptive_interval()
        assert interval == 60, "Stabilized phase should use 60s interval"
    
    def test_analyze_logs_failures(self):
        """Test extraction of failure patterns from logs."""
        monitor = GHActionsMonitor("123", "org/repo", "/tmp/test.md")
        
        logs = """
        ✗ Test 1 FAILED
        ✗ Test 2 FAILED
        Some other line
        ERROR: Connection timeout
        """
        
        analysis = monitor.analyze_logs(logs)
        
        assert analysis["total_failures"] == 2, "Should find 2 failures"
        assert analysis["total_errors"] == 1, "Should find 1 error"
        assert len(analysis["failures"]) == 2
        assert len(analysis["errors"]) == 1
    
    def test_analyze_logs_empty(self):
        """Test log analysis with no failures."""
        monitor = GHActionsMonitor("123", "org/repo", "/tmp/test.md")
        
        logs = "All tests passed successfully"
        
        analysis = monitor.analyze_logs(logs)
        
        assert analysis["total_failures"] == 0
        assert analysis["total_errors"] == 0
        assert analysis["failures"] == []
        assert analysis["errors"] == []
    
    @patch('subprocess.run')
    def test_get_run_status_success(self, mock_run):
        """Test successful status retrieval."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps({
            "status": "in_progress",
            "conclusion": None
        })
        mock_run.return_value = mock_result
        
        monitor = GHActionsMonitor("123", "org/repo", "/tmp/test.md")
        status = monitor.get_run_status()
        
        assert status["status"] == "in_progress"
        assert status["conclusion"] is None
    
    @patch('subprocess.run')
    def test_get_run_status_error(self, mock_run):
        """Test error handling in status retrieval."""
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_run.return_value = mock_result
        
        monitor = GHActionsMonitor("123", "org/repo", "/tmp/test.md")
        status = monitor.get_run_status()
        
        assert status is None
    
    def test_report_generation(self):
        """Test that report file is created with correct structure."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_file = Path(tmpdir) / "report.md"
            
            monitor = GHActionsMonitor("123", "org/repo", str(output_file))
            
            # Mock the poll and extract methods
            with patch.object(monitor, 'poll_until_complete') as mock_poll, \
                 patch.object(monitor, 'extract_logs') as mock_logs, \
                 patch.object(monitor, 'get_pr_comments') as mock_comments:
                
                mock_poll.return_value = {
                    "status": {"status": "completed", "conclusion": "success"},
                    "poll_count": 5,
                    "elapsed_seconds": 150,
                    "avg_interval": 30
                }
                mock_logs.return_value = "Test passed"
                mock_comments.return_value = []
                
                report = monitor.generate_report()
            
            # Verify report was written
            assert output_file.exists(), "Report file should exist"
            content = output_file.read_text()
            assert "Run Summary" in content
            assert "Log Analysis" in content
            assert "PR Review Comments" in content
            assert "150 seconds" in content

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
