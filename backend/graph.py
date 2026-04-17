from langgraph.graph import StateGraph, END
from state import AgentState
from agents.guardrail_agent import guardrail_node
from agents.orchestrator import orchestrator_node
from agents.retrieval_agent import retrieval_node
from agents.factcheck_agent import factcheck_node
from agents.analysis_agent import analysis_node


def build_graph():
    graph = StateGraph(AgentState)

    graph.add_node("guardrail", guardrail_node)
    graph.add_node("orchestrator", orchestrator_node)
    graph.add_node("retrieval", retrieval_node)
    graph.add_node("factcheck", factcheck_node)
    graph.add_node("analysis", analysis_node)

    # Entry point is now guardrail — document processing happens at /upload
    graph.set_entry_point("guardrail")

    # guardrail → orchestrator OR short-circuit to END if blocked
    def guardrail_decision(state: AgentState) -> str:
        return "blocked" if state.get("guardrail_blocked") else "pass"

    graph.add_conditional_edges(
        "guardrail",
        guardrail_decision,
        {
            "blocked": END,
            "pass": "orchestrator",
        },
    )

    # orchestrator → specialist agents
    def route_decision(state: AgentState) -> str:
        return state["route"]

    graph.add_conditional_edges(
        "orchestrator",
        route_decision,
        {
            "retrieval": "retrieval",
            "factcheck": "factcheck",
            "analysis": "analysis",
        },
    )

    graph.add_edge("retrieval", END)
    graph.add_edge("factcheck", END)
    graph.add_edge("analysis", END)

    return graph.compile()
