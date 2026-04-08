import { NODE_COLORS } from "../constants.js";
import { d3, html, useEffect, useRef } from "../lib.js";
import { shortLabel } from "../text.js";
import { clamp } from "../utils.js";

export function GraphCanvas({ nodes, links, selectedNodeId, onSelect }) {
  const svgRef = useRef(null);

  useEffect(() => {
    if (!svgRef.current) return undefined;

    const width = 1200;
    const height = 700;

    const svg = d3.select(svgRef.current);
    svg.selectAll("*").remove();

    const simulationNodes = nodes.map((node) => ({ ...node }));
    const simulationLinks = links.map((edge) => ({ ...edge }));

    const linkSelection = svg
      .append("g")
      .attr("stroke", "#94a3b8")
      .attr("stroke-opacity", 0.44)
      .selectAll("line")
      .data(simulationLinks)
      .join("line")
      .attr("stroke-width", (edge) => (edge.type === "contains" ? 1 : 1.45));

    const nodeSelection = svg
      .append("g")
      .attr("stroke", "#fff")
      .selectAll("circle")
      .data(simulationNodes)
      .join("circle")
      .attr("r", (node) => {
        if (node.type === "topic_part") return 8.3;
        if (node.type === "topic_surface") return 7.2;
        if (node.type === "topic") return 6.3;
        if (node.type === "paper" && node.hop === 0) return 5;
        if (node.type === "paper" && node.hop === 1) return 3.7;
        return 4.2;
      })
      .attr("fill", (node) => {
        if (node.type === "topic_part") return NODE_COLORS.topic_part;
        if (node.type === "topic_surface") return NODE_COLORS.topic_surface;
        if (node.type === "topic") return NODE_COLORS.topic;
        if (node.type === "paper" && node.hop === 0) return NODE_COLORS.paper_seed;
        if (node.type === "paper" && node.hop === 1) return NODE_COLORS.paper_hop;
        return NODE_COLORS.unknown;
      })
      .attr("stroke-width", (node) => (node.id === selectedNodeId ? 2.6 : 1.4))
      .attr("stroke", (node) => (node.id === selectedNodeId ? "#f97316" : "#ffffff"))
      .attr("opacity", (node) => (selectedNodeId && node.id !== selectedNodeId ? 0.76 : 1))
      .on("click", (_event, node) => onSelect(node.id));

    nodeSelection.append("title").text((node) => node.label);

    const labelSelection = svg
      .append("g")
      .selectAll("text")
      .data(simulationNodes.filter((node) => node.type !== "paper" || node.hop === 0))
      .join("text")
      .attr("font-size", 10)
      .attr("fill", "#0f172a")
      .attr("paint-order", "stroke")
      .attr("stroke", "rgba(255,255,255,0.82)")
      .attr("stroke-width", 2)
      .text((node) => shortLabel(node.label, 44));

    const simulation = d3
      .forceSimulation(simulationNodes)
      .force(
        "link",
        d3
          .forceLink(simulationLinks)
          .id((node) => node.id)
          .distance((edge) => (edge.type === "contains" ? 92 : 54))
      )
      .force("charge", d3.forceManyBody().strength((node) => (node.type === "paper" ? -44 : -196)))
      .force("center", d3.forceCenter(width / 2, height / 2))
      .force("collision", d3.forceCollide().radius((node) => {
        if (node.type === "paper" && node.hop === 1) return 7;
        return 10;
      }))
      .on("tick", () => {
        linkSelection
          .attr("x1", (edge) => edge.source.x)
          .attr("y1", (edge) => edge.source.y)
          .attr("x2", (edge) => edge.target.x)
          .attr("y2", (edge) => edge.target.y);

        nodeSelection
          .attr("cx", (node) => clamp(node.x, 10, width - 10))
          .attr("cy", (node) => clamp(node.y, 10, height - 10));

        labelSelection.attr("x", (node) => node.x + 9).attr("y", (node) => node.y + 4);
      });

    const drag = d3
      .drag()
      .on("start", (event) => {
        if (!event.active) simulation.alphaTarget(0.3).restart();
        event.subject.fx = event.subject.x;
        event.subject.fy = event.subject.y;
      })
      .on("drag", (event) => {
        event.subject.fx = event.x;
        event.subject.fy = event.y;
      })
      .on("end", (event) => {
        if (!event.active) simulation.alphaTarget(0);
        event.subject.fx = null;
        event.subject.fy = null;
      });

    nodeSelection.call(drag);

    return () => {
      simulation.stop();
    };
  }, [nodes, links, onSelect, selectedNodeId]);

  return html`<svg
    className="graph-canvas"
    ref=${svgRef}
    viewBox="0 0 1200 700"
    role="img"
    aria-label="Learning engineering topic and citation graph"
  ></svg>`;
}
