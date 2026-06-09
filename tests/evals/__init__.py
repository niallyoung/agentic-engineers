"""
tests/evals/ — Quality evaluation framework for DELEGATE and HANDBACK blocks.

This module provides comprehensive quality evaluation tests that validate:
1. DELEGATE blocks conform to QUEUE-PROTOCOL.md canonical schema
2. HANDBACK blocks conform to QUEUE-PROTOCOL.md canonical schema
3. Orchestrator routing decisions follow the AGENTS.md decision tree
4. Quality standards are met (actionable plans, measurable criteria, etc.)

Test Organization:
- conftest.py: Canonical fixtures (valid samples of each artifact type)
- test_delegate_quality_evals.py: DELEGATE-specific quality checks
- test_handback_quality_evals.py: HANDBACK-specific quality checks
- test_orchestrator_routing_evals.py: Routing decision correctness

Run all evals:
  make test-evals  (or: pytest tests/evals/ -v)

Typical output (20+ tests):
  test_delegate_quality_evals.py::TestDelegateHasRequiredFields::test_canonical_delegate_has_all_required_fields PASS
  test_delegate_quality_evals.py::TestDelegatePlanIsActionable::test_canonical_delegate_plan_is_actionable PASS
  ...
  test_orchestrator_routing_evals.py::TestRoutingDecisionTreeCompliance::test_delegate_corpus_routing_is_correct PASS

  ===== 20+ passed in 1.23s =====
"""
