import { html } from "../../lib.js";

export function HeroSection({ stats }) {
  return html`
    <header className="wrap hero">
      <div className="hero-layout">
        <div className="hero-copy">
          <p className="eyebrow">Learning Engineering Knowledge Studio</p>
          <h1>Graph-grounded evidence workspace with editorial curation and citation QA</h1>
          <p className="lede">
            Resources, programs, and papers are now organized into entity-aware collections, with selected-node provenance and
            a citation explorer directly under the graph for faster inspection.
          </p>
        </div>
        <figure className="hero-figure">
          <img src="assets/what-is-le-banner.png" alt="Learning engineering framework poster" />
        </figure>
      </div>

      <div className="stats-grid">
        ${stats.map(
          ([label, value]) => html`
            <article className="stat-card" key=${label}>
              <div className="k">${label}</div>
              <div className="v">${value}</div>
            </article>
          `
        )}
      </div>
    </header>
  `;
}
