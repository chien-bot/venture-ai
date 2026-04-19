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
from services.database import get_competition_date, get_latest_annotations_for_coach, get_previous_scores, get_teacher_interventions
from services.floor_scorer import compute_floor_scores, enforce_floor, format_breakdown_for_response
from services.cheap_diagnostic import run_cheap_diagnostic, format_diagnostic_for_prompt, format_diagnostic_as_fallback
from services.knowledge_cards import search_cards, format_cards_for_prompt
from services.playbook_engine import match_playbook, format_playbook_for_prompt
from services.debug_logger import DebugLogger

_dbg = DebugLogger("coach_node")


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
    (
        ["免费", "不收费", "先不赚钱", "先做流量", "先积累用户", "暂时不考虑盈利"],
        """[追问策略 - 现金流生存逻辑]
学生计划前期免费运营，先做用户再考虑盈利。需要验证现金流生存能力。
请采用以下策略追问：
1. 现金流压力测试：如果没有外部融资，你的账上资金能支撑你"不赚钱"跑多久？盈亏平衡点在哪里？
2. API/服务成本追问：免费用户越多，你的服务成本越高（如API调用费）——用户量增长是在"烧钱"还是"赚钱"？
3. 融资依赖风险：如果投资人不投，你有Plan B吗？
关键追问模板："假设你一年内拿不到任何融资，你的产品还能活着吗？你每月的固定支出是多少？"
"""
    ),
    (
        ["精准获客", "投放", "转化率", "漏斗", "引流", "小红书", "抖音", "B站", "博主"],
        """[追问策略 - 精准获客逻辑]
学生提到了获客渠道，需要验证渠道选择与目标用户的匹配度。
请采用以下策略追问：
1. 渠道-用户匹配：你的目标用户真的活跃在这个平台吗？有数据证明吗？
2. 获客成本估算：通过这个渠道获取一个付费用户的成本是多少？
3. 转化漏斗量化：从曝光→点击→注册→付费，每一步的预计转化率是多少？
关键追问模板："你的目标用户画像是什么？他们每天花多少时间在你选的这个渠道上？这个数据从哪来的？"
"""
    ),
    (
        ["痛点", "需要", "需求", "想要", "用户想", "用户要", "大家都需要"],
        """[追问策略 - 伪需求识别]
学生描述了用户需求，需要验证这是"真痛点"还是"伪需求"。
请采用以下策略追问：
1. 频率与强度：这个痛点多久发生一次？用户为此付出了什么代价（时间/金钱/情绪）？
2. 现有替代方案：用户现在是怎么解决这个问题的？如果你的产品消失了，他们会怎么办？
3. 支付验证：用户是否愿意为此付费？你做过预售或意向调查吗？
关键追问模板："你能描述一个具体的用户场景吗——谁，在什么时候，遇到了什么问题，损失了什么？"
"""
    ),
    (
        ["规模", "扩张", "全国", "全球", "覆盖", "所有", "百万用户", "千万用户"],
        """[追问策略 - 规模化路径质疑]
学生提到了大规模扩张计划，需要验证规模化的可行性。
请采用以下策略追问：
1. 阶段性规划：从1个城市到全国，你的扩张路径是什么？每个阶段的关键指标？
2. 边际成本分析：规模扩大10倍，你的单位成本是下降还是上升？
3. 运营复杂度：跨区域运营会带来什么新问题？你准备好了吗？
关键追问模板："你打算先从哪一个城市/社区开始？服务好100个用户的方法，和服务10万用户的方法一样吗？"
"""
    ),
    (
        ["团队", "我们两个", "两个人", "一个人", "大二", "大三", "本科"],
        """[追问策略 - 团队-野心匹配度]
学生的团队规模与项目野心可能不匹配。
请采用以下策略追问：
1. 能力缺口分析：你的项目需要哪些核心能力？团队现在具备哪些？缺哪些？
2. 时间资源约束：作为在校学生，你每周能投入多少小时？这够完成计划吗？
3. 关键岗位缺失：如果需要招人，你用什么吸引他们加入（股权？薪资？愿景？）？
关键追问模板："你列出的里程碑，以你现在的团队规模和每周可用时间，能在期限内完成吗？具体怎么分工？"
"""
    ),
    (
        ["合规", "法律", "版权", "授权", "隐私", "数据保护", "许可", "资质"],
        """[追问策略 - 合规风险追问]
学生的项目涉及合规相关议题。
请采用以下策略追问：
1. 法规识别：你的业务涉及哪些法律法规？你查阅过具体条文吗？
2. 授权链条：你使用的数据/内容/技术，授权链条完整吗？有书面协议吗？
3. 风险预案：如果被监管叫停或收到法律函件，你的应对方案是什么？
关键追问模板："你能列出你的项目需要获得的所有许可证、授权和资质吗？哪些已经拿到了？"
"""
    ),
    (
        ["差异化", "优势", "不同", "独特", "特色", "我们比", "竞争优势"],
        """[追问策略 - 差异化壁垒深挖]
学生声称具有差异化优势，需要验证这是"真壁垒"还是"短期功能差异"。
请采用以下策略追问：
1. 可复制性测试：竞争对手需要多长时间、多少资金复制你的差异化？
2. 用户感知：用户真的在乎你说的这个差异化吗？他们的选择标准是什么？
3. 持续性：这个差异化优势6个月后还在吗？12个月后呢？
关键追问模板："如果竞争对手明天抄了你最核心的功能，你还剩什么？用户为什么不会流失？"
"""
    ),
    (
        ["融资", "投资", "天使轮", "种子轮", "VC", "投资人", "估值"],
        """[追问策略 - 融资依赖风险]
学生的商业计划严重依赖外部融资。
请采用以下策略追问：
1. 自我造血能力：如果永远拿不到融资，你的项目能靠自身营收活下来吗？
2. 融资节点清晰度：你需要多少钱？什么时候需要？用在哪里？
3. 投资人视角：你认为投资人最关心什么指标？你现在有这些数据吗？
关键追问模板："投资人通常只投100个项目中的1个——你凭什么是那个1个？你有哪些数据能说服他？"
"""
    ),
    (
        ["出海", "海外", "跨境", "外国人", "国际化", "欧美", "东南亚"],
        """[追问策略 - 跨境落地质疑]
学生计划进行跨境业务，需要验证海外落地的可行性。
请采用以下策略追问：
1. 本地化挑战：目标市场的用户习惯、支付方式、法规和国内有什么不同？
2. 物流与供应链：跨境的物流成本、关税、退货处理怎么解决？
3. 团队本地化能力：你的团队有人了解目标市场吗？语言、文化、渠道？
关键追问模板："你有没有和目标市场的真实用户交流过？他们是怎么评价你的产品概念的？"
"""
    ),
    (
        ["MVP", "最小可行", "原型", "第一版", "demo", "测试版"],
        """[追问策略 - MVP范围控制]
学生提到了MVP或原型开发，需要验证MVP的范围是否合理。
请采用以下策略追问：
1. 核心假设：你的MVP要验证的最关键假设是什么？只能选一个。
2. 范围控制：你描述的MVP功能列表，真的是"最小"的吗？哪些可以砍掉？
3. 验证标准：MVP上线后，什么样的数据结果算"验证成功"？什么算"失败"？
关键追问模板："如果你的MVP只能有一个按钮、一个页面，你选什么？为什么这个功能最能验证你的核心假设？"
"""
    ),
]


