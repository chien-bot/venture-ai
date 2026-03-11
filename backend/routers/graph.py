"""
routers/graph.py
────────────────────────────────────────────────────────────────
Knowledge Graph API endpoints backed by Neo4j (with in-memory fallback)

Endpoints:
  GET /api/graph/status          — Is Neo4j connected?
  POST /api/graph/sync           — Sync KG data to Neo4j
  GET /api/graph/path            — Shortest path between two nodes
  GET /api/graph/node/{id}/rules — Hyperedge rules for a node
  GET /api/graph/node/{id}/prereqs — Prerequisites for a node
  POST /api/graph/cypher         — Raw Cypher query (teacher-only)
"""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from graph_db.neo4j_client import (
    is_available, sync_knowledge_graph,
    find_path, get_related_hyperedges, get_prerequisites,
    query_cypher,
)
from hypergraph.engine import (
    get_stats as hg_stats,
    query_hypergraph,
    format_context_for_prompt,
    search_by_technology,
    search_by_industry,
    find_risk_patterns,
    get_tech_competition,
)

router = APIRouter(prefix="/api/graph", tags=["graph"])


@router.get("/status")
def graph_status():
    available = is_available()
    stats = hg_stats()
    return {
        "neo4j_available": available,
        "message": "Neo4j 已连接" if available else "Neo4j 未配置，使用内存回退模式",
        "hypergraph": stats,
    }


# ── Hypergraph query endpoints ────────────────────────────────

@router.get("/hypergraph/query")
def hypergraph_query(
    tech: str = Query("", description="技术关键词，逗号分隔"),
    industry: str = Query("", description="行业"),
    concept: str = Query("", description="概念"),
):
    """Query the hypergraph for related cases, risks, and competition."""
    tech_list = [t.strip() for t in tech.split(",") if t.strip()] if tech else None
    ctx = query_hypergraph(tech_keywords=tech_list, industry=industry, concept=concept)
    return {
        "context": ctx,
        "formatted": format_context_for_prompt(ctx),
    }


@router.get("/hypergraph/tech-competition")
def tech_competition(tech: str):
    """Check how many projects use a given technology."""
    result = get_tech_competition(tech)
    return result or {"message": f"未找到使用 '{tech}' 的项目集群"}


@router.get("/hypergraph/risks")
def risk_check(
    tech: str = Query("", description="技术关键词，逗号分隔"),
    industry: str = Query("", description="行业"),
):
    """Find risk patterns matching given tech/industry."""
    tech_list = [t.strip() for t in tech.split(",") if t.strip()] if tech else []
    risks = find_risk_patterns(tech_list, industry=industry)
    return {
        "risks": [r._asdict() for r in risks],
        "count": len(risks),
    }


@router.get("/hypergraph/visualization")
def hypergraph_visualization(
    limit: int = Query(200, description="最大节点数"),
    node_types: str = Query("", description="逗号分隔的节点类型过滤，如 Project,Technology,SubTechnology"),
):
    """Return hypergraph data for frontend D3/vis.js visualization."""
    from hypergraph.engine import _nodes, _hyperedges

    # Parse node type filter
    allowed_types = set()
    if node_types:
        allowed_types = {t.strip() for t in node_types.split(",") if t.strip()}

    # Default: show core types (skip Keyword nodes which are too numerous)
    if not allowed_types:
        allowed_types = {
            "Project", "Technology", "SubTechnology", "Market", "Concept",
            "RiskPattern", "BusinessModel", "MoatType", "ApplicationDomain",
            "Framework", "SolutionApproach",
        }

    vis_nodes = []
    vis_edges = []
    included_ids = set()
    type_counts: dict[str, int] = {}

    # Add nodes by type, with per-type limits
    for nid, node in _nodes.items():
        ntype = node["type"]
        if ntype not in allowed_types:
            continue
        type_counts[ntype] = type_counts.get(ntype, 0) + 1
        if type_counts[ntype] > limit:
            continue
        vis_node = {
            "id": nid,
            "label": node["label"],
            "type": ntype,
            "group": ntype,
        }
        if ntype == "Project":
            vis_node["industry"] = node.get("properties", {}).get("industry", "")
        vis_nodes.append(vis_node)
        included_ids.add(nid)

    # Build hyperedges for visualization
    for he_id, he in _hyperedges.items():
        he_node_ids = [nid for nid in he["nodes"] if nid in included_ids]
        if len(he_node_ids) >= 2:
            vis_edges.append({
                "id": he_id,
                "type": he["type"],
                "nodes": he_node_ids,
                "teaching_note": he["properties"].get("teaching_note", ""),
            })

    return {
        "nodes": vis_nodes,
        "hyperedges": vis_edges,
        "stats": hg_stats(),
    }


