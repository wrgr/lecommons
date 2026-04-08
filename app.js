import { App } from "./app/components/App.js";
import { createRoot, html } from "./app/lib.js";

createRoot(document.getElementById("app")).render(html`<${App} />`);
