"""
agents/nodes/grader.py
────────────────────────────────────────────────────────────────
形成性评价 Agent（批改 Agent）

职责：
1. 读取对话历史 + 上传文件内容
2. 基于 Rubric R1-R11 对创业计划书进行逐项评分
3. 输出：分项得分、证据引用、修改建议
"""
from __future__ import annotations
import json
import re
from agents.state import AgentState
from services.claude_client import chat_completion
from config import USE_MOCK_API
from services.debug_logger import DebugLogger

_dbg = DebugLogger("grader_node")

GRADER_SYSTEM_PROMPT = """你是一位专业的创新创业评审专家，需要对学生的创业计划进行形成性评价。

请基于以下 Rubric 标准（R1-R11）对学生的创业项目进行详细评分：

- R1 痛点定义：问题清晰、具体、基于真实用户痛点 (5分)
- R2 用户证据：论点有充分且相关的证据支撑 (5分)
- R3 方案可行性：方案在技术和运营上可行 (5分)
- R4 商业模式：客户、价值主张、渠道、收入、成本保持一致 (5分)
- R5 市场竞争：有清晰的竞争分析和差异化定位 (5分)
- R6 财务逻辑：财务预测合理，有明确盈利路径 (5分)
- R7 创新差异化：有独特创新点或难以复制的竞争优势 (5分)
- R8 团队执行：团队具备执行所需的技能和资源 (5分)
- R9 表达材料：PPT/计划书结构清晰、逻辑完整 (5分)
- R10 合规与社会责任：法律合规、伦理风险与社会影响已充分评估 (5分)
- R11 增长与规模化：增长路径有阶段性逻辑，规模化策略可行 (5分)

评分规则：
- 每项 0-5 分
- 必须引用对话中的具体语句或证据作为评分依据
- 指出每项的主要不足和改进建议

请严格按照以下 JSON 格式输出评分结果（必须输出，不可省略）：
<!--RUBRIC_FULL:
{
  "R1": {"score": 3, "evidence": "学生提到...", "suggestion": "建议..."},
  "R2": {"score": 2, "evidence": "...", "suggestion": "..."},
  "R3": {"score": 3, "evidence": "...", "suggestion": "..."},
  "R4": {"score": 2, "evidence": "...", "suggestion": "..."},
  "R5": {"score": 2, "evidence": "...", "suggestion": "..."},
  "R6": {"score": 1, "evidence": "...", "suggestion": "..."},
  "R7": {"score": 3, "evidence": "...", "suggestion": "..."},
  "R8": {"score": 3, "evidence": "...", "suggestion": "..."},
  "R9": {"score": 2, "evidence": "...", "suggestion": "..."},
  "R10": {"score": 2, "evidence": "...", "suggestion": "..."},
  "R11": {"score": 2, "evidence": "...", "suggestion": "..."}
}
-->

在 JSON 注释之前，请先用中文给出2-3段综合评价，指出项目的最大亮点和最需要改进的方向。

⚠️ 绝对不能违反的规则（必须遵守）：
- 正文中绝对禁止出现任何JSON格式（包括 { } [ ] 等符号的数据结构）
- 正文中绝对禁止出现评分数字或 "R1", "R2" 等标签
- 绝对禁止出现 "score:", "evidence:", "suggestion:" 等JSON字段名
- 所有结构化数据必须且只能放在 <!--RUBRIC_FULL:...--> HTML注释中
- 学生只会看到中文段落文字，完全看不到任何JSON或评分数据

正文格式示例：
✅ 好：「你的项目在用户痛点定义方面表现不错，清晰地描述了目标用户的核心需求。在商业模式方面还需加强，特别是收入来源的论证...」
❌ 坏：「R1评分为3分，因为...」或任何包含JSON的输出

只有HTML注释中可以出现JSON数据。
"""


def _parse_rubric_full(text: str) -> dict | None:
    from services.marker_parser import parse_rubric_full
    return parse_rubric_full(text)


def _clean(text: str) -> str:
    from services.marker_parser import clean_reply
    return clean_reply(text)


def _mock_grader() -> str:
    return """根据你提交的材料，以下是形成性评价报告：

**综合评价：**

你的项目有明确的目标用户群体，但在市场证据和竞争分析方面还需要加强。商业模式的逻辑性基本清晰，但财务预测过于乐观，缺少具体的数据支撑。

建议重点补充：用户访谈记录、竞争对手分析、以及更保守的财务预测。

<!--RUBRIC_FULL:
{
  "R1": {"score": 3, "evidence": "学生明确定义了目标用户群体", "suggestion": "建议进一步细化用户痛点的严重程度和频率"},
  "R2": {"score": 2, "evidence": "仅有主观判断，缺少访谈数据", "suggestion": "需要至少10份真实用户访谈记录"},
  "R3": {"score": 3, "evidence": "技术方案基本可行", "suggestion": "需要更详细的技术路线图和风险评估"},
  "R4": {"score": 2, "evidence": "商业模式画布不完整", "suggestion": "补充完整的收入来源和成本结构"},
  "R5": {"score": 2, "evidence": "仅列举了直接竞争对手", "suggestion": "需要分析替代品和潜在进入者"},
  "R6": {"score": 1, "evidence": "财务预测过于乐观", "suggestion": "基于真实CAC和转化率重新建模"},
  "R7": {"score": 3, "evidence": "核心技术有一定创新性", "suggestion": "需要量化与竞品的差异"},
  "R8": {"score": 3, "evidence": "团队有相关背景", "suggestion": "补充关键岗位的具体分工"},
  "R9": {"score": 2, "evidence": "材料结构基本完整", "suggestion": "加强数据可视化和逻辑连接"},
  "R10": {"score": 2, "evidence": "未提及合规和伦理风险评估", "suggestion": "补充数据隐私合规分析和知识产权清单"},
  "R11": {"score": 1, "evidence": "缺乏阶段性增长规划", "suggestion": "制定种子期→扩展期→规模期的增长路径"}
}
-->"""


def grader_node(state: AgentState) -> AgentState:
    """形成性评价节点：对创业项目进行 Rubric R1-R11 评分。"""
    session_id = state.get("session_id", "")
    messages = state.get("messages", [])

    _dbg.agent_start(session_id=session_id, intent="grader", message_preview=state.get("current_message", ""))

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
        # Log each rubric rule evaluation
        for rule_id, detail in rubric_full.items():
            score = detail.get("score", 0)
            severity = "high" if score <= 1 else ("medium" if score <= 2 else "low")
            _dbg.rule_triggered(
                rule_id=rule_id,
                rule_type=f"rubric_score={score}/5",
                severity=severity,
                confidence=round(score / 5, 3),
            )

    _dbg.agent_done(scores=rubric_scores, stage="grader")

    return {
        **state,
        "coach_output": clean,
        "rubric_scores": rubric_scores,
        "rubric_full": rubric_full,
    }
