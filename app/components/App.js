import { RESOURCE_GROUP_ORDER } from "../constants.js";
import { loadAllData } from "../data-loader.js";
import { computeVisibleGraph, buildNodeIndex } from "../graph.js";
import { html, React, useEffect, useMemo, useState } from "../lib.js";
import { buildPaperRows } from "../papers.js";
import { cleanText } from "../text.js";
import { groupBy, tokenize } from "../utils.js";
import { ExtraDocsSection } from "./sections/ExtraDocsSection.js";
import { FieldSignalsSection } from "./sections/FieldSignalsSection.js";
import { GraphWorkspaceSection } from "./sections/GraphWorkspaceSection.js";
import { HeroSection } from "./sections/HeroSection.js";
import { PapersSection } from "./sections/PapersSection.js";
import { ProgramsSection } from "./sections/ProgramsSection.js";
import { ResourceNavigatorSection } from "./sections/ResourceNavigatorSection.js";
import { UpdateWorkflowSection } from "./sections/UpdateWorkflowSection.js";

export function App() {
  const [data, setData] = useState(null);
  const [error, setError] = useState("");

  const [includeHop, setIncludeHop] = useState(false);
  const [search, setSearch] = useState("");
  const [artifactFilter, setArtifactFilter] = useState("all");

  const [resourceQuery, setResourceQuery] = useState("");
  const [activeEntities, setActiveEntities] = useState([]);

  const [selectedNodeId, setSelectedNodeId] = useState("");

  useEffect(() => {
    let mounted = true;

    loadAllData()
      .then((nextData) => {
        if (!mounted) return;
        setData(nextData);
      })
      .catch((loadError) => {
        if (!mounted) return;
        setError(String(loadError));
      });

    return () => {
      mounted = false;
    };
  }, []);

  const artifactOptions = useMemo(() => {
    if (!data) return [];
    const options = new Set((data.endnotesRaw.notes || []).map((note) => note.artifact_type));
    options.add("derived_one_hop");
    return [...options].filter(Boolean).sort((a, b) => a.localeCompare(b));
  }, [data]);

  const paperRows = useMemo(() => {
    if (!data) return [];
    return buildPaperRows(data.seedPapers, data.hopPapers, data.endnotesEnriched);
  }, [data]);

  const visibleGraph = useMemo(() => {
    if (!data) return { nodes: [], links: [] };
    return computeVisibleGraph(data.graph, includeHop);
  }, [data, includeHop]);

  const nodeIndex = useMemo(() => buildNodeIndex(visibleGraph), [visibleGraph]);

  useEffect(() => {
    if (!visibleGraph.nodes.length) return;
    const found = visibleGraph.nodes.some((node) => node.id === selectedNodeId);
    if (!found) {
      setSelectedNodeId(visibleGraph.nodes[0].id);
    }
  }, [selectedNodeId, visibleGraph]);

  const selectedNode = useMemo(() => nodeIndex.nodeMap.get(selectedNodeId) || null, [nodeIndex, selectedNodeId]);

  const filteredPapers = useMemo(() => {
    const query = cleanText(search).toLowerCase();

    return paperRows
      .filter((paper) => includeHop || paper.scope === "seed")
      .filter((paper) => artifactFilter === "all" || paper.artifactTypes.includes(artifactFilter))
      .filter((paper) => {
        if (!query) return true;
        const haystack = `${paper.title} ${(paper.authors || []).join(" ")} ${paper.citation_plain}`.toLowerCase();
        return haystack.includes(query);
      })
      .sort((a, b) => {
        if (a.scope !== b.scope) return a.scope === "seed" ? -1 : 1;
        return (b.cited_by_count || 0) - (a.cited_by_count || 0);
      });
  }, [artifactFilter, includeHop, paperRows, search]);

  const filteredResourceRows = useMemo(() => {
    if (!data) return [];

    const query = cleanText(resourceQuery).toLowerCase();
    const activeSet = new Set(activeEntities);

    return (data.resourceRows || []).filter((row) => {
      if (query) {
        const haystack = `${row.section} ${row.title} ${row.context}`.toLowerCase();
        if (!haystack.includes(query)) return false;
      }

      if (activeSet.size) {
        const matches = row.entityKeys.some((key) => activeSet.has(key));
        if (!matches) return false;
      }

      return true;
    });
  }, [activeEntities, data, resourceQuery]);

  const groupedResources = useMemo(() => {
    const grouped = groupBy(filteredResourceRows, (row) => row.group);
    return RESOURCE_GROUP_ORDER.filter((group) => grouped[group]?.length).map((group) => ({
      group,
      rows: grouped[group],
    }));
  }, [filteredResourceRows]);

  const citationContext = useMemo(() => {
    if (!selectedNode) return { incoming: [], outgoing: [] };

    const incoming = (nodeIndex.incoming.get(selectedNode.id) || []).map((edge) => ({
      edge,
      node: nodeIndex.nodeMap.get(edge.source),
    }));

    const outgoing = (nodeIndex.outgoing.get(selectedNode.id) || []).map((edge) => ({
      edge,
      node: nodeIndex.nodeMap.get(edge.target),
    }));

    return {
      incoming: incoming.filter((item) => item.node),
      outgoing: outgoing.filter((item) => item.node),
    };
  }, [nodeIndex, selectedNode]);

  const nodeRelatedPapers = useMemo(() => {
    if (!selectedNode) return [];

    if (selectedNode.type === "paper") {
      return filteredPapers.filter((paper) => paper.id === selectedNode.id).slice(0, 1);
    }

    const chapter = Number(selectedNode.chapter);
    if (Number.isFinite(chapter) && chapter > 0) {
      return filteredPapers.filter((paper) => (paper.chapters || []).includes(chapter)).slice(0, 8);
    }

    const tokens = tokenize(selectedNode.label);
    if (!tokens.length) return [];

    return filteredPapers
      .filter((paper) => {
        const haystack = `${paper.title} ${paper.citation_plain}`.toLowerCase();
        return tokens.some((token) => haystack.includes(token));
      })
      .slice(0, 8);
  }, [filteredPapers, selectedNode]);

  const nodeRelatedResources = useMemo(() => {
    if (!selectedNode) return [];

    const tokens = tokenize(selectedNode.label);
    if (!tokens.length) return [];

    return filteredResourceRows
      .filter((row) => {
        const haystack = `${row.title} ${row.context} ${row.section}`.toLowerCase();
        return tokens.some((token) => haystack.includes(token));
      })
      .slice(0, 8);
  }, [filteredResourceRows, selectedNode]);

  const signalCards = useMemo(() => {
    if (!data) return [];

    const labels = {
      missing_metadata_coverage: {
        title: "Citation Metadata Coverage",
        body: "Coverage remains uneven across heterogeneous artifact types. Continue DOI-first matching and incremental verification for non-DOI records.",
      },
      role_based_navigation: {
        title: "Role-Based Pathways",
        body: "Role-oriented pathways are visible across ICICLE pages (SIGs/MIGs, meetings, and audience-specific tracks).",
      },
      reproducible_assets: {
        title: "Reusable Technical Assets",
        body: "Templates and checklists are present. Reusable data/API/code assets should be expanded for stronger replication and operational adoption.",
      },
    };

    return (data.gaps.gaps || []).map((gap) => ({
      id: gap.id,
      title: labels[gap.id]?.title || gap.label,
      body: labels[gap.id]?.body || gap.detail,
      links: gap.evidence_links || [],
    }));
  }, [data]);

  const stats = useMemo(() => {
    if (!data) return [];

    return [
      ["Parsed Endnotes", data.summary.parsed_endnotes],
      ["Matched Seed Links", data.summary.matched_endnotes],
      ["Seed Papers", data.summary.seed_papers],
      ["One-Hop Papers", data.summary.one_hop_papers],
      ["Resource Items", data.summary.icicle_resource_items],
      ["Graph Nodes", data.summary.graph_nodes],
      ["Graph Edges", data.summary.graph_edges],
      ["External Docs", data.extraDocs.count || 0],
    ];
  }, [data]);

  const topicPaperClusters = useMemo(() => {
    const byTopic = new Map();

    for (const paper of filteredPapers) {
      const chapters = paper.chapters?.length ? paper.chapters : ["unmapped"];

      for (const chapter of chapters) {
        const key = chapter === "unmapped" ? "unmapped" : `chapter-${chapter}`;
        if (!byTopic.has(key)) {
          byTopic.set(key, {
            key,
            chapter,
            label: chapter === "unmapped" ? "Unmapped / Cross-Cutting" : `Chapter ${chapter}`,
            papers: [],
          });
        }

        byTopic.get(key).papers.push(paper);
      }
    }

    return [...byTopic.values()]
      .map((cluster) => {
        const deduped = [...new Map(cluster.papers.map((paper) => [paper.id, paper])).values()].sort(
          (a, b) => (b.cited_by_count || 0) - (a.cited_by_count || 0)
        );

        return {
          ...cluster,
          papers: deduped,
        };
      })
      .sort((a, b) => {
        if (a.chapter === "unmapped") return 1;
        if (b.chapter === "unmapped") return -1;
        return Number(a.chapter) - Number(b.chapter);
      });
  }, [filteredPapers]);

  const groupedPrograms = useMemo(() => {
    if (!data) return {};
    return groupBy(data.programs, (program) => program.category || "other");
  }, [data]);

  const toggleEntity = (key) => {
    setActiveEntities((previous) =>
      previous.includes(key) ? previous.filter((item) => item !== key) : [...previous, key]
    );
  };

  if (error) {
    return html`
      <main className="wrap app-shell">
        <section className="panel">
          <h1>Failed to load data</h1>
          <pre>${error}</pre>
        </section>
      </main>
    `;
  }

  if (!data) {
    return html`
      <main className="wrap app-shell">
        <section className="panel loading-panel">
          <p>Loading learning engineering workspace...</p>
        </section>
      </main>
    `;
  }

  return html`
    <${React.Fragment}>
      <${HeroSection} stats=${stats} />

      <main className="wrap app-shell">
        <${GraphWorkspaceSection}
          includeHop=${includeHop}
          setIncludeHop=${setIncludeHop}
          visibleGraph=${visibleGraph}
          selectedNodeId=${selectedNodeId}
          setSelectedNodeId=${setSelectedNodeId}
          selectedNode=${selectedNode}
          citationContext=${citationContext}
          nodeRelatedPapers=${nodeRelatedPapers}
          nodeRelatedResources=${nodeRelatedResources}
        />

        <${ProgramsSection} groupedPrograms=${groupedPrograms} />

        <${ResourceNavigatorSection}
          groupedResources=${groupedResources}
          filteredResourceRows=${filteredResourceRows}
          entities=${data.entities}
          activeEntities=${activeEntities}
          toggleEntity=${toggleEntity}
          resourceQuery=${resourceQuery}
          setResourceQuery=${setResourceQuery}
          clearEntities=${() => setActiveEntities([])}
        />

        <${PapersSection}
          search=${search}
          setSearch=${setSearch}
          artifactFilter=${artifactFilter}
          setArtifactFilter=${setArtifactFilter}
          artifactOptions=${artifactOptions}
          filteredPapers=${filteredPapers}
          topicPaperClusters=${topicPaperClusters}
        />

        <${FieldSignalsSection} signalCards=${signalCards} />
        <${ExtraDocsSection} extraDocs=${data.extraDocs} />
        <${UpdateWorkflowSection} />
      </main>
    <//>
  `;
}
