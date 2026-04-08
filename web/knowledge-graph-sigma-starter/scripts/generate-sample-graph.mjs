import fs from 'node:fs/promises';
import path from 'node:path';

const NODE_COUNT = 150;
const COMMUNITY_COUNT = 5;
const nodes = [];
const edges = [];
const colors = ['#4f46e5', '#0ea5e9', '#10b981', '#f59e0b', '#ef4444'];

for (let i = 0; i < NODE_COUNT; i += 1) {
  const community = i % COMMUNITY_COUNT;
  const ring = Math.floor(i / COMMUNITY_COUNT);
  const angle = (2 * Math.PI * ring) / (NODE_COUNT / COMMUNITY_COUNT);
  const radius = 2 + community * 1.3 + Math.random() * 0.4;

  nodes.push({
    id: `node-${i + 1}`,
    label: `Concept ${i + 1}`,
    type: `community-${community + 1}`,
    community: community + 1,
    color: colors[community],
    x: Math.cos(angle) * radius + community * 0.8,
    y: Math.sin(angle) * radius + community * 0.5,
    size: 4 + Math.random() * 3,
    summary: `Example summary for Concept ${i + 1}`,
  });
}

function addEdge(source, target, relation = 'related_to', weight = 1) {
  if (source === target) return;
  const id = `${source}->${target}`;
  if (edges.find((edge) => edge.id === id)) return;
  edges.push({ id, source, target, relation, label: relation, weight, size: 1 });
}

for (let i = 0; i < NODE_COUNT; i += 1) {
  const current = `node-${i + 1}`;
  const next = `node-${((i + 1) % NODE_COUNT) + 1}`;
  addEdge(current, next, 'adjacent_to', 1);

  const sameCommunityPartner = `node-${((i + COMMUNITY_COUNT) % NODE_COUNT) + 1}`;
  addEdge(current, sameCommunityPartner, 'co_occurs_with', 2);

  if (i + 10 < NODE_COUNT) {
    addEdge(current, `node-${i + 11}`, 'references', 1);
  }
}

const output = { nodes, edges };
const outputPath = path.resolve('public/data/sample-graph.json');
await fs.writeFile(outputPath, JSON.stringify(output, null, 2));
console.log(`Wrote ${nodes.length} nodes and ${edges.length} edges to ${outputPath}`);
