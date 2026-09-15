"""Third-stage proposal gate, versioned artifacts and human acceptance ledger."""

import json
import hashlib
import re
from math import ceil
from typing import Literal

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from services.access_control import require_project, require_teacher, require_user
from services.database import get_conn

router = APIRouter(prefix="/api/stage3", tags=["stage3"])

DOCUMENT_KINDS = {"proposal", "plan", "slides", "script", "qa", "stage_summary"}
FINAL_DOCUMENT_KINDS = ("proposal", "plan", "slides", "script", "qa", "stage_summary")
GATE_KEYS = ("G1", "G2", "G3", "G4", "G5", "G6")
SCORE_SCALES = {
    "project": {"social_value": 20, "evidence_process": 20, "innovation": 20, "feasibility": 25, "team_consistency": 15},
    "agent": {"three_flows": 20, "traceability": 20, "effectiveness": 25, "correctness": 20, "human_boundary": 15},
    "defense": {"narrative_time": 20, "logic_consistency": 20, "answers": 25, "evidence_boundary": 20, "team_delivery": 15},
}
FLOW_AGENTS = {"F1": {"tutor"}, "F2": {"coach", "competition", "defense", "plan_draft"}, "F3": {"grader"}}


def _rows(query: str, args: tuple = ()) -> list[dict]:
    with get_conn() as conn:
        return [dict(row) for row in conn.execute(query, args).fetchall()]


def _latest_document(project_id: str, kind: str) -> dict | None:
    rows = _rows(
        "SELECT * FROM stage3_documents WHERE project_id=? AND kind=? ORDER BY version DESC LIMIT 1",
        (project_id, kind),
    )
    return rows[0] if rows else None


def _document(project_id: str, kind: str, version: int) -> dict | None:
    rows = _rows(
        "SELECT * FROM stage3_documents WHERE project_id=? AND kind=? AND version=?",
        (project_id, kind, version),
    )
    return rows[0] if rows else None


def _gate(project_id: str) -> dict:
    proposal = _latest_document(project_id, "proposal")
    if not proposal:
        return {"approved": False, "proposal_version": None, "review": None}
    reviews = _rows(
        "SELECT * FROM stage3_gate_reviews WHERE project_id=? AND proposal_version=? ORDER BY id DESC LIMIT 1",
        (project_id, proposal["version"]),
    )
    review = reviews[0] if reviews else None
    if review:
        review["criteria"] = json.loads(review.pop("criteria_json"))
    return {
        "approved": bool(review and review["decision"] == "approved"),
        "proposal_version": proposal["version"],
        "review": review,
    }


def _latest_scores(project_id: str) -> dict:
    rows = _rows("SELECT * FROM stage3_scores WHERE project_id=? ORDER BY id DESC", (project_id,))
    result = {}
    for row in rows:
        if row["category"] not in result:
            row["scores"] = json.loads(row.pop("scores_json"))
            result[row["category"]] = row
    return result


def _score_is_current(score: dict | None, gate: dict, plan: dict | None) -> bool:
    return bool(
        score and plan and
        score["proposal_version"] == gate["proposal_version"] and
        score["plan_version"] == plan["version"]
    )


