"""Build user-facing provenance cards for one saved CareAI report."""

from datetime import datetime, timezone

from app.schemas import EvidenceCard, EvidenceReference, ReportEvidenceBundle, ReportHistoryItem
from app.services.risk_config import PUBLIC_HEALTH_REFERENCES


SOURCE_FIELDS = {
    "BMI": ["user_input.height_cm", "user_input.weight_kg"],
    "sleep": ["user_input.sleep_hours"],
    "exercise": ["user_input.exercise_days_per_week"],
    "blood_pressure": ["user_input.systolic_bp", "user_input.diastolic_bp"],
    "fasting_blood_glucose": ["user_input.fasting_blood_glucose_mmol_l"],
}


def _references_for(category: str) -> list[EvidenceReference]:
    dimension = {"exercise": "exercise", "sleep": "sleep", "BMI": "BMI"}.get(category)
    if dimension is None:
        return [EvidenceReference(
            title="CareAI项目规则（待专业复核）",
            use="该阈值属于项目参考设置；上线或真实使用前必须由具备相应资质的专业人员复核。",
        )]
    return [
        EvidenceReference(title=item["title"], url=item["url"], use=item["use"])
        for item in PUBLIC_HEALTH_REFERENCES if item["dimension"] == dimension
    ]


def build_report_evidence(item: ReportHistoryItem) -> ReportEvidenceBundle:
    cards: list[EvidenceCard] = []
    for index, risk in enumerate(item.assessment.risks, start=1):
        cards.append(EvidenceCard(
            id=f"rule-{index}-{risk.category}", kind="rule", title=risk.title,
            source_fields=SOURCE_FIELDS.get(risk.category, [risk.source]), rule_version=item.rule_version,
            decision_owner="local_rule", explanation=risk.reason,
            uncertainty="单次记录只用于健康教育提示，不用于疾病判断；测量条件和个体情况可能影响数值。",
            references=_references_for(risk.category),
        ))
    categories = [risk.category for risk in item.assessment.risks if risk.level.value != "normal"]
    source_fields = sorted({field for category in categories for field in SOURCE_FIELDS.get(category, [])})
    recommendation_owner = item.generation_source
    recommendation_uncertainty = {
        "local_rule": "建议由本地规则模板生成；可执行性仍需用户结合自身情况判断。",
        "constrained_ai": "受限AI只负责把规则结果转化为低风险生活方式表达；建议的可行性仍需用户结合自身情况判断。",
        "legacy_unknown": "这是迁移前保存的历史报告，当前无法确认建议由本地规则还是受限AI生成。",
    }[recommendation_owner]
    for index, recommendation in enumerate(item.report.recommendations, start=1):
        cards.append(EvidenceCard(
            id=f"recommendation-{index}", kind="recommendation", title=f"行动建议 {index}",
            source_fields=source_fields, rule_version=item.rule_version, decision_owner=recommendation_owner,
            explanation=recommendation,
            uncertainty=recommendation_uncertainty,
            references=[],
        ))
    return ReportEvidenceBundle(
        report_id=item.id,
        generated_at=datetime.now(timezone.utc).isoformat(),
        rule_version=item.rule_version,
        agent_version=item.agent_version,
        model=item.generation_model,
        cards=cards,
        safety_notice="证据卡用于说明数据、规则和AI的职责边界；不能替代专业判断。",
    )
