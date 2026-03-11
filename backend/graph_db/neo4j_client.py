"""
graph_db/neo4j_client.py
────────────────────────────────────────────────────────────────
Neo4j 图数据库客户端

功能：
- 将知识图谱节点（KGNode）和边（KGEdge）同步到 Neo4j
- 将超图约束规则（H1-H15）作为 HyperEdge 节点存储
- 提供 Cypher 查询接口：路径搜索、相关规则查询等
- 可选集成：NEO4J_URI 未配置时自动降级，不影响系统运行

Neo4j Schema：
  (:Concept {id, label, labelEn, type, description})
  (:HyperEdge {id, name, severity, trigger, fix})
  (:Concept)-[:PREREQ|USES|PRODUCES|MEASURED_BY|EVIDENCED_BY]->(:Concept)
  (:HyperEdge)-[:CONSTRAINS]->(:Concept)
"""
from __future__ import annotations

import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)

# ── Config ────────────────────────────────────────────────────
NEO4J_URI      = os.getenv("NEO4J_URI", "")          # e.g. "bolt://localhost:7687"
NEO4J_USER     = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "")

_driver = None
_available = False


def _get_driver():
    global _driver, _available
    if _driver is not None:
        return _driver
    if not NEO4J_URI:
        return None
    try:
        from neo4j import GraphDatabase
        _driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
        _driver.verify_connectivity()
        _available = True
        logger.info(f"Neo4j connected: {NEO4J_URI}")
        return _driver
    except Exception as e:
        logger.warning(f"Neo4j unavailable, falling back to in-memory: {e}")
        _available = False
        return None


def is_available() -> bool:
    return _get_driver() is not None


# ── Knowledge Graph data (inline, mirrors frontend TS data) ──
_KG_NODES = [
    {"id": "pmf",     "label": "产品市场契合", "labelEn": "PMF",                    "type": "concept"},
    {"id": "moat",    "label": "护城河",       "labelEn": "Moat",                   "type": "concept"},
    {"id": "vp",      "label": "价值主张",     "labelEn": "Value Proposition",      "type": "concept"},
    {"id": "tam",     "label": "市场规模",     "labelEn": "TAM/SAM/SOM",            "type": "concept"},
    {"id": "persona", "label": "用户画像",     "labelEn": "User Persona",           "type": "concept"},
    {"id": "jtbd",    "label": "待办工作",     "labelEn": "JTBD",                   "type": "method"},
    {"id": "bmc",     "label": "商业模式画布", "labelEn": "Business Model Canvas",  "type": "method"},
    {"id": "lean",    "label": "精益画布",     "labelEn": "Lean Canvas",            "type": "method"},
    {"id": "swot",    "label": "SWOT 分析",   "labelEn": "SWOT",                   "type": "method"},
    {"id": "porter",  "label": "波特五力",     "labelEn": "Porter's Five Forces",   "type": "method"},
    {"id": "aarrr",   "label": "海盗指标",     "labelEn": "AARRR",                  "type": "method"},
    {"id": "cac",     "label": "获客成本",     "labelEn": "CAC",                    "type": "metric"},
    {"id": "ltv",     "label": "用户终身价值", "labelEn": "LTV",                    "type": "metric"},
    {"id": "bep",     "label": "盈亏平衡点",   "labelEn": "BEP",                    "type": "metric"},
    {"id": "mrr",     "label": "月经常性收入", "labelEn": "MRR",                    "type": "metric"},
    {"id": "churn",   "label": "流失率",       "labelEn": "Churn Rate",             "type": "metric"},
    {"id": "interview","label": "用户访谈",    "labelEn": "User Interview",         "type": "task"},
    {"id": "mvp",     "label": "最小可行产品", "labelEn": "MVP",                    "type": "task"},
    {"id": "abtest",  "label": "A/B 测试",    "labelEn": "A/B Test",               "type": "task"},
    {"id": "pitch",   "label": "路演材料",     "labelEn": "Pitch Deck",             "type": "artifact"},
    {"id": "bizplan", "label": "商业计划书",   "labelEn": "Business Plan",          "type": "artifact"},
]

