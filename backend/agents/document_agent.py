"""Document Agent — Agent 1.

Runs first in the pipeline. Responsibilities:
  1. Chunk + embed + store document in ChromaDB (vector search)
  2. Extract structured paper metadata via GPT-4o and store as JSON in SQLite

Metadata extracted and stored in SQLite (paper_metadata JSON column):
  - title
  - authors        list of author names
  - abstract
  - year
  - journal        journal or conference name
  - doi
  - keywords
  - institution    author affiliations / institutions
"""

import os
import json
from openai import OpenAI
from state import AgentState
from tools.document_tools import store_document
from tools.metadata_store import save_metadata

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

EXTRACTION_PROMPT = """You are a research paper metadata extractor.
Extract the following fields from the paper text provided.
If a field is not present, use null.

Respond ONLY in JSON:
{
  "title": "full paper title",
  "authors": ["Author One", "Author Two"],
  "abstract": "full abstract text",
  "year": "publication year as string or null",
  "journal": "journal or conference name or null",
  "doi": "DOI string or null",
  "keywords": ["keyword1", "keyword2"],
  "institution": ["institution/affiliation 1", "institution/affiliation 2"]
}"""


def _extract_paper_metadata(text: str) -> dict:
    """Use GPT-4o to extract structured metadata from the first part of the paper."""
    try:
        # Title, authors, abstract are almost always in the first 3000 chars
        preview = text[:3000]
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": EXTRACTION_PROMPT},
                {"role": "user", "content": f"Paper text:\n{preview}"},
            ],
            max_tokens=512,
            response_format={"type": "json_object"},
        )
        return json.loads(response.choices[0].message.content)
    except Exception:
        return {}


def document_agent_node(state: AgentState) -> AgentState:
    try:
        # 1. Store chunks + embeddings in ChromaDB
        collection_name, total_chunks = store_document(
            state["file_name"], state["document_text"]
        )

        # 2. Extract paper metadata (title, authors, abstract, etc.)
        paper_metadata = _extract_paper_metadata(state["document_text"])

        # 3. Persist document record + metadata JSON to SQLite
        save_metadata(
            file_name=state["file_name"],
            collection_name=collection_name,
            total_chunks=total_chunks,
            char_count=len(state["document_text"]),
            paper_metadata=paper_metadata,
        )

        return {**state, "collection_name": collection_name}
    except Exception as e:
        return {**state, "collection_name": None, "error": str(e)}
