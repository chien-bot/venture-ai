"""
services/evidence_tracer.py
────────────────────────────────────────────────────────────────
证据追踪引用系统

功能：
- 从对话历史中提取"证据片段"（用户提供的具体数据、引用、陈述）
- 给每条证据打标签（属于哪个维度 / Rubric 项）
- 在教师审查和 coach 回复中引用 "你在第N轮提到..."

证据类型：
  CLAIM   — 无数据支撑的主张（如："我认为市场很大"）
  DATA    — 带数字/来源的陈述（如："访谈了20个用户"）
  QUOTE   — 用户引用外部来源（如："根据艾瑞报告"）
  COMMIT  — 承诺/计划（如："下周会完成"）
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field, asdict
from typing import Optional


# ── Evidence categories ──────────────────────────────────────
RUBRIC_SIGNALS: dict[str, list[str]] = {
    "R1_pain_point":    ["痛点", "问题", "需求", "困难", "不方便", "麻烦"],
    "R2_user_evidence": ["访谈", "调研", "问卷", "用户说", "反馈", "测试了"],
    "R3_solution":      ["解决方案", "产品", "功能", "服务", "方案"],
    "R4_business_model":["商业模式", "盈利", "收费", "收入", "订阅", "佣金"],
    "R5_market":        ["市场", "TAM", "SAM", "SOM", "规模", "亿", "竞争"],
    "R6_finance":       ["财务", "成本", "LTV", "CAC", "盈亏", "利润"],
    "R7_innovation":    ["创新", "差异化", "护城河", "专利", "独特"],
    "R8_execution":     ["团队", "执行", "资源", "里程碑", "计划", "时间"],
    "R9_pitch":         ["路演", "PPT", "投资人", "Pitch", "表达"],
}

# Signals that suggest the statement has data backing
DATA_SIGNALS: list[str] = [
    r"\d+%",          # percentage
    r"\d+[\s]?人",    # number of people
    r"\d+[\s]?万",    # 10k units
    r"\d+[\s]?亿",    # 100M units
    r"根据", r"来源", r"数据显示", r"报告", r"研究",
    r"访谈了\d+", r"调研了\d+",
]

QUOTE_SIGNALS: list[str] = ["根据", "来源", "数据显示", "报告显示", "研究表明", "统计"]
COMMIT_SIGNALS: list[str] = ["会", "将", "打算", "计划", "准备", "下周", "下月", "明天"]
CLAIM_SIGNALS: list[str] = ["我认为", "应该", "可能", "大概", "估计", "感觉"]


@dataclass
class Evidence:
    turn: int              # message index (1-based, user messages only)
    text: str              # the extracted evidence snippet
    ev_type: str           # CLAIM | DATA | QUOTE | COMMIT
    rubric_tags: list[str] = field(default_factory=list)   # e.g. ["R2_user_evidence"]
    session_id: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    def citation(self) -> str:
        """Return a human-readable citation string."""
        tag_str = "、".join(self.rubric_tags) if self.rubric_tags else "通用"
        return f"（第{self.turn}轮·{self.ev_type}·{tag_str}）"


class EvidenceTracer:
    """
    Session-scoped evidence tracer with incremental ingestion.

    Usage:
        tracer = EvidenceTracer(session_id)
        tracer.ingest(messages)          # first call: scans all
        tracer.ingest(messages + [new])  # subsequent: only scans new messages
        evidences = tracer.get_by_rubric("R2_user_evidence")
        summary = tracer.summarize()
    """

    def __init__(self, session_id: str = ""):
        self.session_id = session_id
        self._evidences: list[Evidence] = []
        self._ingested_msg_count: int = 0  # how many messages already processed
        self._ingested_user_turn: int = 0  # user turn counter at last ingest

    # ── Ingestion ────────────────────────────────────────────

    def ingest(self, messages: list[dict]) -> None:
        """
        Incrementally scan conversation history and extract evidence.

        Only processes messages beyond what was already ingested.
        If the message list is shorter than previously ingested (e.g. new
        session), performs a full re-scan.
        """
        msg_count = len(messages)

        # Detect if history was reset (shorter than before) → full re-scan
        if msg_count < self._ingested_msg_count:
            self._evidences = []
            self._ingested_msg_count = 0
            self._ingested_user_turn = 0

        # Nothing new to process
        if msg_count <= self._ingested_msg_count:
            return

        # Count user turns in already-processed prefix to set correct turn counter
        user_turn = self._ingested_user_turn
        new_messages = messages[self._ingested_msg_count:]

        for msg in new_messages:
            if msg.get("role") != "user":
                continue
            user_turn += 1
            content = msg.get("content", "")
            # Split into sentences for finer granularity
            sentences = re.split(r"[。！？\n]", content)
            for sent in sentences:
                sent = sent.strip()
                if len(sent) < 5:
                    continue
                ev = self._classify(sent, user_turn)
                if ev:
                    self._evidences.append(ev)

        self._ingested_msg_count = msg_count
        self._ingested_user_turn = user_turn

    def _classify(self, text: str, turn: int) -> Optional[Evidence]:
        """Classify a sentence into an Evidence object."""
        # Detect rubric tags
        tags = []
        for rubric_key, signals in RUBRIC_SIGNALS.items():
            if any(s in text for s in signals):
                tags.append(rubric_key)

        if not tags:
            return None  # No relevant content

        # Determine evidence type
        has_data = any(re.search(p, text) for p in DATA_SIGNALS)
        has_quote = any(s in text for s in QUOTE_SIGNALS)
        has_commit = any(s in text for s in COMMIT_SIGNALS)
        has_claim = any(s in text for s in CLAIM_SIGNALS)

        if has_data or has_quote:
            ev_type = "DATA" if has_data else "QUOTE"
        elif has_commit:
            ev_type = "COMMIT"
        elif has_claim:
            ev_type = "CLAIM"
        else:
            ev_type = "DATA"  # default to DATA if tagged but no explicit type

        return Evidence(
            turn=turn,
            text=text[:120],  # cap length
            ev_type=ev_type,
            rubric_tags=tags,
            session_id=self.session_id,
        )

    # ── Query ────────────────────────────────────────────────

    def get_all(self) -> list[Evidence]:
        return self._evidences

    def get_by_rubric(self, rubric_key: str) -> list[Evidence]:
        return [e for e in self._evidences if rubric_key in e.rubric_tags]

    def get_by_type(self, ev_type: str) -> list[Evidence]:
        return [e for e in self._evidences if e.ev_type == ev_type]

    def get_claims_without_data(self) -> list[Evidence]:
        """Return CLAIM evidences that have no corresponding DATA evidence for same rubric."""
        data_covered: set[str] = set()
        for e in self._evidences:
            if e.ev_type in ("DATA", "QUOTE"):
                data_covered.update(e.rubric_tags)
        return [
            e for e in self._evidences
            if e.ev_type == "CLAIM" and not any(t in data_covered for t in e.rubric_tags)
        ]

    # ── Summary ──────────────────────────────────────────────

    def summarize(self) -> dict:
        """Return a structured summary of all collected evidence."""
        by_rubric: dict[str, list[dict]] = {}
        for e in self._evidences:
            for tag in e.rubric_tags:
                by_rubric.setdefault(tag, []).append(e.to_dict())

        weak_claims = [e.to_dict() for e in self.get_claims_without_data()]

        return {
            "total": len(self._evidences),
            "by_type": {
                "DATA": len(self.get_by_type("DATA")),
                "QUOTE": len(self.get_by_type("QUOTE")),
                "CLAIM": len(self.get_by_type("CLAIM")),
                "COMMIT": len(self.get_by_type("COMMIT")),
            },
            "by_rubric": {k: len(v) for k, v in by_rubric.items()},
            "weak_claims": weak_claims,
            "evidence_list": [e.to_dict() for e in self._evidences],
        }

    def format_for_coach(self, rubric_key: str) -> str:
        """
        返回可供 coach prompt 使用的证据引用文本，格式如：
        '你在第2轮提到「访谈了20个用户」，这是很好的 R2 证据。'
        """
        evs = self.get_by_rubric(rubric_key)
        if not evs:
            return ""
        lines = []
        for e in evs[:3]:  # limit to 3 most recent
            lines.append(f"你在第{e.turn}轮提到「{e.text}」{e.citation()}")
        return "\n".join(lines)

    def format_missing_evidence(self) -> str:
        """返回缺失数据支撑的主张列表，供 coach 追问。"""
        weak = self.get_claims_without_data()
        if not weak:
            return ""
        lines = ["以下主张尚缺乏数据支撑："]
        for e in weak[:5]:
            lines.append(f"  • 第{e.turn}轮：「{e.text[:60]}」")
        return "\n".join(lines)


# ── Session-level cache ───────────────────────────────────────
_tracers: dict[str, EvidenceTracer] = {}


def get_tracer(session_id: str) -> EvidenceTracer:
    """Get or create an EvidenceTracer for a session."""
    if session_id not in _tracers:
        _tracers[session_id] = EvidenceTracer(session_id)
    return _tracers[session_id]


def refresh_tracer(session_id: str, messages: list[dict]) -> EvidenceTracer:
    """Re-ingest all messages for the session and return updated tracer."""
    tracer = get_tracer(session_id)
    tracer.ingest(messages)
    return tracer
