"""
ThreatPath Domain and API Models
"""
from enum import Enum
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field


class CompromiseClassification(str, Enum):
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"
    SUSPICIOUS = "suspicious"
    LIKELY_COMPROMISE = "likely_compromise"


class RemediationPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class EvidenceType(str, Enum):
    OBSERVED = "observed"
    CORRELATED = "correlated"
    INFERRED = "inferred"
    MISSING = "missing"


class PolicyDecision(str, Enum):
    ALLOW = "ALLOW"
    REQUIRE_APPROVAL = "REQUIRE_APPROVAL"
    BLOCK = "BLOCK"


class ActionStatus(str, Enum):
    PROPOSED = "PROPOSED"
    VALIDATED = "VALIDATED"
    WAITING_FOR_APPROVAL = "WAITING_FOR_APPROVAL"
    APPROVED = "APPROVED"
    EXECUTING = "EXECUTING"
    VERIFYING = "VERIFYING"
    VERIFIED = "VERIFIED"
    FAILED = "FAILED"
    UNVERIFIED = "UNVERIFIED"
    DENIED = "DENIED"
    CANCELLED = "CANCELLED"


class ResponseActionType(str, Enum):
    SIMULATE_ISOLATE_HOST = "SIMULATE_ISOLATE_HOST"
    SIMULATE_DISABLE_ACCOUNT = "SIMULATE_DISABLE_ACCOUNT"
    SIMULATE_BLOCK_INDICATOR = "SIMULATE_BLOCK_INDICATOR"
    SIMULATE_ESCALATE_INCIDENT = "SIMULATE_ESCALATE_INCIDENT"


# Cytoscape-compatible Graph Representation
class GraphNode(BaseModel):
    id: str
    label: str
    category: str
    properties: Dict[str, Any] = Field(default_factory=dict)


class GraphEdge(BaseModel):
    id: str
    source: str
    target: str
    relation: str
    properties: Dict[str, Any] = Field(default_factory=dict)


class GraphData(BaseModel):
    nodes: List[GraphNode] = Field(default_factory=list)
    edges: List[GraphEdge] = Field(default_factory=list)


# Domain entities
class AlertSummary(BaseModel):
    id: str
    title: str
    description: str
    severity: str
    status: str
    timestamp: str
    source: str
    alert_type: str
    target_host: Optional[str] = None
    target_identity: Optional[str] = None


class EvidenceItem(BaseModel):
    id: str
    evidence_type: EvidenceType
    title: str
    description: str
    source_entity_id: str
    confidence: float = 1.0
    properties: Dict[str, Any] = Field(default_factory=dict)


class ScoreFactor(BaseModel):
    factor_name: str
    weight: float
    description: str
    evidence_ids: List[str] = Field(default_factory=list)


class Assessment(BaseModel):
    classification: CompromiseClassification
    raw_score: float = Field(..., description="Deterministic heuristic score between 0.0 and 1.0 (not a calibrated probability)")
    remediation_priority: RemediationPriority
    score_factors: List[ScoreFactor] = Field(default_factory=list)
    supporting_evidence_ids: List[str] = Field(default_factory=list)
    contradictory_evidence_ids: List[str] = Field(default_factory=list)
    missing_evidence: List[str] = Field(default_factory=list)
    relevant_graph_paths: List[str] = Field(default_factory=list)
    uncertainty_explanation: str


class ResponseActionRecord(BaseModel):
    id: str
    action_type: ResponseActionType
    target_entity: str
    target_type: str  # host, identity, indicator, incident
    justification: str
    policy_decision: PolicyDecision
    status: ActionStatus
    proposed_at: str
    approved_at: Optional[str] = None
    executed_at: Optional[str] = None
    verified_at: Optional[str] = None
    verification_details: Optional[str] = None
    investigation_id: Optional[str] = None


class InvestigationRecord(BaseModel):
    id: str
    alert_id: str
    started_at: str
    completed_at: Optional[str] = None
    status: str = "completed"
    mode: str = "deterministic"  # deterministic or llm
    assessment: Assessment
    narrative: str
    graph: GraphData
    recommended_action: Optional[ResponseActionRecord] = None
    provenance_path_count: int = 0


# API Payloads
class InvestigationRequest(BaseModel):
    alert_id: str
    investigation_prompt: Optional[str] = None
    use_llm: Optional[bool] = False


class ActionApprovalRequest(BaseModel):
    approver: str = "Security Analyst"
    comment: Optional[str] = None


class ActionDenialRequest(BaseModel):
    approver: str = "Security Analyst"
    reason: str
