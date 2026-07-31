/**
 * Client-side interactivity for the build-time Topic Map (graph.astro): hover
 * highlighting, the node detail panel, topic-control buttons, and in-panel
 * prerequisite/concept navigation. Extracted from graph.astro to keep that page
 * under the repo's file-length limit and to mirror the focusGraph.ts pattern.
 */

interface EnrichmentItem {
  external?: boolean;
  href?: string;
  title?: string;
  collection?: string;
}
interface Enrichment {
  type: "topic" | "concept";
  name?: string;
  description?: string;
  url?: string;
  contentCount?: number;
  siteItems?: EnrichmentItem[];
  children?: { id: string; name: string; bloom: string }[];
  bloom?: string;
  prereqChain?: { id: string; name: string }[];
  papers?: any[];
  resources?: { id: string; name: string; url: string }[];
}

/** True only for absolute http(s) URLs — used to avoid emitting broken links. */
function isHttpUrl(u: unknown): u is string {
  return typeof u === "string" && /^https?:\/\//.test(u);
}

/** Escape a string for safe injection into innerHTML. */
function escapeHtml(value: string): string {
  return (value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

/** Wire up the Topic Map SVG: hover highlight, detail panel, and controls. */
export function initTopicMap(): void {
  const svg = document.getElementById("graph-svg");
  const panel = document.getElementById("detail-panel");
  const dataEl = document.getElementById("enrichment-data");
  if (!svg || !panel || !dataEl) return;
  const enrichment: Record<string, Enrichment> = JSON.parse(dataEl.textContent ?? "{}");

  const allNodes = svg.querySelectorAll(".node");
  const allEdges = svg.querySelectorAll(".edge");

  // Adjacency index for hover highlighting.
  const neighbors = new Map<string, Set<string>>();
  const nodeEdges = new Map<string, Set<Element>>();

  for (const edge of allEdges) {
    const src = edge.getAttribute("data-source")!;
    const tgt = edge.getAttribute("data-target")!;
    for (const id of [src, tgt]) {
      if (!neighbors.has(id)) neighbors.set(id, new Set());
      if (!nodeEdges.has(id)) nodeEdges.set(id, new Set());
    }
    neighbors.get(src)!.add(tgt);
    neighbors.get(tgt)!.add(src);
    nodeEdges.get(src)!.add(edge);
    nodeEdges.get(tgt)!.add(edge);
  }

  function clearHighlight(): void {
    for (const n of allNodes) n.classList.remove("dimmed", "highlighted");
    for (const e of allEdges) {
      e.classList.remove("dimmed", "highlighted");
      if (e.getAttribute("marker-end")) e.setAttribute("marker-end", "url(#arrow)");
    }
  }

  function highlightNode(id: string): void {
    const nbrs = neighbors.get(id) ?? new Set<string>();
    const myEdges = nodeEdges.get(id) ?? new Set<Element>();
    for (const n of allNodes) {
      const nid = n.getAttribute("data-id")!;
      n.classList.toggle("highlighted", nid === id || nbrs.has(nid));
      n.classList.toggle("dimmed", nid !== id && !nbrs.has(nid));
    }
    for (const e of allEdges) {
      e.classList.toggle("highlighted", myEdges.has(e));
      e.classList.toggle("dimmed", !myEdges.has(e));
      if (myEdges.has(e) && e.getAttribute("marker-end")) {
        e.setAttribute("marker-end", "url(#arrow-hl)");
      }
    }
  }

  for (const node of allNodes) {
    node.addEventListener("mouseenter", () => highlightNode(node.getAttribute("data-id")!));
    node.addEventListener("mouseleave", clearHighlight);
  }

  // Detail-panel element references.
  const chipEl = document.getElementById("detail-chip")!;
  const bloomEl = document.getElementById("detail-bloom")!;
  const titleEl = document.getElementById("detail-title")!;
  const descEl = document.getElementById("detail-description")!;
  const openEl = document.getElementById("detail-open") as HTMLAnchorElement | null;
  const prereqsSection = document.getElementById("detail-prereqs")!;
  const prereqChainEl = document.getElementById("detail-prereq-chain")!;
  const childrenSection = document.getElementById("detail-children")!;
  const childrenList = document.getElementById("detail-children-list")!;
  const itemsSection = document.getElementById("detail-items")!;
  const itemsList = document.getElementById("detail-items-list")!;
  const papersSection = document.getElementById("detail-papers")!;
  const papersList = document.getElementById("detail-papers-list")!;
  const resourcesSection = document.getElementById("detail-resources")!;
  const resourcesList = document.getElementById("detail-resources-list")!;
  const countEl = document.getElementById("detail-count")!;

  /** Render the panel for the topic node `data`. */
  function showTopic(data: Enrichment): void {
    bloomEl.hidden = true;
    descEl.textContent = data.description ?? "";
    descEl.hidden = !data.description;

    // "Open full topic page" gives the panel an explicit navigation target
    // (nodes themselves stay panel-only). Concepts have no page, so it hides.
    if (openEl) {
      if (isHttpUrl(data.url) || (typeof data.url === "string" && data.url.startsWith("/"))) {
        openEl.href = data.url!;
        openEl.hidden = false;
      } else {
        openEl.hidden = true;
      }
    }

    const children = data.children ?? [];
    if (children.length > 0) {
      childrenList.innerHTML = children
        .map(
          (c) =>
            `<li class="associated-concept"><button class="detail-link" data-nav="${escapeHtml(c.id)}" type="button">${escapeHtml(c.name)}</button><span class="bloom-tag">${escapeHtml(c.bloom)}</span></li>`,
        )
        .join("");
      childrenSection.hidden = false;
    } else {
      childrenSection.hidden = true;
    }

    prereqsSection.hidden = true;
    papersSection.hidden = true;
    resourcesSection.hidden = true;

    const siteItems = data.siteItems ?? [];
    if (siteItems.length > 0) {
      itemsList.innerHTML = siteItems
        .map((item) => {
          const target = item.external ? ` target="_blank" rel="noopener"` : "";
          return `<li class="associated-item"><a href="${escapeHtml(item.href ?? "")}"${target} class="resource-link">${escapeHtml(item.title ?? "")}</a><span class="associated-meta">${escapeHtml(item.collection ?? "")}</span></li>`;
        })
        .join("");
      itemsSection.hidden = false;
    } else {
      itemsSection.hidden = true;
    }

    const count = data.contentCount ?? 0;
    if (count > 0) {
      countEl.innerHTML = `<strong>${count}</strong> site item${count !== 1 ? "s" : ""} tagged with this topic`;
    } else {
      countEl.textContent = "No site items tagged with this topic yet";
    }
    countEl.hidden = false;
  }

  /** Render the panel for the concept node `data` (label shown as the head). */
  function showConcept(data: Enrichment, label: string): void {
    bloomEl.textContent = `Bloom: ${data.bloom}`;
    bloomEl.hidden = false;
    descEl.hidden = true;
    childrenSection.hidden = true;
    itemsSection.hidden = true;
    if (openEl) openEl.hidden = true;

    const chain = data.prereqChain ?? [];
    if (chain.length > 0) {
      const steps = [
        ...chain.map((c) => `<button class="chain-step" data-nav="${escapeHtml(c.id)}" type="button">${escapeHtml(c.name)}</button>`),
        `<span class="chain-current">${escapeHtml(label)}</span>`,
      ];
      prereqChainEl.innerHTML = steps.join('<span class="chain-arrow">→</span>');
      prereqsSection.hidden = false;
    } else {
      prereqsSection.hidden = true;
    }

    const papers = data.papers ?? [];
    if (papers.length > 0) {
      papersList.innerHTML = papers.map(renderPaper).join("");
      papersSection.hidden = false;
    } else {
      papersSection.hidden = true;
    }

    const resources = data.resources ?? [];
    if (resources.length > 0) {
      resourcesList.innerHTML = resources
        .map((r) =>
          isHttpUrl(r.url)
            ? `<li><a href="${escapeHtml(r.url)}" target="_blank" rel="noopener" class="resource-link">${escapeHtml(r.name)}</a></li>`
            : `<li class="resource-item">${escapeHtml(r.name)}</li>`,
        )
        .join("");
      resourcesSection.hidden = false;
    } else {
      resourcesSection.hidden = true;
    }

    countEl.hidden = true;
  }

  /** Render one paper list item, guarding every URL before linking. */
  function renderPaper(p: any): string {
    const title = escapeHtml(p.title || "Untitled paper");
    const year = Number(p.year || 0);
    const metaBits: string[] = [];
    if (p.authors) metaBits.push(escapeHtml(p.authors));
    if (year > 0) metaBits.push(String(year));
    const metaHtml = metaBits.length ? `<span class="paper-authors">${metaBits.join(" · ")}</span>` : "";

    const titleHtml = isHttpUrl(p.url)
      ? `<a href="${escapeHtml(p.url)}" target="_blank" rel="noopener" class="resource-link paper-title-link">${title}</a>`
      : `<span class="paper-title">${title}</span>`;

    const hasCachedText = Boolean(p.fullTextCached);
    const chars = Number(p.fullTextChars || 0);
    const sourceUrl = p.fullTextSourceUrl || p.url || "";
    const cacheBadge = hasCachedText
      ? `<span class="paper-badge paper-badge--cached">Full text cached${chars > 0 ? ` · ${chars.toLocaleString()} chars` : ""}</span>`
      : `<span class="paper-badge paper-badge--missing">No cached full text</span>`;
    const cacheLink = hasCachedText && isHttpUrl(sourceUrl)
      ? `<a href="${escapeHtml(sourceUrl)}" target="_blank" rel="noopener" class="paper-cache-link">Open full-text source</a>`
      : "";
    const excerpt = escapeHtml((p.fullTextExcerpt || "") as string);
    const excerptHtml = hasCachedText && excerpt
      ? `<details class="paper-excerpt"><summary>Preview cached text</summary><p>${excerpt}</p></details>`
      : "";

    return `<li class="paper-item">${titleHtml}${metaHtml}<div class="paper-meta-row">${cacheBadge}${cacheLink}</div>${excerptHtml}</li>`;
  }

  function showDetail(id: string): void {
    const nodeEl = svg!.querySelector(`.node[data-id="${id}"]`);
    if (!nodeEl) return;
    const label = nodeEl.getAttribute("data-label")!;
    const type = nodeEl.getAttribute("data-type")!;
    const layer = nodeEl.getAttribute("data-layer")!;
    const data = enrichment[id];
    if (!data) return;

    chipEl.textContent = type === "topic" ? `Topic ${id}` : `Concept ${id}`;
    chipEl.className = `detail-chip detail-chip--${layer.toLowerCase()}`;
    titleEl.textContent = label;

    if (data.type === "topic") showTopic(data);
    else showConcept(data, label);

    panel!.hidden = false;
    highlightNode(id);
    panel!.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }

  for (const node of allNodes) {
    node.addEventListener("click", () => showDetail(node.getAttribute("data-id")!));
    node.addEventListener("keydown", (e: Event) => {
      const ke = e as KeyboardEvent;
      if (ke.key === "Enter" || ke.key === " ") { ke.preventDefault(); (node as HTMLElement).click(); }
    });
  }

  panel.querySelector(".detail-close")!.addEventListener("click", () => {
    panel!.hidden = true;
    clearHighlight();
  });

  // Topic-control buttons focus the matching node's detail.
  document.querySelectorAll("[data-node-id]").forEach((btn) => {
    btn.addEventListener("click", () => showDetail(btn.getAttribute("data-node-id")!));
  });

  // In-panel navigation (prereq chain steps, child concepts).
  panel.addEventListener("click", (e) => {
    const target = (e.target as HTMLElement).closest("[data-nav]");
    if (target) showDetail(target.getAttribute("data-nav")!);
  });
}
