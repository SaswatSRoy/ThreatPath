import React, { useState } from 'react';
import type { ResponseActionRecord } from '../types';
import { ShieldCheck, ShieldAlert, CheckCircle2, XCircle, Play, Lock, AlertCircle, Loader2 } from 'lucide-react';

interface ResponseActionPanelProps {
  action: ResponseActionRecord | null;
  onApprove: (actionId: string) => Promise<void>;
  onDeny: (actionId: string, reason: string) => Promise<void>;
  onExecute: (actionId: string) => Promise<void>;
}

export const ResponseActionPanel: React.FC<ResponseActionPanelProps> = ({
  action,
  onApprove,
  onDeny,
  onExecute
}) => {
  const [loading, setLoading] = useState(false);
  const [denyReason, setDenyReason] = useState('');
  const [showDenyModal, setShowDenyModal] = useState(false);

  if (!action) {
    return (
      <div className="glass-panel" style={{ padding: '20px', textAlign: 'center', color: '#64748b' }}>
        <ShieldCheck size={28} style={{ margin: '0 auto 8px', opacity: 0.5 }} />
        <div style={{ fontSize: '13px' }}>No active response action proposed.</div>
      </div>
    );
  }

  const handleApprove = async () => {
    setLoading(true);
    try {
      await onApprove(action.id);
    } finally {
      setLoading(false);
    }
  };

  const handleDeny = async () => {
    if (!denyReason.trim()) return;
    setLoading(true);
    try {
      await onDeny(action.id, denyReason);
      setShowDenyModal(false);
    } finally {
      setLoading(false);
    }
  };

  const handleExecute = async () => {
    setLoading(true);
    try {
      await onExecute(action.id);
    } finally {
      setLoading(false);
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'WAITING_FOR_APPROVAL':
        return (
          <span style={{
            background: 'rgba(245, 158, 11, 0.2)',
            color: '#fbbf24',
            border: '1px solid #f59e0b',
            padding: '3px 8px',
            borderRadius: '6px',
            fontSize: '11px',
            fontWeight: 700,
            display: 'inline-flex',
            alignItems: 'center',
            gap: '4px'
          }}>
            <Lock size={12} /> WAITING FOR APPROVAL
          </span>
        );
      case 'APPROVED':
        return (
          <span style={{
            background: 'rgba(56, 189, 248, 0.2)',
            color: '#38bdf8',
            border: '1px solid #38bdf8',
            padding: '3px 8px',
            borderRadius: '6px',
            fontSize: '11px',
            fontWeight: 700,
            display: 'inline-flex',
            alignItems: 'center',
            gap: '4px'
          }}>
            <CheckCircle2 size={12} /> APPROVED (READY TO EXECUTE)
          </span>
        );
      case 'VERIFIED':
        return (
          <span style={{
            background: 'rgba(16, 185, 129, 0.2)',
            color: '#34d399',
            border: '1px solid #10b981',
            padding: '3px 8px',
            borderRadius: '6px',
            fontSize: '11px',
            fontWeight: 700,
            display: 'inline-flex',
            alignItems: 'center',
            gap: '4px'
          }}>
            <ShieldCheck size={12} /> OUTCOME VERIFIED
          </span>
        );
      case 'DENIED':
        return (
          <span style={{
            background: 'rgba(225, 29, 72, 0.2)',
            color: '#fb7185',
            border: '1px solid #e11d48',
            padding: '3px 8px',
            borderRadius: '6px',
            fontSize: '11px',
            fontWeight: 700,
            display: 'inline-flex',
            alignItems: 'center',
            gap: '4px'
          }}>
            <XCircle size={12} /> ACTION DENIED
          </span>
        );
      default:
        return (
          <span style={{
            background: 'rgba(148, 163, 184, 0.2)',
            color: '#cbd5e1',
            border: '1px solid #64748b',
            padding: '3px 8px',
            borderRadius: '6px',
            fontSize: '11px',
            fontWeight: 700
          }}>
            {status}
          </span>
        );
    }
  };

  return (
    <div className="glass-panel" style={{ padding: '20px', display: 'flex', flexDirection: 'column', gap: '14px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '8px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <ShieldAlert size={18} color="#38bdf8" />
          <span style={{ fontSize: '13px', fontWeight: 700, color: '#f8fafc', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
            Recommended Response Action
          </span>
        </div>
        {getStatusBadge(action.status)}
      </div>

      <div style={{ background: 'rgba(0, 0, 0, 0.3)', border: '1px solid rgba(255,255,255,0.06)', borderRadius: '8px', padding: '12px', fontSize: '12px' }}>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '10px', marginBottom: '8px' }}>
          <div>
            <span style={{ color: '#64748b' }}>Action Type:</span>
            <div style={{ color: '#38bdf8', fontWeight: 600, fontFamily: 'JetBrains Mono, monospace' }}>{action.action_type}</div>
          </div>
          <div>
            <span style={{ color: '#64748b' }}>Target Entity:</span>
            <div style={{ color: '#f1f5f9', fontWeight: 600, fontFamily: 'JetBrains Mono, monospace' }}>{action.target_entity} ({action.target_type})</div>
          </div>
          <div>
            <span style={{ color: '#64748b' }}>Policy Requirement:</span>
            <div style={{ color: action.policy_decision === 'REQUIRE_APPROVAL' ? '#fbbf24' : '#34d399', fontWeight: 600 }}>
              {action.policy_decision}
            </div>
          </div>
        </div>

        <div style={{ marginTop: '8px', paddingTop: '8px', borderTop: '1px solid rgba(255,255,255,0.06)' }}>
          <span style={{ color: '#64748b' }}>Justification:</span>
          <div style={{ color: '#cbd5e1', marginTop: '2px', lineHeight: 1.4 }}>{action.justification}</div>
        </div>
      </div>

      {action.verification_details && (
        <div style={{
          background: action.status === 'VERIFIED' ? 'rgba(16, 185, 129, 0.1)' : 'rgba(225, 29, 72, 0.1)',
          border: `1px solid ${action.status === 'VERIFIED' ? '#10b981' : '#e11d48'}`,
          padding: '10px 14px',
          borderRadius: '8px',
          fontSize: '12px',
          color: action.status === 'VERIFIED' ? '#a7f3d0' : '#fecdd3',
          display: 'flex',
          alignItems: 'flex-start',
          gap: '8px'
        }}>
          {action.status === 'VERIFIED' ? <CheckCircle2 size={16} color="#10b981" /> : <AlertCircle size={16} color="#e11d48" />}
          <div>
            <strong>{action.status === 'VERIFIED' ? 'Telemetry Verification Confirmed:' : 'Verification Notice:'}</strong>
            <div style={{ marginTop: '2px' }}>{action.verification_details}</div>
          </div>
        </div>
      )}

      <div style={{ display: 'flex', gap: '10px', alignItems: 'center', marginTop: '4px' }}>
        {action.status === 'WAITING_FOR_APPROVAL' && (
          <>
            <button
              id="btn-approve-action"
              onClick={handleApprove}
              disabled={loading}
              style={{
                background: 'linear-gradient(135deg, #10b981, #059669)',
                color: '#fff',
                border: 'none',
                padding: '8px 16px',
                borderRadius: '6px',
                fontSize: '12px',
                fontWeight: 600,
                display: 'inline-flex',
                alignItems: 'center',
                gap: '6px',
                boxShadow: '0 2px 10px rgba(16, 185, 129, 0.3)'
              }}
            >
              {loading ? <Loader2 size={14} className="spin-slow" /> : <CheckCircle2 size={14} />} Approve Simulated Action
            </button>
            <button
              id="btn-deny-action"
              onClick={() => setShowDenyModal(true)}
              disabled={loading}
              style={{
                background: 'rgba(225, 29, 72, 0.15)',
                color: '#fb7185',
                border: '1px solid #e11d48',
                padding: '8px 14px',
                borderRadius: '6px',
                fontSize: '12px',
                fontWeight: 600,
                display: 'inline-flex',
                alignItems: 'center',
                gap: '6px'
              }}
            >
              <XCircle size={14} /> Deny
            </button>
          </>
        )}

        {action.status === 'APPROVED' && (
          <button
            id="btn-execute-action"
            onClick={handleExecute}
            disabled={loading}
            style={{
              background: 'linear-gradient(135deg, #38bdf8, #2563eb)',
              color: '#fff',
              border: 'none',
              padding: '8px 18px',
              borderRadius: '6px',
              fontSize: '12px',
              fontWeight: 600,
              display: 'inline-flex',
              alignItems: 'center',
              gap: '6px',
              boxShadow: '0 2px 12px rgba(56, 189, 248, 0.3)'
            }}
          >
            {loading ? <Loader2 size={14} className="spin-slow" /> : <Play size={14} />} Execute & Verify Simulation
          </button>
        )}

        {action.status === 'VERIFIED' && (
          <div style={{ fontSize: '11px', color: '#10b981', display: 'flex', alignItems: 'center', gap: '4px' }}>
            <CheckCircle2 size={14} /> Simulated containment successfully executed and cryptographically verified.
          </div>
        )}
      </div>

      {showDenyModal && (
        <div style={{
          marginTop: '8px',
          background: 'rgba(0,0,0,0.4)',
          border: '1px solid #e11d48',
          borderRadius: '8px',
          padding: '12px'
        }}>
          <div style={{ fontSize: '12px', color: '#f8fafc', fontWeight: 600, marginBottom: '6px' }}>Provide Reason for Denial:</div>
          <input
            id="input-deny-reason"
            type="text"
            placeholder="e.g. Critical production job running; reschedule isolation"
            value={denyReason}
            onChange={(e) => setDenyReason(e.target.value)}
            style={{
              width: '100%',
              background: '#0f172a',
              border: '1px solid rgba(255,255,255,0.15)',
              borderRadius: '4px',
              padding: '6px 10px',
              color: '#fff',
              fontSize: '12px',
              marginBottom: '8px',
              outline: 'none'
            }}
          />
          <div style={{ display: 'flex', gap: '8px', justifyContent: 'flex-end' }}>
            <button
              onClick={() => setShowDenyModal(false)}
              style={{ background: 'transparent', border: 'none', color: '#94a3b8', fontSize: '11px', padding: '4px 8px' }}
            >
              Cancel
            </button>
            <button
              id="btn-confirm-deny"
              onClick={handleDeny}
              disabled={!denyReason.trim() || loading}
              style={{ background: '#e11d48', border: 'none', color: '#fff', fontSize: '11px', padding: '4px 10px', borderRadius: '4px' }}
            >
              Confirm Denial
            </button>
          </div>
        </div>
      )}
    </div>
  );
};
