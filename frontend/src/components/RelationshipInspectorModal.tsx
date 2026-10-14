import React from 'react';
import type { GraphEdge, GraphNode } from '../types';
import { X, ArrowRight, GitCommit, Layers } from 'lucide-react';

interface RelationshipInspectorProps {
  edge: GraphEdge | null;
  nodes: GraphNode[];
  onClose: () => void;
}

export const RelationshipInspectorModal: React.FC<RelationshipInspectorProps> = ({
  edge,
  nodes,
  onClose
}) => {
  if (!edge) return null;

  const sourceNode = nodes.find(n => n.id === edge.source);
  const targetNode = nodes.find(n => n.id === edge.target);

  return (
    <div style={{
      position: 'absolute',
      bottom: '12px',
      right: '12px',
      width: '340px',
      maxHeight: 'calc(100% - 24px)',
      background: 'rgba(15, 23, 42, 0.95)',
      backdropFilter: 'blur(16px)',
      border: '1px solid rgba(56, 189, 248, 0.4)',
      borderRadius: '10px',
      padding: '14px 16px',
      boxShadow: '0 12px 30px -5px rgba(0,0,0,0.8)',
      zIndex: 25,
      overflowY: 'auto'
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <GitCommit size={16} color="var(--accent-cyan)" />
          <span style={{ fontSize: '11px', textTransform: 'uppercase', letterSpacing: '0.06em', color: 'var(--accent-cyan)', fontWeight: 700 }}>
            Relationship Inspector
          </span>
        </div>
        <button
          onClick={onClose}
          aria-label="Close relationship inspector"
          style={{ background: 'transparent', border: 'none', color: 'var(--text-dim)', padding: '2px' }}
        >
          <X size={15} />
        </button>
      </div>

      <div style={{
        background: 'rgba(0, 0, 0, 0.35)',
        border: '1px solid rgba(255, 255, 255, 0.08)',
        borderRadius: '6px',
        padding: '10px',
        marginBottom: '10px'
      }}>
        <div style={{ fontSize: '12px', fontWeight: 700, color: '#f8fafc', fontFamily: 'JetBrains Mono, monospace', marginBottom: '8px' }}>
          [:{edge.relation}]
        </div>
        
        {/* Source -> Target Topology Flow */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '11px', flexWrap: 'wrap' }}>
          <div style={{
            background: 'rgba(56, 189, 248, 0.12)',
            border: '1px solid rgba(56, 189, 248, 0.3)',
            borderRadius: '4px',
            padding: '3px 6px',
            color: '#38bdf8'
          }}>
            <span style={{ fontSize: '9px', color: '#94a3b8', display: 'block' }}>{sourceNode?.category || 'Source'}</span>
            <strong>{sourceNode?.label || edge.source}</strong>
          </div>

          <ArrowRight size={14} color="var(--accent-cyan)" />

          <div style={{
            background: 'rgba(168, 85, 247, 0.12)',
            border: '1px solid rgba(168, 85, 247, 0.3)',
            borderRadius: '4px',
            padding: '3px 6px',
            color: '#c084fc'
          }}>
            <span style={{ fontSize: '9px', color: '#94a3b8', display: 'block' }}>{targetNode?.category || 'Target'}</span>
            <strong>{targetNode?.label || edge.target}</strong>
          </div>
        </div>
      </div>

      {/* Relationship Properties */}
      <div style={{ fontSize: '11px', color: 'var(--text-dim)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '4px', marginBottom: '6px', fontWeight: 600, color: 'var(--text-secondary)' }}>
          <Layers size={13} color="var(--text-dim)" /> FalkorDB Graph Properties:
        </div>
        {Object.entries(edge.properties || {}).length > 0 ? (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
            {Object.entries(edge.properties).map(([k, v]) => (
              <div key={k} style={{ display: 'flex', justifyContent: 'space-between', background: 'rgba(0,0,0,0.2)', padding: '3px 6px', borderRadius: '4px' }}>
                <span style={{ color: 'var(--text-dim)' }}>{k}:</span>
                <span style={{ color: 'var(--text-main)', fontFamily: 'JetBrains Mono, monospace' }}>{String(v)}</span>
              </div>
            ))}
          </div>
        ) : (
          <div style={{ fontStyle: 'italic', color: 'var(--text-dim)', padding: '4px 0' }}>
            Direct structural traversal relationship. No scalar edge properties recorded.
          </div>
        )}
      </div>
    </div>
  );
};