def _overview(project_id: str) -> dict:
    gate = _gate(project_id)
    docs = {kind: _latest_document(project_id, kind) for kind in FINAL_DOCUMENT_KINDS}
    scores = _latest_scores(project_id)
    use_records = _rows(
        "SELECT * FROM stage3_use_records WHERE project_id=? ORDER BY id", (project_id,)
    )
    flows = sorted({row["flow"] for row in use_records})
    required_docs = ["plan", "slides", "script", "qa", "stage_summary"]
    current_plan_version = docs["plan"]["version"] if docs["plan"] and docs["plan"]["source"] == "student" else None
    missing = []
    if not gate["approved"]:
        missing.append("立项 G1–G6 尚未由教师全部通过")
    for kind in required_docs:
        if not docs[kind]:
            missing.append(f"缺少 {kind} 的版本材料")
        elif docs[kind]["basis_version"] != gate["proposal_version"]:
            missing.append(f"{kind} 与当前立项版本不一致")
        elif docs[kind]["source"] != "student":
            missing.append(f"{kind} 仍是 Agent 草稿，学生尚未提交核验修改版")
        elif kind in ("slides", "script", "qa") and docs[kind]["plan_version"] != current_plan_version:
            missing.append(f"{kind} 未绑定当前学生计划书版本")
    for flow in FLOW_AGENTS:
        if flow not in flows:
            missing.append(f"缺少 {flow} 的真实运行、人工处理与成果映射记录")
    if "F1" in flows and not any(r["flow"] == "F1" and r["learning_check"] for r in use_records):
        missing.append("F1 缺少理解检查与错误纠正记录")
    if "F3" in flows and not any(r["flow"] == "F3" and r["verification_run_id"] for r in use_records):
        missing.append("F3 缺少修改后的真实复验运行")
    for category in ("project", "agent"):
        if category not in scores:
            missing.append(f"缺少教师的 {category} 100 分评审")
        elif (
            scores[category]["proposal_version"] != gate["proposal_version"] or
            scores[category]["plan_version"] != current_plan_version
        ):
            missing.append(f"{category} 评分未绑定当前立项书与计划书版本")
        elif scores[category]["total"] < 60:
            missing.append(f"{category} 未达到独立 60 分门槛")
    if not _rows("SELECT id FROM stage3_evidence_items WHERE project_id=? LIMIT 1", (project_id,)):
        missing.append("缺少 F/I/H/S 证据台账")
    final_rows = _rows(
        "SELECT * FROM stage3_final_reviews WHERE project_id=? ORDER BY id DESC LIMIT 1", (project_id,)
    )
    final_review = final_rows[0] if final_rows else None
    if final_review:
        final_review["current"] = (
            final_review["proposal_version"] == gate["proposal_version"] and
            final_review["plan_version"] == current_plan_version
        )
    progress = _rows("SELECT * FROM stage3_daily_progress WHERE project_id=? ORDER BY day", (project_id,))
    completed_days = {row["day"] for row in progress}
    for day in range(1, 10):
        if day not in completed_days:
            missing.append(f"缺少 D{day} 进展记录")
    return {
        "project_id": project_id,
        "gate": gate,
        "documents": docs,
        "scores": scores,
        "flow_coverage": flows,
        "use_records": use_records,
        "missing": missing,
        "ready_for_acceptance": not missing,
        "final_review": final_review,
        "daily_progress": progress,
    }


class DocumentInput(BaseModel):
    kind: Literal["proposal", "plan", "slides", "script", "qa", "stage_summary"]
    content: str = Field(min_length=20, max_length=200000)
    source: Literal["student", "agent_draft", "external"] = "student"
    basis_version: int | None = None
    plan_version: int | None = None
    timed_seconds: int | None = None
    note: str = Field(default="", max_length=2000)


@router.get("/{project_id}/overview")
def overview(project_id: str, request: Request):
    require_project(request, project_id)
    return _overview(project_id)


