"""Constrained Health Report Agent built on top of deterministic risk rules."""

import json
import re
from typing import Any

from pydantic import BaseModel, Field, ValidationError

from app.schemas import HealthReport, RiskItem, RiskLevel, RuleAssessment
from app.services.llm import LLMServiceError, chat
from app.services.risk_rules import SAFETY_NOTICE


class HealthReportAgentError(RuntimeError):
    """Raised when the model response does not meet the agent's safety contract."""


class _ReportDraft(BaseModel):
    """The limited content the LLM is allowed to generate."""

    summary: str = Field(min_length=1, max_length=500)
    risk_explanations: dict[str, str]
    recommendations: list[str] = Field(min_length=1, max_length=5)
    action_plan: list[str] = Field(min_length=7, max_length=7)


_FORBIDDEN_TERMS = (
    "诊断",
    "确诊",
    "患有",
    "疾病",
    "处方",
    "药物剂量",
    "diagnos",
    "disease",
    "prescription",
    "dosage",
    "medication",
)


def _parse_json_object(content: str) -> dict[str, Any]:
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", content.strip(), flags=re.IGNORECASE)
    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise HealthReportAgentError("Model response was not valid JSON") from exc
    if not isinstance(parsed, dict):
        raise HealthReportAgentError("Model response JSON must be an object")
    return parsed


def _ensure_non_diagnostic(draft: _ReportDraft, expected_categories: set[str]) -> None:
    if set(draft.risk_explanations) != expected_categories:
        raise HealthReportAgentError("Model response must explain exactly the rule-provided risk categories")
    text = "\n".join(
        [draft.summary, *draft.risk_explanations.values(), *draft.recommendations, *draft.action_plan]
    )
    if any(term in text for term in _FORBIDDEN_TERMS):
        raise HealthReportAgentError("Model response violated CareAI's non-diagnostic boundary")


def _items_requiring_attention(assessment: RuleAssessment) -> list[RiskItem]:
    return [item for item in assessment.risks if item.level != RiskLevel.NORMAL]


async def generate_health_report(assessment: RuleAssessment) -> HealthReport:
    """Generate explanations and a 7-day plan without delegating risk decisions to the LLM."""
    attention_items = _items_requiring_attention(assessment)
    model_input = [
        {
            "category": item.category,
            "title": item.title,
            "level": item.level.value,
            "reason": item.reason,
            "source": item.source,
        }
        for item in attention_items
    ]
    system_prompt = """你是 CareAI 的健康报告写作助手，不是医生。你不能判断、调整或新增健康风险，
更不能诊断疾病。你只能解释下方规则引擎已经给出的风险项，并生成生活方式建议和7天行动计划。
不得使用“诊断、确诊、患有、疾病、处方、药物剂量”等表述；不得推荐药物；不得添加未提供的症状或指标。
仅返回合法 JSON，不要 Markdown，格式必须是：
{
  "summary": "",
  "risk_explanations": {"规则类别": "该类别的通俗解释"},
  "recommendations": ["建议"],
  "action_plan": ["第1天：...", "第2天：...", "第3天：...", "第4天：...", "第5天：...", "第6天：...", "第7天：..."]
}
risk_explanations 的键必须且只能使用输入中给出的 category；如没有需要关注的风险项，则返回空对象 {}。"""
    user_prompt = (
        "以下内容完全由规则引擎产生，风险等级由系统固定，不需要你判断：\n"
        f"{json.dumps(model_input, ensure_ascii=False)}"
    )
    expected_categories = {item.category for item in attention_items}
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]
    draft: _ReportDraft | None = None
    for attempt in range(2):
        try:
            raw_content = await chat(messages, temperature=0.2)
            candidate = _ReportDraft.model_validate(_parse_json_object(raw_content))
            _ensure_non_diagnostic(candidate, expected_categories)
            draft = candidate
            break
        except LLMServiceError as exc:
            raise HealthReportAgentError(str(exc)) from exc
        except (HealthReportAgentError, ValidationError) as exc:
            if attempt == 1:
                raise HealthReportAgentError(str(exc)) from exc
            messages.extend(
                [
                    {"role": "assistant", "content": raw_content},
                    {
                        "role": "user",
                        "content": (
                            "上一版未通过格式或非诊断安全校验。请完整重写 JSON："
                            "只解释给定 category；不要使用疾病、诊断、确诊、患有、处方、"
                            "药物或任何英文医疗判断词；不要提及任何具体病名。"
                        ),
                    },
                ]
            )

    if draft is None:
        raise HealthReportAgentError("Model response did not produce a usable report")
    key_risks = [
        f"{item.title}（来源：{item.source}）：{draft.risk_explanations[item.category]}"
        for item in attention_items
    ]
    if not key_risks:
        key_risks = ["当前已输入的规则指标中，未发现需要重点关注的项目。"]
    return HealthReport(
        summary=draft.summary,
        risk_level=assessment.overall_level,
        key_risks=key_risks,
        recommendations=draft.recommendations,
        action_plan=draft.action_plan,
        safety_notice=SAFETY_NOTICE,
    )
