import { html } from "../../lib.js";

export function ExtraDocsSection({ extraDocs }) {
  return html`
    <section className="panel">
      <h2>Scanned and Uploaded Docs</h2>
      ${extraDocs.documents.length
        ? html`
            <p className="caption">${extraDocs.count || extraDocs.documents.length} docs in retrieval corpus. Showing up to 40.</p>
            <ul className="flat-list">
              ${extraDocs.documents.slice(0, 40).map(
                (doc, index) => html`
                  <li key=${`doc:${index}:${doc.title}`}>
                    <strong>${doc.title}</strong>
                    <span className="tag">${doc.source_type}</span>
                    ${doc.url ? html`<a href=${doc.url} target="_blank" rel="noreferrer">open source</a>` : ""}
                    ${doc.file_path ? html`<code>${doc.file_path}</code>` : ""}
                    ${doc.summary ? html`<p>${doc.summary}</p>` : ""}
                  </li>
                `
              )}
            </ul>
          `
        : html`
            <p className="caption">
              No scanned or uploaded docs yet. Use <code>scripts/knowledge_ops.py</code> to ingest documents.
            </p>
          `}
    </section>
  `;
}
