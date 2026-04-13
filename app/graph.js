/** Normalizes D3 or raw link endpoints to string ids. */
function edgeEndpointId(edge, which) {
  const v = edge[which];
  if (v == null) return "";
  if (typeof v === "object" && v.id != null) return String(v.id);
  return String(v);
}

/** Undirected adjacency for neighbor highlighting and list filtering. */
export function buildNeighborIndex(links) {
  const neighborSet = new Map();
  for (const edge of links || []) {
    const src = edgeEndpointId(edge, "source");
    const tgt = edgeEndpointId(edge, "target");
    if (!src || !tgt) continue;
    if (!neighborSet.has(src)) neighborSet.set(src, new Set());
    if (!neighborSet.has(tgt)) neighborSet.set(tgt, new Set());
    neighborSet.get(src).add(tgt);
    neighborSet.get(tgt).add(src);
  }
  return neighborSet;
}

/**
 * Same rules as the graph canvas: search on label/id, type pill, or neighbor focus.
 * @param {string} [focusId]  Selected node id for "Neighbors" filter (no hover in list mode).
 */
export function matchesGraphNodeFilters(node, query, typeFilter, neighborIndex, focusId) {
  const q = (query || "").toLowerCase().trim();
  const searchOk = !q || `${node.label || ""} ${node.id || ""}`.toLowerCase().includes(q);
  if (!searchOk) return false;
  if (typeFilter === "all" || !typeFilter) return true;
  if (typeFilter === "neighbors") {
    if (!focusId) return true;
    const focusNeighbors = neighborIndex.get(focusId) ?? new Set();
    return node.id === focusId || focusNeighbors.has(node.id);
  }
  return node.type === typeFilter;
}

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

/** Maps legacy or uncommon node types into browse group keys. */
export function browseGroupKey(node) {
  const t = node.type || "unknown";
  if (t === "topic_part" || t === "topic_surface") return "topic";
  if (t === "topic" || t === "concept" || t === "paper" || t === "resource") return t;
  return "other";
}
