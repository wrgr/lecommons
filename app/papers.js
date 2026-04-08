import { cleanText } from "./text.js";

function looksMalformedAbstract(text, paperType) {
  const lower = text.toLowerCase();
  const urlCount = (text.match(/https?:\/\//g) || []).length;
  const isBookLike = /book|monograph|book-series|edited-book/.test((paperType || "").toLowerCase());

  if (text.length > 5000) return true;
  if (lower.includes("search for more papers by this author")) return true;
  if (lower.startsWith("no access") && lower.includes("doi.org")) return true;
  if (urlCount >= 4 && text.length > 900) return true;
  if (isBookLike && text.length > 1700) return true;
  return false;
}

function summarizeAbstract(raw, paperType) {
  const text = cleanText(raw);

  if (!text) {
    return {
      preview: "Abstract unavailable.",
      full: "",
      canExpand: false,
      qaFlag: false,
    };
  }

  if (looksMalformedAbstract(text, paperType)) {
    return {
      preview: "Abstract hidden by QA: source metadata appears malformed or excessively long.",
      full: "",
      canExpand: false,
      qaFlag: true,
    };
  }

  const previewLimit = /book|monograph|book-series|edited-book/.test((paperType || "").toLowerCase()) ? 420 : 620;

  if (text.length <= previewLimit) {
    return {
      preview: text,
      full: text,
      canExpand: false,
      qaFlag: false,
    };
  }

  return {
    preview: `${text.slice(0, previewLimit).replace(/\s+\S*$/, "")}...`,
    full: text,
    canExpand: text.length <= 3000,
    qaFlag: text.length > 1400,
  };
}

export function buildPaperRows(seedPapers, hopPapers, endnotesEnriched) {
  const workMeta = new Map();

  for (const row of endnotesEnriched.rows || []) {
    if (!row.matched || !row.work_id) continue;

    if (!workMeta.has(row.work_id)) {
      workMeta.set(row.work_id, {
        chapters: new Set(),
        artifactTypes: new Set(),
        notes: new Set(),
      });
    }

    const bucket = workMeta.get(row.work_id);
    if (Number.isFinite(row.chapter)) bucket.chapters.add(row.chapter);
    bucket.artifactTypes.add(row.artifact_type || "article_report_or_web");
    bucket.notes.add(row.id);
  }

  const toPaper = (paper, scope) => {
    const meta = workMeta.get(paper.id);
    return {
      ...paper,
      scope,
      chapters: meta ? [...meta.chapters].sort((a, b) => a - b) : [],
      artifactTypes: meta ? [...meta.artifactTypes] : scope === "seed" ? ["paper_or_article"] : ["derived_one_hop"],
      matchedNoteCount: meta ? meta.notes.size : 0,
      abstractQA: summarizeAbstract(paper.abstract, paper.type),
    };
  };

  const seedRows = (seedPapers.papers || []).map((paper) => toPaper(paper, "seed"));
  const hopRows = (hopPapers.papers || []).map((paper) => toPaper(paper, "hop"));
  return [...seedRows, ...hopRows];
}
