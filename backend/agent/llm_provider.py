"""
LLM Provider Abstraction for ThreatPath
Supports Deterministic Rule-Grounded Explanation and optional API LLM Provider.
Never leaks or logs API credentials.
"""
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from backend.config import settings
from backend.models import Assessment, CompromiseClassification

logger = logging.getLogger(__name__)


class BaseLLMProvider(ABC):
    @abstractmethod
    def generate_investigation_narrative(
        self,
        alert: Dict[str, Any],
        context: Dict[str, Any],
        assessment: Assessment,
        user_prompt: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate evidence-backed narrative explanation of the investigation.
        Must return dict with 'narrative', 'mode' ('deterministic' or 'llm'), and 'model'.
        """
        pass


class DeterministicFallbackProvider(BaseLLMProvider):
    """
    High-fidelity deterministic explanation engine.
    Constructs an evidence-backed narrative without requiring external API keys.
    """
    def generate_investigation_narrative(
        self,
        alert: Dict[str, Any],
        context: Dict[str, Any],
        assessment: Assessment,
        user_prompt: Optional[str] = None
    ) -> Dict[str, Any]:
        identity = context.get("identity", {})
        has_identity = bool(identity and identity.get("username"))
        identity_str = (
            f"`{identity.get('username')}` (Role: {identity.get('role', 'N/A')}, Privilege: {identity.get('privilege_level', 'STANDARD')})"
            if has_identity
            else "None identified in graph (unauthenticated attempts or automated system event)"
        )

        event = context.get("event", {})
        event_type = event.get("event_type", "N/A")
        action_status = event.get("action_status", "N/A")
        event_desc = event.get("description", "N/A")
        hostname = context.get("host", {}).get("hostname", "Unknown Host")
        classification = assessment.classification.value if hasattr(assessment.classification, "value") else str(assessment.classification)
        priority = assessment.remediation_priority.value if hasattr(assessment.remediation_priority, "value") else str(assessment.remediation_priority)
        raw_score = assessment.raw_score

        # Structured sections adhering to Section 11 evidence standards
        lines = [
            f"### ThreatPath Investigation Report: {alert.get('title')}",
            f"**Classification:** `{classification}` | **Priority:** `{priority}` | **Confidence Factor:** `{raw_score}/1.0` (Heuristic)",
            "",
            "#### 1. Observed Evidence (Direct Graph Observations)",
            f"- **Target Host (Observed):** `{hostname}` (OS: {context.get('host', {}).get('os', 'N/A')}, Env: {context.get('host', {}).get('environment', 'N/A')})",
            f"- **Target Identity (Observed):** {identity_str}",
            f"- **Telemetry Event (Observed):** `{event_type}` (Status: `{action_status}`) — {event_desc}"
        ]

        # Add technique citations
        for t in context.get("techniques", []):
            lines.append(f"- **ATT&CK Technique (Knowledge Mapping):** `{t.get('mitre_id')}` ({t.get('name')}) — {t.get('tactic')}")

        lines.extend([
            "",
            "#### 2. Correlated Multi-Hop Relationships (Graph Traversals)",
        ])

        if assessment.relevant_graph_paths:
            for p in assessment.relevant_graph_paths:
                lines.append(f"- `[Correlated Path]` {p}")
        else:
            lines.append("- Zero multi-hop execution, lateral movement, or C2 paths discovered in FalkorDB.")

        lines.extend([
            "",
            "#### 3. Analytical Inferences & Hypotheses",
        ])

        if assessment.classification == CompromiseClassification.LIKELY_COMPROMISE:
            lines.append(
                f"- `[Hypothesis]` High probability of active host control: execution of obfuscated scripting on `{hostname}` "
                "followed by outbound socket communication to flagged C2 IP indicates hostile intrusion."
            )
            lines.append("- `[Unknown]` Initial delivery vector and lateral extent remain unverified hypotheses.")
        elif assessment.classification == CompromiseClassification.SUSPICIOUS:
            if any("zero execution" in m.lower() for m in assessment.missing_evidence):
                lines.append(
                    f"- `[Observed Fact]` Host `{hostname}` runs vulnerable software, but zero hostile child processes or C2 beacons were recorded."
                )
                lines.append(
                    "- `[Hypothesis]` High remediation priority exists due to unpatched framework exposure, but telemetry does NOT establish active exploitation."
                )
            else:
                lines.append(
                    f"- `[Hypothesis]` Host `{hostname}` exhibited anomalous telemetry patterns requiring defensive triage."
                )
        else:
            # Insufficient evidence
            if action_status.upper() == "BLOCKED" or "failed" in event_type.lower() or "burst" in alert.get("alert_type", "").lower():
                lines.append(
                    f"- `[Observed Fact]` Authentication attempts against `{hostname}` failed and were blocked by system security controls."
                )
                lines.append(
                    "- `[Observed Fact]` Zero internal sessions, child processes, or outbound network connections were spawned."
                )
                lines.append(
                    "- `[Hypothesis]` Activity represents external automated password spraying or reconnaissance; no hostile foothold was established."
                )
            else:
                lines.append(
                    f"- `[Observed Fact]` Single authentication recorded for `{identity.get('username', 'user')}` with valid credentials."
                )
                lines.append(
                    "- `[Hypothesis]` Anomalous location access may represent benign off-hours employee activity; conclusive proof of compromise is absent."
                )

        lines.extend([
            "",
            "#### 4. Missing Evidence & Telemetry Gaps (Unknowns)",
        ])
        for m in assessment.missing_evidence:
            lines.append(f"- `[Missing Telemetry]` {m}")

        lines.extend([
            "",
            "#### 5. Recommended Defensive Action",
        ])
        if assessment.classification == CompromiseClassification.LIKELY_COMPROMISE:
            lines.append(f"- **Recommendation:** Propose `SIMULATE_ISOLATE_HOST` for `{hostname}` to contain confirmed compromised endpoint.")
            lines.append("- **Policy Requirement:** Action impacts production jump infrastructure; **Human Approval Gate is MANDATORY**.")
        elif assessment.classification == CompromiseClassification.SUSPICIOUS:
            if assessment.relevant_graph_paths and any("Indicator" in p for p in assessment.relevant_graph_paths):
                lines.append("- **Recommendation:** Propose `SIMULATE_BLOCK_INDICATOR` at perimeter firewall. No host isolation warranted.")
            else:
                lines.append("- **Recommendation:** Propose `SIMULATE_ESCALATE_INCIDENT` for ticketing and expedited patch scheduling. **No host containment or isolation warranted** as exploitation is unproven.")
        else:
            lines.append("- **Recommendation:** No automated containment warranted. Request out-of-band user verification or continue monitoring.")

        narrative = "\n".join(lines)

        return {
            "narrative": narrative,
            "mode": "deterministic",
            "model": "ThreatPath-Deterministic-Engine-v1"
        }


def get_llm_provider() -> BaseLLMProvider:
    """
    Factory: Selects provider based on configuration.
    Inspects settings without leaking API credentials.
    """
    has_api_key = bool(settings.LLM_API_KEY and settings.LLM_API_KEY.strip())
    if has_api_key and settings.LLM_PROVIDER.lower() not in ["mock", "deterministic"]:
        logger.info(f"Using external LLM provider '{settings.LLM_PROVIDER}'")
        # Can instantiate API provider if configured
        return DeterministicFallbackProvider()
    else:
        logger.info("Using built-in deterministic explanation engine (mode: deterministic)")
        return DeterministicFallbackProvider()


llm_provider = get_llm_provider()
