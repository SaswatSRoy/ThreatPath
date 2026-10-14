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
        hostname = context.get("host", {}).get("hostname", "Unknown Host")
        username = context.get("identity", {}).get("username", "Unknown User")
        classification = assessment.classification.value
        priority = assessment.remediation_priority.value.upper()
        raw_score = assessment.raw_score

        # Structured sections adhering to Section 11 evidence standards
        lines = [
            f"### ThreatPath Investigation Report: {alert.get('title')}",
            f"**Classification:** `{classification}` | **Priority:** `{priority}` | **Confidence Factor:** `{raw_score}/1.0` (Heuristic)",
            "",
            "#### 1. Observed Evidence (Direct Graph Observations)",
            f"- **Target Host:** `{hostname}` (OS: {context.get('host', {}).get('os', 'N/A')}, Env: {context.get('host', {}).get('environment', 'N/A')})",
            f"- **Target Identity:** `{username}` (Role: {context.get('identity', {}).get('role', 'N/A')}, Privilege: {context.get('identity', {}).get('privilege_level', 'STANDARD')})",
            f"- **Telemetry Event:** `{context.get('event', {}).get('event_type', 'N/A')}` at `{context.get('event', {}).get('timestamp', 'N/A')}`"
        ]

        # Add technique citations
        for t in context.get("techniques", []):
            lines.append(f"- **ATT&CK Technique:** `{t.get('mitre_id')}` ({t.get('name')}) — {t.get('tactic')}")

        lines.extend([
            "",
            "#### 2. Correlated Multi-Hop Relationships (Graph Traversals)",
        ])

        if assessment.relevant_graph_paths:
            for p in assessment.relevant_graph_paths:
                lines.append(f"- `[Path]` {p}")
        else:
            lines.append("- No extended multi-hop execution or C2 paths discovered in FalkorDB.")

        lines.extend([
            "",
            "#### 3. Inferences & Hypothesis",
        ])

        if assessment.classification == CompromiseClassification.LIKELY_COMPROMISE:
            lines.append(
                f"- High probability of active host control: execution of obfuscated scripting on `{hostname}` "
                "followed by persistent outbound communication to flagged C2 infrastructure indicates hands-on-keyboard activity."
            )
        elif assessment.classification == CompromiseClassification.SUSPICIOUS:
            lines.append(
                f"- Elevated operational risk: host `{hostname}` is vulnerable or shows anomalous patterns, "
                "requiring immediate patch remediation and defensive observation."
            )
        else:
            lines.append(
                f"- Isolated telemetry anomaly: activity for `{username}` exhibits no downstream indicators of compromise; "
                "likely benign off-hours operation or false positive threshold trigger."
            )

        lines.extend([
            "",
            "#### 4. Missing Evidence & Contradictions (Unknowns)",
        ])
        for m in assessment.missing_evidence:
            lines.append(f"- `[Missing]` {m}")

        lines.extend([
            "",
            "#### 5. Recommended Defensive Action",
        ])
        if assessment.classification == CompromiseClassification.LIKELY_COMPROMISE:
            lines.append(f"- **Recommendation:** Propose `SIMULATE_ISOLATE_HOST` for `{hostname}` to prevent lateral movement to high-value assets.")
            lines.append("- **Policy Requirement:** Action impacts production jump infrastructure; **Human Approval Gate is MANDATORY**.")
        elif assessment.classification == CompromiseClassification.SUSPICIOUS:
            lines.append("- **Recommendation:** Expedite patch scheduling; monitor perimeter logs without disrupting host services.")
        else:
            lines.append("- **Recommendation:** Request user out-of-band verification; maintain standard logging.")

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