_KG_EDGES = [
    ("interview", "pmf",     "PREREQ"),
    ("interview", "vp",      "EVIDENCED_BY"),
    ("persona",   "interview","PREREQ"),
    ("jtbd",      "persona",  "USES"),
    ("vp",        "bmc",      "PREREQ"),
    ("lean",      "bmc",      "USES"),
    ("pmf",       "moat",     "PREREQ"),
    ("tam",       "bmc",      "USES"),
    ("porter",    "moat",     "USES"),
    ("porter",    "swot",     "USES"),
    ("mvp",       "pmf",      "PRODUCES"),
    ("mvp",       "abtest",   "PREREQ"),
    ("abtest",    "aarrr",    "MEASURED_BY"),
    ("cac",       "aarrr",    "MEASURED_BY"),
    ("ltv",       "aarrr",    "MEASURED_BY"),
    ("ltv",       "cac",      "MEASURED_BY"),
    ("bep",       "bmc",      "MEASURED_BY"),
    ("mrr",       "ltv",      "PRODUCES"),
    ("churn",     "ltv",      "MEASURED_BY"),
    ("bmc",       "bizplan",  "PRODUCES"),
    ("bmc",       "pitch",    "PRODUCES"),
    ("swot",      "bizplan",  "USES"),
    ("tam",       "pitch",    "EVIDENCED_BY"),
]

_HYPEREDGES = [
    {"id":"H1",  "name":"客户–价值主张错位",    "severity":"high",   "nodes":["persona","vp","bmc"],           "trigger":"客户群体与价值主张不匹配",         "fix":"重新定义目标客户或调整价值主张"},
    {"id":"H2",  "name":"渠道不可达",           "severity":"high",   "nodes":["persona","bmc","tam"],          "trigger":"选定渠道无法触达目标客户",         "fix":"验证渠道可达性，提供触达证据"},
    {"id":"H3",  "name":"定价无支付意愿证据",   "severity":"medium", "nodes":["vp","interview","mvp"],         "trigger":"缺乏用户支付意愿的验证数据",       "fix":"进行支付意愿调研或预售测试"},
    {"id":"H4",  "name":"TAM/SAM/SOM口径混乱", "severity":"medium", "nodes":["tam","bmc","pitch"],            "trigger":"市场规模估算的数据来源不一致",     "fix":"统一数据口径，自下而上重新估算"},
    {"id":"H5",  "name":"需求证据不足",         "severity":"high",   "nodes":["interview","pmf","vp"],         "trigger":"用户痛点缺乏一手数据支撑",         "fix":"补充用户访谈或行为数据"},
    {"id":"H6",  "name":"竞品对比不可比",       "severity":"medium", "nodes":["porter","swot","moat"],         "trigger":"竞品对比维度不对等或遗漏关键竞品", "fix":"按统一维度重构竞品对比矩阵"},
    {"id":"H7",  "name":"创新点不可验证",       "severity":"medium", "nodes":["moat","abtest","mvp"],          "trigger":"创新点缺乏数据或实验支撑",         "fix":"设计验证实验或提供对比数据"},
    {"id":"H8",  "name":"单位经济不成立",       "severity":"high",   "nodes":["ltv","cac","bep","bmc"],        "trigger":"LTV < CAC 或单位经济模型假设不合理","fix":"重新计算单位经济，调整定价或降低获客成本"},
    {"id":"H9",  "name":"增长逻辑跳跃",         "severity":"medium", "nodes":["aarrr","cac","mrr"],            "trigger":"用户增长策略缺乏阶段性逻辑",       "fix":"拆解增长为种子期、扩展期、规模期"},
    {"id":"H10", "name":"里程碑不可交付",       "severity":"medium", "nodes":["mvp","abtest","bizplan"],       "trigger":"里程碑设置过于模糊或不可量化",     "fix":"定义 SMART 指标的具体交付物"},
    {"id":"H11", "name":"合规/伦理缺口",        "severity":"high",   "nodes":["bmc","tam","bizplan"],          "trigger":"项目涉及数据隐私、行业准入等合规风险","fix":"补充合规分析和伦理风险评估"},
    {"id":"H12", "name":"技术路线与资源不匹配", "severity":"high",   "nodes":["mvp","moat","bizplan"],         "trigger":"技术方案超出团队现有能力和资源",   "fix":"调整技术方案或补充资源获取计划"},
    {"id":"H13", "name":"实验设计不合格",       "severity":"medium", "nodes":["abtest","mvp","interview"],     "trigger":"验证实验缺乏对照组或样本量不足",   "fix":"重新设计实验方案"},
    {"id":"H14", "name":"路演叙事断裂",         "severity":"low",    "nodes":["pitch","vp","tam","bmc"],       "trigger":"路演材料的故事线不连贯",           "fix":"按 问题→方案→市场→模式→团队 重构叙事"},
    {"id":"H15", "name":"评分项证据覆盖不足",   "severity":"medium", "nodes":["interview","pitch","bizplan","bmc"],"trigger":"多个评分维度缺乏支撑证据",     "fix":"针对缺失项逐一补充证据材料"},
]


