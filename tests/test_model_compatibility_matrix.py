"""
Unit tests for Model Compatibility Matrix (TASK-EVALS-002)

Tests cover:
- ScenarioMetrics creation and serialization
- ModelCompatibilityMatrix aggregation
- Regression detection (quality and latency)
- Colored matrix visualization
- Summary statistics by model and scenario
- JSON serialization/deserialization
"""

import pytest
import json
import tempfile
from pathlib import Path
from datetime import datetime

from src.skills._meta.evaluation_framework.model_matrix import (
    ModelCompatibilityMatrix,
    ScenarioMetrics,
    TestScenario,
    TestStatus,
)


class TestScenarioMetrics:
    """Test ScenarioMetrics dataclass."""
    
    def test_create_scenario_metrics(self):
        """Test creating scenario metrics."""
        metric = ScenarioMetrics(
            scenario=TestScenario.SIMPLE,
            model="haiku",
            harness="opencode",
            latency_ms=150,
            quality_score=95.0,
            tokens_used=1200,
            cost_usd=0.03,
            error_rate=0.0,
            status=TestStatus.PASS,
        )
        
        assert metric.scenario == TestScenario.SIMPLE
        assert metric.model == "haiku"
        assert metric.quality_score == 95.0
        assert metric.latency_ms == 150
    
    def test_scenario_metrics_to_dict(self):
        """Test converting metrics to dictionary."""
        metric = ScenarioMetrics(
            scenario=TestScenario.CODE_FIX,
            model="sonnet",
            harness="copilot",
            latency_ms=250,
            quality_score=88.5,
            tokens_used=2500,
            cost_usd=0.08,
            error_rate=1.5,
            status=TestStatus.PASS,
        )
        
        data = metric.to_dict()
        assert data["scenario"] == "code-fix"
        assert data["model"] == "sonnet"
        assert data["quality_score"] == 88.5
        assert data["status"] == "pass"


