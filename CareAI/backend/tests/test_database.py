from app.database import get_health_report, get_health_trends, list_health_reports, save_health_report
from app.schemas import Gender, HealthDataInput, HealthReport, RiskLevel
from app.services.risk_rules import assess_health_risk


def test_saved_reports_and_trends_use_sqlite(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("CAREAI_DB_PATH", str(tmp_path / "careai-test.db"))
    data = HealthDataInput(
        age=22,
        gender=Gender.FEMALE,
        height_cm=165,
        weight_kg=62,
        sleep_hours=6.5,
        exercise_days_per_week=2,
    )
    assessment = assess_health_risk(data)
    report = HealthReport(
        summary="需要关注作息与运动习惯。",
        risk_level=assessment.overall_level,
        key_risks=["睡眠时长需要关注。"],
        recommendations=["保持规律作息。"],
        action_plan=[f"第{i}天：完成轻度活动。" for i in range(1, 8)],
        safety_notice="本报告不用于疾病诊断。",
    )

    saved = save_health_report(data, assessment, report)

    assert saved.id == 1
    assert get_health_report(saved.id).report.summary == report.summary
    assert len(list_health_reports()) == 1
    trend = get_health_trends()
    assert trend[0].bmi == assessment.bmi
    assert trend[0].risk_level == RiskLevel.ATTENTION
