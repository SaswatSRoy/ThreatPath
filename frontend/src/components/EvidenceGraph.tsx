import React, { useEffect, useRef, useState } from 'react';
import cytoscape from 'cytoscape';
import type { Core, EventObject } from 'cytoscape';
import type { GraphData, GraphNode } from '../types';
import { Maximize2, ZoomIn, ZoomOut, RefreshCw } from 'lucide-react';

interface EvidenceGraphProps {
  graphData: GraphData;
  onSelectNode: (node: GraphNode | null) => void;
  selectedNode: GraphNode | null;
}

const CATEGORY_COLORS: Record<string, { bg: string; border: string; shape: string }> = {
  Alert: { bg: '#881337', border: '#f43f5e', shape: 'diamond' },
  Event: { bg: '#78350f', border: '#f59e0b', shape: 'round-rectangle' },
  Host: { bg: '#0c4a6e', border: '#38bdf8', shape: 'rectangle' },
  Process: { bg: '#581c87', border: '#c084fc', shape: 'round-triangle' },
  Indicator: { bg: '#991b1b', border: '#ef4444', shape: 'octagon' },
  Asset: { bg: '#713f12', border: '#eab308', shape: 'barrel' },
  Technique: { bg: '#134e4a', border: '#2dd4bf', shape: 'hexagon' },
  Software: { bg: '#064e3b', border: '#34d399', shape: 'ellipse' },
  Vulnerability: { bg: '#7c2d12', border: '#fb923c', shape: 'vee' },
  Identity: { bg: '#115e59', border: '#5eead4', shape: 'round-rectangle' },
  Entity: { bg: '#1e293b', border: '#94a3b8', shape: 'ellipse' }
};

