"""Comprehensive test suite for ModelRouter and cost analysis."""

import pytest

from src.copilot.model_router import (
    CostAnalyzer,
    CostAnalysis,
    ComplexityScore,
    ModelRouter,
    RoutingDecision,
)


class TestComplexityAnalysis:
    """Test complexity scoring algorithm."""

    def test_analyze_complexity_basic(self) -> None:
        """Test basic complexity analysis."""
        router = ModelRouter()
        task = {
            "effort": "low",
            "description": "Add a simple validation rule",
        }
        result = router.analyze_complexity(task)

        assert isinstance(result, ComplexityScore)
        assert 0 <= result.score <= 100
        assert result.effort_factor == 1.0
        assert not result.has_thinking_requirements
        assert len(result.reasons) > 0

    def test_analyze_complexity_low_effort(self) -> None:
        """Test low effort task."""
        router = ModelRouter()
        task = {
            "effort": "low",
            "description": "Update a single function",
        }
        result = router.analyze_complexity(task)

        assert result.score <= 25  # Low effort should score low
        assert "low effort" in " ".join(result.reasons).lower()

    def test_analyze_complexity_high_effort(self) -> None:
        """Test high effort task."""
        router = ModelRouter()
        task = {
            "effort": "high",
            "description": "Complex multi-service refactor",
        }
        result = router.analyze_complexity(task)

        assert result.score >= 20
        assert "high effort" in " ".join(result.reasons).lower()

    def test_analyze_complexity_max_effort(self) -> None:
        """Test max effort task."""
        router = ModelRouter()
        task = {
            "effort": "max",
            "description": "Critical security audit",
        }
        result = router.analyze_complexity(task)

        assert result.score >= 30
        assert result.effort_factor > 1.0

    def test_analyze_complexity_long_description(self) -> None:
        """Test task with long, complex description."""
        router = ModelRouter()
        long_desc = (
            "This is a very long description. "
            * 50
            + "It involves refactoring, architecture, and multi-service integration."
        )
        task = {
            "effort": "medium",
            "description": long_desc,
        }
        result = router.analyze_complexity(task)

        assert result.score > 25
        assert "long" in " ".join(result.reasons).lower()

    def test_analyze_complexity_thinking_required(self) -> None:
        """Test task requiring thinking capability."""
        router = ModelRouter()
        task = {
            "effort": "medium",
            "description": "Debug the root cause of production issue",
            "thinking_required": True,
        }
        result = router.analyze_complexity(task)

        assert result.has_thinking_requirements
        assert any("thinking" in r.lower() for r in result.reasons)
        assert result.score > 25

    def test_analyze_complexity_thinking_keywords(self) -> None:
        """Test detection of thinking keywords in description."""
        router = ModelRouter()
        task = {
            "effort": "low",
            "description": "Analyze the design and architecture implications",
        }
        result = router.analyze_complexity(task)

        assert result.has_thinking_requirements

    def test_analyze_complexity_complexity_keywords(self) -> None:
        """Test detection of complexity keywords."""
        router = ModelRouter()
        task = {
            "effort": "medium",
            "description": (
                "Refactor the architecture for distributed system migration "
                "with async concurrent processing"
            ),
        }
        result = router.analyze_complexity(task)

        assert result.score > 30
        assert any("keyword" in r.lower() for r in result.reasons)

    def test_analyze_complexity_many_requirements(self) -> None:
        """Test task with many requirements."""
        router = ModelRouter()
        task = {
            "effort": "medium",
            "description": "Implementation task",
            "requirements": ["Req1", "Req2", "Req3", "Req4", "Req5", "Req6"],
        }
        result = router.analyze_complexity(task)

        assert result.score > 15
        assert any("requirement" in r.lower() for r in result.reasons)

    def test_analyze_complexity_strict_constraints(self) -> None:
        """Test task with strict constraints."""
        router = ModelRouter()
        task = {
            "effort": "medium",
            "description": "Code change",
            "constraints": [
                "Maintain backward compatibility",
                "Performance must not degrade",
            ],
        }
        result = router.analyze_complexity(task)

        assert any("constraint" in r.lower() for r in result.reasons)

    def test_analyze_complexity_edge_cases(self) -> None:
        """Test edge cases."""
        router = ModelRouter()

        # Empty task
        result = router.analyze_complexity({})
        assert 0 <= result.score <= 100
        assert result.effort_factor == 1.0

        # Invalid effort value
        result = router.analyze_complexity({"effort": "invalid", "description": "Test"})
        assert result.score >= 0

        # Score capping at 100
        task = {
            "effort": "max",
            "description": "A" * 2000,
            "thinking_required": True,
            "requirements": ["R"] * 20,
        }
        result = router.analyze_complexity(task)
        assert result.score <= 100