@router.post("/{project_id}/documents")
def save_document(project_id: str, req: DocumentInput, request: Request):
    require_project(request, project_id)
    user = require_user(request)
    gate = _gate(project_id)
    if req.kind != "proposal":
        if not gate["approved"]:
            raise HTTPException(409, "立项尚未通过，不能创建第三阶段正式材料")
        if req.basis_version != gate["proposal_version"]:
            raise HTTPException(409, "材料必须绑定当前已通过的立项版本")
        if req.kind in ("slides", "script", "qa"):
            plan = _latest_document(project_id, "plan")
            if not plan or plan["source"] != "student" or req.plan_version != plan["version"]:
                raise HTTPException(409, "PPT、讲稿与问答库必须绑定当前学生核验的计划书版本")
    if req.kind == "script" and (req.timed_seconds is None or not 1 <= req.timed_seconds <= 600):
        raise HTTPException(422, "讲稿必须记录实际计时，且须在10分钟内完成")
    if req.kind == "qa":
        question_count = len(re.findall(r"[？?]", req.content))
        if question_count < 10:
            raise HTTPException(422, "问答库至少需要10个高风险问题及回答")
    with get_conn() as conn:
        row = conn.execute(
            "SELECT COALESCE(MAX(version),0)+1 AS next_version FROM stage3_documents WHERE project_id=? AND kind=?",
            (project_id, req.kind),
        ).fetchone()
        version = row["next_version"]
        if version > 1 and len(req.note.strip()) < 8:
            raise HTTPException(422, "再次提交必须写明上轮反馈、具体修改和验证结果")
        conn.execute(
            """INSERT INTO stage3_documents
               (project_id,kind,version,basis_version,plan_version,content,content_hash,timed_seconds,source,note,created_by)
               VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (project_id, req.kind, version, req.basis_version if req.kind != "proposal" else None,
             req.plan_version, req.content, hashlib.sha256(req.content.encode()).hexdigest(),
             req.timed_seconds, req.source, req.note, user["user_id"]),
        )
    return _document(project_id, req.kind, version)


@router.get("/{project_id}/documents")
def list_documents(project_id: str, request: Request, kind: str = ""):
    require_project(request, project_id)
    if kind and kind not in DOCUMENT_KINDS:
        raise HTTPException(400, "未知材料类型")
    if kind:
        return {"documents": _rows(
            "SELECT * FROM stage3_documents WHERE project_id=? AND kind=? ORDER BY id DESC",
            (project_id, kind),
        )}
    return {"documents": _rows(
        "SELECT * FROM stage3_documents WHERE project_id=? ORDER BY id DESC", (project_id,)
    )}


class GateReviewInput(BaseModel):
    proposal_version: int
    criteria: dict[str, bool]
    decision: Literal["approved", "revise"]
    feedback: str = Field(min_length=8, max_length=4000)


@router.post("/{project_id}/gate-review")
def gate_review(project_id: str, req: GateReviewInput, request: Request):
    user = require_teacher(request)
    require_project(request, project_id)
    current = _latest_document(project_id, "proposal")
    if not current or req.proposal_version != current["version"]:
        raise HTTPException(409, "只能复审当前立项书版本")
    if current["source"] != "student":
        raise HTTPException(409, "立项书必须由学生核验并提交，不能直接通过 Agent 草稿")
    if set(req.criteria) != set(GATE_KEYS):
        raise HTTPException(422, "必须逐项填写 G1–G6")
    if req.decision == "approved" and not all(req.criteria.values()):
        raise HTTPException(422, "六项均达到才能通过立项")
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO stage3_gate_reviews
               (project_id,proposal_version,criteria_json,decision,feedback,reviewer_id)
               VALUES (?,?,?,?,?,?)""",
            (project_id, req.proposal_version, json.dumps(req.criteria),
             req.decision, req.feedback, user["user_id"]),
        )
    return _gate(project_id)


class UseRecordInput(BaseModel):
    run_id: str
    flow: Literal["F1", "F2", "F3"]
    task: str = Field(min_length=8, max_length=2000)
    material_kind: Literal["proposal", "plan", "slides", "script", "qa", "stage_summary"]
    material_version: int
    action: Literal["adopted", "rejected", "rewritten", "supplemented"]
    reason: str = Field(min_length=8, max_length=3000)
    learning_check: str = Field(default="", max_length=3000)
    issue_location: str = Field(default="", max_length=1000)
    verification_run_id: str = ""
    result_kind: str | None = None
    result_version: int | None = None
    evidence_ref: str = Field(min_length=4, max_length=1000)
    effect_judgment: str = Field(min_length=8, max_length=2000)


