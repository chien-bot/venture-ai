"""
agents/nodes/critic.py
────────────────────────────────────────────────────────────────
Critic Agent 节点 V2

职责：
1. 调用超图一致性检查器，检测 H1-H15 约束规则是否被触发
2. 将违规规则注入 diagnosis，追加到 coach/competition 输出后
3. 在 final_reply 中追加结构化的超图诊断提示（仅当有触发时）
4. V2: 高置信度规则触发时，生成 critic_redirect 信号让 tutor 介入解释相关概念
5. V2: 生成 knowledge_recommendations 学习路径推荐

这是一个纯诊断节点，不调用 LLM，运行极快。
"""
from __future__ import annotations

from agents.state import AgentState
from hypergraph.consistency_check import (
    check_conversation,
    format_violations,
    rules_to_diagnosis,
    TriggeredRule,
)
from hypergraph.knowledge_recommendations import get_recommendations


# 置信度阈值：只有高置信度 + high severity 的规则才触发 tutor 跳转
_REDIRECT_CONFIDENCE_THRESHOLD = 0.55
_REDIRECT_SEVERITY = ("high",)


def critic_node(state: AgentState) -> AgentState:
    """
    在所有 agent 输出之后运行，进行超图约束检测。
    修改 state 中的 diagnosis 和 (如有) final_reply。

    V2: 增加 critic_redirect 和 knowledge_recommendations 输出。
    """
    messages = state.get("messages", [])
    current_message = state.get("current_message", "")
    session_id = state.get("session_id", "")
    loop_count = state.get("loop_count", 0)

    # 运行超图一致性检验
    triggered: list[TriggeredRule] = check_conversation(
        messages, current_message, session_id=session_id
    )

    # 将触发规则合并到 diagnosis（避免重复）
    existing_diagnosis: list[str] = list(state.get("diagnosis") or [])
    new_diagnosis = rules_to_diagnosis(triggered)

    # 去重：避免跨轮重复添加相同规则
    existing_ids = {d.split("]")[0].lstrip("[") for d in existing_diagnosis if "]" in d}
    for d in new_diagnosis:
        rule_id = d.split("]")[0].lstrip("[")
        if rule_id not in existing_ids:
            existing_diagnosis.append(d)
            existing_ids.add(rule_id)

    # 如果有高/中风险规则，在 final_reply 后追加超图诊断块
    high_medium = [r for r in triggered if r.severity in ("high", "medium")]
    final_reply = state.get("final_reply", "")

    if high_medium and final_reply:
        violations_text = format_violations(high_medium)
        final_reply = final_reply + "\n\n---\n" + violations_text

    # ── V2: Critic redirect 判断 ──
    # 当高置信度规则触发且尚未循环过时，生成 tutor 跳转信号
    critic_redirect = None
    knowledge_recs = None

    if loop_count == 0:  # 只允许一次重定向，防止无限循环
        redirect_candidates = [
            r for r in triggered
            if r.severity in _REDIRECT_SEVERITY
            and r.confidence >= _REDIRECT_CONFIDENCE_THRESHOLD
        ]

        if redirect_candidates:
            # 取最高置信度的规则
            top_rule = max(redirect_candidates, key=lambda r: r.confidence)
            triggered_ids = [r.rule_id for r in redirect_candidates[:3]]

            # 获取学习路径推荐
            recs = get_recommendations(triggered_ids)
            if recs:
                knowledge_recs = recs
                # 取第一个推荐概念作为 tutor 跳转目标
                critic_redirect = recs[0]["concept"]

                # 在 final_reply 中追加学习推荐
                rec_lines = ["\n\n**📚 推荐学习路径：**"]
                for rec in recs[:2]:
                    path = " → ".join(rec.get("learning_order", [rec["concept"]]))
                    rec_lines.append(f"  • **{rec['concept']}**：{rec['query']}")
                    if rec.get("learning_order") and len(rec["learning_order"]) > 1:
                        rec_lines.append(f"    学习顺序：{path}")
                final_reply += "\n".join(rec_lines)

    return {
        **state,
        "diagnosis": existing_diagnosis,
        "final_reply": final_reply,
        "triggered_rules": [r._asdict() for r in triggered],
        "critic_redirect": critic_redirect,
        "knowledge_recommendations": knowledge_recs,
        "loop_count": loop_count + 1,
    }
