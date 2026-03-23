"""
agents/adaptive_questioning.py
────────────────────────────────────────────────────────────────
苏格拉底追问策略库 V2（Adaptive Questioning Engine with Memory）

核心逻辑：
1. 根据当前 scores 找出最薄弱维度
2. DimTracker 跟踪每个维度的历史状态：连续薄弱轮次、已问级别、证据变化
3. 集成 EvidenceTracer 区分 CLAIM vs DATA，避免对已有充分证据的维度重复追问
4. 结果注入 coach system prompt 作为动态指令

V2 改进：
- DimTracker：会话级对话记忆，跟踪每个维度的薄弱持续轮次和已追问级别
- 证据感知：集成 EvidenceTracer，根据 DATA/CLAIM 比例调整追问策略
- 智能升级：自动从 L1→L2→L3，不重复同级追问
- 长期回避检测：跨全部对话历史检测回避模式，不受窗口限制
"""
from __future__ import annotations

from dataclasses import dataclass, field

# ─────────────────────────────────────────────────────────────
# 追问链定义
# ─────────────────────────────────────────────────────────────

@dataclass
class QuestionChain:
    dim: str          # 维度 id
    label: str        # 维度中文名
    signals: list[str]  # 这个维度"已被提及"的关键词
    l1: str           # 轻度追问
    l2: str           # 中度追问（学生回答仍薄弱）
    l3: str           # 强力挑战（连续回避）
    evasion_tip: str  # 系统提示：学生正在回避时追加的指令
    # V2: 对应的 rubric 标签，用于从 EvidenceTracer 查询证据质量
    rubric_keys: list[str] = field(default_factory=list)


QUESTION_CHAINS: list[QuestionChain] = [
    QuestionChain(
        dim="empathy",
        label="痛点发现",
        signals=["痛点", "用户", "访谈", "调研", "问题", "需求", "不方便", "困难", "场景"],
        l1="你提到了这个问题，但我想更具体地了解：**你采访过真实用户吗？他们用什么词描述这个痛苦？**",
        l2="你说的这个痛点，我想反问一句：**用户现在是怎么解决这个问题的？为什么现有方案不够好？**",
        l3="我们已经聊了几轮，但我还没看到任何一手用户证据。**请告诉我：你最近一次和目标用户面对面交流是什么时候？他们说了什么？**",
        evasion_tip="[追问指令] 学生连续多轮未提供用户访谈证据，请在本轮追问用户一手证据，不要接受泛化描述。",
        rubric_keys=["R1_pain_point", "R2_user_evidence"],
    ),
    QuestionChain(
        dim="ideation",
        label="方案策划",
        signals=["方案", "产品", "功能", "设计", "原型", "MVP", "技术", "实现", "差异"],
        l1="你的方案思路有了，但我想知道：**和市面上已有的解决方案相比，你最核心的差异化是什么？**",
        l2="我听到了你的方案，现在做个压力测试：**如果微信/阿里明天发布一个免费功能解决同样的问题，你的产品还有价值吗？**",
        l3="我们讨论方案已经好几轮了，但还没有触及护城河。**你的方案中，有没有竞争对手6个月内无法复制的东西？**",
        evasion_tip="[追问指令] 学生多次描述方案但回避竞品分析，本轮请直接追问差异化和护城河，不要跳过。",
        rubric_keys=["R3_solution", "R7_innovation"],
    ),
    QuestionChain(
        dim="business",
        label="商业建模",
        signals=["商业模式", "盈利", "收费", "付费", "价格", "收入", "定价", "变现", "订阅", "客单价"],
        l1="你提到了项目方向，但我还不清楚：**谁来付钱？付多少？为什么愿意付这个价格而不是免费替代品？**",
        l2="让我们具体一点：**假设你有100个用户，每人每月付X元，你的成本是多少，利润是多少？这个数字能养活团队吗？**",
        l3="我们聊了很多，但你的商业模式还很模糊。**请现在给我一个最简单的数字：你的第一年目标收入是多少，这基于什么假设？**",
        evasion_tip="[追问指令] 学生回避商业模式讨论，请在本轮强制引导到具体定价和单位经济模型，要求给出数字。",
        rubric_keys=["R4_business_model", "R6_finance"],
    ),
    QuestionChain(
        dim="execution",
        label="资源杠杆",
        signals=["团队", "资源", "合作", "执行", "计划", "里程碑", "MVP", "时间", "人手", "预算"],
        l1="想法很好，但执行是关键：**你们团队现在有几个人？每个人负责什么？你最担心哪个环节卡住？**",
        l2="你提到了计划，我想问更实际的：**在没有外部融资的情况下，你能用学校现有的资源（实验室/导师/政府补贴）走多远？**",
        l3="我们一直在讨论想法，但还没谈执行路径。**请给我一个3个月的里程碑计划：第1个月做什么，第2个月验证什么，第3个月交付什么？**",
        evasion_tip="[追问指令] 学生回避执行细节，请追问具体的里程碑和资源盘点，不接受'后续再说'类回答。",
        rubric_keys=["R8_execution"],
    ),
    QuestionChain(
        dim="pitching",
        label="路演表达",
        signals=["路演", "演示", "pitch", "PPT", "投资人", "故事", "表达", "逻辑", "叙述"],
        l1="你的项目逻辑是否能被30秒内解释清楚？**试试用一句话告诉我：你为谁、解决了什么问题、用什么方式、凭什么比现有方案好。**",
        l2="假设你在电梯里遇到了一个投资人，只有60秒：**你会说什么？请现在就说，我来帮你找逻辑漏洞。**",
        l3="路演是你向外界证明价值的关键时刻。**你的Pitch有几页PPT？每页的核心信息是什么？你有没有演练过？最担心评委问哪个问题？**",
        evasion_tip="[追问指令] 学生路演逻辑薄弱，请引导其做一次简短的口头路演，并指出逻辑断层。",
        rubric_keys=["R9_pitch"],
    ),
]