@router.post("/{project_id}/use-records")
def add_use_record(project_id: str, req: UseRecordInput, request: Request):
    require_project(request, project_id)
    user = require_user(request)
    runs = _rows("SELECT * FROM agent_runs WHERE run_id=?", (req.run_id,))
    if not runs or runs[0]["project_id"] != project_id or runs[0]["status"] != "completed":
        raise HTTPException(422, "run_id 不属于本项目已完成的真实运行")
    if runs[0]["flow"] not in FLOW_AGENTS[req.flow]:
        raise HTTPException(422, "运行类型与 F1/F2/F3 流程不符")
    if req.flow == "F1" and len(req.learning_check.strip()) < 8:
        raise HTTPException(422, "F1 必须记录理解检查与错误纠正")
    if req.flow in ("F2", "F3") and (req.result_kind is None or req.result_version is None):
        raise HTTPException(422, "F2/F3 必须映射到修改后的成果版本")
    if req.flow == "F3" and req.result_kind == req.material_kind and req.result_version == req.material_version:
        raise HTTPException(422, "F3 的复验成果必须是修改后的新版本")
    if req.flow == "F3":
        if not req.issue_location.strip() or not req.verification_run_id:
            raise HTTPException(422, "F3 必须记录问题位置和修改后的复验 run_id")
        verified = _rows("SELECT * FROM agent_runs WHERE run_id=?", (req.verification_run_id,))
        if not verified or verified[0]["project_id"] != project_id or verified[0]["status"] != "completed" or verified[0]["flow"] != "grader" or verified[0]["run_id"] == req.run_id:
            raise HTTPException(422, "复验必须是本项目另一次完成的评分运行")
    if not _document(project_id, req.material_kind, req.material_version):
        raise HTTPException(422, "输入材料版本不存在")
    if (req.result_kind is None) != (req.result_version is None):
        raise HTTPException(422, "成果类型和版本必须同时填写")
    if req.result_kind and (
        req.result_kind not in DOCUMENT_KINDS or
        not _document(project_id, req.result_kind, req.result_version)
    ):
        raise HTTPException(422, "成果材料版本不存在")
    with get_conn() as conn:
        cursor = conn.execute(
            """INSERT INTO stage3_use_records
               (project_id,run_id,flow,task,material_kind,material_version,action,reason,
                learning_check,issue_location,verification_run_id,result_kind,result_version,
                evidence_ref,effect_judgment,created_by)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (project_id, req.run_id, req.flow, req.task, req.material_kind,
             req.material_version, req.action, req.reason, req.learning_check,
             req.issue_location, req.verification_run_id, req.result_kind,
             req.result_version, req.evidence_ref, req.effect_judgment, user["user_id"]),
        )
        record_id = cursor.lastrowid
    return _rows("SELECT * FROM stage3_use_records WHERE id=?", (record_id,))[0]


class EvidenceInput(BaseModel):
    label: Literal["F", "I", "H", "S"]
    claim: str = Field(min_length=4, max_length=4000)
    source_ref: str = Field(default="", max_length=2000)
    formula: str = Field(default="", max_length=2000)


@router.post("/{project_id}/evidence")
def add_evidence(project_id: str, req: EvidenceInput, request: Request):
    require_project(request, project_id)
    user = require_user(request)
    if req.label == "F" and len(req.source_ref.strip()) < 5:
        raise HTTPException(422, "F（事实）必须填写可定位来源")
    if req.label == "S" and "模拟" not in (req.source_ref + req.claim):
        raise HTTPException(422, "S（模拟）必须明确标出模拟性质")
    with get_conn() as conn:
        cursor = conn.execute(
            """INSERT INTO stage3_evidence_items
               (project_id,label,claim,source_ref,formula,created_by) VALUES (?,?,?,?,?,?)""",
            (project_id, req.label, req.claim, req.source_ref, req.formula, user["user_id"]),
        )
        evidence_id = cursor.lastrowid
    return _rows("SELECT * FROM stage3_evidence_items WHERE id=?", (evidence_id,))[0]


@router.get("/{project_id}/evidence")
def list_evidence(project_id: str, request: Request):
    require_project(request, project_id)
    return {"items": _rows("SELECT * FROM stage3_evidence_items WHERE project_id=? ORDER BY id", (project_id,))}


class DailyProgressInput(BaseModel):
    day: int = Field(ge=1, le=9)
    goal: str = Field(min_length=4, max_length=2000)
    artifact: str = Field(min_length=4, max_length=2000)
    agent_evidence: str = Field(min_length=4, max_length=2000)
    risk_next: str = Field(min_length=4, max_length=2000)


@router.put("/{project_id}/daily-progress")
def save_daily_progress(project_id: str, req: DailyProgressInput, request: Request):
    require_project(request, project_id)
    user = require_user(request)
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO stage3_daily_progress
               (project_id,day,goal,artifact,agent_evidence,risk_next,created_by)
               VALUES (?,?,?,?,?,?,?)
               ON CONFLICT(project_id,day) DO UPDATE SET
               goal=excluded.goal, artifact=excluded.artifact,
               agent_evidence=excluded.agent_evidence, risk_next=excluded.risk_next,
               created_by=excluded.created_by, created_at=datetime('now')""",
            (project_id, req.day, req.goal, req.artifact, req.agent_evidence,
             req.risk_next, user["user_id"]),
        )
    return _rows("SELECT * FROM stage3_daily_progress WHERE project_id=? AND day=?", (project_id, req.day))[0]


