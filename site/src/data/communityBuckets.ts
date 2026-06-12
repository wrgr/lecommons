// Shared community bucketing and sorting rules so all community pages stay aligned.
import type { CollectionEntry } from "astro:content";

export type CommEntry = CollectionEntry<"community">;
export type EventEntry = CollectionEntry<"events">;

const STUDY_GROUP_KEYWORDS = [
  " sig", " mig", "working group", "community", "incubator",
  "learnlab", "consortium", "initiative", "lab ",
];

const INST_PRIORITY: Record<string, number> = {
  "IEEE ICICLE": 1,
  "Carnegie Mellon University": 2,
  "Johns Hopkins University": 3,
  "Arizona State University": 4,
  "Massachusetts Institute of Technology": 5,
};

export function isStudyGroup(entry: CommEntry): boolean {
  const name = entry.data.title.toLowerCase();
  if (entry.data.format !== "org" && entry.data.format !== "program") return false;
  if (name.includes("sigs & migs") || name.includes(" sig") || name.includes(" mig")) return true;
  return STUDY_GROUP_KEYWORDS.some((k) => name.includes(k));
}

export function isConferenceFromCommunity(entry: CommEntry): boolean {
  const name = entry.data.title.toLowerCase();
  return (
    entry.data.format === "event" ||
    name.includes("conference") ||
    name.includes("summit") ||
    name.includes("annual meeting") ||
    name.includes("i/itsec")
  );
}

export function partitionCommunity(entries: CommEntry[]): {
  study: CommEntry[];
  conferencesFromCommunity: CommEntry[];
  institutions: CommEntry[];
  people: CommEntry[];
} {
  const study: CommEntry[] = [];
  const conferencesFromCommunity: CommEntry[] = [];
  const institutions: CommEntry[] = [];
  const people: CommEntry[] = [];

  for (const entry of entries) {
    if (entry.data.format === "person") {
      people.push(entry);
      continue;
    }
    if (isConferenceFromCommunity(entry)) {
      conferencesFromCommunity.push(entry);
      continue;
    }
    if (isStudyGroup(entry)) {
      study.push(entry);
      continue;
    }
    institutions.push(entry);
  }

  return {
    study: sortStudy(study),
    conferencesFromCommunity: sortAlpha(conferencesFromCommunity),
    institutions: sortInstitutions(institutions),
    people: sortAlpha(people),
  };
}

export function conferenceEvents(entries: EventEntry[]): EventEntry[] {
  const selected = entries.filter(
    (entry) => entry.data.format === "conference" || entry.data.format === "series",
  );
  return sortAlpha(selected);
}

function sortAlpha<T extends CommEntry | EventEntry>(entries: T[]): T[] {
  return entries.slice().sort((a, b) => a.data.title.localeCompare(b.data.title));
}

function sortStudy(entries: CommEntry[]): CommEntry[] {
  return sortAlpha(entries);
}

function sortInstitutions(entries: CommEntry[]): CommEntry[] {
  return entries.slice().sort((a, b) => {
    const ap = INST_PRIORITY[a.data.title] ?? (a.data.format === "institution" ? 10 : 20);
    const bp = INST_PRIORITY[b.data.title] ?? (b.data.format === "institution" ? 10 : 20);
    return ap - bp || a.data.title.localeCompare(b.data.title);
  });
}
