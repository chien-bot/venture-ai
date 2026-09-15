"""Deterministic, non-diagnostic health-risk rules for the MVP."""

from app.schemas import HealthDataInput, RiskItem, RiskLevel, RuleAssessment
from app.services.risk_config import THRESHOLDS

SAFETY_NOTICE = (
    "本结果仅用于健康风险提示与健康教育，不能用于疾病诊断，也不能替代医生的专业意见。"
)


def _bmi_risk(bmi: float) -> RiskItem:
    if bmi < THRESHOLDS.bmi_low:
        return RiskItem(
            category="BMI",
            level=RiskLevel.ATTENTION,
            title="BMI 偏低",
            reason=f"当前 BMI 为 {bmi}，低于成人参考区间。",
            recommendation="注意均衡饮食和规律作息；如体重持续下降或伴随不适，请咨询专业人员。",
        )
    if bmi < THRESHOLDS.bmi_attention:
        return RiskItem(
            category="BMI",
            level=RiskLevel.NORMAL,
            title="BMI 处于一般参考区间",
            reason=f"当前 BMI 为 {bmi}，处于成人一般参考区间。",
            recommendation="保持均衡饮食和规律运动，并定期记录变化。",
        )
    if bmi < THRESHOLDS.bmi_high_attention:
        return RiskItem(
            category="BMI",
            level=RiskLevel.ATTENTION,
            title="BMI 需要关注",
            reason=f"当前 BMI 为 {bmi}，高于成人一般参考区间。",
            recommendation="可逐步增加日常活动、控制高糖高脂食物摄入，并持续观察体重变化。",
        )
    return RiskItem(
        category="BMI",
        level=RiskLevel.HIGH_ATTENTION,
        title="BMI 明显偏高，需要重点关注",
        reason=f"当前 BMI 为 {bmi}，明显高于成人一般参考区间。",
        recommendation="建议尽快咨询线下专业人员，结合个人情况制定健康管理方案。",
    )


def _sleep_risk(sleep_hours: float) -> RiskItem:
    if THRESHOLDS.sleep_hours_min <= sleep_hours <= THRESHOLDS.sleep_hours_max:
        return RiskItem(
            category="sleep",
            level=RiskLevel.NORMAL,
            title="睡眠时长基本充足",
            reason=f"平均每晚睡眠 {sleep_hours} 小时，处于成人常见建议范围。",
            recommendation="尽量维持规律睡眠时间，持续关注睡眠质量。",
        )
    if sleep_hours < THRESHOLDS.sleep_high_attention_below:
        return RiskItem(
            category="sleep",
            level=RiskLevel.HIGH_ATTENTION,
            title="睡眠时长明显不足，需要重点关注",
            reason=f"平均每晚睡眠仅 {sleep_hours} 小时，可能影响日间精力与长期健康。",
            recommendation="优先调整作息，逐步增加睡眠时间；若长期难以入睡或明显影响生活，建议咨询专业人员。",
        )
    return RiskItem(
        category="sleep",
        level=RiskLevel.ATTENTION,
        title="睡眠时长需关注",
        reason=f"平均每晚睡眠 {sleep_hours} 小时，未处于成人常见建议范围。",
        recommendation="尝试固定起睡时间、减少睡前屏幕使用，并观察改善情况。",
    )


def _exercise_risk(days: int) -> RiskItem:
    if days >= THRESHOLDS.exercise_days_target:
        return RiskItem(
            category="exercise",
            level=RiskLevel.NORMAL,
            title="运动频率基本达标",
            reason=f"每周运动 {days} 天，已具备规律运动习惯。",
            recommendation="保持适合自身的运动强度，并注意热身与恢复。",
        )
    if days == 0:
        return RiskItem(
            category="exercise",
        level=RiskLevel.HIGH_ATTENTION,
        title="缺少规律运动，需要重点关注",
            reason="近一周没有记录运动日，久坐相关健康风险值得关注。",
            recommendation="可从每天 10–20 分钟快走或轻度运动开始，循序渐进建立习惯。",
        )
    return RiskItem(
        category="exercise",
        level=RiskLevel.ATTENTION,
        title="运动频率偏少",
        reason=f"每周运动 {days} 天，规律性仍有提升空间。",
        recommendation="尝试将运动增加到每周至少 3 天，并选择可长期坚持的方式。",
    )


