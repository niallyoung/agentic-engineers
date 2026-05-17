"""
Artifact linking and traceability for cross-lifecycle relationships.

Enables linking between:
- DELEGATE → HANDBACK (task execution)
- HANDBACK → Quality Evaluation (quality assessment)
- Quality Evaluation → Feedback/Outcome (feedback loops)
- Feedback/Outcome → Optimization (optimization recommendations)
- Task → Related Tasks (dependencies, related work)
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional
from datetime import datetime


@dataclass
class ArtifactLink:
    """Link between artifacts."""
    
    # Core fields
    link_id: str
    source_artifact_id: str
    source_artifact_type: str  # delegate, handback, quality_evaluation, feedback_outcome, optimization
    target_artifact_id: str
    target_artifact_type: str
    
    # Link type
    link_type: str  # executes, evaluates, feeds_into, recommends, depends_on, related_to
    
    # Metadata
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    description: str = ""
    
    # Traceability
    version: str = "1.0"
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "link_id": self.link_id,
            "source_artifact_id": self.source_artifact_id,
            "source_artifact_type": self.source_artifact_type,
            "target_artifact_id": self.target_artifact_id,
            "target_artifact_type": self.target_artifact_type,
            "link_type": self.link_type,
            "created_at": self.created_at,
            "description": self.description,
            "version": self.version,
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "ArtifactLink":
        """Create from dictionary."""
        return cls(
            link_id=data["link_id"],
            source_artifact_id=data["source_artifact_id"],
            source_artifact_type=data["source_artifact_type"],
            target_artifact_id=data["target_artifact_id"],
            target_artifact_type=data["target_artifact_type"],
            link_type=data["link_type"],
            created_at=data.get("created_at", datetime.utcnow().isoformat()),
            description=data.get("description", ""),
            version=data.get("version", "1.0"),
        )
    
    def validate(self) -> List[str]:
        """Validate schema."""
        errors = []
        
        if not self.link_id:
            errors.append("link_id is required")
        if not self.source_artifact_id:
            errors.append("source_artifact_id is required")
        if not self.target_artifact_id:
            errors.append("target_artifact_id is required")
        if self.source_artifact_type not in ["delegate", "handback", "quality_evaluation", "feedback_outcome", "optimization"]:
            errors.append(f"Invalid source_artifact_type: {self.source_artifact_type}")
        if self.target_artifact_type not in ["delegate", "handback", "quality_evaluation", "feedback_outcome", "optimization"]:
            errors.append(f"Invalid target_artifact_type: {self.target_artifact_type}")
        if self.link_type not in ["executes", "evaluates", "feeds_into", "recommends", "depends_on", "related_to"]:
            errors.append(f"Invalid link_type: {self.link_type}")
        
        return errors


class ArtifactLinkage:
    """Manages artifact linking and traceability."""
    
    def __init__(self):
        self.links: Dict[str, ArtifactLink] = {}
    
    def create_link(self, source_id: str, source_type: str, target_id: str, target_type: str, link_type: str, description: str = "") -> ArtifactLink:
        """Create a new artifact link."""
        link_id = f"{source_id}-{link_type}-{target_id}"
        link = ArtifactLink(
            link_id=link_id,
            source_artifact_id=source_id,
            source_artifact_type=source_type,
            target_artifact_id=target_id,
            target_artifact_type=target_type,
            link_type=link_type,
            description=description,
        )
        
        errors = link.validate()
        if errors:
            raise ValueError(f"Invalid link: {', '.join(errors)}")
        
        self.links[link_id] = link
        return link
    
    def get_links_from(self, artifact_id: str) -> List[ArtifactLink]:
        """Get all links from an artifact."""
        return [link for link in self.links.values() if link.source_artifact_id == artifact_id]
    
    def get_links_to(self, artifact_id: str) -> List[ArtifactLink]:
        """Get all links to an artifact."""
        return [link for link in self.links.values() if link.target_artifact_id == artifact_id]
    
    def get_full_chain(self, artifact_id: str) -> Dict[str, List[ArtifactLink]]:
        """Get full chain of links (upstream and downstream)."""
        return {
            "upstream": self.get_links_to(artifact_id),
            "downstream": self.get_links_from(artifact_id),
        }
