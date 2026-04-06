"""Competition node: Rubric R1-R11 scoring with dynamic competition template switching."""

import re
import json
from agents.state import AgentState
from config import USE_MOCK_API
from services.claude_client import chat_completion
from prompts.competition import COMPETITION_SYSTEM_PROMPT
from mock.responses import MOCK_COMPETITION_REPLY
from services.competition_templates import match_template, format_template_for_prompt
from services.debug_logger import DebugLogger

_dbg = DebugLogger("competition_node")


def _parse_rubric(text: str) -> dict | None:
    from services.marker_parser import parse_rubric
    return parse_rubric(text)


def _clean(text: str) -> str:
    from services.marker_parser import clean_reply
    return clean_reply(text)


def _detect_competition_from_messages(messages: list[dict]) -> str:
    """从对话历史中提取赛事关键词。"""
    full_text = " ".join(
        m.get("content", "") for m in messages if isinstance(m.get("content"), str)
    )
    return full_text


def competition_node(state: AgentState) -> AgentState:
    session_id = state.get("session_id", "")
    _dbg.agent_start(session_id=session_id, intent="competition", message_preview=state.get("current_message", ""))

    if USE_MOCK_API:
        raw = MOCK_COMPETITION_REPLY
    else:
        system = COMPETITION_SYSTEM_PROMPT

        # ★ Dynamic competition template switching (A5-2)
        full_text = _detect_competition_from_messages(state.get("messages", []))
        matched_template = match_template(full_text)
        if matched_template:
            template_prompt = format_template_for_prompt(matched_template)
            system += f"\n\n{template_prompt}"
            _dbg.competition_template(
                template_name=matched_template["name"],
                rubric_weights=matched_template["rubric_weights"],
            )

        # ★ Inject hypergraph context for benchmark comparison
        hypergraph_ctx = state.get("hypergraph_context", "")
        if hypergraph_ctx:
            system += (
                "\n\n[超图案例库 — 同类竞赛项目参考]\n"
                "以下是超图中检索到的同类竞赛项目，请在评分时参考这些案例的水平：\n\n"
                f"{hypergraph_ctx}"
            )

        raw = chat_completion(system, state["messages"])

    rubric = _parse_rubric(raw)
    clean = _clean(raw)

    if rubric:
        _dbg.info(f"rubric_scores: {json.dumps(rubric)}")
        for rule_id, score in rubric.items():
            severity = "high" if score <= 1 else ("medium" if score <= 2 else "low")
            _dbg.rule_triggered(
                rule_id=rule_id,
                rule_type=f"competition_score={score}/5",
                severity=severity,
                confidence=round(score / 5, 3),
            )

    _dbg.agent_done(scores=rubric, stage="competition")

    return {
        **state,
        "competition_output": clean,
        "rubric_scores": rubric,
    }
