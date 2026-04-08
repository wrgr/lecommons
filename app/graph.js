export function computeVisibleGraph(graph, includeHop) {
  const nodes = (graph.nodes || []).filter((node) => includeHop || node.hop === 0).map((node) => ({ ...node }));
  const visibleIds = new Set(nodes.map((node) => node.id));
  const links = (graph.edges || [])
    .filter((edge) => visibleIds.has(edge.source) && visibleIds.has(edge.target))
    .map((edge) => ({ ...edge }));

  return { nodes, links };
}

export function buildNodeIndex(visibleGraph) {
  const nodeMap = new Map((visibleGraph.nodes || []).map((node) => [node.id, node]));
  const incoming = new Map();
  const outgoing = new Map();

  for (const edge of visibleGraph.links || []) {
    const sourceList = outgoing.get(edge.source) || [];
    sourceList.push(edge);
    outgoing.set(edge.source, sourceList);

    const targetList = incoming.get(edge.target) || [];
    targetList.push(edge);
    incoming.set(edge.target, targetList);
  }

  return { nodeMap, incoming, outgoing };
}
