// ── Clarification prompt — orchestrator asks which paper ──────────────────────
function ClarificationResult({ clarification, onClarifyPaper, onClarifyBoth }) {
  const { question, papers } = clarification;
  return (
    <div className="result-section">
      <div className="result-agent-label">
        <span className="result-agent-dot" style={{ background: "var(--accent, #6ee7b7)" }} />
        Orchestrator — needs clarification
      </div>

      <p style={{ margin: "0.75rem 0 1rem", lineHeight: 1.6, color: "var(--text-primary, #e2e8f0)" }}>
        {question}
      </p>

      <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
        {papers.map((p) => (
          <button
            key={p.id}
            className="followup-btn"
            style={{ textAlign: "left", justifyContent: "flex-start" }}
            onClick={() => onClarifyPaper(p.id)}
          >
            {p.fileName}
          </button>
        ))}

        {papers.length > 1 && (
          <button
            className="followup-btn"
            style={{
              textAlign: "left",
              justifyContent: "flex-start",
              borderColor: "var(--accent, #6ee7b7)",
              color: "var(--accent, #6ee7b7)",
            }}
            onClick={onClarifyBoth}
          >
            Both papers — show answers side by side
          </button>
        )}
      </div>
    </div>
  );
}

// ── Retrieval result ───────────────────────────────────────────────────────────
function RetrievalResult({ result }) {
  return (
    <div className="result-section">
      <div className="result-agent-label">
        <span className="result-agent-dot" />
        Retrieval Agent — fetched from database
      </div>

      {/* Single-paper metadata answer */}
      {result.answer_source === "metadata" && !result.per_paper_answers && (
        <>
          {result.answer ? (
            <p className="answer-text" style={{ margin: "0.75rem 0" }}>{result.answer}</p>
          ) : (
            <div className="warning-banner">
              ⚠ Metadata not found. Please re-upload the paper so it can be re-processed.
            </div>
          )}
        </>
      )}

      {/* Multi-paper metadata — per-paper labeled answers */}
      {result.answer_source === "metadata" && result.per_paper_answers && (
        <div style={{ marginTop: "0.75rem", display: "flex", flexDirection: "column", gap: "1rem" }}>
          {result.per_paper_answers.map((p, i) => (
            <div
              key={i}
              style={{
                background: "var(--surface-2, rgba(255,255,255,0.04))",
                border: "1px solid var(--border)",
                borderRadius: "8px",
                padding: "0.75rem 1rem",
              }}
            >
              <p
                style={{
                  fontSize: "0.72rem",
                  fontFamily: "var(--font-mono)",
                  color: "var(--accent, #6ee7b7)",
                  marginBottom: "0.4rem",
                  letterSpacing: "0.05em",
                  textTransform: "uppercase",
                }}
              >
                {p.paper_title || p.file_name}
              </p>
              {p.answer ? (
                <p className="answer-text" style={{ margin: 0 }}>{p.answer}</p>
              ) : (
                <p style={{ color: "var(--text-muted)", fontSize: "0.8rem", margin: 0 }}>
                  Metadata not available for this paper.
                </p>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Content query — show relevant passages from ChromaDB */}
      {result.answer_source === "content" && (
        <>
          <p className="answer-text" style={{ margin: "0.75rem 0 0.5rem" }}>{result.message}</p>

          {!result.found_in_doc && (
            <div className="warning-banner">
              ⚠ No relevant passages found in the paper for this query.
            </div>
          )}

          {result.passages?.length > 0 && (
            <>
              <p className="passages-heading" style={{ marginBottom: "0.5rem" }}>Relevant Passages</p>
              {result.passages.map((p, i) => (
                <div key={i} style={{ marginBottom: "0.75rem" }}>
                  <blockquote>{p.text}</blockquote>
                  <p style={{ fontSize: "0.68rem", color: "var(--text-muted)", marginTop: "0.25rem", paddingLeft: "0.5rem", fontFamily: "var(--font-mono)" }}>
                    {p.source_file && <span>{p.source_file} · </span>}chunk {p.chunk_index + 1} of {p.total_chunks}
                  </p>
                </div>
              ))}
            </>
          )}
        </>
      )}
    </div>
  );
}

function FactCheckResult({ result }) {
  return (
    <div className="result-section">
      <div className="result-agent-label">
        <span className="result-agent-dot" />
        Fact-Check Agent
      </div>

      <div className={`verdict-pill verdict-${result.verdict}`}>
        {result.verdict?.replace("_", " ")}
      </div>

      <p className="verdict-explanation">{result.verdict_explanation}</p>

      {result.supporting_quote && (
        <>
          <p className="passages-heading">Supporting evidence</p>
          <blockquote>"{result.supporting_quote}"</blockquote>
        </>
      )}

      {result.contradicting_quote && (
        <>
          <p className="passages-heading">Contradicting evidence</p>
          <blockquote className="conflict-quote">"{result.contradicting_quote}"</blockquote>
        </>
      )}

      <div className="confidence-badge">
        Confidence: {result.confidence}
      </div>

      {result.warning && (
        <div className="warning-banner">
          ⚠ {result.warning}
        </div>
      )}
    </div>
  );
}

function AnalysisResult({ result, onFollowup }) {
  return (
    <div className="result-section">
      <div className="result-agent-label">
        <span className="result-agent-dot" />
        Analysis Agent
      </div>

      <div className="doc-type-badge">{result.document_type}</div>

      {result.papers_analyzed?.length > 1 && (
        <p style={{ fontSize: "0.75rem", color: "var(--text-muted)", margin: "0.4rem 0 0.75rem", fontFamily: "var(--font-mono)" }}>
          Analyzing: {result.papers_analyzed.join(" · ")}
        </p>
      )}

      <div className="summary-block">
        <h2>Summary</h2>
        <p>{result.summary}</p>
      </div>

      {result.key_highlights?.length > 0 && (
        <div className="highlights-grid">
          <p className="section-heading">Key Highlights</p>
          {result.key_highlights.map((h, i) => (
            <div
              className="highlight-card"
              key={i}
              style={{ animationDelay: `${i * 0.1}s` }}
            >
              <span className="highlight-dot" />
              <div>
                <strong>{h.point}</strong>
                <p>{h.importance}</p>
              </div>
            </div>
          ))}
        </div>
      )}

      {result.risk_flags?.length > 0 && (
        <div className="risk-section">
          <p className="section-heading">Risk Flags</p>
          {result.risk_flags.map((r, i) => (
            <div
              className={`risk-flag severity-${r.severity}`}
              key={i}
              style={{ animationDelay: `${i * 0.12}s` }}
            >
              <span className="severity-dot" />
              <div>
                <strong>{r.flag}</strong>
                <p>{r.detail}</p>
              </div>
              <span className={`severity-badge ${r.severity}`}>{r.severity}</span>
            </div>
          ))}
        </div>
      )}

      {result.gaps?.length > 0 && (
        <div className="gaps-section">
          <p className="section-heading">What's Missing</p>
          <ul>
            {result.gaps.map((g, i) => (
              <li key={i}>{g}</li>
            ))}
          </ul>
        </div>
      )}

      {result.big_picture_insight && (
        <div className="insight-card">
          <span className="insight-label">Big picture insight</span>
          <p className="insight-text">{result.big_picture_insight}</p>
        </div>
      )}

      {result.recommended_followup_questions?.length > 0 && (
        <div className="followup-section">
          <p className="section-heading">Suggested follow-up questions</p>
          {result.recommended_followup_questions.map((q, i) => (
            <button
              className="followup-btn"
              key={i}
              onClick={() => onFollowup(q)}
            >
              {q}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

export default function ResultPanel({ status, activeAgent, result, error, clarification, onFollowup, onClarifyPaper, onClarifyBoth }) {
  if (error) {
    return (
      <div className="result-panel">
        <div className="error-banner">
          <strong>Error:</strong> {error}
        </div>
      </div>
    );
  }

  if (status === "idle") {
    return (
      <div className="result-panel">
        <div className="empty-state">
          <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1">
            <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" />
          </svg>
          <p>Upload a document and ask a question to begin your research analysis.</p>
        </div>
      </div>
    );
  }

  if (["routing", "running"].includes(status)) {
    return (
      <div className="result-panel">
        <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
          {[120, 80, 100, 60].map((w, i) => (
            <div
              key={i}
              className="skeleton"
              style={{ height: "18px", width: `${w}%`, maxWidth: "100%" }}
            />
          ))}
        </div>
      </div>
    );
  }

  if (status === "done") {
    // Clarification — orchestrator needs the user to pick a paper
    if (clarification) {
      return (
        <div className="result-panel">
          <ClarificationResult
            clarification={clarification}
            onClarifyPaper={onClarifyPaper}
            onClarifyBoth={onClarifyBoth}
          />
        </div>
      );
    }

    if (result) {
      return (
        <div className="result-panel">
          {activeAgent === "retrieval" && <RetrievalResult result={result} />}
          {activeAgent === "factcheck" && <FactCheckResult result={result} />}
          {activeAgent === "analysis" && <AnalysisResult result={result} onFollowup={onFollowup} />}
        </div>
      );
    }
  }

  return null;
}
