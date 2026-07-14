// @ts-check
import { defineConfig } from "astro/config";
import mdx from "@astrojs/mdx";

// Deployed via GitHub Pages at the default wrgr.github.io/lecommons URL (no
// custom domain configured yet). `site` + `base` keep canonical URLs and
// sitemap entries rooted there — update both if a custom domain is added.
export default defineConfig({
  site: "https://wrgr.github.io",
  base: "/lecommons/",
  integrations: [mdx()],
});
