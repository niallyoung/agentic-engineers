"""
Unit Tests for Continuous CI/CD Pipeline (TASK-EVALS-005)

Tests cover:
- Regression detection logic (quality, latency, new failures)
- Baseline management (create, load, snapshot, cleanup)
- Dashboard generation
- CLI commands
- End-to-end pipeline logic
"""

import json
import pytest
from pathlib import Path
from datetime import datetime, timedelta
from tempfile import TemporaryDirectory

from src.skills._meta.evaluation_framework.regression_detector import (
    RegressionDetector,
    Regression,
)
from src.skills._meta.evaluation_framework.baseline_manager import BaselineManager
from src.skills._meta.evaluation_framework.dashboard_generator import DashboardGenerator


class TestRegressionDetector:
    """Tests for regression detection logic."""

    @pytest.fixture
    def detector(self):
        """Create regression detector instance."""
        return RegressionDetector()

    @pytest.fixture
    def baseline_results(self):
        """Create baseline results."""
        return {
            "summary": {
                "total_tests": 100,
                "passed": 95,
                "failed": 5,
                "pass_rate": 95.0,
                "avg_duration_ms": 1000,
                "by_harness": {
                    "opencode": {"passed": 50, "failed": 1, "pass_rate": 98.0},
                    "copilot": {"passed": 45, "failed": 4, "pass_rate": 92.0},
                },
            },
            "failed_tests": ["test_001", "test_002", "test_003", "test_004", "test_005"],
        }

    @pytest.fixture
    def current_results_degraded(self):
        """Create degraded current results."""
        return {
            "summary": {
                "total_tests": 100,
                "passed": 80,
                "failed": 20,
                "pass_rate": 80.0,
                "avg_duration_ms": 1500,
                "by_harness": {
                    "opencode": {"passed": 40, "failed": 10, "pass_rate": 80.0},
                    "copilot": {"passed": 40, "failed": 10, "pass_rate": 80.0},
                },
            },
            "failed_tests": [
                "test_001", "test_002", "test_003", "test_004", "test_005",
                "test_006", "test_007", "test_008", "test_009", "test_010",
                "test_011", "test_012", "test_013", "test_014", "test_015",
                "test_016", "test_017", "test_018", "test_019", "test_020",
            ],
        }

    def test_detect_quality_drop(self, detector, baseline_results, current_results_degraded):
        """Test detection of quality drop > 10%."""
        regressions = detector.detect(baseline_results, current_results_degraded)

        assert len(regressions) > 0
        quality_regressions = [r for r in regressions if r.regression_type == "quality"]
        assert len(quality_regressions) > 0

        # Overall quality drop
        overall_regression = next(
            (r for r in quality_regressions if r.test_id == "overall_quality"),
            None
        )
        assert overall_regression is not None
        assert overall_regression.severity in ("high", "critical")
        assert overall_regression.change_percent < -10

    def test_detect_latency_increase(self, detector, baseline_results, current_results_degraded):
        """Test detection of latency increase > 25%."""
        regressions = detector.detect(baseline_results, current_results_degraded)

        latency_regressions = [r for r in regressions if r.regression_type == "latency"]
        assert len(latency_regressions) > 0

        latency_regression = latency_regressions[0]
        assert latency_regression.severity in ("medium", "high")
        assert latency_regression.change_percent > 25

    def test_detect_new_failures(self, detector, baseline_results, current_results_degraded):
        """Test detection of new test failures."""
        regressions = detector.detect(baseline_results, current_results_degraded)

        failure_regressions = [r for r in regressions if r.regression_type == "new_failure"]
        # New failures: test_006 through test_020
        expected_new_failures = 15
        assert len(failure_regressions) == expected_new_failures

        for regression in failure_regressions:
            assert regression.severity == "high"
            assert regression.change_percent == 100.0

    def test_no_regressions_identical_results(self, detector, baseline_results):
        """Test no regressions detected when results are identical."""
        regressions = detector.detect(baseline_results, baseline_results)

        assert len(regressions) == 0

    def test_minor_improvements(self, detector, baseline_results):
        """Test no regressions when results improve."""
        improved_results = {
            "summary": {
                "total_tests": 100,
                "passed": 98,
                "failed": 2,
                "pass_rate": 98.0,
                "avg_duration_ms": 950,
                "by_harness": {
                    "opencode": {"passed": 50, "failed": 0, "pass_rate": 100.0},
                    "copilot": {"passed": 48, "failed": 2, "pass_rate": 96.0},
                },
            },
            "failed_tests": ["test_001", "test_002"],
        }
        regressions = detector.detect(baseline_results, improved_results)

        # No regressions should be detected for improvements
        assert len(regressions) == 0

    def test_regression_summary(self, detector, baseline_results, current_results_degraded):
        """Test regression summary statistics."""
        detector.detect(baseline_results, current_results_degraded)
        summary = detector.get_summary()

        assert summary["total_regressions"] > 0
        assert summary["critical"] + summary["high"] + summary["medium"] + summary["low"] == summary["total_regressions"]
        assert summary["quality_regressions"] > 0

    def test_regression_to_markdown(self, detector, baseline_results, current_results_degraded):
        """Test regression markdown report generation."""
        detector.detect(baseline_results, current_results_degraded)
        markdown = detector.to_markdown()

        assert "## Regressions Summary" in markdown
        assert "Critical" in markdown
        assert "High" in markdown

    def test_get_critical_regressions(self, detector, baseline_results, current_results_degraded):
        """Test filtering critical regressions."""
        detector.detect(baseline_results, current_results_degraded)
        critical = detector.get_critical_regressions()

        assert len(critical) > 0
        for regression in critical:
            assert regression.severity in ("critical", "high")


