import React, { useState, useEffect } from "react";

export default function TimelineView({ backendUrl, token, onOpenIntelligence, onSelectEntity }) {
  const [events, setEvents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedModality, setSelectedModality] = useState("");
  const [selectedClassification, setSelectedClassification] = useState("");

  const fetchTimeline = async () => {
    setLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams();
      if (selectedModality) params.append("modality", selectedModality);
      if (selectedClassification) params.append("classification", selectedClassification);

      const res = await fetch(`${backendUrl}/api/timeline?${params.toString()}`, {
        headers: token ? { Authorization: `Bearer ${token}` } : {}
      });

      if (!res.ok) {
        throw new Error(`Failed to load timeline (${res.status})`);
      }

      const data = await res.json();
      setEvents(data.events || data.timeline || []);
    } catch (err) {
      setError(err.message || "Failed to load timeline events");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchTimeline();
  }, [backendUrl, token, selectedModality, selectedClassification]);

  const getModalityIcon = (modality) => {
    switch ((modality || "").toLowerCase()) {
      case "pdf": return "📄";
      case "docx": return "📝";
      case "pptx": return "📊";
      case "xlsx": return "📈";
      case "csv": return "📑";
      case "txt": return "📜";
      case "image": return "🖼️";
      case "audio": return "🎵";
      default: return "📁";
    }
  };

  const getClassificationColor = (cls) => {
    switch (cls) {
      case "TOP_SECRET": return "#ef4444";
      case "SECRET": return "#f97316";
      case "CONFIDENTIAL": return "#f59e0b";
      case "RESTRICTED": return "#06b6d4";
      default: return "#10b981";
    }
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "24px" }}>
      {/* Header and Filter Controls */}
      <div style={{
        padding: "24px", background: "var(--bg-card)",
        border: "1px solid var(--border-glass)", borderRadius: "var(--radius-lg)",
        boxShadow: "0 4px 20px rgba(0,0,0,0.03)"
      }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px" }}>
          <div>
            <h3 style={{ fontSize: "18px", fontWeight: "700", color: "var(--text-main)", margin: 0 }}>
              Chronological Evidence Timeline
            </h3>
            <p style={{ fontSize: "13px", color: "var(--text-muted)", marginTop: "4px", margin: 0 }}>
              Cross-modality temporal mapping of documents, audio transcripts, intelligence mentions, and events.
            </p>
          </div>
          <button className="btn btn-secondary" onClick={fetchTimeline} disabled={loading} style={{ padding: "8px 14px", fontSize: "12px" }}>
            🔄 Refresh
          </button>
        </div>

        {/* Filter Bar */}
        <div style={{ display: "flex", gap: "16px", flexWrap: "wrap", alignItems: "center" }}>
          <div>
            <label style={{ fontSize: "12px", fontWeight: "600", color: "var(--text-muted)", marginRight: "8px" }}>
              Modality:
            </label>
            <select
              value={selectedModality}
              onChange={(e) => setSelectedModality(e.target.value)}
              style={{
                padding: "6px 12px", borderRadius: "6px",
                border: "1px solid var(--border-glass)", background: "var(--bg-sidebar)",
                color: "var(--text-main)", fontSize: "12px"
              }}
            >
              <option value="">All 8 Modalities</option>
              <option value="pdf">PDF</option>
              <option value="docx">DOCX</option>
              <option value="pptx">PPTX</option>
              <option value="xlsx">XLSX</option>
              <option value="csv">CSV</option>
              <option value="txt">TXT</option>
              <option value="image">Image</option>
              <option value="audio">Audio</option>
            </select>
          </div>

          <div>
            <label style={{ fontSize: "12px", fontWeight: "600", color: "var(--text-muted)", marginRight: "8px" }}>
              Clearance:
            </label>
            <select
              value={selectedClassification}
              onChange={(e) => setSelectedClassification(e.target.value)}
              style={{
                padding: "6px 12px", borderRadius: "6px",
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

          <span style={{ fontSize: "12px", color: "var(--text-muted)", marginLeft: "auto" }}>
            Showing {events.length} timeline milestones
          </span>
        </div>
      </div>

      {error && (
        <div style={{ padding: "14px", background: "rgba(239, 68, 68, 0.1)", border: "1px solid var(--color-danger)", borderRadius: "8px", color: "var(--color-danger)", fontSize: "13px" }}>
          ⚠️ {error}
        </div>
      )}

      {loading && (
        <div style={{ textAlign: "center", padding: "60px 0", color: "var(--color-accent)" }}>
          <div className="spinner" style={{ margin: "0 auto 12px" }}></div>
          <p style={{ fontSize: "14px", color: "var(--text-muted)" }}>Constructing temporal evidence stream...</p>
        </div>
      )}

      {!loading && events.length === 0 && (
        <div style={{
          padding: "60px 20px", textAlign: "center", background: "var(--bg-card)",
          borderRadius: "var(--radius-lg)", border: "1px solid var(--border-glass)"
        }}>
          <div style={{ fontSize: "40px", marginBottom: "12px" }}>⏱️</div>
          <h4 style={{ fontSize: "16px", color: "var(--text-main)", marginBottom: "4px" }}>No Timeline Milestones Found</h4>
          <p style={{ fontSize: "13px", color: "var(--text-muted)" }}>
            Processed documents with timestamps, dates, or audio recordings will automatically appear in chronological sequence here.
          </p>
        </div>
      )}

      {/* Vertical Timeline Stream */}
      {!loading && events.length > 0 && (
        <div style={{ position: "relative", paddingLeft: "36px" }}>
          {/* Vertical Connecting Line */}
          <div style={{
            position: "absolute", top: "12px", bottom: "12px", left: "16px",
            width: "2px", background: "linear-gradient(to bottom, var(--color-accent), var(--color-accent-purple))"
          }} />

          <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
            {events.map((ev, idx) => {
              const clsColor = getClassificationColor(ev.classification);
              const isAudio = (ev.modality || "").toLowerCase() === "audio";

              return (
                <div key={idx} style={{ position: "relative" }}>
                  {/* Timeline Dot */}
                  <div style={{
                    position: "absolute", left: "-28px", top: "16px",
                    width: "16px", height: "16px", borderRadius: "50%",
                    background: "var(--bg-sidebar)", border: `3px solid ${clsColor}`,
                    boxShadow: `0 0 10px ${clsColor}80`
                  }} />

                  {/* Card */}
                  <div style={{
                    padding: "16px 20px", background: "var(--bg-card)",
                    border: "1px solid var(--border-glass)", borderRadius: "var(--radius-md)",
                    display: "flex", flexDirection: "column", gap: "10px",
                    boxShadow: "0 2px 10px rgba(0,0,0,0.02)"
                  }}>
                    {/* Header: Date + Source info */}
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "8px" }}>
                      <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                        <span style={{ fontSize: "16px" }}>{getModalityIcon(ev.modality)}</span>
                        <span style={{
                          fontSize: "12px", fontWeight: "700",
                          color: "var(--color-accent)", textTransform: "uppercase"
                        }}>
                          {ev.modality || "DOCUMENT"}
                        </span>
                        <span style={{ fontSize: "13px", fontWeight: "600", color: "var(--text-main)" }}>
                          {ev.title || ev.source_file || ev.filename || "Event Marker"}
                        </span>
                      </div>

                      <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                        {ev.timestamp && (
                          <span style={{ fontSize: "12px", fontWeight: "600", color: "var(--text-muted)" }}>
                            📅 {ev.timestamp}
                          </span>
                        )}
                        {ev.classification && (
                          <span style={{
                            fontSize: "10px", fontWeight: "700", padding: "2px 6px", borderRadius: "4px",
                            background: `${clsColor}20`, color: clsColor, border: `1px solid ${clsColor}50`
                          }}>
                            {ev.classification}
                          </span>
                        )}
                      </div>
                    </div>

                    {/* Audio Timestamp / Range */}
                    {isAudio && ev.start_sec != null && (
                      <div style={{ fontSize: "12px", color: "var(--color-accent-purple)", fontWeight: "600" }}>
                        ⏱️ Audio Segment: {formatSec(ev.start_sec)} - {formatSec(ev.end_sec)}
                      </div>
                    )}

                    {/* Snippet / Description */}
                    <div style={{ fontSize: "13px", color: "var(--text-main)", lineHeight: "1.6", background: "rgba(0,0,0,0.02)", padding: "10px 14px", borderRadius: "6px" }}>
                      {ev.description || ev.text || ev.snippet || "No textual summary"}
                    </div>

                    {/* Entities */}
                    {ev.entities && ev.entities.length > 0 && (
                      <div style={{ display: "flex", alignItems: "center", gap: "6px", flexWrap: "wrap" }}>
                        <span style={{ fontSize: "11px", color: "var(--text-muted)" }}>Linked Entities:</span>
                        {ev.entities.map((e, eIdx) => (
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

                    {/* Action */}
                    {onOpenIntelligence && (ev.document_id || ev.id) && (
                      <div style={{ display: "flex", justifyContent: "flex-end" }}>
                        <button
                          className="btn btn-secondary"
                          style={{ padding: "4px 10px", fontSize: "11px" }}
                          onClick={() => onOpenIntelligence(ev.document_id || ev.id)}
                        >
                          Inspect Source Document ➔
                        </button>
                      </div>
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

function formatSec(sec) {
  if (sec == null) return "00:00";
  const m = Math.floor(sec / 60);
  const s = Math.floor(sec % 60);
  return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
}
