/** Maps topic codes (T00–T17) to URL slugs and back. */

// @ts-ignore — JSON import
import topicMap from "./topic_map.json";

const codeToSlug = new Map<string, string>();
const slugToCode = new Map<string, string>();
const codeToName = new Map<string, string>();

for (const t of topicMap as { topic_code: string; topic_name: string }[]) {
  const slug = t.topic_name
    .toLowerCase()
    .replace(/&/g, "and")
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/(^-|-$)/g, "");
  codeToSlug.set(t.topic_code, slug);
  slugToCode.set(slug, t.topic_code);
  codeToName.set(t.topic_code, t.topic_name);
}

export function topicSlug(code: string): string {
  return codeToSlug.get(code) ?? code.toLowerCase();
}

export function topicCode(slug: string): string {
  return slugToCode.get(slug) ?? slug;
}

export function topicName(code: string): string {
  return codeToName.get(code) ?? code;
}

export function topicUrl(code: string): string {
  const base = import.meta.env.BASE_URL;
  return `${base}topics/${topicSlug(code)}/`;
}
