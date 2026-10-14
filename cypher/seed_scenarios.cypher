// ThreatPath Scenario Seed Script
// Each scenario is a self-contained Cypher transaction block maintaining entity variable scope.

// --- SCENARIO_A ---
MERGE (a1:Alert {id: "alert-sec-001"})
SET a1.title = "Suspicious Interactive Logon & Beaconing Activity",
    a1.description = "DevOps user authenticated via RDP followed by encoded PowerShell execution and external network beaconing to known C2 IP.",
    a1.severity = "CRITICAL",
    a1.status = "NEW",
    a1.timestamp = "2026-10-14T03:14:22Z",
    a1.source = "EDR-CrowdProtect",
    a1.alert_type = "unusual_execution"
MERGE (e1:Event {id: "evt-101"})
SET e1.event_type = "interactive_logon",
    e1.timestamp = "2026-10-14T03:14:00Z",
    e1.description = "Remote interactive login via RDP from unknown subnet outside normal working hours",
    e1.action_status = "SUCCESS"
MERGE (i1:Identity {id: "id-jdoe"})
SET i1.username = "jdoe",
    i1.email = "jdoe@corp.internal",
    i1.role = "DevOps Engineer",
    i1.department = "Cloud Platform",
    i1.privilege_level = "ELEVATED"
MERGE (h1:Host {id: "host-jump-prod-01"})
SET h1.hostname = "jump-prod-01.corp.internal",
    h1.ip_address = "10.0.10.15",
    h1.os = "Windows Server 2022",
    h1.environment = "production",
    h1.isolated = false
MERGE (p1:Process {id: "proc-powershell-enc"})
SET p1.name = "powershell.exe",
    p1.pid = 4892,
    p1.command_line = "powershell.exe -NonI -W Hidden -enc SQBFAFgA...",
    p1.hash = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    p1.executed_by = "jdoe"
MERGE (ind1:Indicator {id: "ind-c2-ip"})
SET ind1.value = "198.51.100.44",
    ind1.indicator_type = "ipv4",
    ind1.reputation = "MALICIOUS",
    ind1.malicious_score = 95
MERGE (t1:Technique {id: "tech-t1059-001"})
SET t1.mitre_id = "T1059.001",
    t1.name = "Command and Scripting Interpreter: PowerShell",
    t1.tactic = "Execution",
    t1.description = "Adversaries may abuse PowerShell commands and scripts for execution."
MERGE (t2:Technique {id: "tech-t1078"})
SET t2.mitre_id = "T1078",
    t2.name = "Valid Accounts",
    t2.tactic = "Defense Evasion",
    t2.description = "Adversaries may obtain and abuse credentials of existing accounts."
MERGE (ast1:Asset {id: "asset-customer-db"})
SET ast1.name = "Customer Records Database",
    ast1.asset_type = "database_cluster",
    ast1.criticality = "CRITICAL",
    ast1.data_classification = "Restricted PII"
MERGE (a1)-[:HAS_EVENT]->(e1)
MERGE (e1)-[:INVOLVES_IDENTITY]->(i1)
MERGE (e1)-[:OCCURRED_ON]->(h1)
MERGE (e1)-[:INVOLVES_PROCESS]->(p1)
MERGE (h1)-[:EXECUTED]->(p1)
MERGE (p1)-[:CONNECTED_TO]->(ind1)
MERGE (e1)-[:MAPS_TO]->(t1)
MERGE (e1)-[:MAPS_TO]->(t2)
MERGE (h1)-[:CAN_ACCESS]->(ast1);

// --- SCENARIO_B ---
MERGE (a2:Alert {id: "alert-sec-002"})
SET a2.title = "Off-Hours Portal Access from Anomalous Geolocation",
    a2.description = "Frontend engineer logged into internal authentication portal from a novel IP ASN during off-hours.",
    a2.severity = "LOW",
    a2.status = "NEW",
    a2.timestamp = "2026-10-14T02:22:10Z",
    a2.source = "Okta-Identity-Log",
    a2.alert_type = "anomalous_login"
MERGE (e2:Event {id: "evt-201"})
SET e2.event_type = "sso_auth",
    e2.timestamp = "2026-10-14T02:22:00Z",
    e2.description = "Web SSO authentication succeeded with valid MFA token",
    e2.action_status = "SUCCESS"
MERGE (i2:Identity {id: "id-mchen"})
SET i2.username = "mchen",
    i2.email = "mchen@corp.internal",
    i2.role = "Frontend Developer",
    i2.department = "Engineering",
    i2.privilege_level = "STANDARD"
