/**
 * Papers and Artifacts: search and artifact filter over seed + expansion papers; topic browse when not searching.
 */
import { html } from "../../lib.js";

function PaperDetailBlock({ paper }) {
  const authorLine = paper.authors.length ? paper.authors.join(", ") : "Authors unavailable";
  return html`
    <details className="paper-hit">
      <summary>${paper.title}</summary>
      <p className="paper-hit-meta">
        <span className=${paper.scope === "hop" ? "paper-scope-tag paper-scope-hop" : "paper-scope-tag paper-scope-seed"}>
          ${paper.scope === "hop" ? "Expansion" : "Seed"}
        </span>
        ${authorLine}${paper.year ? ` · ${paper.year}` : ""}
      </p>
      <p
        className=${paper.abstractQA.missing ? "abstract missing" : paper.abstractQA.qaFlag ? "abstract warning" : "abstract"}
      >
        ${paper.abstractQA.proxy ? "[Proxy description] " : ""}
        ${paper.abstractQA.preview}
      </p>
      <p><strong>Citation:</strong> ${paper.citation_plain || "No citation available."}</p>
      ${paper.source_url
        ? html`<p><a href=${paper.source_url} target="_blank" rel="noreferrer">source</a></p>`
        : ""}
    </details>
  `;
}

export function PapersSection({
  search,
  setSearch,
  artifactFilter,
  setArtifactFilter,
  artifactOptions,
  filteredPapers,
  topicPaperClusters,
  dataQuality,
}) {
  const queryTrim = (search || "").trim();

  return html`
    <section className="panel">
      <div className="panel-head">
        <div>
          <h2>Papers and Artifacts</h2>
          <p className="caption">
            Seed and expansion (one-hop) papers are both included here — the graph “Include related papers” switch only affects the
            graph above, not this list. Grouped by topic when not searching; search matches every paper below.
          </p>
        </div>
        <div className="controls">
          <input
            type="search"
            value=${search}
            onInput=${(event) => setSearch(event.target.value)}
            placeholder="Search by title, author, or citation"
          />
          <select value=${artifactFilter} onChange=${(event) => setArtifactFilter(event.target.value)}>
            <option value="all">All artifact types</option>
            ${artifactOptions.map((type) => html`<option key=${type} value=${type}>${type}</option>`)}
          </select>
        </div>
      </div>

      <p className="caption">${filteredPapers.length} papers across ${topicPaperClusters.length} topic clusters.</p>
      <div className="quality-banner">
        <strong>Coverage notes:</strong>
        ${dataQuality.missingAbstractCount} papers are missing abstract text, ${dataQuality.proxyAbstractCount} use proxy descriptions,
        ${dataQuality.shortTitleCount} have short titles,
        and ${dataQuality.missingResourceTopicCount} topics have no non-paper resources yet.
        ${dataQuality.missingResourceTopicCodes?.length
          ? html` Topics missing resources: ${dataQuality.missingResourceTopicCodes.join(", ")}.`
          : ""}
      </div>

      ${queryTrim
        ? html`
            <div className="paper-search-matches">
              <h3 className="paper-search-matches-head">
                Matching papers <span className="count-pill">${filteredPapers.length}</span>
              </h3>
              <p className="caption">Clear the search box to browse by topic cluster again.</p>
              ${filteredPapers.length
                ? html`
                    <ul className="flat-list compact paper-flat-list">
                      ${filteredPapers.map(
                        (paper) => html`
                          <li key=${`hit:${paper.id}`}>
                            <${PaperDetailBlock} paper=${paper} />
                          </li>
                        `
                      )}
                    </ul>
                  `
                : html`<p className="caption">No papers match — try different words, clear the artifact filter, or check spelling.</p>`}
            </div>
          `
        : html`
            <details className="paper-tray" open>
              <summary>Browse by topic</summary>
              <div className="topic-paper-grid">
                ${topicPaperClusters.map(
                  (cluster) => html`
                    <article className="topic-paper-card" key=${cluster.key}>
                      <h3>${cluster.label}</h3>
                      <p className="caption">${cluster.papers.length} papers</p>
                      <details>
                        <summary>Show papers</summary>
                        <ul className="flat-list compact">
                          ${cluster.papers.map(
                            (paper) => html`
                              <li key=${`cluster:${cluster.key}:${paper.id}`}>
                                <${PaperDetailBlock} paper=${paper} />
                              </li>
                            `
                          )}
                        </ul>
                      </details>
                    </article>
                  `
                )}
              </div>
            </details>
          `}
    </section>
  `;
}