class TestModelSelection:
    """Test model selection based on complexity."""

    def test_select_model_low_complexity(self) -> None:
        """Test Haiku selection for low complexity."""
        router = ModelRouter()
        model, rule = router.select_model(10)

        assert model == "claude-haiku-4.5"
        assert "0-30" in rule

    def test_select_model_medium_complexity(self) -> None:
        """Test Sonnet selection for medium complexity."""
        router = ModelRouter()
        model, rule = router.select_model(50)

        assert model == "claude-sonnet-4.6"
        assert "31-70" in rule

    def test_select_model_high_complexity(self) -> None:
        """Test Opus selection for high complexity."""
        router = ModelRouter()
        model, rule = router.select_model(85)

        assert model == "claude-opus-4.8"
        assert "71-100" in rule

    def test_select_model_boundary_30(self) -> None:
        """Test model selection at complexity boundary 30."""
        router = ModelRouter()

        # At 30 should still be Haiku
        model, _ = router.select_model(30)
        assert model == "claude-haiku-4.5"

        # At 31 should be Sonnet
        model, _ = router.select_model(31)
        assert model == "claude-sonnet-4.6"

    def test_select_model_boundary_70(self) -> None:
        """Test model selection at complexity boundary 70."""
        router = ModelRouter()

        # At 70 should still be Sonnet
        model, _ = router.select_model(70)
        assert model == "claude-sonnet-4.6"

        # At 71 should be Opus
        model, _ = router.select_model(71)
        assert model == "claude-opus-4.8"


class TestTokenEstimation:
    """Test token count projection."""

    def test_estimate_tokens_low_complexity(self) -> None:
        """Test token estimation for low complexity task."""
        router = ModelRouter()
        tokens = router.estimate_tokens(10)

        assert 1000 < tokens < 3000

    def test_estimate_tokens_medium_complexity(self) -> None:
        """Test token estimation for medium complexity task."""
        router = ModelRouter()
        tokens = router.estimate_tokens(50)

        assert 3500 < tokens <= 8000

    def test_estimate_tokens_high_complexity(self) -> None:
        """Test token estimation for high complexity task."""
        router = ModelRouter()
        tokens = router.estimate_tokens(90)

        assert 8000 < tokens <= 25000

    def test_estimate_tokens_with_description(self) -> None:
        """Test token estimation accounting for description size."""
        router = ModelRouter()

        desc_short = "Short description"
        tokens_short = router.estimate_tokens(50, description=desc_short)

        desc_long = "This is a very long description. " * 50
        tokens_long = router.estimate_tokens(50, description=desc_long)

        assert tokens_long > tokens_short

    def test_estimate_tokens_with_requirements(self) -> None:
        """Test token estimation accounting for requirements."""
        router = ModelRouter()

        no_reqs = router.estimate_tokens(50, requirements=[])
        with_reqs = router.estimate_tokens(50, requirements=["Req1", "Req2", "Req3"])

        assert with_reqs > no_reqs

    def test_estimate_tokens_consistency(self) -> None:
        """Test that token estimation is consistent."""
        router = ModelRouter()

        task = {
            "effort": "high",
            "description": "Test task",
            "requirements": ["R1", "R2"],
        }

        tokens1 = router.estimate_tokens(50, "Test task", ["R1", "R2"])
        tokens2 = router.estimate_tokens(50, "Test task", ["R1", "R2"])

        assert tokens1 == tokens2


