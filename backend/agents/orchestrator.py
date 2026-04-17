import os
import json
from openai import OpenAI
from state import AgentState
from tools.metadata_store import get_paper_metadata_batch

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

# ── Single-paper routing (or user confirmed "both/all") ──────────────────────
SYSTEM_PROMPT_SINGLE = """You are a routing orchestrator for a document research assistant.
Given a user query and document context, decide which specialist agent should handle it.

Respond ONLY with valid JSON:
{
  "route": "retrieval" | "factcheck" | "analysis",
  "routing_reason": "one sentence explaining why",
  "retrieval_type": "metadata" | "content" | null
}
retrieval_type is REQUIRED when route is "retrieval", otherwise set it to null.

ROUTING RULES — Follow this strict decision tree:

1. IS IT A TESTABLE CLAIM OR EXISTENCE CHECK? -> route to "factcheck"
   - Checking if something exists or is mentioned in the paper ("does this paper tell about X?", "is Y mentioned?")
   - Asks if something is TRUE / FALSE / yes / no
   - Evaluates a hypothesis ("does X cause Y", "did they find Z", "is X effective")
   
2. DOES IT ASK FOR GENERAL INFO, DETAILS, OR EXTRACTED LISTS? -> route to "analysis"
   - The user uses words like "analysis", "details", "info", "achievements", "results", "findings", "overview"
   - Asks for a general summary, implications, gaps, or a comprehensive breakdown extracted from the text.
   - Examples: "what are achievements from the paper?", "give me the info", "summarize the paper", "analyze the methodology"

3. IS IT A LOOKUP OF PAPER IDENTITY/TOPIC FROM METADATA? -> route to "retrieval" with retrieval_type="metadata"
   - Asks about what the paper IS: title, authors, year, journal, publisher, abstract, or its general topic.
   - Examples: "who wrote this", "when was it published", "what's the title", "what is this paper about?"

4. IS IT A SPECIFIC COMMAND TO FIND RAW TEXT EXCERPTS? -> route to "retrieval" with retrieval_type="content"
   - Exclusively for when the user literally asks to fetch exact passages, quotes, or raw text excerpts.
   - Examples: "find passages about BMI", "show me the exact sentences mentioning weight loss"

When in doubt, default to "analysis" for open-ended questions like "achievements" or "details".
"""

# ── Multi-paper routing — may ask for clarification ───────────────────────────
SYSTEM_PROMPT_MULTI = """You are a routing orchestrator for a document research assistant.
The user has {n} papers selected. Your job is to FIRST decide whether to ask the user which paper they mean, THEN route to the right agent.

Papers available:
{paper_list}

STEP 1 — Should you ask for clarification?
Ask for clarification ("clarification" route) ONLY when:
  The query is a SPECIFIC targeted text lookup or a factual claim that MUST be answered by ONE specific document, BUT the user did not specify which one, AND did not use words like "both", "all", "compare", or "summarize".
  (Note: Our system auto-intercepts the phrase "the paper", so you do not need to worry about that. Only ask for clarification if a search query is hopelessly ambiguous across multiple distinct documents).
  Do NOT ask for clarification if the query is a broad analysis or comparison that naturally spans documents.

STEP 2 — If NOT clarifying, route using this strict decision tree:

1. IS IT A TESTABLE CLAIM OR EXISTENCE CHECK? -> route to "factcheck" ("does X cause Y?", "does this mention Z?")
2. DOES IT ASK FOR GENERAL INFO, DETAILS, OR EXTRACTED LISTS? -> route to "analysis" ("give me details", "what are achievements?", "summarize both", "compare the methods")
3. IS IT A LOOKUP OF PAPER IDENTITY FROM METADATA? -> route to "retrieval" with retrieval_type="metadata" ("who are the authors of these papers?", "what are these papers about?")
4. IS IT A SPECIFIC COMMAND TO FIND RAW TEXT EXCERPTS? -> route to "retrieval" with retrieval_type="content" ("find mentions of weight loss in all papers", "show exact quotes")

Respond ONLY with valid JSON:
{{
  "route": "retrieval" | "factcheck" | "analysis" | "clarification",
  "routing_reason": "one sentence explaining why",
  "retrieval_type": "metadata" | "content" | null,
  "clarification_question": "only when route is clarification — a concise, friendly question naming each paper by its short title"
}}
"""


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


