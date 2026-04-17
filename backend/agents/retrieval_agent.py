"""Retrieval Agent — pure ChromaDB fetch, no LLM.

Queries the vector store with the user's query, retrieves the top-k most
semantically similar chunks, and returns them directly as the result.
No generation, no hallucination risk — just what the DB has.
"""

from state import AgentState
from tools.document_tools import similarity_search


def retrieval_node(state: AgentState) -> AgentState:
    try:
        hits = similarity_search(state["collection_name"], state["user_query"], top_k=5)

        if not hits:
            return {
                **state,
                "retrieval_result": {
                    "found_in_doc": False,
                    "query": state["user_query"],
                    "passages": [],
                    "message": "No relevant passages found in the paper for this query.",
                },
            }

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
                "found_in_doc": True,
                "query": state["user_query"],
                "passages": passages,
                "message": f"Found {len(passages)} relevant passage(s) from {state['file_name']}.",
            },
        }

    except Exception as e:
        return {
            **state,
            "retrieval_result": {
                "found_in_doc": False,
                "query": state["user_query"],
                "passages": [],
                "message": f"Retrieval error: {str(e)}",
            },
            "error": str(e),
        }
