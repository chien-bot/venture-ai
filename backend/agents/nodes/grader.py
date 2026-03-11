"""
agents/nodes/grader.py
────────────────────────────────────────────────────────────────
形成性评价 Agent（批改 Agent）

职责：
1. 读取对话历史 + 上传文件内容
2. 基于 Rubric R1-R9 对创业计划书进行逐项评分
3. 输出：分项得分、证据引用、修改建议
"""
from __future__ import annotations
import json
import re
from agents.state import AgentState
from services.claude_client import chat_completion
from config import USE_MOCK_API

GRADER_SYSTEM_PROMPT = """你是一位专业的创新创业评审专家，需要对学生的创业计划进行形成性评价。

请基于以下 Rubric 标准（R1-R9）对学生的创业项目进行详细评分：

- R1 痛点定义：问题清晰、具体、基于真实用户痛点 (10分)
- R2 用户证据：论点有充分且相关的证据支撑 (10分)
- R3 方案可行性：方案在技术和运营上可行 (10分)
- R4 商业模式：客户、价值主张、渠道、收入、成本保持一致 (10分)
- R5 市场竞争：有清晰的竞争分析和差异化定位 (10分)
- R6 财务逻辑：财务预测合理，有明确盈利路径 (10分)
- R7 创新差异化：有独特创新点或难以复制的竞争优势 (10分)
- R8 团队执行：团队具备执行所需的技能和资源 (10分)
- R9 表达材料：PPT/计划书结构清晰、逻辑完整 (10分)

评分规则：
- 每项 0-10 分
- 必须引用对话中的具体语句或证据作为评分依据
- 指出每项的主要不足和改进建议

请严格按照以下 JSON 格式输出评分结果（必须输出，不可省略）：
<!--RUBRIC_FULL:
{
  "R1": {"score": 7, "evidence": "学生提到...", "suggestion": "建议..."},
  "R2": {"score": 5, "evidence": "...", "suggestion": "..."},
  "R3": {"score": 6, "evidence": "...", "suggestion": "..."},
  "R4": {"score": 4, "evidence": "...", "suggestion": "..."},
  "R5": {"score": 5, "evidence": "...", "suggestion": "..."},
  "R6": {"score": 3, "evidence": "...", "suggestion": "..."},
  "R7": {"score": 7, "evidence": "...", "suggestion": "..."},
  "R8": {"score": 6, "evidence": "...", "suggestion": "..."},
  "R9": {"score": 5, "evidence": "...", "suggestion": "..."}
}
-->

在 JSON 之前，请先用中文给出2-3段综合评价，指出项目的最大亮点和最需要改进的方向。
"""


def _parse_rubric_full(text: str) -> dict | None:
    match = re.search(r"<!--RUBRIC_FULL:\s*([\s\S]*?)-->", text)
    if match:
        try:
            return json.loads(match.group(1).strip())
        except json.JSONDecodeError:
            return None
    return None


def _clean(text: str) -> str:
    return re.sub(r"<!--RUBRIC_FULL:[\s\S]*?-->", "", text).strip()


def _mock_grader() -> str:
    return """根据你提交的材料，以下是形成性评价报告：

**综合评价：**

你的项目有明确的目标用户群体，但在市场证据和竞争分析方面还需要加强。商业模式的逻辑性基本清晰，但财务预测过于乐观，缺少具体的数据支撑。

建议重点补充：用户访谈记录、竞争对手分析、以及更保守的财务预测。

<!--RUBRIC_FULL:
{
  "R1": {"score": 7, "evidence": "学生明确定义了目标用户群体", "suggestion": "建议进一步细化用户痛点的严重程度和频率"},
  "R2": {"score": 4, "evidence": "仅有主观判断，缺少访谈数据", "suggestion": "需要至少10份真实用户访谈记录"},
  "R3": {"score": 6, "evidence": "技术方案基本可行", "suggestion": "需要更详细的技术路线图和风险评估"},
  "R4": {"score": 5, "evidence": "商业模式画布不完整", "suggestion": "补充完整的收入来源和成本结构"},
  "R5": {"score": 4, "evidence": "仅列举了直接竞争对手", "suggestion": "需要分析替代品和潜在进入者"},
  "R6": {"score": 3, "evidence": "财务预测过于乐观", "suggestion": "基于真实CAC和转化率重新建模"},
  "R7": {"score": 7, "evidence": "核心技术有一定创新性", "suggestion": "需要量化与竞品的差异"},
  "R8": {"score": 6, "evidence": "团队有相关背景", "suggestion": "补充关键岗位的具体分工"},
  "R9": {"score": 5, "evidence": "材料结构基本完整", "suggestion": "加强数据可视化和逻辑连接"}
}
-->"""


def grader_node(state: AgentState) -> AgentState:
    """形成性评价节点：对创业项目进行 Rubric R1-R9 评分。"""
    messages = state.get("messages", [])

    if USE_MOCK_API:
        raw = _mock_grader()
    else:
        raw = chat_completion(GRADER_SYSTEM_PROMPT, messages)

    rubric_full = _parse_rubric_full(raw)
    clean = _clean(raw)

    # Build rubric_scores dict for compatibility with existing schema
    rubric_scores = None
    if rubric_full:
        rubric_scores = {k: v["score"] for k, v in rubric_full.items()}

    return {
        **state,
        "coach_output": clean,
        "rubric_scores": rubric_scores,
        "rubric_full": rubric_full,
    }