MERGE (h2:Host {id: "host-auth-portal-01"})
SET h2.hostname = "auth-gateway.corp.internal",
    h2.ip_address = "10.0.4.50",
    h2.os = "Ubuntu 24.04 LTS",
    h2.environment = "production",
    h2.isolated = false
MERGE (a2)-[:HAS_EVENT]->(e2)
MERGE (e2)-[:INVOLVES_IDENTITY]->(i2)
MERGE (e2)-[:OCCURRED_ON]->(h2);

// --- SCENARIO_C ---
MERGE (a3:Alert {id: "alert-sec-003"})
SET a3.title = "Vulnerability Disclosure: Critical RCE on External Gateway",
    a3.description = "Vulnerability scan detected unpatched Apache Struts component (CVE-2023-50164, CVSS 9.8). No signs of exploitation observed.",
    a3.severity = "HIGH",
    a3.status = "NEW",
    a3.timestamp = "2026-10-14T06:00:00Z",
    a3.source = "Tenable-Scanner",
    a3.alert_type = "vulnerability_exposure"
MERGE (e3:Event {id: "evt-301"})
SET e3.event_type = "vuln_scan_finding",
    e3.timestamp = "2026-10-14T05:50:00Z",
    e3.description = "Automated package inspection verified installed Struts version vulnerable to CVE-2023-50164",
    e3.action_status = "DETECTED"
MERGE (h3:Host {id: "host-web-dmz-02"})
SET h3.hostname = "api-gw-dmz-02.corp.internal",
    h3.ip_address = "10.0.2.22",
    h3.os = "Alpine Linux 3.19",
    h3.environment = "dmz",
    h3.isolated = false
MERGE (s3:Software {id: "soft-struts"})
SET s3.name = "Apache Struts",
    s3.version = "2.5.20",
    s3.vendor = "Apache Software Foundation"
MERGE (v3:Vulnerability {id: "vuln-cve-2023-50164"})
SET v3.cve_id = "CVE-2023-50164",
    v3.cvss_score = 9.8,
    v3.cisa_kev = true,
    v3.description = "Apache Struts File Upload Remote Code Execution vulnerability"
MERGE (ast3:Asset {id: "asset-payment-api"})
SET ast3.name = "Payment Gateway Core",
    ast3.asset_type = "internal_api",
    ast3.criticality = "HIGH",
    ast3.data_classification = "PCI-DSS"
MERGE (p3:Process {id: "proc-java-normal"})
SET p3.name = "java",
    p3.pid = 1042,
    p3.command_line = "/usr/bin/java -jar /opt/app/server.jar",
    p3.hash = "4a2b918703080004d490aa102213",
    p3.executed_by = "appuser"
MERGE (a3)-[:HAS_EVENT]->(e3)
MERGE (e3)-[:OCCURRED_ON]->(h3)
MERGE (h3)-[:RUNS]->(s3)
MERGE (s3)-[:AFFECTED_BY]->(v3)
MERGE (h3)-[:CAN_ACCESS]->(ast3)
MERGE (h3)-[:EXECUTED]->(p3);

// --- SCENARIO_D ---
MERGE (a4:Alert {id: "alert-sec-004"})
SET a4.title = "Repeated Password Spray Failures on Staging Bastion",
    a4.description = "Multiple failed SSH authentications for non-existent system accounts.",
    a4.severity = "MEDIUM",
    a4.status = "NEW",
    a4.timestamp = "2026-10-14T07:10:00Z",
    a4.source = "Linux-Auditd",
    a4.alert_type = "auth_failure_burst"
MERGE (e4:Event {id: "evt-401"})
SET e4.event_type = "failed_ssh",
    e4.timestamp = "2026-10-14T07:09:00Z",
    e4.description = "5 failed SSH login attempts for invalid user guest",
    e4.action_status = "BLOCKED"
MERGE (h4:Host {id: "host-stage-bastion"})
SET h4.hostname = "bastion-stage.corp.internal",
    h4.ip_address = "10.0.99.10",
    h4.os = "Debian 12",
    h4.environment = "staging",
    h4.isolated = false
MERGE (ind_disc:Indicator {id: "ind-unrelated-scanner"})
SET ind_disc.value = "203.0.113.88",
    ind_disc.indicator_type = "ipv4",
    ind_disc.reputation = "MALICIOUS",
    ind_disc.malicious_score = 90
MERGE (a4)-[:HAS_EVENT]->(e4)
MERGE (e4)-[:OCCURRED_ON]->(h4);
