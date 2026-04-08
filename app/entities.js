import { ORG_RE, PERSON_BLOCKLIST, PERSON_RE } from "./constants.js";
import { normalizeKey } from "./resources.js";
import { cleanText } from "./text.js";

function extractEntitiesFromText(text) {
  const cleaned = cleanText(text);
  const people = [];
  const organizations = [];

  for (const match of cleaned.matchAll(PERSON_RE)) {
    const name = cleanText(match[1]);
    if (!name || PERSON_BLOCKLIST.has(name) || /\d/.test(name)) continue;
    const wordCount = name.split(" ").length;
    if (wordCount < 2 || wordCount > 3) continue;
    people.push(name);
  }

  for (const match of cleaned.matchAll(ORG_RE)) {
    const organization = cleanText(match[1]);
    if (!organization || /\d/.test(organization)) continue;
    organizations.push(organization);
  }

  return {
    people: [...new Set(people)],
    organizations: [...new Set(organizations)],
  };
}

export function enrichResourceEntities(resourceRows) {
  return resourceRows.map((row) => {
    const entities = extractEntitiesFromText(`${row.title} ${row.context}`);

    return {
      ...row,
      people: entities.people,
      organizations: entities.organizations,
      entityKeys: [...entities.people, ...entities.organizations].map((name) => normalizeKey(name)),
    };
  });
}

export function buildEntityDirectory(resourceRows, programs) {
  const entityMap = new Map();

  function upsertEntity(name, type, resourceKeys = []) {
    const cleaned = cleanText(name);
    if (!cleaned) return;

    const key = normalizeKey(cleaned);
    if (!key) return;

    if (!entityMap.has(key)) {
      entityMap.set(key, {
        key,
        name: cleaned,
        type,
        count: 0,
        resourceKeys: new Set(),
      });
    }

    const entity = entityMap.get(key);
    entity.count += 1;
    for (const resourceKey of resourceKeys) {
      entity.resourceKeys.add(resourceKey);
    }
  }

  for (const row of resourceRows) {
    for (const person of row.people || []) {
      upsertEntity(person, "person", [row.key]);
    }
    for (const organization of row.organizations || []) {
      upsertEntity(organization, "organization", [row.key]);
    }
  }

  for (const program of programs) {
    upsertEntity(program.name.replace(/\([^)]*\)/g, "").trim(), "organization");
  }

  return [...entityMap.values()]
    .filter((entity) => entity.count >= 2 || entity.type === "organization")
    .map((entity) => ({
      key: entity.key,
      name: entity.name,
      type: entity.type,
      count: entity.count,
      resourceKeys: [...entity.resourceKeys],
    }))
    .sort((a, b) => {
      if (a.type !== b.type) return a.type === "organization" ? -1 : 1;
      if (b.count !== a.count) return b.count - a.count;
      return a.name.localeCompare(b.name);
    })
    .slice(0, 60);
}