# 快速查询 dict
_CHAINS_BY_DIM: dict[str, QuestionChain] = {c.dim: c for c in QUESTION_CHAINS}


# ─────────────────────────────────────────────────────────────
# V2: DimTracker — 维度级对话记忆
# ─────────────────────────────────────────────────────────────

@dataclass
class DimState:
    """单个维度的追踪状态。"""
    consecutive_weak: int = 0       # 连续薄弱轮次
    last_asked_level: int = 0       # 上次追问级别（0=未追问过）
    total_asks: int = 0             # 总追问次数
    data_count: int = 0             # DATA/QUOTE 类证据数量
    claim_count: int = 0            # CLAIM 类证据数量
    last_score: float = 0.0         # 上次得分
    score_improved: bool = False    # 本轮得分是否有改善


class DimTracker:
    """
    会话级维度追踪器。跟踪每个维度的薄弱持续时间、已追问级别、证据变化。
    每轮调用 update() 后，get_question_level() 返回基于历史的智能追问级别。
    """

    def __init__(self):
        self._dims: dict[str, DimState] = {
            dim: DimState() for dim in DIM_LABELS
        }

    def update(
        self,
        scores: dict | None,
        messages: list[dict],
        session_id: str = "",
    ) -> None:
        """
        每轮对话后调用，更新所有维度的状态。
        集成 EvidenceTracer 获取证据质量信息。
        """
        if not scores:
            return

        # 获取证据信息（复用 session 级缓存的 tracer，增量解析）
        evidence_by_rubric: dict[str, dict] = {}  # rubric_key → {data: int, claim: int}
        try:
            from services.evidence_tracer import refresh_tracer
            tracer = refresh_tracer(session_id, messages)
            for chain in QUESTION_CHAINS:
                for rk in chain.rubric_keys:
                    if rk not in evidence_by_rubric:
                        evs = tracer.get_by_rubric(rk)
                        evidence_by_rubric[rk] = {
                            "data": sum(1 for e in evs if e.ev_type in ("DATA", "QUOTE")),
                            "claim": sum(1 for e in evs if e.ev_type == "CLAIM"),
                        }
        except Exception:
            pass

        # 更新每个维度
        for dim, ds in self._dims.items():
            score = scores.get(dim, 0)
            chain = _CHAINS_BY_DIM.get(dim)

            # 得分改善检测
            ds.score_improved = score > ds.last_score + 0.5
            prev_score = ds.last_score
            ds.last_score = score

            # 连续薄弱计数
            if score < SCORE_THRESHOLDS["weak"]:
                ds.consecutive_weak += 1
            else:
                ds.consecutive_weak = 0

            # 证据质量汇总
            if chain:
                total_data = 0
                total_claim = 0
                for rk in chain.rubric_keys:
                    info = evidence_by_rubric.get(rk, {})
                    total_data += info.get("data", 0)
                    total_claim += info.get("claim", 0)
                ds.data_count = total_data
                ds.claim_count = total_claim

    def get_state(self, dim: str) -> DimState:
        return self._dims.get(dim, DimState())

    def record_ask(self, dim: str, level: int) -> None:
        """记录对某维度进行了追问。"""
        ds = self._dims.get(dim)
        if ds:
            ds.last_asked_level = level
            ds.total_asks += 1

    def get_question_level(self, dim: str) -> int:
        """
        基于历史追踪的智能追问级别。

        升级逻辑：
        - 首次薄弱 → L1
        - 已问过 L1 且得分未改善 → L2
        - 已问过 L2 或连续薄弱 ≥ 3 轮 → L3
        - 得分有改善 → 保持或降级（不重复施压）
        - 有充足 DATA 证据 → 降一级（已有数据，不需要强追问）
        """
        ds = self._dims.get(dim, DimState())

        # 基础级别：根据连续薄弱轮次
        if ds.consecutive_weak >= 3:
            base = 3
        elif ds.consecutive_weak >= 2:
            base = 2
        else:
            base = 1

        # 升级：上次已经问过该级别且得分未改善 → 升一级
        if ds.last_asked_level >= base and not ds.score_improved:
            base = min(ds.last_asked_level + 1, 3)

        # 降级：得分有改善 → 不升级，保持当前级别
        if ds.score_improved and base > 1:
            base = max(base - 1, 1)

        # 降级：有充足 DATA 证据（≥2条） → 降一级
        if ds.data_count >= 2 and base > 1:
            base = max(base - 1, 1)

        return base


