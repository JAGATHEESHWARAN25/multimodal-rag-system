import React, { useState, useEffect, useRef, useContext } from "react";
import { AuthContext } from "./context/AuthContext";
import Login from "./pages/Login";
import UserManagement from "./components/UserManagement";
import ChatSidebar from "./components/ChatSidebar";
import AuditLogs from "./components/AuditLogs";
import KnowledgeGraphExplorer from "./components/KnowledgeGraphExplorer";
import IntelligenceDashboard from "./components/IntelligenceDashboard";
import AdvancedSearch from "./components/AdvancedSearch";
import TimelineView from "./components/TimelineView";
import EntityProfileModal from "./components/EntityProfileModal";
import DocumentIntelligenceModal from "./components/DocumentIntelligenceModal";
import DocumentComparison from "./components/DocumentComparison";
import MultiDocReport from "./components/MultiDocReport";

import DocViewer, { DocViewerRenderers } from "@cyntler/react-doc-viewer";

export const BACKEND_URL = "http://localhost:8000";

export default function App() {
  const { user, token, logout, loading } = useContext(AuthContext);
  
  // Custom fetch to include auth token
  const fetchWithAuth = async (url, options = {}) => {
    const headers = { ...options.headers };
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }
    return fetch(url, { ...options, headers });
  };

  const [activeTab, setActiveTab] = useState("dashboard");
  const [images, setImages] = useState([]);
  const [backendOnline, setBackendOnline] = useState(false);
  const [selectedGalleryImages, setSelectedGalleryImages] = useState([]);
  
  // Upload States
  const [selectedFiles, setSelectedFiles] = useState([]);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadClassification, setUploadClassification] = useState("PUBLIC");
  
  // Modal & OCR Inspect States
  const [selectedImgForModal, setSelectedImgForModal] = useState(null);
  const [modalOcrText, setModalOcrText] = useState("");
  const [modalOcrData, setModalOcrData] = useState(null);
  const [modalOcrChunks, setModalOcrChunks] = useState([]);
  const [modalPanelTab, setModalPanelTab] = useState("text"); // 'text' | 'chunks'
  const [modalViewMode, setModalViewMode] = useState("original"); // 'original' | 'overlay'
  const [modalLoadingText, setModalLoadingText] = useState(false);
  const [highlightCitation, setHighlightCitation] = useState(null);
  
  // RAG Chat & Search States
  const [chatSubTab, setChatSubTab] = useState("chat"); // 'chat' | 'search'
  const [chatInputText, setChatInputText] = useState("");
  const [chatAttachments, setChatAttachments] = useState([]); // [{ document_id, filename }]
  const [uploadingAttachment, setUploadingAttachment] = useState(false);
  const [chatHistory, setChatHistory] = useState([
    {
      id: "welcome",
      sender: "bot",
      text: "Welcome to the RAG System. I am your secure AI assistant. Ask me questions based on your processed documents.",
      sources: null
    }
  ]);
  const [chatLoading, setChatLoading] = useState(false);

  const [chatSessionId, setChatSessionId] = useState(null);
  const [sidebarRefresh, setSidebarRefresh] = useState(0);

  // Change Password States
  const [pwdCurrent, setPwdCurrent] = useState("");
  const [pwdNew, setPwdNew] = useState("");
  const [pwdConfirm, setPwdConfirm] = useState("");
  const [pwdLoading, setPwdLoading] = useState(false);
  const [pwdMsg, setPwdMsg] = useState({ text: "", type: "" });

  const handlePasswordChange = async (e) => {
    e.preventDefault();
    setPwdMsg({ text: "", type: "" });

    if (!pwdCurrent || !pwdNew || !pwdConfirm) {
      setPwdMsg({ text: "Please fill in all password fields.", type: "error" });
      return;
    }
    if (pwdNew !== pwdConfirm) {
      setPwdMsg({ text: "New password and confirmation do not match.", type: "error" });
      return;
    }
    if (pwdNew.length < 6) {
      setPwdMsg({ text: "New password must be at least 6 characters long.", type: "error" });
      return;
    }

    setPwdLoading(true);
    try {
      const res = await fetchWithAuth(`${BACKEND_URL}/api/auth/change-password`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          current_password: pwdCurrent,
          new_password: pwdNew
        })
      });

      const data = await res.json();
      if (res.ok) {
        setPwdMsg({ text: "Password updated successfully!", type: "success" });
        setPwdCurrent("");
        setPwdNew("");
        setPwdConfirm("");
      } else {
        setPwdMsg({ text: data.detail || "Failed to update password.", type: "error" });
      }
    } catch (err) {
      setPwdMsg({ text: "Network error updating password.", type: "error" });
    } finally {
      setPwdLoading(false);
    }
  };

  // Deep Intelligence Modals & Speech Query State
  const [selectedEntityForProfile, setSelectedEntityForProfile] = useState(null);
  const [selectedDocForIntelligence, setSelectedDocForIntelligence] = useState(null);
  const [isRecordingSpeech, setIsRecordingSpeech] = useState(false);
  const speechRecognitionRef = useRef(null);
  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);

  const toggleSpeechRecognition = () => {
    if (isRecordingSpeech) {
      stopSpeechRecognition();
    } else {
      startSpeechRecognition();
    }
  };

  const startSpeechRecognition = () => {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (SpeechRecognition) {
      try {
        const recognition = new SpeechRecognition();
        recognition.continuous = false;
        recognition.interimResults = true;
        recognition.lang = "en-US";

        recognition.onstart = () => {
          setIsRecordingSpeech(true);
          showStatus("Microphone listening... Speak your question now.", "success");
        };

        recognition.onresult = (event) => {
          let transcript = "";
          for (let i = event.resultIndex; i < event.results.length; i++) {
            transcript += event.results[i][0].transcript;
          }
          if (transcript) {
            setChatInputText(transcript);
          }
        };

        recognition.onerror = (event) => {
          console.warn("Speech recognition error:", event.error);
          setIsRecordingSpeech(false);
          if (event.error !== "no-speech") {
            showStatus(`Microphone notice: ${event.error}`, "error");
          }
        };

        recognition.onend = () => {
          setIsRecordingSpeech(false);
        };

        speechRecognitionRef.current = recognition;
        recognition.start();
        return;
      } catch (err) {
        console.warn("SpeechRecognition init failed, falling back to MediaRecorder", err);
      }
    }

    // Fallback: MediaRecorder stream sent to /api/audio/transcribe
    if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
      navigator.mediaDevices.getUserMedia({ audio: true })
        .then((stream) => {
          setIsRecordingSpeech(true);
          showStatus("Recording voice query... Click mic again when finished speaking.", "success");
          audioChunksRef.current = [];
          const recorder = new MediaRecorder(stream);
          mediaRecorderRef.current = recorder;

          recorder.ondataavailable = (e) => {
            if (e.data.size > 0) audioChunksRef.current.push(e.data);
          };

          recorder.onstop = async () => {
            setIsRecordingSpeech(false);
            stream.getTracks().forEach(track => track.stop());
            if (audioChunksRef.current.length === 0) return;

            showStatus("Transcribing speech query via offline engine...", "success");
            try {
              const audioBlob = new Blob(audioChunksRef.current, { type: "audio/wav" });
              const formData = new FormData();
              formData.append("file", audioBlob, "voice_query.wav");

              const res = await fetchWithAuth(`${BACKEND_URL}/api/audio/transcribe`, {
                method: "POST",
                body: formData
              });

              if (res.ok) {
                const data = await res.json();
                if (data.text) {
                  setChatInputText(data.text);
                  showStatus("Speech transcribed successfully!", "success");
                } else {
                  showStatus("No speech detected in audio.", "error");
                }
              } else {
                showStatus("Failed to transcribe audio clip.", "error");
              }
            } catch (err) {
              console.error(err);
              showStatus("Audio transcription network error.", "error");
            }
          };

          recorder.start();
        })
        .catch((err) => {
          console.error("Microphone access error:", err);
          showStatus("Microphone access denied or not available.", "error");
          setIsRecordingSpeech(false);
        });
    } else {
      showStatus("Speech recognition is not supported in this browser.", "error");
    }
  };

  const stopSpeechRecognition = () => {
    if (speechRecognitionRef.current) {
      try {
        speechRecognitionRef.current.stop();
      } catch (e) {}
      speechRecognitionRef.current = null;
    }
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== "inactive") {
      try {
        mediaRecorderRef.current.stop();
      } catch (e) {}
      mediaRecorderRef.current = null;
    }
    setIsRecordingSpeech(false);
  };

  const handleAskAboutDocument = (doc) => {
    if (!doc) return;
    setChatAttachments([{
      document_id: doc.document_id || doc.id,
      filename: doc.filename || doc.source_file || "Document"
    }]);
    setChatInputText("What are the key intelligence findings, entities, and summary of this document?");
    setActiveTab("chat");
  };

  const loadChatSession = async (sessionId) => {
    if (!sessionId) return;
    setChatSessionId(sessionId);
    localStorage.setItem("active_chat_session_id", sessionId);
    setChatLoading(true);
    try {
      const res = await fetchWithAuth(`${BACKEND_URL}/api/chat/sessions/${sessionId}`);
      if (res.ok) {
        const data = await res.json();
        const loadedHistory = [];
        if (data.messages && data.messages.length > 0) {
          data.messages.forEach(msg => {
            let sources = null;
            if (msg.citations_json) {
              try {
                sources = typeof msg.citations_json === "string" ? JSON.parse(msg.citations_json) : msg.citations_json;
              } catch (e) {}
            }
            loadedHistory.push({
              id: msg.id || `msg_${Math.random()}`,
              sender: msg.role === "user" ? "user" : "bot",
              text: msg.content || "",
              sources: sources
            });
          });
        }
        if (loadedHistory.length > 0) {
          setChatHistory(loadedHistory);
        } else {
          setChatHistory([{
            id: "welcome",
            sender: "bot",
            text: "Welcome to the RAG System. I am your secure AI assistant. Ask me questions based on your processed documents.",
            sources: null
          }]);
        }
      } else {
        setChatSessionId(null);
        localStorage.removeItem("active_chat_session_id");
        setChatHistory([{
          id: "welcome",
          sender: "bot",
          text: "Welcome to the RAG System. I am your secure AI assistant. Ask me questions based on your processed documents.",
          sources: null
        }]);
      }
    } catch (e) {
      console.error(e);
      setChatSessionId(null);
      localStorage.removeItem("active_chat_session_id");
    } finally {
      setChatLoading(false);
    }
  };

  const startNewChatSession = async () => {
    try {
      const res = await fetchWithAuth(`${BACKEND_URL}/api/chat/sessions`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ title: "New Chat Session" })
      });
      if (res.ok) {
        const session = await res.json();
        setChatSessionId(session.id);
        localStorage.setItem("active_chat_session_id", session.id);
        setSidebarRefresh(prev => prev + 1);
      } else {
        setChatSessionId(null);
        localStorage.removeItem("active_chat_session_id");
      }
    } catch (e) {
      console.error("Failed to create chat session", e);
      setChatSessionId(null);
      localStorage.removeItem("active_chat_session_id");
    }
    setChatHistory([{
      id: "welcome",
      sender: "bot",
      text: "Welcome to the RAG System. I am your secure AI assistant. Ask me questions based on your processed documents.",
      sources: null
    }]);
  };

  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState([]);
  const [searchLoading, setSearchLoading] = useState(false);
  
  // Global message alerts
  const [statusMsg, setStatusMsg] = useState({ text: "", type: "" });
  
  const fileInputRef = useRef(null);
  const chatFileInputRef = useRef(null);
  const abortControllerRef = useRef(null);
  const [isGenerating, setIsGenerating] = useState(false);

  // Dashboard Metrics
  const [dashboardData, setDashboardData] = useState(null);

  // Fetch all images metadata
  const fetchImages = async () => {
    try {
      const res = await fetchWithAuth(`${BACKEND_URL}/api/images`);
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
      const res = await fetchWithAuth(`${BACKEND_URL}/api/health`);
      if (res.ok) {
        setBackendOnline(true);
      } else {
        setBackendOnline(false);
      }
    } catch (err) {
      setBackendOnline(false);
    }
  };

  const fetchDashboard = async () => {
    try {
      const res = await fetchWithAuth(`${BACKEND_URL}/api/system/dashboard`);
      if (res.ok) {
        const data = await res.json();
        setDashboardData(data);
      }
    } catch (err) {
      console.error("Dashboard fetch failed", err);
    }
  };

  useEffect(() => {
    checkHealth();
    fetchImages();
    const interval = setInterval(checkHealth, 5000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    if (token) {
      const savedSessionId = localStorage.getItem("active_chat_session_id");
      if (savedSessionId) {
        loadChatSession(savedSessionId);
      }
    }
  }, [token]);

  // Poll backend status periodically when any document is in 'Processing' or 'Queued' state
  useEffect(() => {
    const hasProcessing = images.some((img) => 
      ["processing", "queued", "pending", "uploaded"].includes((img.status || "").toLowerCase())
    );
    if (hasProcessing) {
      const interval = setInterval(fetchImages, 2500);
      return () => clearInterval(interval);
    }
  }, [images]);

  // If a document is open in the modal and its status updates in the background, refresh its modal view
  useEffect(() => {
    if (selectedImgForModal) {
      const updated = images.find((img) => img.id === selectedImgForModal.id);
      if (updated && (updated.status || "").toLowerCase() !== (selectedImgForModal.status || "").toLowerCase()) {
        setSelectedImgForModal(updated);
        if ((updated.status || "").toLowerCase() === "completed") {
          handleOpenOcrModal(updated, highlightCitation);
        }
      }
    }
  }, [images]);

  // Update lists when tab changes
  useEffect(() => {
    if (activeTab === "gallery") {
      fetchImages();
    } else if (activeTab === "dashboard") {
      fetchDashboard();
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
    const allowedTypes = [
      "image/png", "image/jpeg", "image/jpg", "image/webp", "image/gif",
      "application/pdf", 
      "application/vnd.openxmlformats-officedocument.wordprocessingml.document", // DOCX
      "application/vnd.openxmlformats-officedocument.presentationml.presentation", // PPTX
      "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", // XLSX
      "application/vnd.ms-excel",
      "text/csv",
      "text/plain",
      "audio/wav", "audio/x-wav", "audio/mpeg", "audio/mp3", "audio/ogg", "audio/flac", "audio/x-m4a", "audio/m4a",
      "video/mp4", "video/x-msvideo", "video/quicktime", "video/x-matroska", "video/webm"
    ];
    const allowedExtensions = [".png", ".jpg", ".jpeg", ".webp", ".gif", ".pdf", ".docx", ".pptx", ".xlsx", ".csv", ".txt", ".wav", ".mp3", ".ogg", ".flac", ".m4a", ".mp4", ".avi", ".mov", ".mkv", ".webm"];
    const maxLimit = 100 * 1024 * 1024; // 100MB

    for (let file of files) {
      const ext = file.name.includes('.') ? '.' + file.name.split('.').pop().toLowerCase() : '';
      const isAllowed = allowedTypes.includes(file.type) || allowedExtensions.includes(ext);

      if (!isAllowed) {
        showStatus(`File "${file.name}" rejected: Supported formats include PDF, DOCX, PPTX, XLSX, CSV, TXT, Image (PNG/JPG), Audio (WAV/MP3), and Video (MP4/AVI/MOV/MKV/WEBM).`, "error");
        continue;
      }
      if (file.size > maxLimit) {
        showStatus(`File "${file.name}" rejected: Exceeds 50MB size limit.`, "error");
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

  const getFileTypeName = (filename) => {
    if (!filename) return "Document";
    const lower = filename.toLowerCase();
    if (lower.match(/\.(wav|mp3|ogg|flac|m4a)$/)) return "Audio recording";
    if (lower.match(/\.(jpg|jpeg|png|gif|webp|bmp|tiff)$/)) return "Image";
    if (lower.match(/\.(csv|xlsx|xls)$/)) return "Spreadsheet";
    if (lower.match(/\.(pptx|ppt)$/)) return "Presentation";
    if (lower.match(/\.(pdf|docx|doc|txt)$/)) return "Document";
    return "Document";
  };

  const getUploadSuccessMessage = (files) => {
    if (!files || files.length === 0) return "Files uploaded successfully!";
    
    // Group files by type using getFileTypeName
    const types = [...new Set(files.map(f => getFileTypeName(f.name)))];
    
    if (types.length === 1) {
      const type = types[0];
      if (type === "Spreadsheet") {
        return files.length === 1 ? "Spreadsheet uploaded successfully!" : "Spreadsheets uploaded successfully!";
      }
      if (type === "Audio recording") {
        return files.length === 1 ? "Audio recording uploaded successfully!" : "Audio files uploaded successfully!";
      }
      if (type === "Presentation") {
        return files.length === 1 ? "Presentation uploaded successfully!" : "Presentations uploaded successfully!";
      }
      if (type === "Image") {
        return "Images uploaded successfully!";
      }
      if (type === "Document") {
        return files.length === 1 ? "Document uploaded successfully!" : "Documents uploaded successfully!";
      }
      return `${type} uploaded successfully!`;
    }
    
    // Multiple distinct types
    const hasAudio = types.includes("Audio recording");
    const hasDocs = types.includes("Document") || types.includes("Spreadsheet") || types.includes("Presentation");
    if (hasAudio && hasDocs) {
      return "Documents and audio recordings uploaded successfully!";
    }
    
    return `${files.length} files uploaded successfully!`;
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
    formData.append("classification", uploadClassification);

    xhr.upload.addEventListener("progress", (e) => {
      if (e.lengthComputable) {
        const percent = Math.round((e.loaded / e.total) * 100);
        setUploadProgress(percent);
      }
    });

    xhr.addEventListener("load", () => {
      setIsUploading(false);
      if (xhr.status >= 200 && xhr.status < 300) {
        const msg = getUploadSuccessMessage(selectedFiles);
        showStatus(msg, "success");
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
    if (token && typeof xhr.setRequestHeader === "function") {
      xhr.setRequestHeader("Authorization", `Bearer ${token}`);
    }
    xhr.send(formData);
  };

  const cancelJob = async (e, documentId) => {
    if (e) e.stopPropagation();
    try {
      const res = await fetchWithAuth(`${BACKEND_URL}/api/jobs/${documentId}/cancel`, {
        method: "POST"
      });
      if (res.ok) {
        showStatus("Processing job cancelled.", "success");
        fetchImages();
      } else {
        const d = await res.json();
        showStatus(`Cancel failed: ${d.detail || "Error"}`, "error");
      }
    } catch (err) {
      showStatus("Network error cancelling job.", "error");
    }
  };

  const updateDocumentClassification = async (docId, newClass) => {
    try {
      const res = await fetchWithAuth(`${BACKEND_URL}/api/images/${docId}/metadata`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ classification: newClass })
      });
      if (res.ok) {
        showStatus(`Classification updated to ${newClass}`, "success");
        setSelectedImgForModal(prev => prev ? { ...prev, classification: newClass } : null);
        fetchImages();
      } else {
        const d = await res.json();
        showStatus(`Failed to update classification: ${d.detail || "Error"}`, "error");
      }
    } catch (e) {
      showStatus("Network error updating classification.", "error");
    }
  };

  // Trigger OCR analysis asynchronously on backend
  const triggerOcr = async (e, imgId) => {
    e.stopPropagation(); // Avoid opening modal on button click
    
    try {
      const res = await fetchWithAuth(`${BACKEND_URL}/api/images/${imgId}/ocr`, {
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
    const count = selectedGalleryImages.length;
    if (!window.confirm(`Are you sure you want to delete ${count} selected item(s)?`)) return;

    showStatus(`Deleting ${count} item(s)...`, "success");
    
    Promise.all(selectedGalleryImages.map(id => 
      fetchWithAuth(`${BACKEND_URL}/api/images/${id}`, { method: "DELETE" })
    )).then(() => {
      setSelectedGalleryImages([]);
      fetchImages();
      showStatus(`${count} item(s) deleted successfully.`, "success");
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
      fetchWithAuth(`${BACKEND_URL}/api/images/${img.id}/ocr`, { method: "POST" })
    )).then(() => {
      setSelectedGalleryImages([]);
      fetchImages();
    }).catch(() => {
      showStatus("Network error during batch processing.", "error");
    });
  };

  // Fetch and show OCR Detail Modal dialogue
  const handleOpenOcrModal = async (img, citation = null) => {
    // We intentionally removed the strict img.status !== "Completed" check here 
    // because the frontend state often lags behind the backend worker's completion.
    
    setSelectedImgForModal(img);
    setModalViewMode("original");
    setModalPanelTab("text");
    setModalOcrText("");
    setModalOcrData(null);
    setModalOcrChunks([]);
    setModalLoadingText(true);
    setHighlightCitation(citation);
    
    if (citation) {
        setModalPanelTab("chunks");
    }
    
    try {
      // 1. Fetch clean text representation
      const textRes = await fetchWithAuth(`${BACKEND_URL}/api/images/${img.id}/ocr/text`);
      if (textRes.ok) {
        const textData = await textRes.json();
        setModalOcrText(textData.text);
      } else {
        setModalOcrText("Failed to retrieve text extraction cache.");
      }

      // 2. Fetch structural coordinate metadata JSON
      const dataRes = await fetchWithAuth(`${BACKEND_URL}/api/images/${img.id}/ocr/data`);
      if (dataRes.ok) {
        const ocrData = await dataRes.json();
        setModalOcrData(ocrData);
      }

      // 3. Fetch text chunks JSON
      const chunksRes = await fetchWithAuth(`${BACKEND_URL}/api/images/${img.id}/ocr/chunks`);
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
    const targetDoc = images.find(img => img.id === imageId);
    const typeName = getFileTypeName(targetDoc?.filename);
    const lowerType = typeName.toLowerCase();

    if (!window.confirm(`Are you sure you want to delete this ${lowerType} physically?`)) return;
    
    try {
      const res = await fetchWithAuth(`${BACKEND_URL}/api/images/${imageId}`, {
        method: "DELETE"
      });
      if (res.ok) {
        showStatus(`${typeName} deleted successfully.`, "success");
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
      const res = await fetchWithAuth(`${BACKEND_URL}/api/images/search?query=${encodeURIComponent(searchQuery)}&limit=5`);
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

  const handleChatFileSelect = async (e) => {
    const selectedFiles = Array.from(e.target.files);
    if (!selectedFiles.length) return;

    setUploadingAttachment(true);
    showStatus("Uploading chat attachments...", "success");

    try {
      const formData = new FormData();
      selectedFiles.forEach((file) => formData.append("files", file));

      const res = await fetchWithAuth(`${BACKEND_URL}/api/upload`, {
        method: "POST",
        body: formData
      });

      if (res.ok) {
        const queuedJobs = await res.json();
        setChatAttachments((prev) => [...prev, ...queuedJobs]);
        showStatus(`Successfully attached ${queuedJobs.length} file(s).`, "success");
        fetchImages();
      } else {
        const errorData = await res.json();
        showStatus(errorData.detail || "Failed to upload chat attachments.", "error");
      }
    } catch (err) {
      showStatus("Network error uploading attachments.", "error");
    } finally {
      setUploadingAttachment(false);
      if (chatFileInputRef.current) chatFileInputRef.current.value = "";
    }
  };

  const removeChatAttachment = (docId) => {
    setChatAttachments((prev) => prev.filter((a) => a.document_id !== docId));
  };

  const handleChatSubmit = async (e) => {
    if (e) e.preventDefault();
    const queryText = chatInputText.trim();
    if (!queryText && !chatAttachments.length) return;
    
    const userMsgId = `user_${Date.now()}`;
    const botMsgId = `bot_${Date.now()}`;
    
    const attachedFileIds = chatAttachments.map((a) => a.document_id);
    const attachedFileNames = chatAttachments.map((a) => a.filename);
    
    const userMsg = {
      id: userMsgId,
      sender: "user",
      text: queryText || "[Querying attached files]",
      attachments: attachedFileNames,
      sources: null
    };
    
    const botMsg = {
      id: botMsgId,
      sender: "bot",
      text: "",
      input_summary: null,
      related_knowledge: null,
      confidence: null,
      sources: null
    };
    
    setChatHistory((prev) => [...prev, userMsg, botMsg]);
    setChatInputText("");
    setChatAttachments([]);
    setChatLoading(true);
    setIsGenerating(true);
    
    abortControllerRef.current = new AbortController();
    
    try {
      let currentSessionId = chatSessionId;
      if (!currentSessionId) {
        try {
          const titleText = (queryText || "Chat Analysis").slice(0, 30);
          const sRes = await fetchWithAuth(`${BACKEND_URL}/api/chat/sessions`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ title: titleText })
          });
          if (sRes.ok) {
            const sData = await sRes.json();
            currentSessionId = sData.id;
            setChatSessionId(currentSessionId);
            localStorage.setItem("active_chat_session_id", currentSessionId);
            setSidebarRefresh(prev => prev + 1);
          }
        } catch (err) {
          console.error("Failed to auto-create session on first chat message", err);
        }
      }

      const formattedHistory = chatHistory
        .filter((msg) => msg.id !== "welcome" && msg.text)
        .map((msg) => ({ sender: msg.sender, text: msg.text }));

      const res = await fetchWithAuth(`${BACKEND_URL}/api/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          query: queryText || "Summarize and analyze these attached files",
          file_ids: attachedFileIds,
          limit: 5,
          history: formattedHistory,
          use_graph_expansion: true,
          session_id: currentSessionId
        }),
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

      setChatLoading(false);
      
      const reader = res.body.getReader();
      const decoder = new TextDecoder("utf-8");
      let buffer = "";

      try {
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          
          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split("\n\n");
          buffer = lines.pop();
          
          for (const line of lines) {
            if (line.startsWith("data: ")) {
              try {
                const data = JSON.parse(line.substring(6));
                
                if (data.type === "input_summary") {
                  setChatHistory((prev) => prev.map(msg => 
                    msg.id === botMsgId ? { ...msg, input_summary: data.summary } : msg
                  ));
                } else if (data.type === "related_knowledge") {
                  setChatHistory((prev) => prev.map(msg => 
                    msg.id === botMsgId ? {
                      ...msg,
                      related_knowledge: {
                        related_documents: data.related_documents,
                        related_images: data.related_images,
                        related_entities: data.related_entities,
                        relationships: data.relationships
                      }
                    } : msg
                  ));
                } else if (data.type === "confidence") {
                  setChatHistory((prev) => prev.map(msg => 
                    msg.id === botMsgId ? { ...msg, confidence: data.confidence } : msg
                  ));
                } else if (data.type === "sources") {
                  setChatHistory((prev) => prev.map(msg => 
                    msg.id === botMsgId ? { ...msg, sources: data.sources } : msg
                  ));
                } else if (data.type === "token") {
                  const tokenText = data.text;
                  setChatHistory((prev) => prev.map(msg => 
                    msg.id === botMsgId ? { ...msg, text: msg.text + tokenText } : msg
                  ));
                } else if (data.type === "timing") {
                  setChatHistory((prev) => prev.map(msg => 
                    msg.id === botMsgId ? { ...msg, timing: data.timing } : msg
                  ));
                }
              } catch (err) {
                // Ignore parse errors on partial stream chunks
              }
            }
          }
        }
      } finally {
        reader.releaseLock();
        setSidebarRefresh(prev => prev + 1);
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
      setSidebarRefresh(prev => prev + 1);
    }
  };

  const formatBytes = (bytes) => {
    if (bytes === 0) return "0 Bytes";
    const k = 1024;
    const sizes = ["Bytes", "KB", "MB"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + " " + sizes[i];
  };
  if (loading) return <div>Loading...</div>;
  if (!user) return <Login />;

  return (
    <div className="app-container">
      {/* Sidebar Navigation */}
      <aside className="sidebar">
        <div className="logo-container">
          <div className="logo-icon">R</div>
          <h1 className="logo-text">RAG System</h1>
        </div>
        <ul className="nav-menu">
          <li className={`nav-item ${activeTab === "dashboard" ? "active" : ""}`} onClick={() => setActiveTab("dashboard")}>
            Dashboard
          </li>
          <li className={`nav-item ${activeTab === "search" ? "active" : ""}`} onClick={() => setActiveTab("search")}>
            Advanced Search
          </li>
          <li className={`nav-item ${activeTab === "timeline" ? "active" : ""}`} onClick={() => setActiveTab("timeline")}>
            Evidence Timeline
          </li>
          <li className={`nav-item ${activeTab === "upload" ? "active" : ""}`} onClick={() => setActiveTab("upload")}>
            Upload Documents
          </li>
          <li className={`nav-item ${activeTab === "gallery" ? "active" : ""}`} onClick={() => setActiveTab("gallery")}>
            Document Gallery
          </li>
          <li className={`nav-item ${activeTab === "compare" ? "active" : ""}`} onClick={() => setActiveTab("compare")}>
            Doc Comparison
          </li>
          <li className={`nav-item ${activeTab === "report" ? "active" : ""}`} onClick={() => setActiveTab("report")}>
            Multi-Doc Report
          </li>
          <li className={`nav-item ${activeTab === "chat" ? "active" : ""}`} onClick={() => setActiveTab("chat")}>
            Semantic Chat
          </li>
          <li className={`nav-item ${activeTab === "graph" ? "active" : ""}`} onClick={() => setActiveTab("graph")}>
            Knowledge Graph
          </li>
          <li className={`nav-item ${activeTab === "users" ? "active" : ""}`} onClick={() => setActiveTab("users")}>
            User Management
          </li>
          <li className={`nav-item ${activeTab === "settings" ? "active" : ""}`} onClick={() => setActiveTab("settings")}>
            System Settings
          </li>
          <li className={`nav-item ${activeTab === "audit" ? "active" : ""}`} onClick={() => setActiveTab("audit")}>
            Audit Logs
          </li>
        </ul>
        {/* Auth Info & Logout */}
        <div style={{ marginTop: 'auto', padding: '1rem', borderTop: '1px solid #333', textAlign: 'center' }}>
          <div style={{ fontSize: '13px', fontWeight: '600', color: 'var(--text-main)', marginBottom: '10px' }}>👤 {user.username}</div>
          <button 
            onClick={logout}
            style={{ width: '100%', padding: '8px', background: '#333', color: '#ff4d4f', border: 'none', borderRadius: '4px', cursor: 'pointer' }}
          >
            Logout
          </button>
        </div>
      </aside>

      {/* Main Panel Content */}
      <main className="main-content">
        <header className="header-panel">
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <div>
              <h2 className="header-title">RAG System</h2>
              <p className="header-subtitle">Retrieval-Augmented Generation Workspace</p>
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

        {/* VIEW 1: INTELLIGENCE DASHBOARD */}
        {activeTab === "dashboard" && (
          <section className="panel" style={{ padding: "10px" }}>
            <IntelligenceDashboard
              backendUrl={BACKEND_URL}
              token={token}
              onNavigate={(tab) => setActiveTab(tab)}
              onSelectEntity={(ent) => setSelectedEntityForProfile(ent)}
            />
          </section>
        )}

        {/* VIEW: ADVANCED SEARCH */}
        {activeTab === "search" && (
          <section className="panel">
            <AdvancedSearch
              backendUrl={BACKEND_URL}
              token={token}
              onOpenIntelligence={(id) => setSelectedDocForIntelligence(id)}
              onAskInChat={handleAskAboutDocument}
              onSelectEntity={(ent) => setSelectedEntityForProfile(ent)}
            />
          </section>
        )}

        {/* VIEW: TIMELINE */}
        {activeTab === "timeline" && (
          <section className="panel">
            <TimelineView
              backendUrl={BACKEND_URL}
              token={token}
              onOpenIntelligence={(id) => setSelectedDocForIntelligence(id)}
              onSelectEntity={(ent) => setSelectedEntityForProfile(ent)}
            />
          </section>
        )}

        {/* VIEW: DOCUMENT COMPARISON */}
        {activeTab === "compare" && (
          <section className="panel">
            <DocumentComparison
              documents={images}
              backendUrl={BACKEND_URL}
              token={token}
              onSelectEntity={(ent) => setSelectedEntityForProfile(ent)}
              onOpenIntelligence={(id) => setSelectedDocForIntelligence(id)}
            />
          </section>
        )}

        {/* VIEW: MULTI-DOC REPORT */}
        {activeTab === "report" && (
          <section className="panel">
            <MultiDocReport
              documents={images}
              backendUrl={BACKEND_URL}
              token={token}
              onSelectEntity={(ent) => setSelectedEntityForProfile(ent)}
            />
          </section>
        )}

        {/* VIEW: KNOWLEDGE GRAPH EXPLORER */}
        {activeTab === "graph" && (
          <section className="panel" style={{ minHeight: "calc(100vh - 120px)" }}>
            <KnowledgeGraphExplorer
              token={token}
              onSelectEntity={(ent) => setSelectedEntityForProfile(ent)}
              onOpenDocument={(id) => setSelectedDocForIntelligence(id)}
            />
          </section>
        )}

        {/* VIEW: AUDIT LOGS */}
        {activeTab === "audit" && (
          <section className="panel" style={{ height: "calc(100vh - 120px)" }}>
            <h3 style={{ marginBottom: "20px", fontWeight: "600" }}>System Audit Logs</h3>
            <AuditLogs token={token} />
          </section>
        )}

        {/* VIEW 2: UPLOAD */}
        {activeTab === "upload" && (
          <section className="panel">
            <h3 style={{ marginBottom: "20px", fontWeight: "600" }}>Upload Documents & Audio</h3>
            
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
                accept=".png,.jpg,.jpeg,.webp,.gif,.pdf,.docx,.pptx,.txt,.csv,.xlsx,.wav,.mp3,.ogg,.flac,.m4a,.mp4,.avi,.mov,.mkv,.webm,audio/*,video/*" 
                style={{ display: "none" }}
                onChange={handleFileChange}
              />
              <div className="upload-icon">⇪</div>
              <p style={{ fontSize: "16px", fontWeight: "500", marginBottom: "6px" }}>Drag & Drop files here</p>
              <p style={{ fontSize: "12px", color: "var(--text-muted)" }}>or click to browse local storage (PDF, DOCX, PPTX, Images, Audio, Video [MP4, AVI, MOV, MKV, WEBM] up to 100MB)</p>
            </div>

            {selectedFiles.length > 0 && (
              <div>
                <h4 style={{ marginBottom: "12px", fontSize: "14px", color: "var(--text-muted)" }}>Selected Queue ({selectedFiles.length} files)</h4>
                <div className="preview-list">
                  {selectedFiles.map((file, idx) => (
                    <div key={idx} className="preview-card">
                      {file.type?.startsWith("image/") || file.name.match(/\.(png|jpe?g|webp|gif)$/i) ? (
                        <img src={URL.createObjectURL(file)} className="preview-thumb" alt="thumbnail" />
                      ) : (
                        <div className="preview-thumb" style={{ display: "flex", alignItems: "center", justifyContent: "center", fontSize: "22px", background: "rgba(255,255,255,0.05)" }}>
                          {file.name.match(/\.(mp4|avi|mov|mkv|webm)$/i) || file.type?.startsWith("video/") ? "🎥"
                           : file.name.match(/\.(wav|mp3|ogg|flac|m4a)$/i) || file.type?.startsWith("audio/") ? "🎵"
                           : file.name.match(/\.(csv|xlsx)$/i) ? "📊"
                           : file.name.match(/\.pptx$/i) ? "📽️"
                           : file.name.match(/\.pdf$/i) ? "📕"
                           : "📄"}
                        </div>
                      )}
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
                {user?.role === "SYSTEM_ADMIN" && selectedGalleryImages.length > 0 && (
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
                <p>No documents or audio recordings found in the index directory.</p>
                <p style={{ fontSize: "12px", marginTop: "6px" }}>Use the Upload panel to catalog documents and audio recordings.</p>
              </div>
            ) : (
              <div className="gallery-grid">
                {images.map((img) => {
                  const statusLower = (img.status || "").toLowerCase();
                  const isCompleted = statusLower === "completed";
                  const isProcessing = statusLower === "processing" || statusLower === "queued";
                  const isUploaded = statusLower === "uploaded" || statusLower === "pending";
                  const isFailed = statusLower === "failed";
                  
                  return (
                    <div 
                      key={img.id} 
                      className="gallery-card"
                      style={{ cursor: "pointer" }}
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
                        {img.filename && img.filename.toLowerCase().match(/\.(jpg|jpeg|png|gif|webp|pdf)$/) ? (
                          <img 
                            src={`${BACKEND_URL}/api/images/${img.id}/thumbnail?token=${localStorage.getItem('token') || token}`} 
                            className="gallery-img" 
                            alt={img.filename} 
                            loading="lazy"
                            onError={(e) => {
                              e.target.style.display = 'none';
                              if (e.target.nextSibling) {
                                e.target.nextSibling.style.display = 'flex';
                              }
                            }}
                          />
                        ) : null}
                        <div className="gallery-img" style={{ display: img.filename && img.filename.toLowerCase().match(/\.(jpg|jpeg|png|gif|webp|pdf)$/) ? 'none' : 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', background: 'var(--bg-panel)', color: 'var(--text-muted)' }}>
                          <div style={{ fontSize: '40px', marginBottom: '10px' }}>
                            {img.filename?.toLowerCase().match(/\.(mp4|avi|mov|mkv|webm)$/) ? '🎥'
                             : img.filename?.toLowerCase().match(/\.(wav|mp3|ogg|flac|m4a)$/) ? '🎵'
                             : img.filename?.toLowerCase().match(/\.(csv|xlsx|xls)$/) ? '📊'
                             : img.filename?.toLowerCase().match(/\.(pptx|ppt)$/) ? '📽️'
                             : img.filename?.toLowerCase().match(/\.(docx|doc)$/) ? '📝'
                             : img.filename?.toLowerCase().match(/\.pdf$/) ? '📕'
                             : '📄'}
                          </div>
                          <div style={{ fontSize: '12px', fontWeight: 'bold' }}>{img.filename ? img.filename.split('.').pop().toUpperCase() : 'DOCUMENT'} FILE</div>
                        </div>
                        {user?.role === "SYSTEM_ADMIN" && (
                          <button className="gallery-delete-btn" title={`Delete ${getFileTypeName(img.filename)}`} onClick={(e) => deleteImage(e, img.id)}>
                            🗑
                          </button>
                        )}
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
                            {img.filename?.toLowerCase().match(/\.(mp4|avi|mov|mkv|webm)$/) ? "🎬 Process Video Intelligence"
                             : img.filename?.toLowerCase().match(/\.(wav|mp3|ogg|flac|m4a)$/) ? "🎙️ Transcribe Audio"
                             : "🔍 Process Document"}
                          </button>
                        )}
                        
                        {isProcessing && (
                          <div style={{ display: "flex", alignItems: "center", gap: "8px", justifyContent: "space-between", padding: "6px 0", fontSize: "12px", color: "var(--color-accent-purple)", fontWeight: "600" }}>
                            <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                              <div className="spinner"></div> Analyzing...
                            </div>
                            <button 
                              className="btn btn-secondary" 
                              style={{ padding: "2px 8px", fontSize: "11px", color: "var(--color-error)", borderColor: "var(--color-error)" }} 
                              onClick={(e) => cancelJob(e, img.id)}
                            >
                              Cancel
                            </button>
                          </div>
                        )}
                        
                        {isCompleted && (
                          <div style={{ display: "flex", gap: "6px", marginTop: "6px" }}>
                            <button
                              className="btn btn-secondary"
                              style={{ flex: 1, padding: "4px 4px", fontSize: "11px", color: "var(--color-accent)" }}
                              onClick={(e) => {
                                e.stopPropagation();
                                setSelectedDocForIntelligence(img.id);
                              }}
                            >
                              🧠 Dossier
                            </button>
                            <button
                              className="btn btn-secondary"
                              style={{ flex: 1, padding: "4px 4px", fontSize: "11px" }}
                              onClick={(e) => {
                                e.stopPropagation();
                                handleAskAboutDocument({ document_id: img.id, filename: img.filename });
                              }}
                            >
                              💬 Ask AI
                            </button>
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
          <section className="panel" style={{ display: "flex", flexDirection: "row", height: "calc(100vh - 160px)", padding: 0, overflow: "hidden" }}>
            <ChatSidebar 
              activeSessionId={chatSessionId}
              onSelectSession={loadChatSession}
              onNewSession={startNewChatSession}
              backendUrl={BACKEND_URL}
              token={token}
              triggerRefresh={sidebarRefresh}
            />
            <div style={{ display: "flex", flexDirection: "column", flexGrow: 1, padding: "24px", overflow: "hidden" }}>
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
                      
                      {/* Input Summary Box */}
                      {msg.input_summary && (
                        <div style={{
                          marginTop: "8px",
                          padding: "10px 14px",
                          background: "rgba(99, 102, 241, 0.08)",
                          borderRadius: "8px",
                          border: "1px solid rgba(99, 102, 241, 0.2)",
                          fontSize: "12px",
                          color: "var(--text-main)"
                        }}>
                          <div style={{ fontWeight: "600", color: "var(--color-accent-purple)", marginBottom: "4px" }}>
                            📋 Input Document Understanding & Summary
                          </div>
                          <div>{msg.input_summary}</div>
                        </div>
                      )}

                      {/* Evidence Confidence Badge */}
                      {msg.confidence && (
                        <div style={{ marginTop: "6px", display: "flex", alignItems: "center", gap: "8px" }}>
                          <span style={{
                            fontSize: "11px",
                            fontWeight: "700",
                            padding: "3px 8px",
                            borderRadius: "12px",
                            background: msg.confidence.level === "HIGH" ? "rgba(16, 185, 129, 0.15)" : msg.confidence.level === "MEDIUM" ? "rgba(245, 158, 11, 0.15)" : "rgba(239, 68, 68, 0.15)",
                            color: msg.confidence.level === "HIGH" ? "#10B981" : msg.confidence.level === "MEDIUM" ? "#F59E0B" : "#EF4444",
                            border: "1px solid currentColor"
                          }}>
                            Confidence: {msg.confidence.level} ({msg.confidence.confidence}%)
                          </span>
                          <span style={{ fontSize: "11px", color: "var(--text-muted)" }}>
                            ({msg.confidence.supporting_documents} docs, {msg.confidence.evidence_count} chunks)
                          </span>
                          {msg.timing && (
                            <span style={{ fontSize: "11px", color: "var(--text-muted)", marginLeft: "auto" }} title={`Embed: ${msg.timing.embedding_ms}ms | Retrieval: ${msg.timing.vector_retrieval_ms}ms | Graph: ${msg.timing.graph_traversal_ms}ms | Agents: ${msg.timing.pipeline_ms}ms`}>
                              ⚡ Retrieval: {(msg.timing.total_prep_ms / 1000).toFixed(2)}s
                            </span>
                          )}
                        </div>
                      )}

                      {/* Related Knowledge Discovery Section */}
                      {msg.related_knowledge && (
                        <div style={{ marginTop: "10px", display: "flex", flexDirection: "column", gap: "8px" }}>
                          {/* Related Documents */}
                          {msg.related_knowledge.related_documents?.length > 0 && (
                            <details style={{ fontSize: "11px", color: "var(--text-muted)", cursor: "pointer" }}>
                              <summary style={{ outline: "none", fontWeight: "600", color: "var(--color-accent)" }}>
                                📄 Related Authorized Documents ({msg.related_knowledge.related_documents.length})
                              </summary>
                              <div style={{ display: "flex", flexDirection: "column", gap: "6px", marginTop: "6px" }}>
                                {msg.related_knowledge.related_documents.map((doc) => (
                                  <div key={doc.document_id} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "6px 10px", background: "rgba(0,0,0,0.03)", borderRadius: "6px" }}>
                                    <span style={{ fontWeight: "600" }}>{doc.filename} ({doc.modality})</span>
                                    <button 
                                      className="btn btn-secondary"
                                      style={{ padding: "2px 8px", fontSize: "10px" }}
                                      onClick={() => {
                                        const found = images.find(i => i.id === doc.document_id);
                                        if (found) handleOpenOcrModal(found);
                                      }}
                                    >
                                      Inspect
                                    </button>
                                  </div>
                                ))}
                              </div>
                            </details>
                          )}

                          {/* Related Images / Visual Assets */}
                          {msg.related_knowledge.related_images?.length > 0 && (
                            <details style={{ fontSize: "11px", color: "var(--text-muted)", cursor: "pointer" }}>
                              <summary style={{ outline: "none", fontWeight: "600", color: "var(--color-accent-purple)" }}>
                                🖼️ Related Visual Assets ({msg.related_knowledge.related_images.length})
                              </summary>
                              <div style={{ display: "flex", gap: "8px", flexWrap: "wrap", marginTop: "6px" }}>
                                {msg.related_knowledge.related_images.map((imgAsset) => (
                                  <div key={imgAsset.document_id} style={{ width: "70px", height: "70px", borderRadius: "6px", overflow: "hidden", border: "1px solid var(--border-glass)", cursor: "pointer" }} onClick={() => {
                                    const found = images.find(i => i.id === imgAsset.document_id);
                                    if (found) handleOpenOcrModal(found);
                                  }}>
                                    <img src={`${BACKEND_URL}${imgAsset.thumbnail_url}?token=${localStorage.getItem('token')}`} alt={imgAsset.filename} style={{ width: "100%", height: "100%", objectFit: "cover" }} />
                                  </div>
                                ))}
                              </div>
                            </details>
                          )}

                          {/* Related Entities */}
                          {msg.related_knowledge.related_entities?.length > 0 && (
                            <div style={{ display: "flex", flexWrap: "wrap", gap: "4px", marginTop: "4px" }}>
                              <span style={{ fontSize: "11px", fontWeight: "600", color: "var(--text-muted)", marginRight: "4px" }}>Entities:</span>
                              {msg.related_knowledge.related_entities.map((ent, idx) => (
                                <span key={idx} style={{ fontSize: "10px", padding: "2px 6px", borderRadius: "4px", background: "rgba(99, 102, 241, 0.12)", color: "var(--color-accent)", border: "1px solid rgba(99, 102, 241, 0.2)" }}>
                                  {ent.name} ({ent.entity_type})
                                </span>
                              ))}
                            </div>
                          )}

                          {/* Graph Relationships */}
                          {msg.related_knowledge.relationships?.length > 0 && (
                            <details style={{ fontSize: "11px", color: "var(--text-muted)", cursor: "pointer" }}>
                              <summary style={{ outline: "none", fontWeight: "600", color: "var(--color-accent)" }}>
                                🕸️ Graph Relationships ({msg.related_knowledge.relationships.length})
                              </summary>
                              <div style={{ display: "flex", flexDirection: "column", gap: "4px", marginTop: "6px" }}>
                                {msg.related_knowledge.relationships.map((rel, idx) => (
                                  <div key={idx} style={{ fontSize: "10px", padding: "4px 8px", background: "rgba(0,0,0,0.03)", borderRadius: "4px" }}>
                                    <strong>{rel.source_name}</strong> ➔ <em>[{rel.relationship}]</em> ➔ <strong>{rel.target_name}</strong>
                                  </div>
                                ))}
                                <button className="btn btn-secondary" style={{ marginTop: "4px", padding: "4px 8px", fontSize: "10px", alignSelf: "flex-start" }} onClick={() => setActiveTab("graph")}>
                                  Open Knowledge Graph Explorer
                                </button>
                              </div>
                            </details>
                          )}
                        </div>
                      )}

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
                              <div key={source.chunk_id || index} style={{ display: "flex", flexDirection: "column", gap: "2px" }}>
                                <div style={{ display: "flex", justifyContent: "space-between", color: "var(--color-accent)", fontWeight: "600" }}>
                                  <span style={{ textDecoration: "underline", cursor: "pointer" }} onClick={() => {
                                    const img = images.find(i => i.id === source.metadata?.document_id);
                                    if (img) handleOpenOcrModal(img, source);
                                  }}>
                                    Ref #{index + 1}: {source.metadata?.source_file || "Document"}
                                  </span>
                                  <span>{Math.round((source.score || 0.8) * 100)}% match</span>
                                </div>
                                <div style={{ fontStyle: "italic", color: "var(--text-muted)", paddingLeft: "6px" }}>
                                  "{source.text ? source.text.substring(0, 120) : ""}..."
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

                {/* Gemini-Style Unified Input Container */}
                <div style={{
                  background: "var(--bg-sidebar)",
                  border: "1px solid var(--border-glass)",
                  borderRadius: "var(--radius-lg)",
                  padding: "16px",
                  display: "flex",
                  flexDirection: "column",
                  gap: "12px",
                  boxShadow: "0 4px 20px rgba(0,0,0,0.15)"
                }}>
                  {/* Attached File Pills Inside Container */}
                  {chatAttachments.length > 0 && (
                    <div style={{ display: "flex", gap: "8px", flexWrap: "wrap" }}>
                      {chatAttachments.map((att) => (
                        <span key={att.document_id} style={{ fontSize: "12px", background: "rgba(99, 102, 241, 0.15)", border: "1px solid rgba(99, 102, 241, 0.3)", borderRadius: "12px", padding: "4px 10px", display: "flex", alignItems: "center", gap: "6px" }}>
                          📎 {att.filename}
                          <button type="button" style={{ background: "none", border: "none", cursor: "pointer", color: "var(--text-muted)", fontWeight: "bold", outline: "none" }} onClick={() => removeChatAttachment(att.document_id)}>
                            ×
                          </button>
                        </span>
                      ))}
                    </div>
                  )}

                  {/* Speech Listening Indicator */}
                  {isRecordingSpeech && (
                    <div style={{ display: "flex", alignItems: "center", gap: "8px", fontSize: "12px", color: "#ef4444", fontWeight: "600", padding: "4px 10px", background: "rgba(239, 68, 68, 0.08)", borderRadius: "6px" }}>
                      <span className="spinner" style={{ width: "12px", height: "12px", borderColor: "#ef4444", borderTopColor: "transparent" }}></span>
                      Microphone active: Speak your question clearly... (Click 🎙️ to stop)
                    </div>
                  )}

                  {/* Input form */}
                  <form onSubmit={handleChatSubmit} style={{ display: "flex", gap: "12px", alignItems: "flex-end" }}>
                    <input 
                      type="file"
                      ref={chatFileInputRef}
                      onChange={handleChatFileSelect}
                      multiple
                      accept=".pdf,.docx,.pptx,.png,.jpg,.jpeg,.txt,.csv,.xlsx,.wav,.mp3,.ogg,.flac,.m4a"
                      style={{ display: "none" }}
                    />
                    
                    <button 
                      type="button" 
                      onClick={() => chatFileInputRef.current && chatFileInputRef.current.click()}
                      disabled={uploadingAttachment || isGenerating}
                      style={{ 
                        background: "rgba(255,255,255,0.05)",
                        border: "1px solid var(--border-glass)",
                        borderRadius: "50%",
                        width: "48px",
                        height: "48px",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        cursor: "pointer",
                        color: "var(--text-main)",
                        flexShrink: 0
                      }}
                      title="Attach Files (Docs, Images, Audio)"
                      aria-label="Attach Files"
                    >
                      {uploadingAttachment ? "..." : "📎"}
                    </button>

                    <input 
                      type="text"
                      placeholder="Ask a question, speak via mic (🎤), or attach files (PDF, Audio, Image)..."
                      value={chatInputText}
                      onChange={(e) => setChatInputText(e.target.value)}
                      style={{
                        flexGrow: 1,
                        padding: "14px 0px",
                        background: "transparent",
                        border: "none",
                        color: "var(--text-main)",
                        fontSize: "15px",
                        outline: "none",
                        height: "48px"
                      }}
                      disabled={isGenerating}
                    />

                    {/* Microphone Voice Query Button */}
                    <button
                      type="button"
                      onClick={toggleSpeechRecognition}
                      disabled={isGenerating || chatLoading}
                      style={{
                        background: isRecordingSpeech ? "rgba(239, 68, 68, 0.2)" : "rgba(255,255,255,0.05)",
                        border: isRecordingSpeech ? "2px solid #ef4444" : "1px solid var(--border-glass)",
                        borderRadius: "50%",
                        width: "48px",
                        height: "48px",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        cursor: "pointer",
                        color: isRecordingSpeech ? "#ef4444" : "var(--text-main)",
                        flexShrink: 0,
                        fontSize: "20px",
                        boxShadow: isRecordingSpeech ? "0 0 14px rgba(239, 68, 68, 0.7)" : "none",
                        transition: "all 0.3s ease"
                      }}
                      title={isRecordingSpeech ? "Listening... Click to stop" : "Ask question with speech (Microphone)"}
                      aria-label="Ask with Speech"
                    >
                      {isRecordingSpeech ? "🎙️" : "🎤"}
                    </button>
                    
                    {isGenerating ? (
                      <button type="button" className="btn btn-secondary" onClick={handleStopGeneration} style={{ height: "48px", padding: "0 24px", color: "var(--color-error)", borderColor: "var(--color-error)" }}>
                        Stop
                      </button>
                    ) : (
                      <button type="submit" aria-label="Send Question" className="btn btn-primary" style={{ height: "48px", padding: "0 24px", borderRadius: "24px" }} disabled={chatLoading || (!chatInputText && !chatAttachments.length)}>
                        Send
                      </button>
                    )}
                  </form>
                </div>
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
                          if (img) handleOpenOcrModal(img, match);
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
            </div>
          </section>
        )}

        {/* VIEW 5: USER MANAGEMENT */}
        {activeTab === "users" && (
          <section className="panel" style={{ height: "calc(100vh - 160px)", overflow: 'auto' }}>
            <UserManagement token={token} />
          </section>
        )}

        {/* VIEW 6: SYSTEM SETTINGS */}
        {activeTab === "settings" && (
          <section className="panel">
            <h3 style={{ marginBottom: "20px", fontWeight: "600" }}>System Settings</h3>
            <div style={{ display: "flex", flexDirection: "column", gap: "24px", maxWidth: "600px" }}>
              {/* Account Security Box */}
              <div style={{ padding: "20px", background: "var(--bg-sidebar)", border: "1px solid var(--border-glass)", borderRadius: "var(--radius-md)" }}>
                <h4 style={{ fontSize: "15px", fontWeight: "600", color: "var(--text-main)", marginBottom: "14px" }}>
                  Account Security — Change Password
                </h4>
                {pwdMsg.text && (
                  <div className={`status-message ${pwdMsg.type}`} style={{ padding: "10px 14px", marginBottom: "14px" }}>
                    {pwdMsg.text}
                  </div>
                )}
                <form onSubmit={handlePasswordChange} style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
                  <div>
                    <label style={{ display: "block", fontSize: "12px", fontWeight: "600", color: "var(--text-muted)", marginBottom: "4px" }}>
                      Current Password
                    </label>
                    <input 
                      type="password"
                      className="form-input"
                      value={pwdCurrent}
                      onChange={(e) => setPwdCurrent(e.target.value)}
                      placeholder="Enter current password"
                      required
                    />
                  </div>
                  <div>
                    <label style={{ display: "block", fontSize: "12px", fontWeight: "600", color: "var(--text-muted)", marginBottom: "4px" }}>
                      New Password
                    </label>
                    <input 
                      type="password"
                      className="form-input"
                      value={pwdNew}
                      onChange={(e) => setPwdNew(e.target.value)}
                      placeholder="Enter new password (min. 6 characters)"
                      required
                    />
                  </div>
                  <div>
                    <label style={{ display: "block", fontSize: "12px", fontWeight: "600", color: "var(--text-muted)", marginBottom: "4px" }}>
                      Confirm New Password
                    </label>
                    <input 
                      type="password"
                      className="form-input"
                      value={pwdConfirm}
                      onChange={(e) => setPwdConfirm(e.target.value)}
                      placeholder="Confirm new password"
                      required
                    />
                  </div>
                  <button type="submit" className="btn btn-primary" style={{ marginTop: "6px", alignSelf: "flex-start" }} disabled={pwdLoading}>
                    {pwdLoading ? "Updating..." : "Update Password"}
                  </button>
                </form>
              </div>

              {/* System Infrastructure Info */}
              <div style={{ padding: "20px", background: "var(--bg-sidebar)", border: "1px solid var(--border-glass)", borderRadius: "var(--radius-md)" }}>
                <h4 style={{ fontSize: "15px", fontWeight: "600", color: "var(--text-main)", marginBottom: "14px" }}>
                  Offline Infrastructure
                </h4>
                <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
                  <div>
                    <label style={{ display: "block", fontSize: "12px", fontWeight: "600", color: "var(--text-muted)", marginBottom: "4px" }}>
                      Backend Service Endpoint
                    </label>
                    <input 
                      type="text" 
                      value={BACKEND_URL} 
                      disabled 
                      style={{
                        width: "100%", 
                        padding: "10px", 
                        borderRadius: "var(--radius-md)", 
                        border: "1px solid var(--border-glass)", 
                        background: "var(--bg-main)",
                        color: "var(--text-main)"
                      }} 
                    />
                  </div>
                  <div style={{ display: "flex", gap: "16px" }}>
                    <div style={{ flex: 1 }}>
                      <label style={{ display: "block", fontSize: "12px", fontWeight: "600", color: "var(--text-muted)", marginBottom: "4px" }}>
                        Session Expiry
                      </label>
                      <div style={{ padding: "10px", border: "1px solid var(--border-glass)", borderRadius: "var(--radius-md)", background: "var(--bg-main)", fontSize: "13px" }}>
                        8 Hours (Shift Duration)
                      </div>
                    </div>
                    <div style={{ flex: 1 }}>
                      <label style={{ display: "block", fontSize: "12px", fontWeight: "600", color: "var(--text-muted)", marginBottom: "4px" }}>
                        Registry Database
                      </label>
                      <div style={{ padding: "10px", border: "1px solid var(--border-glass)", borderRadius: "var(--radius-md)", background: "var(--bg-main)", fontSize: "13px" }}>
                        SQLite (metadata.db)
                      </div>
                    </div>
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
            <header className="modal-header" style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
              <div>
                <h3 style={{ fontSize: "18px", fontWeight: "700", margin: 0 }}>{selectedImgForModal.filename}</h3>
                <p style={{ fontSize: "12px", color: "var(--text-muted)", margin: "4px 0 8px 0" }}>Registry UUID: {selectedImgForModal.id}</p>
                <div style={{ display: "flex", alignItems: "center", gap: "8px", fontSize: "12px" }}>
                  <span style={{ color: "var(--text-muted)" }}>Status:</span>
                  <span style={{ padding: "2px 8px", borderRadius: "4px", background: "rgba(99, 102, 241, 0.1)", color: "var(--color-accent)", fontWeight: "600" }}>
                    {selectedImgForModal.status || "ACTIVE"}
                  </span>
                </div>
              </div>
              <button className="modal-close-x" onClick={handleCloseModal}>×</button>
            </header>

            {highlightCitation && (
              <div style={{
                background: "rgba(99, 102, 241, 0.12)",
                border: "1px solid var(--color-accent)",
                borderRadius: "var(--radius-md)",
                padding: "8px 16px",
                margin: "12px 24px 0 24px",
                fontSize: "12px",
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between"
              }}>
                <div>
                  <strong style={{ color: "var(--color-accent)" }}>Cited Source Reference:</strong> "{highlightCitation.text ? highlightCitation.text.substring(0, 110) : ''}..."
                </div>
                <span style={{ fontWeight: "700", color: "#10b981", whiteSpace: "nowrap", marginLeft: "12px" }}>
                  {Math.round((highlightCitation.score || 0.8) * 100)}% Match
                </span>
              </div>
            )}
            
            <div className="modal-body">
              {/* Left Pane: Toggled Image Viewers */}
              <div className="modal-pane left">
                <div className="toggle-group">
                  <button 
                    className={`toggle-btn ${modalViewMode === "original" ? "active" : ""}`}
                    onClick={() => setModalViewMode("original")}
                  >
                    {selectedImgForModal.filename?.toLowerCase().match(/\.(wav|mp3|ogg|flac|m4a)$/) ? "Audio Recording" : "Original View"}
                  </button>
                  {!selectedImgForModal.filename?.toLowerCase().match(/\.(wav|mp3|ogg|flac|m4a)$/) && (
                    <button 
                      className={`toggle-btn ${modalViewMode === "overlay" ? "active" : ""}`}
                      onClick={() => setModalViewMode("overlay")}
                    >
                      OCR Layout Grid
                    </button>
                  )}
                </div>
                
                <div className="modal-viewer-frame">
                  {modalViewMode === "original" ? (
                    <>
                      {selectedImgForModal.filename && selectedImgForModal.filename.toLowerCase().match(/\.(jpg|jpeg|png|gif|webp)$/) ? (
                        <img 
                          src={`${BACKEND_URL}/api/images/${selectedImgForModal.id}/raw?token=${token || localStorage.getItem('token') || sessionStorage.getItem('token')}`} 
                          className="modal-viewer-img" 
                          alt="original" 
                          style={{ objectFit: 'contain' }}
                        />
                      ) : selectedImgForModal.filename && selectedImgForModal.filename.toLowerCase().match(/\.(mp4|avi|mov|mkv|webm)$/) ? (
                        <div style={{ width: '100%', height: '100%', minHeight: '520px', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', background: 'var(--bg-panel)', padding: '20px', textAlign: 'center' }}>
                          <h3 style={{ fontSize: '18px', fontWeight: '600', marginBottom: '8px', color: 'var(--text-main)' }}>🎥 Video Intelligence Player</h3>
                          <p style={{ color: 'var(--text-muted)', fontSize: '12px', marginBottom: '16px' }}>{selectedImgForModal.filename}</p>
                          <video 
                            id="modal-video-player"
                            controls 
                            src={`${BACKEND_URL}/api/images/${selectedImgForModal.id}/raw?token=${token || localStorage.getItem('token') || sessionStorage.getItem('token')}`} 
                            style={{ width: '100%', maxWidth: '640px', maxHeight: '380px', borderRadius: '8px', background: '#000' }}
                          />
                        </div>
                      ) : selectedImgForModal.filename && selectedImgForModal.filename.toLowerCase().match(/\.(wav|mp3|ogg|flac|m4a)$/) ? (
                        <div style={{ width: '100%', height: '100%', minHeight: '520px', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', background: 'var(--bg-panel)', padding: '30px', textAlign: 'center' }}>
                          <div style={{ fontSize: '72px', marginBottom: '16px' }}>🎙️</div>
                          <h3 style={{ fontSize: '20px', fontWeight: '600', marginBottom: '8px', color: 'var(--text-main)' }}>{selectedImgForModal.filename}</h3>
                          <p style={{ color: 'var(--text-muted)', fontSize: '13px', marginBottom: '28px' }}>Native Audio Intelligence Modality & Recording</p>
                          <audio 
                            controls 
                            src={`${BACKEND_URL}/api/images/${selectedImgForModal.id}/raw?token=${token || localStorage.getItem('token') || sessionStorage.getItem('token')}`} 
                            style={{ width: '100%', maxWidth: '520px', outline: 'none' }}
                          />
                        </div>
                      ) : selectedImgForModal.filename && selectedImgForModal.filename.toLowerCase().match(/\.(docx|pptx|txt|csv|tsv|xlsx|xls)$/) ? (
                        <iframe
                          src={`${BACKEND_URL}/api/images/${selectedImgForModal.id}/html?token=${token || localStorage.getItem('token') || sessionStorage.getItem('token')}`}
                          style={{ width: '100%', height: '100%', minHeight: '600px', border: 'none', backgroundColor: '#fff' }}
                          title="Document Viewer"
                        />
                      ) : (
                        <div style={{ width: '100%', height: '100%', minHeight: '600px', backgroundColor: '#fff' }}>
                          <DocViewer 
                            documents={[{ 
                              uri: `${BACKEND_URL}/api/images/${selectedImgForModal.id}/raw?token=${token || localStorage.getItem('token') || sessionStorage.getItem('token')}`,
                              fileName: selectedImgForModal.filename 
                            }]} 
                            pluginRenderers={DocViewerRenderers} 
                            style={{ width: '100%', height: '100%' }}
                            config={{
                              header: {
                                disableHeader: true,
                                disableFileName: true,
                                retainURLParams: true
                              }
                            }}
                          />
                        </div>
                      )}
                    </>
                  ) : (
                    <img 
                      src={`${BACKEND_URL}/api/images/${selectedImgForModal.id}/ocr/overlay?token=${token || localStorage.getItem('token') || sessionStorage.getItem('token')}`} 
                      className="modal-viewer-img" 
                      alt="overlay" 
                    />
                  )}
                  {/* CITATION HIGHLIGHT OVERLAY */}
                  {highlightCitation && highlightCitation.metadata && highlightCitation.metadata.bounding_box && (
                    <div style={{
                      position: 'absolute',
                      top: highlightCitation.metadata.bounding_box[1] ? `${(highlightCitation.metadata.bounding_box[1] / 1000) * 100}%` : '0',
                      left: highlightCitation.metadata.bounding_box[0] ? `${(highlightCitation.metadata.bounding_box[0] / 1000) * 100}%` : '0',
                      width: (highlightCitation.metadata.bounding_box[2] && highlightCitation.metadata.bounding_box[0]) ? `${((highlightCitation.metadata.bounding_box[2] - highlightCitation.metadata.bounding_box[0]) / 1000) * 100}%` : '0',
                      height: (highlightCitation.metadata.bounding_box[3] && highlightCitation.metadata.bounding_box[1]) ? `${((highlightCitation.metadata.bounding_box[3] - highlightCitation.metadata.bounding_box[1]) / 1000) * 100}%` : '0',
                      border: '3px solid #00ff00',
                      backgroundColor: 'rgba(0, 255, 0, 0.2)',
                      pointerEvents: 'none'
                    }} />
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
                      Words: {modalOcrData.word_count || modalOcrData.total_words_detected || 0}
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
                  (modalOcrText === "No extractable text found in document." && selectedImgForModal && (selectedImgForModal.status || "").toLowerCase() !== "completed") ? (
                    <div style={{ flexGrow: 1, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", background: "var(--bg-sidebar)", borderRadius: "var(--radius-md)", padding: "30px", textAlign: "center", gap: "14px" }}>
                      <div className="spinner" style={{ width: "28px", height: "28px" }}></div>
                      <p style={{ color: "var(--color-accent-purple)", fontWeight: "600", fontSize: "14px", margin: 0 }}>Document processing in progress...</p>
                      <p style={{ color: "var(--text-muted)", fontSize: "12px", margin: 0, maxWidth: "340px" }}>Text extraction, vision analysis, and chunking are running in the background. Content will refresh automatically.</p>
                    </div>
                  ) : (
                    <textarea 
                      className="ocr-text-area" 
                      readOnly 
                      value={modalOcrText}
                    />
                  )
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
                          borderRadius: "var(--radius-md)",
                          padding: "16px",
                          display: "flex",
                          flexDirection: "column",
                          gap: "8px",
                          border: highlightCitation && highlightCitation.chunk_id === chunk.chunk_id ? "2px solid #00ff00" : "1px solid var(--border-glass)"
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
                            <span>Source: {chunk.metadata?.source_file || 'Unknown'}</span>
                            <span>Confidence Score: {chunk.metadata?.ocr_confidence || 100}%</span>
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

      {/* GLOBAL ENTITY PROFILE MODAL */}
      {selectedEntityForProfile && (
        <EntityProfileModal
          entityName={selectedEntityForProfile}
          onClose={() => setSelectedEntityForProfile(null)}
          onExploreInGraph={(name) => {
            setSelectedEntityForProfile(null);
            setActiveTab("graph");
          }}
          onOpenDocument={(docId) => {
            setSelectedEntityForProfile(null);
            setSelectedDocForIntelligence(docId);
          }}
          backendUrl={BACKEND_URL}
          token={token}
        />
      )}

      {/* GLOBAL DOCUMENT INTELLIGENCE MODAL */}
      {selectedDocForIntelligence && (
        <DocumentIntelligenceModal
          documentId={selectedDocForIntelligence}
          onClose={() => setSelectedDocForIntelligence(null)}
          onAskAboutDocument={handleAskAboutDocument}
          onSelectEntity={(ent) => {
            setSelectedDocForIntelligence(null);
            setSelectedEntityForProfile(ent);
          }}
          backendUrl={BACKEND_URL}
          token={token}
        />
      )}
    </div>
  );
}