def _enforce_single_next_task(text: str) -> str:
    """A2-1: Ensure coach reply contains at most one '下一步' task block."""
    pattern = r"(#{1,4}\s*下一步[：:][^\n]*\n(?:(?!#{1,4}\s*下一步).)*)"
    matches = list(re.finditer(pattern, text, re.DOTALL))
    if len(matches) <= 1:
        return text
    first_end = matches[0].end()
    cleaned = text[:first_end]
    tail_start = matches[-1].end()
    cleaned += text[tail_start:]
    return cleaned.strip()


def _detect_fallacy_strategy(message: str) -> tuple[str, list[str]]:
    """
    检测消息中的常见创业谬误，返回 (注入策略文本, 触发策略名称列表)。
    策略名称用于 Debug 日志输出。
    """
    detected_prompts = []
    detected_names = []
    for keywords, strategy_prompt in _FALLACY_STRATEGIES:
        if any(kw in message for kw in keywords):
            detected_prompts.append(strategy_prompt)
            # 从策略文本第一行提取名称，如 "[追问策略 - 竞争幻觉识别]"
            first_line = strategy_prompt.strip().split("\n")[0]
            name = first_line.strip("[]").replace("追问策略 - ", "")
            detected_names.append(name)
    return "\n".join(detected_prompts), detected_names


