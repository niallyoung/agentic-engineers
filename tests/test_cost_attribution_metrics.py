"""
Tests for CostAttributionMetrics — integration with MetricsRegistry.

Covers:
  - Recording attribution results to metrics
  - Retrieving costs by dimension
  - Thread safety
"""

import pytest
from src.orchestration.monitoring.metrics import MetricsRegistry, create_cost_metrics
from src.orchestration.models.cost_attributor import CostAttributor
from src.orchestration.models.cost_attribution_metrics import CostAttributionMetrics


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def registry():
    """Fresh MetricsRegistry instance."""
    return MetricsRegistry()


@pytest.fixture
def cost_metrics(registry):
    """Cost metrics from registry."""
    return create_cost_metrics(registry)


@pytest.fixture
def attribution_metrics(registry, cost_metrics):
    """CostAttributionMetrics instance."""
    return CostAttributionMetrics(registry, cost_metrics)


@pytest.fixture
def attributor():
    """Fresh CostAttributor instance."""
    return CostAttributor()


# ---------------------------------------------------------------------------
# Test: Recording Attribution Results
# ---------------------------------------------------------------------------

class TestRecordingAttribution:
    """Test recording attribution results to metrics."""
    
    def test_record_single_attribution(self, attributor, attribution_metrics):
        """Record a single attribution result."""
        result = attributor.attribute_cost(
            task_id="task-001",
            agents=["engineer"],
            tokens_per_agent={"engineer": 1000},
            total_cost=0.30,
            roles_per_agent={"engineer": "engineer"},
            models_per_agent={"engineer": "haiku-4-5"},
        )
        
        # Should not raise
        attribution_metrics.record_attribution(result)
    
    def test_record_multiple_agents(self, attributor, attribution_metrics):
        """Record attribution with multiple agents."""
        result = attributor.attribute_cost(
            task_id="task-002",
            agents=["engineer", "senior"],
            tokens_per_agent={"engineer": 10000, "senior": 20000},
            total_cost=0.45,
            roles_per_agent={"engineer": "engineer", "senior": "senior_engineer"},
            models_per_agent={"engineer": "haiku-4-5", "senior": "sonnet-4-6"},
            task_type="implementation",
        )
        
        # Should not raise
        attribution_metrics.record_attribution(result)
    
    def test_record_with_task_type(self, attributor, attribution_metrics):
        """Record attribution with task type."""
        result = attributor.attribute_cost(
            task_id="task-003",
            agents=["agent_a"],
            tokens_per_agent={"agent_a": 5000},
            total_cost=0.20,
            roles_per_agent={"agent_a": "engineer"},
            models_per_agent={"agent_a": "sonnet-4-6"},
            task_type="review",
        )
        
        # Should not raise
        attribution_metrics.record_attribution(result)
    
    def test_record_multiple_attributions(self, attributor, attribution_metrics):
        """Record multiple attribution results sequentially."""
        for i in range(5):
            result = attributor.attribute_cost(
                task_id=f"task-{i:03d}",
                agents=["agent_a"],
                tokens_per_agent={"agent_a": 1000 * (i + 1)},
                total_cost=0.10 * (i + 1),
                roles_per_agent={"agent_a": "engineer"},
                models_per_agent={"agent_a": "haiku-4-5"},
            )
            attribution_metrics.record_attribution(result)


# ---------------------------------------------------------------------------
# Test: Retrieving Costs by Dimension
# ---------------------------------------------------------------------------

