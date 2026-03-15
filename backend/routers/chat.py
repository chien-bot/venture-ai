from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from models.schemas import ChatRequest, ChatResponse
from agents.router import run_agent, run_agent_stream, get_greeting
from services.session_store import (
    get_chat_history,
    append_chat,
    create_session,
    bind_session_to_project,
    get_project_for_session,
    update_project_scores,
    get_latest_session_for_project,
    get_project,
)
from services.database import save_session_rating, get_rating_for_session, auto_detect_task_completion
from hypergraph.knowledge_recommendations import get_recommendations
import uuid

router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.post("/start")
def start_chat(request: Request, agent_type: str = "auto", project_id: str = ""):
    from services.database import get_user_by_token
    auth = request.headers.get("Authorization", "")
    user = get_user_by_token(auth[7:]) if auth.startswith("Bearer ") else None
    owner_id = user["user_id"] if user else ""

    session_id = str(uuid.uuid4())
    create_session(session_id, project_id, agent_type, owner_id)
    greeting = get_greeting(agent_type)
    append_chat(session_id, "assistant", greeting)

    if project_id:
        bind_session_to_project(session_id, project_id)

    return {
        "session_id": session_id,
        "greeting": greeting,
        "agent_type": agent_type,
        "project_id": project_id,
    }


@router.post("/message", response_model=ChatResponse)
def send_message(req: ChatRequest):
    if not req.message.strip():
        raise HTTPException(status_code=400, detail="消息不能为空")

    # Bind project if provided and not already bound
    if req.project_id:
        bind_session_to_project(req.session_id, req.project_id)

    project_id = req.project_id or get_project_for_session(req.session_id)
    result = run_agent(req.session_id, req.message, req.agent_type, project_id=project_id)

    # P0-1 & P0-2: Write scores back to project
    if project_id and (result.get("scores") or result.get("stage") or result.get("diagnosis")):
        update_project_scores(
            project_id,
            scores=result.get("scores"),
            stage=result.get("stage"),
            diagnosis=result.get("diagnosis"),
        )

    # F5-adv: Auto-detect learning task completion
    if project_id:
        auto_detect_task_completion(project_id, req.message)

    # Build knowledge recommendations from triggered H-rules (F1)
    triggered = result.get("triggered_rules") or []
    triggered_ids = [r["rule_id"] for r in triggered if isinstance(r, dict)]
    knowledge_recs = get_recommendations(triggered_ids)

    # Extract structured fix_tasks from triggered rules (H1-H15)
    fix_tasks = [
        {"rule_id": r["rule_id"], "severity": r["severity"], "fix_task": r["fix_task"]}
        for r in triggered
        if isinstance(r, dict) and r.get("fix_task") and r.get("severity") in ("high", "medium")
    ] or None

    return ChatResponse(
        session_id=req.session_id,
        reply=result["reply"],
        scores=result.get("scores"),
        diagnosis=result.get("diagnosis"),
        stage=result.get("stage"),
        rubric_scores=result.get("rubric_scores"),
        intent=result.get("intent"),
        knowledge_recommendations=knowledge_recs or None,
        fix_tasks=fix_tasks,
    )


@router.post("/message/stream")
def send_message_stream(req: ChatRequest):
    """SSE streaming endpoint — sends tokens as they arrive from the LLM."""
    if not req.message.strip():
        raise HTTPException(status_code=400, detail="消息不能为空")

    if req.project_id:
        bind_session_to_project(req.session_id, req.project_id)

    project_id = req.project_id or get_project_for_session(req.session_id)

    def event_generator():
        for event in run_agent_stream(req.session_id, req.message, req.agent_type, project_id=project_id):
            yield event

        # Post-stream: update project scores (from the 'done' event data)
        # This is handled by the frontend calling the scores from the done event.
        if project_id:
            auto_detect_task_completion(project_id, req.message)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/history/{session_id}")
def get_history(session_id: str):
    history = get_chat_history(session_id)
    return {"session_id": session_id, "messages": history}


# ── Mock Investor Defense ─────────────────────────────────────────────

class DefenseStartRequest(BaseModel):
    project_id: str
    investor_style: str = "aggressive"  # aggressive | analytical | strategic
    total_questions: int = 7


@router.post("/defense/start")
def start_defense(req: DefenseStartRequest):
    """Start a mock investor defense session."""
    from prompts.investor import INVESTOR_GREETING
    session_id = str(uuid.uuid4())
    create_session(session_id, req.project_id, "defense")
    bind_session_to_project(session_id, req.project_id)
    greeting = INVESTOR_GREETING.format(total_questions=req.total_questions)
    append_chat(session_id, "assistant", greeting)
    return {
        "session_id": session_id,
        "greeting": greeting,
        "project_id": req.project_id,
        "investor_style": req.investor_style,
        "total_questions": req.total_questions,
    }


