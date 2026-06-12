// Content collection schemas.
//
// Six collections, organized around the visitor's question:
//   practice      — how LEs work (diagrams, frameworks, methods, templates, toolkits)
//   tools         — platforms and software LEs build on
//   field-notes   — short editorial practitioner posts (our voice)
//   reading-list  — papers, books, articles, reports, posts
//   events        — conferences, workshops, recurring series, talks, podcasts, keynotes
//   community     — orgs, programs, degrees, people

import { defineCollection } from "astro:content";
import { glob } from "astro/loaders";
import { z } from "zod";

// Format enum covers every artifact type. A record lives in exactly one collection;
// format tells the visitor what *kind* of thing it is within that section.
const formats = [
  // practice
  "diagram", "framework", "method", "template", "toolkit",
  // tools
  "tool", "platform",
  // reading-list
  "paper", "book", "article", "report", "post", "essay",
  // events
  "conference", "workshop", "series", "convening",
  "video", "podcast", "keynote", "webinar", "conference-talk",
  // community
  "org", "program", "degree", "person", "event", "institution", "study-group",
] as const;

const urlTransform = z
  .string()
  .optional()
  .transform((v) => (v && /^https?:\/\//.test(v) ? v : undefined));

const provenance = z.object({
  dataset: z.string(),
  ref: z.string().optional(),
  sheet: z.string().optional(),
  sectionHeader: z.string().optional(),
});

const resourceSchema = z.object({
  title: z.string(),
  format: z.enum(formats),
  venue: z.string().optional(),
  authors: z.string().optional(),
  year: z.number().optional(),
  url: urlTransform,
  otherUrls: z.array(z.string()).default([]),
  cluster: z.string().optional(),
  topics: z.array(z.string()).default([]),
  tags: z.array(z.string()).default([]),
  featured: z.boolean().default(false),
  missingProvenance: z.boolean().default(false),
  // A 2-4 sentence editorial abstract — distinct from the MDX body.
  summary: z.string().optional(),
  // Embeddable player URL (YouTube /embed/ID, Vimeo /video/ID, etc).
  // Only set for items that are safe & useful to embed inline.
  embed: urlTransform,
  // Optional speaker portrait shown in the hero header for embed-bearing
  // cards. Falls back to the YouTube thumbnail when omitted.
  speakerImage: urlTransform,
  // Optional display name for the speaker(s) shown alongside the portrait.
  // Distinct from `authors` (which may be a long credit string).
  speakerName: z.string().optional(),
  provenance,
  order: z.number().default(999),
});

const fieldNoteSchema = z.object({
  title: z.string(),
  date: z.coerce.date(),
  summary: z.string(),
  tags: z.array(z.string()).default([]),
  draft: z.boolean().default(false),
});

function resourceCollection(name: string) {
  return defineCollection({
    loader: glob({ pattern: "**/*.mdx", base: `./src/content/${name}` }),
    schema: resourceSchema,
  });
}

export const collections = {
  practice:       resourceCollection("practice"),
  tools:          resourceCollection("tools"),
  "reading-list": resourceCollection("reading-list"),
  events:         resourceCollection("events"),
  community:      resourceCollection("community"),
  "field-notes":  defineCollection({
    loader: glob({ pattern: "**/*.mdx", base: "./src/content/field-notes" }),
    schema: fieldNoteSchema,
  }),
};
