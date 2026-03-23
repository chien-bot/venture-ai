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


# ── Multi-hop traversal ───────────────────────────────────────

def traverse_multi_hop(
    start_node_ids: list[str],
    max_hops: int = 2,
    edge_type_filter: list[str] | None = None,
    node_type_filter: list[str] | None = None,
) -> list[dict]:
    """
    从给定节点出发，做 N 跳超图遍历，收集路径上的所有节点和超边。

    与 get_neighbors() 的区别：
    - get_neighbors 只看 1 跳
    - 这里做 BFS 多跳，记录完整路径（node → edge → node → edge → ...）
    - 可以按超边类型和节点类型过滤，避免爆炸

    Parameters
    ----------
    start_node_ids : 起始节点 ID 列表
    max_hops : 最大跳数（每经过一条超边算一跳）
    edge_type_filter : 只遍历这些类型的超边（None = 不限）
    node_type_filter : 只收集这些类型的节点（None = 不限）

    Returns
    -------
    [{hop, node, via_edge, via_edge_type, path}] 按 hop 排序
    """
    from collections import deque

    results = []
    visited_nodes: set[str] = set(start_node_ids)
    # queue item: (node_id, hop_count, path)
    queue: deque = deque()
    for nid in start_node_ids:
        queue.append((nid, 0, [nid]))

    while queue:
        current_id, hop, path = queue.popleft()
        if hop >= max_hops:
            continue

        for he in get_incident_edges(current_id):
            # 超边类型过滤
            if edge_type_filter and he["type"] not in edge_type_filter:
                continue

            for neighbor_id in he["nodes"]:
                if neighbor_id in visited_nodes or neighbor_id not in _nodes:
                    continue

                neighbor = _nodes[neighbor_id]
                # 节点类型过滤
                if node_type_filter and neighbor["type"] not in node_type_filter:
                    continue

                visited_nodes.add(neighbor_id)
                new_path = path + [he["id"], neighbor_id]

                results.append({
                    "hop": hop + 1,
                    "node": neighbor,
                    "via_edge": he,
                    "via_edge_type": he["type"],
                    "path": new_path,
                })

                queue.append((neighbor_id, hop + 1, new_path))

    return results


def build_reasoning_chain(
    project_ids: list[str],
    max_hops: int = 2,
) -> dict:
    """
    构建完整的多跳推理链：

    项目 →(1跳) 风险模式 →(2跳) 修复概念 →(2跳) 前置概念
    项目 →(1跳) 技术 →(2跳) 同技术竞品项目
    项目 →(1跳) 痛点 →(2跳) 类似痛点的其他项目

    返回结构化的推理结果，供 coach prompt 使用。
    """
    chains = {
        "risk_to_concept_chains": [],   # 项目→风险→需学概念→前置概念
        "tech_competition_chains": [],  # 项目→技术→同技术竞品
        "pain_similarity_chains": [],   # 项目→痛点→类似痛点项目
        "concept_learning_paths": [],   # 概念→前置概念学习路径
    }

    # ── Chain 1: 项目 → Risk_Pattern → Concept → Concept_Prerequisite ──
    # 第一跳：找风险模式
    risk_hops = traverse_multi_hop(
        project_ids,
        max_hops=1,
        edge_type_filter=["Risk_Pattern"],
        node_type_filter=["RiskPattern", "Concept"],
    )

    risk_concepts: set[str] = set()
    risk_map: dict[str, list[str]] = {}  # risk_label → [concept_labels]

    for item in risk_hops:
        node = item["node"]
        if node["type"] == "RiskPattern":
            risk_label = node["label"]
            risk_map.setdefault(risk_label, [])
        elif node["type"] == "Concept":
            # 找这个 concept 关联的 risk
            via_edge = item["via_edge"]
            risk_in_edge = [
                _nodes[nid]["label"]
                for nid in via_edge["nodes"]
                if nid in _nodes and _nodes[nid]["type"] == "RiskPattern"
            ]
            for rl in risk_in_edge:
                risk_map.setdefault(rl, []).append(node["label"])
            risk_concepts.add(node["id"])

    # 第二跳：从 risk 关联的 concept 出发，找前置概念
    if risk_concepts:
        prereq_hops = traverse_multi_hop(
            list(risk_concepts),
            max_hops=1,
            edge_type_filter=["Concept_Prerequisite"],
            node_type_filter=["Concept"],
        )
        prereq_map: dict[str, list[str]] = {}  # concept → [prerequisite concepts]
        for item in prereq_hops:
            # 找到是从哪个概念出发的
            path = item["path"]
            start_concept_id = path[0]
            if start_concept_id in _nodes:
                start_label = _nodes[start_concept_id]["label"]
                prereq_map.setdefault(start_label, []).append(item["node"]["label"])

        for risk_label, concepts in risk_map.items():
            if not concepts:
                continue
            chain_entry = {
                "risk": risk_label,
                "fix_concepts": concepts,
                "prerequisites": {},
            }
            for c in concepts:
                if c in prereq_map:
                    chain_entry["prerequisites"][c] = prereq_map[c]
            chains["risk_to_concept_chains"].append(chain_entry)

    # ── Chain 2: 项目 → Technology_Cluster → 同技术竞品 ──
    tech_hops = traverse_multi_hop(
        project_ids,
        max_hops=2,
        edge_type_filter=["Technology_Cluster", "Product_Market_Fit"],
        node_type_filter=["Technology", "SubTechnology", "Project"],
    )

    seen_competitors: set[str] = set(project_ids)
    for item in tech_hops:
        node = item["node"]
        if node["type"] == "Project" and node["id"] not in seen_competitors:
            seen_competitors.add(node["id"])
            chains["tech_competition_chains"].append({
                "competitor": node["label"],
                "industry": node.get("properties", {}).get("industry", ""),
                "hop": item["hop"],
                "via_tech": item["via_edge"].get("properties", {}).get("techs", [])[:3],
            })

    # 去重，最多 5 个
    chains["tech_competition_chains"] = chains["tech_competition_chains"][:5]

    # ── Chain 3: 项目 → Pain_Solution_Fit → 类似痛点项目 ──
    pain_hops = traverse_multi_hop(
        project_ids,
        max_hops=2,
        edge_type_filter=["Pain_Solution_Fit"],
        node_type_filter=["PainPoint", "SolutionApproach", "Project"],
    )

    seen_pain_projects: set[str] = set(project_ids)
    for item in pain_hops:
        node = item["node"]
        if node["type"] == "Project" and node["id"] not in seen_pain_projects:
            seen_pain_projects.add(node["id"])
            # 找到是通过什么痛点连接的
            via_edge = item["via_edge"]
            shared_pains = via_edge.get("properties", {}).get("pain_points", [])[:3]
            chains["pain_similarity_chains"].append({
                "project": node["label"],
                "shared_pain_points": shared_pains,
                "hop": item["hop"],
            })

    chains["pain_similarity_chains"] = chains["pain_similarity_chains"][:5]

    return chains


