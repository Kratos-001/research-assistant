from typing import TypedDict, Optional, Literal


class AgentState(TypedDict):
    # Inputs
    user_query: str
    document_text: str
    file_name: str

    # Set by document_agent (Agent 1) — ChromaDB collection for this upload
    collection_name: Optional[str]

    # Routing
    route: Optional[Literal["retrieval", "factcheck", "analysis"]]
    routing_reason: Optional[str]

    # Agent outputs
    retrieval_result: Optional[dict]
    factcheck_result: Optional[dict]
    analysis_result: Optional[dict]

    # Guardrail
    guardrail_blocked: Optional[bool]

    # Final
    final_response: Optional[dict]
    error: Optional[str]