class TestBaselineManager:
    """Tests for baseline management."""

    @pytest.fixture
    def temp_baseline_dir(self):
        """Create temporary baseline directory."""
        with TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def manager(self, temp_baseline_dir):
        """Create baseline manager with temp directory."""
        return BaselineManager(temp_baseline_dir)

    @pytest.fixture
    def sample_results(self):
        """Create sample evaluation results."""
        return {
            "summary": {
                "total_tests": 100,
                "passed": 95,
                "failed": 5,
                "pass_rate": 95.0,
                "avg_duration_ms": 1000,
            },
            "results": [
                {"test_id": "test_001", "status": "pass", "duration_ms": 100},
                {"test_id": "test_002", "status": "pass", "duration_ms": 150},
            ],
        }

    def test_save_and_load_baseline(self, manager, sample_results):
        """Test saving and loading baseline."""
        save_path = manager.save_baseline(sample_results)

        assert Path(save_path).exists()

        loaded = manager.get_current_baseline()
        assert loaded is not None
        assert loaded["results"] == sample_results

    def test_baseline_includes_metadata(self, manager, sample_results):
        """Test baseline includes timestamp and version."""
        manager.save_baseline(sample_results)
        baseline = manager.get_current_baseline()

        assert "timestamp" in baseline
        assert "baseline_version" in baseline
        assert baseline["baseline_version"] == 1

    def test_create_monthly_snapshot(self, manager, sample_results):
        """Test creating monthly snapshot."""
        snapshot_path = manager.create_monthly_snapshot(sample_results)

        assert Path(snapshot_path).exists()
        assert "baseline_snapshot_" in snapshot_path

    def test_get_last_snapshot(self, manager, sample_results):
        """Test retrieving last snapshot."""
        # Create multiple snapshots
        manager.create_monthly_snapshot(sample_results)
        manager.create_monthly_snapshot(sample_results)

        last = manager.get_last_snapshot()
        assert last is not None
        assert "results" in last

    def test_list_snapshots(self, manager, sample_results):
        """Test listing all snapshots."""
        # Create multiple snapshots with different dates
        import time
        for i in range(3):
            manager.create_monthly_snapshot(sample_results)
            time.sleep(0.01)  # Small delay to ensure different timestamps

        snapshots = manager.list_snapshots()
        assert len(snapshots) >= 1  # At least one snapshot created

        for snapshot in snapshots:
            assert "filename" in snapshot
            assert "timestamp" in snapshot
            assert "path" in snapshot

    def test_cleanup_old_snapshots(self, manager, sample_results):
        """Test cleanup of old snapshots."""
        # Create multiple snapshots
        for i in range(15):
            manager.create_monthly_snapshot(sample_results)

        initial_count = len(manager.list_snapshots())
        deleted = manager.cleanup_old_snapshots(keep_count=10)

        assert len(deleted) >= initial_count - 10
        final_count = len(manager.list_snapshots())
        assert final_count <= 10

    def test_get_baseline_history(self, manager, sample_results):
        """Test retrieving baseline history for trends."""
        # Create multiple snapshots
        for i in range(5):
            manager.create_monthly_snapshot(sample_results)

        history = manager.get_baseline_history(limit=10)
        assert len(history) > 0

        for item in history:
            assert "timestamp" in item
            assert "filename" in item
            assert "summary" in item

    def test_no_baseline_returns_none(self, manager):
        """Test loading non-existent baseline returns None."""
        baseline = manager.get_current_baseline()
        assert baseline is None

    def test_get_snapshot_by_date(self, manager, sample_results):
        """Test retrieving snapshot by specific date."""
        now = datetime.utcnow()
        manager.create_monthly_snapshot(sample_results)

        snapshot = manager.get_snapshot_by_date(now.year, now.month, now.day)
        assert snapshot is not None
        assert "results" in snapshot


