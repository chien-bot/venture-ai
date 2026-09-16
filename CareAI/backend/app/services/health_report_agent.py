"""Constrained Health Report Agent built on top of deterministic risk rules."""

import json
import re
from typing import Any

from pydantic import BaseModel, Field, ValidationError

from app.schemas import HealthReport, RiskItem, RiskLevel, RuleAssessment
from app.services.llm import LLMServiceError, chat
from app.services.risk_rules import SAFETY_NOTICE

AGENT_VERSION = "careai-report-agent-v2"


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

_SAFETY_PATTERNS: tuple[tuple[str, str], ...] = (
    ("direct-disease-claim-zh", r"(?:你|用户|患者).{0,8}(?:有|得了|患上|患有|属于).{0,12}(?:高血压|糖尿病|冠心病|抑郁症|焦虑症|脂肪肝|肾病|癌症)"),
    ("direct-disease-claim-en", r"\b(?:you|the user|the patient)\s+(?:have|has|suffer(?:s)? from)\s+(?:hypertension|diabetes|depression|cancer|kidney disease)\b"),
    ("disease-name", r"(?:高血压|糖尿病|冠心病|抑郁症|焦虑症|脂肪肝|肾病|癌症|hypertension|diabetes|depression|cancer)"),
    ("specific-medication", r"(?:阿司匹林|二甲双胍|布洛芬|对乙酰氨基酚|氨氯地平|aspirin|metformin|ibuprofen|amlodipine)"),
    ("specific-dosage", r"\d+(?:\.\d+)?\s*(?:mg|g|ml|毫克|克|毫升|片|粒)"),
    ("medication-frequency", r"(?:每天|每日|一天).{0,8}(?:服用|口服|吃药)|(?:服用|口服).{0,8}(?:每天|每日|一天)|\b(?:take|use)\b.{0,30}\b(?:daily|twice a day|once a day)\b"),
    ("medication-instruction", r"(?:建议|应该|请|需要).{0,12}(?:服用|口服|停药|换药|加量|减量)|\b(?:take|stop|increase|decrease)\b.{0,20}\b(?:aspirin|metformin|ibuprofen|medication|dose)\b"),
)


def find_safety_violations(text: str) -> list[str]:
    """Return terms and pattern labels found in generated lifestyle guidance."""
    lowered = text.lower()
    violations = {term for term in _FORBIDDEN_TERMS if term.lower() in lowered}
    violations.update(label for label, pattern in _SAFETY_PATTERNS if re.search(pattern, lowered, re.IGNORECASE))
    return sorted(violations)


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
    if find_safety_violations(text):
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


def generate_local_rule_report(assessment: RuleAssessment) -> HealthReport:
    """Create a useful offline report without sending any data to an LLM."""
    attention_items = _items_requiring_attention(assessment)
    key_risks = [f"{item.title}（来源：{item.source}）：{item.reason}" for item in attention_items]
    if not key_risks:
        key_risks = ["当前已输入的规则指标中，未发现需要重点关注的项目。"]
    recommendations = [item.recommendation for item in attention_items]
    if not recommendations:
        recommendations = ["保持规律作息、适量活动，并继续记录变化。"]
    seed = recommendations[:3]
    action_plan = [
        "第1天：选择一项最容易开始的生活方式行动，并记录计划时间。",
        f"第2天：{seed[0]}",
        "第3天：记录行动是否完成，以及最主要的帮助或阻碍。",
        f"第4天：{seed[min(1, len(seed) - 1)]}",
        "第5天：重复最容易坚持的一项行动，保持低负担。",
        f"第6天：{seed[min(2, len(seed) - 1)]}",
        "第7天：回顾本周完成情况，只保留下一周最可执行的一项调整。",
    ]
    return HealthReport(
        summary="本报告由本地规则生成，未调用外部 AI。请根据需要关注的指标选择一个低负担行动，并持续记录变化。",
        risk_level=assessment.overall_level,
        key_risks=key_risks,
        recommendations=recommendations[:5],
        action_plan=action_plan,
        safety_notice=SAFETY_NOTICE + " 本次报告未调用外部 AI。",
    )
