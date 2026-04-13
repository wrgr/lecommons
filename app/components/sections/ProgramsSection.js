import { html } from "../../lib.js";

export function ProgramsSection({ groupedPrograms }) {
  const academicPrograms = groupedPrograms.academic || [];

  if (!academicPrograms.length) return "";

  return html`
    <section className="panel">
      <div className="panel-head">
        <div>
          <h2>Academic Programs</h2>
          <p className="caption">A quick view of degree and certificate programs. For organizations, people, and other resources, use Resource Navigator.</p>
        </div>
      </div>

      <div className="program-grid">
        ${academicPrograms.map((program) => {
          const displayLinks = program.links.length
            ? program.links
            : [`https://duckduckgo.com/?q=${encodeURIComponent(`${program.name} learning program`)}`];

          return html`
            <article className="program-card" key=${program.name}>
              <h3>${program.name}</h3>
              <p>${program.summary}</p>
              ${displayLinks.length
                ? html`
                    <p className="program-links">
                      ${displayLinks.map(
                        (link, index) => html`
                          <a key=${`${program.name}:${link}`} href=${link} target="_blank" rel="noreferrer">
                            ${index === 0 ? "website" : "source"}
                          </a>
                        `
                      )}
                    </p>
                  `
                : ""}
            </article>
          `;
        })}
      </div>
    </section>
  `;
}
