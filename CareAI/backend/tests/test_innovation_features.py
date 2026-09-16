from fastapi.testclient import TestClient

from app import main
from app.database import save_health_report
from app.schemas import HealthDataInput, HealthReport
from app.services.health_report_agent import find_safety_violations
from app.services.risk_rules import assess_health_risk


def _payload(user_id: str) -> dict:
    return {
        "age": 28, "gender": "female", "height": 165, "weight": 62,
        "blood_pressure": "128/82", "sleep_hours": 6.5, "exercise_frequency": 1,
        "user_id": user_id, "recorded_at": "2026-09-16", "health_goal": "改善睡眠",
    }


async def _fake_report(assessment) -> HealthReport:
    return HealthReport(
        summary="测试健康教育报告。", risk_level=assessment.overall_level,
        key_risks=["睡眠时长需要关注。"], recommendations=["今晚提前20分钟准备休息。"],
        action_plan=[f"第{day}天：记录睡眠准备时间。" for day in range(1, 8)],
        safety_notice="本报告不用于疾病诊断。",
    )


def test_privacy_can_disable_ai_and_persistence(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("CAREAI_DB_PATH", str(tmp_path / "privacy.db"))
    client = TestClient(main.app)
    client.post("/api/v1/users", json={"id": "private-user", "display_name": "Private User"})
    response = client.put("/api/v1/privacy/private-user", json={
        "ai_processing_enabled": False, "save_reports": False,
        "retention_days": 30, "summary_export_enabled": True,
    })
    assert response.status_code == 200
    assert response.json()["ai_processing_enabled"] is False

    result = client.post("/api/v1/health/analyze", json=_payload("private-user"))
    assert result.status_code == 200
    assert "本地规则" in result.json()["summary"]
    assert "X-CareAI-Report-Id" not in result.headers
    assert client.get("/api/v1/health/reports?user_id=private-user").json() == []
    assert client.post("/api/v1/health/weekly-plan-drafts?user_id=private-user").status_code == 403
    assert client.post(
        "/api/v1/health/weekly-plan-experiments?user_id=private-user",
        json={"experiment_variable": "提醒时间", "difficulty": 2},
    ).status_code == 403


def test_privacy_disables_ai_for_weekly_plan_and_records_local_provenance(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("CAREAI_DB_PATH", str(tmp_path / "local-mode.db"))

    async def unexpected_ai(*args, **kwargs):
        raise AssertionError("external weekly-plan AI must not run while AI processing is disabled")

    monkeypatch.setattr(main, "generate_weekly_plan", unexpected_ai)
    client = TestClient(main.app)
    client.post("/api/v1/users", json={"id": "local-user", "display_name": "Local User", "health_goal": "改善睡眠"})
    client.put("/api/v1/privacy/local-user", json={
        "ai_processing_enabled": False, "save_reports": True,
        "retention_days": 30, "summary_export_enabled": True,
    })
    analyzed = client.post("/api/v1/health/analyze", json=_payload("local-user"))
    report_id = int(analyzed.headers["X-CareAI-Report-Id"])
    assert analyzed.headers["X-CareAI-Generation-Source"] == "local_rule"

    evidence = client.get(f"/api/v1/health/reports/{report_id}/evidence?user_id=local-user").json()
    recommendation_cards = [card for card in evidence["cards"] if card["kind"] == "recommendation"]
    assert recommendation_cards
    assert {card["decision_owner"] for card in recommendation_cards} == {"local_rule"}
    assert evidence["model"] == "CareAI deterministic local rules"

    draft = client.post("/api/v1/health/weekly-plan-drafts?user_id=local-user")
    assert draft.status_code == 200
    assert draft.json()["experiment_snapshot"]


def test_evidence_cards_and_comprehension_are_saved(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("CAREAI_DB_PATH", str(tmp_path / "evidence.db"))
    monkeypatch.setattr(main, "generate_health_report", _fake_report)
    client = TestClient(main.app)
    analyzed = client.post("/api/v1/health/analyze", json=_payload("learner"))
    report_id = int(analyzed.headers["X-CareAI-Report-Id"])

    evidence = client.get(f"/api/v1/health/reports/{report_id}/evidence?user_id=learner")
    assert evidence.status_code == 200
    assert evidence.json()["rule_version"] == "2026.09-mvp"
    assert any(card["decision_owner"] == "local_rule" for card in evidence.json()["cards"])
    assert any(card["kind"] == "recommendation" for card in evidence.json()["cards"])

    wrong = client.post(f"/api/v1/health/reports/{report_id}/comprehension?user_id=learner", json={
        "meaning_answer": "medical_diagnosis", "boundary_answer": "change_medicine",
        "action_answer": "wait_for_diagnosis",
    })
    assert wrong.json()["score"] == 0
    correct = client.post(f"/api/v1/health/reports/{report_id}/comprehension?user_id=learner", json={
        "meaning_answer": "health_education", "boundary_answer": "repeat_and_seek_help",
        "action_answer": "choose_one_small_step",
    })
    assert correct.json()["passed"] is True
    assert correct.json()["attempts"] == 2

    plan = client.get(f"/api/v1/health/reports/{report_id}/plan?user_id=learner").json()
    updated = client.patch(
        f"/api/v1/health/plan-tasks/{plan['tasks'][0]['id']}?user_id=learner",
        json={"completed": True, "completion_reason": "理解后开始"},
    )
    assert updated.status_code == 200


def test_legacy_report_evidence_keeps_unknown_source(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("CAREAI_DB_PATH", str(tmp_path / "legacy-evidence.db"))
    data = HealthDataInput.model_validate(_payload("legacy-user"))
    saved = save_health_report(data, assess_health_risk(data), HealthReport(
        summary="迁移前报告。", risk_level="attention", key_risks=["历史关注项。"],
        recommendations=["保留一项低负担行动。"],
        action_plan=[f"第{day}天：记录行动。" for day in range(1, 8)],
        safety_notice="仅供健康教育。",
    ))
    client = TestClient(main.app)
    evidence = client.get(f"/api/v1/health/reports/{saved.id}/evidence?user_id=legacy-user").json()
    owners = {card["decision_owner"] for card in evidence["cards"] if card["kind"] == "recommendation"}
    assert owners == {"legacy_unknown"}


def test_action_tracking_is_locked_until_comprehension_passes(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("CAREAI_DB_PATH", str(tmp_path / "comprehension-gate.db"))
    monkeypatch.setattr(main, "generate_health_report", _fake_report)
    client = TestClient(main.app)
    analyzed = client.post("/api/v1/health/analyze", json=_payload("gate-user"))
    report_id = int(analyzed.headers["X-CareAI-Report-Id"])
    task_id = client.get(f"/api/v1/health/reports/{report_id}/plan?user_id=gate-user").json()["tasks"][0]["id"]
    locked = client.patch(
        f"/api/v1/health/plan-tasks/{task_id}?user_id=gate-user",
        json={"completed": True, "completion_reason": None},
    )
    assert locked.status_code == 403


def test_portable_and_fhir_exports_include_provenance(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("CAREAI_DB_PATH", str(tmp_path / "export.db"))
    monkeypatch.setattr(main, "generate_health_report", _fake_report)
    client = TestClient(main.app)
    client.post("/api/v1/health/analyze", json=_payload("export-user"))

    summary = client.get("/api/v1/health/portable-summary?user_id=export-user")
    assert summary.status_code == 200
    assert summary.json()["provenance"]["schema_version"] == "careai-portable-summary-v1"
    assert summary.json()["observations"]

    fhir = client.get("/api/v1/health/fhir-export?user_id=export-user")
    assert fhir.status_code == 200
    assert fhir.json()["resourceType"] == "Bundle"
    assert any(entry["resource"]["resourceType"] == "Provenance" for entry in fhir.json()["entry"])

    safety = client.get("/api/v1/safety/suite")
    assert safety.status_code == 200
    assert safety.json()["passed"] is True
    assert safety.json()["pass_count"] == safety.json()["total_count"]
    assert safety.json()["total_count"] == 12
    assert "direct-disease-claim-zh" in find_safety_violations("你有高血压。")
    assert "specific-dosage" in find_safety_violations("每天服用5mg阿司匹林。")


def test_weekly_experiment_versions_and_changes_one_variable(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("CAREAI_DB_PATH", str(tmp_path / "experiments.db"))
    client = TestClient(main.app)
    client.post("/api/v1/users", json={"id": "experiment-user", "display_name": "Experiment User", "health_goal": "改善睡眠"})
    first = client.post("/api/v1/health/weekly-plan-experiments?user_id=experiment-user", json={"experiment_variable": "提醒时间", "difficulty": 2})
    second = client.post("/api/v1/health/weekly-plan-experiments?user_id=experiment-user", json={"experiment_variable": "行动时长", "difficulty": 3})
    assert first.status_code == 200 and second.status_code == 200
    assert first.json()["version"] == 1
    assert second.json()["version"] == 2
    assert second.json()["previous_draft_id"] == first.json()["id"]
    assert second.json()["experiment_variable"] == "行动时长"
    first_snapshot = first.json()["experiment_snapshot"]
    second_snapshot = second.json()["experiment_snapshot"]
    changed = {key for key in first_snapshot if first_snapshot[key] != second_snapshot[key]}
    assert changed == {"duration_minutes"}
    assert first_snapshot["difficulty"] == second_snapshot["difficulty"] == 1
    assert [task["content"] for task in first.json()["tasks"]] != [task["content"] for task in second.json()["tasks"]]