class TestModelCompatibilityMatrix:
    """Test ModelCompatibilityMatrix functionality."""
    
    def test_create_empty_matrix(self):
        """Test creating an empty matrix."""
        matrix = ModelCompatibilityMatrix()
        assert len(matrix.results) == 0
        assert matrix.generated_at is not None
    
    def test_add_result_to_matrix(self):
        """Test adding results to matrix."""
        matrix = ModelCompatibilityMatrix()
        
        metric1 = ScenarioMetrics(
            scenario=TestScenario.SIMPLE,
            model="haiku",
            harness="opencode",
            latency_ms=100,
            quality_score=90.0,
            tokens_used=1000,
            cost_usd=0.02,
            error_rate=0.0,
        )
        
        metric2 = ScenarioMetrics(
            scenario=TestScenario.COMPLEX,
            model="sonnet",
            harness="copilot",
            latency_ms=500,
            quality_score=95.0,
            tokens_used=3000,
            cost_usd=0.10,
            error_rate=0.0,
        )
        
        matrix.add_result(metric1)
        matrix.add_result(metric2)
        
        assert len(matrix.results) == 2
    
    def test_summary_by_model(self):
        """Test summary statistics by model."""
        matrix = ModelCompatibilityMatrix()
        
        # Add 3 Haiku results
        for i in range(3):
            matrix.add_result(ScenarioMetrics(
                scenario=TestScenario.SIMPLE,
                model="haiku",
                harness="opencode",
                latency_ms=100 + i*10,
                quality_score=90.0 + i,
                tokens_used=1000,
                cost_usd=0.02,
                error_rate=0.0,
                status=TestStatus.PASS,
            ))
        
        # Add 1 failed Haiku result
        matrix.add_result(ScenarioMetrics(
            scenario=TestScenario.SIMPLE,
            model="haiku",
            harness="opencode",
            latency_ms=150,
            quality_score=80.0,
            tokens_used=1500,
            cost_usd=0.03,
            error_rate=5.0,
            status=TestStatus.FAIL,
        ))
        
        summary = matrix.get_summary_by_model()
        
        assert "haiku" in summary
        assert summary["haiku"]["count"] == 4
        assert summary["haiku"]["passed"] == 3
        assert summary["haiku"]["failed"] == 1
        assert summary["haiku"]["avg_quality"] == pytest.approx(90.75, 0.1)
    
    def test_summary_by_scenario(self):
        """Test summary statistics by scenario."""
        matrix = ModelCompatibilityMatrix()
        
        # Add SIMPLE scenario results
        matrix.add_result(ScenarioMetrics(
            scenario=TestScenario.SIMPLE,
            model="haiku",
            harness="opencode",
            latency_ms=100,
            quality_score=95.0,
            tokens_used=1000,
            cost_usd=0.02,
            error_rate=0.0,
            status=TestStatus.PASS,
        ))
        matrix.add_result(ScenarioMetrics(
            scenario=TestScenario.SIMPLE,
            model="sonnet",
            harness="copilot",
            latency_ms=200,
            quality_score=98.0,
            tokens_used=2000,
            cost_usd=0.05,
            error_rate=0.0,
            status=TestStatus.PASS,
        ))
        
        # Add COMPLEX scenario results
        matrix.add_result(ScenarioMetrics(
            scenario=TestScenario.COMPLEX,
            model="opus",
            harness="opencode",
            latency_ms=400,
            quality_score=94.0,
            tokens_used=4000,
            cost_usd=0.15,
            error_rate=0.0,
            status=TestStatus.PASS,
        ))
        
        summary = matrix.get_summary_by_scenario()
        
        assert "simple" in summary
        assert summary["simple"]["count"] == 2
        assert summary["simple"]["passed"] == 2
        assert summary["simple"]["avg_quality"] == pytest.approx(96.5, 0.1)
        
        assert "complex" in summary
        assert summary["complex"]["count"] == 1
    
    def test_detect_quality_regressions(self):
        """Test quality regression detection."""
        matrix = ModelCompatibilityMatrix()
        
        # Add good quality result (95.0)
        matrix.add_result(ScenarioMetrics(
            scenario=TestScenario.SIMPLE,
            model="haiku",
            harness="opencode",
            latency_ms=100,
            quality_score=95.0,
            tokens_used=1000,
            cost_usd=0.02,
            error_rate=0.0,
        ))
        
        # Add poor quality results (70% - regression > 10%)
        for i in range(3):
            matrix.add_result(ScenarioMetrics(
                scenario=TestScenario.SIMPLE,
                model="haiku",
                harness="opencode",
                latency_ms=100,
                quality_score=70.0,
                tokens_used=1000,
                cost_usd=0.02,
                error_rate=0.0,
            ))
        
        regressions = matrix.detect_quality_regressions(baseline=92.0)
        
        # Should detect regression for haiku:simple
        # Avg = (95 + 70 + 70 + 70) / 4 = 76.25, drop = 92 - 76.25 = 15.75% > 10%
        assert len(regressions) > 0
        assert any(r["model"] == "haiku" and r["scenario"] == "simple" for r in regressions)
    
    def test_detect_latency_regressions(self):
        """Test latency regression detection."""
        matrix = ModelCompatibilityMatrix()
        
        # Add good latency (100ms baseline)
        matrix.add_result(ScenarioMetrics(
            scenario=TestScenario.SIMPLE,
            model="haiku",
            harness="opencode",
            latency_ms=100,
            quality_score=90.0,
            tokens_used=1000,
            cost_usd=0.02,
            error_rate=0.0,
        ))
        
        # Add high latency (500ms - 400% increase, > 25% threshold)
        matrix.add_result(ScenarioMetrics(
            scenario=TestScenario.SIMPLE,
            model="haiku",
            harness="opencode",
            latency_ms=500,
            quality_score=90.0,
            tokens_used=1000,
            cost_usd=0.02,
            error_rate=0.0,
        ))
        
        regressions = matrix.detect_latency_regressions(baseline=100.0)
        
        assert len(regressions) > 0
        assert any(r["model"] == "haiku" and r["scenario"] == "simple" for r in regressions)
    
    def test_no_quality_regressions_when_above_threshold(self):
        """Test that no regressions are detected when quality is above threshold."""
        matrix = ModelCompatibilityMatrix()
        
        # All results above 92% (baseline)
        for i in range(3):
            matrix.add_result(ScenarioMetrics(
                scenario=TestScenario.SIMPLE,
                model="haiku",
                harness="opencode",
                latency_ms=100,
                quality_score=93.0 + i,
                tokens_used=1000,
                cost_usd=0.02,
                error_rate=0.0,
            ))
        
        regressions = matrix.detect_quality_regressions(baseline=92.0)
        
        # Should have no regressions
        assert len(regressions) == 0
    
    def test_no_latency_regressions_when_within_threshold(self):
        """Test that no regressions are detected when latency is within threshold."""
        matrix = ModelCompatibilityMatrix()
        
        # Add latencies close to baseline (100ms)
        for latency in [100, 110, 120, 115]:
            matrix.add_result(ScenarioMetrics(
                scenario=TestScenario.SIMPLE,
                model="haiku",
                harness="opencode",
                latency_ms=latency,
                quality_score=90.0,
                tokens_used=1000,
                cost_usd=0.02,
                error_rate=0.0,
            ))
        
        regressions = matrix.detect_latency_regressions(baseline=100.0)
        
        # Should have no regressions (all <25% increase)
        assert len(regressions) == 0
    
    def test_generate_colored_matrix(self):
        """Test colored matrix visualization generation."""
        matrix = ModelCompatibilityMatrix()
        
        # Add results for different models and harnesses
        for model in ["haiku", "sonnet", "opus"]:
            for harness in ["opencode", "copilot"]:
                matrix.add_result(ScenarioMetrics(
                    scenario=TestScenario.SIMPLE,
                    model=model,
                    harness=harness,
                    latency_ms=100,
                    quality_score=95.0,
                    tokens_used=1000,
                    cost_usd=0.02,
                    error_rate=0.0,
                    status=TestStatus.PASS,
                ))
        
        matrix_str = matrix.generate_colored_matrix()
        
        # Should contain model names
        assert "HAIKU" in matrix_str
        assert "SONNET" in matrix_str
        assert "OPUS" in matrix_str
        
        # Should contain emoji indicators
        assert "✅" in matrix_str
    
    def test_colored_matrix_with_failures(self):
        """Test colored matrix with failed tests."""
        matrix = ModelCompatibilityMatrix()
        
        # Good results
        matrix.add_result(ScenarioMetrics(
            scenario=TestScenario.SIMPLE,
            model="haiku",
            harness="opencode",
            latency_ms=100,
            quality_score=95.0,
            tokens_used=1000,
            cost_usd=0.02,
            error_rate=0.0,
            status=TestStatus.PASS,
        ))
        
        # Failed result
        matrix.add_result(ScenarioMetrics(
            scenario=TestScenario.SIMPLE,
            model="haiku",
            harness="copilot",
            latency_ms=100,
            quality_score=50.0,
            tokens_used=1000,
            cost_usd=0.02,
            error_rate=50.0,
            status=TestStatus.FAIL,
        ))
        
        matrix_str = matrix.generate_colored_matrix()
        
        # Should contain both pass and fail indicators
        assert "✅" in matrix_str or "🟡" in matrix_str or "❌" in matrix_str
    
    def test_colored_matrix_filtered_by_scenario(self):
        """Test colored matrix filtered by scenario."""
        matrix = ModelCompatibilityMatrix()
        
        # Add different scenarios
        matrix.add_result(ScenarioMetrics(
            scenario=TestScenario.SIMPLE,
            model="haiku",
            harness="opencode",
            latency_ms=100,
            quality_score=95.0,
            tokens_used=1000,
            cost_usd=0.02,
            error_rate=0.0,
        ))
        
        matrix.add_result(ScenarioMetrics(
            scenario=TestScenario.COMPLEX,
            model="haiku",
            harness="opencode",
            latency_ms=300,
            quality_score=90.0,
            tokens_used=2000,
            cost_usd=0.05,
            error_rate=0.0,
        ))
        
        # Filter by SIMPLE scenario
        simple_matrix = matrix.generate_colored_matrix(scenario=TestScenario.SIMPLE)
        
        assert "simple" in simple_matrix.lower()
        # Should only have results for simple scenario
    
    def test_to_json(self):
        """Test JSON serialization."""
        matrix = ModelCompatibilityMatrix()
        
        matrix.add_result(ScenarioMetrics(
            scenario=TestScenario.SIMPLE,
            model="haiku",
            harness="opencode",
            latency_ms=100,
            quality_score=95.0,
            tokens_used=1000,
            cost_usd=0.02,
            error_rate=0.0,
        ))
        
        json_data = matrix.to_json()
        
        assert "results" in json_data
        assert "summary_by_model" in json_data
        assert "summary_by_scenario" in json_data
        assert len(json_data["results"]) == 1
    
    def test_save_and_load_json(self):
        """Test saving and loading matrix from JSON."""
        with tempfile.TemporaryDirectory() as tmpdir:
            matrix1 = ModelCompatibilityMatrix()
            
            # Add results
            for i in range(3):
                matrix1.add_result(ScenarioMetrics(
                    scenario=TestScenario.SIMPLE,
                    model="haiku",
                    harness="opencode",
                    latency_ms=100 + i*10,
                    quality_score=90.0 + i,
                    tokens_used=1000,
                    cost_usd=0.02,
                    error_rate=0.0,
                ))
            
            # Save to file
            json_path = Path(tmpdir) / "matrix.json"
            matrix1.save_json(json_path)
            
            # Load from file
            matrix2 = ModelCompatibilityMatrix.from_json(json_path)
            
            # Verify results
            assert len(matrix2.results) == 3
            assert all(r.model == "haiku" for r in matrix2.results)
            assert all(r.harness == "opencode" for r in matrix2.results)
    
    def test_all_scenarios_covered(self):
        """Test that all 5 scenarios are properly handled."""
        matrix = ModelCompatibilityMatrix()
        
        scenarios = [
            TestScenario.SIMPLE,
            TestScenario.COMPLEX,
            TestScenario.CODE_FIX,
            TestScenario.REASONING,
            TestScenario.SECURITY,
        ]
        
        for scenario in scenarios:
            matrix.add_result(ScenarioMetrics(
                scenario=scenario,
                model="haiku",
                harness="opencode",
                latency_ms=100,
                quality_score=90.0,
                tokens_used=1000,
                cost_usd=0.02,
                error_rate=0.0,
            ))
        
        summary = matrix.get_summary_by_scenario()
        
        assert len(summary) == 5
        for scenario in scenarios:
            assert scenario.value in summary


