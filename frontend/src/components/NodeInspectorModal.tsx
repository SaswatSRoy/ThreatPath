import React from 'react';
import type { GraphNode } from '../types';
import { X, Info, Shield, Server, Terminal, AlertTriangle, Database, User, Code2 } from 'lucide-react';

interface NodeInspectorProps {
  node: GraphNode | null;
  onClose: () => void;
}

const getCategoryIcon = (category: string) => {
  switch (category) {
    case 'Host': return <Server size={18} color="var(--accent-cyan)" />;
    case 'Process': return <Terminal size={18} color="#c084fc" />;
    case 'Indicator': return <AlertTriangle size={18} color="var(--accent-crimson)" />;
    case 'Asset': return <Database size={18} color="var(--accent-amber)" />;
    case 'Vulnerability': return <Shield size={18} color="var(--accent-rose)" />;
    case 'Identity': return <User size={18} color="var(--accent-emerald)" />;
    case 'Software': return <Code2 size={18} color="#2dd4bf" />;
    default: return <Info size={18} color="var(--text-dim)" />;
  }
};

export const NodeInspectorModal: React.FC<NodeInspectorProps> = ({ node, onClose }) => {
  if (!node) return null;

  return (
    <div style={{
      position: 'absolute',
      top: '12px',
      left: '12px',
      width: '320px',
      maxHeight: 'calc(100% - 24px)',
      background: 'rgba(15, 23, 42, 0.95)',
      backdropFilter: 'blur(16px)',
      border: '1px solid rgba(56, 189, 248, 0.35)',
      borderRadius: '10px',
      padding: '16px',
      boxShadow: '0 12px 30px -5px rgba(0,0,0,0.8)',
      zIndex: 25,
      overflowY: 'auto'
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          {getCategoryIcon(node.category)}
          <span style={{ fontSize: '11px', textTransform: 'uppercase', letterSpacing: '0.06em', color: 'var(--accent-cyan)', fontWeight: 700 }}>
            {node.category}
          </span>
        </div>
        <button
          onClick={onClose}
          aria-label="Close node inspector"
          style={{ background: 'transparent', border: 'none', color: 'var(--text-dim)', padding: '2px' }}
        >
          <X size={16} />
        </button>
      </div>

      <h3 style={{ fontSize: '13px', fontWeight: 600, color: 'var(--text-main)', marginBottom: '12px', wordBreak: 'break-all', lineHeight: 1.4 }}>
        {node.label}
      </h3>

      <div style={{ fontSize: '12px', color: 'var(--text-muted)', borderTop: '1px solid rgba(255,255,255,0.08)', paddingTop: '10px' }}>
        <div style={{ marginBottom: '8px' }}>
          <strong style={{ color: 'var(--text-secondary)' }}>FalkorDB ID:</strong> <code style={{ color: 'var(--accent-cyan)', fontSize: '11px' }}>{node.id}</code>
        </div>
        {Object.entries(node.properties).map(([key, val]) => {
          if (key === 'id') return null;
          return (
            <div key={key} style={{ marginBottom: '8px', wordBreak: 'break-word' }}>
              <span style={{ color: 'var(--text-dim)', fontSize: '11px', textTransform: 'uppercase', letterSpacing: '0.04em' }}>{key}:</span>
              <div style={{ color: 'var(--text-main)', background: 'rgba(0,0,0,0.3)', border: '1px solid rgba(255,255,255,0.05)', padding: '4px 8px', borderRadius: '4px', marginTop: '2px', fontSize: '11px', fontFamily: typeof val === 'number' || typeof val === 'boolean' ? 'JetBrains Mono, monospace' : 'Inter, sans-serif' }}>
                {typeof val === 'boolean' ? (val ? 'true' : 'false') : String(val)}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
