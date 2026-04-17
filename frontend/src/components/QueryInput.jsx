import { useState, useEffect, useRef } from "react";

const PLACEHOLDERS = [
  "What does the paper say about side effects?",
  "Is it true that the study used a control group?",
  "Summarize the key findings and any risks",
  "Find all mentions of statistical significance",
  "Does the document mention contraindications?",
  "What are the main arguments made?",
];

export default function QueryInput({ query, onQueryChange, onSubmit, status, file }) {
  const [placeholderIdx, setPlaceholderIdx] = useState(0);
  const textareaRef = useRef(null);

  useEffect(() => {
    const interval = setInterval(() => {
      setPlaceholderIdx((i) => (i + 1) % PLACEHOLDERS.length);
    }, 3500);
    return () => clearInterval(interval);
  }, []);

  // Auto-resize textarea
  useEffect(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${el.scrollHeight}px`;
  }, [query]);

  const isLoading = ["uploading", "routing", "running"].includes(status);
  const canSubmit = file && query.trim() && !isLoading;

  function handleKey(e) {
    if (e.key === "Enter" && (e.metaKey || e.ctrlKey) && canSubmit) {
      onSubmit();
    }
  }

  const hint = PLACEHOLDERS[placeholderIdx];
  let hintType = "analysis";
  if (hint.toLowerCase().includes("is it true") || hint.toLowerCase().includes("does the document mention")) {
    hintType = "factcheck";
  } else if (hint.toLowerCase().includes("find") || hint.toLowerCase().includes("what does")) {
    hintType = "retrieval";
  }

  const hintLabels = {
    retrieval: "retrieval",
    factcheck: "fact-check",
    analysis: "analysis",
  };

  return (
    <div className="query-section">
      <label className="query-label">Your Query</label>
      <textarea
        ref={textareaRef}
        className="query-textarea"
        placeholder={PLACEHOLDERS[placeholderIdx]}
        value={query}
        onChange={(e) => onQueryChange(e.target.value)}
        onKeyDown={handleKey}
        rows={3}
        disabled={isLoading}
      />

      <button
        className="submit-btn"
        onClick={onSubmit}
        disabled={!canSubmit}
      >
        {isLoading ? (
          <>
            <div className="spinner" />
            {status === "routing" ? "Routing..." : status === "running" ? "Analyzing..." : "Uploading..."}
          </>
        ) : (
          <>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path strokeLinecap="round" strokeLinejoin="round" d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09z" />
            </svg>
            Analyze Document
          </>
        )}
      </button>

      {!file && (
        <p className="query-hint">Upload a document first to enable analysis.</p>
      )}
      {file && !isLoading && (
        <p className="query-hint">
          Tip: ask <strong>"Is it true that..."</strong> for fact-checking · <strong>"Find..."</strong> for retrieval · <strong>"Summarize..."</strong> for analysis
        </p>
      )}
    </div>
  );
}