def sync_knowledge_graph() -> bool:
    """
    Sync the full knowledge graph (nodes + edges + hyperedges) to Neo4j.
    Returns True if successful, False if Neo4j unavailable.
    """
    driver = _get_driver()
    if not driver:
        return False

    try:
        with driver.session() as session:
            # Clear existing KG data
            session.run("MATCH (n:KGNode) DETACH DELETE n")
            session.run("MATCH (h:HyperEdge) DETACH DELETE h")

            # Create concept nodes
            for node in _KG_NODES:
                session.run(
                    """
                    MERGE (n:KGNode {id: $id})
                    SET n.label = $label, n.labelEn = $labelEn, n.type = $type
                    """,
                    **node,
                )

            # Create edges
            for src, tgt, rel_type in _KG_EDGES:
                session.run(
                    f"""
                    MATCH (a:KGNode {{id: $src}}), (b:KGNode {{id: $tgt}})
                    MERGE (a)-[:{rel_type}]->(b)
                    """,
                    src=src, tgt=tgt,
                )

            # Create hyperedge nodes + CONSTRAINS relationships
            for he in _HYPEREDGES:
                session.run(
                    """
                    MERGE (h:HyperEdge {id: $id})
                    SET h.name = $name, h.severity = $severity,
                        h.trigger = $trigger, h.fix = $fix
                    """,
                    id=he["id"], name=he["name"], severity=he["severity"],
                    trigger=he["trigger"], fix=he["fix"],
                )
                for node_id in he["nodes"]:
                    session.run(
                        """
                        MATCH (h:HyperEdge {id: $hid}), (n:KGNode {id: $nid})
                        MERGE (h)-[:CONSTRAINS]->(n)
                        """,
                        hid=he["id"], nid=node_id,
                    )

        logger.info("Knowledge graph synced to Neo4j successfully.")
        return True

    except Exception as e:
        logger.error(f"Failed to sync knowledge graph to Neo4j: {e}")
        return False


def find_path(from_id: str, to_id: str) -> list[dict]:
    """
    Find shortest path between two concept nodes.
    Returns list of nodes along the path.
    """
    driver = _get_driver()
    if not driver:
        return _fallback_find_path(from_id, to_id)

    try:
        with driver.session() as session:
            result = session.run(
                """
                MATCH path = shortestPath(
                    (a:KGNode {id: $from_id})-[*..6]-(b:KGNode {id: $to_id})
                )
                RETURN [n in nodes(path) | {id: n.id, label: n.label, type: n.type}] AS nodes,
                       length(path) AS length
                """,
                from_id=from_id, to_id=to_id,
            )
            record = result.single()
            if record:
                return record["nodes"]
            return []
    except Exception as e:
        logger.warning(f"Neo4j path query failed: {e}")
        return []


