import { loadAllData } from "../data-loader.js";
import { computeVisibleGraph, buildNodeIndex } from "../graph.js";
import { html, React, useEffect, useMemo, useState } from "../lib.js";
import { buildPaperRows } from "../papers.js";
import { cleanText } from "../text.js";
import { tokenize } from "../utils.js";
import { ExtraDocsSection } from "./sections/ExtraDocsSection.js";
import { FieldSignalsSection } from "./sections/FieldSignalsSection.js";
import { GraphWorkspaceSection } from "./sections/GraphWorkspaceSection.js";
import { HeroSection } from "./sections/HeroSection.js";
import { PapersSection } from "./sections/PapersSection.js";
import { ResourceNavigatorSection } from "./sections/ResourceNavigatorSection.js";
import { SiteFooter } from "./sections/SiteFooter.js";
import { UpdateWorkflowSection } from "./sections/UpdateWorkflowSection.js";

export function App() {
  const [data, setData] = useState(null);
  const [error, setError] = useState("");

  const [includeHop, setIncludeHop] = useState(false);
  const [search, setSearch] = useState("");
  const [artifactFilter, setArtifactFilter] = useState("all");

  const [resourceQuery, setResourceQuery] = useState("");

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
    if (!data || !data.seedPapers || !data.hopPapers) return [];
    const rows = buildPaperRows(data.seedPapers, data.hopPapers, data.endnotesEnriched);
    const options = new Set();
    for (const paper of rows) {
      for (const artifactType of paper.artifactTypes || []) {
        if (artifactType) options.add(artifactType);
      }
    }
    return [...options].sort((a, b) => a.localeCompare(b));
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

  /** All seed + expansion papers; graph “Include related papers” only affects the graph, not this list. */
  const filteredPapers = useMemo(() => {
    const query = cleanText(search).toLowerCase();

    return paperRows
      .filter((paper) => artifactFilter === "all" || (paper.artifactTypes || []).includes(artifactFilter))
      .filter((paper) => {
        if (!query) return true;
        const idBits = [paper.id, paper.openalex_id, paper.doi, paper.source_url].filter(Boolean).join(" ");
        const haystack = `${paper.title} ${(paper.authors || []).join(" ")} ${paper.citation_plain} ${idBits} ${paper.scope || ""}`
          .toLowerCase()
          .replace(/https?:\/\/openalex\.org\//g, "");
        return haystack.includes(query);
      })
      .sort((a, b) => {
        if (a.scope !== b.scope) return a.scope === "seed" ? -1 : 1;
        return (b.cited_by_count || 0) - (a.cited_by_count || 0);
      });
  }, [artifactFilter, paperRows, search]);

  const filteredResourceRows = useMemo(() => {
    if (!data) return [];
    const query = cleanText(resourceQuery).toLowerCase();
    return (data.resourceRows || []).filter((row) => {
      if (!query) return true;
      const haystack = `${row.section} ${row.title} ${row.context}`.toLowerCase();
      return haystack.includes(query);
    });
  }, [data, resourceQuery]);

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

    if (selectedNode.type === "topic") {
      const topicCode = selectedNode.topic_code || selectedNode.id;
      return filteredPapers.filter((paper) => (paper.topic_codes || []).includes(topicCode)).slice(0, 12);
    }

    if (selectedNode.type === "resource") {
      const selectedResource = filteredResourceRows.find((row) => row.resource_id === selectedNode.id);
      if (!selectedResource) return [];
      const topicSet = new Set(selectedResource.topic_codes || []);
      return filteredPapers.filter((paper) => (paper.topic_codes || []).some((code) => topicSet.has(code))).slice(0, 8);
    }

    const tokens = tokenize(selectedNode.label);
    if (!tokens.length) return [];

    return filteredPapers
      .filter((paper) => {
        const haystack = `${paper.title} ${paper.citation_plain}`.toLowerCase();
        return tokens.some((token) => haystack.includes(token));
      })
      .slice(0, 8);
  }, [filteredPapers, filteredResourceRows, selectedNode]);

  const nodeRelatedResources = useMemo(() => {
    if (!selectedNode) return [];

    if (selectedNode.type === "topic") {
      const topicCode = selectedNode.topic_code || selectedNode.id;
      return filteredResourceRows.filter((row) => (row.topic_codes || []).includes(topicCode)).slice(0, 12);
    }

    if (selectedNode.type === "paper") {
      const selectedPaper = filteredPapers.find((paper) => paper.id === selectedNode.id);
      if (!selectedPaper) return [];
      const topicSet = new Set(selectedPaper.topic_codes || []);
      return filteredResourceRows.filter((row) => (row.topic_codes || []).some((code) => topicSet.has(code))).slice(0, 8);
    }

    if (selectedNode.type === "resource") {
      return filteredResourceRows.filter((row) => row.resource_id === selectedNode.id).slice(0, 1);
    }

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
    const cards = (data.gaps.gaps || []).map((gap) => {
      const severity = gap.evidence?.severity ? `Severity: ${gap.evidence.severity}. ` : "";
      return {
        id: gap.id,
        title: gap.evidence?.topic ? `${gap.evidence.topic} Coverage Gap` : gap.label,
        body: `${severity}${gap.detail || gap.label}`,
        links: gap.evidence_links || [],
      };
    });

    const topicCodes = (data.topicMap?.topics || []).map((topic) => topic.topic_code);
    const resourceCoverage = new Map(topicCodes.map((code) => [code, 0]));
    for (const row of data.resourceRows || []) {
      for (const code of row.topic_codes || []) {
        resourceCoverage.set(code, (resourceCoverage.get(code) || 0) + 1);
      }
    }
    const missingResourceTopics = topicCodes.filter((code) => (resourceCoverage.get(code) || 0) === 0);
    const missingAbstracts = paperRows.filter((paper) => paper.abstractQA?.missing).length;
    const proxyAbstracts = paperRows.filter((paper) => paper.abstractQA?.proxy).length;

    cards.unshift({
      id: "abstract_coverage",
      title: "Abstract Metadata Coverage",
      body:
        missingAbstracts === 0
          ? `All papers currently include abstract text. ${proxyAbstracts} records are explicitly marked as proxy descriptions (not source abstracts).`
          : `${missingAbstracts} papers currently lack abstract text, and ${proxyAbstracts} are proxy descriptions. This is expected for some book and policy records.`,
      links: [],
    });
    cards.unshift({
      id: "topic_resource_coverage",
      title: "Topic-to-Resource Coverage",
      body:
        missingResourceTopics.length === 0
          ? "Every topic currently has at least one non-paper resource."
          : `Topics missing non-paper resources: ${missingResourceTopics.join(", ")}.`,
      links: [],
    });
    return cards;
  }, [data, paperRows]);

  const stats = useMemo(() => {
    if (!data) return [];

    return [
      ["Topics", data.topicMap?.count || 0],
      ["Source Endnotes", data.summary.parsed_endnotes],
      ["Linked Endnotes", data.summary.matched_endnotes],
      ["Core Papers", data.summary.seed_papers],
      ["Related Papers", data.summary.one_hop_papers],
      ["Field Resources", data.summary.icicle_resource_items],
      ["Graph Nodes", data.summary.graph_nodes],
      ["Graph Edges", data.summary.graph_edges],
      ["Supporting Docs", data.extraDocs.count || 0],
    ];
  }, [data]);

  const dataQuality = useMemo(() => {
    const missingAbstractCount = paperRows.filter((paper) => paper.abstractQA?.missing).length;
    const proxyAbstractCount = paperRows.filter((paper) => paper.abstractQA?.proxy).length;
    const shortTitleCount = paperRows.filter(
      (paper) => (paper.title || "").trim().length < 12 || (paper.title || "").trim().toLowerCase() === "untitled"
    ).length;
    const topicCodes = new Set((data?.topicMap?.topics || []).map((topic) => topic.topic_code));
    const covered = new Set();
    for (const row of data?.resourceRows || []) {
      for (const code of row.topic_codes || []) {
        if (topicCodes.has(code)) covered.add(code);
      }
    }
    const missingResourceTopicCodes = [...topicCodes].filter((code) => !covered.has(code));
    return {
      missingAbstractCount,
      proxyAbstractCount,
      shortTitleCount,
      missingResourceTopicCount: missingResourceTopicCodes.length,
      missingResourceTopicCodes,
    };
  }, [data, paperRows]);

  const topicPaperClusters = useMemo(() => {
    const topicNameByCode = new Map((data?.topicMap?.topics || []).map((topic) => [topic.topic_code, topic.topic_name]));
    const topicOrder = new Map((data?.topicMap?.topics || []).map((topic, index) => [topic.topic_code, index]));
    const byTopic = new Map();

    for (const paper of filteredPapers) {
      const topicCodes = paper.topic_codes?.length ? paper.topic_codes : ["unmapped"];

      for (const topicCode of topicCodes) {
        const key = topicCode === "unmapped" ? "unmapped" : `topic-${topicCode}`;
        if (!byTopic.has(key)) {
          const label =
            topicCode === "unmapped"
              ? "Unmapped / Cross-Cutting"
              : `${topicCode} ${topicNameByCode.get(topicCode) || "Unknown Topic"}`;
          byTopic.set(key, {
            key,
            topicCode,
            label,
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
        if (a.topicCode === "unmapped") return 1;
        if (b.topicCode === "unmapped") return -1;
        return (topicOrder.get(a.topicCode) ?? Number.MAX_SAFE_INTEGER) - (topicOrder.get(b.topicCode) ?? Number.MAX_SAFE_INTEGER);
      });
  }, [data, filteredPapers]);

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

        <${ResourceNavigatorSection}
          filteredResourceRows=${filteredResourceRows}
          resourceQuery=${resourceQuery}
          setResourceQuery=${setResourceQuery}
        />

        <${PapersSection}
          search=${search}
          setSearch=${setSearch}
          artifactFilter=${artifactFilter}
          setArtifactFilter=${setArtifactFilter}
          artifactOptions=${artifactOptions}
          filteredPapers=${filteredPapers}
          topicPaperClusters=${topicPaperClusters}
          dataQuality=${dataQuality}
        />

        <${FieldSignalsSection} signalCards=${signalCards} />
        <${ExtraDocsSection} extraDocs=${data.extraDocs} />
        <${UpdateWorkflowSection} />
        <${SiteFooter} />
      </main>
    <//>
  `;
}
