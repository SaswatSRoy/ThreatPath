import React from 'react';
import { Shield, Database, Cpu, Lock } from 'lucide-react';
import type { SystemHealth } from '../types';

interface HeaderProps {
  health: SystemHealth | null;
}

export const Header: React.FC<HeaderProps> = ({ health }) => {
  return (
    <header style={{
      background: 'rgba(15, 23, 42, 0.85)',
      backdropFilter: 'blur(16px)',
      borderBottom: '1px solid rgba(255, 255, 255, 0.08)',
      padding: '14px 24px',
      display: 'flex',
      justifyContent: 'space-between',
      alignItems: 'center',
      flexWrap: 'wrap',
      gap: '12px'
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
        <div style={{
          width: '38px',
          height: '38px',
          borderRadius: '10px',
          background: 'linear-gradient(135deg, #0284c7, #6366f1)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          boxShadow: '0 0 15px rgba(56, 189, 248, 0.4)'
        }}>
          <Shield size={22} color="#ffffff" />
        </div>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{ fontSize: '18px', fontWeight: 800, letterSpacing: '-0.02em', color: '#f8fafc' }}>
              THREATPATH
            </span>
            <span style={{
              background: 'rgba(56, 189, 248, 0.15)',
              color: '#38bdf8',
              border: '1px solid rgba(56, 189, 248, 0.3)',
              borderRadius: '4px',
              padding: '1px 6px',
              fontSize: '10px',
              fontWeight: 700,
              textTransform: 'uppercase'
            }}>
              Graph Hacks 2026
            </span>
          </div>
          <div style={{ fontSize: '11px', color: '#94a3b8' }}>
            Graph-Native Defensive Investigation Agent • Track 01: Agents That Act on Connected Data
          </div>
        </div>
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flexWrap: 'wrap' }}>
        <div style={{
          background: 'rgba(15, 23, 42, 0.8)',
          border: '1px solid rgba(255, 255, 255, 0.08)',
          borderRadius: '6px',
          padding: '4px 10px',
          display: 'flex',
          alignItems: 'center',
          gap: '6px',
          fontSize: '11px'
        }}>
          <Database size={13} color="#38bdf8" />
          <span style={{ color: '#94a3b8' }}>FalkorDB:</span>
          <span style={{ color: health?.falkordb_status === 'connected' ? '#34d399' : '#fb7185', fontWeight: 600 }}>
            {health?.active_graph || 'threatpath_dev'}
          </span>
          <span style={{
            width: '6px',
            height: '6px',
            borderRadius: '50%',
            background: health?.falkordb_status === 'connected' ? '#10b981' : '#f43f5e',
            display: 'inline-block'
          }} />
        </div>

        <div style={{
          background: 'rgba(15, 23, 42, 0.8)',
          border: '1px solid rgba(255, 255, 255, 0.08)',
          borderRadius: '6px',
          padding: '4px 10px',
          display: 'flex',
          alignItems: 'center',
          gap: '6px',
          fontSize: '11px'
        }}>
          <Cpu size={13} color="#c084fc" />
          <span style={{ color: '#94a3b8' }}>Mode:</span>
          <span style={{ color: '#c084fc', fontWeight: 600 }}>
            {health?.llm_mode === 'deterministic' ? 'Deterministic Engine' : 'LLM Orchestrated'}
          </span>
        </div>

        <div style={{
          background: 'rgba(16, 185, 129, 0.1)',
          border: '1px solid rgba(16, 185, 129, 0.25)',
          borderRadius: '6px',
          padding: '4px 10px',
          display: 'flex',
          alignItems: 'center',
          gap: '6px',
          fontSize: '11px',
          color: '#34d399',
          fontWeight: 600
        }}>
          <Lock size={12} />
          <span>Simulated Fleet Safe</span>
        </div>
      </div>
    </header>
  );
};
