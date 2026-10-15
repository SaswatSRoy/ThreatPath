import React, { useState, useEffect, useRef, useCallback } from 'react';
import cytoscape from 'cytoscape';
import type { Core } from 'cytoscape';
import type { 
  ScenarioValidationResponse, 
  ScenarioSummary, 
  ValidationErrorItem,
  GraphNode
} from '../types';
import { CATEGORY_COLORS, STARTER_SCENARIO } from '../constants';
import { 
  X, 
  FlaskConical, 
  Sparkles, 
  CheckCircle2, 
  AlertOctagon, 
  AlertTriangle, 
  Play, 
  Save, 
  RotateCcw, 
  FolderArchive, 
  Code2, 
  Loader2, 
  Eye, 
  CheckCheck,
  ArrowRight
} from 'lucide-react';

interface ScenarioLabModalProps {
  isOpen: boolean;
  onClose: () => void;
  sessionId: string;
  onScenarioSelected: (alertId: string) => void;
  onScenarioSaved: () => void;
}

export const ScenarioLabModal: React.FC<ScenarioLabModalProps> = ({
  isOpen,
  onClose,
  sessionId,
  onScenarioSelected,
  onScenarioSaved
}) => {
  const [activeTab, setActiveTab] = useState<'builder' | 'saved'>('builder');
  const [jsonText, setJsonText] = useState<string>(() => JSON.stringify(STARTER_SCENARIO, null, 2));
  const [validating, setValidating] = useState<boolean>(false);
  const [saving, setSaving] = useState<boolean>(false);
  const [validationResult, setValidationResult] = useState<ScenarioValidationResponse | null>(null);
  const [generalError, setGeneralError] = useState<string | null>(null);
  const [saveSuccessMsg, setSaveSuccessMsg] = useState<string | null>(null);
  
  // Saved scenarios state
  const [savedScenarios, setSavedScenarios] = useState<ScenarioSummary[]>([]);
  const [loadingSaved, setLoadingSaved] = useState<boolean>(false);

  // Preview graph state
  const previewContainerRef = useRef<HTMLDivElement>(null);
  const cyRef = useRef<Core | null>(null);
  const [selectedPreviewNode, setSelectedPreviewNode] = useState<GraphNode | null>(null);

  // Reset or reload starter template
  const loadStarterTemplate = useCallback(() => {
    setJsonText(JSON.stringify(STARTER_SCENARIO, null, 2));
    setValidationResult(null);
    setGeneralError(null);
    setSaveSuccessMsg(null);
  }, []);

  const fetchSavedScenarios = useCallback(async () => {
    setLoadingSaved(true);
    try {
      const res = await fetch('/api/scenarios', {
        headers: { 'X-Session-ID': sessionId }
      });
      if (res.ok) {
        const data: ScenarioSummary[] = await res.json();
        setSavedScenarios(data);
      }
    } catch {
      console.error('Failed to fetch saved scenarios');
    } finally {
      setLoadingSaved(false);
    }
  }, [sessionId]);

  useEffect(() => {
    if (isOpen) {
      queueMicrotask(() => {
        fetchSavedScenarios();
      });
    }
  }, [isOpen, fetchSavedScenarios]);

  // Handle preview Cytoscape rendering
  useEffect(() => {
    if (!previewContainerRef.current || !validationResult?.preview) {
      if (cyRef.current) {
        cyRef.current.destroy();
        cyRef.current = null;
      }
      return;
    }

    const preview = validationResult.preview;
    const elements: cytoscape.ElementDefinition[] = [];

    preview.nodes.forEach(n => {
      const styleInfo = CATEGORY_COLORS[n.category] || CATEGORY_COLORS.Entity;
      elements.push({
        group: 'nodes',
        data: {
          id: n.id,
          label: n.label,
          category: n.category,
          bgColor: styleInfo.bg,
          borderColor: styleInfo.border,
          shape: styleInfo.shape,
          rawProperties: n.properties
        }
      });
    });

    preview.edges.forEach(e => {
      elements.push({
        group: 'edges',
        data: {
          id: e.id,
          source: e.source,
          target: e.target,
          label: e.relation,
          rawProperties: e.properties
        }
      });
    });

    if (cyRef.current) {
      cyRef.current.destroy();
    }

    const cy = cytoscape({
      container: previewContainerRef.current,
      elements,
      style: [
        {
          selector: 'node',
          style: {
            'label': 'data(label)',
            'color': '#f8fafc',
            'font-family': 'Inter, sans-serif',
            'font-size': '10px',
            'font-weight': 600,
            'text-valign': 'bottom',
            'text-margin-y': 5,
            'text-background-color': '#070a10',
            'text-background-opacity': 0.85,
            'text-background-padding': '2px',
            'text-background-shape': 'roundrectangle',
            'background-color': 'data(bgColor)',
            'border-width': 2,
            'border-color': 'data(borderColor)',
            'shape': 'data(shape)' as any,
            'width': 28,
            'height': 28
          }
        },
        {
          selector: 'edge',
          style: {
            'width': 1.5,
            'line-color': '#475569',
            'target-arrow-color': '#38bdf8',
            'target-arrow-shape': 'triangle',
            'arrow-scale': 0.8,
            'curve-style': 'bezier',
            'label': 'data(label)',
            'font-family': 'JetBrains Mono, monospace',
            'font-size': '8px',
            'color': '#94a3b8',
            'text-background-color': '#070a10',
            'text-background-opacity': 0.85,
            'text-background-padding': '2px'
          }
        },
        {
          selector: 'node:selected',
          style: {
            'border-color': '#38bdf8',
            'border-width': 3
          }
        }
      ],
      layout: {
        name: 'breadthfirst',
        directed: true,
        padding: 20,
        spacingFactor: 1.1
      } as any,
      userZoomingEnabled: true,
      userPanningEnabled: true
    });

    cy.on('tap', 'node', (evt) => {
      const node = evt.target;
      setSelectedPreviewNode({
        id: node.data('id'),
        label: node.data('label'),
        category: node.data('category'),
        properties: node.data('rawProperties') || {}
      });
    });

    cy.on('tap', (evt) => {
      if (evt.target === cy) {
        setSelectedPreviewNode(null);
      }
    });

    cyRef.current = cy;
  }, [validationResult]);

  const handleValidate = async () => {
    setValidating(true);
    setGeneralError(null);
    setSaveSuccessMsg(null);
    try {
      let parsedPayload: any;
      try {
        parsedPayload = JSON.parse(jsonText);
      } catch (parseErr: any) {
        setValidationResult({
          valid: false,
          errors: [{ field: 'syntax', message: `Malformed JSON: ${parseErr.message}`, code: 'JSON_SYNTAX_ERROR' }],
          warnings: [],
          preview: null
        });
        setValidating(false);
        return;
      }

      const res = await fetch('/api/scenarios/validate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(parsedPayload)
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Validation request failed');
      }

      const result: ScenarioValidationResponse = await res.json();
      setValidationResult(result);
    } catch (e: any) {
      setGeneralError(e.message || 'Validation failed');
    } finally {
      setValidating(false);
    }
  };

  const handleFormatJson = () => {
    try {
      const parsed = JSON.parse(jsonText);
      setJsonText(JSON.stringify(parsed, null, 2));
      setGeneralError(null);
    } catch (e: any) {
      setGeneralError(`Cannot format: Invalid JSON (${e.message})`);
    }
  };

  const handleSaveScenario = async (andInvestigate: boolean = false) => {
    setSaving(true);
    setGeneralError(null);
    setSaveSuccessMsg(null);
    try {
      let parsedPayload: any;
      try {
        parsedPayload = JSON.parse(jsonText);
      } catch (parseErr: any) {
        setGeneralError(`Invalid JSON: ${parseErr.message}`);
        setSaving(false);
        return;
      }

      const res = await fetch('/api/scenarios', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Session-ID': sessionId
        },
        body: JSON.stringify(parsedPayload)
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Failed to save scenario');
      }

      const summary: ScenarioSummary = await res.json();
      setSaveSuccessMsg(`Scenario '${summary.name}' saved successfully in FalkorDB (Alert ID: ${summary.alert_id})`);
      onScenarioSaved();
      await fetchSavedScenarios();

      if (andInvestigate) {
        onScenarioSelected(summary.alert_id);
        onClose();
      }
    } catch (e: any) {
      setGeneralError(e.message || 'Save error');
    } finally {
      setSaving(false);
    }
  };

  const handleLoadScenarioIntoEditor = async (scenarioId: string) => {
    try {
      const res = await fetch(`/api/scenarios/${scenarioId}`, {
        headers: { 'X-Session-ID': sessionId }
      });
      if (res.ok) {
        const details = await res.json();
        setJsonText(JSON.stringify(details.payload, null, 2));
        setActiveTab('builder');
        setValidationResult(null);
        setSaveSuccessMsg(null);
        setGeneralError(null);
      }
    } catch {
      setGeneralError('Could not load scenario details.');
    }
  };

  if (!isOpen) return null;

  return (
    <div style={{
      position: 'fixed',
      inset: 0,
      zIndex: 9999,
      background: 'rgba(3, 7, 18, 0.85)',
      backdropFilter: 'blur(10px)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      padding: '20px'
    }}>
      <div 
        className="glass-panel" 
        style={{
          width: '100%',
          maxWidth: '1280px',
          height: '92vh',
          display: 'flex',
          flexDirection: 'column',
          overflow: 'hidden',
          background: 'rgba(11, 17, 32, 0.96)',
          border: '1px solid rgba(56, 189, 248, 0.3)',
          boxShadow: '0 25px 60px -15px rgba(0, 0, 0, 0.9)'
        }}
      >
        {/* Modal Header */}
        <div style={{
          padding: '16px 24px',
          borderBottom: '1px solid var(--border-subtle)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          background: 'rgba(15, 23, 42, 0.8)'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <div style={{
              width: '36px',
              height: '36px',
              borderRadius: '8px',
              background: 'linear-gradient(135deg, #0284c7, #6366f1)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              boxShadow: '0 0 12px rgba(56, 189, 248, 0.4)'
            }}>
              <FlaskConical size={20} color="#ffffff" />
            </div>
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <h2 style={{ fontSize: '16px', fontWeight: 800, letterSpacing: '-0.01em', color: 'var(--text-main)' }}>
                  CUSTOM SCENARIO LAB
                </h2>
                <span style={{
                  background: 'rgba(56, 189, 248, 0.15)',
                  color: 'var(--accent-cyan)',
                  border: '1px solid rgba(56, 189, 248, 0.3)',
                  borderRadius: '4px',
                  padding: '1px 6px',
                  fontSize: '10px',
                  fontWeight: 700
                }}>
                  Schema v1.0
                </span>
                <span style={{
                  background: 'rgba(52, 211, 153, 0.15)',
                  color: 'var(--accent-emerald)',
                  border: '1px solid rgba(52, 211, 153, 0.3)',
                  borderRadius: '4px',
                  padding: '1px 6px',
                  fontSize: '10px',
                  fontWeight: 700
                }}>
                  Session Isolated: {sessionId.slice(0, 14)}...
                </span>
              </div>
              <p style={{ fontSize: '12px', color: 'var(--text-dim)', marginTop: '2px' }}>
                Design custom threat topologies, validate against FalkorDB schema allowlists, preview attack graphs, and trigger deterministic investigations.
              </p>
            </div>
          </div>

          <button
            onClick={onClose}
            style={{
              background: 'transparent',
              border: 'none',
              color: 'var(--text-dim)',
              padding: '6px',
              borderRadius: '6px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center'
            }}
            title="Close Lab (Esc)"
          >
            <X size={20} />
          </button>
        </div>

        {/* Tab Switcher */}
        <div style={{
          padding: '8px 24px',
          borderBottom: '1px solid var(--border-subtle)',
          display: 'flex',
          gap: '8px',
          background: 'rgba(7, 10, 16, 0.5)'
        }}>
          <button
            onClick={() => setActiveTab('builder')}
            style={{
              background: activeTab === 'builder' ? 'rgba(56, 189, 248, 0.18)' : 'transparent',
              border: `1px solid ${activeTab === 'builder' ? 'var(--accent-cyan)' : 'transparent'}`,
              color: activeTab === 'builder' ? 'var(--accent-cyan)' : 'var(--text-dim)',
              padding: '6px 14px',
              borderRadius: '6px',
              fontSize: '12px',
              fontWeight: 600,
              display: 'flex',
              alignItems: 'center',
              gap: '6px'
            }}
          >
            <Code2 size={14} />
            Scenario Builder & Validator
          </button>

          <button
            onClick={() => setActiveTab('saved')}
            style={{
              background: activeTab === 'saved' ? 'rgba(56, 189, 248, 0.18)' : 'transparent',
              border: `1px solid ${activeTab === 'saved' ? 'var(--accent-cyan)' : 'transparent'}`,
              color: activeTab === 'saved' ? 'var(--accent-cyan)' : 'var(--text-dim)',
              padding: '6px 14px',
              borderRadius: '6px',
              fontSize: '12px',
              fontWeight: 600,
              display: 'flex',
              alignItems: 'center',
              gap: '6px'
            }}
          >
            <FolderArchive size={14} />
            Session Scenarios ({savedScenarios.length})
          </button>
        </div>

        {/* Main Content Area */}
        <div style={{ flex: 1, overflow: 'hidden', display: 'flex' }}>
          {activeTab === 'builder' ? (
            <div style={{
              display: 'grid',
              gridTemplateColumns: 'minmax(420px, 1fr) minmax(420px, 1fr)',
              width: '100%',
              height: '100%',
              overflow: 'hidden'
            }}>
              {/* Left Column: JSON Editor */}
              <div style={{
                display: 'flex',
                flexDirection: 'column',
                borderRight: '1px solid var(--border-subtle)',
                background: '#070a10',
                overflow: 'hidden'
              }}>
                {/* Editor Toolbar */}
                <div style={{
                  padding: '10px 16px',
                  background: 'rgba(15, 23, 42, 0.7)',
                  borderBottom: '1px solid var(--border-subtle)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  gap: '8px',
                  flexWrap: 'wrap'
                }}>
                  <span style={{ fontSize: '11px', color: 'var(--text-muted)', fontWeight: 600 }}>
                    JSON Schema Editor
                  </span>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <button
                      onClick={loadStarterTemplate}
                      style={{
                        background: 'rgba(255, 255, 255, 0.05)',
                        border: '1px solid var(--border-subtle)',
                        color: 'var(--text-main)',
                        padding: '4px 10px',
                        borderRadius: '4px',
                        fontSize: '11px',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '5px'
                      }}
                      title="Load synthetic PowerShell endpoint scenario"
                    >
                      <Sparkles size={12} color="#c084fc" />
                      Load Starter
                    </button>
                    <button
                      onClick={handleFormatJson}
                      style={{
                        background: 'rgba(255, 255, 255, 0.05)',
                        border: '1px solid var(--border-subtle)',
                        color: 'var(--text-main)',
                        padding: '4px 10px',
                        borderRadius: '4px',
                        fontSize: '11px',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '5px'
                      }}
                      title="Format and pretty-print JSON"
                    >
                      <CheckCheck size={12} color="#34d399" />
                      Format
                    </button>
                    <button
                      onClick={() => { setJsonText('{\n  "schema_version": "1.0",\n  "name": "",\n  "alert": {\n    "id": "alert-custom-001",\n    "title": ""\n  },\n  "entities": [],\n  "relationships": []\n}'); setValidationResult(null); }}
                      style={{
                        background: 'transparent',
                        border: '1px solid var(--border-subtle)',
                        color: 'var(--text-dim)',
                        padding: '4px 8px',
                        borderRadius: '4px',
                        fontSize: '11px'
                      }}
                      title="Reset editor"
                    >
                      <RotateCcw size={12} />
                    </button>
                  </div>
                </div>

                {/* Textarea Code Editor */}
                <div style={{ flex: 1, position: 'relative', overflow: 'hidden' }}>
                  <textarea
                    value={jsonText}
                    onChange={(e) => {
                      setJsonText(e.target.value);
                      setSaveSuccessMsg(null);
                    }}
                    spellCheck={false}
                    style={{
                      width: '100%',
                      height: '100%',
                      background: 'transparent',
                      border: 'none',
                      color: '#f1f5f9',
                      fontFamily: 'JetBrains Mono, monospace',
                      fontSize: '12px',
                      lineHeight: '1.6',
                      padding: '16px',
                      resize: 'none',
                      outline: 'none',
                      whiteSpace: 'pre',
                      overflowY: 'auto'
                    }}
                    placeholder="Paste or write structured scenario JSON here..."
                  />
                </div>

                {/* Bottom Action Bar */}
                <div style={{
                  padding: '12px 16px',
                  background: 'rgba(15, 23, 42, 0.9)',
                  borderTop: '1px solid var(--border-subtle)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  gap: '10px'
                }}>
                  <button
                    onClick={handleValidate}
                    disabled={validating || !jsonText.trim()}
                    style={{
                      background: 'rgba(56, 189, 248, 0.15)',
                      border: '1px solid var(--accent-cyan)',
                      color: 'var(--accent-cyan)',
                      padding: '8px 16px',
                      borderRadius: '6px',
                      fontSize: '12px',
                      fontWeight: 700,
                      display: 'flex',
                      alignItems: 'center',
                      gap: '6px'
                    }}
                  >
                    {validating ? <Loader2 size={14} className="animate-spin" /> : <Eye size={14} />}
                    Validate Scenario
                  </button>

                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <button
                      onClick={() => handleSaveScenario(false)}
                      disabled={saving || !validationResult?.valid}
                      style={{
                        background: 'rgba(255, 255, 255, 0.08)',
                        border: '1px solid var(--border-subtle)',
                        color: validationResult?.valid ? '#f8fafc' : 'var(--text-dim)',
                        padding: '8px 14px',
                        borderRadius: '6px',
                        fontSize: '12px',
                        fontWeight: 600,
                        display: 'flex',
                        alignItems: 'center',
                        gap: '6px'
                      }}
                      title={!validationResult?.valid ? 'Validate scenario successfully before saving' : 'Save to session graph'}
                    >
                      {saving ? <Loader2 size={14} className="animate-spin" /> : <Save size={14} />}
                      Save to Graph
                    </button>

                    <button
                      onClick={() => handleSaveScenario(true)}
                      disabled={saving || !validationResult?.valid}
                      style={{
                        background: validationResult?.valid ? 'linear-gradient(135deg, #0284c7, #2563eb)' : 'rgba(255, 255, 255, 0.05)',
                        border: validationResult?.valid ? 'none' : '1px solid var(--border-subtle)',
                        color: validationResult?.valid ? '#ffffff' : 'var(--text-dim)',
                        padding: '8px 16px',
                        borderRadius: '6px',
                        fontSize: '12px',
                        fontWeight: 700,
                        display: 'flex',
                        alignItems: 'center',
                        gap: '6px',
                        boxShadow: validationResult?.valid ? '0 0 15px rgba(2, 132, 199, 0.4)' : 'none'
                      }}
                      title={!validationResult?.valid ? 'Validate scenario successfully before saving' : 'Save and trigger ThreatPath investigation'}
                    >
                      {saving ? <Loader2 size={14} className="animate-spin" /> : <Play size={14} />}
                      Save & Investigate
                    </button>
                  </div>
                </div>
              </div>

              {/* Right Column: Validation Status & Graph Preview */}
              <div style={{
                display: 'flex',
                flexDirection: 'column',
                background: 'rgba(11, 17, 32, 0.7)',
                overflow: 'hidden'
              }}>
                {/* Status Messages */}
                {generalError && (
                  <div style={{
                    padding: '10px 16px',
                    background: 'rgba(225, 29, 72, 0.15)',
                    borderBottom: '1px solid rgba(225, 29, 72, 0.3)',
                    color: '#fb7185',
                    fontSize: '12px',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '8px'
                  }}>
                    <AlertOctagon size={16} />
                    <span>{generalError}</span>
                  </div>
                )}

                {saveSuccessMsg && (
                  <div style={{
                    padding: '10px 16px',
                    background: 'rgba(52, 211, 153, 0.15)',
                    borderBottom: '1px solid rgba(52, 211, 153, 0.3)',
                    color: '#34d399',
                    fontSize: '12px',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '8px'
                  }}>
                    <CheckCircle2 size={16} />
                    <span>{saveSuccessMsg}</span>
                  </div>
                )}

                {/* Validation Feedback Banner */}
                <div style={{
                  padding: '12px 16px',
                  background: 'rgba(15, 23, 42, 0.8)',
                  borderBottom: '1px solid var(--border-subtle)',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '8px'
                }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span style={{ fontSize: '11px', color: 'var(--text-muted)', fontWeight: 600 }}>
                      Validation Feedback & Preview
                    </span>
                    {validationResult && (
                      <span style={{
                        fontSize: '11px',
                        fontWeight: 700,
                        color: validationResult.valid ? '#34d399' : '#fb7185',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '5px'
                      }}>
                        {validationResult.valid ? (
                          <>
                            <CheckCircle2 size={13} /> Valid Topology ({validationResult.preview?.nodes.length || 0} nodes, {validationResult.preview?.edges.length || 0} edges)
                          </>
                        ) : (
                          <>
                            <AlertOctagon size={13} /> {validationResult.errors.length} Validation Errors
                          </>
                        )}
                      </span>
                    )}
                  </div>

                  {/* Errors List */}
                  {validationResult && !validationResult.valid && (
                    <div style={{
                      maxHeight: '120px',
                      overflowY: 'auto',
                      display: 'flex',
                      flexDirection: 'column',
                      gap: '6px',
                      padding: '8px',
                      background: 'rgba(225, 29, 72, 0.1)',
                      border: '1px solid rgba(225, 29, 72, 0.25)',
                      borderRadius: '6px'
                    }}>
                      {validationResult.errors.map((err: ValidationErrorItem, i: number) => (
                        <div key={i} style={{ fontSize: '11px', color: '#fb7185', display: 'flex', alignItems: 'flex-start', gap: '6px' }}>
                          <span style={{ fontFamily: 'JetBrains Mono, monospace', background: 'rgba(225, 29, 72, 0.2)', padding: '1px 4px', borderRadius: '3px', fontSize: '10px' }}>
                            {err.field}
                          </span>
                          <span>{err.message}</span>
                        </div>
                      ))}
                    </div>
                  )}

                  {/* Warnings List */}
                  {validationResult?.warnings && validationResult.warnings.length > 0 && (
                    <div style={{
                      maxHeight: '90px',
                      overflowY: 'auto',
                      display: 'flex',
                      flexDirection: 'column',
                      gap: '4px',
                      padding: '8px',
                      background: 'rgba(245, 158, 11, 0.08)',
                      border: '1px solid rgba(245, 158, 11, 0.25)',
                      borderRadius: '6px'
                    }}>
                      {validationResult.warnings.map((w: string, i: number) => (
                        <div key={i} style={{ fontSize: '11px', color: '#fbbf24', display: 'flex', alignItems: 'center', gap: '6px' }}>
                          <AlertTriangle size={12} />
                          <span>{w}</span>
                        </div>
                      ))}
                    </div>
                  )}

                  {!validationResult && (
                    <div style={{ fontSize: '11px', color: 'var(--text-dim)', fontStyle: 'italic' }}>
                      Click "Validate Scenario" to test schema compliance, verify allowed relationship directions, and render the attack graph preview.
                    </div>
                  )}
                </div>

                {/* Graph Preview Canvas */}
                <div style={{ flex: 1, position: 'relative', overflow: 'hidden' }}>
                  {validationResult?.valid ? (
                    <div 
                      ref={previewContainerRef} 
                      style={{ 
                        width: '100%', 
                        height: '100%',
                        background: 'radial-gradient(circle at center, rgba(30, 41, 59, 0.3) 0%, rgba(7, 10, 16, 0.8) 100%)'
                      }} 
                    />
                  ) : (
                    <div style={{
                      width: '100%',
                      height: '100%',
                      display: 'flex',
                      flexDirection: 'column',
                      alignItems: 'center',
                      justifyContent: 'center',
                      color: 'var(--text-dim)',
                      gap: '12px'
                    }}>
                      <div style={{
                        width: '48px',
                        height: '48px',
                        borderRadius: '50%',
                        background: 'rgba(255, 255, 255, 0.04)',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center'
                      }}>
                        <Eye size={24} color="#64748b" />
                      </div>
                      <span style={{ fontSize: '12px' }}>
                        Graph preview will appear here upon successful validation.
                      </span>
                    </div>
                  )}

                  {/* Selected Preview Node Floating Card */}
                  {selectedPreviewNode && (
                    <div style={{
                      position: 'absolute',
                      bottom: '12px',
                      left: '12px',
                      right: '12px',
                      background: 'rgba(15, 23, 42, 0.95)',
                      backdropFilter: 'blur(12px)',
                      border: '1px solid rgba(56, 189, 248, 0.3)',
                      borderRadius: '8px',
                      padding: '10px 14px',
                      boxShadow: '0 8px 24px rgba(0, 0, 0, 0.8)'
                    }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                          <span style={{
                            background: CATEGORY_COLORS[selectedPreviewNode.category]?.bg || '#1e293b',
                            color: CATEGORY_COLORS[selectedPreviewNode.category]?.border || '#94a3b8',
                            border: `1px solid ${CATEGORY_COLORS[selectedPreviewNode.category]?.border || '#94a3b8'}`,
                            padding: '1px 6px',
                            borderRadius: '4px',
                            fontSize: '10px',
                            fontWeight: 700
                          }}>
                            {selectedPreviewNode.category}
                          </span>
                          <span style={{ fontSize: '12px', fontWeight: 700, color: '#f8fafc' }}>
                            {selectedPreviewNode.label}
                          </span>
                        </div>
                        <button
                          onClick={() => setSelectedPreviewNode(null)}
                          style={{ background: 'transparent', border: 'none', color: '#94a3b8' }}
                        >
                          <X size={14} />
                        </button>
                      </div>
                      <div style={{ fontSize: '11px', color: '#94a3b8', display: 'flex', flexWrap: 'wrap', gap: '10px' }}>
                        <span>ID: <code style={{ color: '#38bdf8' }}>{selectedPreviewNode.id}</code></span>
                        {Object.entries(selectedPreviewNode.properties).map(([k, v]) => (
                          k !== 'id' && (
                            <span key={k}>
                              {k}: <code style={{ color: '#e2e8f0' }}>{String(v)}</code>
                            </span>
                          )
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            </div>
          ) : (
            /* Saved Scenarios Tab */
            <div style={{
              flex: 1,
              padding: '24px',
              overflowY: 'auto',
              background: '#070a10',
              display: 'flex',
              flexDirection: 'column',
              gap: '16px'
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div>
                  <h3 style={{ fontSize: '14px', fontWeight: 700, color: 'var(--text-main)' }}>
                    Custom Scenarios for Current Session
                  </h3>
                  <p style={{ fontSize: '12px', color: 'var(--text-dim)', marginTop: '2px' }}>
                    These scenarios are stored in FalkorDB and scoped strictly to session <code>{sessionId}</code>.
                  </p>
                </div>
                <button
                  onClick={fetchSavedScenarios}
                  disabled={loadingSaved}
                  style={{
                    background: 'rgba(255, 255, 255, 0.05)',
                    border: '1px solid var(--border-subtle)',
                    color: 'var(--text-main)',
                    padding: '6px 12px',
                    borderRadius: '6px',
                    fontSize: '12px',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '6px'
                  }}
                >
                  {loadingSaved ? <Loader2 size={12} className="animate-spin" /> : <RotateCcw size={12} />}
                  Refresh List
                </button>
              </div>

              {savedScenarios.length === 0 ? (
                <div style={{
                  padding: '48px 24px',
                  border: '1px dashed var(--border-subtle)',
                  borderRadius: '10px',
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: '12px',
                  color: 'var(--text-dim)'
                }}>
                  <FolderArchive size={36} color="#475569" />
                  <span style={{ fontSize: '13px', fontWeight: 600 }}>No custom scenarios created in this session.</span>
                  <p style={{ fontSize: '12px', textAlign: 'center', maxWidth: '400px' }}>
                    Use the Scenario Builder tab to paste or load structured threat JSON and save it to FalkorDB.
                  </p>
                  <button
                    onClick={() => setActiveTab('builder')}
                    style={{
                      background: 'rgba(56, 189, 248, 0.15)',
                      border: '1px solid var(--accent-cyan)',
                      color: 'var(--accent-cyan)',
                      padding: '6px 14px',
                      borderRadius: '6px',
                      fontSize: '12px',
                      fontWeight: 600,
                      marginTop: '8px'
                    }}
                  >
                    Open Builder
                  </button>
                </div>
              ) : (
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(360px, 1fr))', gap: '16px' }}>
                  {savedScenarios.map((scen: ScenarioSummary) => (
                    <div
                      key={scen.id}
                      className="glass-panel"
                      style={{
                        padding: '16px',
                        display: 'flex',
                        flexDirection: 'column',
                        gap: '12px',
                        background: 'rgba(15, 23, 42, 0.85)',
                        border: '1px solid rgba(255, 255, 255, 0.08)'
                      }}
                    >
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                        <div>
                          <div style={{ fontSize: '13px', fontWeight: 700, color: 'var(--text-main)' }}>
                            {scen.name}
                          </div>
                          <div style={{ fontSize: '11px', color: 'var(--accent-cyan)', fontFamily: 'JetBrains Mono, monospace', marginTop: '2px' }}>
                            Alert: {scen.alert_id}
                          </div>
                        </div>
                        <span style={{
                          background: scen.severity === 'CRITICAL' ? 'rgba(225, 29, 72, 0.15)' : 'rgba(249, 115, 22, 0.15)',
                          color: scen.severity === 'CRITICAL' ? '#fb7185' : '#fb923c',
                          border: `1px solid ${scen.severity === 'CRITICAL' ? 'rgba(225, 29, 72, 0.3)' : 'rgba(249, 115, 22, 0.3)'}`,
                          padding: '2px 6px',
                          borderRadius: '4px',
                          fontSize: '10px',
                          fontWeight: 700
                        }}>
                          {scen.severity}
                        </span>
                      </div>

                      <p style={{ fontSize: '11px', color: 'var(--text-muted)', lineHeight: '1.5', minHeight: '34px' }}>
                        {scen.description || 'No description provided.'}
                      </p>

                      <div style={{
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'space-between',
                        paddingTop: '8px',
                        borderTop: '1px solid var(--border-subtle)',
                        fontSize: '10px',
                        color: 'var(--text-dim)'
                      }}>
                        <span>Created: {new Date(scen.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
                        <div style={{ display: 'flex', gap: '8px' }}>
                          <button
                            onClick={() => handleLoadScenarioIntoEditor(scen.id)}
                            style={{
                              background: 'transparent',
                              border: '1px solid var(--border-subtle)',
                              color: 'var(--text-muted)',
                              padding: '4px 8px',
                              borderRadius: '4px',
                              fontSize: '11px'
                            }}
                          >
                            Edit
                          </button>
                          <button
                            onClick={() => {
                              onScenarioSelected(scen.alert_id);
                              onClose();
                            }}
                            style={{
                              background: 'rgba(56, 189, 248, 0.15)',
                              border: '1px solid var(--accent-cyan)',
                              color: 'var(--accent-cyan)',
                              padding: '4px 10px',
                              borderRadius: '4px',
                              fontSize: '11px',
                              fontWeight: 600,
                              display: 'flex',
                              alignItems: 'center',
                              gap: '4px'
                            }}
                          >
                            Investigate
                            <ArrowRight size={11} />
                          </button>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
