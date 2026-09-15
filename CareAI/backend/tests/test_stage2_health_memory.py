from datetime import date, timedelta

from app.database import (
    confirm_weekly_plan_draft,
    get_action_plan_for_report,
    get_weekly_review,
    list_health_reports,
    save_health_report,
    save_user_profile,
    save_weekly_plan_draft,
    update_plan_task,
)
from app.schemas import Gender, HealthDataInput, HealthReport, UserProfileInput
from app.services.risk_rules import assess_health_risk
from app.services.trend_insights import generate_trend_insights


def _report_for(data: HealthDataInput) -> HealthReport:
    assessment = assess_health_risk(data)
    return HealthReport(
        summary="健康 Memory 测试报告。", risk_level=assessment.overall_level,
        key_risks=["测试风险提示。"], recommendations=["测试建议。"],
        action_plan=[f"第{day}天：完成测试行动。" for day in range(1, 8)],
        safety_notice="本报告不用于疾病诊断。",
    )


def test_health_memory_isolates_profiles_and_persists_plan(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("CAREAI_DB_PATH", str(tmp_path / "stage2.db"))
    save_user_profile(UserProfileInput(id="alice", display_name="Alice", age=30, gender=Gender.FEMALE))
    save_user_profile(UserProfileInput(id="bob", display_name="Bob", age=31, gender=Gender.MALE))
    alice_data = HealthDataInput(age=30, gender=Gender.FEMALE, height_cm=160, weight_kg=55,
        sleep_hours=7, exercise_days_per_week=3, user_id="alice", recorded_at=date(2026, 1, 1))
    bob_data = HealthDataInput(age=31, gender=Gender.MALE, height_cm=175, weight_kg=75,
        sleep_hours=7, exercise_days_per_week=3, user_id="bob", recorded_at=date(2026, 1, 1))
    saved_alice = save_health_report(alice_data, assess_health_risk(alice_data), _report_for(alice_data))
    save_health_report(bob_data, assess_health_risk(bob_data), _report_for(bob_data))

    assert [item.id for item in list_health_reports("alice")] == [saved_alice.id]
    assert list_health_reports("bob")[0].input.user_id == "bob"
    plan = get_action_plan_for_report(saved_alice.id, "alice")
    assert plan is not None and len(plan.tasks) == 7
    completed = update_plan_task(plan.tasks[0].id, "alice", True, "已完成")
    assert completed is not None and completed.completed
    assert get_weekly_review("alice").completed_tasks == 1


def test_trend_insights_require_history_then_detect_sleep_decline(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("CAREAI_DB_PATH", str(tmp_path / "trends.db"))
    records = []
    for offset, sleep in enumerate((8, 7, 6)):
        data = HealthDataInput(age=30, gender=Gender.FEMALE, height_cm=160, weight_kg=55,
            sleep_hours=sleep, exercise_days_per_week=3, user_id="demo-user",
            recorded_at=date(2026, 1, 1) + timedelta(days=offset * 30))
        records.append(save_health_report(data, assess_health_risk(data), _report_for(data)))

    insights = generate_trend_insights(list_health_reports("demo-user"))
    assert any(item.category == "sleep" and item.level == "attention" for item in insights)


def test_confirmed_weekly_plan_becomes_the_next_review_source(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("CAREAI_DB_PATH", str(tmp_path / "weekly-plan.db"))
    draft = save_weekly_plan_draft("demo-user", "改善睡眠", "测试总结", "测试调整原因", [f"第{i}天：测试任务" for i in range(1, 8)])
    assert draft.confirmed_at is None
    confirmed = confirm_weekly_plan_draft(draft.id, "demo-user")
    assert confirmed is not None and confirmed.confirmed_at is not None
    review = get_weekly_review("demo-user")
    assert review.total_tasks == 7
    assert review.completion_rate == 0
