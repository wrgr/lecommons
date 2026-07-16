/**
 * Client-side force-directed knowledge graph for the Explore page: renders an
 * SVG of topic and lebokai-page nodes and re-lays-out ("reconfigures") whenever
 * a learner journey or competency is selected, so users can navigate a focused
 * subgraph and its associated resources.
 */

import {
  forceSimulation,
  forceLink,
  forceManyBody,
  forceCenter,
  forceCollide,
} from "d3-force";

const SVG_NS = "http://www.w3.org/2000/svg";
const WIDTH = 1200;
const HEIGHT = 820;
const LEBOK_CAP = 60; // max lebok page nodes shown per focused selection

interface TopicNode { id: string; label: string; layer: string; description: string }
interface LebokNode {
  id: string; label: string; topics: string[]; description: string;
  href: string; kaNumber: number | null; isKa: boolean;
}
interface TopicEdge { source: string; target: string; type: string }
interface ResourceItem { title: string; href: string; external: boolean; collection: string }
interface Selection {
  id: string; kind: "journey" | "competency"; label: string;
  description: string; pedagogy: string; theme?: string;
  topics: string[]; concepts: string[]; standards: string[];
}
interface ExploreData {
  topics: TopicNode[];
  lebok: LebokNode[];
  topicEdges: TopicEdge[];
  topicItems: Record<string, ResourceItem[]>;
  selections: Selection[];
  standards: Record<string, { name: string; url: string }>;
  wikiBase: string;
}

interface SimNode {
  id: string; kind: "topic" | "lebok"; label: string; layer: string;
  ref: TopicNode | LebokNode; x?: number; y?: number;
}
interface SimEdge { source: string | SimNode; target: string | SimNode; kind: string }

const LAYER_FILL: Record<string, string> = {
  Foundation: "#7a4e22", Practice: "#2c5f6f", Context: "#5a6b4a",
};

/** Escape user/content strings before injecting into innerHTML. */
function esc(v: string): string {
  return (v ?? "").replace(/&/g, "&amp;").replace(/</g, "&lt;")
    .replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#39;");
}

/** Nodes + edges to show for a selection (null = default topic overview). */
function visibleGraph(data: ExploreData, sel: Selection | null): { nodes: SimNode[]; edges: SimEdge[] } {
  const topicSet = sel ? new Set(sel.topics) : null;
  const topics = data.topics.filter((t) => !topicSet || topicSet.has(t.id));
  const topicIds = new Set(topics.map((t) => t.id));

  let lebok: LebokNode[];
  if (!topicSet) {
    lebok = data.lebok.filter((n) => n.isKa); // overview: KA landing pages only
  } else {
    lebok = data.lebok.filter((n) => n.topics.some((t) => topicSet.has(t)));
    // Prefer AI-tagged/described nodes, then stable alpha; cap to keep it legible.
    lebok = lebok
      .sort((a, b) => Number(Boolean(b.description)) - Number(Boolean(a.description)) || a.label.localeCompare(b.label))
      .slice(0, LEBOK_CAP);
  }

  const nodes: SimNode[] = [
    ...topics.map((t): SimNode => ({ id: t.id, kind: "topic", label: t.label, layer: t.layer, ref: t })),
    ...lebok.map((n): SimNode => ({ id: n.id, kind: "lebok", label: n.label, layer: "lebok", ref: n })),
  ];
  const nodeIds = new Set(nodes.map((n) => n.id));

  const edges: SimEdge[] = [];
  for (const e of data.topicEdges) {
    if (nodeIds.has(e.source) && nodeIds.has(e.target)) edges.push({ source: e.source, target: e.target, kind: e.type });
  }
  for (const n of lebok) {
    for (const t of n.topics) {
      if (topicIds.has(t)) edges.push({ source: n.id, target: t, kind: "COVERS" });
    }
  }
  return { nodes, edges };
}

