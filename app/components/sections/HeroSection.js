import { html } from "../../lib.js";
import { SITE_DISCLAIMER } from "../../siteCopy.js";

export function HeroSection({ stats }) {
  return html`
    <header className="wrap hero">
      <div className="hero-layout">
        <div className="hero-copy">
          <p className="eyebrow">Learning Engineering</p>
          <h1>A curated evidence workspace for the learning engineering field</h1>
          <p className="lede">
            Explore core and related papers, field programs, and non-paper resources — each linked to a topic and traceable back to
            its source. Provenance is visible on every item.
          </p>
          <p style=${{ marginTop: "0.9rem" }}>
            <a href="whitepaper.html" className="wp-cta">Read the whitepaper →</a>
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

      <p className="hero-disclaimer">${SITE_DISCLAIMER}</p>
    </header>
  `;
}
