// @ts-check
import { defineConfig } from "astro/config";
import mdx from "@astrojs/mdx";

// Deployed to https://lecommons.org via the gh-pages workflow. `site` + `base`
// keep canonical URLs and sitemap entries rooted at the custom domain.
export default defineConfig({
  site: "https://lecommons.org",
  base: "/",
  integrations: [mdx()],
});
