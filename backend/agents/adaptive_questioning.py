"""
agents/adaptive_questioning.py
────────────────────────────────────────────────────────────────
苏格拉底追问策略库（Adaptive Questioning Engine）

核心逻辑：
1. 根据当前 scores 找出最薄弱维度
2. 检测学生是否"回避"了某类问题（连续多轮未提相关关键词）
3. 根据薄弱维度 + 回避模式，返回对应的追问链（question chain）
4. 结果注入 coach system prompt 作为动态指令

追问链结构：
  每个维度有 3 个层级的追问（深入追问）：
  - L1: 第一次发现薄弱时触发（温和引导）
  - L2: 第二次还是薄弱时触发（加大压力）
  - L3: 连续 3 轮薄弱时触发（直接挑战）
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


QUESTION_CHAINS: list[QuestionChain] = [
    QuestionChain(
        dim="empathy",
        label="痛点发现",
        signals=["痛点", "用户", "访谈", "调研", "问题", "需求", "不方便", "困难", "场景"],
        l1="你提到了这个问题，但我想更具体地了解：**你采访过真实用户吗？他们用什么词描述这个痛苦？**",
        l2="你说的这个痛点，我想反问一句：**用户现在是怎么解决这个问题的？为什么现有方案不够好？**",
        l3="我们已经聊了几轮，但我还没看到任何一手用户证据。**请告诉我：你最近一次和目标用户面对面交流是什么时候？他们说了什么？**",
        evasion_tip="[追问指令] 学生连续多轮未提供用户访谈证据，请在本轮追问用户一手证据，不要接受泛化描述。",
    ),
    QuestionChain(
        dim="ideation",
        label="方案策划",
        signals=["方案", "产品", "功能", "设计", "原型", "MVP", "技术", "实现", "差异"],
        l1="你的方案思路有了，但我想知道：**和市面上已有的解决方案相比，你最核心的差异化是什么？**",
        l2="我听到了你的方案，现在做个压力测试：**如果微信/阿里明天发布一个免费功能解决同样的问题，你的产品还有价值吗？**",
        l3="我们讨论方案已经好几轮了，但还没有触及护城河。**你的方案中，有没有竞争对手6个月内无法复制的东西？**",
        evasion_tip="[追问指令] 学生多次描述方案但回避竞品分析，本轮请直接追问差异化和护城河，不要跳过。",
    ),
    QuestionChain(
        dim="business",
        label="商业建模",
        signals=["商业模式", "盈利", "收费", "付费", "价格", "收入", "定价", "变现", "订阅", "客单价"],
        l1="你提到了项目方向，但我还不清楚：**谁来付钱？付多少？为什么愿意付这个价格而不是免费替代品？**",
        l2="让我们具体一点：**假设你有100个用户，每人每月付X元，你的成本是多少，利润是多少？这个数字能养活团队吗？**",
        l3="我们聊了很多，但你的商业模式还很模糊。**请现在给我一个最简单的数字：你的第一年目标收入是多少，这基于什么假设？**",
        evasion_tip="[追问指令] 学生回避商业模式讨论，请在本轮强制引导到具体定价和单位经济模型，要求给出数字。",
    ),
    QuestionChain(
        dim="execution",
        label="资源杠杆",
        signals=["团队", "资源", "合作", "执行", "计划", "里程碑", "MVP", "时间", "人手", "预算"],
        l1="想法很好，但执行是关键：**你们团队现在有几个人？每个人负责什么？你最担心哪个环节卡住？**",
        l2="你提到了计划，我想问更实际的：**在没有外部融资的情况下，你能用学校现有的资源（实验室/导师/政府补贴）走多远？**",
        l3="我们一直在讨论想法，但还没谈执行路径。**请给我一个3个月的里程碑计划：第1个月做什么，第2个月验证什么，第3个月交付什么？**",
        evasion_tip="[追问指令] 学生回避执行细节，请追问具体的里程碑和资源盘点，不接受'后续再说'类回答。",
    ),
    QuestionChain(
        dim="pitching",
        label="路演表达",
        signals=["路演", "演示", "pitch", "PPT", "投资人", "故事", "表达", "逻辑", "叙述"],
        l1="你的项目逻辑是否能被30秒内解释清楚？**试试用一句话告诉我：你为谁、解决了什么问题、用什么方式、凭什么比现有方案好。**",
        l2="假设你在电梯里遇到了一个投资人，只有60秒：**你会说什么？请现在就说，我来帮你找逻辑漏洞。**",
        l3="路演是你向外界证明价值的关键时刻。**你的Pitch有几页PPT？每页的核心信息是什么？你有没有演练过？最担心评委问哪个问题？**",
        evasion_tip="[追问指令] 学生路演逻辑薄弱，请引导其做一次简短的口头路演，并指出逻辑断层。",
    ),
]

# 快速查询 dict
_CHAINS_BY_DIM: dict[str, QuestionChain] = {c.dim: c for c in QUESTION_CHAINS}

# ─────────────────────────────────────────────────────────────
# 回避检测
# ─────────────────────────────────────────────────────────────

EVASION_WEAK_WORDS = [
    "应该", "可能", "大概", "估计", "打算", "以后", "后续",
    "不确定", "不清楚", "还没想好", "之后再说", "先不管",
    "不知道", "说不好", "暂时", "再看看",
]

def detect_evasion(messages: list[dict], dim: str, window: int = 4) -> bool:
    """
    检测最近 window 轮用户消息中：
    1. 完全没有提到该维度的关键词，且
    2. 或者出现了回避性词汇
    → 返回 True 表示正在回避
    """
    chain = _CHAINS_BY_DIM.get(dim)
    if not chain:
        return False

    user_msgs = [m["content"] for m in messages if m["role"] == "user"]
    recent = user_msgs[-window:] if len(user_msgs) >= window else user_msgs
    if not recent:
        return False

    combined = " ".join(recent)
    has_signal = any(kw in combined for kw in chain.signals)
    has_evasion = any(w in combined for w in EVASION_WEAK_WORDS)

    # 没有提及任何信号 = 回避；或者有弱化词 = 主动回避
    return (not has_signal) or has_evasion


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
# 追问级别计算
# ─────────────────────────────────────────────────────────────

def get_question_level(scores: dict | None, dim: str, round_num: int) -> int:
    """
    根据得分和轮次决定追问级别（1/2/3）。
    round_num 为当前对话轮数（从消息数推算）。
    """
    score = (scores or {}).get(dim, 0)
    if score < 2.0:
        return 3
    if score < 4.0 and round_num >= 4:
        return 2
    return 1


# ─────────────────────────────────────────────────────────────
# 主入口：生成追问上下文块
# ─────────────────────────────────────────────────────────────

def build_questioning_context(
    scores: dict | None,
    messages: list[dict],
    current_message: str,
) -> str:
    """
    分析当前状态，返回注入 system prompt 的动态追问指令块。
    如果没有明确的追问目标，返回空字符串。
    """
    if not scores:
        return ""

    round_num = len([m for m in messages if m["role"] == "user"])
    weak_dims = get_weak_dims(scores)

    if not weak_dims:
        return ""

    lines: list[str] = ["[动态追问策略 - 本轮重点]"]

    # 最多关注最薄弱的 2 个维度
    for dim in weak_dims[:2]:
        chain = _CHAINS_BY_DIM.get(dim)
        if not chain:
            continue

        level = get_question_level(scores, dim, round_num)
        question = {1: chain.l1, 2: chain.l2, 3: chain.l3}[level]
        is_evading = detect_evasion(messages, dim)

        lines.append(f"\n▶ {chain.label}（当前得分 {scores.get(dim, 0):.1f}/10，追问级别 L{level}）")
        lines.append(f"  推荐追问：{question}")

        if is_evading:
            lines.append(f"  ⚠️ 回避检测：{chain.evasion_tip}")

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
