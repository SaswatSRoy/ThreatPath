import { useState, useEffect, useCallback } from 'react';
import { Header } from './components/Header';
import { AlertQueue } from './components/AlertQueue';
import { EvidenceGraph } from './components/EvidenceGraph';
import { NodeInspectorModal } from './components/NodeInspectorModal';
import { RelationshipInspectorModal } from './components/RelationshipInspectorModal';
import { FindingsPanel } from './components/FindingsPanel';
import { ResponseActionPanel } from './components/ResponseActionPanel';
import type { AlertSummary, InvestigationRecord, GraphNode, GraphEdge, SystemHealth } from './types';
import { 
  Sparkles, 
  Network,
  Loader2,
  Send,
  AlertCircle,
  HelpCircle,
  ChevronRight
} from 'lucide-react';
import { SCENARIO_HINTS } from './constants';

export function App() {
  const [alerts, setAlerts] = useState<AlertSummary[]>([]);
  const [selectedAlert, setSelectedAlert] = useState<AlertSummary | null>(null);
  const [investigation, setInvestigation] = useState<InvestigationRecord | null>(null);
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);
  const [selectedEdge, setSelectedEdge] = useState<GraphEdge | null>(null);
  const [highlightedEntityIds, setHighlightedEntityIds] = useState<string[]>([]);
  const [prompt, setPrompt] = useState<string>('');
  const [health, setHealth] = useState<SystemHealth | null>(null);
  const [loadingAlerts, setLoadingAlerts] = useState(false);
  const [investigating, setInvestigating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Mobile / Tablet Tab Navigation (< 1024px)
  const [mobileTab, setMobileTab] = useState<'queue' | 'graph' | 'findings'>('graph');

  const fetchHealth = useCallback(async () => {
    try {
      const res = await fetch('/api/health');
      if (res.ok) {
        const data = await res.json();
        setHealth(data);
      }
    } catch (e) {
      console.error('Failed to fetch system health:', e);
    }
  }, []);

  const fetchAlerts = useCallback(async () => {
    setLoadingAlerts(true);
    try {
      const res = await fetch('/api/alerts');
      if (res.ok) {
        const data: AlertSummary[] = await res.json();
        setAlerts(data);
        if (data.length > 0) {
          setSelectedAlert(prev => {
            if (!prev) {
              const first = data[0];
              const hint = SCENARIO_HINTS[first.id];
              setPrompt(hint ? hint.defaultPrompt : `Investigate alert ${first.id} and trace attack paths.`);
              return first;
            }
            return prev;
          });
        }
      }
    } catch {
      setError('Could not connect to ThreatPath API backend.');
    } finally {
      setLoadingAlerts(false);
    }
  }, []);

  useEffect(() => {
    fetchHealth();
    fetchAlerts();
  }, [fetchHealth, fetchAlerts]);

  const handleSelectAlert = (alert: AlertSummary) => {
    setSelectedAlert(alert);
    const hint = SCENARIO_HINTS[alert.id];
    setPrompt(hint ? hint.defaultPrompt : `Investigate alert ${alert.id} and trace attack paths.`);
    setSelectedNode(null);
    setSelectedEdge(null);
    setHighlightedEntityIds([]);
    setError(null);
    // On mobile, switch to graph view
    if (window.innerWidth < 1024) {
      setMobileTab('graph');
    }
  };

  const getOrCreateSessionId = (): string => {
    try {
      let sid = sessionStorage.getItem('threatpath_session_id');
      if (!sid) {
        sid = 'session-' + Math.random().toString(36).substring(2, 10);
        sessionStorage.setItem('threatpath_session_id', sid);
      }
      return sid;
    } catch {
      return 'demo_default';
    }
  };

  const runInvestigation = async () => {
    if (!selectedAlert || investigating) return;
    setInvestigating(true);
    setError(null);
    try {
      const res = await fetch('/api/investigations', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Session-ID': getOrCreateSessionId()
        },
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
      
      // Auto-highlight supporting evidence entities
      if (invRecord.assessment.supporting_evidence_ids.length > 0) {
        setHighlightedEntityIds(invRecord.assessment.supporting_evidence_ids);
      } else {
        setHighlightedEntityIds([]);
      }
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

  // Extract entity IDs from path string to highlight them
  const handleHighlightPath = (pathStr: string) => {
    if (!investigation) return;
    // Extract entity tokens like (host-xxx), (proc-xxx), (ind-xxx) or node names
    const matchedNodeIds: string[] = [];
    investigation.graph.nodes.forEach(n => {
      if (pathStr.includes(n.id) || pathStr.includes(n.label)) {
        matchedNodeIds.push(n.id);
      }
    });

    if (matchedNodeIds.length > 0) {
      setHighlightedEntityIds(matchedNodeIds);
    } else {
      setHighlightedEntityIds(investigation.assessment.supporting_evidence_ids);
    }
  };

  const handleHighlightEntity = (entityId: string) => {
    setHighlightedEntityIds([entityId]);
    if (investigation) {
      const node = investigation.graph.nodes.find(n => n.id === entityId || n.label === entityId);
      if (node) {
        setSelectedNode(node);
      }
    }
  };

  // Compute current workflow step (1 to 4)
  const getWorkflowStep = () => {
    if (!selectedAlert) return 1;
    if (investigating) return 2;
    if (investigation) {
      if (investigation.recommended_action?.status === 'VERIFIED') return 4;
      return 3;
    }
    return 1;
  };

  const currentStep = getWorkflowStep();

  return (
    <div style={{ display: 'flex', flexDirection: 'column', minHeight: '100vh', background: 'var(--bg-primary)' }}>
      <Header health={health} />

      {/* Investigation Progress Stepper */}
      <div style={{
        background: 'rgba(13, 19, 31, 0.95)',
        borderBottom: '1px solid var(--border-subtle)',
        padding: '8px 24px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        flexWrap: 'wrap',
        gap: '12px',
        fontSize: '11px'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
          <span style={{ color: 'var(--text-dim)', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.04em' }}>
            Workflow:
          </span>

          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: currentStep >= 1 ? 'var(--accent-cyan)' : 'var(--text-dim)' }}>
            <span style={{ width: '18px', height: '18px', borderRadius: '50%', background: currentStep >= 1 ? 'rgba(56,189,248,0.2)' : 'rgba(255,255,255,0.06)', border: `1px solid ${currentStep >= 1 ? 'var(--accent-cyan)' : 'var(--border-subtle)'}`, display: 'inline-flex', alignItems: 'center', justifyContent: 'center', fontSize: '10px', fontWeight: 700 }}>
              1
            </span>
            <span>Alert Selected</span>
          </div>

          <ChevronRight size={13} color="var(--text-dim)" />

          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: currentStep >= 2 ? 'var(--accent-cyan)' : 'var(--text-dim)' }}>
            <span style={{ width: '18px', height: '18px', borderRadius: '50%', background: currentStep >= 2 ? 'rgba(56,189,248,0.2)' : 'rgba(255,255,255,0.06)', border: `1px solid ${currentStep >= 2 ? 'var(--accent-cyan)' : 'var(--border-subtle)'}`, display: 'inline-flex', alignItems: 'center', justifyContent: 'center', fontSize: '10px', fontWeight: 700 }}>
              2
            </span>
            <span>FalkorDB Traversal</span>
          </div>

          <ChevronRight size={13} color="var(--text-dim)" />

          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: currentStep >= 3 ? 'var(--accent-cyan)' : 'var(--text-dim)' }}>
            <span style={{ width: '18px', height: '18px', borderRadius: '50%', background: currentStep >= 3 ? 'rgba(56,189,248,0.2)' : 'rgba(255,255,255,0.06)', border: `1px solid ${currentStep >= 3 ? 'var(--accent-cyan)' : 'var(--border-subtle)'}`, display: 'inline-flex', alignItems: 'center', justifyContent: 'center', fontSize: '10px', fontWeight: 700 }}>
              3
            </span>
            <span>Heuristic Assessment</span>
          </div>

          <ChevronRight size={13} color="var(--text-dim)" />

          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: currentStep >= 4 ? 'var(--accent-emerald)' : 'var(--text-dim)' }}>
            <span style={{ width: '18px', height: '18px', borderRadius: '50%', background: currentStep >= 4 ? 'rgba(52,211,153,0.2)' : 'rgba(255,255,255,0.06)', border: `1px solid ${currentStep >= 4 ? 'var(--accent-emerald)' : 'var(--border-subtle)'}`, display: 'inline-flex', alignItems: 'center', justifyContent: 'center', fontSize: '10px', fontWeight: 700 }}>
              4
            </span>
            <span>Response & Verification</span>
          </div>
        </div>

        {/* Mobile Tab Switcher (< 1024px) */}
        <div className="mobile-tab-switch" style={{ display: 'none', gap: '4px' }}>
          <button
            onClick={() => setMobileTab('queue')}
            style={{
              background: mobileTab === 'queue' ? 'rgba(56, 189, 248, 0.2)' : 'transparent',
              border: `1px solid ${mobileTab === 'queue' ? 'var(--accent-cyan)' : 'transparent'}`,
              color: mobileTab === 'queue' ? 'var(--accent-cyan)' : 'var(--text-dim)',
              padding: '3px 8px',
              borderRadius: '4px',
              fontSize: '11px',
              fontWeight: 600
            }}
          >
            Alerts ({alerts.length})
          </button>
          <button
            onClick={() => setMobileTab('graph')}
            style={{
              background: mobileTab === 'graph' ? 'rgba(56, 189, 248, 0.2)' : 'transparent',
              border: `1px solid ${mobileTab === 'graph' ? 'var(--accent-cyan)' : 'transparent'}`,
              color: mobileTab === 'graph' ? 'var(--accent-cyan)' : 'var(--text-dim)',
              padding: '3px 8px',
              borderRadius: '4px',
              fontSize: '11px',
              fontWeight: 600
            }}
          >
            Graph Canvas
          </button>
          <button
            onClick={() => setMobileTab('findings')}
            style={{
              background: mobileTab === 'findings' ? 'rgba(56, 189, 248, 0.2)' : 'transparent',
              border: `1px solid ${mobileTab === 'findings' ? 'var(--accent-cyan)' : 'transparent'}`,
              color: mobileTab === 'findings' ? 'var(--accent-cyan)' : 'var(--text-dim)',
              padding: '3px 8px',
              borderRadius: '4px',
              fontSize: '11px',
              fontWeight: 600
            }}
          >
            Findings & Action
          </button>
        </div>
      </div>

      <main style={{
        flex: 1,
        padding: '20px 24px',
        display: 'grid',
        gridTemplateColumns: '320px minmax(420px, 1fr) 400px',
        gap: '20px',
        alignItems: 'start'
      }}>
        {/* Left Column: Alert Queue */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          <AlertQueue
            alerts={alerts}
            selectedAlert={selectedAlert}
            onSelectAlert={handleSelectAlert}
            loading={loadingAlerts}
            currentAssessment={investigation?.assessment}
            investigatedAlertId={investigation?.alert_id}
          />
        </div>

        {/* Center Column: Investigation Workspace & Cytoscape Graph */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          {/* Investigation Objective & Trigger Panel */}
          <div className="glass-panel" style={{ padding: '16px', display: 'flex', flexDirection: 'column', gap: '12px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Sparkles size={16} color="#c084fc" />
                <h2 style={{ fontSize: '13px', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.04em', color: 'var(--text-main)' }}>
                  Investigation Objective
                </h2>
              </div>
              {selectedAlert && (
                <span style={{ fontSize: '11px', color: 'var(--accent-cyan)', fontFamily: 'JetBrains Mono, monospace' }}>
                  Target: {selectedAlert.id}
                </span>
              )}
            </div>

            <textarea
              id="input-investigation-prompt"
              rows={2}
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              onKeyDown={(e) => {
                if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
                  e.preventDefault();
                  runInvestigation();
                }
              }}
              placeholder="Specify investigative instructions or hypotheses..."
              aria-label="Investigation objective prompt"
              style={{
                width: '100%',
                background: 'rgba(0, 0, 0, 0.4)',
                border: '1px solid var(--border-subtle)',
                borderRadius: '6px',
                padding: '10px 12px',
                color: 'var(--text-main)',
                fontSize: '12px',
                fontFamily: 'Inter, sans-serif',
                resize: 'none',
                outline: 'none'
              }}
            />

            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '8px' }}>
              <div style={{ fontSize: '11px', color: 'var(--text-dim)', display: 'flex', alignItems: 'center', gap: '4px' }}>
                <HelpCircle size={12} />
                <span>Traverses real FalkorDB paths before applying deterministic rules (Press Ctrl+Enter)</span>
              </div>
              <button
                id="btn-run-investigation"
                onClick={runInvestigation}
                disabled={investigating || !selectedAlert}
                aria-label="Run graph investigation"
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
                  boxShadow: '0 2px 10px rgba(56, 189, 248, 0.35)'
                }}
              >
                {investigating ? <Loader2 size={14} className="spin-slow" /> : <Send size={14} />}
                {investigating ? 'Traversing FalkorDB Graph...' : 'Run Graph Investigation'}
              </button>
            </div>

            {error && (
              <div style={{ background: 'rgba(225, 29, 72, 0.15)', border: '1px solid #e11d48', padding: '8px 12px', borderRadius: '6px', color: '#fb7185', fontSize: '12px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                <AlertCircle size={15} />
                <span>{error}</span>
              </div>
            )}
          </div>

          {/* Evidence Graph Canvas Panel */}
          <div className="glass-panel" style={{ padding: '16px', display: 'flex', flexDirection: 'column', gap: '10px', height: '560px', position: 'relative' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Network size={16} color="var(--accent-cyan)" />
                <h2 style={{ fontSize: '13px', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.04em', color: 'var(--text-main)' }}>
                  FalkorDB Evidence Subgraph
                </h2>
                {investigation && (
                  <span style={{ fontSize: '11px', background: 'rgba(56,189,248,0.15)', border: '1px solid rgba(56,189,248,0.3)', color: 'var(--accent-cyan)', padding: '1px 6px', borderRadius: '4px', fontWeight: 600 }}>
                    {investigation.graph.nodes.length} Nodes • {investigation.graph.edges.length} Edges
                  </span>
                )}
              </div>
              <div style={{ fontSize: '11px', color: 'var(--text-dim)' }}>
                Click node or edge to inspect • Select path to focus
              </div>
            </div>

            {/* Canvas Body */}
            <div style={{ flex: 1, position: 'relative', width: '100%', height: '100%' }}>
              <EvidenceGraph
                graphData={investigation?.graph || { nodes: [], edges: [] }}
                onSelectNode={setSelectedNode}
                selectedNode={selectedNode}
                onSelectEdge={setSelectedEdge}
                selectedEdge={selectedEdge}
                highlightedEntityIds={highlightedEntityIds}
                onClearHighlight={() => setHighlightedEntityIds([])}
              />
              <NodeInspectorModal
                node={selectedNode}
                onClose={() => setSelectedNode(null)}
              />
              <RelationshipInspectorModal
                edge={selectedEdge}
                nodes={investigation?.graph.nodes || []}
                onClose={() => setSelectedEdge(null)}
              />
            </div>
          </div>
        </div>

        {/* Right Column: Findings & Response Panel */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          <FindingsPanel
            assessment={investigation?.assessment || null}
            narrative={investigation?.narrative || ''}
            onHighlightEntity={handleHighlightEntity}
            onHighlightPath={handleHighlightPath}
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
