// @ts-check
import { defineConfig } from "astro/config";
import mdx from "@astrojs/mdx";

// Deployed to https://capabilitymatters.org via the gh-pages workflow. `site` + `base`
// keep canonical URLs and sitemap entries rooted at the custom domain.
export default defineConfig({
  site: "https://capabilitymatters.org",
  base: "/",
  integrations: [mdx()],
});
