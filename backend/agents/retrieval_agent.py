"""Retrieval Agent — smart fetch from two stores.

- Metadata queries (authors, title, year, journal, DOI, abstract, etc.)
  → reads from SQLite, then uses GPT-4o-mini to give a direct natural language answer.

- Content queries (findings, methods, results, statistics, etc.)
  → cosine similarity search against ChromaDB chunks.
"""

import os
import json
from openai import OpenAI
from state import AgentState
from tools.document_tools import similarity_search
from tools.metadata_store import get_paper_metadata

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

# Keywords that signal the user wants paper-level metadata from SQLite
METADATA_KEYWORDS = [
    # authorship
    "author", "authors", "who wrote", "who are the", "written by", "wrote this",
    # title
    "title", "what is this paper", "name of the paper", "name of the study",
    # publication details
    "journal", "published", "publication", "year", "when was", "date",
    "doi", "volume", "issue", "conference",
    # affiliation
    "institution", "affiliation", "university", "college", "funded", "funding",
    "where is", "which university", "which institution",
    # abstract / keywords
    "abstract", "summary of the paper", "overview of the paper",
    "keyword", "keywords", "topic", "topics",
]


def _is_metadata_query(query: str) -> bool:
    q = query.lower()
    return any(kw in q for kw in METADATA_KEYWORDS)


def _generate_answer(query: str, paper_meta: dict) -> str:
    """Use GPT-4o-mini to generate a focused natural language answer from SQLite metadata."""
    try:
        meta_str = json.dumps(paper_meta, indent=2)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a research assistant. Answer the user's question directly and concisely "
                        "using ONLY the paper metadata provided. Be specific and complete — include all "
                        "relevant names, affiliations, years, etc. from the metadata. "
                        "If the specific information is not in the metadata, say so clearly."
                    ),
                },
                {
                    "role": "user",
                    "content": f"Paper metadata:\n{meta_str}\n\nQuestion: {query}",
                },
            ],
            max_tokens=400,
        )
        return response.choices[0].message.content.strip()
    except Exception:
        return None


def retrieval_node(state: AgentState) -> AgentState:
    try:
        _raw = get_paper_metadata(state["collection_name"])  # None = no DB record
        record_exists = _raw is not None
        paper_meta = _raw or {}
        query = state["user_query"]

        if _is_metadata_query(query):
            # Fetch from SQLite, then generate a direct natural language answer.
            # has_content = True when the dict has any data at all (extraction worked).
            has_content = bool(paper_meta)

            answer = _generate_answer(query, paper_meta) if has_content else None

            return {
                **state,
                "retrieval_result": {
                    "found_in_doc": record_exists,
                    "query": query,
                    "answer_source": "metadata",
                    "answer": answer,
                    "paper_metadata": paper_meta,
                    "passages": [],
                    "message": (
                        answer if answer else
                        (
                            "Metadata extraction failed for this paper. Try re-uploading."
                            if record_exists else
                            "Document not found in database. Please re-upload the paper."
                        )
                    ),
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
                "answer": None,
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
                "answer": None,
                "paper_metadata": {},
                "passages": [],
                "message": f"Retrieval error: {str(e)}",
            },
            "error": str(e),
        }