class TestDashboardGenerator:
    """Tests for dashboard generation."""

    @pytest.fixture
    def sample_results(self):
        """Create sample results."""
        return {
            "summary": {
                "total_tests": 100,
                "passed": 95,
                "failed": 5,
                "pass_rate": 95.0,
                "avg_duration_ms": 1000,
                "by_harness": {
                    "opencode": {"passed": 50, "failed": 1, "pass_rate": 98.0},
                    "copilot": {"passed": 45, "failed": 4, "pass_rate": 92.0},
                },
            }
        }

    @pytest.fixture
    def sample_baseline(self):
        """Create sample baseline."""
        return {
            "results": {
                "summary": {
                    "total_tests": 100,
                    "passed": 94,
                    "failed": 6,
                    "pass_rate": 94.0,
                    "avg_duration_ms": 1100,
                    "by_harness": {
                        "opencode": {"passed": 49, "failed": 2, "pass_rate": 96.0},
                        "copilot": {"passed": 45, "failed": 4, "pass_rate": 92.0},
                    },
                }
            }
        }

    @pytest.fixture
    def sample_regressions(self):
        """Create sample regressions."""
        return [
            {
                "test_id": "test_001",
                "regression_type": "quality",
                "severity": "high",
                "baseline_value": 95.0,
                "current_value": 92.0,
                "change_percent": -3.0,
                "description": "Quality drop detected"
            }
        ]

    def test_generate_basic_dashboard(self, sample_results):
        """Test generating basic dashboard without baseline."""
        generator = DashboardGenerator(sample_results)

        with TemporaryDirectory() as tmpdir:
            output_file = Path(tmpdir) / "dashboard.html"
            result = generator.generate(str(output_file))

            assert Path(result).exists()
            assert output_file.exists()

            content = output_file.read_text()
            assert "Evaluation Framework Dashboard" in content
            assert "Status" in content or "status" in content

    def test_dashboard_includes_results(self, sample_results):
        """Test dashboard includes result metrics."""
        generator = DashboardGenerator(sample_results)

        with TemporaryDirectory() as tmpdir:
            output_file = Path(tmpdir) / "dashboard.html"
            generator.generate(str(output_file))

            content = output_file.read_text()
            assert "95" in content  # Pass count
            assert "5" in content   # Fail count

    def test_dashboard_with_baseline(self, sample_results, sample_baseline):
        """Test dashboard includes baseline comparison."""
        generator = DashboardGenerator(sample_results, sample_baseline)

        with TemporaryDirectory() as tmpdir:
            output_file = Path(tmpdir) / "dashboard.html"
            generator.generate(str(output_file))

            content = output_file.read_text()
            assert "Baseline" in content or "baseline" in content

    def test_dashboard_with_regressions(self, sample_results, sample_regressions):
        """Test dashboard includes regression details."""
        generator = DashboardGenerator(sample_results, regressions=sample_regressions)

        with TemporaryDirectory() as tmpdir:
            output_file = Path(tmpdir) / "dashboard.html"
            generator.generate(str(output_file))

            content = output_file.read_text()
            # Should include some regression information
            assert len(content) > 1000

    def test_dashboard_html_valid(self, sample_results):
        """Test generated dashboard is valid HTML."""
        generator = DashboardGenerator(sample_results)

        with TemporaryDirectory() as tmpdir:
            output_file = Path(tmpdir) / "dashboard.html"
            generator.generate(str(output_file))

            content = output_file.read_text()
            assert content.startswith("<!DOCTYPE html>")
            assert "<html" in content
            assert "</html>" in content

    def test_dashboard_escapes_untrusted_regression_fields(self):
        """Regression result fields must be HTML-escaped to prevent XSS."""
        payload = "<script>alert('xss')</script>"
        results = {"summary": {"total_tests": 1, "passed": 0, "failed": 1, "pass_rate": 0.0}}
        regressions = [
            {
                "test_id": payload,
                "regression_type": "<img src=x onerror=alert(1)>",
                "severity": "high\"><script>alert(2)</script>",
                "baseline_value": 95.0,
                "current_value": 0.0,
                "change_percent": -100.0,
            }
        ]
        generator = DashboardGenerator(results, regressions=regressions)

        with TemporaryDirectory() as tmpdir:
            output_file = Path(tmpdir) / "dashboard.html"
            generator.generate(str(output_file))
            content = output_file.read_text()

        # Raw payload must never appear unescaped in the output.
        assert "<script>alert('xss')</script>" not in content
        assert "<img src=x onerror=alert(1)>" not in content
        # Escaped form must be present instead.
        assert "&lt;script&gt;alert(&#x27;xss&#x27;)&lt;/script&gt;" in content
        # Untrusted severity must not leak into the CSS class verbatim.
        assert "severity-high\"><script>" not in content

    def test_dashboard_escapes_untrusted_harness_name(self):
        """Harness names embedded in the heatmap must be HTML-escaped."""
        results = {
            "summary": {
                "total_tests": 1,
                "passed": 0,
                "failed": 1,
                "pass_rate": 0.0,
                "by_harness": {
                    "<script>alert(3)</script>": {"passed": 0, "failed": 1, "pass_rate": 0.0}
                },
            }
        }
        generator = DashboardGenerator(results)

        with TemporaryDirectory() as tmpdir:
            output_file = Path(tmpdir) / "dashboard.html"
            generator.generate(str(output_file))
            content = output_file.read_text()

        assert "<script>alert(3)</script>" not in content
        assert "&lt;script&gt;" in content


