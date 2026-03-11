"""
routers/tools.py
────────────────────────────────────────────────────────────────
四大创新功能 API：
  1. GET  /api/tools/timeline/{project_id}     — 项目演进时间线
  2. GET  /api/tools/benchmark/{project_id}    — 匿名对标（超图增强）
  3. POST /api/tools/pitch-check              — Pitch Deck 结构检查
  4. POST /api/tools/interview-analyze        — 用户访谈报告解析
"""
from __future__ import annotations

import re
from fastapi import APIRouter
from pydantic import BaseModel
from services.database import (
    get_score_snapshots, get_all_projects,
    save_interview_analysis, get_interview_analyses,
    save_pitch_check, get_pitch_checks,
    get_project, get_sessions_for_project, get_chat_history,
    get_project_activity_in_range, save_weekly_report,
    get_weekly_reports, get_all_weekly_reports,
    update_learning_task_status,
)
from services.learning_path import get_or_generate_learning_path, generate_learning_path
from services.evidence_tracer import EvidenceTracer
from services.claude_client import chat_completion
from hypergraph.engine import query_hypergraph, search_by_industry
from config import USE_MOCK_API

router = APIRouter(prefix="/api/tools", tags=["tools"])

DIMS = ["empathy", "ideation", "business", "execution", "pitching"]
DIM_LABELS = {
    "empathy": "痛点发现", "ideation": "方案策划",
    "business": "商业建模", "execution": "资源杠杆", "pitching": "路演表达",
}

# ──────────────────────────────────────────────────────────────
# 1. 项目演进时间线
# ──────────────────────────────────────────────────────────────

@router.get("/timeline/{project_id}")
def get_timeline(project_id: str):
    """
    返回该项目的所有得分快照，按轮次排序。
    前端可用折线图展示 5 维度随时间的变化。
    """
    snapshots = get_score_snapshots(project_id)
    proj = get_project(project_id)

    # Build per-dimension series for charting
    series: dict[str, list] = {d: [] for d in DIMS}
    labels: list[str] = []

    for snap in snapshots:
        labels.append(f"第{snap['round_num']}轮")
        for d in DIMS:
            series[d].append(snap["scores"].get(d, 0))

    # Trend: compare first vs latest snapshot
    trend = {}
    if len(snapshots) >= 2:
        first, last = snapshots[0]["scores"], snapshots[-1]["scores"]
        for d in DIMS:
            delta = last.get(d, 0) - first.get(d, 0)
            trend[d] = {"delta": round(delta, 1), "direction": "up" if delta > 0 else "down" if delta < 0 else "flat"}

    return {
        "project_id": project_id,
        "project_name": proj.get("name", "") if proj else "",
        "snapshots": snapshots,
        "labels": labels,
        "series": series,
        "trend": trend,
        "total_rounds": len(snapshots),
    }


# ──────────────────────────────────────────────────────────────
# 2. 跨项目匿名对标（超图增强 + AI 洞察）
# ──────────────────────────────────────────────────────────────

_BENCHMARK_INSIGHT_PROMPT = """你是一位创业导师，正在帮助学生对标分析。
给你以下信息：
1. 学生项目基本信息（行业、技术、当前评分）
2. 班级内排名数据（各维度百分位）
3. 超图竞赛案例库检索结果（同行业/同技术的历史优秀案例）

请生成一段200字以内的对标洞察，内容包括：
- 和历史竞赛案例相比，该项目的差距在哪（1-2条）
- 历史案例中有哪些值得借鉴的成功要素（1-2条）
- 针对最弱维度给出具体改进建议（1条）

以JSON返回，格式：
{"gaps": ["差距1", "差距2"], "learnings": ["借鉴1", "借鉴2"], "suggestion": "改进建议", "summary": "一句话综合评价"}
只返回JSON，不要其他文字。"""


