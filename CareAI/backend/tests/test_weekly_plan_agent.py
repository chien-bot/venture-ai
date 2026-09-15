import asyncio
import json

from app.schemas import RiskLevel, TrendInsight, WeeklyReview
from app.services import weekly_plan_agent


def test_weekly_plan_agent_only_returns_lifestyle_draft(monkeypatch) -> None:
    async def fake_chat(messages, temperature=0.2) -> str:
        assert temperature == 0.2
        return json.dumps({
            "summary": "本周先保持低门槛行动，再观察记录变化。",
            "adjustment_reason": "完成率偏低，因此将任务拆分为更容易坚持的小步骤。",
            "action_plan": [f"第{day}天：晚饭后步行十分钟并记录完成情况。" for day in range(1, 8)],
        }, ensure_ascii=False)

    monkeypatch.setattr(weekly_plan_agent, "chat", fake_chat)
    plan = asyncio.run(weekly_plan_agent.generate_weekly_plan(
        "建立运动习惯",
        WeeklyReview(user_id="demo-user", completed_tasks=1, total_tasks=7, completion_rate=14, summary="完成率较低。"),
        [TrendInsight(category="exercise", level=RiskLevel.ATTENTION, title="运动偏少", explanation="最近记录偏少。", next_step="从低强度开始。", data_points=3)],
    ))
    assert len(plan.action_plan) == 7
    assert "诊断" not in plan.summary
