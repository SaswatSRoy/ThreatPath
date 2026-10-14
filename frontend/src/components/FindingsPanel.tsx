import React, { useState } from 'react';
import type { Assessment } from '../types';
import { ShieldAlert, AlertTriangle, CheckCircle, HelpCircle, GitCommit, FileText, Activity } from 'lucide-react';

interface FindingsPanelProps {
  assessment: Assessment | null;
  narrative: string;
}

export const FindingsPanel: React.FC<FindingsPanelProps> = ({ assessment, narrative }) => {
  const [activeTab, setActiveTab] = useState<'evidence' | 'factors' | 'narrative'>('evidence');

  if (!assessment) {
    return (
      <div className="glass-panel" style={{ padding: '24px', textAlign: 'center', color: '#64748b' }}>
        <Activity size={32} style={{ margin: '0 auto 12px', opacity: 0.5 }} />
        <p style={{ fontSize: '14px' }}>Select an alert and run investigation to view graph-backed findings.</p>
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
            fontSize: '12px',
            fontWeight: 700,
            display: 'inline-flex',
            alignItems: 'center',
            gap: '6px'
          }}>
            <ShieldAlert size={14} /> LIKELY COMPROMISE
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
            fontSize: '12px',
            fontWeight: 700,
            display: 'inline-flex',
            alignItems: 'center',
            gap: '6px'
          }}>
            <AlertTriangle size={14} /> SUSPICIOUS ACTIVITY
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
            fontSize: '12px',
            fontWeight: 700,
            display: 'inline-flex',
            alignItems: 'center',
            gap: '6px'
          }}>
            <HelpCircle size={14} /> INSUFFICIENT EVIDENCE
          </span>
        );
    }
  };

  const getPriorityBadge = (priority: string) => {
    const colors: Record<string, { bg: string; text: string; border: string }> = {
      critical: { bg: 'rgba(225, 29, 72, 0.2)', text: '#fb7185', border: '#e11d48' },
      high: { bg: 'rgba(249, 115, 22, 0.2)', text: '#fb923c', border: '#ea580c' },
      medium: { bg: 'rgba(234, 179, 8, 0.2)', text: '#fde047', border: '#ca8a04' },
      low: { bg: 'rgba(34, 197, 94, 0.2)', text: '#4ade80', border: '#16a34a' }
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

  return (
    <div className="glass-panel" style={{ padding: '20px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '12px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          {getClassificationBadge(assessment.classification)}
          {getPriorityBadge(assessment.remediation_priority)}
        </div>
        <div style={{ textAlign: 'right' }}>
          <div style={{ fontSize: '11px', color: '#94a3b8' }}>Deterministic Heuristic Score</div>
          <div style={{ fontSize: '18px', fontWeight: 700, color: '#38bdf8' }}>
            {assessment.raw_score.toFixed(2)} <span style={{ fontSize: '12px', color: '#64748b' }}>/ 1.00</span>
          </div>
        </div>
      </div>

      <div style={{
        background: 'rgba(15, 23, 42, 0.6)',
        borderLeft: '3px solid #38bdf8',
        padding: '10px 14px',
        borderRadius: '0 8px 8px 0',
        fontSize: '12px',
        lineHeight: 1.5,
        color: '#cbd5e1'
      }}>
        <strong style={{ color: '#38bdf8' }}>Uncertainty Bounds:</strong> {assessment.uncertainty_explanation}
      </div>

      <div style={{ display: 'flex', gap: '8px', borderBottom: '1px solid rgba(255,255,255,0.08)', paddingBottom: '6px' }}>
        <button
          onClick={() => setActiveTab('evidence')}
          style={{
            background: activeTab === 'evidence' ? 'rgba(56, 189, 248, 0.15)' : 'transparent',
            border: 'none',
            color: activeTab === 'evidence' ? '#38bdf8' : '#94a3b8',
            padding: '6px 12px',
            borderRadius: '6px',
            fontSize: '12px',
            fontWeight: 600,
            display: 'flex',
            alignItems: 'center',
            gap: '6px'
          }}
        >
          <GitCommit size={14} /> Multi-Hop Evidence ({assessment.relevant_graph_paths.length})
        </button>
        <button
          onClick={() => setActiveTab('factors')}
          style={{
            background: activeTab === 'factors' ? 'rgba(56, 189, 248, 0.15)' : 'transparent',
            border: 'none',
            color: activeTab === 'factors' ? '#38bdf8' : '#94a3b8',
            padding: '6px 12px',
            borderRadius: '6px',
            fontSize: '12px',
            fontWeight: 600,
            display: 'flex',
            alignItems: 'center',
            gap: '6px'
          }}
        >
          <Activity size={14} /> Score Factors ({assessment.score_factors.length})
        </button>
        <button
          onClick={() => setActiveTab('narrative')}
          style={{
            background: activeTab === 'narrative' ? 'rgba(56, 189, 248, 0.15)' : 'transparent',
            border: 'none',
            color: activeTab === 'narrative' ? '#38bdf8' : '#94a3b8',
            padding: '6px 12px',
            borderRadius: '6px',
            fontSize: '12px',
            fontWeight: 600,
            display: 'flex',
            alignItems: 'center',
            gap: '6px'
          }}
        >
          <FileText size={14} /> Full Agent Report
        </button>
      </div>

      {activeTab === 'evidence' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '14px', fontSize: '13px' }}>
          <div>
            <div style={{ fontWeight: 600, color: '#f8fafc', marginBottom: '8px', display: 'flex', alignItems: 'center', gap: '6px' }}>
              <CheckCircle size={15} color="#10b981" /> FalkorDB Graph Traversal Paths:
            </div>
            {assessment.relevant_graph_paths.length > 0 ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                {assessment.relevant_graph_paths.map((p, idx) => (
                  <div key={idx} style={{
                    background: 'rgba(0, 0, 0, 0.3)',
                    border: '1px solid rgba(255, 255, 255, 0.08)',
                    padding: '8px 12px',
                    borderRadius: '6px',
                    fontFamily: 'JetBrains Mono, monospace',
                    fontSize: '12px',
                    color: '#38bdf8'
                  }}>
                    {p}
                  </div>
                ))}
              </div>
            ) : (
              <div style={{ color: '#94a3b8', fontStyle: 'italic', padding: '6px 0' }}>
                Zero multi-hop attack or asset paths were discovered in FalkorDB for this alert.
              </div>
            )}
          </div>

          <div>
            <div style={{ fontWeight: 600, color: '#f8fafc', marginBottom: '8px', display: 'flex', alignItems: 'center', gap: '6px' }}>
              <HelpCircle size={15} color="#f59e0b" /> Missing Evidence & Telemetry Gaps:
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
              {assessment.missing_evidence.map((m, idx) => (
                <div key={idx} style={{
                  background: 'rgba(245, 158, 11, 0.08)',
                  border: '1px solid rgba(245, 158, 11, 0.2)',
                  color: '#fef08a',
                  padding: '8px 12px',
                  borderRadius: '6px',
                  fontSize: '12px'
                }}>
                  {m}
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {activeTab === 'factors' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
          {assessment.score_factors.map((f, idx) => (
            <div key={idx} style={{
              background: 'rgba(0, 0, 0, 0.25)',
              border: '1px solid rgba(255, 255, 255, 0.06)',
              padding: '10px 14px',
              borderRadius: '8px',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'flex-start',
              gap: '12px'
            }}>
              <div>
                <div style={{ fontWeight: 600, color: '#f1f5f9', fontSize: '13px' }}>{f.factor_name}</div>
                <div style={{ color: '#94a3b8', fontSize: '12px', marginTop: '2px' }}>{f.description}</div>
                {f.evidence_ids.length > 0 && (
                  <div style={{ display: 'flex', gap: '4px', marginTop: '6px', flexWrap: 'wrap' }}>
                    {f.evidence_ids.map(eid => (
                      <span key={eid} style={{
                        background: 'rgba(56, 189, 248, 0.1)',
                        color: '#38bdf8',
                        padding: '1px 6px',
                        borderRadius: '4px',
                        fontSize: '10px',
                        fontFamily: 'JetBrains Mono, monospace'
                      }}>
                        {eid}
                      </span>
                    ))}
                  </div>
                )}
              </div>
              <div style={{
                background: 'rgba(56, 189, 248, 0.15)',
                color: '#38bdf8',
                fontWeight: 700,
                padding: '4px 8px',
                borderRadius: '6px',
                fontSize: '12px'
              }}>
                +{f.weight.toFixed(2)}
              </div>
            </div>
          ))}
        </div>
      )}

      {activeTab === 'narrative' && (
        <div style={{
          background: 'rgba(0, 0, 0, 0.4)',
          border: '1px solid rgba(255, 255, 255, 0.08)',
          borderRadius: '8px',
          padding: '14px',
          maxHeight: '340px',
          overflowY: 'auto',
          fontSize: '12px',
          lineHeight: 1.6,
          color: '#cbd5e1',
          whiteSpace: 'pre-wrap',
          fontFamily: 'Inter, sans-serif'
        }}>
          {narrative}
        </div>
      )}
    </div>
  );
};
