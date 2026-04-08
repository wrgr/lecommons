import Graph from 'graphology';

const DEFAULT_NODE_COLOR = '#4f46e5';
const DEFAULT_EDGE_COLOR = '#cbd5e1';
const HIGHLIGHT_NODE_COLOR = '#dc2626';
const HIGHLIGHT_EDGE_COLOR = '#0f172a';
const DIM_NODE_COLOR = '#d1d5db';
const DIM_EDGE_COLOR = '#e5e7eb';

export function loadGraphFromData(data) {
  const graph = new Graph({ multi: false, allowSelfLoops: false });

  for (const node of data.nodes) {
    const { type: semanticType, ...nodeAttrs } = node;
    graph.addNode(node.id, {
      label: node.label,
      x: node.x,
      y: node.y,
      size: node.size ?? 6,
      color: node.color ?? DEFAULT_NODE_COLOR,
      originalColor: node.color ?? DEFAULT_NODE_COLOR,
      semanticType: semanticType ?? null,
      ...nodeAttrs,
      type: 'circle',
    });
  }

  for (const edge of data.edges) {
    const { type: semanticType, ...edgeAttrs } = edge;
    const edgeKey = edge.id ?? `${edge.source}->${edge.target}`;
    graph.addEdgeWithKey(edgeKey, edge.source, edge.target, {
      size: edge.size ?? 1,
      color: edge.color ?? DEFAULT_EDGE_COLOR,
      originalColor: edge.color ?? DEFAULT_EDGE_COLOR,
      label: edge.label ?? '',
      semanticType: semanticType ?? null,
      ...edgeAttrs,
      type: 'line',
    });
  }

  return graph;
}

export function resetStyles(graph) {
  graph.forEachNode((node, attrs) => {
    graph.setNodeAttribute(node, 'color', attrs.originalColor ?? DEFAULT_NODE_COLOR);
    graph.setNodeAttribute(node, 'hidden', false);
  });

  graph.forEachEdge((edge, attrs) => {
    graph.setEdgeAttribute(edge, 'color', attrs.originalColor ?? DEFAULT_EDGE_COLOR);
    graph.setEdgeAttribute(edge, 'hidden', false);
  });
}

export function highlightSelection(graph, selectedNodeId, hoveredNodeId = null) {
  resetStyles(graph);

  const activeNodeId = selectedNodeId ?? hoveredNodeId;
  if (!activeNodeId || !graph.hasNode(activeNodeId)) return;

  const neighbors = new Set(graph.neighbors(activeNodeId));
  neighbors.add(activeNodeId);

  graph.forEachNode((node, attrs) => {
    if (neighbors.has(node)) {
      graph.setNodeAttribute(
        node,
        'color',
        node === activeNodeId ? HIGHLIGHT_NODE_COLOR : attrs.originalColor ?? DEFAULT_NODE_COLOR,
      );
    } else {
      graph.setNodeAttribute(node, 'color', DIM_NODE_COLOR);
    }
  });

  graph.forEachEdge((edge, attrs, source, target) => {
    if (source === activeNodeId || target === activeNodeId) {
      graph.setEdgeAttribute(edge, 'color', HIGHLIGHT_EDGE_COLOR);
    } else {
      graph.setEdgeAttribute(edge, 'color', DIM_EDGE_COLOR);
    }
  });
}

export function centerOnNode(renderer, nodeId) {
  if (!renderer || !nodeId) return;
  const sigmaGraph = renderer.getGraph();
  if (!sigmaGraph.hasNode(nodeId)) return;

  const x = sigmaGraph.getNodeAttribute(nodeId, 'x');
  const y = sigmaGraph.getNodeAttribute(nodeId, 'y');
  const camera = renderer.getCamera();

  camera.animate(
    { x, y, ratio: 0.35 },
    { duration: 500 }
  );
}
