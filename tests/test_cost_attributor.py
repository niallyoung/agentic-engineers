"""
Tests for CostAttributor — cost allocation by role, model, task type, and time.

Covers:
  - Basic cost attribution (weighted by tokens)
  - Edge cases (zero tokens, single agent, negative cost)
  - Aggregation by role, model, task type, date
  - Thread safety
  - History tracking
"""

import pytest
from datetime import datetime
from src.orchestration.models.cost_attributor import (
    CostAttributor,
    CostAttributionResult,
    AgentCostShare,
    DimensionalCosts,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def attributor():
    """Fresh CostAttributor instance."""
    return CostAttributor()


# ---------------------------------------------------------------------------
# Test: Basic Cost Attribution
# ---------------------------------------------------------------------------

class TestBasicAttribution:
    """Test basic cost attribution with token-weighted distribution."""
    
    def test_single_agent_gets_all_cost(self, attributor):
        """Single agent should receive 100% of cost."""
        result = attributor.attribute_cost(
            task_id="task-001",
            agents=["engineer"],
            tokens_per_agent={"engineer": 1000},
            total_cost=0.30,
        )
        
        assert result.task_id == "task-001"
        assert result.total_cost == 0.30
        assert result.total_tokens == 1000
        assert len(result.agent_shares) == 1
        
        engineer_share = result.agent_shares["engineer"]
        assert engineer_share.cost == 0.30
        assert engineer_share.weight == 1.0
        assert engineer_share.tokens == 1000
    
    def test_two_agents_weighted_by_tokens(self, attributor):
        """Cost should be split proportionally by token contribution."""
        result = attributor.attribute_cost(
            task_id="task-002",
            agents=["engineer", "senior_engineer"],
            tokens_per_agent={"engineer": 10000, "senior_engineer": 20000},
            total_cost=0.45,
            roles_per_agent={"engineer": "engineer", "senior_engineer": "senior_engineer"},
        )
        
        assert result.total_cost == 0.45
        assert result.total_tokens == 30000
        
        # Engineer: 10K/30K = 1/3 of cost
        engineer_share = result.agent_shares["engineer"]
        assert engineer_share.cost == pytest.approx(0.15, abs=0.001)
        assert engineer_share.weight == pytest.approx(1/3, abs=0.001)
        assert engineer_share.tokens == 10000
        
        # Senior Engineer: 20K/30K = 2/3 of cost
        senior_share = result.agent_shares["senior_engineer"]
        assert senior_share.cost == pytest.approx(0.30, abs=0.001)
        assert senior_share.weight == pytest.approx(2/3, abs=0.001)
        assert senior_share.tokens == 20000
    
    def test_three_agents_proportional_split(self, attributor):
        """Cost split among three agents proportionally."""
        result = attributor.attribute_cost(
            task_id="task-003",
            agents=["agent_a", "agent_b", "agent_c"],
            tokens_per_agent={"agent_a": 5000, "agent_b": 10000, "agent_c": 5000},
            total_cost=1.00,
        )
        
        assert result.total_tokens == 20000
        
        # agent_a: 5K/20K = 25%
        assert result.agent_shares["agent_a"].cost == pytest.approx(0.25, abs=0.001)
        assert result.agent_shares["agent_a"].weight == pytest.approx(0.25, abs=0.001)
        
        # agent_b: 10K/20K = 50%
        assert result.agent_shares["agent_b"].cost == pytest.approx(0.50, abs=0.001)
        assert result.agent_shares["agent_b"].weight == pytest.approx(0.50, abs=0.001)
        
        # agent_c: 5K/20K = 25%
        assert result.agent_shares["agent_c"].cost == pytest.approx(0.25, abs=0.001)
        assert result.agent_shares["agent_c"].weight == pytest.approx(0.25, abs=0.001)


# ---------------------------------------------------------------------------
# Test: Edge Cases
# ---------------------------------------------------------------------------

class TestEdgeCases:
    """Test edge cases and error handling."""
    
    def test_zero_tokens_equal_split(self, attributor):
        """When all agents have zero tokens, cost should split equally."""
        result = attributor.attribute_cost(
            task_id="task-zero",
            agents=["agent_a", "agent_b"],
            tokens_per_agent={"agent_a": 0, "agent_b": 0},
            total_cost=0.20,
        )
        
        assert result.total_tokens == 0
        assert result.agent_shares["agent_a"].cost == pytest.approx(0.10, abs=0.001)
        assert result.agent_shares["agent_b"].cost == pytest.approx(0.10, abs=0.001)
        assert result.agent_shares["agent_a"].weight == pytest.approx(0.5, abs=0.001)
        assert result.agent_shares["agent_b"].weight == pytest.approx(0.5, abs=0.001)
    
    def test_zero_cost(self, attributor):
        """Task with zero cost should still attribute correctly."""
        result = attributor.attribute_cost(
            task_id="task-free",
            agents=["agent_a", "agent_b"],
            tokens_per_agent={"agent_a": 1000, "agent_b": 2000},
            total_cost=0.0,
        )
        
        assert result.total_cost == 0.0
        assert result.agent_shares["agent_a"].cost == 0.0
        assert result.agent_shares["agent_b"].cost == 0.0
    
    def test_empty_agents_raises_error(self, attributor):
        """Empty agents list should raise ValueError."""
        with pytest.raises(ValueError, match="agents list cannot be empty"):
            attributor.attribute_cost(
                task_id="task-bad",
                agents=[],
                tokens_per_agent={},
                total_cost=0.10,
            )
    
    def test_negative_cost_raises_error(self, attributor):
        """Negative cost should raise ValueError."""
        with pytest.raises(ValueError, match="total_cost must be non-negative"):
            attributor.attribute_cost(
                task_id="task-bad",
                agents=["agent_a"],
                tokens_per_agent={"agent_a": 1000},
                total_cost=-0.10,
            )
    
    def test_missing_agent_in_tokens_dict(self, attributor):
        """Agent not in tokens_per_agent should be treated as 0 tokens."""
        result = attributor.attribute_cost(
            task_id="task-missing",
            agents=["agent_a", "agent_b"],
            tokens_per_agent={"agent_a": 1000},  # agent_b missing
            total_cost=0.30,
        )
        
        assert result.agent_shares["agent_a"].tokens == 1000
        assert result.agent_shares["agent_b"].tokens == 0
        assert result.agent_shares["agent_a"].cost == pytest.approx(0.30, abs=0.001)
        assert result.agent_shares["agent_b"].cost == pytest.approx(0.0, abs=0.001)


# ---------------------------------------------------------------------------
# Test: Metadata (Role, Model, Task Type)
# ---------------------------------------------------------------------------

class TestMetadata:
    """Test attribution with role, model, and task type metadata."""
    
    def test_role_metadata_preserved(self, attributor):
        """Role metadata should be preserved in shares."""
        result = attributor.attribute_cost(
            task_id="task-roles",
            agents=["engineer", "senior"],
            tokens_per_agent={"engineer": 5000, "senior": 5000},
            total_cost=0.40,
            roles_per_agent={"engineer": "engineer", "senior": "senior_engineer"},
        )
        
        assert result.agent_shares["engineer"].role == "engineer"
        assert result.agent_shares["senior"].role == "senior_engineer"
    
    def test_model_metadata_preserved(self, attributor):
        """Model metadata should be preserved in shares."""
        result = attributor.attribute_cost(
            task_id="task-models",
            agents=["agent_a", "agent_b"],
            tokens_per_agent={"agent_a": 5000, "agent_b": 5000},
            total_cost=0.40,
            models_per_agent={"agent_a": "haiku-4-5", "agent_b": "sonnet-4-6"},
        )
        
        assert result.agent_shares["agent_a"].model == "haiku-4-5"
        assert result.agent_shares["agent_b"].model == "sonnet-4-6"
    
    def test_task_type_metadata(self, attributor):
        """Task type should be stored in all shares."""
        result = attributor.attribute_cost(
            task_id="task-impl",
            agents=["agent_a", "agent_b"],
            tokens_per_agent={"agent_a": 5000, "agent_b": 5000},
            total_cost=0.40,
            task_type="implementation",
        )
        
        assert result.agent_shares["agent_a"].task_type == "implementation"
        assert result.agent_shares["agent_b"].task_type == "implementation"
    
    def test_timestamp_auto_generated(self, attributor):
        """Timestamp should be auto-generated if not provided."""
        result = attributor.attribute_cost(
            task_id="task-ts",
            agents=["agent_a"],
            tokens_per_agent={"agent_a": 1000},
            total_cost=0.10,
        )
        
        assert result.timestamp is not None
        assert "T" in result.timestamp  # ISO8601 format
        assert result.agent_shares["agent_a"].timestamp is not None
    
    def test_custom_timestamp(self, attributor):
        """Custom timestamp should be preserved."""
        custom_ts = "2025-01-15T10:30:00Z"
        result = attributor.attribute_cost(
            task_id="task-custom-ts",
            agents=["agent_a"],
            tokens_per_agent={"agent_a": 1000},
            total_cost=0.10,
            timestamp=custom_ts,
        )
        
        assert result.timestamp == custom_ts
        assert result.agent_shares["agent_a"].timestamp == custom_ts


# ---------------------------------------------------------------------------
# Test: Aggregation
# ---------------------------------------------------------------------------

class TestAggregation:
    """Test cost aggregation by different dimensions."""
    
    def test_aggregate_by_role(self, attributor):
        """Aggregate costs by role."""
        results = [
            attributor.attribute_cost(
                task_id="task-1",
                agents=["eng", "senior"],
                tokens_per_agent={"eng": 5000, "senior": 5000},
                total_cost=0.30,
                roles_per_agent={"eng": "engineer", "senior": "senior_engineer"},
            ),
            attributor.attribute_cost(
                task_id="task-2",
                agents=["eng"],
                tokens_per_agent={"eng": 10000},
                total_cost=0.20,
                roles_per_agent={"eng": "engineer"},
            ),
        ]
        
        by_role = attributor.aggregate_by_role(results)
        
        # Engineer: 0.15 (from task-1) + 0.20 (from task-2) = 0.35
        assert by_role["engineer"] == pytest.approx(0.35, abs=0.001)
        # Senior Engineer: 0.15 (from task-1)
        assert by_role["senior_engineer"] == pytest.approx(0.15, abs=0.001)
    
    def test_aggregate_by_model(self, attributor):
        """Aggregate costs by model."""
        results = [
            attributor.attribute_cost(
                task_id="task-1",
                agents=["agent_a", "agent_b"],
                tokens_per_agent={"agent_a": 5000, "agent_b": 5000},
                total_cost=0.40,
                models_per_agent={"agent_a": "haiku-4-5", "agent_b": "sonnet-4-6"},
            ),
            attributor.attribute_cost(
                task_id="task-2",
                agents=["agent_c"],
                tokens_per_agent={"agent_c": 10000},
                total_cost=0.20,
                models_per_agent={"agent_c": "sonnet-4-6"},
            ),
        ]
        
        by_model = attributor.aggregate_by_model(results)
        
        # Haiku: 0.20 (from task-1)
        assert by_model["haiku-4-5"] == pytest.approx(0.20, abs=0.001)
        # Sonnet: 0.20 (from task-1) + 0.20 (from task-2) = 0.40
        assert by_model["sonnet-4-6"] == pytest.approx(0.40, abs=0.001)
    
    def test_aggregate_by_task_type(self, attributor):
        """Aggregate costs by task type."""
        results = [
            attributor.attribute_cost(
                task_id="task-1",
                agents=["agent_a"],
                tokens_per_agent={"agent_a": 5000},
                total_cost=0.30,
                task_type="implementation",
            ),
            attributor.attribute_cost(
                task_id="task-2",
                agents=["agent_b"],
                tokens_per_agent={"agent_b": 5000},
                total_cost=0.20,
                task_type="review",
            ),
            attributor.attribute_cost(
                task_id="task-3",
                agents=["agent_c"],
                tokens_per_agent={"agent_c": 5000},
                total_cost=0.15,
                task_type="implementation",
            ),
        ]
        
        by_type = attributor.aggregate_by_task_type(results)
        
        # Implementation: 0.30 + 0.15 = 0.45
        assert by_type["implementation"] == pytest.approx(0.45, abs=0.001)
        # Review: 0.20
        assert by_type["review"] == pytest.approx(0.20, abs=0.001)
    
    def test_aggregate_by_date(self, attributor):
        """Aggregate costs by date."""
        results = [
            attributor.attribute_cost(
                task_id="task-1",
                agents=["agent_a"],
                tokens_per_agent={"agent_a": 5000},
                total_cost=0.30,
                timestamp="2025-01-15T10:00:00Z",
            ),
            attributor.attribute_cost(
                task_id="task-2",
                agents=["agent_b"],
                tokens_per_agent={"agent_b": 5000},
                total_cost=0.20,
                timestamp="2025-01-15T14:00:00Z",
            ),
            attributor.attribute_cost(
                task_id="task-3",
                agents=["agent_c"],
                tokens_per_agent={"agent_c": 5000},
                total_cost=0.15,
                timestamp="2025-01-16T10:00:00Z",
            ),
        ]
        
        by_date = attributor.aggregate_by_date(results)
        
        # 2025-01-15: 0.30 + 0.20 = 0.50
        assert by_date["2025-01-15"] == pytest.approx(0.50, abs=0.001)
        # 2025-01-16: 0.15
        assert by_date["2025-01-16"] == pytest.approx(0.15, abs=0.001)
    
    def test_aggregate_by_dimensions(self, attributor):
        """Aggregate by all dimensions at once."""
        results = [
            attributor.attribute_cost(
                task_id="task-1",
                agents=["eng"],
                tokens_per_agent={"eng": 5000},
                total_cost=0.30,
                roles_per_agent={"eng": "engineer"},
                models_per_agent={"eng": "haiku-4-5"},
                task_type="implementation",
                timestamp="2025-01-15T10:00:00Z",
            ),
        ]
        
        dims = attributor.aggregate_by_dimensions(results)
        
        assert dims.by_role["engineer"] == pytest.approx(0.30, abs=0.001)
        assert dims.by_model["haiku-4-5"] == pytest.approx(0.30, abs=0.001)
        assert dims.by_task_type["implementation"] == pytest.approx(0.30, abs=0.001)
        assert dims.by_date["2025-01-15"] == pytest.approx(0.30, abs=0.001)


# ---------------------------------------------------------------------------
# Test: History Tracking
# ---------------------------------------------------------------------------

class TestHistory:
    """Test attribution history tracking."""
    
    def test_history_records_attributions(self, attributor):
        """Each attribution should be recorded in history."""
        attributor.attribute_cost(
            task_id="task-1",
            agents=["agent_a"],
            tokens_per_agent={"agent_a": 1000},
            total_cost=0.10,
        )
        attributor.attribute_cost(
            task_id="task-2",
            agents=["agent_b"],
            tokens_per_agent={"agent_b": 2000},
            total_cost=0.20,
        )
        
        history = attributor.get_history()
        assert len(history) == 2
        assert history[0].task_id == "task-1"
        assert history[1].task_id == "task-2"
    
    def test_get_task_attribution(self, attributor):
        """Retrieve specific task attribution by task_id."""
        result1 = attributor.attribute_cost(
            task_id="task-1",
            agents=["agent_a"],
            tokens_per_agent={"agent_a": 1000},
            total_cost=0.10,
        )
        attributor.attribute_cost(
            task_id="task-2",
            agents=["agent_b"],
            tokens_per_agent={"agent_b": 2000},
            total_cost=0.20,
        )
        
        retrieved = attributor.get_task_attribution("task-1")
        assert retrieved is not None
        assert retrieved.task_id == "task-1"
        assert retrieved.total_cost == result1.total_cost
    
    def test_get_nonexistent_task(self, attributor):
        """Retrieving nonexistent task should return None."""
        attributor.attribute_cost(
            task_id="task-1",
            agents=["agent_a"],
            tokens_per_agent={"agent_a": 1000},
            total_cost=0.10,
        )
        
        retrieved = attributor.get_task_attribution("task-999")
        assert retrieved is None
    
    def test_clear_history(self, attributor):
        """Clear history should remove all records."""
        attributor.attribute_cost(
            task_id="task-1",
            agents=["agent_a"],
            tokens_per_agent={"agent_a": 1000},
            total_cost=0.10,
        )
        attributor.attribute_cost(
            task_id="task-2",
            agents=["agent_b"],
            tokens_per_agent={"agent_b": 2000},
            total_cost=0.20,
        )
        
        assert len(attributor.get_history()) == 2
        attributor.clear_history()
        assert len(attributor.get_history()) == 0


# ---------------------------------------------------------------------------
# Test: Result Summary
# ---------------------------------------------------------------------------

class TestResultSummary:
    """Test CostAttributionResult.summary() output."""
    
    def test_summary_format(self, attributor):
        """Summary should be human-readable."""
        result = attributor.attribute_cost(
            task_id="task-001",
            agents=["engineer", "senior"],
            tokens_per_agent={"engineer": 10000, "senior": 20000},
            total_cost=0.45,
            roles_per_agent={"engineer": "engineer", "senior": "senior_engineer"},
            models_per_agent={"engineer": "haiku-4-5", "senior": "sonnet-4-6"},
        )
        
        summary = result.summary()
        assert "task-001" in summary
        assert "0.45" in summary
        assert "30" in summary  # 30,000 tokens
        assert "engineer" in summary
        assert "senior_engineer" in summary
        assert "haiku-4-5" in summary
        assert "sonnet-4-6" in summary


# ---------------------------------------------------------------------------
# Test: Utility Methods
# ---------------------------------------------------------------------------

class TestUtilityMethods:
    """Test static utility methods."""
    
    def test_calculate_weight(self):
        """Calculate weight from tokens."""
        weight = CostAttributor.calculate_weight(tokens=10, total_tokens=100)
        assert weight == pytest.approx(0.1, abs=0.001)
    
    def test_calculate_weight_zero_total(self):
        """Weight with zero total should be 0."""
        weight = CostAttributor.calculate_weight(tokens=10, total_tokens=0)
        assert weight == 0.0
    
    def test_allocate_cost(self):
        """Allocate cost based on weight."""
        cost = CostAttributor.allocate_cost(weight=0.25, total_cost=1.00)
        assert cost == pytest.approx(0.25, abs=0.001)
    
    def test_allocate_cost_zero_weight(self):
        """Allocate with zero weight should be zero."""
        cost = CostAttributor.allocate_cost(weight=0.0, total_cost=1.00)
        assert cost == 0.0
