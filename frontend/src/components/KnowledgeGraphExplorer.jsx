import React, { useState, useEffect, useMemo, useRef } from "react";

const BACKEND_URL = "http://localhost:8000";

const TYPE_COLORS = {
  DOCUMENT: "#3b82f6",
  PAGE: "#06b6d4",
  SECTION: "#6366f1",
  PARAGRAPH: "#10b981",
  TABLE: "#f59e0b",
  IMAGE: "#ec4899",
  ENTITY: "#8b5cf6",
  TEXT: "#14b8a6",
  DEFAULT: "#64748b"
};

export default function KnowledgeGraphExplorer({ token, initialEntity, onSelectEntity, onOpenDocument }) {
  const [graphData, setGraphData] = useState({ nodes: [], edges: [] });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  
  // Natural-Language Graph Query State
  const [nlQuery, setNlQuery] = useState("");
  const [nlLoading, setNlLoading] = useState(false);
  const [nlResult, setNlResult] = useState(null);
  
  // Selection and navigation
  const [selectedNodeId, setSelectedNodeId] = useState(null);
  const [selectedNodeDetails, setSelectedNodeDetails] = useState(null);
  const [nodeParents, setNodeParents] = useState([]);
  const [nodeChildren, setNodeChildren] = useState([]);
  const [nodeNeighbors, setNodeNeighbors] = useState([]);
  const [loadingNeighbors, setLoadingNeighbors] = useState(false);

  // Filters & search
  const [searchTerm, setSearchTerm] = useState("");
  const [typeFilter, setTypeFilter] = useState("ALL");
  const [viewMode, setViewMode] = useState("canvas"); // 'canvas' | 'directory'

  // Reasoning Path tool
  const [pathTargetId, setPathTargetId] = useState("");
  const [reasoningPath, setReasoningPath] = useState(null);
  const [pathLoading, setPathLoading] = useState(false);

  const fetchWithAuth = async (url) => {
    return fetch(url, {
      headers: {
        Authorization: `Bearer ${token}`
      }
    });
  };

  const loadGraph = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetchWithAuth(`${BACKEND_URL}/api/graph/visualize`);
      if (!res.ok) {
        throw new Error(`Failed to fetch knowledge graph (${res.status})`);
      }
      const data = await res.json();
      setGraphData({
        nodes: data.nodes || [],
        edges: data.edges || []
      });
      if (data.nodes && data.nodes.length > 0 && !selectedNodeId) {
        selectNode(data.nodes[0].id);
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadGraph();
  }, [token]);

  useEffect(() => {
    if (initialEntity) {
      setSearchTerm(initialEntity);
    }
  }, [initialEntity]);

  const handleNlGraphQuery = async (e) => {
    if (e) e.preventDefault();
    if (!nlQuery.trim()) return;
    setNlLoading(true);
    try {
      const res = await fetch(`${BACKEND_URL}/api/graph/query`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(token ? { Authorization: `Bearer ${token}` } : {})
        },
        body: JSON.stringify({ query: nlQuery.trim() })
      });
      if (res.ok) {
        const data = await res.json();
        setNlResult(data);
      }
    } catch (err) {
      console.error("NL graph query error:", err);
    } finally {
      setNlLoading(false);
    }
  };

  const selectNode = async (nodeId) => {
    setSelectedNodeId(nodeId);
    setReasoningPath(null);
    setLoadingNeighbors(true);
    try {
      // 1. Fetch node full details
      const nodeRes = await fetchWithAuth(`${BACKEND_URL}/api/graph/nodes/${nodeId}`);
      if (nodeRes.ok) {
        const node = await nodeRes.json();
        setSelectedNodeDetails(node);
      }

      // 2. Fetch parents
      const pRes = await fetchWithAuth(`${BACKEND_URL}/api/graph/nodes/${nodeId}/parents`);
      if (pRes.ok) {
        const parents = await pRes.json();
        setNodeParents(parents);
      }

      // 3. Fetch children
      const cRes = await fetchWithAuth(`${BACKEND_URL}/api/graph/nodes/${nodeId}/children`);
      if (cRes.ok) {
        const children = await cRes.json();
        setNodeChildren(children);
      }

      // 4. Fetch neighbors
      const nRes = await fetchWithAuth(`${BACKEND_URL}/api/graph/nodes/${nodeId}/neighbors?depth=1`);
      if (nRes.ok) {
        const neighbors = await nRes.json();
        setNodeNeighbors(neighbors);
      }
    } catch (e) {
      console.error("Error loading node details:", e);
    } finally {
      setLoadingNeighbors(false);
    }
  };

  const handleFindPath = async () => {
    if (!selectedNodeId || !pathTargetId) return;
    setPathLoading(true);
    setReasoningPath(null);
    try {
      const res = await fetchWithAuth(
        `${BACKEND_URL}/api/graph/reason?source_id=${selectedNodeId}&target_id=${pathTargetId}&max_depth=3`
      );
      if (res.ok) {
        const data = await res.json();
        setReasoningPath(data.path || []);
      } else {
        setReasoningPath([]);
      }
    } catch (e) {
      console.error(e);
      setReasoningPath([]);
    } finally {
      setPathLoading(false);
    }
  };

  // Filtered nodes
  const filteredNodes = useMemo(() => {
    return graphData.nodes.filter((node) => {
      const matchesType =
        typeFilter === "ALL" ||
        (node.object_type || "").toUpperCase() === typeFilter.toUpperCase();
      const query = searchTerm.toLowerCase();
      const matchesSearch =
        !query ||
        (node.id || "").toLowerCase().includes(query) ||
        (node.content || "").toLowerCase().includes(query) ||
        (node.document_filename || "").toLowerCase().includes(query);
      return matchesType && matchesSearch;
    });
  }, [graphData.nodes, typeFilter, searchTerm]);

  // Types list for filter pills
  const availableTypes = useMemo(() => {
    const types = new Set(graphData.nodes.map((n) => (n.object_type || "UNKNOWN").toUpperCase()));
    return ["ALL", ...Array.from(types)];
  }, [graphData.nodes]);

  // Compute node positions for SVG canvas
  const svgLayout = useMemo(() => {
    const width = 800;
    const height = 500;
    const centerX = width / 2;
    const centerY = height / 2;
    const nodes = filteredNodes.slice(0, 80); // Cap at 80 nodes on canvas for clean layout
    const positions = {};

    if (nodes.length === 0) return { positions, edges: [] };

    // Arrange nodes in circular orbits grouped by document/type
    const count = nodes.length;
    nodes.forEach((node, i) => {
      const radius = count > 20 ? 120 + ((i % 3) * 80) : 160;
      const angle = (i / count) * 2 * Math.PI;
      positions[node.id] = {
        x: centerX + radius * Math.cos(angle),
        y: centerY + radius * Math.sin(angle),
        node
      };
    });

    const activeIds = new Set(nodes.map((n) => n.id));
    const edges = graphData.edges.filter(
      (e) => activeIds.has(e.source_id) && activeIds.has(e.target_id)
    );

    return { positions, edges, width, height };
  }, [filteredNodes, graphData.edges]);

  const activeNode = selectedNodeDetails || graphData.nodes.find((n) => n.id === selectedNodeId);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
      {/* Top Metrics Bar */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: "16px" }}>
        <div className="metric-card" style={{ padding: "16px" }}>
          <h4 className="metric-title">Authorized Nodes</h4>
          <div className="metric-value">{graphData.nodes.length}</div>
        </div>
        <div className="metric-card" style={{ padding: "16px" }}>
          <h4 className="metric-title">Relationship Edges</h4>
          <div className="metric-value">{graphData.edges.length}</div>
        </div>
        <div className="metric-card" style={{ padding: "16px" }}>
          <h4 className="metric-title">Filtered Nodes</h4>
          <div className="metric-value">{filteredNodes.length}</div>
        </div>
        <div className="metric-card" style={{ padding: "16px" }}>
          <h4 className="metric-title">Canonical Engine</h4>
          <div style={{ fontSize: "16px", fontWeight: "600", color: "var(--color-accent)", marginTop: "4px" }}>
            SQLite + BFS Reasoner
          </div>
        </div>
      </div>

      {/* Natural-Language Graph Query Interface */}
      <div className="panel" style={{ padding: "16px 20px" }}>
        <form onSubmit={handleNlGraphQuery} style={{ display: "flex", gap: "10px", alignItems: "center" }}>
          <span style={{ fontSize: "18px" }}>💬</span>
          <input
            type="text"
            className="input-box"
            placeholder="Ask a natural-language graph query (e.g. 'What entities connect to Project Alpha?' or 'Show organizations linked to top secret records')..."
            value={nlQuery}
            onChange={(e) => setNlQuery(e.target.value)}
            style={{ flex: 1, padding: "10px 14px", fontSize: "13px" }}
          />
          <button
            type="submit"
            className="btn btn-primary"
            disabled={nlLoading || !nlQuery.trim()}
            style={{ padding: "10px 18px", fontSize: "13px" }}
          >
            {nlLoading ? "Querying..." : "Query Graph"}
          </button>
        </form>

        {nlResult && (
          <div style={{ marginTop: "12px", padding: "12px 16px", background: "rgba(99, 102, 241, 0.05)", border: "1px solid var(--border-glass)", borderRadius: "8px" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "6px" }}>
              <span style={{ fontSize: "12px", fontWeight: "700", color: "var(--color-accent)" }}>
                Graph Query Synthesis
              </span>
              <button
                onClick={() => setNlResult(null)}
                style={{ background: "none", border: "none", fontSize: "14px", cursor: "pointer", color: "var(--text-muted)" }}
              >
                ×
              </button>
            </div>
            <p style={{ fontSize: "13px", color: "var(--text-main)", margin: 0, lineHeight: "1.5" }}>
              {nlResult.answer || nlResult.summary || "No textual answer generated."}
            </p>
            {nlResult.entities && nlResult.entities.length > 0 && (
              <div style={{ display: "flex", gap: "6px", flexWrap: "wrap", marginTop: "8px" }}>
                <span style={{ fontSize: "11px", color: "var(--text-muted)" }}>Target Entities:</span>
                {nlResult.entities.map((e, idx) => (
                  <button
                    key={idx}
                    type="button"
                    onClick={() => {
                      const name = e.name || e;
                      setSearchTerm(name);
                      if (onSelectEntity) onSelectEntity(name);
                    }}
                    style={{
                      fontSize: "11px", padding: "2px 8px", borderRadius: "4px",
                      background: "var(--bg-sidebar)", border: "1px solid var(--border-glass)",
                      color: "var(--color-accent)", cursor: "pointer"
                    }}
                  >
                    {e.name || e}
                  </button>
                ))}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Controls Bar */}
      <div className="panel" style={{ padding: "16px", display: "flex", flexWrap: "wrap", gap: "12px", alignItems: "center", justifyContent: "space-between" }}>
        <div style={{ display: "flex", gap: "10px", alignItems: "center", flex: "1 1 300px" }}>
          <input
            type="text"
            className="input-box"
            placeholder="Search nodes by ID, content, filename..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            style={{ width: "100%", maxWidth: "340px", padding: "8px 12px" }}
          />
          <select
            className="input-box"
            value={typeFilter}
            onChange={(e) => setTypeFilter(e.target.value)}
            style={{ padding: "8px 12px", maxWidth: "160px" }}
          >
            {availableTypes.map((t) => (
              <option key={t} value={t}>
                {t}
              </option>
            ))}
          </select>
        </div>

        <div style={{ display: "flex", gap: "8px" }}>
          <button
            className={`btn ${viewMode === "canvas" ? "btn-primary" : "btn-secondary"}`}
            onClick={() => setViewMode("canvas")}
            style={{ padding: "8px 14px", fontSize: "13px" }}
          >
            🌐 Graph Canvas
          </button>
          <button
            className={`btn ${viewMode === "directory" ? "btn-primary" : "btn-secondary"}`}
            onClick={() => setViewMode("directory")}
            style={{ padding: "8px 14px", fontSize: "13px" }}
          >
            📋 Node Directory
          </button>
          <button
            className="btn btn-secondary"
            onClick={loadGraph}
            disabled={loading}
            style={{ padding: "8px 14px", fontSize: "13px" }}
            title="Refresh Graph"
          >
            🔄 Refresh
          </button>
        </div>
      </div>

      {loading && (
        <div style={{ textAlign: "center", padding: "40px", color: "var(--text-muted)" }}>
          Loading knowledge graph structure...
        </div>
      )}

      {error && (
        <div className="status-message error" style={{ padding: "14px" }}>
          {error}
        </div>
      )}

      {!loading && !error && (
        <div style={{ display: "grid", gridTemplateColumns: "1fr 380px", gap: "20px", alignItems: "start" }}>
          {/* Main Visualizer or Directory View */}
          <div className="panel" style={{ padding: "16px", minHeight: "560px", overflow: "hidden", display: "flex", flexDirection: "column" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "12px" }}>
              <h4 style={{ fontWeight: "600", fontSize: "15px" }}>
                {viewMode === "canvas" ? "Interactive Graph Canvas" : `Node Directory (${filteredNodes.length})`}
              </h4>
              <div style={{ display: "flex", gap: "10px", fontSize: "11px", color: "var(--text-muted)" }}>
                {Object.entries(TYPE_COLORS)
                  .filter(([k]) => k !== "DEFAULT")
                  .map(([type, color]) => (
                    <span key={type} style={{ display: "inline-flex", alignItems: "center", gap: "4px" }}>
                      <span style={{ width: "8px", height: "8px", borderRadius: "50%", background: color }}></span>
                      {type}
                    </span>
                  ))}
              </div>
            </div>

            {viewMode === "canvas" ? (
              <div style={{ flex: 1, position: "relative", background: "var(--bg-sidebar)", borderRadius: "var(--radius-md)", border: "1px solid var(--border-glass)", overflow: "auto" }}>
                {filteredNodes.length === 0 ? (
                  <div style={{ textAlign: "center", padding: "60px", color: "var(--text-muted)" }}>
                    No matching graph nodes found.
                  </div>
                ) : (
                  <svg width="100%" height="520" viewBox={`0 0 ${svgLayout.width} ${svgLayout.height}`} style={{ minWidth: "700px" }}>
                    {/* Render Edges */}
                    {svgLayout.edges.map((e, idx) => {
                      const src = svgLayout.positions[e.source_id];
                      const tgt = svgLayout.positions[e.target_id];
                      if (!src || !tgt) return null;
                      const isHighlighted =
                        e.source_id === selectedNodeId || e.target_id === selectedNodeId;
                      return (
                        <g key={e.id || idx}>
                          <line
                            x1={src.x}
                            y1={src.y}
                            x2={tgt.x}
                            y2={tgt.y}
                            stroke={isHighlighted ? "var(--color-accent)" : "hsla(220, 15%, 70%, 0.4)"}
                            strokeWidth={isHighlighted ? 2.5 : 1}
                            strokeDasharray={e.relationship_type === "REFERENCES" ? "4 2" : "none"}
                          />
                        </g>
                      );
                    })}

                    {/* Render Nodes */}
                    {Object.values(svgLayout.positions).map(({ x, y, node }) => {
                      const isSelected = node.id === selectedNodeId;
                      const color = TYPE_COLORS[(node.object_type || "").toUpperCase()] || TYPE_COLORS.DEFAULT;
                      return (
                        <g
                          key={node.id}
                          transform={`translate(${x}, ${y})`}
                          style={{ cursor: "pointer" }}
                          onClick={() => selectNode(node.id)}
                        >
                          <circle
                            r={isSelected ? 18 : 12}
                            fill={color}
                            stroke={isSelected ? "#fff" : "none"}
                            strokeWidth={isSelected ? 3 : 0}
                            style={{
                              filter: isSelected ? "drop-shadow(0 0 8px rgba(59, 130, 246, 0.8))" : "none",
                              transition: "all 0.2s ease"
                            }}
                          />
                          <text
                            textAnchor="middle"
                            dy=".3em"
                            fill="#fff"
                            fontSize={isSelected ? "10px" : "8px"}
                            fontWeight="bold"
                            pointerEvents="none"
                          >
                            {(node.object_type || "N")[0]}
                          </text>
                          <text
                            x="0"
                            y={isSelected ? 26 : 20}
                            textAnchor="middle"
                            fill="var(--text-main)"
                            fontSize="9px"
                            fontWeight={isSelected ? "600" : "400"}
                            pointerEvents="none"
                          >
                            {(node.document_filename || node.object_type || node.id).slice(0, 14)}
                          </text>
                        </g>
                      );
                    })}
                  </svg>
                )}
              </div>
            ) : (
              <div style={{ flex: 1, maxHeight: "520px", overflowY: "auto", display: "flex", flexDirection: "column", gap: "8px" }}>
                {filteredNodes.map((node) => {
                  const isSelected = node.id === selectedNodeId;
                  const color = TYPE_COLORS[(node.object_type || "").toUpperCase()] || TYPE_COLORS.DEFAULT;
                  return (
                    <div
                      key={node.id}
                      onClick={() => selectNode(node.id)}
                      style={{
                        padding: "10px 14px",
                        borderRadius: "8px",
                        border: isSelected ? "2px solid var(--color-accent)" : "1px solid var(--border-glass)",
                        background: isSelected ? "var(--bg-card-hover)" : "var(--bg-card)",
                        cursor: "pointer",
                        display: "flex",
                        justifyContent: "space-between",
                        alignItems: "center",
                        transition: "all 0.15s ease"
                      }}
                    >
                      <div style={{ display: "flex", alignItems: "center", gap: "10px", maxWidth: "80%" }}>
                        <span style={{ width: "10px", height: "10px", borderRadius: "50%", background: color, flexShrink: 0 }}></span>
                        <div>
                          <div style={{ fontSize: "13px", fontWeight: "600", color: "var(--text-main)" }}>
                            {node.object_type || "NODE"} : <span style={{ fontFamily: "monospace", fontSize: "11px" }}>{node.id}</span>
                          </div>
                          <div style={{ fontSize: "12px", color: "var(--text-muted)", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
                            {node.content ? node.content.slice(0, 70) : "(No text content)"}
                          </div>
                        </div>
                      </div>
                      {node.document_filename && (
                        <span style={{ fontSize: "10px", padding: "2px 8px", background: "var(--bg-sidebar)", borderRadius: "4px", color: "var(--text-muted)" }}>
                          {node.document_filename}
                        </span>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          {/* Node Inspector & Neighborhood Panel */}
          <div className="panel" style={{ padding: "18px", display: "flex", flexDirection: "column", gap: "16px" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", borderBottom: "1px solid var(--border-glass)", paddingBottom: "10px" }}>
              <h3 style={{ fontSize: "16px", fontWeight: "600", margin: 0 }}>Node Inspector</h3>
              {activeNode && (
                <span
                  style={{
                    fontSize: "11px",
                    fontWeight: "600",
                    padding: "3px 8px",
                    borderRadius: "4px",
                    background: TYPE_COLORS[(activeNode.object_type || "").toUpperCase()] || TYPE_COLORS.DEFAULT,
                    color: "#fff"
                  }}
                >
                  {activeNode.object_type || "OBJECT"}
                </span>
              )}
            </div>

            {!activeNode ? (
              <div style={{ textAlign: "center", padding: "40px 10px", color: "var(--text-muted)" }}>
                Click a node in the graph canvas or directory to inspect its details and relationships.
              </div>
            ) : (
              <div style={{ display: "flex", flexDirection: "column", gap: "14px" }}>
                {/* Identification */}
                <div>
                  <div style={{ fontSize: "11px", color: "var(--text-muted)", marginBottom: "2px" }}>Node ID</div>
                  <div style={{ fontSize: "12px", fontFamily: "monospace", wordBreak: "break-all", background: "var(--bg-sidebar)", padding: "6px 8px", borderRadius: "4px" }}>
                    {activeNode.id}
                  </div>
                </div>

                {activeNode.document_id && (
                  <div>
                    <div style={{ fontSize: "11px", color: "var(--text-muted)", marginBottom: "2px" }}>Source Document</div>
                    <div style={{ fontSize: "12px", color: "var(--text-main)" }}>
                      📄 {activeNode.document_filename || activeNode.document_id}
                    </div>
                  </div>
                )}

                {/* Content */}
                <div>
                  <div style={{ fontSize: "11px", color: "var(--text-muted)", marginBottom: "2px" }}>Content</div>
                  <div
                    style={{
                      fontSize: "12px",
                      lineHeight: "1.5",
                      maxHeight: "120px",
                      overflowY: "auto",
                      background: "var(--bg-sidebar)",
                      padding: "8px",
                      borderRadius: "6px",
                      border: "1px solid var(--border-glass)",
                      whiteSpace: "pre-wrap"
                    }}
                  >
                    {activeNode.content || "(Empty text content)"}
                  </div>
                </div>

                {/* Direct Intelligence Action Buttons */}
                <div style={{ display: "flex", gap: "8px", flexWrap: "wrap" }}>
                  {onSelectEntity && (activeNode.object_type === "ENTITY" || (activeNode.id || "").startsWith("entity_")) && (
                    <button
                      className="btn btn-secondary"
                      style={{ padding: "4px 10px", fontSize: "11px", color: "var(--color-accent)" }}
                      onClick={() => onSelectEntity(activeNode.content || activeNode.id.replace("entity_", ""))}
                    >
                      👤 Entity Dossier ➔
                    </button>
                  )}
                  {onOpenDocument && activeNode.document_id && (
                    <button
                      className="btn btn-secondary"
                      style={{ padding: "4px 10px", fontSize: "11px" }}
                      onClick={() => onOpenDocument(activeNode.document_id)}
                    >
                      📄 Inspect Document ➔
                    </button>
                  )}
                </div>

                {/* Connected Relationships Navigation */}
                <div style={{ borderTop: "1px solid var(--border-glass)", paddingTop: "12px" }}>
                  <h4 style={{ fontSize: "13px", fontWeight: "600", marginBottom: "8px" }}>
                    Connected Hierarchy & Neighbors
                  </h4>

                  {loadingNeighbors ? (
                    <div style={{ fontSize: "12px", color: "var(--text-muted)", padding: "10px 0" }}>
                      Navigating connections...
                    </div>
                  ) : (
                    <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
                      {/* Parents */}
                      <div>
                        <div style={{ fontSize: "11px", fontWeight: "600", color: "var(--color-accent)", marginBottom: "4px" }}>
                          ▲ Parent Nodes ({nodeParents.length})
                        </div>
                        {nodeParents.length === 0 ? (
                          <div style={{ fontSize: "11px", color: "var(--text-muted)" }}>No parent nodes</div>
                        ) : (
                          <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
                            {nodeParents.map((p) => (
                              <button
                                key={p.id}
                                className="btn btn-secondary"
                                onClick={() => selectNode(p.id)}
                                style={{
                                  padding: "4px 8px",
                                  fontSize: "11px",
                                  textAlign: "left",
                                  display: "flex",
                                  justifyContent: "space-between"
                                }}
                              >
                                <span>{p.object_type}: {p.id.slice(0, 16)}...</span>
                                <span>➔</span>
                              </button>
                            ))}
                          </div>
                        )}
                      </div>

                      {/* Children */}
                      <div>
                        <div style={{ fontSize: "11px", fontWeight: "600", color: "var(--color-success)", marginBottom: "4px" }}>
                          ▼ Child Nodes ({nodeChildren.length})
                        </div>
                        {nodeChildren.length === 0 ? (
                          <div style={{ fontSize: "11px", color: "var(--text-muted)" }}>No child nodes</div>
                        ) : (
                          <div style={{ display: "flex", flexDirection: "column", gap: "4px", maxHeight: "90px", overflowY: "auto" }}>
                            {nodeChildren.map((c) => (
                              <button
                                key={c.id}
                                className="btn btn-secondary"
                                onClick={() => selectNode(c.id)}
                                style={{
                                  padding: "4px 8px",
                                  fontSize: "11px",
                                  textAlign: "left",
                                  display: "flex",
                                  justifyContent: "space-between"
                                }}
                              >
                                <span>{c.object_type}: {c.id.slice(0, 16)}...</span>
                                <span>➔</span>
                              </button>
                            ))}
                          </div>
                        )}
                      </div>

                      {/* Connected Neighbors */}
                      <div>
                        <div style={{ fontSize: "11px", fontWeight: "600", color: "var(--color-accent-purple)", marginBottom: "4px" }}>
                          ↔ Connected Neighbors ({nodeNeighbors.length})
                        </div>
                        {nodeNeighbors.length === 0 ? (
                          <div style={{ fontSize: "11px", color: "var(--text-muted)" }}>No direct neighbors</div>
                        ) : (
                          <div style={{ display: "flex", flexDirection: "column", gap: "4px", maxHeight: "90px", overflowY: "auto" }}>
                            {nodeNeighbors.map((n) => (
                              <button
                                key={n.id}
                                className="btn btn-secondary"
                                onClick={() => selectNode(n.id)}
                                style={{
                                  padding: "4px 8px",
                                  fontSize: "11px",
                                  textAlign: "left",
                                  display: "flex",
                                  justifyContent: "space-between"
                                }}
                              >
                                <span>{n.object_type}: {n.id.slice(0, 16)}...</span>
                                <span>➔</span>
                              </button>
                            ))}
                          </div>
                        )}
                      </div>
                    </div>
                  )}
                </div>

                {/* Path Reasoning Tool */}
                <div style={{ borderTop: "1px solid var(--border-glass)", paddingTop: "12px" }}>
                  <h4 style={{ fontSize: "13px", fontWeight: "600", marginBottom: "8px" }}>
                    Reasoning Path Tracer
                  </h4>
                  <div style={{ display: "flex", gap: "6px", marginBottom: "8px" }}>
                    <select
                      className="input-box"
                      value={pathTargetId}
                      onChange={(e) => setPathTargetId(e.target.value)}
                      style={{ fontSize: "12px", padding: "6px", flex: 1 }}
                    >
                      <option value="">Select target node...</option>
                      {graphData.nodes
                        .filter((n) => n.id !== activeNode.id)
                        .slice(0, 100)
                        .map((n) => (
                          <option key={n.id} value={n.id}>
                            {n.object_type}: {n.id.slice(0, 20)}
                          </option>
                        ))}
                    </select>
                    <button
                      className="btn btn-primary"
                      onClick={handleFindPath}
                      disabled={!pathTargetId || pathLoading}
                      style={{ fontSize: "12px", padding: "6px 10px" }}
                    >
                      {pathLoading ? "..." : "Trace"}
                    </button>
                  </div>

                  {reasoningPath && (
                    <div style={{ fontSize: "11px", background: "var(--bg-sidebar)", padding: "8px", borderRadius: "6px" }}>
                      {reasoningPath.length === 0 ? (
                        <div style={{ color: "var(--text-muted)" }}>No path found within depth 3.</div>
                      ) : (
                        <div>
                          <div style={{ fontWeight: "600", color: "var(--color-success)", marginBottom: "4px" }}>
                            Path Discovered ({reasoningPath.length} hops):
                          </div>
                          {reasoningPath.map((hop, idx) => (
                            <div key={hop.id || idx} style={{ display: "flex", alignItems: "center", gap: "6px", margin: "3px 0" }}>
                              <span>{idx + 1}.</span>
                              <span
                                style={{ color: "var(--color-accent)", cursor: "pointer", textDecoration: "underline" }}
                                onClick={() => selectNode(hop.id)}
                              >
                                {hop.object_type || "Node"} ({hop.id.slice(0, 12)})
                              </span>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
