"""Agent router: entry point for multi-agent LangGraph pipeline."""

import re
import json
from services.session_store import get_chat_history, append_chat
from services.database import get_uploaded_files_for_project
from prompts.coach import COACH_GREETING
from agents.graph import get_graph


def get_greeting(agent_type: str) -> str:
    greetings = {
        "coach": COACH_GREETING,
        "tutor": "你好！我是创新创业学习辅导员。有什么概念或问题想了解的吗？比如 PMF、商业模式画布、TAM/SAM/SOM 等等。",
        "competition": "你好！我是竞赛顾问。请先简单描述一下你的项目，我来帮你评估竞赛准备情况。",
        "grader": "你好！请提交你的项目材料（计划书或PPT内容），我会基于 Rubric 标准进行评估。",
        "auto": (
            "你好！我是你的创新创业 AI 助手。无论你是想讨论项目想法、"
            "学习创业概念，还是评估竞赛准备，直接告诉我就好——"
            "我会自动为你找到最合适的帮助。🚀"
        ),
    }
    return greetings.get(agent_type, greetings["auto"])


def run_agent(session_id: str, message: str, agent_type: str = "coach", project_id: str = "") -> dict:
    append_chat(session_id, "user", message)
    history = get_chat_history(session_id)

    # F3-adv: Inject uploaded file context into message
    file_context = ""
    if project_id:
        files = get_uploaded_files_for_project(project_id)
        texts = [f"[文件: {f['filename']}]\n{f['extracted_text'][:2000]}"
                 for f in files if f.get("extracted_text")]
        if texts:
            file_context = "\n\n---\n已上传文件参考资料：\n" + "\n\n".join(texts[-3:])  # latest 3

    current_msg = message + file_context if file_context else message

    initial_state = {
        "session_id": session_id,
        "project_id": project_id,
        "messages": history,
        "current_message": current_msg,
        "intent": "",
        "tutor_concept": None,
        "coach_output": None,
        "tutor_output": None,
        "competition_output": None,
        "scores": None,
        "rubric_scores": None,
        "stage": None,
        "diagnosis": [],
        "final_reply": "",
        "triggered_rules": None,
        "rubric_full": None,
        "hypergraph_context": None,
        "extracted_techs": None,
        "extracted_industry": None,
        "extracted_concept": None,
        # V2: flexible pipeline
        "critic_redirect": None,
        "knowledge_recommendations": None,
        "loop_count": 0,
        # V3: floor score breakdown
        "score_breakdown": None,
    }

    graph = get_graph()
    final_state = graph.invoke(initial_state)

    reply = final_state.get("final_reply", "")
    append_chat(session_id, "assistant", reply)

    result: dict = {
        "reply": reply,
        "intent": final_state.get("intent", "coach"),
    }
    if final_state.get("scores"):
        result["scores"] = final_state["scores"]
    if final_state.get("stage"):
        result["stage"] = final_state["stage"]
    if final_state.get("diagnosis"):
        result["diagnosis"] = final_state["diagnosis"]
    if final_state.get("rubric_scores"):
        result["rubric_scores"] = final_state["rubric_scores"]
    if final_state.get("triggered_rules"):
        result["triggered_rules"] = final_state["triggered_rules"]
    if final_state.get("knowledge_recommendations"):
        result["knowledge_recommendations"] = final_state["knowledge_recommendations"]
    if final_state.get("score_breakdown"):
        result["score_breakdown"] = final_state["score_breakdown"]

    return result


def _build_initial_state(session_id: str, message: str, project_id: str) -> dict:
    """Build the shared initial state for both streaming and non-streaming paths."""
    history = get_chat_history(session_id)
    file_context = ""
    if project_id:
        files = get_uploaded_files_for_project(project_id)
        texts = [f"[文件: {f['filename']}]\n{f['extracted_text'][:2000]}"
                 for f in files if f.get("extracted_text")]
        if texts:
            file_context = "\n\n---\n已上传文件参考资料：\n" + "\n\n".join(texts[-3:])
    current_msg = message + file_context if file_context else message
    return {
        "session_id": session_id,
        "project_id": project_id,
        "messages": history,
        "current_message": current_msg,
        "intent": "",
        "tutor_concept": None,
        "coach_output": None,
        "tutor_output": None,
        "competition_output": None,
        "scores": None,
        "rubric_scores": None,
        "rubric_full": None,
        "stage": None,
        "diagnosis": [],
        "final_reply": "",
        "triggered_rules": None,
        "hypergraph_context": None,
        "extracted_techs": None,
        "extracted_industry": None,
        "extracted_concept": None,
        # V2: flexible pipeline
        "critic_redirect": None,
        "knowledge_recommendations": None,
        "loop_count": 0,
        # V3: floor score breakdown
        "score_breakdown": None,
    }


