import React, { useState } from 'react';
import type { ResponseActionRecord } from '../types';
import { 
  ShieldCheck, 
  ShieldAlert, 
  CheckCircle2, 
  XCircle, 
  Play, 
  Lock, 
  AlertCircle, 
  Loader2,
  AlertTriangle,
  Radio
} from 'lucide-react';

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
  const [showConfirmModal, setShowConfirmModal] = useState(false);

  if (!action) {
    return (
      <div className="glass-panel" style={{ padding: '20px', textAlign: 'center', color: 'var(--text-dim)' }}>
        <ShieldCheck size={28} style={{ margin: '0 auto 8px', opacity: 0.4 }} />
        <div style={{ fontSize: '13px', color: 'var(--text-muted)' }}>No active response action proposed.</div>
        <div style={{ fontSize: '11px', color: 'var(--text-dim)', marginTop: '4px' }}>
          Execute an investigation to generate policy-aligned response options.
        </div>
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
    // If consequential action, require confirmation first
    const isConsequential = 
      action.action_type === 'SIMULATE_ISOLATE_HOST' || 
      action.action_type === 'SIMULATE_DISABLE_ACCOUNT';

    if (isConsequential && !showConfirmModal) {
      setShowConfirmModal(true);
      return;
    }

    setLoading(true);
    setShowConfirmModal(false);
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

  const getActionSuccessMessage = (actionRecord: ResponseActionRecord) => {
    switch (actionRecord.action_type) {
      case 'SIMULATE_ISOLATE_HOST':
        return 'Simulated host containment successfully executed and interface isolation verified.';
      case 'SIMULATE_DISABLE_ACCOUNT':
        return 'Simulated account disablement successfully executed and directory state verified.';
      case 'SIMULATE_BLOCK_INDICATOR':
        return 'Simulated perimeter block rule applied and boundary drop telemetry verified.';
      case 'SIMULATE_ESCALATE_INCIDENT':
        return 'Simulated incident escalation ticket successfully dispatched to SOC queue (no host containment executed).';
      default:
        return `Simulated action '${actionRecord.action_type}' successfully executed and verified.`;
    }
  };

  const getActionExecuteLabel = (actionType: string) => {
    switch (actionType) {
      case 'SIMULATE_ISOLATE_HOST':
        return 'Execute Host Isolation & Verify';
      case 'SIMULATE_DISABLE_ACCOUNT':
        return 'Execute Account Disablement & Verify';
      case 'SIMULATE_BLOCK_INDICATOR':
        return 'Apply Firewall Block & Verify';
      case 'SIMULATE_ESCALATE_INCIDENT':
        return 'Dispatch Escalation Ticket & Verify';
      default:
        return 'Execute & Verify Simulation';
    }
  };

  return (
    <div className="glass-panel" style={{ padding: '18px', display: 'flex', flexDirection: 'column', gap: '14px' }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '8px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <ShieldAlert size={16} color="var(--accent-cyan)" />
          <h2 style={{ fontSize: '13px', fontWeight: 700, color: 'var(--text-main)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
            Recommended Response Action
          </h2>
        </div>
        {getStatusBadge(action.status)}
      </div>

      {/* Simulation Boundary Banner */}
      <div style={{
        background: 'rgba(56, 189, 248, 0.08)',
        border: '1px solid rgba(56, 189, 248, 0.25)',
        borderRadius: '6px',
        padding: '5px 10px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        fontSize: '11px',
        color: 'var(--accent-cyan)'
      }}>
        <span style={{ display: 'flex', alignItems: 'center', gap: '5px', fontWeight: 600 }}>
          <Radio size={12} className="spin-slow" /> SIMULATION ENVIRONMENT
        </span>
        <span style={{ fontSize: '10px', color: 'var(--text-dim)' }}>Zero Production Fleet Impact</span>
      </div>

      {/* Action Metadata Box */}
      <div style={{ background: 'rgba(0, 0, 0, 0.35)', border: '1px solid var(--border-subtle)', borderRadius: '8px', padding: '12px', fontSize: '12px' }}>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))', gap: '10px', marginBottom: '8px' }}>
          <div>
            <span style={{ color: 'var(--text-dim)', fontSize: '11px' }}>Action Type:</span>
            <div style={{ color: 'var(--accent-cyan)', fontWeight: 600, fontFamily: 'JetBrains Mono, monospace' }}>{action.action_type}</div>
          </div>
          <div>
            <span style={{ color: 'var(--text-dim)', fontSize: '11px' }}>Target Entity:</span>
            <div style={{ color: 'var(--text-main)', fontWeight: 600, fontFamily: 'JetBrains Mono, monospace' }}>
              {action.target_entity} ({action.target_type})
            </div>
          </div>
          <div>
            <span style={{ color: 'var(--text-dim)', fontSize: '11px' }}>Policy Requirement:</span>
            <div style={{ color: action.policy_decision === 'REQUIRE_APPROVAL' ? 'var(--accent-amber)' : 'var(--accent-emerald)', fontWeight: 600 }}>
              {action.policy_decision}
            </div>
          </div>
        </div>

        <div style={{ marginTop: '8px', paddingTop: '8px', borderTop: '1px solid rgba(255,255,255,0.06)' }}>
          <span style={{ color: 'var(--text-dim)', fontSize: '11px' }}>Deterministic Justification:</span>
          <div style={{ color: 'var(--text-secondary)', marginTop: '2px', lineHeight: 1.4 }}>{action.justification}</div>
        </div>
      </div>

      {/* Verification Notice */}
      {action.verification_details && (
        <div style={{
          background: action.status === 'VERIFIED' ? 'rgba(16, 185, 129, 0.12)' : 'rgba(225, 29, 72, 0.12)',
          border: `1px solid ${action.status === 'VERIFIED' ? '#10b981' : '#e11d48'}`,
          padding: '10px 12px',
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
            <div style={{ marginTop: '2px', lineHeight: 1.4 }}>{action.verification_details}</div>
          </div>
        </div>
      )}

      {/* Action Controls */}
      <div style={{ display: 'flex', gap: '10px', alignItems: 'center', marginTop: '2px' }}>
        {action.status === 'WAITING_FOR_APPROVAL' && (
          <>
            <button
              id="btn-approve-action"
              onClick={handleApprove}
              disabled={loading}
              aria-label="Approve simulated response action"
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
              aria-label="Deny simulated response action"
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
            aria-label={getActionExecuteLabel(action.action_type)}
            style={{
              background: 'linear-gradient(135deg, #0284c7, #6366f1)',
              color: '#fff',
              border: 'none',
              padding: '8px 18px',
              borderRadius: '6px',
              fontSize: '12px',
              fontWeight: 600,
              display: 'inline-flex',
              alignItems: 'center',
              gap: '6px',
              boxShadow: '0 2px 12px rgba(56, 189, 248, 0.35)'
            }}
          >
            {loading ? <Loader2 size={14} className="spin-slow" /> : <Play size={14} />} {getActionExecuteLabel(action.action_type)}
          </button>
        )}

        {action.status === 'VERIFIED' && (
          <div style={{ fontSize: '11px', color: 'var(--accent-emerald)', display: 'flex', alignItems: 'center', gap: '6px' }}>
            <CheckCircle2 size={14} /> {getActionSuccessMessage(action)}
          </div>
        )}
      </div>

      {/* Confirmation Modal before Consequential Action */}
      {showConfirmModal && (
        <div style={{
          marginTop: '8px',
          background: 'rgba(15, 23, 42, 0.95)',
          border: '1px solid var(--accent-amber)',
          borderRadius: '8px',
          padding: '12px',
          boxShadow: '0 8px 24px rgba(0,0,0,0.6)'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: 'var(--accent-amber)', fontSize: '12px', fontWeight: 700, marginBottom: '6px' }}>
            <AlertTriangle size={15} /> Confirm High-Consequence Action Execution
          </div>
          <div style={{ fontSize: '11px', color: 'var(--text-secondary)', lineHeight: 1.4, marginBottom: '10px' }}>
            You are about to execute <strong>{action.action_type}</strong> targeting <strong>{action.target_entity}</strong> in the simulated fleet.
            This action was approved under Policy Gate rules.
          </div>
          <div style={{ display: 'flex', gap: '8px', justifyContent: 'flex-end' }}>
            <button
              onClick={() => setShowConfirmModal(false)}
              style={{ background: 'transparent', border: '1px solid var(--border-subtle)', color: 'var(--text-dim)', fontSize: '11px', padding: '5px 10px', borderRadius: '4px' }}
            >
              Cancel
            </button>
            <button
              onClick={handleExecute}
              disabled={loading}
              style={{
                background: 'linear-gradient(135deg, #0284c7, #2563eb)',
                border: 'none',
                color: '#fff',
                fontSize: '11px',
                fontWeight: 600,
                padding: '5px 12px',
                borderRadius: '4px',
                display: 'flex',
                alignItems: 'center',
                gap: '4px'
              }}
            >
              {loading ? <Loader2 size={12} className="spin-slow" /> : <Play size={12} />} Proceed with Simulation
            </button>
          </div>
        </div>
      )}

      {/* Deny Reason Modal */}
      {showDenyModal && (
        <div style={{
          marginTop: '8px',
          background: 'rgba(0,0,0,0.45)',
          border: '1px solid var(--accent-crimson)',
          borderRadius: '8px',
          padding: '12px'
        }}>
          <div style={{ fontSize: '12px', color: '#f8fafc', fontWeight: 600, marginBottom: '6px' }}>Provide Reason for Denial:</div>
          <input
            id="input-deny-reason"
            type="text"
            placeholder="e.g. Critical production batch running; reschedule host isolation"
            value={denyReason}
            onChange={(e) => setDenyReason(e.target.value)}
            style={{
              width: '100%',
              background: '#070a10',
              border: '1px solid var(--border-subtle)',
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
              style={{ background: 'transparent', border: 'none', color: 'var(--text-dim)', fontSize: '11px', padding: '4px 8px' }}
            >
              Cancel
            </button>
            <button
              id="btn-confirm-deny"
              onClick={handleDeny}
              disabled={!denyReason.trim() || loading}
              style={{ background: 'var(--accent-crimson)', border: 'none', color: '#fff', fontSize: '11px', padding: '4px 10px', borderRadius: '4px' }}
            >
              Confirm Denial
            </button>
          </div>
        </div>
      )}
    </div>
  );
};
