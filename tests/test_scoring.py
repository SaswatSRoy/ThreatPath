"""
Unit tests for ThreatPath Deterministic Assessment Engine
"""
import pytest
from backend.scoring import assessment_engine
from backend.models import CompromiseClassification, RemediationPriority


def test_scenario_a_scoring_correlated_activity():
    """
    Scenario A: Host executes suspicious process beaconing to malicious C2 IP,
    with access to critical customer database.
    Expected: LIKELY_COMPROMISE, CRITICAL priority.
    """
    alert = {"id": "alert-sec-001", "severity": "CRITICAL", "alert_type": "unusual_execution"}
    context = {
        "host": {"hostname": "jump-prod-01.corp.internal"},
        "identity": {"username": "jdoe", "role": "DevOps Engineer", "privilege_level": "ELEVATED"},
        "techniques": [{"id": "t1", "mitre_id": "T1059.001"}]
    }
    attack_paths = {
        "paths": ["mock_path"],
        "processes": [{"id": "proc-1", "name": "powershell.exe"}],
        "indicators": [{"id": "ind-1", "value": "198.51.100.44", "reputation": "MALICIOUS", "malicious_score": 95}]
    }
    asset_exposures = [{"asset_id": "ast-1", "asset_name": "Customer Records DB", "criticality": "CRITICAL"}]
    vuln_exposures = []
    related_alerts = []

    result = assessment_engine.assess_investigation(
        alert, context, attack_paths, asset_exposures, vuln_exposures, related_alerts
    )

    assert result.classification == CompromiseClassification.LIKELY_COMPROMISE
    assert result.remediation_priority == RemediationPriority.CRITICAL
    assert result.raw_score >= 0.80
    assert "ind-1" in result.supporting_evidence_ids
    assert len(result.relevant_graph_paths) >= 2


def test_scenario_b_scoring_insufficient_evidence():
    """
    Scenario B: Off-hours login with no child processes, no C2 connection, no critical asset exposure.
    Expected: INSUFFICIENT_EVIDENCE, LOW priority.
    """
    alert = {"id": "alert-sec-002", "severity": "LOW", "alert_type": "anomalous_login"}
    context = {
        "host": {"hostname": "auth-gateway.corp.internal"},
        "identity": {"username": "mchen", "role": "Frontend Developer", "privilege_level": "STANDARD"},
        "techniques": []
    }
    attack_paths = {"paths": [], "processes": [], "indicators": []}
    asset_exposures = []
    vuln_exposures = []
    related_alerts = []

    result = assessment_engine.assess_investigation(
        alert, context, attack_paths, asset_exposures, vuln_exposures, related_alerts
    )

    assert result.classification == CompromiseClassification.INSUFFICIENT_EVIDENCE
    assert result.remediation_priority == RemediationPriority.LOW
    assert result.raw_score <= 0.20
    assert any("No active network beaconing" in m for m in result.missing_evidence)


def test_scenario_c_scoring_vulnerable_not_compromised():
    """
    Scenario C: Known Exploited Vulnerability (Apache Struts, CISA KEV) on host with payment gateway access,
    but ZERO malicious child processes or C2 beaconing.
    Expected: SUSPICIOUS (NOT likely_compromise), HIGH priority.
    Must distinguish vulnerability from exploitation!
    """
    alert = {"id": "alert-sec-003", "severity": "HIGH", "alert_type": "vulnerability_exposure"}
    context = {
        "host": {"hostname": "api-gw-dmz-02.corp.internal"},
        "identity": {},
        "techniques": []
    }
    attack_paths = {"paths": [], "processes": [], "indicators": []}
    asset_exposures = [{"asset_id": "ast-3", "asset_name": "Payment Gateway Core", "criticality": "HIGH"}]
    vuln_exposures = [{
        "cve_id": "CVE-2023-50164",
        "cvss_score": 9.8,
        "cisa_kev": True,
        "software": "Apache Struts"
    }]
    related_alerts = []

    result = assessment_engine.assess_investigation(
        alert, context, attack_paths, asset_exposures, vuln_exposures, related_alerts
    )

    # Crucial acceptance criteria: Must NOT claim likely_compromise!
    assert result.classification == CompromiseClassification.SUSPICIOUS
    assert result.classification != CompromiseClassification.LIKELY_COMPROMISE
    assert result.remediation_priority == RemediationPriority.HIGH
    assert any("zero execution" in m.lower() for m in result.missing_evidence)