class DefenseMessageRequest(BaseModel):
    session_id: str
    project_id: str
    message: str
    investor_style: str = "aggressive"
    current_round: int = 1
    total_questions: int = 7


@router.post("/defense/message")
def defense_message(req: DefenseMessageRequest):
    """Send a message in a mock investor defense and get the investor's response."""
    import re as _re
    import json as _json
    from prompts.investor import INVESTOR_SYSTEM_PROMPT, INVESTOR_STYLES
    from services.claude_client import chat_completion
    from agents.nodes.retriever import retriever_node
    from hypergraph.engine import query_hypergraph, format_context_for_prompt

    if not req.message.strip():
        raise HTTPException(status_code=400, detail="消息不能为空")

    append_chat(req.session_id, "user", req.message)
    history = get_chat_history(req.session_id)

    # Get hypergraph context for the project
    project = get_project(req.project_id)
    hypergraph_ctx = ""
    if project:
        industry = project.get("industry", "")
        # Simple keyword extraction from message
        techs = []
        tech_words = ["AI", "深度学习", "机器学习", "区块链", "IoT", "大数据", "云计算", "无人机", "机器人"]
        for tw in tech_words:
            if tw.lower() in req.message.lower() or tw.lower() in project.get("description", "").lower():
                techs.append(tw)
        if techs or industry:
            ctx = query_hypergraph(tech_keywords=techs, industry=industry)
            hypergraph_ctx = format_context_for_prompt(ctx)

    style_desc = INVESTOR_STYLES.get(req.investor_style, INVESTOR_STYLES["aggressive"])
    system = INVESTOR_SYSTEM_PROMPT.format(
        investor_style=style_desc,
        total_questions=req.total_questions,
        current_round=req.current_round,
    )
    if hypergraph_ctx:
        system += f"\n\n[超图案例库参考]\n{hypergraph_ctx}"

    raw = chat_completion(system, history)
    append_chat(req.session_id, "assistant", raw)

    # Parse defense report if present (last round)
    report = None
    report_match = _re.search(r"<!--DEFENSE_REPORT:(.*?)-->", raw, _re.DOTALL)
    if report_match:
        try:
            report = _json.loads(report_match.group(1))
        except _json.JSONDecodeError:
            pass

    clean = _re.sub(r"<!--DEFENSE_REPORT:.*?-->", "", raw, flags=_re.DOTALL).strip()

    return {
        "session_id": req.session_id,
        "reply": clean,
        "current_round": req.current_round,
        "is_final": req.current_round >= req.total_questions,
        "report": report,
    }


# ── Session Rating (F5) ───────────────────────────────────────────────

class RatingRequest(BaseModel):
    session_id: str
    project_id: str = ""
    student_id: str = "student"
    rating: int
    comment: str = ""


@router.post("/rating")
def submit_rating(req: RatingRequest):
    if not 1 <= req.rating <= 5:
        raise HTTPException(status_code=400, detail="评分必须在 1-5 之间")
    save_session_rating(req.session_id, req.project_id, req.student_id, req.rating, req.comment)
    return {"ok": True}


@router.get("/rating/{session_id}")
def get_rating(session_id: str):
    return get_rating_for_session(session_id) or {}


# ── Student Session History ───────────────────────────────────────────

@router.get("/my-sessions")
def get_my_sessions(request: Request):
    """Return all coaching sessions for the current student."""
    from services.database import get_sessions_for_user, get_user_by_token
    auth = request.headers.get("Authorization", "")
    user = get_user_by_token(auth[7:]) if auth.startswith("Bearer ") else None
    if not user:
        raise HTTPException(status_code=401, detail="未登录")
    sessions = get_sessions_for_user(user["user_id"])
    return {"sessions": sessions}


@router.delete("/session/{session_id}")
def delete_session_endpoint(session_id: str, request: Request):
    """Delete a session (owner only)."""
    from services.database import delete_session, get_user_by_token
    auth = request.headers.get("Authorization", "")
    user = get_user_by_token(auth[7:]) if auth.startswith("Bearer ") else None
    if not user:
        raise HTTPException(status_code=401, detail="未登录")
    ok = delete_session(session_id, user["user_id"])
    if not ok:
        raise HTTPException(status_code=404, detail="对话不存在或无权限删除")
    return {"ok": True}


# ── Session Memory (F1-adv) ──────────────────────────────────────────

@router.get("/latest-session/{project_id}")
def get_latest_session(project_id: str):
    """Return the latest session for a project so frontend can restore state."""
    session = get_latest_session_for_project(project_id)
    if not session or not session.get("messages"):
        return {"exists": False}
    proj = get_project(project_id)
    return {
        "exists": True,
        "session_id": session["session_id"],
        "agent_type": session.get("agent_type", "auto"),
        "messages": session["messages"],
        "scores": proj.get("scores") if proj else None,
        "stage": proj.get("stage") if proj else None,
        "diagnosis": proj.get("diagnosis") if proj else None,
    }
