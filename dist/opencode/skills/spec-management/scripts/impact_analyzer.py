"""
impact_analyzer.py — Analyzes impact of proposed SPEC.md changes.

Detects:
- Affected sections and their dependencies
- Breaking changes
- Affected agent roles
- Affected workflows
- Compatibility risks
- Downstream dependencies
- Migration requirements

Author: Principal Engineer
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional


@dataclass
class ImpactAnalysis:
    """Computed analysis of change impact"""
    change_id: str
    affected_sections: List[str]
    is_breaking_change: bool
    affected_agents: List[str]
    affected_workflows: List[str]
    compatibility_risks: List[str]
    migration_required: bool
    downstream_impact: Dict[str, List[str]] = field(default_factory=dict)


class ImpactAnalyzer:
    """Analyzes impact of proposed changes."""
    
    # Section dependencies: section -> [affected_sections]
    SECTION_DEPENDENCIES = {
        "ORCHESTRATOR-FIRST EXECUTION MODEL": [
            "Implementation Requirements for Engineers",
            "DELEGATE-HANDBACK PROTOCOL",
            "Queue Mechanics"
        ],
        "Implementation Requirements": [
            "ORCHESTRATOR-FIRST EXECUTION MODEL",
            "DELEGATE-HANDBACK PROTOCOL"
        ],
        "QUEUE POLLING": [
            "Queue Mechanics",
            "Session Partitioning"
        ]
    }
    
    # Sections that affect specific agent roles
    AGENT_DEPENDENCIES = {
        "ORCHESTRATOR-FIRST EXECUTION MODEL": ["orchestrator"],
        "Implementation Requirements": ["all"],
        "DELEGATE-HANDBACK PROTOCOL": ["all"],
        "Queue Mechanics": ["orchestrator", "engineer", "senior-engineer"],
        "Approval Chain": ["lead-engineer", "principal-engineer"],
        "Authorization": ["security-engineer", "lead-engineer"],
        "QUEUE POLLING": ["orchestrator"]
    }
    
    # Workflows affected by different sections
    WORKFLOW_DEPENDENCIES = {
        "ORCHESTRATOR-FIRST EXECUTION MODEL": [
            "delegation",
            "queue_polling",
            "task_routing"
        ],
        "DELEGATE-HANDBACK PROTOCOL": [
            "proposal_submission",
            "approval_workflow",
            "change_application"
        ],
        "Approval Chain": [
            "approval_workflow",
            "escalation"
        ]
    }
    
    # Keywords that indicate breaking changes
    BREAKING_KEYWORDS = {
        "incompatible", "breaking", "must update", "required change",
        "no longer supported", "deprecated", "removed", "discontinue"
    }
    
    def analyze(self, proposal) -> ImpactAnalysis:
        """Analyze impact of proposed change.
        
        Args:
            proposal: ChangeProposal to analyze
            
        Returns:
            ImpactAnalysis with impact details
        """
        affected_sections = proposal.affected_sections if hasattr(proposal, 'affected_sections') else []
        
        # Detect breaking changes
        is_breaking = self._detect_breaking_change(proposal)
        
        # Find affected agents
        affected_agents = self._find_affected_agents(affected_sections)
        
        # Find affected workflows
        affected_workflows = self._find_affected_workflows(affected_sections)
        
        # Find compatibility risks
        compatibility_risks = self._find_compatibility_risks(proposal)
        
        # Determine if migration is required
        migration_required = (
            is_breaking or
            len(compatibility_risks) > 0 or
            (hasattr(proposal, 'migration_path') and proposal.migration_path)
        )
        
        # Map downstream dependencies
        downstream = self._map_downstream_dependencies(affected_sections)
        
        return ImpactAnalysis(
            change_id=proposal.change_id if hasattr(proposal, 'change_id') else "UNKNOWN",
            affected_sections=affected_sections,
            is_breaking_change=is_breaking,
            affected_agents=list(set(affected_agents)),  # Deduplicate
            affected_workflows=list(set(affected_workflows)),
            compatibility_risks=compatibility_risks,
            migration_required=migration_required,
            downstream_impact=downstream
        )
    
    def _detect_breaking_change(self, proposal) -> bool:
        """Detect if change is breaking.
        
        A change is breaking if:
        - Explicitly marked as breaking_change=true
        - Proposed text contains breaking keywords
        - Affects core protocol sections
        """
        # Explicit flag
        if hasattr(proposal, 'breaking_change') and proposal.breaking_change:
            return True
        
        # Check proposed text for breaking keywords
        if hasattr(proposal, 'proposed_changes'):
            for section, text in proposal.proposed_changes.items():
                text_lower = text.lower()
                if any(kw in text_lower for kw in self.BREAKING_KEYWORDS):
                    return True
        
        # Check if affecting core protocol sections
        core_sections = [
            "ORCHESTRATOR-FIRST EXECUTION MODEL",
            "DELEGATE-HANDBACK PROTOCOL"
        ]
        if hasattr(proposal, 'affected_sections'):
            for section in proposal.affected_sections:
                if section in core_sections:
                    return True
        
        return False
    
    def _find_affected_agents(self, affected_sections: List[str]) -> List[str]:
        """Find which agent roles are affected."""
        agents = set()
        for section in affected_sections:
            if section in self.AGENT_DEPENDENCIES:
                deps = self.AGENT_DEPENDENCIES[section]
                if "all" in deps:
                    agents.update([
                        "orchestrator", "engineer", "senior-engineer",
                        "lead-engineer", "principal-engineer", "security-engineer"
                    ])
                else:
                    agents.update(deps)
        return list(agents)
    
    def _find_affected_workflows(self, affected_sections: List[str]) -> List[str]:
        """Find which workflows are affected."""
        workflows = set()
        for section in affected_sections:
            if section in self.WORKFLOW_DEPENDENCIES:
                workflows.update(self.WORKFLOW_DEPENDENCIES[section])
        return list(workflows)
    
    def _find_compatibility_risks(self, proposal) -> List[str]:
        """Find compatibility risks."""
        risks = []
        
        # Breaking change risk
        if hasattr(proposal, 'breaking_change') and proposal.breaking_change:
            risks.append("Breaking change - requires agent updates")
        
        # No migration path risk
        if hasattr(proposal, 'breaking_change') and proposal.breaking_change:
            if not hasattr(proposal, 'migration_path') or not proposal.migration_path:
                risks.append("Breaking change without clear migration path")
        
        # Core protocol changes
        core_sections = [
            "ORCHESTRATOR-FIRST EXECUTION MODEL",
            "DELEGATE-HANDBACK PROTOCOL"
        ]
        if hasattr(proposal, 'affected_sections'):
            for section in proposal.affected_sections:
                if section in core_sections:
                    risks.append(f"Core protocol change: {section}")
        
        return risks
    
    def _map_downstream_dependencies(self, affected_sections: List[str]) -> Dict[str, List[str]]:
        """Map downstream dependencies."""
        dependencies = {}
        
        for section in affected_sections:
            if section in self.SECTION_DEPENDENCIES:
                dependencies[section] = self.SECTION_DEPENDENCIES[section]
        
        return dependencies