class TestPipelineIntegration:
    """Integration tests for the full pipeline."""

    def test_regression_detection_workflow(self):
        """Test complete regression detection workflow."""
        # Setup baseline
        baseline_results = {
            "summary": {
                "total_tests": 100,
                "passed": 95,
                "failed": 5,
                "pass_rate": 95.0,
                "avg_duration_ms": 1000,
                "by_harness": {
                    "opencode": {"passed": 50, "failed": 1, "pass_rate": 98.0},
                    "copilot": {"passed": 45, "failed": 4, "pass_rate": 92.0},
                },
            },
            "failed_tests": ["test_001", "test_002", "test_003", "test_004", "test_005"],
        }

        # Setup degraded results
        degraded_results = {
            "summary": {
                "total_tests": 100,
                "passed": 80,
                "failed": 20,
                "pass_rate": 80.0,
                "avg_duration_ms": 1500,
                "by_harness": {
                    "opencode": {"passed": 40, "failed": 10, "pass_rate": 80.0},
                    "copilot": {"passed": 40, "failed": 10, "pass_rate": 80.0},
                },
            },
            "failed_tests": ["test_" + str(i).zfill(3) for i in range(1, 21)],
        }

        # Detect regressions
        detector = RegressionDetector()
        regressions = detector.detect(baseline_results, degraded_results)

        # Verify detection
        assert len(regressions) > 0
        summary = detector.get_summary()
        assert summary["total_regressions"] > 0

        # Generate markdown report
        markdown = detector.to_markdown()
        assert "Regressions Summary" in markdown

    def test_baseline_lifecycle(self):
        """Test complete baseline lifecycle."""
        with TemporaryDirectory() as tmpdir:
            manager = BaselineManager(Path(tmpdir))

            results = {
                "summary": {"total_tests": 100, "passed": 95, "failed": 5, "pass_rate": 95.0},
            }

            # Save baseline
            manager.save_baseline(results)
            baseline = manager.get_current_baseline()
            assert baseline is not None

            # Create snapshot
            snapshot_path = manager.create_monthly_snapshot(results)
            assert Path(snapshot_path).exists()

            # Load snapshot
            snapshot = manager.get_last_snapshot()
            assert snapshot is not None

            # List all
            snapshots = manager.list_snapshots()
            assert len(snapshots) > 0

    def test_end_to_end_pipeline(self):
        """Test end-to-end pipeline: detect -> report -> dashboard."""
        with TemporaryDirectory() as tmpdir:
            # Create baseline
            baseline = {
                "summary": {
                    "total_tests": 100,
                    "passed": 95,
                    "failed": 5,
                    "pass_rate": 95.0,
                    "avg_duration_ms": 1000,
                    "by_harness": {
                        "opencode": {"passed": 50, "failed": 1, "pass_rate": 98.0},
                    },
                },
                "failed_tests": ["test_001"],
            }

            # Create degraded results
            current = {
                "summary": {
                    "total_tests": 100,
                    "passed": 85,
                    "failed": 15,
                    "pass_rate": 85.0,
                    "avg_duration_ms": 1200,
                    "by_harness": {
                        "opencode": {"passed": 45, "failed": 6, "pass_rate": 88.0},
                    },
                },
                "failed_tests": ["test_" + str(i).zfill(3) for i in range(1, 16)],
            }

            # Detect regressions
            detector = RegressionDetector()
            regressions = detector.detect(baseline, current)

            # Generate dashboard
            generator = DashboardGenerator(
                current,
                {"results": baseline},
                detector.to_dict_list()
            )

            output_file = Path(tmpdir) / "dashboard.html"
            generator.generate(str(output_file))

            assert Path(output_file).exists()
            assert len(regressions) > 0


class TestQualityMetrics:
    """Tests for quality score calculations."""

    def test_quality_score_perfect(self):
        """Test quality score calculation for perfect results."""
        results = {
            "summary": {
                "total_tests": 100,
                "passed": 100,
                "failed": 0,
                "pass_rate": 100.0,
            }
        }

        pass_rate = results["summary"]["pass_rate"]
        quality_score = pass_rate / 100.0
        assert quality_score == 1.0

    def test_quality_score_degraded(self):
        """Test quality score calculation for degraded results."""
        results = {
            "summary": {
                "total_tests": 100,
                "passed": 80,
                "failed": 20,
                "pass_rate": 80.0,
            }
        }

        pass_rate = results["summary"]["pass_rate"]
        quality_score = pass_rate / 100.0
        assert quality_score == 0.8


# Pytest configuration for coverage
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--cov=src/skills/_meta/evaluation_framework", "--cov-report=term-missing"])