@router.get("/benchmark/{project_id}")
def get_benchmark(project_id: str):
    """
    返回当前项目在班级中各维度的百分位排名，
    同时从超图检索同行业竞赛案例，并由 LLM 生成对标洞察。
    """
    proj = get_project(project_id)
    if not proj:
        return {"error": "项目不存在"}

    all_projects = get_all_projects()
    scored = [p for p in all_projects if p.get("scores") and any(p["scores"].get(d, 0) > 0 for d in DIMS)]

    my_scores = proj.get("scores", {})
    benchmark: dict[str, dict] = {}

    if scored:
        for d in DIMS:
            my_val = my_scores.get(d, 0)
            all_vals = sorted([p["scores"].get(d, 0) for p in scored])
            n = len(all_vals)
            class_avg = round(sum(all_vals) / n, 1) if n else 0
            class_median = all_vals[n // 2] if n else 0
            top20_idx = max(0, int(n * 0.8) - 1)
            top20_threshold = all_vals[top20_idx] if n else 0
            below = sum(1 for v in all_vals if v <= my_val)
            percentile = round(below / n * 100) if n else 0
            benchmark[d] = {
                "my_score": my_val,
                "class_avg": class_avg,
                "class_median": class_median,
                "top20_threshold": top20_threshold,
                "percentile": percentile,
                "rank": n - below + 1,
                "total": n,
                "status": "top20" if percentile >= 80 else "above_avg" if my_val >= class_avg else "below_avg",
            }

    distribution: dict[str, list[float]] = {}
    for d in DIMS:
        distribution[d] = sorted([p["scores"].get(d, 0) for p in scored]) if scored else []

    # ── 超图检索：找同行业/同技术的竞赛案例 ──────────────────
    industry = proj.get("industry", "")
    proj_techs = proj.get("technologies", []) or []
    hypergraph_ctx = query_hypergraph(
        tech_keywords=proj_techs[:5] if proj_techs else None,
        industry=industry,
    )

    # 组装给 LLM 用的超图摘要
    similar_cases = hypergraph_ctx.get("detailed_cases", []) or hypergraph_ctx.get("similar_projects", [])
    risk_patterns = hypergraph_ctx.get("risk_patterns", [])

    # ── LLM 生成对标洞察 ──────────────────────────────────────
    ai_insight: dict = {}
    if not USE_MOCK_API and (similar_cases or risk_patterns):
        try:
            # 找最弱维度
            weakest_dim = min(DIMS, key=lambda d: my_scores.get(d, 0))
            weakest_label = DIM_LABELS.get(weakest_dim, weakest_dim)

            cases_text = ""
            for c in similar_cases[:3]:
                name = c.get("name") or c.get("project", "")
                industry_c = c.get("industry", "")
                success = "; ".join(c.get("success_factors", [])[:2]) if c.get("success_factors") else ""
                risks = "; ".join(c.get("failure_risks", [])[:2]) if c.get("failure_risks") else ""
                moat = ", ".join(c.get("moat", [])[:2]) if c.get("moat") else ""
                cases_text += f"\n- {name}（{industry_c}）"
                if success: cases_text += f"  ✅成功要素：{success}"
                if risks: cases_text += f"  ⚠风险：{risks}"
                if moat: cases_text += f"  壁垒：{moat}"

            risk_text = ""
            for r in risk_patterns[:3]:
                risk_text += f"\n- {r['risk']}（{r['severity']}）: {r.get('note', '')}"

            user_msg = f"""项目名称：{proj.get('name', '')}
行业：{industry}
技术：{', '.join(proj_techs[:5]) if proj_techs else '未指定'}
当前评分：{', '.join(f'{DIM_LABELS[d]}={my_scores.get(d,0)}' for d in DIMS)}
最弱维度：{weakest_label}（{my_scores.get(weakest_dim, 0)}分）

【超图同行业竞赛案例】{cases_text if cases_text else '暂无匹配案例'}

【超图风险模式匹配】{risk_text if risk_text else '暂无风险提示'}"""

            raw = chat_completion(_BENCHMARK_INSIGHT_PROMPT, [{"role": "user", "content": user_msg}], max_tokens=400)
            import json as _j
            m = re.search(r'\{[\s\S]*\}', raw)
            if m:
                ai_insight = _j.loads(m.group(0))
        except Exception:
            pass

    if not ai_insight and similar_cases:
        # Mock fallback: derive insight from hypergraph data directly
        top_case = similar_cases[0]
        ai_insight = {
            "gaps": [f"与「{top_case.get('name', '优秀案例')}」相比，商业模式清晰度有待提升"],
            "learnings": top_case.get("success_factors", ["注重早期用户验证"])[:2] or ["注重早期用户验证"],
            "suggestion": f"重点加强{DIM_LABELS.get(min(DIMS, key=lambda d: my_scores.get(d,0)), '最弱维度')}维度，对标竞赛案例的最佳实践",
            "summary": f"项目处于起步阶段，超图中有 {len(similar_cases)} 个同行业竞赛案例可参考",
        }

    return {
        "project_id": project_id,
        "project_name": proj.get("name", ""),
        "class_size": len(scored),
        "benchmark": benchmark,
        "distribution": distribution,
        # 超图数据
        "hypergraph": {
            "similar_cases": similar_cases[:5],
            "risk_patterns": risk_patterns[:5],
            "biz_strategies": hypergraph_ctx.get("business_strategies", [])[:3],
        },
        # AI 洞察
        "ai_insight": ai_insight,
    }


# ──────────────────────────────────────────────────────────────
# 3. Pitch Deck 结构检查器
# ──────────────────────────────────────────────────────────────

PITCH_STRUCTURE = [
    {"id": "problem",  "name": "问题定义",   "keywords": ["问题", "痛点", "现状", "困境", "不方便", "需求"]},
    {"id": "solution", "name": "解决方案",   "keywords": ["解决方案", "产品", "功能", "服务", "我们做", "方案"]},
    {"id": "market",   "name": "市场规模",   "keywords": ["市场", "TAM", "规模", "亿", "万", "用户群", "目标市场"]},
    {"id": "model",    "name": "商业模式",   "keywords": ["商业模式", "盈利", "收入", "收费", "订阅", "变现", "模式"]},
    {"id": "team",     "name": "团队介绍",   "keywords": ["团队", "创始人", "成员", "经验", "背景", "负责人"]},
    {"id": "traction", "name": "牵引力数据", "keywords": ["用户", "数据", "增长", "收入", "验证", "PMF", "访谈"]},
    {"id": "ask",      "name": "融资需求",   "keywords": ["融资", "投资", "需要", "计划用", "里程碑", "下一步"]},
]

PITCH_SYSTEM_PROMPT = """你是一位创业竞赛评委，专门审核路演材料的叙事结构。

用户会提交路演PPT的文字大纲（可能是标题+要点的列表）。
你需要按照「问题→解决方案→市场→商业模式→团队→牵引力→融资需求」7个模块评估大纲是否结构完整。

对每个模块，你要：
1. 判断大纲是否覆盖了该模块（covered: true/false）
2. 如果有覆盖，给出0-10的充分度评分
3. 给出简短的改进建议（1句话）

请严格以如下JSON格式返回（不要包含其他文字）：
{
  "problem":  {"covered": true, "score": 7, "tip": "建议用数据量化痛点规模"},
  "solution": {"covered": true, "score": 8, "tip": "可补充技术差异化说明"},
  "market":   {"covered": false, "score": 0, "tip": "缺失TAM/SAM/SOM估算"},
  "model":    {"covered": true, "score": 5, "tip": "收入来源不够清晰"},
  "team":     {"covered": false, "score": 0, "tip": "需补充核心成员背景"},
  "traction": {"covered": false, "score": 0, "tip": "若有早期用户/数据请务必展示"},
  "ask":      {"covered": false, "score": 0, "tip": "需明确融资金额和用途"}
}"""


class PitchCheckRequest(BaseModel):
    project_id: str = ""
    outline: str   # The pitch deck outline text


@router.post("/pitch-check")
def check_pitch(req: PitchCheckRequest):
    """Analyze pitch deck outline for structural completeness."""
    outline = req.outline.strip()
    if not outline:
        return {"error": "请提供路演大纲内容"}

    if USE_MOCK_API:
        result = _mock_pitch_check(outline)
    else:
        raw = chat_completion(PITCH_SYSTEM_PROMPT, [{"role": "user", "content": outline}], max_tokens=800)
        result = _parse_pitch_json(raw)

    # Compute overall completeness
    covered = sum(1 for v in result.values() if v.get("covered"))
    avg_score = round(sum(v.get("score", 0) for v in result.values()) / len(result), 1) if result else 0
    missing = [PITCH_STRUCTURE[i]["name"] for i, s in enumerate(PITCH_STRUCTURE) if not result.get(s["id"], {}).get("covered")]
    h14_triggered = len(missing) >= 3  # H14: 路演叙事断裂

    if req.project_id:
        save_pitch_check(req.project_id, outline, result)

    return {
        "result": result,
        "summary": {
            "covered_count": covered,
            "total": len(PITCH_STRUCTURE),
            "avg_score": avg_score,
            "missing_sections": missing,
            "h14_triggered": h14_triggered,
            "overall_grade": "优秀" if avg_score >= 7 else "良好" if avg_score >= 5 else "需改进",
        }
    }


def _mock_pitch_check(outline: str) -> dict:
    text = outline.lower()
    result = {}
    for s in PITCH_STRUCTURE:
        covered = any(kw in outline for kw in s["keywords"])
        score = 6 if covered else 0
        tips = {
            "problem":  "建议用数据量化痛点规模（如：XX万用户面临此问题）",
            "solution": "补充核心功能截图或原型演示链接",
            "market":   "自下而上估算市场规模，提供数据来源",
            "model":    "明确收入流：谁付钱、付多少、为什么付",
            "team":     "突出与项目直接相关的核心能力",
            "traction": "哪怕只有5个用户访谈也要展示",
            "ask":      "明确融资金额和12个月里程碑",
        }
        result[s["id"]] = {"covered": covered, "score": score, "tip": tips.get(s["id"], "请完善此模块")}
    return result


def _parse_pitch_json(raw: str) -> dict:
    import json
    try:
        match = re.search(r"\{[\s\S]*\}", raw)
        if match:
            return json.loads(match.group())
    except Exception:
        pass
    return _mock_pitch_check("")


# ──────────────────────────────────────────────────────────────
# 4. 用户访谈报告解析器
# ──────────────────────────────────────────────────────────────

INTERVIEW_SYSTEM_PROMPT = """你是一位创新创业教育专家，擅长从用户访谈记录中提取结构化信息。

用户会提交原始访谈记录（对话或笔记格式）。
你需要提取以下信息，严格以JSON返回（不要包含其他文字）：

{
  "jtbd_statements": [
    "用户雇佣产品完成的任务描述1",
    "用户雇佣产品完成的任务描述2"
  ],
  "pain_points": [
    {"description": "痛点描述", "frequency": "高/中/低", "intensity": "强/中/弱"}
  ],
  "payment_willingness": {
    "willing": true,
    "price_range": "50-100元/月",
    "evidence_quote": "用户原话"
  },
  "key_quotes": [
    {"quote": "用户原话", "insight": "洞察"}
  ],
  "rubric_evidence": {
    "R1": "对应R1痛点定义的证据摘要",
    "R2": "对应R2用户证据的证据摘要"
  },
  "summary": "一段话总结核心发现"
}"""


class InterviewRequest(BaseModel):
    project_id: str = ""
    interview_text: str


@router.post("/interview-analyze")
def analyze_interview(req: InterviewRequest):
    """Parse user interview transcript and extract structured evidence."""
    text = req.interview_text.strip()
    if not text or len(text) < 20:
        return {"error": "访谈内容太短，请至少输入50字"}

    if USE_MOCK_API:
        result = _mock_interview_analyze(text)
    else:
        raw = chat_completion(
            INTERVIEW_SYSTEM_PROMPT,
            [{"role": "user", "content": f"以下是访谈记录：\n\n{text}"}],
            max_tokens=1200
        )
        result = _parse_interview_json(raw)

    if req.project_id:
        save_interview_analysis(req.project_id, text, result)

    return {"result": result, "project_id": req.project_id}


@router.get("/interview-history/{project_id}")
def get_interview_history(project_id: str):
    analyses = get_interview_analyses(project_id)
    return {"project_id": project_id, "analyses": analyses}


@router.get("/pitch-history/{project_id}")
def get_pitch_history(project_id: str):
    checks = get_pitch_checks(project_id)
    return {"project_id": project_id, "checks": checks}


# ── F4: Evidence Dashboard（超图增强 + AI 分析） ────────────────────────

_EVIDENCE_ANALYSIS_PROMPT = """你是一位创业导师，帮助学生分析他们的证据质量。
给你：
1. 学生对话中提取的证据统计（DATA/CLAIM/QUOTE/COMMIT 各类数量，各Rubric维度覆盖情况）
2. 无数据支撑的弱主张列表
3. 超图竞赛案例中类似项目的证据质量参照

请生成证据质量分析报告，以JSON返回：
{
  "quality_score": 0-10分,
  "quality_label": "充分/一般/薄弱",
  "strengths": ["优势1", "优势2"],
  "weak_dimensions": ["待加强的Rubric维度1", "维度2"],
  "hypergraph_comparison": "与超图案例相比的1句话评价",
  "next_actions": ["具体行动建议1", "具体行动建议2", "具体行动建议3"],
  "summary": "50字以内总结"
}
只返回JSON，不要其他文字。"""


@router.get("/evidence/{project_id}")
def get_evidence_dashboard(project_id: str):
    """
    Aggregate all chat messages for the project and run EvidenceTracer.
    Also maps evidence to hypergraph nodes and generates AI quality analysis.
    """
    sessions = get_sessions_for_project(project_id)
    all_messages: list[dict] = []
    for sess in sessions:
        all_messages.extend(get_chat_history(sess["session_id"]))

    if not all_messages:
        return {
            "project_id": project_id,
            "total": 0,
            "by_type": {"DATA": 0, "QUOTE": 0, "CLAIM": 0, "COMMIT": 0},
            "by_rubric": {},
            "weak_claims": [],
            "evidence_list": [],
            "hypergraph_nodes": [],
            "ai_analysis": None,
        }

    tracer = EvidenceTracer(project_id)
    tracer.ingest(all_messages)
    summary = tracer.summarize()

    # ── 超图节点映射：从证据文本提取技术/行业关键词，查超图 ──
    proj = get_project(project_id)
    industry = proj.get("industry", "") if proj else ""
    proj_techs = (proj.get("technologies", []) or []) if proj else []

    # Also extract keywords from evidence texts
    evidence_texts = " ".join(e["text"] for e in summary.get("evidence_list", [])[:30])
    hypergraph_ctx = query_hypergraph(
        tech_keywords=proj_techs[:5] if proj_techs else None,
        industry=industry,
    )
    similar_cases = hypergraph_ctx.get("detailed_cases", []) or hypergraph_ctx.get("similar_projects", [])

    # Map evidence rubric coverage to hypergraph concept nodes
    from hypergraph.engine import _find_concept_id, get_neighbors, _nodes
    _RUBRIC_TO_CONCEPT = {
        "R1_pain_point":     "痛点",
        "R2_user_evidence":  "用户访谈",
        "R3_solution":       "解决方案",
        "R4_business_model": "商业模式",
        "R5_market":         "市场规模",
        "R6_finance":        "财务规划",
        "R7_innovation":     "护城河",
        "R8_execution":      "精益创业",
        "R9_pitch":          "路演",
    }
    hypergraph_nodes = []
    by_rubric = summary.get("by_rubric", {})
    for rubric_key, concept_label in _RUBRIC_TO_CONCEPT.items():
        cid = _find_concept_id(concept_label)
        count = by_rubric.get(rubric_key, 0)
        if cid:
            node = _nodes.get(cid, {})
            neighbors = [n["label"] for n in get_neighbors(cid) if n["type"] == "Concept"][:3]
            hypergraph_nodes.append({
                "rubric": rubric_key,
                "concept": node.get("label", concept_label),
                "evidence_count": count,
                "status": "covered" if count > 0 else "missing",
                "related_concepts": neighbors,
            })

    # ── LLM 生成证据质量分析 ──────────────────────────────────
    ai_analysis: dict | None = None
    if not USE_MOCK_API:
        try:
            weak_claims_text = "\n".join(
                f"  - 第{w['turn']}轮：「{w['text'][:60]}」"
                for w in summary.get("weak_claims", [])[:5]
            ) or "  （无）"

            covered_rubrics = [k for k, v in by_rubric.items() if v > 0]
            missing_rubrics = [k for k in _RUBRIC_TO_CONCEPT if k not in covered_rubrics]

            case_ref = ""
            if similar_cases:
                c = similar_cases[0]
                case_ref = f"超图参考案例「{c.get('name','')}」：{', '.join(c.get('success_factors',[])[:2])}"

            user_msg = f"""项目：{proj.get('name','') if proj else project_id}，行业：{industry}
证据统计：DATA={summary['by_type']['DATA']} QUOTE={summary['by_type']['QUOTE']} CLAIM={summary['by_type']['CLAIM']} COMMIT={summary['by_type']['COMMIT']}
已覆盖Rubric维度：{', '.join(covered_rubrics) or '无'}
缺失Rubric维度：{', '.join(missing_rubrics) or '无'}
无数据支撑的弱主张：
{weak_claims_text}
{case_ref}"""

            raw = chat_completion(_EVIDENCE_ANALYSIS_PROMPT, [{"role": "user", "content": user_msg}], max_tokens=500)
            import json as _j
            m = re.search(r'\{[\s\S]*\}', raw)
            if m:
                ai_analysis = _j.loads(m.group(0))
        except Exception:
            pass

    if not ai_analysis:
        # Rule-based fallback
        total = summary.get("total", 0)
        data_count = summary["by_type"].get("DATA", 0)
        claim_count = summary["by_type"].get("CLAIM", 0)
        covered_count = len([k for k, v in by_rubric.items() if v > 0])
        quality_score = min(10, round(data_count * 1.5 + covered_count * 0.5))
        ai_analysis = {
            "quality_score": quality_score,
            "quality_label": "充分" if quality_score >= 7 else "一般" if quality_score >= 4 else "薄弱",
            "strengths": [f"已提供 {data_count} 条有数据支撑的陈述"] if data_count > 0 else [],
            "weak_dimensions": [k for k, v in by_rubric.items() if v == 0][:3],
            "hypergraph_comparison": f"超图中有 {len(similar_cases)} 个同行业案例可参考" if similar_cases else "暂无超图匹配案例",
            "next_actions": [
                "用具体数据（数字、来源）替代主观判断",
                "补充用户访谈记录（R2证据）",
                "引用行业报告数据支撑市场规模主张",
            ][:3 - min(2, data_count)],
            "summary": f"共收集 {total} 条证据，覆盖 {covered_count}/9 个评分维度",
        }

    return {
        "project_id": project_id,
        **summary,
        "hypergraph_nodes": hypergraph_nodes,
        "ai_analysis": ai_analysis,
    }


def _mock_interview_analyze(text: str) -> dict:
    has_price = any(w in text for w in ["元", "块", "钱", "付费", "价格", "收费"])
    has_pain = any(w in text for w in ["麻烦", "困难", "不方便", "痛苦", "浪费", "问题"])
    return {
        "jtbd_statements": [
            "帮我在繁忙时快速找到可信赖的解决方案，让我不用花时间反复比较",
            "帮我减少决策成本，直接给我最优选项"
        ],
        "pain_points": [
            {"description": "信息太分散，需要在多个平台对比", "frequency": "高", "intensity": "强"},
            {"description": "现有方案质量参差不齐，难以判断", "frequency": "中", "intensity": "中"},
        ],
        "payment_willingness": {
            "willing": has_price,
            "price_range": "50-150元/月" if has_price else "未明确",
            "evidence_quote": next((s for s in text.split("。") if any(w in s for w in ["元", "付", "买"])), "未找到明确支付意愿表述"),
        },
        "key_quotes": [
            {"quote": text[:80] + "...", "insight": "用户表达了核心需求，可作为R2证据"},
        ],
        "rubric_evidence": {
            "R1": "访谈揭示了明确的用户痛点：信息分散、决策成本高" if has_pain else "痛点描述需进一步挖掘",
            "R2": f"本次访谈提供了{'有效' if len(text) > 100 else '初步'}的用户一手证据",
        },
        "summary": f"本次访谈{'揭示了明确的支付意愿和痛点，可直接用于R1/R2证据' if has_price and has_pain else '提供了初步洞察，建议补充更多量化数据'}。",
    }


def _parse_interview_json(raw: str) -> dict:
    import json
    try:
        match = re.search(r"\{[\s\S]*\}", raw)
        if match:
            return json.loads(match.group())
    except Exception:
        pass
    return _mock_interview_analyze(raw)


# ──────────────────────────────────────────────────────────────
# F2-adv: AI 周报 / 进度报告
# ──────────────────────────────────────────────────────────────

from datetime import datetime, timedelta
import json as _json


def _current_week_range(week_start: str | None = None):
    """Return (start, end) ISO date strings for the requested or current week."""
    if week_start:
        start = datetime.strptime(week_start, "%Y-%m-%d")
    else:
        today = datetime.now()
        start = today - timedelta(days=today.weekday())  # Monday
    end = start + timedelta(days=6)
    return start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d")


@router.get("/weekly-report/{project_id}")
def get_weekly_report(project_id: str, week_start: str = ""):
    """Generate or retrieve weekly report for a project."""
    ws, we = _current_week_range(week_start or None)

    # Check if report already exists
    existing = get_weekly_reports(project_id)
    for r in existing:
        if r.get("week_start") == ws:
            return r

    # Generate new report from activity data
    activity = get_project_activity_in_range(project_id, ws, we)
    proj = get_project(project_id)

    summary = {
        "week_start": ws,
        "week_end": we,
        "highlights": [],
        "score_changes": {},
        "action_items": [],
        "stats": {
            "sessions": activity.get("session_count", 0),
            "messages": activity.get("message_count", 0),
        },
    }

    # Score changes
    snapshots = activity.get("snapshots", [])
    if snapshots:
        first = snapshots[0].get("scores", {})
        last = snapshots[-1].get("scores", {})
        for d in DIMS:
            delta = last.get(d, 0) - first.get(d, 0)
            if delta != 0:
                summary["score_changes"][d] = {
                    "from": first.get(d, 0), "to": last.get(d, 0),
                    "delta": round(delta, 1),
                }

    # Auto-generate highlights
    if activity.get("session_count", 0) > 0:
        summary["highlights"].append(f"本周共进行了 {activity['session_count']} 次对话")
    if activity.get("message_count", 0) > 0:
        summary["highlights"].append(f"交流了 {activity['message_count']} 条消息")
    if summary["score_changes"]:
        improved = [DIM_LABELS.get(d, d) for d, v in summary["score_changes"].items() if v["delta"] > 0]
        if improved:
            summary["highlights"].append(f"{'、'.join(improved)} 维度有所提升")

    # Action items based on weak scores
    scores = proj.get("scores", {}) if proj else {}
    for d in DIMS:
        if scores.get(d, 0) < 5:
            summary["action_items"].append(f"加强 {DIM_LABELS.get(d, d)} 维度（当前 {scores.get(d, 0)} 分）")

    if not summary["action_items"]:
        summary["action_items"].append("继续保持良好势头，尝试更深入的用户验证")

    # Save report
    save_weekly_report(project_id, proj.get("owner_id", "") if proj else "", ws, we, summary)

    return {
        "project_id": project_id,
        "project_name": proj.get("name", "") if proj else "",
        **summary,
    }


@router.get("/weekly-reports/all")
def get_all_reports(week_start: str = ""):
    """Get weekly reports for all projects (teacher view)."""
    ws, we = _current_week_range(week_start or None)
    all_projects = get_all_projects()
    reports = []
    for p in all_projects:
        try:
            report = get_weekly_report(p["project_id"], week_start=ws)
            reports.append(report)
        except Exception:
            continue
    return {"week_start": ws, "week_end": we, "reports": reports, "total": len(reports)}


# ──────────────────────────────────────────────────────────────
# F5-adv: 个性化学习路径
# ──────────────────────────────────────────────────────────────

class TaskStatusRequest(BaseModel):
    status: str  # "pending" | "completed"


@router.get("/learning-path/{project_id}")
def get_learning_path(project_id: str):
    """Get or generate personalized learning path."""
    return get_or_generate_learning_path(project_id)


@router.post("/learning-path/{project_id}/generate")
def regenerate_learning_path(project_id: str):
    """Force regenerate learning path based on current scores."""
    tasks = generate_learning_path(project_id)
    return {"project_id": project_id, "tasks": tasks, "regenerated": True}


@router.post("/learning-path/task/{task_id}/status")
def update_task_status(task_id: str, req: TaskStatusRequest):
    """Manually update a learning task status."""
    update_learning_task_status(task_id, req.status)
    return {"ok": True, "task_id": task_id, "status": req.status}
