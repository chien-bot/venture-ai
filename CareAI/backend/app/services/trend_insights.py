"""Explainable, non-diagnostic trend checks over one user's health memory."""

from app.schemas import ReportHistoryItem, RiskLevel, TrendInsight


def generate_trend_insights(reports: list[ReportHistoryItem]) -> list[TrendInsight]:
    """Return only deterministic observations; require three records before any trend claim."""
    chronological = list(reversed(reports))
    count = len(chronological)
    if count < 3:
        return [TrendInsight(category="data_quality", level=RiskLevel.NORMAL, title="健康记忆仍在建立中",
            explanation=f"目前只有 {count} 次记录；至少需要 3 次带日期的记录才会判断个人趋势。",
            next_step="请在不同日期继续记录相同指标，CareAI 会在资料足够时进行趋势比较。", data_points=count)]

    recent = chronological[-3:]
    insights: list[TrendInsight] = []
    sleeps = [item.input.sleep_hours for item in recent]
    if sleeps[0] - sleeps[-1] >= 1 and sleeps[0] >= sleeps[1] >= sleeps[2]:
        insights.append(TrendInsight(category="sleep", level=RiskLevel.ATTENTION, title="近三次睡眠时长持续下降",
            explanation=f"最近三次记录从 {sleeps[0]:.1f} 小时降至 {sleeps[-1]:.1f} 小时；这是基于个人记录的变化提示，不是疾病判断。",
            next_step="本周优先固定起床时间，并在下次记录中观察睡眠是否回升。", data_points=3))

    bmis = [item.assessment.bmi for item in recent]
    if bmis[-1] - bmis[0] >= 0.8 and bmis[0] <= bmis[1] <= bmis[2]:
        insights.append(TrendInsight(category="BMI", level=RiskLevel.ATTENTION, title="BMI 近三次呈上升趋势",
            explanation=f"BMI 从 {bmis[0]:.1f} 上升至 {bmis[-1]:.1f}，增幅为 {bmis[-1] - bmis[0]:.1f}。",
            next_step="结合饮食与活动记录，选择一个可持续的小目标，并在后续记录中观察变化。", data_points=3))

    exercise = [item.input.exercise_days_per_week for item in recent]
    if all(days <= 1 for days in exercise):
        insights.append(TrendInsight(category="exercise", level=RiskLevel.ATTENTION, title="运动记录持续偏少",
            explanation=f"最近三次记录的每周运动天数为 {', '.join(str(days) for days in exercise)} 天。",
            next_step="从每周增加一天低强度活动开始，完成后再逐步调整。", data_points=3))

    pressures = [item.input.systolic_bp for item in recent]
    if all(value is not None and value >= 130 for value in pressures):
        values = [int(value) for value in pressures if value is not None]
        insights.append(TrendInsight(category="blood_pressure", level=RiskLevel.HIGH_ATTENTION, title="血压记录连续需要关注",
            explanation=f"最近三次收缩压记录均在 130 mmHg 或以上（{', '.join(map(str, values))} mmHg）。单次或少量记录不能用于诊断。",
            next_step="请在安静休息后按规范复测并记录；若持续异常或伴随不适，请咨询线下专业人员。", data_points=3))

    glucose = [item.input.fasting_blood_glucose_mmol_l for item in recent]
    if all(value is not None and value >= 6.1 for value in glucose):
        values = [f"{float(value):.1f}" for value in glucose if value is not None]
        insights.append(TrendInsight(category="fasting_blood_glucose", level=RiskLevel.HIGH_ATTENTION, title="空腹血糖记录连续需要关注",
            explanation=f"最近三次已记录空腹血糖均为 6.1 mmol/L 或以上（{', '.join(values)} mmol/L）。这不是疾病诊断。",
            next_step="确认每次均为空腹检测并在后续复测；若持续偏离一般参考范围，请咨询线下专业人员。", data_points=3))

    if not insights:
        insights.append(TrendInsight(category="overall", level=RiskLevel.NORMAL, title="暂未发现需要额外关注的连续变化",
            explanation=f"已比较最近 {count} 次健康记录；这仅表示目前规则未识别到预设的连续变化模式。",
            next_step="继续在相近条件下记录指标，并按计划保持健康习惯。", data_points=count))
    return insights
