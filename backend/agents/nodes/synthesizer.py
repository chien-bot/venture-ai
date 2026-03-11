"""Synthesizer node: merges multi-agent outputs into a single reply."""

from agents.state import AgentState


def synthesizer_node(state: AgentState) -> AgentState:
    intent = state.get("intent", "coach")
    parts = []

    if intent == "hybrid":
        # Tutor explanation first, then coach follow-up
        if state.get("tutor_output"):
            concept = state.get("tutor_concept") or "概念"
            parts.append(f"### 关于「{concept}」的解释\n\n{state['tutor_output']}")
        if state.get("coach_output"):
            parts.append(f"---\n\n### 回到你的项目\n\n{state['coach_output']}")
        final = "\n\n".join(parts) if parts else state.get("coach_output", "")

    elif intent == "tutor":
        final = state.get("tutor_output", "")

    elif intent == "competition":
        final = state.get("competition_output", "")

    else:
        # coach (default)
        final = state.get("coach_output", "")

    return {
        **state,
        "final_reply": final,
    }
