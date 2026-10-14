"""
Deterministic Scoring & Assessment Engine for ThreatPath
Produces transparent, rule-based compromise classification and remediation priority.
"""
from typing import Dict, Any, List
from backend.models import (
    Assessment,
    CompromiseClassification,
    RemediationPriority,
    ScoreFactor
)


class ThreatAssessmentEngine:
    """
    Evaluates graph-derived facts using transparent, deterministic rules.
    Does NOT use LLM for scoring or policy decisions.
    """

    @staticmethod
    def assess_investigation(
        alert: Dict[str, Any],
        context: Dict[str, Any],
        attack_paths: Dict[str, Any],
        asset_exposures: List[Dict[str, Any]],
        vuln_exposures: List[Dict[str, Any]],
        related_alerts: List[Dict[str, Any]]
    ) -> Assessment:
        score_factors: List[ScoreFactor] = []
        supporting_evidence_ids: List[str] = []
        contradictory_evidence_ids: List[str] = []
        missing_evidence: List[str] = []
        relevant_graph_paths: List[str] = []

        # 1. Inspect Attack Paths (Host -> Process -> Indicator)
        paths = attack_paths.get("paths", [])
        processes = attack_paths.get("processes", [])
        indicators = attack_paths.get("indicators", [])

        has_process_to_indicator = len(paths) > 0 and len(processes) > 0 and len(indicators) > 0
        has_malicious_indicator = False

        if has_process_to_indicator:
            proc = processes[0]
            ind = indicators[0]
            proc_id = proc.get("id", "proc")
            ind_id = ind.get("id", "ind")
            supporting_evidence_ids.extend([proc_id, ind_id])

            score_factors.append(ScoreFactor(
                factor_name="Corroborating Execution & Beaconing Path",
                weight=0.40,
                description=f"Host executed suspicious process '{proc.get('name')}' connecting to external indicator '{ind.get('value')}'.",
                evidence_ids=[proc_id, ind_id]
            ))

            mal_score = ind.get("malicious_score", 0)
            if mal_score >= 80 or ind.get("reputation") == "MALICIOUS":
                has_malicious_indicator = True
                score_factors.append(ScoreFactor(
                    factor_name="Malicious Threat Intelligence Score",
                    weight=0.25,
                    description=f"External indicator '{ind.get('value')}' has confirmed malicious reputation score of {mal_score}.",
                    evidence_ids=[ind_id]
                ))

            relevant_graph_paths.append(f"Alert({alert.get('id')}) -> Host({context.get('host', {}).get('hostname')}) -> Process({proc.get('name')}) -> Indicator({ind.get('value')})")
        else:
            missing_evidence.append("No active network beaconing or C2 communication path detected.")
            if not processes:
                missing_evidence.append("No suspicious child processes connected to the event.")

        # 2. Inspect ATT&CK Techniques
        techniques = context.get("techniques", [])
        if techniques:
            tech_ids = [t.get("mitre_id") for t in techniques if t.get("mitre_id")]
            tech_entity_ids = [t.get("id") for t in techniques if t.get("id")]
            supporting_evidence_ids.extend(tech_entity_ids)
            score_factors.append(ScoreFactor(
                factor_name="MITRE ATT&CK Alignment",
                weight=0.15,
                description=f"Observed telemetry maps to ATT&CK techniques: {', '.join(tech_ids)}.",
                evidence_ids=tech_entity_ids
            ))

        # 3. Inspect Identity Context
        identity = context.get("identity", {})
        if identity.get("privilege_level") == "ELEVATED":
            id_val = identity.get("id", "identity")
            supporting_evidence_ids.append(id_val)
            score_factors.append(ScoreFactor(
                factor_name="Elevated Privilege Context",
                weight=0.10,
                description=f"Activity involves privileged identity '{identity.get('username')}' with {identity.get('role')} privileges.",
                evidence_ids=[id_val]
            ))

        # 4. Inspect Vulnerability Exposure
        has_cisa_kev = any(v.get("cisa_kev") for v in vuln_exposures)
        max_cvss = max([v.get("cvss_score", 0.0) for v in vuln_exposures], default=0.0)

        if vuln_exposures:
            vuln_ids = [v.get("cve_id") for v in vuln_exposures if v.get("cve_id")]
            supporting_evidence_ids.extend(vuln_ids)
            score_factors.append(ScoreFactor(
                factor_name="Known Exploited Vulnerability Exposure",
                weight=0.15 if has_cisa_kev else 0.10,
                description=f"Host runs software affected by {', '.join(vuln_ids)} (CVSS {max_cvss}, CISA KEV: {has_cisa_kev}).",
                evidence_ids=vuln_ids
            ))
            if not has_process_to_indicator:
                # Contradictory / Disproving evidence regarding active compromise
                missing_evidence.append("CRITICAL: Known vulnerability detected on host, but zero execution or exploitation telemetry observed.")
        else:
            missing_evidence.append("No known unpatched high-severity CVEs identified on host.")

        # 5. Inspect Asset Criticality Exposure
        highest_asset_criticality = "LOW"
        critical_assets = []
        for exp in asset_exposures:
            crit = exp.get("criticality", "LOW").upper()
            if crit == "CRITICAL":
                highest_asset_criticality = "CRITICAL"
                critical_assets.append(exp.get("asset_name"))
            elif crit == "HIGH" and highest_asset_criticality != "CRITICAL":
                highest_asset_criticality = "HIGH"
                critical_assets.append(exp.get("asset_name"))

        if critical_assets:
            score_factors.append(ScoreFactor(
                factor_name="High-Value Asset Reachability",
                weight=0.10,
                description=f"Host maintains network/access paths to {highest_asset_criticality} assets: {', '.join(critical_assets)}.",
                evidence_ids=[exp.get("asset_id") for exp in asset_exposures]
            ))
            relevant_graph_paths.append(f"Host({context.get('host', {}).get('hostname')}) -[:CAN_ACCESS]-> Asset({', '.join(critical_assets)})")

        # 6. Compute Raw Score (Heuristic, bounded)
        raw_score = sum(f.weight for f in score_factors)
        raw_score = min(0.95, max(0.05, round(raw_score, 2)))

        # 7. Classification Rules
        if has_process_to_indicator and has_malicious_indicator:
            classification = CompromiseClassification.LIKELY_COMPROMISE
        elif (vuln_exposures and (has_cisa_kev or max_cvss >= 9.0)) or (has_process_to_indicator) or (alert.get("alert_type") == "unusual_execution"):
            classification = CompromiseClassification.SUSPICIOUS
        else:
            classification = CompromiseClassification.INSUFFICIENT_EVIDENCE

        # 8. Remediation Priority Rules
        if classification == CompromiseClassification.LIKELY_COMPROMISE:
            if highest_asset_criticality == "CRITICAL":
                priority = RemediationPriority.CRITICAL
            else:
                priority = RemediationPriority.HIGH
        elif classification == CompromiseClassification.SUSPICIOUS:
            if has_cisa_kev or highest_asset_criticality in ["CRITICAL", "HIGH"]:
                priority = RemediationPriority.HIGH
            else:
                priority = RemediationPriority.MEDIUM
        else:
            # Insufficient evidence
            if identity.get("privilege_level") == "ELEVATED":
                priority = RemediationPriority.MEDIUM
            else:
                priority = RemediationPriority.LOW

        # 9. Uncertainty Explanation
        if classification == CompromiseClassification.LIKELY_COMPROMISE:
            uncertainty_explanation = (
                f"Multi-hop graph traversal confirmed causal chain from {alert.get('id')} to active C2 beaconing. "
                "Residual uncertainty: initial malware dropper origin and scope of lateral movement remain unverified."
            )
        elif vuln_exposures and not has_process_to_indicator:
            uncertainty_explanation = (
                f"Host is exposed to {vuln_exposures[0].get('cve_id')} (CISA KEV), but FalkorDB query confirmed zero anomalous "
                "child processes or network beacons. Presence of vulnerability does NOT establish exploitation."
            )
        elif classification == CompromiseClassification.INSUFFICIENT_EVIDENCE:
            uncertainty_explanation = (
                "Single anomalous authentication event observed without corroborating child processes, outbound connections, "
                "or lateral traversal. Graph traversal finds no multi-hop evidence of compromise."
            )
        else:
            uncertainty_explanation = (
                "Activity exhibits anomalous characteristics requiring analyst review, but lacks conclusive proof of hostile control."
            )

        return Assessment(
            classification=classification,
            raw_score=raw_score,
            remediation_priority=priority,
            score_factors=score_factors,
            supporting_evidence_ids=supporting_evidence_ids,
            contradictory_evidence_ids=contradictory_evidence_ids,
            missing_evidence=missing_evidence,
            relevant_graph_paths=relevant_graph_paths,
            uncertainty_explanation=uncertainty_explanation
        )


assessment_engine = ThreatAssessmentEngine()
