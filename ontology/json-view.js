// Display exact JSON values as accessible, expandable records. Never interpret strings as markup.
const node = (tag, text, cls) => {
  const el = document.createElement(tag);
  if (text !== undefined) el.textContent = text;
  if (cls) el.className = cls;
  return el;
};
export const fieldLabel = key => String(key).replace(/([a-z])([A-Z])/g, '$1 $2').replace(/[_-]/g, ' ');
export function jsonTree(value, label = 'Record', depth = 0) {
  if (value === null || typeof value !== 'object') {
    const el = node(typeof value === 'string' && value.includes('\n') ? 'pre' : 'span', value === null ? 'null' : String(value), 'json-value json-' + (value === null ? 'null' : typeof value));
    return el;
  }
  const array = Array.isArray(value), entries = Object.entries(value);
  const details = node('details', undefined, 'json-branch');
  details.open = depth < 2;
  const summary = node('summary');
  summary.append(node('strong', fieldLabel(label)), node('span', `${entries.length} ${array ? (entries.length === 1 ? 'item' : 'items') : (entries.length === 1 ? 'field' : 'fields')}`, 'json-count'));
  details.append(summary);
  const list = node('dl', undefined, 'json-fields');
  for (const [key, item] of entries) {
    const row = node('div', undefined, 'json-row');
    let name = array ? String(Number(key) + 1).padStart(2, '0') : fieldLabel(key);
    if (array && item && typeof item === 'object') name += ' · ' + (item.from && item.to ? `${fieldLabel(item.from)} · ${item.label} · ${fieldLabel(item.to)}` : item.title || item.label || item.name || item.resource || (item.specific && item.general ? `${fieldLabel(item.specific)} / ${fieldLabel(item.general)}` : '') || (item.seq ? `Event ${item.seq}: ${item.kind || ''}` : item.id) || 'Record');
    const dt = node('dt', name); dt.title = key;
    const dd = node('dd');
    const empty = item && typeof item === 'object' && Object.keys(item).length === 0;
    dd.append(empty ? node('span', Array.isArray(item) ? '[]' : '{}', 'json-value') : jsonTree(item, name, depth + 1));
    row.append(dt, dd); list.append(row);
  }
  details.append(list);
  return details;
}
export function renderJson(target, value) { target.replaceChildren(jsonTree(value)); }
export function toggleBranches(target, open) { for (const d of target.querySelectorAll('details')) d.open = open; }
