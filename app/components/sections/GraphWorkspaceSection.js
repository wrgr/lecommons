import { html } from "../../lib.js";
import { shortLabel } from "../../text.js";
import { GraphCanvas } from "../GraphCanvas.js";

export function GraphWorkspaceSection({
  includeHop,
  setIncludeHop,
  visibleGraph,
  selectedNodeId,
  setSelectedNodeId,
  selectedNode,
  citationContext,
  nodeRelatedPapers,
  nodeRelatedResources,
}) {
  return html`
    <section className="panel">
      <div className="panel-head">
        <div>
          <h2>Graph Workspace</h2>
          <p className="caption">Selected node details and citation links appear directly below the graph.</p>
        </div>
        <label className="switch">
          <input type="checkbox" checked=${includeHop} onChange=${(event) => setIncludeHop(event.target.checked)} />
          <span>Include one-hop expansion</span>
        </label>
      </div>

      <${GraphCanvas}
        nodes=${visibleGraph.nodes}
        links=${visibleGraph.links}
        selectedNodeId=${selectedNodeId}
        onSelect=${setSelectedNodeId}
      />

      <div className="selected-node-panel">
        ${selectedNode
          ? html`
              <div className="selected-node-head">
                <h3>Selected Node</h3>
                <div className="tags">
                  <span className="tag tag-topic">${selectedNode.type}</span>
                  <span className="tag">hop ${selectedNode.hop}</span>
                  <span className="tag">${selectedNode.id}</span>
                </div>
              </div>

              <p><strong>${selectedNode.label}</strong></p>

              <details>
                <summary>Provenance</summary>
                <pre>${JSON.stringify(selectedNode.provenance || {}, null, 2)}</pre>
              </details>

              <div className="citation-grid">
                <article className="citation-col">
                  <h4>Incoming Links (${citationContext.incoming.length})</h4>
                  <ul className="flat-list compact">
                    ${citationContext.incoming.slice(0, 20).map(
                      ({ edge, node }) => html`
                        <li key=${`in:${edge.source}:${edge.target}:${edge.type}`}>
                          <button className="node-link" onClick=${() => setSelectedNodeId(node.id)}>
                            ${shortLabel(node.label, 88)}
                          </button>
                          <span className="mini-tag">${edge.type}</span>
                        </li>
                      `
                    )}
                  </ul>
                </article>

                <article className="citation-col">
                  <h4>Outgoing Links (${citationContext.outgoing.length})</h4>
                  <ul className="flat-list compact">
                    ${citationContext.outgoing.slice(0, 20).map(
                      ({ edge, node }) => html`
                        <li key=${`out:${edge.source}:${edge.target}:${edge.type}`}>
                          <button className="node-link" onClick=${() => setSelectedNodeId(node.id)}>
                            ${shortLabel(node.label, 88)}
                          </button>
                          <span className="mini-tag">${edge.type}</span>
                        </li>
                      `
                    )}
                  </ul>
                </article>
              </div>

              <div className="node-fit-grid">
                <article>
                  <h4>Related Papers</h4>
                  <ul className="flat-list compact">
                    ${nodeRelatedPapers.length
                      ? nodeRelatedPapers.map((paper) => html`<li key=${`np:${paper.id}`}>${shortLabel(paper.title, 120)}</li>`)
                      : html`<li>No direct paper matches for this node.</li>`}
                  </ul>
                </article>
                <article>
                  <h4>Related Resources</h4>
                  <ul className="flat-list compact">
                    ${nodeRelatedResources.length
                      ? nodeRelatedResources.map(
                          (resource) => html`
                            <li key=${`nr:${resource.key}`}>
                              <a href=${resource.url} target="_blank" rel="noreferrer">${shortLabel(resource.title, 120)}</a>
                            </li>
                          `
                        )
                      : html`<li>No direct resource matches for this node.</li>`}
                  </ul>
                </article>
              </div>
            `
          : html`<p className="caption">Select a node to inspect provenance and citation context.</p>`}
      </div>
    </section>
  `;
}
