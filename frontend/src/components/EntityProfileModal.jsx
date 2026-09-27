import React, { useState, useEffect } from "react";

export default function EntityProfileModal({ entityName, onClose, onExploreInGraph, onOpenDocument, backendUrl, token }) {
  const [profile, setProfile] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!entityName) return;
    let isMounted = true;
    setLoading(true);
    setError(null);

    const fetchProfile = async () => {
      try {
        const res = await fetch(`${backendUrl}/api/graph/entities/${encodeURIComponent(entityName)}/profile`, {
          headers: token ? { Authorization: `Bearer ${token}` } : {}
        });
        if (!res.ok) {
          throw new Error(`Failed to load entity profile (${res.status})`);
        }
        const data = await res.json();
        if (isMounted) {
          setProfile(data);
        }
      } catch (err) {
        if (isMounted) {
          setError(err.message || "Failed to load entity intelligence");
        }
      } finally {
        if (isMounted) {
          setLoading(false);
        }
      }
    };

    fetchProfile();
    return () => { isMounted = false; };
  }, [entityName, backendUrl, token]);

  if (!entityName) return null;

  return (
    <div className="modal-overlay" style={{
      position: "fixed", top: 0, left: 0, right: 0, bottom: 0,
      backgroundColor: "rgba(10, 15, 25, 0.75)",
      backdropFilter: "blur(6px)",
      display: "flex", alignItems: "center", justifyContent: "center",
      zIndex: 10000, padding: "20px"
    }} onClick={onClose}>
      <div className="modal-content" style={{
        backgroundColor: "var(--bg-sidebar)",
        border: "1px solid var(--border-glass)",
        borderRadius: "var(--radius-lg)",
        width: "100%", maxWidth: "780px", maxHeight: "88vh",
        display: "flex", flexDirection: "column",
        boxShadow: "0 20px 50px rgba(0,0,0,0.3)",
        overflow: "hidden"
      }} onClick={(e) => e.stopPropagation()}>
        {/* Header */}
        <div style={{
          padding: "20px 24px",
          borderBottom: "1px solid var(--border-glass)",
          display: "flex", justifyContent: "space-between", alignItems: "center",
          background: "linear-gradient(90deg, rgba(99, 102, 241, 0.08), transparent)"
        }}>
          <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
            <div style={{
              width: "40px", height: "40px", borderRadius: "10px",
              background: "linear-gradient(135deg, var(--color-accent), var(--color-accent-purple))",
              display: "flex", alignItems: "center", justifyContent: "center",
              color: "#fff", fontSize: "20px", fontWeight: "bold"
            }}>
              👤
            </div>
            <div>
              <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                <h3 style={{ margin: 0, fontSize: "18px", fontWeight: "700", color: "var(--text-main)" }}>
                  {entityName}
                </h3>
                {profile?.entity_type && (
                  <span style={{
                    fontSize: "11px", fontWeight: "600",
                    padding: "2px 8px", borderRadius: "12px",
                    background: "rgba(99, 102, 241, 0.15)",
                    color: "var(--color-accent)", border: "1px solid rgba(99, 102, 241, 0.3)"
                  }}>
                    {profile.entity_type}
                  </span>
                )}
              </div>
              <p style={{ margin: 0, fontSize: "12px", color: "var(--text-muted)", marginTop: "2px" }}>
                Entity Intelligence Dossier & Cross-Document Graph
              </p>
            </div>
          </div>
          <button onClick={onClose} style={{
            background: "none", border: "none", fontSize: "22px",
            color: "var(--text-muted)", cursor: "pointer", padding: "4px 8px"
          }}>
            ×
          </button>
        </div>

        {/* Body */}
        <div style={{ padding: "24px", overflowY: "auto", display: "flex", flexDirection: "column", gap: "20px" }}>
          {loading && (
            <div style={{ textAlign: "center", padding: "40px", color: "var(--color-accent)" }}>
              <div className="spinner" style={{ margin: "0 auto 12px" }}></div>
              <p style={{ fontSize: "14px", color: "var(--text-muted)" }}>Synthesizing entity knowledge graph...</p>
            </div>
          )}

          {error && (
            <div style={{ padding: "16px", background: "rgba(239, 68, 68, 0.1)", border: "1px solid var(--color-danger)", borderRadius: "8px", color: "var(--color-danger)", fontSize: "14px" }}>
              {error}
            </div>
          )}

          {!loading && profile && (
            <>
              {/* Summary Stats */}
              <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: "12px" }}>
                <div style={{ padding: "14px", background: "var(--bg-card)", border: "1px solid var(--border-glass)", borderRadius: "var(--radius-md)", textAlign: "center" }}>
                  <div style={{ fontSize: "11px", color: "var(--text-muted)", textTransform: "uppercase", fontWeight: "600" }}>Total Mentions</div>
                  <div style={{ fontSize: "22px", fontWeight: "700", color: "var(--color-accent)", marginTop: "4px" }}>
                    {profile.mention_count || 1}
                  </div>
                </div>
                <div style={{ padding: "14px", background: "var(--bg-card)", border: "1px solid var(--border-glass)", borderRadius: "var(--radius-md)", textAlign: "center" }}>
                  <div style={{ fontSize: "11px", color: "var(--text-muted)", textTransform: "uppercase", fontWeight: "600" }}>Connected Documents</div>
                  <div style={{ fontSize: "22px", fontWeight: "700", color: "var(--color-accent-purple)", marginTop: "4px" }}>
                    {profile.documents?.length || 0}
                  </div>
                </div>
                <div style={{ padding: "14px", background: "var(--bg-card)", border: "1px solid var(--border-glass)", borderRadius: "var(--radius-md)", textAlign: "center" }}>
                  <div style={{ fontSize: "11px", color: "var(--text-muted)", textTransform: "uppercase", fontWeight: "600" }}>Graph Connections</div>
                  <div style={{ fontSize: "22px", fontWeight: "700", color: "var(--color-success)", marginTop: "4px" }}>
                    {profile.relationships?.length || 0}
                  </div>
                </div>
              </div>

              {/* Connected Documents */}
              <div>
                <h4 style={{ fontSize: "14px", fontWeight: "600", marginBottom: "10px", color: "var(--text-main)", display: "flex", alignItems: "center", gap: "6px" }}>
                  📁 Referenced Documents ({profile.documents?.length || 0})
                </h4>
                {(!profile.documents || profile.documents.length === 0) ? (
                  <p style={{ fontSize: "13px", color: "var(--text-muted)", fontStyle: "italic" }}>No document links found.</p>
                ) : (
                  <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
                    {profile.documents.map((doc, idx) => (
                      <div key={idx} style={{
                        padding: "10px 14px", background: "var(--bg-card)",
                        border: "1px solid var(--border-glass)", borderRadius: "8px",
                        display: "flex", justifyContent: "space-between", alignItems: "center"
                      }}>
                        <div>
                          <div style={{ fontSize: "13px", fontWeight: "600", color: "var(--text-main)" }}>
                            {doc.filename || doc.document_id}
                          </div>
                          <div style={{ fontSize: "11px", color: "var(--text-muted)", marginTop: "2px" }}>
                            {doc.modality && <span style={{ textTransform: "uppercase", marginRight: "8px" }}>[{doc.modality}]</span>}
                            {doc.classification && <span>Classification: {doc.classification}</span>}
                          </div>
                        </div>
                        {onOpenDocument && (
                          <button className="btn btn-secondary" style={{ padding: "4px 10px", fontSize: "11px" }} onClick={() => onOpenDocument(doc.document_id || doc.id)}>
                            Inspect
                          </button>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Graph Relationships */}
              <div>
                <h4 style={{ fontSize: "14px", fontWeight: "600", marginBottom: "10px", color: "var(--text-main)", display: "flex", alignItems: "center", gap: "6px" }}>
                  🕸️ Knowledge Graph Triples ({profile.relationships?.length || 0})
                </h4>
                {(!profile.relationships || profile.relationships.length === 0) ? (
                  <p style={{ fontSize: "13px", color: "var(--text-muted)", fontStyle: "italic" }}>No direct relationships identified.</p>
                ) : (
                  <div style={{ display: "flex", flexDirection: "column", gap: "6px", maxHeight: "180px", overflowY: "auto" }}>
                    {profile.relationships.map((rel, idx) => (
                      <div key={idx} style={{
                        padding: "8px 12px", background: "rgba(0,0,0,0.02)",
                        border: "1px solid var(--border-glass)", borderRadius: "6px",
                        fontSize: "12px", display: "flex", alignItems: "center", gap: "8px"
                      }}>
                        <span style={{ fontWeight: "600", color: "var(--color-accent)" }}>{rel.source}</span>
                        <span style={{ fontSize: "11px", color: "var(--text-muted)", background: "rgba(99, 102, 241, 0.08)", padding: "2px 6px", borderRadius: "4px" }}>
                          ➔ [{rel.relationship || "RELATED_TO"}] ➔
                        </span>
                        <span style={{ fontWeight: "600", color: "var(--color-accent-purple)" }}>{rel.target}</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Co-occurring Entities */}
              {profile.co_occurring_entities?.length > 0 && (
                <div>
                  <h4 style={{ fontSize: "14px", fontWeight: "600", marginBottom: "10px", color: "var(--text-main)" }}>
                    🤝 Co-Occurring Entities
                  </h4>
                  <div style={{ display: "flex", flexWrap: "wrap", gap: "6px" }}>
                    {profile.co_occurring_entities.map((co, idx) => (
                      <span key={idx} style={{
                        fontSize: "11px", padding: "4px 8px", borderRadius: "6px",
                        background: "var(--bg-card)", border: "1px solid var(--border-glass)",
                        color: "var(--text-main)"
                      }}>
                        {co.name || co} {co.count ? `(${co.count})` : ""}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </>
          )}
        </div>

        {/* Footer Actions */}
        <div style={{
          padding: "16px 24px",
          borderTop: "1px solid var(--border-glass)",
          display: "flex", justifyContent: "space-between", alignItems: "center",
          background: "var(--bg-sidebar)"
        }}>
          <button className="btn btn-secondary" onClick={onClose} style={{ padding: "8px 16px" }}>
            Close
          </button>
          {onExploreInGraph && (
            <button className="btn btn-primary" onClick={() => { onClose(); onExploreInGraph(entityName); }} style={{ padding: "8px 18px", display: "flex", alignItems: "center", gap: "6px" }}>
              <span>Open in Knowledge Graph</span> ➔
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
