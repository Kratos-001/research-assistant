import os
import json
from openai import OpenAI
from state import AgentState
from tools.document_tools import reconstruct_text

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

SYSTEM_PROMPT = """You are a senior research analyst and expert in document analysis.
You have been given one or more research papers to analyze based on the user's request.

Your job is to produce a RICH, MULTI-DIMENSIONAL analysis that goes beyond a simple summary.

Based on the document type, include relevant sections:
- For MEDICAL papers: highlight efficacy data, side effects, patient populations, contraindications, statistical significance, and any safety risks
- For SCIENTIFIC/RESEARCH papers: highlight methodology, key findings, limitations, reproducibility concerns, and future research directions
- For EDUCATIONAL content: highlight core concepts, learning objectives, key definitions, common misconceptions addressed, and practical applications
- For LEGAL documents: highlight key obligations, rights, risk clauses, ambiguous language, and important deadlines
- For GENERAL documents: highlight main argument, evidence quality, conclusions, and open questions

When MULTIPLE papers are provided:
- Compare and contrast key findings across papers where relevant
- Note agreements, contradictions, or complementary insights between papers
- Attribute each key point to its specific paper

ALWAYS include:
1. A concise summary (3-5 sentences)
2. Key highlights (5-7 bullet points of the most important content)
3. Risk/concern flags (anything that could be problematic, surprising, or needs attention)
4. What's NOT in the document but probably should be (gaps analysis)
5. One "big picture" insight that someone skimming would miss

Respond in JSON:
{
  "document_type": "detected type",
  "papers_analyzed": ["paper name 1", "paper name 2"],
  "summary": "3-5 sentence summary",
  "key_highlights": [
    {"point": "highlight text", "importance": "why this matters"}
  ],
  "risk_flags": [
    {"flag": "description", "severity": "high | medium | low", "detail": "explanation"}
  ],
  "gaps": ["what is missing or not addressed"],
  "big_picture_insight": "the one insight a skimmer would miss",
  "recommended_followup_questions": ["question 1", "question 2", "question 3"]
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


def analysis_node(state: AgentState) -> AgentState:
    try:
        collection_names, file_names = _resolve_collections(state)

        # Budget 15000 chars split across all papers
        per_paper_limit = max(3000, 15000 // len(collection_names))

        doc_parts = []
        for col_name, fname in zip(collection_names, file_names):
            text = reconstruct_text(col_name, max_chars=per_paper_limit)
            if text:
                doc_parts.append(f"=== Paper: {fname} ===\n{text}")

        if not doc_parts:
            doc_text = "No document text could be retrieved."
        else:
            doc_text = "\n\n".join(doc_parts)

        paper_label = (
            "Full document" if len(collection_names) == 1
            else f"{len(collection_names)} papers"
        )

        user_message = f"""User request: {state["user_query"]}

{paper_label} (may be truncated):
{doc_text}"""

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
            max_tokens=2048,
            response_format={"type": "json_object"},
        )

        result = json.loads(response.choices[0].message.content)
        return {**state, "analysis_result": result}

    except Exception as e:
        return {
            **state,
            "analysis_result": {
                "document_type": "Unknown",
                "papers_analyzed": file_names,
                "summary": "An error occurred during analysis.",
                "key_highlights": [],
                "risk_flags": [],
                "gaps": [],
                "big_picture_insight": "",
                "recommended_followup_questions": [],
            },
            "error": str(e),
        }
