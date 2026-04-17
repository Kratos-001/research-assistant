import { useState } from "react";
import FileUpload from "./components/FileUpload";
import QueryInput from "./components/QueryInput";
import AgentPipeline from "./components/AgentPipeline";
import ResultPanel from "./components/ResultPanel";

const API_URL = "http://localhost:8080";

export default function App() {
  const [file, setFile] = useState(null);
  const [query, setQuery] = useState("");
  const [status, setStatus] = useState("idle"); // idle | uploading | routing | running | done | error
  const [activeAgent, setActiveAgent] = useState(null);
  const [routingReason, setRoutingReason] = useState(null);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  async function handleSubmit() {
    if (!file || !query.trim()) return;

    setStatus("uploading");
    setResult(null);
    setError(null);
    setActiveAgent(null);
    setRoutingReason(null);

    const formData = new FormData();
    formData.append("file", file);
    formData.append("query", query);

    try {
      setStatus("routing");

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
        <span className="header-tagline">LangGraph · Multi-Agent · Claude</span>
      </header>

      <main className="main-grid">
        {/* Left panel */}
        <aside className="left-panel">
          <FileUpload file={file} onFileChange={setFile} />
          <QueryInput
            query={query}
            onQueryChange={setQuery}
            onSubmit={handleSubmit}
            status={status}
            file={file}
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