export const EvidenceGraph: React.FC<EvidenceGraphProps> = ({ graphData, onSelectNode, selectedNode: _selectedNode }) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const cyRef = useRef<Core | null>(null);
  const [layoutName, setLayoutName] = useState<'breadthfirst' | 'cose' | 'concentric'>('breadthfirst');

  useEffect(() => {
    if (!containerRef.current) return;

    const elements: cytoscape.ElementDefinition[] = [];

    graphData.nodes.forEach(n => {
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

    graphData.edges.forEach(e => {
      elements.push({
        group: 'edges',
        data: {
          id: e.id,
          source: e.source,
          target: e.target,
          label: e.relation
        }
      });
    });

    const cy = cytoscape({
      container: containerRef.current,
      elements,
      style: [
        {
          selector: 'node',
          style: {
            'label': 'data(label)',
            'color': '#f8fafc',
            'font-family': 'Inter, sans-serif',
            'font-size': '11px',
            'font-weight': 600,
            'text-valign': 'bottom',
            'text-margin-y': 6,
            'text-background-color': '#0a0e17',
            'text-background-opacity': 0.8,
            'text-background-padding': '3px',
            'text-background-shape': 'roundrectangle',
            'background-color': 'data(bgColor)',
            'border-width': 2,
            'border-color': 'data(borderColor)',
            'shape': 'data(shape)' as any,
            'width': 38,
            'height': 38,
            'transition-property': 'background-color, border-color, border-width',
            'transition-duration': 0.2
          }
        },
        {
          selector: 'node:selected',
          style: {
            'border-width': 4,
            'border-color': '#38bdf8'
          }
        },
        {
          selector: 'edge',
          style: {
            'width': 2,
            'line-color': '#475569',
            'target-arrow-color': '#94a3b8',
            'target-arrow-shape': 'triangle',
            'curve-style': 'bezier',
            'label': 'data(label)',
            'font-family': 'JetBrains Mono, monospace',
            'font-size': '9px',
            'color': '#cbd5e1',
            'text-background-color': '#0f172a',
            'text-background-opacity': 0.85,
            'text-background-padding': '2px',
            'text-rotation': 'autorotate'
          }
        },
        {
          selector: 'edge:selected',
          style: {
            'line-color': '#38bdf8',
            'target-arrow-color': '#38bdf8',
            'width': 3
          }
        }
      ],
      layout: {
        name: layoutName,
        padding: 40,
        animate: true,
        animationDuration: 400
      }
    });

    cy.on('tap', 'node', (evt: EventObject) => {
      const node = evt.target;
      const rawProps = node.data('rawProperties');
      onSelectNode({
        id: node.id(),
        label: node.data('label'),
        category: node.data('category'),
        properties: rawProps || {}
      });
    });

    cy.on('tap', (evt: EventObject) => {
      if (evt.target === cy) {
        onSelectNode(null);
      }
    });

    cyRef.current = cy;

    return () => {
      cy.destroy();
    };
  }, [graphData, layoutName]);

  const handleZoomIn = () => cyRef.current?.zoom(cyRef.current.zoom() * 1.25);
  const handleZoomOut = () => cyRef.current?.zoom(cyRef.current.zoom() * 0.8);
  const handleFit = () => cyRef.current?.fit(undefined, 30);
  const handleRelayout = () => {
    cyRef.current?.layout({ name: layoutName, animate: true }).run();
  };

  return (
    <div style={{ position: 'relative', width: '100%', height: '100%', minHeight: '440px', background: '#090d16', borderRadius: '8px', overflow: 'hidden' }}>
      <div ref={containerRef} style={{ width: '100%', height: '100%', minHeight: '440px' }} />

      <div style={{
        position: 'absolute',
        top: '12px',
        right: '12px',
        display: 'flex',
        gap: '6px',
        background: 'rgba(15, 23, 42, 0.85)',
        backdropFilter: 'blur(8px)',
        padding: '6px',
        borderRadius: '8px',
        border: '1px solid rgba(255, 255, 255, 0.1)',
        zIndex: 10
      }}>
        <button
          id="btn-graph-zoom-in"
          onClick={handleZoomIn}
          title="Zoom In"
          style={{ background: 'transparent', border: 'none', color: '#94a3b8', padding: '4px', borderRadius: '4px' }}
        >
          <ZoomIn size={16} />
        </button>
        <button
          id="btn-graph-zoom-out"
          onClick={handleZoomOut}
          title="Zoom Out"
          style={{ background: 'transparent', border: 'none', color: '#94a3b8', padding: '4px', borderRadius: '4px' }}
        >
          <ZoomOut size={16} />
        </button>
        <button
          id="btn-graph-fit"
          onClick={handleFit}
          title="Fit Graph"
          style={{ background: 'transparent', border: 'none', color: '#94a3b8', padding: '4px', borderRadius: '4px' }}
        >
          <Maximize2 size={16} />
        </button>
        <button
          id="btn-graph-relayout"
          onClick={handleRelayout}
          title="Reset Layout"
          style={{ background: 'transparent', border: 'none', color: '#94a3b8', padding: '4px', borderRadius: '4px' }}
        >
          <RefreshCw size={16} />
        </button>
        <div style={{ width: '1px', background: 'rgba(255,255,255,0.1)', margin: '0 2px' }} />
        <select
          id="select-graph-layout"
          value={layoutName}
          onChange={(e) => setLayoutName(e.target.value as any)}
          style={{
            background: 'transparent',
            border: 'none',
            color: '#38bdf8',
            fontSize: '11px',
            fontWeight: 600,
            cursor: 'pointer',
            outline: 'none'
          }}
        >
          <option value="breadthfirst" style={{ background: '#0f172a', color: '#fff' }}>Breadthfirst</option>
          <option value="cose" style={{ background: '#0f172a', color: '#fff' }}>Force-Directed (COSE)</option>
          <option value="concentric" style={{ background: '#0f172a', color: '#fff' }}>Concentric</option>
        </select>
      </div>

      <div style={{
        position: 'absolute',
        bottom: '12px',
        left: '12px',
        display: 'flex',
        flexWrap: 'wrap',
        gap: '8px',
        background: 'rgba(15, 23, 42, 0.85)',
        backdropFilter: 'blur(8px)',
        padding: '6px 12px',
        borderRadius: '8px',
        border: '1px solid rgba(255, 255, 255, 0.08)',
        fontSize: '10px',
        color: '#94a3b8',
        zIndex: 10
      }}>
        {Object.entries(CATEGORY_COLORS).slice(0, 8).map(([cat, colors]) => (
          <div key={cat} style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
            <span style={{
              width: '8px',
              height: '8px',
              borderRadius: '2px',
              backgroundColor: colors.bg,
              border: `1px solid ${colors.border}`
            }} />
            <span>{cat}</span>
          </div>
        ))}
      </div>
    </div>
  );
};
