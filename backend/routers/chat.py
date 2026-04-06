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
from services.intake_form import (
    get_intake_schema, predict_gaps, extract_evidence_from_intake,
    format_intake_for_prompt, format_intake_summary_for_student,
)
from hypergraph.knowledge_recommendations import get_recommendations
import uuid

router = APIRouter(prefix="/api/chat", tags=["chat"])

# ── A1-2 / A2-2 反代写拦截层 ─────────────────────────────────────
# 检测到以下关键词时，直接返回苏格拉底引导，不走 LLM
_GHOSTWRITE_PATTERNS = [
    "直接帮我写", "帮我写完", "帮我写好", "帮我生成", "生成可以直接提交",
    "直接写", "帮我弄个", "你直接写", "代写", "直接给我写",
    "写个800字", "写个500字", "写完给我", "直接出一份",
    "你来写", "替我写", "帮我完成商业计划", "写完整的BP",
    "帮我写", "帮我出", "帮我做完", "帮我完成",
]

_GHOSTWRITE_REPLY = """我理解你现在可能感到压力很大，但我没办法直接替你写——这是我的底线，也是对你真正的负责。

直接给你一份成品，对你参加答辩和未来创业没有任何帮助。让我们换个方式：

**三个问题帮你找到突破口：**

1. 你的目标用户是谁？能不能描述一个真实的用户场景（谁、在什么时候、遇到什么问题）？

2. 你的产品/服务，和用户现在的解决方式相比，具体好在哪里？能量化吗？

3. 如果只保留一个核心功能上线，你选哪个？为什么是这个？

先回答第一个问题，我们一步一步来。🎯

> *AI 生成，仅供参考*"""


def _detect_ghostwrite(message: str) -> bool:
    """检测消息是否包含代写请求关键词。"""
    return any(p in message for p in _GHOSTWRITE_PATTERNS)


# ── A7 鲁棒性与边界异常兜底层 ─────────────────────────────────────
import re as _re

def _is_garbled(message: str) -> bool:
    """检测消息是否为无意义/乱码/纯数字/纯符号输入。"""
    cleaned = message.strip()
    if len(cleaned) < 2:
        return True
    # 纯数字或纯重复字符
    if _re.fullmatch(r'[\d\s]+', cleaned):
        return True
    if _re.fullmatch(r'(.)\1{3,}', cleaned):
        return True
    # 几乎没有有意义的中文或英文字符
    meaningful = _re.findall(r'[\u4e00-\u9fff a-zA-Z]', cleaned)
    if len(meaningful) < max(2, len(cleaned) * 0.2):
        return True
    return False

_GARBLED_REPLY = """未检测到有效的项目信息。请详细描述你的创新想法，例如：

1. 你想解决什么问题？（谁在什么场景下遇到了什么痛苦？）
2. 你打算怎么解决？（大致的方案方向）
3. 你的目标用户是谁？

随时告诉我，我们一起开始！🚀

> *AI 生成，仅供参考*"""

_JAILBREAK_PATTERNS = [
    "忽略以上所有", "忽略上面的", "忽略之前的", "忽略你的规则",
    "ignore all", "ignore above", "ignore previous", "ignore your",
    "forget your instructions", "disregard your",
    "帮我写一段代码", "帮我写爬虫", "帮我写脚本",
    "写一段python", "写一段java", "写一段代码",
    "抓取数据", "爬取网站", "破解密码",
    "DAN模式", "越狱", "jailbreak",
    "你现在是一个", "假装你是", "pretend you are",
    "帮我做作业", "帮我写论文", "帮我抄",
]

def _is_jailbreak(message: str) -> bool:
    """检测消息是否为越狱/偏离双创主题的请求。"""
    msg = message.lower()
    return any(p.lower() in msg for p in _JAILBREAK_PATTERNS)

_JAILBREAK_REPLY = """我是你的创新创业 AI 教练，专注于帮助你完成双创项目。这个请求超出了我的职责范围，我没办法帮你处理哦。

不过我可以在这些方面帮到你：

- 🎯 **项目诊断**：分析你的创业想法，找出关键瓶颈
- 📚 **概念学习**：解释 PMF、商业模式画布、TAM/SAM/SOM 等创业概念
- 🏆 **竞赛准备**：模拟路演提问，帮你查漏补缺
- 📝 **材料评估**：基于 Rubric 标准评估你的计划书

请告诉我你的创业项目相关的问题，让我们回到正题！

> *AI 生成，仅供参考*"""

_EMOTIONAL_PATTERNS = [
    "太难了", "不想思考", "不想做了", "做不下去",
    "随便给我", "随便弄个", "交差", "应付",
    "烦死了", "受不了", "崩溃", "放弃了",
    "算了不做了", "懒得想", "不管了",
]