@router.get("/hypergraph/insights")
def hypergraph_insights():
    """
    Teacher-facing: aggregated insights from the hypergraph.
    Returns tech heatmap, industry distribution, common risks, etc.
    """
    from hypergraph.engine import _nodes, _hyperedges

    # 1. Technology heatmap: count how many projects use each tech
    tech_counts: dict[str, int] = {}
    for nid, node in _nodes.items():
        if node["type"] == "Project":
            for tech in node.get("properties", {}).get("technologies", []):
                tech_counts[tech] = tech_counts.get(tech, 0) + 1
    tech_heatmap = sorted(
        [{"tech": t, "count": c} for t, c in tech_counts.items()],
        key=lambda x: -x["count"],
    )[:15]

    # 2. Industry distribution
    industry_counts: dict[str, int] = {}
    for nid, node in _nodes.items():
        if node["type"] == "Project":
            ind = node.get("properties", {}).get("industry", "其他")
            industry_counts[ind] = industry_counts.get(ind, 0) + 1
    industry_dist = sorted(
        [{"industry": k, "count": v} for k, v in industry_counts.items()],
        key=lambda x: -x["count"],
    )

    # 3. Risk pattern frequency
    risk_counts: dict[str, dict] = {}
    for he in _hyperedges.values():
        if he["type"] == "Risk_Pattern":
            risk_nodes = [
                _nodes[nid] for nid in he["nodes"]
                if nid in _nodes and _nodes[nid]["type"] == "RiskPattern"
            ]
            proj_count = len([
                nid for nid in he["nodes"]
                if nid in _nodes and _nodes[nid]["type"] == "Project"
            ])
            for rn in risk_nodes:
                rid = rn["id"]
                if rid not in risk_counts:
                    risk_counts[rid] = {
                        "risk": rn["label"],
                        "severity": rn.get("properties", {}).get("severity", "medium"),
                        "affected_projects": 0,
                    }
                risk_counts[rid]["affected_projects"] += proj_count
    risk_freq = sorted(risk_counts.values(), key=lambda x: -x["affected_projects"])

    # 4. Moat coverage: how many projects have clear moat
    total_proj = sum(1 for n in _nodes.values() if n["type"] == "Project")
    has_moat = sum(
        1 for he in _hyperedges.values()
        if he["type"] == "Product_Market_Fit" and he.get("properties", {}).get("has_moat")
    )
    has_biz = sum(
        1 for he in _hyperedges.values()
        if he["type"] == "Product_Market_Fit" and he.get("properties", {}).get("has_biz_model")
    )

    # 5. Teaching interventions based on gaps
    interventions = []
    if total_proj > 0:
        moat_pct = has_moat / total_proj * 100
        biz_pct = has_biz / total_proj * 100
        if moat_pct < 50:
            interventions.append(f"仅 {moat_pct:.0f}% 的项目有明确护城河，建议安排竞争壁垒专题")
        if biz_pct < 60:
            interventions.append(f"仅 {biz_pct:.0f}% 的项目有清晰商业模式，建议加强精益画布训练")
        if tech_heatmap and tech_heatmap[0]["count"] > total_proj * 0.3:
            interventions.append(
                f"技术同质化严重：{tech_heatmap[0]['tech']} 被 {tech_heatmap[0]['count']}/{total_proj} "
                f"个项目使用，建议引导差异化技术路线"
            )

    return {
        "tech_heatmap": tech_heatmap,
        "industry_distribution": industry_dist,
        "risk_frequency": risk_freq,
        "coverage": {
            "total_projects": total_proj,
            "has_moat": has_moat,
            "has_biz_model": has_biz,
            "moat_pct": round(has_moat / max(total_proj, 1) * 100, 1),
            "biz_pct": round(has_biz / max(total_proj, 1) * 100, 1),
        },
        "interventions": interventions,
    }


@router.post("/sync")
def sync_graph():
    """Push all KG nodes, edges, and hyperedges to Neo4j."""
    success = sync_knowledge_graph()
    if success:
        return {"status": "ok", "message": "知识图谱已同步到 Neo4j"}
    return {"status": "fallback", "message": "Neo4j 未配置，数据保留在内存中"}


@router.get("/path")
def get_path(from_id: str, to_id: str):
    """Get shortest path between two concept nodes."""
    path = find_path(from_id, to_id)
    return {"from_id": from_id, "to_id": to_id, "path": path, "length": len(path) - 1 if path else -1}


@router.get("/node/{node_id}/rules")
def get_node_rules(node_id: str):
    """Get all hyperedge constraint rules involving this node."""
    rules = get_related_hyperedges(node_id)
    return {"node_id": node_id, "rules": rules, "count": len(rules)}


@router.get("/node/{node_id}/prereqs")
def get_node_prereqs(node_id: str):
    """Get prerequisite concepts for this node."""
    prereqs = get_prerequisites(node_id)
    return {"node_id": node_id, "prerequisites": prereqs}


class CypherQuery(BaseModel):
    cypher: str
    params: dict = {}


@router.post("/cypher")
def run_cypher(query: CypherQuery):
    """Execute a raw Cypher query (for teacher/admin use)."""
    if not is_available():
        raise HTTPException(status_code=503, detail="Neo4j 未连接")
    # Safety: only allow read queries
    stmt = query.cypher.strip().upper()
    if any(stmt.startswith(kw) for kw in ("CREATE", "MERGE", "DELETE", "DROP", "SET", "REMOVE")):
        raise HTTPException(status_code=403, detail="只允许 MATCH/RETURN 查询")
    results = query_cypher(query.cypher, query.params)
    return {"results": results, "count": len(results)}
