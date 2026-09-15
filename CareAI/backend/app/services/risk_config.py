"""Central, reviewable reference configuration for CareAI's non-diagnostic rules."""

from dataclasses import asdict, dataclass
from typing import Any


RULES_VERSION = "2026.09-mvp"
RULES_SCOPE = (
    "仅适用于 CareAI MVP 的成年用户健康教育和风险提示。阈值用于生成 normal、"
    "attention、high_attention 标签，不用于疾病诊断、筛查结论或处方建议。"
)
CLINICAL_REVIEW_NOTICE = "上线前应由具有相应资质的专业人员结合目标人群和适用规范进行复核。"


@dataclass(frozen=True)
class RuleThresholds:
    bmi_low: float = 18.5
    bmi_attention: float = 24.0
    bmi_high_attention: float = 28.0
    sleep_hours_min: float = 7.0
    sleep_hours_max: float = 9.0
    sleep_high_attention_below: float = 6.0
    exercise_days_target: int = 3
    blood_pressure_low_systolic: int = 90
    blood_pressure_low_diastolic: int = 60
    blood_pressure_attention_systolic: int = 120
    blood_pressure_attention_diastolic: int = 80
    blood_pressure_high_systolic: int = 140
    blood_pressure_high_diastolic: int = 90
    fasting_glucose_low: float = 3.9
    fasting_glucose_attention: float = 6.1
    fasting_glucose_high_attention: float = 7.0


THRESHOLDS = RuleThresholds()

PUBLIC_HEALTH_REFERENCES = (
    {
        "dimension": "sleep",
        "title": "CDC — About Sleep",
        "url": "https://www.cdc.gov/sleep/about/index.html",
        "use": "成人睡眠时长的公共健康教育参考。",
    },
    {
        "dimension": "exercise",
        "title": "WHO — Guidelines on physical activity and sedentary behaviour",
        "url": "https://www.who.int/publications/i/item/9789240015128",
        "use": "成年人规律身体活动的公共健康教育参考；MVP 以每周运动天数作为简化追踪指标。",
    },
    {
        "dimension": "BMI",
        "title": "WHO — Use of body mass index of adults in assessing nutritional status",
        "url": "https://iris.who.int/handle/10665/264139",
        "use": "成人 BMI 健康教育背景参考；具体项目分段必须经专业复核。",
    },
)


def get_rule_information() -> dict[str, Any]:
    """Return safe-to-display rule metadata without exposing internal implementation details."""
    return {
        "version": RULES_VERSION,
        "scope": RULES_SCOPE,
        "clinical_review_notice": CLINICAL_REVIEW_NOTICE,
        "thresholds": asdict(THRESHOLDS),
        "references": list(PUBLIC_HEALTH_REFERENCES),
    }
