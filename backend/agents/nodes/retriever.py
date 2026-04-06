"""
agents/nodes/retriever.py
────────────────────────────────────────────────────────────────
超图检索节点 (Retriever Node) — V3 缓存增强版

在 LangGraph 流程中，这个节点在 router 之后、coach/tutor/competition 之前运行。

V2 改进：
1. 用 LLM（MODEL_LIGHT）做语义提取，替代硬编码关键词表
2. 用 TF-IDF 向量相似度做项目检索，替代关键词交集匹配
3. 保留关键词匹配作为 fallback（LLM 不可用时）
4. 两层融合：LLM 提取结果 + 语义检索结果合并去重

V3 改进：
- Session 级检索缓存：相同提取结果（techs/industry/concept）命中缓存，跳过
  search_projects + query_hypergraph，节省 100-200ms/轮
- 缓存键为提取结果的哈希；用户切换话题时自动失效

RAG 流程：
  学生输入 → LLM语义提取 → [缓存命中?] → 超图检索（语义+关键词） → 上下文注入
"""
from __future__ import annotations

import logging
from agents.state import AgentState
from hypergraph.engine import query_hypergraph, format_context_for_prompt
from hypergraph.semantic_retriever import search_projects, detect_technologies, detect_industry, detect_concepts
from hypergraph.llm_extractor import extract_from_conversation
from services.debug_logger import DebugLogger

logger = logging.getLogger(__name__)
_dbg = DebugLogger("retriever_node")


# ── V3: Session-level retrieval cache ────────────────────────
class _RetrieverCache:
    """Per-session cache for retriever results."""
    __slots__ = ("cache_key", "context_text", "techs", "industry", "concept")

    def __init__(self):
        self.cache_key: str = ""
        self.context_text: str = ""
        self.techs: list[str] = []
        self.industry: str = ""
        self.concept: str = ""


_session_retriever_cache: dict[str, _RetrieverCache] = {}


def _make_cache_key(techs: list[str], industry: str, concept: str) -> str:
    """Build a stable cache key from extraction results."""
    return f"{','.join(sorted(t.lower() for t in techs))}|{industry}|{concept}"


def _run_search(
    current: str,
    messages: list[dict],
    tech_kws: list[str],
    industry: str,
    concept: str,
    project_desc: str,
) -> str:
    """Execute the full search pipeline (semantic + hypergraph) and return formatted context."""

    # ── 语义相似度搜索项目案例 ──
    user_msgs = [m["content"] for m in messages if m.get("role") == "user"]
    search_query = current
    if project_desc:
        search_query = project_desc + " " + search_query
    if user_msgs:
        search_query += " " + " ".join(user_msgs[-3:])

    semantic_results = search_projects(
        query=search_query,
        top_k=5,
        min_score=0.03,
        industry_filter="",
    )

    # ── 超图结构化检索 ──
    ctx = query_hypergraph(
        tech_keywords=tech_kws if tech_kws else None,
        industry=industry if industry != "通用" else "",
        concept=concept,
    )

    # ── 融合语义搜索结果 ──
    existing_ids = {p.get("name") for p in ctx.get("similar_projects", [])}
    for result in semantic_results:
        if result.label not in existing_ids:
            ctx["similar_projects"].append({
                "name": result.label,
                "industry": result.industry,
                "techs": result.technologies[:3],
                "has_moat": False,
                "has_biz_model": False,
                "semantic_score": result.score,
            })
            existing_ids.add(result.label)

    ctx["similar_projects"].sort(
        key=lambda p: p.get("semantic_score", 0),
        reverse=True,
    )
    ctx["similar_projects"] = ctx["similar_projects"][:8]

    return format_context_for_prompt(ctx)


def retriever_node(state: AgentState) -> AgentState:
    """
    超图检索节点（V3 缓存增强）。

    策略：
    1. 用 LLM 从当前消息提取 techs/industry/concept（精确）
    2. 检查 session 级缓存 — 提取结果不变则直接返回上次检索结果
    3. 缓存未命中时执行完整检索（语义 + 超图），写入缓存
    """
    messages = state.get("messages", [])
    current = state.get("current_message", "")
    session_id = state.get("session_id", "")

    # ── Step 1: 语义提取（LLM + TF-IDF 融合） ──
    extracted = extract_from_conversation(messages, current, window=5)
    tech_kws = extracted["techs"]
    industry = extracted["industry"]
    concept = extracted["concept"]
    project_desc = extracted.get("project_desc", "")

    logger.info(
        f"Retriever extracted: techs={tech_kws}, "
        f"industry={industry}, concept={concept}, desc={project_desc}"
    )
    _dbg.agent_start(session_id=session_id, intent="retrieval",
                     message_preview=current)
    _dbg.retrieved_nodes(tech_kws + ([concept] if concept else []), source="llm_extraction")

    # ── Step 2: 缓存检查 ──
    cache_key = _make_cache_key(tech_kws, industry, concept)
    cache = _session_retriever_cache.get(session_id)

    if cache and cache.cache_key == cache_key:
        # Cache hit — same extraction, reuse previous search results
        logger.info(f"Retriever cache HIT for session {session_id}")
        _dbg.info(f"Cache HIT for session {session_id} — reusing previous retrieval results")
        return {
            **state,
            "hypergraph_context": cache.context_text,
            "extracted_techs": cache.techs,
            "extracted_industry": cache.industry,
            "extracted_concept": cache.concept,
        }

    # ── Step 3: 缓存未命中 — 执行完整检索 ──
    logger.info(f"Retriever cache MISS for session {session_id}")
    _dbg.info(f"Cache MISS — executing full hypergraph search (techs={tech_kws}, industry={industry}, concept={concept})")
    context_text = _run_search(
        current, messages, tech_kws, industry, concept, project_desc,
    )
    # Log retrieved hyperedge types inferred from context
    edge_types_detected = []
    if "价值闭环" in context_text or "商业模式" in context_text:
        edge_types_detected.append("Value_Loop_Edge")
    if "风险" in context_text or "失败" in context_text:
        edge_types_detected.append("Risk_Pattern_Edge")
    if "竞争" in context_text or "替代" in context_text:
        edge_types_detected.append("Competition_Edge")
    if tech_kws:
        edge_types_detected.append("Technology_Hierarchy_Edge")
    _dbg.retrieved_hyperedges(
        [{"type": et, "query_context": f"techs={tech_kws}, industry={industry}"} for et in edge_types_detected],
        edge_types=edge_types_detected,
    )

    # ── Step 4: 写入缓存 ──
    new_cache = _RetrieverCache()
    new_cache.cache_key = cache_key
    new_cache.context_text = context_text
    new_cache.techs = tech_kws
    new_cache.industry = industry
    new_cache.concept = concept
    _session_retriever_cache[session_id] = new_cache

    return {
        **state,
        "hypergraph_context": context_text,
        "extracted_techs": tech_kws,
        "extracted_industry": industry,
        "extracted_concept": concept,
    }