/** Run the force simulation to assign x/y, then clamp to the viewBox. */
function layout(nodes: SimNode[], edges: SimEdge[]): void {
  const sim = forceSimulation(nodes as never[])
    .force("link", forceLink(edges as never[]).id((d: never) => (d as SimNode).id).distance(90).strength(0.25))
    .force("charge", forceManyBody().strength(-260))
    .force("center", forceCenter(WIDTH / 2, HEIGHT / 2))
    .force("collide", forceCollide().radius((d: never) => ((d as SimNode).kind === "topic" ? 34 : 20)))
    .stop();
  const ticks = Math.min(400, 120 + nodes.length * 2);
  for (let i = 0; i < ticks; i++) sim.tick();
  const pad = 60;
  for (const n of nodes) {
    n.x = Math.max(pad, Math.min(WIDTH - pad, n.x ?? WIDTH / 2));
    n.y = Math.max(pad, Math.min(HEIGHT - pad, n.y ?? HEIGHT / 2));
  }
}

/** Draw the current node/edge set into the SVG element. */
function render(svg: SVGSVGElement, nodes: SimNode[], edges: SimEdge[]): void {
  while (svg.firstChild) svg.removeChild(svg.firstChild);
  const byId = new Map(nodes.map((n) => [n.id, n]));

  const edgeLayer = document.createElementNS(SVG_NS, "g");
  for (const e of edges) {
    const s = byId.get(typeof e.source === "string" ? e.source : e.source.id);
    const t = byId.get(typeof e.target === "string" ? e.target : e.target.id);
    if (!s || !t) continue;
    const line = document.createElementNS(SVG_NS, "line");
    line.setAttribute("x1", String(s.x)); line.setAttribute("y1", String(s.y));
    line.setAttribute("x2", String(t.x)); line.setAttribute("y2", String(t.y));
    line.setAttribute("class", `ex-edge ex-edge--${e.kind.toLowerCase()}`);
    edgeLayer.appendChild(line);
  }
  svg.appendChild(edgeLayer);

  const nodeLayer = document.createElementNS(SVG_NS, "g");
  for (const n of nodes) {
    const g = document.createElementNS(SVG_NS, "g");
    g.setAttribute("class", `ex-node ex-node--${n.kind}`);
    g.setAttribute("data-id", n.id);
    g.setAttribute("tabindex", "0");
    g.setAttribute("role", "button");
    g.setAttribute("aria-label", `${n.kind === "topic" ? "Topic" : "Page"}: ${n.label}`);
    const r = n.kind === "topic" ? 18 : 9;
    const circle = document.createElementNS(SVG_NS, "circle");
    circle.setAttribute("cx", String(n.x)); circle.setAttribute("cy", String(n.y));
    circle.setAttribute("r", String(r));
    circle.setAttribute("fill", n.kind === "topic" ? (LAYER_FILL[n.layer] ?? "#555") : "#c98a3a");
    g.appendChild(circle);
    const label = document.createElementNS(SVG_NS, "text");
    label.setAttribute("x", String(n.x)); label.setAttribute("y", String((n.y ?? 0) + r + 12));
    label.setAttribute("text-anchor", "middle");
    label.setAttribute("class", `ex-label ex-label--${n.kind}`);
    const max = n.kind === "topic" ? 26 : 30;
    label.textContent = n.label.length > max ? n.label.slice(0, max - 1) + "…" : n.label;
    g.appendChild(label);
    nodeLayer.appendChild(g);
  }
  svg.appendChild(nodeLayer);
}

/** Build the detail-panel HTML for a clicked node. */
function nodeDetailHtml(data: ExploreData, node: SimNode): string {
  if (node.kind === "topic") {
    const ref = node.ref as TopicNode;
    const items = (data.topicItems[node.id] ?? []).slice(0, 12);
    const list = items.map((i) => {
      const tgt = i.external ? ' target="_blank" rel="noopener"' : "";
      return `<li><a href="${esc(i.href)}"${tgt}>${esc(i.title)}</a> <span class="ex-meta">${esc(i.collection)}</span></li>`;
    }).join("");
    return `<span class="ex-chip">Topic ${esc(node.id)}</span>` +
      `<h3>${esc(ref.label)}</h3><p>${esc(ref.description)}</p>` +
      (list ? `<h4>Associated resources</h4><ul class="ex-list">${list}</ul>` : "<p class='ex-muted'>No resources tagged yet.</p>");
  }
  const ref = node.ref as LebokNode;
  const url = data.wikiBase + ref.href;
  const desc = ref.description ? `<p>${esc(ref.description)}</p>` : "<p class='ex-muted'>No description yet (pending review).</p>";
  return `<span class="ex-chip ex-chip--lebok">LEBOK${ref.kaNumber ? " · KA" + ref.kaNumber : ""}</span>` +
    `<h3>${esc(ref.label)}</h3>${desc}` +
    `<p><a href="${esc(url)}" target="_blank" rel="noopener">Open in LEBOK wiki →</a></p>` +
    `<p class="ex-meta">Topics: ${ref.topics.map(esc).join(", ") || "—"}</p>`;
}

