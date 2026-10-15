"""
Custom Scenario Schema Definitions, Allowlists, and Validation Constraints
"""
import re
from typing import Dict, Any, List, Optional, Set
from pydantic import BaseModel, Field, ConfigDict
from backend.models import GraphData

SUPPORTED_SCHEMA_VERSIONS = {"1.0"}

ALLOWED_NODE_LABELS: Set[str] = {
    "Event",
    "Host",
    "Identity",
    "Process",
    "Indicator",
    "Technique",
    "Software",
    "Vulnerability",
    "Asset"
}

ALLOWED_RELATIONSHIPS: Set[str] = {
    "HAS_EVENT",
    "OCCURRED_ON",
    "INVOLVES_IDENTITY",
    "INVOLVES_PROCESS",
    "EXECUTED",
    "CONNECTED_TO",
    "MAPS_TO",
    "RUNS",
    "AFFECTED_BY",
    "CAN_ACCESS"
}

# Explicit domain endpoint constraints: {relation_type: (allowed_source_labels, allowed_target_labels)}
RELATIONSHIP_ENDPOINT_CONSTRAINTS: Dict[str, tuple[Set[str], Set[str]]] = {
    "HAS_EVENT": ({"Alert"}, {"Event"}),
    "OCCURRED_ON": ({"Event"}, {"Host"}),
    "INVOLVES_IDENTITY": ({"Event"}, {"Identity"}),
    "INVOLVES_PROCESS": ({"Event"}, {"Process"}),
    "EXECUTED": ({"Host"}, {"Process"}),
    "CONNECTED_TO": ({"Process"}, {"Indicator"}),
    "MAPS_TO": ({"Event"}, {"Technique"}),
    "RUNS": ({"Host"}, {"Software"}),
    "AFFECTED_BY": ({"Software"}, {"Vulnerability"}),
    "CAN_ACCESS": ({"Host"}, {"Asset"})
}

ALLOWED_SEVERITIES = {"CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"}
ALLOWED_STATUSES = {"NEW", "INVESTIGATING", "RESOLVED", "CLOSED"}

ID_REGEX = re.compile(r"^[a-zA-Z0-9_\-\.:]{1,64}$")

MAX_ENTITIES = 50
MAX_RELATIONSHIPS = 100
MAX_PROPERTY_KEY_LEN = 64
MAX_PROPERTY_VAL_LEN = 500


class ValidationErrorItem(BaseModel):
    field: str
    message: str
    code: str


class ScenarioAlert(BaseModel):
    id: str = Field(..., max_length=64, description="Alert identifier (e.g. alert-custom-001)")
    title: str = Field(..., min_length=1, max_length=200)
    severity: str = Field("HIGH", description="Severity level (CRITICAL, HIGH, MEDIUM, LOW, INFO)")
    status: str = Field("NEW", description="Alert status (NEW, INVESTIGATING, RESOLVED, CLOSED)")
    description: str = Field("", max_length=1000)
    source: str = Field("CUSTOM_SCENARIO", max_length=64)
    alert_type: Optional[str] = Field("custom_synthetic", max_length=64)


class ScenarioEntity(BaseModel):
    id: str = Field(..., max_length=64)
    label: str = Field(..., max_length=32)
    properties: Dict[str, Any] = Field(default_factory=dict)


class ScenarioRelationship(BaseModel):
    from_: str = Field(..., alias="from", max_length=64)
    type: str = Field(..., max_length=32)
    to: str = Field(..., max_length=64)
    properties: Dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(populate_by_name=True)


class CustomScenarioPayload(BaseModel):
    schema_version: str = Field("1.0", max_length=8)
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field("", max_length=1000)
    alert: ScenarioAlert
    entities: List[ScenarioEntity] = Field(default_factory=list)
    relationships: List[ScenarioRelationship] = Field(default_factory=list)


class ScenarioValidationResponse(BaseModel):
    valid: bool
    errors: List[ValidationErrorItem] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    preview: Optional[GraphData] = None


class ScenarioSummary(BaseModel):
    id: str
    name: str
    description: str
    alert_id: str
    alert_title: str
    severity: str
    created_at: str
    node_count: int
    relationship_count: int
    session_id: str


class ScenarioDetails(ScenarioSummary):
    payload: Dict[str, Any]
