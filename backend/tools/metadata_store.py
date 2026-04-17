"""SQLite-backed document metadata registry.

Two responsibilities:
1. Document registry — one row per uploaded paper (file_name, chunks, upload time)
2. Paper metadata — structured JSON extracted from the paper (title, authors,
   abstract, year, journal, DOI, keywords) stored in the `paper_metadata` column

The retrieval agent reads from here when the user asks about paper metadata
(authors, title, year, etc.) instead of doing a vector search.

Schema
------
documents
  id              INTEGER  PK autoincrement
  file_name       TEXT     original upload filename
  collection_name TEXT     ChromaDB collection name (UNIQUE)
  total_chunks    INTEGER  number of chunks in ChromaDB
  char_count      INTEGER  total characters in extracted text
  uploaded_at     TEXT     ISO-8601 UTC timestamp
  paper_metadata  TEXT     JSON — extracted paper info (title, authors, etc.)
"""

import json
import sqlite3
import os
from datetime import datetime, timezone
from contextlib import contextmanager

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "metadata.db")


def _db_path() -> str:
    return os.path.abspath(DB_PATH)


@contextmanager
def _conn():
    con = sqlite3.connect(_db_path())
    con.row_factory = sqlite3.Row
    try:
        yield con
        con.commit()
    finally:
        con.close()


def init_db() -> None:
    """Create the documents table if it doesn't exist. Call once at startup."""
    with _conn() as con:
        con.execute("""
            CREATE TABLE IF NOT EXISTS documents (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                file_name       TEXT    NOT NULL,
                collection_name TEXT    NOT NULL UNIQUE,
                total_chunks    INTEGER NOT NULL,
                char_count      INTEGER NOT NULL,
                uploaded_at     TEXT    NOT NULL,
                paper_metadata  TEXT    DEFAULT '{}'
            )
        """)
        # Add paper_metadata column if upgrading from old schema
        try:
            con.execute("ALTER TABLE documents ADD COLUMN paper_metadata TEXT DEFAULT '{}'")
        except Exception:
            pass  # column already exists


def save_metadata(
    file_name: str,
    collection_name: str,
    total_chunks: int,
    char_count: int,
    paper_metadata: dict | None = None,
) -> dict:
    """Insert or replace a document record including extracted paper metadata JSON."""
    uploaded_at = datetime.now(timezone.utc).isoformat()
    meta_json = json.dumps(paper_metadata or {})

    with _conn() as con:
        con.execute("""
            INSERT INTO documents
                (file_name, collection_name, total_chunks, char_count, uploaded_at, paper_metadata)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(collection_name) DO UPDATE SET
                file_name      = excluded.file_name,
                total_chunks   = excluded.total_chunks,
                char_count     = excluded.char_count,
                uploaded_at    = excluded.uploaded_at,
                paper_metadata = excluded.paper_metadata
        """, (file_name, collection_name, total_chunks, char_count, uploaded_at, meta_json))

    return get_metadata(collection_name)


def get_paper_metadata(collection_name: str) -> dict | None:
    """Fetch only the extracted paper metadata JSON for a document."""
    with _conn() as con:
        row = con.execute(
            "SELECT paper_metadata FROM documents WHERE collection_name = ?",
            (collection_name,)
        ).fetchone()
    if not row:
        return None
    return json.loads(row["paper_metadata"] or "{}")


def get_metadata(collection_name: str) -> dict | None:
    """Fetch the full registry record for a document."""
    with _conn() as con:
        row = con.execute(
            "SELECT * FROM documents WHERE collection_name = ?", (collection_name,)
        ).fetchone()
    if not row:
        return None
    record = dict(row)
    record["paper_metadata"] = json.loads(record.get("paper_metadata") or "{}")
    return record


def get_paper_metadata_batch(collection_names: list) -> list[dict]:
    """Fetch full records for a list of collection names in one query."""
    if not collection_names:
        return []
    placeholders = ",".join("?" * len(collection_names))
    with _conn() as con:
        rows = con.execute(
            f"SELECT * FROM documents WHERE collection_name IN ({placeholders})",
            collection_names,
        ).fetchall()
    result = []
    for r in rows:
        record = dict(r)
        record["paper_metadata"] = json.loads(record.get("paper_metadata") or "{}")
        result.append(record)
    return result


def list_documents() -> list[dict]:
    """Return all document records, newest first."""
    with _conn() as con:
        rows = con.execute(
            "SELECT * FROM documents ORDER BY uploaded_at DESC"
        ).fetchall()
    result = []
    for r in rows:
        record = dict(r)
        record["paper_metadata"] = json.loads(record.get("paper_metadata") or "{}")
        result.append(record)
    return result


def delete_metadata(collection_name: str) -> bool:
    """Remove a document record. Returns True if a row was deleted."""
    with _conn() as con:
        cursor = con.execute(
            "DELETE FROM documents WHERE collection_name = ?", (collection_name,)
        )
    return cursor.rowcount > 0
