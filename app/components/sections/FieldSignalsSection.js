import { html } from "../../lib.js";

export function FieldSignalsSection({ signalCards }) {
  return html`
    <section className="panel">
      <h2>Field Signals</h2>
      <div className="signal-grid">
        ${signalCards.map(
          (card) => html`
            <article className="signal-card" key=${card.id}>
              <h3>${card.title}</h3>
              <p>${card.body}</p>
              ${card.links.length
                ? html`
                    <details>
                      <summary>Sources (${card.links.length})</summary>
                      <ul className="flat-list compact">
                        ${card.links.map(
                          (link) => html`<li key=${`${card.id}:${link}`}><a href=${link} target="_blank" rel="noreferrer">${link}</a></li>`
                        )}
                      </ul>
                    </details>
                  `
                : ""}
            </article>
          `
        )}
      </div>
    </section>
  `;
}
