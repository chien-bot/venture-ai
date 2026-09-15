"""A constrained agent that drafts the next week's lifestyle plan."""

import json
import re
from typing import Any

from pydantic import BaseModel, Field, ValidationError

from app.schemas import TrendInsight, WeeklyReview
from app.services.health_report_agent import HealthReportAgentError, _FORBIDDEN_TERMS
from app.services.llm import LLMServiceError, chat


class _WeeklyPlanContent(BaseModel):
    summary: str = Field(min_length=1, max_length=300)
    adjustment_reason: str = Field(min_length=1, max_length=300)
    action_plan: list[str] = Field(min_length=7, max_length=7)


def _parse(content: str) -> _WeeklyPlanContent:
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", content.strip(), flags=re.IGNORECASE)
    try:
        draft = _WeeklyPlanContent.model_validate(json.loads(cleaned))
    except (json.JSONDecodeError, ValidationError) as exc:
        raise HealthReportAgentError("Weekly plan response was not valid JSON") from exc
    all_text = "\n".join([draft.summary, draft.adjustment_reason, *draft.action_plan])
    if any(term in all_text for term in _FORBIDDEN_TERMS):
        raise HealthReportAgentError("Weekly plan response violated CareAI's non-diagnostic boundary")
    return draft


async def generate_weekly_plan(goal: str, review: WeeklyReview, insights: list[TrendInsight]) -> _WeeklyPlanContent:
    """Draft seven lifestyle tasks only from saved, non-diagnostic inputs."""
    system = """你是 CareAI 的每周健康习惯计划写作助手，不是医生。
你只能依据输入的用户目标、行动完成率与已经给出的非诊断趋势提示，生成下一周的生活方式计划。
不要判断疾病、不要推荐药物、不要给剂量、不要添加未提供的症状或数据。
只返回 JSON，不要 Markdown：
{"summary":"","adjustment_reason":"","action_plan":["第1天：...","第2天：...","第3天：...","第4天：...","第5天：...","第6天：...","第7天：..."]}
计划必须具体、低门槛，并根据完成率调整难度；不得使用诊断、确诊、疾病、处方、药物剂量等词。"""
    user = json.dumps({
        "goal": goal,
        "weekly_review": review.model_dump(mode="json"),
        "trend_insights": [item.model_dump(mode="json") for item in insights],
    }, ensure_ascii=False)
    try:
        return _parse(await chat([{"role": "system", "content": system}, {"role": "user", "content": user}], temperature=0.2))
    except LLMServiceError as exc:
        raise HealthReportAgentError(str(exc)) from exc