class TestCostEstimation:
    """Test cost estimation per model."""

    def test_estimate_cost_haiku(self) -> None:
        """Test cost estimation for Haiku model."""
        router = ModelRouter()
        cost = router.estimate_cost("claude-haiku-4.5", 5000)

        assert cost > 0
        assert cost < 1.0  # 5K tokens should be cheap

    def test_estimate_cost_sonnet(self) -> None:
        """Test cost estimation for Sonnet model."""
        router = ModelRouter()
        cost = router.estimate_cost("claude-sonnet-4.6", 5000)

        assert cost > 0

    def test_estimate_cost_opus(self) -> None:
        """Test cost estimation for Opus model."""
        router = ModelRouter()
        cost = router.estimate_cost("claude-opus-4.8", 5000)

        assert cost > 0

    def test_estimate_cost_comparison(self) -> None:
        """Test that Haiku is cheaper than Sonnet."""
        router = ModelRouter()
        tokens = 5000

        cost_haiku = router.estimate_cost("claude-haiku-4.5", tokens)
        cost_sonnet = router.estimate_cost("claude-sonnet-4.6", tokens)
        cost_opus = router.estimate_cost("claude-opus-4.8", tokens)

        assert cost_haiku < cost_sonnet < cost_opus

    def test_estimate_cost_scale(self) -> None:
        """Test that cost scales with token count."""
        router = ModelRouter()

        cost_1k = router.estimate_cost("claude-haiku-4.5", 1000)
        cost_10k = router.estimate_cost("claude-haiku-4.5", 10000)

        assert cost_10k > cost_1k

    def test_estimate_cost_unknown_model(self) -> None:
        """Test handling of unknown model."""
        router = ModelRouter()
        cost = router.estimate_cost("unknown-model", 5000)

        assert cost == 0.0

    def test_estimate_cost_zero_tokens(self) -> None:
        """Test cost estimation with zero tokens."""
        router = ModelRouter()
        cost = router.estimate_cost("claude-haiku-4.5", 0)

        assert cost == 0.0


class TestRoutingDecision:
    """Test full routing decision."""

    def test_route_simple_task(self) -> None:
        """Test routing decision for simple task."""
        router = ModelRouter()
        task = {
            "task_id": "TASK-001",
            "effort": "low",
            "description": "Add validation",
            "requirements": ["Req1"],
        }
        decision = router.route(task)

        assert isinstance(decision, RoutingDecision)
        assert decision.model_name == "claude-haiku-4.5"
        assert 0 <= decision.complexity_score <= 30
        assert decision.estimated_tokens > 0
        assert decision.estimated_cost > 0
        assert decision.explanation
        assert decision.routing_rule

    def test_route_complex_task(self) -> None:
        """Test routing decision for complex task."""
        router = ModelRouter()
        task = {
            "task_id": "TASK-002",
            "effort": "max",
            "description": "Design and implement distributed system",
            "thinking_required": True,
            "requirements": ["R1", "R2", "R3", "R4", "R5"],
        }
        decision = router.route(task)

        assert decision.model_name in ["claude-sonnet-4.6", "claude-opus-4.8"]
        assert decision.complexity_score > 50
        assert decision.estimated_tokens > 0
        assert decision.estimated_cost > 0

    def test_route_medium_task(self) -> None:
        """Test routing decision for medium task."""
        router = ModelRouter()
        task = {
            "task_id": "TASK-003",
            "effort": "medium",
            "description": "Refactor module architecture",
            "requirements": ["R1", "R2", "R3"],
        }
        decision = router.route(task)

        assert decision.model_name in ["claude-haiku-4.5", "claude-sonnet-4.6"]
        assert decision.complexity_score >= 15

    def test_route_includes_all_reasons(self) -> None:
        """Test that routing decision includes complexity reasons."""
        router = ModelRouter()
        task = {
            "effort": "high",
            "description": "Complex task",
            "thinking_required": True,
        }
        decision = router.route(task)

        # Explanation should mention complexity factors
        assert "complexity" in decision.explanation.lower()
        assert "factors" in decision.explanation.lower()
        assert "tokens" in decision.explanation.lower()
        assert "$" in decision.explanation


