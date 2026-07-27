import React, { useState, useEffect, useRef } from "react";

const BACKEND_URL = "http://localhost:8000";

export default function App() {
  const [activeTab, setActiveTab] = useState("dashboard");
  const [images, setImages] = useState([]);
  const [backendOnline, setBackendOnline] = useState(false);
  const [selectedGalleryImages, setSelectedGalleryImages] = useState([]);
  
  // Upload States
  const [selectedFiles, setSelectedFiles] = useState([]);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [isUploading, setIsUploading] = useState(false);
  
  // Modal & OCR Inspect States
  const [selectedImgForModal, setSelectedImgForModal] = useState(null);
  const [modalOcrText, setModalOcrText] = useState("");
  const [modalOcrData, setModalOcrData] = useState(null);
  const [modalOcrChunks, setModalOcrChunks] = useState([]);
  const [modalPanelTab, setModalPanelTab] = useState("text"); // 'text' | 'chunks'
  const [modalViewMode, setModalViewMode] = useState("original"); // 'original' | 'overlay'
  const [modalLoadingText, setModalLoadingText] = useState(false);
  
  // RAG Chat & Search States
  const [chatSubTab, setChatSubTab] = useState("chat"); // 'chat' | 'search'
  const [chatInputText, setChatInputText] = useState("");
  const [chatHistory, setChatHistory] = useState([
    {
      id: "welcome",
      sender: "bot",
      text: "Welcome to the NTRO Document Intelligence Workspace. I am your local, secure AI assistant. Ask me questions based on the contents of your processed gallery documents.",
      sources: null
    }
  ]);
  const [chatLoading, setChatLoading] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState([]);
  const [searchLoading, setSearchLoading] = useState(false);
  
  // Global message alerts
  const [statusMsg, setStatusMsg] = useState({ text: "", type: "" });
  
  const fileInputRef = useRef(null);
  const abortControllerRef = useRef(null);
  const [isGenerating, setIsGenerating] = useState(false);

  // Fetch all images metadata
  const fetchImages = async () => {
    try {
      const res = await fetch(`${BACKEND_URL}/api/images`);
      if (res.ok) {
        const data = await res.json();
        setImages(data);
        setBackendOnline(true);
      } else {
        setBackendOnline(false);
      }
    } catch (err) {
      setBackendOnline(false);
    }
  };

  // Check health status of backend
  const checkHealth = async () => {
    try {
      const res = await fetch(`${BACKEND_URL}/api/health`);
      if (res.ok) {
        setBackendOnline(true);
      } else {
        setBackendOnline(false);
      }
    } catch (err) {
      setBackendOnline(false);
    }
  };

  useEffect(() => {
    checkHealth();
    fetchImages();
    const interval = setInterval(checkHealth, 5000);
    return () => clearInterval(interval);
  }, []);

  // Poll backend status periodically ONLY when at least one image is in the 'Processing' state
  useEffect(() => {
    const hasProcessing = images.some((img) => img.status === "Processing");
    if (hasProcessing) {
      const interval = setInterval(fetchImages, 2500);
      return () => clearInterval(interval);
    }
  }, [images]);

  // Update lists when tab changes
  useEffect(() => {
    if (activeTab === "gallery" || activeTab === "dashboard") {
      fetchImages();
    }
  }, [activeTab]);

  // Drag & Drop Handlers
  const [dragActive, setDragActive] = useState(false);
  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  };

  const processFiles = (files) => {
    const validFiles = [];
    const allowedTypes = ["image/png", "image/jpeg", "image/jpg"];
    const maxLimit = 10 * 1024 * 1024; // 10MB

    for (let file of files) {
      if (!allowedTypes.includes(file.type)) {
        showStatus(`File "${file.name}" rejected: Only PNG and JPG formats supported.`, "error");
        continue;
      }
      if (file.size > maxLimit) {
        showStatus(`File "${file.name}" rejected: Exceeds 10MB size limit.`, "error");
        continue;
      }
      validFiles.push(file);
    }

    if (validFiles.length > 0) {
      setSelectedFiles((prev) => [...prev, ...validFiles]);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      processFiles(Array.from(e.dataTransfer.files));
    }
  };

  const handleFileChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      processFiles(Array.from(e.target.files));
    }
  };

  const removeSelectedFile = (idx) => {
    setSelectedFiles((prev) => prev.filter((_, i) => i !== idx));
  };

  const showStatus = (text, type) => {
    setStatusMsg({ text, type });
    setTimeout(() => setStatusMsg({ text: "", type: "" }), 6000);
  };

  // Upload submitting queue
  const handleUploadSubmit = () => {
    if (selectedFiles.length === 0) return;
    
    setIsUploading(true);
    setUploadProgress(0);
    
    const xhr = new XMLHttpRequest();
    const formData = new FormData();
    
    selectedFiles.forEach((file) => {
      formData.append("files", file);
    });

    xhr.upload.addEventListener("progress", (e) => {
      if (e.lengthComputable) {
        const percent = Math.round((e.loaded / e.total) * 100);
        setUploadProgress(percent);
      }
    });

    xhr.addEventListener("load", () => {
      setIsUploading(false);
      if (xhr.status >= 200 && xhr.status < 300) {
        showStatus("Images uploaded successfully!", "success");
        setSelectedFiles([]);
        setUploadProgress(0);
        fetchImages();
      } else {
        const errDetail = JSON.parse(xhr.responseText || "{}").detail || "Upload failed.";
        showStatus(`Upload failed: ${errDetail}`, "error");
      }
    });

    xhr.addEventListener("error", () => {
      setIsUploading(false);
      showStatus("Network error occurred during upload. Check server connection.", "error");
    });

    xhr.open("POST", `${BACKEND_URL}/api/upload`);
    xhr.send(formData);
  };

  // Trigger OCR analysis asynchronously on backend
  const triggerOcr = async (e, imgId) => {
    e.stopPropagation(); // Avoid opening modal on button click
    
    try {
      const res = await fetch(`${BACKEND_URL}/api/images/${imgId}/ocr`, {
        method: "POST"
      });
      if (res.ok) {
        showStatus("Document analysis scheduled.", "success");
        fetchImages(); // Refresh to trigger loading status spinner
      } else {
        const data = await res.json();
        showStatus(`OCR trigger failed: ${data.detail || "Unknown error"}`, "error");
      }
    } catch (err) {
      showStatus("Network error triggering OCR parser.", "error");
    }
  };

  const handleToggleSelectImage = (e, id) => {
    e.stopPropagation();
    setSelectedGalleryImages(prev => 
      prev.includes(id) ? prev.filter(imgId => imgId !== id) : [...prev, id]
    );
  };

  const handleSelectAll = (e) => {
    if (e.target.checked) {
      setSelectedGalleryImages(images.map(img => img.id));
    } else {
      setSelectedGalleryImages([]);
    }
  };

  const handleDeleteSelected = async () => {
    if (selectedGalleryImages.length === 0) return;
    if (!window.confirm(`Are you sure you want to delete ${selectedGalleryImages.length} selected image(s)?`)) return;

    showStatus(`Deleting ${selectedGalleryImages.length} document(s)...`, "success");
    
    Promise.all(selectedGalleryImages.map(id => 
      fetch(`${BACKEND_URL}/api/images/${id}`, { method: "DELETE" })
    )).then(() => {
      setSelectedGalleryImages([]);
      fetchImages();
      showStatus("Deleted successfully.", "success");
    }).catch(() => {
      showStatus("Network error during bulk deletion.", "error");
    });
  };

  const handleProcessSelected = async () => {
    const targets = selectedGalleryImages.length > 0 
      ? images.filter(img => selectedGalleryImages.includes(img.id) && (img.status === "Uploaded" || img.status === "Failed"))
      : images.filter(img => img.status === "Uploaded" || img.status === "Failed");

    if (targets.length === 0) {
      showStatus("No unprocessed images selected or available.", "success");
      return;
    }
    
    showStatus(`Queuing ${targets.length} documents for analysis...`, "success");
    
    Promise.all(targets.map(img => 
      fetch(`${BACKEND_URL}/api/images/${img.id}/ocr`, { method: "POST" })
    )).then(() => {
      setSelectedGalleryImages([]);
      fetchImages();
    }).catch(() => {
      showStatus("Network error during batch processing.", "error");
    });
  };

  // Fetch and show OCR Detail Modal dialogue
  const handleOpenOcrModal = async (img) => {
    if (img.status !== "Completed") return; // Open modal only if processing succeeded
    
    setSelectedImgForModal(img);
    setModalViewMode("original");
    setModalPanelTab("text");
    setModalOcrText("");
    setModalOcrData(null);
    setModalOcrChunks([]);
    setModalLoadingText(true);
    
    try {
      // 1. Fetch clean text representation
      const textRes = await fetch(`${BACKEND_URL}/api/images/${img.id}/ocr/text`);
      if (textRes.ok) {
        const textData = await textRes.json();
        setModalOcrText(textData.text);
      } else {
        setModalOcrText("Failed to retrieve text extraction cache.");
      }

      // 2. Fetch structural coordinate metadata JSON
      const dataRes = await fetch(`${BACKEND_URL}/api/images/${img.id}/ocr/data`);
      if (dataRes.ok) {
        const ocrData = await dataRes.json();
        setModalOcrData(ocrData);
      }

      // 3. Fetch text chunks JSON
      const chunksRes = await fetch(`${BACKEND_URL}/api/images/${img.id}/ocr/chunks`);
      if (chunksRes.ok) {
        const chunksData = await chunksRes.json();
        setModalOcrChunks(chunksData);
      }
    } catch (err) {
      setModalOcrText("Network error loading cached document outputs.");
    } finally {
      setModalLoadingText(false);
    }
  };

  const handleCloseModal = () => {
    setSelectedImgForModal(null);
    setModalOcrText("");
    setModalOcrData(null);
    setModalOcrChunks([]);
    setModalPanelTab("text");
  };

  const deleteImage = async (e, imageId) => {
    e.stopPropagation(); // Avoid card click opening modal
    if (!window.confirm("Are you sure you want to delete this document physically?")) return;
    
    try {
      const res = await fetch(`${BACKEND_URL}/api/images/${imageId}`, {
        method: "DELETE"
      });
      if (res.ok) {
        showStatus("Image deleted successfully.", "success");
        fetchImages();
        if (selectedImgForModal && selectedImgForModal.id === imageId) {
          handleCloseModal();
        }
      } else {
        const data = await res.json();
        showStatus(`Deletion failed: ${data.detail || "Unknown error"}`, "error");
      }
    } catch (err) {
      showStatus("Network error. Failed to delete record.", "error");
    }
  };

  const handleSearchSubmit = async (e) => {
    if (e) e.preventDefault();
    if (!searchQuery.trim()) return;
    
    setSearchLoading(true);
    setSearchResults([]);
    
    try {
      const res = await fetch(`${BACKEND_URL}/api/images/search?query=${encodeURIComponent(searchQuery)}&limit=5`);
      if (res.ok) {
        const data = await res.json();
        setSearchResults(data);
      } else {
        showStatus("Failed to retrieve search results.", "error");
      }
    } catch (err) {
      showStatus("Network error performing semantic search.", "error");
    } finally {
      setSearchLoading(false);
    }
  };

  const handleStopGeneration = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
      setIsGenerating(false);
      setChatLoading(false);
    }
  };

  const handleChatSubmit = async (e) => {
    if (e) e.preventDefault();
    const queryText = chatInputText.trim();
    if (!queryText) return;
    
    const userMsgId = `user_${Date.now()}`;
    const botMsgId = `bot_${Date.now()}`;
    
    // Add user question to history
    const userMsg = { id: userMsgId, sender: "user", text: queryText, sources: null };
    // Add empty bot message to history instantly
    const botMsg = { id: botMsgId, sender: "bot", text: "", sources: null };
    
    setChatHistory((prev) => [...prev, userMsg, botMsg]);
    setChatInputText("");
    setChatLoading(true);
    setIsGenerating(true);
    
    abortControllerRef.current = new AbortController();
    
    try {
      // Filter out internal initial system messages before sending history
      const formattedHistory = chatHistory
        .filter(msg => msg.id !== "welcome" && msg.text)
        .map(msg => ({ sender: msg.sender, text: msg.text }));

      const res = await fetch(`${BACKEND_URL}/api/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: queryText, limit: 5, history: formattedHistory }),
        signal: abortControllerRef.current.signal
      });
      
      if (!res.ok) {
        setChatHistory((prev) => prev.map(msg => 
          msg.id === botMsgId ? { ...msg, text: "An error occurred on the local RAG backend trying to generate an answer." } : msg
        ));
        setChatLoading(false);
        setIsGenerating(false);
        return;
      }

      setChatLoading(false); // Stop loading spinner, streaming started
      
      const reader = res.body.getReader();
      const decoder = new TextDecoder("utf-8");
      let buffer = "";

      try {
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          
          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split("\n\n");
          buffer = lines.pop(); // Keep incomplete chunk in buffer
          
          for (const line of lines) {
            if (line.startsWith("data: ")) {
              try {
                const data = JSON.parse(line.substring(6));
                
                if (data.type === "sources") {
                  setChatHistory((prev) => prev.map(msg => 
                    msg.id === botMsgId ? { ...msg, sources: data.sources } : msg
                  ));
                } else if (data.type === "token") {
                  const tokenText = data.text;
                  setChatHistory((prev) => prev.map(msg => 
                    msg.id === botMsgId ? { ...msg, text: msg.text + tokenText } : msg
                  ));
                }
              } catch (err) {
                // Ignore parse errors on partial streams
              }
            }
          }
        }
      } finally {
        reader.releaseLock();
      }
    } catch (err) {
      if (err.name === 'AbortError') {
        setChatHistory((prev) => prev.map(msg => 
          msg.id === botMsgId ? { ...msg, text: msg.text + (msg.text === "" ? "[Generation stopped by user.]" : "\n\n[Generation stopped by user.]") } : msg
        ));
        showStatus("Generation stopped by user.", "success");
      } else {
        setChatHistory((prev) => prev.map(msg => 
          msg.id === botMsgId ? { ...msg, text: msg.text + "\n[Connection to backend lost.]" } : msg
        ));
      }
    } finally {
      setIsGenerating(false);
      abortControllerRef.current = null;
      setChatLoading(false);
    }
  };

  const formatBytes = (bytes) => {
    if (bytes === 0) return "0 Bytes";
    const k = 1024;
    const sizes = ["Bytes", "KB", "MB"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + " " + sizes[i];
  };

  return (
    <div className="app-container">
      {/* Sidebar Navigation */}
      <aside className="sidebar">
        <div className="logo-container">
          <div className="logo-icon">Ω</div>
          <h1 className="logo-text">Multimodal</h1>
        </div>
        <ul className="nav-links">
          <li className={`nav-item ${activeTab === "dashboard" ? "active" : ""}`} onClick={() => setActiveTab("dashboard")}>
            Dashboard
          </li>
          <li className={`nav-item ${activeTab === "upload" ? "active" : ""}`} onClick={() => setActiveTab("upload")}>
            Upload Documents
          </li>
          <li className={`nav-item ${activeTab === "gallery" ? "active" : ""}`} onClick={() => setActiveTab("gallery")}>
            Document Gallery
          </li>
          <li className={`nav-item ${activeTab === "chat" ? "active" : ""}`} onClick={() => setActiveTab("chat")}>
            Semantic Chat
          </li>
          <li className={`nav-item ${activeTab === "settings" ? "active" : ""}`} onClick={() => setActiveTab("settings")}>
            System Settings
          </li>
        </ul>
      </aside>

      {/* Main Panel Content */}
      <main className="main-content">
        <header className="header-panel">
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <div>
              <h2 className="header-title">Multimodal Offline RAG System</h2>
              <p className="header-subtitle">On-Premise Secure Document Intelligence Network</p>
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
              <span style={{
                display: "inline-block",
                width: "10px",
                height: "10px",
                borderRadius: "50%",
                backgroundColor: backendOnline ? "var(--color-success)" : "var(--color-danger)",
                boxShadow: backendOnline ? "0 0 8px var(--color-success)" : "0 0 8px var(--color-danger)"
              }}></span>
              <span style={{ fontSize: "12px", fontWeight: "600", color: backendOnline ? "var(--color-success)" : "var(--color-danger)" }}>
                {backendOnline ? "BACKEND ONLINE" : "BACKEND DISCONNECTED"}
              </span>
            </div>
          </div>
        </header>

        {/* Global status banner */}
        {statusMsg.text && (
          <div className={`status-message ${statusMsg.type}`}>
            {statusMsg.text}
          </div>
        )}

        {/* VIEW 1: DASHBOARD */}
        {activeTab === "dashboard" && (
          <div>
            <div className="metrics-grid">
              <div className="metric-card">
                <h4 className="metric-title">Indexed Documents</h4>
                <div className="metric-value">{images.length}</div>
              </div>
              <div className="metric-card">
                <h4 className="metric-title">OCR Completed</h4>
                <div className="metric-value">
                  {images.filter((img) => img.status === "Completed").length}
                </div>
              </div>
              <div className="metric-card">
                <h4 className="metric-title">Processing queue</h4>
                <div className="metric-value">
                  {images.filter((img) => img.status === "Processing").length}
                </div>
              </div>
            </div>

            <section className="panel">
              <h3 style={{ marginBottom: "16px", fontWeight: "600" }}>System Core Specifications</h3>
              <p style={{ color: "var(--text-muted)", fontSize: "14px", lineHeight: "1.6", marginBottom: "20px" }}>
                Welcome to the Multimodal Offline RAG System. This application is configured to run completely local in air-gapped secure networks. Currently, the <strong>Image Module (Ingestion + Preprocessing + OCR)</strong> is loaded.
              </p>
              <div style={{ padding: "16px", background: "var(--bg-sidebar)", borderRadius: "var(--radius-md)", border: "1px solid var(--border-glass)", fontSize: "13px" }}>
                <p style={{ marginBottom: "6px" }}><strong>Database Persistence:</strong> data/sqlite/metadata.db</p>
                <p style={{ marginBottom: "6px" }}><strong>Images Directory:</strong> data/uploads/</p>
                <p style={{ marginBottom: "6px" }}><strong>Binarization Outputs:</strong> data/processed/</p>
                <p><strong>Supported Formats:</strong> png, jpg, jpeg (Max 10MB per file)</p>
              </div>
            </section>
          </div>
        )}

        {/* VIEW 2: UPLOAD */}
        {activeTab === "upload" && (
          <section className="panel">
            <h3 style={{ marginBottom: "20px", fontWeight: "600" }}>Upload Image Documents</h3>
            
            <div 
              className={`dropzone ${dragActive ? "drag-active" : ""}`}
              onDragEnter={handleDrag}
              onDragOver={handleDrag}
              onDragLeave={handleDrag}
              onDrop={handleDrop}
              onClick={() => fileInputRef.current.click()}
            >
              <input 
                type="file" 
                ref={fileInputRef} 
                multiple 
                accept=".png,.jpg,.jpeg" 
                style={{ display: "none" }}
                onChange={handleFileChange}
              />
              <div className="upload-icon">⇪</div>
              <p style={{ fontSize: "16px", fontWeight: "500", marginBottom: "6px" }}>Drag & Drop images here</p>
              <p style={{ fontSize: "12px", color: "var(--text-muted)" }}>or click to browse local storage (PNG, JPG up to 10MB)</p>
            </div>

            {selectedFiles.length > 0 && (
              <div>
                <h4 style={{ marginBottom: "12px", fontSize: "14px", color: "var(--text-muted)" }}>Selected Queue ({selectedFiles.length} files)</h4>
                <div className="preview-list">
                  {selectedFiles.map((file, idx) => (
                    <div key={idx} className="preview-card">
                      <img src={URL.createObjectURL(file)} className="preview-thumb" alt="thumbnail" />
                      <div className="preview-name">{file.name}</div>
                      <div style={{ fontSize: "10px", color: "var(--text-muted)" }}>{formatBytes(file.size)}</div>
                      <button className="remove-btn" onClick={() => removeSelectedFile(idx)}>×</button>
                    </div>
                  ))}
                </div>

                <div className="upload-controls">
                  {isUploading && (
                    <div className="progress-container">
                      <div className="progress-bar-bg">
                        <div className="progress-bar-fill" style={{ width: `${uploadProgress}%` }}></div>
                      </div>
                      <div className="progress-text">Uploading stream: {uploadProgress}%</div>
                    </div>
                  )}
                  <div style={{ display: "flex", gap: "10px", marginLeft: "auto" }}>
                    <button className="btn btn-secondary" onClick={() => setSelectedFiles([])} disabled={isUploading}>
                      Clear Queue
                    </button>
                    <button className="btn btn-primary" onClick={handleUploadSubmit} disabled={isUploading}>
                      {isUploading ? "Uploading..." : `Upload ${selectedFiles.length} File(s)`}
                    </button>
                  </div>
                </div>
              </div>
            )}
          </section>
        )}

        {/* VIEW 3: GALLERY */}
        {activeTab === "gallery" && (
          <section className="panel">
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "20px" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "16px" }}>
                <h3 style={{ fontWeight: "600", margin: 0 }}>Document Storage</h3>
                {images.length > 0 && (
                  <label style={{ display: "flex", alignItems: "center", gap: "6px", fontSize: "14px", cursor: "pointer", color: "var(--text-muted)", borderLeft: "1px solid var(--border-glass)", paddingLeft: "16px" }}>
                    <input 
                      type="checkbox" 
                      checked={selectedGalleryImages.length === images.length && images.length > 0} 
                      onChange={handleSelectAll} 
                      style={{ accentColor: "var(--color-accent)", cursor: "pointer", width: "16px", height: "16px" }}
                    />
                    Select All
                  </label>
                )}
              </div>
              <div style={{ display: "flex", gap: "10px" }}>
                {selectedGalleryImages.length > 0 && (
                  <button className="btn btn-secondary" onClick={handleDeleteSelected} style={{ color: "var(--color-error)" }}>
                    🗑 Delete Selected ({selectedGalleryImages.length})
                  </button>
                )}
                <button className="btn btn-primary" onClick={handleProcessSelected} style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"></polygon>
                  </svg>
                  {selectedGalleryImages.length > 0 ? `Process Selected (${selectedGalleryImages.length})` : "Process All Unprocessed"}
                </button>
              </div>
            </div>
            
            {images.length === 0 ? (
              <div style={{ textAlign: "center", color: "var(--text-muted)", padding: "40px" }}>
                <p>No document images found in the index directory.</p>
                <p style={{ fontSize: "12px", marginTop: "6px" }}>Use the Upload panel to catalog images.</p>
              </div>
            ) : (
              <div className="gallery-grid">
                {images.map((img) => {
                  const isCompleted = img.status === "Completed";
                  const isProcessing = img.status === "Processing";
                  const isUploaded = img.status === "Uploaded";
                  const isFailed = img.status === "Failed";
                  
                  return (
                    <div 
                      key={img.id} 
                      className="gallery-card"
                      style={{ cursor: isCompleted ? "pointer" : "default" }}
                      onClick={() => handleOpenOcrModal(img)}
                    >
                      <div className="gallery-image-wrapper">
                        <input 
                          type="checkbox"
                          className="gallery-checkbox"
                          checked={selectedGalleryImages.includes(img.id)}
                          onChange={(e) => handleToggleSelectImage(e, img.id)}
                          onClick={(e) => e.stopPropagation()}
                        />
                        <img 
                          src={`${BACKEND_URL}/api/images/${img.id}/raw`} 
                          className="gallery-img" 
                          alt={img.filename} 
                          loading="lazy"
                        />
                        <button className="gallery-delete-btn" title="Delete Image" onClick={(e) => deleteImage(e, img.id)}>
                          🗑
                        </button>
                      </div>
                      
                      <div className="gallery-info">
                        <h4 className="gallery-name" title={img.filename}>{img.filename}</h4>
                        <div className="gallery-meta" style={{ marginBottom: "12px" }}>
                          <span>{formatBytes(img.size_bytes)}</span>
                          <span className={`status-badge ${img.status.toLowerCase()}`}>{img.status}</span>
                        </div>
                        
                        {/* Pulse Action controls for Ingest processes */}
                        {(isUploaded || isFailed) && (
                          <button className="btn btn-pulse" style={{ width: "100%", justifyContent: "center" }} onClick={(e) => triggerOcr(e, img.id)}>
                            🔍 Process OCR
                          </button>
                        )}
                        
                        {isProcessing && (
                          <div style={{ display: "flex", alignItems: "center", gap: "8px", justifyContent: "center", padding: "6px 0", fontSize: "12px", color: "var(--color-accent-purple)", fontWeight: "600" }}>
                            <div className="spinner"></div> Analyzing...
                          </div>
                        )}
                        
                        {isCompleted && (
                          <div style={{ fontSize: "11px", color: "var(--color-success)", fontWeight: "600", textAlign: "center", padding: "6px 0" }}>
                            ✓ Click to Inspect text
                          </div>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </section>
        )}

        {/* VIEW 4: CHAT / RAG WORKSPACE */}
        {activeTab === "chat" && (
          <section className="panel" style={{ display: "flex", flexDirection: "column", height: "calc(100vh - 160px)" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px" }}>
              <h3 style={{ fontWeight: "600" }}>RAG Document Intelligence</h3>
              <div className="toggle-group">
                <button 
                  className={`toggle-btn ${chatSubTab === "chat" ? "active" : ""}`}
                  onClick={() => setChatSubTab("chat")}
                >
                  Semantic Chat AI
                </button>
                <button 
                  className={`toggle-btn ${chatSubTab === "search" ? "active" : ""}`}
                  onClick={() => setChatSubTab("search")}
                >
                  Vector DB Search
                </button>
              </div>
            </div>

            {/* SUB-VIEW 1: SEMANTIC CHAT */}
            {chatSubTab === "chat" && (
              <div style={{ display: "flex", flexDirection: "column", flexGrow: 1, overflow: "hidden" }}>
                {/* Chat Log Window */}
                <div style={{
                  flexGrow: 1,
                  background: "var(--bg-sidebar)",
                  border: "1px solid var(--border-glass)",
                  borderRadius: "var(--radius-md)",
                  padding: "20px",
                  overflowY: "auto",
                  display: "flex",
                  flexDirection: "column",
                  gap: "16px",
                  marginBottom: "16px",
                  maxHeight: "calc(100vh - 350px)"
                }}>
                  {chatHistory.map((msg) => (
                    <div key={msg.id} style={{
                      display: "flex",
                      flexDirection: "column",
                      alignSelf: msg.sender === "user" ? "flex-end" : "flex-start",
                      maxWidth: "80%"
                    }}>
                      <div style={{
                        background: msg.sender === "user" ? "linear-gradient(135deg, var(--color-accent), var(--color-accent-purple))" : "var(--bg-card)",
                        border: "1px solid var(--border-glass)",
                        borderRadius: "var(--radius-md)",
                        padding: "14px 18px",
                        color: msg.sender === "user" ? "#fff" : "var(--text-main)",
                        fontSize: "14px",
                        lineHeight: "1.6",
                        whiteSpace: "pre-wrap",
                        boxShadow: "0 4px 12px rgba(0,0,0,0.05)"
                      }}>
                        {msg.text === "" && msg.sender === "bot" ? (
                          <div style={{ display: "flex", alignItems: "center", gap: "8px", opacity: 0.7 }}>
                            <div className="spinner" style={{ width: "14px", height: "14px", borderWidth: "2px" }}></div>
                            <span style={{ fontStyle: "italic", fontSize: "12px" }}>AI is computing answer...</span>
                          </div>
                        ) : (
                          msg.text
                        )}
                      </div>
                      
                      {/* Collapsible Citations References */}
                      {msg.sources && msg.sources.length > 0 && (
                        <details style={{ marginTop: "8px", fontSize: "11px", color: "var(--text-muted)", cursor: "pointer" }}>
                          <summary style={{ outline: "none", fontWeight: "600", color: "var(--color-accent)" }}>
                            Inspect Source Citations ({msg.sources.length})
                          </summary>
                          <div style={{
                            display: "flex",
                            flexDirection: "column",
                            gap: "8px",
                            padding: "10px",
                            background: "rgba(0, 0, 0, 0.03)",
                            borderRadius: "6px",
                            border: "1px solid var(--border-glass)",
                            marginTop: "6px"
                          }}>
                            {msg.sources.map((source, index) => (
                              <div key={source.chunk_id} style={{ display: "flex", flexDirection: "column", gap: "2px" }}>
                                <div style={{ display: "flex", justifyContent: "space-between", color: "var(--color-accent)", fontWeight: "600" }}>
                                  <span style={{ textDecoration: "underline", cursor: "pointer" }} onClick={() => {
                                    const img = images.find(i => i.id === source.metadata.document_id);
                                    if (img) handleOpenOcrModal(img);
                                  }}>
                                    Ref #{index + 1}: {source.metadata.source_file}
                                  </span>
                                  <span>{Math.round(source.score * 100)}% match</span>
                                </div>
                                <div style={{ fontStyle: "italic", color: "var(--text-muted)", paddingLeft: "6px" }}>
                                  "{source.text.substring(0, 120)}..."
                                </div>
                              </div>
                            ))}
                          </div>
                        </details>
                      )}
                    </div>
                  ))}
                  
                  {chatLoading && (
                    <div style={{ display: "flex", alignItems: "center", gap: "10px", color: "var(--color-accent-purple)", fontSize: "13px", paddingLeft: "10px" }}>
                      <div className="spinner"></div> On-Premise AI is compiling context answers...
                    </div>
                  )}
                </div>

                {/* Input form */}
                <form onSubmit={handleChatSubmit} style={{ display: "flex", gap: "12px" }}>
                  <input 
                    type="text"
                    placeholder="Ask a question about the document database (e.g. Find suggestion forms, summarize...)"
                    value={chatInputText}
                    onChange={(e) => setChatInputText(e.target.value)}
                    style={{
                      flexGrow: 1,
                      padding: "14px 20px",
                      borderRadius: "var(--radius-md)",
                      border: "1px solid var(--border-glass)",
                      background: "var(--bg-sidebar)",
                      color: "var(--text-main)",
                      fontSize: "14px",
                      outline: "none"
                    }}
                    disabled={isGenerating}
                  />
                  {isGenerating ? (
                    <button type="button" className="btn btn-secondary" onClick={handleStopGeneration} style={{ padding: "14px 28px", color: "var(--color-error)", borderColor: "var(--color-error)", display: "flex", alignItems: "center", gap: "6px" }}>
                      Stop Generating
                    </button>
                  ) : (
                    <button type="submit" className="btn btn-primary" style={{ padding: "14px 28px" }} disabled={chatLoading}>
                      Send Question
                    </button>
                  )}
                </form>
              </div>
            )}

            {/* SUB-VIEW 2: SEMANTIC SEARCH (DEBUGGER LOG) */}
            {chatSubTab === "search" && (
              <div style={{ display: "flex", flexDirection: "column", flexGrow: 1 }}>
                <p style={{ color: "var(--text-muted)", fontSize: "13px", marginBottom: "16px" }}>
                  Perform semantic searches directly against ChromaDB and inspect retrieved raw vector scores.
                </p>
                <form onSubmit={handleSearchSubmit} style={{ display: "flex", gap: "12px", marginBottom: "20px" }}>
                  <input 
                    type="text"
                    placeholder="Enter keywords or semantic query..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    style={{
                      flexGrow: 1,
                      padding: "14px 20px",
                      borderRadius: "var(--radius-md)",
                      border: "1px solid var(--border-glass)",
                      background: "var(--bg-sidebar)",
                      color: "var(--text-main)",
                      fontSize: "14px",
                      outline: "none"
                    }}
                  />
                  <button type="submit" className="btn btn-primary" disabled={searchLoading}>
                    {searchLoading ? <div className="spinner"></div> : "Find Vectors"}
                  </button>
                </form>

                {searchLoading ? (
                  <div style={{ display: "flex", flexGrow: 1, alignItems: "center", justifyContent: "center", minHeight: "200px" }}>
                    <div className="spinner" style={{ width: "36px", height: "36px" }}></div>
                  </div>
                ) : searchResults.length === 0 ? (
                  <div style={{ textAlign: "center", color: "var(--text-muted)", padding: "40px" }}>
                    <p>Type a search phrase above to search raw vectors.</p>
                  </div>
                ) : (
                  <div style={{ display: "flex", flexDirection: "column", gap: "12px", overflowY: "auto", maxHeight: "calc(100vh - 400px)" }}>
                    {searchResults.map((match) => (
                      <div 
                        key={match.chunk_id} 
                        style={{
                          background: "var(--bg-sidebar)",
                          border: "1px solid var(--border-glass)",
                          borderRadius: "var(--radius-md)",
                          padding: "16px",
                          display: "flex",
                          flexDirection: "column",
                          gap: "8px",
                          cursor: "pointer"
                        }}
                        onClick={() => {
                          const img = images.find(i => i.id === match.metadata.document_id);
                          if (img) handleOpenOcrModal(img);
                        }}
                      >
                        <div style={{ display: "flex", justifyContent: "space-between", fontSize: "12px" }}>
                          <span style={{ fontWeight: "700", color: "var(--color-success)" }}>
                            {Math.round(match.score * 100)}% Similarity Match
                          </span>
                          <span style={{ textDecoration: "underline", color: "var(--text-muted)" }}>
                            {match.metadata.source_file} (Index: #{match.metadata.chunk_index + 1})
                          </span>
                        </div>
                        <div style={{
                          fontSize: "13px",
                          fontFamily: "monospace",
                          color: "var(--text-main)",
                          lineHeight: "1.5",
                          background: "hsla(222, 20%, 6%, 0.3)",
                          padding: "10px",
                          borderRadius: "6px"
                        }}>
                          {match.text}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </section>
        )}

        {/* VIEW 5: SETTINGS */}
        {activeTab === "settings" && (
          <section className="panel">
            <h3 style={{ marginBottom: "20px", fontWeight: "600" }}>Offline System Settings</h3>
            <div style={{ display: "flex", flexDirection: "column", gap: "16px", maxWidth: "600px" }}>
              <div>
                <label style={{ display: "block", fontSize: "13px", fontWeight: "600", color: "var(--text-muted)", marginBottom: "6px" }}>
                  Backend Endpoint URL
                </label>
                <input 
                  type="text" 
                  value={BACKEND_URL} 
                  disabled 
                  style={{
                    width: "100%", 
                    padding: "12px", 
                    borderRadius: "var(--radius-md)", 
                    border: "1px solid var(--border-glass)", 
                    background: "var(--bg-sidebar)",
                    color: "var(--text-main)"
                  }} 
                />
              </div>
              <div style={{ display: "flex", gap: "16px" }}>
                <div style={{ flex: 1 }}>
                  <label style={{ display: "block", fontSize: "13px", fontWeight: "600", color: "var(--text-muted)", marginBottom: "6px" }}>
                    Environment Type
                  </label>
                  <div style={{ padding: "12px", border: "1px solid var(--border-glass)", borderRadius: "var(--radius-md)", background: "var(--bg-sidebar)", fontSize: "14px" }}>
                    Development (Offline Sandbox)
                  </div>
                </div>
                <div style={{ flex: 1 }}>
                  <label style={{ display: "block", fontSize: "13px", fontWeight: "600", color: "var(--text-muted)", marginBottom: "6px" }}>
                    Registry Database
                  </label>
                  <div style={{ padding: "12px", border: "1px solid var(--border-glass)", borderRadius: "var(--radius-md)", background: "var(--bg-sidebar)", fontSize: "14px" }}>
                    SQLite (metadata.db)
                  </div>
                </div>
              </div>
            </div>
          </section>
        )}
      </main>

      {/* DETAIL MODAL OVERLAY PORTAL */}
      {selectedImgForModal && (
        <div className="modal-backdrop" onClick={handleCloseModal}>
          <div className="modal-container" onClick={(e) => e.stopPropagation()}>
            <header className="modal-header">
              <div>
                <h3 style={{ fontSize: "18px", fontWeight: "700" }}>{selectedImgForModal.filename}</h3>
                <p style={{ fontSize: "12px", color: "var(--text-muted)" }}>Registry UUID: {selectedImgForModal.id}</p>
              </div>
              <button className="modal-close-x" onClick={handleCloseModal}>×</button>
            </header>
            
            <div className="modal-body">
              {/* Left Pane: Toggled Image Viewers */}
              <div className="modal-pane left">
                <div className="toggle-group">
                  <button 
                    className={`toggle-btn ${modalViewMode === "original" ? "active" : ""}`}
                    onClick={() => setModalViewMode("original")}
                  >
                    Original Image
                  </button>
                  <button 
                    className={`toggle-btn ${modalViewMode === "overlay" ? "active" : ""}`}
                    onClick={() => setModalViewMode("overlay")}
                  >
                    OCR Layout Grid
                  </button>
                </div>
                
                <div className="modal-viewer-frame">
                  {modalViewMode === "original" ? (
                    <img 
                      src={`${BACKEND_URL}/api/images/${selectedImgForModal.id}/raw`} 
                      className="modal-viewer-img" 
                      alt="original" 
                    />
                  ) : (
                    <img 
                      src={`${BACKEND_URL}/api/images/${selectedImgForModal.id}/ocr/overlay`} 
                      className="modal-viewer-img" 
                      alt="overlay" 
                    />
                  )}
                </div>
              </div>
              
              {/* Right Pane: OCR Text Content & DCS */}
              <div className="modal-pane right">
                {modalOcrData && (
                  <div className="dcs-container">
                    <span style={{ fontSize: "13px", fontWeight: "600", color: "var(--text-muted)" }}>
                      Document Confidence Score (DCS):
                    </span>
                    <span className={`dcs-badge-value ${
                      modalOcrData.document_confidence_score >= 85 ? "high" : 
                      modalOcrData.document_confidence_score >= 70 ? "medium" : "low"
                    }`}>
                      {modalOcrData.document_confidence_score}%
                    </span>
                    <span style={{ fontSize: "12px", color: "var(--text-muted)", marginLeft: "auto" }}>
                      Words: {modalOcrData.total_words_detected}
                    </span>
                  </div>
                )}
                
                {/* Right Pane view tab toggle switches */}
                <div className="toggle-group" style={{ marginBottom: "16px" }}>
                  <button 
                    className={`toggle-btn ${modalPanelTab === "text" ? "active" : ""}`}
                    onClick={() => setModalPanelTab("text")}
                  >
                    Full Text View
                  </button>
                  <button 
                    className={`toggle-btn ${modalPanelTab === "chunks" ? "active" : ""}`}
                    onClick={() => setModalPanelTab("chunks")}
                  >
                    Segmented Chunks ({modalOcrChunks.length})
                  </button>
                </div>
                
                {modalLoadingText ? (
                  <div style={{ flexGrow: 1, display: "flex", alignItems: "center", justifyContent: "center", background: "var(--bg-sidebar)", borderRadius: "var(--radius-md)" }}>
                    <div className="spinner" style={{ width: "32px", height: "32px" }}></div>
                  </div>
                ) : modalPanelTab === "text" ? (
                  <textarea 
                    className="ocr-text-area" 
                    readOnly 
                    value={modalOcrText}
                  />
                ) : (
                  <div style={{ display: "flex", flexDirection: "column", gap: "12px", overflowY: "auto", flexGrow: 1, maxHeight: "calc(80vh - 200px)" }}>
                    {modalOcrChunks.length === 0 ? (
                      <p style={{ color: "var(--text-muted)", fontSize: "14px", textAlign: "center", padding: "20px" }}>
                        No chunks generated.
                      </p>
                    ) : (
                      modalOcrChunks.map((chunk, index) => (
                        <div key={chunk.chunk_id} style={{
                          background: "var(--bg-sidebar)",
                          border: "1px solid var(--border-glass)",
                          borderRadius: "var(--radius-md)",
                          padding: "16px",
                          display: "flex",
                          flexDirection: "column",
                          gap: "8px"
                        }}>
                          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", fontSize: "12px", color: "var(--color-accent)", fontWeight: "600" }}>
                            <span>Chunk #{index + 1} (ID: {chunk.chunk_id.split('_').slice(-2).join('_')})</span>
                            <span style={{ color: "var(--text-muted)" }}>Size: {chunk.text.length} chars</span>
                          </div>
                          <div style={{
                            fontSize: "13px",
                            fontFamily: "monospace",
                            whiteSpace: "pre-wrap",
                            color: "var(--text-main)",
                            lineHeight: "1.5",
                            background: "hsla(222, 20%, 6%, 0.4)",
                            padding: "12px",
                            borderRadius: "6px",
                            border: "1px solid rgba(255,255,255,0.03)"
                          }}>
                            {chunk.text}
                          </div>
                          <div style={{ fontSize: "10px", color: "var(--text-muted)", display: "flex", justifyContent: "space-between" }}>
                            <span>Source: {chunk.metadata.source_file}</span>
                            <span>Confidence Score: {chunk.metadata.ocr_confidence}%</span>
                          </div>
                        </div>
                      ))
                    )}
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
