import { useState } from "react";
import FileUpload from "./components/FileUpload";
import QueryInput from "./components/QueryInput";
import AgentPipeline from "./components/AgentPipeline";
import ResultPanel from "./components/ResultPanel";

const API_URL = "http://localhost:8080";

function PaperMetaCard({ meta, uploadStatus, uploadError }) {
  if (uploadStatus === "uploading") {
    return (
      <div className="paper-meta-card" style={{ marginTop: "1rem" }}>
        <p className="passages-heading" style={{ marginBottom: "0.5rem" }}>Processing paper…</p>
        {[80, 60, 40].map((w, i) => (
          <div key={i} className="skeleton" style={{ height: "14px", width: `${w}%`, marginBottom: "0.5rem" }} />
        ))}
      </div>
    );
  }

  if (uploadStatus === "error") {
    return (
      <div className="warning-banner" style={{ marginTop: "1rem" }}>
        ⚠ {uploadError || "Upload failed. Please try again."}
      </div>
    );
  }

  if (uploadStatus !== "ready" || !meta) return null;

  return (
    <div className="paper-meta-card" style={{ marginTop: "1rem" }}>
      <p className="passages-heading" style={{ marginBottom: "0.6rem" }}>Paper Metadata</p>
      {meta.title && (
        <div className="meta-row">
          <span className="meta-label">Title</span>
          <span className="meta-value">{meta.title}</span>
        </div>
      )}
      {meta.authors?.length > 0 && (
        <div className="meta-row">
          <span className="meta-label">Authors</span>
          <span className="meta-value">{meta.authors.join(", ")}</span>
        </div>
      )}
      {meta.year && (
        <div className="meta-row">
          <span className="meta-label">Year</span>
          <span className="meta-value">{meta.year}</span>
        </div>
      )}
      {meta.journal && (
        <div className="meta-row">
          <span className="meta-label">Journal</span>
          <span className="meta-value">{meta.journal}</span>
        </div>
      )}
      {meta.doi && (
        <div className="meta-row">
          <span className="meta-label">DOI</span>
          <span className="meta-value" style={{ fontFamily: "var(--font-mono)", fontSize: "0.75rem" }}>{meta.doi}</span>
        </div>
      )}
      {meta.institution?.length > 0 && (
        <div className="meta-row">
          <span className="meta-label">Institution</span>
          <span className="meta-value">{meta.institution.join(", ")}</span>
        </div>
      )}
      {meta.keywords?.length > 0 && (
        <div className="meta-row">
          <span className="meta-label">Keywords</span>
          <div style={{ display: "flex", flexWrap: "wrap", gap: "0.35rem", marginTop: "0.2rem" }}>
            {meta.keywords.map((k, i) => (
              <span key={i} className="file-type-badge">{k}</span>
            ))}
          </div>
        </div>
      )}
      {meta.abstract && (
        <div style={{ marginTop: "0.75rem" }}>
          <span className="meta-label">Abstract</span>
          <p style={{ fontSize: "0.82rem", color: "var(--text-secondary)", lineHeight: 1.65, marginTop: "0.3rem" }}>
            {meta.abstract}
          </p>
        </div>
      )}
    </div>
  );
}

export default function App() {
  const [file, setFile] = useState(null);
  const [collectionName, setCollectionName] = useState(null);
  const [paperMetadata, setPaperMetadata] = useState(null);
  const [uploadStatus, setUploadStatus] = useState("idle"); // idle | uploading | ready | error
  const [uploadError, setUploadError] = useState(null);

  const [query, setQuery] = useState("");
  const [status, setStatus] = useState("idle"); // idle | routing | running | done | error
  const [activeAgent, setActiveAgent] = useState(null);
  const [routingReason, setRoutingReason] = useState(null);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  async function handleFileSelect(f) {
    setFile(f);
    // Reset analysis state when file changes
    setResult(null);
    setError(null);
    setActiveAgent(null);
    setRoutingReason(null);
    setStatus("idle");

    if (!f) {
      // File removed
      setCollectionName(null);
      setPaperMetadata(null);
      setUploadStatus("idle");
      setUploadError(null);
      return;
    }

    // Immediately upload and process the file
    setUploadStatus("uploading");
    setUploadError(null);
    setCollectionName(null);
    setPaperMetadata(null);

    try {
      const formData = new FormData();
      formData.append("file", f);

      const response = await fetch(`${API_URL}/upload`, {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        let errMsg = `Upload failed: ${response.status}`;
        try {
          const errBody = await response.json();
          errMsg = errBody.detail || errMsg;
        } catch {}
        throw new Error(errMsg);
      }

      const data = await response.json();
      setCollectionName(data.collection_name);
      setPaperMetadata(data.paper_metadata || null);
      setUploadStatus("ready");
    } catch (err) {
      setUploadStatus("error");
      setUploadError(err.message || "Upload failed. Is the backend running?");
    }
  }

  async function handleSubmit() {
    if (!collectionName || !query.trim() || uploadStatus !== "ready") return;

    setStatus("routing");
    setResult(null);
    setError(null);
    setActiveAgent(null);
    setRoutingReason(null);

    try {
      const formData = new FormData();
      formData.append("collection_name", collectionName);
      formData.append("query", query);
      formData.append("file_name", file.name);

      const response = await fetch(`${API_URL}/analyze`, {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        let errMsg = `Server error: ${response.status}`;
        try {
          const errBody = await response.json();
          errMsg = errBody.detail || errMsg;
        } catch {}
        throw new Error(errMsg);
      }

      const data = await response.json();

      if (data.error) {
        throw new Error(data.error);
      }

      setActiveAgent(data.route);
      setRoutingReason(data.routing_reason);
      setStatus("running");

      // Brief pause so the active-agent animation plays
      await new Promise((r) => setTimeout(r, 1200));

      setResult(data.result);
      setStatus("done");
    } catch (err) {
      setError(err.message || "An unexpected error occurred. Is the backend running?");
      setStatus("error");
    }
  }

  function handleFollowup(q) {
    setQuery(q);
  }

  return (
    <div className="app">
      {/* Header */}
      <header className="header">
        <div className="header-logo">
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
            <path strokeLinecap="round" strokeLinejoin="round" d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09z" />
            <path strokeLinecap="round" strokeLinejoin="round" d="M18.259 8.715L18 9.75l-.259-1.035a3.375 3.375 0 00-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 002.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 002.456 2.456L21.75 6l-1.035.259a3.375 3.375 0 00-2.456 2.456z" />
          </svg>
          <span className="header-title">Research Assistant</span>
        </div>
        <span className="header-tagline">LangGraph · Multi-Agent · OpenAI</span>
      </header>

      <main className="main-grid">
        {/* Left panel */}
        <aside className="left-panel">
          <FileUpload file={file} onFileChange={handleFileSelect} />
          <PaperMetaCard
            meta={paperMetadata}
            uploadStatus={uploadStatus}
            uploadError={uploadError}
          />
          <QueryInput
            query={query}
            onQueryChange={setQuery}
            onSubmit={handleSubmit}
            status={status}
            file={file}
            uploadReady={uploadStatus === "ready"}
          />
        </aside>

        {/* Right panel */}
        <section className="right-panel">
          <AgentPipeline
            status={status}
            activeAgent={activeAgent}
            routingReason={routingReason}
          />
          <ResultPanel
            status={status}
            activeAgent={activeAgent}
            result={result}
            error={error}
            onFollowup={handleFollowup}
          />
        </section>
      </main>
    </div>
  );
}
