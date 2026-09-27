import React, { useState, useEffect } from "react";

export default function IntelligenceDashboard({ backendUrl, token, onNavigate, onSelectEntity }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [lastUpdated, setLastUpdated] = useState(new Date());

  const fetchDashboardData = async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await fetch(`${backendUrl}/api/system/dashboard`, {
        headers: token ? { Authorization: `Bearer ${token}` } : {}
      });
      if (!res.ok) {
        throw new Error(`Failed to load system intelligence dashboard (${res.status})`);
      }
      const json = await res.json();
      setData(json);
      setLastUpdated(new Date());
    } catch (err) {
      setError(err.message || "Network error loading dashboard");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDashboardData();
    const interval = setInterval(fetchDashboardData, 15000); // 15s refresh
    return () => clearInterval(interval);
  }, [backendUrl, token]);

  const modalities = [
    { key: "pdf", label: "PDF Documents", icon: "📄", color: "#ef4444" },
    { key: "docx", label: "Word (DOCX)", icon: "📝", color: "#3b82f6" },
    { key: "pptx", label: "PowerPoint", icon: "📊", color: "#f97316" },
    { key: "xlsx", label: "Excel Spreadsheets", icon: "📈", color: "#10b981" },
    { key: "csv", label: "CSV Data", icon: "📑", color: "#14b8a6" },
    { key: "txt", label: "Plain Text", icon: "📜", color: "#6b7280" },
    { key: "image", label: "Visual Images", icon: "🖼️", color: "#8b5cf6" },
    { key: "audio", label: "Audio Transcripts", icon: "🎵", color: "#ec4899" },
  ];

  const classifications = [
    { key: "UNCLASSIFIED", label: "Unclassified", color: "#10b981", bg: "rgba(16, 185, 129, 0.12)" },
    { key: "RESTRICTED", label: "Restricted", color: "#06b6d4", bg: "rgba(6, 182, 212, 0.12)" },
    { key: "CONFIDENTIAL", label: "Confidential", color: "#f59e0b", bg: "rgba(245, 158, 11, 0.12)" },
    { key: "SECRET", label: "Secret", color: "#f97316", bg: "rgba(249, 115, 22, 0.12)" },
    { key: "TOP_SECRET", label: "Top Secret", color: "#ef4444", bg: "rgba(239, 68, 68, 0.12)" },
  ];

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "24px" }}>
      {/* Top Banner Header */}
      <div style={{
        display: "flex", justifyContent: "space-between", alignItems: "center",
        padding: "20px 24px", background: "var(--bg-card)",
        border: "1px solid var(--border-glass)", borderRadius: "var(--radius-lg)",
        boxShadow: "0 4px 20px rgba(0,0,0,0.03)"
      }}>
        <div>
          <h2 style={{ fontSize: "20px", fontWeight: "700", color: "var(--text-main)", margin: 0 }}>
            System Overview & Analytics
          </h2>
          <p style={{ fontSize: "13px", color: "var(--text-muted)", marginTop: "4px", margin: 0 }}>
            Multi-format document processing & local retrieval analytics
          </p>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
          <span style={{ fontSize: "12px", color: "var(--text-muted)" }}>
            Updated: {lastUpdated.toLocaleTimeString()}
          </span>
          <button
            className="btn btn-secondary"
            onClick={fetchDashboardData}
            disabled={loading}
            style={{ display: "flex", alignItems: "center", gap: "6px", padding: "8px 14px", fontSize: "12px" }}
          >
            🔄 Refresh
          </button>
        </div>
      </div>

      {error && (
        <div style={{ padding: "14px", background: "rgba(239, 68, 68, 0.1)", border: "1px solid var(--color-danger)", borderRadius: "8px", color: "var(--color-danger)", fontSize: "13px" }}>
          ⚠️ {error}
        </div>
      )}

      {/* KPI Stats Grid */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: "16px" }}>
        <div className="metric-card" style={{ padding: "18px", borderLeft: "4px solid var(--color-accent)" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <span style={{ fontSize: "12px", fontWeight: "600", color: "var(--text-muted)", textTransform: "uppercase" }}>Indexed Docs</span>
            <span style={{ fontSize: "20px" }}>📁</span>
          </div>
          <div style={{ fontSize: "26px", fontWeight: "700", color: "var(--text-main)", marginTop: "8px" }}>
            {data?.total_documents ?? 0}
          </div>
          <div style={{ fontSize: "11px", color: "var(--text-muted)", marginTop: "4px" }}>Across 8 modalities</div>
        </div>

        <div className="metric-card" style={{ padding: "18px", borderLeft: "4px solid var(--color-accent-purple)" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <span style={{ fontSize: "12px", fontWeight: "600", color: "var(--text-muted)", textTransform: "uppercase" }}>Graph Entities</span>
            <span style={{ fontSize: "20px" }}>🕸️</span>
          </div>
          <div style={{ fontSize: "26px", fontWeight: "700", color: "var(--color-accent-purple)", marginTop: "8px" }}>
            {data?.graph_nodes ?? 0}
          </div>
          <div style={{ fontSize: "11px", color: "var(--text-muted)", marginTop: "4px" }}>Extracted & linked</div>
        </div>

        <div className="metric-card" style={{ padding: "18px", borderLeft: "4px solid var(--color-success)" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <span style={{ fontSize: "12px", fontWeight: "600", color: "var(--text-muted)", textTransform: "uppercase" }}>Graph Triples</span>
            <span style={{ fontSize: "20px" }}>🔗</span>
          </div>
          <div style={{ fontSize: "26px", fontWeight: "700", color: "var(--color-success)", marginTop: "8px" }}>
            {data?.graph_edges ?? 0}
          </div>
          <div style={{ fontSize: "11px", color: "var(--text-muted)", marginTop: "4px" }}>Relational edges</div>
        </div>

        <div className="metric-card" style={{ padding: "18px", borderLeft: "4px solid #f59e0b" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <span style={{ fontSize: "12px", fontWeight: "600", color: "var(--text-muted)", textTransform: "uppercase" }}>Job Queue</span>
            <span style={{ fontSize: "20px" }}>⏳</span>
          </div>
          <div style={{ fontSize: "26px", fontWeight: "700", color: "#f59e0b", marginTop: "8px" }}>
            {data?.jobs?.QUEUED ?? 0}
          </div>
          <div style={{ fontSize: "11px", color: "var(--text-muted)", marginTop: "4px" }}>Active: {data?.jobs?.PROCESSING ?? 0}</div>
        </div>

        <div className="metric-card" style={{ padding: "18px", borderLeft: "4px solid #06b6d4" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <span style={{ fontSize: "12px", fontWeight: "600", color: "var(--text-muted)", textTransform: "uppercase" }}>CPU Util</span>
            <span style={{ fontSize: "20px" }}>⚡</span>
          </div>
          <div style={{ fontSize: "26px", fontWeight: "700", color: "var(--text-main)", marginTop: "8px" }}>
            {data?.system_resources?.cpu_percent != null ? `${data.system_resources.cpu_percent}%` : "0%"}
          </div>
          <div style={{ fontSize: "11px", color: "var(--text-muted)", marginTop: "4px" }}>CPU-first threads</div>
        </div>

        <div className="metric-card" style={{ padding: "18px", borderLeft: "4px solid #8b5cf6" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <span style={{ fontSize: "12px", fontWeight: "600", color: "var(--text-muted)", textTransform: "uppercase" }}>Avail RAM</span>
            <span style={{ fontSize: "20px" }}>💾</span>
          </div>
          <div style={{ fontSize: "22px", fontWeight: "700", color: "var(--text-main)", marginTop: "10px" }}>
            {data?.system_resources?.ram_available_gb != null
              ? `${data.system_resources.ram_available_gb.toFixed(1)} GB`
              : "Active"}
          </div>
          <div style={{ fontSize: "11px", color: "var(--text-muted)", marginTop: "4px" }}>
            {data?.system_resources?.ram_percent != null ? `${data.system_resources.ram_percent}% used` : "Protected"}
          </div>
        </div>
      </div>

      {/* Middle Grid: 8-Modality Distribution & Classification Security Breakdown */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "20px" }}>
        {/* 8-Modality Distribution */}
        <div style={{
          padding: "20px 24px", background: "var(--bg-card)",
          border: "1px solid var(--border-glass)", borderRadius: "var(--radius-lg)"
        }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px" }}>
            <h3 style={{ fontSize: "16px", fontWeight: "600", color: "var(--text-main)", margin: 0 }}>
              8-Modality Document Distribution
            </h3>
            <span style={{ fontSize: "12px", color: "var(--text-muted)" }}>Total: {data?.total_documents ?? 0} files</span>
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
            {modalities.map(m => {
              const count = data?.modality_distribution?.[m.key] ?? 0;
              const total = data?.total_documents || 1;
              const pct = Math.round((count / total) * 100);
              return (
                <div key={m.key} style={{ display: "flex", alignItems: "center", gap: "12px" }}>
                  <span style={{ width: "24px", textAlign: "center" }}>{m.icon}</span>
                  <span style={{ width: "130px", fontSize: "13px", fontWeight: "500", color: "var(--text-main)" }}>
                    {m.label}
                  </span>
                  <div style={{ flexGrow: 1, height: "8px", background: "rgba(0,0,0,0.06)", borderRadius: "4px", overflow: "hidden" }}>
                    <div style={{
                      width: `${Math.max(pct, count > 0 ? 5 : 0)}%`,
                      height: "100%",
                      background: m.color,
                      borderRadius: "4px",
                      transition: "width 0.5s ease"
                    }} />
                  </div>
                  <span style={{ width: "45px", textAlign: "right", fontSize: "12px", fontWeight: "600", color: "var(--text-main)" }}>
                    {count}
                  </span>
                </div>
              );
            })}
          </div>
        </div>

        {/* System Infrastructure & Local Storage Status */}
        <div style={{
          padding: "20px 24px", background: "var(--bg-card)",
          border: "1px solid var(--border-glass)", borderRadius: "var(--radius-lg)"
        }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px" }}>
            <h3 style={{ fontSize: "16px", fontWeight: "600", color: "var(--text-main)", margin: 0 }}>
              System Workspace Status
            </h3>
            <span style={{ fontSize: "12px", color: "var(--color-success)", fontWeight: "600" }}>
              🟢 Local Engine Active
            </span>
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
            <div style={{
              display: "flex", justifyContent: "space-between", alignItems: "center",
              padding: "10px 14px", background: "rgba(16, 185, 129, 0.08)",
              border: "1px solid rgba(16, 185, 129, 0.2)", borderRadius: "8px"
            }}>
              <span style={{ fontSize: "13px", fontWeight: "600", color: "#10b981" }}>
                Vector Index Storage
              </span>
              <span style={{ fontSize: "13px", fontWeight: "700", color: "var(--text-main)" }}>
                ChromaDB (Local Persistent)
              </span>
            </div>

            <div style={{
              display: "flex", justifyContent: "space-between", alignItems: "center",
              padding: "10px 14px", background: "rgba(59, 130, 246, 0.08)",
              border: "1px solid rgba(59, 130, 246, 0.2)", borderRadius: "8px"
            }}>
              <span style={{ fontSize: "13px", fontWeight: "600", color: "#3b82f6" }}>
                Database Registry Engine
              </span>
              <span style={{ fontSize: "13px", fontWeight: "700", color: "var(--text-main)" }}>
                SQLite (metadata.db)
              </span>
            </div>

            <div style={{
              display: "flex", justifyContent: "space-between", alignItems: "center",
              padding: "10px 14px", background: "rgba(139, 92, 246, 0.08)",
              border: "1px solid rgba(139, 92, 246, 0.2)", borderRadius: "8px"
            }}>
              <span style={{ fontSize: "13px", fontWeight: "600", color: "#8b5cf6" }}>
                Knowledge Graph Engine
              </span>
              <span style={{ fontSize: "13px", fontWeight: "700", color: "var(--text-main)" }}>
                Embedded Entity Graph
              </span>
            </div>
          </div>

          <div style={{
            marginTop: "16px", padding: "10px 14px",
            background: "rgba(99, 102, 241, 0.05)", border: "1px solid var(--border-glass)",
            borderRadius: "8px", fontSize: "12px", color: "var(--text-muted)", display: "flex", alignItems: "center", gap: "8px"
          }}>
            <span>💻</span>
            <span>Local On-Premise Execution Workspace. Multi-format document retrieval active.</span>
          </div>
        </div>
      </div>

      {/* Bottom Grid: Top Intelligence Entities & Quick Action Launchers */}
      <div style={{ display: "grid", gridTemplateColumns: "2fr 1fr", gap: "20px" }}>
        {/* Top Entities */}
        <div style={{
          padding: "20px 24px", background: "var(--bg-card)",
          border: "1px solid var(--border-glass)", borderRadius: "var(--radius-lg)"
        }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "14px" }}>
            <h3 style={{ fontSize: "16px", fontWeight: "600", color: "var(--text-main)", margin: 0 }}>
              Key Entities of Intelligence (Top Discovered)
            </h3>
            {onNavigate && (
              <button className="btn btn-secondary" style={{ padding: "4px 10px", fontSize: "11px" }} onClick={() => onNavigate("graph")}>
                View Full Graph ➔
              </button>
            )}
          </div>

          {(!data?.top_entities || data.top_entities.length === 0) ? (
            <p style={{ fontSize: "13px", color: "var(--text-muted)", fontStyle: "italic", padding: "20px 0" }}>
              No entities extracted yet. Upload or process documents to build entity intelligence.
            </p>
          ) : (
            <div style={{ display: "flex", flexWrap: "wrap", gap: "8px" }}>
              {data.top_entities.map((ent, idx) => (
                <button
                  key={idx}
                  onClick={() => onSelectEntity && onSelectEntity(ent.name || ent.text)}
                  style={{
                    display: "flex", alignItems: "center", gap: "6px",
                    padding: "6px 12px", borderRadius: "8px",
                    background: "var(--bg-sidebar)",
                    border: "1px solid var(--border-glass)",
                    color: "var(--text-main)", cursor: "pointer",
                    transition: "all 0.2s ease"
                  }}
                  title="Click to view Entity Intelligence Profile"
                >
                  <span style={{ fontSize: "12px", fontWeight: "600" }}>{ent.name || ent.text}</span>
                  <span style={{
                    fontSize: "10px", fontWeight: "700",
                    padding: "1px 5px", borderRadius: "4px",
                    background: "rgba(99, 102, 241, 0.15)", color: "var(--color-accent)"
                  }}>
                    {ent.type || ent.entity_type || "ENTITY"}
                  </span>
                  <span style={{ fontSize: "10px", color: "var(--text-muted)" }}>
                    ×{ent.count || ent.frequency || 1}
                  </span>
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Quick Launchers */}
        <div style={{
          padding: "20px 24px", background: "var(--bg-card)",
          border: "1px solid var(--border-glass)", borderRadius: "var(--radius-lg)",
          display: "flex", flexDirection: "column", gap: "10px"
        }}>
          <h3 style={{ fontSize: "16px", fontWeight: "600", color: "var(--text-main)", margin: 0, marginBottom: "6px" }}>
            Operational Workspaces
          </h3>

          {onNavigate && (
            <>
              <button
                className="btn btn-secondary"
                style={{ justifyContent: "flex-start", padding: "10px 14px", display: "flex", gap: "10px", alignItems: "center" }}
                onClick={() => onNavigate("search")}
              >
                <span>🔍</span>
                <div style={{ textAlign: "left" }}>
                  <div style={{ fontSize: "13px", fontWeight: "600" }}>Advanced Search</div>
                  <div style={{ fontSize: "11px", color: "var(--text-muted)" }}>8-modality multi-filter query</div>
                </div>
              </button>

              <button
                className="btn btn-secondary"
                style={{ justifyContent: "flex-start", padding: "10px 14px", display: "flex", gap: "10px", alignItems: "center" }}
                onClick={() => onNavigate("timeline")}
              >
                <span>⏱️</span>
                <div style={{ textAlign: "left" }}>
                  <div style={{ fontSize: "13px", fontWeight: "600" }}>Evidence Timeline</div>
                  <div style={{ fontSize: "11px", color: "var(--text-muted)" }}>Chronological cross-modality stream</div>
                </div>
              </button>

              <button
                className="btn btn-secondary"
                style={{ justifyContent: "flex-start", padding: "10px 14px", display: "flex", gap: "10px", alignItems: "center" }}
                onClick={() => onNavigate("compare")}
              >
                <span>⚖️</span>
                <div style={{ textAlign: "left" }}>
                  <div style={{ fontSize: "13px", fontWeight: "600" }}>Document Comparison</div>
                  <div style={{ fontSize: "11px", color: "var(--text-muted)" }}>Side-by-side semantic diff</div>
                </div>
              </button>

              <button
                className="btn btn-secondary"
                style={{ justifyContent: "flex-start", padding: "10px 14px", display: "flex", gap: "10px", alignItems: "center" }}
                onClick={() => onNavigate("report")}
              >
                <span>📑</span>
                <div style={{ textAlign: "left" }}>
                  <div style={{ fontSize: "13px", fontWeight: "600" }}>Multi-Doc Synthesis</div>
                  <div style={{ fontSize: "11px", color: "var(--text-muted)" }}>Compile executive intelligence dossier</div>
                </div>
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
