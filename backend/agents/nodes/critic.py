"""
agents/nodes/critic.py
────────────────────────────────────────────────────────────────
Critic Agent 节点

职责：
1. 调用超图一致性检查器，检测 H1-H15 约束规则是否被触发
2. 将违规规则注入 diagnosis，追加到 coach/competition 输出后
3. 在 final_reply 中追加结构化的超图诊断提示（仅当有触发时）

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


def critic_node(state: AgentState) -> AgentState:
    """
    在所有 agent 输出之后运行，进行超图约束检测。
    修改 state 中的 diagnosis 和 (如有) final_reply。
    """
    messages = state.get("messages", [])
    current_message = state.get("current_message", "")

    # 运行超图一致性检验
    triggered: list[TriggeredRule] = check_conversation(messages, current_message)

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

    return {
        **state,
        "diagnosis": existing_diagnosis,
        "final_reply": final_reply,
        # expose triggered rules for downstream use (e.g., teacher dashboard)
        "triggered_rules": [r._asdict() for r in triggered],
    }
