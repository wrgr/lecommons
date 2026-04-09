import { CONTROL_CHARS_RE, CP1252_REPAIRS, NEW_LENS_URL, OLD_LENS_URL } from "./constants.js";

function decodeHtmlEntities(value) {
  if (value == null) return "";
  const decoder = decodeHtmlEntities.decoder || (decodeHtmlEntities.decoder = document.createElement("textarea"));
  decoder.innerHTML = String(value);
  return decoder.value;
}

export function cleanText(value, { keepNewlines = false } = {}) {
  if (value == null) return "";
  const decoded = decodeHtmlEntities(String(value))
    .replace(/[\u0091\u0092\u0093\u0094\u0096\u0097\u00A0]/g, (ch) => CP1252_REPAIRS[ch] || ch)
    .normalize("NFKC");

  if (keepNewlines) {
    return decoded
      .replace(/\r\n/g, "\n")
      .split("\n")
      .map((line) => line.replace(CONTROL_CHARS_RE, " ").trimEnd())
      .join("\n")
      .replace(/\n{3,}/g, "\n\n")
      .trim();
  }

  return decoded.replace(CONTROL_CHARS_RE, " ").replace(/\s+/g, " ").trim();
}

export function cleanUrl(value) {
  const raw = cleanText(value);
  if (!raw) return "";

  let url = raw.replace(/\s/g, "");
  if (url === OLD_LENS_URL || url.includes("education.jhu.edu/academics/masters-programs/learning-design-technology")) {
    url = NEW_LENS_URL;
  }
  if (url.startsWith("www.")) {
    url = `https://${url}`;
  }
  return url;
}

export function shortLabel(text, maxLength = 54) {
  const value = cleanText(text);
  if (value.length <= maxLength) return value;
  return `${value.slice(0, maxLength - 1)}...`;
}

export function contextSnippet(value, maxWords = 12) {
  const cleaned = cleanText(value);
  if (!cleaned) return "";
  const words = cleaned.split(" ");
  if (words.length <= maxWords) return cleaned;
  return `${words.slice(0, maxWords).join(" ")}...`;
}

export function prettyDomain(value) {
  try {
    const source = cleanUrl(value);
    if (!source) return "";
    return new URL(source).hostname.replace(/^www\./i, "");
  } catch {
    return "";
  }
}
