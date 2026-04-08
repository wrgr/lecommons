import { cleanText, cleanUrl } from "./text.js";
import { normalizeKey } from "./resources.js";

function canonicalInstitution(value) {
  const cleaned = cleanText(value)
    .replace(/\([^)]*\)/g, " ")
    .replace(/\bSchool of Education\b/i, " ")
    .replace(/\bMaster of Education\b/i, " ")
    .replace(/\bM\.Ed\.?\b/i, " ")
    .replace(/\bProgram\b/gi, " ");

  return cleaned
    .toLowerCase()
    .replace(/[^a-z0-9\s]/g, " ")
    .replace(/\b(the|of|for|and|in|at|university|college|institute|school|community|consortium)\b/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

function editorializeProgram(program) {
  const rawName = cleanText(program.name);
  let name = rawName;
  const category = cleanText(program.category || "other");
  const links = (program.links || []).map(cleanUrl).filter(Boolean);
  const lower = rawName.toLowerCase();

  let summary = cleanText(program.summary);

  if (lower.includes("carnegie mellon")) {
    name = "Carnegie Mellon University";
    summary =
      "CMU's METALS degree pathway, Open Learning Initiative (OLI), and OpenSimon ecosystem demonstrate a mature learning engineering stack spanning research, instrumentation, and iterative course improvement.";
  }

  if (lower.includes("johns hopkins") || lower.includes("lens")) {
    name = "Johns Hopkins University";
    summary =
      "Johns Hopkins' Learning Design and Technology program aligns with a systems-oriented learning engineering approach for high-consequence domains, including healthcare, defense, and large-scale education.";
  }

  if (lower.includes("arizona state")) {
    summary =
      "ASU combines institute-level research with graduate pathways, connecting learning science, analytics, and implementation practices at scale.";
  }

  if (lower.includes("boston college")) {
    summary =
      "Boston College offers a practice-focused learning design and technology pathway with direct alignment to evidence-based instructional decision cycles.";
  }

  if (lower.includes("icicle")) {
    summary =
      "ICICLE is a field coordination hub that curates frameworks, convenes working groups, and supports shared learning engineering standards and practice artifacts.";
  }

  if (lower.includes("learning agency")) {
    summary =
      "The Learning Agency Community connects practitioners and researchers through open programming, events, and community-sourced learning engineering resources.";
  }

  if (lower.includes("yet analytics")) {
    summary =
      "Yet Analytics provides implementation-oriented tooling and services for instrumentation, data interoperability, and evidence workflows in learning systems.";
  }

  return {
    name,
    category,
    summary,
    links,
    institutionKey: canonicalInstitution(name),
    relatedMentions: [],
  };
}

function parseAdjacentMention(mention) {
  const text = cleanText(mention);
  if (!text || text.startsWith("(Replaces")) return null;

  const dashIndex = text.indexOf(" - ");
  if (dashIndex <= 0) {
    return {
      institution: text,
      detail: "",
      raw: text,
      key: canonicalInstitution(text),
    };
  }

  const institution = cleanText(text.slice(0, dashIndex));
  const detail = cleanText(text.slice(dashIndex + 3));

  return {
    institution,
    detail,
    raw: text,
    key: canonicalInstitution(institution),
  };
}

export function mergePrograms(programPayload) {
  const basePrograms = (programPayload.programs || []).map(editorializeProgram);
  const byKey = new Map();

  for (const program of basePrograms) {
    byKey.set(program.institutionKey || normalizeKey(program.name), program);
  }

  const mentions = (programPayload.adjacent_program_mentions || []).map(parseAdjacentMention).filter(Boolean);

  for (const mention of mentions) {
    const key = mention.key || normalizeKey(mention.institution);

    if (byKey.has(key)) {
      const program = byKey.get(key);
      if (mention.detail && !program.relatedMentions.includes(mention.detail)) {
        program.relatedMentions.push(mention.detail);
      }
      continue;
    }

    const synthetic = {
      name: mention.institution,
      category: "academic",
      summary:
        mention.detail ||
        "Adjacent program mention extracted from source lists; verify current program structure before formal inclusion.",
      links: [],
      institutionKey: key,
      relatedMentions: [],
      adjacentOnly: true,
    };

    byKey.set(key, synthetic);
    basePrograms.push(synthetic);
  }

  for (const program of basePrograms) {
    program.relatedMentions = [...new Set(program.relatedMentions)].slice(0, 8);
  }

  const academicLinkHints = [
    ["carnegie mellon", "https://www.cmu.edu/masters-educational-technology-applied-learning-science/"],
    ["arizona state", "https://education.asu.edu/degree/graduate-certificate-learning-engineering"],
    [
      "johns hopkins",
      "https://education.jhu.edu/masters-programs/master-of-education-in-learning-design-and-technology/",
    ],
    [
      "boston college",
      "https://www.bc.edu/content/bc-web/schools/lynch-school/academics/departments-and-programs/curriculum-and-instruction/ma-learning-design-technology.html",
    ],
    ["stanford", "https://ed.stanford.edu/academics/masters-programs"],
    ["harvard", "https://www.gse.harvard.edu/academics/masters"],
    ["university pennsylvania", "https://www.gse.upenn.edu/academics/programs"],
    ["northwestern", "https://www.northwestern.edu"],
    ["asbury", "https://www.asbury.edu"],
  ];

  return basePrograms.map((program) => {
    if (program.category !== "academic" || program.links?.length) return program;

    const lower = `${program.name} ${program.summary}`.toLowerCase();
    const hinted = academicLinkHints.find(([needle]) => lower.includes(needle));
    if (hinted) {
      return { ...program, links: [hinted[1]] };
    }

    const query = encodeURIComponent(`${program.name} learning program`);
    return { ...program, links: [`https://duckduckgo.com/?q=${query}`] };
  });
}
