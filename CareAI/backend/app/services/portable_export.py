"""Portable, user-controlled health-summary exports."""

from datetime import datetime, timezone

from app.schemas import (
    PortableHealthSummary, PortableObservation, ProvenanceMetadata, ReportHistoryItem,
    TrendInsight, UserProfile, WeeklyReview,
)
from app.services.risk_config import RULES_VERSION


def _latest_observations(reports: list[ReportHistoryItem]) -> list[PortableObservation]:
    if not reports:
        return []
    latest = reports[0]
    recorded_at = latest.input.recorded_at.isoformat()
    source = latest.input.source
    values: list[tuple[str, str, float | int | str, str | None]] = [
        ("bmi", "BMI", latest.assessment.bmi, "kg/m2"),
        ("sleep-hours", "平均睡眠时长", latest.input.sleep_hours, "h/night"),
        ("exercise-days", "每周运动天数", latest.input.exercise_days_per_week, "days/week"),
    ]
    if latest.input.systolic_bp is not None and latest.input.diastolic_bp is not None:
        values.append(("blood-pressure", "血压记录", f"{latest.input.systolic_bp}/{latest.input.diastolic_bp}", "mmHg"))
    if latest.input.fasting_blood_glucose_mmol_l is not None:
        values.append(("fasting-glucose", "空腹血糖记录", latest.input.fasting_blood_glucose_mmol_l, "mmol/L"))
    return [PortableObservation(code=code, display=display, value=value, unit=unit, recorded_at=recorded_at, source=source)
            for code, display, value, unit in values]


def build_portable_summary(
    user: UserProfile,
    reports: list[ReportHistoryItem],
    insights: list[TrendInsight],
    review: WeeklyReview,
) -> PortableHealthSummary:
    generated_at = datetime.now(timezone.utc).isoformat()
    return PortableHealthSummary(
        user=user,
        observations=_latest_observations(reports),
        trend_insights=insights,
        weekly_review=review,
        provenance=ProvenanceMetadata(
            schema_version="careai-portable-summary-v1",
            generated_at=generated_at,
            rule_version=RULES_VERSION,
            source_report_ids=[item.id for item in reports],
            generator="CareAI local export",
            boundary="用户控制的非诊断性健康教育摘要；未经医疗机构认证。",
        ),
        safety_notice="本摘要供用户保存或与专业人员沟通参考，不构成医疗诊断、处方或治疗建议。",
    )


def build_fhir_demo_bundle(summary: PortableHealthSummary) -> dict:
    """Create a small FHIR R5-shaped demo bundle; it is not a certified clinical exchange."""
    patient_id = summary.user.id
    entries: list[dict] = [{
        "fullUrl": f"urn:uuid:patient-{patient_id}",
        "resource": {"resourceType": "Patient", "id": patient_id, "name": [{"text": summary.user.display_name}]},
    }]
    observation_refs: list[dict] = []
    for index, observation in enumerate(summary.observations, start=1):
        resource_id = f"careai-observation-{index}"
        resource = {
            "resourceType": "Observation", "id": resource_id, "status": "final",
            "code": {"text": observation.display}, "subject": {"reference": f"Patient/{patient_id}"},
            "effectiveDateTime": observation.recorded_at,
            "note": [{"text": "CareAI非诊断性用户自录数据；仅用于健康教育。"}],
        }
        if isinstance(observation.value, (int, float)):
            resource["valueQuantity"] = {"value": observation.value, "unit": observation.unit}
        else:
            resource["valueString"] = str(observation.value)
        entries.append({"fullUrl": f"urn:uuid:{resource_id}", "resource": resource})
        observation_refs.append({"reference": f"Observation/{resource_id}"})
    entries.append({
        "fullUrl": "urn:uuid:careai-provenance",
        "resource": {
            "resourceType": "Provenance", "id": "careai-provenance", "target": observation_refs,
            "recorded": summary.provenance.generated_at,
            "activity": {"text": "CareAI user-controlled summary export"},
            "agent": [{"type": {"text": "assembler"}, "who": {"display": "CareAI local export"}}],
            "policy": ["https://hl7.org/fhir/provenance.html"],
        },
    })
    return {"resourceType": "Bundle", "type": "collection", "timestamp": summary.provenance.generated_at,
            "meta": {"tag": [{"display": "Demonstration export; not certified clinical exchange"}]}, "entry": entries}
