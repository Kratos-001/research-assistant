import { useState, useRef } from "react";

function formatBytes(bytes) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export default function FileUpload({ file, onFileChange }) {
  const [dragOver, setDragOver] = useState(false);
  const inputRef = useRef(null);

  const MAX_MB = 20;

  function validateAndSet(f) {
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
    onFileChange(f);
  }

  function handleDrop(e) {
    e.preventDefault();
    setDragOver(false);
    validateAndSet(e.dataTransfer.files[0]);
  }

  function handleChange(e) {
    validateAndSet(e.target.files[0]);
  }

  function handleRemove(e) {
    e.stopPropagation();
    onFileChange(null);
    if (inputRef.current) inputRef.current.value = "";
  }

  const zoneClass = [
    "drop-zone",
    dragOver ? "drag-over" : "",
    file ? "has-file" : "",
  ]
    .filter(Boolean)
    .join(" ");

  return (
    <div>
      <div
        className={zoneClass}
        onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
        onDragLeave={() => setDragOver(false)}
        onDrop={handleDrop}
        onClick={() => !file && inputRef.current?.click()}
      >
        <input
          ref={inputRef}
          type="file"
          accept=".pdf,.txt"
          onChange={handleChange}
          style={{ display: "none" }}
        />

        {file ? (
          <>
            <div className="drop-icon">
              <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
            <div className="file-info">
              <span className="file-type-badge">
                {file.name.endsWith(".pdf") ? "PDF" : "TXT"}
              </span>
              <span className="file-name">{file.name}</span>
              <span className="file-size">{formatBytes(file.size)}</span>
              <button className="remove-file-btn" onClick={handleRemove} title="Remove file">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
          </>
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
    </div>
  );
}
