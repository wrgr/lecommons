/**
 * Merges `programs_summary.json` academic rows into ICICLE-derived resource rows
 * so degree and certificate programs stay visible under Programs & Curricula without a separate panel.
 */
import { normalizeKey } from "./resources.js";
import { cleanText, cleanUrl } from "./text.js";

/** Appends academic program rows missing from the navigator (matched by normalized title). */
export function appendAcademicProgramRowsFromSummary(programPayload, bareRows) {
  const programs = programPayload.programs || [];
  const academic = programs.filter((p) => cleanText(p.category).toLowerCase() === "academic");
  const seen = new Set(bareRows.map((r) => normalizeKey(r.title)));

  const additions = [];
  for (const p of academic) {
    const title = cleanText(p.name);
    const nk = normalizeKey(title);
    if (!title || seen.has(nk)) continue;
    seen.add(nk);

    const links = (p.links || []).map(cleanUrl).filter(Boolean);
    additions.push({
      key: `programs-summary-${nk}`,
      section: "Programs & Curricula",
      title,
      url: links[0] || "",
      context: cleanText(p.summary),
      topic_codes: [],
      resource_id: "",
      content_type: "PC",
      status: "APPROVED",
    });
  }

  return [...bareRows, ...additions];
}