class TestCostAnalysis:
    """Test cost comparison and analysis."""

    def test_compare_models_basic(self) -> None:
        """Test model comparison."""
        router = ModelRouter()
        task = {
            "task_id": "TASK-001",
            "effort": "medium",
            "description": "Test task",
        }
        analysis = router.compare_models(task)

        assert isinstance(analysis, CostAnalysis)
        assert analysis.task_id == "TASK-001"
        assert analysis.haiku_cost > 0
        assert analysis.sonnet_cost > 0
        assert analysis.opus_cost > 0
        assert analysis.haiku_cost < analysis.sonnet_cost < analysis.opus_cost

    def test_compare_models_suitability(self) -> None:
        """Test model suitability assessment."""
        router = ModelRouter()

        # Low complexity: Haiku suitable
        task_low = {
            "task_id": "LOW",
            "effort": "low",
            "description": "Simple task",
        }
        analysis_low = router.compare_models(task_low)
        assert analysis_low.haiku_suitable
        assert analysis_low.recommended_model == "claude-haiku-4.5"

        # High complexity: Opus may or may not be recommended
        task_high = {
            "task_id": "HIGH",
            "effort": "max",
            "description": "Complex task",
            "thinking_required": True,
        }
        analysis_high = router.compare_models(task_high)
        assert analysis_high.opus_suitable
        assert analysis_high.recommended_model in ["claude-sonnet-4.6", "claude-opus-4.8"]

    def test_compare_models_savings_calculation(self) -> None:
        """Test savings calculation."""
        router = ModelRouter()
        task = {
            "task_id": "TASK-001",
            "effort": "low",
            "description": "Simple task",
        }
        analysis = router.compare_models(task)

        # Should have savings calculated if haiku is suitable
        if analysis.haiku_suitable and analysis.recommended_model != "claude-haiku-4.5":
            assert analysis.savings_with_haiku is not None
            assert analysis.savings_with_haiku > 0

    def test_get_cost_comparison_matrix(self) -> None:
        """Test cost comparison matrix generation."""
        router = ModelRouter()

        analyses = [
            router.compare_models(
                {
                    "task_id": "T1",
                    "effort": "low",
                    "description": "Task 1",
                }
            ),
            router.compare_models(
                {
                    "task_id": "T2",
                    "effort": "high",
                    "description": "Task 2",
                }
            ),
        ]

        matrix = router.get_cost_comparison_matrix(analyses)

        assert matrix["total_tasks"] == 2
        assert matrix["haiku_total_cost"] > 0
        assert matrix["sonnet_total_cost"] > 0
        assert matrix["opus_total_cost"] > 0
        assert matrix["potential_savings_vs_sonnet"] > 0


class TestCostAnalyzer:
    """Test CostAnalyzer module."""

    def test_analyzer_batch(self) -> None:
        """Test batch analysis."""
        router = ModelRouter()
        analyzer = CostAnalyzer(router)

        tasks = [
            {"task_id": "T1", "effort": "low", "description": "Task 1"},
            {"task_id": "T2", "effort": "high", "description": "Task 2"},
        ]

        analyses, matrix = analyzer.analyze_batch(tasks)

        assert len(analyses) == 2
        assert matrix["total_tasks"] == 2
        assert all(isinstance(a, CostAnalysis) for a in analyses)

    def test_analyzer_report_generation(self) -> None:
        """Test report generation."""
        router = ModelRouter()
        analyzer = CostAnalyzer(router)

        analyses = [
            router.compare_models(
                {"task_id": "T1", "effort": "low", "description": "Task 1"}
            ),
        ]

        report = analyzer.generate_cost_report(analyses)

        assert "Cost Analysis Report" in report
        assert "Task ID" in report
        assert "Haiku" in report
        assert "Sonnet" in report
        assert "Opus" in report
        assert "$" in report

    def test_analyzer_default_router(self) -> None:
        """Test analyzer with default router."""
        analyzer = CostAnalyzer()

        assert analyzer.router is not None
        assert isinstance(analyzer.router, ModelRouter)


