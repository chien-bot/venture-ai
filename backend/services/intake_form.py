"""
services/intake_form.py
────────────────────────────────────────────────────────────────
前置采集层 — 信息增益问卷 (IG Form)

核心思路（方向1）：
把原先 8-12 轮的"导师式追问"改为 2-3 轮高信息增益采集：
  第1轮：结构化采集（尽可能一次问全关键变量）
  第2轮：缺口确认（仅问缺失的 3 个最关键字段）
  第3轮：输出诊断/建议，进入正式教练对话

设计原理：
- 把创业项目拆成 16 个"最能决定后续推理"的变量
- 变量按 Rubric (R1-R9) 分组，覆盖五大维度
- 用规则 + 超图先做"缺口预测"：根据已填字段预测还缺哪些关键字段
- LLM 仅在最终输出阶段调用，采集阶段零 LLM 消耗
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Optional


# ── 采集变量定义 ──────────────────────────────────────────────
# 每个变量：key, 中文标签, 所属 Rubric, 信息增益权重(越高越重要), 输入类型, 选项(可选)

@dataclass
class IntakeField:
    key: str
    label: str
    rubric: str           # R1-R9
    dimension: str        # empathy/ideation/business/execution/pitching
    ig_weight: float      # 信息增益权重 0~1
    input_type: str       # "text" | "select" | "number" | "textarea"
    placeholder: str = ""
    options: list[str] = field(default_factory=list)
    required: bool = False
    group: str = ""       # 分组标签


# 16 个核心采集变量（按信息增益排序）
INTAKE_FIELDS: list[IntakeField] = [
    # ── 痛点发现 (Empathy) ──
    IntakeField(
        key="target_user", label="目标用户群体",
        rubric="R1", dimension="empathy", ig_weight=0.95,
        input_type="text", placeholder="例：18-25岁大学生 / 二线城市社区诊所医生",
        required=True, group="痛点发现",
    ),
    IntakeField(
        key="pain_scenario", label="痛点场景",
        rubric="R1", dimension="empathy", ig_weight=0.93,
        input_type="textarea", placeholder="在什么场景下、遇到什么具体问题？",
        required=True, group="痛点发现",
    ),
    IntakeField(
        key="user_research", label="用户调研情况",
        rubric="R2", dimension="empathy", ig_weight=0.88,
        input_type="select", options=["还没做过调研", "和身边朋友聊过", "正式访谈了1-5人", "访谈了5-20人", "访谈了20人以上", "做过问卷调查(50+份)"],
        group="痛点发现",
    ),
    IntakeField(
        key="user_quote", label="用户原话/关键发现",
        rubric="R2", dimension="empathy", ig_weight=0.85,
        input_type="textarea", placeholder="用户访谈中最让你印象深刻的一句话或发现（如没有可跳过）",
        group="痛点发现",
    ),

    # ── 方案策划 (Ideation) ──
    IntakeField(
        key="solution_desc", label="解决方案概述",
        rubric="R3", dimension="ideation", ig_weight=0.92,
        input_type="textarea", placeholder="你打算怎么解决这个问题？核心产品/服务是什么？",
        required=True, group="方案策划",
    ),
    IntakeField(
        key="tech_approach", label="技术路线",
        rubric="R3", dimension="ideation", ig_weight=0.70,
        input_type="text", placeholder="例：深度学习图像识别 / 微信小程序 / IoT传感器",
        group="方案策划",
    ),
    IntakeField(
        key="differentiation", label="核心差异化",
        rubric="R7", dimension="ideation", ig_weight=0.82,
        input_type="textarea", placeholder="和市面上的替代品比，你最核心的不同是什么？",
        group="方案策划",
    ),
    IntakeField(
        key="alternatives", label="用户现在怎么解决",
        rubric="R7", dimension="ideation", ig_weight=0.80,
        input_type="text", placeholder="没有你的产品前，用户用什么替代方案？",
        group="方案策划",
    ),

    # ── 商业建模 (Business) ──
    IntakeField(
        key="revenue_model", label="盈利模式",
        rubric="R4", dimension="business", ig_weight=0.87,
        input_type="select", options=["还没想好", "SaaS订阅", "交易佣金", "广告", "硬件销售", "服务收费", "政府/补贴", "免费增值(Freemium)", "其他"],
        group="商业建模",
    ),
    IntakeField(
        key="payer", label="谁来付钱",
        rubric="R4", dimension="business", ig_weight=0.86,
        input_type="text", placeholder="最终的付费方是谁？（可能不是终端用户）",
        group="商业建模",
    ),
    IntakeField(
        key="unit_price", label="预计单价/客单价",
        rubric="R6", dimension="business", ig_weight=0.75,
        input_type="text", placeholder="例：月费99元 / 每单佣金5% / 年费12万",
        group="商业建模",
    ),
    IntakeField(
        key="market_size", label="目标市场规模",
        rubric="R5", dimension="business", ig_weight=0.72,
        input_type="select", options=["还没估算", "百万级", "千万级", "亿级", "十亿级以上"],
        group="商业建模",
    ),

    # ── 资源杠杆 (Execution) ──
    IntakeField(
        key="team_size", label="团队人数",
        rubric="R8", dimension="execution", ig_weight=0.65,
        input_type="select", options=["1人(只有我)", "2-3人", "4-6人", "7人以上"],
        group="资源与执行",
    ),
    IntakeField(
        key="team_skills", label="团队核心能力",
        rubric="R8", dimension="execution", ig_weight=0.63,
        input_type="text", placeholder="例：技术开发+医学背景 / 全是商科同学",
        group="资源与执行",
    ),
    IntakeField(
        key="mvp_status", label="MVP/原型状态",
        rubric="R8", dimension="execution", ig_weight=0.68,
        input_type="select", options=["还在想法阶段", "有初步原型/Demo", "MVP已完成", "已有真实用户", "已有付费用户"],
        group="资源与执行",
    ),

    # ── 路演表达 (Pitching) ──
    IntakeField(
        key="pitch_ready", label="路演材料状态",
        rubric="R9", dimension="pitching", ig_weight=0.50,
        input_type="select", options=["还没准备", "有初稿PPT", "PPT已完成", "已练习过路演"],
        group="路演表达",
    ),
]

# 按 ig_weight 降序的字段 key 列表
_FIELDS_BY_IG = sorted(INTAKE_FIELDS, key=lambda f: -f.ig_weight)
_FIELD_MAP = {f.key: f for f in INTAKE_FIELDS}

# 维度→字段映射
_DIM_FIELDS: dict[str, list[str]] = {}
for _f in INTAKE_FIELDS:
    _DIM_FIELDS.setdefault(_f.dimension, []).append(_f.key)


# ── 缺口预测 ─────────────────────────────────────────────────

@dataclass
class IntakeGap:
    """一个缺口：哪个字段没填 + 为什么重要。"""
    field_key: str
    label: str
    dimension: str
    rubric: str
    ig_weight: float
    reason: str       # 为什么这个字段重要的一句话解释


def predict_gaps(filled_data: dict[str, str], max_gaps: int = 3) -> list[IntakeGap]:
    """
    根据已填数据，预测最需要补充的 N 个字段。

    策略：
    1. 必填字段未填 → 优先返回
    2. 按信息增益权重排序未填字段
    3. 考虑跨字段依赖（如填了 revenue_model 但没填 payer → payer 优先级提升）
    """
    gaps: list[IntakeGap] = []

    # 已填字段集合（非空值）
    filled_keys = {k for k, v in filled_data.items() if v and v.strip() and v not in ("还没想好", "还没做过调研", "还没估算", "还没准备", "还在想法阶段")}

    # 遍历所有字段，按 ig_weight 降序
    for f in _FIELDS_BY_IG:
        if f.key in filled_keys:
            continue

        # 生成缺口原因
        reason = _gap_reason(f, filled_data, filled_keys)

        gaps.append(IntakeGap(
            field_key=f.key,
            label=f.label,
            dimension=f.dimension,
            rubric=f.rubric,
            ig_weight=f.ig_weight,
            reason=reason,
        ))

    # 动态提升优先级：跨字段依赖
    _boost_dependencies(gaps, filled_keys)

    # 按 ig_weight 重排（boost 可能改了权重）
    gaps.sort(key=lambda g: -g.ig_weight)

    return gaps[:max_gaps]


def _gap_reason(f: IntakeField, filled: dict, filled_keys: set) -> str:
    """为缺口生成一句话解释。"""
    reasons = {
        "target_user": "明确目标用户是所有后续分析的基础",
        "pain_scenario": "具体的痛点场景决定了方案设计方向",
        "user_research": "用户调研的深度直接影响痛点验证的可信度",
        "user_quote": "真实用户反馈是最有力的证据",
        "solution_desc": "需要了解你的核心解决方案才能评估可行性",
        "tech_approach": "技术路线决定了开发难度和资源需求",
        "differentiation": "差异化是投资人最关注的点之一",
        "alternatives": "了解替代品有助于评估你的竞争优势",
        "revenue_model": "盈利模式是商业可行性的核心",
        "payer": "搞清楚谁付钱是商业模式成立的前提",
        "unit_price": "价格决定了单位经济是否成立",
        "market_size": "市场规模影响项目的增长天花板",
        "team_size": "团队规模决定了执行能力上限",
        "team_skills": "团队技能需要和项目需求匹配",
        "mvp_status": "产品阶段决定了下一步的重点方向",
        "pitch_ready": "路演准备状态影响竞赛评审表现",
    }
    return reasons.get(f.key, f"缺少{f.label}的信息")


def _boost_dependencies(gaps: list[IntakeGap], filled_keys: set):
    """跨字段依赖：某些字段组合缺失时提升优先级。"""
    gap_keys = {g.field_key for g in gaps}

    # 填了盈利模式但没填 payer → 提升 payer
    if "revenue_model" in filled_keys and "payer" in gap_keys:
        for g in gaps:
            if g.field_key == "payer":
                g.ig_weight += 0.1
                g.reason = "你已选择了盈利模式，需要明确谁来付钱"

    # 填了目标用户但没做调研 → 强烈提升 user_research
    if "target_user" in filled_keys and "user_research" in gap_keys:
        for g in gaps:
            if g.field_key == "user_research":
                g.ig_weight += 0.08
                g.reason = "你已定义了目标用户，下一步最关键的是验证假设"

    # 有方案但没有差异化 → 提升 differentiation
    if "solution_desc" in filled_keys and "differentiation" in gap_keys:
        for g in gaps:
            if g.field_key == "differentiation":
                g.ig_weight += 0.08
                g.reason = "方案已有雏形，需要明确和竞品的区别"

    # 有团队但没有 MVP 状态 → 提升 mvp_status
    if "team_size" in filled_keys and "mvp_status" in gap_keys:
        for g in gaps:
            if g.field_key == "mvp_status":
                g.ig_weight += 0.05


# ── 采集结果 → 证据预填充 ────────────────────────────────────

@dataclass
class IntakeEvidence:
    """从采集表单提取的一条预填证据。"""
    text: str
    ev_type: str        # DATA | CLAIM | QUOTE | COMMIT
    rubric_tag: str     # R1_pain_point 等


def extract_evidence_from_intake(filled_data: dict[str, str]) -> list[IntakeEvidence]:
    """
    把结构化采集数据转化为证据列表，预填充到 EvidenceTracer。

    规则：
    - 有具体数字/来源 → DATA
    - 有用户原话 → QUOTE
    - 选择了具体选项（非"还没"） → CLAIM（至少是有方向的主张）
    - 涉及计划/承诺 → COMMIT
    """
    evidences: list[IntakeEvidence] = []

    for key, value in filled_data.items():
        if not value or not value.strip():
            continue

        f = _FIELD_MAP.get(key)
        if not f:
            continue

        rubric_tag = _key_to_rubric_tag(f.rubric)
        ev_type = _classify_intake_evidence(key, value)

        # 跳过"空"选项
        if value in ("还没想好", "还没做过调研", "还没估算", "还没准备", "还在想法阶段"):
            continue

        evidences.append(IntakeEvidence(
            text=f"[采集表] {f.label}: {value}",
            ev_type=ev_type,
            rubric_tag=rubric_tag,
        ))

    return evidences


def _key_to_rubric_tag(rubric_id: str) -> str:
    """R1 → R1_pain_point, R2 → R2_user_evidence, etc."""
    mapping = {
        "R1": "R1_pain_point",
        "R2": "R2_user_evidence",
        "R3": "R3_solution",
        "R4": "R4_business_model",
        "R5": "R5_market",
        "R6": "R6_finance",
        "R7": "R7_innovation",
        "R8": "R8_execution",
        "R9": "R9_pitch",
    }
    return mapping.get(rubric_id, rubric_id)


def _classify_intake_evidence(key: str, value: str) -> str:
    """根据字段类型和内容判断证据类型。"""
    import re

    # 用户原话 → QUOTE
    if key == "user_quote" and value.strip():
        return "QUOTE"

    # 有数字的 → DATA
    if re.search(r'\d+', value):
        return "DATA"

    # 调研选项中有具体数字 → DATA
    if key == "user_research" and any(w in value for w in ["访谈了", "问卷调查"]):
        return "DATA"

    # MVP 有实际产出 → DATA
    if key == "mvp_status" and any(w in value for w in ["已完成", "已有真实用户", "已有付费用户"]):
        return "DATA"

    # 其他非空选项 → CLAIM
    return "CLAIM"


# ── 采集摘要 → 注入 coach prompt ─────────────────────────────

def format_intake_for_prompt(filled_data: dict[str, str], gaps: list[IntakeGap]) -> str:
    """
    将采集结果格式化为注入 LLM system prompt 的上下文块。

    LLM 收到后知道：
    1. 学生已提供了哪些信息（不需要重复追问）
    2. 还缺什么（应该优先追问）
    3. 每条已有信息的证据强度
    """
    lines = ["[前置采集结果 — 学生在开始对话前已填写的项目信息]"]

    # 已填写的信息
    filled_items = []
    for f in INTAKE_FIELDS:
        v = filled_data.get(f.key, "")
        if v and v.strip() and v not in ("还没想好", "还没做过调研", "还没估算", "还没准备", "还在想法阶段"):
            ev_type = _classify_intake_evidence(f.key, v)
            filled_items.append((f, v, ev_type))

    if filled_items:
        lines.append("\n已有信息：")
        current_group = ""
        for f, v, ev_type in filled_items:
            if f.group != current_group:
                current_group = f.group
                lines.append(f"\n  【{current_group}】")
            strength = {"DATA": "✓数据", "QUOTE": "✓引用", "CLAIM": "△主张", "COMMIT": "○承诺"}
            lines.append(f"  • {f.label}: {v}  [{strength.get(ev_type, '△')}]")

    # 明确标注为空的关键字段
    empty_required = []
    for f in INTAKE_FIELDS:
        v = filled_data.get(f.key, "")
        if f.required and (not v or not v.strip()):
            empty_required.append(f.label)

    if empty_required:
        lines.append(f"\n⚠️ 必填但未提供：{', '.join(empty_required)}")

    # 缺口分析
    if gaps:
        lines.append(f"\n🔍 系统识别的 Top {len(gaps)} 信息缺口：")
        for i, g in enumerate(gaps, 1):
            lines.append(f"  {i}. {g.label}（{g.reason}）")

    lines.append("\n请基于以上已有信息开始对话。")
    lines.append("对于已提供数据证据的方面，不要重复追问基础信息，而是进行深度追问。")
    lines.append("对于信息缺口，请在前 2 轮对话中优先覆盖。")

    return "\n".join(lines)


def format_intake_summary_for_student(filled_data: dict[str, str], gaps: list[IntakeGap]) -> str:
    """
    生成面向学生的采集摘要，作为第一条 AI 消息。

    风格：简洁、鼓励、直接指出下一步方向。
    """
    # 统计填写情况
    filled_count = sum(
        1 for f in INTAKE_FIELDS
        if filled_data.get(f.key, "").strip()
        and filled_data[f.key] not in ("还没想好", "还没做过调研", "还没估算", "还没准备", "还在想法阶段")
    )
    total = len(INTAKE_FIELDS)
    coverage = filled_count / total

    lines = []

    # 开头：根据覆盖率调整语气
    if coverage >= 0.7:
        lines.append("你的项目信息已经相当完整了，让我们直接进入深度分析。")
    elif coverage >= 0.4:
        lines.append("感谢你提供的项目信息，我已经对你的项目有了初步了解。")
    else:
        lines.append("感谢你的初步信息，让我们一起把项目的关键部分理清楚。")

    lines.append("")

    # 亮点：已有数据证据的方面
    data_items = []
    for f in INTAKE_FIELDS:
        v = filled_data.get(f.key, "")
        if v and _classify_intake_evidence(f.key, v) == "DATA":
            data_items.append(f.label)
    if data_items:
        lines.append(f"**已有数据支撑的方面：** {'、'.join(data_items[:3])}")
        lines.append("")

    # 缺口追问
    if gaps:
        lines.append("**为了更好地帮助你，我想先确认几个关键点：**")
        lines.append("")
        for i, g in enumerate(gaps, 1):
            question = _gap_to_question(g)
            lines.append(f"{i}. {question}")
        lines.append("")
        lines.append("你可以逐个回答，也可以一次性说完。准备好了就开始吧！")

    return "\n".join(lines)


def _gap_to_question(gap: IntakeGap) -> str:
    """把缺口转化为自然语言提问。"""
    questions = {
        "target_user": "你的产品/服务具体面向**哪类人群**？能描述一下他们的典型特征吗？",
        "pain_scenario": "这些用户在**什么具体场景**下会遇到这个问题？",
        "user_research": "你有没有和潜在用户**直接交流**过？聊了几个人？",
        "user_quote": "在和用户交流中，有没有**让你印象深刻的一句话**或发现？",
        "solution_desc": "能用 2-3 句话描述一下你的**核心解决方案**吗？",
        "tech_approach": "你打算用什么**技术手段**来实现？",
        "differentiation": "和市面上已有的替代方案比，你**最核心的不同**是什么？",
        "alternatives": "在你的方案出现之前，用户是**怎么解决这个问题**的？",
        "revenue_model": "你打算**怎么赚钱**？是订阅、佣金还是其他方式？",
        "payer": "最终**谁来付钱**？（可能不是终端用户哦）",
        "unit_price": "你的**定价思路**是什么？预计客单价多少？",
        "market_size": "你估算的**目标市场有多大**？",
        "team_size": "你的**团队现在有几个人**？",
        "team_skills": "团队成员各自擅长什么？有没有**关键能力缺口**？",
        "mvp_status": "你的产品现在到**什么阶段**了？有原型或真实用户了吗？",
        "pitch_ready": "你的**路演材料**准备到什么程度了？",
    }
    return questions.get(gap.field_key, f"能告诉我关于「{gap.label}」的情况吗？")


# ── 工具函数 ──────────────────────────────────────────────────

def get_intake_schema() -> list[dict]:
    """返回前端渲染所需的表单 schema。"""
    groups: dict[str, list[dict]] = {}
    for f in INTAKE_FIELDS:
        item = {
            "key": f.key,
            "label": f.label,
            "input_type": f.input_type,
            "placeholder": f.placeholder,
            "options": f.options,
            "required": f.required,
            "dimension": f.dimension,
        }
        groups.setdefault(f.group, []).append(item)

    return [{"group": g, "fields": fs} for g, fs in groups.items()]
