"""
services/floor_scorer.py
────────────────────────────────────────────────────────────────
可计算底分系统（Computable Floor Scores）

核心思路：
- 每个评分维度拆成 floor_score（证据可计算底分）+ llm_delta（LLM 可调部分）
- floor_score 基于 EvidenceTracer 统计的证据数量和质量自动算出
- LLM 给出的分数不能低于 floor，但可以在 floor 基础上加 delta
- 输出 score_breakdown 让教师可以看到"为什么得这个分"

5 维度 → Rubric 映射：
  empathy   → R1_pain_point, R2_user_evidence
  ideation  → R3_solution, R7_innovation
  business  → R4_business_model, R6_finance
  execution → R8_execution
  pitching  → R9_pitch
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from services.evidence_tracer import EvidenceTracer, get_tracer


# ── 维度 → Rubric 标签映射 ──────────────────────────────────
_DIM_TO_RUBRICS: dict[str, list[str]] = {
    "empathy":   ["R1_pain_point", "R2_user_evidence"],
    "ideation":  ["R3_solution", "R7_innovation"],
    "business":  ["R4_business_model", "R6_finance"],
    "execution": ["R8_execution"],
    "pitching":  ["R9_pitch"],
}

# ── 每条证据的分值贡献 ──────────────────────────────────────
# DATA/QUOTE 是强证据，CLAIM 是弱证据，COMMIT 有一定价值
_EV_WEIGHTS: dict[str, float] = {
    "DATA":   1.2,   # 带数字、来源的陈述 → 高价值
    "QUOTE":  1.0,   # 引用外部来源 → 高价值
    "COMMIT": 0.4,   # 承诺/计划 → 有一定价值
    "CLAIM":  0.2,   # 无数据支撑的主张 → 低价值
}

# ── 底分上限：证据再多也不能超过这个（剩余空间留给 LLM 评主观部分）
_FLOOR_CAP = 6.0

# ── LLM delta 上限：LLM 最多在底分基础上加这么多
_LLM_DELTA_CAP = 4.0


@dataclass
class DimBreakdown:
    """单个维度的评分分解。"""
    dim: str                    # 维度 ID
    floor_score: float          # 证据底分（可计算）
    llm_delta: float            # LLM 调整幅度
    final_score: float          # 最终得分 = max(floor, smoothed)
    data_count: int             # DATA/QUOTE 强证据数
    claim_count: int            # CLAIM 弱证据数
    commit_count: int           # COMMIT 承诺数
    evidence_summary: str       # 可读的证据摘要


def compute_floor_scores(
    session_id: str,
    messages: list[dict],
) -> dict[str, DimBreakdown]:
    """
    基于 EvidenceTracer 为每个维度计算证据底分。

    算法：
    1. 从 tracer 获取每个维度对应 rubric 标签下的证据
    2. 按证据类型加权求和：DATA×1.2 + QUOTE×1.0 + COMMIT×0.4 + CLAIM×0.2
    3. 底分 = min(加权和, _FLOOR_CAP)
    4. 返回每个维度的 DimBreakdown（底分 + 证据统计）
    """
    from services.evidence_tracer import refresh_tracer
    tracer = refresh_tracer(session_id, messages)

    breakdowns: dict[str, DimBreakdown] = {}

    for dim, rubric_keys in _DIM_TO_RUBRICS.items():
        data_count = 0
        claim_count = 0
        commit_count = 0
        weighted_sum = 0.0
        evidence_parts: list[str] = []

        for rk in rubric_keys:
            for ev in tracer.get_by_rubric(rk):
                w = _EV_WEIGHTS.get(ev.ev_type, 0.2)
                weighted_sum += w

                if ev.ev_type in ("DATA", "QUOTE"):
                    data_count += 1
                    if len(evidence_parts) < 3:  # 最多展示 3 条
                        evidence_parts.append(
                            f"✓ 第{ev.turn}轮「{ev.text[:40]}」({ev.ev_type})"
                        )
                elif ev.ev_type == "CLAIM":
                    claim_count += 1
                elif ev.ev_type == "COMMIT":
                    commit_count += 1

        floor = round(min(weighted_sum, _FLOOR_CAP), 1)

        # 构建可读摘要
        if data_count + claim_count + commit_count == 0:
            summary = "尚无任何证据"
        else:
            parts = []
            if data_count > 0:
                parts.append(f"{data_count}条数据证据")
            if claim_count > 0:
                parts.append(f"{claim_count}条未验证主张")
            if commit_count > 0:
                parts.append(f"{commit_count}条计划承诺")
            summary = "、".join(parts)
            if evidence_parts:
                summary += "\n" + "\n".join(evidence_parts)

        breakdowns[dim] = DimBreakdown(
            dim=dim,
            floor_score=floor,
            llm_delta=0.0,       # 后续由 enforce_floor 填充
            final_score=floor,   # 后续由 enforce_floor 覆盖
            data_count=data_count,
            claim_count=claim_count,
            commit_count=commit_count,
            evidence_summary=summary,
        )

    return breakdowns


def enforce_floor(
    llm_scores: dict,
    breakdowns: dict[str, DimBreakdown],
) -> dict:
    """
    用底分约束 LLM 评分：final = max(floor, llm_score)，同时限制 delta。

    规则：
    1. LLM 分 < floor → 提升到 floor（证据保底）
    2. LLM 分 > floor + _LLM_DELTA_CAP → 封顶（防止 LLM 虚高）
    3. 记录 llm_delta = final - floor

    返回: 调整后的 scores dict（同原格式，可直接替换）
    """
    adjusted = {}
    for dim, raw_val in llm_scores.items():
        if not isinstance(raw_val, (int, float)):
            adjusted[dim] = raw_val
            continue

        bd = breakdowns.get(dim)
        if not bd:
            adjusted[dim] = raw_val
            continue

        floor = bd.floor_score

        # 规则 1: 不低于底分
        val = max(raw_val, floor)

        # 规则 2: delta 封顶
        if val > floor + _LLM_DELTA_CAP:
            val = floor + _LLM_DELTA_CAP

        # Clamp [0, 10]
        val = round(max(0, min(10, val)), 1)

        # 记录 delta
        bd.llm_delta = round(val - floor, 1)
        bd.final_score = val
        adjusted[dim] = val

    return adjusted


def format_breakdown_for_response(
    breakdowns: dict[str, DimBreakdown],
) -> dict:
    """
    将 breakdown 格式化为前端/教师可用的 JSON 结构。

    返回格式:
    {
      "empathy": {
        "floor_score": 3.6,
        "llm_delta": 2.4,
        "final_score": 6.0,
        "data_count": 3,
        "claim_count": 1,
        "commit_count": 0,
        "evidence_summary": "3条数据证据、1条未验证主张\n✓ 第2轮「访谈了20个用户」(DATA)..."
      },
      ...
    }
    """
    return {dim: asdict(bd) for dim, bd in breakdowns.items()}
