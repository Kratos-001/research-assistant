from typing import TypedDict, Optional, Literal


class AgentState(TypedDict):
    # Inputs
    user_query: str
    document_text: str       # always "" in new flow — kept for guardrail compat
    file_name: str           # first/primary file name (legacy compat)

    # Single-paper (legacy, always set to first element of collection_names)
    collection_name: Optional[str]

    # Multi-paper support
    collection_names: Optional[list]   # list of collection name strings
    file_names: Optional[list]         # parallel list of file name strings

    # Routing
    route: Optional[Literal["retrieval", "factcheck", "analysis", "clarification"]]
    routing_reason: Optional[str]
    clarification_question: Optional[str]   # set when route == "clarification"
    skip_clarification: Optional[bool]      # frontend sets True when user picks "both"
    retrieval_type: Optional[Literal["metadata", "content"]]  # set by orchestrator when route == "retrieval"

    # Agent outputs
    retrieval_result: Optional[dict]
    factcheck_result: Optional[dict]
    analysis_result: Optional[dict]

    # Guardrail
    guardrail_blocked: Optional[bool]

    # Final
    final_response: Optional[dict]
    error: Optional[str]