def get_related_hyperedges(node_id: str) -> list[dict]:
    """
    Get all hyperedge rules that involve a given concept node.
    Falls back to in-memory data if Neo4j unavailable.
    """
    driver = _get_driver()
    if not driver:
        return _fallback_get_related_hyperedges(node_id)

    try:
        with driver.session() as session:
            result = session.run(
                """
                MATCH (h:HyperEdge)-[:CONSTRAINS]->(n:KGNode {id: $node_id})
                RETURN h.id AS id, h.name AS name, h.severity AS severity,
                       h.trigger AS trigger, h.fix AS fix
                """,
                node_id=node_id,
            )
            return [dict(r) for r in result]
    except Exception as e:
        logger.warning(f"Neo4j hyperedge query failed: {e}")
        return _fallback_get_related_hyperedges(node_id)


def get_prerequisites(node_id: str) -> list[dict]:
    """Get all prerequisite concepts for a given node (follow PREREQ edges)."""
    driver = _get_driver()
    if not driver:
        return _fallback_get_prerequisites(node_id)

    try:
        with driver.session() as session:
            result = session.run(
                """
                MATCH (n:KGNode {id: $node_id})<-[:PREREQ*1..3]-(prereq:KGNode)
                RETURN DISTINCT prereq.id AS id, prereq.label AS label, prereq.type AS type
                """,
                node_id=node_id,
            )
            return [dict(r) for r in result]
    except Exception as e:
        logger.warning(f"Neo4j prerequisites query failed: {e}")
        return []


def query_cypher(cypher: str, params: dict | None = None) -> list[dict]:
    """
    Execute a raw Cypher query. For advanced use cases.
    Returns list of record dicts.
    """
    driver = _get_driver()
    if not driver:
        return []
    try:
        with driver.session() as session:
            result = session.run(cypher, **(params or {}))
            return [dict(r) for r in result]
    except Exception as e:
        logger.error(f"Cypher query failed: {e}")
        return []


# ── In-memory fallbacks ───────────────────────────────────────

def _fallback_get_related_hyperedges(node_id: str) -> list[dict]:
    return [
        {"id": he["id"], "name": he["name"], "severity": he["severity"],
         "trigger": he["trigger"], "fix": he["fix"]}
        for he in _HYPEREDGES
        if node_id in he["nodes"]
    ]


def _fallback_get_prerequisites(node_id: str) -> list[dict]:
    prereq_ids = {src for src, tgt, rel in _KG_EDGES if tgt == node_id and rel == "PREREQ"}
    return [
        {"id": n["id"], "label": n["label"], "type": n["type"]}
        for n in _KG_NODES if n["id"] in prereq_ids
    ]


def _fallback_find_path(from_id: str, to_id: str) -> list[dict]:
    """Simple BFS over in-memory edges."""
    adj: dict[str, list[str]] = {}
    for src, tgt, _ in _KG_EDGES:
        adj.setdefault(src, []).append(tgt)
        adj.setdefault(tgt, []).append(src)

    from collections import deque
    queue: deque = deque([[from_id]])
    visited = {from_id}
    while queue:
        path = queue.popleft()
        node = path[-1]
        if node == to_id:
            node_map = {n["id"]: n for n in _KG_NODES}
            return [{"id": nid, "label": node_map.get(nid, {}).get("label", nid),
                     "type": node_map.get(nid, {}).get("type", "")} for nid in path]
        for neighbor in adj.get(node, []):
            if neighbor not in visited:
                visited.add(neighbor)
                queue.append(path + [neighbor])
    return []
