"""Tutor node: explains entrepreneurship concepts."""

from agents.state import AgentState
from config import USE_MOCK_API
from services.claude_client import chat_completion
from prompts.tutor import TUTOR_SYSTEM_PROMPT
from mock.responses import MOCK_TUTOR_REPLIES


def _mock_tutor(concept: str | None, message: str) -> str:
    if concept:
        key = concept.upper()
        for k, v in MOCK_TUTOR_REPLIES.items():
            if k.upper() == key:
                return v
    # Fallback keyword matching
    if "获客" in message or "用户成本" in message:
        return MOCK_TUTOR_REPLIES["CAC"]
    if "终身价值" in message or "留存" in message:
        return MOCK_TUTOR_REPLIES["LTV"]
    if "市场规模" in message or "市场大小" in message:
        return MOCK_TUTOR_REPLIES["TAM"]
    if "精益" in message or "画布" in message:
        return MOCK_TUTOR_REPLIES["Lean Canvas"]
    if "任务" in message and "完成" in message:
        return MOCK_TUTOR_REPLIES["JTBD"]
    if "PMF" in message.upper() or "契合" in message:
        return MOCK_TUTOR_REPLIES["PMF"]
    if "CAC" in message.upper():
        return MOCK_TUTOR_REPLIES["CAC"]
    if "LTV" in message.upper():
        return MOCK_TUTOR_REPLIES["LTV"]
    return MOCK_TUTOR_REPLIES["default"]


def tutor_node(state: AgentState) -> AgentState:
    concept = state.get("tutor_concept")
    message = state["current_message"]

    if USE_MOCK_API:
        reply = _mock_tutor(concept, message)
    else:
        # Build system prompt with hypergraph context
        system = TUTOR_SYSTEM_PROMPT

        # ★ Inject hypergraph context for concept-related case examples
        hypergraph_ctx = state.get("hypergraph_context", "")
        if hypergraph_ctx:
            system += (
                "\n\n[超图案例库参考]\n"
                "请结合以下真实竞赛案例来举例说明概念：\n\n"
                f"{hypergraph_ctx}"
            )

        # ★ 知识卡片注入：查找概念相关卡片，提供结构化知识
        try:
            from services.knowledge_cards import search_cards, format_cards_for_prompt
            query = concept if concept else message[:50]
            related_cards = search_cards(query=query, card_type="concept", max_results=2)
            # 也搜索 mistake 和 template 卡片
            related_cards += search_cards(query=query, card_type="mistake", max_results=1)
            related_cards += search_cards(query=query, card_type="template", max_results=1)
            card_prompt = format_cards_for_prompt(related_cards, max_cards=3)
            if card_prompt:
                system += f"\n\n{card_prompt}"
        except Exception:
            pass

        context = f"学生想了解的概念：{concept}\n学生原话：{message}" if concept else message
        tutor_messages = [{"role": "user", "content": context}]
        reply = chat_completion(system, tutor_messages)

    return {
        **state,
        "tutor_output": reply,
    }
