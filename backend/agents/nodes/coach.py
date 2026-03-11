"""Coach node: Socratic entrepreneurship coaching."""

import re
import json
from agents.state import AgentState
from config import USE_MOCK_API
from services.claude_client import chat_completion
from prompts.coach import COACH_SYSTEM_PROMPT
from mock.responses import MOCK_COACH_REPLIES
from services.evidence_tracer import refresh_tracer
from agents.adaptive_questioning import (
    build_questioning_context,
    get_weak_dims,
    detect_evasion,
    DIM_LABELS,
)
from services.competition_mode import get_countdown_context
from services.database import get_competition_date, get_latest_annotations_for_coach


def _parse_scores(text: str) -> dict | None:
    match = re.search(r"<!--SCORES:(.*?)-->", text)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            return None
    return None


def _clean(text: str) -> str:
    return re.sub(r"<!--SCORES:.*?-->", "", text).strip()


def _mock_coach(state: AgentState) -> str:
    message = state["current_message"]
    history_len = len(state["messages"])
    scores = state.get("scores") or {}

    # Adaptive: 薄弱维度优先触发对应 mock 回复
    weak_dims = get_weak_dims(scores)

    if "没有对手" in message or "没有竞争" in message or "唯一" in message:
        return MOCK_COACH_REPLIES[2]["reply"]

    # 如果检测到 business 薄弱且学生在回避
    if "business" in weak_dims and detect_evasion(state["messages"], "business"):
        return MOCK_COACH_REPLIES[3]["reply"]

    if "商业模式" in message or "盈利" in message or "收费" in message:
        return MOCK_COACH_REPLIES[3]["reply"]
    if "执行" in message or "团队" in message or "MVP" in message:
        return MOCK_COACH_REPLIES[4]["reply"]
    if "路演" in message or "pitch" in message.lower() or "投资人" in message:
        return MOCK_COACH_REPLIES[5]["reply"]
    if history_len > 6:
        return MOCK_COACH_REPLIES[6]["reply"]
    return MOCK_COACH_REPLIES[1]["reply"]


def coach_node(state: AgentState) -> AgentState:
    session_id = state.get("session_id", "")
    messages = state.get("messages", [])
    scores = state.get("scores")
    current_message = state.get("current_message", "")

    # Refresh evidence tracer
    tracer = refresh_tracer(session_id, messages)

    if USE_MOCK_API:
        raw = _mock_coach(state)
    else:
        system = COACH_SYSTEM_PROMPT

        # ★ Inject hypergraph retrieval context (RAG)
        hypergraph_ctx = state.get("hypergraph_context", "")
        if hypergraph_ctx:
            system += (
                "\n\n[超图知识库检索结果 — 基于82个真实竞赛案例]\n"
                "以下是从超图案例库中检索到的与学生项目相关的信息。"
                "请在回答中引用这些案例和风险模式来增强你的指导：\n\n"
                f"{hypergraph_ctx}"
            )

        # Inject evidence tracer context
        evidence_context = tracer.format_missing_evidence()
        if evidence_context:
            system += f"\n\n[证据追踪摘要]\n{evidence_context}"

        # Inject adaptive questioning context
        questioning_context = build_questioning_context(scores, messages, current_message)
        if questioning_context:
            system += f"\n\n{questioning_context}"

        # Inject competition countdown mode
        if project_id := state.get("project_id"):
            comp_date = get_competition_date(project_id)
            countdown_ctx = get_countdown_context(comp_date)
            if countdown_ctx:
                system += f"\n\n{countdown_ctx}"

            # Inject teacher annotations
            try:
                notes = get_latest_annotations_for_coach(project_id)
                if notes:
                    system += "\n\n[教师批注 - 请在本轮对话中体现以下教师指导意见]\n"
                    for a in notes[:3]:
                        system += f"  • {a['note_text']}\n"
            except Exception:
                pass

        raw = chat_completion(system, messages)

    scores_data = _parse_scores(raw)
    clean = _clean(raw)

    new_scores = None
    stage = state.get("stage")
    diagnosis = state.get("diagnosis", [])

    if scores_data:
        new_scores = {k: v for k, v in scores_data.items() if k not in ("stage", "diagnosis")}
        stage = scores_data.get("stage", stage)
        diagnosis = scores_data.get("diagnosis", diagnosis)

    return {
        **state,
        "coach_output": clean,
        "scores": new_scores,
        "stage": stage,
        "diagnosis": diagnosis,
    }
