"""Keep classroom competitor tests genuinely comparative and evidence-safe."""

import re


def _named_competitor(request: str) -> str | None:
    # A named product followed by a supplied capability is a stronger signal
    # than a generic mention of "other competitors".
    match = re.search(r"(?:^|[：，。；\s])([\u4e00-\u9fffA-Za-z0-9·]{2,16})(?:已经|已有|提供)", request)
    if match:
        return match.group(1)
    match = re.search(r"(?:对照|相比于|对比)([\u4e00-\u9fffA-Za-z0-9·]{2,16})", request)
    return match.group(1) if match else None


def needs_comparison_protocol(request: str) -> bool:
    return "对照测试" in request and bool(_named_competitor(request))


def ensure_comparison_protocol(reply: str, request: str) -> str:
    """Replace an incomplete task plan with a matched two-product protocol."""
    competitor = _named_competitor(request)
    if not competitor or "对照测试" not in request:
        return reply

    # Keep the model's project assessment and structured risk appendix. Only
    # replace its next-step plan, which often compares with a straw man.
    appendix_match = re.search(r"\n---\n\*\*⚠ 超图约束检测结果", reply)
    appendix = reply[appendix_match.start():] if appendix_match else ""
    body = reply[:appendix_match.start()] if appendix_match else reply
    # The model may invent a missing feature for the named competitor even
    # when the student explicitly warned against that assumption. Keep the
    # evidence-gap discussion, and let the matched protocol do the comparison.
    body = re.sub(
        r"(?ms)^#{1,4}\s*(?:项目对比|竞品对比|产品对比|与[^\n]{1,30}的对比)\s*\n.*?(?=^#{1,4}\s|\Z)",
        "",
        body,
    )
    task_match = re.search(
        r"(?m)^#{1,4}\s*(?:下一步[^\n]*|[^\n]*(?:对照测试|测试方案)[^\n]*)|^\*\*下一步任务",
        body,
    )
    if task_match:
        body = body[:task_match.start()].rstrip()

    protocol = f"""

### 与{competitor}的同条件课堂对照（方案，尚未执行）

目前没有证据证明用户会选择本项目。学生提供的{competitor}功能信息只作为待核验的竞品背景，不能假定它缺少某项功能。

**唯一下一步任务：** 写一页对照测试方案。用同一份标为 S（模拟）的虚构样本资料，让体验者分别在本项目和{competitor}完成相同任务：录入或查看资料、找到结果解释、找到下一步行动，并说明数据与使用边界。若某项在任一产品中不可用，记录“未找到/不适用”，不自行补写。

预先记录两边相同的观察指标：任务完成情况、耗时、操作步骤、对提示的正确理解、行动建议的清晰度和主观偏好。交换使用顺序，避免先后顺序影响。课堂内只使用虚构资料，不采集真实个人数据；真实参与者、人数与知情同意安排应由课程要求决定。结果未产生前，所有“更受欢迎/更有效”的判断都标记为 H（待验证）。
"""
    return body + protocol + appendix