def get_concept_prerequisites(concept_name: str, max_depth: int = 2) -> dict:
    """
    给定一个概念名，返回它的直接前置依赖（限制深度）。

    例如：输入 "盈亏平衡点"
    返回：{
        "concept": "盈亏平衡点",
        "prerequisites": ["客户获取成本", "用户终身价值", "定价策略"],
        "learning_order": ["客户获取成本", "用户终身价值", "定价策略", "盈亏平衡点"],
    }

    限制 max_depth 避免遍历整个概念图（因为 Concept_Prerequisite 超边
    是多节点超边，BFS 会迅速扩散到所有连通概念）。
    """
    concept_id = _find_concept_id(concept_name)
    if not concept_id:
        return {"concept": concept_name, "prerequisites": [], "learning_order": [concept_name]}

    # BFS with depth limit: 只找直接关联的前置概念
    from collections import deque
    queue: deque = deque([(concept_id, 0)])
    visited = {concept_id}
    prereqs = []  # 按发现顺序

    while queue:
        current, depth = queue.popleft()
        if depth >= max_depth:
            continue
        for he in get_incident_edges(current):
            if he["type"] != "Concept_Prerequisite":
                continue
            for nid in he["nodes"]:
                if nid not in visited and nid in _nodes and _nodes[nid]["type"] == "Concept":
                    visited.add(nid)
                    prereqs.append(_nodes[nid]["label"])
                    queue.append((nid, depth + 1))

    # 学习顺序：前置概念在前，目标概念在后（最多保留 6 个）
    prereqs = prereqs[:6]
    learning_order = list(reversed(prereqs)) + [_nodes[concept_id]["label"]]

    return {
        "concept": _nodes[concept_id]["label"],
        "prerequisites": prereqs,
        "learning_order": learning_order,
    }


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
    """Find concept node ID by label or keyword (bidirectional substring match)."""
    kw = label_or_keyword.lower()
    best: tuple[int, str | None] = (0, None)  # (match_length, node_id)
    for nid, node in _nodes.items():
        if node["type"] != "Concept":
            continue
        label = node["label"].lower()
        en = node.get("properties", {}).get("en", "").lower()
        # Exact match — return immediately
        if kw == label or kw == en:
            return nid
        # Bidirectional: kw in label OR label in kw (handles "护城河理论" vs "护城河")
        if kw in label or label in kw or (en and (kw in en or en in kw)):
            match_len = len(label)
            if match_len > best[0]:
                best = (match_len, nid)
    return best[1]


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

    # 4. Concept info + prerequisites (multi-hop)
    if concept:
        cid = _find_concept_id(concept)
        if cid:
            node = _nodes[cid]
            neighbors = get_neighbors(cid)
            concept_neighbors = [n for n in neighbors if n["type"] == "Concept"]
            # 获取前置依赖（多跳）
            prereq_info = get_concept_prerequisites(concept)
            context["concept_info"].append({
                "concept": node["label"],
                "related_concepts": [n["label"] for n in concept_neighbors[:5]],
                "prerequisites": prereq_info["prerequisites"],
                "learning_order": prereq_info["learning_order"],
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

    # 7. Multi-hop reasoning chains (2-hop traversal)
    # 从已找到的 similar_projects 出发，做多跳推理
    similar_proj_ids = []
    if tech_keywords:
        similar_projs = search_by_technology(tech_keywords)
        similar_proj_ids = [s["project"]["id"] for s in similar_projs[:5]]
    if industry and not similar_proj_ids:
        industry_projs = search_by_industry(industry)
        similar_proj_ids = [s["project"]["id"] for s in industry_projs[:5]]

    if similar_proj_ids:
        reasoning = build_reasoning_chain(similar_proj_ids, max_hops=2)
        context["reasoning_chains"] = reasoning

    # 8. Concept learning paths for risk-related concepts
    # 从风险模式中提到的概念，生成学习路径建议
    if context["risk_patterns"]:
        learning_paths = []
        seen_concepts: set[str] = set()
        for rp in context["risk_patterns"]:
            for c in rp.get("related_concepts", []):
                if c not in seen_concepts:
                    seen_concepts.add(c)
                    prereqs = get_concept_prerequisites(c)
                    if prereqs["prerequisites"]:
                        learning_paths.append(prereqs)
        context["concept_learning_paths"] = learning_paths[:5]

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
        for i, p in enumerate(ctx["similar_projects"][:8], 1):
            techs_str = ",".join(p["techs"]) if p.get("techs") else "未知"
            # 语义检索的项目可能没有 moat/biz 信息
            score = p.get("semantic_score")
            if score:
                relevance = f"相关度{score:.0%}"
            else:
                moat_str = "有壁垒" if p.get("has_moat") else "⚠无明确壁垒"
                biz_str = "有商业模式" if p.get("has_biz_model") else "⚠商业模式不清晰"
                relevance = f"{moat_str} | {biz_str}"
            parts.append(
                f"  {i}. {p['name']}（{p.get('industry', '')}）"
                f"— 技术：{techs_str} | {relevance}"
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
            # 显示前置依赖和学习路径（多跳遍历结果）
            if c.get("prerequisites"):
                parts.append(f"  📚 前置知识：{' → '.join(c['prerequisites'])}")
            if c.get("learning_order") and len(c["learning_order"]) > 1:
                parts.append(f"  🗺️ 建议学习顺序：{' → '.join(c['learning_order'])}")

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

    # 多跳推理链
    reasoning = ctx.get("reasoning_chains", {})

    if reasoning.get("risk_to_concept_chains"):
        parts.append("\n【超图多跳推理：风险→修复概念→前置知识】")
        for chain in reasoning["risk_to_concept_chains"][:3]:
            fix_str = "、".join(chain["fix_concepts"][:3])
            parts.append(f"  ⚠ {chain['risk']} → 建议学习：{fix_str}")
            for concept, prereqs in chain.get("prerequisites", {}).items():
                if prereqs:
                    parts.append(f"    ↳ 学习「{concept}」前需先掌握：{' → '.join(prereqs[:3])}")

    if reasoning.get("pain_similarity_chains"):
        parts.append("\n【超图多跳推理：相似痛点项目】")
        for chain in reasoning["pain_similarity_chains"][:3]:
            pains = "、".join(chain["shared_pain_points"][:3]) if chain["shared_pain_points"] else "相关痛点"
            parts.append(f"  📌 {chain['project']}（共同痛点：{pains}）")

    # 概念学习路径
    if ctx.get("concept_learning_paths"):
        parts.append("\n【超图推荐学习路径】")
        for lp in ctx["concept_learning_paths"][:3]:
            if lp["learning_order"]:
                parts.append(f"  📖 {lp['concept']}：{' → '.join(lp['learning_order'])}")

    return "\n".join(parts) if parts else ""