# ── 会话级 DimTracker 缓存 ──────────────────────────────────
_trackers: dict[str, DimTracker] = {}


def get_tracker(session_id: str) -> DimTracker:
    """获取或创建会话级 DimTracker。"""
    if session_id not in _trackers:
        _trackers[session_id] = DimTracker()
    return _trackers[session_id]


# ─────────────────────────────────────────────────────────────
# 回避检测 V2
# ─────────────────────────────────────────────────────────────

EVASION_WEAK_WORDS = [
    "应该", "可能", "大概", "估计", "打算", "以后", "后续",
    "不确定", "不清楚", "还没想好", "之后再说", "先不管",
    "不知道", "说不好", "暂时", "再看看",
]


def detect_evasion(
    messages: list[dict],
    dim: str,
    window: int = 4,
    session_id: str = "",
) -> bool:
    """
    V2 回避检测：结合短期窗口 + 长期模式 + 证据质量。

    判定回避的条件（需同时满足）：
    1. 最近 window 轮中没有提及该维度的信号词
    2. 最近 window 轮中出现了回避性词汇
    3. 该维度没有 DATA/QUOTE 类证据（有数据就不算回避）
    """
    chain = _CHAINS_BY_DIM.get(dim)
    if not chain:
        return False

    user_msgs = [m["content"] for m in messages if m.get("role") == "user"]
    recent = user_msgs[-window:] if len(user_msgs) >= window else user_msgs
    if not recent:
        return False

    combined = " ".join(recent)
    has_signal = any(kw in combined for kw in chain.signals)
    has_evasion = any(w in combined for w in EVASION_WEAK_WORDS)

    # 条件 1+2：无信号 AND 有回避词
    if has_signal or not has_evasion:
        return False

    # 条件 3：检查是否有 DATA 证据（有数据不算回避）
    if session_id:
        tracker = get_tracker(session_id)
        ds = tracker.get_state(dim)
        if ds.data_count >= 1:
            return False

    return True


# ─────────────────────────────────────────────────────────────
# 薄弱维度分析
# ─────────────────────────────────────────────────────────────

SCORE_THRESHOLDS = {
    "weak": 4.0,      # < 4 = 薄弱
    "medium": 6.5,    # 4-6.5 = 中等
}

DIM_LABELS = {
    "empathy": "痛点发现",
    "ideation": "方案策划",
    "business": "商业建模",
    "execution": "资源杠杆",
    "pitching": "路演表达",
}


def get_weak_dims(scores: dict | None, threshold: float = SCORE_THRESHOLDS["weak"]) -> list[str]:
    """返回得分低于阈值的维度列表，按得分升序排列（最弱的在前）。"""
    if not scores:
        return []
    weak = [(dim, scores.get(dim, 0)) for dim in DIM_LABELS if scores.get(dim, 0) < threshold]
    return [dim for dim, _ in sorted(weak, key=lambda x: x[1])]


# ─────────────────────────────────────────────────────────────
# V1 兼容：保留 get_question_level 函数签名
# ─────────────────────────────────────────────────────────────

def get_question_level(scores: dict | None, dim: str, round_num: int) -> int:
    """
    V1 兼容接口。优先使用 DimTracker，无 tracker 时 fallback 到简单逻辑。
    """
    # fallback: 简单逻辑（无 tracker 时）
    score = (scores or {}).get(dim, 0)
    if score < 2.0:
        return 3
    if score < 4.0 and round_num >= 4:
        return 2
    return 1


