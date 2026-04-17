"""Retrieval Agent — smart fetch across one or more document stores.

- Metadata queries (authors, title, year, journal, DOI, abstract, etc.)
  → reads from SQLite for all selected papers, then GPT-4o-mini answers directly.

- Content queries (findings, methods, results, statistics, etc.)
  → cosine similarity search across all selected ChromaDB collections,
    merged and ranked by distance.
"""

import os
import json
from openai import OpenAI
from state import AgentState
from tools.document_tools import similarity_search
from tools.metadata_store import get_paper_metadata, get_paper_metadata_batch

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

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


def _resolve_collections(state: AgentState):
    names = state.get("collection_names") or (
        [state["collection_name"]] if state.get("collection_name") else []
    )
    files = state.get("file_names") or (
        [state["file_name"]] if state.get("file_name") else []
    )
    while len(files) < len(names):
        files.append("unknown")
    return names, files


def _generate_answer(query: str, meta_payload) -> str:
    """Generate a focused natural language answer from SQLite metadata.
    meta_payload is either a single dict or a list of dicts (multi-paper).
    """
    try:
        meta_str = json.dumps(meta_payload, indent=2)
        is_multi = isinstance(meta_payload, list)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a research assistant. Answer the user's question directly and concisely "
                        "using ONLY the paper metadata provided. Be specific and complete — include all "
                        "relevant names, affiliations, years, etc. "
                        + ("When multiple papers are provided, clearly attribute each piece of info to the correct paper. "
                           if is_multi else "")
                        + "If the specific information is not in the metadata, say so clearly."
                    ),
                },
                {
                    "role": "user",
                    "content": f"Paper metadata:\n{meta_str}\n\nQuestion: {query}",
                },
            ],
            max_tokens=500,
        )
        return response.choices[0].message.content.strip()
    except Exception:
        return None


def _generate_per_paper_answers(query: str, records: list) -> list:
    """For multi-paper metadata queries, generate a separate answer per paper.
    Returns list of {paper_title, file_name, answer} dicts.
    """
    results = []
    for rec in records:
        pm = rec.get("paper_metadata", {})
        title = pm.get("title") or rec.get("file_name", "Unknown paper")
        if not pm:
            results.append({"paper_title": title, "file_name": rec.get("file_name", ""), "answer": None})
            continue
        answer = _generate_answer(query, pm)
        results.append({
            "paper_title": title,
            "file_name": rec.get("file_name", ""),
            "answer": answer,
        })
    return results


def retrieval_node(state: AgentState) -> AgentState:
    try:
        collection_names, file_names = _resolve_collections(state)
        query = state["user_query"]
        
        is_metadata = (state.get("retrieval_type") == "metadata") or _is_metadata_query(query)

        if is_metadata:
            # Fetch metadata for all selected papers from SQLite
            records = get_paper_metadata_batch(collection_names)
            record_exists = len(records) > 0

            if len(records) == 1:
                paper_meta = records[0]["paper_metadata"]
                has_content = bool(paper_meta)
                answer = _generate_answer(query, paper_meta) if has_content else None
                return {
                    **state,
                    "retrieval_result": {
                        "found_in_doc": record_exists,
                        "query": query,
                        "answer_source": "metadata",
                        "answer": answer,
                        "per_paper_answers": None,
                        "paper_metadata": paper_meta,
                        "passages": [],
                        "message": answer or (
                            "Metadata extraction failed. Try re-uploading the paper."
                            if record_exists else
                            "Document not found in database. Please re-upload."
                        ),
                    },
                }
            else:
                # Multi-paper: generate a separate labeled answer per paper
                per_paper = _generate_per_paper_answers(query, records)
                has_content = any(p["answer"] for p in per_paper)
                return {
                    **state,
                    "retrieval_result": {
                        "found_in_doc": record_exists,
                        "query": query,
                        "answer_source": "metadata",
                        "answer": None,          # not used for multi-paper
                        "per_paper_answers": per_paper,
                        "paper_metadata": None,
                        "passages": [],
                        "message": (
                            f"Found metadata across {len(per_paper)} papers."
                            if has_content else
                            "Metadata extraction failed. Try re-uploading the papers."
                        ),
                    },
                }

        # Content query — search ChromaDB across all selected collections
        all_hits = []
        for col_name, fname in zip(collection_names, file_names):
            try:
                hits = similarity_search(col_name, query, top_k=5)
                for h in hits:
                    h["source_file"] = fname
                    h["source_collection"] = col_name
                all_hits.extend(hits)
            except Exception:
                pass  # skip missing/corrupt collections

        # Merge by cosine distance (lower = more similar) and take global top 5
        all_hits.sort(key=lambda h: h.get("distance", 1.0))
        top_hits = all_hits[:5]

        passages = [
            {
                "text": h["text"],
                "chunk_index": h["metadata"]["chunk_index"],
                "total_chunks": h["metadata"]["total_chunks"],
                "char_start": h["metadata"].get("char_start", 0),
                "source_file": h.get("source_file", ""),
            }
            for h in top_hits
        ]

        paper_count = len(collection_names)
        return {
            **state,
            "retrieval_result": {
                "found_in_doc": len(passages) > 0,
                "query": query,
                "answer_source": "content",
                "answer": None,
                "per_paper_answers": None,
                "paper_metadata": {},
                "passages": passages,
                "message": (
                    f"Found {len(passages)} relevant passage(s) across {paper_count} paper(s)."
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
                "per_paper_answers": None,
                "paper_metadata": {},
                "passages": [],
                "message": f"Retrieval error: {str(e)}",
            },
            "error": str(e),
        }
