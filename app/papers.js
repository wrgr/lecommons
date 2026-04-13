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

function summarizeAbstract(raw, paperType, isProxy) {
  const text = cleanText(raw);

  if (!text) {
    return {
      preview: "Abstract unavailable.",
      full: "",
      canExpand: false,
      qaFlag: true,
      missing: true,
      proxy: false,
    };
  }

  if (isProxy) {
    return {
      preview: text,
      full: text,
      canExpand: false,
      qaFlag: false,
      missing: false,
      proxy: true,
    };
  }

  if (looksMalformedAbstract(text, paperType)) {
    return {
      preview: "Abstract hidden by QA: source metadata appears malformed or excessively long.",
      full: "",
      canExpand: false,
      qaFlag: true,
      missing: false,
      proxy: false,
    };
  }

  const previewLimit = /book|monograph|book-series|edited-book/.test((paperType || "").toLowerCase()) ? 420 : 620;

  if (text.length <= previewLimit) {
    return {
      preview: text,
      full: text,
      canExpand: false,
      qaFlag: false,
      missing: false,
      proxy: false,
    };
  }

  return {
    preview: `${text.slice(0, previewLimit).replace(/\s+\S*$/, "")}...`,
    full: text,
    canExpand: text.length <= 3000,
    qaFlag: text.length > 1400,
    missing: false,
    proxy: false,
  };
}

export function buildPaperRows(seedPapers, hopPapers, endnotesEnriched) {
  const workMeta = new Map();
  for (const row of endnotesEnriched.rows || []) {
    if (!row.work_id) continue;
    if (!workMeta.has(row.work_id)) {
      workMeta.set(row.work_id, {
        topics: new Set(),
        artifactTypes: new Set(),
        notes: new Set(),
      });
    }
    const bucket = workMeta.get(row.work_id);
    for (const code of row.topic_codes || []) {
      bucket.topics.add(code);
    }
    bucket.artifactTypes.add(row.artifact_type || "paper_like");
    if (row.id) bucket.notes.add(row.id);
  }

  const toPaper = (paper, scope) => {
    const meta = workMeta.get(paper.id);
    const directTopics = (paper.topic_codes || []).filter(Boolean);
    const mergedTopics = new Set([...(meta ? [...meta.topics] : []), ...directTopics]);
    const artifactType =
      paper.artifact_type ||
      (scope === "seed" ? "paper_like" : "derived_one_hop");

    const artifactTypesSet = new Set(meta ? [...meta.artifactTypes] : [artifactType]);
    if (scope === "hop") {
      artifactTypesSet.add("derived_one_hop");
    }

    return {
      ...paper,
      scope,
      topic_codes: [...mergedTopics],
      artifactTypes: [...artifactTypesSet].sort(),
      matchedNoteCount: meta ? meta.notes.size : 0,
      abstractQA: summarizeAbstract(paper.abstract, paper.type, Boolean(paper.abstract_is_proxy)),
    };
  };

  const seedRows = (seedPapers.papers || []).map((paper) => toPaper(paper, "seed"));
  const hopRows = (hopPapers.papers || []).map((paper) => toPaper(paper, "hop"));
  return [...seedRows, ...hopRows];
}
