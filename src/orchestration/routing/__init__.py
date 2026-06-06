"""Routing subsystem — task → (role, model, effort, budget) decisions."""

from .model_router import (
    ModelRouter,
    RoutingDecision,
    RoutingRule,
    load_default_router,
)

__all__ = [
    "ModelRouter",
    "RoutingDecision",
    "RoutingRule",
    "load_default_router",
]
