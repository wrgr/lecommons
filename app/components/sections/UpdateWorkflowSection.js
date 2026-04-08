import { html } from "../../lib.js";

export function UpdateWorkflowSection() {
  return html`
    <section className="panel">
      <h2>Update Workflow</h2>
      <p className="caption">Use this process when refreshing content, links, and editorial text in this workspace.</p>
      <ol className="flat-list compact">
        <li>
          Refresh and rebuild data with
          <code>python3 scripts/build_dataset.py --seed-limit 296 --doi-only --hop-per-seed 5 --hop-total-limit 180</code>.
        </li>
        <li>
          Pull additional web/uploads into the retrieval corpus with <code>python3 scripts/knowledge_ops.py sync ...</code>, then
          rebuild corpus if needed.
        </li>
        <li>
          Review program cards and links in <code>data/programs_summary.json</code>; keep all academic entries link-backed.
        </li>
        <li>
          QA pass on long abstracts and malformed text is enforced in <code>scripts/build_dataset.py</code> and
          <code>app/papers.js</code>; verify outliers after each rebuild.
        </li>
        <li>
          Run a quick UI check at <a href="http://127.0.0.1:8000/" target="_blank" rel="noreferrer">http://127.0.0.1:8000/</a>
          and confirm topic clustering, filters, and citation navigation.
        </li>
      </ol>
      <p className="caption">
        Full IEEE ICICLE content, partners, and community listings are maintained on the official site:
        <a href="https://sagroups.ieee.org/icicle/" target="_blank" rel="noreferrer"> https://sagroups.ieee.org/icicle/</a>.
      </p>
    </section>
  `;
}