def _is_emotional_bail(message: str) -> bool:
    """检测消息是否为情绪化的逃避/敷衍请求。"""
    return any(p in message for p in _EMOTIONAL_PATTERNS)

_EMOTIONAL_REPLY = """我完全理解你的感受——创业计划确实不容易，压力大的时候想放弃是很正常的。但你已经走到这一步了，说明你是有想法的人。

我们不需要一次做完所有事，**先做最小的一步就好**：

🎯 **现在只需要回答我一个问题：**

> 你最初想做这个项目，是因为注意到了什么现象或问题？（哪怕只是一个模糊的感觉也行）

从这一个点出发，我带你一步一步把思路理清。不着急，我们慢慢来。

> *AI 生成，仅供参考*"""


def _robustness_check(message: str) -> tuple[str, str] | None:
    """A7 鲁棒性检查：返回 (reply, intent) 或 None（正常放行）。"""
    if _is_garbled(message):
        return _GARBLED_REPLY, "guardrail_garbled"
    if _is_jailbreak(message):
        return _JAILBREAK_REPLY, "guardrail_jailbreak"
    if _is_emotional_bail(message):
        return _EMOTIONAL_REPLY, "guardrail_emotional"
    return None


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

    # ── A7 鲁棒性兜底检查 ──
    robustness = _robustness_check(req.message)
    if robustness:
        reply, intent = robustness
        append_chat(req.session_id, "user", req.message)
        append_chat(req.session_id, "assistant", reply)
        return ChatResponse(session_id=req.session_id, reply=reply, intent=intent)

    # ── A1-2 / A2-2 反代写拦截 ──
    if _detect_ghostwrite(req.message):
        append_chat(req.session_id, "user", req.message)
        append_chat(req.session_id, "assistant", _GHOSTWRITE_REPLY)
        return ChatResponse(
            session_id=req.session_id,
            reply=_GHOSTWRITE_REPLY,
            intent="guardrail_ghostwrite",
        )

    # Bind project if provided and not already bound
    if req.project_id:
        bind_session_to_project(req.session_id, req.project_id)

    project_id = req.project_id or get_project_for_session(req.session_id)
    result = run_agent(req.session_id, req.message, req.agent_type, project_id=project_id)

    # P0-1 & P0-2: Write scores back to project (with EMA smoothing)
    if project_id and (result.get("scores") or result.get("stage") or result.get("diagnosis")):
        update_project_scores(
            project_id,
            scores=result.get("scores"),
            stage=result.get("stage"),
            diagnosis=result.get("diagnosis"),
        )
        # Read back smoothed scores so frontend gets stable values
        if result.get("scores"):
            from services.database import get_previous_scores
            smoothed = get_previous_scores(project_id)
            if smoothed:
                result["scores"] = smoothed

    # Save rubric_full if grader produced it
    if project_id and result.get("rubric_full"):
        from services.database import get_project, save_project
        proj = get_project(project_id)
        if proj:
            proj["rubric_full"] = result["rubric_full"]
            save_project(proj)

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
        score_breakdown=result.get("score_breakdown"),
    )


