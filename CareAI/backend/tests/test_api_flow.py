from fastapi.testclient import TestClient

from app import main
from app.schemas import HealthReport, RiskLevel


def test_complete_analysis_flow_with_llm_stub(monkeypatch, tmp_path) -> None:
    """Verify the HTTP pipeline while isolating the external MaaS dependency."""

    async def fake_generate_health_report(assessment) -> HealthReport:
        assert assessment.overall_level == RiskLevel.HIGH_ATTENTION
        assert assessment.bmi == 26.1
        return HealthReport(
            summary="存在需要重点关注的健康指标。",
            risk_level=RiskLevel.HIGH_ATTENTION,
            key_risks=["睡眠时长需要重点关注。"],
            recommendations=["建议复测并保持规律生活。"],
            action_plan=[f"第{i}天：安排适量活动。" for i in range(1, 8)],
            safety_notice="本报告不用于疾病诊断。",
        )

    monkeypatch.setattr(main, "generate_health_report", fake_generate_health_report)
    monkeypatch.setenv("CAREAI_DB_PATH", str(tmp_path / "careai-api-test.db"))
    client = TestClient(main.app)
    response = client.post(
        "/api/v1/health/analyze",
        json={
            "age": 22,
            "gender": "male",
            "height": 175,
            "weight": 80,
            "blood_pressure": "145/90",
            "sleep_hours": 5,
            "exercise_frequency": 1,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["risk_level"] == "high_attention"
    assert len(body["action_plan"]) == 7
    assert "诊断" in body["safety_notice"]
    assert response.headers["X-CareAI-Report-Id"] == "1"

    history = client.get("/api/v1/health/reports")
    trends = client.get("/api/v1/health/trends")

    assert history.status_code == 200
    assert history.json()[0]["assessment"]["bmi"] == 26.1
    assert trends.status_code == 200
    assert trends.json()[0]["risk_level"] == "high_attention"
