import asyncio
import json

from app.schemas import Gender, HealthDataInput, RiskLevel
from app.services import health_report_agent
from app.services.risk_rules import assess_health_risk


def test_agent_uses_rule_level_and_returns_fixed_report(monkeypatch) -> None:
    async def fake_chat(messages, temperature=0.2) -> str:
        assert temperature == 0.2
        return json.dumps(
            {
                "summary": "部分已输入指标需要重点关注，可从规律作息和日常活动开始改善。",
                "risk_explanations": {
                    "BMI": "当前体重与身高计算出的结果高于一般参考区间。",
                    "sleep": "当前记录的睡眠时长偏少，建议逐步调整。",
                    "exercise": "当前每周运动次数偏少，可循序增加。",
                    "blood_pressure": "本次记录偏高，建议在安静状态下复测。",
                },
                "recommendations": ["保持规律作息。", "安排适合自身的日常活动。"],
                "action_plan": [f"第{i}天：记录睡眠并安排 15 分钟步行。" for i in range(1, 8)],
            },
            ensure_ascii=False,
        )

    monkeypatch.setattr(health_report_agent, "chat", fake_chat)
    assessment = assess_health_risk(
        HealthDataInput.model_validate(
            {
                "age": 22,
                "gender": Gender.MALE,
                "height": 175,
                "weight": 80,
                "blood_pressure": "145/90",
                "sleep_hours": 5,
                "exercise_frequency": 1,
            }
        )
    )

    report = asyncio.run(health_report_agent.generate_health_report(assessment))

    assert report.risk_level == RiskLevel.HIGH_ATTENTION
    assert len(report.key_risks) == 4
    assert len(report.action_plan) == 7
    assert "来源：user_input" in report.key_risks[0]
