import React, { useState } from 'react';
import type { Assessment } from '../types';
import { 
  ShieldAlert, 
  AlertTriangle, 
  CheckCircle, 
  HelpCircle, 
  GitCommit, 
  FileText, 
  Activity,
  Crosshair,
  Info
} from 'lucide-react';

interface FindingsPanelProps {
  assessment: Assessment | null;
  narrative: string;
  onHighlightEntity?: (entityId: string) => void;
  onHighlightPath?: (pathStr: string) => void;
}

export const FindingsPanel: React.FC<FindingsPanelProps> = ({ 
  assessment, 
  narrative,
  onHighlightEntity,
  onHighlightPath
}) => {
  const [activeTab, setActiveTab] = useState<'evidence' | 'report' | 'factors'>('evidence');

  if (!assessment) {
    return (
      <div className="glass-panel" style={{ padding: '24px', textAlign: 'center', color: 'var(--text-dim)' }}>
        <Activity size={32} style={{ margin: '0 auto 12px', opacity: 0.5 }} />
        <p style={{ fontSize: '13px', color: 'var(--text-muted)' }}>
          Select an alert and run investigation to view graph-backed findings.
        </p>
      </div>
    );
  }

  const getClassificationBadge = (classification: string) => {
    switch (classification) {
      case 'likely_compromise':
        return (
          <span style={{
            background: 'rgba(225, 29, 72, 0.2)',
            color: '#fb7185',
            border: '1px solid #e11d48',
            padding: '4px 10px',
            borderRadius: '6px',
            fontSize: '11px',
            fontWeight: 700,
            display: 'inline-flex',
            alignItems: 'center',
            gap: '6px'
          }}>
            <ShieldAlert size={13} /> LIKELY COMPROMISE
          </span>
        );
      case 'suspicious':
        return (
          <span style={{
            background: 'rgba(245, 158, 11, 0.2)',
            color: '#fbbf24',
            border: '1px solid #f59e0b',
            padding: '4px 10px',
            borderRadius: '6px',
            fontSize: '11px',
            fontWeight: 700,
            display: 'inline-flex',
            alignItems: 'center',
            gap: '6px'
          }}>
            <AlertTriangle size={13} /> SUSPICIOUS ACTIVITY
          </span>
        );
      default:
        return (
          <span style={{
            background: 'rgba(56, 189, 248, 0.15)',
            color: '#38bdf8',
            border: '1px solid rgba(56, 189, 248, 0.4)',
            padding: '4px 10px',
            borderRadius: '6px',
            fontSize: '11px',
            fontWeight: 700,
            display: 'inline-flex',
            alignItems: 'center',
            gap: '6px'
          }}>
            <HelpCircle size={13} /> INSUFFICIENT EVIDENCE
          </span>
        );
    }
  };

  const getPriorityBadge = (priority: string) => {
    const colors: Record<string, { bg: string; text: string; border: string }> = {
      critical: { bg: 'rgba(225, 29, 72, 0.2)', text: '#fda4af', border: '#e11d48' },
      high: { bg: 'rgba(249, 115, 22, 0.2)', text: '#fed7aa', border: '#ea580c' },
      medium: { bg: 'rgba(234, 179, 8, 0.2)', text: '#fef08a', border: '#ca8a04' },
      low: { bg: 'rgba(34, 197, 94, 0.2)', text: '#bbf7d0', border: '#16a34a' }
    };
    const c = colors[priority.toLowerCase()] || colors.low;
    return (
      <span style={{
        background: c.bg,
        color: c.text,
        border: `1px solid ${c.border}`,
        padding: '3px 8px',
        borderRadius: '6px',
        fontSize: '11px',
        fontWeight: 700,
        textTransform: 'uppercase'
      }}>
        Priority: {priority}
      </span>
    );
  };

  // Helper to highlight markdown tags
  const renderFormattedNarrative = (text: string) => {
    return text.split('\n').map((line, idx) => {
      let content: React.ReactNode = line;

      if (line.includes('[Observed Fact]')) {
        const parts = line.split('[Observed Fact]');
        content = (
          <span>
            {parts[0]}
            <span style={{ background: 'rgba(56, 189, 248, 0.18)', color: '#38bdf8', padding: '1px 5px', borderRadius: '4px', fontWeight: 600, fontSize: '10px' }}>
              [Observed Fact]
            </span>
            {parts[1]}
          </span>
        );
      } else if (line.includes('[Correlated Path]')) {
        const parts = line.split('[Correlated Path]');
        content = (
          <span>
            {parts[0]}
            <span style={{ background: 'rgba(168, 85, 247, 0.18)', color: '#c084fc', padding: '1px 5px', borderRadius: '4px', fontWeight: 600, fontSize: '10px' }}>
              [Correlated Path]
            </span>
            {parts[1]}
          </span>
        );
      } else if (line.includes('[Hypothesis]')) {
        const parts = line.split('[Hypothesis]');
        content = (
          <span>
            {parts[0]}
            <span style={{ background: 'rgba(245, 158, 11, 0.18)', color: '#fbbf24', padding: '1px 5px', borderRadius: '4px', fontWeight: 600, fontSize: '10px' }}>
              [Hypothesis]
            </span>
            {parts[1]}
          </span>
        );
      } else if (line.includes('[Missing Telemetry]')) {
        const parts = line.split('[Missing Telemetry]');
        content = (
          <span>
            {parts[0]}
            <span style={{ background: 'rgba(244, 63, 94, 0.18)', color: '#fb7185', padding: '1px 5px', borderRadius: '4px', fontWeight: 600, fontSize: '10px' }}>
              [Missing Telemetry]
            </span>
            {parts[1]}
          </span>
        );
      } else if (line.startsWith('### ') || line.startsWith('#### ')) {
        return (
          <div key={idx} style={{ 
            color: '#f8fafc', 
            fontWeight: 700, 
            fontSize: line.startsWith('### ') ? '14px' : '12px',
            marginTop: '12px', 
            marginBottom: '4px',
            borderBottom: line.startsWith('### ') ? '1px solid rgba(255,255,255,0.08)' : 'none',
            paddingBottom: '2px'
          }}>
            {line.replace(/^#+\s*/, '')}
          </div>
        );
      }

      return (
        <div key={idx} style={{ minHeight: line.trim() ? 'auto' : '8px', marginBottom: '2px' }}>
          {content}
        </div>
      );
    });
  };

  return (
    <div className="glass-panel" style={{ padding: '18px', display: 'flex', flexDirection: 'column', gap: '14px' }}>
      {/* 1. Assessment & Priority Banner */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '10px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          {getClassificationBadge(assessment.classification)}
          {getPriorityBadge(assessment.remediation_priority)}
        </div>
        <div style={{ textAlign: 'right' }}>
          <div style={{ fontSize: '10px', color: 'var(--text-dim)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
            Internal Assessment Score
          </div>
          <div style={{ fontSize: '17px', fontWeight: 700, color: 'var(--accent-cyan)' }}>
            {assessment.raw_score.toFixed(2)} <span style={{ fontSize: '11px', color: 'var(--text-dim)' }}>/ 1.00</span>
          </div>
        </div>
      </div>

      {/* Uncertainty & Telemetry Bounds */}
      <div style={{
        background: 'rgba(15, 23, 42, 0.75)',
        borderLeft: '3px solid var(--accent-cyan)',
        border: '1px solid var(--border-subtle)',
        borderLeftWidth: '3px',
        padding: '10px 12px',
        borderRadius: '0 6px 6px 0',
        fontSize: '12px',
        lineHeight: 1.5,
        color: 'var(--text-secondary)'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '5px', marginBottom: '3px' }}>
          <Info size={13} color="var(--accent-cyan)" />
          <strong style={{ color: 'var(--accent-cyan)', fontSize: '11px', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
            Evaluation Bounds & Uncertainty:
          </strong>
        </div>
        <div>{assessment.uncertainty_explanation}</div>
      </div>

      {/* Navigation Tabs */}
      <div style={{ display: 'flex', gap: '6px', borderBottom: '1px solid var(--border-subtle)', paddingBottom: '6px' }}>
        <button
          onClick={() => setActiveTab('evidence')}
          style={{
            background: activeTab === 'evidence' ? 'rgba(56, 189, 248, 0.15)' : 'transparent',
            border: `1px solid ${activeTab === 'evidence' ? 'var(--accent-cyan)' : 'transparent'}`,
            color: activeTab === 'evidence' ? 'var(--accent-cyan)' : 'var(--text-dim)',
            padding: '5px 10px',
            borderRadius: '6px',
            fontSize: '11px',
            fontWeight: 600,
            display: 'flex',
            alignItems: 'center',
            gap: '5px'
          }}
        >
          <GitCommit size={13} /> Graph Evidence ({assessment.relevant_graph_paths.length})
        </button>
        <button
          onClick={() => setActiveTab('factors')}
          style={{
            background: activeTab === 'factors' ? 'rgba(56, 189, 248, 0.15)' : 'transparent',
            border: `1px solid ${activeTab === 'factors' ? 'var(--accent-cyan)' : 'transparent'}`,
            color: activeTab === 'factors' ? 'var(--accent-cyan)' : 'var(--text-dim)',
            padding: '5px 10px',
            borderRadius: '6px',
            fontSize: '11px',
            fontWeight: 600,
            display: 'flex',
            alignItems: 'center',
            gap: '5px'
          }}
        >
          <Activity size={13} /> Score Breakdown ({assessment.score_factors.length})
        </button>
        <button
          onClick={() => setActiveTab('report')}
          style={{
            background: activeTab === 'report' ? 'rgba(56, 189, 248, 0.15)' : 'transparent',
            border: `1px solid ${activeTab === 'report' ? 'var(--accent-cyan)' : 'transparent'}`,
            color: activeTab === 'report' ? 'var(--accent-cyan)' : 'var(--text-dim)',
            padding: '5px 10px',
            borderRadius: '6px',
            fontSize: '11px',
            fontWeight: 600,
            display: 'flex',
            alignItems: 'center',
            gap: '5px'
          }}
        >
          <FileText size={13} /> Detailed Findings
        </button>
      </div>

      {/* Tab 1: Evidence & Telemetry Gaps */}
      {activeTab === 'evidence' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', fontSize: '12px' }}>
          {/* Supporting Evidence Entities */}
          {assessment.supporting_evidence_ids.length > 0 && (
            <div>
              <span style={{ fontSize: '11px', color: 'var(--text-dim)', fontWeight: 600, display: 'block', marginBottom: '5px' }}>
                Corroborating Graph Evidence Entities (Click to focus in canvas):
              </span>
              <div style={{ display: 'flex', gap: '5px', flexWrap: 'wrap' }}>
                {assessment.supporting_evidence_ids.map(eid => (
                  <button
                    key={eid}
                    onClick={() => onHighlightEntity && onHighlightEntity(eid)}
                    style={{
                      background: 'rgba(56, 189, 248, 0.12)',
                      border: '1px solid rgba(56, 189, 248, 0.35)',
                      color: 'var(--accent-cyan)',
                      padding: '2px 8px',
                      borderRadius: '4px',
                      fontSize: '11px',
                      fontFamily: 'JetBrains Mono, monospace',
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: '4px'
                    }}
                  >
                    <Crosshair size={11} /> {eid}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Graph Paths */}
          <div>
            <div style={{ fontWeight: 600, color: 'var(--text-main)', marginBottom: '6px', display: 'flex', alignItems: 'center', gap: '6px' }}>
              <CheckCircle size={14} color="var(--accent-emerald)" /> FalkorDB Multi-Hop Attack & Exposure Paths:
            </div>
            {assessment.relevant_graph_paths.length > 0 ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                {assessment.relevant_graph_paths.map((p, idx) => (
                  <div 
                    key={idx} 
                    style={{
                      background: 'rgba(0, 0, 0, 0.35)',
                      border: '1px solid var(--border-subtle)',
                      padding: '8px 10px',
                      borderRadius: '6px',
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'center',
                      gap: '8px'
                    }}
                  >
                    <div style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '11px', color: 'var(--accent-cyan)', wordBreak: 'break-all' }}>
                      {p}
                    </div>
                    {onHighlightPath && (
                      <button
                        onClick={() => onHighlightPath(p)}
                        title="Highlight path on graph canvas"
                        aria-label={`Highlight path ${idx + 1}`}
                        style={{
                          background: 'rgba(56, 189, 248, 0.15)',
                          border: '1px solid var(--accent-cyan)',
                          color: 'var(--accent-cyan)',
                          padding: '3px 6px',
                          borderRadius: '4px',
                          fontSize: '10px',
                          whiteSpace: 'nowrap',
                          display: 'flex',
                          alignItems: 'center',
                          gap: '3px'
                        }}
                      >
                        <Crosshair size={10} /> Focus
                      </button>
                    )}
                  </div>
                ))}
              </div>
            ) : (
              <div style={{ color: 'var(--text-dim)', fontStyle: 'italic', padding: '4px 0' }}>
                Zero multi-hop attack or asset paths were discovered in FalkorDB for this alert.
              </div>
            )}
          </div>

          {/* Missing Telemetry & Uncertainty */}
          <div>
            <div style={{ fontWeight: 600, color: 'var(--text-main)', marginBottom: '6px', display: 'flex', alignItems: 'center', gap: '6px' }}>
              <HelpCircle size={14} color="var(--accent-amber)" /> Missing Telemetry & Known Unknowns:
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '5px' }}>
              {assessment.missing_evidence.map((m, idx) => (
                <div key={idx} style={{
                  background: 'rgba(245, 158, 11, 0.08)',
                  border: '1px solid rgba(245, 158, 11, 0.25)',
                  color: '#fef08a',
                  padding: '6px 10px',
                  borderRadius: '6px',
                  fontSize: '11px',
                  lineHeight: 1.4
                }}>
                  {m}
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Tab 2: Heuristic Score Breakdown */}
      {activeTab === 'factors' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', maxHeight: '340px', overflowY: 'auto' }}>
          <div style={{ fontSize: '11px', color: 'var(--text-dim)', marginBottom: '4px' }}>
            Heuristic factors evaluated from verified FalkorDB graph relationships:
          </div>
          {assessment.score_factors.map((f, idx) => (
            <div key={idx} style={{
              background: 'rgba(0, 0, 0, 0.3)',
              border: '1px solid var(--border-subtle)',
              padding: '8px 12px',
              borderRadius: '6px',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'flex-start',
              gap: '10px'
            }}>
              <div>
                <div style={{ fontWeight: 600, color: 'var(--text-main)', fontSize: '12px' }}>{f.factor_name}</div>
                <div style={{ color: 'var(--text-dim)', fontSize: '11px', marginTop: '2px', lineHeight: 1.3 }}>{f.description}</div>
                {f.evidence_ids.length > 0 && (
                  <div style={{ display: 'flex', gap: '4px', marginTop: '5px', flexWrap: 'wrap' }}>
                    {f.evidence_ids.map(eid => (
                      <button
                        key={eid}
                        onClick={() => onHighlightEntity && onHighlightEntity(eid)}
                        style={{
                          background: 'rgba(56, 189, 248, 0.1)',
                          border: '1px solid rgba(56, 189, 248, 0.25)',
                          color: 'var(--accent-cyan)',
                          padding: '1px 5px',
                          borderRadius: '3px',
                          fontSize: '10px',
                          fontFamily: 'JetBrains Mono, monospace'
                        }}
                      >
                        {eid}
                      </button>
                    ))}
                  </div>
                )}
              </div>
              <div style={{
                background: 'rgba(56, 189, 248, 0.15)',
                color: 'var(--accent-cyan)',
                fontWeight: 700,
                padding: '3px 7px',
                borderRadius: '4px',
                fontSize: '11px',
                fontFamily: 'JetBrains Mono, monospace'
              }}>
                +{f.weight.toFixed(2)}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Tab 3: Detailed Findings (Narrative) */}
      {activeTab === 'report' && (
        <div style={{
          background: 'rgba(0, 0, 0, 0.45)',
          border: '1px solid var(--border-subtle)',
          borderRadius: '6px',
          padding: '12px',
          maxHeight: '340px',
          overflowY: 'auto',
          fontSize: '11px',
          lineHeight: 1.6,
          color: 'var(--text-secondary)',
          fontFamily: 'Inter, sans-serif'
        }}>
          {renderFormattedNarrative(narrative)}
        </div>
      )}
    </div>
  );
};
