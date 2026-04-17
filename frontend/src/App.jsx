import { useState } from "react";
import FileUpload from "./components/FileUpload";
import QueryInput from "./components/QueryInput";
import AgentPipeline from "./components/AgentPipeline";
import ResultPanel from "./components/ResultPanel";

const API_URL = "http://localhost:8080";

// ── Paper selector — shown when 2+ papers are ready ─────────────────────────
function PaperSelector({ papers, selectedIds, onToggle, onSelectAll }) {
  const readyPapers = papers.filter((p) => p.uploadStatus === "ready");
  if (readyPapers.length < 2) return null;

  const allSelected = selectedIds === "all";

  return (
    <div style={{ marginTop: "1rem" }}>
      <p className="query-label" style={{ marginBottom: "0.4rem" }}>Select papers to query</p>
      <div
        style={{
          background: "var(--surface-2, rgba(255,255,255,0.04))",
          border: "1px solid var(--border)",
          borderRadius: "8px",
          overflow: "hidden",
        }}
      >
        {/* All papers option */}
        <label
          style={{
            display: "flex",
            alignItems: "center",
            gap: "0.5rem",
            padding: "0.5rem 0.75rem",
            cursor: "pointer",
            borderBottom: "1px solid var(--border)",
            fontSize: "0.8rem",
            color: "var(--text-secondary)",
          }}
        >
          <input
            type="checkbox"
            checked={allSelected}
            onChange={() => onSelectAll()}
            style={{ accentColor: "var(--accent)", width: 14, height: 14 }}
          />
          <span style={{ fontWeight: 500, color: "var(--text-primary, #e2e8f0)" }}>All papers</span>
          <span style={{ marginLeft: "auto", color: "var(--text-muted)", fontSize: "0.72rem" }}>
            {readyPapers.length} papers
          </span>
        </label>

        {/* Individual papers */}
        {readyPapers.map((paper) => {
          const checked = allSelected || (Array.isArray(selectedIds) && selectedIds.includes(paper.id));
          return (
            <label
              key={paper.id}
              style={{
                display: "flex",
                alignItems: "center",
                gap: "0.5rem",
                padding: "0.45rem 0.75rem",
                cursor: "pointer",
                fontSize: "0.78rem",
                color: "var(--text-secondary)",
                borderBottom: "1px solid var(--border)",
              }}
            >
              <input
                type="checkbox"
                checked={checked}
                onChange={() => onToggle(paper.id)}
                style={{ accentColor: "var(--accent)", width: 14, height: 14 }}
              />
              <span
                style={{
                  overflow: "hidden",
                  textOverflow: "ellipsis",
                  whiteSpace: "nowrap",
                }}
                title={paper.fileName}
              >
                {paper.fileName}
              </span>
            </label>
          );
        })}
      </div>
    </div>
  );
}

