"""
LangGraph multi-agent graph definition V2.

Pipeline:
  router → retriever → (coach | tutor | competition | grader) → synthesizer → critic
                                                                                 ↓
                                                                          [redirect?]
                                                                           ↓        ↓
                                                                      tutor_redir → synthesizer_redir → END
                                                                           (no)
                                                                            ↓
                                                                           END

V2 改进:
- critic 检测到高风险规则时，可选择跳转到 tutor 解释相关概念（critic_redirect）
- 支持 hybrid 路由：tutor → coach → synthesizer
- loop_count 防止无限循环（最多 1 次重定向）
"""

from langgraph.graph import StateGraph, END
from agents.state import AgentState
from agents.nodes.router import router_node
from agents.nodes.retriever import retriever_node
from agents.nodes.coach import coach_node
from agents.nodes.tutor import tutor_node
from agents.nodes.competition import competition_node
from agents.nodes.grader import grader_node
from agents.nodes.synthesizer import synthesizer_node
from agents.nodes.critic import critic_node


def _route_after_retriever(state: AgentState) -> str:
    intent = state.get("intent", "coach")
    if intent == "competition":
        return "competition"
    if intent in ("tutor", "hybrid"):
        return "tutor"
    if intent == "grader":
        return "grader"
    return "coach"  # default: coach


def _route_after_tutor(state: AgentState) -> str:
    # hybrid: tutor → coach → synthesizer
    # tutor-only: tutor → synthesizer
    if state.get("intent") == "hybrid":
        return "coach"
    return "synthesizer"


def _route_after_critic(state: AgentState) -> str:
    """
    V2: critic 后的条件路由。
    - 有 critic_redirect 且 loop_count <= 1 → tutor_redirect（插入概念解释）
    - 否则 → END
    """
    redirect = state.get("critic_redirect")
    loop_count = state.get("loop_count", 0)

    if redirect and loop_count <= 1:
        return "tutor_redirect"
    return "end"


def _tutor_redirect_node(state: AgentState) -> AgentState:
    """
    由 critic 触发的 tutor 微型节点。
    只做一件事：用 critic_redirect 的概念调用 tutor，
    将结果追加到 final_reply 尾部。
    """
    concept = state.get("critic_redirect", "")
    if not concept:
        return state

    # 构造一个轻量 tutor 调用
    tutor_state = {
        **state,
        "tutor_concept": concept,
        "current_message": f"请帮我解释一下「{concept}」这个概念，以及它在创业项目中的具体应用。",
    }
    result = tutor_node(tutor_state)
    tutor_output = result.get("tutor_output", "")

    if tutor_output:
        final_reply = state.get("final_reply", "")
        final_reply += (
            f"\n\n---\n\n### 💡 知识补充：{concept}\n\n"
            f"{tutor_output}"
        )
        return {
            **state,
            "final_reply": final_reply,
            "tutor_output": tutor_output,
            "critic_redirect": None,  # 清除重定向信号
        }

    return {**state, "critic_redirect": None}


def build_graph() -> StateGraph:
    graph = StateGraph(AgentState)

    # Add nodes
    graph.add_node("router", router_node)
    graph.add_node("retriever", retriever_node)
    graph.add_node("coach", coach_node)
    graph.add_node("tutor", tutor_node)
    graph.add_node("competition", competition_node)
    graph.add_node("grader", grader_node)
    graph.add_node("synthesizer", synthesizer_node)
    graph.add_node("critic", critic_node)
    graph.add_node("tutor_redirect", _tutor_redirect_node)

    # Entry point
    graph.set_entry_point("router")

    # router → retriever (always)
    graph.add_edge("router", "retriever")

    # Conditional routing after retriever
    graph.add_conditional_edges(
        "retriever",
        _route_after_retriever,
        {
            "coach": "coach",
            "tutor": "tutor",
            "competition": "competition",
            "grader": "grader",
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

    # All terminal agents go to synthesizer, then critic
    graph.add_edge("coach", "synthesizer")
    graph.add_edge("competition", "synthesizer")
    graph.add_edge("grader", "synthesizer")
    graph.add_edge("synthesizer", "critic")

    # V2: critic → conditional redirect or END
    graph.add_conditional_edges(
        "critic",
        _route_after_critic,
        {
            "tutor_redirect": "tutor_redirect",
            "end": END,
        },
    )

    # tutor_redirect → END (no further loops)
    graph.add_edge("tutor_redirect", END)

    return graph.compile()


# Singleton compiled graph
_compiled_graph = None


def get_graph():
    global _compiled_graph
    if _compiled_graph is None:
        _compiled_graph = build_graph()
    return _compiled_graph
