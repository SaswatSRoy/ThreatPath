"""
Pure Scenario Validator and Graph Preview Generator for ThreatPath
Performs strict schema, identifier, relationship, and endpoint type validation without database mutations.
"""
from typing import Dict, Any, List, Optional, Tuple, Set
from backend.models import GraphData, GraphNode, GraphEdge
from backend.scenarios.schema import (
    CustomScenarioPayload,
    ValidationErrorItem,
    ScenarioValidationResponse,
    ALLOWED_NODE_LABELS,
    ALLOWED_RELATIONSHIPS,
    RELATIONSHIP_ENDPOINT_CONSTRAINTS,
    ALLOWED_SEVERITIES,
    ALLOWED_STATUSES,
    SUPPORTED_SCHEMA_VERSIONS,
    ID_REGEX,
    MAX_ENTITIES,
    MAX_RELATIONSHIPS,
    MAX_PROPERTY_KEY_LEN,
    MAX_PROPERTY_VAL_LEN
)


class ScenarioValidator:
    @classmethod
    def validate(cls, raw_data: Any) -> ScenarioValidationResponse:
        errors: List[ValidationErrorItem] = []
        warnings: List[str] = []

        # 1. Type and dictionary check
        if not isinstance(raw_data, dict):
            errors.append(ValidationErrorItem(
                field="root",
                message="Scenario payload must be a JSON object.",
                code="INVALID_ROOT_TYPE"
            ))
            return ScenarioValidationResponse(valid=False, errors=errors, warnings=warnings, preview=None)

        # 2. Schema version check
        schema_version = str(raw_data.get("schema_version", ""))
        if not schema_version:
            errors.append(ValidationErrorItem(
                field="schema_version",
                message="Missing required 'schema_version' field.",
                code="MISSING_SCHEMA_VERSION"
            ))
        elif schema_version not in SUPPORTED_SCHEMA_VERSIONS:
            errors.append(ValidationErrorItem(
                field="schema_version",
                message=f"Unsupported schema version '{schema_version}'. Supported versions: {sorted(SUPPORTED_SCHEMA_VERSIONS)}",
                code="UNSUPPORTED_SCHEMA_VERSION"
            ))

        # 3. Top-level metadata
        name = raw_data.get("name")
        if not name or not isinstance(name, str) or not name.strip():
            errors.append(ValidationErrorItem(
                field="name",
                message="Scenario name is required and cannot be empty.",
                code="EMPTY_SCENARIO_NAME"
            ))
        elif len(name) > 100:
            errors.append(ValidationErrorItem(
                field="name",
                message="Scenario name must not exceed 100 characters.",
                code="SCENARIO_NAME_TOO_LONG"
            ))

        # 4. Alert validation
        alert_data = raw_data.get("alert")
        if not alert_data or not isinstance(alert_data, dict):
            errors.append(ValidationErrorItem(
                field="alert",
                message="Scenario must define an 'alert' object.",
                code="MISSING_ALERT"
            ))
            alert_id = None
        else:
            alert_id = alert_data.get("id")
            if not alert_id or not isinstance(alert_id, str) or not alert_id.strip():
                errors.append(ValidationErrorItem(
                    field="alert.id",
                    message="Alert 'id' is required.",
                    code="MISSING_ALERT_ID"
                ))
            elif not ID_REGEX.match(alert_id):
                errors.append(ValidationErrorItem(
                    field="alert.id",
                    message=f"Alert ID '{alert_id}' contains invalid characters. Use alphanumeric, dashes, dots, or underscores (max 64 chars).",
                    code="INVALID_ALERT_ID"
                ))

            alert_title = alert_data.get("title")
            if not alert_title or not isinstance(alert_title, str) or not alert_title.strip():
                errors.append(ValidationErrorItem(
                    field="alert.title",
                    message="Alert 'title' is required.",
                    code="MISSING_ALERT_TITLE"
                ))

            severity = str(alert_data.get("severity", "HIGH")).upper()
            if severity not in ALLOWED_SEVERITIES:
                errors.append(ValidationErrorItem(
                    field="alert.severity",
                    message=f"Invalid alert severity '{severity}'. Allowed: {sorted(ALLOWED_SEVERITIES)}",
                    code="INVALID_SEVERITY"
                ))

            status = str(alert_data.get("status", "NEW")).upper()
            if status not in ALLOWED_STATUSES:
                errors.append(ValidationErrorItem(
                    field="alert.status",
                    message=f"Invalid alert status '{status}'. Allowed: {sorted(ALLOWED_STATUSES)}",
                    code="INVALID_STATUS"
                ))

        # 5. Entity array validation
        entities_data = raw_data.get("entities", [])
        if not isinstance(entities_data, list):
            errors.append(ValidationErrorItem(
                field="entities",
                message="'entities' must be an array of objects.",
                code="INVALID_ENTITIES_TYPE"
            ))
            entities_data = []

        if len(entities_data) > MAX_ENTITIES:
            errors.append(ValidationErrorItem(
                field="entities",
                message=f"Too many entities ({len(entities_data)}). Maximum allowed is {MAX_ENTITIES}.",
                code="EXCEEDED_MAX_ENTITIES"
            ))

        declared_ids: Set[str] = set()
        node_type_map: Dict[str, str] = {}  # entity_id -> label
        if alert_id:
            declared_ids.add(alert_id)
            node_type_map[alert_id] = "Alert"

        for idx, ent in enumerate(entities_data):
            loc = f"entities[{idx}]"
            if not isinstance(ent, dict):
                errors.append(ValidationErrorItem(
                    field=loc,
                    message="Entity entry must be an object.",
                    code="INVALID_ENTITY_FORMAT"
                ))
                continue

            ent_id = ent.get("id")
            if not ent_id or not isinstance(ent_id, str) or not ent_id.strip():
                errors.append(ValidationErrorItem(
                    field=f"{loc}.id",
                    message="Entity missing required 'id'.",
                    code="MISSING_ENTITY_ID"
                ))
                continue

            if not ID_REGEX.match(ent_id):
                errors.append(ValidationErrorItem(
                    field=f"{loc}.id",
                    message=f"Entity ID '{ent_id}' contains invalid characters. Use alphanumeric, dashes, dots, or underscores.",
                    code="INVALID_ENTITY_ID"
                ))

            if ent_id in declared_ids:
                errors.append(ValidationErrorItem(
                    field=f"{loc}.id",
                    message=f"Duplicate entity ID detected: '{ent_id}'. All identifiers must be unique.",
                    code="DUPLICATE_ENTITY_ID"
                ))
            else:
                declared_ids.add(ent_id)

            label = ent.get("label")
            if not label or not isinstance(label, str):
                errors.append(ValidationErrorItem(
                    field=f"{loc}.label",
                    message=f"Entity '{ent_id}' missing required 'label'.",
                    code="MISSING_ENTITY_LABEL"
                ))
            elif label not in ALLOWED_NODE_LABELS:
                errors.append(ValidationErrorItem(
                    field=f"{loc}.label",
                    message=f"Entity '{ent_id}' has unsupported label '{label}'. Allowed: {sorted(ALLOWED_NODE_LABELS)}",
                    code="UNSUPPORTED_NODE_LABEL"
                ))
            else:
                node_type_map[ent_id] = label

            # Property validation
            props = ent.get("properties", {})
            if not isinstance(props, dict):
                errors.append(ValidationErrorItem(
                    field=f"{loc}.properties",
                    message=f"Properties for entity '{ent_id}' must be a dictionary.",
                    code="INVALID_PROPERTIES_FORMAT"
                ))
            else:
                for p_key, p_val in props.items():
                    if not isinstance(p_key, str) or len(p_key) > MAX_PROPERTY_KEY_LEN:
                        errors.append(ValidationErrorItem(
                            field=f"{loc}.properties.{p_key}",
                            message=f"Invalid property key '{p_key}' on entity '{ent_id}'. Must be string <= {MAX_PROPERTY_KEY_LEN} chars.",
                            code="INVALID_PROPERTY_KEY"
                        ))
                    if isinstance(p_val, (dict, list)):
                        errors.append(ValidationErrorItem(
                            field=f"{loc}.properties.{p_key}",
                            message=f"Complex nested value not allowed for property '{p_key}' on entity '{ent_id}'. Use scalar values (string, number, boolean).",
                            code="NESTED_PROPERTY_NOT_ALLOWED"
                        ))
                    elif isinstance(p_val, str) and len(p_val) > MAX_PROPERTY_VAL_LEN:
                        errors.append(ValidationErrorItem(
                            field=f"{loc}.properties.{p_key}",
                            message=f"Property value for '{p_key}' on entity '{ent_id}' exceeds maximum length of {MAX_PROPERTY_VAL_LEN}.",
                            code="PROPERTY_VALUE_TOO_LONG"
                        ))

        # 6. Relationship array validation
        rels_data = raw_data.get("relationships", [])
        if not isinstance(rels_data, list):
            errors.append(ValidationErrorItem(
                field="relationships",
                message="'relationships' must be an array of objects.",
                code="INVALID_RELATIONSHIPS_TYPE"
            ))
            rels_data = []

        if len(rels_data) > MAX_RELATIONSHIPS:
            errors.append(ValidationErrorItem(
                field="relationships",
                message=f"Too many relationships ({len(rels_data)}). Maximum allowed is {MAX_RELATIONSHIPS}.",
                code="EXCEEDED_MAX_RELATIONSHIPS"
            ))

        seen_edges: Set[Tuple[str, str, str]] = set()

        for idx, rel in enumerate(rels_data):
            loc = f"relationships[{idx}]"
            if not isinstance(rel, dict):
                errors.append(ValidationErrorItem(
                    field=loc,
                    message="Relationship entry must be an object.",
                    code="INVALID_RELATIONSHIP_FORMAT"
                ))
                continue

            from_id = rel.get("from")
            rel_type = rel.get("type")
            to_id = rel.get("to")

            if not from_id or not isinstance(from_id, str):
                errors.append(ValidationErrorItem(
                    field=f"{loc}.from",
                    message="Relationship missing required 'from' source entity ID.",
                    code="MISSING_RELATIONSHIP_FROM"
                ))

            if not to_id or not isinstance(to_id, str):
                errors.append(ValidationErrorItem(
                    field=f"{loc}.to",
                    message="Relationship missing required 'to' target entity ID.",
                    code="MISSING_RELATIONSHIP_TO"
                ))

            if not rel_type or not isinstance(rel_type, str):
                errors.append(ValidationErrorItem(
                    field=f"{loc}.type",
                    message="Relationship missing required 'type'.",
                    code="MISSING_RELATIONSHIP_TYPE"
                ))
                continue

            if rel_type not in ALLOWED_RELATIONSHIPS:
                errors.append(ValidationErrorItem(
                    field=f"{loc}.type",
                    message=f"Unsupported relationship type '{rel_type}'. Allowed: {sorted(ALLOWED_RELATIONSHIPS)}",
                    code="UNSUPPORTED_RELATIONSHIP_TYPE"
                ))
                continue

            # Check that endpoints exist in declared IDs
            from_valid = from_id in declared_ids
            to_valid = to_id in declared_ids

            if from_id and not from_valid:
                errors.append(ValidationErrorItem(
                    field=f"{loc}.from",
                    message=f"Source entity '{from_id}' was not declared in entities or alert.",
                    code="UNDECLARED_RELATIONSHIP_SOURCE"
                ))

            if to_id and not to_valid:
                errors.append(ValidationErrorItem(
                    field=f"{loc}.to",
                    message=f"Target entity '{to_id}' was not declared in entities or alert.",
                    code="UNDECLARED_RELATIONSHIP_TARGET"
                ))

            # Endpoint label constraints check
            if from_valid and to_valid and rel_type in RELATIONSHIP_ENDPOINT_CONSTRAINTS:
                from_label = node_type_map.get(from_id)
                to_label = node_type_map.get(to_id)
                allowed_from, allowed_to = RELATIONSHIP_ENDPOINT_CONSTRAINTS[rel_type]

                if from_label not in allowed_from:
                    errors.append(ValidationErrorItem(
                        field=f"{loc}.from",
                        message=f"Relationship '{rel_type}' requires source node of type {sorted(allowed_from)}, but '{from_id}' is a '{from_label}'.",
                        code="INVALID_RELATIONSHIP_SOURCE_TYPE"
                    ))

                if to_label not in allowed_to:
                    errors.append(ValidationErrorItem(
                        field=f"{loc}.to",
                        message=f"Relationship '{rel_type}' requires target node of type {sorted(allowed_to)}, but '{to_id}' is a '{to_label}'.",
                        code="INVALID_RELATIONSHIP_TARGET_TYPE"
                    ))

            # Deduplication
            if from_id and to_id and rel_type:
                edge_key = (from_id, rel_type, to_id)
                if edge_key in seen_edges:
                    warnings.append(f"Duplicate relationship detected: ({from_id})-[:{rel_type}]->({to_id}) will be merged.")
                else:
                    seen_edges.add(edge_key)

        # 7. Semantic warnings
        has_alert_event = any(r.get("type") == "HAS_EVENT" for r in rels_data if isinstance(r, dict))
        if not has_alert_event:
            warnings.append("Scenario contains no 'HAS_EVENT' relationship connecting the Alert to an Event. Investigations require at least one connected Event.")

        has_host = any(ent.get("label") == "Host" for ent in entities_data if isinstance(ent, dict))
        if not has_host:
            warnings.append("Scenario contains no Host node. Remediation containment (host isolation) will not be applicable.")

        has_indicator = any(ent.get("label") == "Indicator" for ent in entities_data if isinstance(ent, dict))
        if not has_indicator:
            warnings.append("Scenario contains no external Indicator node. C2 network correlation and IP blocking will not trigger.")

        # 8. Build GraphPreview if no fatal errors
        preview: Optional[GraphData] = None
        is_valid = len(errors) == 0

        if is_valid:
            preview_nodes: List[GraphNode] = []
            preview_edges: List[GraphEdge] = []

            # Add Alert node
            if alert_data and alert_id:
                preview_nodes.append(GraphNode(
                    id=alert_id,
                    label=alert_data.get("title", alert_id),
                    category="Alert",
                    properties={
                        "id": alert_id,
                        "title": alert_data.get("title", ""),
                        "severity": str(alert_data.get("severity", "HIGH")).upper(),
                        "status": str(alert_data.get("status", "NEW")).upper(),
                        "description": alert_data.get("description", ""),
                        "source": alert_data.get("source", "CUSTOM_SCENARIO")
                    }
                ))

            # Add Entity nodes
            for ent in entities_data:
                e_id = ent.get("id")
                e_lbl = ent.get("label", "Entity")
                e_props = ent.get("properties", {})
                display_label = (
                    e_props.get("name") or
                    e_props.get("title") or
                    e_props.get("hostname") or
                    e_props.get("username") or
                    e_props.get("value") or
                    e_props.get("mitre_id") or
                    e_props.get("cve_id") or
                    e_id
                )
                preview_nodes.append(GraphNode(
                    id=e_id,
                    label=str(display_label),
                    category=e_lbl,
                    properties={"id": e_id, **e_props}
                ))

            # Add Edges
            for idx, rel in enumerate(rels_data):
                f = rel.get("from")
                t = rel.get("to")
                r_type = rel.get("type", "RELATED_TO")
                preview_edges.append(GraphEdge(
                    id=f"preview_edge_{idx}_{f}_{t}",
                    source=f,
                    target=t,
                    relation=r_type,
                    properties=rel.get("properties", {})
                ))

            preview = GraphData(nodes=preview_nodes, edges=preview_edges)

        return ScenarioValidationResponse(
            valid=is_valid,
            errors=errors,
            warnings=warnings,
            preview=preview
        )
