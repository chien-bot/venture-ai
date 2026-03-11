"""Competition node: Rubric R1-R9 scoring."""

import re
import json
from agents.state import AgentState
from config import USE_MOCK_API
from services.claude_client import chat_completion
from prompts.competition import COMPETITION_SYSTEM_PROMPT
from mock.responses import MOCK_COMPETITION_REPLY


def _parse_rubric(text: str) -> dict | None:
    match = re.search(r"<!--RUBRIC:(.*?)-->", text)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            return None
    return None


def _clean(text: str) -> str:
    return re.sub(r"<!--RUBRIC:.*?-->", "", text).strip()


def competition_node(state: AgentState) -> AgentState:
    if USE_MOCK_API:
        raw = MOCK_COMPETITION_REPLY
    else:
        system = COMPETITION_SYSTEM_PROMPT

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

    return {
        **state,
        "competition_output": clean,
        "rubric_scores": rubric,
    }
