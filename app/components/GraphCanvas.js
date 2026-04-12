/**
 * Force-directed graph canvas with zoom/pan, hover highlighting, search, and
 * node-type filtering. Splits layout (physics simulation) from visual updates
 * so selecting a node or changing filters never restarts the simulation.
 */
import { NODE_COLORS } from "../constants.js";
import { d3, html, useEffect, useRef } from "../lib.js";
import { shortLabel } from "../text.js";
import { clamp } from "../utils.js";

const GRAPH_HEIGHT = 680;

/** Returns the display radius for a node based on its type. */
function getNodeRadius(node) {
  if (node.type === "topic") return 8;
  if (node.type === "concept") return 6.5;
  if (node.type === "resource") return 4.7;
  if (node.type === "paper" && node.hop === 0) return 5.2;
  if (node.type === "paper" && node.hop === 1) return 3.7;
  // Legacy node type support
  if (node.type === "topic_part") return 8.3;
  if (node.type === "topic_surface") return 7.2;
  return 4.2;
}

/** Returns the base fill color for a node. */
function getNodeColor(node) {
  if (node.type === "topic") return NODE_COLORS.topic;
  if (node.type === "concept") return NODE_COLORS.concept;
  if (node.type === "resource") return NODE_COLORS.resource;
  if (node.type === "paper" && node.hop === 0) return NODE_COLORS.paper_seed;
  if (node.type === "paper" && node.hop === 1) return NODE_COLORS.paper_hop;
  if (node.type === "topic_part") return NODE_COLORS.topic_part;
  if (node.type === "topic_surface") return NODE_COLORS.topic_surface;
  return NODE_COLORS.unknown;
}

/**
 * @param {{ nodes: object[], links: object[], selectedNodeId: string,
 *   onSelect: (id: string) => void, search: string, typeFilter: string,
 *   resetRef: React.MutableRefObject }} props
 */
