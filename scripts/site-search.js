// Client-side filtering for the site-wide search index page.
function normalize(value) {
  return (value || "").toLowerCase().trim();
}

function applyInitialState(controls) {
  const params = new URLSearchParams(window.location.search);

  if (controls.search && params.has("q")) controls.search.value = params.get("q") || "";
  if (controls.collection && params.has("section")) controls.collection.value = params.get("section") || "all";
  if (controls.format && params.has("type")) controls.format.value = params.get("type") || "all";
  if (controls.topic && params.has("topic")) controls.topic.value = params.get("topic") || "all";
}

function syncUrl(controls) {
  const params = new URLSearchParams(window.location.search);

  const q = normalize(controls.search && controls.search.value);
  if (q) params.set("q", q);
  else params.delete("q");

  if (controls.collection && controls.collection.value !== "all") params.set("section", controls.collection.value);
  else params.delete("section");

  if (controls.format && controls.format.value !== "all") params.set("type", controls.format.value);
  else params.delete("type");

  if (controls.topic && controls.topic.value !== "all") params.set("topic", controls.topic.value);
  else params.delete("topic");

  const query = params.toString();
  const next = `${window.location.pathname}${query ? `?${query}` : ""}${window.location.hash}`;
  window.history.replaceState({}, "", next);
}

function matches(item, controls) {
  const q = normalize(controls.search && controls.search.value);
  const section = controls.collection ? controls.collection.value : "all";
  const format = controls.format ? controls.format.value : "all";
  const topic = controls.topic ? controls.topic.value : "all";

  const haystack = item.dataset.search || "";
  const itemSection = item.dataset.section || "";
  const itemFormat = item.dataset.format || "";
  const itemTopics = item.dataset.topics || "";

  if (q && !haystack.includes(q)) return false;
  if (section !== "all" && section !== itemSection) return false;
  if (format !== "all" && format !== itemFormat) return false;
  if (topic !== "all" && !itemTopics.split("|").includes(topic)) return false;

  return true;
}

function initialize(root) {
  const controls = {
    search: root.querySelector("[data-site-search-input]"),
    collection: root.querySelector("[data-site-search-section]"),
    format: root.querySelector("[data-site-search-type]"),
    topic: root.querySelector("[data-site-search-topic]"),
    count: root.querySelector("[data-site-search-count]"),
    empty: root.querySelector("[data-site-search-empty]"),
  };

  const items = Array.from(root.querySelectorAll("[data-site-item]"));
  if (!items.length) return;

  applyInitialState(controls);

  const apply = () => {
    let visible = 0;

    items.forEach((item) => {
      const matched = matches(item, controls);
      item.hidden = !matched;
      if (matched) visible += 1;
    });

    if (controls.count) controls.count.textContent = String(visible);
    if (controls.empty) controls.empty.hidden = visible !== 0;

    syncUrl(controls);
  };

  [controls.search, controls.collection, controls.format, controls.topic]
    .filter(Boolean)
    .forEach((control) => {
      const eventName = control.tagName === "INPUT" ? "input" : "change";
      control.addEventListener(eventName, apply);
    });

  apply();
}

document.querySelectorAll("[data-site-search-root]").forEach(initialize);
