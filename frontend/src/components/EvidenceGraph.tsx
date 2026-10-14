import React, { useEffect, useRef, useState, useCallback } from 'react';
import cytoscape from 'cytoscape';
import type { Core, EventObject } from 'cytoscape';
import type { GraphData, GraphNode, GraphEdge } from '../types';
import { 
  Maximize2, 
  ZoomIn, 
  ZoomOut, 
  RefreshCw, 
  RotateCcw,
  Eye,
  Layers,
  Crosshair
} from 'lucide-react';

interface EvidenceGraphProps {
  graphData: GraphData;
  onSelectNode: (node: GraphNode | null) => void;
  selectedNode: GraphNode | null;
  onSelectEdge?: (edge: GraphEdge | null) => void;
  selectedEdge?: GraphEdge | null;
  highlightedEntityIds?: string[];
  onClearHighlight?: () => void;
}

import { CATEGORY_COLORS } from '../constants';

export const EvidenceGraph: React.FC<EvidenceGraphProps> = ({ 
  graphData, 
  onSelectNode, 
  selectedNode,
  onSelectEdge,
  selectedEdge: _selectedEdge,
  highlightedEntityIds,
  onClearHighlight
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const cyRef = useRef<Core | null>(null);
  const [layoutName, setLayoutName] = useState<'breadthfirst' | 'cose' | 'concentric'>('breadthfirst');
  const [focusPathOnly, setFocusPathOnly] = useState<boolean>(false);
  const [showLegend, setShowLegend] = useState<boolean>(true);

  // Initialize and update Cytoscape instance
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
          label: e.relation,
          rawProperties: e.properties
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
            'text-margin-y': 7,
            'text-background-color': '#070a10',
            'text-background-opacity': 0.88,
            'text-background-padding': '3px',
            'text-background-shape': 'roundrectangle',
            'background-color': 'data(bgColor)',
            'border-width': 2,
            'border-color': 'data(borderColor)',
            'shape': 'data(shape)' as any,
            'width': 36,
            'height': 36,
            'transition-property': 'background-color, border-color, border-width, opacity',
            'transition-duration': 0.2
          }
        },
        {
          selector: 'node:selected',
          style: {
            'border-width': 4,
            'border-color': '#38bdf8',
            'underlay-color': '#38bdf8',
            'underlay-padding': 3,
            'underlay-opacity': 0.4
          }
        },
        {
          selector: 'edge',
          style: {
            'width': 2,
            'line-color': '#475569',
            'target-arrow-color': '#94a3b8',
            'target-arrow-shape': 'triangle',
            'arrow-scale': 1.1,
            'curve-style': 'bezier',
            'label': 'data(label)',
            'font-family': 'JetBrains Mono, monospace',
            'font-size': '9px',
            'font-weight': 500,
            'color': '#cbd5e1',
            'text-background-color': '#0d131f',
            'text-background-opacity': 0.9,
            'text-background-padding': '2px',
            'text-rotation': 'autorotate',
            'transition-property': 'line-color, target-arrow-color, width, opacity',
            'transition-duration': 0.2
          }
        },
        {
          selector: 'edge:selected',
          style: {
            'line-color': '#38bdf8',
            'target-arrow-color': '#38bdf8',
            'width': 3.5
          }
        },
        // Dimmed state when path or entity is highlighted
        {
          selector: '.dimmed',
          style: {
            'opacity': 0.16
          }
        },
        // Emphasized state for highlighted evidence path nodes
        {
          selector: 'node.highlighted',
          style: {
            'border-width': 4,
            'border-color': '#38bdf8',
            'opacity': 1,
            'underlay-color': '#38bdf8',
            'underlay-padding': 4,
            'underlay-opacity': 0.5
          }
        },
        // Emphasized state for highlighted evidence path edges
        {
          selector: 'edge.highlighted',
          style: {
            'line-color': '#38bdf8',
            'target-arrow-color': '#38bdf8',
            'width': 3.5,
            'opacity': 1
          }
        }
      ],
      layout: {
        name: layoutName,
        padding: 45,
        animate: true,
        animationDuration: 350
      }
    });

    // Node click
    cy.on('tap', 'node', (evt: EventObject) => {
      const node = evt.target;
      const rawProps = node.data('rawProperties');
      if (onSelectEdge) onSelectEdge(null);
      onSelectNode({
        id: node.id(),
        label: node.data('label'),
        category: node.data('category'),
        properties: rawProps || {}
      });
    });

    // Edge click
    cy.on('tap', 'edge', (evt: EventObject) => {
      const edge = evt.target;
      if (onSelectEdge) {
        onSelectEdge({
          id: edge.id(),
          source: edge.data('source'),
          target: edge.data('target'),
          relation: edge.data('label'),
          properties: edge.data('rawProperties') || {}
        });
      }
    });

    // Canvas click (deselect all)
    cy.on('tap', (evt: EventObject) => {
      if (evt.target === cy) {
        onSelectNode(null);
        if (onSelectEdge) onSelectEdge(null);
        if (onClearHighlight) onClearHighlight();
      }
    });

    cyRef.current = cy;

    return () => {
      cy.destroy();
    };
  }, [graphData, layoutName, onSelectNode, onSelectEdge, onClearHighlight]);

  // Handle path highlighting and dimming dynamically without reloading graph
  useEffect(() => {
    const cy = cyRef.current;
    if (!cy) return;

    cy.batch(() => {
      if (highlightedEntityIds && highlightedEntityIds.length > 0) {
        // Dim all elements first
        cy.elements().addClass('dimmed').removeClass('highlighted');

        // Highlight matching nodes
        highlightedEntityIds.forEach(id => {
          const el = cy.getElementById(id);
          if (el.nonempty()) {
            el.removeClass('dimmed').addClass('highlighted');
          }
        });

        // Highlight connecting edges between highlighted nodes
        cy.edges().forEach(edge => {
          const src = edge.data('source');
          const tgt = edge.data('target');
          if (highlightedEntityIds.includes(src) && highlightedEntityIds.includes(tgt)) {
            edge.removeClass('dimmed').addClass('highlighted');
          }
        });

        if (focusPathOnly) {
          const highlightedEles = cy.elements('.highlighted');
          if (highlightedEles.nonempty()) {
            cy.fit(highlightedEles, 45);
          }
        }
      } else {
        cy.elements().removeClass('dimmed').removeClass('highlighted');
      }
    });
  }, [highlightedEntityIds, focusPathOnly]);

  const handleZoomIn = () => cyRef.current?.zoom(cyRef.current.zoom() * 1.25);
  const handleZoomOut = () => cyRef.current?.zoom(cyRef.current.zoom() * 0.8);
  const handleFit = () => cyRef.current?.fit(undefined, 35);
  const handleReset = () => {
    if (!cyRef.current) return;
    cyRef.current.reset();
    cyRef.current.fit(undefined, 35);
  };
  const handleRelayout = () => {
    cyRef.current?.layout({ name: layoutName, animate: true, animationDuration: 300 }).run();
  };

  const handleFitSelected = useCallback(() => {
    const cy = cyRef.current;
    if (!cy) return;
    if (selectedNode) {
      const nodeEle = cy.getElementById(selectedNode.id);
      if (nodeEle.nonempty()) {
        cy.animate({
          fit: { eles: nodeEle.closedNeighborhood(), padding: 50 },
          duration: 350
        });
      }
    } else if (highlightedEntityIds && highlightedEntityIds.length > 0) {
      const highlightedEles = cy.elements('.highlighted');
      if (highlightedEles.nonempty()) {
        cy.animate({
          fit: { eles: highlightedEles, padding: 50 },
          duration: 350
        });
      }
    } else {
      cy.fit(undefined, 35);
    }
  }, [selectedNode, highlightedEntityIds]);

  return (
    <div style={{ position: 'relative', width: '100%', height: '100%', minHeight: '460px', background: 'var(--bg-primary)', borderRadius: '8px', overflow: 'hidden' }}>
      <div ref={containerRef} style={{ width: '100%', height: '100%', minHeight: '460px' }} />

      {/* Top Toolbar Controls */}
      <div style={{
        position: 'absolute',
        top: '12px',
        right: '12px',
        display: 'flex',
        alignItems: 'center',
        gap: '6px',
        background: 'rgba(13, 19, 31, 0.92)',
        backdropFilter: 'blur(10px)',
        padding: '5px 8px',
        borderRadius: '8px',
        border: '1px solid var(--border-subtle)',
        zIndex: 10
      }}>
        <button
          id="btn-graph-zoom-in"
          onClick={handleZoomIn}
          title="Zoom In"
          aria-label="Zoom In"
          style={{ background: 'transparent', border: 'none', color: 'var(--text-dim)', padding: '5px', borderRadius: '4px', display: 'flex' }}
        >
          <ZoomIn size={15} />
        </button>
        <button
          id="btn-graph-zoom-out"
          onClick={handleZoomOut}
          title="Zoom Out"
          aria-label="Zoom Out"
          style={{ background: 'transparent', border: 'none', color: 'var(--text-dim)', padding: '5px', borderRadius: '4px', display: 'flex' }}
        >
          <ZoomOut size={15} />
        </button>
        <button
          id="btn-graph-fit"
          onClick={handleFit}
          title="Fit All Nodes"
          aria-label="Fit Graph"
          style={{ background: 'transparent', border: 'none', color: 'var(--text-dim)', padding: '5px', borderRadius: '4px', display: 'flex' }}
        >
          <Maximize2 size={15} />
        </button>
        <button
          id="btn-graph-fit-selected"
          onClick={handleFitSelected}
          title="Fit Selected Entity / Path"
          aria-label="Fit Selected Entity"
          style={{ background: 'transparent', border: 'none', color: selectedNode || (highlightedEntityIds && highlightedEntityIds.length > 0) ? 'var(--accent-cyan)' : 'var(--text-dim)', padding: '5px', borderRadius: '4px', display: 'flex' }}
        >
          <Crosshair size={15} />
        </button>
        <button
          id="btn-graph-reset"
          onClick={handleReset}
          title="Reset Zoom & Pan"
          aria-label="Reset View"
          style={{ background: 'transparent', border: 'none', color: 'var(--text-dim)', padding: '5px', borderRadius: '4px', display: 'flex' }}
        >
          <RotateCcw size={15} />
        </button>
        <button
          id="btn-graph-relayout"
          onClick={handleRelayout}
          title="Recalculate Layout"
          aria-label="Recalculate Layout"
          style={{ background: 'transparent', border: 'none', color: 'var(--text-dim)', padding: '5px', borderRadius: '4px', display: 'flex' }}
        >
          <RefreshCw size={15} />
        </button>

        <div style={{ width: '1px', height: '16px', background: 'var(--border-subtle)', margin: '0 2px' }} />

        {/* Toggle Evidence Path Focus */}
        <button
          id="btn-toggle-path-focus"
          onClick={() => setFocusPathOnly(!focusPathOnly)}
          title={focusPathOnly ? "Show Full Relevant Subgraph" : "Focus Direct Evidence Path"}
          aria-label="Toggle Evidence Path Focus"
          style={{
            background: focusPathOnly ? 'rgba(56, 189, 248, 0.2)' : 'transparent',
            border: `1px solid ${focusPathOnly ? 'var(--accent-cyan)' : 'transparent'}`,
            color: focusPathOnly ? 'var(--accent-cyan)' : 'var(--text-dim)',
            padding: '3px 7px',
            borderRadius: '4px',
            fontSize: '11px',
            fontWeight: 600,
            display: 'inline-flex',
            alignItems: 'center',
            gap: '4px'
          }}
        >
          <Eye size={12} />
          <span>{focusPathOnly ? "Focused" : "Full"}</span>
        </button>

        {/* Layout Selector */}
        <select
          id="select-graph-layout"
          value={layoutName}
          onChange={(e) => setLayoutName(e.target.value as any)}
          aria-label="Select Cytoscape Layout"
          style={{
            background: 'transparent',
            border: 'none',
            color: 'var(--accent-cyan)',
            fontSize: '11px',
            fontWeight: 600,
            cursor: 'pointer',
            outline: 'none',
            paddingLeft: '2px'
          }}
        >
          <option value="breadthfirst" style={{ background: '#0d131f', color: '#fff' }}>Breadthfirst</option>
          <option value="cose" style={{ background: '#0d131f', color: '#fff' }}>Force (COSE)</option>
          <option value="concentric" style={{ background: '#0d131f', color: '#fff' }}>Concentric</option>
        </select>
      </div>

      {/* Bottom Category Legend */}
      <div style={{
        position: 'absolute',
        bottom: '12px',
        left: '12px',
        display: 'flex',
        alignItems: 'center',
        gap: '6px',
        zIndex: 10
      }}>
        <button
          onClick={() => setShowLegend(!showLegend)}
          aria-label="Toggle category legend"
          style={{
            background: 'rgba(13, 19, 31, 0.9)',
            border: '1px solid var(--border-subtle)',
            color: showLegend ? 'var(--accent-cyan)' : 'var(--text-dim)',
            padding: '4px 8px',
            borderRadius: '6px',
            fontSize: '10px',
            fontWeight: 600,
            display: 'flex',
            alignItems: 'center',
            gap: '4px'
          }}
        >
          <Layers size={11} /> Legend
        </button>

        {showLegend && (
          <div style={{
            display: 'flex',
            flexWrap: 'wrap',
            gap: '8px',
            background: 'rgba(13, 19, 31, 0.92)',
            backdropFilter: 'blur(10px)',
            padding: '5px 10px',
            borderRadius: '6px',
            border: '1px solid var(--border-subtle)',
            fontSize: '10px',
            color: 'var(--text-muted)'
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
        )}
      </div>
    </div>
  );
};
