import React, { useState } from "react";

export default function DocumentComparison({ documents, backendUrl, token, onSelectEntity, onOpenIntelligence }) {
  const [docAId, setDocAId] = useState(documents && documents.length > 0 ? documents[0].id : "");
  const [docBId, setDocBId] = useState(documents && documents.length > 1 ? documents[1].id : (documents && documents[0] ? documents[0].id : ""));
  const [comparison, setComparison] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleCompare = async () => {
    if (!docAId || !docBId) return;
    setLoading(true);
    setError(null);

    try {
      const res = await fetch(`${backendUrl}/api/documents/compare`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(token ? { Authorization: `Bearer ${token}` } : {})
        },
        body: JSON.stringify({
          doc_id_a: docAId,
          doc_id_b: docBId
        })
      });

      if (!res.ok) {
        const errJson = await res.json().catch(() => ({}));
        throw new Error(errJson.detail || `Comparison failed (${res.status})`);
      }

      const data = await res.json();
      setComparison(data);
    } catch (err) {
      setError(err.message || "Error comparing documents");
      setComparison(null);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "24px" }}>
      {/* Selector Header Panel */}
      <div style={{
        padding: "24px", background: "var(--bg-card)",
        border: "1px solid var(--border-glass)", borderRadius: "var(--radius-lg)",
        boxShadow: "0 4px 20px rgba(0,0,0,0.03)"
      }}>
        <h3 style={{ fontSize: "18px", fontWeight: "700", color: "var(--text-main)", marginBottom: "4px" }}>
          Side-by-Side Document Intelligence Comparison
        </h3>
        <p style={{ fontSize: "13px", color: "var(--text-muted)", marginBottom: "20px" }}>
          Compare textual content, named entities, security clearance differentials, and semantic similarity.
        </p>

        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr auto", gap: "16px", alignItems: "flex-end" }}>
          <div>
            <label style={{ display: "block", fontSize: "12px", fontWeight: "600", color: "var(--text-muted)", marginBottom: "6px" }}>
              Primary Document (A)
            </label>
            <select
              value={docAId}
              onChange={(e) => setDocAId(e.target.value)}
              style={{
                width: "100%", padding: "10px 14px", borderRadius: "var(--radius-md)",
                border: "1px solid var(--border-glass)", background: "var(--bg-sidebar)",
                color: "var(--text-main)", fontSize: "13px"
              }}
            >
              {documents.map((d) => (
                <option key={d.id} value={d.id}>
                  {d.filename} ({d.modality || "doc"})
                </option>
              ))}
            </select>
          </div>

          <div>
            <label style={{ display: "block", fontSize: "12px", fontWeight: "600", color: "var(--text-muted)", marginBottom: "6px" }}>
              Secondary Document (B)
            </label>
            <select
              value={docBId}
              onChange={(e) => setDocBId(e.target.value)}
              style={{
                width: "100%", padding: "10px 14px", borderRadius: "var(--radius-md)",
                border: "1px solid var(--border-glass)", background: "var(--bg-sidebar)",
                color: "var(--text-main)", fontSize: "13px"
              }}
            >
              {documents.map((d) => (
                <option key={d.id} value={d.id}>
                  {d.filename} ({d.modality || "doc"})
                </option>
              ))}
            </select>
          </div>

          <button
            className="btn btn-primary"
            onClick={handleCompare}
            disabled={loading || !docAId || !docBId}
            style={{ padding: "10px 24px", height: "42px", fontSize: "13px" }}
          >
            {loading ? "Comparing..." : "Compare Documents"}
          </button>
        </div>
      </div>

      {error && (
        <div style={{ padding: "14px", background: "rgba(239, 68, 68, 0.1)", border: "1px solid var(--color-danger)", borderRadius: "8px", color: "var(--color-danger)", fontSize: "13px" }}>
          ⚠️ {error}
        </div>
      )}

      {/* Comparison Results */}
      {comparison && (
        <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
          {/* Similarity & Clearance Metric Banner */}
          <div style={{
            display: "grid", gridTemplateColumns: "1fr 1fr", gap: "16px",
            padding: "20px", background: "var(--bg-card)",
            border: "1px solid var(--border-glass)", borderRadius: "var(--radius-lg)"
          }}>
            {/* Similarity Meter */}
            <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <span style={{ fontSize: "13px", fontWeight: "600", color: "var(--text-main)" }}>
                  Semantic Content Similarity
                </span>
                <span style={{ fontSize: "16px", fontWeight: "700", color: "var(--color-accent)" }}>
                  {Math.round((comparison.similarity_score ?? 0.5) * 100)}%
                </span>
              </div>
              <div style={{ width: "100%", height: "10px", background: "rgba(0,0,0,0.06)", borderRadius: "5px", overflow: "hidden" }}>
                <div style={{
                  width: `${Math.round((comparison.similarity_score ?? 0.5) * 100)}%`,
                  height: "100%",
                  background: "linear-gradient(90deg, var(--color-accent), var(--color-accent-purple))",
                  borderRadius: "5px"
                }} />
              </div>
            </div>

            {/* Security Differential */}
            <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
              <span style={{ fontSize: "13px", fontWeight: "600", color: "var(--text-main)" }}>
                Classification Tier Assessment
              </span>
              <div style={{ display: "flex", alignItems: "center", gap: "8px", marginTop: "4px" }}>
                <span style={{ fontSize: "12px", padding: "2px 8px", borderRadius: "4px", background: "rgba(99, 102, 241, 0.1)", fontWeight: "600" }}>
                  Doc A: {comparison.doc_a?.classification || "UNCLASSIFIED"}
                </span>
                <span>➔</span>
                <span style={{ fontSize: "12px", padding: "2px 8px", borderRadius: "4px", background: "rgba(99, 102, 241, 0.1)", fontWeight: "600" }}>
                  Doc B: {comparison.doc_b?.classification || "UNCLASSIFIED"}
                </span>
              </div>
              {comparison.doc_a?.classification !== comparison.doc_b?.classification && (
                <span style={{ fontSize: "11px", color: "#f59e0b", marginTop: "2px" }}>
                  ⚠️ Security Clearance mismatch: Handling protocols must respect the highest tier.
                </span>
              )}
            </div>
          </div>

          {/* Side by Side Document Info */}
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "20px" }}>
            {/* Document A Card */}
            <div style={{
              padding: "20px", background: "var(--bg-card)",
              border: "1px solid var(--border-glass)", borderRadius: "var(--radius-lg)",
              display: "flex", flexDirection: "column", gap: "12px"
            }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <h4 style={{ fontSize: "15px", fontWeight: "700", color: "var(--color-accent)", margin: 0 }}>
                  Document A: {comparison.doc_a?.filename}
                </h4>
                {onOpenIntelligence && (
                  <button className="btn btn-secondary" style={{ padding: "4px 8px", fontSize: "11px" }} onClick={() => onOpenIntelligence(docAId)}>
                    Inspect
                  </button>
                )}
              </div>
              <div style={{ fontSize: "12px", color: "var(--text-muted)", display: "flex", gap: "12px" }}>
                <span>Modality: {comparison.doc_a?.modality}</span>
                <span>Chunks: {comparison.doc_a?.chunk_count || 0}</span>
                <span>Entities: {comparison.doc_a?.entity_count || 0}</span>
              </div>
              <div style={{ fontSize: "13px", color: "var(--text-main)", background: "rgba(0,0,0,0.02)", padding: "12px", borderRadius: "8px", maxHeight: "200px", overflowY: "auto", lineHeight: "1.5" }}>
                {comparison.doc_a?.snippet || "No textual summary"}
              </div>
            </div>

            {/* Document B Card */}
            <div style={{
              padding: "20px", background: "var(--bg-card)",
              border: "1px solid var(--border-glass)", borderRadius: "var(--radius-lg)",
              display: "flex", flexDirection: "column", gap: "12px"
            }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <h4 style={{ fontSize: "15px", fontWeight: "700", color: "var(--color-accent-purple)", margin: 0 }}>
                  Document B: {comparison.doc_b?.filename}
                </h4>
                {onOpenIntelligence && (
                  <button className="btn btn-secondary" style={{ padding: "4px 8px", fontSize: "11px" }} onClick={() => onOpenIntelligence(docBId)}>
                    Inspect
                  </button>
                )}
              </div>
              <div style={{ fontSize: "12px", color: "var(--text-muted)", display: "flex", gap: "12px" }}>
                <span>Modality: {comparison.doc_b?.modality}</span>
                <span>Chunks: {comparison.doc_b?.chunk_count || 0}</span>
                <span>Entities: {comparison.doc_b?.entity_count || 0}</span>
              </div>
              <div style={{ fontSize: "13px", color: "var(--text-main)", background: "rgba(0,0,0,0.02)", padding: "12px", borderRadius: "8px", maxHeight: "200px", overflowY: "auto", lineHeight: "1.5" }}>
                {comparison.doc_b?.snippet || "No textual summary"}
              </div>
            </div>
          </div>

          {/* Entity Comparison Matrix */}
          <div style={{
            padding: "20px 24px", background: "var(--bg-card)",
            border: "1px solid var(--border-glass)", borderRadius: "var(--radius-lg)",
            display: "flex", flexDirection: "column", gap: "16px"
          }}>
            <h4 style={{ fontSize: "15px", fontWeight: "700", color: "var(--text-main)", margin: 0 }}>
              Entity Intersection & Differential Matrix
            </h4>

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: "16px" }}>
              {/* Shared Entities */}
              <div style={{ padding: "14px", background: "rgba(16, 185, 129, 0.06)", border: "1px solid rgba(16, 185, 129, 0.2)", borderRadius: "8px" }}>
                <div style={{ fontSize: "12px", fontWeight: "700", color: "var(--color-success)", marginBottom: "8px" }}>
                  🤝 Shared Entities ({comparison.shared_entities?.length || 0})
                </div>
                <div style={{ display: "flex", flexWrap: "wrap", gap: "6px" }}>
                  {(!comparison.shared_entities || comparison.shared_entities.length === 0) ? (
                    <span style={{ fontSize: "11px", color: "var(--text-muted)", fontStyle: "italic" }}>None</span>
                  ) : (
                    comparison.shared_entities.map((e, idx) => (
                      <span
                        key={idx}
                        onClick={() => onSelectEntity && onSelectEntity(e)}
                        style={{ fontSize: "11px", padding: "2px 6px", background: "#fff", border: "1px solid rgba(16, 185, 129, 0.3)", borderRadius: "4px", color: "var(--color-success)", cursor: "pointer" }}
                      >
                        {e}
                      </span>
                    ))
                  )}
                </div>
              </div>

              {/* Unique to Doc A */}
              <div style={{ padding: "14px", background: "rgba(99, 102, 241, 0.06)", border: "1px solid rgba(99, 102, 241, 0.2)", borderRadius: "8px" }}>
                <div style={{ fontSize: "12px", fontWeight: "700", color: "var(--color-accent)", marginBottom: "8px" }}>
                  Unique to Doc A ({comparison.unique_to_a?.length || 0})
                </div>
                <div style={{ display: "flex", flexWrap: "wrap", gap: "6px" }}>
                  {(!comparison.unique_to_a || comparison.unique_to_a.length === 0) ? (
                    <span style={{ fontSize: "11px", color: "var(--text-muted)", fontStyle: "italic" }}>None</span>
                  ) : (
                    comparison.unique_to_a.map((e, idx) => (
                      <span
                        key={idx}
                        onClick={() => onSelectEntity && onSelectEntity(e)}
                        style={{ fontSize: "11px", padding: "2px 6px", background: "#fff", border: "1px solid rgba(99, 102, 241, 0.3)", borderRadius: "4px", color: "var(--color-accent)", cursor: "pointer" }}
                      >
                        {e}
                      </span>
                    ))
                  )}
                </div>
              </div>

              {/* Unique to Doc B */}
              <div style={{ padding: "14px", background: "rgba(139, 92, 246, 0.06)", border: "1px solid rgba(139, 92, 246, 0.2)", borderRadius: "8px" }}>
                <div style={{ fontSize: "12px", fontWeight: "700", color: "var(--color-accent-purple)", marginBottom: "8px" }}>
                  Unique to Doc B ({comparison.unique_to_b?.length || 0})
                </div>
                <div style={{ display: "flex", flexWrap: "wrap", gap: "6px" }}>
                  {(!comparison.unique_to_b || comparison.unique_to_b.length === 0) ? (
                    <span style={{ fontSize: "11px", color: "var(--text-muted)", fontStyle: "italic" }}>None</span>
                  ) : (
                    comparison.unique_to_b.map((e, idx) => (
                      <span
                        key={idx}
                        onClick={() => onSelectEntity && onSelectEntity(e)}
                        style={{ fontSize: "11px", padding: "2px 6px", background: "#fff", border: "1px solid rgba(139, 92, 246, 0.3)", borderRadius: "4px", color: "var(--color-accent-purple)", cursor: "pointer" }}
                      >
                        {e}
                      </span>
                    ))
                  )}
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
