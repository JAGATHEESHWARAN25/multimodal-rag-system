import React, { useState, useEffect, useRef } from "react";

export default function DocumentIntelligenceModal({
  documentId,
  onClose,
  onAskAboutDocument,
  onSelectEntity,
  backendUrl,
  token
}) {
  const [data, setData] = useState(null);
  const [imageIntel, setImageIntel] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [activeTab, setActiveTab] = useState("content"); // 'content' | 'entities' | 'graph' | 'metadata'
  const [showBoundingBoxes, setShowBoundingBoxes] = useState(true);
  const [currentAudioTime, setCurrentAudioTime] = useState(0);

  const audioRef = useRef(null);

  useEffect(() => {
    if (!documentId) return;
    let isMounted = true;
    setLoading(true);
    setError(null);

    const fetchIntelligence = async () => {
      try {
        const headers = token ? { Authorization: `Bearer ${token}` } : {};
        
        // 1. Fetch document intelligence
        const res = await fetch(`${backendUrl}/api/documents/${documentId}/intelligence`, { headers });
        if (!res.ok) {
          throw new Error(`Failed to load document intelligence (${res.status})`);
        }
        const docData = await res.json();
        if (isMounted) setData(docData);

        // 2. If it's an image, also fetch vision intelligence
        const isImage = (docData.modality || "").toLowerCase() === "image" ||
          (docData.filename || "").toLowerCase().match(/\.(jpg|jpeg|png|webp|bmp)$/);

        if (isImage) {
          try {
            const imgRes = await fetch(`${backendUrl}/api/images/${documentId}/intelligence`, { headers });
            if (imgRes.ok) {
              const imgData = await imgRes.json();
              if (isMounted) setImageIntel(imgData);
            }
          } catch (e) {
            console.warn("Vision intelligence not available:", e);
          }
        }
      } catch (err) {
        if (isMounted) setError(err.message || "Failed to load intelligence");
      } finally {
        if (isMounted) setLoading(false);
      }
    };

    fetchIntelligence();
    return () => { isMounted = false; };
  }, [documentId, backendUrl, token]);

  if (!documentId) return null;

  const isAudio = (data?.modality || "").toLowerCase() === "audio" ||
    (data?.filename || "").toLowerCase().match(/\.(wav|mp3|ogg|m4a|flac)$/);

  const isImage = (data?.modality || "").toLowerCase() === "image" ||
    (data?.filename || "").toLowerCase().match(/\.(jpg|jpeg|png|webp|bmp)$/);

  const handleAudioTimeUpdate = () => {
    if (audioRef.current) {
      setCurrentAudioTime(audioRef.current.currentTime);
    }
  };

  const jumpToAudioTime = (sec) => {
    if (audioRef.current) {
      audioRef.current.currentTime = sec;
      audioRef.current.play().catch(() => {});
    }
  };

  const formatSec = (s) => {
    if (s == null) return "00:00";
    const mins = Math.floor(s / 60);
    const secs = Math.floor(s % 60);
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
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
        width: "100%", maxWidth: "960px", maxHeight: "90vh",
        display: "flex", flexDirection: "column",
        boxShadow: "0 20px 50px rgba(0,0,0,0.3)",
        overflow: "hidden"
      }} onClick={(e) => e.stopPropagation()}>
        {/* Modal Header */}
        <div style={{
          padding: "20px 24px",
          borderBottom: "1px solid var(--border-glass)",
          display: "flex", justifyContent: "space-between", alignItems: "center",
          background: "linear-gradient(90deg, rgba(99, 102, 241, 0.08), transparent)"
        }}>
          <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
            <div style={{
              width: "44px", height: "44px", borderRadius: "10px",
              background: isAudio ? "#ec4899" : isImage ? "#8b5cf6" : "var(--color-accent)",
              display: "flex", alignItems: "center", justifyContent: "center",
              color: "#fff", fontSize: "22px"
            }}>
              {isAudio ? "🎵" : isImage ? "🖼️" : "📄"}
            </div>
            <div>
              <div style={{ display: "flex", alignItems: "center", gap: "8px", flexWrap: "wrap" }}>
                <h3 style={{ margin: 0, fontSize: "17px", fontWeight: "700", color: "var(--text-main)" }}>
                  {data?.filename || documentId}
                </h3>
                {data?.modality && (
                  <span style={{
                    fontSize: "11px", fontWeight: "700",
                    padding: "2px 8px", borderRadius: "6px",
                    background: "rgba(99, 102, 241, 0.15)", color: "var(--color-accent)"
                  }}>
                    {data.modality.toUpperCase()}
                  </span>
                )}
                {data?.classification && (
                  <span style={{
                    fontSize: "10px", fontWeight: "700", padding: "2px 6px", borderRadius: "4px",
                    background: `${getClassificationColor(data.classification)}20`,
                    color: getClassificationColor(data.classification),
                    border: `1px solid ${getClassificationColor(data.classification)}50`
                  }}>
                    {data.classification}
                  </span>
                )}
              </div>
              <p style={{ margin: 0, fontSize: "12px", color: "var(--text-muted)", marginTop: "2px" }}>
                Deep Document Intelligence & Multimodal Knowledge Extraction
              </p>
            </div>
          </div>

          <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
            {onAskAboutDocument && data && (
              <button
                className="btn btn-primary"
                onClick={() => {
                  onClose();
                  onAskAboutDocument({
                    document_id: documentId,
                    filename: data.filename
                  });
                }}
                style={{ padding: "8px 16px", fontSize: "13px", display: "flex", alignItems: "center", gap: "6px" }}
              >
                <span>💬 Ask AI About This</span>
              </button>
            )}
            <button onClick={onClose} style={{
              background: "none", border: "none", fontSize: "24px",
              color: "var(--text-muted)", cursor: "pointer", padding: "4px 8px"
            }}>
              ×
            </button>
          </div>
        </div>

        {/* Navigation Tabs */}
        <div style={{
          display: "flex", gap: "16px", padding: "12px 24px",
          borderBottom: "1px solid var(--border-glass)", background: "rgba(0,0,0,0.02)"
        }}>
          <button
            className={`btn ${activeTab === "content" ? "btn-primary" : "btn-secondary"}`}
            style={{ padding: "6px 14px", fontSize: "12px" }}
            onClick={() => setActiveTab("content")}
          >
            {isAudio ? "🎵 Audio & Transcript" : isImage ? "🖼️ Image & Vision" : "📄 Content & Chunks"}
          </button>
          <button
            className={`btn ${activeTab === "entities" ? "btn-primary" : "btn-secondary"}`}
            style={{ padding: "6px 14px", fontSize: "12px" }}
            onClick={() => setActiveTab("entities")}
          >
            👤 Extracted Entities ({data?.entities?.length || 0})
          </button>
          <button
            className={`btn ${activeTab === "metadata" ? "btn-primary" : "btn-secondary"}`}
            style={{ padding: "6px 14px", fontSize: "12px" }}
            onClick={() => setActiveTab("metadata")}
          >
            ℹ️ Metadata & Quality
          </button>
        </div>

        {/* Modal Body */}
        <div style={{ padding: "24px", overflowY: "auto", flexGrow: 1, display: "flex", flexDirection: "column", gap: "20px" }}>
          {loading && (
            <div style={{ textAlign: "center", padding: "60px 0", color: "var(--color-accent)" }}>
              <div className="spinner" style={{ margin: "0 auto 12px" }}></div>
              <p style={{ fontSize: "14px", color: "var(--text-muted)" }}>Synthesizing multimodal document intelligence...</p>
            </div>
          )}

          {error && (
            <div style={{ padding: "16px", background: "rgba(239, 68, 68, 0.1)", border: "1px solid var(--color-danger)", borderRadius: "8px", color: "var(--color-danger)", fontSize: "14px" }}>
              ⚠️ {error}
            </div>
          )}

          {!loading && data && (
            <>
              {/* TAB 1: CONTENT (AUDIO / IMAGE / TEXT) */}
              {activeTab === "content" && (
                <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
                  {/* AUDIO MODALITY VIEWER */}
                  {isAudio && (
                    <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
                      <div style={{
                        padding: "16px 20px", background: "var(--bg-card)",
                        border: "1px solid var(--border-glass)", borderRadius: "var(--radius-md)",
                        display: "flex", flexDirection: "column", gap: "12px"
                      }}>
                        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                          <span style={{ fontSize: "13px", fontWeight: "600", color: "var(--text-main)" }}>
                            Audio Playback Stream (Offline In-Memory)
                          </span>
                          <span style={{ fontSize: "12px", color: "var(--color-accent)", fontWeight: "600" }}>
                            Current: {formatSec(currentAudioTime)}
                          </span>
                        </div>
                        <audio
                          ref={audioRef}
                          controls
                          onTimeUpdate={handleAudioTimeUpdate}
                          src={`${backendUrl}/api/images/${documentId}/file?token=${token || ""}`}
                          style={{ width: "100%", outline: "none" }}
                        />
                      </div>

                      {/* Synced Interactive Transcript */}
                      <div>
                        <h4 style={{ fontSize: "14px", fontWeight: "600", marginBottom: "10px", color: "var(--text-main)" }}>
                          Synchronized Transcript Chunks ({data.segments?.length || data.chunks?.length || 0})
                        </h4>
                        <p style={{ fontSize: "12px", color: "var(--text-muted)", marginBottom: "12px" }}>
                          Click any timestamp badge to jump audio playback to that exact segment.
                        </p>

                        <div style={{ display: "flex", flexDirection: "column", gap: "10px", maxHeight: "360px", overflowY: "auto" }}>
                          {(data.segments || data.chunks || []).map((seg, idx) => {
                            const start = seg.start_sec != null ? seg.start_sec : (seg.metadata?.start_sec ?? 0);
                            const end = seg.end_sec != null ? seg.end_sec : (seg.metadata?.end_sec ?? 0);
                            const isActive = currentAudioTime >= start && currentAudioTime <= (end || start + 5);

                            return (
                              <div
                                key={idx}
                                style={{
                                  padding: "12px 16px",
                                  background: isActive ? "rgba(99, 102, 241, 0.12)" : "var(--bg-card)",
                                  border: isActive ? "1px solid var(--color-accent)" : "1px solid var(--border-glass)",
                                  borderRadius: "8px",
                                  display: "flex", flexDirection: "column", gap: "6px",
                                  transition: "all 0.2s ease"
                                }}
                              >
                                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                                  <button
                                    onClick={() => jumpToAudioTime(start)}
                                    style={{
                                      padding: "3px 8px", borderRadius: "4px",
                                      background: isActive ? "var(--color-accent)" : "rgba(99, 102, 241, 0.15)",
                                      color: isActive ? "#fff" : "var(--color-accent)",
                                      border: "none", cursor: "pointer", fontSize: "11px", fontWeight: "700"
                                    }}
                                  >
                                    ▶ [{formatSec(start)} - {formatSec(end)}]
                                  </button>
                                  {seg.confidence != null && (
                                    <span style={{ fontSize: "11px", color: "var(--text-muted)" }}>
                                      {Math.round(seg.confidence * 100)}% confidence
                                    </span>
                                  )}
                                </div>
                                <p style={{ fontSize: "13px", color: "var(--text-main)", margin: 0, lineHeight: "1.5" }}>
                                  {seg.text || seg.content || "Empty transcript chunk"}
                                </p>
                              </div>
                            );
                          })}
                        </div>
                      </div>
                    </div>
                  )}

                  {/* IMAGE MODALITY VIEWER */}
                  {isImage && (
                    <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
                      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                        <span style={{ fontSize: "13px", fontWeight: "600", color: "var(--text-main)" }}>
                          Visual Asset Inspection & Florence-2 Vision Features
                        </span>
                        <label style={{ display: "flex", alignItems: "center", gap: "6px", fontSize: "12px", cursor: "pointer", color: "var(--text-muted)" }}>
                          <input
                            type="checkbox"
                            checked={showBoundingBoxes}
                            onChange={(e) => setShowBoundingBoxes(e.target.checked)}
                          />
                          Show OCR Bounding Boxes
                        </label>
                      </div>

                      {/* Image Viewer with Optional Bounding Box Overlay */}
                      <div style={{
                        position: "relative",
                        maxHeight: "380px",
                        background: "#000",
                        borderRadius: "var(--radius-md)",
                        overflow: "hidden",
                        display: "flex", alignItems: "center", justifyContent: "center"
                      }}>
                        <img
                          src={`${backendUrl}/api/images/${documentId}/file?token=${token || ""}`}
                          alt={data.filename}
                          style={{ maxWidth: "100%", maxHeight: "380px", objectFit: "contain" }}
                        />
                        {/* Bounding box overlays if enabled */}
                        {showBoundingBoxes && imageIntel?.bounding_boxes?.map((box, bIdx) => (
                          <div
                            key={bIdx}
                            style={{
                              position: "absolute",
                              left: `${box.x_min * 100}%`,
                              top: `${box.y_min * 100}%`,
                              width: `${(box.x_max - box.x_min) * 100}%`,
                              height: `${(box.y_max - box.y_min) * 100}%`,
                              border: "2px solid rgba(239, 68, 68, 0.8)",
                              backgroundColor: "rgba(239, 68, 68, 0.15)",
                              pointerEvents: "none"
                            }}
                            title={box.label || "Detected Text Region"}
                          />
                        ))}
                      </div>

                      {/* Florence-2 Captions / Detailed Regions */}
                      {imageIntel && (
                        <div style={{
                          padding: "14px 18px", background: "var(--bg-card)",
                          border: "1px solid var(--border-glass)", borderRadius: "var(--radius-md)",
                          display: "flex", flexDirection: "column", gap: "8px"
                        }}>
                          <div style={{ fontSize: "12px", fontWeight: "700", color: "var(--color-accent-purple)", textTransform: "uppercase" }}>
                            Florence-2 Dense Vision Caption
                          </div>
                          <div style={{ fontSize: "13px", color: "var(--text-main)", lineHeight: "1.5" }}>
                            {imageIntel.caption || imageIntel.detailed_caption || "No visual caption generated."}
                          </div>
                        </div>
                      )}
                    </div>
                  )}

                  {/* DOCUMENT / SPREADSHEET / TEXT CONTENT */}
                  {!isAudio && (
                    <div>
                      <h4 style={{ fontSize: "14px", fontWeight: "600", marginBottom: "10px", color: "var(--text-main)" }}>
                        Document Chunks & Extracted Text ({data.chunks?.length || 0})
                      </h4>
                      <div style={{ display: "flex", flexDirection: "column", gap: "10px", maxHeight: "360px", overflowY: "auto" }}>
                        {(data.chunks || []).map((ch, idx) => (
                          <div
                            key={idx}
                            style={{
                              padding: "12px 16px", background: "var(--bg-card)",
                              border: "1px solid var(--border-glass)", borderRadius: "8px",
                              display: "flex", flexDirection: "column", gap: "6px"
                            }}
                          >
                            <div style={{ display: "flex", justifyContent: "space-between", fontSize: "11px", color: "var(--text-muted)" }}>
                              <span style={{ fontWeight: "600" }}>
                                Chunk #{idx + 1} {ch.page_number ? `• Page ${ch.page_number}` : ""} {ch.slide_number ? `• Slide ${ch.slide_number}` : ""}
                              </span>
                              {ch.token_count && <span>{ch.token_count} tokens</span>}
                            </div>
                            <p style={{ fontSize: "13px", color: "var(--text-main)", margin: 0, lineHeight: "1.5" }}>
                              {ch.text || ch.content || "Empty chunk"}
                            </p>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* TAB 2: ENTITIES */}
              {activeTab === "entities" && (
                <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
                  <h4 style={{ fontSize: "14px", fontWeight: "600", color: "var(--text-main)", margin: 0 }}>
                    Extracted Named Entities & Concepts ({data.entities?.length || 0})
                  </h4>
                  <p style={{ fontSize: "12px", color: "var(--text-muted)", margin: 0 }}>
                    Click any entity to open its comprehensive Intelligence Dossier across all documents.
                  </p>

                  {(!data.entities || data.entities.length === 0) ? (
                    <p style={{ fontSize: "13px", color: "var(--text-muted)", fontStyle: "italic" }}>
                      No named entities detected in this document.
                    </p>
                  ) : (
                    <div style={{ display: "flex", flexWrap: "wrap", gap: "8px" }}>
                      {data.entities.map((ent, idx) => (
                        <button
                          key={idx}
                          onClick={() => onSelectEntity && onSelectEntity(ent.name || ent.text || ent)}
                          style={{
                            padding: "6px 12px", borderRadius: "8px",
                            background: "var(--bg-card)", border: "1px solid var(--border-glass)",
                            cursor: "pointer", display: "flex", alignItems: "center", gap: "6px"
                          }}
                        >
                          <span style={{ fontSize: "12px", fontWeight: "600", color: "var(--text-main)" }}>
                            {ent.name || ent.text || ent}
                          </span>
                          {(ent.type || ent.entity_type) && (
                            <span style={{
                              fontSize: "10px", fontWeight: "700", padding: "1px 5px",
                              borderRadius: "4px", background: "rgba(99, 102, 241, 0.15)", color: "var(--color-accent)"
                            }}>
                              {ent.type || ent.entity_type}
                            </span>
                          )}
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              )}

              {/* TAB 3: METADATA & QUALITY */}
              {activeTab === "metadata" && (
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "16px" }}>
                  <div style={{
                    padding: "16px", background: "var(--bg-card)",
                    border: "1px solid var(--border-glass)", borderRadius: "var(--radius-md)"
                  }}>
                    <h5 style={{ fontSize: "13px", fontWeight: "600", marginBottom: "12px", color: "var(--text-main)" }}>
                      File Attributes
                    </h5>
                    <div style={{ display: "flex", flexDirection: "column", gap: "8px", fontSize: "12px" }}>
                      <div><strong>Document ID:</strong> <span style={{ color: "var(--text-muted)" }}>{data.document_id || documentId}</span></div>
                      <div><strong>Filename:</strong> <span style={{ color: "var(--text-muted)" }}>{data.filename}</span></div>
                      <div><strong>Modality:</strong> <span style={{ color: "var(--color-accent)", textTransform: "uppercase" }}>{data.modality}</span></div>
                      <div><strong>Classification:</strong> <span style={{ color: getClassificationColor(data.classification) }}>{data.classification}</span></div>
                      <div><strong>SHA-256 Hash:</strong> <span style={{ color: "var(--text-muted)", wordBreak: "break-all" }}>{data.hash || data.sha256 || "N/A"}</span></div>
                    </div>
                  </div>

                  <div style={{
                    padding: "16px", background: "var(--bg-card)",
                    border: "1px solid var(--border-glass)", borderRadius: "var(--radius-md)"
                  }}>
                    <h5 style={{ fontSize: "13px", fontWeight: "600", marginBottom: "12px", color: "var(--text-main)" }}>
                      Processing Intelligence Metrics
                    </h5>
                    <div style={{ display: "flex", flexDirection: "column", gap: "8px", fontSize: "12px" }}>
                      <div><strong>Extraction Status:</strong> <span style={{ color: "var(--color-success)" }}>Completed</span></div>
                      <div><strong>Total Chunks:</strong> <span style={{ color: "var(--text-muted)" }}>{data.chunks?.length || 0}</span></div>
                      <div><strong>Entity Count:</strong> <span style={{ color: "var(--text-muted)" }}>{data.entities?.length || 0}</span></div>
                      {imageIntel && (
                        <>
                          <div><strong>Blur Variance:</strong> <span style={{ color: "var(--text-muted)" }}>{imageIntel.blur_variance?.toFixed(2) || "N/A"}</span></div>
                          <div><strong>Contrast Score:</strong> <span style={{ color: "var(--text-muted)" }}>{imageIntel.contrast_score?.toFixed(2) || "N/A"}</span></div>
                        </>
                      )}
                    </div>
                  </div>
                </div>
              )}
            </>
          )}
        </div>

        {/* Modal Footer */}
        <div style={{
          padding: "16px 24px",
          borderTop: "1px solid var(--border-glass)",
          display: "flex", justifyContent: "space-between", alignItems: "center",
          background: "var(--bg-sidebar)"
        }}>
          <button className="btn btn-secondary" onClick={onClose} style={{ padding: "8px 16px" }}>
            Close
          </button>
          {onAskAboutDocument && data && (
            <button
              className="btn btn-primary"
              onClick={() => {
                onClose();
                onAskAboutDocument({
                  document_id: documentId,
                  filename: data.filename
                });
              }}
              style={{ padding: "8px 18px" }}
            >
              Ask AI About This Document ➔
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
