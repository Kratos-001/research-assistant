import os
import json
from openai import OpenAI
from state import AgentState
from tools.document_tools import similarity_search

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

SYSTEM_PROMPT = """You are a rigorous fact-checking specialist working strictly from provided document excerpts.
Your job is to determine if the user's claim or question is TRUE, FALSE, PARTIALLY_TRUE, or NOT_MENTIONED based solely on the document content.

Rules:
- Never use external knowledge. Only use what is in the provided document excerpts.
- If the document doesn't address it, say NOT_MENTIONED — do not guess.
- Quote the exact passage that supports your verdict.
- If there is a contradiction in the document itself, flag it as CONFLICTED.
- When excerpts are from multiple papers, clearly note which paper supports or contradicts the claim.

Respond in JSON:
{
  "verdict": "TRUE | FALSE | PARTIALLY_TRUE | NOT_MENTIONED | CONFLICTED",
  "verdict_explanation": "clear explanation of the verdict",
  "supporting_quote": "exact quote from document that led to this verdict",
  "contradicting_quote": "quote if verdict is PARTIALLY_TRUE or CONFLICTED, else null",
  "confidence": "high | medium | low",
  "warning": "any important caveat, or null"
}"""


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


def factcheck_node(state: AgentState) -> AgentState:
    try:
        collection_names, file_names = _resolve_collections(state)

        # Per-paper chunk budget so total context stays manageable
        per_paper_top_k = max(3, 8 // len(collection_names)) if len(collection_names) > 1 else 8

        context_parts = []
        for col_name, fname in zip(collection_names, file_names):
            try:
                hits = similarity_search(col_name, state["user_query"], top_k=per_paper_top_k)
                if hits:
                    chunks = "\n\n---\n\n".join(h["text"] for h in hits)
                    context_parts.append(f"[From: {fname}]\n{chunks}")
            except Exception:
                pass

        if not context_parts:
            return {
                **state,
                "factcheck_result": {
                    "verdict": "NOT_MENTIONED",
                    "verdict_explanation": "No relevant content found in the selected paper(s).",
                    "supporting_quote": "",
                    "contradicting_quote": None,
                    "confidence": "low",
                    "warning": "Could not retrieve chunks from the document(s).",
                },
            }

        context = "\n\n===\n\n".join(context_parts)
        # Cap total context to avoid token overflow
        context = context[:12000]

        paper_label = (
            file_names[0] if len(file_names) == 1
            else f"{len(file_names)} selected papers"
        )

        user_message = f"""User query/claim to verify: {state["user_query"]}

Relevant document excerpts (from {paper_label}):
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
        return {**state, "factcheck_result": result}

    except Exception as e:
        return {
            **state,
            "factcheck_result": {
                "verdict": "NOT_MENTIONED",
                "verdict_explanation": "An error occurred during fact-checking.",
                "supporting_quote": "",
                "contradicting_quote": None,
                "confidence": "low",
                "warning": str(e),
            },
            "error": str(e),
        }
