import os
import json
from openai import OpenAI
from state import AgentState
from tools.document_tools import similarity_search

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

SYSTEM_PROMPT = """You are a precise document retrieval specialist.
You have been given relevant excerpts from a document and a user query.
Your job is to extract and present ONLY the information from the document that directly answers the query.
Do not add information not in the document.
Do not hallucinate.
Always cite which part of the document you found the answer in.

Respond in JSON:
{
  "answer": "direct answer based on the document",
  "relevant_passages": ["passage 1", "passage 2"],
  "source_sections": ["section or location description"],
  "confidence": "high | medium | low",
  "found_in_doc": true | false
}"""


def retrieval_node(state: AgentState) -> AgentState:
    try:
        hits = similarity_search(state["collection_name"], state["user_query"], top_k=5)

        context = "\n\n---\n\n".join(h["text"] for h in hits)
        source_hints = ", ".join(
            f"chunk {h['metadata']['chunk_index'] + 1}/{h['metadata']['total_chunks']}"
            for h in hits
        )

        user_message = f"""User query: {state["user_query"]}

Relevant document excerpts (from {state["file_name"]}, {source_hints}):
{context}"""

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
            max_tokens=1024,
            response_format={"type": "json_object"},
        )

        result = json.loads(response.choices[0].message.content)
        return {**state, "retrieval_result": result}
    except Exception as e:
        return {
            **state,
            "retrieval_result": {
                "answer": "An error occurred during retrieval.",
                "relevant_passages": [],
                "source_sections": [],
                "confidence": "low",
                "found_in_doc": False,
            },
            "error": str(e),
        }
