import React, { useState } from "react";

export default function MultiDocReport({ documents, backendUrl, token, onSelectEntity }) {
  const [selectedDocIds, setSelectedDocIds] = useState(
    documents ? documents.slice(0, 3).map(d => d.id) : []
  );
  const [query, setQuery] = useState(
    "Synthesize all operational findings, key actors, critical dates, and security implications."
  );
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const toggleDoc = (id) => {
    setSelectedDocIds(prev =>
      prev.includes(id) ? prev.filter(d => d !== id) : [...prev, id]
    );
  };

  const selectAll = () => {
    if (selectedDocIds.length === documents.length) {
      setSelectedDocIds([]);
    } else {
      setSelectedDocIds(documents.map(d => d.id));
    }
  };

  const handleGenerateReport = async () => {
    if (selectedDocIds.length === 0) return;
    setLoading(true);
    setError(null);

    try {
      const res = await fetch(`${backendUrl}/api/documents/report`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(token ? { Authorization: `Bearer ${token}` } : {})
        },
        body: JSON.stringify({
          document_ids: selectedDocIds,
          query: query
        })
      });

      if (!res.ok) {
        const errJson = await res.json().catch(() => ({}));
        throw new Error(errJson.detail || `Report compilation failed (${res.status})`);
      }

      const data = await res.json();
      setReport(data);
    } catch (err) {
      setError(err.message || "Error generating multi-document report");
      setReport(null);
    } finally {
      setLoading(false);
    }
  };

  const copyMarkdown = () => {
    if (!report) return;
    const md = report.markdown_report || JSON.stringify(report, null, 2);
    navigator.clipboard.writeText(md);
    alert("Report markdown copied to clipboard!");
  };

  const downloadReportTxt = () => {
    if (!report) return;
    const text = report.markdown_report || JSON.stringify(report, null, 2);
    const element = document.createElement("a");
    const file = new Blob([text], { type: "text/plain" });
    element.href = URL.createObjectURL(file);
    element.download = `Intelligence_Report_${new Date().toISOString().slice(0, 10)}.txt`;
    document.body.appendChild(element);
    element.click();
    document.body.removeChild(element);
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "24px" }}>
      {/* Configuration Header Panel */}
      <div style={{
        padding: "24px", background: "var(--bg-card)",
        border: "1px solid var(--border-glass)", borderRadius: "var(--radius-lg)",
        boxShadow: "0 4px 20px rgba(0,0,0,0.03)"
      }}>
        <h3 style={{ fontSize: "18px", fontWeight: "700", color: "var(--text-main)", marginBottom: "4px" }}>
          Multi-Document Intelligence Synthesis Report
        </h3>
        <p style={{ fontSize: "13px", color: "var(--text-muted)", marginBottom: "20px" }}>
          Compile cross-source analytical intelligence dossiers across arbitrary sets of multi-modal files.
        </p>

        {/* Document Selection Box */}
        <div style={{ marginBottom: "16px" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px" }}>
            <label style={{ fontSize: "12px", fontWeight: "600", color: "var(--text-muted)" }}>
              Select Source Documents ({selectedDocIds.length} of {documents?.length || 0} selected):
            </label>
            <button
              type="button"
              onClick={selectAll}
              style={{ background: "none", border: "none", color: "var(--color-accent)", fontSize: "12px", cursor: "pointer" }}
            >
              {selectedDocIds.length === documents?.length ? "Deselect All" : "Select All"}
            </button>
          </div>

          <div style={{
            display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(220px, 1fr))", gap: "8px",
            maxHeight: "150px", overflowY: "auto", padding: "10px", background: "var(--bg-sidebar)",
            borderRadius: "var(--radius-md)", border: "1px solid var(--border-glass)"
          }}>
            {(documents || []).map(doc => {
              const isSelected = selectedDocIds.includes(doc.id);
              return (
                <div
                  key={doc.id}
                  onClick={() => toggleDoc(doc.id)}
                  style={{
                    display: "flex", alignItems: "center", gap: "8px",
                    padding: "6px 10px", borderRadius: "6px",
                    background: isSelected ? "rgba(99, 102, 241, 0.1)" : "transparent",
                    border: isSelected ? "1px solid var(--color-accent)" : "1px solid transparent",
                    cursor: "pointer", fontSize: "12px"
                  }}
                >
                  <input
                    type="checkbox"
                    checked={isSelected}
                    onChange={() => {}}
                    style={{ accentColor: "var(--color-accent)" }}
                  />
                  <span style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                    {doc.filename}
                  </span>
                </div>
              );
            })}
          </div>
        </div>

        {/* Analytical Focus / Query Input */}
        <div style={{ display: "flex", flexDirection: "column", gap: "6px", marginBottom: "16px" }}>
          <label style={{ fontSize: "12px", fontWeight: "600", color: "var(--text-muted)" }}>
            Intelligence Report Objective / Synthesis Prompt
          </label>
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Specify synthesis instructions or analytical questions..."
            style={{
              padding: "12px 16px", borderRadius: "var(--radius-md)",
              border: "1px solid var(--border-glass)", background: "var(--bg-sidebar)",
              color: "var(--text-main)", fontSize: "13px", outline: "none"
            }}
          />
        </div>

        <div style={{ display: "flex", justifyContent: "flex-end" }}>
          <button
            className="btn btn-primary"
            onClick={handleGenerateReport}
            disabled={loading || selectedDocIds.length === 0}
            style={{ padding: "10px 24px", fontSize: "14px", display: "flex", alignItems: "center", gap: "8px" }}
          >
            {loading ? <div className="spinner" /> : "📑"}
            <span>{loading ? "Synthesizing Multimodal Intelligence..." : "Generate Synthesis Dossier"}</span>
          </button>
        </div>
      </div>

      {error && (
        <div style={{ padding: "14px", background: "rgba(239, 68, 68, 0.1)", border: "1px solid var(--color-danger)", borderRadius: "8px", color: "var(--color-danger)", fontSize: "13px" }}>
          ⚠️ {error}
        </div>
      )}

      {/* Report Viewer */}
      {report && (
        <div style={{
          padding: "24px", background: "var(--bg-card)",
          border: "1px solid var(--border-glass)", borderRadius: "var(--radius-lg)",
          display: "flex", flexDirection: "column", gap: "20px"
        }}>
          {/* Action Bar */}
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", borderBottom: "1px solid var(--border-glass)", paddingBottom: "16px" }}>
            <div>
              <h4 style={{ fontSize: "16px", fontWeight: "700", color: "var(--text-main)", margin: 0 }}>
                Synthesized Intelligence Dossier
              </h4>
              <span style={{ fontSize: "12px", color: "var(--text-muted)" }}>
                Sources: {report.source_documents?.length || selectedDocIds.length} multi-modal documents
              </span>
            </div>

            <div style={{ display: "flex", gap: "10px" }}>
              <button className="btn btn-secondary" onClick={copyMarkdown} style={{ padding: "6px 12px", fontSize: "12px" }}>
                📋 Copy Markdown
              </button>
              <button className="btn btn-secondary" onClick={downloadReportTxt} style={{ padding: "6px 12px", fontSize: "12px" }}>
                💾 Export Text
              </button>
            </div>
          </div>

          {/* Executive Summary */}
          <div>
            <h5 style={{ fontSize: "14px", fontWeight: "700", color: "var(--color-accent)", marginBottom: "8px" }}>
              Executive Summary
            </h5>
            <div style={{
              fontSize: "14px", color: "var(--text-main)", lineHeight: "1.7",
              background: "rgba(99, 102, 241, 0.04)", padding: "16px 20px",
              borderRadius: "var(--radius-md)", borderLeft: "4px solid var(--color-accent)"
            }}>
              {report.executive_summary || "No executive summary available."}
            </div>
          </div>

          {/* Cross-Document Key Findings */}
          {report.findings && report.findings.length > 0 && (
            <div>
              <h5 style={{ fontSize: "14px", fontWeight: "700", color: "var(--text-main)", marginBottom: "10px" }}>
                Key Findings by Source
              </h5>
              <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
                {report.findings.map((f, idx) => (
                  <div
                    key={idx}
                    style={{
                      padding: "12px 16px", background: "var(--bg-sidebar)",
                      border: "1px solid var(--border-glass)", borderRadius: "8px"
                    }}
                  >
                    <div style={{ fontSize: "13px", fontWeight: "600", color: "var(--text-main)", marginBottom: "4px" }}>
                      📁 {f.filename || f.document_id}
                    </div>
                    <div style={{ fontSize: "13px", color: "var(--text-muted)", lineHeight: "1.5" }}>
                      {f.summary || f.insight}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Cross-Document Entity Matrix */}
          {report.shared_entities && report.shared_entities.length > 0 && (
            <div>
              <h5 style={{ fontSize: "14px", fontWeight: "700", color: "var(--text-main)", marginBottom: "8px" }}>
                Cross-Document Entity Nexus
              </h5>
              <div style={{ display: "flex", flexWrap: "wrap", gap: "8px" }}>
                {report.shared_entities.map((e, idx) => (
                  <button
                    key={idx}
                    onClick={() => onSelectEntity && onSelectEntity(e.name || e)}
                    style={{
                      padding: "6px 12px", borderRadius: "8px",
                      background: "var(--bg-sidebar)", border: "1px solid var(--border-glass)",
                      cursor: "pointer", display: "flex", alignItems: "center", gap: "6px"
                    }}
                  >
                    <span style={{ fontSize: "12px", fontWeight: "600", color: "var(--color-accent)" }}>
                      {e.name || e}
                    </span>
                    {e.document_count && (
                      <span style={{ fontSize: "10px", color: "var(--text-muted)" }}>
                        in {e.document_count} docs
                      </span>
                    )}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Unified Timeline in Report */}
          {report.timeline_events && report.timeline_events.length > 0 && (
            <div>
              <h5 style={{ fontSize: "14px", fontWeight: "700", color: "var(--text-main)", marginBottom: "8px" }}>
                Synthesized Chronological Milestones
              </h5>
              <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
                {report.timeline_events.map((t, idx) => (
                  <div
                    key={idx}
                    style={{
                      padding: "8px 12px", background: "rgba(0,0,0,0.02)",
                      border: "1px solid var(--border-glass)", borderRadius: "6px",
                      fontSize: "12px", display: "flex", alignItems: "center", gap: "10px"
                    }}
                  >
                    <span style={{ fontWeight: "700", color: "var(--color-accent)" }}>{t.date || t.timestamp}</span>
                    <span style={{ color: "var(--text-main)" }}>{t.event || t.description}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
