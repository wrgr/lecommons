import { GENERIC_RESOURCE_TITLES } from "./constants.js";
import { cleanText, cleanUrl, contextSnippet, prettyDomain } from "./text.js";

function makeDescriptiveResourceTitle(rawTitle, context, section, url) {
  const title = cleanText(rawTitle);
  const sectionLabel = cleanText(section);
  const contextLabel = cleanText(context);
  const titleLower = title.toLowerCase();
  const looksLikeUrl = /^https?:\/\//i.test(title) || /^www\./i.test(title);

  if (!title) {
    const fallback = contextSnippet(contextLabel, 11) || sectionLabel || "Resource";
    const domain = prettyDomain(url);
    return domain ? `${fallback} (${domain})` : fallback;
  }

  if (looksLikeUrl) {
    const fallback = contextSnippet(contextLabel, 11) || sectionLabel || "Resource";
    const domain = prettyDomain(url || title);
    return domain ? `${fallback} (${domain})` : fallback;
  }

  if (GENERIC_RESOURCE_TITLES.has(titleLower) || title.length < 5) {
    const extra = contextSnippet(contextLabel, 11);
    if (extra && extra.toLowerCase() !== titleLower) {
      return `${title}: ${extra}`;
    }
  }

  if (sectionLabel && titleLower === sectionLabel.toLowerCase() && contextLabel) {
    return `${title}: ${contextSnippet(contextLabel, 11)}`;
  }

  return title;
}

export function classifyResource(row) {
  const blob = `${row.section} ${row.title} ${row.context} ${row.url}`.toLowerCase();

  if (/conference|proceedings|meeting|symposium|summit|workshop|icicle 20\d{2}/.test(blob)) {
    return "Conferences & Events";
  }
  if (/team|roles|experts|faculty|coach|stakeholder/.test(blob)) {
    return "People & Teams";
  }
  if (/webinar|podcast|youtube|youtu\.be|keynote|video/.test(blob)) {
    return "Media & Webinars";
  }
  if (/book|chapter|routledge|press|taylorfrancis|ebook/.test(blob)) {
    return "Books & Reading";
  }
  if (/template|checklist|tracker|process|guide|analysis|tool|workflow|model/.test(blob)) {
    return "Methods & Tools";
  }
  if (/standard|ieee|ltsc|xapi|caliper|specification/.test(blob)) {
    return "Standards & Infrastructure";
  }
  if (/university|institute|academy|community|consortium|program/.test(blob)) {
    return "Programs & Organizations";
  }
  return "Other";
}

export function normalizeKey(value) {
  return cleanText(value).toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/(^-|-$)/g, "");
}

export function normalizeResourceSection(section) {
  const sectionLabel = cleanText(section.section);

  return {
    section: sectionLabel,
    items: (section.items || []).map((item, index) => {
      const contextLabel = cleanText(item.context);
      const title = makeDescriptiveResourceTitle(item.title || item.url, contextLabel, sectionLabel, item.url);

      return {
        key: `${normalizeKey(section.section)}-${index}-${normalizeKey(title || item.url)}`,
        section: sectionLabel,
        title,
        url: cleanUrl(item.url),
        context: contextLabel,
      };
    }),
  };
}
