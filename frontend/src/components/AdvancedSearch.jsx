import React, { useState } from "react";

export default function AdvancedSearch({ backendUrl, token, onOpenIntelligence, onAskInChat, onSelectEntity }) {
  const [query, setQuery] = useState("");
  const [selectedModalities, setSelectedModalities] = useState({
    pdf: true,
    docx: true,
    pptx: true,
    xlsx: true,
    csv: true,
    txt: true,
    image: true,
    audio: true,
  });
  const [classification, setClassification] = useState("");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [minConfidence, setMinConfidence] = useState(0.3);
  const [entityFilter, setEntityFilter] = useState("");

  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [searched, setSearched] = useState(false);
  const [error, setError] = useState(null);

  const modalityList = [
    { id: "pdf", label: "PDF", icon: "📄" },
    { id: "docx", label: "DOCX", icon: "📝" },
    { id: "pptx", label: "PPTX", icon: "📊" },
    { id: "xlsx", label: "XLSX", icon: "📈" },
    { id: "csv", label: "CSV", icon: "📑" },
    { id: "txt", label: "TXT", icon: "📜" },
    { id: "image", label: "Image", icon: "🖼️" },
    { id: "audio", label: "Audio", icon: "🎵" },
  ];

  const toggleModality = (id) => {
    setSelectedModalities(prev => ({ ...prev, [id]: !prev[id] }));
  };

  const selectAllModalities = (val) => {
    const updated = {};
    modalityList.forEach(m => { updated[m.id] = val; });
    setSelectedModalities(updated);
  };

  const handleSearch = async (e) => {
    if (e) e.preventDefault();
    if (!query.trim() && !entityFilter.trim()) return;

    setLoading(true);
    setError(null);
    setSearched(true);

    try {
      const activeMods = Object.keys(selectedModalities).filter(k => selectedModalities[k]);
      const params = new URLSearchParams();
      if (query.trim()) params.append("q", query.trim());
      if (activeMods.length > 0 && activeMods.length < modalityList.length) {
        params.append("modalities", activeMods.join(","));
      }
      if (classification) params.append("classification", classification);
      if (startDate) params.append("start_date", startDate);
      if (endDate) params.append("end_date", endDate);
      if (minConfidence > 0) params.append("min_confidence", minConfidence.toString());
      if (entityFilter.trim()) params.append("entity", entityFilter.trim());

      const res = await fetch(`${backendUrl}/api/search/advanced?${params.toString()}`, {
        headers: token ? { Authorization: `Bearer ${token}` } : {}
      });

      if (!res.ok) {
        throw new Error(`Advanced search failed with status ${res.status}`);
      }

      const data = await res.json();
      setResults(data.results || []);
    } catch (err) {
      setError(err.message || "Error executing multi-filter search");
      setResults([]);
    } finally {
      setLoading(false);
    }
  };

  const getModalityBadge = (modality) => {
    const mod = (modality || "").toLowerCase();
    const found = modalityList.find(m => m.id === mod);
    return (
      <span style={{
        fontSize: "11px", fontWeight: "700", padding: "2px 8px", borderRadius: "6px",
        background: "rgba(99, 102, 241, 0.12)", color: "var(--color-accent)",
        display: "inline-flex", alignItems: "center", gap: "4px"
      }}>
        {found ? found.icon : "📁"} {mod.toUpperCase()}
      </span>
    );
  };

  const getClassificationBadge = (cls) => {
    if (!cls) return null;
    const colors = {
      UNCLASSIFIED: "#10b981",
      RESTRICTED: "#06b6d4",
      CONFIDENTIAL: "#f59e0b",
      SECRET: "#f97316",
      TOP_SECRET: "#ef4444",
    };
    const c = colors[cls] || "#6b7280";
    return (
      <span style={{
        fontSize: "10px", fontWeight: "700", padding: "2px 6px", borderRadius: "4px",
        background: `${c}20`, color: c, border: `1px solid ${c}50`
      }}>
        {cls}
      </span>
    );
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "24px" }}>
      {/* Search & Filter Header Panel */}
      <div style={{
        padding: "24px", background: "var(--bg-card)",
        border: "1px solid var(--border-glass)", borderRadius: "var(--radius-lg)",
        boxShadow: "0 4px 20px rgba(0,0,0,0.03)"
      }}>
        <h3 style={{ fontSize: "18px", fontWeight: "700", color: "var(--text-main)", marginBottom: "4px" }}>
          Multi-Modality Advanced Intelligence Search
        </h3>
        <p style={{ fontSize: "13px", color: "var(--text-muted)", marginBottom: "20px" }}>
          Reciprocal Rank Fusion hybrid retrieval across text, tables, audio transcripts, visual documents, and metadata.
        </p>

        <form onSubmit={handleSearch} style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
          {/* Main Query Bar */}
          <div style={{ display: "flex", gap: "12px" }}>
            <input
              type="text"
              placeholder="Search concepts, statements, names, audio utterances, table records..."
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              style={{
                flexGrow: 1, padding: "12px 16px", borderRadius: "var(--radius-md)",
                border: "1px solid var(--border-glass)", background: "var(--bg-sidebar)",
                color: "var(--text-main)", fontSize: "14px", outline: "none"
              }}
            />
            <button
              type="submit"
              className="btn btn-primary"
              disabled={loading || (!query.trim() && !entityFilter.trim())}
              style={{ padding: "0 24px", fontSize: "14px" }}
            >
              {loading ? "Searching..." : "Search Evidence"}
            </button>
          </div>

          {/* Filter Controls Accordion / Row */}
          <div style={{
            display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: "16px",
            padding: "16px", background: "rgba(0,0,0,0.02)", borderRadius: "var(--radius-md)",
            border: "1px solid var(--border-glass)"
          }}>
            {/* Entity Filter */}
            <div>
              <label style={{ display: "block", fontSize: "12px", fontWeight: "600", color: "var(--text-muted)", marginBottom: "6px" }}>
                Filter By Entity
              </label>
              <input
                type="text"
                placeholder="e.g. Ministry, Alpha, John Doe"
                value={entityFilter}
                onChange={(e) => setEntityFilter(e.target.value)}
                style={{
                  width: "100%", padding: "8px 12px", borderRadius: "6px",
                  border: "1px solid var(--border-glass)", background: "var(--bg-sidebar)",
                  color: "var(--text-main)", fontSize: "12px"
                }}
              />
            </div>

            {/* Classification Tier */}
            <div>
              <label style={{ display: "block", fontSize: "12px", fontWeight: "600", color: "var(--text-muted)", marginBottom: "6px" }}>
                Classification Tier
              </label>
              <select
                value={classification}
                onChange={(e) => setClassification(e.target.value)}
                style={{
                  width: "100%", padding: "8px 12px", borderRadius: "6px",
                  border: "1px solid var(--border-glass)", background: "var(--bg-sidebar)",
                  color: "var(--text-main)", fontSize: "12px"
                }}
              >
                <option value="">All Permitted Clearances</option>
                <option value="UNCLASSIFIED">UNCLASSIFIED</option>
                <option value="RESTRICTED">RESTRICTED</option>
                <option value="CONFIDENTIAL">CONFIDENTIAL</option>
                <option value="SECRET">SECRET</option>
                <option value="TOP_SECRET">TOP SECRET</option>
              </select>
            </div>

            {/* Date Range Start */}
            <div>
              <label style={{ display: "block", fontSize: "12px", fontWeight: "600", color: "var(--text-muted)", marginBottom: "6px" }}>
                From Date
              </label>
              <input
                type="date"
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
                style={{
                  width: "100%", padding: "8px 12px", borderRadius: "6px",
                  border: "1px solid var(--border-glass)", background: "var(--bg-sidebar)",
                  color: "var(--text-main)", fontSize: "12px"
                }}
              />
            </div>

            {/* Date Range End */}
            <div>
              <label style={{ display: "block", fontSize: "12px", fontWeight: "600", color: "var(--text-muted)", marginBottom: "6px" }}>
                To Date
              </label>
              <input
                type="date"
                value={endDate}
                onChange={(e) => setEndDate(e.target.value)}
                style={{
                  width: "100%", padding: "8px 12px", borderRadius: "6px",
                  border: "1px solid var(--border-glass)", background: "var(--bg-sidebar)",
                  color: "var(--text-main)", fontSize: "12px"
                }}
              />
            </div>

            {/* Min Confidence Slider */}
            <div>
              <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "6px" }}>
                <label style={{ fontSize: "12px", fontWeight: "600", color: "var(--text-muted)" }}>
                  Min Confidence
                </label>
                <span style={{ fontSize: "12px", fontWeight: "700", color: "var(--color-accent)" }}>
                  {Math.round(minConfidence * 100)}%
                </span>
              </div>
              <input
                type="range"
                min="0"
                max="0.9"
                step="0.05"
                value={minConfidence}
                onChange={(e) => setMinConfidence(parseFloat(e.target.value))}
                style={{ width: "100%", accentColor: "var(--color-accent)" }}
              />
            </div>
          </div>

          {/* 8-Modality Selector Chips */}
          <div>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px" }}>
              <span style={{ fontSize: "12px", fontWeight: "600", color: "var(--text-muted)" }}>
                Active Modalities:
              </span>
              <div style={{ display: "flex", gap: "8px" }}>
                <button type="button" onClick={() => selectAllModalities(true)} style={{ background: "none", border: "none", color: "var(--color-accent)", fontSize: "11px", cursor: "pointer" }}>
                  Select All
                </button>
                <span style={{ color: "var(--border-glass)" }}>|</span>
                <button type="button" onClick={() => selectAllModalities(false)} style={{ background: "none", border: "none", color: "var(--text-muted)", fontSize: "11px", cursor: "pointer" }}>
                  Clear All
                </button>
              </div>
            </div>

            <div style={{ display: "flex", flexWrap: "wrap", gap: "8px" }}>
              {modalityList.map(m => {
                const isSelected = !!selectedModalities[m.id];
                return (
                  <button
                    key={m.id}
                    type="button"
                    onClick={() => toggleModality(m.id)}
                    style={{
                      padding: "6px 12px", borderRadius: "20px", fontSize: "12px", fontWeight: "500",
                      background: isSelected ? "var(--color-accent)" : "var(--bg-sidebar)",
                      color: isSelected ? "#fff" : "var(--text-muted)",
                      border: isSelected ? "1px solid var(--color-accent)" : "1px solid var(--border-glass)",
                      cursor: "pointer", display: "flex", alignItems: "center", gap: "6px",
                      transition: "all 0.2s ease"
                    }}
                  >
                    <span>{m.icon}</span>
                    <span>{m.label}</span>
                  </button>
                );
              })}
            </div>
          </div>
        </form>
      </div>

      {/* Error Display */}
      {error && (
        <div style={{ padding: "14px", background: "rgba(239, 68, 68, 0.1)", border: "1px solid var(--color-danger)", borderRadius: "8px", color: "var(--color-danger)", fontSize: "13px" }}>
          ⚠️ {error}
        </div>
      )}

      {/* Results Section */}
      {searched && (
        <div>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "14px" }}>
            <h4 style={{ fontSize: "16px", fontWeight: "600", color: "var(--text-main)", margin: 0 }}>
              Evidence Results ({results.length})
            </h4>
            {results.length > 0 && (
              <span style={{ fontSize: "12px", color: "var(--text-muted)" }}>
                Ranked by hybrid lexical + dense vector score
              </span>
            )}
          </div>

          {results.length === 0 && !loading && (
            <div style={{
              padding: "40px", textAlign: "center", background: "var(--bg-card)",
              borderRadius: "var(--radius-lg)", border: "1px solid var(--border-glass)"
            }}>
              <p style={{ fontSize: "15px", color: "var(--text-muted)", margin: 0 }}>
                No matching evidence chunks found matching criteria.
              </p>
              <p style={{ fontSize: "12px", color: "var(--text-muted)", marginTop: "6px" }}>
                Try adjusting the minimum confidence threshold or expanding modality filters.
              </p>
            </div>
          )}

          <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
            {results.map((item, idx) => {
              const meta = item.metadata || {};
              const score = item.score != null ? Math.round(item.score * 100) : null;

              return (
                <div
                  key={idx}
                  style={{
                    padding: "16px 20px", background: "var(--bg-card)",
                    borderRadius: "var(--radius-md)", border: "1px solid var(--border-glass)",
                    display: "flex", flexDirection: "column", gap: "10px",
                    boxShadow: "0 2px 8px rgba(0,0,0,0.02)"
                  }}
                >
                  {/* Result Header */}
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
                    <div style={{ display: "flex", alignItems: "center", gap: "10px", flexWrap: "wrap" }}>
                      {getModalityBadge(meta.modality || item.modality)}
                      <span style={{ fontSize: "14px", fontWeight: "600", color: "var(--text-main)" }}>
                        {meta.source_file || item.filename || "Document Chunk"}
                      </span>
                      {meta.page_number && (
                        <span style={{ fontSize: "11px", color: "var(--text-muted)" }}>
                          Page {meta.page_number}
                        </span>
                      )}
                      {meta.slide_number && (
                        <span style={{ fontSize: "11px", color: "var(--text-muted)" }}>
                          Slide {meta.slide_number}
                        </span>
                      )}
                      {meta.start_sec != null && (
                        <span style={{ fontSize: "11px", color: "var(--color-accent)", fontWeight: "600" }}>
                          ⏱️ {formatTimestamp(meta.start_sec)} - {formatTimestamp(meta.end_sec)}
                        </span>
                      )}
                      {getClassificationBadge(meta.classification || item.classification)}
                    </div>

                    {score != null && (
                      <span style={{
                        fontSize: "12px", fontWeight: "700",
                        color: score >= 75 ? "var(--color-success)" : score >= 50 ? "#f59e0b" : "var(--text-muted)",
                        padding: "2px 8px", borderRadius: "6px", background: "rgba(0,0,0,0.04)"
                      }}>
                        {score}% match
                      </span>
                    )}
                  </div>

                  {/* Result Snippet */}
                  <div style={{
                    fontSize: "13px", color: "var(--text-main)", lineHeight: "1.6",
                    background: "rgba(0,0,0,0.02)", padding: "10px 14px", borderRadius: "6px",
                    borderLeft: "3px solid var(--color-accent)"
                  }}>
                    {item.text || item.content || meta.snippet || "No text available"}
                  </div>

                  {/* Associated Entities */}
                  {meta.entities && meta.entities.length > 0 && (
                    <div style={{ display: "flex", alignItems: "center", gap: "6px", flexWrap: "wrap" }}>
                      <span style={{ fontSize: "11px", color: "var(--text-muted)" }}>Entities:</span>
                      {meta.entities.slice(0, 6).map((e, eIdx) => (
                        <span
                          key={eIdx}
                          onClick={() => onSelectEntity && onSelectEntity(e.name || e)}
                          style={{
                            fontSize: "10px", padding: "2px 6px", borderRadius: "4px",
                            background: "rgba(99, 102, 241, 0.1)", color: "var(--color-accent)",
                            cursor: "pointer", border: "1px solid rgba(99, 102, 241, 0.2)"
                          }}
                        >
                          {e.name || e}
                        </span>
                      ))}
                    </div>
                  )}

                  {/* Action Buttons */}
                  <div style={{ display: "flex", justifyContent: "flex-end", gap: "10px", marginTop: "4px" }}>
                    {onOpenIntelligence && (meta.document_id || item.document_id) && (
                      <button
                        className="btn btn-secondary"
                        style={{ padding: "4px 10px", fontSize: "12px" }}
                        onClick={() => onOpenIntelligence(meta.document_id || item.document_id)}
                      >
                        Inspect Document
                      </button>
                    )}
                    {onAskInChat && (
                      <button
                        className="btn btn-primary"
                        style={{ padding: "4px 12px", fontSize: "12px" }}
                        onClick={() => onAskInChat({
                          document_id: meta.document_id || item.document_id,
                          filename: meta.source_file || item.filename,
                          snippet: item.text
                        })}
                      >
                        Ask AI About This
                      </button>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}

function formatTimestamp(seconds) {
  if (seconds == null) return "00:00";
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
}