def orchestrator_node(state: AgentState) -> AgentState:
    try:
        collection_names, file_names = _resolve_collections(state)
        n_papers = len(collection_names)
        skip_clarification = state.get("skip_clarification", False)

        # Build context from SQLite metadata (titles + abstract excerpts)
        records = get_paper_metadata_batch(collection_names)
        context_parts = []
        paper_titles = []
        for rec in records:
            pm = rec.get("paper_metadata", {})
            title = pm.get("title") or rec.get("file_name", "Unknown paper")
            paper_titles.append(title)
            abstract = (pm.get("abstract") or "")[:400]
            context_parts.append(f"Paper: {title}\nAbstract: {abstract}")

        doc_context = "\n\n".join(context_parts) or "Research paper(s) — no preview available."

        # Choose system prompt based on number of papers and skip flag
        if n_papers > 1 and not skip_clarification:
            paper_list = "\n".join(
                f"  {i+1}. {title}" for i, title in enumerate(paper_titles)
            )
            system_prompt = SYSTEM_PROMPT_MULTI.format(
                n=n_papers,
                paper_list=paper_list,
            )
        else:
            system_prompt = SYSTEM_PROMPT_SINGLE

        user_message = f"""User query: {state["user_query"]}

Analyzing {n_papers} paper(s):
{doc_context}"""

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            max_tokens=256,
            response_format={"type": "json_object"},
        )

        data = json.loads(response.choices[0].message.content)
        route = data.get("route", "analysis")
        if route not in ("retrieval", "factcheck", "analysis", "clarification"):
            route = "analysis"

        # If route is clarification but we only have 1 paper — re-ask with single prompt
        if route == "clarification" and n_papers <= 1:
            fallback = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT_SINGLE},
                    {"role": "user", "content": user_message},
                ],
                max_tokens=200,
                response_format={"type": "json_object"},
            )
            fb_data = json.loads(fallback.choices[0].message.content)
            route = fb_data.get("route", "analysis")
            if route not in ("retrieval", "factcheck", "analysis"):
                route = "analysis"
            data["routing_reason"] = fb_data.get("routing_reason", data.get("routing_reason", ""))
            data["retrieval_type"] = fb_data.get("retrieval_type")

        # Programmatic heuristic: force clarification if the user asks for a singular paper
        # but multiple are selected, as LLMs frequently fail at this logic puzzle.
        lower_q = state["user_query"].lower()
        has_singular = "the paper" in lower_q or "this paper" in lower_q or "the document" in lower_q
        has_plural = "papers" in lower_q or "documents" in lower_q or "both" in lower_q or "all" in lower_q
        
        if n_papers > 1 and not skip_clarification and has_singular and not has_plural:
            route = "clarification"
            data["routing_reason"] = "The query uses singular terms ('the paper') but multiple papers are selected."
            data["clarification_question"] = "Which paper are you asking about? " + " or ".join([f"'{t}'" for t in paper_titles])
            data["retrieval_type"] = None

        retrieval_type = data.get("retrieval_type") if route == "retrieval" else None

        return {
            **state,
            "route": route,
            "routing_reason": data.get("routing_reason", ""),
            "clarification_question": data.get("clarification_question") if route == "clarification" else None,
            "retrieval_type": retrieval_type,
        }
    except Exception as e:
        return {**state, "route": "analysis", "routing_reason": None, "clarification_question": None, "error": str(e)}