def _blood_pressure_risk(systolic: int | None, diastolic: int | None) -> RiskItem | None:
    """Interpret one adult blood-pressure record as a follow-up signal, never a diagnosis."""
    if systolic is None or diastolic is None:
        return None
    reading = f"{systolic}/{diastolic} mmHg"
    if systolic < THRESHOLDS.blood_pressure_low_systolic or diastolic < THRESHOLDS.blood_pressure_low_diastolic:
        return RiskItem(
            category="blood_pressure",
            level=RiskLevel.HIGH_ATTENTION,
            title="本次血压记录明显偏低，需要重点关注",
            reason=f"本次输入血压为 {reading}，低于成人常用参考范围。单次记录不能用于判断疾病。",
            recommendation="建议在安静休息后复测；如反复出现偏低记录或伴随明显不适，请尽快咨询线下专业人员。",
        )
    if systolic < THRESHOLDS.blood_pressure_attention_systolic and diastolic < THRESHOLDS.blood_pressure_attention_diastolic:
        return RiskItem(
            category="blood_pressure",
            level=RiskLevel.NORMAL,
            title="本次血压记录处于一般参考范围",
            reason=f"本次输入血压为 {reading}，处于成人常用一般参考范围。",
            recommendation="保持规律作息、合理饮食和适量运动，并定期记录血压。",
        )
    if systolic < THRESHOLDS.blood_pressure_high_systolic and diastolic < THRESHOLDS.blood_pressure_high_diastolic:
        return RiskItem(
            category="blood_pressure",
            level=RiskLevel.ATTENTION,
            title="本次血压记录需要关注",
            reason=f"本次输入血压为 {reading}，高于成人一般参考范围。单次记录不能用于判断疾病。",
            recommendation="建议在不同日期、安静状态下重复测量，并关注高盐饮食、睡眠与运动习惯。",
        )
    return RiskItem(
        category="blood_pressure",
        level=RiskLevel.HIGH_ATTENTION,
        title="本次血压记录偏高，需要重点关注",
        reason=f"本次输入血压为 {reading}，达到需要尽快复测和关注的水平；单次记录不能用于判断疾病。",
        recommendation="建议尽快在安静状态下复测并记录结果；若多次复测仍偏高，请咨询线下专业人员。",
    )


def _fasting_blood_glucose_risk(value: float | None) -> RiskItem | None:
    """Interpret an optional fasting glucose result without inferring a disease."""
    if value is None:
        return None
    reading = f"{value:.1f} mmol/L"
    if THRESHOLDS.fasting_glucose_low <= value < THRESHOLDS.fasting_glucose_attention:
        return RiskItem(
            category="fasting_blood_glucose",
            level=RiskLevel.NORMAL,
            source="user_input.blood_glucose",
            title="空腹血糖记录处于一般参考范围",
            reason=f"本次输入空腹血糖为 {reading}，处于成人常用一般参考范围。",
            recommendation="保持均衡饮食、规律运动与定期健康检查。",
        )
    if THRESHOLDS.fasting_glucose_attention <= value < THRESHOLDS.fasting_glucose_high_attention:
        return RiskItem(
            category="fasting_blood_glucose",
            level=RiskLevel.ATTENTION,
            source="user_input.blood_glucose",
            title="空腹血糖记录需要关注",
            reason=f"本次输入空腹血糖为 {reading}，高于成人一般参考范围。单次结果不能用于判断疾病。",
            recommendation="建议确认是否为空腹检测，并在后续健康检查中复测；同时关注饮食、体重和运动习惯。",
        )
    return RiskItem(
        category="fasting_blood_glucose",
        level=RiskLevel.HIGH_ATTENTION,
        source="user_input.blood_glucose",
        title="空腹血糖记录明显偏离一般参考范围，需要重点关注",
        reason=f"本次输入空腹血糖为 {reading}，明显偏离成人一般参考范围。单次结果不能用于判断疾病。",
        recommendation="建议尽快确认检测条件并复测；如复测仍明显偏离一般参考范围，请咨询线下专业人员。",
    )


def assess_health_risk(data: HealthDataInput) -> RuleAssessment:
    """Evaluate the three MVP dimensions without making medical diagnoses."""
    bmi = data.bmi
    risks = [_bmi_risk(bmi), _sleep_risk(data.sleep_hours), _exercise_risk(data.exercise_days_per_week)]
    blood_pressure_risk = _blood_pressure_risk(data.systolic_bp, data.diastolic_bp)
    glucose_risk = _fasting_blood_glucose_risk(data.fasting_blood_glucose_mmol_l)
    risks.extend(item for item in (blood_pressure_risk, glucose_risk) if item is not None)
    if any(item.level == RiskLevel.HIGH_ATTENTION for item in risks):
        overall_level = RiskLevel.HIGH_ATTENTION
    elif any(item.level is RiskLevel.ATTENTION for item in risks):
        overall_level = RiskLevel.ATTENTION
    else:
        overall_level = RiskLevel.NORMAL
    return RuleAssessment(bmi=bmi, overall_level=overall_level, risks=risks, safety_notice=SAFETY_NOTICE)