class ScoreInput(BaseModel):
    category: Literal["project", "agent", "defense"]
    scores: dict[str, int]
    feedback: str = Field(min_length=8, max_length=4000)


@router.post("/{project_id}/scores")
def add_score(project_id: str, req: ScoreInput, request: Request):
    user = require_teacher(request)
    require_project(request, project_id)
    if not _gate(project_id)["approved"]:
        raise HTTPException(409, "立项未通过，不能进行正式评分")
    overview_data = _overview(project_id)
    required_docs = ("plan", "slides", "script", "qa", "stage_summary")
    docs = overview_data["documents"]
    current_plan = docs["plan"]
    if any(
        not docs[kind] or docs[kind]["source"] != "student" or
        docs[kind]["basis_version"] != overview_data["gate"]["proposal_version"]
        for kind in required_docs
    ) or any(
        docs[kind]["plan_version"] != current_plan["version"]
        for kind in ("slides", "script", "qa")
    ):
        raise HTTPException(409, "正式评分前必须提交全部学生核验版材料")
    if req.category == "agent" and set(overview_data["flow_coverage"]) != set(FLOW_AGENTS):
        raise HTTPException(409, "Agent 评分前必须完成 F1/F2/F3 三流程证据")
    scale = SCORE_SCALES[req.category]
    if set(req.scores) != set(scale) or any(
        isinstance(req.scores[k], bool) or req.scores[k] < 0 or req.scores[k] > limit
        for k, limit in scale.items()
    ):
        raise HTTPException(422, "评分维度或分值不符合报告中的100分表")
    total = sum(req.scores.values())
    with get_conn() as conn:
        cursor = conn.execute(
            """INSERT INTO stage3_scores
               (project_id,category,scores_json,total,proposal_version,plan_version,feedback,reviewer_id)
               VALUES (?,?,?,?,?,?,?,?)""",
            (project_id, req.category, json.dumps(req.scores), total,
             overview_data["gate"]["proposal_version"],
             overview_data["documents"]["plan"]["version"], req.feedback, user["user_id"]),
        )
        score_id = cursor.lastrowid
    return {"id": score_id, "category": req.category, "total": total, "pass": total >= 60}


class FinalReviewInput(BaseModel):
    decision: Literal["pass", "conditional", "fail"]
    redline: bool = False
    feedback: str = Field(min_length=8, max_length=4000)


