export const SCENARIO_HINTS: Record<string, { label: string; tag: string; defaultPrompt: string }> = {
  'alert-sec-001': {
    label: 'Scenario A: Correlated Activity',
    tag: 'Multi-Hop Chain',
    defaultPrompt: 'Investigate anomalous off-hours RDP logon, trace child process execution, identify outbound C2 indicators, and assess critical asset exposure.'
  },
  'alert-sec-002': {
    label: 'Scenario B: Insufficient Evidence',
    tag: 'Telemetry Gaps',
    defaultPrompt: 'Analyze off-hours portal access from anomalous ASN. Trace whether any child processes or lateral movement took place.'
  },
  'alert-sec-003': {
    label: 'Scenario C: Vulnerable Not Compromised',
    tag: 'KEV vs Exploitation',
    defaultPrompt: 'Inspect unpatched Apache Struts exposure (CVE-2023-50164, CISA KEV) on DMZ gateway. Verify whether active exploitation occurred.'
  },
  'alert-sec-004': {
    label: 'Scenario D: Disconnected Entities',
    tag: 'Non-Correlation',
    defaultPrompt: 'Evaluate failed SSH password spray against staging bastion. Verify whether independent scanner IP is falsely correlated.'
  }
};

export const CATEGORY_COLORS: Record<string, { bg: string; border: string; shape: string }> = {
  Alert: { bg: '#881337', border: '#f43f5e', shape: 'diamond' },
  Event: { bg: '#78350f', border: '#f59e0b', shape: 'round-rectangle' },
  Host: { bg: '#0c4a6e', border: '#38bdf8', shape: 'rectangle' },
  Process: { bg: '#581c87', border: '#c084fc', shape: 'round-triangle' },
  Indicator: { bg: '#991b1b', border: '#ef4444', shape: 'octagon' },
  Asset: { bg: '#713f12', border: '#eab308', shape: 'barrel' },
  Technique: { bg: '#134e4a', border: '#2dd4bf', shape: 'hexagon' },
  Software: { bg: '#064e3b', border: '#34d399', shape: 'ellipse' },
  Vulnerability: { bg: '#7c2d12', border: '#fb923c', shape: 'vee' },
  Identity: { bg: '#115e59', border: '#5eead4', shape: 'round-rectangle' },
  Entity: { bg: '#1e293b', border: '#94a3b8', shape: 'ellipse' }
};

export const STARTER_SCENARIO = {
  schema_version: "1.0",
  name: "Suspicious PowerShell Execution on Workstation",
  description: "Synthetic endpoint telemetry: An engineer workstation spawned PowerShell with execution policy bypass flags. Observed suspicious command, but no confirmed C2 network beacon.",
  alert: {
    id: "alert-custom-001",
    title: "Suspicious PowerShell Command Line Observed",
    severity: "HIGH",
    status: "NEW",
    description: "Endpoint sensor detected powershell.exe executed with suspicious bypass parameters.",
    source: "CUSTOM_SCENARIO",
    alert_type: "unusual_execution"
  },
  entities: [
    {
      id: "event-custom-001",
      label: "Event",
      properties: {
        event_type: "process_execution",
        action_status: "DETECTED",
        description: "PowerShell spawned with ExecutionPolicy Bypass parameters"
      }
    },
    {
      id: "host-custom-001",
      label: "Host",
      properties: {
        hostname: "workstation-17.corp.internal",
        environment: "endpoint",
        os: "Windows 11 Enterprise",
        isolated: false
      }
    },
    {
      id: "id-custom-001",
      label: "Identity",
      properties: {
        username: "alex.morgan",
        role: "Software Developer",
        privilege_level: "STANDARD"
      }
    },
    {
      id: "proc-custom-001",
      label: "Process",
      properties: {
        name: "powershell.exe",
        command_line: "powershell.exe -NoProfile -ExecutionPolicy Bypass -Command Get-Process",
        pid: 4820,
        executed_by: "alex.morgan"
      }
    },
    {
      id: "tech-custom-001",
      label: "Technique",
      properties: {
        mitre_id: "T1059.001",
        name: "Command and Scripting Interpreter: PowerShell",
        tactic: "Execution"
      }
    }
  ],
  relationships: [
    {
      from: "alert-custom-001",
      type: "HAS_EVENT",
      to: "event-custom-001"
    },
    {
      from: "event-custom-001",
      type: "OCCURRED_ON",
      to: "host-custom-001"
    },
    {
      from: "event-custom-001",
      type: "INVOLVES_IDENTITY",
      to: "id-custom-001"
    },
    {
      from: "event-custom-001",
      type: "INVOLVES_PROCESS",
      to: "proc-custom-001"
    },
    {
      from: "host-custom-001",
      type: "EXECUTED",
      to: "proc-custom-001"
    },
    {
      from: "event-custom-001",
      type: "MAPS_TO",
      to: "tech-custom-001"
    }
  ]
};

