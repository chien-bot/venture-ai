"""
hypergraph/consistency_check.py
────────────────────────────────────────────────────────────────
运行时超图路径校验器

在每轮对话后检测用户描述的项目是否触发 H1-H15 约束规则。
返回触发的规则列表，供 critic_node 或 coach_node 使用。
"""
from __future__ import annotations
import json
import re
from pathlib import Path
from typing import NamedTuple

# ── Load constraint rules from JSON ──────────────────────────
_RULES_PATH = Path(__file__).parent.parent / "data" / "rubric" / "constraint_rules.json"
with open(_RULES_PATH, encoding="utf-8") as f:
    _RAW_RULES: list[dict] = json.load(f)

# ── Trigger keyword map: rule_id → list of signal phrases ────
# Each entry maps a rule to keyword signals that, when found in
# conversation history, indicate the rule MAY be triggered.
_TRIGGER_SIGNALS: dict[str, list[str]] = {
    "H1": ["目标客户", "用户群", "客户群", "价值主张", "痛点", "用户需求"],
    "H2": ["渠道", "触达", "获客渠道", "推广", "分发"],
    "H3": ["定价", "收费", "价格", "支付意愿", "付费", "多少钱"],
    "H4": ["TAM", "SAM", "SOM", "市场规模", "市场大小", "亿", "万亿"],
    "H5": ["用户访谈", "调研", "问卷", "一手数据", "用户反馈", "痛点验证"],
    "H6": ["竞争对手", "竞品", "对比", "差异化", "竞争分析"],
    "H7": ["创新", "独特", "差异", "专利", "技术壁垒", "护城河"],
    "H8": ["LTV", "CAC", "获客成本", "终身价值", "单位经济", "盈利"],
    "H9": ["增长", "用户增长", "扩张", "规模化", "增长策略"],
    "H10": ["里程碑", "时间节点", "计划", "交付", "阶段"],
    "H11": ["数据隐私", "合规", "监管", "许可证", "资质", "伦理"],
    "H12": ["技术", "开发", "算法", "团队能力", "资源", "人手"],
    "H13": ["实验", "A/B测试", "验证", "测试", "对照组", "样本"],
    "H14": ["路演", "PPT", "演示", "Pitch", "投资人", "故事"],
    "H15": ["证据", "数据支撑", "材料", "来源", "引用"],
}

# ── Weak evidence signals: phrases suggesting MISSING evidence ──
_WEAK_EVIDENCE: list[str] = [
    "应该", "可能", "大概", "估计", "打算", "计划",
    "没有", "尚未", "还没", "暂时", "之后再", "后续",
    "不确定", "不清楚", "不知道",
]

# ── Strong evidence signals: phrases suggesting evidence EXISTS ──
_STRONG_EVIDENCE: list[str] = [
    "访谈了", "调研了", "测试了", "数据显示", "根据",
    "已经", "完成了", "验证了", "证明了", "统计",
    "用户说", "反馈是", "结果是",
]


class TriggeredRule(NamedTuple):
    rule_id: str
    rule_type: str
    severity: str
    trigger_message: str
    fix_task: str
    confidence: float  # 0.0 - 1.0


def check_conversation(
    messages: list[dict],
    current_message: str = "",
) -> list[TriggeredRule]:
    """
    分析对话历史，检测触发了哪些 H1-H15 约束规则。

    Parameters
    ----------
    messages : 完整对话历史（role + content）
    current_message : 本轮用户消息

    Returns
    -------
    触发规则列表（按 severity 排序：high > medium > low）
    """
    # 合并所有用户消息为分析文本
    user_text = " ".join(
        m["content"] for m in messages if m.get("role") == "user"
    )
    if current_message:
        user_text += " " + current_message

    triggered: list[TriggeredRule] = []

    for rule in _RAW_RULES:
        rid = rule["rule_id"]
        signals = _TRIGGER_SIGNALS.get(rid, [])

        # Count how many topic signals appear
        topic_hits = sum(1 for s in signals if s in user_text)
        if topic_hits == 0:
            continue

        # Check for weak evidence (increases trigger probability)
        weak_hits = sum(1 for w in _WEAK_EVIDENCE if w in user_text)
        strong_hits = sum(1 for s in _STRONG_EVIDENCE if s in user_text)

        # Confidence heuristic:
        # - topic mentioned + strong evidence   → low confidence (user has data, probably OK)
        # - topic mentioned + weak evidence     → high confidence (rule fires)
        # - topic mentioned + no indicator      → medium confidence
        # Topic hit count boosts confidence beyond the base.
        hit_bonus = min(topic_hits * 0.15, 0.45)   # max +0.45 from multiple hits

        if strong_hits > weak_hits:
            confidence = 0.15 + hit_bonus
        elif weak_hits > 0:
            confidence = 0.55 + hit_bonus
        else:
            confidence = 0.35 + hit_bonus

        if confidence >= 0.35:
            triggered.append(TriggeredRule(
                rule_id=rid,
                rule_type=rule["type"],
                severity=rule["severity"],
                trigger_message=rule["trigger_message"],
                fix_task=rule["fix_task"],
                confidence=round(confidence, 2),
            ))

    # Sort: high > medium > low, then by confidence desc
    _order = {"high": 0, "medium": 1, "low": 2}
    triggered.sort(key=lambda r: (_order.get(r.severity, 3), -r.confidence))
    return triggered


def format_violations(rules: list[TriggeredRule]) -> str:
    """
    将触发的规则格式化为可读的诊断文本，供 AI 回复中引用。
    """
    if not rules:
        return ""
    lines = ["**⚠ 超图约束检测结果：**\n"]
    severity_emoji = {"high": "🔴", "medium": "🟡", "low": "🔵"}
    for r in rules:
        emoji = severity_emoji.get(r.severity, "⚪")
        lines.append(
            f"{emoji} **[{r.rule_id}] {r.rule_type}**\n"
            f"   触发信号：{r.trigger_message}\n"
            f"   建议修复：{r.fix_task}\n"
        )
    return "\n".join(lines)


def get_high_risk_rules(rules: list[TriggeredRule]) -> list[TriggeredRule]:
    """仅返回 high severity 规则。"""
    return [r for r in rules if r.severity == "high"]


def rules_to_diagnosis(rules: list[TriggeredRule]) -> list[str]:
    """
    将触发规则转换为 diagnosis 字符串列表，与现有 AgentState.diagnosis 兼容。
    """
    return [
        f"[{r.rule_id}] {r.rule_type}：{r.trigger_message}"
        for r in rules
    ]
