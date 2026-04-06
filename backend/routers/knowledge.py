"""
routers/knowledge.py
────────────────────────────────────────────────────────────────
知识卡片 API — Knowledge Cards CRUD + 检索
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from services.knowledge_cards import (
    get_all_cards, get_card, search_cards,
    generate_cards_from_hypergraph,
    get_cards_for_rubric_gap,
)
from services.competition_templates import get_all_templates, match_template, get_template_by_id

router = APIRouter(prefix="/api/knowledge", tags=["knowledge"])


@router.get("/cards")
def list_cards(
    card_type: str = "",
    stage: str = "",
    dimension: str = "",
    rubric: str = "",
    industry: str = "",
    q: str = "",
    limit: int = 20,
):
    """
    检索知识卡片。支持多条件组合过滤 + 关键词搜索。

    参数：
    - card_type: concept | method | case | mistake | template
    - stage: discovery | ideation | modeling | execution | pitching
    - dimension: empathy | ideation | business | execution | pitching
    - rubric: R1-R9
    - industry: 行业过滤
    - q: 关键词搜索
    - limit: 最大返回数
    """
    results = search_cards(
        query=q,
        card_type=card_type,
        stage=stage,
        dimension=dimension,
        rubric=rubric,
        industry=industry,
        max_results=limit,
    )
    return {"cards": results, "total": len(results)}


@router.get("/cards/{card_id}")
def get_card_detail(card_id: str):
    """获取单张卡片详情。"""
    card = get_card(card_id)
    if not card:
        raise HTTPException(status_code=404, detail="卡片不存在")
    return card.to_dict()


@router.get("/cards/rubric/{rubric_id}")
def get_cards_by_rubric(rubric_id: str, dimension: str = ""):
    """
    为特定 Rubric 缺口推荐卡片。
    用于：学生某个维度得分低时，推荐相关知识卡片。
    """
    cards = get_cards_for_rubric_gap(rubric_id, dimension)
    return {"cards": cards, "rubric": rubric_id}


@router.post("/cards/generate")
def generate_cards():
    """
    从超图 + Rubric + H规则一次性生成知识卡片库。
    幂等操作：重复调用会覆盖已有同 ID 卡片。
    """
    stats = generate_cards_from_hypergraph()
    return {"ok": True, **stats}


@router.get("/competition-templates")
def list_competition_templates():
    """获取所有赛事评估模板。"""
    templates = get_all_templates()
    return {"templates": templates, "total": len(templates)}


@router.get("/competition-templates/{template_id}")
def get_competition_template(template_id: str):
    """获取单个赛事模板详情。"""
    tpl = get_template_by_id(template_id)
    if not tpl:
        raise HTTPException(status_code=404, detail="赛事模板不存在")
    return tpl


@router.post("/competition-templates/match")
def match_competition_template(query: str = ""):
    """根据用户输入匹配赛事模板。"""
    tpl = match_template(query)
    if not tpl:
        return {"matched": False, "template": None}
    return {"matched": True, "template": tpl}


@router.get("/stats")
def get_knowledge_stats():
    """知识卡片统计。"""
    cards = get_all_cards()
    type_counts: dict[str, int] = {}
    stage_counts: dict[str, int] = {}
    dim_counts: dict[str, int] = {}
    for card in cards:
        type_counts[card.card_type] = type_counts.get(card.card_type, 0) + 1
        for s in card.stage:
            stage_counts[s] = stage_counts.get(s, 0) + 1
        for d in card.dimensions:
            dim_counts[d] = dim_counts.get(d, 0) + 1
    return {
        "total": len(cards),
        "by_type": type_counts,
        "by_stage": stage_counts,
        "by_dimension": dim_counts,
    }
