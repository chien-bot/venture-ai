"""
services/cheap_diagnostic.py
────────────────────────────────────────────────────────────────
Cheap-First 轻推理层 — 纯规则/检索诊断，零 LLM 调用

核心思路（方向2）：
在 LLM 生成回复之前，先用已有的规则引擎、证据追踪器、超图检索
做一次完整的「轻推理」，输出结构化诊断框架：
  - 缺口列表（哪些维度缺证据）
  - 修复任务（每个缺口的具体行动项）
  - 证据覆盖率（每个 Rubric 的 DATA/CLAIM 分布）
  - 底分分解（来自 floor_scorer）
  - 超图案例匹配摘要

这个框架注入到 LLM system prompt，LLM 只负责：
  1. 把诊断结果转化成自然语言追问
  2. 加入表达质量、叙事逻辑等主观评价
  3. 控制对话语气和节奏

效果：
- LLM 不再需要自己"猜"学生缺什么，诊断精度提升
- 即使 LLM 失败，规则层的诊断结果本身就可以作为 fallback 返回
- 减少 LLM 的推理负担，降低 token 消耗
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from services.evidence_tracer import refresh_tracer, EvidenceTracer, RUBRIC_SIGNALS
from services.floor_scorer import compute_floor_scores, DimBreakdown


# ── Rubric 完整定义（来自 rubric_items.json，内联以避免重复 IO） ──
_RUBRIC_META: dict[str, dict] = {
    "R1_pain_point":     {"name": "痛点定义", "required": ["用户访谈", "问卷调查"]},
    "R2_user_evidence":  {"name": "用户证据", "required": ["访谈引用", "行为数据"]},
    "R3_solution":       {"name": "方案可行性", "required": ["技术路线图", "资源匹配"]},
    "R4_business_model": {"name": "商业模式", "required": ["商业模式画布"]},
    "R5_market":         {"name": "市场与竞争", "required": ["TAM/SAM/SOM", "竞品对比表"]},
    "R6_finance":        {"name": "财务逻辑", "required": ["单位经济模型", "现金流"]},
    "R7_innovation":     {"name": "创新差异化", "required": ["对比矩阵"]},
    "R8_execution":      {"name": "团队执行", "required": ["团队简介", "里程碑"]},
    "R9_pitch":          {"name": "表达材料", "required": ["路演PPT"]},
}

# ── 维度→Rubric 映射（与 floor_scorer 一致） ──
_DIM_TO_RUBRICS: dict[str, list[str]] = {
    "empathy":   ["R1_pain_point", "R2_user_evidence"],
    "ideation":  ["R3_solution", "R7_innovation"],
    "business":  ["R4_business_model", "R6_finance"],
    "execution": ["R8_execution"],
    "pitching":  ["R9_pitch"],
}

_DIM_LABELS: dict[str, str] = {
    "empathy": "痛点发现",
    "ideation": "方案策划",
    "business": "商业建模",
    "execution": "资源杠杆",
    "pitching": "路演表达",
}


@dataclass
class RubricGap:
    """单个 Rubric 的缺口分析。"""
    rubric_key: str
    rubric_name: str
    data_count: int         # 强证据数
    claim_count: int        # 弱主张数
    coverage: str           # "充分" | "部分" | "缺失"
    missing_evidence: list[str]   # 缺少的证据类型
    top_evidence: list[str]       # 已有的最佳证据（最多2条）


@dataclass
class DimDiagnostic:
    """单个维度的诊断结果。"""
    dim: str
    label: str
    floor_score: float
    rubric_gaps: list[RubricGap]
    priority: str            # "urgent" | "attention" | "ok"
    fix_tasks: list[str]     # 具体修复行动


@dataclass
class CheapDiagnostic:
    """完整的轻推理诊断报告。"""
    dimensions: dict[str, DimDiagnostic]
    overall_coverage: float       # 0~1，证据总覆盖率
    urgent_count: int             # urgent 维度数
    top_gaps: list[str]           # 最重要的 3 个缺口描述


def run_cheap_diagnostic(
    session_id: str,
    messages: list[dict],
    current_scores: dict | None = None,
) -> CheapDiagnostic:
    """
    执行 Phase 1 轻推理：纯规则/证据/超图分析，零 LLM 调用。

    输入：session_id + 完整消息历史
    输出：结构化诊断报告

    耗时：< 5ms（纯内存计算）
    """
    # 1. 证据分析
    tracer = refresh_tracer(session_id, messages)

    # 2. 底分计算
    breakdowns = compute_floor_scores(session_id, messages)

    # 3. 逐维度诊断
    dimensions: dict[str, DimDiagnostic] = {}
    total_rubrics = 0
    covered_rubrics = 0
    all_gaps: list[tuple[str, str, int]] = []  # (dim, gap_desc, severity_score)

    for dim, rubric_keys in _DIM_TO_RUBRICS.items():
        rubric_gaps: list[RubricGap] = []
        dim_fix_tasks: list[str] = []

        for rk in rubric_keys:
            meta = _RUBRIC_META.get(rk, {})
            rubric_name = meta.get("name", rk)
            required = meta.get("required", [])

            evs = tracer.get_by_rubric(rk)
            data_count = sum(1 for e in evs if e.ev_type in ("DATA", "QUOTE"))
            claim_count = sum(1 for e in evs if e.ev_type == "CLAIM")

            # 覆盖度判定
            total_rubrics += 1
            if data_count >= 2:
                coverage = "充分"
                covered_rubrics += 1
            elif data_count >= 1 or claim_count >= 2:
                coverage = "部分"
                covered_rubrics += 0.5
            else:
                coverage = "缺失"

            # 缺失证据
            missing = []
            if coverage != "充分":
                missing = required

            # 已有证据摘要
            top_ev = []
            for e in evs[:2]:
                if e.ev_type in ("DATA", "QUOTE"):
                    top_ev.append(f"第{e.turn}轮: {e.text[:50]} ({e.ev_type})")

            gap = RubricGap(
                rubric_key=rk,
                rubric_name=rubric_name,
                data_count=data_count,
                claim_count=claim_count,
                coverage=coverage,
                missing_evidence=missing,
                top_evidence=top_ev,
            )
            rubric_gaps.append(gap)

            # 生成修复任务
            if coverage == "缺失":
                dim_fix_tasks.append(f"补充{rubric_name}相关的数据证据（如{', '.join(required[:2])}）")
                all_gaps.append((dim, f"{_DIM_LABELS[dim]}缺少{rubric_name}证据", 3))
            elif coverage == "部分":
                dim_fix_tasks.append(f"加强{rubric_name}的数据支撑（当前仅有{data_count}条数据+{claim_count}条主张）")
                all_gaps.append((dim, f"{_DIM_LABELS[dim]}的{rubric_name}证据不足", 2))

        # 维度优先级
        bd = breakdowns.get(dim, DimBreakdown(dim=dim, floor_score=0, llm_delta=0,
                                               final_score=0, data_count=0,
                                               claim_count=0, commit_count=0,
                                               evidence_summary=""))
        score = current_scores.get(dim, 0) if current_scores else 0
        has_all_missing = all(g.coverage == "缺失" for g in rubric_gaps)
        has_any_missing = any(g.coverage == "缺失" for g in rubric_gaps)

        if has_all_missing or (score < 3 and has_any_missing):
            priority = "urgent"
        elif has_any_missing or score < 5:
            priority = "attention"
        else:
            priority = "ok"

        dimensions[dim] = DimDiagnostic(
            dim=dim,
            label=_DIM_LABELS[dim],
            floor_score=bd.floor_score,
            rubric_gaps=rubric_gaps,
            priority=priority,
            fix_tasks=dim_fix_tasks,
        )

    # 4. 全局统计
    overall_coverage = covered_rubrics / max(total_rubrics, 1)
    urgent_count = sum(1 for d in dimensions.values() if d.priority == "urgent")

    # 5. Top gaps（按严重度排序）
    all_gaps.sort(key=lambda x: -x[2])
    top_gaps = [g[1] for g in all_gaps[:3]]

    return CheapDiagnostic(
        dimensions=dimensions,
        overall_coverage=round(overall_coverage, 2),
        urgent_count=urgent_count,
        top_gaps=top_gaps,
    )


def format_diagnostic_for_prompt(diag: CheapDiagnostic) -> str:
    """
    将诊断结果格式化为 LLM system prompt 注入块。

    LLM 收到这个块后，只需要：
    1. 将诊断结果转化为自然语言追问
    2. 加入主观评价（表达质量、创新性等）
    3. 不需要自己判断"学生缺什么"——系统已经告诉它了
    """
    lines = ["[Phase1 诊断结果 — 基于规则引擎和证据分析，非 LLM 生成]"]
    lines.append(f"证据总覆盖率：{diag.overall_coverage:.0%}，"
                 f"紧急缺口：{diag.urgent_count}个维度\n")

    if diag.top_gaps:
        lines.append("🔴 最重要的缺口：")
        for g in diag.top_gaps:
            lines.append(f"  • {g}")
        lines.append("")

    for dim in ["empathy", "ideation", "business", "execution", "pitching"]:
        dd = diag.dimensions.get(dim)
        if not dd:
            continue

        icon = {"urgent": "🔴", "attention": "🟡", "ok": "🟢"}[dd.priority]
        lines.append(f"{icon} {dd.label}（底分 {dd.floor_score}）：")

        for gap in dd.rubric_gaps:
            ev_status = f"数据{gap.data_count}条+主张{gap.claim_count}条"
            lines.append(f"  [{gap.coverage}] {gap.rubric_name}：{ev_status}")
            if gap.top_evidence:
                for te in gap.top_evidence[:1]:
                    lines.append(f"        已有: {te}")
            if gap.missing_evidence and gap.coverage != "充分":
                lines.append(f"        缺少: {', '.join(gap.missing_evidence)}")

        if dd.fix_tasks:
            lines.append(f"  → 修复任务：{dd.fix_tasks[0]}")
        lines.append("")

    lines.append("请基于以上诊断结果，用自然语言向学生追问最紧急的缺口。")
    lines.append("你的职责是把结构化诊断变成有温度的苏格拉底式对话，而非机械地列举缺口。")

    return "\n".join(lines)


def format_diagnostic_as_fallback(diag: CheapDiagnostic) -> str:
    """
    当 LLM 不可用时，直接用规则层结果生成用户可读的 fallback 回复。

    虽然不如 LLM 自然，但包含了所有关键诊断信息，比空白/错误页有用得多。
    """
    lines = ["根据我对你项目的分析，以下是目前的诊断：\n"]

    urgent_dims = [d for d in diag.dimensions.values() if d.priority == "urgent"]
    attention_dims = [d for d in diag.dimensions.values() if d.priority == "attention"]
    ok_dims = [d for d in diag.dimensions.values() if d.priority == "ok"]

    if urgent_dims:
        lines.append("**需要重点补充的方面：**")
        for dd in urgent_dims:
            lines.append(f"- **{dd.label}**（证据底分 {dd.floor_score}/10）")
            for task in dd.fix_tasks[:2]:
                lines.append(f"  → {task}")
        lines.append("")

    if attention_dims:
        lines.append("**可以进一步加强的方面：**")
        for dd in attention_dims:
            total_data = sum(g.data_count for g in dd.rubric_gaps)
            lines.append(f"- **{dd.label}**（已有{total_data}条数据证据，底分 {dd.floor_score}）")
            if dd.fix_tasks:
                lines.append(f"  → {dd.fix_tasks[0]}")
        lines.append("")

    if ok_dims:
        ok_names = "、".join(dd.label for dd in ok_dims)
        lines.append(f"**已有充分证据的方面：**{ok_names}\n")

    lines.append(f"当前项目证据覆盖率：**{diag.overall_coverage:.0%}**")

    if diag.top_gaps:
        lines.append("\n**建议你优先回答以下问题：**")
        prompts = {
            "痛点发现缺少痛点定义证据": "你的目标用户是谁？他们遇到了什么具体的问题？你有没有和他们直接交流过？",
            "痛点发现缺少用户证据证据": "你做过用户访谈吗？有多少人？他们怎么描述这个问题？",
            "方案策划缺少方案可行性证据": "你的解决方案具体怎么运作？有什么技术路线？",
            "方案策划缺少创新差异化证据": "和市面上的替代品比，你最核心的差异化是什么？",
            "商业建模缺少商业模式证据": "谁来付钱？怎么收费？用户为什么愿意付这个价格？",
            "商业建模缺少财务逻辑证据": "获取一个客户要花多少钱？一个客户能给你带来多少收入？",
            "资源杠杆缺少团队执行证据": "你的团队有几个人？各自负责什么？3个月内的里程碑是什么？",
            "路演表达缺少表达材料证据": "你能用一句话说清楚你的项目吗？为谁、解决什么、怎么赚钱？",
        }
        for gap_desc in diag.top_gaps[:2]:
            question = prompts.get(gap_desc, "能否针对这个方面提供更多具体的信息？")
            lines.append(f"- {question}")

    return "\n".join(lines)