def test_scenario_d_disconnected_entities_not_correlated():
    """
    Scenario D: Failed authentication on bastion. Database has an independent malicious indicator,
    but there is NO graph relationship connecting them.
    Expected: INSUFFICIENT_EVIDENCE, indicator must NOT be listed in supporting evidence.
    """
    alert = {"id": "alert-sec-004", "severity": "MEDIUM", "alert_type": "auth_failure_burst"}
    context = {
        "host": {"hostname": "bastion-stage.corp.internal"},
        "identity": {},
        "techniques": []
    }
    # Disconnected indicator is NOT in the alert's attack paths
    attack_paths = {"paths": [], "processes": [], "indicators": []}
    asset_exposures = []
    vuln_exposures = []
    related_alerts = []

    result = assessment_engine.assess_investigation(
        alert, context, attack_paths, asset_exposures, vuln_exposures, related_alerts
    )

    assert result.classification == CompromiseClassification.INSUFFICIENT_EVIDENCE
    assert "ind-unrelated-scanner" not in result.supporting_evidence_ids


def test_scenario_d_narrative_grounding_no_fake_user_or_single_event():
    """
    Regression Test for Issue 1 & 4:
    Scenario D describes repeated SSH password spray failures (failed_ssh, BLOCKED).
    1. Scoring uncertainty must reflect blocked/spray activity and NEVER claim 'single anomalous authentication'.
    2. Narrative must not invent a fake 'Unknown User (STANDARD)'.
    """
    from backend.agent.llm_provider import DeterministicFallbackProvider

    alert = {
        "id": "alert-sec-004",
        "title": "High Volume Failed SSH Logons (External Password Spray)",
        "severity": "MEDIUM",
        "alert_type": "auth_failure_burst"
    }
    context = {
        "host": {"hostname": "bastion-stage.corp.internal", "environment": "staging", "os": "Linux Ubuntu 22.04"},
        "identity": {},  # No identity in graph
        "event": {
            "id": "evt-401",
            "event_type": "failed_ssh",
            "action_status": "BLOCKED",
            "description": "Repeated failed SSH logon burst from untrusted external IP; blocked by host security controls."
        },
        "techniques": [{"id": "t4", "mitre_id": "T1110.003", "name": "Password Spraying", "tactic": "Credential Access"}]
    }
    attack_paths = {"paths": [], "processes": [], "indicators": []}
    asset_exposures = []
    vuln_exposures = []
    related_alerts = []

    assessment = assessment_engine.assess_investigation(
        alert, context, attack_paths, asset_exposures, vuln_exposures, related_alerts
    )

    # 1. Uncertainty explanation must reflect actual blocked spray telemetry
    assert "single anomalous authentication" not in assessment.uncertainty_explanation.lower()
    assert "authentication failures" in assessment.uncertainty_explanation.lower() or "failed ssh" in assessment.uncertainty_explanation.lower()
    assert "blocked" in assessment.uncertainty_explanation.lower()

    # 2. Narrative must not claim an Unknown User with STANDARD privileges
    provider = DeterministicFallbackProvider()
    narrative_dict = provider.generate_investigation_narrative(alert, context, assessment)
    narrative = narrative_dict["narrative"]

    assert "Unknown User" not in narrative
    assert "None identified in graph" in narrative
    assert "single anomalous authentication" not in narrative.lower()

    # 3. Must distinguish facts, multi-hop traversals, hypotheses, and unknowns
    assert "#### 1. Observed Evidence (Direct Graph Observations)" in narrative
    assert "#### 2. Correlated Multi-Hop Relationships (Graph Traversals)" in narrative
    assert "#### 3. Analytical Inferences & Hypotheses" in narrative
    assert "#### 4. Missing Evidence & Telemetry Gaps (Unknowns)" in narrative
    assert "#### 5. Recommended Defensive Action" in narrative
    assert "[Observed Fact]" in narrative
    assert "[Hypothesis]" in narrative
    assert "[Missing Telemetry]" in narrative