def run_agent_stream(session_id: str, message: str, agent_type: str = "coach", project_id: str = ""):
    """
    Streaming version: runs router + retriever synchronously, then streams the
    main LLM call. Yields SSE-formatted strings: data chunks + final metadata.
    """
    from agents.nodes.router import router_node
    from agents.nodes.retriever import retriever_node
    from agents.nodes.critic import critic_node
    from agents.nodes.synthesizer import synthesizer_node
    from services.claude_client import chat_completion_stream
    from services.evidence_tracer import refresh_tracer
    from agents.adaptive_questioning import build_questioning_context
    from services.competition_mode import get_countdown_context
    from services.database import get_competition_date, get_latest_annotations_for_coach, get_previous_scores
    from prompts.coach import COACH_SYSTEM_PROMPT
    from prompts.tutor import TUTOR_SYSTEM_PROMPT
    from prompts.competition import COMPETITION_SYSTEM_PROMPT
    from config import USE_MOCK_API

    append_chat(session_id, "user", message)
    state = _build_initial_state(session_id, message, project_id)

    # Phase 1: Router (fast — lightweight LLM or keyword-based)
    state = {**state, **router_node(state)}
    intent = state.get("intent", "coach")

    # Phase 2: Retriever (no LLM, pure data lookup)
    state = {**state, **retriever_node(state)}
    hypergraph_ctx = state.get("hypergraph_context", "")

    # Phase 3: Build system prompt based on intent
    if intent == "grader":
        from agents.nodes.grader import GRADER_SYSTEM_PROMPT
        system = GRADER_SYSTEM_PROMPT
    elif intent == "competition":
        system = COMPETITION_SYSTEM_PROMPT
        if hypergraph_ctx:
            system += f"\n\n[超图案例库参考]\n{hypergraph_ctx}"
    elif intent in ("tutor", "hybrid"):
        system = TUTOR_SYSTEM_PROMPT
        if hypergraph_ctx:
            system += f"\n\n[超图案例参考]\n{hypergraph_ctx}"
    else:
        system = COACH_SYSTEM_PROMPT
        if hypergraph_ctx:
            system += (
                "\n\n[超图知识库检索结果 — 基于82个真实竞赛案例]\n"
                "以下是从超图案例库中检索到的与学生项目相关的信息。"
                "请在回答中引用这些案例和风险模式来增强你的指导：\n\n"
                f"{hypergraph_ctx}"
            )
        # Evidence tracer
        tracer = refresh_tracer(session_id, state.get("messages", []))
        evidence_ctx = tracer.format_missing_evidence()
        if evidence_ctx:
            system += f"\n\n[证据追踪摘要]\n{evidence_ctx}"
        # Adaptive questioning
        q_ctx = build_questioning_context(state.get("scores"), state.get("messages", []), message)
        if q_ctx:
            system += f"\n\n{q_ctx}"
        # Competition countdown
        if project_id:
            comp_date = get_competition_date(project_id)
            cd_ctx = get_countdown_context(comp_date)
            if cd_ctx:
                system += f"\n\n{cd_ctx}"
            try:
                notes = get_latest_annotations_for_coach(project_id)
                if notes:
                    system += "\n\n[教师批注 - 请在本轮对话中体现以下教师指导意见]\n"
                    for a in notes[:3]:
                        system += f"  • {a['note_text']}\n"
            except Exception:
                pass

            # ★ Score anchoring: inject previous scores
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

        # ★ 范式库注入：匹配学生项目的创业范式
        try:
            from services.playbook_engine import match_playbook as _match_pb, format_playbook_for_prompt as _fmt_pb
            intake_data = session_meta.get("intake_data") or {}
            _pb_desc = intake_data.get("solution_desc") or intake_data.get("pain_scenario") or ""
            _pb_ind = intake_data.get("industry_choice", "")
            _pb_biz = intake_data.get("revenue_model", "")
            if not _pb_desc and project_id:
                from services.database import get_project as _gp
                _pi = _gp(project_id)
                if _pi:
                    _pb_desc = _pi.get("description", "")
                    _pb_ind = _pi.get("industry", _pb_ind)
            if _pb_desc:
                _pb_matched = _match_pb(_pb_desc, _pb_ind, _pb_biz)
                if _pb_matched:
                    _pb_prompt = _fmt_pb(_pb_matched[0]["playbook_id"])
                    if _pb_prompt:
                        system += f"\n\n{_pb_prompt}"
        except Exception:
            pass

        # ★ Phase 1: Cheap-First 轻推理 — 注入结构化诊断到 LLM prompt
        from services.cheap_diagnostic import run_cheap_diagnostic, format_diagnostic_for_prompt, format_diagnostic_as_fallback
        all_msgs_for_diag = list(state.get("messages", []))
        all_msgs_for_diag.append({"role": "user", "content": message})
        try:
            cheap_diag = run_cheap_diagnostic(session_id, all_msgs_for_diag, current_scores=state.get("scores"))
            diag_prompt = format_diagnostic_for_prompt(cheap_diag)
            if diag_prompt:
                system += f"\n\n{diag_prompt}"
        except Exception:
            cheap_diag = None

        # ★ 知识卡片注入：根据诊断缺口或消息关键词推荐卡片
        try:
            from services.knowledge_cards import search_cards, format_cards_for_prompt
            if cheap_diag and cheap_diag.top_gaps:
                urgent_dims = [d for d in cheap_diag.dimensions.values() if d.priority == "urgent"]
                if urgent_dims:
                    gap_cards = search_cards(dimension=urgent_dims[0].dim, max_results=3)
                    card_prompt = format_cards_for_prompt(gap_cards, max_cards=2)
                    if card_prompt:
                        system += f"\n\n{card_prompt}"
            else:
                kw_cards = search_cards(query=message[:50], max_results=2)
                card_prompt = format_cards_for_prompt(kw_cards, max_cards=2)
                if card_prompt:
                    system += f"\n\n{card_prompt}"
        except Exception:
            pass

    # Phase 4: Send intent metadata
    yield f"data: {json.dumps({'type': 'meta', 'intent': intent})}\n\n"

    # Phase 5: Stream LLM response
    if USE_MOCK_API:
        yield f"data: {json.dumps({'type': 'token', 'content': '（Mock 模式暂无流式输出）'})}\n\n"
        full_text = "（Mock 模式暂无流式输出）"
    else:
        full_text = ""
        buffer = ""
        for chunk in chat_completion_stream(system, state.get("messages", [])):
            full_text += chunk
            buffer += chunk
            # Hold back buffer if it might be the start of a SCORES comment
            while True:
                start = buffer.find("<!--SCORES:")
                if start == -1:
                    # No SCORES comment starting, flush everything
                    if buffer:
                        yield f"data: {json.dumps({'type': 'token', 'content': buffer})}\n\n"
                        buffer = ""
                    break
                elif start > 0:
                    # Flush content before the potential SCORES comment
                    yield f"data: {json.dumps({'type': 'token', 'content': buffer[:start]})}\n\n"
                    buffer = buffer[start:]
                    break
                else:
                    # buffer starts with <!--SCORES:, wait for closing -->
                    end = buffer.find("-->")
                    if end != -1:
                        # Found complete SCORES comment, discard it
                        buffer = buffer[end + 3:]
                    else:
                        # Incomplete comment, keep buffering
                        break
        # Flush any remaining buffer (strip any incomplete SCORES comment)
        if buffer:
            clean_buffer = re.sub(r"<!--SCORES:.*?-->", "", buffer)
            # Only yield if clean_buffer has no remaining SCORES markers
            if clean_buffer and not re.search(r"<!--SCORES:", clean_buffer):
                yield f"data: {json.dumps({'type': 'token', 'content': clean_buffer})}\n\n"

        # ★ Cheap-First fallback: LLM 失败时用规则层诊断生成回复
        if full_text.startswith("抱歉，AI 服务暂时无法响应") and intent == "coach":
            cheap_diag_local = locals().get("cheap_diag")
            if cheap_diag_local:
                fallback_text = format_diagnostic_as_fallback(cheap_diag_local)
                full_text = fallback_text
                # Re-stream the fallback to the frontend
                yield f"data: {json.dumps({'type': 'token', 'content': fallback_text})}\n\n"

    # Phase 6: Parse scores from accumulated text, run critic
    scores_match = re.search(r"<!--SCORES:(.*?)-->", full_text)
    scores_data = None
    if scores_match:
        try:
            scores_data = json.loads(scores_match.group(1))
        except json.JSONDecodeError:
            pass

    # Parse full rubric from grader
    rubric_full = None
    rubric_full_match = re.search(r"<!--RUBRIC_FULL:\s*([\s\S]*?)-->", full_text)
    if rubric_full_match:
        try:
            rubric_full = json.loads(rubric_full_match.group(1).strip())
        except json.JSONDecodeError:
            pass

    clean_reply = re.sub(r"<!--SCORES:.*?-->", "", full_text).strip()
    # Also clean rubric scores marker
    clean_reply = re.sub(r"<!--RUBRIC:.*?-->", "", clean_reply).strip()
    # Clean full rubric marker
    clean_reply = re.sub(r"<!--RUBRIC_FULL:[\s\S]*?-->", "", clean_reply).strip()

    new_scores = None
    stage = state.get("stage")
    diagnosis = state.get("diagnosis", [])
    score_breakdown = None
    if scores_data:
        new_scores = {k: v for k, v in scores_data.items() if k not in ("stage", "diagnosis")}
        stage = scores_data.get("stage", stage)
        diagnosis = scores_data.get("diagnosis", diagnosis)

        # ★ 可计算底分：用证据约束 LLM 评分（streaming path）
        from services.floor_scorer import compute_floor_scores, enforce_floor, format_breakdown_for_response
        all_msgs = list(state.get("messages", []))
        all_msgs.append({"role": "user", "content": message})
        breakdowns = compute_floor_scores(session_id, all_msgs)
        new_scores = enforce_floor(new_scores, breakdowns)
        score_breakdown = format_breakdown_for_response(breakdowns)

    # For hybrid: we only streamed the first agent (tutor). We need coach too.
    # For simplicity, hybrid falls back to non-streaming for the coach part.
    if intent == "hybrid":
        state["tutor_output"] = clean_reply
        # Run coach via non-streaming graph path
        from agents.nodes.coach import coach_node
        coach_state = {**state, **coach_node(state)}
        coach_output = coach_state.get("coach_output", "")
        if coach_output:
            yield "data: " + json.dumps({
    "type": "token",
    "content": "\n\n---\n\n### 回到你的项目\n\n"
}) + "\n\n"
            yield f"data: {json.dumps({'type': 'token', 'content': coach_output})}\n\n"
            concept = state.get("tutor_concept") or "概念"
            clean_reply = f"### 关于「{concept}」的解释\n\n{clean_reply}\n\n---\n\n### 回到你的项目\n\n{coach_output}"
            # Use coach scores if available
            if coach_state.get("scores"):
                new_scores = coach_state["scores"]
                stage = coach_state.get("stage", stage)
                diagnosis = coach_state.get("diagnosis", diagnosis)

    # Run critic for constraint checking
    state["final_reply"] = clean_reply
    state["scores"] = new_scores
    state["stage"] = stage
    state["diagnosis"] = diagnosis
    state["loop_count"] = 0
    critic_result = critic_node(state)
    triggered = critic_result.get("triggered_rules") or []

    # V2: Handle critic redirect — if critic wants to redirect to tutor
    critic_redirect = critic_result.get("critic_redirect")
    knowledge_recs = critic_result.get("knowledge_recommendations")
    if critic_redirect and critic_result.get("loop_count", 0) <= 1:
        # Stream the redirect tutor output
        from agents.nodes.tutor import tutor_node as _tutor_node
        redirect_state = {
            **critic_result,
            "tutor_concept": critic_redirect,
            "current_message": f"请帮我解释一下「{critic_redirect}」这个概念，以及它在创业项目中的具体应用。",
        }
        redirect_result = _tutor_node(redirect_state)
        tutor_extra = redirect_result.get("tutor_output", "")
        if tutor_extra:
            redirect_block = f"\n\n---\n\n### 💡 知识补充：{critic_redirect}\n\n{tutor_extra}"
            yield f"data: {json.dumps({'type': 'token', 'content': redirect_block})}\n\n"
            clean_reply += redirect_block

    # Update final_reply from critic (includes learning recommendations)
    clean_reply = critic_result.get("final_reply", clean_reply)

    # Save reply and update project scores (with EMA smoothing)
    append_chat(session_id, "assistant", clean_reply)
    if project_id and (new_scores or stage or diagnosis):
        from services.session_store import update_project_scores
        update_project_scores(project_id, new_scores, stage, diagnosis)
    # Read back smoothed scores for frontend
    if project_id and new_scores:
        from services.database import get_previous_scores as _get_smoothed
        smoothed = _get_smoothed(project_id)
        if smoothed:
            new_scores = smoothed

    # Phase 7: Send final metadata
    if rubric_full:
        rubric_scores_from_full = {k: v["score"] for k, v in rubric_full.items()}
    else:
        rubric_scores_from_full = None
    meta = {"type": "done", "intent": intent}
    if new_scores:
        meta["scores"] = new_scores
    if stage:
        meta["stage"] = stage
    if diagnosis:
        meta["diagnosis"] = diagnosis
    if rubric_full:
        meta["rubric_full"] = rubric_full
    if rubric_scores_from_full:
        meta["rubric_scores"] = rubric_scores_from_full
    if triggered:
        meta["triggered_rules"] = triggered
        # Structured fix tasks for frontend display
        fix_tasks = [
            {"rule_id": r["rule_id"], "severity": r["severity"], "fix_task": r["fix_task"]}
            for r in triggered
            if isinstance(r, dict) and r.get("fix_task") and r.get("severity") in ("high", "medium")
        ]
        if fix_tasks:
            meta["fix_tasks"] = fix_tasks
    if knowledge_recs:
        meta["knowledge_recommendations"] = knowledge_recs
    if score_breakdown:
        meta["score_breakdown"] = score_breakdown

    yield f"data: {json.dumps(meta)}\n\n"
