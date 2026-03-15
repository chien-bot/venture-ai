"""Router node: classifies user intent and routes to the right agent."""

from agents.state import AgentState
from config import USE_MOCK_API
from services.claude_client import chat_completion

# Concepts the tutor can explain
TUTOR_KEYWORDS = [
    "PMF", "CAC", "LTV", "TAM", "SAM", "SOM", "JTBD", "AARRR", "SWOT", "BEP",
    "产品市场契合", "获客成本", "终身价值", "市场规模", "商业模式画布", "精益画布",
    "波特五力", "价值主张", "护城河", "用户画像", "竞品分析",
    "什么是", "解释一下", "帮我理解", "概念", "定义", "怎么算",
]

COMPETITION_KEYWORDS = [
    "竞赛评分", "rubric评分", "Rubric评分", "挑战杯评分", "互联网+评分",
    "评估我的项目", "帮我打分", "按rubric", "按Rubric", "竞赛打分",
]

GRADER_KEYWORDS = [
    "批改", "形成性评价", "评价我的计划", "批改计划书", "给我打分",
    "rubric评分", "全面评估", "评价一下", "综合评分", "帮我评分",
    "评价报告", "改进建议", "修改意见", "帮我评价", "形成性",
]

CONFUSION_WORDS = [
    "不懂", "不理解", "什么意思", "不太明白", "不太懂",
    "不清楚", "搞不懂", "没搞懂", "不知道", "怎么理解",
]

ROUTER_SYSTEM_PROMPT = """你是一个意图分类器。根据用户最新消息和对话历史，判断应该调用哪个 Agent。

输出必须是以下之一（只输出这一个词，不要有其他内容）：
- coach     → 用户在讨论项目想法、商业模式、团队、执行、路演等创业话题，或者只是打招呼/闲聊
- tutor     → 用户在询问某个创业/商业概念的定义或解释
- competition → 用户明确要求"按rubric打分"或"竞赛评分"（必须有明确打分请求才触发）
- grader    → 用户要求对整个项目/计划书进行全面批改、形成性评价、生成改进建议报告
- hybrid    → 用户同时涉及概念疑问 + 项目讨论（先解释概念再继续教练对话）

重要规则：
- 简单问候（你好、hi、hello、在吗）→ 一律输出 coach
- 讨论路演、投资人、pitch、答辩技巧 → 输出 coach（这是正常教练对话，不是竞赛评分）
- 只有当消息中明确包含商业概念词（如PMF、LTV、CAC等）且同时在讨论项目时，才输出 hybrid
- "批改"、"形成性评价"、"全面评估"、"改进建议" → grader
- competition 仅当用户明确说"帮我按rubric打分"、"竞赛评分"时才触发
- 如果不确定，默认输出 coach

示例：
"你好" → coach
"我想做一个帮助老人的APP" → coach
"我怎么练习路演" → coach
"投资人会问哪些问题" → coach
"PMF 是什么意思" → tutor
"帮我按rubric评分" → competition
"帮我批改一下我的计划书" → grader
"我不太明白 LTV，但我觉得我的项目盈利模式..." → hybrid
"""


def _detect_concept(message: str) -> str | None:
    """Try to extract the concept name from the message."""
    concepts = ["PMF", "CAC", "LTV", "TAM", "SAM", "SOM", "JTBD", "AARRR",
                "SWOT", "BEP", "Lean Canvas", "精益画布", "商业模式画布",
                "波特五力", "价值主张", "护城河"]
    for c in concepts:
        if c.upper() in message.upper():
            return c
    return None


def _mock_route(message: str) -> tuple[str, str | None]:
    """Keyword-based routing for mock mode."""
    msg_upper = message.upper()

    # Check grader keywords first
    if any(kw in message for kw in GRADER_KEYWORDS):
        return "grader", None

    # Check competition keywords
    if any(kw.upper() in msg_upper for kw in COMPETITION_KEYWORDS):
        return "competition", None

    # Check hybrid: conceptual confusion + project discussion
    has_concept = any(kw.upper() in msg_upper for kw in TUTOR_KEYWORDS)
    has_confusion = any(w in message for w in CONFUSION_WORDS)
    has_project = any(kw in message for kw in ["项目", "我想", "方案", "用户", "市场", "产品", "但"])

    if has_concept and has_confusion and has_project:
        return "hybrid", _detect_concept(message)

    # Pure tutor
    if has_concept and has_confusion:
        return "tutor", _detect_concept(message)
    if "什么是" in message or "解释" in message or "帮我理解" in message:
        return "tutor", _detect_concept(message)

    return "coach", None


def router_node(state: AgentState) -> AgentState:
    message = state["current_message"]

    if USE_MOCK_API:
        intent, concept = _mock_route(message)
    else:
        # Use a lightweight LLM call for classification
        history_snippet = state["messages"][-4:] if len(state["messages"]) >= 4 else state["messages"]
        classification_messages = history_snippet + [{"role": "user", "content": message}]
        try:
            from config import MODEL_LIGHT
            intent = chat_completion(ROUTER_SYSTEM_PROMPT, classification_messages, model=MODEL_LIGHT).strip().lower()
            if intent not in ("coach", "tutor", "competition", "grader", "hybrid"):
                intent = "coach"
        except Exception:
            intent = "coach"
        concept = _detect_concept(message)

    return {
        **state,
        "intent": intent,
        "tutor_concept": concept,
    }