def _parse_scores(text: str) -> dict | None:
    from services.marker_parser import parse_scores
    return parse_scores(text)


def _clean(text: str) -> str:
    from services.marker_parser import clean_reply
    return clean_reply(text)


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

    _dbg.agent_start(session_id=session_id, intent="coach", message_preview=current_message)

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

        # Inject adaptive questioning context (V2: with session memory)
        questioning_context = build_questioning_context(scores, messages, current_message, session_id=session_id)
        if questioning_context:
            system += f"\n\n{questioning_context}"
            _dbg.info(f"adaptive_questioning_context injected: {questioning_context[:200]}")

        # ★ Inject fallacy strategy library (追问策略库)
        fallacy_strategy, detected_strategy_names = _detect_fallacy_strategy(current_message)
        if fallacy_strategy:
            system += f"\n\n{fallacy_strategy}"
            for strategy_name in detected_strategy_names:
                _dbg.fallacy_detected(
                    fallacy_label=strategy_name,
                    triggered_by=current_message[:100],
                )
                _dbg.strategy_selected(
                    strategy_name=strategy_name,
                    question=f"[将由LLM基于策略生成追问，策略={strategy_name}]",
                )

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

            # ★ A6-3: Inject teacher interventions — keyword-triggered instructions
            try:
                interventions = get_teacher_interventions(project_id)
                matched_instructions = [
                    iv["instruction"] for iv in interventions
                    if iv.get("trigger_keyword") and iv["trigger_keyword"] in current_message
                ]
                if matched_instructions:
                    system += "\n\n[教师干预指令 - 请在本轮严格遵守以下教师设定的辅导策略]\n"
                    for instr in matched_instructions[:3]:
                        system += f"  • {instr}\n"
                    _dbg.info(f"Injected {len(matched_instructions)} teacher intervention(s) for project {project_id}")
            except Exception:
                pass

        # ★ Inject previous scores for score anchoring
        if project_id := state.get("project_id"):
            prev_scores = get_previous_scores(project_id)
            if prev_scores:
                dims = {
                    "empathy": "痛点发现", "ideation": "方案策划",
                    "business": "商业建模", "execution": "资源杠杆",
                    "pitching": "路演表达",
                }
                score_lines = ", ".join(
                    f"{dims.get(k, k)}={v}" for k, v in prev_scores.items()
                    if isinstance(v, (int, float))
                )
                system += (
                    "\n\n[上轮评分参考 — 请基于此进行渐进式调整]\n"
                    f"上轮评分：{score_lines}\n"
                    "重要规则：\n"
                    "- 每个维度每轮变化幅度不超过±2分，除非学生表现有明显突破或严重退步\n"
                    "- 若学生本轮未涉及某维度，该维度评分应与上轮保持一致\n"
                    "- 评分应反映累积进展，不要因单轮表现完全重置\n"
                )

        # ★ 前置采集层注入：如果本 session 有采集数据，注入到 prompt
        from services.session_store import get_session
        session_meta = get_session(session_id) or {}
        intake_ctx = session_meta.get("intake_context")
        if intake_ctx:
            system += f"\n\n{intake_ctx}"

        # ★ 范式库注入：根据项目信息匹配创业范式，注入 prompt
        try:
            intake_data = session_meta.get("intake_data") or {}
            proj_desc = intake_data.get("solution_desc") or intake_data.get("pain_scenario") or ""
            proj_industry = intake_data.get("industry_choice", "")
            proj_biz = intake_data.get("revenue_model", "")
            proj_type = ""
            if project_id:
                from services.database import get_project
                proj_info = get_project(project_id)
                if proj_info:
                    if not proj_desc:
                        proj_desc = proj_info.get("description", "")
                        proj_industry = proj_info.get("industry", proj_industry)
                    proj_type = proj_info.get("project_type") or ""
            if proj_desc:
                matched = match_playbook(proj_desc, proj_industry, proj_biz)
                if matched:
                    pb_prompt = format_playbook_for_prompt(matched[0]["playbook_id"])
                    if pb_prompt:
                        system += f"\n\n{pb_prompt}"
            # ★ 项目类型差异化提示注入（创新/商业/公益）
            if proj_type:
                from routers.projects import PROJECT_TYPE_FOCUS
                type_focus = PROJECT_TYPE_FOCUS.get(proj_type, "")
                if type_focus:
                    system += f"\n\n{type_focus}\n请在提问与反馈中围绕上述重点展开。"
        except Exception:
            pass

        # ★ Phase 1: Cheap-First 轻推理 — 注入结构化诊断到 LLM prompt
        all_msgs_for_diag = list(messages)
        if current_message:
            all_msgs_for_diag.append({"role": "user", "content": current_message})
        try:
            diag = run_cheap_diagnostic(session_id, all_msgs_for_diag, current_scores=scores)
            diag_prompt = format_diagnostic_for_prompt(diag)
            if diag_prompt:
                system += f"\n\n{diag_prompt}"
        except Exception:
            diag = None

        # ★ 知识卡片注入：根据诊断缺口推荐相关知识卡片
        try:
            if diag and diag.top_gaps:
                # 从最紧急的缺口维度搜索相关卡片
                urgent_dims = [d for d in diag.dimensions.values() if d.priority == "urgent"]
                if urgent_dims:
                    dim = urgent_dims[0]
                    gap_cards = search_cards(
                        dimension=dim.dim,
                        max_results=3,
                    )
                    card_prompt = format_cards_for_prompt(gap_cards, max_cards=2)
                    if card_prompt:
                        system += f"\n\n{card_prompt}"
            elif current_message:
                # 无诊断时按消息关键词搜索
                kw_cards = search_cards(query=current_message[:50], max_results=2)
                card_prompt = format_cards_for_prompt(kw_cards, max_cards=2)
                if card_prompt:
                    system += f"\n\n{card_prompt}"
        except Exception:
            pass

        # Phase 2: LLM 生成回复（带诊断上下文）
        raw = chat_completion(system, messages)

        # ★ Cheap-First fallback: LLM 失败时用规则层诊断生成回复
        if raw.startswith("抱歉，AI 服务暂时无法响应") and diag:
            raw = format_diagnostic_as_fallback(diag)

    # A2-1: enforce single next-task constraint before score parsing
    raw = _enforce_single_next_task(raw)

    scores_data = _parse_scores(raw)
    clean = _clean(raw)

    new_scores = None
    stage = state.get("stage")
    diagnosis = state.get("diagnosis", [])
    score_breakdown = None

    if scores_data:
        new_scores = {k: v for k, v in scores_data.items() if k not in ("stage", "diagnosis")}
        stage = scores_data.get("stage", stage)
        diagnosis = scores_data.get("diagnosis", diagnosis)

        # ★ 可计算底分：用证据约束 LLM 评分
        all_msgs = list(messages)
        if current_message:
            all_msgs.append({"role": "user", "content": current_message})
        breakdowns = compute_floor_scores(session_id, all_msgs)
        new_scores = enforce_floor(new_scores, breakdowns)
        score_breakdown = format_breakdown_for_response(breakdowns)

    _dbg.agent_done(scores=new_scores, stage=stage or "", diagnosis=diagnosis)

    return {
        **state,
        "coach_output": clean,
        "scores": new_scores,
        "stage": stage,
        "diagnosis": diagnosis,
        "score_breakdown": score_breakdown,
    }
