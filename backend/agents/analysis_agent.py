import os
import json
from openai import OpenAI
from state import AgentState

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

SYSTEM_PROMPT = """You are a senior research analyst and expert in document analysis.
You have been given a full document to analyze based on the user's request.

Your job is to produce a RICH, MULTI-DIMENSIONAL analysis that goes beyond a simple summary.

Based on the document type, include relevant sections:
- For MEDICAL papers: highlight efficacy data, side effects, patient populations, contraindications, statistical significance, and any safety risks
- For SCIENTIFIC/RESEARCH papers: highlight methodology, key findings, limitations, reproducibility concerns, and future research directions
- For EDUCATIONAL content: highlight core concepts, learning objectives, key definitions, common misconceptions addressed, and practical applications
- For LEGAL documents: highlight key obligations, rights, risk clauses, ambiguous language, and important deadlines
- For GENERAL documents: highlight main argument, evidence quality, conclusions, and open questions

ALWAYS include:
1. A concise summary (3-5 sentences)
2. Key highlights (5-7 bullet points of the most important content)
3. Risk/concern flags (anything that could be problematic, surprising, or needs attention)
4. What's NOT in the document but probably should be (gaps analysis)
5. One "big picture" insight that someone skimming would miss

Respond in JSON:
{
  "document_type": "detected type",
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


def analysis_node(state: AgentState) -> AgentState:
    try:
        doc_text = state["document_text"][:15000]

        user_message = f"""User request: {state["user_query"]}

Full document (may be truncated):
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
                "summary": "An error occurred during analysis.",
                "key_highlights": [],
                "risk_flags": [],
                "gaps": [],
                "big_picture_insight": "",
                "recommended_followup_questions": [],
            },
            "error": str(e),
        }
