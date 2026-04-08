import { TOKEN_BLOCKLIST } from "./constants.js";
import { cleanText } from "./text.js";

export function groupBy(items, keyFn) {
  return items.reduce((acc, item) => {
    const key = keyFn(item);
    if (!acc[key]) acc[key] = [];
    acc[key].push(item);
    return acc;
  }, {});
}

export function clamp(value, min, max) {
  return Math.max(min, Math.min(max, value));
}

export function tokenize(value) {
  return cleanText(value)
    .toLowerCase()
    .split(/[^a-z0-9]+/)
    .filter((token) => token && token.length > 2 && !TOKEN_BLOCKLIST.has(token));
}
