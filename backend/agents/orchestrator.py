import os
import json
from openai import OpenAI
from state import AgentState

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

SYSTEM_PROMPT = """You are a routing orchestrator for a document research assistant.
Given a user query and document context, decide which specialist agent should handle it.

Respond ONLY with valid JSON:
{
  "route": "retrieval" | "factcheck" | "analysis",
  "routing_reason": "one sentence explaining why"
}

Routing rules:
- retrieval: user wants to find/fetch/extract specific info from the document
- factcheck: user wants to verify a claim or check if something is true per the document
- analysis: user wants summary, key points, risks, highlights, or deep understanding

Be decisive. Pick exactly one route."""


def orchestrator_node(state: AgentState) -> AgentState:
    try:
        doc_preview = state["document_text"][:2000]
        user_message = f"""User query: {state["user_query"]}

Document context (first 2000 chars):
{doc_preview}"""

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
            max_tokens=256,
            response_format={"type": "json_object"},
        )

        data = json.loads(response.choices[0].message.content)
        route = data.get("route", "analysis")
        if route not in ("retrieval", "factcheck", "analysis"):
            route = "analysis"

        return {
            **state,
            "route": route,
            "routing_reason": data.get("routing_reason", ""),
        }
    except Exception as e:
        return {**state, "route": "analysis", "routing_reason": None, "error": str(e)}
