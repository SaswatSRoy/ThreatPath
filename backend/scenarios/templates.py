"""
Canonical Starter Scenarios for the Custom Scenario Lab
"""
from typing import Dict, Any

CANONICAL_ENDPOINT_SCENARIO: Dict[str, Any] = {
    "schema_version": "1.0",
    "name": "Suspicious PowerShell Execution on Workstation",
    "description": "Synthetic endpoint telemetry: An engineer workstation spawned PowerShell with execution policy bypass flags. Observed suspicious command, but no confirmed C2 network beacon.",
    "alert": {
        "id": "alert-custom-001",
        "title": "Suspicious PowerShell Command Line Observed",
        "severity": "HIGH",
        "status": "NEW",
        "description": "Endpoint sensor detected powershell.exe executed with suspicious bypass parameters.",
        "source": "CUSTOM_SCENARIO",
        "alert_type": "unusual_execution"
    },
    "entities": [
        {
            "id": "event-custom-001",
            "label": "Event",
            "properties": {
                "event_type": "process_execution",
                "action_status": "DETECTED",
                "description": "PowerShell spawned with ExecutionPolicy Bypass parameters"
            }
        },
        {
            "id": "host-custom-001",
            "label": "Host",
            "properties": {
                "hostname": "workstation-17.corp.internal",
                "environment": "endpoint",
                "os": "Windows 11 Enterprise",
                "isolated": False
            }
        },
        {
            "id": "id-custom-001",
            "label": "Identity",
            "properties": {
                "username": "alex.morgan",
                "role": "Software Developer",
                "privilege_level": "STANDARD"
            }
        },
        {
            "id": "proc-custom-001",
            "label": "Process",
            "properties": {
                "name": "powershell.exe",
                "command_line": "powershell.exe -NoProfile -ExecutionPolicy Bypass -Command Get-Process",
                "pid": 4820,
                "executed_by": "alex.morgan"
            }
        },
        {
            "id": "tech-custom-001",
            "label": "Technique",
            "properties": {
                "mitre_id": "T1059.001",
                "name": "Command and Scripting Interpreter: PowerShell",
                "tactic": "Execution"
            }
        }
    ],
    "relationships": [
        {
            "from": "alert-custom-001",
            "type": "HAS_EVENT",
            "to": "event-custom-001"
        },
        {
            "from": "event-custom-001",
            "type": "OCCURRED_ON",
            "to": "host-custom-001"
        },
        {
            "from": "event-custom-001",
            "type": "INVOLVES_IDENTITY",
            "to": "id-custom-001"
        },
        {
            "from": "event-custom-001",
            "type": "INVOLVES_PROCESS",
            "to": "proc-custom-001"
        },
        {
            "from": "host-custom-001",
            "type": "EXECUTED",
            "to": "proc-custom-001"
        },
        {
            "from": "event-custom-001",
            "type": "MAPS_TO",
            "to": "tech-custom-001"
        }
    ]
}
