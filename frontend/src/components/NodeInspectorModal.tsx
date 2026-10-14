import React from 'react';
import type { GraphNode } from '../types';
import { X, Info, Shield, Server, Terminal, AlertTriangle, Database } from 'lucide-react';

interface NodeInspectorProps {
  node: GraphNode | null;
  onClose: () => void;
}

const getCategoryIcon = (category: string) => {
  switch (category) {
    case 'Host': return <Server size={18} color="#38bdf8" />;
    case 'Process': return <Terminal size={18} color="#c084fc" />;
    case 'Indicator': return <AlertTriangle size={18} color="#ef4444" />;
    case 'Asset': return <Database size={18} color="#eab308" />;
    case 'Vulnerability': return <Shield size={18} color="#fb923c" />;
    default: return <Info size={18} color="#94a3b8" />;
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
      border: '1px solid rgba(56, 189, 248, 0.3)',
      borderRadius: '10px',
      padding: '16px',
      boxShadow: '0 10px 25px -5px rgba(0,0,0,0.7)',
      zIndex: 20,
      overflowY: 'auto'
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          {getCategoryIcon(node.category)}
          <span style={{ fontSize: '11px', textTransform: 'uppercase', letterSpacing: '0.05em', color: '#38bdf8', fontWeight: 700 }}>
            {node.category}
          </span>
        </div>
        <button
          onClick={onClose}
          style={{ background: 'transparent', border: 'none', color: '#94a3b8', padding: '2px' }}
        >
          <X size={16} />
        </button>
      </div>

      <h4 style={{ fontSize: '14px', fontWeight: 600, color: '#f8fafc', marginBottom: '12px', wordBreak: 'break-all' }}>
        {node.label}
      </h4>

      <div style={{ fontSize: '12px', color: '#94a3b8', borderTop: '1px solid rgba(255,255,255,0.08)', paddingTop: '10px' }}>
        <div style={{ marginBottom: '6px' }}>
          <strong style={{ color: '#cbd5e1' }}>Graph ID:</strong> <code style={{ color: '#38bdf8' }}>{node.id}</code>
        </div>
        {Object.entries(node.properties).map(([key, val]) => {
          if (key === 'id') return null;
          return (
            <div key={key} style={{ marginBottom: '8px', wordBreak: 'break-word' }}>
              <span style={{ color: '#64748b', fontSize: '11px', textTransform: 'uppercase' }}>{key}:</span>
              <div style={{ color: '#f1f5f9', background: 'rgba(0,0,0,0.25)', padding: '4px 6px', borderRadius: '4px', marginTop: '2px' }}>
                {typeof val === 'boolean' ? (val ? 'true' : 'false') : String(val)}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
