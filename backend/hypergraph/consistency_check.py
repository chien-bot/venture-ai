"""
hypergraph/consistency_check.py
────────────────────────────────────────────────────────────────
运行时超图路径校验器 V3

在每轮对话后检测用户描述的项目是否触发 H1-H15 约束规则。
返回触发的规则列表，供 critic_node 或 coach_node 使用。

V2 改进：
- 集成 EvidenceTracer：用证据分类（CLAIM/DATA/QUOTE/COMMIT）替代粗糙的强弱词判断
- 逐轮分析：按轮次窗口检测，区分"早期提过但后来推翻"的情况
- H规则→R维度映射：用 EvidenceTracer 的 rubric 标签精确判断某个维度是否有数据支撑
- 置信度模型细化：5 因子加权（话题覆盖、证据质量、证据数量、时效衰减、回避信号）

V3 改进：
- 增量分析：缓存每个 session 的 per-rule 中间结果，只扫描新消息
- topic_hits 累计而非每次重算 full_text
- 复杂度从 O(turns × rules × keywords) 降至 O(new_msgs × rules × keywords)
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

# ── H 规则 → Rubric 维度映射 ──────────────────────────────────
# 用于从 EvidenceTracer 查询某条 H 规则对应维度是否有数据支撑
_H_TO_RUBRIC: dict[str, list[str]] = {
    "H1":  ["R1_pain_point", "R3_solution"],
    "H2":  ["R4_business_model"],
    "H3":  ["R4_business_model", "R6_finance"],
    "H4":  ["R5_market"],
    "H5":  ["R1_pain_point", "R2_user_evidence"],
    "H6":  ["R5_market", "R7_innovation"],
    "H7":  ["R7_innovation"],
    "H8":  ["R6_finance"],
    "H9":  ["R4_business_model"],
    "H10": ["R8_execution"],
    "H11": ["R4_business_model"],
    "H12": ["R3_solution", "R8_execution"],
    "H13": ["R2_user_evidence"],
    "H14": ["R9_pitch"],
    "H15": ["R2_user_evidence"],
}

# ── Evasion / weak phrases (used for penalty factor) ──────────
_WEAK_PHRASES: list[str] = [
    "应该", "可能", "大概", "估计", "打算",
    "没有", "尚未", "还没", "暂时", "之后再", "后续",
    "不确定", "不清楚", "不知道",
]


class TriggeredRule(NamedTuple):
    rule_id: str
    rule_type: str
    severity: str
    trigger_message: str
    fix_task: str
    confidence: float  # 0.0 - 1.0
    evidence_summary: str  # V2: 证据摘要


# ── V3: Session-level incremental cache ──────────────────────

class _RuleCache:
    """Per-rule cached topic hits, accumulated across turns."""
    __slots__ = ("topic_hits",)

    def __init__(self):
        self.topic_hits: dict[str, int] = {}  # rule_id → cumulative topic hit count


class _SessionCache:
    """Per-session incremental analysis state."""
    __slots__ = ("processed_user_count", "rule_cache", "per_turn_texts")

    def __init__(self):
        self.processed_user_count: int = 0  # how many user messages already scanned
        self.rule_cache = _RuleCache()
        self.per_turn_texts: list[str] = []  # user message texts in order


_session_caches: dict[str, _SessionCache] = {}


def _get_session_cache(session_id: str) -> _SessionCache:
    if session_id not in _session_caches:
        _session_caches[session_id] = _SessionCache()
    return _session_caches[session_id]


def _compute_confidence(
    topic_hits: int,
    total_signals: int,
    data_count: int,
    claim_count: int,
    weak_phrase_count: int,
    recency_ratio: float,
) -> float:
    """
    5 因子加权置信度模型。

    返回值：0.0 ~ 1.0，越高越有把握该规则被违反（= 缺乏证据）。

    因子含义：
    1. topic_coverage (0~0.25): 话题覆盖度 — 越多关键词命中，越说明这个维度被讨论过
    2. evidence_quality (0~0.35): 证据质量 — DATA/QUOTE 多则置信低（有证据），CLAIM 多则置信高
    3. evidence_quantity (0~0.15): 证据数量 — 完全没有证据 → 高置信
    4. recency (0~0.10): 时效性 — 最近的消息有提到 → 降低置信（说明在积极处理）
    5. evasion (0~0.15): 回避信号 — 弱化词越多 → 置信越高
    """
    # Factor 1: topic coverage — more hits = topic is being discussed
    coverage = min(topic_hits / max(total_signals, 1), 1.0)
    f_topic = coverage * 0.25

    # Factor 2: evidence quality — key factor
    total_ev = data_count + claim_count
    if total_ev == 0:
        # 话题提到了但完全没有证据 → 高置信（规则违反）
        f_quality = 0.30
    else:
        data_ratio = data_count / total_ev
        # data_ratio 高 → 有数据支撑 → 低置信
        f_quality = (1.0 - data_ratio) * 0.35

    # Factor 3: evidence quantity
    if total_ev == 0:
        f_quantity = 0.15
    elif total_ev <= 1:
        f_quantity = 0.10
    elif total_ev <= 3:
        f_quantity = 0.05
    else:
        f_quantity = 0.0

    # Factor 4: recency — recent discussion lowers confidence
    f_recency = (1.0 - recency_ratio) * 0.10

    # Factor 5: evasion — weak phrases boost confidence
    evasion_score = min(weak_phrase_count / 3.0, 1.0)
    f_evasion = evasion_score * 0.15

    confidence = f_topic + f_quality + f_quantity + f_recency + f_evasion
    return round(min(max(confidence, 0.0), 1.0), 3)


def check_conversation(
    messages: list[dict],
    current_message: str = "",
    session_id: str = "",
) -> list[TriggeredRule]:
    """
    分析对话历史，检测触发了哪些 H1-H15 约束规则。

    V3: 增量分析 — 只扫描新消息计算 topic_hits，
    证据查询委托给 EvidenceTracer（已增量），
    recency / evasion 只看最近 3 轮。

    Parameters
    ----------
    messages : 完整对话历史（role + content）
    current_message : 本轮用户消息
    session_id : 会话 ID（用于 EvidenceTracer 和增量缓存）

    Returns
    -------
    触发规则列表（按 severity 排序：high > medium > low）
    """
    from services.evidence_tracer import refresh_tracer

    # ── 准备证据分析（复用 session 级缓存，增量解析） ──
    all_messages = list(messages)
    if current_message:
        all_messages.append({"role": "user", "content": current_message})

    tracer = refresh_tracer(session_id, all_messages)

    # ── 提取用户消息文本 ──
    user_texts = [m["content"] for m in all_messages if m.get("role") == "user"]
    total_user_turns = len(user_texts)

    # ── V3: 增量 topic_hits 计算 ──
    cache = _get_session_cache(session_id)

    # Detect reset (fewer user messages than cached → new session)
    if total_user_turns < cache.processed_user_count:
        cache.__init__()  # type: ignore[misc]

    # Only scan user messages beyond what we've already processed
    new_texts = user_texts[cache.processed_user_count:]

    if new_texts:
        # Incrementally accumulate topic_hits for each rule
        new_combined = " ".join(new_texts)
        for rid, signals in _TRIGGER_SIGNALS.items():
            new_hits = sum(1 for s in signals if s in new_combined)
            cache.rule_cache.topic_hits[rid] = (
                cache.rule_cache.topic_hits.get(rid, 0) + new_hits
            )
        cache.per_turn_texts.extend(new_texts)
        cache.processed_user_count = total_user_turns

    # ── 最近 3 轮窗口（recency + evasion，每次重算，成本极低） ──
    recent_window = 3
    recent_texts = cache.per_turn_texts[-recent_window:] if cache.per_turn_texts else []
    recent_text = " ".join(recent_texts)

    # ── 逐规则评估 ──
    triggered: list[TriggeredRule] = []

    for rule in _RAW_RULES:
        rid = rule["rule_id"]
        signals = _TRIGGER_SIGNALS.get(rid, [])

        # ── 话题覆盖检测（从缓存读取累计值） ──
        topic_hits = cache.rule_cache.topic_hits.get(rid, 0)
        if topic_hits == 0:
            continue  # 话题完全未被提及，跳过

        # ── 时效性：最近轮次是否还在讨论这个话题 ──
        recent_hits = sum(1 for s in signals if s in recent_text)
        recency_ratio = min(recent_hits / max(topic_hits, 1), 1.0)

        # ── 证据质量：通过 rubric 标签查询（EvidenceTracer 已增量） ──
        rubric_keys = _H_TO_RUBRIC.get(rid, [])
        data_count = 0
        claim_count = 0
        evidence_texts: list[str] = []

        for rk in rubric_keys:
            for ev in tracer.get_by_rubric(rk):
                if ev.ev_type in ("DATA", "QUOTE"):
                    data_count += 1
                    evidence_texts.append(f"✓ {ev.text[:40]}（第{ev.turn}轮·{ev.ev_type}）")
                elif ev.ev_type == "CLAIM":
                    claim_count += 1
                    evidence_texts.append(f"? {ev.text[:40]}（第{ev.turn}轮·CLAIM）")

        # ── 回避词检测（只在最近轮次中检测）──
        weak_phrase_count = sum(1 for w in _WEAK_PHRASES if w in recent_text)

        # ── 计算置信度 ──
        confidence = _compute_confidence(
            topic_hits=topic_hits,
            total_signals=len(signals),
            data_count=data_count,
            claim_count=claim_count,
            weak_phrase_count=weak_phrase_count,
            recency_ratio=recency_ratio,
        )

        # 阈值：置信度 >= 0.30 才触发
        if confidence >= 0.30:
            # 构建证据摘要
            if evidence_texts:
                summary = "; ".join(evidence_texts[:3])
            elif topic_hits > 0:
                summary = "话题被提及但无具体证据"
            else:
                summary = ""

            triggered.append(TriggeredRule(
                rule_id=rid,
                rule_type=rule["type"],
                severity=rule["severity"],
                trigger_message=rule["trigger_message"],
                fix_task=rule["fix_task"],
                confidence=confidence,
                evidence_summary=summary,
            ))

    # Sort: high > medium > low, then by confidence desc
    _order = {"high": 0, "medium": 1, "low": 2}
    triggered.sort(key=lambda r: (_order.get(r.severity, 3), -r.confidence))
    return triggered


def format_violations(rules: list[TriggeredRule]) -> str:
    """
    将触发的规则格式化为可读的诊断文本，供 AI 回复中引用。
    V2: 增加置信度和证据摘要显示。
    """
    if not rules:
        return ""
    lines = ["**⚠ 超图约束检测结果：**\n"]
    severity_emoji = {"high": "🔴", "medium": "🟡", "low": "🔵"}
    conf_label = lambda c: "高" if c >= 0.65 else ("中" if c >= 0.45 else "低")
    for r in rules:
        emoji = severity_emoji.get(r.severity, "⚪")
        lines.append(
            f"{emoji} **[{r.rule_id}] {r.rule_type}** （置信度：{conf_label(r.confidence)}）\n"
            f"   触发信号：{r.trigger_message}\n"
            f"   建议修复：{r.fix_task}"
        )
        if r.evidence_summary:
            lines.append(f"   证据状态：{r.evidence_summary}")
        lines.append("")
    return "\n".join(lines)


def get_high_risk_rules(rules: list[TriggeredRule]) -> list[TriggeredRule]:
    """仅返回 high severity 规则。"""
    return [r for r in rules if r.severity == "high"]


def rules_to_diagnosis(rules: list[TriggeredRule]) -> list[str]:
    """
    将触发规则转换为 diagnosis 字符串列表，与现有 AgentState.diagnosis 兼容。
    V2: 增加置信度信息。
    """
    conf_label = lambda c: "高" if c >= 0.65 else ("中" if c >= 0.45 else "低")
    return [
        f"[{r.rule_id}] {r.rule_type}（置信度{conf_label(r.confidence)}）：{r.trigger_message}"
        for r in rules
    ]