class TestRetrievingCosts:
    """Test retrieving aggregated costs by dimension."""
    
    def test_get_cost_by_role(self, attributor, attribution_metrics):
        """Retrieve costs aggregated by role."""
        # Record two attributions
        result1 = attributor.attribute_cost(
            task_id="task-1",
            agents=["eng"],
            tokens_per_agent={"eng": 5000},
            total_cost=0.30,
            roles_per_agent={"eng": "engineer"},
            models_per_agent={"eng": "haiku-4-5"},
        )
        attribution_metrics.record_attribution(result1)
        
        result2 = attributor.attribute_cost(
            task_id="task-2",
            agents=["senior"],
            tokens_per_agent={"senior": 5000},
            total_cost=0.20,
            roles_per_agent={"senior": "senior_engineer"},
            models_per_agent={"senior": "sonnet-4-6"},
        )
        attribution_metrics.record_attribution(result2)
        
        # Retrieve costs by role
        by_role = attribution_metrics.get_cost_by_role()
        
        # Should have entries for both roles
        assert "engineer" in by_role
        assert "senior_engineer" in by_role
        assert by_role["engineer"] == pytest.approx(0.30, abs=0.001)
        assert by_role["senior_engineer"] == pytest.approx(0.20, abs=0.001)
    
    def test_get_cost_by_model(self, attributor, attribution_metrics):
        """Retrieve costs aggregated by model."""
        result1 = attributor.attribute_cost(
            task_id="task-1",
            agents=["agent_a"],
            tokens_per_agent={"agent_a": 5000},
            total_cost=0.30,
            roles_per_agent={"agent_a": "engineer"},
            models_per_agent={"agent_a": "haiku-4-5"},
        )
        attribution_metrics.record_attribution(result1)
        
        result2 = attributor.attribute_cost(
            task_id="task-2",
            agents=["agent_b"],
            tokens_per_agent={"agent_b": 5000},
            total_cost=0.50,
            roles_per_agent={"agent_b": "senior_engineer"},
            models_per_agent={"agent_b": "sonnet-4-6"},
        )
        attribution_metrics.record_attribution(result2)
        
        by_model = attribution_metrics.get_cost_by_model()
        
        assert "haiku-4-5" in by_model
        assert "sonnet-4-6" in by_model
        assert by_model["haiku-4-5"] == pytest.approx(0.30, abs=0.001)
        assert by_model["sonnet-4-6"] == pytest.approx(0.50, abs=0.001)
    
    def test_get_cost_by_task_type(self, attributor, attribution_metrics):
        """Retrieve costs aggregated by task type."""
        result1 = attributor.attribute_cost(
            task_id="task-1",
            agents=["agent_a"],
            tokens_per_agent={"agent_a": 5000},
            total_cost=0.30,
            roles_per_agent={"agent_a": "engineer"},
            models_per_agent={"agent_a": "haiku-4-5"},
            task_type="implementation",
        )
        attribution_metrics.record_attribution(result1)
        
        result2 = attributor.attribute_cost(
            task_id="task-2",
            agents=["agent_b"],
            tokens_per_agent={"agent_b": 5000},
            total_cost=0.20,
            roles_per_agent={"agent_b": "engineer"},
            models_per_agent={"agent_b": "haiku-4-5"},
            task_type="review",
        )
        attribution_metrics.record_attribution(result2)
        
        by_type = attribution_metrics.get_cost_by_task_type()
        
        assert "implementation" in by_type
        assert "review" in by_type
        assert by_type["implementation"] == pytest.approx(0.30, abs=0.001)
        assert by_type["review"] == pytest.approx(0.20, abs=0.001)
    
    def test_get_cost_by_date(self, attributor, attribution_metrics):
        """Retrieve costs aggregated by date."""
        result1 = attributor.attribute_cost(
            task_id="task-1",
            agents=["agent_a"],
            tokens_per_agent={"agent_a": 5000},
            total_cost=0.30,
            roles_per_agent={"agent_a": "engineer"},
            models_per_agent={"agent_a": "haiku-4-5"},
            timestamp="2025-01-15T10:00:00Z",
        )
        attribution_metrics.record_attribution(result1)
        
        result2 = attributor.attribute_cost(
            task_id="task-2",
            agents=["agent_b"],
            tokens_per_agent={"agent_b": 5000},
            total_cost=0.20,
            roles_per_agent={"agent_b": "engineer"},
            models_per_agent={"agent_b": "haiku-4-5"},
            timestamp="2025-01-15T14:00:00Z",
        )
        attribution_metrics.record_attribution(result2)
        
        result3 = attributor.attribute_cost(
            task_id="task-3",
            agents=["agent_c"],
            tokens_per_agent={"agent_c": 5000},
            total_cost=0.15,
            roles_per_agent={"agent_c": "engineer"},
            models_per_agent={"agent_c": "haiku-4-5"},
            timestamp="2025-01-16T10:00:00Z",
        )
        attribution_metrics.record_attribution(result3)
        
        by_date = attribution_metrics.get_cost_by_date()
        
        assert "2025-01-15" in by_date
        assert "2025-01-16" in by_date
        # Note: dates accumulate, so 2025-01-15 should have 0.30 + 0.20 = 0.50
        assert by_date["2025-01-15"] == pytest.approx(0.50, abs=0.001)
        assert by_date["2025-01-16"] == pytest.approx(0.15, abs=0.001)
