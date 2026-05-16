"""
Shadow Mode Integration Example for Orchestrator.

Demonstrates how to integrate shadow mode into the Orchestrator's task
execution pipeline to safely test new routing logic.
"""

from src.orchestration.agents.shadow_mode import (
    ShadowModeContext,
    ShadowModeAggregator,
    get_shadow_mode_config,
)
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class OrchestratorWithShadowMode:
    """
    Extended Orchestrator with shadow mode support.
    
    Demonstrates integration of shadow mode into the task execution pipeline.
    """
    
    def __init__(self):
        """Initialize orchestrator with shadow mode."""
        self.shadow_enabled, self.shadow_traffic = get_shadow_mode_config()
        logger.info(
            f"Shadow mode initialized: enabled={self.shadow_enabled}, "
            f"traffic={self.shadow_traffic}%"
        )
    
    def route_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Route a task using shadow mode for A/B testing.
        
        This example shows how to test a new routing algorithm in shadow mode
        while keeping the current routing algorithm in production.
        
        Args:
            task: Task to route
        
        Returns:
            Routing decision (from production code)
        """
        # Create shadow mode context
        shadow_ctx = ShadowModeContext(
            task_id=task['task_id'],
            traffic_percentage=self.shadow_traffic,
            enabled=self.shadow_enabled,
        )
        
        # Define production routing logic (current algorithm)
        def production_routing(task):
            """Current routing algorithm - proven, stable."""
            return self._route_task_v1(task)
        
        # Define shadow routing logic (new algorithm)
        def shadow_routing(task):
            """New routing algorithm - experimental."""
            return self._route_task_v2(task)
        
        # Execute both in parallel
        prod_routing, shadow_routing_result = shadow_ctx.execute_parallel(
            production_routing,
            shadow_routing,
            task
        )
        
        # Define custom comparison for routing decisions
        def compare_routing_decisions(prod, shadow):
            """Compare routing decisions with detailed analysis."""
            if prod == shadow:
                return {
                    'match': True,
                    'differences': None,
                }
            
            return {
                'match': False,
                'differences': {
                    'production_agent': prod.get('agent'),
                    'shadow_agent': shadow.get('agent'),
                    'production_model': prod.get('model'),
                    'shadow_model': shadow.get('model'),
                    'production_effort': prod.get('effort'),
                    'shadow_effort': shadow.get('effort'),
                },
            }
        
        # Record metrics with custom comparison
        result = shadow_ctx.record_result(compare_routing_decisions)
        
        # Save to metrics
        shadow_ctx.save_result(result)
        
        # Log summary
        if shadow_ctx.sampled:
            logger.info(
                f"Shadow mode execution: task_id={task['task_id']}, "
                f"match={result.results_match}, "
                f"prod_latency={result.production_latency_ms:.2f}ms, "
                f"shadow_latency={result.shadow_latency_ms:.2f}ms"
            )
        
        # Return production result (shadow doesn't affect output)
        return prod_routing
    
    def _route_task_v1(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Production routing algorithm (v1).
        
        Current algorithm based on task effort and complexity.
        """
        effort = task.get('effort', 'medium')
        
        # Simple routing based on effort
        routing = {
            'low': {'agent': 'engineer', 'model': 'claude-haiku-4.5'},
            'medium': {'agent': 'senior-engineer', 'model': 'claude-sonnet-4.5'},
            'high': {'agent': 'principal-engineer', 'model': 'claude-opus'},
        }
        
        decision = routing.get(effort, routing['medium'])
        decision['effort'] = effort
        decision['algorithm'] = 'v1-effort-based'
        
        return decision
    
    def _route_task_v2(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Shadow routing algorithm (v2).
        
        New algorithm based on task complexity, effort, and historical performance.
        """
        effort = task.get('effort', 'medium')
        complexity = task.get('complexity', 'medium')
        
        # More sophisticated routing considering complexity
        if effort == 'low' and complexity == 'low':
            decision = {'agent': 'engineer', 'model': 'claude-haiku-4.5'}
        elif effort == 'low' and complexity == 'high':
            decision = {'agent': 'senior-engineer', 'model': 'claude-sonnet-4.5'}
        elif effort == 'medium' and complexity == 'low':
            decision = {'agent': 'senior-engineer', 'model': 'claude-haiku-4.5'}
        elif effort == 'medium' and complexity == 'high':
            decision = {'agent': 'principal-engineer', 'model': 'claude-sonnet-4.5'}
        else:  # high effort
            decision = {'agent': 'principal-engineer', 'model': 'claude-opus'}
        
        decision['effort'] = effort
        decision['complexity'] = complexity
        decision['algorithm'] = 'v2-complexity-aware'
        
        return decision
    
    def execute_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a task with shadow mode.
        
        Args:
            task: Task to execute
        
        Returns:
            Task result
        """
        # Route task (with shadow mode)
        routing = self.route_task(task)
        
        # Execute task using routed agent/model
        logger.info(
            f"Executing task {task['task_id']} with "
            f"agent={routing['agent']}, model={routing['model']}"
        )
        
        # Actual execution would happen here
        result = {
            'task_id': task['task_id'],
            'status': 'complete',
            'routing': routing,
        }
        
        return result


# ============================================================================
# Example Usage
# ============================================================================

def example_basic_usage():
    """Example: Basic shadow mode usage."""
    print("\n" + "="*70)
    print("Example 1: Basic Shadow Mode Usage")
    print("="*70 + "\n")
    
    orchestrator = OrchestratorWithShadowMode()
    
    # Execute multiple tasks
    tasks = [
        {
            'task_id': 'task-2025-01-15-001',
            'effort': 'low',
            'complexity': 'low',
        },
        {
            'task_id': 'task-2025-01-15-002',
            'effort': 'medium',
            'complexity': 'high',
        },
        {
            'task_id': 'task-2025-01-15-003',
            'effort': 'high',
            'complexity': 'high',
        },
    ]
    
    for task in tasks:
        result = orchestrator.execute_task(task)
        print(f"Task {task['task_id']}: {result['routing']['algorithm']}")
        print(f"  Agent: {result['routing']['agent']}")
        print(f"  Model: {result['routing']['model']}")
        print()


def example_metrics_analysis():
    """Example: Analyzing shadow mode metrics."""
    print("\n" + "="*70)
    print("Example 2: Metrics Analysis")
    print("="*70 + "\n")
    
    aggregator = ShadowModeAggregator()
    
    # Get today's metrics
    metrics = aggregator.aggregate_daily()
    
    print(f"Total tasks: {metrics.total_tasks}")
    print(f"Sampled tasks: {metrics.sampled_tasks}")
    print(f"Sampling rate: {metrics.sampling_rate:.1%}")
    print()
    
    print(f"Correctness:")
    print(f"  Match rate: {metrics.match_rate:.1%}")
    print(f"  Matching: {metrics.matching_results}")
    print(f"  Mismatched: {metrics.mismatched_results}")
    print()
    
    print(f"Performance:")
    print(f"  Avg production latency: {metrics.avg_production_latency_ms:.2f}ms")
    print(f"  Avg shadow latency: {metrics.avg_shadow_latency_ms:.2f}ms")
    print(f"  Performance ratio: {metrics.avg_performance_ratio:.2f}x")
    print()
    
    # Save report
    report_path = aggregator.save_aggregated_report(metrics)
    print(f"Report saved to: {report_path}")


def example_gradual_rollout():
    """Example: Gradual rollout strategy."""
    print("\n" + "="*70)
    print("Example 3: Gradual Rollout Strategy")
    print("="*70 + "\n")
    
    rollout_phases = [
        ("Phase 1", 1, "Monitor for obvious errors"),
        ("Phase 2", 5, "Expand to 5% for better coverage"),
        ("Phase 3", 10, "Standard 10% traffic"),
        ("Phase 4", 25, "Quarter of traffic"),
        ("Phase 5", 50, "Half of traffic"),
        ("Phase 6", 100, "Full rollout - promote to production"),
    ]
    
    for phase, traffic, description in rollout_phases:
        print(f"{phase}: {traffic}% traffic")
        print(f"  {description}")
        print(f"  Expected tasks sampled per 1000: {traffic}")
        print()


def example_error_handling():
    """Example: Error handling in shadow mode."""
    print("\n" + "="*70)
    print("Example 4: Error Handling")
    print("="*70 + "\n")
    
    from src.orchestration.agents.shadow_mode import ShadowModeContext
    
    ctx = ShadowModeContext(
        task_id="task-error-handling",
        traffic_percentage=100,
        enabled=True,
    )
    
    def production_func():
        """Production code - must succeed."""
        return {"status": "success"}
    
    def shadow_func():
        """Shadow code - errors are caught."""
        raise RuntimeError("Shadow code has a bug")
    
    # Execute - production succeeds, shadow error is caught
    prod_result, shadow_result = ctx.execute_parallel(
        production_func,
        shadow_func,
    )
    
    print(f"Production result: {prod_result}")
    print(f"Shadow result: {shadow_result}")
    print(f"Shadow error: {ctx.shadow_error}")
    print()
    print("✅ Production succeeded despite shadow error")
    print("✅ Shadow error was logged but didn't affect production")


def example_custom_comparison():
    """Example: Custom result comparison."""
    print("\n" + "="*70)
    print("Example 5: Custom Result Comparison")
    print("="*70 + "\n")
    
    from src.orchestration.agents.shadow_mode import ShadowModeContext
    
    ctx = ShadowModeContext(
        task_id="task-custom-compare",
        traffic_percentage=100,
        enabled=True,
    )
    
    def production_func():
        return {"route": "api-v1", "latency": 45}
    
    def shadow_func():
        return {"route": "api-v2", "latency": 52}
    
    # Execute
    prod_result, shadow_result = ctx.execute_parallel(
        production_func,
        shadow_func,
    )
    
    # Define custom comparison
    def compare_routing(prod, shadow):
        """Compare routing decisions with tolerance."""
        same_route = prod.get('route') == shadow.get('route')
        latency_diff = abs(prod.get('latency', 0) - shadow.get('latency', 0))
        
        return {
            'match': same_route,
            'differences': {
                'same_route': same_route,
                'latency_diff': latency_diff,
                'prod_route': prod.get('route'),
                'shadow_route': shadow.get('route'),
            },
        }
    
    # Record with custom comparison
    result = ctx.record_result(compare_routing)
    
    print(f"Production route: {prod_result['route']}")
    print(f"Shadow route: {shadow_result['route']}")
    print(f"Routes match: {result.results_match}")
    print(f"Latency difference: {abs(prod_result['latency'] - shadow_result['latency'])}ms")


if __name__ == "__main__":
    # Run examples
    example_basic_usage()
    example_gradual_rollout()
    example_error_handling()
    example_custom_comparison()
    example_metrics_analysis()
    
    print("\n" + "="*70)
    print("Examples completed!")
    print("="*70 + "\n")
