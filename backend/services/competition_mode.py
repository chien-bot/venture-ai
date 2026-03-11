"""
services/competition_mode.py
────────────────────────────────────────────────────────────────
竞赛倒计时模式 — 根据距比赛天数切换 Coach 策略
"""
from __future__ import annotations
from datetime import date


def get_countdown_context(competition_date_str: str | None) -> str:
    """
    Returns a system prompt injection block based on days remaining.
    Returns empty string if no competition date is set.
    """
    if not competition_date_str:
        return ""
    try:
        comp_date = date.fromisoformat(competition_date_str)
        days_left = (comp_date - date.today()).days
    except (ValueError, TypeError):
        return ""

    if days_left < 0:
        return ""  # competition has passed

    if days_left <= 7:
        return (
            f"[竞赛倒计时模式: PITCH SPRINT ⚡] 距竞赛仅剩 {days_left} 天。"
            "本轮请聚焦路演表达和现有材料的打磨，不再深究未验证假设。"
            "帮学生打磨开场60秒陈述、数据引用的精准度、和回答评委问题的策略。"
            "每轮回复必须包含1个具体可执行的路演改进建议。"
        )
    elif days_left <= 30:
        return (
            f"[竞赛倒计时模式: ACCELERATE 🚀] 距竞赛 {days_left} 天。"
            "优先处理商业模式和证据链的关键漏洞。"
            "每轮追问必须直指最高风险维度，不接受'后续再完善'类答复。"
            "建议学生本周完成至少一项可量化的验证动作（访谈/原型测试/市场调研）。"
        )
    else:
        return (
            f"[竞赛倒计时模式: EXPLORE 🌱] 距竞赛 {days_left} 天，时间充裕。"
            "深度探索，鼓励学生充分发散思维和系统验证，建立扎实的假设-验证循环。"
        )
