/**
 * List view of every node in the visible graph: same filters as the canvas, grouped by type
 * like Resource Navigator (search + pills, collapsible sections).
 */
import { html, useMemo, useState } from "../lib.js";
import { browseGroupKey, buildNeighborIndex, matchesGraphNodeFilters } from "../graph.js";
import { shortLabel } from "../text.js";

const GROUP_META = [
  { key: "topic", label: "Topics" },
  { key: "concept", label: "Concepts" },
  { key: "paper", label: "Papers" },
  { key: "resource", label: "Resources" },
  { key: "other", label: "Other" },
];

const INITIAL_VISIBLE = 24;

function sortNodesInGroup(a, b) {
  if (a.type === "paper" && b.type === "paper" && Number(a.hop) !== Number(b.hop)) {
    return Number(a.hop) - Number(b.hop);
  }
  return (a.label || "").localeCompare(b.label || "", undefined, { sensitivity: "base" });
}

export function GraphNodeBrowsePanel({
  visibleGraph,
  search,
  typeFilter,
  selectedNodeId,
  setSelectedNodeId,
}) {
  const neighborIndex = useMemo(() => buildNeighborIndex(visibleGraph.links), [visibleGraph.links]);

  const groupedNodes = useMemo(() => {
    const filtered = (visibleGraph.nodes || []).filter((node) =>
      matchesGraphNodeFilters(node, search, typeFilter, neighborIndex, selectedNodeId)
    );
    const map = new Map(GROUP_META.map(({ key }) => [key, []]));
    for (const node of filtered) {
      const g = browseGroupKey(node);
      if (!map.has(g)) map.set(g, []);
      map.get(g).push(node);
    }
    for (const [, arr] of map) {
      arr.sort(sortNodesInGroup);
    }
    return map;
  }, [visibleGraph.nodes, search, typeFilter, neighborIndex, selectedNodeId]);

  const totalListed = useMemo(() => {
    let n = 0;
    for (const [, arr] of groupedNodes) n += arr.length;
    return n;
  }, [groupedNodes]);

  return html`
    <div className="graph-browse">
      <p className="caption graph-browse-intro">
        ${totalListed === 0
          ? "No nodes match — clear the search, set type to All, or adjust filters."
          : `${totalListed} node${totalListed !== 1 ? "s" : ""} match the current search and filters — same set as the graph above. Click a row to select it.`}
      </p>
      ${GROUP_META.filter(({ key }) => (groupedNodes.get(key) || []).length > 0).map(({ key, label }) => {
        const nodes = groupedNodes.get(key) || [];
        return html`<${GraphBrowseGroup}
          key=${key}
          groupKey=${key}
          label=${label}
          nodes=${nodes}
          selectedNodeId=${selectedNodeId}
          setSelectedNodeId=${setSelectedNodeId}
        />`;
      })}
    </div>
  `;
}

function GraphBrowseGroup({ groupKey, label, nodes, selectedNodeId, setSelectedNodeId }) {
  const [expanded, setExpanded] = useState(false);
  const visible = expanded ? nodes : nodes.slice(0, INITIAL_VISIBLE);
  const overflow = nodes.length - INITIAL_VISIBLE;

  return html`
    <div className="resource-type-section graph-browse-section">
      <h3 className="resource-type-head">
        ${label}
        <span className="count-pill">${nodes.length}</span>
      </h3>
      <ul className="flat-list compact graph-browse-list">
        ${visible.map(
          (node) => html`
            <li key=${`${groupKey}:${node.id}`}>
              <button
                type="button"
                className=${"graph-browse-row" + (node.id === selectedNodeId ? " is-selected" : "")}
                onClick=${() => setSelectedNodeId(node.id)}
              >
                <span className="graph-browse-label">${shortLabel(node.label, 96)}</span>
                ${node.type === "paper"
                  ? html`<span className="graph-browse-meta">hop ${node.hop ?? 0}</span>`
                  : ""}
                <span className="graph-browse-id">${node.id}</span>
              </button>
            </li>
          `
        )}
      </ul>
      ${!expanded && overflow > 0
        ? html`<button type="button" className="ghost-btn" onClick=${() => setExpanded(true)}>
            Show ${overflow} more
          </button>`
        : ""}
    </div>
  `;
}