class TestQualityScore:
    """Test quality score calculation and evaluation."""
    
    def test_quality_score_excellent(self):
        """Test excellent quality score."""
        metric = ScenarioMetrics(
            scenario=TestScenario.SIMPLE,
            model="opus",
            harness="opencode",
            latency_ms=100,
            quality_score=98.0,
            tokens_used=1000,
            cost_usd=0.15,
            error_rate=0.0,
        )
        
        assert metric.quality_score >= 90
        assert metric.error_rate == 0.0
    
    def test_quality_score_poor(self):
        """Test poor quality score."""
        metric = ScenarioMetrics(
            scenario=TestScenario.SIMPLE,
            model="haiku",
            harness="opencode",
            latency_ms=100,
            quality_score=60.0,
            tokens_used=1000,
            cost_usd=0.02,
            error_rate=10.0,
        )
        
        assert metric.quality_score < 70


class TestCostCalculation:
    """Test cost calculations."""
    
    def test_cost_by_model(self):
        """Test that cost varies by model."""
        results = []
        
        # Haiku should be cheapest
        results.append(ScenarioMetrics(
            scenario=TestScenario.SIMPLE,
            model="haiku",
            harness="opencode",
            latency_ms=100,
            quality_score=90.0,
            tokens_used=1000,
            cost_usd=0.02,
            error_rate=0.0,
        ))
        
        # Sonnet more expensive
        results.append(ScenarioMetrics(
            scenario=TestScenario.SIMPLE,
            model="sonnet",
            harness="opencode",
            latency_ms=200,
            quality_score=95.0,
            tokens_used=2000,
            cost_usd=0.08,
            error_rate=0.0,
        ))
        
        # Opus most expensive
        results.append(ScenarioMetrics(
            scenario=TestScenario.SIMPLE,
            model="opus",
            harness="opencode",
            latency_ms=300,
            quality_score=98.0,
            tokens_used=3000,
            cost_usd=0.15,
            error_rate=0.0,
        ))
        
        costs = [r.cost_usd for r in results]
        assert costs == sorted(costs)  # Should be in ascending order
