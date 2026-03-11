"""Coach node: Socratic entrepreneurship coaching."""

import re
import json
from agents.state import AgentState
from config import USE_MOCK_API
from services.claude_client import chat_completion
from prompts.coach import COACH_SYSTEM_PROMPT
from mock.responses import MOCK_COACH_REPLIES
from services.evidence_tracer import refresh_tracer
from agents.adaptive_questioning import (
    build_questioning_context,
    get_weak_dims,
    detect_evasion,
    DIM_LABELS,
)
from services.competition_mode import get_countdown_context
from services.database import get_competition_date, get_latest_annotations_for_coach


# ── 追问策略库 ─────────────────────────────────────────────────────
# 每个条目：触发关键词列表 → 注入的精准反驳策略提示
_FALLACY_STRATEGIES: list[tuple[list[str], str]] = [
    (
        ["没有对手", "没有竞争", "没有竞争对手", "唯一一家", "市场空白", "全球唯一"],
        """[追问策略 - 竞争幻觉识别]
学生声称没有竞争对手或市场空白。这是典型的"隐性替代品盲区"。
请采用以下策略进行苏格拉底式追问：
1. 挑战替代品：用户在此方案出现前如何解决该问题？Excel/微信群/线下咨询都是竞争对手。
2. 模拟巨头入场：如果阿里/腾讯/字节下周推出相同功能，你的护城河在哪里？
3. 追问信息来源：你是如何确认市场空白的？用了哪些具体调研方法？
关键追问模板："如果一个资深投资人用10分钟搜索，他能找到3个类似的公司——你怎么解释你所说的'没有竞争对手'？"
"""
    ),
    (
        ["1%", "1%的中国人", "百分之一", "中国有14亿", "只需要1%", "哪怕1%"],
        """[追问策略 - 市场规模幻觉]
学生使用了"1%中国人"或类似的自上而下市场推算法（TAM×1%），这是最常见的创业逻辑谬误之一。
请采用以下策略追问：
1. 要求自下而上推算：你具体能接触到哪些渠道？每个渠道能覆盖多少精准用户？
2. 追问获客成本：获取这1%用户的CAC（客户获取成本）是多少？与LTV（用户终身价值）的比例？
3. 锚定具体场景：你的第一批100个付费用户从哪里来？他们是谁？
关键追问模板："把1%中国人换成具体数字——你的第一个月能服务多少用户，第一年呢？钱从哪里来？"
"""
    ),
    (
        ["技术门槛极高", "技术壁垒", "专利保护", "算法领先", "独家技术", "核心算法"],
        """[追问策略 - 技术壁垒质疑]
学生声称技术门槛是其核心壁垒。需要区分"难以复制的技术"与"短期领先的功能"。
请采用以下策略追问：
1. 量化技术差距：竞争对手需要多少时间/资金复制你的技术？有具体数据支撑吗？
2. 追问专利有效性：专利申请了吗？覆盖哪些核心功能？竞争对手能否绕过？
3. 市场对技术的感知：用户是否真的为"更好的技术"付费，还是他们只关心结果？
关键追问模板："假设一家有500人工程团队的公司决定进入这个领域，你的技术壁垒能撑多久？"
"""
    ),
    (
        ["用户都喜欢", "用户反馈很好", "朋友都说好", "身边的人", "大家都需要"],
        """[追问策略 - 确认偏差识别]
学生的用户调研可能存在确认偏差（只收集正面反馈）。
请采用以下策略追问：
1. 追问反面证据：有用户明确拒绝或不感兴趣吗？占比多少？
2. 挑战样本代表性：调研了多少人？用了什么方法？有没有陌生人参与？
3. 区分"喜欢"与"付费意愿"：有多少用户愿意现在付钱？价格是多少？
关键追问模板："在你调研的用户中，有多少人说'不'或'不确定'？他们的理由是什么？"
"""
    ),
    (
        ["盈利模式", "商业模式", "怎么赚钱", "收费方式", "变现", "营收"],
        """[追问策略 - 商业模式深挖]
学生提到了盈利相关内容。需要验证商业模式的可持续性。
请采用以下策略追问：
1. 验证定价逻辑：定价依据是什么？竞品定价如何？用户的支付意愿调研结果？
2. 测算单位经济：每个用户的边际成本、毛利率、回收周期？
3. 追问规模化路径：从100个用户到10000个用户，商业模式会发生什么变化？
关键追问模板："你的商业模式中，最大的成本项是什么？当用户量扩大10倍，这个成本怎么变化？"
"""
    ),
    (
        ["政策支持", "国家政策", "政府补贴", "政策红利", "国家鼓励"],
        """[追问策略 - 政策依赖风险]
学生将政策作为重要驱动力。需要评估政策风险和独立生存能力。
请采用以下策略追问：
1. 追问政策依赖度：如果政策明天取消，你的商业模式还能运转吗？
2. 竞争格局分析：政策同时惠及你的竞争对手，你的相对优势在哪里？
3. 政策时效性：这个政策的有效期是多久？你能在政策窗口期内建立独立竞争力吗？
关键追问模板："如果政策支持减少50%，你的项目生存概率是多少？用什么数据支撑这个判断？"
"""
    ),
]