/** Selection summary panel: pedagogy grounding + documented resources. */
function selectionDetailHtml(data: ExploreData, sel: Selection): string {
  const items: ResourceItem[] = [];
  const seen = new Set<string>();
  for (const t of sel.topics) {
    for (const i of data.topicItems[t] ?? []) {
      if (seen.has(i.href)) continue;
      seen.add(i.href); items.push(i);
    }
  }
  const resList = items.slice(0, 12).map((i) => {
    const tgt = i.external ? ' target="_blank" rel="noopener"' : "";
    return `<li><a href="${esc(i.href)}"${tgt}>${esc(i.title)}</a> <span class="ex-meta">${esc(i.collection)}</span></li>`;
  }).join("");
  const standards = sel.standards.map((id) => data.standards[id]).filter(Boolean)
    .map((s) => `<li><a href="${esc(s.url)}" target="_blank" rel="noopener">${esc(s.name)}</a></li>`).join("");
  const kind = sel.kind === "journey" ? "Journey" : "Competency";
  return `<span class="ex-chip ex-chip--sel">${kind}</span><h3>${esc(sel.label)}</h3>` +
    `<p>${esc(sel.description)}</p>` +
    `<h4>Pedagogical grounding</h4><p class="ex-ped">${esc(sel.pedagogy)}</p>` +
    (standards ? `<h4>Standards</h4><ul class="ex-list">${standards}</ul>` : "") +
    (resList ? `<h4>Documented resources</h4><ul class="ex-list">${resList}</ul>` : "");
}

/** Wire up hover highlight + click-to-detail on the current SVG nodes. */
function attachNodeHandlers(svg: SVGSVGElement, nodes: SimNode[], onDetail: (n: SimNode) => void): void {
  const byId = new Map(nodes.map((n) => [n.id, n]));
  for (const el of Array.from(svg.querySelectorAll<SVGGElement>(".ex-node"))) {
    const node = byId.get(el.getAttribute("data-id") ?? "");
    if (!node) continue;
    el.addEventListener("click", () => onDetail(node));
    el.addEventListener("keydown", (e) => {
      if (e.key === "Enter" || e.key === " ") { e.preventDefault(); onDetail(node); }
    });
  }
}

/** Entry point: render the default graph and wire the selection controls. */
export function initExploreGraph(): void {
  const dataEl = document.getElementById("explore-data");
  const svg = document.getElementById("explore-svg") as SVGSVGElement | null;
  const detail = document.getElementById("explore-detail");
  const controls = document.getElementById("explore-controls");
  if (!dataEl || !svg || !detail || !controls) return;
  const data: ExploreData = JSON.parse(dataEl.textContent ?? "{}");

  let current: Selection | null = null;

  function draw(): void {
    const { nodes, edges } = visibleGraph(data, current);
    layout(nodes, edges);
    render(svg!, nodes, edges);
    attachNodeHandlers(svg!, nodes, (n) => { detail!.innerHTML = nodeDetailHtml(data, n); });
    if (current) detail!.innerHTML = selectionDetailHtml(data, current);
    else detail!.innerHTML = "<p class='ex-muted'>Select a journey or competency to focus the graph, or click any node for detail.</p>";
    const total = current ? data.lebok.filter((n) => n.topics.some((t) => current!.topics.includes(t))).length : 0;
    const cap = document.getElementById("explore-cap");
    if (cap) cap.textContent = current && total > LEBOK_CAP ? `Showing ${LEBOK_CAP} of ${total} matching LEBOK pages.` : "";
  }

  controls.addEventListener("click", (e) => {
    const btn = (e.target as HTMLElement).closest<HTMLButtonElement>("[data-sel]");
    if (!btn) return;
    const id = btn.getAttribute("data-sel");
    current = id === "__all__" ? null : (data.selections.find((s) => s.id === id) ?? null);
    for (const b of Array.from(controls.querySelectorAll("[data-sel]"))) b.classList.toggle("active", b === btn);
    draw();
  });

  draw();
}
