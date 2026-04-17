"""Document Agent — Agent 1.

Runs first in the pipeline (before the orchestrator routes to any specialist).
Responsibilities:
  1. Chunk the uploaded document using recursive splitting
  2. Embed each chunk with sentence-transformers (all-MiniLM-L6-v2)
  3. Persist chunks + per-chunk metadata to ChromaDB (vector store)
  4. Persist document-level metadata to SQLite (metadata registry)
  5. Write the collection name into state so downstream agents can query it

Two-store architecture
  ChromaDB  — chunk vectors + chunk-level metadata (file_name, chunk_index,
               total_chunks, char_start). Used by retrieval & factcheck agents
               for cosine-similarity search.
  SQLite    — document-level metadata (file_name, collection_name,
               total_chunks, char_count, uploaded_at). Used for listing
               documents, fetching paper info, and admin endpoints without
               touching the vector store.
"""

from state import AgentState
from tools.document_tools import store_document
from tools.metadata_store import save_metadata


def document_agent_node(state: AgentState) -> AgentState:
    try:
        collection_name, total_chunks = store_document(
            state["file_name"], state["document_text"]
        )

        # Write document-level record to SQLite
        save_metadata(
            file_name=state["file_name"],
            collection_name=collection_name,
            total_chunks=total_chunks,
            char_count=len(state["document_text"]),
        )

        return {**state, "collection_name": collection_name}
    except Exception as e:
        return {**state, "collection_name": None, "error": str(e)}
