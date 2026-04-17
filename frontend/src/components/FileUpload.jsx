import { useState, useRef } from "react";

function formatBytes(bytes) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function StatusIcon({ status }) {
  if (status === "uploading") {
    return <div className="spinner" style={{ width: 14, height: 14, flexShrink: 0 }} />;
  }
  if (status === "ready") {
    return (
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="var(--accent)" strokeWidth="2.5" style={{ flexShrink: 0 }}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
      </svg>
    );
  }
  if (status === "error") {
    return (
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="var(--danger, #f87171)" strokeWidth="2" style={{ flexShrink: 0 }}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126z" />
        <path strokeLinecap="round" strokeLinejoin="round" d="M12 15.75h.007v.008H12v-.008z" />
      </svg>
    );
  }
  return null;
}

export default function FileUpload({ papers, onFileAdd, onFileRemove }) {
  const [dragOver, setDragOver] = useState(false);
  const inputRef = useRef(null);
  const MAX_MB = 20;

  function validateAndAdd(f) {
    if (!f) return;
    const ext = f.name.split(".").pop().toLowerCase();
    if (!["pdf", "txt"].includes(ext)) {
      alert("Only PDF and TXT files are accepted.");
      return;
    }
    if (f.size > MAX_MB * 1024 * 1024) {
      alert(`File is too large. Maximum size is ${MAX_MB} MB.`);
      return;
    }
    if (f.size === 0) {
      alert("The file is empty.");
      return;
    }
    onFileAdd(f);
    if (inputRef.current) inputRef.current.value = "";
  }

  function handleDrop(e) {
    e.preventDefault();
    setDragOver(false);
    Array.from(e.dataTransfer.files).forEach(validateAndAdd);
  }

  function handleChange(e) {
    Array.from(e.target.files).forEach(validateAndAdd);
    if (inputRef.current) inputRef.current.value = "";
  }

  const zoneClass = ["drop-zone", dragOver ? "drag-over" : ""].filter(Boolean).join(" ");
  const hasPapers = papers.length > 0;

  return (
    <div>
      {/* Drop zone */}
      <div
        className={zoneClass}
        style={hasPapers ? { padding: "0.75rem 1rem" } : {}}
        onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
        onDragLeave={() => setDragOver(false)}
        onDrop={handleDrop}
        onClick={() => inputRef.current?.click()}
      >
        <input
          ref={inputRef}
          type="file"
          accept=".pdf,.txt"
          multiple
          onChange={handleChange}
          style={{ display: "none" }}
        />
        {hasPapers ? (
          <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", color: "var(--text-muted)", fontSize: "0.8rem" }}>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
            </svg>
            Add another paper
          </div>
        ) : (
          <>
            <div className="drop-icon">
              <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                <path strokeLinecap="round" strokeLinejoin="round" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5m-13.5-9L12 3m0 0l4.5 4.5M12 3v13.5" />
              </svg>
            </div>
            <p className="drop-label">Drop your research paper here or click to browse</p>
            <p className="drop-hint">Research papers only &nbsp;·&nbsp; PDF &nbsp;·&nbsp; TXT</p>
          </>
        )}
      </div>

      {/* Paper list */}
      {papers.map((paper) => (
        <div
          key={paper.id}
          style={{
            display: "flex",
            alignItems: "center",
            gap: "0.5rem",
            marginTop: "0.5rem",
            padding: "0.5rem 0.65rem",
            background: "var(--surface-2, rgba(255,255,255,0.04))",
            borderRadius: "8px",
            border: "1px solid var(--border)",
          }}
        >
          <StatusIcon status={paper.uploadStatus} />
          <span className="file-type-badge" style={{ flexShrink: 0 }}>
            {paper.fileName?.endsWith(".pdf") ? "PDF" : "TXT"}
          </span>
          <span style={{
            fontSize: "0.78rem",
            color: "var(--text-secondary)",
            overflow: "hidden",
            textOverflow: "ellipsis",
            whiteSpace: "nowrap",
            flex: 1,
          }}>
            {paper.fileName}
          </span>
          {paper.uploadStatus === "error" && (
            <span
              title={paper.uploadError || "Upload failed"}
              style={{ fontSize: "0.7rem", color: "var(--danger, #f87171)", flexShrink: 0, maxWidth: "140px", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", cursor: "help" }}
            >
              {paper.uploadError || "Upload failed"}
            </span>
          )}
          <button
            onClick={(e) => { e.stopPropagation(); onFileRemove(paper.id); }}
            title="Remove"
            style={{
              background: "none",
              border: "none",
              cursor: "pointer",
              color: "var(--text-muted)",
              padding: "2px",
              display: "flex",
              flexShrink: 0,
            }}
          >
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
      ))}
    </div>
  );
}
