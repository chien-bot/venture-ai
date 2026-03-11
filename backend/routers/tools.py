"""
routers/tools.py
────────────────────────────────────────────────────────────────
四大创新功能 API：
  1. GET  /api/tools/timeline/{project_id}     — 项目演进时间线
  2. GET  /api/tools/benchmark/{project_id}    — 匿名对标
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
# 2. 跨项目匿名对标
# ──────────────────────────────────────────────────────────────

@router.get("/benchmark/{project_id}")
def get_benchmark(project_id: str):
    """
    返回当前项目在班级中各维度的百分位排名。
    其他项目匿名显示（只显示序号，不显示名称）。
    """
    proj = get_project(project_id)
    if not proj:
        return {"error": "项目不存在"}

    all_projects = get_all_projects()
    scored = [p for p in all_projects if p.get("scores") and any(p["scores"].get(d, 0) > 0 for d in DIMS)]

    if not scored:
        return {
            "project_id": project_id,
            "message": "暂无其他项目数据",
            "benchmark": {},
        }

    my_scores = proj.get("scores", {})
    benchmark: dict[str, dict] = {}

    for d in DIMS:
        my_val = my_scores.get(d, 0)
        all_vals = sorted([p["scores"].get(d, 0) for p in scored])
        n = len(all_vals)
        class_avg = round(sum(all_vals) / n, 1) if n else 0
        class_median = all_vals[n // 2] if n else 0
        # Top 20% threshold
        top20_idx = max(0, int(n * 0.8) - 1)
        top20_threshold = all_vals[top20_idx] if n else 0

        # Percentile: what % of projects score <= my_val
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

    # Class distribution (anonymized): list of scores per dimension
    distribution: dict[str, list[float]] = {}
    for d in DIMS:
        distribution[d] = sorted([p["scores"].get(d, 0) for p in scored])

    return {
        "project_id": project_id,
        "project_name": proj.get("name", ""),
        "class_size": len(scored),
        "benchmark": benchmark,
        "distribution": distribution,
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


# ── F4: Evidence Dashboard ────────────────────────────────────────────

@router.get("/evidence/{project_id}")
def get_evidence_dashboard(project_id: str):
    """
    Aggregate all chat messages for the project and run EvidenceTracer.
    Returns structured breakdown of DATA/CLAIM/QUOTE/COMMIT per Rubric dimension.
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
        }

    tracer = EvidenceTracer(project_id)
    tracer.ingest(all_messages)
    summary = tracer.summarize()
    return {"project_id": project_id, **summary}


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
