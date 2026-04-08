import { useEffect, useMemo, useRef, useState } from 'react';
import Sigma from 'sigma';
import { centerOnNode, highlightSelection, loadGraphFromData, resetStyles } from './graph';

const GRAPH_VIEWS = {
  topic: {
    label: 'Topic Graph',
    description: 'Concept clusters connected to representative papers.',
    url: '/data/topic-graph.json',
  },
  citation: {
    label: 'Citation Graph',
    description: 'Paper-to-paper citations using the same paper IDs as the topic graph.',
    url: '/data/citation-graph.json',
  },
};

function App() {
  const containerRef = useRef(null);
  const rendererRef = useRef(null);
  const graphRef = useRef(null);

  const [activeView, setActiveView] = useState('topic');
  const [graphData, setGraphData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [selectedNodeId, setSelectedNodeId] = useState(null);
  const [selectedEdgeId, setSelectedEdgeId] = useState(null);
  const [hoveredNodeId, setHoveredNodeId] = useState(null);
  const [search, setSearch] = useState('');

  const activeViewConfig = GRAPH_VIEWS[activeView];

  useEffect(() => {
    const controller = new AbortController();

    async function load() {
      try {
        setLoading(true);
        setError('');

        const response = await fetch(activeViewConfig.url, { signal: controller.signal });
        if (!response.ok) {
          throw new Error(`Failed to load graph: ${response.status}`);
        }

        const data = await response.json();
        setGraphData(data);
        setSelectedNodeId(null);
        setSelectedEdgeId(null);
        setHoveredNodeId(null);
        setSearch('');
      } catch (err) {
        if (err instanceof Error && err.name === 'AbortError') return;
        setError(err instanceof Error ? err.message : 'Unknown error');
      } finally {
        setLoading(false);
      }
    }

    load();

    return () => {
      controller.abort();
    };
  }, [activeViewConfig.url]);

  useEffect(() => {
    if (!graphData || !containerRef.current) return;

    const graph = loadGraphFromData(graphData);
    graphRef.current = graph;

    const renderer = new Sigma(graph, containerRef.current, {
      renderLabels: true,
      renderEdgeLabels: false,
      labelDensity: 0.07,
      labelGridCellSize: 80,
      labelRenderedSizeThreshold: 10,
      defaultNodeType: 'circle',
      defaultEdgeType: 'line',
      allowInvalidContainer: true,
      zIndex: true,
      minCameraRatio: 0.03,
      maxCameraRatio: 10,
    });

    renderer.on('clickNode', ({ node }) => {
      setSelectedEdgeId(null);
      setSelectedNodeId(node);
      centerOnNode(renderer, node);
    });

    renderer.on('clickEdge', ({ edge }) => {
      setSelectedNodeId(null);
      setSelectedEdgeId(edge);
    });

    renderer.on('clickStage', () => {
      setSelectedNodeId(null);
      setSelectedEdgeId(null);
    });

    renderer.on('enterNode', ({ node }) => setHoveredNodeId(node));
    renderer.on('leaveNode', () => setHoveredNodeId(null));

    rendererRef.current = renderer;

    return () => {
      renderer.kill();
      rendererRef.current = null;
      graphRef.current = null;
    };
  }, [graphData]);

  useEffect(() => {
    const graph = graphRef.current;
    const renderer = rendererRef.current;
    if (!graph || !renderer) return;

    if (selectedNodeId || hoveredNodeId) {
      highlightSelection(graph, selectedNodeId, hoveredNodeId);
    } else {
      resetStyles(graph);
    }

    renderer.refresh();
  }, [selectedNodeId, hoveredNodeId]);

  const nodes = useMemo(() => graphData?.nodes ?? [], [graphData]);
  const edges = useMemo(() => graphData?.edges ?? [], [graphData]);

  const filteredNodes = useMemo(() => {
    const query = search.trim().toLowerCase();
    if (!query) return nodes.slice(0, 20);

    return nodes
      .filter((node) => {
        const label = (node.label ?? '').toLowerCase();
        const id = String(node.id).toLowerCase();
        const type = String(node.type ?? '').toLowerCase();
        return label.includes(query) || id.includes(query) || type.includes(query);
      })
      .slice(0, 20);
  }, [nodes, search]);

  const selectedNode = selectedNodeId
    ? nodes.find((node) => node.id === selectedNodeId) ?? null
    : null;

  const selectedEdge = selectedEdgeId
    ? edges.find((edge) => (edge.id ?? `${edge.source}->${edge.target}`) === selectedEdgeId) ?? null
    : null;

  const nodeCrossLinks = selectedNode
    ? activeView === 'topic'
      ? selectedNode.linkedPapers ?? []
      : selectedNode.topicIds ?? []
    : [];

  function handleNodeJump(nodeId) {
    setSelectedEdgeId(null);
    setSelectedNodeId(nodeId);
    centerOnNode(rendererRef.current, nodeId);
  }

  return (
    <div className="app-shell">
      <header className="topbar">
        <div>
          <h1>Knowledge Graph Starter</h1>
          <p>{activeViewConfig.description}</p>
          <div className="view-switch" role="group" aria-label="Graph view switcher">
            {Object.entries(GRAPH_VIEWS).map(([viewKey, config]) => (
              <button
                key={viewKey}
                className={`view-button ${viewKey === activeView ? 'active' : ''}`}
                onClick={() => setActiveView(viewKey)}
                type="button"
              >
                {config.label}
              </button>
            ))}
          </div>
        </div>
        <div className="stats">
          <span>{activeViewConfig.label}</span>
          <span>{nodes.length.toLocaleString()} nodes</span>
          <span>{edges.length.toLocaleString()} edges</span>
        </div>
      </header>

      <main className="layout">
        <section className="graph-panel">
          {loading && <div className="status">Loading graph…</div>}
          {error && <div className="status error">{error}</div>}
          <div ref={containerRef} className="graph-container" />
        </section>

        <aside className="sidebar">
          <div className="card">
            <h2>Search nodes</h2>
            <input
              type="text"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Search by label, id, or type"
            />
            <div className="search-results">
              {filteredNodes.map((node) => (
                <button
                  key={node.id}
                  className="result-item"
                  onClick={() => handleNodeJump(node.id)}
                >
                  <strong>{node.label}</strong>
                  <span>{node.id}</span>
                </button>
              ))}
              {!filteredNodes.length && <p className="muted">No matching nodes.</p>}
            </div>
          </div>

          <div className="card">
            <h2>Selection</h2>
            {!selectedNode && !selectedEdge && (
              <p className="muted">Click a node or edge to inspect it.</p>
            )}

            {selectedNode && (
              <>
                <div className="selection-title">Node: {selectedNode.label}</div>
                <dl className="property-list">
                  <div><dt>ID</dt><dd>{selectedNode.id}</dd></div>
                  <div><dt>Type</dt><dd>{selectedNode.type ?? '—'}</dd></div>
                  <div><dt>Degree</dt><dd>{graphRef.current?.degree(selectedNode.id) ?? '—'}</dd></div>
                  <div><dt>Linked</dt><dd>{nodeCrossLinks.length ? nodeCrossLinks.join(', ') : '—'}</dd></div>
                  <div><dt>X</dt><dd>{Number(selectedNode.x).toFixed(3)}</dd></div>
                  <div><dt>Y</dt><dd>{Number(selectedNode.y).toFixed(3)}</dd></div>
                </dl>
                <details>
                  <summary>All node attributes</summary>
                  <pre>{JSON.stringify(selectedNode, null, 2)}</pre>
                </details>
              </>
            )}

            {selectedEdge && (
              <>
                <div className="selection-title">Edge: {selectedEdge.label || 'Untitled edge'}</div>
                <dl className="property-list">
                  <div><dt>ID</dt><dd>{selectedEdge.id ?? `${selectedEdge.source}->${selectedEdge.target}`}</dd></div>
                  <div><dt>Source</dt><dd>{selectedEdge.source}</dd></div>
                  <div><dt>Target</dt><dd>{selectedEdge.target}</dd></div>
                  <div><dt>Weight</dt><dd>{selectedEdge.weight ?? '—'}</dd></div>
                  <div><dt>Relation</dt><dd>{selectedEdge.relation ?? '—'}</dd></div>
                </dl>
                <details>
                  <summary>All edge attributes</summary>
                  <pre>{JSON.stringify(selectedEdge, null, 2)}</pre>
                </details>
              </>
            )}
          </div>

          <div className="card">
            <h2>How to swap in your graphs</h2>
            <ol>
              <li>Replace <code>public/data/topic-graph.json</code> and <code>public/data/citation-graph.json</code>.</li>
              <li>Keep shared paper IDs stable between graphs for loose coupling.</li>
              <li>Precompute x/y positions for each graph offline.</li>
              <li>Keep labels sparse at lower zoom levels for larger graphs.</li>
            </ol>
          </div>
        </aside>
      </main>
    </div>
  );
}

export default App;