class TestIntegration:
    """Integration tests combining multiple components."""

    def test_end_to_end_routing_workflow(self) -> None:
        """Test complete routing workflow."""
        router = ModelRouter()

        # Define a realistic task
        task = {
            "task_id": "TASK-COPILOT-001",
            "effort": "high",
            "description": (
                "Implement a distributed caching layer with TTL support "
                "and cross-service consistency. Requires analyzing "
                "the current architecture and designing the integration points."
            ),
            "thinking_required": True,
            "requirements": [
                "Support for multiple backends",
                "Automatic TTL management",
                "Consistency guarantees",
                "Performance monitoring",
            ],
            "constraints": [
                "Maintain backward compatibility",
                "No performance degradation",
            ],
        }

        # Get complexity score
        complexity = router.analyze_complexity(task)
        assert 50 <= complexity.score <= 100

        # Get routing decision
        decision = router.route(task)
        assert decision.model_name == "claude-opus-4.8"
        assert decision.complexity_score > 70

        # Get cost comparison
        analysis = router.compare_models(task)
        assert analysis.recommended_model == "claude-opus-4.8"
        assert analysis.opus_suitable

    def test_batch_routing_with_cost_analysis(self) -> None:
        """Test batch routing with cost analysis."""
        router = ModelRouter()
        analyzer = CostAnalyzer(router)

        tasks = [
            {
                "task_id": "T1",
                "effort": "low",
                "description": "Simple validation",
            },
            {
                "task_id": "T2",
                "effort": "medium",
                "description": "Refactor module",
            },
            {
                "task_id": "T3",
                "effort": "max",
                "description": "Distributed system design",
                "thinking_required": True,
            },
        ]

        analyses, matrix = analyzer.analyze_batch(tasks)

        # Verify correct models selected
        assert analyses[0].recommended_model == "claude-haiku-4.5"
        assert analyses[1].recommended_model in ["claude-haiku-4.5", "claude-sonnet-4.6"]
        assert analyses[2].recommended_model in ["claude-sonnet-4.6", "claude-opus-4.8"]

        # Verify cost analysis
        assert matrix["total_tasks"] == 3
        assert matrix["haiku_total_cost"] < matrix["sonnet_total_cost"] < matrix["opus_total_cost"]

        # Generate report
        report = analyzer.generate_cost_report(analyses)
        assert "3" in report or "three" in report.lower()

    def test_routing_decision_consistency(self) -> None:
        """Test that routing decisions are consistent for same input."""
        router = ModelRouter()

        task = {
            "task_id": "TEST",
            "effort": "medium",
            "description": "Test task",
        }

        decision1 = router.route(task)
        decision2 = router.route(task)

        assert decision1.model_name == decision2.model_name
        assert decision1.complexity_score == decision2.complexity_score
        assert decision1.estimated_tokens == decision2.estimated_tokens
        assert decision1.estimated_cost == decision2.estimated_cost


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_zero_complexity_edge_case(self) -> None:
        """Test routing with minimal complexity."""
        router = ModelRouter()
        decision = router.route({})

        assert decision.model_name == "claude-haiku-4.5"
        assert decision.complexity_score >= 0

    def test_maximum_complexity_edge_case(self) -> None:
        """Test routing with very high complexity."""
        router = ModelRouter()
        task = {
            "effort": "max",
            "description": "A" * 1000,
            "thinking_required": True,
            "requirements": ["R"] * 20,
            "constraints": [
                "Security critical",
                "Performance sensitive",
                "Backward compatible",
            ],
        }

        decision = router.route(task)
        assert decision.complexity_score <= 100
        assert decision.model_name == "claude-opus-4.8"

    def test_cost_estimation_precision(self) -> None:
        """Test cost estimation precision."""
        router = ModelRouter()

        # Test with various token counts
        for tokens in [100, 1000, 5000, 10000]:
            cost = router.estimate_cost("claude-haiku-4.5", tokens)
            assert cost >= 0
            assert cost < 100  # Sanity check

    def test_pricing_data_completeness(self) -> None:
        """Test that all models have pricing data."""
        router = ModelRouter()

        expected_models = [
            "claude-haiku-4.5",
            "claude-sonnet-4.6",
            "claude-opus-4.8",
        ]

        for model in expected_models:
            assert model in router.PRICING
            assert "input" in router.PRICING[model]
            assert "output" in router.PRICING[model]
            assert router.PRICING[model]["input"] > 0
            assert router.PRICING[model]["output"] > 0

    def test_threshold_consistency(self) -> None:
        """Test that thresholds are consistent."""
        router = ModelRouter()

        # Haiku/Sonnet boundary
        assert router.HAIKU_THRESHOLD < router.SONNET_THRESHOLD

        # Score range
        assert 0 <= router.HAIKU_THRESHOLD <= 100
        assert 0 <= router.SONNET_THRESHOLD <= 100
