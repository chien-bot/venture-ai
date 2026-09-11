"""Course-level evidence-boundary enforcement for Agent outputs."""

from __future__ import annotations

import re


def enforce_course_boundary(text: str, request: str) -> str:
    """Keep course outputs honest when the model overstates evidence.

    This is intentionally a narrow post-processing layer: it preserves the
    model's analysis while making simulated inputs, absent sources, and future
    validation work explicit.
    """
    if not text:
        return text

    replacements = {
        "进行用户访谈": "完成一份课程内证据/假设表，并把真实访谈列为后续验证计划",
        "用户访谈、问卷调查": "公开资料核验、F/I/H/S 标注或后续真实验证计划",
        "至少10位目标用户": "课程内模拟情境或公开资料核验",
        "至少10位用户": "课程内模拟情境或公开资料核验",
        "至少10份真实用户访谈记录": "公开资料核验或明确标注的课程模拟材料",
    }
    for unsafe, safe in replacements.items():
        text = text.replace(unsafe, safe)

    # Models often phrase the same out-of-scope requirement in slightly
    # different ways.  Keep the concrete variants below explicit so normal
    # project advice is untouched while course deliverables remain feasible.
    phrase_replacements = (
        (
            r"请用具体的用户访谈或问卷数据来验证",
            "请先用课程内证据/假设表来标记待验证内容；真实访谈仅作为后续验证计划",
        ),
        (
            r"提交至少\s*\d+\s*位目标用户的访谈记录或问卷结果",
            "提交一份标有 F/I/H/S 的课程内证据/假设表，并说明后续验证计划",
        ),
        (
            r"收集至少\s*\d+\s*位目标用户的反馈",
            "整理课程内模拟情境或公开资料核验结果，并明确其证据等级",
        ),
        (
            r"通过问卷调查、访谈等方式获取真实用户反馈",
            "通过公开资料核验或明确标注的课程模拟材料补足证据，并把真实用户验证列为后续计划",
        ),
        (
            r"真实访谈列为后续验证计划或问卷调查",
            "真实访谈列为后续验证计划",
        ),
        (
            r"找到课程内模拟情境或公开资料核验，进行面对面或在线访谈，记录他们的回答。",
            "整理课程内模拟情境或公开资料核验结果，并为每项内容标明 F/I/H/S。",
        ),
        (
            r"提交访谈记录表和问卷结果，分析用户的真实需求和对现有平台的满意度。",
            "提交课程内证据/假设表，说明哪些结论仍待后续验证。",
        ),
        (
            r"实际用户需求的验证需要通过问卷调查、访谈等方法获取真实数据。",
            "当前用户需求仍是 H（假设）；请用课程内证据/假设表记录验证缺口，并将真实数据收集列入后续计划。",
        ),
        (
            r"建议团队尽快开展用户调研，获取真实数据，验证用户需求和市场潜力。",
            "建议团队先补充课程内证据/假设表，并将真实用户验证写入后续计划。",
        ),
    )
    for unsafe_pattern, safe in phrase_replacements:
        text = re.sub(unsafe_pattern, safe, text)

    notices: list[str] = []
    if any(token in request for token in ("课程模拟材料", "教师提供的模拟情境", "模拟用户")):
        notices.append("本次输入中的新增情境与模拟反馈均标记为 S（模拟），不能作为真实市场或用户证据。")
    if "没有提供任何真实来源" in request or "无来源" in request:
        notices.append("题干未提供来源的比例、支持和支付意愿均为 H（假设），不得写成已证实事实。")
    if "引用必须" in request and "http" not in text and "来源：" not in text:
        notices.append("本回复未提供可核验引用；示例只用于说明方法，不能作为外部事实依据。")
    if "DroneFarm" in text and "DroneFarm" not in request:
        notices.append("DroneFarm 仅为 S（模拟）教学示例，不代表已发生的调研、用户反馈或项目成果。")

    if notices:
        return "**证据边界：** " + " ".join(notices) + "\n\n" + text
    return text
