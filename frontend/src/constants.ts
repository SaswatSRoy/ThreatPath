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
