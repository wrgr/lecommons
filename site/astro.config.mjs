// @ts-check
import { defineConfig } from "astro/config";
import mdx from "@astrojs/mdx";

// Deployed to https://wrgr.github.io/learning-engineering-resources/ via the
// gh-pages workflow. `site` + `base` make Astro generate correctly prefixed
// canonical URLs and sitemap entries. Internal links still need to prepend
// `import.meta.env.BASE_URL` — Astro does not auto-rewrite hard-coded hrefs.
export default defineConfig({
  site: "https://wrgr.github.io",
  base: "/learning-engineering-resources/",
  integrations: [mdx()],
});
