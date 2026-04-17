"""SQLite-backed document metadata registry.

Stores document-level metadata separately from ChromaDB so it can be
queried without touching the vector store. ChromaDB owns the chunks +
embeddings; this module owns the document registry.

Schema
------
documents
  id             INTEGER  PK autoincrement
  file_name      TEXT     original upload filename
  collection_name TEXT    ChromaDB collection name for this document
  total_chunks   INTEGER  number of chunks stored in ChromaDB
  char_count     INTEGER  total characters in the extracted text
  uploaded_at    TEXT     ISO-8601 UTC timestamp
"""

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
    con.row_factory = sqlite3.Row  # rows behave like dicts
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
                uploaded_at     TEXT    NOT NULL
            )
        """)


def save_metadata(
    file_name: str,
    collection_name: str,
    total_chunks: int,
    char_count: int,
) -> dict:
    """Insert or replace a document metadata record.

    Uses INSERT OR REPLACE so re-uploading the same file updates the row
    (collection_name has a UNIQUE constraint).
    """
    uploaded_at = datetime.now(timezone.utc).isoformat()
    with _conn() as con:
        con.execute("""
            INSERT INTO documents (file_name, collection_name, total_chunks, char_count, uploaded_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(collection_name) DO UPDATE SET
                file_name    = excluded.file_name,
                total_chunks = excluded.total_chunks,
                char_count   = excluded.char_count,
                uploaded_at  = excluded.uploaded_at
        """, (file_name, collection_name, total_chunks, char_count, uploaded_at))

    return get_metadata(collection_name)


def get_metadata(collection_name: str) -> dict | None:
    """Fetch metadata for a single document by collection name."""
    with _conn() as con:
        row = con.execute(
            "SELECT * FROM documents WHERE collection_name = ?", (collection_name,)
        ).fetchone()
    return dict(row) if row else None


def list_documents() -> list[dict]:
    """Return all document metadata records, newest first."""
    with _conn() as con:
        rows = con.execute(
            "SELECT * FROM documents ORDER BY uploaded_at DESC"
        ).fetchall()
    return [dict(r) for r in rows]


def delete_metadata(collection_name: str) -> bool:
    """Remove a document's metadata record. Returns True if a row was deleted."""
    with _conn() as con:
        cursor = con.execute(
            "DELETE FROM documents WHERE collection_name = ?", (collection_name,)
        )
    return cursor.rowcount > 0
