import os
import json
from openai import OpenAI
from state import AgentState
from tools.document_tools import similarity_search

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

SYSTEM_PROMPT = """You are a rigorous fact-checking specialist working strictly from a provided document.
Your job is to determine if the user's claim or question is TRUE, FALSE, PARTIALLY TRUE, or NOT MENTIONED based solely on the document content.

Rules:
- Never use external knowledge. Only use what is in the provided document excerpts.
- If the document doesn't address it, say NOT_MENTIONED — do not guess.
- Quote the exact passage that supports your verdict.
- If there is a contradiction in the document itself, flag it as CONFLICTED.

Respond in JSON:
{
  "verdict": "TRUE | FALSE | PARTIALLY_TRUE | NOT_MENTIONED | CONFLICTED",
  "verdict_explanation": "clear explanation of the verdict",
  "supporting_quote": "exact quote from document that led to this verdict",
  "contradicting_quote": "quote if verdict is PARTIALLY_TRUE or CONFLICTED, else null",
  "confidence": "high | medium | low",
  "warning": "any important caveat, or null"
}"""


def factcheck_node(state: AgentState) -> AgentState:
    try:
        hits = similarity_search(state["collection_name"], state["user_query"], top_k=8)

        context = "\n\n---\n\n".join(h["text"] for h in hits)

        user_message = f"""User query/claim to verify: {state["user_query"]}

Relevant document excerpts (from {state["file_name"]}):
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
