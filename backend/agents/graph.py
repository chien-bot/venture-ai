"""
LangGraph multi-agent graph definition.

Pipeline:
  router → retriever → (coach | tutor | competition) → synthesizer → critic → END

retriever 节点在 router 之后运行，查询超图获取相关案例和风险模式，
将检索结果注入 state，供后续 coach/tutor/competition 节点作为 RAG 上下文使用。
"""

from langgraph.graph import StateGraph, END
from agents.state import AgentState
from agents.nodes.router import router_node
from agents.nodes.retriever import retriever_node
from agents.nodes.coach import coach_node
from agents.nodes.tutor import tutor_node
from agents.nodes.competition import competition_node
from agents.nodes.synthesizer import synthesizer_node
from agents.nodes.critic import critic_node


def _route_after_retriever(state: AgentState) -> str:
    intent = state.get("intent", "coach")
    if intent == "competition":
        return "competition"
    if intent in ("tutor", "hybrid"):
        return "tutor"
    return "coach"  # default: coach


def _route_after_tutor(state: AgentState) -> str:
    # hybrid: tutor → coach → synthesizer
    # tutor-only: tutor → synthesizer
    if state.get("intent") == "hybrid":
        return "coach"
    return "synthesizer"


def build_graph() -> StateGraph:
    graph = StateGraph(AgentState)

    # Add nodes
    graph.add_node("router", router_node)
    graph.add_node("retriever", retriever_node)
    graph.add_node("coach", coach_node)
    graph.add_node("tutor", tutor_node)
    graph.add_node("competition", competition_node)
    graph.add_node("synthesizer", synthesizer_node)
    graph.add_node("critic", critic_node)

    # Entry point
    graph.set_entry_point("router")

    # router → retriever (always)
    graph.add_edge("router", "retriever")

    # Conditional routing after retriever (was after router)
    graph.add_conditional_edges(
        "retriever",
        _route_after_retriever,
        {
            "coach": "coach",
            "tutor": "tutor",
            "competition": "competition",
        },
    )

    # After tutor: either go to coach (hybrid) or synthesizer
    graph.add_conditional_edges(
        "tutor",
        _route_after_tutor,
        {
            "coach": "coach",
            "synthesizer": "synthesizer",
        },
    )

    # All terminal agents go to synthesizer, then critic, then END
    graph.add_edge("coach", "synthesizer")
    graph.add_edge("competition", "synthesizer")
    graph.add_edge("synthesizer", "critic")
    graph.add_edge("critic", END)

    return graph.compile()


# Singleton compiled graph
_compiled_graph = None


def get_graph():
    global _compiled_graph
    if _compiled_graph is None:
        _compiled_graph = build_graph()
    return _compiled_graph