@router.post("/{project_id}/final-review")
def final_review(project_id: str, req: FinalReviewInput, request: Request):
    user = require_teacher(request)
    require_project(request, project_id)
    overview_data = _overview(project_id)
    if req.decision == "pass" and (req.redline or not overview_data["ready_for_acceptance"]):
        raise HTTPException(409, "双门槛、材料、三流程或诚信条件未满足，不能通过")
    if req.decision == "conditional" and (
        req.redline or not overview_data["gate"]["approved"] or
        any(overview_data["scores"].get(k, {}).get("total", 0) < 60 for k in ("project", "agent"))
    ):
        raise HTTPException(409, "有条件通过只允许非核心缺项且双门槛已达标")
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO stage3_final_reviews
               (project_id,decision,redline,proposal_version,plan_version,feedback,reviewer_id)
               VALUES (?,?,?,?,?,?,?)""",
            (project_id, req.decision, int(req.redline),
             overview_data["gate"]["proposal_version"],
             overview_data["documents"]["plan"]["version"],
             req.feedback, user["user_id"]),
        )
    return _overview(project_id)


@router.get("/{project_id}/evidence-export")
def evidence_export(project_id: str, request: Request):
    require_project(request, project_id)
    data = _overview(project_id)
    data["runs"] = _rows("SELECT * FROM agent_runs WHERE project_id=? ORDER BY started_at, run_id", (project_id,))
    data["gate_history"] = _rows("SELECT * FROM stage3_gate_reviews WHERE project_id=? ORDER BY id", (project_id,))
    data["score_history"] = _rows("SELECT * FROM stage3_scores WHERE project_id=? ORDER BY id", (project_id,))
    data["document_history"] = _rows("SELECT * FROM stage3_documents WHERE project_id=? ORDER BY id", (project_id,))
    data["evidence_items"] = _rows("SELECT * FROM stage3_evidence_items WHERE project_id=? ORDER BY id", (project_id,))
    data["daily_progress"] = _rows("SELECT * FROM stage3_daily_progress WHERE project_id=? ORDER BY day", (project_id,))
    return data


@router.get("/teacher/ranking")
def ranking(request: Request):
    require_teacher(request)
    # Teacher class membership is a course policy; project list is supplied by
    # the existing teacher visibility endpoint. This endpoint only ranks the
    # projects that are both scored and through the proposal gate.
    from routers.teacher import _get_teacher_projects
    projects = _get_teacher_projects(request)
    eligible = []
    for project in projects:
        pid = project["project_id"]
        if not _gate(pid)["approved"]:
            continue
        gate = _gate(pid)
        plan = _latest_document(pid, "plan")
        scores = _latest_scores(pid)
        if not all(_score_is_current(scores.get(kind), gate, plan) for kind in ("project", "agent")):
            continue
        p = scores.get("project", {}).get("total", 0)
        a = scores.get("agent", {}).get("total", 0)
        if p >= 60 and a >= 60:
            defense = scores.get("defense")
            defense_score = defense["total"] if _score_is_current(defense, gate, plan) else None
            eligible.append({"project_id": pid, "name": project["name"],
                             "project_score": p, "agent_score": a,
                             "ranking_score": round((p + a) / 2, 1),
                             "defense_score": defense_score,
                             "final_total": p + a + defense_score if defense_score is not None else None,
                             "final_rank": None})
    eligible.sort(key=lambda row: (-row["ranking_score"], -row["project_score"], row["project_id"]))
    slots = ceil(len(eligible) / 2)
    for index, row in enumerate(eligible):
        row["rank"] = index + 1
        row["provisional_shortlist"] = index < slots
    finalists = sorted(
        (row for row in eligible if row["provisional_shortlist"] and row["final_total"] is not None),
        key=lambda row: (-row["final_total"], -row["defense_score"], row["rank"]),
    )
    for index, row in enumerate(finalists):
        row["final_rank"] = index + 1
    return {"eligible_count": len(eligible), "provisional_slots": slots,
            "rows": eligible, "finalists_scored": len(finalists),
            "teacher_confirmation_required": True}