def _detect_fallacy_strategy(message: str) -> str:
    """检测消息中的常见创业谬误，返回需要注入的策略提示（如有）。"""
    detected = []
    message_lower = message.lower()
    for keywords, strategy_prompt in _FALLACY_STRATEGIES:
        if any(kw in message for kw in keywords):
            detected.append(strategy_prompt)
    return "\n".join(detected)


def _parse_scores(text: str) -> dict | None:
    match = re.search(r"<!--SCORES:(.*?)-->", text)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            return None
    return None


def _clean(text: str) -> str:
    return re.sub(r"<!--SCORES:.*?-->", "", text).strip()


def _mock_coach(state: AgentState) -> str:
    message = state["current_message"]
    history_len = len(state["messages"])
    scores = state.get("scores") or {}

    # Adaptive: 薄弱维度优先触发对应 mock 回复
    weak_dims = get_weak_dims(scores)

    if "没有对手" in message or "没有竞争" in message or "唯一" in message:
        return MOCK_COACH_REPLIES[2]["reply"]

    # 如果检测到 business 薄弱且学生在回避
    if "business" in weak_dims and detect_evasion(state["messages"], "business"):
        return MOCK_COACH_REPLIES[3]["reply"]

    if "商业模式" in message or "盈利" in message or "收费" in message:
        return MOCK_COACH_REPLIES[3]["reply"]
    if "执行" in message or "团队" in message or "MVP" in message:
        return MOCK_COACH_REPLIES[4]["reply"]
    if "路演" in message or "pitch" in message.lower() or "投资人" in message:
        return MOCK_COACH_REPLIES[5]["reply"]
    if history_len > 6:
        return MOCK_COACH_REPLIES[6]["reply"]
    return MOCK_COACH_REPLIES[1]["reply"]


def coach_node(state: AgentState) -> AgentState:
    session_id = state.get("session_id", "")
    messages = state.get("messages", [])
    scores = state.get("scores")
    current_message = state.get("current_message", "")

    # Refresh evidence tracer
    tracer = refresh_tracer(session_id, messages)

    if USE_MOCK_API:
        raw = _mock_coach(state)
    else:
        system = COACH_SYSTEM_PROMPT

        # ★ Inject hypergraph retrieval context (RAG)
        hypergraph_ctx = state.get("hypergraph_context", "")
        if hypergraph_ctx:
            system += (
                "\n\n[超图知识库检索结果 — 基于82个真实竞赛案例]\n"
                "以下是从超图案例库中检索到的与学生项目相关的信息。"
                "请在回答中引用这些案例和风险模式来增强你的指导：\n\n"
                f"{hypergraph_ctx}"
            )

        # Inject evidence tracer context
        evidence_context = tracer.format_missing_evidence()
        if evidence_context:
            system += f"\n\n[证据追踪摘要]\n{evidence_context}"

        # Inject adaptive questioning context
        questioning_context = build_questioning_context(scores, messages, current_message)
        if questioning_context:
            system += f"\n\n{questioning_context}"

        # ★ Inject fallacy strategy library (追问策略库)
        fallacy_strategy = _detect_fallacy_strategy(current_message)
        if fallacy_strategy:
            system += f"\n\n{fallacy_strategy}"

        # Inject competition countdown mode
        if project_id := state.get("project_id"):
            comp_date = get_competition_date(project_id)
            countdown_ctx = get_countdown_context(comp_date)
            if countdown_ctx:
                system += f"\n\n{countdown_ctx}"

            # Inject teacher annotations
            try:
                notes = get_latest_annotations_for_coach(project_id)
                if notes:
                    system += "\n\n[教师批注 - 请在本轮对话中体现以下教师指导意见]\n"
                    for a in notes[:3]:
                        system += f"  • {a['note_text']}\n"
            except Exception:
                pass

        raw = chat_completion(system, messages)

    scores_data = _parse_scores(raw)
    clean = _clean(raw)

    new_scores = None
    stage = state.get("stage")
    diagnosis = state.get("diagnosis", [])

    if scores_data:
        new_scores = {k: v for k, v in scores_data.items() if k not in ("stage", "diagnosis")}
        stage = scores_data.get("stage", stage)
        diagnosis = scores_data.get("diagnosis", diagnosis)

    return {
        **state,
        "coach_output": clean,
        "scores": new_scores,
        "stage": stage,
        "diagnosis": diagnosis,
    }