// ── Main App ──────────────────────────────────────────────────────────────────
export default function App() {
  // Multi-paper state — each paper: { id, file, fileName, collectionName, uploadStatus, uploadError }
  const [papers, setPapers] = useState([]);
  // selectedIds: "all" or array of paper IDs
  const [selectedIds, setSelectedIds] = useState("all");

  // Analysis state
  const [query, setQuery] = useState("");
  const [status, setStatus] = useState("idle");
  const [activeAgent, setActiveAgent] = useState(null);
  const [routingReason, setRoutingReason] = useState(null);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  // Clarification state: null | { question, papers: [{id, fileName}] }
  const [clarification, setClarification] = useState(null);

  // ── Upload a new file ──────────────────────────────────────────────────────
  async function handleFileAdd(file) {
    const id = `${Date.now()}-${Math.random()}`;
    const newPaper = {
      id,
      file,
      fileName: file.name,
      collectionName: null,
      uploadStatus: "uploading",
      uploadError: null,
    };

    setPapers((prev) => [...prev, newPaper]);

    try {
      const formData = new FormData();
      formData.append("file", file);

      const response = await fetch(`${API_URL}/upload`, {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        let errMsg = `Upload failed: ${response.status}`;
        try { const b = await response.json(); errMsg = b.detail || errMsg; } catch {}
        throw new Error(errMsg);
      }

      const data = await response.json();
      setPapers((prev) =>
        prev.map((p) =>
          p.id === id
            ? { ...p, collectionName: data.collection_name, uploadStatus: "ready" }
            : p
        )
      );
    } catch (err) {
      setPapers((prev) =>
        prev.map((p) =>
          p.id === id ? { ...p, uploadStatus: "error", uploadError: err.message } : p
        )
      );
    }
  }

  // ── Remove a paper ─────────────────────────────────────────────────────────
  async function handleFileRemove(id) {
    const paper = papers.find((p) => p.id === id);
    if (paper?.collectionName) {
      try {
        await fetch(`${API_URL}/documents/${paper.collectionName}`, { method: "DELETE" });
      } catch {}
    }
    setPapers((prev) => prev.filter((p) => p.id !== id));
    setSelectedIds((prev) => {
      if (prev === "all") return "all";
      return prev.filter((sid) => sid !== id);
    });
    setResult(null);
    setError(null);
    setStatus("idle");
  }

  // ── Paper selection ────────────────────────────────────────────────────────
  function handleSelectAll() {
    setSelectedIds("all");
  }

  function handleToggle(id) {
    setSelectedIds((prev) => {
      const readyIds = papers.filter((p) => p.uploadStatus === "ready").map((p) => p.id);
      const current = prev === "all" ? readyIds : [...prev];
      if (current.includes(id)) {
        const next = current.filter((sid) => sid !== id);
        return next.length === 0 ? "all" : next;
      } else {
        return [...current, id];
      }
    });
  }

  // ── Submit query ───────────────────────────────────────────────────────────
  async function handleSubmit({ skipClarification = false, overridePaperIds = null } = {}) {
    const readyPapers = papers.filter((p) => p.uploadStatus === "ready");
    if (!readyPapers.length || !query.trim()) return;

    // Resolve selected papers — allow override from clarification buttons
    let targetPapers;
    const idsToUse = overridePaperIds ?? selectedIds;
    if (idsToUse === "all") {
      targetPapers = readyPapers;
    } else {
      targetPapers = readyPapers.filter((p) => idsToUse.includes(p.id));
      if (!targetPapers.length) targetPapers = readyPapers;
    }

    const collectionNames = targetPapers.map((p) => p.collectionName);
    const fileNames = targetPapers.map((p) => p.fileName);

    setStatus("routing");
    setResult(null);
    setError(null);
    setActiveAgent(null);
    setRoutingReason(null);
    setClarification(null);

    try {
      const response = await fetch(`${API_URL}/analyze`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          collection_names: collectionNames,
          file_names: fileNames,
          query,
          skip_clarification: skipClarification,
        }),
      });

      if (!response.ok) {
        let errMsg = `Server error: ${response.status}`;
        try { const b = await response.json(); errMsg = b.detail || errMsg; } catch {}
        throw new Error(errMsg);
      }

      const data = await response.json();
      if (data.error) throw new Error(data.error);

      // Orchestrator asked for clarification — show paper-selection prompt
      if (data.route === "clarification") {
        setActiveAgent("clarification");
        setRoutingReason(data.routing_reason);
        setStatus("done");
        setClarification({
          question: data.clarification_question || "Which paper would you like to query?",
          papers: targetPapers.map((p) => ({ id: p.id, fileName: p.fileName })),
        });
        return;
      }

      setActiveAgent(data.route);
      setRoutingReason(data.routing_reason);
      setStatus("running");

      await new Promise((r) => setTimeout(r, 1200));

      setResult(data.result);
      setStatus("done");
    } catch (err) {
      setError(err.message || "An unexpected error occurred. Is the backend running?");
      setStatus("error");
    }
  }

  // ── Clarification handlers ─────────────────────────────────────────────────
  // User chose a single specific paper from the clarification prompt
  function handleClarifyPaper(paperId) {
    setClarification(null);
    handleSubmit({ skipClarification: false, overridePaperIds: [paperId] });
  }

  // User chose to query all papers — skip future clarification
  function handleClarifyBoth() {
    setClarification(null);
    const readyIds = papers.filter((p) => p.uploadStatus === "ready").map((p) => p.id);
    handleSubmit({ skipClarification: true, overridePaperIds: readyIds });
  }

  function handleFollowup(q) {
    setQuery(q);
  }

  const readyPapers = papers.filter((p) => p.uploadStatus === "ready");
  const hasReadyPapers = readyPapers.length > 0;
  const isLoading = ["routing", "running"].includes(status);

  return (
    <div className="app">
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
        <aside className="left-panel">
          <FileUpload
            papers={papers}
            onFileAdd={handleFileAdd}
            onFileRemove={handleFileRemove}
          />
          <PaperSelector
            papers={papers}
            selectedIds={selectedIds}
            onToggle={handleToggle}
            onSelectAll={handleSelectAll}
          />
          <QueryInput
            query={query}
            onQueryChange={setQuery}
            onSubmit={handleSubmit}
            status={status}
            uploadReady={hasReadyPapers}
          />
        </aside>

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
            clarification={clarification}
            onFollowup={handleFollowup}
            onClarifyPaper={handleClarifyPaper}
            onClarifyBoth={handleClarifyBoth}
          />
        </section>
      </main>
    </div>
  );
}