export function GraphCanvas({ nodes, links, selectedNodeId, onSelect, search, typeFilter, resetRef }) {
  const svgRef = useRef(null);
  const selectionsRef = useRef(null);
  const applyRef = useRef(null);
  const hoveredIdRef = useRef("");

  // Stable refs so Phase-1 closures always read current prop values without
  // being listed as effect dependencies (which would restart the simulation).
  const selectedIdRef = useRef(selectedNodeId);
  const searchRef = useRef(search || "");
  const filterRef = useRef(typeFilter || "all");
  const onSelectRef = useRef(onSelect);

  selectedIdRef.current = selectedNodeId;
  searchRef.current = search || "";
  filterRef.current = typeFilter || "all";
  onSelectRef.current = onSelect;

  // ── Phase 1: layout ──────────────────────────────────────────────────────
  // Builds the force simulation and wires up zoom/drag/hover events.
  // Only reruns when the graph topology (nodes or links) changes.
  useEffect(() => {
    if (!svgRef.current || !nodes.length) return undefined;

    const svgEl = svgRef.current;
    const width = svgEl.getBoundingClientRect().width || 1100;

    const svg = d3.select(svgEl);
    svg.selectAll("*").remove();

    const zoomGroup = svg.append("g").attr("class", "zoom-root");

    const simNodes = nodes.map((n) => ({ ...n }));
    const simLinks = links.map((e) => ({ ...e }));

    // Build adjacency index before D3 replaces source/target strings with objects.
    const neighborSet = new Map(simNodes.map((n) => [n.id, new Set()]));
    for (const edge of simLinks) {
      const src = String(edge.source);
      const tgt = String(edge.target);
      if (neighborSet.has(src)) neighborSet.get(src).add(tgt);
      if (neighborSet.has(tgt)) neighborSet.get(tgt).add(src);
    }

    const linkSelection = zoomGroup
      .append("g")
      .attr("class", "links")
      .selectAll("line")
      .data(simLinks)
      .join("line")
      .attr("stroke-width", (e) =>
        e.type === "contains" ? 1 : e.type === "resource" ? 0.9 : 1.45
      );

    const nodeSelection = zoomGroup
      .append("g")
      .attr("class", "nodes")
      .selectAll("circle")
      .data(simNodes)
      .join("circle")
      .attr("r", getNodeRadius)
      .attr("stroke", "#fff")
      .attr("stroke-width", 1.4)
      .attr("cursor", "pointer")
      .on("click", (_evt, node) => onSelectRef.current(node.id))
      .on("mouseenter", (_evt, node) => {
        hoveredIdRef.current = node.id;
        applyRef.current?.();
      })
      .on("mouseleave", () => {
        hoveredIdRef.current = "";
        applyRef.current?.();
      });

    nodeSelection.append("title").text((n) => n.label);

    // Labels only for non-hop-1 papers to reduce clutter.
    const labelSelection = zoomGroup
      .append("g")
      .attr("class", "labels")
      .selectAll("text")
      .data(simNodes.filter((n) => n.type !== "paper" || n.hop === 0))
      .join("text")
      .attr("font-size", 10)
      .attr("fill", "#0f172a")
      .attr("paint-order", "stroke")
      .attr("stroke", "rgba(255,255,255,0.82)")
      .attr("stroke-width", 2)
      .attr("pointer-events", "none")
      .text((n) => shortLabel(n.label, 44));

    const simulation = d3
      .forceSimulation(simNodes)
      .force(
        "link",
        d3
          .forceLink(simLinks)
          .id((n) => n.id)
          .distance((e) =>
            e.type === "contains" ? 92 : e.type === "resource" ? 84 : 54
          )
      )
      .force(
        "charge",
        d3.forceManyBody().strength((n) => (n.type === "paper" ? -44 : -196))
      )
      .force("center", d3.forceCenter(width / 2, GRAPH_HEIGHT / 2))
      .force(
        "collision",
        d3.forceCollide().radius((n) => (n.type === "paper" && n.hop === 1 ? 7 : 10))
      )
      .on("tick", () => {
        linkSelection
          .attr("x1", (e) => e.source.x)
          .attr("y1", (e) => e.source.y)
          .attr("x2", (e) => e.target.x)
          .attr("y2", (e) => e.target.y);

        nodeSelection
          .attr("cx", (n) => clamp(n.x, 10, width - 10))
          .attr("cy", (n) => clamp(n.y, 10, GRAPH_HEIGHT - 10));

        labelSelection
          .attr("x", (n) => n.x + 9)
          .attr("y", (n) => n.y + 4);
      });

    const drag = d3
      .drag()
      .on("start", (evt) => {
        if (!evt.active) simulation.alphaTarget(0.3).restart();
        evt.subject.fx = evt.subject.x;
        evt.subject.fy = evt.subject.y;
      })
      .on("drag", (evt) => {
        evt.subject.fx = evt.x;
        evt.subject.fy = evt.y;
      })
      .on("end", (evt) => {
        if (!evt.active) simulation.alphaTarget(0);
        evt.subject.fx = null;
        evt.subject.fy = null;
      });
    nodeSelection.call(drag);

    const zoom = d3
      .zoom()
      .scaleExtent([0.08, 5])
      .on("zoom", (evt) => zoomGroup.attr("transform", evt.transform));
    svg.call(zoom).on("dblclick.zoom", null);

    if (resetRef) {
      resetRef.current = () =>
        svg.transition().duration(400).call(zoom.transform, d3.zoomIdentity);
    }

    selectionsRef.current = { linkSelection, nodeSelection, labelSelection, neighborSet };

    // ── applyVisualState ────────────────────────────────────────────────────
    // Reads all current state from refs so it never goes stale between calls.
    function applyVisualState() {
      const sel = selectionsRef.current;
      if (!sel) return;

      const selId = selectedIdRef.current;
      const hovId = hoveredIdRef.current;
      const query = searchRef.current.toLowerCase().trim();
      const filter = filterRef.current;

      const focusId = selId || hovId;
      const focusNeighbors = focusId
        ? (sel.neighborSet.get(focusId) ?? new Set())
        : new Set();

      function isVisible(node) {
        const searchOk =
          !query || `${node.label} ${node.id}`.toLowerCase().includes(query);
        if (!searchOk) return false;
        if (filter === "all") return true;
        if (filter === "neighbors") {
          if (!focusId) return true;
          return node.id === focusId || focusNeighbors.has(node.id);
        }
        return node.type === filter;
      }

      sel.nodeSelection
        .attr("fill", (n) => {
          if (!isVisible(n)) return "#e2e8f0";
          if (focusId && n.id !== focusId && !focusNeighbors.has(n.id))
            return "#cbd5e1";
          return getNodeColor(n);
        })
        .attr("stroke", (n) =>
          n.id === selId || n.id === hovId ? "#f97316" : "#ffffff"
        )
        .attr("stroke-width", (n) =>
          n.id === selId || n.id === hovId ? 2.6 : 1.4
        )
        .attr("opacity", (n) => {
          if (!isVisible(n)) return 0.18;
          if (focusId && n.id !== focusId && !focusNeighbors.has(n.id))
            return 0.3;
          return 1;
        });

      sel.linkSelection
        .attr("stroke", (e) => {
          const src = e.source.id ?? e.source;
          const tgt = e.target.id ?? e.target;
          if (focusId) {
            if (src === focusId) return "#ea580c";
            if (tgt === focusId) return "#0f766e";
            return "#cbd5e1";
          }
          if (e.type === "resource") return "#0f766e";
          if (e.type === "expands_to") return "#ca8a04";
          if (e.type === "prereq") return "#0f766e";
          return "#94a3b8";
        })
        .attr("stroke-opacity", (e) => {
          const src = e.source.id ?? e.source;
          const tgt = e.target.id ?? e.target;
          if (focusId) {
            return src === focusId || tgt === focusId ? 0.85 : 0.08;
          }
          return 0.5;
        });

      sel.labelSelection.attr("opacity", (n) => {
        if (!isVisible(n)) return 0;
        if (focusId && n.id !== focusId && !focusNeighbors.has(n.id)) return 0.3;
        return 1;
      });
    }

    applyRef.current = applyVisualState;
    applyVisualState();

    return () => {
      simulation.stop();
      selectionsRef.current = null;
      applyRef.current = null;
      if (resetRef) resetRef.current = null;
    };
  }, [nodes, links]); // eslint-disable-line react-hooks/exhaustive-deps

  // ── Phase 2: visual updates ───────────────────────────────────────────────
  // Applies color/opacity changes without touching the simulation.
  useEffect(() => {
    applyRef.current?.();
  }, [selectedNodeId, search, typeFilter]);

  return html`<svg
    className="graph-canvas"
    ref=${svgRef}
    height=${GRAPH_HEIGHT}
    role="img"
    aria-label="Learning engineering topic and citation graph"
  ></svg>`;
}
