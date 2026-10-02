// Client-side filters for community hub and subpages.
function normalize(value) {
  return (value || "").toLowerCase().trim();
}

function applyInitialUrlState(controls) {
  const params = new URLSearchParams(window.location.search);

  if (controls.search && params.has("q")) {
    controls.search.value = params.get("q") || "";
  }
  if (controls.group && params.has("group")) {
    controls.group.value = params.get("group") || "all";
  }
  if (controls.type && params.has("type")) {
    controls.type.value = params.get("type") || "all";
  }
  if (controls.topic && params.has("topic")) {
    controls.topic.value = params.get("topic") || "all";
  }
  if (controls.knownSource && params.get("known") === "1") {
    controls.knownSource.checked = true;
  }
}

function syncUrl(controls) {
  const params = new URLSearchParams(window.location.search);

  const q = normalize(controls.search && controls.search.value);
  if (q) params.set("q", q);
  else params.delete("q");

  if (controls.group && controls.group.value !== "all") params.set("group", controls.group.value);
  else params.delete("group");

  if (controls.type && controls.type.value !== "all") params.set("type", controls.type.value);
  else params.delete("type");

  if (controls.topic && controls.topic.value !== "all") params.set("topic", controls.topic.value);
  else params.delete("topic");

  if (controls.knownSource && controls.knownSource.checked) params.set("known", "1");
  else params.delete("known");

  const query = params.toString();
  const next = `${window.location.pathname}${query ? `?${query}` : ""}${window.location.hash}`;
  window.history.replaceState({}, "", next);
}

function itemMatches(item, controls) {
  const q = normalize(controls.search && controls.search.value);
  const group = controls.group ? controls.group.value : "all";
  const type = controls.type ? controls.type.value : "all";
  const topic = controls.topic ? controls.topic.value : "all";
  const knownOnly = controls.knownSource ? controls.knownSource.checked : false;

  const haystack = item.dataset.search || "";
  const itemGroup = item.dataset.group || "";
  const itemType = item.dataset.format || "";
  const topics = item.dataset.topics || "";
  const missing = item.dataset.missing === "true";

  if (q && !haystack.includes(q)) return false;
  if (group !== "all" && group !== itemGroup) return false;
  if (type !== "all" && type !== itemType) return false;
  if (topic !== "all" && !topics.split("|").includes(topic)) return false;
  if (knownOnly && missing) return false;

  return true;
}

function updateSections(root) {
  const sections = root.querySelectorAll("[data-community-section]");
  sections.forEach((section) => {
    const total = Number(section.getAttribute("data-section-total") || "0");
    const visible = section.querySelectorAll("[data-community-item]:not([hidden])").length;
    section.hidden = visible === 0;

    const countEl = section.querySelector("[data-section-count]");
    if (!countEl) return;
    countEl.textContent = visible === total ? `(${total})` : `(${visible}/${total})`;
  });
}

function initializeRoot(root) {
  const controls = {
    search: root.querySelector("[data-filter-search]"),
    group: root.querySelector("[data-filter-group]"),
    type: root.querySelector("[data-filter-type]"),
    topic: root.querySelector("[data-filter-topic]"),
    knownSource: root.querySelector("[data-filter-known-source]"),
    count: root.querySelector("[data-filter-count]"),
    empty: root.querySelector("[data-filter-empty]"),
  };

  const items = Array.from(root.querySelectorAll("[data-community-item]"));
  if (!items.length) return;

  applyInitialUrlState(controls);

  const apply = () => {
    let shown = 0;

    items.forEach((item) => {
      const match = itemMatches(item, controls);
      item.hidden = !match;
      if (match) shown += 1;
    });

    updateSections(root);

    if (controls.count) controls.count.textContent = String(shown);
    if (controls.empty) controls.empty.hidden = shown !== 0;

    syncUrl(controls);
  };

  [controls.search, controls.group, controls.type, controls.topic, controls.knownSource]
    .filter(Boolean)
    .forEach((control) => {
      const eventName = control.tagName === "INPUT" && control.type === "search" ? "input" : "change";
      control.addEventListener(eventName, apply);
    });

  apply();
}

document.querySelectorAll("[data-community-filter-root]").forEach(initializeRoot);