@router.post("/message/stream")
def send_message_stream(req: ChatRequest):
    """SSE streaming endpoint — sends tokens as they arrive from the LLM."""
    if not req.message.strip():
        raise HTTPException(status_code=400, detail="消息不能为空")

    # ── A7 鲁棒性兜底检查（流式版） ──
    robustness = _robustness_check(req.message)
    if robustness:
        reply, intent = robustness
        append_chat(req.session_id, "user", req.message)
        append_chat(req.session_id, "assistant", reply)

        def robustness_stream():
            import json as _json
            yield f"data: {_json.dumps({'type': 'meta', 'intent': intent})}\n\n"
            yield f"data: {_json.dumps({'type': 'token', 'content': reply})}\n\n"
            yield f"data: {_json.dumps({'type': 'done', 'intent': intent, 'reply': reply})}\n\n"

        return StreamingResponse(
            robustness_stream(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"},
        )

    # ── A1-2 / A2-2 反代写拦截（流式版） ──
    if _detect_ghostwrite(req.message):
        append_chat(req.session_id, "user", req.message)
        append_chat(req.session_id, "assistant", _GHOSTWRITE_REPLY)

        def guardrail_stream():
            import json as _json
            yield f"data: {_json.dumps({'type': 'meta', 'intent': 'guardrail_ghostwrite'})}\n\n"
            yield f"data: {_json.dumps({'type': 'token', 'content': _GHOSTWRITE_REPLY})}\n\n"
            yield f"data: {_json.dumps({'type': 'done', 'intent': 'guardrail_ghostwrite', 'reply': _GHOSTWRITE_REPLY})}\n\n"

        return StreamingResponse(
            guardrail_stream(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"},
        )

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
    from services.database import get_project, get_conn
    history = get_chat_history(session_id)
    project_id = get_project_for_session(session_id)
    proj = get_project(project_id) if project_id else None

    # Get session agent_type from database
    agent_type = "coach"
    try:
        with get_conn() as conn:
            row = conn.execute("SELECT agent_type FROM chat_sessions WHERE session_id=?", (session_id,)).fetchone()
            if row:
                agent_type = row["agent_type"] or "coach"
    except Exception:
        pass

    return {
        "session_id": session_id,
        "messages": history,
        "agent_type": agent_type,
        "scores": proj.get("scores") if proj else None,
        "stage": proj.get("stage") if proj else None,
        "diagnosis": proj.get("diagnosis") if proj else None,
        "rubric_full": proj.get("rubric_full") if proj else None,
    }


# ── Intake Form (前置采集层) ──────────────────────────────────────────

@router.get("/intake/schema")
def get_intake_form_schema():
    """返回前置采集表单的 schema，前端用于渲染表单。"""
    return {"groups": get_intake_schema()}


class IntakeSubmitRequest(BaseModel):
    session_id: str
    project_id: str
    filled_data: dict  # {field_key: value}


@router.post("/intake/submit")
def submit_intake(req: IntakeSubmitRequest):
    """
    提交前置采集数据。

    处理流程：
    1. 预测信息缺口（top 3）
    2. 提取证据并预填充到 EvidenceTracer
    3. 生成面向学生的摘要（作为第一条 AI 消息）
    4. 生成注入 coach prompt 的上下文块（存到 session 元数据）
    """
    from services.evidence_tracer import refresh_tracer
    from services.session_store import set_session, get_session

    # 1. 缺口预测
    gaps = predict_gaps(req.filled_data, max_gaps=3)

    # 2. 提取证据
    evidences = extract_evidence_from_intake(req.filled_data)

    # 3. 预填充证据到 tracer（通过构造一条虚拟的用户消息）
    intake_text_parts = []
    for ev in evidences:
        intake_text_parts.append(ev.text)
    if intake_text_parts:
        intake_message = "\n".join(intake_text_parts)
        append_chat(req.session_id, "user", f"[项目信息采集]\n{intake_message}")
        # Refresh tracer so it picks up the intake evidence
        history = get_chat_history(req.session_id)
        refresh_tracer(req.session_id, history)

    # 4. 生成面向学生的摘要
    student_summary = format_intake_summary_for_student(req.filled_data, gaps)
    append_chat(req.session_id, "assistant", student_summary)

    # 5. 生成 prompt 注入块，存到 session 元数据
    prompt_context = format_intake_for_prompt(req.filled_data, gaps)
    session_meta = get_session(req.session_id) or {}
    session_meta["intake_context"] = prompt_context
    session_meta["intake_data"] = req.filled_data
    set_session(req.session_id, session_meta)

    # 6. 如果有项目绑定，更新项目描述
    if req.project_id:
        project = get_project(req.project_id)
        if project:
            # 用采集数据丰富项目描述
            desc_parts = []
            if req.filled_data.get("target_user"):
                desc_parts.append(f"目标用户：{req.filled_data['target_user']}")
            if req.filled_data.get("pain_scenario"):
                desc_parts.append(f"痛点：{req.filled_data['pain_scenario'][:100]}")
            if req.filled_data.get("solution_desc"):
                desc_parts.append(f"方案：{req.filled_data['solution_desc'][:100]}")
            if desc_parts and not project.get("description"):
                from services.session_store import set_project
                project["description"] = " | ".join(desc_parts)
                set_project(req.project_id, project)

    return {
        "session_id": req.session_id,
        "student_summary": student_summary,
        "gaps": [
            {"field_key": g.field_key, "label": g.label, "reason": g.reason}
            for g in gaps
        ],
        "evidence_count": len(evidences),
        "intake_complete": True,
    }


class IntakeGapCheckRequest(BaseModel):
    filled_data: dict


@router.post("/intake/gaps")
def check_intake_gaps(req: IntakeGapCheckRequest):
    """实时缺口预测 — 前端在用户填写过程中调用，动态显示缺口。"""
    gaps = predict_gaps(req.filled_data, max_gaps=5)
    return {
        "gaps": [
            {"field_key": g.field_key, "label": g.label, "reason": g.reason, "dimension": g.dimension}
            for g in gaps
        ],
    }


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
