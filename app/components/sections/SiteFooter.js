/** Page footer with the same development disclaimer as the hero for readers who skip the top of the page. */
import { html } from "../../lib.js";
import { SITE_DISCLAIMER } from "../../siteCopy.js";

export function SiteFooter() {
  return html`
    <footer className="wrap site-footer">
      <p>${SITE_DISCLAIMER}</p>
    </footer>
  `;
}
