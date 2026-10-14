import React, { useState, useMemo } from 'react';
import type { AlertSummary, Assessment } from '../types';
import { 
  ShieldAlert, 
  Search, 
  X, 
  SlidersHorizontal, 
  Loader2, 
  Server, 
  User, 
  Clock,
  ShieldCheck,
  AlertTriangle,
  HelpCircle
} from 'lucide-react';

import { SCENARIO_HINTS } from '../constants';

const SEVERITY_ORDER: Record<string, number> = {
  CRITICAL: 4,
  HIGH: 3,
  MEDIUM: 2,
  LOW: 1,
  INFO: 0
};

interface AlertQueueProps {
  alerts: AlertSummary[];
  selectedAlert: AlertSummary | null;
  onSelectAlert: (alert: AlertSummary) => void;
  loading: boolean;
  currentAssessment?: Assessment | null;
  investigatedAlertId?: string | null;
}

export const AlertQueue: React.FC<AlertQueueProps> = ({
  alerts,
  selectedAlert,
  onSelectAlert,
  loading,
  currentAssessment,
  investigatedAlertId
}) => {
  const [searchQuery, setSearchQuery] = useState('');
  const [severityFilter, setSeverityFilter] = useState<string>('ALL');
  const [sortBy, setSortBy] = useState<'default' | 'severity' | 'recency'>('default');
  const [showFilters, setShowFilters] = useState(false);

  const filteredAlerts = useMemo(() => {
    return alerts
      .filter(alert => {
        const matchesQuery = 
          alert.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
          alert.id.toLowerCase().includes(searchQuery.toLowerCase()) ||
          alert.alert_type.toLowerCase().includes(searchQuery.toLowerCase()) ||
          (alert.target_host && alert.target_host.toLowerCase().includes(searchQuery.toLowerCase())) ||
          (alert.target_identity && alert.target_identity.toLowerCase().includes(searchQuery.toLowerCase()));

        const matchesSeverity = 
          severityFilter === 'ALL' || alert.severity.toUpperCase() === severityFilter;

        return matchesQuery && matchesSeverity;
      })
      .sort((a, b) => {
        if (sortBy === 'severity') {
          const scoreA = SEVERITY_ORDER[a.severity.toUpperCase()] || 0;
          const scoreB = SEVERITY_ORDER[b.severity.toUpperCase()] || 0;
          return scoreB - scoreA;
        }
        if (sortBy === 'recency') {
          return new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime();
        }
        return 0;
      });
  }, [alerts, searchQuery, severityFilter, sortBy]);

  const getSourceSeverityBadge = (severity: string) => {
    switch (severity.toUpperCase()) {
      case 'CRITICAL':
        return (
          <span style={{
            background: 'rgba(225, 29, 72, 0.15)',
            color: '#fb7185',
            border: '1px solid rgba(225, 29, 72, 0.4)',
            padding: '2px 7px',
            borderRadius: '4px',
            fontSize: '10px',
            fontWeight: 700,
            letterSpacing: '0.04em'
          }}>
            SRC: CRITICAL
          </span>
        );
      case 'HIGH':
        return (
          <span style={{
            background: 'rgba(249, 115, 22, 0.15)',
            color: '#fb923c',
            border: '1px solid rgba(249, 115, 22, 0.4)',
            padding: '2px 7px',
            borderRadius: '4px',
            fontSize: '10px',
            fontWeight: 700,
            letterSpacing: '0.04em'
          }}>
            SRC: HIGH
          </span>
        );
      case 'MEDIUM':
        return (
          <span style={{
            background: 'rgba(234, 179, 8, 0.15)',
            color: '#fde047',
            border: '1px solid rgba(234, 179, 8, 0.4)',
            padding: '2px 7px',
            borderRadius: '4px',
            fontSize: '10px',
            fontWeight: 700,
            letterSpacing: '0.04em'
          }}>
            SRC: MEDIUM
          </span>
        );
      default:
        return (
          <span style={{
            background: 'rgba(56, 189, 248, 0.15)',
            color: '#38bdf8',
            border: '1px solid rgba(56, 189, 248, 0.4)',
            padding: '2px 7px',
            borderRadius: '4px',
            fontSize: '10px',
            fontWeight: 700,
            letterSpacing: '0.04em'
          }}>
            SRC: {severity.toUpperCase()}
          </span>
        );
    }
  };

  const getAssessedPriorityBadge = (assessment: Assessment) => {
    const priority = assessment.remediation_priority.toUpperCase();
    const colors: Record<string, { bg: string; text: string; border: string }> = {
      CRITICAL: { bg: 'rgba(225, 29, 72, 0.25)', text: '#fda4af', border: '#e11d48' },
      HIGH: { bg: 'rgba(249, 115, 22, 0.25)', text: '#fed7aa', border: '#ea580c' },
      MEDIUM: { bg: 'rgba(234, 179, 8, 0.25)', text: '#fef08a', border: '#ca8a04' },
      LOW: { bg: 'rgba(34, 197, 94, 0.25)', text: '#bbf7d0', border: '#16a34a' }
    };
    const c = colors[priority] || colors.LOW;
    return (
      <span style={{
        background: c.bg,
        color: c.text,
        border: `1px solid ${c.border}`,
        padding: '2px 7px',
        borderRadius: '4px',
        fontSize: '10px',
        fontWeight: 700,
        letterSpacing: '0.04em',
        display: 'inline-flex',
        alignItems: 'center',
        gap: '4px'
      }}>
        {priority === 'CRITICAL' ? <ShieldAlert size={10} /> : priority === 'HIGH' ? <AlertTriangle size={10} /> : <HelpCircle size={10} />}
        ASSESSED: {priority}
      </span>
    );
  };

  return (
    <div className="glass-panel" style={{ padding: '16px', display: 'flex', flexDirection: 'column', gap: '12px' }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <ShieldAlert size={16} color="var(--accent-cyan)" />
          <h2 style={{ fontSize: '13px', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--text-main)' }}>
            Alert Queue ({filteredAlerts.length})
          </h2>
        </div>
        <button
          onClick={() => setShowFilters(!showFilters)}
          aria-label="Toggle alert queue filters"
          style={{
            background: showFilters || severityFilter !== 'ALL' || sortBy !== 'default' ? 'rgba(56, 189, 248, 0.2)' : 'rgba(255,255,255,0.05)',
            border: `1px solid ${showFilters ? 'var(--accent-cyan)' : 'var(--border-subtle)'}`,
            color: showFilters ? 'var(--accent-cyan)' : 'var(--text-dim)',
            padding: '4px 8px',
            borderRadius: '6px',
            fontSize: '11px',
            display: 'inline-flex',
            alignItems: 'center',
            gap: '5px'
          }}
        >
          <SlidersHorizontal size={12} />
          <span>Filters</span>
          {severityFilter !== 'ALL' && (
            <span style={{ width: '6px', height: '6px', borderRadius: '50%', background: 'var(--accent-cyan)' }} />
          )}
        </button>
      </div>

      {/* Search Bar */}
      <div style={{ position: 'relative', width: '100%' }}>
        <Search size={14} style={{ position: 'absolute', left: '10px', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-dim)' }} />
        <input
          id="input-alert-search"
          type="text"
          placeholder="Filter by title, ID, host, type..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          aria-label="Search alerts"
          style={{
            width: '100%',
            background: 'rgba(0, 0, 0, 0.35)',
            border: '1px solid var(--border-subtle)',
            borderRadius: '6px',
            padding: '7px 28px 7px 32px',
            color: 'var(--text-main)',
            fontSize: '12px',
            outline: 'none'
          }}
        />
        {searchQuery && (
          <button
            onClick={() => setSearchQuery('')}
            aria-label="Clear search query"
            style={{ position: 'absolute', right: '8px', top: '50%', transform: 'translateY(-50%)', background: 'transparent', border: 'none', color: 'var(--text-dim)', padding: '2px' }}
          >
            <X size={12} />
          </button>
        )}
      </div>

      {/* Expandable Filter / Sort Section */}
      {showFilters && (
        <div style={{
          background: 'rgba(0, 0, 0, 0.4)',
          border: '1px solid var(--border-subtle)',
          borderRadius: '6px',
          padding: '10px',
          display: 'flex',
          flexDirection: 'column',
          gap: '8px',
          fontSize: '11px'
        }}>
          <div>
            <span style={{ color: 'var(--text-dim)', fontWeight: 600, display: 'block', marginBottom: '4px' }}>Source Severity:</span>
            <div style={{ display: 'flex', gap: '4px', flexWrap: 'wrap' }}>
              {['ALL', 'CRITICAL', 'HIGH', 'MEDIUM', 'LOW'].map(sev => (
                <button
                  key={sev}
                  onClick={() => setSeverityFilter(sev)}
                  style={{
                    background: severityFilter === sev ? 'rgba(56, 189, 248, 0.25)' : 'rgba(255,255,255,0.04)',
                    border: `1px solid ${severityFilter === sev ? 'var(--accent-cyan)' : 'transparent'}`,
                    color: severityFilter === sev ? 'var(--accent-cyan)' : 'var(--text-dim)',
                    padding: '2px 8px',
                    borderRadius: '4px',
                    fontSize: '10px',
                    fontWeight: 600
                  }}
                >
                  {sev}
                </button>
              ))}
            </div>
          </div>

          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', paddingTop: '4px', borderTop: '1px solid rgba(255,255,255,0.06)' }}>
            <span style={{ color: 'var(--text-dim)', fontWeight: 600 }}>Sort Order:</span>
            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value as any)}
              style={{
                background: '#0d131f',
                border: '1px solid var(--border-subtle)',
                color: 'var(--text-secondary)',
                fontSize: '11px',
                borderRadius: '4px',
                padding: '2px 6px',
                outline: 'none'
              }}
            >
              <option value="default">Default Scenarios</option>
              <option value="severity">Source Severity</option>
              <option value="recency">Most Recent</option>
            </select>
          </div>
        </div>
      )}

      {/* Loading state */}
      {loading && (
        <div style={{ textAlign: 'center', padding: '24px', color: 'var(--text-dim)' }}>
          <Loader2 size={20} className="spin-slow" style={{ margin: '0 auto 8px' }} />
          <span style={{ fontSize: '12px' }}>Loading graph alerts...</span>
        </div>
      )}

      {/* Empty Filtered State */}
      {!loading && filteredAlerts.length === 0 && (
        <div style={{ textAlign: 'center', padding: '24px 12px', color: 'var(--text-dim)', fontSize: '12px' }}>
          <ShieldCheck size={28} style={{ margin: '0 auto 8px', opacity: 0.4 }} />
          <div>No alerts match active filters</div>
          <button
            onClick={() => { setSearchQuery(''); setSeverityFilter('ALL'); setSortBy('default'); }}
            style={{
              marginTop: '10px',
              background: 'rgba(56, 189, 248, 0.15)',
              border: '1px solid var(--accent-cyan)',
              color: 'var(--accent-cyan)',
              padding: '4px 10px',
              borderRadius: '4px',
              fontSize: '11px',
              fontWeight: 600
            }}
          >
            Reset Filters
          </button>
        </div>
      )}

      {/* Alert Cards List */}
      <div 
        role="listbox" 
        aria-label="Alert List"
        style={{ display: 'flex', flexDirection: 'column', gap: '8px', maxHeight: 'calc(100vh - 280px)', overflowY: 'auto', paddingRight: '2px' }}
      >
        {filteredAlerts.map(alert => {
          const hint = SCENARIO_HINTS[alert.id];
          const isSelected = selectedAlert?.id === alert.id;
          const isInvestigated = investigatedAlertId === alert.id && currentAssessment;

          return (
            <div
              key={alert.id}
              id={`alert-card-${alert.id}`}
              role="option"
              aria-selected={isSelected}
              tabIndex={0}
              onClick={() => onSelectAlert(alert)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                  e.preventDefault();
                  onSelectAlert(alert);
                }
              }}
              style={{
                background: isSelected 
                  ? 'linear-gradient(90deg, rgba(56, 189, 248, 0.16) 0%, rgba(15, 23, 42, 0.8) 100%)' 
                  : 'rgba(0, 0, 0, 0.3)',
                border: isSelected ? '1px solid var(--accent-cyan)' : '1px solid var(--border-subtle)',
                borderLeft: isSelected ? '4px solid var(--accent-cyan)' : '1px solid var(--border-subtle)',
                borderRadius: '8px',
                padding: '12px',
                cursor: 'pointer',
                transition: 'all 0.15s ease',
                outline: 'none'
              }}
            >
              {hint && (
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
                  <span style={{ fontSize: '10px', color: 'var(--accent-cyan)', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                    {hint.label}
                  </span>
                  <span style={{ fontSize: '9px', background: 'rgba(255,255,255,0.06)', border: '1px solid rgba(255,255,255,0.08)', padding: '1px 5px', borderRadius: '4px', color: 'var(--text-muted)' }}>
                    {hint.tag}
                  </span>
                </div>
              )}

              <div style={{ fontSize: '12px', fontWeight: 600, color: 'var(--text-main)', marginBottom: '8px', lineHeight: 1.4 }}>
                {alert.title}
              </div>

              {/* Entity Context: Host or Identity */}
              {(alert.target_host || alert.target_identity) && (
                <div style={{ display: 'flex', gap: '10px', fontSize: '11px', color: 'var(--text-dim)', marginBottom: '8px', flexWrap: 'wrap' }}>
                  {alert.target_host && (
                    <span style={{ display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
                      <Server size={11} color="var(--accent-cyan)" /> {alert.target_host}
                    </span>
                  )}
                  {alert.target_identity && (
                    <span style={{ display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
                      <User size={11} color="var(--accent-emerald)" /> {alert.target_identity}
                    </span>
                  )}
                </div>
              )}

              {/* Severity vs Assessment Distinction */}
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '6px', fontSize: '11px', borderTop: '1px solid rgba(255,255,255,0.05)', paddingTop: '6px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                  {getSourceSeverityBadge(alert.severity)}
                  {isInvestigated && getAssessedPriorityBadge(currentAssessment)}
                </div>
                <span style={{ color: 'var(--text-dim)', fontSize: '10px', display: 'inline-flex', alignItems: 'center', gap: '3px' }}>
                  <Clock size={10} /> {alert.source}
                </span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
