"""Retrieval Agent — fetches data from the two stores.

- Paper metadata (title, authors, abstract, year, etc.) → SQLite
- Relevant content passages → ChromaDB cosine similarity search

No LLM calls. Pure database fetch.
"""

from state import AgentState
from tools.document_tools import similarity_search
from tools.metadata_store import get_paper_metadata


def retrieval_node(state: AgentState) -> AgentState:
    try:
        # Fetch paper metadata from SQLite
        paper_meta = get_paper_metadata(state["collection_name"]) or {}

        # Fetch relevant passages from ChromaDB
        hits = similarity_search(state["collection_name"], state["user_query"], top_k=5)

        passages = [
            {
                "text": h["text"],
                "chunk_index": h["metadata"]["chunk_index"],
                "total_chunks": h["metadata"]["total_chunks"],
                "char_start": h["metadata"].get("char_start", 0),
            }
            for h in hits
        ]

        return {
            **state,
            "retrieval_result": {
                "found_in_doc": len(passages) > 0,
                "query": state["user_query"],
                # Structured metadata from SQLite
                "paper_metadata": {
                    "title":       paper_meta.get("title"),
                    "authors":     paper_meta.get("authors", []),
                    "abstract":    paper_meta.get("abstract"),
                    "year":        paper_meta.get("year"),
                    "journal":     paper_meta.get("journal"),
                    "doi":         paper_meta.get("doi"),
                    "keywords":    paper_meta.get("keywords", []),
                    "institution": paper_meta.get("institution", []),
                },
                # Relevant content passages from ChromaDB
                "passages": passages,
                "message": (
                    f"Found {len(passages)} relevant passage(s) from {state['file_name']}."
                    if passages else
                    "No relevant passages found in the paper for this query."
                ),
            },
        }

    except Exception as e:
        return {
            **state,
            "retrieval_result": {
                "found_in_doc": False,
                "query": state["user_query"],
                "paper_metadata": {},
                "passages": [],
                "message": f"Retrieval error: {str(e)}",
            },
            "error": str(e),
        }
