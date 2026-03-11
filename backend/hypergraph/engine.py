"""
hypergraph/engine.py
────────────────────────────────────────────────────────────────
真正的超图引擎 — 基于 HyperNetX 构建，从竞赛案例数据加载

核心能力：
1. 加载 hypergraph_data.json（196节点 + 205超边，源自82个真实竞赛项目）
2. 超图遍历：给定节点，找到所有关联超边及其包含的其他节点
3. 相似项目检索：根据技术/行业/风险模式找到相关案例
4. 风险模式匹配：识别学生项目与已知风险超边的重合
5. 概念路径发现：在概念节点之间找学习路径
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import NamedTuple

logger = logging.getLogger(__name__)

# ── Load hypergraph data ──────────────────────────────────────
_DATA_PATH = Path(__file__).parent.parent / "data" / "hypergraph_data.json"

_nodes: dict[str, dict] = {}       # node_id -> node_dict
_hyperedges: dict[str, dict] = {}  # he_id -> hyperedge_dict
_node_to_edges: dict[str, list[str]] = {}  # node_id -> [he_ids]


def _load_data():
    """Load hypergraph data from JSON file (called once at import)."""
    global _nodes, _hyperedges, _node_to_edges

    if not _DATA_PATH.exists():
        logger.warning(f"Hypergraph data not found: {_DATA_PATH}")
        return

    with open(_DATA_PATH, encoding="utf-8") as f:
        data = json.load(f)

    _nodes = {n["id"]: n for n in data["nodes"]}
    _hyperedges = {he["id"]: he for he in data["hyperedges"]}

    # Build inverted index: node -> hyperedges
    _node_to_edges = {}
    for he in data["hyperedges"]:
        for nid in he["nodes"]:
            _node_to_edges.setdefault(nid, []).append(he["id"])

    logger.info(
        f"Hypergraph loaded: {len(_nodes)} nodes, "
        f"{len(_hyperedges)} hyperedges"
    )


# Auto-load on import
_load_data()


# ── Data access ───────────────────────────────────────────────

def get_stats() -> dict:
    """Return hypergraph statistics."""
    type_counts = {}
    for n in _nodes.values():
        t = n["type"]
        type_counts[t] = type_counts.get(t, 0) + 1
    edge_type_counts = {}
    for he in _hyperedges.values():
        t = he["type"]
        edge_type_counts[t] = edge_type_counts.get(t, 0) + 1
    return {
        "total_nodes": len(_nodes),
        "total_hyperedges": len(_hyperedges),
        "node_types": type_counts,
        "edge_types": edge_type_counts,
    }


def get_node(node_id: str) -> dict | None:
    """Get a node by ID."""
    return _nodes.get(node_id)


def get_hyperedge(he_id: str) -> dict | None:
    """Get a hyperedge by ID."""
    return _hyperedges.get(he_id)


# ── Core traversal: find related hyperedges for a node ────────

def get_incident_edges(node_id: str) -> list[dict]:
    """Get all hyperedges that contain the given node."""
    edge_ids = _node_to_edges.get(node_id, [])
    return [_hyperedges[eid] for eid in edge_ids if eid in _hyperedges]


def get_neighbors(node_id: str) -> list[dict]:
    """Get all nodes that share at least one hyperedge with the given node."""
    neighbor_ids: set[str] = set()
    for he in get_incident_edges(node_id):
        for nid in he["nodes"]:
            if nid != node_id:
                neighbor_ids.add(nid)
    return [_nodes[nid] for nid in neighbor_ids if nid in _nodes]


# ── Search: find projects by technology keywords ──────────────

def search_by_technology(tech_keywords: list[str]) -> list[dict]:
    """
    Find projects that use technologies matching any of the given keywords.
    Returns list of {project_node, matching_techs, hyperedges}.
    """
    results = []
    for he in _hyperedges.values():
        if he["type"] != "Product_Market_Fit":
            continue
        he_techs = he["properties"].get("techs", [])
        matched = [t for t in he_techs
                   if any(kw.lower() in t.lower() for kw in tech_keywords)]
        if matched:
            # Find the project node in this hyperedge
            proj_nodes = [_nodes[nid] for nid in he["nodes"]
                         if nid in _nodes and _nodes[nid]["type"] == "Project"]
            if proj_nodes:
                results.append({
                    "project": proj_nodes[0],
                    "matching_techs": matched,
                    "hyperedge": he,
                })
    return results


def search_by_industry(industry: str) -> list[dict]:
    """Find all projects in a given industry."""
    results = []
    for he in _hyperedges.values():
        if he["type"] == "Product_Market_Fit" and he["properties"].get("industry") == industry:
            proj_nodes = [_nodes[nid] for nid in he["nodes"]
                         if nid in _nodes and _nodes[nid]["type"] == "Project"]
            if proj_nodes:
                results.append({
                    "project": proj_nodes[0],
                    "hyperedge": he,
                })
    return results


# ── Risk pattern matching ─────────────────────────────────────

class RiskMatch(NamedTuple):
    risk_label: str
    severity: str
    related_projects: list[str]
    related_concepts: list[str]
    teaching_note: str


def find_risk_patterns(
    tech_keywords: list[str],
    industry: str = "",
    has_moat: bool = True,
    has_biz_model: bool = True,
) -> list[RiskMatch]:
    """
    Given a student's project characteristics, find matching risk patterns
    from the hypergraph case library.
    """
    matches: list[RiskMatch] = []
    seen_risks: set[str] = set()

    # Strategy 1: Find similar projects and their associated risks
    similar = search_by_technology(tech_keywords)
    if industry:
        similar += search_by_industry(industry)

    similar_proj_ids = {r["project"]["id"] for r in similar}

    for he in _hyperedges.values():
        if he["type"] != "Risk_Pattern":
            continue
        # Check if this risk edge connects to any similar project
        he_proj_ids = {nid for nid in he["nodes"] if nid in similar_proj_ids}
        if not he_proj_ids:
            continue

        risk_id = next(
            (nid for nid in he["nodes"] if nid in _nodes and _nodes[nid]["type"] == "RiskPattern"),
            None,
        )
        if not risk_id or risk_id in seen_risks:
            continue
        seen_risks.add(risk_id)

        risk_node = _nodes[risk_id]
        concept_labels = [
            _nodes[nid]["label"]
            for nid in he["nodes"]
            if nid in _nodes and _nodes[nid]["type"] == "Concept"
        ]
        proj_labels = [
            _nodes[nid]["label"]
            for nid in he_proj_ids
            if nid in _nodes
        ]

        matches.append(RiskMatch(
            risk_label=risk_node["label"],
            severity=risk_node["properties"].get("severity", "medium"),
            related_projects=proj_labels[:3],
            related_concepts=concept_labels,
            teaching_note=he["properties"].get("teaching_note", ""),
        ))

    # Strategy 2: Direct risk triggers based on student's project gaps
    if not has_moat and "risk_no_moat" not in seen_risks:
        node = _nodes.get("risk_no_moat")
        if node:
            matches.append(RiskMatch(
                risk_label=node["label"],
                severity="high",
                related_projects=[],
                related_concepts=["护城河", "SWOT分析"],
                teaching_note="未提及技术壁垒或差异化优势，超图中类似项目多因此失败。",
            ))

    if not has_biz_model and "risk_biz_unclear" not in seen_risks:
        node = _nodes.get("risk_biz_unclear")
        if node:
            matches.append(RiskMatch(
                risk_label=node["label"],
                severity="medium",
                related_projects=[],
                related_concepts=["精益画布", "定价策略", "盈亏平衡点"],
                teaching_note="盈利模式不清晰，建议先完成精益画布。",
            ))

    # Sort by severity
    _order = {"high": 0, "medium": 1, "low": 2}
    matches.sort(key=lambda m: _order.get(m.severity, 3))
    return matches


# ── Technology cluster analysis ───────────────────────────────

def get_tech_competition(tech_keyword: str) -> dict | None:
    """
    Find how many projects use a given technology.
    Returns cluster info for competitive analysis.
    """
    for he in _hyperedges.values():
        if he["type"] != "Technology_Cluster":
            continue
        tech_nid = next(
            (nid for nid in he["nodes"]
             if nid in _nodes and _nodes[nid]["type"] == "Technology"
             and tech_keyword.lower() in _nodes[nid]["label"].lower()),
            None,
        )
        if tech_nid:
            proj_labels = [
                _nodes[nid]["label"]
                for nid in he["nodes"]
                if nid in _nodes and _nodes[nid]["type"] == "Project"
            ]
            return {
                "technology": _nodes[tech_nid]["label"],
                "project_count": he["properties"].get("project_count", len(proj_labels)),
                "example_projects": proj_labels[:5],
                "teaching_note": he["properties"].get("teaching_note", ""),
            }
    return None


# ── Concept path discovery ────────────────────────────────────

def find_concept_path(from_concept: str, to_concept: str) -> list[dict] | None:
    """
    Find a learning path between two concepts via Concept_Prerequisite hyperedges.
    """
    # Find concept node IDs by label match
    from_id = _find_concept_id(from_concept)
    to_id = _find_concept_id(to_concept)
    if not from_id or not to_id:
        return None

    # BFS over hyperedges
    from collections import deque
    queue: deque = deque([[from_id]])
    visited = {from_id}

    while queue:
        path = queue.popleft()
        current = path[-1]
        if current == to_id:
            return [_nodes[nid] for nid in path if nid in _nodes]

        for he in get_incident_edges(current):
            if he["type"] != "Concept_Prerequisite":
                continue
            for nid in he["nodes"]:
                if nid not in visited and nid in _nodes and _nodes[nid]["type"] == "Concept":
                    visited.add(nid)
                    queue.append(path + [nid])

    return None


def _find_concept_id(label_or_keyword: str) -> str | None:
    """Find concept node ID by label or keyword."""
    kw = label_or_keyword.lower()
    for nid, node in _nodes.items():
        if node["type"] != "Concept":
            continue
        if kw in node["label"].lower() or kw in node.get("properties", {}).get("en", "").lower():
            return nid
    return None


# ── High-level query: "What does the hypergraph say about X?" ──

def query_hypergraph(
    tech_keywords: list[str] | None = None,
    industry: str = "",
    concept: str = "",
) -> dict:
    """
    High-level query interface for the Agent.
    Returns structured context that can be injected into LLM prompts.

    This is the main entry point for the RAG pipeline.
    """
    context = {
        "similar_projects": [],
        "detailed_cases": [],
        "risk_patterns": [],
        "tech_competition": [],
        "concept_info": [],
        "teaching_notes": [],
    }

    # 1. Find similar projects (prioritize detailed Case_Study hyperedges)
    if tech_keywords:
        similar = search_by_technology(tech_keywords)
        for s in similar[:5]:
            proj = s["project"]
            context["similar_projects"].append({
                "name": proj["label"],
                "industry": proj["properties"].get("industry", ""),
                "techs": s["matching_techs"],
                "has_moat": s["hyperedge"]["properties"].get("has_moat", False),
                "has_biz_model": s["hyperedge"]["properties"].get("has_biz_model", False),
            })
            note = s["hyperedge"]["properties"].get("teaching_note", "")
            if note:
                context["teaching_notes"].append(note)

    # 1b. Find detailed Case_Study hyperedges (enriched with problem/solution/risks)
    if tech_keywords or industry:
        for he in _hyperedges.values():
            if he["type"] != "Case_Study" or not he["properties"].get("is_detailed"):
                continue
            props = he["properties"]
            # Match by industry
            industry_match = industry and props.get("industry") == industry
            # Match by tech
            case_techs = [_nodes[nid]["label"] for nid in he["nodes"]
                         if nid in _nodes and _nodes[nid]["type"] == "Technology"]
            tech_match = any(
                kw.lower() in t.lower()
                for t in case_techs
                for kw in (tech_keywords or [])
            )
            if industry_match or tech_match:
                context["detailed_cases"].append({
                    "name": props["project"],
                    "industry": props["industry"],
                    "problem": props.get("problem", "")[:150],
                    "solution": props.get("solution", "")[:150],
                    "market_size": props.get("market_size", ""),
                    "biz_models": props.get("biz_models", []),
                    "moat": props.get("moat", []),
                    "success_factors": props.get("success_factors", []),
                    "failure_risks": props.get("failure_risks", []),
                })
                if len(context["detailed_cases"]) >= 3:
                    break

    # 2. Find risk patterns
    if tech_keywords or industry:
        risks = find_risk_patterns(
            tech_keywords or [],
            industry=industry,
        )
        for r in risks[:5]:
            context["risk_patterns"].append({
                "risk": r.risk_label,
                "severity": r.severity,
                "related_projects": r.related_projects,
                "related_concepts": r.related_concepts,
                "note": r.teaching_note,
            })

    # 3. Tech competition landscape
    if tech_keywords:
        for kw in tech_keywords[:3]:
            cluster = get_tech_competition(kw)
            if cluster:
                context["tech_competition"].append(cluster)

    # 4. Concept info
    if concept:
        cid = _find_concept_id(concept)
        if cid:
            node = _nodes[cid]
            neighbors = get_neighbors(cid)
            concept_neighbors = [n for n in neighbors if n["type"] == "Concept"]
            context["concept_info"].append({
                "concept": node["label"],
                "related_concepts": [n["label"] for n in concept_neighbors[:5]],
            })

    # 5. Business strategies from matching projects
    if tech_keywords or industry:
        biz_strategies = []
        for he in _hyperedges.values():
            if he["type"] != "Business_Strategy":
                continue
            props = he["properties"]
            proj_name = props.get("project", "")
            # Check if this project matches our search
            matched = False
            if industry and any(
                nid in _nodes and _nodes[nid].get("properties", {}).get("industry") == industry
                for nid in he["nodes"]
            ):
                matched = True
            if tech_keywords and not matched:
                for nid in he["nodes"]:
                    if nid in _nodes and _nodes[nid]["type"] in ("Technology", "SubTechnology"):
                        if any(kw.lower() in _nodes[nid]["label"].lower() for kw in tech_keywords):
                            matched = True
                            break
            if matched:
                biz_strategies.append({
                    "project": proj_name,
                    "biz_models": props.get("biz_models", []),
                    "moat_types": props.get("moat_types", []),
                })
        context["business_strategies"] = biz_strategies[:5]

    # 6. Application domains
    if tech_keywords:
        app_domains = []
        for he in _hyperedges.values():
            if he["type"] != "Application_Domain_Map":
                continue
            props = he["properties"]
            domain_projects = [nid for nid in he["nodes"] if nid in _nodes and _nodes[nid]["type"] == "Project"]
            for nid in he["nodes"]:
                if nid in _nodes and _nodes[nid]["type"] == "ApplicationDomain":
                    app_domains.append({
                        "domain": _nodes[nid]["label"],
                        "project_count": props.get("project_count", 0),
                    })
        context["application_domains"] = app_domains[:5]

    return context


# ── Ingestion: add new nodes/edges and persist ───────────────

def add_project_to_hypergraph(
    project_name: str,
    industry: str,
    technologies: list[str],
    problem: str = "",
    solution: str = "",
    market_size: str = "",
    biz_models: list[str] | None = None,
    moat: list[str] | None = None,
    source: str = "user_upload",
) -> dict:
    """
    Add a new project and its relationships to the hypergraph.
    Returns the created project node and hyperedge IDs.
    """
    import hashlib

    pid = "proj_" + hashlib.md5(project_name.encode()).hexdigest()[:8]

    # 1. Create project node
    proj_node = {
        "id": pid,
        "type": "Project",
        "label": project_name,
        "properties": {
            "industry": industry,
            "source": source,
            "technologies": technologies,
            "biz_model": biz_models or [],
            "moat": moat or [],
            "problem": problem[:200],
            "solution": solution[:200],
            "market_size": market_size,
            "is_detailed_case": bool(problem and solution),
        },
    }
    _nodes[pid] = proj_node

    created_edges = []

    # 2. Create/find technology nodes and link
    tech_node_ids = []
    for tech in technologies:
        tech_id = "tech_" + tech.lower().replace(" ", "_")
        if tech_id not in _nodes:
            _nodes[tech_id] = {
                "id": tech_id,
                "type": "Technology",
                "label": tech,
                "properties": {},
            }
        tech_node_ids.append(tech_id)

    # 3. Create/find market node
    market_id = ""
    if industry:
        market_id = "market_" + industry
        if market_id not in _nodes:
            _nodes[market_id] = {
                "id": market_id,
                "type": "Market",
                "label": industry,
                "properties": {},
            }

    # 4. Create PMF hyperedge
    pmf_nodes = [pid] + tech_node_ids
    if market_id:
        pmf_nodes.append(market_id)
    pmf_he_id = f"he_pmf_{pid}"
    pmf_he = {
        "id": pmf_he_id,
        "type": "Product_Market_Fit",
        "nodes": pmf_nodes,
        "properties": {
            "project": project_name,
            "industry": industry,
            "techs": technologies,
            "has_moat": bool(moat),
            "has_biz_model": bool(biz_models),
            "teaching_note": "",
        },
    }
    _hyperedges[pmf_he_id] = pmf_he
    created_edges.append(pmf_he_id)

    # 5. Update inverted index
    for nid in pmf_he["nodes"]:
        _node_to_edges.setdefault(nid, []).append(pmf_he_id)

    # 6. If detailed, create Case_Study hyperedge
    if problem and solution:
        cs_he_id = f"he_case_{pid}"
        cs_he = {
            "id": cs_he_id,
            "type": "Case_Study",
            "nodes": [pid] + tech_node_ids[:3],
            "properties": {
                "is_detailed": True,
                "project": project_name,
                "industry": industry,
                "problem": problem[:300],
                "solution": solution[:300],
                "market_size": market_size,
                "biz_models": biz_models or [],
                "moat": moat or [],
                "success_factors": [],
                "failure_risks": [],
            },
        }
        _hyperedges[cs_he_id] = cs_he
        created_edges.append(cs_he_id)
        for nid in cs_he["nodes"]:
            _node_to_edges.setdefault(nid, []).append(cs_he_id)

    # 7. Persist to disk
    _save_data()

    logger.info(f"Added project '{project_name}' to hypergraph: 1 node, {len(created_edges)} edges")
    return {
        "project_id": pid,
        "project_name": project_name,
        "created_edges": created_edges,
        "total_nodes": len(_nodes),
        "total_hyperedges": len(_hyperedges),
    }


def _save_data():
    """Persist current hypergraph state to JSON file."""
    data = {
        "nodes": list(_nodes.values()),
        "hyperedges": list(_hyperedges.values()),
    }
    with open(_DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    logger.info(f"Hypergraph saved: {len(_nodes)} nodes, {len(_hyperedges)} hyperedges")


def format_context_for_prompt(ctx: dict) -> str:
    """
    Format query_hypergraph() output into a text block
    that can be injected into LLM system/user prompt.
    """
    parts = []

    if ctx["similar_projects"]:
        parts.append("【超图案例检索结果】")
        parts.append(f"找到 {len(ctx['similar_projects'])} 个相关竞赛项目：")
        for i, p in enumerate(ctx["similar_projects"][:5], 1):
            moat_str = "有壁垒" if p["has_moat"] else "⚠无明确壁垒"
            biz_str = "有商业模式" if p["has_biz_model"] else "⚠商业模式不清晰"
            parts.append(
                f"  {i}. {p['name']}（{p['industry']}）"
                f"— 技术：{','.join(p['techs'])} | {moat_str} | {biz_str}"
            )

    if ctx.get("detailed_cases"):
        parts.append("\n【超图核心案例深度分析】")
        for i, c in enumerate(ctx["detailed_cases"][:3], 1):
            parts.append(f"  案例{i}: {c['name']}（{c['industry']}）")
            if c["problem"]:
                parts.append(f"    痛点：{c['problem']}")
            if c["solution"]:
                parts.append(f"    方案：{c['solution']}")
            if c["market_size"]:
                parts.append(f"    市场规模：{c['market_size']}")
            if c["biz_models"]:
                parts.append(f"    商业模式：{', '.join(c['biz_models'])}")
            if c["moat"]:
                parts.append(f"    壁垒：{', '.join(c['moat'][:3])}")
            if c["success_factors"]:
                parts.append(f"    ✅ 成功要素：{'; '.join(c['success_factors'][:3])}")
            if c["failure_risks"]:
                parts.append(f"    ⚠ 风险警示：{'; '.join(c['failure_risks'][:3])}")

    if ctx["risk_patterns"]:
        parts.append("\n【超图风险模式匹配】")
        severity_emoji = {"high": "🔴", "medium": "🟡", "low": "🔵"}
        for r in ctx["risk_patterns"][:5]:
            emoji = severity_emoji.get(r["severity"], "⚪")
            parts.append(f"  {emoji} {r['risk']}（{r['severity']}）")
            if r["related_projects"]:
                parts.append(f"     历史案例：{', '.join(r['related_projects'][:3])}")
            if r["related_concepts"]:
                parts.append(f"     建议学习：{', '.join(r['related_concepts'])}")

    if ctx["tech_competition"]:
        parts.append("\n【超图技术竞争态势】")
        for tc in ctx["tech_competition"][:3]:
            parts.append(
                f"  '{tc['technology']}' 已有 {tc['project_count']} 个项目采用"
            )
            if tc["example_projects"]:
                parts.append(f"     代表项目：{', '.join(tc['example_projects'][:3])}")
            parts.append(f"     ⚡ {tc['teaching_note']}")

    if ctx["concept_info"]:
        parts.append("\n【超图概念关联】")
        for c in ctx["concept_info"]:
            parts.append(
                f"  概念 '{c['concept']}' 关联概念：{', '.join(c['related_concepts'])}"
            )

    if ctx.get("business_strategies"):
        parts.append("\n【超图商业策略分析】")
        for bs in ctx["business_strategies"][:5]:
            biz = "、".join(bs["biz_models"][:3]) if bs["biz_models"] else "未明确"
            moat = "、".join(bs["moat_types"][:3]) if bs["moat_types"] else "未明确"
            parts.append(f"  {bs['project']}：商业模式={biz}，壁垒={moat}")

    if ctx.get("application_domains"):
        parts.append("\n【超图应用领域】")
        for ad in ctx["application_domains"][:5]:
            parts.append(f"  {ad['domain']}（{ad['project_count']}个项目）")

    return "\n".join(parts) if parts else ""
