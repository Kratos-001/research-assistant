"""Retrieval Agent — smart fetch from two stores.

- Metadata queries (authors, title, year, journal, DOI, etc.)
  → answered directly from SQLite, no ChromaDB search at all.

- Content queries (findings, methods, results, statistics, etc.)
  → cosine similarity search against ChromaDB chunks.
"""

import re
from state import AgentState
from tools.document_tools import similarity_search
from tools.metadata_store import get_paper_metadata

# Keywords that signal the user wants paper-level metadata, not content
METADATA_KEYWORDS = [
    "author", "authors", "who wrote", "who are the", "written by",
    "title", "journal", "published", "publication", "year", "doi",
    "institution", "affiliation", "university", "college", "funded",
    "keyword", "keywords",
]


def _is_metadata_query(query: str) -> bool:
    q = query.lower()
    return any(kw in q for kw in METADATA_KEYWORDS)


def retrieval_node(state: AgentState) -> AgentState:
    try:
        paper_meta = get_paper_metadata(state["collection_name"]) or {}
        query = state["user_query"]

        if _is_metadata_query(query):
            # Pure metadata fetch from SQLite — no chunk search needed
            return {
                **state,
                "retrieval_result": {
                    "found_in_doc": bool(paper_meta),
                    "query": query,
                    "answer_source": "metadata",
                    "paper_metadata": paper_meta,
                    "passages": [],
                    "message": "Answered from paper metadata.",
                },
            }

        # Content query — search ChromaDB
        hits = similarity_search(state["collection_name"], query, top_k=5)
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
                "query": query,
                "answer_source": "content",
                "paper_metadata": paper_meta,
                "passages": passages,
                "message": (
                    f"Found {len(passages)} relevant passage(s) from {state['file_name']}."
                    if passages else
                    "No relevant passages found for this query."
                ),
            },
        }

    except Exception as e:
        return {
            **state,
            "retrieval_result": {
                "found_in_doc": False,
                "query": state["user_query"],
                "answer_source": None,
                "paper_metadata": {},
                "passages": [],
                "message": f"Retrieval error: {str(e)}",
            },
            "error": str(e),
        }
