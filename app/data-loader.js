import { DATA_FILES } from "./constants.js";
import { buildEntityDirectory, enrichResourceEntities } from "./entities.js";
import { mergePrograms } from "./programs.js";
import { classifyResource, normalizeResourceSection } from "./resources.js";
import { cleanText, cleanUrl } from "./text.js";

async function fetchJson(config) {
  const response = await fetch(config.path);
  if (config.optional && response.status === 404) {
    return config.fallback;
  }
  if (!response.ok) {
    throw new Error(`${config.path}: ${response.status}`);
  }
  return response.json();
}

function normalizePaper(paper) {
  return {
    ...paper,
    id: cleanText(paper.id),
    openalex_id: cleanText(paper.openalex_id || paper.id),
    title: cleanText(paper.title || "Untitled"),
    abstract: cleanText(paper.abstract),
    year: paper.year,
    doi: cleanUrl(paper.doi),
    type: cleanText(paper.type || "unknown"),
    cited_by_count: Number(paper.cited_by_count || 0),
    authors: (paper.authors || []).map((author) => cleanText(author)).filter(Boolean),
    referenced_works: (paper.referenced_works || []).map((workId) => cleanText(workId)),
    citation_plain: cleanText(paper.citation_plain),
    citation_bibtex: cleanText(paper.citation_bibtex, { keepNewlines: true }),
    source_url: cleanUrl(paper.source_url),
  };
}

function normalizeResources(rawResources) {
  const sections = (rawResources.sections || []).map(normalizeResourceSection);
  const bareRows = sections.flatMap((section) => section.items || []);
  const resourceRows = enrichResourceEntities(bareRows).map((row) => ({
    ...row,
    group: classifyResource(row),
  }));

  return {
    resources: {
      ...rawResources,
      sections,
    },
    resourceRows,
  };
}

function normalizeEndnotesRaw(rawEndnotes) {
  return {
    ...rawEndnotes,
    notes: (rawEndnotes.notes || []).map((note) => ({
      ...note,
      artifact_type: cleanText(note.artifact_type || "article_report_or_web"),
    })),
  };
}

function normalizeEndnotesEnriched(rawEndnotes) {
  return {
    ...rawEndnotes,
    rows: (rawEndnotes.rows || []).map((row) => ({
      ...row,
      id: cleanText(row.id),
      chapter: Number(row.chapter),
      matched: Boolean(row.matched),
      work_id: cleanText(row.work_id),
      artifact_type: cleanText(row.artifact_type || "article_report_or_web"),
    })),
  };
}

function normalizeGraph(rawGraph) {
  return {
    ...rawGraph,
    nodes: (rawGraph.nodes || []).map((node) => ({
      ...node,
      id: cleanText(node.id),
      label: cleanText(node.label || node.id),
      type: cleanText(node.type || "unknown"),
      hop: Number(node.hop || 0),
      chapter: Number(node.chapter),
    })),
    edges: (rawGraph.edges || []).map((edge) => ({
      ...edge,
      source: cleanText(edge.source),
      target: cleanText(edge.target),
      type: cleanText(edge.type || "related"),
    })),
  };
}

function normalizeGaps(rawGaps) {
  return {
    ...rawGaps,
    gaps: (rawGaps.gaps || []).map((gap) => ({
      id: cleanText(gap.id),
      label: cleanText(gap.label),
      detail: cleanText(gap.detail),
      evidence_links: (gap.evidence_links || []).map(cleanUrl).filter(Boolean),
      evidence: gap.evidence || {},
    })),
  };
}

function normalizeExtraDocs(rawExtraDocs) {
  return {
    ...rawExtraDocs,
    count: Number(rawExtraDocs.count || 0),
    documents: (rawExtraDocs.documents || []).map((doc) => ({
      ...doc,
      source_type: cleanText(doc.source_type || "external"),
      title: cleanText(doc.title || "Untitled"),
      url: cleanUrl(doc.url),
      file_path: cleanText(doc.file_path),
      summary: cleanText(doc.summary),
    })),
  };
}

export async function loadAllData() {
  const loaded = Object.fromEntries(
    await Promise.all(Object.entries(DATA_FILES).map(async ([key, config]) => [key, await fetchJson(config)]))
  );

  const { resources, resourceRows } = normalizeResources(loaded.resources);

  const programs = mergePrograms(loaded.programs || {});
  const entities = buildEntityDirectory(resourceRows, programs);

  return {
    summary: loaded.summary,
    resources,
    resourceRows,
    entities,
    programs,
    seedPapers: {
      ...loaded.seedPapers,
      papers: (loaded.seedPapers.papers || []).map(normalizePaper),
    },
    hopPapers: {
      ...loaded.hopPapers,
      papers: (loaded.hopPapers.papers || []).map(normalizePaper),
    },
    endnotesRaw: normalizeEndnotesRaw(loaded.endnotesRaw),
    endnotesEnriched: normalizeEndnotesEnriched(loaded.endnotesEnriched),
    graph: normalizeGraph(loaded.graph),
    gaps: normalizeGaps(loaded.gaps),
    extraDocs: normalizeExtraDocs(loaded.extraDocs),
  };
}
