export const DATA_FILES = {
  summary: { path: "data/build_summary.json" },
  graph: { path: "data/graph.json" },
  resources: { path: "data/icicle_resources.json" },
  seedPapers: { path: "data/papers_seed.json" },
  hopPapers: { path: "data/papers_one_hop.json" },
  endnotesEnriched: { path: "data/endnotes_enriched.json" },
  endnotesRaw: { path: "data/endnotes_raw.json" },
  programs: { path: "data/programs_summary.json" },
  gaps: { path: "data/gaps.json" },
  extraDocs: {
    path: "data/extra_docs.json",
    optional: true,
    fallback: { count: 0, documents: [] },
  },
};

export const RESOURCE_GROUP_ORDER = [
  "People & Teams",
  "Conferences & Events",
  "Methods & Tools",
  "Programs & Organizations",
  "Books & Reading",
  "Media & Webinars",
  "Standards & Infrastructure",
  "Other",
];

export const OLD_LENS_URL = "https://education.jhu.edu/academics/masters-programs/learning-design-technology/";
export const NEW_LENS_URL =
  "https://education.jhu.edu/masters-programs/master-of-education-in-learning-design-and-technology/";

export const NODE_COLORS = {
  topic_part: "#0f766e",
  topic_surface: "#f97316",
  topic: "#334155",
  paper_seed: "#1d4ed8",
  paper_hop: "#a16207",
  unknown: "#94a3b8",
};

export const CP1252_REPAIRS = {
  "\u0091": "'",
  "\u0092": "'",
  "\u0093": '"',
  "\u0094": '"',
  "\u0096": "-",
  "\u0097": "-",
  "\u00A0": " ",
};

export const CONTROL_CHARS_RE = /[\u0000-\u0008\u000B\u000C\u000E-\u001F\u007F-\u009F]/g;
export const PERSON_RE = /\b([A-Z][a-z]+(?:\s+[A-Z][a-z.'-]+){1,2})\b/g;
export const ORG_RE =
  /\b([A-Z][A-Za-z&.'-]+(?:\s+[A-Z][A-Za-z&.'-]+){0,8}\s(?:University|College|Institute|Consortium|Community|School|Academy|Committee|Center|Centre|Agency|Laboratory|Labs))\b/g;

export const PERSON_BLOCKLIST = new Set([
  "Learning Engineering",
  "Learning Sciences",
  "Open Learning",
  "Design Thinking",
  "Stage Two",
  "Higher Education",
  "Market Interest",
  "Mission Critical",
  "Performance Task",
  "Silver Lining",
  "Generalizable Learning",
  "Organization Maturity",
  "Learning Design",
  "Instructional Design",
  "Data Use",
]);

export const TOKEN_BLOCKLIST = new Set([
  "the",
  "and",
  "for",
  "with",
  "from",
  "learning",
  "engineering",
  "chapter",
  "toolkit",
  "resource",
  "resources",
  "icicle",
]);

export const GENERIC_RESOURCE_TITLES = new Set([
  "activity",
  "introduction",
  "presentation",
  "workbook",
  "resource",
  "resources",
  "video",
  "tool",
  "article",
  "link",
  "source",
]);
