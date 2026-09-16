"""A constrained agent that drafts the next week's lifestyle plan."""

import json
import re
from typing import Any

from pydantic import BaseModel, Field, ValidationError

from app.schemas import TrendInsight, WeeklyPlanDraft, WeeklyReview
from app.services.health_report_agent import HealthReportAgentError, _FORBIDDEN_TERMS
from app.services.llm import LLMServiceError, chat


class _WeeklyPlanContent(BaseModel):
    summary: str = Field(min_length=1, max_length=300)
    adjustment_reason: str = Field(min_length=1, max_length=300)
    action_plan: list[str] = Field(min_length=7, max_length=7)


class SingleVariableExperiment(_WeeklyPlanContent):
    snapshot: dict[str, str | int]
    difficulty: int = Field(ge=1, le=5)


_VARIABLE_KEYS = {
    "提醒时间": "reminder_time",
    "行动时长": "duration_minutes",
    "行动频率": "active_days",
    "任务难度": "difficulty",
}


def _goal_action(goal: str) -> str:
    if "睡眠" in goal:
        return "进行放松准备并记录入睡时间"
    if "运动" in goal:
        return "完成轻度活动并记录感受"
    if "体重" in goal:
        return "完成一项规律饮食或活动行动并记录"
    if "血压" in goal:
        return "在相近条件下记录一次血压并备注状态"
    return "完成一项低负担健康行动并记录感受"


def build_single_variable_experiment(
    goal: str,
    review: WeeklyReview,
    experiment_variable: str,
    requested_difficulty: int,
    previous: WeeklyPlanDraft | None,
) -> SingleVariableExperiment:
    """Create a canonical plan where exactly one experiment setting changes."""
    if experiment_variable not in _VARIABLE_KEYS:
        raise ValueError("Unsupported experiment variable")
    baseline: dict[str, str | int] = {
        "reminder_time": "21:30",
        "duration_minutes": 10,
        "active_days": 4,
        "difficulty": 1,
        "action": _goal_action(goal),
    }
    if previous and previous.experiment_snapshot:
        baseline.update(previous.experiment_snapshot)
    snapshot = baseline.copy()
    key = _VARIABLE_KEYS[experiment_variable]
    if key == "reminder_time":
        snapshot[key] = "20:30" if baseline[key] != "20:30" else "21:30"
    elif key == "duration_minutes":
        current = int(baseline[key])
        snapshot[key] = max(5, current - 5) if current >= 20 else current + 5
    elif key == "active_days":
        current = int(baseline[key])
        snapshot[key] = 3 if current >= 6 else current + 1
    else:
        next_difficulty = requested_difficulty
        if next_difficulty == int(baseline[key]):
            next_difficulty = 1 if next_difficulty == 5 else next_difficulty + 1
        snapshot[key] = next_difficulty

    changed = {name for name in baseline if snapshot[name] != baseline[name]}
    if changed != {key}:
        raise ValueError(f"Experiment must change exactly {key}; changed={sorted(changed)}")

    active_days = int(snapshot["active_days"])
    tasks = []
    for day in range(1, 8):
        if day <= active_days:
            task = (
                f"第{day}天：{snapshot['reminder_time']}提醒；用{snapshot['duration_minutes']}分钟"
                f"{snapshot['action']}（难度{snapshot['difficulty']}/5）。"
            )
        else:
            task = f"第{day}天：休息并用1分钟复盘本周行动，不增加新的行动任务。"
        tasks.append(task)
    completion_note = "尚无完成率" if review.completion_rate is None else f"上轮完成率{review.completion_rate}%"
    return SingleVariableExperiment(
        summary=f"本轮以{goal}为目标，只测试“{experiment_variable}”这一项变化。",
        adjustment_reason=f"{completion_note}；其余提醒、时长、频率、难度和核心行动保持上一版设置。",
        action_plan=tasks,
        snapshot=snapshot,
        difficulty=int(snapshot["difficulty"]),
    )


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


async def generate_weekly_plan(
    goal: str,
    review: WeeklyReview,
    insights: list[TrendInsight],
    experiment_variable: str = "任务难度",
    difficulty: int = 2,
) -> _WeeklyPlanContent:
    """Draft seven lifestyle tasks only from saved, non-diagnostic inputs."""
    system = """你是 CareAI 的每周健康习惯计划写作助手，不是医生。
你只能依据输入的用户目标、行动完成率与已经给出的非诊断趋势提示，生成下一周的生活方式计划。
不要判断疾病、不要推荐药物、不要给剂量、不要添加未提供的症状或数据。
只返回 JSON，不要 Markdown：
{"summary":"","adjustment_reason":"","action_plan":["第1天：...","第2天：...","第3天：...","第4天：...","第5天：...","第6天：...","第7天：..."]}
计划必须具体、低门槛，并根据完成率调整难度；本轮只允许围绕指定的一个实验变量调整，
其余计划条件尽量保持稳定，方便用户判断什么改变真正有帮助。
不得使用诊断、确诊、疾病、处方、药物剂量等词。"""
    user = json.dumps({
        "goal": goal,
        "weekly_review": review.model_dump(mode="json"),
        "trend_insights": [item.model_dump(mode="json") for item in insights],
        "experiment": {
            "variable": experiment_variable,
            "difficulty": difficulty,
            "instruction": "只改变这个变量，并在 adjustment_reason 中说明与上一周相比改变了什么。",
        },
    }, ensure_ascii=False)
    try:
        return _parse(await chat([{"role": "system", "content": system}, {"role": "user", "content": user}], temperature=0.2))
    except LLMServiceError as exc:
        raise HealthReportAgentError(str(exc)) from exc