# ─────────────────────────────────────────────────────────────
# 主入口 V2：生成追问上下文块
# ─────────────────────────────────────────────────────────────

def build_questioning_context(
    scores: dict | None,
    messages: list[dict],
    current_message: str,
    session_id: str = "",
) -> str:
    """
    V2: 分析当前状态 + 对话记忆，返回注入 system prompt 的动态追问指令块。

    新增功能：
    - 利用 DimTracker 记忆追问历史，避免重复同级追问
    - 注入证据状态摘要（"你已经给了N条数据，但还缺..."）
    - 基于连续薄弱轮次自动升级追问强度
    """
    if not scores:
        return ""

    round_num = len([m for m in messages if m.get("role") == "user"])
    weak_dims = get_weak_dims(scores)

    if not weak_dims:
        return ""

    # 获取或创建 tracker
    tracker = get_tracker(session_id) if session_id else DimTracker()

    # 每轮更新 tracker 状态
    all_messages = list(messages)
    if current_message:
        all_messages.append({"role": "user", "content": current_message})
    tracker.update(scores, all_messages, session_id)

    lines: list[str] = ["[动态追问策略 - 本轮重点]"]

    # 最多关注最薄弱的 2 个维度
    for dim in weak_dims[:2]:
        chain = _CHAINS_BY_DIM.get(dim)
        if not chain:
            continue

        ds = tracker.get_state(dim)

        # 使用 tracker 的智能级别
        level = tracker.get_question_level(dim)
        question = {1: chain.l1, 2: chain.l2, 3: chain.l3}[level]
        is_evading = detect_evasion(messages, dim, session_id=session_id)

        # 构建状态摘要
        status_parts = [f"当前得分 {scores.get(dim, 0):.1f}/10"]
        if ds.consecutive_weak > 1:
            status_parts.append(f"连续{ds.consecutive_weak}轮薄弱")
        if ds.score_improved:
            status_parts.append("本轮有改善↑")
        status_parts.append(f"追问级别 L{level}")
        status_str = "，".join(status_parts)

        lines.append(f"\n▶ {chain.label}（{status_str}）")
        lines.append(f"  推荐追问：{question}")

        # 证据状态摘要
        if ds.data_count > 0 or ds.claim_count > 0:
            ev_parts = []
            if ds.data_count > 0:
                ev_parts.append(f"{ds.data_count}条数据证据")
            if ds.claim_count > 0:
                ev_parts.append(f"{ds.claim_count}条未验证主张")
            lines.append(f"  📊 证据状态：{' + '.join(ev_parts)}")
            if ds.claim_count > ds.data_count:
                lines.append(f"  💡 策略提示：学生有主张但缺数据支撑，追问时要求给出具体数字或来源。")
        else:
            lines.append(f"  📊 证据状态：尚无任何证据")

        if is_evading:
            lines.append(f"  ⚠️ 回避检测：{chain.evasion_tip}")

        # 记录本次追问
        tracker.record_ask(dim, level)

    # 特殊检测：学生是否声称"没有竞争对手"
    no_competitor_phrases = ["没有竞争对手", "没有对手", "唯一", "全球第一", "没人做过", "市场空白"]
    if any(phrase in current_message for phrase in no_competitor_phrases):
        lines.append("\n⚠️ 竞品回避触发：学生声称无竞争对手。")
        lines.append("  [指令] 必须触发竞品追问链：")
        lines.append("  → 追问：'真的没有吗？用户现在用什么替代方案解决这个问题？免费的、手动的、习惯性的都算竞争对手。'")
        lines.append("  → 追问：'如果你说的市场空白是真实的，为什么至今没有人填补？是时机问题、技术问题还是市场太小？'")

    # 特殊检测：学生声称已做了访谈，但得分仍低
    interview_phrases = ["访谈了", "调研了", "问卷", "用户说", "反馈"]
    if any(p in current_message for p in interview_phrases) and scores.get("empathy", 0) < 5:
        lines.append("\n⚠️ 访谈质量追问触发：")
        lines.append("  [指令] 学生声称做了访谈，但痛点发现得分仍低，追问访谈质量：")
        lines.append("  → '你访谈了多少人？是否有录音/笔记？他们是陌生人还是朋友/家人？'")
        lines.append("  → '在所有受访者中，有多少人表示愿意现在就花钱解决这个问题？'")

    if len(lines) <= 1:
        return ""

    return "\n".join(lines)
