"""
services/debug_logger.py
────────────────────────────────────────────────────────────────
结构化 Debug 日志系统

满足测试文档 2.1 可观测性要求，明文打印以下关键中间态：
  - agent_name            当前处理的智能体名称
  - retrieved_kg_nodes    检索到的知识图谱节点
  - retrieved_hyperedges  检索到的超图超边（异构子图）
  - fallacy_label         识别到的谬误类型
  - rule_triggered        触发的约束规则
  - selected_strategy     选择的追问策略
  - generated_question    生成的追问内容（摘要）
  - strategy_selected     与 selected_strategy 同义，兼容测试文档两种写法

使用方式：
    from services.debug_logger import DebugLogger
    log = DebugLogger("coach_node")
    log.agent_start(session_id="xxx", intent="coach")
    log.retrieved_nodes(["PMF", "CAC", "proj_abc"])
    log.fallacy_detected("大数幻觉谬误", triggered_by="1%中国人")
    log.strategy_selected("市场规模幻觉", question="你的第一批100个用户从哪里来？")
    log.rule_triggered("H8", "LTV < CAC or unrealistic assumptions")
    log.agent_done(scores={"empathy": 6.0})
"""
from __future__ import annotations

import json
import logging
import sys
from datetime import datetime
from typing import Any

# 全局 debug logger — 输出到 stdout，便于测试人员直接查看终端
_handler = logging.StreamHandler(sys.stdout)
_handler.setFormatter(logging.Formatter("%(message)s"))

_debug_logger = logging.getLogger("venture_ai.debug")
_debug_logger.addHandler(_handler)
_debug_logger.setLevel(logging.DEBUG)
_debug_logger.propagate = False  # 避免与 root logger 重复输出


def _ts() -> str:
    return datetime.now().strftime("%H:%M:%S.%f")[:-3]


def _fmt(data: Any) -> str:
    if isinstance(data, (dict, list)):
        return json.dumps(data, ensure_ascii=False, indent=2)
    return str(data)


class DebugLogger:
    """
    每个 Agent 节点创建一个实例，统一管理该节点的结构化日志输出。
    所有日志以 [DEBUG][agent_name] 开头，便于过滤。
    """

    def __init__(self, agent_name: str):
        self.agent_name = agent_name
        self._prefix = f"[DEBUG][{agent_name}]"

    def _emit(self, tag: str, payload: str):
        _debug_logger.debug(f"{_ts()} {self._prefix}[{tag}] {payload}")

    def agent_start(self, session_id: str = "", intent: str = "", message_preview: str = ""):
        """智能体开始处理。"""
        self._emit("AGENT_START", json.dumps({
            "agent_name": self.agent_name,
            "session_id": session_id,
            "intent": intent,
            "message_preview": message_preview[:80] + ("…" if len(message_preview) > 80 else ""),
        }, ensure_ascii=False))

    def retrieved_nodes(self, nodes: list[str], source: str = "hypergraph"):
        """
        打印检索到的知识图谱节点（retrieved_kg_nodes）。
        满足 A1-3 KG Baseline Retrieval 的日志校验要求。
        """
        self._emit("RETRIEVED_KG_NODES", json.dumps({
            "retrieved_kg_nodes": nodes,
            "source": source,
            "count": len(nodes),
        }, ensure_ascii=False))

    def retrieved_hyperedges(self, edges: list[dict], edge_types: list[str] | None = None):
        """
        打印检索到的超图超边（retrieved_heterogeneous_subgraph）。
        满足 A3 异构超图检索断言要求。
        """
        self._emit("RETRIEVED_HYPEREDGES", json.dumps({
            "retrieved_heterogeneous_subgraph": edges[:5],   # 最多打印前5条
            "edge_types": edge_types or list({e.get("type", "unknown") for e in edges}),
            "total_edges": len(edges),
        }, ensure_ascii=False))

    def fallacy_detected(self, fallacy_label: str, triggered_by: str = "", confidence: float = 0.0):
        """
        打印识别到的谬误标签（fallacy_label）。
        满足 A3 通过标准：日志必须明文记录 fallacy_label。
        """
        self._emit("FALLACY_LABEL", json.dumps({
            "fallacy_label": fallacy_label,
            "triggered_by": triggered_by,
            "confidence": round(confidence, 3),
        }, ensure_ascii=False))

    def strategy_selected(self, strategy_name: str, question: str = ""):
        """
        打印选择的追问策略和生成的追问（selected_strategy + generated_question）。
        满足 A3 通过标准：日志必须明文记录 selected_strategy 和 generated_question。
        """
        self._emit("STRATEGY_SELECTED", json.dumps({
            "selected_strategy": strategy_name,
            "strategy_selected": strategy_name,      # 两种字段名都输出，兼容测试文档
            "generated_question": question[:200] + ("…" if len(question) > 200 else ""),
        }, ensure_ascii=False))

    def rule_triggered(self, rule_id: str, rule_type: str = "", severity: str = "", confidence: float = 0.0):
        """
        打印触发的约束规则（rule_triggered）。
        满足 A4 通过标准：日志明文记录 rule_id 和触发信息。
        """
        self._emit("RULE_TRIGGERED", json.dumps({
            "rule_triggered": rule_id,
            "rule_id": rule_id,
            "rule_type": rule_type,
            "severity": severity,
            "confidence": round(confidence, 3),
        }, ensure_ascii=False))

    def competition_template(self, template_name: str, rubric_weights: dict):
        """打印赛事模板切换信息（A5-2）。"""
        self._emit("COMPETITION_TEMPLATE", json.dumps({
            "template_name": template_name,
            "rubric_weights": rubric_weights,
        }, ensure_ascii=False))

    def agent_done(self, scores: dict | None = None, stage: str = "", diagnosis: list | None = None):
        """智能体处理完成摘要。"""
        self._emit("AGENT_DONE", json.dumps({
            "agent_name": self.agent_name,
            "stage": stage,
            "scores": scores or {},
            "diagnosis_count": len(diagnosis or []),
        }, ensure_ascii=False))

    def info(self, message: str):
        """通用 info 日志。"""
        self._emit("INFO", message)

    def warning(self, message: str):
        self._emit("WARNING", message)
