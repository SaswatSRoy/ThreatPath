import { useState, useEffect } from 'react';
import { Header } from './components/Header';
import { EvidenceGraph } from './components/EvidenceGraph';
import { NodeInspectorModal } from './components/NodeInspectorModal';
import { FindingsPanel } from './components/FindingsPanel';
import { ResponseActionPanel } from './components/ResponseActionPanel';
import type { AlertSummary, InvestigationRecord, GraphNode, SystemHealth } from './types';
import { 
  ShieldAlert, 
  Play, 
  Sparkles, 
  Network,
  Loader2
} from 'lucide-react';

const SCENARIO_HINTS: Record<string, { label: string; tag: string; defaultPrompt: string }> = {
  'alert-sec-001': {
    label: 'Scenario A: Correlated Activity',
    tag: 'Full Multi-Hop Chain',
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

export function App() {
  const [alerts, setAlerts] = useState<AlertSummary[]>([]);
  const [selectedAlert, setSelectedAlert] = useState<AlertSummary | null>(null);
  const [investigation, setInvestigation] = useState<InvestigationRecord | null>(null);
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);
  const [prompt, setPrompt] = useState<string>('');
  const [health, setHealth] = useState<SystemHealth | null>(null);
  const [loadingAlerts, setLoadingAlerts] = useState(false);
  const [investigating, setInvestigating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchHealth();
    fetchAlerts();
  }, []);

  const fetchHealth = async () => {
    try {
      const res = await fetch('/api/health');
      if (res.ok) {
        const data = await res.json();
        setHealth(data);
      }
    } catch (e) {
      console.error('Failed to fetch system health:', e);
    }
  };

  const fetchAlerts = async () => {
    setLoadingAlerts(true);
    try {
      const res = await fetch('/api/alerts');
      if (res.ok) {
        const data: AlertSummary[] = await res.json();
        setAlerts(data);
        if (data.length > 0 && !selectedAlert) {
          handleSelectAlert(data[0]);
        }
      }
    } catch (e) {
      setError('Could not connect to ThreatPath API backend.');
    } finally {
      setLoadingAlerts(false);
    }
  };

  const handleSelectAlert = (alert: AlertSummary) => {
    setSelectedAlert(alert);
    const hint = SCENARIO_HINTS[alert.id];
    setPrompt(hint ? hint.defaultPrompt : `Investigate alert ${alert.id} and trace attack paths.`);
    setSelectedNode(null);
  };

  const runInvestigation = async () => {
    if (!selectedAlert) return;
    setInvestigating(true);
    setError(null);
    try {
      const res = await fetch('/api/investigations', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          alert_id: selectedAlert.id,
          investigation_prompt: prompt
        })
      });

      if (!res.ok) {
        const errData = await res.json();
        throw new Error(errData.detail || 'Investigation failed');
      }

      const invRecord: InvestigationRecord = await res.json();
      setInvestigation(invRecord);
    } catch (e: any) {
      setError(e.message || 'Investigation execution error');
    } finally {
      setInvestigating(false);
    }
  };

  const handleApproveAction = async (actionId: string) => {
    try {
      const res = await fetch(`/api/actions/${actionId}/approve`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ approver: 'Lead Incident Responder' })
      });
      if (res.ok) {
        const updated = await res.json();
        setInvestigation(prev => prev ? { ...prev, recommended_action: updated } : null);
      }
    } catch (e) {
      console.error('Approve failed:', e);
    }
  };

  const handleDenyAction = async (actionId: string, reason: string) => {
    try {
      const res = await fetch(`/api/actions/${actionId}/deny`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ approver: 'Lead Incident Responder', reason })
      });
      if (res.ok) {
        const updated = await res.json();
        setInvestigation(prev => prev ? { ...prev, recommended_action: updated } : null);
      }
    } catch (e) {
      console.error('Deny failed:', e);
    }
  };

  const handleExecuteAction = async (actionId: string) => {
    try {
      const res = await fetch(`/api/actions/${actionId}/execute`, {
        method: 'POST'
      });
      if (res.ok) {
        const updated = await res.json();
        setInvestigation(prev => prev ? { ...prev, recommended_action: updated } : null);
      }
    } catch (e) {
      console.error('Execute failed:', e);
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', minHeight: '100vh', background: 'var(--bg-primary)' }}>
      <Header health={health} />

      <main style={{
        flex: 1,
        padding: '20px 24px',
        display: 'grid',
        gridTemplateColumns: '320px 1fr 380px',
        gap: '20px',
        alignItems: 'start'
      }}>
        {/* Left Column: Synthetic Alerts Queue */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          <div className="glass-panel" style={{ padding: '16px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '14px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <ShieldAlert size={16} color="#38bdf8" />
                <h3 style={{ fontSize: '13px', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                  Alert Queue ({alerts.length})
                </h3>
              </div>
              <span style={{ fontSize: '11px', color: '#64748b' }}>FalkorDB Synced</span>
            </div>

            {loadingAlerts && (
              <div style={{ textAlign: 'center', padding: '20px', color: '#94a3b8' }}>
                <Loader2 size={20} className="spin-slow" style={{ margin: '0 auto 8px' }} />
                <span style={{ fontSize: '12px' }}>Loading graph alerts...</span>
              </div>
            )}

            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
              {alerts.map(a => {
                const hint = SCENARIO_HINTS[a.id];
                const isSelected = selectedAlert?.id === a.id;
                return (
                  <div
                    key={a.id}
                    id={`alert-card-${a.id}`}
                    onClick={() => handleSelectAlert(a)}
                    style={{
                      background: isSelected ? 'rgba(56, 189, 248, 0.12)' : 'rgba(0, 0, 0, 0.3)',
                      border: isSelected ? '1px solid #38bdf8' : '1px solid rgba(255, 255, 255, 0.06)',
                      borderRadius: '8px',
                      padding: '12px',
                      cursor: 'pointer',
                      transition: 'all 0.15s ease'
                    }}
                  >
                    {hint && (
                      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '6px' }}>
                        <span style={{ fontSize: '10px', color: '#38bdf8', fontWeight: 700, textTransform: 'uppercase' }}>
                          {hint.label}
                        </span>
                        <span style={{ fontSize: '9px', background: 'rgba(255,255,255,0.06)', padding: '1px 5px', borderRadius: '4px', color: '#94a3b8' }}>
                          {hint.tag}
                        </span>
                      </div>
                    )}
                    <div style={{ fontSize: '12px', fontWeight: 600, color: '#f8fafc', marginBottom: '6px', lineHeight: 1.3 }}>
                      {a.title}
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '11px', color: '#64748b' }}>
                      <span style={{
                        color: a.severity === 'CRITICAL' ? '#fb7185' : a.severity === 'HIGH' ? '#fb923c' : '#38bdf8',
                        fontWeight: 700
                      }}>
                        {a.severity}
                      </span>
                      <span>{a.source}</span>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>

        {/* Center Column: Investigation Workspace & Cytoscape Graph */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          {/* Investigation Input Panel */}
          <div className="glass-panel" style={{ padding: '16px', display: 'flex', flexDirection: 'column', gap: '12px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Sparkles size={16} color="#c084fc" />
                <span style={{ fontSize: '13px', fontWeight: 700, textTransform: 'uppercase', color: '#f1f5f9' }}>
                  Investigation Objective
                </span>
              </div>
              {selectedAlert && (
                <span style={{ fontSize: '11px', color: '#38bdf8', fontFamily: 'JetBrains Mono, monospace' }}>
                  Target: {selectedAlert.id}
                </span>
              )}
            </div>

            <textarea
              id="input-investigation-prompt"
              rows={2}
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              placeholder="Specify investigative instructions or hypotheses..."
              style={{
                width: '100%',
                background: 'rgba(0, 0, 0, 0.4)',
                border: '1px solid rgba(255, 255, 255, 0.1)',
                borderRadius: '6px',
                padding: '10px 12px',
                color: '#f8fafc',
                fontSize: '12px',
                fontFamily: 'Inter, sans-serif',
                resize: 'none',
                outline: 'none'
              }}
            />

            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div style={{ fontSize: '11px', color: '#64748b' }}>
                Agent executes multi-hop FalkorDB traversals before evaluating deterministic rules.
              </div>
              <button
                id="btn-run-investigation"
                onClick={runInvestigation}
                disabled={investigating || !selectedAlert}
                style={{
                  background: 'linear-gradient(135deg, #0284c7, #6366f1)',
                  color: '#ffffff',
                  border: 'none',
                  padding: '8px 18px',
                  borderRadius: '6px',
                  fontSize: '12px',
                  fontWeight: 600,
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px',
                  boxShadow: '0 2px 10px rgba(56, 189, 248, 0.3)'
                }}
              >
                {investigating ? <Loader2 size={14} className="spin-slow" /> : <Play size={14} />}
                Run Graph Investigation
              </button>
            </div>

            {error && (
              <div style={{ background: 'rgba(225, 29, 72, 0.15)', border: '1px solid #e11d48', padding: '8px 12px', borderRadius: '6px', color: '#fb7185', fontSize: '12px' }}>
                {error}
              </div>
            )}
          </div>

          {/* Evidence Graph Canvas */}
          <div className="glass-panel" style={{ padding: '16px', display: 'flex', flexDirection: 'column', gap: '10px', height: '540px', position: 'relative' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Network size={16} color="#38bdf8" />
                <span style={{ fontSize: '13px', fontWeight: 700, textTransform: 'uppercase', color: '#f1f5f9' }}>
                  FalkorDB Evidence Subgraph
                </span>
                {investigation && (
                  <span style={{ fontSize: '11px', background: 'rgba(56,189,248,0.15)', color: '#38bdf8', padding: '1px 6px', borderRadius: '4px' }}>
                    {investigation.graph.nodes.length} Nodes • {investigation.graph.edges.length} Edges
                  </span>
                )}
              </div>
              <div style={{ fontSize: '11px', color: '#64748b' }}>
                Interactive Cytoscape.js • Click any node to inspect properties
              </div>
            </div>

            <div style={{ flex: 1, position: 'relative', width: '100%', height: '100%' }}>
              <EvidenceGraph
                graphData={investigation?.graph || { nodes: [], edges: [] }}
                onSelectNode={setSelectedNode}
                selectedNode={selectedNode}
              />
              <NodeInspectorModal
                node={selectedNode}
                onClose={() => setSelectedNode(null)}
              />
            </div>
          </div>
        </div>

        {/* Right Column: Findings & Response Panel */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          <FindingsPanel
            assessment={investigation?.assessment || null}
            narrative={investigation?.narrative || ''}
          />

          <ResponseActionPanel
            action={investigation?.recommended_action || null}
            onApprove={handleApproveAction}
            onDeny={handleDenyAction}
            onExecute={handleExecuteAction}
          />
        </div>
      </main>
    </div>
  );
}

export default App;
